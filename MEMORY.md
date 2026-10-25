---
Status: Active
Version: 2.0
Last Updated: 2026-10-25
Source of Truth: MEMORY.md
---

# Project Memory

*Source of Truth Context: This document defines durable, long-term project knowledge to quickly onboard future human and AI agents. It is NOT a changelog.*

## Checkpoint Status

CURRENT PROJECT:
DevTwin — AI-Powered Developer Capability Intelligence Platform

CURRENT PHASE:
Full-Stack MVP — Live Integration Ready

## Implementation Status

### Backend (FastAPI / Python) — COMPLETE
All backend features are implemented, tested, and running on port 8000.
Backend virtual environment: `backend/.venv/`
Start command: `backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
**Test Suite: 377 tests passing** (as of 2026-10-25)

#### Completed Backend Steps
- Steps 1–4A: Project foundation, DB schema, domain model, migrations
- Step 5A: OAuth callback foundation (PKCE state machine)
- Step 5B: GitHub identity verification (`get_authenticated_user`, `list_user_installations`)
- Step 5C: GitHub account linking (INSERT/UPDATE/409 conflict with rollback safety)
- Step 5D: `installation_id` persistence during OAuth callback
- Step 6A: `/github/status` endpoint
- Step 6B–6I: Mining, SkillGraph, CodeRisk, Evidence, Capability, Pipeline completion
- Step 6J: Core Intelligence Read APIs
- Step 7F (backend): `/github/disconnect` endpoint
- Step 7G (backend): `GET /github/repositories` — lists accessible repos via installation token
- Step 8A: Git integrity & live integration preflight audit
- Step 8B: Authentication architecture & configuration audit

#### Active Backend Endpoints
| Method | Path | Auth Required | Description |
|--------|------|--------------|-------------|
| GET | `/health` | No | Health check |
| GET | `/health/database` | No | DB reachability check |
| GET | `/developers/me` | Yes | Get/create developer profile |
| POST | `/developers/me` | Yes | Provision developer profile |
| GET | `/github/install` | Yes | Generate GitHub App install URL |
| GET | `/github/callback` | No (state-bound) | OAuth callback handler |
| GET | `/github/status` | Yes | GitHub connection status |
| DELETE | `/github/disconnect` | Yes | Disconnect GitHub account |
| GET | `/github/repositories` | Yes | List accessible GitHub repos via installation token |
| GET/POST | `/projects` | Yes | List / create projects |
| GET/POST | `/repositories` | Yes | List / register repositories |
| GET | `/repositories/{id}` | Yes | Get single repository |
| GET | `/repositories/{id}/risks` | Yes | CodeRisk findings |
| GET | `/repositories/{id}/skillgraph` | Yes | SkillGraph data |
| POST | `/analysis/jobs` | Yes | Submit analysis job |
| GET | `/analysis/jobs/{id}` | Yes | Get analysis job |
| GET | `/analysis/jobs/{id}/runs` | Yes | Get analysis runs |
| GET | `/developers/me/capabilities` | Yes | Paginated capabilities |
| GET | `/developers/me/capabilities/history` | Yes | Capability history |
| GET | `/developers/me/evidence` | Yes | Evidence list |

### Frontend (Next.js / TypeScript / Tailwind CSS v4) — COMPLETE
Frontend is running on port 3000.
Start command: `npm run dev` from `frontend/`

#### Completed Frontend Steps
- Step 7A: Foundation & design system (dark mode, sidebar, typography, all UI primitives)
- Step 7B: Frontend–backend integration audit & contract matrix verification
- Step 7C: Interactive visualizations — Cytoscape SkillGraph canvas + Recharts temporal capability trend charts
- Step 7D: Browser E2E & live integration (Playwright 40 tests, Vitest 36/36, ESLint clean, Next.js build clean)
- Step 7E: Authenticated E2E & git integrity audit (47 Playwright, 21 passed, 26 skipped)
- Step 7F (frontend): GitHub connect flow, Repositories page, Add Repository dialog
- Step 7G (frontend): Full dashboard — GitHub status card, repo selector, analysis pipeline card, capabilities card, risks card

#### Frontend Pages
| Route | Component | Description |
|-------|-----------|-------------|
| `/` | `OverviewView` | Dashboard — GitHub status, repo selector, analysis pipeline, capabilities, risks |
| `/repositories` | `RepositoriesPage` | Repo list + detail + analysis trigger |
| `/capabilities` | `CapabilitiesPage` | Paginated capability scores with history chart |
| `/coderisk` | `CodeRiskPage` | Risk findings table with severity filters |
| `/skillgraph` | `SkillGraphPage` | Cytoscape interactive graph + dependency list |
| `/evidence` | `EvidencePage` | Evidence list with type/polarity filters |

#### Auth Pattern (Dev-Mode)
- The frontend uses `sessionStorage.devtwin_dev_token` for development
- The "Sign in" button prompts for a raw Supabase access token (JWT)
- `AuthContext` wires the token to `apiClient` and fetches `GET /developers/me`
- A 404 triggers auto-provisioning via `POST /developers/me`
- Token is cleared on 401 (expired/invalid)

**IMPORTANT**: This is a dev-mode workaround. A proper Supabase Auth UI integration (with `@supabase/ssr` and `@supabase/auth-ui-react`) has NOT been implemented yet.

## Identity & Mapping Rules
- **Developer Identity Mapping**: `Supabase auth.users.id -> developers.auth_user_id`. `developers.id` is a unique internal UUID. Do NOT force `developers.id = auth.uid()`.
- GitHub IDs remain purely external identifiers.

## Architecture Notes

### Queue
The queue is PostgreSQL-native (using `analysis_jobs` table + polling), NOT Redis, despite the stack listing. Redis was removed from the active implementation.

### GitHub App OAuth Flow
1. `GET /github/install` → returns `install_url` with PKCE state
2. User installs GitHub App → GitHub redirects to `GET /github/callback?code=&state=&installation_id=`
3. Callback: exchanges code → OAuth token → verifies identity → links installation → stores `installation_id`
4. `GET /github/status` → confirms `is_connected=true`, `is_installed=true`
5. `GET /github/repositories` → ephemeral installation token → lists repos
6. `POST /repositories` with `project_id` + `github_repo_id` → registers repo
7. `POST /analysis/jobs` with `repository_id` → triggers pipeline

### Analysis Pipeline Stages
`QUEUED → FETCHING → MINING → SKILL_GRAPH → CODE_RISK → CAPABILITY → COMPLETED/FAILED`

## Forbidden Behaviors
Agents must NOT:
- Invent requirements
- Silently change architecture
- Introduce technologies without justification and ADR
- Modify database design casually
- Create undocumented APIs
- Claim implementation when only specification exists

## Known Limitations (Minor MVP)
- Dev-mode JWT auth (no Supabase sign-in UI)
- No worker process running — analysis jobs queue but won't process unless worker is started separately
- No email/notification on analysis completion
- No multi-developer team features

## Current Technology Stack
- Frontend: Next.js / TypeScript / Tailwind CSS v4
- Backend: FastAPI / Python
- Database: PostgreSQL / Supabase (27 tables with RLS)
- Queue: PostgreSQL-native (NOT Redis)
- Testing: pytest (backend), Vitest + Playwright (frontend)

## Project Concepts Reference
- **Skill ≠ Capability**: "Backend Development" is a Skill. A developer's "Capability in Backend Development" is a scored metric.
- **Observation ≠ Evidence**: Observation = raw fact from code. Evidence = contextualized interpretation.
- **Analysis Job ≠ Analysis Run**: Job = user request to process. Run = single execution attempt.
