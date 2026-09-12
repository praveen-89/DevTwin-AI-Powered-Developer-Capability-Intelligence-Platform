"""
DevTwin Backend Tests — Configuration Validation

Verifies that the Settings class raises validation errors when
required environment variables are absent.
"""

import pytest
from pydantic import ValidationError


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Ensure lru_cache is cleared before and after each test."""
    from app.core.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_settings_fails_without_database_url(monkeypatch):
    """Settings must raise ValidationError if DATABASE_URL is missing.

    _env_file=None is passed explicitly so that pydantic-settings does NOT
    fall back to loading backend/.env — the test must be hermetic and must
    not depend on the presence or contents of any .env file on disk.
    """
    monkeypatch.setenv("SUPABASE_URL", "https://placeholder.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service")
    monkeypatch.setenv("SECRET_KEY", "secret")
    # Deliberately omit DATABASE_URL — also remove it if it leaked from another test
    monkeypatch.delenv("DATABASE_URL", raising=False)

    from app.core.config import Settings
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)  # type: ignore[call-arg]  # disable .env loading

    errors = exc_info.value.errors()
    field_names = [e["loc"][0] for e in errors]
    assert "DATABASE_URL" in field_names


def test_settings_loads_correctly(monkeypatch):
    """Settings loads all values from environment variables correctly."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-key")
    monkeypatch.setenv("SECRET_KEY", "my-secret")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001")

    from app.core.config import Settings
    settings = Settings()  # type: ignore[call-arg]

    assert settings.DATABASE_URL == "postgresql+asyncpg://u:p@localhost/db"
    assert settings.SUPABASE_URL == "https://test.supabase.co"
    assert settings.DEBUG is False
    assert settings.cors_origins_list == ["http://localhost:3000", "http://localhost:3001"]


def _set_base_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-key")
    monkeypatch.setenv("SECRET_KEY", "secret")
    # Base GitHub config
    monkeypatch.setenv("GITHUB_APP_ID", "123")
    monkeypatch.setenv("GITHUB_APP_SLUG", "devtwin-app")
    monkeypatch.setenv("GITHUB_CLIENT_ID", "client123")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "secret123")
    monkeypatch.setenv("GITHUB_PRIVATE_KEY", "pem-key")
    monkeypatch.setenv("GITHUB_REDIRECT_URL", "http://localhost:8000/github/callback")
    monkeypatch.setenv("GITHUB_STATE_ENCRYPTION_KEY", "N2F0d1VNb2h3Nnl4S3hZYmF0bzh1amV6dVpZcDJ2bXg=")


def test_cors_origins_list_single_origin(monkeypatch):
    """cors_origins_list correctly parses a single origin."""
    _set_base_env(monkeypatch)
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")

    from app.core.config import Settings
    settings = Settings()  # type: ignore[call-arg]
    assert settings.cors_origins_list == ["http://localhost:3000"]


def test_github_config_loads_defaults(monkeypatch):
    """GitHub configuration loads successfully with correct defaults."""
    _set_base_env(monkeypatch)
    from app.core.config import Settings
    settings = Settings()  # type: ignore[call-arg]
    assert settings.GITHUB_APP_ID == 123
    assert settings.GITHUB_APP_SLUG == "devtwin-app"
    assert settings.GITHUB_STATE_TTL_SECONDS == 600
    assert settings.GITHUB_API_BASE_URL == "https://api.github.com"


def test_github_config_fails_missing_required(monkeypatch):
    """Missing required GitHub configuration fails."""
    _set_base_env(monkeypatch)
    monkeypatch.delenv("GITHUB_CLIENT_ID", raising=False)

    from app.core.config import Settings
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)  # type: ignore[call-arg]
    assert "GITHUB_CLIENT_ID" in [e["loc"][0] for e in exc_info.value.errors()]


def test_github_config_fails_invalid_fernet_key(monkeypatch):
    """Invalid Fernet key fails."""
    _set_base_env(monkeypatch)
    monkeypatch.setenv("GITHUB_STATE_ENCRYPTION_KEY", "invalid-key")

    from app.core.config import Settings
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)  # type: ignore[call-arg]
    assert "GITHUB_STATE_ENCRYPTION_KEY" in [e["loc"][0] for e in exc_info.value.errors()]


def test_github_config_fails_invalid_app_id(monkeypatch):
    """Invalid APP_ID fails."""
    _set_base_env(monkeypatch)
    monkeypatch.setenv("GITHUB_APP_ID", "-5")

    from app.core.config import Settings
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)  # type: ignore[call-arg]
    assert "GITHUB_APP_ID" in [e["loc"][0] for e in exc_info.value.errors()]


def test_github_config_fails_invalid_ttl(monkeypatch):
    """Invalid TTL fails."""
    _set_base_env(monkeypatch)
    monkeypatch.setenv("GITHUB_STATE_TTL_SECONDS", "0")

    from app.core.config import Settings
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)  # type: ignore[call-arg]
    assert "GITHUB_STATE_TTL_SECONDS" in [e["loc"][0] for e in exc_info.value.errors()]


def test_secrets_not_exposed_in_repr(monkeypatch):
    """Secrets must not be exposed in __repr__ or __str__."""
    _set_base_env(monkeypatch)
    from app.core.config import Settings
    settings = Settings()  # type: ignore[call-arg]
    rep = repr(settings)
    s = str(settings)
    assert "secret123" not in rep
    assert "secret123" not in s
    assert "N2F0d1VNb2h3Nnl4S3hZYmF0bzh1amV6dVpZcDJ2bXg=" not in rep
    assert "N2F0d1VNb2h3Nnl4S3hZYmF0bzh1amV6dVpZcDJ2bXg=" not in s
    assert "pem-key" not in rep
    assert "pem-key" not in s
