"""
DevTwin Backend — Repositories Routes
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies.auth import get_current_developer
from app.db.connection import get_db_session
from app.models.developer import Developer
from app.models.project import Project
from app.models.github_account import GitHubAccount
from app.models.repository import Repository
from app.services.github.client import GitHubClient
from app.services.github.auth import generate_app_jwt
from app.services.github.exceptions import GitHubHTTPError, GitHubResponseError, GitHubIntegrationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repositories", tags=["repositories"])

class RepositoryCreateRequest(BaseModel):
    project_id: uuid.UUID
    github_repo_id: int

class RepositoryResponse(BaseModel):
    id: uuid.UUID
    project_id: Optional[uuid.UUID]
    github_repo_id: Optional[int]
    owner_login: str
    name: str
    full_name: str
    url: str
    default_branch: str
    visibility: str
    synced_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def create_repository(
    request: RepositoryCreateRequest,
    developer: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Register a GitHub repository to a project.
    """
    # 1. Verify project ownership
    query = select(Project).where(
        Project.id == request.project_id,
        Project.developer_id == developer.id
    )
    project_result = await session.execute(query)
    project = project_result.scalar_one_or_none()

    if not project:
        logger.warning(f"Project {request.project_id} not found or not owned by developer {developer.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or not owned by developer."
        )

    # 2. Query GitHubAccount
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

    # 3. GitHub API interaction
    client = GitHubClient()
    
    try:
        app_jwt = generate_app_jwt()
        # Ephemeral token
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
        repo_data = await client.get_installation_repository(request.github_repo_id, installation_token)
    except GitHubHTTPError as e:
        logger.warning(f"Failed to fetch repository from GitHub: HTTP {e.status_code}")
        if e.status_code in (403, 404):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Repository not found or inaccessible by your personal installation."
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to verify repository with GitHub."
        )
    except GitHubIntegrationError as e:
        logger.error(f"GitHub integration error fetching repo: {e.__class__.__name__}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to verify repository with GitHub."
        )
    
    # 4. Construct Repository Model
    owner_login = repo_data.get("owner", {}).get("login")
    name = repo_data.get("name")
    full_name = repo_data.get("full_name")
    html_url = repo_data.get("html_url")
    default_branch = repo_data.get("default_branch")
    visibility = repo_data.get("visibility")
    
    if (
        not all([owner_login, name, full_name, html_url, default_branch, visibility])
        or not isinstance(default_branch, str)
        or not default_branch.strip()
    ):
        logger.error("GitHub repository response missing required metadata fields.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid repository metadata received from GitHub."
        )

    new_repo = Repository(
        project_id=project.id,
        github_repo_id=request.github_repo_id,
        owner_login=owner_login,
        name=name,
        full_name=full_name,
        url=html_url,
        default_branch=default_branch,
        visibility=visibility
    )

    session.add(new_repo)

    try:
        await session.commit()
        await session.refresh(new_repo)
    except IntegrityError as e:
        await session.rollback()
        orig = getattr(e, "orig", None)
        sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
        
        if sqlstate == "23505" or "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
            logger.warning(f"Duplicate repository registration attempt for github_repo_id {request.github_repo_id}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Repository already registered."
            )
            
        logger.error(f"IntegrityError saving repository: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save repository."
        )
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to save repository: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save repository."
        )

    return new_repo
