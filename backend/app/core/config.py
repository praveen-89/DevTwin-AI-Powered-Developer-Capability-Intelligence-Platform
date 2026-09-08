"""
DevTwin Backend — Application Configuration

Loads all configuration from environment variables.
Never stores secrets in source code.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All required fields will raise a ValidationError on startup
    if they are not provided — this is intentional and safe.
    """

    # ── Application ────────────────────────────────────────────────
    APP_NAME: str = "DevTwin API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # ── Database (Supabase PostgreSQL) ─────────────────────────────
    # Format: postgresql+asyncpg://user:password@host:port/database
    DATABASE_URL: str

    # ── Supabase ───────────────────────────────────────────────────
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # ── Security ───────────────────────────────────────────────────
    # Used for internal token signing if needed.  Keep secret.
    SECRET_KEY: str

    # ── CORS ───────────────────────────────────────────────────────
    # Comma-separated list of allowed origins, e.g. http://localhost:3000
    CORS_ORIGINS: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached singleton Settings instance.
    Raises pydantic.ValidationError if required env vars are missing.
    """
    return Settings()  # type: ignore[call-arg]
