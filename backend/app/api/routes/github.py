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

@router.get("/callback")
async def github_callback(
    state: str | None = None,
    installation_id: int | None = None,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Handle GitHub App installation redirect.
    Verifies the short-lived state, verifies the installation via GitHub API,
    and links the GitHub account to the developer.
    """
    if not state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing state parameter.")
    if not installation_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing installation_id parameter.")

    try:
        claimed_state = await claim_state(session, state)
    except GitHubStateNotFoundError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state token.")
    except GitHubStateExpiredError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="State token expired or already used.")
    except Exception as e:
        logger.error(f"Error claiming state: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

    developer_id = claimed_state.developer_id

    # Verify installation belongs to DevTwin App
    try:
        app_jwt = generate_app_jwt()
        github_client = GitHubClient()
        installation = await github_client.get_installation(installation_id, app_jwt)
    except GitHubHTTPError as e:
        err_str = str(e).lower()
        if "not found" in err_str or "404" in err_str:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GitHub App Installation not found.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="GitHub API error.")
    except Exception as e:
        logger.error(f"Error verifying installation: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

    github_id = installation.account_github_id
    username = installation.account_login

    try:
        stmt = select(GitHubAccount).where(GitHubAccount.developer_id == developer_id)
        result = await session.execute(stmt)
        existing_account = result.scalar_one_or_none()

        if existing_account:
            if existing_account.github_id != github_id:
                if existing_account.disconnected_at is None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Developer already has an active GitHub account connected."
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Account switching is not supported."
                    )
            else:
                # Reconnecting the same account
                existing_account.installation_id = installation_id
                existing_account.username = username
                existing_account.disconnected_at = None
        else:
            # First-time link
            new_account = GitHubAccount(
                developer_id=developer_id,
                github_id=github_id,
                username=username,
                installation_id=installation_id
            )
            session.add(new_account)

        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This GitHub account is already linked to another developer."
        )
    except HTTPException:
        await session.rollback()
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Database error linking account: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

    return {"status": "success", "message": "GitHub account successfully linked"}
