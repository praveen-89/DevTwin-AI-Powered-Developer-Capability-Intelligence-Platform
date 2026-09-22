"""
DevTwin Backend — GitHub OAuth State + PKCE Persistence Service

Owns the transient OAuth state lifecycle:
  1. generate_oauth_state()   — create cryptographically secure raw state + PKCE verifier
  2. create_pending_state()   — INSERT an encrypted, hashed state row with TTL
  3. claim_state()            — atomically UPDATE ... RETURNING the pending row
  4. (internal) decrypt verifier from the claimed row

Security invariants enforced here:
  - Raw state is NEVER persisted (only SHA-256 hash stored).
  - Raw PKCE verifier is NEVER persisted (only Fernet-encrypted bytes stored).
  - State is single-use: claim is an atomic UPDATE that sets used_at.
  - State has a TTL: claim rejects rows where expires_at <= NOW().
  - No raw secrets appear in logs.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.crypto import (
    encrypt_pkce_verifier,
    decrypt_pkce_verifier,
    PKCEEncryptionError,
    PKCEDecryptionError,
)
from app.models.github_connection_state import GitHubConnectionState
from .exceptions import (
    GitHubStateNotFoundError,
    GitHubStateExpiredError,
    GitHubStatePersistenceError,
    GitHubStateDecryptionError,
)

logger = logging.getLogger(__name__)

# PKCE verifier length: 32 url-safe bytes → 43 base64url characters.
# Satisfies RFC 7636 requirement: 43–128 characters.
_PKCE_VERIFIER_BYTES = 32


@dataclass(frozen=True)
class GitHubOAuthStateContext:
    """
    Result returned after a successful atomic state claim.

    Contains only the information the callback route needs:
      - developer_id: the developer who initiated the flow
      - code_verifier: plaintext PKCE verifier (recovered after claim)
      - state_id: the UUID of the consumed state row (for audit/tracing)

    Does NOT contain:
      - raw OAuth state string
      - encrypted verifier bytes
      - GitHub access tokens
      - Supabase JWT
    """

    developer_id: uuid.UUID
    code_verifier: str
    state_id: uuid.UUID


@dataclass(frozen=True)
class PendingOAuthState:
    """
    Result returned after creating a pending state row.

    The raw_state must be sent to GitHub as the OAuth `state` parameter.
    It is NOT persisted and must not be logged.
    The state_id is safe to log (UUID only).
    """

    raw_state: str          # sent to GitHub in the OAuth redirect URL
    state_id: uuid.UUID     # safe to log
    expires_at: datetime    # informational: when the state expires


# ---------------------------------------------------------------------------
# Public helpers (no database)
# ---------------------------------------------------------------------------

def generate_raw_state() -> str:
    """
    Generate a cryptographically secure random OAuth state token.

    Uses secrets.token_urlsafe(32) → ~256 bits of entropy.
    The returned value is the RAW state, used as the OAuth `state` parameter.
    It must NEVER be persisted; only its SHA-256 hash is stored.
    """
    return secrets.token_urlsafe(32)


def hash_state(raw_state: str) -> str:
    """
    Return the hex-encoded SHA-256 digest of the raw state.

    This is the value stored in `github_connection_states.state_hash`.
    Deterministic: hash_state(x) == hash_state(x) for all valid x.
    """
    return hashlib.sha256(raw_state.encode("utf-8")).hexdigest()


def generate_pkce_verifier() -> str:
    """
    Generate a cryptographically secure PKCE code_verifier.

    Returns a URL-safe base64 string of ~43 characters (256 bits of entropy),
    satisfying RFC 7636 §4.1 length requirements (43–128 characters).

    The returned value is PLAINTEXT and must be encrypted before persistence.
    """
    return secrets.token_urlsafe(_PKCE_VERIFIER_BYTES)


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------

async def create_pending_state(
    session: AsyncSession,
    developer_id: uuid.UUID,
) -> PendingOAuthState:
    """
    Generate a fresh OAuth state + PKCE verifier and persist a pending row.

    Steps:
      1. Generate raw_state (sent to GitHub; never stored).
      2. Compute state_hash = SHA-256(raw_state) → stored in DB.
      3. Generate plaintext code_verifier (never stored).
      4. Encrypt code_verifier → code_verifier_enc → stored in DB.
      5. INSERT the row with expires_at = NOW() + TTL.
      6. Commit.

    Returns PendingOAuthState containing the raw_state (to embed in the
    GitHub redirect URL) and safe metadata. The raw_state is NOT logged.

    Raises:
        GitHubStatePersistenceError: on any database error.
    """
    settings = get_settings()
    ttl_seconds = settings.GITHUB_STATE_TTL_SECONDS

    raw_state = generate_raw_state()
    state_hash = hash_state(raw_state)
    plaintext_verifier = generate_pkce_verifier()

    try:
        code_verifier_enc: bytes = encrypt_pkce_verifier(plaintext_verifier)
    except PKCEEncryptionError:
        logger.error("Failed to encrypt PKCE verifier during state creation.")
        raise GitHubStatePersistenceError("Failed to prepare OAuth state.")

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=ttl_seconds)

    state_row = GitHubConnectionState(
        developer_id=developer_id,
        state_hash=state_hash,
        expires_at=expires_at,
        code_verifier_enc=code_verifier_enc,
    )

    try:
        session.add(state_row)
        await session.commit()
        await session.refresh(state_row)
    except SQLAlchemyError:
        await session.rollback()
        logger.error("Failed to persist OAuth state row for developer.")
        raise GitHubStatePersistenceError("Failed to persist OAuth state.")

    logger.debug("Created pending OAuth state row id=%s", state_row.id)

    return PendingOAuthState(
        raw_state=raw_state,
        state_id=state_row.id,
        expires_at=expires_at,
    )


async def claim_state(
    session: AsyncSession,
    raw_state: str,
) -> GitHubOAuthStateContext:
    """
    Atomically claim a pending OAuth state and recover the PKCE verifier.

    Uses a single UPDATE ... RETURNING statement so that exactly one
    concurrent callback can succeed. SELECT-then-UPDATE would allow replay.

    Steps:
      1. Compute state_hash = SHA-256(raw_state).
      2. Atomic UPDATE: SET used_at = NOW() WHERE state_hash = :h
         AND used_at IS NULL AND expires_at > NOW() RETURNING id, developer_id,
         code_verifier_enc, expires_at, used_at.
      3. No row returned → state unknown, expired, or already claimed.
         Distinguish unknown vs expired/used via a secondary read.
      4. Decrypt code_verifier_enc → plaintext verifier.
      5. Commit the used_at timestamp.
      6. Return GitHubOAuthStateContext.

    Raises:
        GitHubStateNotFoundError: no row matched the state hash at all.
        GitHubStateExpiredError: row exists but is expired or already used.
        GitHubStateDecryptionError: row claimed but PKCE decryption failed.
        GitHubStatePersistenceError: database error during claim.
    """
    state_hash = hash_state(raw_state)

    # Atomic UPDATE ... RETURNING — sets used_at only if the row is
    # pending (used_at IS NULL) and not yet expired (expires_at > NOW()).
    claim_sql = text("""
        UPDATE github_connection_states
           SET used_at = NOW()
         WHERE state_hash = :state_hash
           AND used_at IS NULL
           AND expires_at > NOW()
     RETURNING id,
               developer_id,
               code_verifier_enc,
               expires_at,
               used_at
    """)

    try:
        result = await session.execute(claim_sql, {"state_hash": state_hash})
        row = result.fetchone()
    except SQLAlchemyError:
        logger.error("Database error during OAuth state claim.")
        raise GitHubStatePersistenceError("Failed to claim OAuth state.")

    if row is None:
        # No pending row matched. Check whether the row exists at all to
        # give a caller-distinguishable error.
        check_sql = text(
            "SELECT id FROM github_connection_states WHERE state_hash = :state_hash"
        )
        try:
            check_result = await session.execute(check_sql, {"state_hash": state_hash})
            existing = check_result.fetchone()
        except SQLAlchemyError:
            logger.error("Database error during OAuth state existence check.")
            raise GitHubStatePersistenceError("Failed to check OAuth state.")

        if existing is None:
            logger.warning("OAuth state claim attempted for unknown state hash.")
            raise GitHubStateNotFoundError("Invalid OAuth state.")
        else:
            # Row exists but failed the WHERE clause → expired or already used.
            logger.warning(
                "OAuth state claim failed: state row %s is expired or already used.",
                existing[0],
            )
            raise GitHubStateExpiredError("OAuth state is expired or already used.")

    state_id: uuid.UUID = row[0]
    developer_id: uuid.UUID = row[1]
    code_verifier_enc: Optional[bytes] = row[2]

    logger.debug("OAuth state row %s claimed for developer.", state_id)

    # Decrypt verifier before committing the used_at timestamp.
    if not code_verifier_enc:
        logger.error("OAuth state row %s has no encrypted verifier.", state_id)
        raise GitHubStateDecryptionError("OAuth state is missing PKCE verifier.")

    try:
        plaintext_verifier = decrypt_pkce_verifier(code_verifier_enc)
    except PKCEDecryptionError:
        logger.error("PKCE verifier decryption failed for state row %s.", state_id)
        raise GitHubStateDecryptionError("Failed to recover PKCE verifier.")

    try:
        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        logger.error("Failed to commit used_at for state row %s.", state_id)
        raise GitHubStatePersistenceError("Failed to finalise OAuth state claim.")

    return GitHubOAuthStateContext(
        developer_id=developer_id,
        code_verifier=plaintext_verifier,
        state_id=state_id,
    )
