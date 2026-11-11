# 17. Development Roadmap

---
Status: Active
Version: 2.0
Last Updated: 2026-11-12
---

## Phase Overview

```text
PHASE 1  [Backend Foundation]               -> COMPLETED
PHASE 2  [Database / Supabase Migrations]   -> COMPLETED
PHASE 3  [Authentication & Provisioning]   -> COMPLETED
PHASE 4  [GitHub App Integration]           -> COMPLETED
PHASE 5  [Repository Ingestion & Fetching]  -> COMPLETED
PHASE 6  [Repository Mining Engine]         -> COMPLETED
PHASE 7  [SkillGraph Engine]                -> COMPLETED
PHASE 8  [CodeRisk Engine]                  -> COMPLETED
PHASE 9  [Evidence Engine]                  -> COMPLETED
PHASE 10 [Capability Scoring Engine]        -> COMPLETED
PHASE 11 [REST Read APIs & Integration]     -> COMPLETED
PHASE 12 [Frontend Dashboard & UI]          -> COMPLETED
PHASE 13 [Testing Pyramid & Live E2E Run]   -> COMPLETED (Checkpoint 31)
PHASE 14 [Research Evaluation & Benchmarks] -> ACTIVE / NEXT
```

---

## Detailed Phase Status

### PHASE 1 — Backend Foundation
**Status: COMPLETED**
- FastAPI application factory with structured logging, CORS middleware, and settings validation (`backend/app/main.py`, `config.py`).
- Asynchronous database connection handling via SQLAlchemy and `asyncpg`.
- Health and database readiness endpoints (`GET /health`, `GET /health/database`).

### PHASE 2 — Database / Supabase Schema & Security
**Status: COMPLETED**
- 5 SQL migrations defining all 27 tables with normalized relationships, UUID primary keys, and Exclusive Arc constraints (`database/migrations/`).
- Defense-in-depth Row-Level Security (RLS) policies protecting tenant isolation based on `auth.users.id`.
- NULL-ownership regression hardening patches applied.

### PHASE 3 — Authentication & Identity Provisioning
**Status: COMPLETED**
- Cryptographic Supabase JWT verification using remote JWKS endpoint (`backend/app/api/dependencies/auth.py`).
- Explicit identity mapping `auth.uid() -> developers.auth_user_id -> developers.id`.
- Auto-provisioning via `POST /developers/me` on 404.

### PHASE 4 — GitHub App Integration & OAuth Flow
**Status: COMPLETED**
- GitHub App service layer for app JWT generation, user installation listing, and short-lived token generation (`backend/app/services/github/`).
- `GET /github/install` with cryptographically secure state generation.
- `GET /github/callback` with atomic state claim and safe 302 redirect.
- `GET /github/status` and `DELETE /github/disconnect`.
- `GET /github/repositories` using ephemeral installation access tokens.

### PHASE 5 — Repository Ingestion & Fetching
**Status: COMPLETED**
- `POST /repositories` and `GET /repositories` with project ownership enforcement.
- Safe tarball archive fetching and streaming download (50 MB limit).
- Path traversal and Zip Slip guard (`is_safe_tar_member`).
- Ephemeral isolated temporary workspace lifecycle with guaranteed cleanup.

### PHASE 6 — Repository Mining
**Status: COMPLETED**
- Safe file traversal excluding `.git`, `node_modules`, `venv`, etc.
- Language classification and byte-weighted distribution calculation.
- Dependency extraction from `package.json`, `requirements.txt`, `Cargo.toml`.
- Python AST parsing extracting classes, async/documented functions, and imports.

### PHASE 7 — SkillGraph Engine
**Status: COMPLETED**
- Grounded taxonomy mapping for canonical languages and popular dependencies.
- Fallback handling for ungrounded packages without hallucination.
- AST concept mapping (`Object-Oriented Programming`, `Asynchronous Programming`, etc.).
- Provenance-backed observation creation, deduplication, and database persistence.

### PHASE 8 — CodeRisk Engine
**Status: COMPLETED**
- Static risk analyzer with 8 rules (`SEC-001`–`SEC-003`, `REL-001`–`REL-002`, `MAINT-001`–`MAINT-002`, `TEST-001`).
- Safe AST inspection for `subprocess` with `shell=True`.
- Secret redaction from evidence code snippets.
- Generation of `RISK_OBSERVED` observations (Risk ≠ Competence).

### PHASE 9 — Evidence Engine
**Status: COMPLETED**
- Deterministic translation of raw observations into contextualized `evidence` records.
- Strength (`0..1`), directness (`0..1`), reliability (`0..1`), and polarity (`-1..+1`) scoring.
- Junction table linking (`evidence_skills`, `evidence_technologies`, `evidence_concepts`).
- Exclusion of pure diagnostic warnings from capability scoring.

### PHASE 10 — Capability Scoring Engine
**Status: COMPLETED**
- Mathematical aggregation model v1 (`backend/app/capability/scorer.py`):
  - Normalized score: `score = clamp(sigmoid(sum / 3.0), 0.01, 0.99)`.
  - Diminishing returns: `w_k / sqrt(k)`.
  - Half-life temporal decay (365 days).
  - Uncertainty-aware confidence: `clamp(q * d * c * R_mean, 0.05, 0.98)`.
- Append-only `capability_history` logging for temporal trend analysis.
- Exclusive Arc validation across skills, technologies, and concepts.

### PHASE 11 — REST Read APIs & Worker Pipeline Integration
**Status: COMPLETED**
- Core intelligence read endpoints: `/developers/me/capabilities`, `/developers/me/capabilities/history`, `/developers/me/evidence`, `/repositories/{id}/risks`, `/repositories/{id}/skillgraph`.
- Atomic PostgreSQL-native queue runner (`workers/runner.py`) with `SELECT ... FOR UPDATE SKIP LOCKED`.
- Atomic Stage 8 terminal completion lifecycle (`analysis_runs` -> `COMPLETED`, `analysis_jobs` -> `COMPLETED`).

### PHASE 12 — Frontend Dashboard & Visualizations
**Status: COMPLETED**
- Next.js 16 (App Router, Turbopack, Tailwind CSS v4, TypeScript).
- 6 complete pages: `/` (Overview Dashboard), `/repositories`, `/capabilities`, `/coderisk`, `/skillgraph`, `/evidence`.
- Interactive Cytoscape SkillGraph canvas with zoom/pan and accessible tabular toggle.
- Recharts temporal capability trend charts.
- In-app Supabase Auth Modal (Sign In / Sign Up) with graceful dev-token fallback.

### PHASE 13 — Testing Pyramid & Live E2E Run Verification
**Status: COMPLETED (Checkpoint 31)**
- 385 backend pytest tests passing.
- 64 frontend Vitest tests passing across 7 suites.
- 47 Playwright browser E2E tests (21 passing, 26 skipped pending live credentials).
- Verified live E2E run (`3bfc7727-8c19-46da-9490-5faf245e4940`) processing a multi-language repository through all 8 stages in ~20s.

---

### PHASE 14 — Research Evaluation (ACTIVE / NEXT)
- Curated evaluation dataset of open-source repositories representing varied expertise levels.
- Quantitative verification of provenance traceability (100% target).
- CodeRisk false positive rate assessment and capability heuristic validation.
