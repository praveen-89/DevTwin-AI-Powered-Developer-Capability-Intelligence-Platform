# 12. API Specification (Data Contracts)

*Source of Truth Context: This document defines external/backend contracts for FastAPI.*

## Core Principles
- **Authentication**: Bearer Token (Supabase JWT). The backend maps `auth.uid()` -> `developers.auth_user_id` -> internal `developers.id` for all context resolution.
- **Format**: JSON.
- **Pagination**: `?page=` and `?limit=` query parameters.

## API Resources

### 1. Developers

**`GET /developers/me`**
*   **Purpose**: Retrieve developer identity for the authenticated user.
*   **Response**: `200 OK`, `DeveloperResponse` (`id`, `auth_user_id`, `created_at`, `updated_at`). Returns `404 Not Found` if profile not yet created.

**`POST /developers/me`**
*   **Purpose**: Create a developer identity for the newly authenticated user. Idempotent: returns existing record if already initialized.
*   **Response**: `201 Created` or `200 OK`, `DeveloperResponse`.

**`GET /developers/me/capabilities`** and **`GET /developers/{id}/capabilities`**
*   **Purpose**: Retrieve capability scores and confidence intervals for the developer. Enforces caller ownership (returns 404 on cross-developer access).
*   **Query Parameters**: `target_type` (optional: `skill`, `technology`, `concept`), `min_confidence` (optional float), `limit` (default 50), `offset` (default 0).
*   **Response**: `200 OK`, `DeveloperCapabilityListResponse` containing `items` with resolved `target` metadata (`target_type`, `target_id`, `target_name`, `domain_or_category`), `score` [0.0, 1.0], `confidence` [0.0, 1.0], `scoring_version`, `updated_at`.

**`GET /developers/me/capabilities/history`**
*   **Purpose**: Retrieve append-only history of capability score snapshots for trend visualization.
*   **Query Parameters**: `target_id`, `target_type`, `capability_id`, `analysis_run_id`, `limit`, `offset`.
*   **Response**: `200 OK`, `CapabilityHistoryListResponse` sorted by `recorded_at DESC`.

**`GET /developers/me/evidence`**
*   **Purpose**: Retrieve contextualized evidence supporting capabilities, including safe source code provenance.
*   **Query Parameters**: `repository_id`, `analysis_run_id`, `evidence_type`, `polarity` (`positive`/`negative`), `target_id`, `limit`, `offset`.
*   **Response**: `200 OK`, `EvidenceListResponse` with `items` containing `type`, `strength`, `directness`, `reliability`, `polarity`, `recency`, linked `skills`, `technologies`, `concepts`, and safe `provenance` (file/line numbers without secret code).

### 2. GitHub Integration

**`GET /github/install`**
*   **Purpose**: Start the GitHub App connection flow.
*   **Response**: `{ "install_url": "string" }`

**`GET /github/callback`**
*   **Purpose**: Handle GitHub App installation redirect with user authorization. Implements atomic state claim and code exchange.
*   **Request**: `?code=&installation_id=&setup_action=install&state=`
*   **Response**: 302 Redirect

**`GET /github/status`**
*   **Purpose**: Check GitHub connection status.
*   **Response**: `{ "connected": boolean, "username": "string", "installation_id": 123 }`

**`DELETE /github/disconnect`**
*   **Purpose**: Remove/inactivate the active GitHub connection (does NOT delete historical DevTwin analysis data).
*   **Response**: 204 No Content

**`GET /github/repositories`** *(NOT IMPLEMENTED — Future Phase)*
*   **Purpose**: List repositories accessible via the GitHub App installation using an on-demand Installation Access Token.
*   **Response**: 200 OK, array of repository objects

### 3. Repositories

**`POST /repositories`**
*   **Purpose**: Register a GitHub repository under an owned project.
*   **Authentication**: Required (Current Developer).
*   **Request**: `{ "project_id": "uuid", "github_repo_id": 123456 }`
*   **Response**: `201 Created`, `{ "id": "uuid", "project_id": "uuid", "github_repo_id": 123456, "name": "string", "full_name": "owner/repo", ... }`

**`GET /repositories`**
*   **Purpose**: List repositories belonging to projects owned by the authenticated developer.
*   **Authentication**: Required (Current Developer).
*   **Query Parameters**: `project_id` (optional UUID filter). Validates ownership if provided.
*   **Response**: `200 OK`, array of `RepositoryResponse` objects. Excludes unowned or NULL-project repositories.

**`GET /repositories/{id}`**
*   **Purpose**: Retrieve details for a single repository owned by the authenticated developer.
*   **Authentication**: Required (Current Developer).
*   **Response**: `200 OK`, `RepositoryResponse` object. Returns 404 for nonexistent or unowned repositories.

**`GET /repositories/{id}/risks`**
*   **Purpose**: Retrieve static CodeRisk findings for a repository. Defaults to the latest completed analysis run unless `run_id` is specified.
*   **Authentication**: Required (Current Developer; returns 404 if not owned).
*   **Query Parameters**: `run_id` (optional), `severity` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), `category`, `limit`, `offset`.
*   **Response**: `200 OK`, `RiskFindingListResponse` containing `items` with `rule_type`, `category`, `severity`, `confidence`, `file_path`, `line_start`, `line_end`, and `analysis_run_id`.

**`GET /repositories/{id}/skillgraph`**
*   **Purpose**: Retrieve repository SkillGraph topology including mined languages, dependencies, resolved taxonomy nodes, and directed relationship edges. Defaults to latest completed run snapshot unless `run_id` is specified.
*   **Authentication**: Required (Current Developer; returns 404 if not owned).
*   **Query Parameters**: `run_id` (optional).
*   **Response**: `200 OK`, `SkillGraphResponse` with `languages`, `dependencies`, `nodes` (skills, technologies, concepts), and `edges` (`USES`, `APPLIES`, `REQUIRES`, `RELATED_TO`).

### 4. Analysis Pipeline

**`POST /analysis/jobs`**
*   **Purpose**: Submit a repository analysis job (Stage 1: Input -> Queue).
*   **Authentication**: Required (Current Developer).
*   **Request**: `{ "repository_id": "uuid" }` (Strict schema; unexpected extra fields rejected with 422).
*   **Ownership Check**: Enforces that `repository_id` resolves to a project owned by the caller. Returns 404 if not found or unowned.
*   **Execution Boundary**: Persists an `analysis_jobs` record in `QUEUED` state with `attempt_count=0`. Does not synchronously mine code or trigger background workers in this step.
*   **Response**: `201 Created`
    ```json
    {
      "id": "uuid",
      "job_id": "uuid",
      "status": "QUEUED"
    }
    ```
*   **Errors**: `401 Unauthorized`, `404 Not Found`, `422 Unprocessable Entity`, `500 Internal Server Error`.

**`GET /analysis/jobs/{id}`**
*   **Purpose**: Poll or inspect status and metadata of an analysis job.
*   **Authentication**: Required (Current Developer).
*   **Ownership Check**: Enforces that the job's repository belongs to a project owned by the caller. Returns 404 if not found or unowned.
*   **Response**: `200 OK`
    ```json
    {
      "id": "uuid",
      "job_id": "uuid",
      "repository_id": "uuid",
      "status": "QUEUED",
      "attempt_count": 0,
      "requested_at": "2026-10-16T19:00:00Z",
      "completed_at": null
    }
    ```
*   **Errors**: `401 Unauthorized`, `404 Not Found`, `500 Internal Server Error`.

**`GET /analysis/jobs/{id}/runs`**
*   **Purpose**: View discrete execution attempts (`analysis_runs`) under an analysis job.
*   **Authentication**: Required (Current Developer).
*   **Ownership Check**: Enforces job ownership. Returns 404 if not found or unowned.
*   **Response**: `200 OK`, array of `AnalysisRunResponse` objects (empty `[]` when queued prior to worker execution).
*   **Errors**: `401 Unauthorized`, `404 Not Found`, `500 Internal Server Error`.
