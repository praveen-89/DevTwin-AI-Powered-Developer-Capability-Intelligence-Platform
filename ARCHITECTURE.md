---
Status: Active
Version: 1.0
Last Updated: 2026-09-08
Source of Truth: ARCHITECTURE.md
---

# Architecture Specification

## System Overview
```text
Developer
 ↓
Frontend (Next.js)
 ↓
API (FastAPI)
 ↓
Analysis Job (PostgreSQL / Redis)
 ↓
Worker (Python)
 ↓
Repository Mining (Git/AST/Linguist)
 ├── SkillGraph Mapper
 └── CodeRisk Engine
        ↓
Evidence Engine
 ↓
Capability Engine (Math Model)
 ↓
Database (PostgreSQL)
 ↓
Dashboard
```

## Components
*   **Frontend**: Next.js providing the SSR and client-side Dashboard.
*   **Backend**: FastAPI serving REST endpoints for the frontend.
*   **Database**: PostgreSQL (Supabase) storing normalized relational data, SkillGraph, and capabilities.
*   **Queue**: Redis for managing background tasks.
*   **Workers**: Python background processes responsible for asynchronous repository analysis.
*   **Engines** (Logical Modules in Worker):
    *   **Repository Miner**: Extracts syntax trees, dependencies, and git history.
    *   **CodeRisk Engine**: Executes static analysis heuristics.
    *   **SkillGraph Builder**: Maps mined terms to the internal taxonomy.
    *   **Evidence Engine**: Translates raw facts into contextualized support.
    *   **Capability Engine**: Aggregates evidence weights into final normalized scores.

## Data Flow (Analysis Lifecycle)
1. Developer registers repo -> API creates `analysis_jobs`.
2. Worker picks up job -> creates `analysis_runs`.
3. Worker clones repo -> runs Miner -> creates `observations`.
4. Worker runs CodeRisk -> creates `risk_findings`.
5. Worker runs Evidence Engine -> creates `evidence`.
6. Worker runs Capability Engine -> updates `developer_capabilities` and logs `capability_history`.

## Analysis State Machine
```text
QUEUED
 ↓
FETCHING
 ↓
MINING
 ↓
SKILL_GRAPH
 ↓
CODE_RISK
 ↓
CAPABILITY
 ↓
COMPLETED
```
*Failure path*: `ANY STATE -> FAILED`.

## Domain Architecture
*   **Skill, Technology, Concept**: The rigid, public taxonomy.
*   **Observation**: An immutable, raw fact from a repo.
*   **Evidence**: A contextualized interpretation of an observation.
*   **Capability**: A developer's scored ability against a Skill/Tech/Concept.
*   **Risk**: A detected codebase flaw.
*   **Skill Gap**: The delta between target and capability.

## Database Architecture
DevTwin utilizes a normalized PostgreSQL database, strictly relying on UUID internal identifiers and enforcing referential integrity via Junction Tables and Exclusive Arcs.
*Canonical Reference*: `docs/11_DATABASE_SCHEMA.md` and `docs/DOMAIN_MODEL.md`.

## API Architecture
RESTful API built with FastAPI, returning structured JSON contracts.
*Canonical Reference*: `docs/12_API_SPECIFICATION.md`.

## Security Architecture
*   **Authentication**: JWT-based authentication.
*   **Authorization & Data Isolation**: Database Row Level Security (RLS) ensures developers can only query their own capabilities and projects.
*   **Secrets**: External GitHub access tokens are stored securely outside the core database or strongly encrypted; never stored plaintext in `github_accounts`.

## AI/ML Architecture
**Strict Separation of Concerns**:
*   **Deterministic Analysis**: Extracting ASTs, finding dependencies, parsing git history, and calculating the final Capability score ($Z$-normalized math) are entirely deterministic.
*   **LLM (Bounded)**: Used *only* for semantic mapping (e.g., mapping an unknown library name to a known Concept) or generating human-readable explanations of a capability score based on evidence. LLMs **DO NOT** output capability scores.
*   **ML (Future)**: Deep Knowledge Tracing or Graph Neural Networks are reserved for the Major scope.

## Scalability
*   The worker fleet scales horizontally via Redis.
*   The API layer is stateless.
*   Database scaling is deferred until Major scope, as PostgreSQL can handle millions of observations via proper indexing (detailed in `11_DATABASE_SCHEMA.md`).
