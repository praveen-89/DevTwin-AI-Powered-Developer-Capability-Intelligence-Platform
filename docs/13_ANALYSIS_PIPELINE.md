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
