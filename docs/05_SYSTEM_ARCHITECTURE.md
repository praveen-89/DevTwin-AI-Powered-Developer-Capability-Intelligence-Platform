# 05. System Architecture

## Overview
DevTwin utilizes a modular, job-based architecture designed to decouple heavy repository analysis from responsive user interactions. The architecture is explicitly designed to support the evidence-backed capability model.

## Implementation Status (v0.1)

**CURRENTLY IMPLEMENTED:**
* FastAPI foundation
* configuration
* health endpoints
* database connectivity
* migrations
* RLS
* security hardening
* backend tests

**PLANNED:**
* authentication
* GitHub integration
* repository ingestion
* mining
* SkillGraph runtime
* CodeRisk runtime
* evidence pipeline
* capability engine
* dashboard

## Core Architectural Components

### 1. Frontend (Next.js)
The developer dashboard and evidence explorer. It provides the UI for users to view their SkillGraph, CodeRisk findings, and Capability states. It communicates with the backend via REST APIs and handles real-time updates via polling or subscriptions for analysis jobs.

### 2. Backend API (FastAPI)
The core orchestration layer. It handles user requests, repository registration, job queuing, and querying the generated intelligence layers.
- **Routes**: `/analysis`, `/capabilities`, `/evidence`, `/coderisk`
- **Responsibilities**: API serving, authentication, database querying, queue management.

### 3. Worker Fleet (Python / Redis / RQ or Celery)
Repository mining and analysis cannot happen within an HTTP request lifecycle. The system relies on background workers to perform heavy lifting.
- **Analysis Pipeline**:
  `QUEUED -> FETCHING -> MINING -> SKILL_GRAPH -> CODE_RISK -> CAPABILITY -> COMPLETED`

### 4. Intelligence Layers
These are logical modules executed primarily by the workers:
- **Repository Miner**: Clones/fetches repositories, extracts metadata, ASTs, and dependencies.
- **CodeRisk Engine**: Runs static analysis and custom rules against the codebase to generate `RiskSignal` objects.
- **SkillGraph Builder**: Maps discovered technologies and concepts to the graph schema.
- **Evidence Engine**: Synthesizes raw observations into contextualized `EvidenceItem` objects.
- **Capability Scorer**: Calculates capability states and confidence intervals based on the evidence.

### 5. Database (PostgreSQL)
A relational schema designed to support graph-like queries without the initial overhead of a dedicated graph database (like Neo4j) for the Minor MVP. It stores users, repositories, evidence, risk signals, and capability states.

### 6. Authentication & Identity
DevTwin uses Supabase Auth for primary user authentication and a hybrid GitHub App flow for secure repository integration.
- **Supabase Auth**: The frontend obtains a JWT which the backend cryptographically verifies using Supabase JWKS.
- **Identity Mapping**: `auth.uid()` maps 1:1 to an internal `developers.auth_user_id`. Developer records are created explicitly via `POST /developers/me`.
- **GitHub Integration**: Uses a GitHub App installation flow with user authorization. The authenticated GitHub user access token is used to verify that the user has access to the specified GitHub App installation (`GET /user/installations`). The temporary user token is never persisted.
- **GitHub Data Access**: Uses on-demand, short-lived installation access tokens. Persistent GitHub credentials are not stored in the database.

## Data Flow Pipeline

```text
POST /analysis (Triggered by user/system)
       ↓
Create Analysis Job
       ↓
Job Queue (Redis)
       ↓
Background Worker Picks Up Job
       ↓
1. Fetch Repository Data (GitHub API / Git Clone)
       ↓
2. Mine Repository (AST parsing, Dependency resolution)
       ↓
3. Build SkillGraph (Identify technologies/concepts)
       ↓
4. Run CodeRisk Analysis (Security, Testing, Architecture checks)
       ↓
5. Generate Evidence (Map findings to developer capabilities)
       ↓
6. Update Capability State (Calculate scores and confidence)
       ↓
Persist to Database (PostgreSQL)
       ↓
Frontend Dashboard Updates
```

## AI / ML Boundaries
- AI is an intelligence layer, not the entire application.
- LLM APIs may be used for semantic skill mapping, concept extraction, or generating human-readable explanations of complex evidence.
- The core capability scoring relies on interpretable weighting and aggregation before any black-box ML models are applied.
