"""
DevTwin Backend — GitHub Routes
"""

import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_developer
from app.core.config import get_settings
from app.db.connection import get_db_session
from app.models.developer import Developer
from app.services.github.state import create_pending_state
from app.services.github.exceptions import GitHubStatePersistenceError

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
    PKCE is not used: GitHub's /installations/new endpoint does not bind PKCE
    parameters to the resulting authorization code. DevTwin is a confidential
    client and uses client_secret for secure token exchange.
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

    query_params = {
        "state": pending_state.raw_state,
    }

    install_url = f"{base_url}?{urlencode(query_params)}"

    logger.info("Generated GitHub installation URL for developer.")

    return {"install_url": install_url}
