"""
DevTwin Backend — Authentication Dependencies

Provides reusable FastAPI dependencies for:
  - get_current_user: verifies the Supabase JWT and returns the verified sub.
  - get_current_developer: resolves the verified sub to a Developer record.

Design:
  - JWT verification is done in core/security.py (JWKS-based, asymmetric).
  - Developer lookup uses the existing async SQLAlchemy session.
  - If no developer record exists for the verified sub, returns 401.
    Developer CREATION is NOT performed here — that is POST /developers/me.
  - Error responses are generic. No JWT payload is ever returned to clients.
  - Raw tokens are never logged.

References: ADR-014, docs/05_SYSTEM_ARCHITECTURE.md
"""

import logging
import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthenticationError, verify_supabase_jwt
from app.db.connection import get_db_session
from app.models.developer import Developer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Bearer extractor
# HTTPBearer rejects requests with no Authorization header or a non-Bearer
# scheme automatically, returning 403. We override auto_error to handle it
# ourselves so we can return a consistent 401.
# ---------------------------------------------------------------------------

_bearer_scheme = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Shared 401 response — used consistently throughout this module
# ---------------------------------------------------------------------------

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Authentication required.",
    headers={"WWW-Authenticate": "Bearer"},
)


# ---------------------------------------------------------------------------
# Authenticated user representation (post-JWT-verification, pre-DB-lookup)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuthenticatedUser:
    """
    Lightweight representation of a Supabase-verified user.
    Contains only what was extracted from the verified JWT claims.
    sub is the Supabase auth.users.id (== developers.auth_user_id).
    """

    sub: str  # Supabase auth UUID string (from JWT 'sub' claim)


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthenticatedUser:
    """
    FastAPI dependency: extract and cryptographically verify the Supabase JWT.

    1. Reject missing Authorization header → 401.
    2. Reject non-Bearer schemes → 401.
    3. Verify JWT signature via Supabase JWKS → 401 on failure.
    4. Validate claims (exp, sub, aud) → 401 on failure.
    5. Return AuthenticatedUser containing the verified sub.

    NEVER logs the token or its contents.
    """
    if credentials is None:
        # No Authorization header present, or scheme is not Bearer.
        raise _UNAUTHORIZED

    token = credentials.credentials
    if not token:
        raise _UNAUTHORIZED

    try:
        payload = verify_supabase_jwt(token)
    except AuthenticationError:
        # verify_supabase_jwt already logged a safe warning.
        raise _UNAUTHORIZED

    sub = payload.get("sub")
    # sub presence and type were already validated inside verify_supabase_jwt,
    # but we guard defensively here in case of future refactors.
    if not sub or not isinstance(sub, str):
        raise _UNAUTHORIZED

    return AuthenticatedUser(sub=sub)


# ---------------------------------------------------------------------------
# get_current_developer
# ---------------------------------------------------------------------------


async def get_current_developer(
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Developer:
    """
    FastAPI dependency: resolve the verified JWT sub to a Developer record.

    JWT sub == Supabase auth.users.id == developers.auth_user_id

    - If a matching developer record exists → return it.
    - If NO matching developer record exists → 401.
      Developer creation is NOT performed here (see POST /developers/me).

    Returns the Developer ORM instance for use by route handlers.
    """
    try:
        auth_user_uuid = uuid.UUID(current_user.sub)
    except ValueError:
        # sub is not a valid UUID — this should be impossible after JWT verification
        # on a Supabase token, but we guard it explicitly.
        logger.warning("Verified JWT sub is not a valid UUID — rejecting.")
        raise _UNAUTHORIZED

    result = await session.execute(
        select(Developer).where(Developer.auth_user_id == auth_user_uuid)
    )
    developer = result.scalar_one_or_none()

    if developer is None:
        # Authenticated Supabase user exists but has not yet created a DevTwin
        # developer record. They must call POST /developers/me first.
        logger.info(
            "Authenticated user has no developer record (auth_user_id=<redacted>). "
            "POST /developers/me required."
        )
        raise _UNAUTHORIZED

    return developer
