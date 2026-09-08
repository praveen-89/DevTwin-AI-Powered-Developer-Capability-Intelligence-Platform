# 12. API Specification (Data Contracts)

## Overview
This document specifies the REST API data contracts for the DevTwin Minor MVP backend (FastAPI). 
*Note: This is a specification for future implementation. The API is not yet built.*

## Core Principles
- **Authentication**: All endpoints require a valid Bearer Token (JWT).
- **Format**: JSON requests and responses.
- **Pagination**: Endpoints returning collections use `?page=` and `?limit=` query parameters.

## API Resources

### 1. Developers

**`GET /developers/{id}`**
*   **Purpose**: Retrieve developer identity.
*   **Response**: `{ "id": "uuid", "github_username": "string", "created_at": "date" }`

**`GET /developers/{id}/capabilities`**
*   **Purpose**: Get the current capability state for the developer.
*   **Response**: Array of `developer_capabilities` objects including target metadata (resolved Skill/Tech/Concept name), `score`, and `confidence`.

**`GET /developers/{id}/capabilities/{capability_id}/history`**
*   **Purpose**: Get time-series trend data for a specific capability.
*   **Response**: Array of `capability_history` objects ordered by `recorded_at` ASC.

**`GET /developers/{id}/evidence`**
*   **Purpose**: Retrieve the contextualized evidence supporting a developer's capabilities.
*   **Query Params**: `?target_id=uuid` (filter by skill/tech).
*   **Response**: Array of `evidence` objects including `type`, `strength`, and `polarity`.

**`GET /developers/{id}/skills/gaps`**
*   **Purpose**: Get calculated skill gaps.
*   **Response**: Array of `skill_gaps` objects.

### 2. Repositories

**`GET /repositories`**
*   **Purpose**: List repositories owned/tracked by the authenticated developer.
*   **Response**: Array of repository metadata.

**`GET /repositories/{id}`**
*   **Purpose**: Get repository details.
*   **Response**: Repo object + nested arrays for `repository_languages` and `repository_dependencies`.

**`GET /repositories/{id}/risks`**
*   **Purpose**: Get CodeRisk findings.
*   **Query Params**: `?severity=HIGH|CRITICAL`, `?category=SECURITY`.
*   **Response**: Array of `risk_findings` objects.

### 3. Analysis Pipeline

**`POST /analysis`**
*   **Purpose**: Queue a repository for analysis.
*   **Request**: `{ "repository_id": "uuid" }`
*   **Response**: `{ "analysis_job_id": "uuid", "status": "QUEUED" }`

**`GET /analysis/runs/{id}`**
*   **Purpose**: Poll the status of a specific analysis run.
*   **Response**: `{ "id": "uuid", "status": "MINING|CODE_RISK|COMPLETED...", "error_info": null }`

### 4. Taxonomy (SkillGraph)

**`GET /graph/skills`**
*   **Purpose**: Get global skills taxonomy.
**`GET /graph/technologies`**
*   **Purpose**: Get global technologies taxonomy.
**`GET /graph/concepts`**
*   **Purpose**: Get global concepts taxonomy.
