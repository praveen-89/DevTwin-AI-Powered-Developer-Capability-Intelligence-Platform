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
    # Deliberately omit DATABASE_URL

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


def test_cors_origins_list_single_origin(monkeypatch):
    """cors_origins_list correctly parses a single origin."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-key")
    monkeypatch.setenv("SECRET_KEY", "secret")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")

    from app.core.config import Settings
    settings = Settings()  # type: ignore[call-arg]
    assert settings.cors_origins_list == ["http://localhost:3000"]
