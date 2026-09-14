"""
DevTwin Backend Tests — GitHub Authentication Service
"""

import pytest
import jwt
from app.services.github.auth import generate_app_jwt
from app.services.github.exceptions import GitHubConfigurationError

# Generate a small RSA private key for testing using cryptography to avoid creating static keys
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import logging

def _generate_test_rsa_key():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    return pem.decode("utf-8")

TEST_PRIVATE_KEY = _generate_test_rsa_key()


@pytest.fixture(autouse=True)
def setup_github_auth_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service")
    monkeypatch.setenv("SECRET_KEY", "secret")
    
    monkeypatch.setenv("GITHUB_APP_ID", "12345")
    monkeypatch.setenv("GITHUB_APP_SLUG", "app")
    monkeypatch.setenv("GITHUB_CLIENT_ID", "client")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "TEST_CLIENT_SECRET")
    monkeypatch.setenv("GITHUB_PRIVATE_KEY", TEST_PRIVATE_KEY)
    monkeypatch.setenv("GITHUB_REDIRECT_URL", "http://localhost/cb")
    monkeypatch.setenv("GITHUB_STATE_ENCRYPTION_KEY", "N2F0d1VNb2h3Nnl4S3hZYmF0bzh1amV6dVpZcDJ2bXg=")
    
    from app.core.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_generate_app_jwt_success():
    """Generates a valid RS256 JWT with correct claims."""
    token = generate_app_jwt()
    assert token
    
    # We can decode without verifying signature to check claims
    unverified = jwt.decode(token, options={"verify_signature": False})
    
    assert unverified["iss"] == "12345"
    assert "iat" in unverified
    assert "exp" in unverified
    
    # Check max lifetime
    lifetime = unverified["exp"] - unverified["iat"]
    assert lifetime == 660  # 600s + 60s skew


def test_generate_app_jwt_fails_missing_key(monkeypatch):
    """Missing private key fails securely."""
    monkeypatch.delenv("GITHUB_PRIVATE_KEY", raising=False)
    
    from app.core.config import get_settings
    get_settings.cache_clear()
    
    # Pydantic will raise a ValidationError before we even get to the function
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        generate_app_jwt()


def test_generate_app_jwt_fails_invalid_key(monkeypatch):
    """Invalid private key format fails securely."""
    monkeypatch.setenv("GITHUB_PRIVATE_KEY", "INVALID_PEM_DATA")
    
    from app.core.config import get_settings
    get_settings.cache_clear()
    
    with pytest.raises(GitHubConfigurationError):
        generate_app_jwt()


def test_jwt_generation_does_not_log_private_key(caplog):
    """Ensure private key is never logged."""
    caplog.set_level(logging.DEBUG)
    generate_app_jwt()
    
    for record in caplog.records:
        assert TEST_PRIVATE_KEY not in record.message
