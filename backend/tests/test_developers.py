"""
DevTwin Backend Tests — Developers API

Tests for `POST /developers/me`.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from app.main import create_app
from app.api.dependencies.auth import get_current_user, AuthenticatedUser
from app.db.connection import get_db_session
from app.models.developer import Developer


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_create_developer_me_unauthenticated(app):
    """POST /developers/me without Auth returns 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post("/developers/me")
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_developer_me_first_time(app):
    """First authenticated request creates the Developer row and returns 201."""
    auth_user_id = uuid.uuid4()
    mock_user = AuthenticatedUser(sub=str(auth_user_id))

    # Mock DB session
    mock_session = AsyncMock()
    mock_session.add = MagicMock()  # add() is synchronous in SQLAlchemy
    # First select returns nothing
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    # Mock refresh to populate UUIDs and timestamps
    async def mock_refresh(instance):
        instance.id = uuid.uuid4()
        from datetime import datetime, timezone
        instance.created_at = datetime.now(timezone.utc)
        instance.updated_at = instance.created_at

    mock_session.refresh.side_effect = mock_refresh

    app.dependency_overrides[get_current_user] = lambda: mock_user
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post("/developers/me")

    assert response.status_code == 201
    data = response.json()
    assert data["auth_user_id"] == str(auth_user_id)
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    
    # Verify session calls
    mock_session.add.assert_called_once()
    added_dev = mock_session.add.call_args[0][0]
    assert added_dev.auth_user_id == auth_user_id
    mock_session.commit.assert_awaited_once()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_developer_me_existing(app):
    """Repeated request returns the existing Developer row and 200."""
    auth_user_id = uuid.uuid4()
    mock_user = AuthenticatedUser(sub=str(auth_user_id))

    _now = datetime.now(timezone.utc)
    existing_dev = Developer(
        id=uuid.uuid4(),
        auth_user_id=auth_user_id,
    )
    existing_dev.created_at = _now
    existing_dev.updated_at = _now

    mock_session = AsyncMock()
    mock_session.add = MagicMock()  # add() is synchronous in SQLAlchemy
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_dev
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_current_user] = lambda: mock_user
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        # Client tries to send an arbitrary body, it should be ignored
        response = await client.post("/developers/me", json={"auth_user_id": str(uuid.uuid4())})

    assert response.status_code == 200
    data = response.json()
    assert data["auth_user_id"] == str(auth_user_id)
    assert data["id"] == str(existing_dev.id)
    
    # Should not attempt to add or commit
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_called()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_developer_me_race_condition(app):
    """Handles IntegrityError and returns 200 if record was created concurrently."""
    auth_user_id = uuid.uuid4()
    mock_user = AuthenticatedUser(sub=str(auth_user_id))

    _now = datetime.now(timezone.utc)
    existing_dev = Developer(
        id=uuid.uuid4(),
        auth_user_id=auth_user_id,
    )
    existing_dev.created_at = _now
    existing_dev.updated_at = _now

    mock_session = AsyncMock()
    mock_session.add = MagicMock()  # add() is synchronous in SQLAlchemy
    
    # 1st execute: returns None (not found)
    # 2nd execute (after rollback): returns existing_dev
    mock_result_none = MagicMock()
    mock_result_none.scalar_one_or_none.return_value = None
    
    mock_result_found = MagicMock()
    mock_result_found.scalar_one_or_none.return_value = existing_dev

    mock_session.execute.side_effect = [mock_result_none, mock_result_found]
    
    # Commit raises IntegrityError due to race
    mock_session.commit.side_effect = IntegrityError(None, None, Exception())

    app.dependency_overrides[get_current_user] = lambda: mock_user
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post("/developers/me")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(existing_dev.id)
    assert data["auth_user_id"] == str(auth_user_id)

    mock_session.rollback.assert_awaited_once()
    assert mock_session.execute.call_count == 2

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_developer_me_invalid_sub(app):
    """Invalid UUID format in JWT sub returns 401."""
    mock_user = AuthenticatedUser(sub="not-a-uuid")
    app.dependency_overrides[get_current_user] = lambda: mock_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post("/developers/me")

    assert response.status_code == 401

    app.dependency_overrides.clear()
