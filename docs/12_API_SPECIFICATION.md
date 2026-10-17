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
*   **Response**: `{ "id": "uuid", "github_username": "string" }`

**`POST /developers/me`**
*   **Purpose**: Create a developer identity for the newly authenticated user.
*   **Response**: `{ "id": "uuid", "auth_user_id": "uuid" }`

**`GET /developers/{id}/capabilities`**
*   **Purpose**: Get the current capability state for the developer.
*   **Response**: Array of `developer_capabilities` objects including target metadata (resolved Skill/Tech/Concept name), `score`, and `confidence`.

**`GET /developers/{id}/evidence`**
*   **Purpose**: Retrieve the contextualized evidence supporting a developer's capabilities.
*   **Response**: Array of `evidence` objects including `type`, `strength`, and `polarity`.

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
*   **Purpose**: Get CodeRisk findings (Pending future milestone).
*   **Response**: Array of `risk_findings` objects.

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
