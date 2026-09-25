"""
DevTwin Backend — GitHub Routes
"""

import base64
import hashlib
import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_developer
from app.core.config import get_settings
from app.db.connection import get_db_session
from app.models.developer import Developer
from app.models.github_account import GitHubAccount
from app.services.github.state import (
    create_pending_state,
    claim_state,
    GitHubStateNotFoundError,
    GitHubStateExpiredError,
)
from app.services.github.exceptions import GitHubStatePersistenceError, GitHubHTTPError
from app.services.github.client import GitHubClient
from app.services.github.auth import generate_app_jwt

from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/github", tags=["github"])


@router.get("/install")
async def get_github_install_url(
    developer: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_db_session)
) -> dict[str, str]:
    """
    Initiate the GitHub App installation flow.

    Requires a valid Supabase JWT for an existing DevTwin developer.
    Generates a secure OAuth state token, persists it (hashed + encrypted),
    and returns the GitHub App installation URL containing the state parameter.

    The state parameter serves as the CSRF guard and developer-identity binding.
    PKCE is used: GitHub's /installations/new endpoint does not bind PKCE
    parameters to the resulting authorization code for all flows, but DevTwin
    enforces it for security hardening.
    """
    settings = get_settings()

    try:
        pending_state = await create_pending_state(session, developer.id)
    except GitHubStatePersistenceError:
        logger.error("Failed to initialize GitHub OAuth state for developer.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize GitHub installation flow."
        )

    # Construct the GitHub App installation URL
    base_url = f"https://github.com/apps/{settings.GITHUB_APP_SLUG}/installations/new"

    # Calculate S256 PKCE code_challenge from the plaintext verifier
    digest = hashlib.sha256(pending_state.code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")

    query_params = {
        "state": pending_state.raw_state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    install_url = f"{base_url}?{urlencode(query_params)}"

    logger.info("Generated GitHub installation URL for developer.")

    return {"install_url": install_url}

@router.get("/callback")
async def github_callback(
    state: str = Query(..., description="OAuth state from GitHub"),
    code: str | None = Query(None, description="OAuth authorization code"),
    error: str | None = Query(None, description="OAuth error from GitHub"),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Handle GitHub App OAuth callback.
    """
    if error:
        logger.warning("GitHub OAuth callback received an error response.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub OAuth authorization failed."
        )

    if not code:
        logger.warning("GitHub OAuth callback received without code.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub OAuth authorization code missing."
        )

    try:
        state_context = await claim_state(session, state)
    except GitHubStateNotFoundError:
        logger.warning("GitHub OAuth state rejected: unknown state.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state."
        )
    except GitHubStateExpiredError:
        logger.warning("GitHub OAuth state rejected: expired or already used.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state."
        )
    except Exception:
        logger.error("Unexpected error during OAuth state validation.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate OAuth state."
        )

    client = GitHubClient()
    try:
        # Token is purposefully discarded after this scope
        _ = await client.exchange_oauth_code(
            code=code,
            code_verifier=state_context.code_verifier
        )
    except GitHubHTTPError:
        logger.error("GitHub OAuth exchange failed.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to exchange authorization code with GitHub."
        )
    except Exception:
        logger.error("Unexpected error during OAuth token exchange.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error during token exchange."
        )

    logger.info("GitHub OAuth callback received and exchange succeeded.")

    return {"status": "success", "detail": "OAuth authorization successful."}
