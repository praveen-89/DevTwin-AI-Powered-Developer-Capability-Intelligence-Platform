"""
DevTwin Backend Tests â€” GitHub Routes
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

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


def make_db_session(account_value):
    """
    Build a properly-typed AsyncMock session for the github_callback tests.

    Real SQLAlchemy: `await session.execute(...)` returns a synchronous Result
    object; `result.scalar_one_or_none()` is a plain synchronous call.

    AsyncMock makes all attribute access return AsyncMock too, so the naive
    chain `mock.execute.return_value.scalar_one_or_none.return_value = X`
    gives a coroutine instead of X when called. We fix this by wiring
    session.execute to return a plain MagicMock result.

    For side_effect (multiple calls), pass a list; for a single return value,
    pass the value directly.
    """
    session = AsyncMock()

    if isinstance(account_value, list):
        side_effects = account_value
        def execute_side_effect(*args, **kwargs):
            val = side_effects.pop(0)
            result = MagicMock()
            result.scalar_one_or_none = MagicMock(return_value=val)
            return result
        # execute is async so we need AsyncMock with side_effect
        async def async_execute(*args, **kwargs):
            return execute_side_effect(*args, **kwargs)
        session.execute = async_execute
    else:
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=account_value)
        session.execute = AsyncMock(return_value=result)

    return session

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
        code_verifier="test_verifier",
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
    # PKCE parameters must be present
    assert "code_challenge=" in url
    assert "code_challenge_method=S256" in url
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
async def test_github_callback_success(app):
    """A valid state and code performs the full Step 5B+5C flow and returns success."""
    from app.services.github.state import GitHubOAuthStateContext
    from app.services.github.client import OAuthToken, GitHubUser, GitHubInstallation
    from app.models.github_account import GitHubAccount

    developer_id = uuid.uuid4()
    mock_session = make_db_session(None)  # No existing github_accounts row.
    app.dependency_overrides[get_db_session] = lambda: mock_session

    state_context = GitHubOAuthStateContext(
        developer_id=developer_id,
        code_verifier="test_verifier",
        state_id=uuid.uuid4(),
    )

    test_token = "test_access_token_secret"
    mock_user = GitHubUser(github_id=123, username="testuser")
    mock_installations = [GitHubInstallation(installation_id=456, account_github_id=123, account_login="testuser")]

    with patch("app.api.routes.github.claim_state", return_value=state_context) as mock_claim, \
         patch("app.api.routes.github.GitHubClient.exchange_oauth_code", return_value=OAuthToken(access_token=test_token)) as mock_exchange, \
         patch("app.api.routes.github.GitHubClient.get_authenticated_user", return_value=mock_user) as mock_get_user, \
         patch("app.api.routes.github.GitHubClient.list_user_installations", return_value=mock_installations) as mock_list_installations:

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/callback?state=valid_state&code=valid_code")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["github_username"] == "testuser"
        assert "detail" in data
        # installations_count must NOT appear in Step 5C response
        assert "installations_count" not in data

        # Verify state is claimed
        mock_claim.assert_awaited_once_with(mock_session, "valid_state")

        # Verify verifier invariant — exact token passed
        mock_exchange.assert_awaited_once_with(code="valid_code", code_verifier="test_verifier")
        mock_get_user.assert_awaited_once_with(test_token)
        mock_list_installations.assert_awaited_once_with(test_token)

        # OAuth token must NOT appear in the response
        assert test_token not in str(data)
        # developer_id must NOT appear in the response
        assert str(developer_id) not in str(data)

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_github_callback_empty_installations(app):
    """Callback with zero installations still completes account linking successfully."""
    from app.services.github.state import GitHubOAuthStateContext
    from app.services.github.client import OAuthToken, GitHubUser

    mock_session = make_db_session(None)
    app.dependency_overrides[get_db_session] = lambda: mock_session

    state_context = GitHubOAuthStateContext(
        developer_id=uuid.uuid4(),
        code_verifier="test_verifier",
        state_id=uuid.uuid4(),
    )

    test_token = "test_access_token_secret"
    mock_user = GitHubUser(github_id=123, username="testuser")
    mock_installations = []

    with patch("app.api.routes.github.claim_state", return_value=state_context), \
         patch("app.api.routes.github.GitHubClient.exchange_oauth_code", return_value=OAuthToken(access_token=test_token)), \
         patch("app.api.routes.github.GitHubClient.get_authenticated_user", return_value=mock_user), \
         patch("app.api.routes.github.GitHubClient.list_user_installations", return_value=mock_installations):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/callback?state=valid_state&code=valid_code")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        # installations_count must not be in Step 5C response
        assert "installations_count" not in data

    app.dependency_overrides.clear()


# ===========================================================================
# Step 5C — Account Linking Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_github_callback_account_new_insert(app):
    """Case 1: No existing row → new GitHubAccount is inserted with correct fields."""
    from app.services.github.state import GitHubOAuthStateContext
    from app.services.github.client import OAuthToken, GitHubUser
    from app.models.github_account import GitHubAccount

    developer_id = uuid.uuid4()
    mock_session = make_db_session(None)
    app.dependency_overrides[get_db_session] = lambda: mock_session

    state_context = GitHubOAuthStateContext(
        developer_id=developer_id,
        code_verifier="test_verifier",
        state_id=uuid.uuid4(),
    )
    mock_user = GitHubUser(github_id=42, username="newuser")

    with patch("app.api.routes.github.claim_state", return_value=state_context), \
         patch("app.api.routes.github.GitHubClient.exchange_oauth_code", return_value=OAuthToken(access_token="tok")), \
         patch("app.api.routes.github.GitHubClient.get_authenticated_user", return_value=mock_user), \
         patch("app.api.routes.github.GitHubClient.list_user_installations", return_value=[]):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/callback?state=s&code=c")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["github_username"] == "newuser"

        # Verify session.add was called with a GitHubAccount with correct fields
        mock_session.add.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert isinstance(added, GitHubAccount)
        assert added.developer_id == developer_id
        assert added.github_id == 42
        assert added.username == "newuser"
        assert added.installation_id is None
        assert added.disconnected_at is None

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_github_callback_account_reconnect_same_developer(app):
    """Case 2: Existing row, same developer → username updated, disconnected_at cleared."""
    from app.services.github.state import GitHubOAuthStateContext
    from app.services.github.client import OAuthToken, GitHubUser
    from app.models.github_account import GitHubAccount
    from datetime import datetime, timezone

    developer_id = uuid.uuid4()
    existing = GitHubAccount(
        developer_id=developer_id,
        github_id=42,
        username="oldname",
        installation_id=None,
        disconnected_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )

    mock_session = make_db_session(existing)
    app.dependency_overrides[get_db_session] = lambda: mock_session

    state_context = GitHubOAuthStateContext(
        developer_id=developer_id,
        code_verifier="test_verifier",
        state_id=uuid.uuid4(),
    )
    mock_user = GitHubUser(github_id=42, username="newname")

    with patch("app.api.routes.github.claim_state", return_value=state_context), \
         patch("app.api.routes.github.GitHubClient.exchange_oauth_code", return_value=OAuthToken(access_token="tok")), \
         patch("app.api.routes.github.GitHubClient.get_authenticated_user", return_value=mock_user), \
         patch("app.api.routes.github.GitHubClient.list_user_installations", return_value=[]):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/callback?state=s&code=c")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["github_username"] == "newname"

        # Existing row must be mutated in-place (no new add)
        mock_session.add.assert_not_called()
        assert existing.username == "newname"
        assert existing.disconnected_at is None

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_github_callback_account_conflict_different_developer(app):
    """Case 3: Existing row belongs to different developer → 409 Conflict."""
    from app.services.github.state import GitHubOAuthStateContext
    from app.services.github.client import OAuthToken, GitHubUser
    from app.models.github_account import GitHubAccount

    owner_developer_id = uuid.uuid4()
    requesting_developer_id = uuid.uuid4()

    existing = GitHubAccount(
        developer_id=owner_developer_id,
        github_id=42,
        username="originalowner",
        installation_id=None,
        disconnected_at=None,
    )

    mock_session = make_db_session(existing)
    app.dependency_overrides[get_db_session] = lambda: mock_session

    state_context = GitHubOAuthStateContext(
        developer_id=requesting_developer_id,
        code_verifier="test_verifier",
        state_id=uuid.uuid4(),
    )
    mock_user = GitHubUser(github_id=42, username="originalowner")

    with patch("app.api.routes.github.claim_state", return_value=state_context), \
         patch("app.api.routes.github.GitHubClient.exchange_oauth_code", return_value=OAuthToken(access_token="tok")), \
         patch("app.api.routes.github.GitHubClient.get_authenticated_user", return_value=mock_user), \
         patch("app.api.routes.github.GitHubClient.list_user_installations", return_value=[]):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/callback?state=s&code=c")

        assert response.status_code == 409
        detail = response.json()["detail"]
        assert "already linked to another developer" in detail
        # Existing row must be untouched
        assert existing.username == "originalowner"
        assert existing.developer_id == owner_developer_id
        # No internal identifiers in response
        assert str(owner_developer_id) not in detail
        assert str(requesting_developer_id) not in detail

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_github_callback_integrity_error_same_developer_race(app):
    """IntegrityError during INSERT, re-query shows same developer → reconnect succeeds."""
    from sqlalchemy.exc import IntegrityError as SAIntegrityError
    from app.services.github.state import GitHubOAuthStateContext
    from app.services.github.client import OAuthToken, GitHubUser
    from app.models.github_account import GitHubAccount

    developer_id = uuid.uuid4()
    existing_after_race = GitHubAccount(
        developer_id=developer_id,
        github_id=42,
        username="raceuser",
        installation_id=None,
        disconnected_at=None,
    )

    mock_session = make_db_session([None, existing_after_race])
    # Simulate IntegrityError on first commit, success on second
    mock_session.commit.side_effect = [SAIntegrityError("dup", None, None), None]
    app.dependency_overrides[get_db_session] = lambda: mock_session

    state_context = GitHubOAuthStateContext(
        developer_id=developer_id,
        code_verifier="test_verifier",
        state_id=uuid.uuid4(),
    )
    mock_user = GitHubUser(github_id=42, username="raceuser")

    with patch("app.api.routes.github.claim_state", return_value=state_context), \
         patch("app.api.routes.github.GitHubClient.exchange_oauth_code", return_value=OAuthToken(access_token="tok")), \
         patch("app.api.routes.github.GitHubClient.get_authenticated_user", return_value=mock_user), \
         patch("app.api.routes.github.GitHubClient.list_user_installations", return_value=[]):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/callback?state=s&code=c")

        assert response.status_code == 200
        mock_session.rollback.assert_called_once()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_github_callback_integrity_error_different_developer_race(app):
    """IntegrityError during INSERT, re-query shows different developer → 409."""
    from sqlalchemy.exc import IntegrityError as SAIntegrityError
    from app.services.github.state import GitHubOAuthStateContext
    from app.services.github.client import OAuthToken, GitHubUser
    from app.models.github_account import GitHubAccount

    owner_id = uuid.uuid4()
    requester_id = uuid.uuid4()
    existing_after_race = GitHubAccount(
        developer_id=owner_id,
        github_id=42,
        username="owner",
        installation_id=None,
        disconnected_at=None,
    )

    mock_session = make_db_session([None, existing_after_race])
    mock_session.commit.side_effect = SAIntegrityError("dup", None, None)
    app.dependency_overrides[get_db_session] = lambda: mock_session

    state_context = GitHubOAuthStateContext(
        developer_id=requester_id,
        code_verifier="test_verifier",
        state_id=uuid.uuid4(),
    )
    mock_user = GitHubUser(github_id=42, username="owner")

    with patch("app.api.routes.github.claim_state", return_value=state_context), \
         patch("app.api.routes.github.GitHubClient.exchange_oauth_code", return_value=OAuthToken(access_token="tok")), \
         patch("app.api.routes.github.GitHubClient.get_authenticated_user", return_value=mock_user), \
         patch("app.api.routes.github.GitHubClient.list_user_installations", return_value=[]):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/callback?state=s&code=c")

        assert response.status_code == 409
        mock_session.rollback.assert_called_once()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_github_callback_integrity_error_developer_uniqueness_conflict(app):
    """IntegrityError caused by developer_id uniqueness → 409."""
    from sqlalchemy.exc import IntegrityError as SAIntegrityError
    from app.services.github.state import GitHubOAuthStateContext
    from app.services.github.client import OAuthToken, GitHubUser
    from app.models.github_account import GitHubAccount

    developer_id = uuid.uuid4()
    existing_other_account = GitHubAccount(
        developer_id=developer_id,
        github_id=99,
        username="other_github",
        installation_id=None,
        disconnected_at=None,
    )

    # First call: None (during the first check)
    # Second call: None (during github_id check in the IntegrityError block)
    # Third call: existing_other_account (during developer_id check in the IntegrityError block)
    mock_session = make_db_session([None, None, existing_other_account])
    mock_session.commit.side_effect = SAIntegrityError("dup", None, None)
    app.dependency_overrides[get_db_session] = lambda: mock_session

    state_context = GitHubOAuthStateContext(
        developer_id=developer_id,
        code_verifier="test_verifier",
        state_id=uuid.uuid4(),
    )
    mock_user = GitHubUser(github_id=42, username="owner")

    with patch("app.api.routes.github.claim_state", return_value=state_context), \
         patch("app.api.routes.github.GitHubClient.exchange_oauth_code", return_value=OAuthToken(access_token="tok")), \
         patch("app.api.routes.github.GitHubClient.get_authenticated_user", return_value=mock_user), \
         patch("app.api.routes.github.GitHubClient.list_user_installations", return_value=[]):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/callback?state=s&code=c")

        assert response.status_code == 409
        detail = response.json()["detail"]
        assert "already have a linked GitHub account" in detail
        mock_session.rollback.assert_called_once()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_github_callback_db_failure_returns_500(app):
    """Unexpected DB exception during INSERT returns sanitized 500."""
    from app.services.github.state import GitHubOAuthStateContext
    from app.services.github.client import OAuthToken, GitHubUser

    mock_session = make_db_session(None)
    mock_session.commit.side_effect = Exception("DB connection lost")
    app.dependency_overrides[get_db_session] = lambda: mock_session

    state_context = GitHubOAuthStateContext(
        developer_id=uuid.uuid4(),
        code_verifier="test_verifier",
        state_id=uuid.uuid4(),
    )
    mock_user = GitHubUser(github_id=42, username="user")

    with patch("app.api.routes.github.claim_state", return_value=state_context), \
         patch("app.api.routes.github.GitHubClient.exchange_oauth_code", return_value=OAuthToken(access_token="tok")), \
         patch("app.api.routes.github.GitHubClient.get_authenticated_user", return_value=mock_user), \
         patch("app.api.routes.github.GitHubClient.list_user_installations", return_value=[]):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/callback?state=s&code=c")

        assert response.status_code == 500
        detail = response.json()["detail"]
        # Must not expose internal DB error string
        assert "DB connection lost" not in detail
        assert "connection" not in detail.lower()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_github_callback_response_has_no_sensitive_fields(app):
    """Success response must not contain token, code, verifier, or DB IDs."""
    from app.services.github.state import GitHubOAuthStateContext
    from app.services.github.client import OAuthToken, GitHubUser

    developer_id = uuid.uuid4()
    mock_session = make_db_session(None)
    app.dependency_overrides[get_db_session] = lambda: mock_session

    state_context = GitHubOAuthStateContext(
        developer_id=developer_id,
        code_verifier="secret_pkce_verifier",
        state_id=uuid.uuid4(),
    )
    secret_token = "super_secret_oauth_token"
    mock_user = GitHubUser(github_id=99, username="safeuser")

    with patch("app.api.routes.github.claim_state", return_value=state_context), \
         patch("app.api.routes.github.GitHubClient.exchange_oauth_code", return_value=OAuthToken(access_token=secret_token)), \
         patch("app.api.routes.github.GitHubClient.get_authenticated_user", return_value=mock_user), \
         patch("app.api.routes.github.GitHubClient.list_user_installations", return_value=[]):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/callback?state=s&code=secret_code_value")

        assert response.status_code == 200
        body = str(response.json())

        assert secret_token not in body
        assert "secret_code_value" not in body
        assert "secret_pkce_verifier" not in body
        assert str(developer_id) not in body
        assert "installation_id" not in body

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_github_callback_account_linking_no_installation_id(app):
    """Newly created GitHubAccount must have installation_id=None."""
    from app.services.github.state import GitHubOAuthStateContext
    from app.services.github.client import OAuthToken, GitHubUser, GitHubInstallation
    from app.models.github_account import GitHubAccount

    mock_session = make_db_session(None)
    app.dependency_overrides[get_db_session] = lambda: mock_session

    state_context = GitHubOAuthStateContext(
        developer_id=uuid.uuid4(),
        code_verifier="test_verifier",
        state_id=uuid.uuid4(),
    )
    # Even with multiple installations returned, installation_id must stay NULL
    mock_installations = [
        GitHubInstallation(installation_id=111, account_github_id=10, account_login="org1"),
        GitHubInstallation(installation_id=222, account_github_id=10, account_login="org2"),
    ]
    mock_user = GitHubUser(github_id=10, username="multiinstall")

    with patch("app.api.routes.github.claim_state", return_value=state_context), \
         patch("app.api.routes.github.GitHubClient.exchange_oauth_code", return_value=OAuthToken(access_token="tok")), \
         patch("app.api.routes.github.GitHubClient.get_authenticated_user", return_value=mock_user), \
         patch("app.api.routes.github.GitHubClient.list_user_installations", return_value=mock_installations):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/callback?state=s&code=c")

        assert response.status_code == 200
        added = mock_session.add.call_args[0][0]
        assert isinstance(added, GitHubAccount)
        assert added.installation_id is None

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_github_callback_account_linking_logs_no_secrets(app, caplog):
    """Account linking must not log access token, code, verifier, or state."""
    import logging
    from app.services.github.state import GitHubOAuthStateContext
    from app.services.github.client import OAuthToken, GitHubUser

    caplog.set_level(logging.DEBUG)

    mock_session = make_db_session(None)
    app.dependency_overrides[get_db_session] = lambda: mock_session

    state_context = GitHubOAuthStateContext(
        developer_id=uuid.uuid4(),
        code_verifier="secret_pkce_verifier",
        state_id=uuid.uuid4(),
    )
    secret_token = "super_secret_token"
    mock_user = GitHubUser(github_id=77, username="logtest")

    with patch("app.api.routes.github.claim_state", return_value=state_context), \
         patch("app.api.routes.github.GitHubClient.exchange_oauth_code", return_value=OAuthToken(access_token=secret_token)), \
         patch("app.api.routes.github.GitHubClient.get_authenticated_user", return_value=mock_user), \
         patch("app.api.routes.github.GitHubClient.list_user_installations", return_value=[]):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            await client.get("/github/callback?state=secret_oauth_state&code=secret_auth_code")

        app_logs = " ".join(
            r.message for r in caplog.records if r.name.startswith("app.")
        )
        assert secret_token not in app_logs
        assert "secret_pkce_verifier" not in app_logs
        assert "secret_auth_code" not in app_logs

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_github_callback_user_api_http_error(app):
    """Failure fetching GitHub user profile returns 502 and does not fetch installations."""
    import uuid
    from app.services.github.state import GitHubOAuthStateContext
    from app.services.github.client import OAuthToken
    from app.services.github.exceptions import GitHubHTTPError

    mock_session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    state_context = GitHubOAuthStateContext(
        developer_id=uuid.uuid4(),
        code_verifier="test_verifier",
        state_id=uuid.uuid4(),
    )

    with patch("app.api.routes.github.claim_state", return_value=state_context), \
         patch("app.api.routes.github.GitHubClient.exchange_oauth_code", return_value=OAuthToken(access_token="test_token")), \
         patch("app.api.routes.github.GitHubClient.get_authenticated_user", side_effect=GitHubHTTPError("API failed")), \
         patch("app.api.routes.github.GitHubClient.list_user_installations") as mock_list:

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/callback?state=valid_state&code=valid_code")

        assert response.status_code == 502
        assert "verify GitHub identity" in response.json()["detail"]
        mock_list.assert_not_called()

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_github_callback_user_api_response_error(app):
    """Malformed GitHub user response returns 502."""
    import uuid
    from app.services.github.state import GitHubOAuthStateContext
    from app.services.github.client import OAuthToken
    from app.services.github.exceptions import GitHubResponseError

    mock_session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    state_context = GitHubOAuthStateContext(
        developer_id=uuid.uuid4(),
        code_verifier="test_verifier",
        state_id=uuid.uuid4(),
    )

    with patch("app.api.routes.github.claim_state", return_value=state_context), \
         patch("app.api.routes.github.GitHubClient.exchange_oauth_code", return_value=OAuthToken(access_token="test_token")), \
         patch("app.api.routes.github.GitHubClient.get_authenticated_user", side_effect=GitHubResponseError("Malformed")), \
         patch("app.api.routes.github.GitHubClient.list_user_installations") as mock_list:

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/callback?state=valid_state&code=valid_code")

        assert response.status_code == 502
        assert "malformed identity data" in response.json()["detail"]
        mock_list.assert_not_called()

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_github_callback_installations_api_http_error(app):
    """Failure fetching installations returns 502."""
    import uuid
    from app.services.github.state import GitHubOAuthStateContext
    from app.services.github.client import OAuthToken, GitHubUser
    from app.services.github.exceptions import GitHubHTTPError

    mock_session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    state_context = GitHubOAuthStateContext(
        developer_id=uuid.uuid4(),
        code_verifier="test_verifier",
        state_id=uuid.uuid4(),
    )

    with patch("app.api.routes.github.claim_state", return_value=state_context), \
         patch("app.api.routes.github.GitHubClient.exchange_oauth_code", return_value=OAuthToken(access_token="test_token")), \
         patch("app.api.routes.github.GitHubClient.get_authenticated_user", return_value=GitHubUser(github_id=123, username="testuser")), \
         patch("app.api.routes.github.GitHubClient.list_user_installations", side_effect=GitHubHTTPError("Installations failed")):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/callback?state=valid_state&code=valid_code")

        assert response.status_code == 502
        assert "verify GitHub installations" in response.json()["detail"]

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_github_callback_installations_api_response_error(app):
    """Malformed installations response returns 502."""
    import uuid
    from app.services.github.state import GitHubOAuthStateContext
    from app.services.github.client import OAuthToken, GitHubUser
    from app.services.github.exceptions import GitHubResponseError

    mock_session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    state_context = GitHubOAuthStateContext(
        developer_id=uuid.uuid4(),
        code_verifier="test_verifier",
        state_id=uuid.uuid4(),
    )

    with patch("app.api.routes.github.claim_state", return_value=state_context), \
         patch("app.api.routes.github.GitHubClient.exchange_oauth_code", return_value=OAuthToken(access_token="test_token")), \
         patch("app.api.routes.github.GitHubClient.get_authenticated_user", return_value=GitHubUser(github_id=123, username="testuser")), \
         patch("app.api.routes.github.GitHubClient.list_user_installations", side_effect=GitHubResponseError("Malformed")):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/callback?state=valid_state&code=valid_code")

        assert response.status_code == 502
        assert "malformed installations data" in response.json()["detail"]

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_github_callback_oauth_error(app):
    """An error from GitHub stops the flow."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/github/callback?state=xyz&error=access_denied")

    assert response.status_code == 400
    assert "GitHub OAuth authorization failed" in response.json()["detail"]

@pytest.mark.asyncio
async def test_github_callback_missing_code(app):
    """Missing code with no error stops the flow."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/github/callback?state=xyz")

    assert response.status_code == 400
    assert "code missing" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_github_callback_unknown_state(app):
    """Unknown state is safely rejected."""
    from app.services.github.state import GitHubStateNotFoundError

    mock_session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    with patch("app.api.routes.github.claim_state", side_effect=GitHubStateNotFoundError("Invalid OAuth state.")), \
         patch("app.api.routes.github.GitHubClient.exchange_oauth_code") as mock_exchange:

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/callback?state=unknown&code=xyz")

        assert response.status_code == 400
        assert "Invalid or expired OAuth state" in response.json()["detail"]
        mock_exchange.assert_not_called()

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_github_callback_expired_or_replayed_state(app):
    """Expired or replayed state is safely rejected."""
    from app.services.github.state import GitHubStateExpiredError

    mock_session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    with patch("app.api.routes.github.claim_state", side_effect=GitHubStateExpiredError("OAuth state is expired or already used.")), \
         patch("app.api.routes.github.GitHubClient.exchange_oauth_code") as mock_exchange:

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/callback?state=expired&code=xyz")

        assert response.status_code == 400
        assert "Invalid or expired OAuth state" in response.json()["detail"]
        mock_exchange.assert_not_called()

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_github_callback_exchange_failure(app, caplog):
    """A failure during token exchange is sanitized and logged safely."""
    import uuid
    from app.services.github.state import GitHubOAuthStateContext
    from app.services.github.exceptions import GitHubHTTPError
    import logging

    caplog.set_level(logging.DEBUG)

    mock_session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    state_context = GitHubOAuthStateContext(
        developer_id=uuid.uuid4(),
        code_verifier="secret_verifier_value",
        state_id=uuid.uuid4(),
    )

    with patch("app.api.routes.github.claim_state", return_value=state_context), \
         patch("app.api.routes.github.GitHubClient.exchange_oauth_code", side_effect=GitHubHTTPError("Exchange failed")):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/github/callback?state=xyz&code=secret_code_value")

        assert response.status_code == 502
        assert "Failed to exchange authorization code" in response.json()["detail"]

    # Check app logs for secret exposure (httpx request logs the URL, which we ignore)
    app_logs = [record.message for record in caplog.records if record.name.startswith("app.")]
    app_logs_text = " ".join(app_logs)
    assert "secret_code_value" not in app_logs_text
    assert "secret_verifier_value" not in app_logs_text

    app.dependency_overrides.clear()
@pytest.mark.asyncio
async def test_pkce_invariant_same_verifier_used(app):
    """
    Verify that the code_challenge in the URL matches the S256 hash of the
    plaintext verifier that gets encrypted and stored in the database.
    """
    import base64
    import hashlib
    from app.core.crypto import decrypt_pkce_verifier

    developer_id = uuid.uuid4()
    mock_dev = Developer(id=developer_id, auth_user_id=uuid.uuid4())
    app.dependency_overrides[get_current_developer] = lambda: mock_dev

    mock_session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/github/install")

    assert response.status_code == 200
    url = response.json()["install_url"]

    from urllib.parse import urlparse, parse_qs
    parsed_url = urlparse(url)
    qs = parse_qs(parsed_url.query)

    assert "code_challenge" in qs
    code_challenge = qs["code_challenge"][0]

    mock_session.add.assert_called_once()
    added_row = mock_session.add.call_args[0][0]
    encrypted_verifier = added_row.code_verifier_enc

    plaintext_verifier = decrypt_pkce_verifier(encrypted_verifier)

    digest = hashlib.sha256(plaintext_verifier.encode("utf-8")).digest()
    expected_challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")

    assert code_challenge == expected_challenge
    app.dependency_overrides.clear()
