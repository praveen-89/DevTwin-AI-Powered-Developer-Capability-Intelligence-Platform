"""
DevTwin Backend — Worker Repository Fetcher
"""

import contextlib
import io
import logging
import os
import shutil
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_job import AnalysisJob
from app.models.github_account import GitHubAccount
from app.models.project import Project
from app.models.repository import Repository
from app.services.github.auth import generate_app_jwt
from app.services.github.client import GitHubClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class FetcherError(Exception):
    """Base error for repository fetching failures."""
    def __init__(self, message: str, code: str = "FETCH_ERROR"):
        super().__init__(message)
        self.code = code


class RepositoryNotFoundError(FetcherError):
    def __init__(self, message: str = "Repository not found."):
        super().__init__(message, code="REPOSITORY_NOT_FOUND")


class RepositoryOwnershipError(FetcherError):
    def __init__(self, message: str = "Repository ownership mismatch or unowned."):
        super().__init__(message, code="REPOSITORY_UNOWNED")


class GitHubAccountDisconnectedError(FetcherError):
    def __init__(self, message: str = "GitHub account is disconnected."):
        super().__init__(message, code="ACCOUNT_DISCONNECTED")


class GitHubInstallationMissingError(FetcherError):
    def __init__(self, message: str = "GitHub App installation is missing."):
        super().__init__(message, code="INSTALLATION_MISSING")


class SecurityArchiveError(FetcherError):
    def __init__(self, message: str = "Security violation in repository archive."):
        super().__init__(message, code="SECURITY_VIOLATION")


class CorruptArchiveError(FetcherError):
    def __init__(self, message: str = "Corrupt repository archive received."):
        super().__init__(message, code="CORRUPT_ARCHIVE")


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FetchResult:
    workspace_dir: Path
    root_dir: Path
    file_count: int
    commit_sha: Optional[str] = None


# ---------------------------------------------------------------------------
# Workspace & Archive Utilities
# ---------------------------------------------------------------------------


@contextlib.asynccontextmanager
async def temporary_workspace():
    """
    Creates an isolated temporary workspace on the filesystem.
    Guarantees deterministic cleanup on both normal completion and exception.
    """
    temp_dir = tempfile.mkdtemp(prefix="devtwin_workspace_")
    path = Path(temp_dir).resolve()
    try:
        yield path
    finally:
        try:
            shutil.rmtree(path, ignore_errors=True)
            logger.debug("Cleaned up temporary workspace: %s", path)
        except Exception as e:
            logger.warning("Failed to clean up temporary workspace %s: %s", path, e)


def is_safe_tar_member(base_dir: Path, member: tarfile.TarInfo) -> bool:
    """
    Validates that a tarball member does not escape the destination directory.
    Guards against Path Traversal (Zip Slip / Tar Slip) vulnerabilities.
    """
    # Reject absolute paths
    if member.name.startswith("/") or member.name.startswith("\\"):
        return False
    if os.path.isabs(member.name):
        return False

    # Reject path traversal segments
    parts = Path(member.name).parts
    if ".." in parts:
        return False

    # Resolve target path and verify it stays strictly inside base_dir
    resolved_base = base_dir.resolve()
    target_path = (base_dir / member.name).resolve()

    try:
        if resolved_base not in target_path.parents and target_path != resolved_base:
            return False
    except Exception:
        return False

    # Check symlinks / hardlinks to ensure target does not point outside base_dir
    if member.issym() or member.islnk():
        link_target = member.linkname
        if os.path.isabs(link_target) or ".." in Path(link_target).parts:
            return False
        target_link_path = (target_path.parent / link_target).resolve()
        try:
            if resolved_base not in target_link_path.parents and target_link_path != resolved_base:
                return False
        except Exception:
            return False

    return True


# Archive extraction safety limits
MAX_EXTRACTED_MEMBERS = 10_000
MAX_EXTRACTED_BYTES = 250 * 1024 * 1024  # 250 MB
MAX_SINGLE_FILE_BYTES = 10 * 1024 * 1024  # 10 MB


def safe_extract_tar(archive_bytes: bytes, destination_dir: Path) -> Path:
    """
    Safely extracts a gzip-compressed tar archive into the destination directory.
    Validates member counts, sizes, and paths to prevent directory traversal and decompression bombs.
    Returns the repository root path inside the destination.
    """
    try:
        fileobj = io.BytesIO(archive_bytes)
        with tarfile.open(fileobj=fileobj, mode="r:gz") as tar:
            members = tar.getmembers()
            if len(members) > MAX_EXTRACTED_MEMBERS:
                raise SecurityArchiveError(
                    f"Archive exceeds maximum member count limit ({len(members)} > {MAX_EXTRACTED_MEMBERS})."
                )

            total_uncompressed = 0
            for member in members:
                if member.isfile():
                    if member.size > MAX_SINGLE_FILE_BYTES:
                        raise SecurityArchiveError(
                            f"Archive member exceeds single file size limit ({member.size} > {MAX_SINGLE_FILE_BYTES} bytes): {member.name}"
                        )
                    total_uncompressed += member.size
                    if total_uncompressed > MAX_EXTRACTED_BYTES:
                        raise SecurityArchiveError(
                            f"Archive total uncompressed bytes exceed limit ({total_uncompressed} > {MAX_EXTRACTED_BYTES} bytes)."
                        )

                if not is_safe_tar_member(destination_dir, member):
                    logger.error("Blocked unsafe archive member: %s", member.name)
                    raise SecurityArchiveError(f"Archive contains illegal path traversal: {member.name}")

            # Safe to extract
            tar.extractall(path=destination_dir)
    except SecurityArchiveError:
        raise
    except tarfile.TarError as e:
        logger.error("Tar extraction error: %s", type(e).__name__)
        raise CorruptArchiveError("Failed to extract repository archive.") from e
    except Exception as e:
        logger.error("Unexpected archive extraction error: %s", type(e).__name__)
        raise CorruptArchiveError("Failed to unpack repository archive.") from e

    # GitHub archives extract into a single top-level directory: <owner>-<repo>-<sha>/
    extracted_items = [p for p in destination_dir.iterdir() if p.is_dir()]
    if len(extracted_items) == 1:
        return extracted_items[0]
    return destination_dir


# ---------------------------------------------------------------------------
# Fetcher Core
# ---------------------------------------------------------------------------


async def fetch_repository_for_job(
    job: AnalysisJob,
    workspace_dir: Path,
    session: AsyncSession,
    github_client: Optional[GitHubClient] = None,
    jwt_generator: Callable[[], str] = generate_app_jwt,
) -> FetchResult:
    """
    Fetches repository contents for an analysis job using trusted persisted records
    and short-lived GitHub App installation credentials.

    Never logs or persists the access token.
    Validates repository and developer ownership.
    Extracts into the provided workspace_dir.
    """
    client = github_client or GitHubClient()

    # 1. Resolve Repository
    repo_result = await session.execute(
        select(Repository).where(Repository.id == job.repository_id)
    )
    repo = repo_result.scalar_one_or_none()
    if not repo:
        raise RepositoryNotFoundError(f"Repository {job.repository_id} not found.")

    if not repo.project_id:
        raise RepositoryOwnershipError(f"Repository {repo.id} has no associated project.")

    # 2. Resolve Project & Developer
    proj_result = await session.execute(
        select(Project).where(Project.id == repo.project_id)
    )
    project = proj_result.scalar_one_or_none()
    if not project or not project.developer_id:
        raise RepositoryOwnershipError(f"Project {repo.project_id} not found or unowned.")

    developer_id = project.developer_id

    # 3. Resolve GitHub Account
    gh_result = await session.execute(
        select(GitHubAccount).where(GitHubAccount.developer_id == developer_id)
    )
    gh_account = gh_result.scalar_one_or_none()
    if not gh_account or gh_account.disconnected_at is not None:
        raise GitHubAccountDisconnectedError("Developer GitHub account is not connected or has been disconnected.")

    if not gh_account.installation_id:
        raise GitHubInstallationMissingError("Developer GitHub account has no associated GitHub App installation.")

    # 4. Generate App JWT & Ephemeral Installation Token
    app_jwt = jwt_generator()
    installation_token = await client.create_installation_access_token(
        installation_id=gh_account.installation_id,
        app_jwt=app_jwt,
    )

    try:
        # 5. Resolve trusted repo metadata from GitHub using installation token
        repo_data = await client.get_installation_repository(
            github_repo_id=repo.github_repo_id,
            installation_token=installation_token,
        )

        owner = repo_data.get("owner", {}).get("login") or repo.owner_login
        repo_name = repo_data.get("name") or repo.name
        default_branch = repo_data.get("default_branch") or repo.default_branch or "main"

        # 6. Download Archive
        archive_bytes = await client.download_repository_archive(
            owner=owner,
            repo=repo_name,
            ref=default_branch,
            installation_token=installation_token,
        )
    finally:
        # Discard token from memory immediately
        del installation_token

    # 7. Extract into workspace safely
    root_dir = safe_extract_tar(archive_bytes, workspace_dir)
    file_count = sum(1 for _ in root_dir.rglob("*") if _.is_file())

    return FetchResult(
        workspace_dir=workspace_dir,
        root_dir=root_dir,
        file_count=file_count,
    )
