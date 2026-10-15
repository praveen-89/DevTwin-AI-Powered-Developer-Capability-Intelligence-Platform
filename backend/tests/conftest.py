"""
DevTwin Backend Tests — Root Test Configuration & Bootstrap

Establishes deterministic placeholder environment variables before test modules
import app.main during pytest collection. Guarantees hermetic test execution
without requiring a .env file or real secrets.
"""

import os
import pytest

# Minimal valid placeholder environment configuration for unit and integration testing.
TEST_ENV_DEFAULTS = {
    "DATABASE_URL": "postgresql+asyncpg://u:p@localhost/db",
    "SUPABASE_URL": "https://placeholder.supabase.co",
    "SUPABASE_ANON_KEY": "anon",
    "SUPABASE_SERVICE_ROLE_KEY": "service",
    "SECRET_KEY": "secret",
    "GITHUB_APP_ID": "123",
    "GITHUB_APP_SLUG": "app",
    "GITHUB_CLIENT_ID": "client",
    "GITHUB_CLIENT_SECRET": "secret",
    "GITHUB_PRIVATE_KEY": "pem",
    "GITHUB_REDIRECT_URL": "http://localhost/cb",
    "GITHUB_STATE_ENCRYPTION_KEY": "N2F0d1VNb2h3Nnl4S3hZYmF0bzh1amV6dVpZcDJ2bXg=",
    "GITHUB_STATE_TTL_SECONDS": "600",
}

# Unconditionally set before any test collection occurs to prevent host-environment leakage.
for key, value in TEST_ENV_DEFAULTS.items():
    os.environ[key] = value


@pytest.fixture(autouse=True)
def reset_settings_cache():
    """Ensure get_settings lru_cache does not leak settings between test cases."""
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
