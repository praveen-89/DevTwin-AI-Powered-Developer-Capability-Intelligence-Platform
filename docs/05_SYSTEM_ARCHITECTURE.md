# 05. System Architecture

---
Status: Active
Version: 2.0
Last Updated: 2026-11-12
---

## Overview
DevTwin utilizes a modular, job-based architecture designed to decouple heavy repository analysis from responsive user interactions. The architecture is explicitly designed to support the evidence-backed capability model.

## Implementation Status (v0.8 — Checkpoint 31)

**CURRENTLY IMPLEMENTED & VERIFIED:**
* FastAPI application factory & 18 active REST endpoints
* Settings and configuration validation
* Health and database readiness endpoints (`/health`, `/health/database`)
* Supabase Auth JWKS verification & developer auto-provisioning
* GitHub App OAuth installation, status, disconnect, and repository listing
* PostgreSQL-native atomic queue runner (`SELECT ... FOR UPDATE SKIP LOCKED`)
* Asynchronous 8-stage analysis pipeline runner
* Safe repository fetching & tarball streaming
* Repository mining (AST parsing, language classification, dependency extraction)
* Grounded SkillGraph taxonomic mapping and snapshot persistence
* CodeRisk static analysis engine (8 security, reliability, maintainability rules)
* Evidence engine (Strength, directness, reliability, polarity scoring)
* Capability scoring engine v1 (Sigmoid saturation, diminishing returns, half-life decay)
* Append-only capability history tracking
* Next.js 16 (App Router, Tailwind CSS v4) frontend with 6 complete views
* Cytoscape interactive graph visualizer & Recharts temporal analytics
* In-app Supabase Auth Modal with dev-token fallback
* Comprehensive test pyramid: 385 backend tests, 64 frontend tests, 47 Playwright tests

---

## Core Architectural Components

### 1. Frontend (Next.js 16 + Tailwind CSS v4)
The developer dashboard and evidence explorer. It provides the UI for users to view their SkillGraph, CodeRisk findings, and Capability states. It communicates with the backend via typed `ApiClient`, handles real-time updates via bounded polling (MAX 75 attempts), renders interactive Cytoscape graphs and Recharts time-series charts, and manages authentication sessions via `@supabase/supabase-js`.

### 2. Backend API (FastAPI)
The core orchestration layer. It handles user requests, repository registration, job queuing, and querying the generated intelligence layers.
- **Routes**: `/developers`, `/github`, `/projects`, `/repositories`, `/analysis`
- **Responsibilities**: API serving, cryptographic JWT verification, database querying, queue management.

### 3. Worker Fleet (Python / PostgreSQL-native Queue)
Repository mining and analysis cannot happen within an HTTP request lifecycle. The system relies on background workers (`workers/runner.py`) using PostgreSQL-native atomic row locking (`SELECT ... FOR UPDATE SKIP LOCKED` on `analysis_jobs`) to perform heavy lifting.
- **Analysis Pipeline (8 Stages)**:
  `QUEUED -> FETCHING -> MINING -> SKILL_GRAPH -> CODE_RISK -> EVIDENCE -> CAPABILITY -> COMPLETED`

### 4. Intelligence Layers
These are logical modules executed primarily by the workers:
- **Repository Miner**: Clones/fetches repositories, extracts metadata, ASTs, and dependencies.
- **CodeRisk Engine**: Runs static analysis and custom rules against the codebase to generate `risk_findings` and paired observations.
- **SkillGraph Builder**: Maps discovered technologies and concepts to the graph schema.
- **Evidence Engine**: Synthesizes raw observations into contextualized `evidence` records.
- **Capability Scorer**: Calculates capability states, diminishing returns, half-life decay, and uncertainty-aware confidence intervals based on the evidence.

### 5. Database (PostgreSQL / Supabase)
A relational schema designed to support graph-like queries without the initial overhead of a dedicated graph database for the Minor MVP. It stores users, repositories, evidence, risk signals, and capability states across 27 tables with Row-Level Security (RLS) enforcement.

### 6. Authentication & Identity
DevTwin uses Supabase Auth for primary user authentication and a hybrid GitHub App flow for secure repository integration.
- **Supabase Auth**: The frontend obtains a JWT which the backend cryptographically verifies using Supabase JWKS (RS256/ES256).
- **Identity Mapping**: `auth.uid()` maps 1:1 to an internal `developers.auth_user_id`. Developer records are created explicitly via `POST /developers/me`.
- **GitHub Integration**: Uses a hybrid GitHub App installation flow with user authorization. The OAuth state is protected by an explicit atomic claim in PostgreSQL to prevent concurrent processing. The temporary user token is never persisted.
- **GitHub Data Access**: Uses on-demand, short-lived installation access tokens. Persistent GitHub credentials are not stored in the database.
- **Safe Disconnect**: The disconnect operation inactivates the connection but preserves historical DevTwin analysis data.

---

## Data Flow Pipeline

```text
POST /analysis/jobs (Triggered by user/system)
       ↓
Create Analysis Job (Status: QUEUED)
       ↓
Job Queue (PostgreSQL-native `analysis_jobs` via FOR UPDATE SKIP LOCKED)
       ↓
Background Worker Picks Up Job (Status: PROCESSING)
       ↓
1. Fetch Repository Data (GitHub App Installation Token / Safe Tarball Stream)
       ↓
2. Mine Repository (AST parsing, Dependency resolution, Language classification)
       ↓
3. Build SkillGraph (Taxonomy mapping, Entity deduplication)
       ↓
4. Run CodeRisk Analysis (Static rules: Security, Reliability, Maintainability)
       ↓
5. Generate Evidence (Map findings to developer capabilities with strength & polarity)
       ↓
6. Update Capability State (Calculate scores, confidence, append to capability_history)
       ↓
7. Atomic Stage 8 Completion (Set analysis_runs and analysis_jobs to COMPLETED)
       ↓
Persist to Database (PostgreSQL / Supabase)
       ↓
Frontend Dashboard Updates (via bounded polling and real-time refresh)
```

## AI / ML Boundaries
- AI is an intelligence layer, not the entire application.
- LLM APIs may be used for semantic skill mapping, concept extraction, or generating human-readable explanations of complex evidence.
- The core capability scoring relies on deterministic mathematical aggregation (sigmoid saturation, diminishing returns, half-life decay) before any black-box ML models are applied.
