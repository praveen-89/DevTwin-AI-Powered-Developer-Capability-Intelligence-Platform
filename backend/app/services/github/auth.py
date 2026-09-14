"""
DevTwin Backend — GitHub Authentication
"""
import time
import logging
import jwt
from app.core.config import get_settings
from .exceptions import GitHubConfigurationError

logger = logging.getLogger(__name__)


def generate_app_jwt() -> str:
    """
    Generates a short-lived GitHub App JWT for server-to-server authentication.
    
    The JWT is signed with RS256 using the configured GITHUB_PRIVATE_KEY.
    NEVER log or persist the resulting token.
    """
    settings = get_settings()
    
    app_id = settings.GITHUB_APP_ID
    private_key = settings.GITHUB_PRIVATE_KEY
    
    if not app_id or not private_key:
        logger.error("Missing GitHub App ID or Private Key configuration.")
        raise GitHubConfigurationError("GitHub App ID and Private Key must be configured.")
    
    # Handle escaped newlines from environment variables
    if isinstance(private_key, str):
        private_key = private_key.replace("\\n", "\n")
    
    now = int(time.time())
    # Account for 60s clock skew
    iat = now - 60
    # Expire in 10 minutes max (GitHub allows max 10 minutes)
    exp = now + 600
    
    payload = {
        "iat": iat,
        "exp": exp,
        "iss": str(app_id)
    }
    
    try:
        encoded_jwt = jwt.encode(payload, private_key, algorithm="RS256")
        return encoded_jwt
    except Exception as e:
        logger.error("Failed to generate GitHub App JWT.")
        raise GitHubConfigurationError("Failed to sign GitHub App JWT. Check private key format.") from e
