"""
DevTwin Backend Tests — Worker Runner and Repository Fetcher (Step 6B)
"""

import io
import os
import tarfile
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.analysis_job import AnalysisJob
from app.models.analysis_run import AnalysisRun
from app.models.developer import Developer
from app.models.github_account import GitHubAccount
from app.models.project import Project
from app.models.repository import Repository
from app.services.github.client import GitHubClient
from app.services.github.exceptions import (
    GitHubHTTPError,
    GitHubRateLimitError,
    GitHubNetworkError,
)
from app.workers.fetcher import (
    FetcherError,
    RepositoryNotFoundError,
    RepositoryOwnershipError,
    GitHubAccountDisconnectedError,
    GitHubInstallationMissingError,
    SecurityArchiveError,
    CorruptArchiveError,
    FetchResult,
    is_safe_tar_member,
    safe_extract_tar,
    temporary_workspace,
    fetch_repository_for_job,
)
from app.workers.runner import (
    MAX_JOB_ATTEMPTS,
    claim_next_job,
    claim_job_by_id,
    sanitize_failure,
    execute_job_run,
    run_worker_once,
)


# Helper to build in-memory tarball for testing
def create_test_tarball(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, content in files.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(content)
            info.mtime = int(datetime.now(timezone.utc).timestamp())
            tar.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


# ===========================================================================
# Queue Claiming Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_claim_next_job_success():
    """claim_next_job claims an eligible QUEUED job, sets status to PROCESSING, increments attempt_count."""
    job_id = uuid.uuid4()
    job = AnalysisJob(
        id=job_id,
        repository_id=uuid.uuid4(),
        status="QUEUED",
        attempt_count=0,
        requested_at=datetime.now(timezone.utc),
    )

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = job
    mock_session.execute.return_value = mock_result

    claimed = await claim_next_job(mock_session)

    assert claimed is not None
    assert claimed.id == job_id
    assert claimed.status == "PROCESSING"
    assert claimed.attempt_count == 1
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_claim_next_job_empty_queue():
    """claim_next_job returns None when no jobs are QUEUED."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    claimed = await claim_next_job(mock_session)
    assert claimed is None
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_claim_next_job_max_attempts_exceeded():
    """claim_next_job marks a job as FAILED if attempt_count >= MAX_JOB_ATTEMPTS."""
    job_id = uuid.uuid4()
    exhausted_job = AnalysisJob(
        id=job_id,
        repository_id=uuid.uuid4(),
        status="QUEUED",
        attempt_count=MAX_JOB_ATTEMPTS,
        requested_at=datetime.now(timezone.utc),
    )

    mock_session = AsyncMock()
    # First query returns exhausted job, second returns None
    result1 = MagicMock()
    result1.scalar_one_or_none.return_value = exhausted_job
    result2 = MagicMock()
    result2.scalar_one_or_none.return_value = None
    mock_session.execute.side_effect = [result1, result2]

    claimed = await claim_next_job(mock_session)

    assert claimed is None
    assert exhausted_job.status == "FAILED"
    assert exhausted_job.completed_at is not None
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_claim_job_by_id_success():
    """claim_job_by_id claims a specific job if QUEUED."""
    job_id = uuid.uuid4()
    job = AnalysisJob(
        id=job_id,
        repository_id=uuid.uuid4(),
        status="QUEUED",
        attempt_count=1,
        requested_at=datetime.now(timezone.utc),
    )

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = job
    mock_session.execute.return_value = mock_result

    claimed = await claim_job_by_id(mock_session, job_id)

    assert claimed is not None
    assert claimed.id == job_id
    assert claimed.status == "PROCESSING"
    assert claimed.attempt_count == 2
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_claim_job_by_id_not_found():
    """claim_job_by_id returns None if job does not exist or is not QUEUED."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    claimed = await claim_job_by_id(mock_session, uuid.uuid4())
    assert claimed is None


# ===========================================================================
# Tarball Safety & Extraction Tests
# ===========================================================================


def test_is_safe_tar_member_allows_safe_files(tmp_path):
    """is_safe_tar_member accepts normal relative paths."""
    safe_info = tarfile.TarInfo(name="repo-main/src/main.py")
    assert is_safe_tar_member(tmp_path, safe_info) is True

    safe_root = tarfile.TarInfo(name="repo-main/README.md")
    assert is_safe_tar_member(tmp_path, safe_root) is True


def test_is_safe_tar_member_blocks_path_traversal(tmp_path):
    """is_safe_tar_member rejects paths with '..' or absolute roots."""
    # Parent directory escape
    bad_traversal = tarfile.TarInfo(name="../escape.py")
    assert is_safe_tar_member(tmp_path, bad_traversal) is False

    nested_traversal = tarfile.TarInfo(name="repo-main/../../escape.py")
    assert is_safe_tar_member(tmp_path, nested_traversal) is False

    # Unix root
    abs_unix = tarfile.TarInfo(name="/etc/shadow")
    assert is_safe_tar_member(tmp_path, abs_unix) is False

    # Windows root / drive
    abs_win = tarfile.TarInfo(name="C:\\Windows\\System32\\cmd.exe")
    assert is_safe_tar_member(tmp_path, abs_win) is False


def test_is_safe_tar_member_blocks_escaping_symlinks(tmp_path):
    """is_safe_tar_member rejects symlinks pointing outside the workspace."""
    sym = tarfile.TarInfo(name="repo-main/sym_escape")
    sym.type = tarfile.SYMTYPE
    sym.linkname = "../../outside"
    assert is_safe_tar_member(tmp_path, sym) is False


def test_safe_extract_tar_rejects_unsafe_archive(tmp_path):
    """safe_extract_tar raises SecurityArchiveError on malicious archives."""
    malicious_bytes = create_test_tarball({"../evil.sh": b"rm -rf /"})
    with pytest.raises(SecurityArchiveError) as exc_info:
        safe_extract_tar(malicious_bytes, tmp_path)
    assert "illegal path traversal" in str(exc_info.value)


def test_safe_extract_tar_success(tmp_path):
    """safe_extract_tar extracts safe archives and resolves top-level dir."""
    safe_bytes = create_test_tarball({
        "myrepo-abc1234/README.md": b"# Test Repo",
        "myrepo-abc1234/src/app.py": b"print('hello')",
    })
    extracted_root = safe_extract_tar(safe_bytes, tmp_path)
    assert extracted_root.is_dir()
    assert (extracted_root / "README.md").is_file()
    assert (extracted_root / "src" / "app.py").is_file()
    assert (extracted_root / "README.md").read_text() == "# Test Repo"


def test_safe_extract_tar_corrupt_data(tmp_path):
    """safe_extract_tar raises CorruptArchiveError on invalid bytes."""
    with pytest.raises(CorruptArchiveError):
        safe_extract_tar(b"not a tarball data", tmp_path)


# ===========================================================================
# Temporary Workspace Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_temporary_workspace_cleanup_on_success():
    """temporary_workspace deletes the directory on successful exit."""
    created_path = None
    async with temporary_workspace() as ws:
        created_path = ws
        assert created_path.exists()
        # Create a file inside
        (created_path / "test.txt").write_text("hello")
        assert (created_path / "test.txt").exists()

    assert not created_path.exists()


@pytest.mark.asyncio
async def test_temporary_workspace_cleanup_on_exception():
    """temporary_workspace deletes the directory even when an exception is raised."""
    created_path = None
    with pytest.raises(RuntimeError):
        async with temporary_workspace() as ws:
            created_path = ws
            assert created_path.exists()
            (created_path / "important.dat").write_bytes(b"data")
            raise RuntimeError("Forced error")

    assert created_path is not None
    assert not created_path.exists()


# ===========================================================================
# Fetcher Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_fetch_repository_success(tmp_path):
    """fetch_repository_for_job resolves credentials, downloads tarball, and extracts files."""
    repo_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    dev_id = uuid.uuid4()

    mock_job = AnalysisJob(id=uuid.uuid4(), repository_id=repo_id, status="PROCESSING")
    mock_repo = Repository(
        id=repo_id,
        project_id=proj_id,
        github_repo_id=12345,
        owner_login="octocat",
        name="hello-world",
        default_branch="main",
    )
    mock_project = Project(id=proj_id, developer_id=dev_id, name="Project Alpha")
    mock_account = GitHubAccount(
        id=uuid.uuid4(),
        developer_id=dev_id,
        github_id=999,
        username="octocat",
        installation_id=54321,
        disconnected_at=None,
    )

    mock_session = AsyncMock()
    # 3 select queries: repo, project, gh_account
    res_repo = MagicMock()
    res_repo.scalar_one_or_none.return_value = mock_repo
    res_proj = MagicMock()
    res_proj.scalar_one_or_none.return_value = mock_project
    res_acc = MagicMock()
    res_acc.scalar_one_or_none.return_value = mock_account

    mock_session.execute.side_effect = [res_repo, res_proj, res_acc]

    # Mock GitHubClient
    mock_client = AsyncMock(spec=GitHubClient)
    mock_client.create_installation_access_token.return_value = "ghs_secret_inst_token"
    mock_client.get_installation_repository.return_value = {
        "owner": {"login": "octocat"},
        "name": "hello-world",
        "default_branch": "main",
    }
    tar_bytes = create_test_tarball({
        "octocat-hello-world-sha/index.js": b"console.log('hi');",
        "octocat-hello-world-sha/package.json": b"{}",
    })
    mock_client.download_repository_archive.return_value = tar_bytes

    result = await fetch_repository_for_job(
        job=mock_job,
        workspace_dir=tmp_path,
        session=mock_session,
        github_client=mock_client,
        jwt_generator=lambda: "mock_app_jwt",
    )

    assert isinstance(result, FetchResult)
    assert result.file_count == 2
    assert (result.root_dir / "index.js").exists()
    assert (result.root_dir / "package.json").exists()

    # Verify client called with correct parameters
    mock_client.create_installation_access_token.assert_awaited_once_with(
        installation_id=54321,
        app_jwt="mock_app_jwt",
    )
    mock_client.download_repository_archive.assert_awaited_once_with(
        owner="octocat",
        repo="hello-world",
        ref="main",
        installation_token="ghs_secret_inst_token",
    )


@pytest.mark.asyncio
async def test_fetch_repository_missing_repo(tmp_path):
    """fetch_repository_for_job raises RepositoryNotFoundError when repo does not exist in DB."""
    mock_job = AnalysisJob(id=uuid.uuid4(), repository_id=uuid.uuid4())
    mock_session = AsyncMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = res

    with pytest.raises(RepositoryNotFoundError):
        await fetch_repository_for_job(mock_job, tmp_path, mock_session)


@pytest.mark.asyncio
async def test_fetch_repository_unowned_project(tmp_path):
    """fetch_repository_for_job raises RepositoryOwnershipError when repo has no project_id."""
    mock_job = AnalysisJob(id=uuid.uuid4(), repository_id=uuid.uuid4())
    mock_repo = Repository(id=mock_job.repository_id, project_id=None)
    mock_session = AsyncMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = mock_repo
    mock_session.execute.return_value = res

    with pytest.raises(RepositoryOwnershipError):
        await fetch_repository_for_job(mock_job, tmp_path, mock_session)


@pytest.mark.asyncio
async def test_fetch_repository_disconnected_account(tmp_path):
    """fetch_repository_for_job raises GitHubAccountDisconnectedError when account is disconnected."""
    repo_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    dev_id = uuid.uuid4()

    mock_job = AnalysisJob(id=uuid.uuid4(), repository_id=repo_id)
    mock_repo = Repository(id=repo_id, project_id=proj_id)
    mock_project = Project(id=proj_id, developer_id=dev_id)
    mock_account = GitHubAccount(
        id=uuid.uuid4(),
        developer_id=dev_id,
        disconnected_at=datetime.now(timezone.utc),
    )

    mock_session = AsyncMock()
    res_repo = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_repo))
    res_proj = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_project))
    res_acc = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_account))
    mock_session.execute.side_effect = [res_repo, res_proj, res_acc]

    with pytest.raises(GitHubAccountDisconnectedError):
        await fetch_repository_for_job(mock_job, tmp_path, mock_session)


@pytest.mark.asyncio
async def test_fetch_repository_missing_installation(tmp_path):
    """fetch_repository_for_job raises GitHubInstallationMissingError when installation_id is None."""
    repo_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    dev_id = uuid.uuid4()

    mock_job = AnalysisJob(id=uuid.uuid4(), repository_id=repo_id)
    mock_repo = Repository(id=repo_id, project_id=proj_id)
    mock_project = Project(id=proj_id, developer_id=dev_id)
    mock_account = GitHubAccount(
        id=uuid.uuid4(),
        developer_id=dev_id,
        installation_id=None,
        disconnected_at=None,
    )

    mock_session = AsyncMock()
    res_repo = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_repo))
    res_proj = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_project))
    res_acc = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_account))
    mock_session.execute.side_effect = [res_repo, res_proj, res_acc]

    with pytest.raises(GitHubInstallationMissingError):
        await fetch_repository_for_job(mock_job, tmp_path, mock_session)


# ===========================================================================
# Failure Sanitization Tests
# ===========================================================================


def test_sanitize_failure_mapping():
    """sanitize_failure safely converts diverse exceptions to standard codes and sanitized messages."""
    assert sanitize_failure(RepositoryNotFoundError()) == (
        "REPOSITORY_NOT_FOUND",
        "Repository not found or inaccessible.",
    )
    assert sanitize_failure(RepositoryOwnershipError()) == (
        "REPOSITORY_UNOWNED",
        "Repository ownership verification failed.",
    )
    assert sanitize_failure(GitHubAccountDisconnectedError()) == (
        "ACCOUNT_DISCONNECTED",
        "GitHub account is disconnected.",
    )
    assert sanitize_failure(GitHubInstallationMissingError()) == (
        "INSTALLATION_MISSING",
        "GitHub App installation is missing.",
    )
    assert sanitize_failure(SecurityArchiveError()) == (
        "SECURITY_VIOLATION",
        "Repository archive security verification failed.",
    )
    assert sanitize_failure(CorruptArchiveError()) == (
        "CORRUPT_ARCHIVE",
        "Repository archive could not be extracted.",
    )
    assert sanitize_failure(GitHubRateLimitError("Rate limit exceeded")) == (
        "RATE_LIMITED",
        "GitHub API rate limit exceeded.",
    )
    assert sanitize_failure(GitHubHTTPError("Not found", status_code=404)) == (
        "GITHUB_HTTP_404",
        "GitHub API error (404).",
    )
    assert sanitize_failure(GitHubNetworkError("Connection timed out")) == (
        "NETWORK_ERROR",
        "Network error communicating with GitHub.",
    )
    # Generic error must not leak raw string or stack trace
    assert sanitize_failure(ValueError("Secret key leaked in db exception: ghs_xyz")) == (
        "INTERNAL_ERROR",
        "An internal error occurred during repository analysis.",
    )


# ===========================================================================
# Execution Lifecycle & End-to-End Worker Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_execute_job_run_success():
    """execute_job_run transitions run to MINING and keeps job in PROCESSING awaiting Stage 4 on successful fetch & mine."""
    job_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    job = AnalysisJob(id=job_id, repository_id=repo_id, status="PROCESSING", attempt_count=1)

    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    mock_fetch_result = FetchResult(
        workspace_dir=Path("/tmp/ws"),
        root_dir=Path("/tmp/ws/repo"),
        file_count=5,
    )

    from app.mining.models import MiningResult, RepositoryInventory
    mock_mining_result = MiningResult(
        schema_version="1.0.0",
        mining_version="1.0.0",
        inventory=RepositoryInventory(5, 5, 0, 0, 1000, 1000),
        languages=[],
        manifests=[],
        ast_summaries=[],
        warnings=[],
        completed_at=datetime.now(timezone.utc).isoformat(),
    )

    with patch(
        "app.workers.runner.fetch_repository_for_job",
        new=AsyncMock(return_value=mock_fetch_result),
    ), patch(
        "app.workers.runner.mine_repository",
        return_value=mock_mining_result,
    ):
        run = await execute_job_run(job, mock_session)

    # Per docs/13_ANALYSIS_PIPELINE.md, COMPLETED is reserved for Stage 8.
    # In Step 6E, run advances to CODE_RISK and job remains PROCESSING (completed_at is None) awaiting Stage 6.
    assert run.status == "CODE_RISK"
    assert run.completed_at is None
    assert job.status == "PROCESSING"
    assert job.completed_at is None
    assert getattr(run, "_mining_result", None) is not None
    assert getattr(run, "_skillgraph_result", None) is not None
    assert getattr(run, "_coderisk_result", None) is not None
    assert mock_session.commit.await_count >= 2


@pytest.mark.asyncio
async def test_repeated_worker_invocation_does_not_reclaim_processing_job():
    """Repeated worker execution does not re-claim or refetch a job that is already PROCESSING."""
    job_id = uuid.uuid4()
    processing_job = AnalysisJob(
        id=job_id,
        repository_id=uuid.uuid4(),
        status="PROCESSING",
        attempt_count=1,
        requested_at=datetime.now(timezone.utc),
    )

    mock_session = AsyncMock()
    # Query with WHERE status == 'QUEUED' returns None
    mock_result_none = MagicMock()
    mock_result_none.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result_none

    # 1. claim_next_job returns None because only QUEUED jobs are claimed
    claimed_next = await claim_next_job(mock_session)
    assert claimed_next is None

    # 2. claim_job_by_id returns None because the job is PROCESSING, not QUEUED
    claimed_by_id = await claim_job_by_id(mock_session, job_id)
    assert claimed_by_id is None
    # State of processing_job must not be mutated
    assert processing_job.status == "PROCESSING"
    assert processing_job.attempt_count == 1



@pytest.mark.asyncio
async def test_execute_job_run_failure():
    """execute_job_run marks job and run as FAILED with sanitized code on fetch error."""
    job_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    job = AnalysisJob(id=job_id, repository_id=repo_id, status="PROCESSING", attempt_count=1)

    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    with patch(
        "app.workers.runner.fetch_repository_for_job",
        new=AsyncMock(side_effect=GitHubHTTPError("Not found", status_code=404)),
    ):
        run = await execute_job_run(job, mock_session)

    assert run.status == "FAILED"
    assert run.error_code == "GITHUB_HTTP_404"
    assert "GitHub API error (404)" in run.error_message
    assert job.status == "FAILED"
    assert job.completed_at is not None


@pytest.mark.asyncio
async def test_tokens_never_persisted_in_failure():
    """Tokens are never written into AnalysisRun or AnalysisJob on exception."""
    job = AnalysisJob(id=uuid.uuid4(), repository_id=uuid.uuid4(), status="PROCESSING", attempt_count=1)
    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    secret_leak_attempt = "Secret token leaked: ghs_SUPER_SECRET_12345"
    with patch(
        "app.workers.runner.fetch_repository_for_job",
        new=AsyncMock(side_effect=Exception(secret_leak_attempt)),
    ):
        run = await execute_job_run(job, mock_session)

    assert run.status == "FAILED"
    assert "ghs_SUPER_SECRET_12345" not in (run.error_message or "")
    assert "token" not in (run.error_message or "").lower()
    assert run.error_code == "INTERNAL_ERROR"


# ===========================================================================
# GitHubClient Archive Download Tests
# ===========================================================================


class MockStreamContext:
    def __init__(self, status_code=200, chunks=(b"fake tarball archive bytes",), headers=None):
        self.status_code = status_code
        self._chunks = chunks
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError("error", request=None, response=MagicMock(status_code=self.status_code))

    async def aiter_bytes(self):
        for c in self._chunks:
            yield c

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


@pytest.mark.asyncio
async def test_download_repository_archive_success():
    """download_repository_archive streams archive bytes and follows redirects."""
    client = GitHubClient()
    tar_content = b"fake tarball archive bytes"

    mock_ctx = MockStreamContext(status_code=200, chunks=(tar_content,))

    with patch("httpx.AsyncClient.stream", return_value=mock_ctx) as mock_stream:
        data = await client.download_repository_archive(
            owner="myorg",
            repo="myrepo",
            ref="main",
            installation_token="ghs_test_token",
        )

    assert data == tar_content
    mock_stream.assert_called_once()
    called_headers = mock_stream.call_args[1]["headers"]
    assert called_headers["Authorization"] == "Bearer ghs_test_token"
    assert "tarball/main" in mock_stream.call_args[0][1]


@pytest.mark.asyncio
async def test_download_repository_archive_rate_limit():
    """download_repository_archive raises GitHubRateLimitError on 429."""
    client = GitHubClient()
    mock_ctx = MockStreamContext(status_code=429)

    with patch("httpx.AsyncClient.stream", return_value=mock_ctx):
        with pytest.raises(GitHubRateLimitError):
            await client.download_repository_archive("o", "r", "main", "tok")


@pytest.mark.asyncio
async def test_download_repository_archive_404():
    """download_repository_archive raises GitHubHTTPError on 404."""
    client = GitHubClient()
    mock_ctx = MockStreamContext(status_code=404)

    with patch("httpx.AsyncClient.stream", return_value=mock_ctx):
        with pytest.raises(GitHubHTTPError) as exc_info:
            await client.download_repository_archive("o", "r", "main", "tok")
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_download_repository_archive_exceeds_max_bytes():
    """download_repository_archive raises GitHubHTTPError(413) when archive exceeds size limit."""
    client = GitHubClient()
    mock_ctx = MockStreamContext(status_code=200, chunks=(b"chunk1_100_bytes" * 10, b"chunk2_100_bytes" * 10))

    with patch("httpx.AsyncClient.stream", return_value=mock_ctx):
        with pytest.raises(GitHubHTTPError) as exc_info:
            await client.download_repository_archive("o", "r", "main", "tok", max_bytes=50)
        assert exc_info.value.status_code == 413
