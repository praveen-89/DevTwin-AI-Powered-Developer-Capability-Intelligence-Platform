"""
DevTwin Backend — Application Configuration

Loads all configuration from environment variables.
Never stores secrets in source code.
"""

from functools import lru_cache
from cryptography.fernet import Fernet
from pydantic import Field, field_validator
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

    # ── GitHub App Integration ─────────────────────────────────────
    GITHUB_APP_ID: int = Field(gt=0)
    GITHUB_APP_SLUG: str = Field(min_length=1)
    GITHUB_CLIENT_ID: str = Field(min_length=1)
    GITHUB_CLIENT_SECRET: str
    GITHUB_PRIVATE_KEY: str
    GITHUB_REDIRECT_URL: str  # The backend OAuth callback URL
    GITHUB_STATE_ENCRYPTION_KEY: str
    GITHUB_STATE_TTL_SECONDS: int = Field(default=600, gt=0)
    GITHUB_API_BASE_URL: str = "https://api.github.com"

    # ── CORS ───────────────────────────────────────────────────────
    # Comma-separated list of allowed origins, e.g. http://localhost:3000
    CORS_ORIGINS: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @field_validator("GITHUB_STATE_ENCRYPTION_KEY")
    @classmethod
    def validate_fernet_key(cls, v: str) -> str:
        try:
            Fernet(v.encode("utf-8"))
        except Exception:
            raise ValueError("GITHUB_STATE_ENCRYPTION_KEY must be a valid Fernet key.")
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    def __repr__(self) -> str:
        """Prevent secrets from leaking in repr."""
        return f"<Settings APP_NAME={self.APP_NAME}>"

    def __str__(self) -> str:
        """Prevent secrets from leaking in string representation."""
        return self.__repr__()


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached singleton Settings instance.
    Raises pydantic.ValidationError if required env vars are missing.
    """
    return Settings()  # type: ignore[call-arg]
