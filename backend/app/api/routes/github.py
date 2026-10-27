"""
DevTwin Backend — GitHub Routes
"""

import base64
from datetime import datetime, timezone
import hashlib
import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
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
from app.services.github.exceptions import (
    GitHubStatePersistenceError,
    GitHubHTTPError,
    GitHubResponseError,
    GitHubIntegrationError,
    GitHubRateLimitError,
)
from app.services.github.client import GitHubClient
from app.services.github.auth import generate_app_jwt

from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/github", tags=["github"])


class GitHubStatusResponse(BaseModel):
    is_connected: bool
    is_installed: bool
    is_disconnected: bool
    github_username: str | None


class GitHubRepositoryResponse(BaseModel):
    github_repo_id: int
    name: str
    full_name: str
    visibility: str
    private: bool
    default_branch: str


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

def _frontend_redirect(param: str, value: str) -> RedirectResponse:
    settings = get_settings()
    base_url = settings.FRONTEND_URL.rstrip("/")
    query = urlencode({param: value})
    target_url = f"{base_url}/?{query}"
    return RedirectResponse(url=target_url, status_code=status.HTTP_302_FOUND)


@router.get("/callback")
async def github_callback(
    state: str = Query(..., description="OAuth state from GitHub"),
    code: str | None = Query(None, description="OAuth authorization code"),
    error: str | None = Query(None, description="OAuth error from GitHub"),
    session: AsyncSession = Depends(get_db_session)
) -> RedirectResponse:
    """
    Handle GitHub App OAuth callback.
    Redirects the browser back to the frontend with safe status indicators.
    Never exposes internal IDs, codes, tokens, or stack traces in redirect URLs.
    """
    if error:
        logger.warning("GitHub OAuth callback received an error response from GitHub: %s", error)
        return _frontend_redirect("github_error", "access_denied")

    if not code:
        logger.warning("GitHub OAuth callback received without code.")
        return _frontend_redirect("github_error", "missing_code")

    try:
        state_context = await claim_state(session, state)
    except (GitHubStateNotFoundError, GitHubStateExpiredError):
        logger.warning("GitHub OAuth state rejected: invalid, expired, or already used.")
        return _frontend_redirect("github_error", "state_expired")
    except Exception:
        logger.error("Unexpected error during OAuth state validation.")
        return _frontend_redirect("github_error", "state_validation_failed")

    client = GitHubClient()
    try:
        oauth_token = await client.exchange_oauth_code(
            code=code,
            code_verifier=state_context.code_verifier
        )
    except GitHubHTTPError:
        logger.error("GitHub OAuth exchange failed.")
        return _frontend_redirect("github_error", "exchange_failed")
    except Exception:
        logger.error("Unexpected error during OAuth token exchange.")
        return _frontend_redirect("github_error", "exchange_failed")

    try:
        github_user = await client.get_authenticated_user(oauth_token.access_token)
    except (GitHubHTTPError, GitHubResponseError):
        logger.error("Failed to verify GitHub user identity.")
        return _frontend_redirect("github_error", "identity_failed")
    except Exception:
        logger.error("Unexpected error fetching GitHub user.")
        return _frontend_redirect("github_error", "identity_failed")

    try:
        installations = await client.list_user_installations(oauth_token.access_token)
    except (GitHubHTTPError, GitHubResponseError):
        logger.error("Failed to verify GitHub installations.")
        return _frontend_redirect("github_error", "installations_failed")
    except Exception:
        logger.error("Unexpected error fetching GitHub installations.")
        return _frontend_redirect("github_error", "installations_failed")

    # Discard OAuth token — it must not be persisted, logged, or returned.
    # All identity information is already captured in github_user.
    del oauth_token

    personal_installation = next(
        (
            installation
            for installation in installations
            if installation.account_github_id == github_user.github_id
        ),
        None,
    )

    installation_id = (
        personal_installation.installation_id
        if personal_installation is not None
        else None
    )

    # ------------------------------------------------------------------
    # Step 5C/5D — Account Linking & Installation Persistence
    #
    # Authoritative identities:
    #   Developer  : state_context.developer_id   (from DB claim — not browser)
    #   GitHub user: github_user.github_id / .username  (from GitHub API)
    #   Installation: installation_id (exact personal match only)
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
            installation_id=installation_id,
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
                dev_check_result = await session.execute(
                    select(GitHubAccount).where(
                        GitHubAccount.developer_id == state_context.developer_id
                    )
                )
                if dev_check_result.scalar_one_or_none() is not None:
                    logger.warning("Developer already has a different GitHub account linked.")
                    return _frontend_redirect("github_error", "developer_conflict")

                logger.error("Unexpected state: IntegrityError but no row found after rollback.")
                return _frontend_redirect("github_error", "linking_failed")

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
                    return _frontend_redirect("github_error", "linking_failed")
            else:
                # Different developer owns this GitHub account.
                logger.warning("GitHub account conflict detected during race condition.")
                return _frontend_redirect("github_error", "account_conflict")
        except Exception:
            await session.rollback()
            logger.error("Unexpected database error during GitHub account creation.")
            return _frontend_redirect("github_error", "linking_failed")

    elif existing_account.developer_id == state_context.developer_id:
        # Case 2 — Same developer: reconnect / reauthorization.
        # Update mutable fields only. Do not touch historical data.
        existing_account.username = github_user.username
        existing_account.installation_id = installation_id
        existing_account.disconnected_at = None
        try:
            await session.commit()
            logger.info("GitHub account reconnected for developer.")
        except Exception:
            await session.rollback()
            logger.error("Unexpected database error during GitHub account reconnect.")
            return _frontend_redirect("github_error", "linking_failed")

    else:
        # Case 3 — GitHub account belongs to a different developer.
        logger.warning("GitHub account ownership conflict: account belongs to another developer.")
        return _frontend_redirect("github_error", "account_conflict")

    logger.info("GitHub account linking complete. Redirecting to frontend.")
    return _frontend_redirect("github", "success")


@router.get("/status", response_model=GitHubStatusResponse)
async def get_github_status(
    developer: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_db_session)
) -> GitHubStatusResponse:
    """
    Retrieve the current local GitHub connection status for the authenticated developer.
    """
    try:
        query = select(GitHubAccount).where(GitHubAccount.developer_id == developer.id)
        account = await session.scalar(query)
    except Exception:
        logger.error("Unexpected database error retrieving GitHub status.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred retrieving GitHub status."
        )

    if not account:
        return GitHubStatusResponse(
            is_connected=False,
            is_installed=False,
            is_disconnected=False,
            github_username=None,
        )

    if account.disconnected_at is not None:
        return GitHubStatusResponse(
            is_connected=False,
            is_installed=False,
            is_disconnected=True,
            github_username=account.username,
        )

    # Developer is connected
    return GitHubStatusResponse(
        is_connected=True,
        is_installed=(account.installation_id is not None),
        is_disconnected=False,
        github_username=account.username,
    )


@router.delete("/disconnect", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_github(
    developer: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """
    Disconnect GitHub App integration for the authenticated developer.

    Implements safe soft-disconnect per ADR-014: sets disconnected_at = NOW().
    Preserves all historical repositories, projects, and analysis data.
    Idempotent: if already disconnected, returns 204 No Content without re-updating.
    """
    try:
        query = select(GitHubAccount).where(GitHubAccount.developer_id == developer.id)
        result = await session.execute(query)
        account = result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Database error looking up GitHub account for disconnect: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred."
        )

    if not account:
        logger.warning(f"Developer {developer.id} attempted to disconnect without linked GitHub account.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No GitHub account linked."
        )

    if account.disconnected_at is None:
        account.disconnected_at = datetime.now(timezone.utc)
        try:
            await session.commit()
            logger.info(f"GitHub account disconnected for developer {developer.id}.")
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to disconnect GitHub account: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to disconnect GitHub account."
            )

    return None


@router.get("/repositories", response_model=list[GitHubRepositoryResponse])
async def list_accessible_github_repositories(
    developer: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_db_session),
) -> list[GitHubRepositoryResponse]:
    """
    List repositories accessible to the developer's GitHub App installation.

    Generates an ephemeral installation access token on demand.
    Queries GitHub's /installation/repositories with automatic pagination.
    Returns normalized repository choices for registration into DevTwin projects.
    Never persists the installation token or exposes secrets.
    """
    gh_query = select(GitHubAccount).where(GitHubAccount.developer_id == developer.id)
    gh_result = await session.execute(gh_query)
    github_account = gh_result.scalar_one_or_none()

    if not github_account:
        logger.warning(f"Developer {developer.id} has no GitHubAccount.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No GitHub account linked."
        )

    if github_account.disconnected_at is not None:
        logger.warning(f"Developer {developer.id} GitHubAccount is disconnected.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub account is disconnected."
        )

    if github_account.installation_id is None:
        logger.warning(f"Developer {developer.id} has no personal installation.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No personal GitHub App installation found."
        )

    client = GitHubClient()
    try:
        app_jwt = generate_app_jwt()
        installation_token = await client.create_installation_access_token(
            github_account.installation_id, app_jwt
        )
    except GitHubIntegrationError as e:
        logger.error(f"Failed to generate installation token: {e.__class__.__name__}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to authenticate with GitHub."
        )

    try:
        repos_data = await client.list_installation_repositories(installation_token)
    except GitHubRateLimitError:
        logger.warning("GitHub rate limit exceeded listing repositories.")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="GitHub API rate limit exceeded. Please try again later."
        )
    except GitHubHTTPError as e:
        logger.warning(f"GitHub HTTP error listing installation repositories: HTTP {e.status_code}")
        if e.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="GitHub installation authentication failed."
            )
        elif e.status_code in (403, 404):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="GitHub App installation lacks access to list repositories."
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch repositories from GitHub."
        )
    except GitHubIntegrationError as e:
        logger.error(f"GitHub integration error listing repositories: {e.__class__.__name__}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch repositories from GitHub."
        )
    finally:
        del installation_token

    results: list[GitHubRepositoryResponse] = []
    for repo in repos_data:
        repo_id = repo.get("id")
        name = repo.get("name")
        full_name = repo.get("full_name")
        is_private = bool(repo.get("private", False))
        visibility = repo.get("visibility") or ("private" if is_private else "public")
        default_branch = repo.get("default_branch") or "main"

        if repo_id and name and full_name:
            results.append(
                GitHubRepositoryResponse(
                    github_repo_id=repo_id,
                    name=name,
                    full_name=full_name,
                    visibility=visibility,
                    private=is_private,
                    default_branch=default_branch,
                )
            )

    return results
