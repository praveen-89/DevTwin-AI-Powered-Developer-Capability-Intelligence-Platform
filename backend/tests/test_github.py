"""
DevTwin Backend Tests â€” GitHub Routes
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.api.dependencies.auth import get_current_developer
from app.db.connection import get_db_session
from app.models.developer import Developer
from app.services.github.state import PendingOAuthState
from app.services.github.exceptions import GitHubStatePersistenceError


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_get_github_install_unauthenticated(app):
    """GET /github/install without Auth returns 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/github/install")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_github_install_success(app):
    """Valid request returns a JSON install_url containing state but NOT PKCE parameters."""
    developer_id = uuid.uuid4()
    mock_dev = Developer(id=developer_id, auth_user_id=uuid.uuid4())

    app.dependency_overrides[get_current_developer] = lambda: mock_dev

    mock_session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    pending_state = PendingOAuthState(
        raw_state="test_raw_state_value_for_url",
        state_id=uuid.uuid4(),
        expires_at=datetime.now(timezone.utc),
    )

    with patch("app.api.routes.github.create_pending_state", return_value=pending_state) as mock_create:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/install")

    assert response.status_code == 200
    data = response.json()
    assert "install_url" in data

    url = data["install_url"]
    # state must be present for CSRF protection and developer binding
    assert "state=test_raw_state_value_for_url" in url
    # PKCE parameters must NOT be present â€” GitHub ignores them on /installations/new
    assert "code_challenge" not in url
    assert "code_challenge_method" not in url
    # Must point to the correct GitHub App slug
    assert "https://github.com/apps/app/installations/new" in url

    mock_create.assert_awaited_once_with(mock_session, developer_id)
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_github_install_persistence_error(app):
    """Database persistence failure returns 500."""
    developer_id = uuid.uuid4()
    mock_dev = Developer(id=developer_id, auth_user_id=uuid.uuid4())

    app.dependency_overrides[get_current_developer] = lambda: mock_dev

    mock_session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    with patch("app.api.routes.github.create_pending_state", side_effect=GitHubStatePersistenceError("DB Error")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/install")

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to initialize GitHub installation flow."
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_callback_missing_state(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/github/callback?installation_id=123")
    assert response.status_code == 400
    assert "Missing state" in response.json()["detail"]

@pytest.mark.asyncio
async def test_callback_missing_installation_id(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/github/callback?state=abc")
    assert response.status_code == 400
    assert "Missing installation_id" in response.json()["detail"]

@pytest.mark.asyncio
async def test_callback_invalid_state(app):
    mock_session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    from app.services.github.state import GitHubStateNotFoundError
    with patch("app.api.routes.github.claim_state", side_effect=GitHubStateNotFoundError):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/callback?state=invalid&installation_id=123")

    assert response.status_code == 400
    assert "Invalid state token" in response.json()["detail"]
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_callback_expired_state(app):
    mock_session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    from app.services.github.state import GitHubStateExpiredError
    with patch("app.api.routes.github.claim_state", side_effect=GitHubStateExpiredError):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/callback?state=expired&installation_id=123")

    assert response.status_code == 400
    assert "State token expired or already used" in response.json()["detail"]
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_callback_installation_verification_failed(app):
    mock_session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    from app.services.github.state import GitHubOAuthStateContext
    from app.services.github.exceptions import GitHubHTTPError

    claimed_state = GitHubOAuthStateContext(developer_id=uuid.uuid4(), code_verifier="verifier", state_id=uuid.uuid4())

    mock_gh_instance = AsyncMock()
    mock_gh_instance.get_installation.side_effect = GitHubHTTPError("404 Not Found")

    with patch("app.api.routes.github.claim_state", return_value=claimed_state), \
         patch("app.api.routes.github.generate_app_jwt", return_value="jwt"), \
         patch("app.api.routes.github.GitHubClient", return_value=mock_gh_instance):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/callback?state=valid&installation_id=123")

    assert response.status_code == 404
    assert "GitHub App Installation not found" in response.json()["detail"]
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_callback_success_first_time_link(app):
    from unittest.mock import MagicMock
    mock_session = AsyncMock()
    mock_result = MagicMock()  # scalar_one_or_none is sync
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_db_session] = lambda: mock_session

    from app.services.github.state import GitHubOAuthStateContext
    from app.services.github.types import GitHubInstallation

    dev_id = uuid.uuid4()
    claimed_state = GitHubOAuthStateContext(developer_id=dev_id, code_verifier="verifier", state_id=uuid.uuid4())
    installation = GitHubInstallation(installation_id=123, account_github_id=456, account_login="user")

    mock_gh_instance = AsyncMock()
    mock_gh_instance.get_installation.return_value = installation

    with patch("app.api.routes.github.claim_state", return_value=claimed_state), \
         patch("app.api.routes.github.generate_app_jwt", return_value="jwt"), \
         patch("app.api.routes.github.GitHubClient", return_value=mock_gh_instance):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/callback?state=valid&installation_id=123")

    assert response.status_code == 200
    assert response.json()["status"] == "success"

    mock_session.add.assert_called_once()
    added_account = mock_session.add.call_args[0][0]
    assert added_account.developer_id == dev_id
    assert added_account.github_id == 456
    assert added_account.username == "user"
    assert added_account.installation_id == 123

    mock_session.commit.assert_called_once()
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_callback_success_reconnect(app):
    from unittest.mock import MagicMock
    mock_session = AsyncMock()
    from app.models.github_account import GitHubAccount
    dev_id = uuid.uuid4()

    existing_account = GitHubAccount(
        developer_id=dev_id, github_id=456, username="old_user", installation_id=111, disconnected_at=datetime.now()
    )
    mock_result = MagicMock()  # scalar_one_or_none is sync
    mock_result.scalar_one_or_none.return_value = existing_account
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_db_session] = lambda: mock_session

    from app.services.github.state import GitHubOAuthStateContext
    from app.services.github.types import GitHubInstallation

    claimed_state = GitHubOAuthStateContext(developer_id=dev_id, code_verifier="verifier", state_id=uuid.uuid4())
    installation = GitHubInstallation(installation_id=123, account_github_id=456, account_login="new_user")

    mock_gh_instance = AsyncMock()
    mock_gh_instance.get_installation.return_value = installation

    with patch("app.api.routes.github.claim_state", return_value=claimed_state), \
         patch("app.api.routes.github.generate_app_jwt", return_value="jwt"), \
         patch("app.api.routes.github.GitHubClient", return_value=mock_gh_instance):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/callback?state=valid&installation_id=123")

    assert response.status_code == 200
    assert existing_account.installation_id == 123
    assert existing_account.username == "new_user"
    assert existing_account.disconnected_at is None

    mock_session.commit.assert_called_once()
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_callback_cross_developer_conflict(app):
    from unittest.mock import MagicMock
    mock_session = AsyncMock()
    mock_result = MagicMock()  # scalar_one_or_none is sync
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    from sqlalchemy.exc import IntegrityError
    mock_session.commit.side_effect = IntegrityError("statement", "params", "orig")

    app.dependency_overrides[get_db_session] = lambda: mock_session

    from app.services.github.state import GitHubOAuthStateContext
    from app.services.github.types import GitHubInstallation

    claimed_state = GitHubOAuthStateContext(developer_id=uuid.uuid4(), code_verifier="verifier", state_id=uuid.uuid4())
    installation = GitHubInstallation(installation_id=123, account_github_id=456, account_login="user")

    mock_gh_instance = AsyncMock()
    mock_gh_instance.get_installation.return_value = installation

    with patch("app.api.routes.github.claim_state", return_value=claimed_state), \
         patch("app.api.routes.github.generate_app_jwt", return_value="jwt"), \
         patch("app.api.routes.github.GitHubClient", return_value=mock_gh_instance):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/callback?state=valid&installation_id=123")

    assert response.status_code == 409
    assert "already linked to another developer" in response.json()["detail"]
    mock_session.rollback.assert_called_once()
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_callback_different_account_conflict(app):
    from unittest.mock import MagicMock
    mock_session = AsyncMock()
    from app.models.github_account import GitHubAccount
    dev_id = uuid.uuid4()

    existing_account = GitHubAccount(
        developer_id=dev_id, github_id=999, username="other_user", installation_id=111, disconnected_at=None
    )
    mock_result = MagicMock()  # scalar_one_or_none is sync
    mock_result.scalar_one_or_none.return_value = existing_account
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_db_session] = lambda: mock_session

    from app.services.github.state import GitHubOAuthStateContext
    from app.services.github.types import GitHubInstallation

    claimed_state = GitHubOAuthStateContext(developer_id=dev_id, code_verifier="verifier", state_id=uuid.uuid4())
    installation = GitHubInstallation(installation_id=123, account_github_id=456, account_login="user")

    mock_gh_instance = AsyncMock()
    mock_gh_instance.get_installation.return_value = installation

    with patch("app.api.routes.github.claim_state", return_value=claimed_state), \
         patch("app.api.routes.github.generate_app_jwt", return_value="jwt"), \
         patch("app.api.routes.github.GitHubClient", return_value=mock_gh_instance):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/callback?state=valid&installation_id=123")

    assert response.status_code == 409
    assert "active GitHub account connected" in response.json()["detail"]
    mock_session.rollback.assert_called_once()
    app.dependency_overrides.clear()
