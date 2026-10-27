---
Status: Active
Version: 2.4
Last Updated: 2026-10-28
Source of Truth: MEMORY.md
---

# Project Memory

*Source of Truth Context: This document defines durable, long-term project knowledge to quickly onboard future human and AI agents. It is NOT a changelog.*

## Checkpoint Status

CURRENT PROJECT:
DevTwin — AI-Powered Developer Capability Intelligence Platform

CURRENT PHASE:
Worker Activation & Real End-to-End Analysis Verified (Checkpoint 31)

## Implementation Status

### Backend (FastAPI / Python) — COMPLETE
All backend features are implemented, tested, and running on port 8000.
Backend virtual environment: `backend/.venv/`
Start command: `backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
Worker start commands:
- From root: `backend\.venv\Scripts\python.exe workers\runner.py --poll` (or `--once`)
- From backend: `cd backend; .venv\Scripts\python.exe -m app.workers.runner --poll` (or `--once`)
**Test Suite: 385 tests passing** (verified 2026-10-28 — Checkpoint 31 re-verified)

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

#### Auth Pattern (Checkpoint 23 — Supabase Session Integration)
- `@supabase/supabase-js` v2 is installed and integrated via `frontend/src/lib/supabase.ts`
- `AuthProvider` (in `auth-context.tsx`) uses `supabase.auth.getSession()` to restore sessions on mount
- `supabase.auth.onAuthStateChange` synchronises token state with `apiClient` automatically
- `signIn(email, password)` and `signUp(email, password)` methods are exposed through `AuthState`
- Token refresh and session persistence are handled automatically by `@supabase/supabase-js`
- A custom `<AuthModal />` (`frontend/src/components/auth/auth-modal.tsx`) replaces `window.prompt()`
- Modal supports Sign In / Sign Up tabs with validation, loading states, error banners, and email confirmation notice
- **Fallback**: When `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` are not set, `isSupabaseConfigured()` returns false and the modal shows a dev-token textarea fallback
- A 404 on `GET /developers/me` triggers auto-provisioning via `POST /developers/me`
- Token is cleared on 401 (expired/invalid) via `signOut()`

**Backend GitHub Callback (Checkpoint 23)**: All `/github/callback` error paths now return `RedirectResponse(302)` to `FRONTEND_URL/?github_error=<safe_code>` or `FRONTEND_URL/?github=success`. Open redirect is prevented by allowlisting. `FRONTEND_URL` is validated in `config.py`.

**Frontend Callback Feedback (Checkpoint 23)**: `OverviewView` reads `?github=success` / `?github_error=<code>` on mount, shows accessible banners, refreshes GitHub status, and sanitizes the URL with `history.replaceState`.

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

### Checkpoint 31 — Verified E2E Run (2026-10-28)
- Analysis run `3bfc7727-8c19-46da-9490-5faf245e4940`: COMPLETED in ~20s
- Persisted: 86 observations, 35 evidence records, 38 developer_capabilities, 1 risk_finding, 4 skills
- Frontend: all 6 pages (/, /repositories, /evidence, /capabilities, /skillgraph, /coderisk) verified with authenticated session
- Production build: all 7 routes compiled successfully (`npm run build` exit 0)
- Test baselines: 385 backend tests passing, 64 frontend tests passing, 0 TypeScript errors
- Note: 4 orphaned runs stuck at CODE_RISK from earlier interrupted sessions — non-blocking

## Forbidden Behaviors
Agents must NOT:
- Invent requirements
- Silently change architecture
- Introduce technologies without justification and ADR
- Modify database design casually
- Create undocumented APIs
- Claim implementation when only specification exists

## Known Limitations (Minor MVP)
- Supabase Auth UI is now implemented with email/password sign-in and sign-up via `@supabase/supabase-js` v2
- When Supabase env vars are absent, the UI falls back gracefully to a dev-token textarea form
- Worker process is operational and verified end-to-end; can be executed via daemon polling loop (`workers\runner.py --poll`)
- No email/notification on analysis completion
- No multi-developer team features

## Current Technology Stack
- Frontend: Next.js / TypeScript / Tailwind CSS v4
- Backend: FastAPI / Python
- Database: PostgreSQL / Supabase (27 tables with RLS)
- Queue: PostgreSQL-native (NOT Redis)
- Testing: pytest (backend), Vitest (frontend — 64 tests), Playwright (E2E)

## Project Concepts Reference
- **Skill ≠ Capability**: "Backend Development" is a Skill. A developer's "Capability in Backend Development" is a scored metric.
- **Observation ≠ Evidence**: Observation = raw fact from code. Evidence = contextualized interpretation.
- **Analysis Job ≠ Analysis Run**: Job = user request to process. Run = single execution attempt.
