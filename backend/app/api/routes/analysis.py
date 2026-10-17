"""
DevTwin Backend — Analysis Pipeline Routes
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.dependencies.auth import get_current_developer
from app.db.connection import get_db_session
from app.models.analysis_job import AnalysisJob
from app.models.analysis_run import AnalysisRun
from app.models.developer import Developer
from app.models.project import Project
from app.models.repository import Repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["Analysis"])


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------


class AnalysisJobCreateRequest(BaseModel):
    repository_id: uuid.UUID

    model_config = ConfigDict(extra="forbid")


class AnalysisJobCreateResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    status: str

    model_config = ConfigDict(from_attributes=True)


class AnalysisJobResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    repository_id: uuid.UUID
    status: str
    attempt_count: int
    requested_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AnalysisRunResponse(BaseModel):
    id: uuid.UUID
    analysis_job_id: uuid.UUID
    repository_id: uuid.UUID
    status: str
    analyzer_version: str
    schema_version: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/jobs", response_model=AnalysisJobCreateResponse, status_code=status.HTTP_201_CREATED)
async def submit_analysis_job(
    request: AnalysisJobCreateRequest,
    developer: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_db_session),
) -> AnalysisJobCreateResponse:
    """
    Submit a repository for analysis (Stage 1: Input -> Queue).

    Enforces that the repository belongs to an owned project of the authenticated developer.
    Persists an analysis_jobs record with status QUEUED and attempt_count 0.
    Does not synchronously execute analysis or spin up workers.
    """
    try:
        repo_query = (
            select(Repository)
            .join(Project, Repository.project_id == Project.id)
            .where(
                Repository.id == request.repository_id,
                Project.developer_id == developer.id,
            )
        )
        repo_result = await session.execute(repo_query)
        repository = repo_result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Database error validating repository {request.repository_id} for analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate repository ownership."
        )

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found or not owned by developer."
        )

    new_job = AnalysisJob(
        id=uuid.uuid4(),
        repository_id=repository.id,
        status="QUEUED",
        attempt_count=0,
    )
    session.add(new_job)

    try:
        await session.commit()
        await session.refresh(new_job)
        logger.info(f"Analysis job {new_job.id} created for repository {repository.id} (developer {developer.id}).")
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to persist analysis job for repository {repository.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit analysis job."
        )

    return AnalysisJobCreateResponse(
        id=new_job.id,
        job_id=new_job.id,
        status=new_job.status,
    )


@router.get("/jobs/{id}", response_model=AnalysisJobResponse)
async def get_analysis_job(
    id: uuid.UUID,
    developer: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_db_session),
) -> AnalysisJobResponse:
    """
    Poll or inspect the status and metadata of an analysis job.

    Enforces that the job belongs to a repository and project owned by the authenticated developer.
    Returns 404 if the job does not exist or belongs to another developer.
    """
    try:
        query = (
            select(AnalysisJob)
            .join(Repository, AnalysisJob.repository_id == Repository.id)
            .join(Project, Repository.project_id == Project.id)
            .where(
                AnalysisJob.id == id,
                Project.developer_id == developer.id,
            )
        )
        result = await session.execute(query)
        job = result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Database error fetching analysis job {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch analysis job."
        )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis job not found."
        )

    return AnalysisJobResponse(
        id=job.id,
        job_id=job.id,
        repository_id=job.repository_id,
        status=job.status,
        attempt_count=job.attempt_count,
        requested_at=job.requested_at,
        completed_at=job.completed_at,
    )


@router.get("/jobs/{id}/runs", response_model=List[AnalysisRunResponse])
async def list_analysis_job_runs(
    id: uuid.UUID,
    developer: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_db_session),
) -> List[AnalysisRun]:
    """
    Retrieve discrete execution attempts (analysis_runs) for an analysis job.

    Enforces that the job belongs to the authenticated developer.
    Returns 404 if the job does not exist or belongs to another developer.
    """
    try:
        job_query = (
            select(AnalysisJob)
            .join(Repository, AnalysisJob.repository_id == Repository.id)
            .join(Project, Repository.project_id == Project.id)
            .where(
                AnalysisJob.id == id,
                Project.developer_id == developer.id,
            )
        )
        job_result = await session.execute(job_query)
        job = job_result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Database error verifying analysis job {id} for runs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch analysis runs."
        )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis job not found."
        )

    try:
        runs_query = (
            select(AnalysisRun)
            .where(AnalysisRun.analysis_job_id == id)
            .order_by(AnalysisRun.created_at.asc())
        )
        runs_result = await session.execute(runs_query)
        runs = runs_result.scalars().all()
        return list(runs)
    except Exception as e:
        logger.error(f"Database error fetching runs for job {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch analysis runs."
        )
