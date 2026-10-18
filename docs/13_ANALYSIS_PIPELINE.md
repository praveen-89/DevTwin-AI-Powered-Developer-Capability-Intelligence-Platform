# 13. Analysis Pipeline Contract

## Overview
Repository analysis in DevTwin MUST NOT happen inside a synchronous HTTP request. 

## Pipeline Flow Contract

### Stage 1: Input -> Queue
-   **Consumes**: API Request (`POST /analysis/jobs`).
-   **Produces**: `analysis_jobs` record (Status: QUEUED).

### Stage 2: Fetching
-   **Consumes**: `analysis_jobs` queue item.
-   **Action**: Worker picks up job, creates an `analysis_runs` attempt record (Status: FETCHING). Clones Git repo, fetches GitHub metadata.
-   **Produces**: Local temporary file tree.

### Stage 3: Repository Mining
-   **Consumes**: File tree.
-   **Action**: Runs Linguist, parses manifests, runs AST parsers. Updates `analysis_runs` to MINING.
-   **Produces**: Raw `observations`.

### Stage 4: SkillGraph Mapping
-   **Consumes**: `observations`, `repository_dependencies`.
-   **Action**: Updates run to SKILL_GRAPH. Maps raw dependencies/languages to global `technologies` and `concepts`.
-   **Produces**: Mapped `observations`.

### Stage 5: CodeRisk
-   **Consumes**: File tree, AST, Git history (Commits).
-   **Action**: Updates run to CODE_RISK. Executes static analysis.
-   **Produces**: `risk_findings`.

### Stage 6: Evidence Generation
-   **Consumes**: `observations`, `risk_findings`.
-   **Action**: Contextualizes observations. Assigns strength, directness, reliability. **CRITICAL: Risk findings are processed as evidence, not automatic capability overrides.**
-   **Produces**: `evidence` records.

### Stage 7: Capability & Skill Gap Calculation
-   **Consumes**: `evidence`.
-   **Action**: Updates run to CAPABILITY. Executes mathematical scoring model to calculate new capability score and confidence.
-   **Produces**: Updates to `developer_capabilities`, appends to `capability_history`, recalculates `skill_gaps`.

### Stage 8: Completion
-   **Consumes**: Run state.
-   **Produces**: Updates `analysis_runs` to COMPLETED. Updates `analysis_jobs` to COMPLETED.

## Error Handling
If any stage fails, the worker logs the exception to `analysis_runs.error_message`, and sets the run to FAILED. A retry logic may attempt another `analysis_runs` execution under the same `analysis_jobs`.

---

## Implementation Status & Checkpoints

### Step 6A: Analysis Pipeline Foundation (Completed)
- **Completed Components**:
  - `AnalysisJob` ORM model (`backend/app/models/analysis_job.py`) mapping to `analysis_jobs` table.
  - `AnalysisRun` ORM model (`backend/app/models/analysis_run.py`) mapping to `analysis_runs` table.
  - API endpoint `POST /analysis/jobs`: Validates repository ownership against caller's projects, strictly validates payload, persists new job with `status="QUEUED"`, `attempt_count=0`.
  - API endpoint `GET /analysis/jobs/{id}`: Polls analysis job status and metadata, strictly enforcing developer ownership via repository/project join.
  - API endpoint `GET /analysis/jobs/{id}/runs`: Retrieves execution attempts for a job, returning an empty list `[]` when queued prior to worker execution.
  - Test suite `backend/tests/test_analysis.py`: 15 automated hermetic tests verifying authentication, ownership validation, cross-tenant isolation, schema validation, persistence, and error handling.
- **Execution & Dispatch Boundary**:
  - **Implemented**: Stage 1 (Input -> Queue) API ingestion and database persistence.
  - **Unimplemented in Step 6A**: Stage 2 (Fetching/Cloning), Stage 3 (Mining), Stage 4 (SkillGraph), Stage 5 (CodeRisk), Stage 6 (Evidence), Stage 7 (Capability Calculation), Stage 8 (Completion). Background Redis queue worker and worker processes are deferred to subsequent worker milestones.
### Step 6B: Worker Runner + Repository Fetching (Completed)
- **Completed Components**:
  - **Worker Runner** (`backend/app/workers/runner.py`, `workers/runner.py`):
    - Atomic job claiming with `SELECT ... FOR UPDATE SKIP LOCKED` preventing concurrent workers from claiming the same `QUEUED` job.
    - Manages attempt counts and guards against infinite retry loops (`MAX_JOB_ATTEMPTS = 3`).
    - Creates and updates `AnalysisRun` with attempt tracking and status transitions:
      - On successful fetch: `run.status` remains `FETCHING` and `job.status` remains `PROCESSING` (`completed_at = None`). `COMPLETED` is strictly reserved for Stage 8 (pipeline completion); a successful fetch does not falsely claim completion of subsequent intelligence stages.
      - On fetch failure: `run.status` and `job.status` transition to `FAILED` with sanitized error reporting and timestamps.
      - Repeated worker invocations ignore `PROCESSING` jobs (only claiming `QUEUED` jobs), preventing duplicate refetches or state corruption.
    - Failure sanitization: Maps internal exceptions and GitHub errors to standard sanitized codes (`REPOSITORY_NOT_FOUND`, `REPOSITORY_UNOWNED`, `ACCOUNT_DISCONNECTED`, `INSTALLATION_MISSING`, `SECURITY_VIOLATION`, `CORRUPT_ARCHIVE`, `RATE_LIMITED`, `GITHUB_HTTP_*`, `NETWORK_ERROR`, `INTERNAL_ERROR`) without leaking access tokens, private keys, or tracebacks into persistent rows.
    - Worker CLI: Supports single-job (`--job-id <UUID>`), single-cycle (`--once`), and polling loop (`--poll --interval 5.0`) execution modes.
  - **Repository Fetcher** (`backend/app/workers/fetcher.py`):
    - Strictly resolves repository ownership against persisted `projects` and `developers` tables.
    - Validates associated `github_accounts` record and requires a valid `installation_id`.
    - Generates short-lived GitHub App JWT and installation access tokens in memory for archive download. Tokens are never persisted or logged.
    - Downloads repository tarball via GitHub API client (`GET /repos/{owner}/{repo}/tarball/{ref}`).
    - Safe extraction: Path traversal and Zip Slip guard (`is_safe_tar_member`) rejects absolute paths, parent directory traversals (`..`), and directory-escaping symlinks.
    - Isolated workspace: `temporary_workspace()` context manager guarantees complete cleanup (`shutil.rmtree`) of extracted repository contents on both success and error.
  - **GitHub Client Extension** (`backend/app/services/github/client.py`):
    - Added `download_repository_archive` supporting redirects (e.g., `codeload.github.com`), rate-limit detection, and error sanitization.
  - **Test Suite** (`backend/tests/test_worker.py`):
    - 26 automated hermetic tests covering atomic queue claiming, retry bounding, non-terminal `FETCHING`/`PROCESSING` lifecycle state, repeated-invocation safety, path-traversal prevention, corrupt archives, temporary workspace cleanup, ownership verification, installation token lifecycle, and error sanitization.
- **Worker Invocation**:
  ```bash
  # Claim and process one job from the queue
  python -m app.workers.runner --once

  # Process a specific job by UUID
  python -m app.workers.runner --job-id <UUID>

  # Run polling loop
  python -m app.workers.runner --poll --interval 5.0
  ```
- **Interrupted-Job Recovery & Operational Boundary**:
  - Abrupt worker process termination (e.g. SIGKILL or node abort) leaves claimed jobs in status `PROCESSING`. Because `analysis_jobs` currently lacks a lease deadline (`lease_expires_at`), heartbeat timestamp (`heartbeat_at`), or worker identifier (`worker_id`), automatic reclamation cannot safely distinguish between a stalled/crashed worker and a slow, live worker actively fetching a large repository. To prevent duplicate concurrent execution by live workers, automatic reclaiming is omitted in Step 6B.
  - *Prerequisite for automated recovery*: A future database migration adding `heartbeat_at TIMESTAMPTZ` or `lease_expires_at TIMESTAMPTZ` (or a distributed Redis lease key) to enable atomic stale-lease reaping without risking split-brain processing.
- **Unimplemented in Step 6B**:
  - Stage 3: Repository Mining (Linguist, dependency manifests, AST parsing).
  - Stage 4: SkillGraph Mapping.
  - Stage 5: CodeRisk Analysis.
  - Stage 6: Evidence Generation.
  - Stage 7: Capability & Skill Gap Calculation.
  - Background distributed queue (Redis/Celery) remains deferred per design specifications.
- **Next Milestone**:
  - **Step 6C — Repository Mining Engine**: Implementation of deterministic file tree analysis, language detection, dependency manifest parsing, and AST extraction from the fetched workspace.
