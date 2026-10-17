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
from app.models.repository import Repository
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


# ===========================================================================
# GET /repositories Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_list_repositories_unauthenticated(app):
    """GET /repositories without Auth returns 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/repositories")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_repositories_empty(app, mock_developer):
    """GET /repositories returns 200 and empty list when no repositories exist."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = []
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/repositories")

    assert response.status_code == 200
    assert response.json() == []

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_repositories_multiple_owned(app, mock_developer):
    """GET /repositories returns only repositories in projects owned by the developer."""
    proj_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    repo1 = Repository(
        id=uuid.uuid4(),
        project_id=proj_id,
        github_repo_id=101,
        owner_login="devtwin-org",
        name="repo-alpha",
        full_name="devtwin-org/repo-alpha",
        url="https://github.com/devtwin-org/repo-alpha",
        default_branch="main",
        visibility="public",
        synced_at=None,
        created_at=now,
    )
    repo2 = Repository(
        id=uuid.uuid4(),
        project_id=proj_id,
        github_repo_id=102,
        owner_login="devtwin-org",
        name="repo-beta",
        full_name="devtwin-org/repo-beta",
        url="https://github.com/devtwin-org/repo-beta",
        default_branch="develop",
        visibility="private",
        synced_at=None,
        created_at=now,
    )

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [repo1, repo2]
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/repositories")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "repo-alpha"
    assert data[0]["full_name"] == "devtwin-org/repo-alpha"
    assert data[0]["default_branch"] == "main"
    assert data[0]["visibility"] == "public"
    assert data[1]["name"] == "repo-beta"
    assert data[1]["default_branch"] == "develop"
    assert data[1]["visibility"] == "private"
    # Ensure no token or secret leaked
    assert "token" not in str(data).lower()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_repositories_with_project_id_filter_success(app, mock_developer):
    """GET /repositories?project_id=... filters repositories by the specified owned project."""
    proj_id = uuid.uuid4()
    mock_project = Project(id=proj_id, developer_id=mock_developer.id)
    repo = Repository(
        id=uuid.uuid4(),
        project_id=proj_id,
        github_repo_id=201,
        owner_login="owner",
        name="filtered-repo",
        full_name="owner/filtered-repo",
        url="https://github.com/owner/filtered-repo",
        default_branch="main",
        visibility="public",
        synced_at=None,
        created_at=datetime.now(timezone.utc),
    )

    mock_session = AsyncMock()
    # First query checks project ownership, second fetches filtered repositories
    mock_proj_result = MagicMock()
    mock_proj_result.scalar_one_or_none.return_value = mock_project

    mock_repo_result = MagicMock()
    mock_repo_result.scalars().all.return_value = [repo]

    mock_session.execute.side_effect = [mock_proj_result, mock_repo_result]

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(f"/repositories?project_id={proj_id}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "filtered-repo"
    assert data[0]["project_id"] == str(proj_id)

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_repositories_project_not_owned(app, mock_developer):
    """GET /repositories?project_id=... returns 404 if project is not owned by developer."""
    unowned_proj_id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_proj_result = MagicMock()
    mock_proj_result.scalar_one_or_none.return_value = None  # Not found or unowned
    mock_session.execute.return_value = mock_proj_result

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(f"/repositories?project_id={unowned_proj_id}")

    assert response.status_code == 404
    assert "Project not found or not owned by developer." in response.json()["detail"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_repositories_db_error_returns_500(app, mock_developer):
    """GET /repositories returns 500 when database fails."""
    mock_session = AsyncMock()
    mock_session.execute.side_effect = Exception("Database connection failure")

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/repositories")

    assert response.status_code == 500
    assert "Failed to fetch repositories." in response.json()["detail"]

    app.dependency_overrides.clear()


# ===========================================================================
# GET /repositories/{id} Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_get_repository_unauthenticated(app):
    """GET /repositories/{id} without Auth returns 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(f"/repositories/{uuid.uuid4()}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_repository_owned_success(app, mock_developer):
    """GET /repositories/{id} returns 200 and repository details when owned."""
    repo_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    repo = Repository(
        id=repo_id,
        project_id=proj_id,
        github_repo_id=301,
        owner_login="owner",
        name="single-repo",
        full_name="owner/single-repo",
        url="https://github.com/owner/single-repo",
        default_branch="main",
        visibility="public",
        synced_at=None,
        created_at=now,
    )

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = repo
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(f"/repositories/{repo_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(repo_id)
    assert data["project_id"] == str(proj_id)
    assert data["name"] == "single-repo"
    assert data["full_name"] == "owner/single-repo"
    assert data["default_branch"] == "main"
    assert data["visibility"] == "public"
    assert "token" not in str(data).lower()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_repository_nonexistent_returns_404(app, mock_developer):
    """GET /repositories/{id} returns 404 when repository does not exist."""
    random_id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(f"/repositories/{random_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Repository not found."

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_repository_other_developer_returns_404(app, mock_developer):
    """GET /repositories/{id} returns 404 when repository belongs to another developer's project."""
    repo_id = uuid.uuid4()

    mock_session = AsyncMock()
    # The ownership query filters by Project.developer_id == developer.id, returning None
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(f"/repositories/{repo_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Repository not found."

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_repository_db_error_returns_500(app, mock_developer):
    """GET /repositories/{id} returns 500 when database query errors."""
    repo_id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_session.execute.side_effect = Exception("DB connection timeout")

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(f"/repositories/{repo_id}")

    assert response.status_code == 500
    assert "Failed to fetch repository." in response.json()["detail"]

    app.dependency_overrides.clear()
