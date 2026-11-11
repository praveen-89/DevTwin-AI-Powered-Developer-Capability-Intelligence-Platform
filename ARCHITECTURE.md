---
Status: Active
Version: 2.0
Last Updated: 2026-11-12
Source of Truth: ARCHITECTURE.md
---

# Architecture Specification

*Source of Truth Context: This document defines how the system is structurally designed.*

## System Overview
```text
Developer
 ↓
Frontend (Next.js 16 + Tailwind CSS v4)
 ↓
API (FastAPI REST Endpoints)
 ↓
Analysis Job (PostgreSQL-native Queue)
 ↓
Worker (Python Analysis Runner)
 ↓
Analysis Run (Execution Attempt)
 ↓
Repository Mining (Git/AST/Linguist)
 ├── SkillGraph Builder
 └── CodeRisk Engine
        ↓
Evidence Engine
 ↓
Capability Engine (Mathematical Scoring Model)
 ↓
Database (PostgreSQL / Supabase with RLS)
 ↓
Interactive Dashboard (Cytoscape Graph + Recharts Temporal Analytics)
```

## Components
*   **Frontend**: Next.js 16 (App Router, Turbopack, Tailwind CSS v4, TypeScript) serving the DevTwin Capability Dashboard. Communicates with backend via typed `ApiClient`, provides `AuthProvider` for session token propagation (with `@supabase/supabase-js` session auto-restoration, in-app `<AuthModal />`, and dev-token fallback), and renders Overview, Repositories, Capabilities (with Recharts temporal history), CodeRisk, SkillGraph (with interactive Cytoscape canvas and accessible table toggle), and Evidence views.
*   **Backend**: FastAPI serving 18 active REST endpoints across `/health`, `/developers`, `/github`, `/projects`, `/repositories`, and `/analysis`.
*   **Database**: PostgreSQL (Supabase) storing normalized relational data (27 tables with Row-Level Security policies).
*   **Queue**: PostgreSQL-native job queue using the `analysis_jobs` table with atomic `SELECT ... FOR UPDATE SKIP LOCKED` claiming. (Redis was evaluated and removed for Minor MVP scope; see ADR-018).
*   **Workers**: Python background processes (`workers/runner.py` / `backend/app/workers/runner.py`) responsible for asynchronous `analysis_runs` with bounded retry limits (`MAX_JOB_ATTEMPTS = 3`).
*   **Engines** (Logical Modules in Worker):
    *   **Repository Miner**: Safely extracts file metrics, dependencies (`package.json`, `requirements.txt`, `Cargo.toml`), and Python AST definitions (classes, async functions, imports).
    *   **SkillGraph Builder**: Maps mined languages and dependencies to the internal taxonomy, creating provenance-backed observations.
    *   **CodeRisk Engine**: Executes 8 static analysis heuristics (`SEC-001`–`003`, `REL-001`–`002`, `MAINT-001`–`002`, `TEST-001`) with secret redaction.
    *   **Evidence Engine**: Translates raw observations into contextualized support with assigned strength, directness, reliability, and polarity (`-1.0` to `+1.0`).
    *   **Capability Engine**: Aggregates evidence weights into normalized capability scores `[0.01, 0.99]` and uncertainty-aware confidence intervals `[0.05, 0.98]`.

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
2. Worker atomically claims job (`SELECT ... FOR UPDATE SKIP LOCKED`) -> creates `analysis_runs` attempt.
3. Worker fetches & extracts repo tarball into isolated workspace (`temporary_workspace`).
4. Worker runs Miner -> creates `observations` (languages, dependencies, AST declarations).
5. Worker runs SkillGraph Mapper -> links taxonomy nodes & creates taxonomic observations.
6. Worker runs CodeRisk -> creates `risk_findings` and paired `RISK_OBSERVED` observations.
7. Worker runs Evidence Engine -> creates `evidence` records with polarity and strength.
8. Worker runs Capability Engine -> upserts `developer_capabilities` and appends to `capability_history`.
9. Worker marks both `analysis_runs` and `analysis_jobs` as `COMPLETED` with UTC timestamp.

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
EVIDENCE
 ↓
CAPABILITY
 ↓
COMPLETED
```
*Failure path*: `ANY STATE -> FAILED (with sanitized error_code and error_message)`

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
