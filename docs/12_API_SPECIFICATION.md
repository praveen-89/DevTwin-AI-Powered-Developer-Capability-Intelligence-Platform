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

**`GET /developers/{id}/capabilities`**
*   **Purpose**: Get the current capability state for the developer.
*   **Response**: Array of `developer_capabilities` objects including target metadata (resolved Skill/Tech/Concept name), `score`, and `confidence`.

**`GET /developers/{id}/evidence`**
*   **Purpose**: Retrieve the contextualized evidence supporting a developer's capabilities.
*   **Response**: Array of `evidence` objects including `type`, `strength`, and `polarity`.

### 2. Repositories

**`GET /repositories`**
*   **Purpose**: List repositories tracked by the developer.
*   **Response**: Array of repository metadata.

**`GET /repositories/{id}/risks`**
*   **Purpose**: Get CodeRisk findings.
*   **Response**: Array of `risk_findings` objects.

### 3. Analysis Pipeline

**`POST /analysis/jobs`**
*   **Purpose**: Request a repository analysis.
*   **Request**: `{ "repository_id": "uuid" }`
*   **Response**: `{ "job_id": "uuid", "status": "QUEUED" }`

**`GET /analysis/jobs/{id}`**
*   **Purpose**: Poll the status of an analysis request.
*   **Response**: `{ "id": "uuid", "status": "PROCESSING", "attempt_count": 1 }`

**`GET /analysis/jobs/{id}/runs`**
*   **Purpose**: View execution attempts for a job.
*   **Response**: Array of runs: `{ "id": "uuid", "status": "MINING|CODE_RISK|COMPLETED...", "error_code": null }`
