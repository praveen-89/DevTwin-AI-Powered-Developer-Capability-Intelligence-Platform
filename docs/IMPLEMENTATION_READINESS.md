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

## PENDING Implementation

| Area | Status |
|---|---|
| GitHub App Hybrid integration | DESIGNED / READY |
| Supabase Auth JWKS integration | DESIGNED / READY |
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
**v0.2 — GitHub Auth & Repository Registration**
1. Supabase Auth JWKS verification in FastAPI (IMPLEMENTED).
2. `POST /developers/me` provisioning (IMPLEMENTED).
3. Follow-up Migration (code_verifier_enc, UNIQUE(developer_id), disconnected_at).
4. GitHub App config + PKCE encryption utility.
5. GitHub OAuth/App backend service.
6. GitHub install & callback routes.
7. Account-linking transaction policy.
8. Status & disconnect endpoints.
9. Security/regression tests for GitHub integration.
10. Repository listing / installation access token service.
