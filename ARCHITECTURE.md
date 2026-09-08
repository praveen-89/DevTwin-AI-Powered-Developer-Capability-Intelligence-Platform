---
Status: Active
Version: 1.1
Last Updated: 2026-09-08
Source of Truth: ARCHITECTURE.md
---

# Architecture Specification

*Source of Truth Context: This document defines how the system is structurally designed.*

## System Overview
```text
Developer
 ↓
Frontend (Next.js)
 ↓
API (FastAPI)
 ↓
Analysis Job (Queue Request)
 ↓
Worker (Python)
 ↓
Analysis Run (Execution Attempt)
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
*   **Queue**: Redis for managing `analysis_jobs`.
*   **Workers**: Python background processes responsible for asynchronous `analysis_runs`.
*   **Engines** (Logical Modules in Worker):
    *   **Repository Miner**: Extracts syntax trees, dependencies, and git history.
    *   **CodeRisk Engine**: Executes static analysis heuristics.
    *   **SkillGraph Builder**: Maps mined terms to the internal taxonomy.
    *   **Evidence Engine**: Translates raw facts into contextualized support.
    *   **Capability Engine**: Aggregates evidence weights into final normalized scores.

## Developer Identity & Auth Architecture
**Mapping**: `Supabase auth.users.id -> developers.auth_user_id -> developers.id`
We map the external authentication provider (Supabase Auth) via a dedicated column `auth_user_id`. The internal `developers.id` remains a pure DevTwin UUIDv4. This prevents tight coupling and ensures RLS works gracefully.

## Security & Credential Architecture
**GitHub Tokens**: Plaintext GitHub access tokens are NEVER stored in DevTwin.
*   **Development**: Local `.env` files manage temporary Personal Access Tokens.
*   **Production**: DevTwin uses a Credential/Secret Store (e.g., Vault, or Supabase Vault/pgsodium). The `access_token_enc` column explicitly means: *encrypted token material or an external credential reference*.
*   **Rules**: Tokens are rotated as necessary. Logs must never contain tokens. Minimum read-only repository scopes are enforced.

## Data Flow (Analysis Lifecycle)
1. Developer registers repo via OAuth -> API creates `analysis_jobs`.
2. Worker picks up job -> creates `analysis_runs` (an execution attempt).
3. Worker clones repo -> runs Miner -> creates `observations`.
4. Worker runs CodeRisk -> creates `risk_findings`.
5. Worker runs Evidence Engine -> creates `evidence`.
6. Worker runs Capability Engine -> updates `developer_capabilities` and appends to `capability_history`.

## Canonical Analysis State Machine
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
*Failure path*: `ANY STATE -> FAILED`

## Domain Architecture
*   **Skill, Technology, Concept**: The rigid, public taxonomy.
*   **Observation**: An immutable, raw fact from a repo.
*   **Evidence**: A contextualized interpretation of an observation.
*   **Risk**: A detected codebase flaw (an observation, not an automatic competence penalty).
*   **Capability**: A developer's scored ability against a target.
*   **Skill Gap**: The delta between target and capability.

## Database & API Architecture
*   Database: `docs/11_DATABASE_SCHEMA.md`
*   API Contracts: `docs/12_API_SPECIFICATION.md`

## AI/ML Architecture
**Strict Separation of Concerns**:
*   **Deterministic Analysis**: AST extraction, Git parsing, and Capability math ($Z$-normalized logic) are purely deterministic.
*   **LLM (Bounded)**: Used *only* for semantic mapping or generating human-readable explanations of a capability score based on proven evidence.
*   **ML (Future)**: Reserved for Major scope (Capability prediction).
