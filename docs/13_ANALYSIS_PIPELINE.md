# 13. Analysis Pipeline Contract

## Overview
Repository analysis in DevTwin MUST NOT happen inside a synchronous HTTP request. The process is resource-intensive and requires an asynchronous, reproducible job-based architecture.

## Pipeline Flow Contract

The pipeline executes sequentially. Each stage consumes data from the previous stage and produces specific database entities.

### Stage 1: Input -> Queue
-   **Consumes**: API Request (`POST /analysis`).
-   **Produces**: `analysis_jobs` record (Status: QUEUED).

### Stage 2: Fetching
-   **Consumes**: `analysis_jobs` queue item.
-   **Action**: Worker picks up job, creates `analysis_runs` record (Status: FETCHING). Clones Git repo, fetches GitHub metadata.
-   **Produces**: Local temporary file tree.

### Stage 3: Repository Mining
-   **Consumes**: File tree.
-   **Action**: Runs Linguist, parses `package.json`/`requirements.txt`, runs AST parsers. Updates `analysis_runs` to MINING.
-   **Produces**: Raw `observations` (e.g., "Dependency React found"), `repository_languages`, `repository_dependencies`.

### Stage 4: SkillGraph Mapping
-   **Consumes**: `observations`, `repository_dependencies`.
-   **Action**: Updates run to SKILL_GRAPH. Maps raw dependencies/languages to global `technologies` and `concepts` in the database.
-   **Produces**: Mapped `observations` linked to taxonomy.

### Stage 5: CodeRisk
-   **Consumes**: File tree, AST, Git history (Commits).
-   **Action**: Updates run to CODE_RISK. Executes static analysis rules (e.g., security heuristics, complexity metrics).
-   **Produces**: `risk_findings` (categorized, severity-rated, optionally attributed to `commits`).

### Stage 6: Evidence Generation
-   **Consumes**: `observations`, `risk_findings`.
-   **Action**: Contextualizes observations. Assigns strength, directness, reliability.
-   **Produces**: `evidence` records and junction records (`evidence_skills`, etc.).

### Stage 7: Capability & Skill Gap Calculation
-   **Consumes**: `evidence` for the developer.
-   **Action**: Updates run to CAPABILITY. Executes mathematical scoring model to calculate new capability score and confidence.
-   **Produces**: Updates to `developer_capabilities`, appends to `capability_history`, recalculates `skill_gaps`.

### Stage 8: Completion
-   **Consumes**: Run state.
-   **Produces**: Updates `analysis_runs` to COMPLETED (or FAILED with `error_info`). Frontend polling displays results.

## Error Handling
If any stage fails critically (e.g., repo not found, out of memory), the pipeline halts, logs the exception trace to `analysis_runs.error_info`, and sets status to FAILED. Partial states (e.g., observations recorded before failure) remain for debugging.
