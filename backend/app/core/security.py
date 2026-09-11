"""
DevTwin Backend — JWKS Client & JWT Verification

Implements asymmetric Supabase JWT verification using the project's JWKS endpoint.

Design principles:
  - Derives the JWKS endpoint from SUPABASE_URL (no hard-coded URLs).
  - Caches the JWKS in-process; refreshes on unknown `kid`.
  - Never logs raw tokens, Authorization headers, or key material.
  - Does NOT implement algorithm negotiation from the JWT header;
    only HS256/RS256 types found in the JWKS are trusted.
  - Algorithm confusion is prevented by extracting algorithm from
    the matched JWKS key's `alg` field rather than the JWT header.

References: ADR-014, docs/05_SYSTEM_ARCHITECTURE.md
"""

import logging
import time
from typing import Any

import httpx
import jwt
from jwt import PyJWKClient, PyJWKClientError, ExpiredSignatureError, InvalidTokenError

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# JWKS client — module-level singleton
# httpx is already in requirements. PyJWKClient from PyJWT handles caching
# and key rotation (re-fetches on unknown kid) with a configurable TTL.
# ---------------------------------------------------------------------------

_jwks_client: PyJWKClient | None = None

# Cache lifetime for successful JWKS responses (5 minutes).
_JWKS_CACHE_TTL_SECONDS = 300

# Network timeout for JWKS endpoint requests.
_JWKS_TIMEOUT_SECONDS = 5


def _get_jwks_client() -> PyJWKClient:
    """
    Return the module-level JWKS client, creating it on first call.
    PyJWKClient from PyJWT handles:
      - Fetching JWKS from the endpoint.
      - In-memory key caching with lifespan.
      - Automatic re-fetch on unknown `kid` (key rotation).
    """
    global _jwks_client
    if _jwks_client is None:
        settings = get_settings()
        jwks_uri = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
        logger.info("Initializing JWKS client for endpoint: %s", jwks_uri)
        _jwks_client = PyJWKClient(
            uri=jwks_uri,
            cache_jwk_set=True,
            lifespan=_JWKS_CACHE_TTL_SECONDS,
            timeout=_JWKS_TIMEOUT_SECONDS,
        )
    return _jwks_client


def reset_jwks_client(client: PyJWKClient | None = None) -> None:
    """
    Replace the module-level JWKS client.
    Used in tests to inject a mock client without touching module internals.
    """
    global _jwks_client
    _jwks_client = client


# ---------------------------------------------------------------------------
# Claim constants
# ---------------------------------------------------------------------------

# Supabase access tokens use "authenticated" as the audience claim value.
_SUPABASE_AUDIENCE = "authenticated"


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


class AuthenticationError(Exception):
    """
    Raised when a JWT cannot be authenticated.
    Callers translate this into an HTTP 401 response.
    The message is intentionally generic — never expose token details.
    """


def verify_supabase_jwt(token: str) -> dict[str, Any]:
    """
    Cryptographically verify a Supabase-issued JWT.

    Steps:
      1. Obtain the matching signing key from the JWKS using the JWT's `kid`.
         PyJWKClient will re-fetch the JWKS if the `kid` is unknown (key rotation).
      2. Verify the signature using the key's algorithm (from JWKS, NOT the
         JWT header — this prevents algorithm confusion attacks).
      3. Validate standard claims: exp, aud.
      4. Require `sub` to be present and non-empty.

    Args:
        token: Raw JWT string (must NOT include "Bearer " prefix).

    Returns:
        The validated JWT payload dict.

    Raises:
        AuthenticationError: For any verification or claim-validation failure.
        Never raises with token-revealing details in the message.
    """
    client = _get_jwks_client()

    try:
        signing_key = client.get_signing_key_from_jwt(token)
    except PyJWKClientError:
        # JWKS fetch failure or no matching key — treat as authentication failure.
        logger.warning("JWKS key resolution failed (fetch error or unknown kid)")
        raise AuthenticationError("Authentication failed.")
    except Exception:
        logger.warning("Unexpected error resolving JWKS signing key")
        raise AuthenticationError("Authentication failed.")

    # The algorithm is taken from the resolved JWKS key, NOT the JWT header.
    # This prevents algorithm-confusion (e.g., HS256 with a public key).
    algorithm = signing_key.algorithm_name
    
    settings = get_settings()
    expected_issuer = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1"

    try:
        payload: dict[str, Any] = jwt.decode(
            jwt=token,
            key=signing_key.key,
            algorithms=[algorithm],
            audience=_SUPABASE_AUDIENCE,
            issuer=expected_issuer,
            options={
                "require": ["exp", "sub", "aud", "iss"],
                "verify_exp": True,
                "verify_aud": True,
                "verify_iss": True,
                "verify_signature": True,
            },
        )
    except ExpiredSignatureError:
        logger.info("JWT rejected: token has expired")
        raise AuthenticationError("Authentication failed.")
    except InvalidTokenError:
        logger.info("JWT rejected: invalid token claims or signature")
        raise AuthenticationError("Authentication failed.")
    except Exception:
        logger.warning("Unexpected error during JWT decode")
        raise AuthenticationError("Authentication failed.")

    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        logger.warning("JWT rejected: missing or empty 'sub' claim")
        raise AuthenticationError("Authentication failed.")

    return payload
