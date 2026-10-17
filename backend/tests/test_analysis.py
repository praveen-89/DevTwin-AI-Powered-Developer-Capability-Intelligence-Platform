"""
DevTwin Backend Tests — Analysis Pipeline API
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.api.dependencies.auth import get_current_developer
from app.db.connection import get_db_session
from app.models.developer import Developer
from app.models.project import Project
from app.models.repository import Repository
from app.models.analysis_job import AnalysisJob
from app.models.analysis_run import AnalysisRun


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def mock_developer():
    return Developer(id=uuid.uuid4(), auth_user_id=uuid.uuid4())


# ===========================================================================
# POST /analysis/jobs Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_submit_analysis_job_unauthenticated(app):
    """POST /analysis/jobs without Auth returns 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/analysis/jobs", json={"repository_id": str(uuid.uuid4())})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_submit_analysis_job_success(app, mock_developer):
    """POST /analysis/jobs creates and returns a QUEUED job for an owned repository."""
    repo_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    mock_repo = Repository(
        id=repo_id,
        project_id=proj_id,
        github_repo_id=101,
        owner_login="owner",
        name="test-repo",
        full_name="owner/test-repo",
        url="https://github.com/owner/test-repo",
        default_branch="main",
        visibility="public",
        synced_at=None,
        created_at=now,
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_repo
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/analysis/jobs", json={"repository_id": str(repo_id)})

    assert response.status_code == 201
    data = response.json()
    assert "job_id" in data
    assert "id" in data
    assert data["job_id"] == data["id"]
    assert data["status"] == "QUEUED"

    # Verify session calls
    mock_session.add.assert_called_once()
    added_job = mock_session.add.call_args[0][0]
    assert isinstance(added_job, AnalysisJob)
    assert added_job.repository_id == repo_id
    assert added_job.status == "QUEUED"
    assert added_job.attempt_count == 0
    mock_session.commit.assert_awaited_once()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_submit_analysis_job_nonexistent_repository(app, mock_developer):
    """POST /analysis/jobs returns 404 when repository does not exist."""
    random_repo_id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/analysis/jobs", json={"repository_id": str(random_repo_id)})

    assert response.status_code == 404
    assert "Repository not found or not owned by developer." in response.json()["detail"]
    mock_session.add.assert_not_called()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_submit_analysis_job_unowned_repository(app, mock_developer):
    """POST /analysis/jobs returns 404 when repository belongs to another developer."""
    repo_id = uuid.uuid4()

    mock_session = AsyncMock()
    # Query filters Project.developer_id == developer.id, returning None for another dev
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/analysis/jobs", json={"repository_id": str(repo_id)})

    assert response.status_code == 404
    assert "Repository not found or not owned by developer." in response.json()["detail"]
    mock_session.add.assert_not_called()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_submit_analysis_job_extra_fields_rejected(app, mock_developer):
    """POST /analysis/jobs strictly rejects extra client-supplied fields."""
    app.dependency_overrides[get_current_developer] = lambda: mock_developer

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/analysis/jobs",
            json={
                "repository_id": str(uuid.uuid4()),
                "status": "COMPLETED",
                "attempt_count": 5,
            },
        )

    assert response.status_code == 422

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_submit_analysis_job_commit_failure_returns_500(app, mock_developer):
    """POST /analysis/jobs rolls back and returns 500 when database commit fails."""
    repo_id = uuid.uuid4()
    proj_id = uuid.uuid4()

    mock_repo = Repository(
        id=repo_id,
        project_id=proj_id,
        github_repo_id=102,
        owner_login="owner",
        name="fail-repo",
        full_name="owner/fail-repo",
        url="https://github.com/owner/fail-repo",
        default_branch="main",
        visibility="public",
        synced_at=None,
        created_at=datetime.now(timezone.utc),
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_repo
    mock_session.execute.return_value = mock_result
    mock_session.commit.side_effect = Exception("DB disk failure")

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/analysis/jobs", json={"repository_id": str(repo_id)})

    assert response.status_code == 500
    assert "Failed to submit analysis job." in response.json()["detail"]
    mock_session.rollback.assert_awaited_once()

    app.dependency_overrides.clear()


# ===========================================================================
# GET /analysis/jobs/{id} Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_get_analysis_job_unauthenticated(app):
    """GET /analysis/jobs/{id} without Auth returns 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(f"/analysis/jobs/{uuid.uuid4()}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_analysis_job_owned_success(app, mock_developer):
    """GET /analysis/jobs/{id} returns job metadata when owned."""
    job_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    mock_job = AnalysisJob(
        id=job_id,
        repository_id=repo_id,
        status="PROCESSING",
        attempt_count=1,
        requested_at=now,
        completed_at=None,
    )

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_job
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(f"/analysis/jobs/{job_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(job_id)
    assert data["job_id"] == str(job_id)
    assert data["repository_id"] == str(repo_id)
    assert data["status"] == "PROCESSING"
    assert data["attempt_count"] == 1
    assert data["completed_at"] is None
    assert "requested_at" in data

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_analysis_job_nonexistent_returns_404(app, mock_developer):
    """GET /analysis/jobs/{id} returns 404 when job does not exist."""
    random_job_id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(f"/analysis/jobs/{random_job_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Analysis job not found."

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_analysis_job_other_developer_returns_404(app, mock_developer):
    """GET /analysis/jobs/{id} returns 404 when job belongs to another developer."""
    job_id = uuid.uuid4()

    mock_session = AsyncMock()
    # Ownership join returns None for other developer
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(f"/analysis/jobs/{job_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Analysis job not found."

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_analysis_job_db_error_returns_500(app, mock_developer):
    """GET /analysis/jobs/{id} returns 500 when database fails."""
    job_id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_session.execute.side_effect = Exception("DB read error")

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(f"/analysis/jobs/{job_id}")

    assert response.status_code == 500
    assert "Failed to fetch analysis job." in response.json()["detail"]

    app.dependency_overrides.clear()


# ===========================================================================
# GET /analysis/jobs/{id}/runs Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_list_job_runs_unauthenticated(app):
    """GET /analysis/jobs/{id}/runs without Auth returns 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(f"/analysis/jobs/{uuid.uuid4()}/runs")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_job_runs_empty_success(app, mock_developer):
    """GET /analysis/jobs/{id}/runs returns empty list when no runs have been executed."""
    job_id = uuid.uuid4()
    mock_job = AnalysisJob(id=job_id, repository_id=uuid.uuid4(), status="QUEUED")

    mock_session = AsyncMock()
    # First query validates job ownership, second fetches runs
    mock_job_result = MagicMock()
    mock_job_result.scalar_one_or_none.return_value = mock_job

    mock_runs_result = MagicMock()
    mock_runs_result.scalars().all.return_value = []

    mock_session.execute.side_effect = [mock_job_result, mock_runs_result]

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(f"/analysis/jobs/{job_id}/runs")

    assert response.status_code == 200
    assert response.json() == []

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_job_runs_with_attempts_success(app, mock_developer):
    """GET /analysis/jobs/{id}/runs returns execution attempts for owned job."""
    job_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    run_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    mock_job = AnalysisJob(id=job_id, repository_id=repo_id, status="COMPLETED")
    mock_run = AnalysisRun(
        id=run_id,
        analysis_job_id=job_id,
        repository_id=repo_id,
        status="COMPLETED",
        analyzer_version="1.0.0",
        schema_version="1.0.0",
        error_code=None,
        error_message=None,
        started_at=now,
        completed_at=now,
        created_at=now,
    )

    mock_session = AsyncMock()
    mock_job_result = MagicMock()
    mock_job_result.scalar_one_or_none.return_value = mock_job

    mock_runs_result = MagicMock()
    mock_runs_result.scalars().all.return_value = [mock_run]

    mock_session.execute.side_effect = [mock_job_result, mock_runs_result]

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(f"/analysis/jobs/{job_id}/runs")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(run_id)
    assert data[0]["analysis_job_id"] == str(job_id)
    assert data[0]["status"] == "COMPLETED"
    assert data[0]["analyzer_version"] == "1.0.0"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_job_runs_unowned_job_returns_404(app, mock_developer):
    """GET /analysis/jobs/{id}/runs returns 404 if job belongs to another developer."""
    job_id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_job_result = MagicMock()
    mock_job_result.scalar_one_or_none.return_value = None  # Not found or unowned
    mock_session.execute.return_value = mock_job_result

    app.dependency_overrides[get_current_developer] = lambda: mock_developer
    async def override_get_db_session():
        yield mock_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(f"/analysis/jobs/{job_id}/runs")

    assert response.status_code == 404
    assert response.json()["detail"] == "Analysis job not found."

    app.dependency_overrides.clear()
