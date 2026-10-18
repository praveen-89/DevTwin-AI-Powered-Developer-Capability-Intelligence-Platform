"""
DevTwin Backend — Worker Analysis Runner
"""

import argparse
import asyncio
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.connection import _get_session_factory
from app.models.analysis_job import AnalysisJob
from app.models.analysis_run import AnalysisRun
from app.services.github.auth import generate_app_jwt
from app.services.github.client import GitHubClient
from app.services.github.exceptions import (
    GitHubHTTPError,
    GitHubRateLimitError,
    GitHubNetworkError,
    GitHubIntegrationError,
)
from app.workers.fetcher import (
    FetcherError,
    RepositoryNotFoundError,
    RepositoryOwnershipError,
    GitHubAccountDisconnectedError,
    GitHubInstallationMissingError,
    SecurityArchiveError,
    CorruptArchiveError,
    fetch_repository_for_job,
    temporary_workspace,
)

logger = logging.getLogger(__name__)

MAX_JOB_ATTEMPTS = 3


# ---------------------------------------------------------------------------
# Sanitized Failure Translation
# ---------------------------------------------------------------------------


def sanitize_failure(exc: Exception) -> Tuple[str, str]:
    """
    Maps exceptions to sanitized error codes and diagnostic messages.
    Guarantees that access tokens, private keys, or internal tracebacks are never leaked.
    """
    if isinstance(exc, RepositoryNotFoundError):
        return ("REPOSITORY_NOT_FOUND", "Repository not found or inaccessible.")
    elif isinstance(exc, RepositoryOwnershipError):
        return ("REPOSITORY_UNOWNED", "Repository ownership verification failed.")
    elif isinstance(exc, GitHubAccountDisconnectedError):
        return ("ACCOUNT_DISCONNECTED", "GitHub account is disconnected.")
    elif isinstance(exc, GitHubInstallationMissingError):
        return ("INSTALLATION_MISSING", "GitHub App installation is missing.")
    elif isinstance(exc, SecurityArchiveError):
        return ("SECURITY_VIOLATION", "Repository archive security verification failed.")
    elif isinstance(exc, CorruptArchiveError):
        return ("CORRUPT_ARCHIVE", "Repository archive could not be extracted.")
    elif isinstance(exc, GitHubRateLimitError):
        return ("RATE_LIMITED", "GitHub API rate limit exceeded.")
    elif isinstance(exc, GitHubHTTPError):
        status = exc.status_code or 500
        return (f"GITHUB_HTTP_{status}", f"GitHub API error ({status}).")
    elif isinstance(exc, GitHubNetworkError):
        return ("NETWORK_ERROR", "Network error communicating with GitHub.")
    elif isinstance(exc, GitHubIntegrationError):
        return ("GITHUB_INTEGRATION_ERROR", "GitHub integration error occurred.")
    elif isinstance(exc, FetcherError):
        return (exc.code, exc.args[0] if exc.args else "Fetcher error.")

    logger.error("Unexpected worker exception: %s: %s", type(exc).__name__, exc)
    return ("INTERNAL_ERROR", "An internal error occurred during repository analysis.")


# ---------------------------------------------------------------------------
# Queue Claiming
# ---------------------------------------------------------------------------


async def claim_next_job(session: AsyncSession) -> Optional[AnalysisJob]:
    """
    Atomically claims the next eligible QUEUED analysis job.
    Uses SELECT ... FOR UPDATE SKIP LOCKED to prevent race conditions among concurrent workers.
    Sets status to 'PROCESSING' and increments attempt_count.
    """
    while True:
        stmt = (
            select(AnalysisJob)
            .where(AnalysisJob.status == "QUEUED")
            .order_by(AnalysisJob.requested_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        result = await session.execute(stmt)
        job = result.scalar_one_or_none()
        if not job:
            return None

        # Guard against exceeding maximum retry attempts
        if job.attempt_count >= MAX_JOB_ATTEMPTS:
            logger.warning(
                "Job %s exceeded max attempts (%d). Marking as FAILED.",
                job.id,
                job.attempt_count,
            )
            job.status = "FAILED"
            job.completed_at = datetime.now(timezone.utc)
            await session.commit()
            continue

        job.status = "PROCESSING"
        job.attempt_count += 1
        await session.commit()
        await session.refresh(job)
        logger.info("Claimed analysis job %s (attempt %d).", job.id, job.attempt_count)
        return job


async def claim_job_by_id(session: AsyncSession, job_id: uuid.UUID) -> Optional[AnalysisJob]:
    """
    Atomically claims a specific QUEUED analysis job by ID.
    Uses SELECT ... FOR UPDATE SKIP LOCKED.
    """
    stmt = (
        select(AnalysisJob)
        .where(AnalysisJob.id == job_id, AnalysisJob.status == "QUEUED")
        .with_for_update(skip_locked=True)
    )
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()
    if not job:
        return None

    if job.attempt_count >= MAX_JOB_ATTEMPTS:
        logger.warning(
            "Job %s exceeded max attempts (%d). Marking as FAILED.",
            job.id,
            job.attempt_count,
        )
        job.status = "FAILED"
        job.completed_at = datetime.now(timezone.utc)
        await session.commit()
        return None

    job.status = "PROCESSING"
    job.attempt_count += 1
    await session.commit()
    await session.refresh(job)
    logger.info("Claimed specific analysis job %s (attempt %d).", job.id, job.attempt_count)
    return job


# ---------------------------------------------------------------------------
# Job Execution Lifecycle
# ---------------------------------------------------------------------------


async def execute_job_run(
    job: AnalysisJob,
    session: AsyncSession,
    github_client: Optional[GitHubClient] = None,
    jwt_generator: Optional[Callable[[], str]] = None,
) -> AnalysisRun:
    """
    Executes an attempt for an analysis job through Stage 2 (Fetching).
    Maintains database state consistency for AnalysisJob and AnalysisRun.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)

    run = AnalysisRun(
        id=uuid.uuid4(),
        analysis_job_id=job.id,
        repository_id=job.repository_id,
        status="FETCHING",
        analyzer_version=settings.APP_VERSION,
        schema_version="1.0.0",
        started_at=now,
        created_at=now,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    client = github_client or GitHubClient()
    jwt_gen = jwt_generator or generate_app_jwt

    try:
        async with temporary_workspace() as workspace_dir:
            fetch_result = await fetch_repository_for_job(
                job=job,
                workspace_dir=workspace_dir,
                session=session,
                github_client=client,
                jwt_generator=jwt_gen,
            )
            logger.info(
                "Successfully fetched repository for job %s: %d files in %s",
                job.id,
                fetch_result.file_count,
                fetch_result.root_dir,
            )

        # Stage 2 (Fetching) is completed for this execution attempt.
        # Per docs/13_ANALYSIS_PIPELINE.md, COMPLETED is strictly reserved for Stage 8 (pipeline completion).
        # In Step 6B, subsequent stages (Stage 3 Mining -> Stage 8 Completion) are deferred to Step 6C+.
        # We do NOT falsely mark the job or run as COMPLETED because capability analysis has not run.
        # The run remains in status 'FETCHING' and the job in 'PROCESSING' (both completed_at = None)
        # awaiting Stage 3 handoff in Step 6C.
        await session.commit()
        logger.info(
            "Stage 2 (Fetching) succeeded for job %s run %s. Awaiting Stage 3 (Mining).",
            job.id,
            run.id,
        )

    except Exception as exc:
        await session.rollback()
        error_code, error_message = sanitize_failure(exc)
        logger.warning(
            "Analysis job %s failed: [%s] %s",
            job.id,
            error_code,
            error_message,
        )

        fail_time = datetime.now(timezone.utc)
        run.status = "FAILED"
        run.error_code = error_code
        run.error_message = error_message
        run.completed_at = fail_time

        job.status = "FAILED"
        job.completed_at = fail_time

        session.add(run)
        session.add(job)
        try:
            await session.commit()
        except Exception as commit_exc:
            await session.rollback()
            logger.error("Failed to commit failure state for job %s: %s", job.id, commit_exc)

    return run


# ---------------------------------------------------------------------------
# Worker Runners & CLI
# ---------------------------------------------------------------------------


async def run_worker_once(
    session_factory=None,
    job_id: Optional[uuid.UUID] = None,
    github_client: Optional[GitHubClient] = None,
    jwt_generator: Optional[Callable[[], str]] = None,
) -> Optional[AnalysisRun]:
    """
    Executes a single job from the queue (or a specified job_id).
    Returns the resulting AnalysisRun, or None if no job was claimed.
    """
    factory = session_factory or _get_session_factory()
    async with factory() as session:
        if job_id is not None:
            job = await claim_job_by_id(session, job_id)
        else:
            job = await claim_next_job(session)

        if not job:
            return None

        return await execute_job_run(
            job=job,
            session=session,
            github_client=github_client,
            jwt_generator=jwt_generator,
        )


async def worker_loop(poll_interval: float = 5.0) -> None:
    """
    Continuous worker loop polling for QUEUED jobs.
    """
    logger.info("Starting DevTwin analysis worker loop (poll interval: %.1fs)...", poll_interval)
    while True:
        try:
            run = await run_worker_once()
            if run is None:
                await asyncio.sleep(poll_interval)
        except asyncio.CancelledError:
            logger.info("Worker loop cancelled. Shutting down.")
            break
        except Exception as exc:
            logger.error("Unexpected error in worker loop: %s", exc)
            await asyncio.sleep(poll_interval)


def main():
    """
    CLI entrypoint for running the DevTwin analysis worker locally.
    Usage:
        python -m app.workers.runner --once
        python -m app.workers.runner --job-id <UUID>
        python -m app.workers.runner --poll --interval 5
    """
    parser = argparse.ArgumentParser(description="DevTwin Analysis Worker Runner")
    parser.add_argument(
        "--job-id",
        type=uuid.UUID,
        default=None,
        help="Process a specific analysis job by UUID.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Claim and process one job from the queue, then exit.",
    )
    parser.add_argument(
        "--poll",
        action="store_true",
        help="Run continuously, polling for new QUEUED jobs.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Polling interval in seconds when running with --poll (default: 5.0).",
    )

    args = parser.parse_args()

    # Configure root logging if running standalone
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    if args.job_id:
        logger.info("Running worker for single job: %s", args.job_id)
        run = asyncio.run(run_worker_once(job_id=args.job_id))
        if run:
            logger.info("Finished processing job %s with status %s", args.job_id, run.status)
        else:
            logger.warning("Job %s could not be claimed or is not QUEUED.", args.job_id)
    elif args.once:
        logger.info("Running single queue cycle...")
        run = asyncio.run(run_worker_once())
        if run:
            logger.info("Finished processing job %s with status %s", run.analysis_job_id, run.status)
        else:
            logger.info("No QUEUED jobs available.")
    else:
        # Default or --poll: run polling loop
        try:
            asyncio.run(worker_loop(poll_interval=args.interval))
        except KeyboardInterrupt:
            logger.info("Worker interrupted by user. Exiting.")


if __name__ == "__main__":
    main()
