"""
DevTwin Backend Tests — Health Endpoint

Tests the /health and /health/database endpoints without requiring
a live Supabase connection. Database check is mocked to keep tests
hermetic and runnable in CI without credentials.
"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def test_env(monkeypatch):
    """
    Inject the minimum required environment variables so the app
    can be imported and configured without a real .env file.
    This ensures tests never depend on developer-local secrets.
    """
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/devtwin_test")
    monkeypatch.setenv("SUPABASE_URL", "https://placeholder.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-unit-tests-only")
    monkeypatch.setenv("DEBUG", "true")


@pytest.fixture
async def client(test_env):
    """
    Create an async test client for the FastAPI app.
    The app is (re-)created after env vars are injected.
    """
    # Clear the lru_cache so settings are re-evaluated with test env vars.
    from app.core.config import get_settings
    get_settings.cache_clear()

    from app.main import create_app
    application = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://testserver",
    ) as ac:
        yield ac


# ── /health ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health_returns_200(client):
    """The liveness endpoint must always return HTTP 200."""
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_structure(client):
    """The liveness response must contain the required fields."""
    response = await client.get("/health")
    body = response.json()

    assert "status" in body
    assert body["status"] == "ok"
    assert "app" in body
    assert "version" in body
    assert "timestamp" in body


@pytest.mark.asyncio
async def test_health_app_name(client):
    """App name in health response must match configuration."""
    response = await client.get("/health")
    body = response.json()
    assert body["app"] == "DevTwin API"


# ── /health/database ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_database_health_when_reachable(client):
    """When DB is reachable, /health/database returns 200 with 'ok' status."""
    with patch(
        "app.api.routes.health.check_database_connectivity",
        new_callable=AsyncMock,
        return_value=True,
    ):
        response = await client.get("/health/database")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "reachable"


@pytest.mark.asyncio
async def test_database_health_when_unreachable(client):
    """When DB is unreachable, /health/database returns 503 with 'degraded' status."""
    with patch(
        "app.api.routes.health.check_database_connectivity",
        new_callable=AsyncMock,
        return_value=False,
    ):
        response = await client.get("/health/database")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["database"] == "unreachable"


@pytest.mark.asyncio
async def test_database_health_no_credentials_in_response(client):
    """
    The health response must NEVER contain connection strings, passwords, or
    any sensitive configuration values — even in the error case.
    """
    with patch(
        "app.api.routes.health.check_database_connectivity",
        new_callable=AsyncMock,
        return_value=False,
    ):
        response = await client.get("/health/database")
    body_text = response.text
    assert "postgresql" not in body_text
    assert "password" not in body_text
    assert "secret" not in body_text.lower()
