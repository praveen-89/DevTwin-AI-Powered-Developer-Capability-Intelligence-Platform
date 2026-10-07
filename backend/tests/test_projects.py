"""
DevTwin Backend Tests — Projects API
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.api.dependencies.auth import get_current_developer
from app.db.connection import get_db_session
from app.models.developer import Developer
from app.models.project import Project


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_create_project_unauthenticated(app):
    """POST /projects without Auth returns 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post("/projects", json={"name": "test project"})
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_project_authenticated(app):
    """POST /projects creates project and returns 201."""
    developer_id = uuid.uuid4()
    mock_developer = Developer(id=developer_id, auth_user_id=uuid.uuid4())

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    
    async def mock_refresh(instance):
        instance.id = uuid.uuid4()
        instance.created_at = datetime.now(timezone.utc)

    mock_session.refresh.side_effect = mock_refresh

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post("/projects", json={"name": "Test Project"})

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Project"
    assert "id" in data
    assert "created_at" in data
    assert "developer_id" not in data
    
    mock_session.add.assert_called_once()
    added_project = mock_session.add.call_args[0][0]
    assert added_project.developer_id == developer_id
    assert added_project.name == "Test Project"
    mock_session.commit.assert_awaited_once()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_project_whitespace_name(app):
    """POST /projects with whitespace-only name -> validation error."""
    mock_developer = Developer(id=uuid.uuid4(), auth_user_id=uuid.uuid4())
    app.dependency_overrides[get_current_developer] = lambda: mock_developer

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post("/projects", json={"name": "   "})

    assert response.status_code == 422
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_project_ignore_client_developer_id(app):
    """POST /projects must not accept/override developer_id from client input."""
    developer_id = uuid.uuid4()
    mock_developer = Developer(id=developer_id, auth_user_id=uuid.uuid4())

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    
    async def mock_refresh(instance):
        instance.id = uuid.uuid4()
        instance.created_at = datetime.now(timezone.utc)
    mock_session.refresh.side_effect = mock_refresh

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    malicious_developer_id = str(uuid.uuid4())

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/projects", 
            json={"name": "Test", "developer_id": malicious_developer_id}
        )

    assert response.status_code == 201
    mock_session.add.assert_called_once()
    added_project = mock_session.add.call_args[0][0]
    assert added_project.developer_id == developer_id
    assert str(added_project.developer_id) != malicious_developer_id

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_projects_unauthenticated(app):
    """GET /projects without authentication -> 401"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/projects")
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_projects_authenticated(app):
    """GET /projects returns only authenticated developer's projects."""
    developer_id = uuid.uuid4()
    mock_developer = Developer(id=developer_id, auth_user_id=uuid.uuid4())

    p1 = Project(id=uuid.uuid4(), developer_id=developer_id, name="P1", created_at=datetime.now(timezone.utc))
    p2 = Project(id=uuid.uuid4(), developer_id=developer_id, name="P2", created_at=datetime.now(timezone.utc))

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [p1, p2]
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/projects")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "P1"
    assert data[1]["name"] == "P2"
    assert "developer_id" not in data[0]

    app.dependency_overrides.clear()
