"""
DevTwin Phase 14 — Evaluation Runner.

Drives the EXISTING analysis pipeline, end to end, exactly the way a normal
authenticated user would (ADR-007: GitHub OAuth + repository selection is
the only ingestion mechanism for Minor scope). This script does NOT clone
repositories, call GitHub directly, or bypass the REST API for ingestion —
every repository is registered and analyzed through the backend's own
`/repositories` and `/analysis/jobs` endpoints.

It does, however, read the database directly (read-only) to attach
observation/evidence/capability/risk_finding counts to each result record,
because no REST endpoint currently exposes raw pipeline counts. This does
not duplicate or alter any pipeline/scoring logic — it is a passive count.

Usage
-----
    python scripts/evaluation/run_evaluation.py --dataset scripts/evaluation/dataset.md

Required environment
---------------------
    DEVTWIN_API_BASE_URL   e.g. http://localhost:8000
    DEVTWIN_API_TOKEN      a valid Supabase access token (JWT) for the
                            developer whose GitHub App installation covers
                            the repositories being evaluated.
    DATABASE_URL           same Postgres connection string the backend uses
                            (only used for read-only result counting).

Safety / idempotency
---------------------
- Never logs DEVTWIN_API_TOKEN, DATABASE_URL, or any header/credential value.
- Before submitting a new analysis job for a repository, checks
  GET /repositories/{id}/skillgraph: if it already resolves a non-null
  analysis_run_id (i.e. a COMPLETED run exists), the existing run is reused
  and no duplicate job is submitted.
- A repository that fails analysis (job/run status FAILED or TIMEOUT) is
  recorded as such; the run continues to the next repository rather than
  aborting the whole evaluation sweep.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx

logger = logging.getLogger("devtwin.evaluation.runner")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

EVAL_PROJECT_NAME = "Phase14-Evaluation"
POLL_INTERVAL_SECONDS = 5
POLL_TIMEOUT_SECONDS = 600  # 10 minutes per repository


class EvaluationError(Exception):
    """Raised for unrecoverable configuration problems (not per-repo failures)."""


@dataclass
class RepoResult:
    full_name: str
    repository_id: Optional[str] = None
    github_repo_id: Optional[int] = None
    job_id: Optional[str] = None
    run_id: Optional[str] = None
    run_status: Optional[str] = None
    reused_existing_run: bool = False
    wall_clock_seconds: Optional[float] = None
    observation_count: Optional[int] = None
    evidence_count: Optional[int] = None
    capability_count: Optional[int] = None
    risk_finding_count: Optional[int] = None
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "full_name": self.full_name,
            "repository_id": self.repository_id,
            "github_repo_id": self.github_repo_id,
            "job_id": self.job_id,
            "run_id": self.run_id,
            "run_status": self.run_status,
            "reused_existing_run": self.reused_existing_run,
            "wall_clock_seconds": self.wall_clock_seconds,
            "observation_count": self.observation_count,
            "evidence_count": self.evidence_count,
            "capability_count": self.capability_count,
            "risk_finding_count": self.risk_finding_count,
            "error": self.error,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }


# ---------------------------------------------------------------------------
# Dataset parsing
# ---------------------------------------------------------------------------

_ROW_RE = re.compile(
    r"^\|\s*\d+\s*\|\s*`([^`]+)`\s*\|"
)


def parse_dataset(dataset_path: Path) -> list[str]:
    """
    Extract `owner/name` repo slugs from the markdown table in dataset.md.
    Skips rows whose slug is the literal placeholder `<PENDING SELECTION>`.
    """
    text = dataset_path.read_text(encoding="utf-8")
    slugs: list[str] = []
    for line in text.splitlines():
        m = _ROW_RE.match(line.strip())
        if not m:
            continue
        slug = m.group(1).strip()
        if slug == "<PENDING SELECTION>":
            continue
        slugs.append(slug)
    return slugs


# ---------------------------------------------------------------------------
# API client helpers
# ---------------------------------------------------------------------------


class ApiClient:
    def __init__(self, base_url: str, token: str):
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=60.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def list_github_repositories(self) -> list[dict[str, Any]]:
        resp = await self._client.get("/github/repositories")
        resp.raise_for_status()
        return resp.json()

    async def list_projects(self) -> list[dict[str, Any]]:
        resp = await self._client.get("/projects")
        resp.raise_for_status()
        return resp.json()

    async def create_project(self, name: str) -> dict[str, Any]:
        resp = await self._client.post("/projects", json={"name": name})
        resp.raise_for_status()
        return resp.json()

    async def list_repositories(self, project_id: str) -> list[dict[str, Any]]:
        resp = await self._client.get("/repositories", params={"project_id": project_id})
        resp.raise_for_status()
        return resp.json()

    async def create_repository(self, project_id: str, github_repo_id: int) -> dict[str, Any]:
        resp = await self._client.post(
            "/repositories",
            json={"project_id": project_id, "github_repo_id": github_repo_id},
        )
        if resp.status_code == 409:
            # Already registered under this or another project — caller handles.
            return {"_conflict": True}
        resp.raise_for_status()
        return resp.json()

    async def get_skillgraph(self, repository_id: str) -> dict[str, Any]:
        resp = await self._client.get(f"/repositories/{repository_id}/skillgraph")
        resp.raise_for_status()
        return resp.json()

    async def submit_analysis_job(self, repository_id: str) -> dict[str, Any]:
        resp = await self._client.post("/analysis/jobs", json={"repository_id": repository_id})
        resp.raise_for_status()
        return resp.json()

    async def get_analysis_job(self, job_id: str) -> dict[str, Any]:
        resp = await self._client.get(f"/analysis/jobs/{job_id}")
        resp.raise_for_status()
        return resp.json()

    async def list_job_runs(self, job_id: str) -> list[dict[str, Any]]:
        resp = await self._client.get(f"/analysis/jobs/{job_id}/runs")
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Ensure project / repository registration (idempotent)
# ---------------------------------------------------------------------------


async def _ensure_evaluation_project(api: ApiClient) -> str:
    projects = await api.list_projects()
    for p in projects:
        if p["name"] == EVAL_PROJECT_NAME:
            return p["id"]
    created = await api.create_project(EVAL_PROJECT_NAME)
    return created["id"]


async def _find_github_repo_id(api: ApiClient, full_name: str) -> Optional[int]:
    repos = await api.list_github_repositories()
    for r in repos:
        # GitHubRepositoryResponse is expected to carry full_name + id fields;
        # tolerate either "full_name" or "id"/"github_repo_id" naming.
        candidate_full_name = r.get("full_name")
        if candidate_full_name == full_name:
            return r.get("github_repo_id") or r.get("id")
    return None


async def _ensure_repository_registered(
    api: ApiClient, project_id: str, full_name: str
) -> Optional[str]:
    """
    Returns the DevTwin repository UUID for `full_name`, registering it via
    POST /repositories if not already present. Returns None if the repo is
    not accessible via the developer's GitHub App installation.
    """
    existing = await api.list_repositories(project_id)
    for r in existing:
        if r.get("full_name") == full_name:
            return r["id"]

    github_repo_id = await _find_github_repo_id(api, full_name)
    if github_repo_id is None:
        logger.warning(
            "Repository %s not found via GET /github/repositories — "
            "is it installed under the GitHub App? Skipping.",
            full_name,
        )
        return None

    created = await api.create_repository(project_id, github_repo_id)
    if created.get("_conflict"):
        # Registered under a different project — re-list without project filter is
        # not exposed; surface as a skip rather than guessing at ownership.
        logger.warning(
            "Repository %s already registered (409) under a different project; skipping.",
            full_name,
        )
        return None
    return created["id"]


# ---------------------------------------------------------------------------
# Job submission + polling
# ---------------------------------------------------------------------------


async def _submit_and_poll(api: ApiClient, repository_id: str) -> tuple[Optional[str], Optional[str], Optional[str], float]:
    """
    Returns (job_id, run_id, final_status, wall_clock_seconds).
    """
    start = time.monotonic()
    created = await api.submit_analysis_job(repository_id)
    job_id = created["job_id"]

    deadline = start + POLL_TIMEOUT_SECONDS
    final_job_status: Optional[str] = None
    while time.monotonic() < deadline:
        job = await api.get_analysis_job(job_id)
        final_job_status = job["status"]
        if final_job_status in ("COMPLETED", "FAILED"):
            break
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
    wall_clock = time.monotonic() - start

    runs = await api.list_job_runs(job_id)
    run_id = None
    run_status = final_job_status
    if runs:
        latest = runs[-1]
        run_id = latest["id"]
        run_status = latest["status"]

    if final_job_status not in ("COMPLETED", "FAILED"):
        run_status = run_status or "TIMEOUT"

    return job_id, run_id, run_status, wall_clock


# ---------------------------------------------------------------------------
# Read-only result counting (direct DB read; not pipeline logic)
# ---------------------------------------------------------------------------


async def _count_run_artifacts(run_id: str) -> dict[str, int]:
    """
    Read-only counts of persisted pipeline artifacts for a single analysis run.
    Uses the same SQLAlchemy models the backend already defines — no new
    schema, no scoring logic, no mutation.
    """
    # Imported lazily so this script can be exercised (dataset parsing, API
    # orchestration) without requiring the backend package on PYTHONPATH.
    backend_root = Path(__file__).resolve().parents[2] / "backend"
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))

    from sqlalchemy import func, select
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy.pool import NullPool

    from app.core.config import get_settings
    from app.models.observation import Observation
    from app.models.evidence import Evidence
    from app.models.capability import CapabilityHistory
    from app.models.risk_finding import RiskFinding

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool, echo=False)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

    run_uuid = uuid.UUID(run_id)

    async with session_factory() as session:
        obs_count = (
            await session.execute(
                select(func.count(Observation.id)).where(Observation.analysis_run_id == run_uuid)
            )
        ).scalar_one()

        obs_ids_subq = select(Observation.id).where(Observation.analysis_run_id == run_uuid)
        ev_count = (
            await session.execute(
                select(func.count(Evidence.id)).where(Evidence.observation_id.in_(obs_ids_subq))
            )
        ).scalar_one()

        cap_count = (
            await session.execute(
                select(func.count(CapabilityHistory.id)).where(
                    CapabilityHistory.analysis_run_id == run_uuid
                )
            )
        ).scalar_one()

        risk_count = (
            await session.execute(
                select(func.count(RiskFinding.id)).where(RiskFinding.analysis_run_id == run_uuid)
            )
        ).scalar_one()

    await engine.dispose()

    return {
        "observation_count": obs_count,
        "evidence_count": ev_count,
        "capability_count": cap_count,
        "risk_finding_count": risk_count,
    }


# ---------------------------------------------------------------------------
# Main evaluation sweep
# ---------------------------------------------------------------------------


async def evaluate_repository(api: ApiClient, project_id: str, full_name: str, results_dir: Path) -> RepoResult:
    result = RepoResult(full_name=full_name)
    slug = full_name.replace("/", "__")
    out_path = results_dir / f"{slug}.json"

    # Idempotency: if a result file already records a COMPLETED run, reuse it.
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
            if existing.get("run_status") == "COMPLETED" and existing.get("run_id"):
                logger.info("Reusing existing COMPLETED result for %s (skip re-run).", full_name)
                existing["reused_existing_run"] = True
                out_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
                return RepoResult(**{k: v for k, v in existing.items() if k in RepoResult.__dataclass_fields__})
        except (json.JSONDecodeError, TypeError, KeyError):
            logger.warning("Could not parse existing result file for %s; re-evaluating.", full_name)

    try:
        repository_id = await _ensure_repository_registered(api, project_id, full_name)
        if repository_id is None:
            result.error = "NOT_ACCESSIBLE_VIA_GITHUB_APP_INSTALLATION"
            _write_result(out_path, result)
            return result
        result.repository_id = repository_id

        # Check for an existing COMPLETED run via the read API before submitting a new job.
        graph = await api.get_skillgraph(repository_id)
        if graph.get("analysis_run_id"):
            result.run_id = graph["analysis_run_id"]
            result.run_status = "COMPLETED"
            result.reused_existing_run = True
            logger.info("Repository %s already has a COMPLETED run %s; skipping new job.", full_name, result.run_id)
        else:
            job_id, run_id, run_status, wall_clock = await _submit_and_poll(api, repository_id)
            result.job_id = job_id
            result.run_id = run_id
            result.run_status = run_status
            result.wall_clock_seconds = round(wall_clock, 2)

        if result.run_id and result.run_status == "COMPLETED":
            counts = await _count_run_artifacts(result.run_id)
            result.observation_count = counts["observation_count"]
            result.evidence_count = counts["evidence_count"]
            result.capability_count = counts["capability_count"]
            result.risk_finding_count = counts["risk_finding_count"]

    except httpx.HTTPStatusError as e:
        result.error = f"HTTP_{e.response.status_code}"
        logger.error("HTTP error evaluating %s: %s", full_name, e)
    except Exception as e:  # noqa: BLE001 — evaluation sweep must not crash on one repo
        result.error = f"{type(e).__name__}"
        logger.error("Unexpected error evaluating %s: %s: %s", full_name, type(e).__name__, e)

    _write_result(out_path, result)
    return result


def _write_result(out_path: Path, result: RepoResult) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")


async def main_async(dataset_path: Path, results_dir: Path) -> int:
    base_url = os.environ.get("DEVTWIN_API_BASE_URL")
    token = os.environ.get("DEVTWIN_API_TOKEN")
    if not base_url or not token:
        raise EvaluationError(
            "DEVTWIN_API_BASE_URL and DEVTWIN_API_TOKEN must be set. "
            "This script authenticates as a real developer via the existing "
            "Supabase-issued bearer token — it does not bypass auth."
        )

    slugs = parse_dataset(dataset_path)
    if not slugs:
        logger.error("No non-placeholder repository rows found in %s.", dataset_path)
        return 1

    logger.info("Evaluating %d repositories: %s", len(slugs), ", ".join(slugs))

    api = ApiClient(base_url, token)
    try:
        project_id = await _ensure_evaluation_project(api)
        results = []
        for slug in slugs:
            logger.info("--- Evaluating %s ---", slug)
            r = await evaluate_repository(api, project_id, slug, results_dir)
            results.append(r)
            status_note = r.error or r.run_status
            logger.info("Result for %s: %s", slug, status_note)
    finally:
        await api.close()

    failures = [r for r in results if r.error or r.run_status not in ("COMPLETED",)]
    logger.info(
        "Evaluation sweep complete: %d/%d repositories reached COMPLETED.",
        len(results) - len(failures),
        len(results),
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="DevTwin Phase 14 evaluation runner.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path(__file__).parent / "dataset.md",
        help="Path to dataset.md",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path(__file__).parent / "results",
        help="Directory to write per-repo JSON result files",
    )
    args = parser.parse_args()
    try:
        return asyncio.run(main_async(args.dataset, args.results_dir))
    except EvaluationError as e:
        logger.error(str(e))
        return 2


if __name__ == "__main__":
    sys.exit(main())
