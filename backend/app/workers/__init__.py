"""
DevTwin Backend — Background Workers Package
"""

from app.workers.fetcher import (
    FetcherError,
    RepositoryNotFoundError,
    RepositoryOwnershipError,
    GitHubAccountDisconnectedError,
    GitHubInstallationMissingError,
    SecurityArchiveError,
    CorruptArchiveError,
    FetchResult,
    temporary_workspace,
    fetch_repository_for_job,
)
def __getattr__(name: str):
    if name in (
        "claim_next_job",
        "claim_job_by_id",
        "execute_job_run",
        "process_job",
        "run_worker_once",
    ):
        import app.workers.runner as runner_mod
        return getattr(runner_mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "FetcherError",
    "RepositoryNotFoundError",
    "RepositoryOwnershipError",
    "GitHubAccountDisconnectedError",
    "GitHubInstallationMissingError",
    "SecurityArchiveError",
    "CorruptArchiveError",
    "FetchResult",
    "temporary_workspace",
    "fetch_repository_for_job",
    "claim_next_job",
    "claim_job_by_id",
    "execute_job_run",
    "process_job",
    "run_worker_once",
]
