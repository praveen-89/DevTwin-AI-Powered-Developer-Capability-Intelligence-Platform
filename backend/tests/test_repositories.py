"""
DevTwin Backend Tests — Repositories API
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from app.main import create_app
from app.api.dependencies.auth import get_current_developer
from app.db.connection import get_db_session
from app.models.developer import Developer
from app.models.project import Project
from app.models.github_account import GitHubAccount
from app.services.github.exceptions import GitHubHTTPError, GitHubIntegrationError


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def mock_developer():
    return Developer(id=uuid.uuid4(), auth_user_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_create_repository_unauthenticated(app):
    """POST /repositories without Auth returns 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/repositories", json={"project_id": str(uuid.uuid4()), "github_repo_id": 123})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_repository_no_github_account(app, mock_developer):
    """POST /repositories returns 400 if no GitHubAccount."""
    mock_session = AsyncMock()
    mock_result_project = MagicMock()
    mock_result_project.scalar_one_or_none.return_value = Project(id=uuid.uuid4(), developer_id=mock_developer.id)
    
    mock_result_gh = MagicMock()
    mock_result_gh.scalar_one_or_none.return_value = None
    
    mock_session.execute.side_effect = [mock_result_project, mock_result_gh]

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/repositories", json={"project_id": str(uuid.uuid4()), "github_repo_id": 123})
    
    assert response.status_code == 400
    assert "No GitHub account" in response.json()["detail"]
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_repository_disconnected_github_account(app, mock_developer):
    """POST /repositories returns 400 if GitHubAccount is disconnected."""
    mock_session = AsyncMock()
    mock_result_project = MagicMock()
    mock_result_project.scalar_one_or_none.return_value = Project(id=uuid.uuid4(), developer_id=mock_developer.id)
    
    gh_account = GitHubAccount(developer_id=mock_developer.id, disconnected_at=datetime.now(timezone.utc))
    mock_result_gh = MagicMock()
    mock_result_gh.scalar_one_or_none.return_value = gh_account
    
    mock_session.execute.side_effect = [mock_result_project, mock_result_gh]

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/repositories", json={"project_id": str(uuid.uuid4()), "github_repo_id": 123})
    
    assert response.status_code == 400
    assert "disconnected" in response.json()["detail"]
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_repository_no_installation(app, mock_developer):
    """POST /repositories returns 400 if GitHubAccount lacks installation_id."""
    mock_session = AsyncMock()
    mock_result_project = MagicMock()
    mock_result_project.scalar_one_or_none.return_value = Project(id=uuid.uuid4(), developer_id=mock_developer.id)
    
    gh_account = GitHubAccount(developer_id=mock_developer.id, installation_id=None)
    mock_result_gh = MagicMock()
    mock_result_gh.scalar_one_or_none.return_value = gh_account
    
    mock_session.execute.side_effect = [mock_result_project, mock_result_gh]

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/repositories", json={"project_id": str(uuid.uuid4()), "github_repo_id": 123})
    
    assert response.status_code == 400
    assert "personal GitHub App installation" in response.json()["detail"]
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_repository_project_not_owned(app, mock_developer):
    """POST /repositories returns 404 if project is not found/owned."""
    mock_session = AsyncMock()
    mock_result_project = MagicMock()
    mock_result_project.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result_project

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/repositories", json={"project_id": str(uuid.uuid4()), "github_repo_id": 123})
    
    assert response.status_code == 404
    app.dependency_overrides.clear()


@pytest.mark.asyncio
@patch("app.api.routes.repositories.generate_app_jwt")
@patch("app.api.routes.repositories.GitHubClient")
async def test_create_repository_token_generation_failure(MockGitHubClient, mock_generate_jwt, app, mock_developer):
    """POST /repositories handles GitHub token generation failure (502)."""
    mock_generate_jwt.return_value = "fake-jwt"
    mock_client = MockGitHubClient.return_value
    mock_client.create_installation_access_token = AsyncMock(side_effect=GitHubIntegrationError("Network Error"))

    mock_session = AsyncMock()
    mock_result_project = MagicMock()
    mock_result_project.scalar_one_or_none.return_value = Project(id=uuid.uuid4(), developer_id=mock_developer.id)
    
    gh_account = GitHubAccount(developer_id=mock_developer.id, installation_id=555)
    mock_result_gh = MagicMock()
    mock_result_gh.scalar_one_or_none.return_value = gh_account
    
    mock_session.execute.side_effect = [mock_result_project, mock_result_gh]

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/repositories", json={"project_id": str(uuid.uuid4()), "github_repo_id": 123})
    
    assert response.status_code == 502
    app.dependency_overrides.clear()


@pytest.mark.asyncio
@patch("app.api.routes.repositories.generate_app_jwt")
@patch("app.api.routes.repositories.GitHubClient")
async def test_create_repository_inaccessible_repository(MockGitHubClient, mock_generate_jwt, app, mock_developer):
    """POST /repositories returns 403 when repo is inaccessible (404 from GitHub)."""
    mock_generate_jwt.return_value = "fake-jwt"
    mock_client = MockGitHubClient.return_value
    mock_client.create_installation_access_token = AsyncMock(return_value="fake-token")
    mock_client.get_installation_repository = AsyncMock(side_effect=GitHubHTTPError("Repository not found or inaccessible.", status_code=404))

    mock_session = AsyncMock()
    mock_result_project = MagicMock()
    mock_result_project.scalar_one_or_none.return_value = Project(id=uuid.uuid4(), developer_id=mock_developer.id)
    
    gh_account = GitHubAccount(developer_id=mock_developer.id, installation_id=555)
    mock_result_gh = MagicMock()
    mock_result_gh.scalar_one_or_none.return_value = gh_account
    
    mock_session.execute.side_effect = [mock_result_project, mock_result_gh]

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/repositories", json={"project_id": str(uuid.uuid4()), "github_repo_id": 123})
    
    assert response.status_code == 403
    app.dependency_overrides.clear()


@pytest.mark.asyncio
@patch("app.api.routes.repositories.generate_app_jwt")
@patch("app.api.routes.repositories.GitHubClient")
async def test_create_repository_success(MockGitHubClient, mock_generate_jwt, app, mock_developer):
    """POST /repositories derives metadata from GitHub and returns 201."""
    mock_generate_jwt.return_value = "fake-jwt"
    mock_client = MockGitHubClient.return_value
    mock_client.create_installation_access_token = AsyncMock(return_value="fake-token")
    mock_client.get_installation_repository = AsyncMock(return_value={
        "owner": {"login": "testowner"},
        "name": "testrepo",
        "full_name": "testowner/testrepo",
        "html_url": "https://github.com/testowner/testrepo",
        "default_branch": "master",
        "visibility": "public"
    })

    mock_session = AsyncMock()
    project_id = uuid.uuid4()
    mock_result_project = MagicMock()
    mock_result_project.scalar_one_or_none.return_value = Project(id=project_id, developer_id=mock_developer.id)
    
    gh_account = GitHubAccount(developer_id=mock_developer.id, installation_id=555)
    mock_result_gh = MagicMock()
    mock_result_gh.scalar_one_or_none.return_value = gh_account
    
    mock_session.execute.side_effect = [mock_result_project, mock_result_gh]
    mock_session.add = MagicMock()

    async def mock_refresh(instance):
        instance.id = uuid.uuid4()
        instance.created_at = datetime.now(timezone.utc)
    mock_session.refresh.side_effect = mock_refresh

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    # Send client malicious data overriding metadata
    payload = {
        "project_id": str(project_id),
        "github_repo_id": 123,
        "owner_login": "hacker",
        "name": "hackerrepo"
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/repositories", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert data["owner_login"] == "testowner"  # Metadata came from GitHub, not client
    assert data["name"] == "testrepo"
    assert data["default_branch"] == "master"
    assert "fake-token" not in str(data)  # Token not leaked
    
    mock_session.add.assert_called_once()
    added_repo = mock_session.add.call_args[0][0]
    assert added_repo.project_id == project_id
    assert added_repo.owner_login == "testowner"
    assert added_repo.full_name == "testowner/testrepo"
    assert added_repo.default_branch == "master"
    mock_session.commit.assert_awaited_once()
    
    app.dependency_overrides.clear()


@pytest.mark.asyncio
@patch("app.api.routes.repositories.generate_app_jwt")
@patch("app.api.routes.repositories.GitHubClient")
async def test_create_repository_duplicate(MockGitHubClient, mock_generate_jwt, app, mock_developer):
    """POST /repositories returns 409 when repository is already registered."""
    mock_generate_jwt.return_value = "fake-jwt"
    mock_client = MockGitHubClient.return_value
    mock_client.create_installation_access_token = AsyncMock(return_value="fake-token")
    mock_client.get_installation_repository = AsyncMock(return_value={
        "owner": {"login": "testowner"},
        "name": "testrepo",
        "full_name": "testowner/testrepo",
        "html_url": "https://github.com/testowner/testrepo",
        "default_branch": "master",
        "visibility": "public"
    })

    mock_session = AsyncMock()
    mock_result_project = MagicMock()
    mock_result_project.scalar_one_or_none.return_value = Project(id=uuid.uuid4(), developer_id=mock_developer.id)
    
    gh_account = GitHubAccount(developer_id=mock_developer.id, installation_id=555)
    mock_result_gh = MagicMock()
    mock_result_gh.scalar_one_or_none.return_value = gh_account
    
    mock_session.execute.side_effect = [mock_result_project, mock_result_gh]
    mock_session.add = MagicMock()
    mock_session.commit.side_effect = IntegrityError("duplicate key", params={}, orig=Exception())

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/repositories", json={"project_id": str(uuid.uuid4()), "github_repo_id": 123})
    
    assert response.status_code == 409
    mock_session.rollback.assert_awaited_once()
    
    app.dependency_overrides.clear()


@pytest.mark.asyncio
@patch("app.api.routes.repositories.generate_app_jwt")
@patch("app.api.routes.repositories.GitHubClient")
async def test_create_repository_missing_metadata(MockGitHubClient, mock_generate_jwt, app, mock_developer):
    """POST /repositories returns 502 when GitHub metadata is incomplete."""
    mock_generate_jwt.return_value = "fake-jwt"
    mock_client = MockGitHubClient.return_value
    mock_client.create_installation_access_token = AsyncMock(return_value="fake-token")
    mock_client.get_installation_repository = AsyncMock(return_value={
        "owner": {},  # Missing login
        "name": "testrepo",
        "full_name": "testowner/testrepo",
        "html_url": "https://github.com/testowner/testrepo",
        "default_branch": "master",
        "visibility": "public"
    })

    mock_session = AsyncMock()
    mock_result_project = MagicMock()
    mock_result_project.scalar_one_or_none.return_value = Project(id=uuid.uuid4(), developer_id=mock_developer.id)
    
    gh_account = GitHubAccount(developer_id=mock_developer.id, installation_id=555)
    mock_result_gh = MagicMock()
    mock_result_gh.scalar_one_or_none.return_value = gh_account
    
    mock_session.execute.side_effect = [mock_result_project, mock_result_gh]

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/repositories", json={"project_id": str(uuid.uuid4()), "github_repo_id": 123})
    
    assert response.status_code == 502
    assert "Invalid repository metadata" in response.json()["detail"]
    app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_branch", [None, "", "   ", 123])
@patch("app.api.routes.repositories.generate_app_jwt")
@patch("app.api.routes.repositories.GitHubClient")
async def test_create_repository_missing_or_invalid_default_branch(
    MockGitHubClient, mock_generate_jwt, bad_branch, app, mock_developer
):
    """POST /repositories returns 502 when default_branch is missing, empty, or invalid."""
    mock_generate_jwt.return_value = "fake-jwt"
    mock_client = MockGitHubClient.return_value
    mock_client.create_installation_access_token = AsyncMock(return_value="fake-token")

    repo_data = {
        "owner": {"login": "testowner"},
        "name": "testrepo",
        "full_name": "testowner/testrepo",
        "html_url": "https://github.com/testowner/testrepo",
        "visibility": "public",
    }
    if bad_branch is not None:
        repo_data["default_branch"] = bad_branch

    mock_client.get_installation_repository = AsyncMock(return_value=repo_data)

    mock_session = AsyncMock()
    mock_result_project = MagicMock()
    mock_result_project.scalar_one_or_none.return_value = Project(id=uuid.uuid4(), developer_id=mock_developer.id)

    gh_account = GitHubAccount(developer_id=mock_developer.id, installation_id=555)
    mock_result_gh = MagicMock()
    mock_result_gh.scalar_one_or_none.return_value = gh_account

    mock_session.execute.side_effect = [mock_result_project, mock_result_gh]

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/repositories", json={"project_id": str(uuid.uuid4()), "github_repo_id": 123})

    assert response.status_code == 502
    assert response.json()["detail"] == "Invalid repository metadata received from GitHub."
    mock_session.add.assert_not_called()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
@patch("app.api.routes.repositories.generate_app_jwt")
@patch("app.api.routes.repositories.GitHubClient")
async def test_create_repository_unrelated_integrity_error(MockGitHubClient, mock_generate_jwt, app, mock_developer):
    """POST /repositories returns 500 on unrelated IntegrityError."""
    mock_generate_jwt.return_value = "fake-jwt"
    mock_client = MockGitHubClient.return_value
    mock_client.create_installation_access_token = AsyncMock(return_value="fake-token")
    mock_client.get_installation_repository = AsyncMock(return_value={
        "owner": {"login": "testowner"},
        "name": "testrepo",
        "full_name": "testowner/testrepo",
        "html_url": "https://github.com/testowner/testrepo",
        "default_branch": "master",
        "visibility": "public"
    })

    mock_session = AsyncMock()
    mock_result_project = MagicMock()
    mock_result_project.scalar_one_or_none.return_value = Project(id=uuid.uuid4(), developer_id=mock_developer.id)
    
    gh_account = GitHubAccount(developer_id=mock_developer.id, installation_id=555)
    mock_result_gh = MagicMock()
    mock_result_gh.scalar_one_or_none.return_value = gh_account
    
    mock_session.execute.side_effect = [mock_result_project, mock_result_gh]
    mock_session.add = MagicMock()
    
    # Simulating an IntegrityError not related to unique constraint
    err = IntegrityError("some unrelated constraint failed", params={}, orig=Exception("fake orig"))
    mock_session.commit.side_effect = err

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/repositories", json={"project_id": str(uuid.uuid4()), "github_repo_id": 123})
    
    assert response.status_code == 500
    mock_session.rollback.assert_awaited_once()
    
    app.dependency_overrides.clear()
