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
async def test_callback_not_implemented(app):
    """Callback route should return 501 until implemented."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/github/callback?state=xyz&installation_id=123")
    assert response.status_code == 501
    assert "Callback not implemented yet" in response.json()["detail"]
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
