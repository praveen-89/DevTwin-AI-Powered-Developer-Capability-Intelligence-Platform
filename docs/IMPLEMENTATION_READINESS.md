# Implementation Readiness

---
Status: Active
Version: 1.2
Last Updated: 2026-09-09
---

## Milestone v0.1 — COMPLETED: Backend & Supabase Foundation

---

## FROZEN Specifications

| Area | Document | Status |
|---|---|---|
| Product Requirements | `PRD.md` | FROZEN |
| UX Design Intent | `DESIGN.md` | FROZEN |
| Architecture | `ARCHITECTURE.md` | FROZEN |
| Domain Model | `docs/DOMAIN_MODEL.md` | FROZEN |
| Database Schema | `docs/11_DATABASE_SCHEMA.md` | FROZEN |
| API Contracts | `docs/12_API_SPECIFICATION.md` | FROZEN |
| Analysis Pipeline | `docs/13_ANALYSIS_PIPELINE.md` | FROZEN |
| Evidence Model | `docs/09_EVIDENCE_MODEL.md` | FROZEN |
| Capability Model | `docs/06_CAPABILITY_MODEL.md` | FROZEN |
| Scoring Model | `docs/10_SCORING_MODEL.md` | FROZEN |
| Minor vs Major Scope | `docs/15_MINOR_VS_MAJOR.md` | FROZEN |
| Engineering Rules | `RULES.md` | FROZEN |
| Agent Protocol | `AGENTS.md` | FROZEN |

---

## IMPLEMENTED (v0.1)

| Area | Status | Location |
|---|---|---|
| FastAPI application factory | IMPLEMENTED | `backend/app/main.py` |
| Settings / configuration validation | IMPLEMENTED | `backend/app/core/config.py` |
| Structured logging | IMPLEMENTED | `backend/app/core/logging.py` |
| Async DB connection (SQLAlchemy+asyncpg) | IMPLEMENTED | `backend/app/db/connection.py` |
| Health endpoint (`GET /health`) | IMPLEMENTED | `backend/app/api/routes/health.py` |
| DB readiness endpoint (`GET /health/database`) | IMPLEMENTED | `backend/app/api/routes/health.py` |
| Initial schema migration (all domain tables) | IMPLEMENTED | `database/migrations/001_initial_schema.sql` |
| RLS policies migration | IMPLEMENTED | `database/migrations/002_rls_policies.sql` |
| RLS security hardening migration | IMPLEMENTED | `database/migrations/003_rls_hardening.sql` |
| Backend unit tests (health, config, RLS security) | IMPLEMENTED | `backend/tests/` |
| `.env.example` with actual required vars | IMPLEMENTED | `.env.example` |

---

## IMPLEMENTED (v0.2 — GitHub Auth & Installation)

| Area | Status | Location |
|---|---|---|
| Supabase Auth JWKS verification | IMPLEMENTED | `backend/app/api/dependencies/auth.py` |
| `POST /developers/me` provisioning | IMPLEMENTED | `backend/app/api/routes/developers.py` |
| GitHub App configuration + PKCE encryption utility | IMPLEMENTED | `backend/app/core/config.py`, `backend/app/core/crypto.py` |
| GitHub connection state model | IMPLEMENTED | `backend/app/models/github_connection_state.py` |
| GitHub account model | IMPLEMENTED | `backend/app/models/github_account.py` |
| `create_pending_state` / `claim_state` service | IMPLEMENTED | `backend/app/services/github/state.py` |
| GitHub App JWT generation | IMPLEMENTED | `backend/app/services/github/auth.py` |
| GitHub HTTP client (`get_installation`, etc.) | IMPLEMENTED | `backend/app/services/github/client.py` |
| `GET /github/install` | IMPLEMENTED | `backend/app/api/routes/github.py` |
| `GET /github/callback` | IMPLEMENTED | `backend/app/api/routes/github.py` |
| GitHub account linking (first link, reconnect, conflict) | IMPLEMENTED | `backend/app/api/routes/github.py` |
| Migration: `github_connection_states` + `github_accounts` | IMPLEMENTED | `database/migrations/004_v02_auth_github.sql`, `005_v02_github_pkce.sql` |
| GitHub integration tests | IMPLEMENTED | `backend/tests/test_github.py`, `backend/tests/services/test_github_client.py` |

---

## PENDING Implementation

| Area | Status |
|---|---|
| GET /github/status | NOT STARTED |
| POST /github/disconnect | NOT STARTED |
| Repository ingestion | NOT STARTED |
| Repository mining workers | NOT STARTED |
| SkillGraph engine | NOT STARTED |
| CodeRisk engine | NOT STARTED |
| Evidence Engine | NOT STARTED |
| Capability calculation | NOT STARTED |
| Business API endpoints | NOT STARTED |
| Next.js dashboard | NOT STARTED |

---

## Next Milestone
**v0.2 remaining — GitHub Status & Disconnect + Repository Registration**
1. `GET /github/status` endpoint.
2. `POST /github/disconnect` endpoint.
3. Repository listing / installation access token service.
4. Repository registration and cloning.
