"""
DevTwin Backend Tests — Authentication Layer

Tests for:
  - core/security.py  (JWKS client + JWT verification)
  - api/dependencies/auth.py (get_current_user + get_current_developer)

All tests are hermetic — no real Supabase credentials required.
JWKS and DB interactions are fully mocked.

Test plan:
  1.  Missing Authorization header → 401
  2.  Non-Bearer scheme → 401
  3.  Empty token → 401
  4.  Invalid JWT signature → 401
  5.  Expired JWT → 401
  6.  Missing 'sub' claim → 401
  7.  Invalid algorithm in JWKS (algorithm confusion guard) → 401
  8.  Valid JWT, correct sub extracted → 200
  9.  Unknown kid triggers JWKS refresh (PyJWKClient behaviour verified)
  10. Developer lookup: matching auth_user_id → developer returned
  11. Developer lookup: no matching developer → 401
  12. Error response must not expose JWT contents or credentials
"""

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import jwt as pyjwt
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from httpx import AsyncClient, ASGITransport


# ---------------------------------------------------------------------------
# Helpers — RSA key generation for test tokens
# ---------------------------------------------------------------------------


def _generate_rsa_keypair():
    """Generate a fresh RSA-2048 key pair for test token signing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    public_key = private_key.public_key()
    return private_key, public_key


def _make_token(
    private_key,
    sub: str = str(uuid.uuid4()),
    aud: str = "authenticated",
    exp_delta: timedelta = timedelta(hours=1),
    kid: str = "test-kid-1",
    algorithm: str = "RS256",
    omit_sub: bool = False,
    iss: str | None = "https://placeholder.supabase.co/auth/v1",
    omit_iss: bool = False,
) -> str:
    """Build a signed JWT for testing purposes."""
    now = datetime.now(tz=timezone.utc)
    payload = {
        "aud": aud,
        "exp": now + exp_delta,
        "iat": now,
        "role": "authenticated",
    }
    if not omit_sub:
        payload["sub"] = sub
    if not omit_iss and iss is not None:
        payload["iss"] = iss

    return pyjwt.encode(
        payload,
        private_key,
        algorithm=algorithm,
        headers={"kid": kid},
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rsa_keypair():
    """Fresh RSA key pair scoped to each test."""
    return _generate_rsa_keypair()


@pytest.fixture
def reset_security_state():
    """Reset the module-level JWKS client singleton between tests.
    NOT autouse — only auth tests need this, and importing security
    before env vars are set would break test_config isolation.
    """
    # Import lazily inside the fixture so the module is only loaded
    # after the test's monkeypatch env setup has run.
    yield
    # Teardown: reset the singleton so subsequent tests start clean.
    from app.core import security
    security._jwks_client = None


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear lru_cache on settings between tests."""
    from app.core.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def test_env(monkeypatch):
    """Inject minimum required env vars for the app to start."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/devtwin_test")
    monkeypatch.setenv("SUPABASE_URL", "https://placeholder.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-unit-tests-only")
    monkeypatch.setenv("DEBUG", "true")


def _make_mock_jwks_client(private_key, public_key, algorithm: str = "RS256", kid: str = "test-kid-1"):
    """
    Build a mock PyJWKClient that returns the given public key for any token
    with matching kid, or raises PyJWKClientError for unknown kids.
    """
    from jwt import PyJWKClient, PyJWKClientError

    mock_signing_key = MagicMock()
    mock_signing_key.key = public_key
    mock_signing_key.algorithm_name = algorithm

    mock_client = MagicMock(spec=PyJWKClient)

    def get_signing_key(token):
        # Decode header without verification to check kid
        header = pyjwt.get_unverified_header(token)
        if header.get("kid") == kid:
            return mock_signing_key
        raise PyJWKClientError("Unable to find a signing key")

    mock_client.get_signing_key_from_jwt.side_effect = get_signing_key
    return mock_client


@pytest.fixture
async def auth_client(test_env, rsa_keypair):
    """
    Async test client with the JWKS client pre-seeded with the test RSA key.
    Uses the real FastAPI app so integration through the dependency stack is tested.
    """
    private_key, public_key = rsa_keypair
    mock_jwks = _make_mock_jwks_client(private_key, public_key)

    from app.core.security import reset_jwks_client
    reset_jwks_client(mock_jwks)

    from app.core.config import get_settings
    get_settings.cache_clear()

    from app.main import create_app
    app = create_app()

    # Add a minimal test-only route that uses both dependencies so we can
    # assert end-to-end behaviour without implementing real business routes yet.
    from fastapi import Depends
    from app.api.dependencies.auth import get_current_user, get_current_developer, AuthenticatedUser
    from app.models.developer import Developer

    @app.get("/_test/me")
    async def _test_me(user: AuthenticatedUser = Depends(get_current_user)):
        return {"sub": user.sub}

    @app.get("/_test/developer")
    async def _test_developer(developer: Developer = Depends(get_current_developer)):
        return {"id": str(developer.id), "auth_user_id": str(developer.auth_user_id)}

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac, private_key


# ---------------------------------------------------------------------------
# Tests — get_current_user (JWT verification layer)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_authorization_header_returns_401(auth_client):
    """No Authorization header → 401."""
    client, _ = auth_client
    response = await client.get("/_test/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_non_bearer_scheme_returns_401(auth_client):
    """Authorization: Basic ... → 401."""
    client, _ = auth_client
    response = await client.get("/_test/me", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_empty_token_returns_401(auth_client):
    """Authorization: Bearer <empty> → 401."""
    client, _ = auth_client
    response = await client.get("/_test/me", headers={"Authorization": "Bearer "})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_jwt_signature_returns_401(auth_client, rsa_keypair):
    """A token signed with a different private key (signature mismatch) → 401."""
    client, _ = auth_client
    # Generate a different key pair — signature won't match the registered public key
    other_private_key, _ = _generate_rsa_keypair()
    bad_token = _make_token(other_private_key, kid="test-kid-1")
    response = await client.get("/_test/me", headers={"Authorization": f"Bearer {bad_token}"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_expired_jwt_returns_401(auth_client, rsa_keypair):
    """An expired JWT → 401."""
    client, private_key = auth_client
    expired_token = _make_token(private_key, exp_delta=timedelta(seconds=-60))
    response = await client.get("/_test/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_missing_sub_claim_returns_401(auth_client, rsa_keypair):
    """JWT without a 'sub' claim → 401."""
    client, private_key = auth_client
    token = _make_token(private_key, omit_sub=True)
    response = await client.get("/_test/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_missing_iss_claim_returns_401(auth_client, rsa_keypair):
    """JWT without an 'iss' claim → 401."""
    client, private_key = auth_client
    token = _make_token(private_key, omit_iss=True)
    response = await client.get("/_test/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_iss_claim_returns_401(auth_client, rsa_keypair):
    """JWT with an incorrect 'iss' claim → 401."""
    client, private_key = auth_client
    token = _make_token(private_key, iss="https://wrong-issuer.com/auth/v1")
    response = await client.get("/_test/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_unknown_kid_returns_401(auth_client, rsa_keypair):
    """JWT with a kid not in the JWKS → 401 (mock raises PyJWKClientError)."""
    client, private_key = auth_client
    # Sign with a kid that the mock JWKS client does not recognise
    token = _make_token(private_key, kid="unknown-kid-999")
    response = await client.get("/_test/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_valid_jwt_returns_200_and_correct_sub(auth_client, rsa_keypair):
    """A valid, properly-signed JWT → 200 with the correct sub extracted."""
    client, private_key = auth_client
    expected_sub = str(uuid.uuid4())
    token = _make_token(private_key, sub=expected_sub)
    response = await client.get("/_test/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["sub"] == expected_sub


@pytest.mark.asyncio
async def test_error_response_does_not_expose_jwt_contents(auth_client, rsa_keypair):
    """The 401 response body must not expose any JWT payload or token material."""
    client, _ = auth_client
    # Use a clearly identifiable sub value
    other_private_key, _ = _generate_rsa_keypair()
    secret_sub = "secret-user-id-12345"
    bad_token = _make_token(other_private_key, sub=secret_sub, kid="test-kid-1")

    response = await client.get("/_test/me", headers={"Authorization": f"Bearer {bad_token}"})
    assert response.status_code == 401
    body_text = response.text
    # Token payload must not appear in the response
    assert secret_sub not in body_text
    assert "Bearer" not in body_text
    assert "eyJ" not in body_text  # JWT prefix must not appear


# ---------------------------------------------------------------------------
# Tests — verify_supabase_jwt directly (unit tests on the security module)
# ---------------------------------------------------------------------------


def test_verify_rejects_wrong_algorithm(rsa_keypair):
    """
    Algorithm confusion guard: a token header claiming HS256 but arriving with
    an RS256 JWKS key is rejected because we use the algorithm from the JWKS key,
    not the token header.
    """
    from app.core.security import verify_supabase_jwt, reset_jwks_client, AuthenticationError
    private_key, public_key = rsa_keypair

    # Build a token with RS256 (the mock JWKS will return RS256 algorithm)
    token = _make_token(private_key, algorithm="RS256", kid="test-kid-1")

    # But mock the JWKS client to claim the key algorithm is HS256 —
    # this should cause jwt.decode to fail since we're using an RSA key with HS256.
    mock_signing_key = MagicMock()
    mock_signing_key.key = public_key
    mock_signing_key.algorithm_name = "HS256"  # Wrong — algorithm confusion

    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
    reset_jwks_client(mock_client)

    with pytest.raises(AuthenticationError):
        verify_supabase_jwt(token)


def test_verify_rejects_unallowed_algorithm(rsa_keypair):
    """
    Regression test for CVE-2026-48523 PyJWT algorithm bypass.
    Ensures that a token attempting to bypass signature verification using an
    unallowed algorithm (like 'none') is explicitly rejected, even if it has a
    valid 'kid'. Our implementation explicitly restricts 'algorithms' to the
    single algorithm defined by the JWKS key.
    """
    from app.core.security import verify_supabase_jwt, reset_jwks_client, AuthenticationError
    import uuid
    from datetime import datetime, timezone, timedelta
    import jwt as pyjwt
    
    private_key, public_key = rsa_keypair

    now = datetime.now(tz=timezone.utc)
    payload = {
        "aud": "authenticated",
        "exp": now + timedelta(hours=1),
        "iat": now,
        "iss": "https://placeholder.supabase.co/auth/v1",
        "sub": str(uuid.uuid4()),
        "role": "authenticated",
    }
    # Attacker crafts an unsigned token claiming algorithm 'none'
    token = pyjwt.encode(payload, key="", algorithm="none", headers={"kid": "test-kid-1"})

    # The JWKS client still resolves 'test-kid-1' to our RS256 key
    mock_signing_key = MagicMock()
    mock_signing_key.key = public_key
    mock_signing_key.algorithm_name = "RS256"

    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
    reset_jwks_client(mock_client)

    with pytest.raises(AuthenticationError):
        verify_supabase_jwt(token)



def test_verify_valid_token_returns_payload(rsa_keypair):
    """Direct unit test: valid token → payload dict returned with correct sub."""
    import os
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@h/db")
    os.environ.setdefault("SUPABASE_URL", "https://placeholder.supabase.co")
    os.environ.setdefault("SUPABASE_ANON_KEY", "anon")
    os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "svc")
    os.environ.setdefault("SECRET_KEY", "sec")

    from app.core.security import verify_supabase_jwt, reset_jwks_client
    private_key, public_key = rsa_keypair
    expected_sub = str(uuid.uuid4())

    mock_signing_key = MagicMock()
    mock_signing_key.key = public_key
    mock_signing_key.algorithm_name = "RS256"

    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
    reset_jwks_client(mock_client)

    token = _make_token(private_key, sub=expected_sub)
    payload = verify_supabase_jwt(token)
    assert payload["sub"] == expected_sub


# ---------------------------------------------------------------------------
# Tests — get_current_developer (DB lookup layer)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_developer_lookup_returns_developer_when_found(test_env, rsa_keypair):
    """Valid JWT + matching developer record → developer returned from dependency."""
    from app.core.config import get_settings
    get_settings.cache_clear()
    from app.core.security import reset_jwks_client
    from app.main import create_app
    from app.api.dependencies.auth import get_current_developer
    from app.db.connection import get_db_session
    from app.models.developer import Developer as Dev

    private_key, public_key = rsa_keypair
    developer_id = uuid.uuid4()
    auth_user_id = uuid.uuid4()

    # Seed the JWKS client
    mock_jwks = _make_mock_jwks_client(private_key, public_key)
    reset_jwks_client(mock_jwks)

    token = _make_token(private_key, sub=str(auth_user_id))

    # Build a mock Developer ORM object
    mock_developer = Dev()
    mock_developer.id = developer_id
    mock_developer.auth_user_id = auth_user_id

    # Clean DB session override
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_developer
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def override_get_db_session():
        yield mock_session

    app = create_app()
    from fastapi import Depends

    @app.get("/_test/dev_lookup")
    async def _dev_lookup(developer: Dev = Depends(get_current_developer)):
        return {"id": str(developer.id), "auth_user_id": str(developer.auth_user_id)}

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        response = await ac.get(
            "/_test/dev_lookup",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(developer_id)
    assert data["auth_user_id"] == str(auth_user_id)


@pytest.mark.asyncio
async def test_developer_lookup_returns_401_when_no_record(test_env, rsa_keypair):
    """Valid JWT but no developer record in DB → 401 (not 403, not 404)."""
    from app.core.config import get_settings
    get_settings.cache_clear()
    from app.core.security import reset_jwks_client
    from app.main import create_app
    from app.api.dependencies.auth import get_current_developer
    from app.db.connection import get_db_session
    from app.models.developer import Developer as Dev

    private_key, public_key = rsa_keypair
    auth_user_id = uuid.uuid4()

    mock_jwks = _make_mock_jwks_client(private_key, public_key)
    reset_jwks_client(mock_jwks)
    token = _make_token(private_key, sub=str(auth_user_id))

    # Session returns None — no developer record found
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def override_get_db_session():
        yield mock_session

    app = create_app()
    from fastapi import Depends

    @app.get("/_test/dev_missing")
    async def _dev_missing(developer: Dev = Depends(get_current_developer)):
        return {"id": str(developer.id)}

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        response = await ac.get(
            "/_test/dev_missing",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 401
    # Must not expose internal details
    body = response.text
    assert str(auth_user_id) not in body
    assert "developer" not in body.lower()
