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
- **Next Milestone**:
  - **Step 6B — Worker Analysis Runner**: Implementation of asynchronous queue consumption, repository cloning, and discrete execution attempt lifecycle (`analysis_runs`).
