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
### Step 6C: Repository Mining Engine (Completed)
- **Completed Components**:
  - **Mining Module** (`backend/app/mining/`):
    - **Safe File-Tree Traversal** (`traversal.py`): Traverses strictly within the isolated workspace boundary. Enforces conservative directory exclusions (`.git`, `node_modules`, `vendor`, `venv`, `build`, `dist`, `__pycache__`, etc.). Completely rejects symlinks and directory escapes. Detects binary files via null-byte inspection (`b'\x00'`). Enforces file count and total source byte budgets.
    - **Language & File Classification** (`classification.py`): Deterministic extension-to-language mapping and special filename recognition. Calculates file counts, byte counts, and byte-weighted percentages sorted deterministically.
    - **Defensive Manifest Extraction** (`manifests.py`): Extracts declared dependencies from `package.json` (npm), `requirements.txt` (pip), and `Cargo.toml` (cargo). Enforces 512 KB manifest file budget and 300 dependencies per manifest cap. Records sanitized `MiningWarning` entries on syntax or decode errors without aborting repository mining.
    - **AST Parser Foundation** (`ast_parser.py`): Standard-library `ast.parse`-based Python AST parser extracting function declarations (async, arg count, docstrings), class declarations (bases, methods, docstrings), and imports (modules, aliases, line numbers). Non-executing and untrusted-source safe; syntax/indentation/recursion errors produce bounded warnings.
    - **Coordinator Engine** (`engine.py`): Integrates traversal, classification, manifest parsing, and AST parsing into a validated, deterministically sorted `MiningResult` contract.
  - **Archive & Resource Safety Hardening**:
    - **Streaming Download** (`backend/app/services/github/client.py`): Implemented chunked streaming via `client.stream("GET", ...)` enforcing a 50 MB archive download limit, raising `GitHubHTTPError(status_code=413)` on violation.
    - **Extraction Limits** (`backend/app/workers/fetcher.py`): Enforces 10,000 maximum archive members, 10 MB single-file size cap, and 250 MB total uncompressed bytes limit, preventing tar bomb and decompression vulnerabilities.
  - **Worker Lifecycle Integration** (`backend/app/workers/runner.py`):
    - Invokes `mine_repository` while the temporary workspace remains open.
    - Status transitions: Updates `run.status = "MINING"` upon commencement. On successful completion, leaves `run.status = "MINING"` and `job.status = "PROCESSING"` (`completed_at = None`) in an honest non-terminal state awaiting Step 6D handoff.
  - **Test Suite** (`backend/tests/test_mining.py`, `backend/tests/test_worker.py`):
    - 44 tests across mining and worker runners verifying traversal exclusions, symlink protection, language metrics, manifest parsing, AST extraction, archive streaming/limits, and worker lifecycle integration.
- **Unimplemented in Step 6C**:
  - Stage 4: SkillGraph Mapping (taxonomic entity resolution, technology/concept graph linking).
  - Stage 5: CodeRisk Analysis (AST static analysis, vulnerability/risk pattern detection).
  - Stage 6: Evidence Generation (observation contextualization, reliability weighting).
  - Stage 7: Capability & Skill Gap Calculation (mathematical scoring model).
  - Stage 8: Pipeline Completion (`analysis_runs` -> `COMPLETED`, `analysis_jobs` -> `COMPLETED`).
### Step 6D: SkillGraph Entity & Relationship Mapping (Completed)
- **Completed Components**:
  - **SkillGraph Models & Schema Alignment** (`backend/app/models/`):
    - `Observation` ORM model (`observation.py`) mapping to `observations` table with JSONB `source_reference` and confidence scoring.
    - `RepositoryLanguage` ORM model (`repository_language.py`) mapping to `repository_languages` with unique `(repository_id, language)`.
    - `RepositoryDependency` ORM model (`repository_dependency.py`) mapping to `repository_dependencies` with unique `(repository_id, ecosystem, package_name)`.
    - Taxonomy ORM models (`taxonomy.py`): `Skill`, `Technology`, `Concept`, `SkillTechnology`, `SkillConcept`, `TechnologyConcept`, `SkillRelationship`.
  - **Deterministic SkillGraph Mapping Engine** (`backend/app/skillgraph/`):
    - `taxonomy.py`: Curated, grounded taxonomy seed mappings for canonical languages (Python, TypeScript, JavaScript, Rust, Go, HTML, CSS, SQL, Shell, Dockerfile) and dependencies (FastAPI, Flask, Django, SQLAlchemy, Pydantic, pytest, HTTPX, Requests, Celery, Redis, React, Next.js, Express, Axios, Jest, Tailwind CSS, Tokio, Serde, Actix-web). Fallback to ungrounded library nodes without hallucinated skills or concepts.
    - `mapper.py`: Pure in-memory transformation from `MiningResult` to `SkillGraphMapping`. Creates factual observations (`LANGUAGE_DETECTED`, `DEPENDENCY_FOUND`, `CLASS_DEFINED`, `FUNCTION_DEFINED`, `MODULE_IMPORTED`, `SYNTAX_ERROR_OBSERVED`, `MINING_WARNING`) with 100% source provenance.
    - `service.py`: `persist_skillgraph` replaces repository language and dependency snapshots, batch-inserts observations linked to `analysis_runs.id`, and resolves/links global taxonomy nodes and edges.
  - **Worker Pipeline Integration** (`backend/app/workers/runner.py`):
    - Transitions `run.status = "SKILL_GRAPH"` upon Stage 4 commencement.
    - Invokes `persist_skillgraph` and binds `run._skillgraph_result`.
    - Leaves `run.status = "SKILL_GRAPH"` and `job.status = "PROCESSING"` (`completed_at = None`) in an honest non-terminal state awaiting Step 6E.
  - **Test Suite** (`backend/tests/test_skillgraph.py`):
    - 14 tests verifying token normalization, language mapping, known/unknown dependency resolution, AST symbol mapping, parse error handling, warning observations, empty repository handling, entity deduplication, database persistence, and worker status lifecycle.
### Step 6E: CodeRisk Engine & Static Analysis (Completed)
- **Completed Components**:
  - **CodeRisk Models & Schema Alignment** (`backend/app/models/`):
    - `RiskFinding` ORM model (`risk_finding.py`) mapping to `risk_findings` table with check constraints for category (`SECURITY`, `RELIABILITY`, `TESTING`, `MAINTAINABILITY`, `DEPENDENCY`, `ARCHITECTURE`), severity (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), confidence (`0..1`), and mandatory `observation_id` foreign key.
  - **Deterministic Static Risk Analysis Engine** (`backend/app/coderisk/`):
    - `rules.py`: Grounded rule catalog (`SEC-001` Hardcoded Secret Literal, `SEC-002` Arbitrary Code Execution Construct, `SEC-003` Insecure Object Deserialization, `REL-001` Bare Except Clause, `REL-002` Silent Exception Swallowing, `MAINT-001` Excessive Parameter Count, `MAINT-002` Syntax Parse Failure, `TEST-001` Missing Test Suite).
    - `analyzer.py`: Non-executing AST and static analysis engine. Performs safe file inspections within bounded budgets (500 files, 512 KB per file limit). Redacts secrets from evidence snippets to prevent credential leaks.
    - `service.py`: `persist_coderisk` executes static analysis, replaces previous repository risk finding snapshots, pairs each finding with an immutable `Observation(type="RISK_OBSERVED")`, and flushes transactionally.
  - **Worker Pipeline Integration** (`backend/app/workers/runner.py`):
    - Transitions `run.status = "CODE_RISK"` upon Stage 5 commencement.
    - Invokes `persist_coderisk` within the temporary workspace lifecycle.
    - Binds `run._coderisk_result`.
    - Leaves `run.status = "CODE_RISK"` and `job.status = "PROCESSING"` (`completed_at = None`) in an honest non-terminal state awaiting Step 6F.
  - **Test Suite** (`backend/tests/test_coderisk.py`):
    - 16 tests verifying positive/negative detection across all rules, placeholder suppression, secret redaction, deterministic ordering, empty/binary file safety, transaction rollback, and worker status lifecycle.
- **Unimplemented in Step 6E**:
  - Stage 6: Evidence Generation (observation contextualization, reliability weighting, polarity assignment).
  - Stage 7: Capability & Skill Gap Calculation (mathematical scoring model).
  - Stage 8: Pipeline Completion (`analysis_runs` -> `COMPLETED`, `analysis_jobs` -> `COMPLETED`).
- **Next Milestone**:
  - **Step 6F — Evidence Generation & Observation Contextualization**: Mapping factual observations and risk findings to contextualized evidence with type, strength, and polarity.