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
from app.services.github.exceptions import GitHubStatePersistenceError, GitHubHTTPError, GitHubResponseError
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
        oauth_token = await client.exchange_oauth_code(
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

    try:
        github_user = await client.get_authenticated_user(oauth_token.access_token)
    except GitHubHTTPError:
        logger.error("Failed to fetch GitHub user profile.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to verify GitHub identity."
        )
    except GitHubResponseError:
        logger.error("Invalid response from GitHub user profile API.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Received malformed identity data from GitHub."
        )
    except Exception:
        logger.error("Unexpected error fetching GitHub user.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error during identity verification."
        )

    try:
        installations = await client.list_user_installations(oauth_token.access_token)
    except GitHubHTTPError:
        logger.error("Failed to fetch GitHub user installations.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to verify GitHub installations."
        )
    except GitHubResponseError:
        logger.error("Invalid response from GitHub installations API.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Received malformed installations data from GitHub."
        )
    except Exception:
        logger.error("Unexpected error fetching GitHub installations.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error during installation verification."
        )

    # Discard OAuth token — it must not be persisted, logged, or returned.
    # All identity information is already captured in github_user.
    del oauth_token

    # ------------------------------------------------------------------
    # Step 5C — Account Linking
    #
    # Authoritative identities:
    #   Developer  : state_context.developer_id   (from DB claim — not browser)
    #   GitHub user: github_user.github_id / .username  (from GitHub API)
    #
    # installation_id is intentionally left NULL — persisted in a later step.
    # ------------------------------------------------------------------

    # Query for an existing github_accounts row by the GitHub-issued user ID.
    result = await session.execute(
        select(GitHubAccount).where(GitHubAccount.github_id == github_user.github_id)
    )
    existing_account: GitHubAccount | None = result.scalar_one_or_none()

    if existing_account is None:
        # Case 1 — No existing row: create a fresh, active GitHubAccount.
        new_account = GitHubAccount(
            developer_id=state_context.developer_id,
            github_id=github_user.github_id,
            username=github_user.username,
            installation_id=None,
            disconnected_at=None,
        )
        session.add(new_account)
        try:
            await session.commit()
            await session.refresh(new_account)
            logger.info("GitHub account linked successfully for developer.")
        except IntegrityError:
            await session.rollback()
            # Race condition: another request inserted concurrently.
            # Re-query to determine the correct case.
            race_result = await session.execute(
                select(GitHubAccount).where(
                    GitHubAccount.github_id == github_user.github_id
                )
            )
            race_account: GitHubAccount | None = race_result.scalar_one_or_none()
            if race_account is None:
                # The IntegrityError was not caused by a concurrent insert of this github_id.
                # It must have been caused by the developer_id UNIQUE constraint.
                # Let's verify this safely.
                dev_check_result = await session.execute(
                    select(GitHubAccount).where(
                        GitHubAccount.developer_id == state_context.developer_id
                    )
                )
                if dev_check_result.scalar_one_or_none() is not None:
                    logger.warning("Developer already has a different GitHub account linked.")
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="You already have a linked GitHub account."
                    )

                logger.error("Unexpected state: IntegrityError but no row found after rollback.")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="An internal error occurred during account linking."
                )

            if race_account.developer_id == state_context.developer_id:
                # Same developer won the race — treat as a reconnect.
                race_account.username = github_user.username
                race_account.disconnected_at = None
                try:
                    await session.commit()
                    logger.info("GitHub account reconnected after race condition.")
                except Exception:
                    await session.rollback()
                    logger.error("Failed to persist reconnect after race condition.")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="An internal error occurred during account linking."
                    )
            else:
                # Different developer owns this GitHub account.
                logger.warning("GitHub account conflict detected during race condition.")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This GitHub account is already linked to another developer."
                )
        except Exception:
            await session.rollback()
            logger.error("Unexpected database error during GitHub account creation.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An internal error occurred during account linking."
            )

    elif existing_account.developer_id == state_context.developer_id:
        # Case 2 — Same developer: reconnect / reauthorization.
        # Update mutable fields only. Do not touch historical data.
        existing_account.username = github_user.username
        existing_account.disconnected_at = None
        try:
            await session.commit()
            logger.info("GitHub account reconnected for developer.")
        except Exception:
            await session.rollback()
            logger.error("Unexpected database error during GitHub account reconnect.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An internal error occurred during account linking."
            )

    else:
        # Case 3 — GitHub account belongs to a different developer.
        # Sanitized 409 — no internal identifiers exposed.
        logger.warning("GitHub account ownership conflict: account belongs to another developer.")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This GitHub account is already linked to another developer."
        )

    logger.info("GitHub account linking complete.")

    return {
        "status": "success",
        "detail": "GitHub account linked successfully.",
        "github_username": github_user.username,
    }
