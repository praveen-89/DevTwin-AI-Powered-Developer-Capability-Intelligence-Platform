# 12. API Specification

## Overview
The backend provides a RESTful API built with FastAPI. It handles synchronous dashboard requests and asynchronous analysis job management.

## Core Endpoints

### 1. Analysis Pipeline (Asynchronous)
-   `POST /api/v1/analysis`
    -   *Payload*: `{ "repository_url": "string", "developer_id": "uuid" }`
    -   *Response*: `{ "job_id": "uuid", "status": "QUEUED" }`
    -   *Action*: Enqueues a repository for background mining.
-   `GET /api/v1/analysis/{job_id}`
    -   *Response*: `{ "job_id": "uuid", "status": "MINING", "progress": 45 }`

### 2. Developer Capability
-   `GET /api/v1/developers/{developer_id}/capabilities`
    -   *Query*: `?type=SKILL|TECHNOLOGY`
    -   *Response*: List of `CapabilityState` objects, including score, confidence, and trend.
-   `GET /api/v1/developers/{developer_id}/capabilities/history`
    -   *Response*: Time-series data for capability trends.

### 3. Evidence Explorer
-   `GET /api/v1/capabilities/{capability_id}/evidence`
    -   *Response*: List of `EvidenceItem` objects supporting the specific capability score, demonstrating provenance.

### 4. CodeRisk
-   `GET /api/v1/repositories/{repository_id}/risks`
    -   *Query*: `?category=SECURITY&severity=HIGH`
    -   *Response*: List of `RiskSignal` objects associated with the repository.

### 5. SkillGraph
-   `GET /api/v1/graph/skills/{skill_id}`
    -   *Response*: The sub-graph of related concepts and technologies.
