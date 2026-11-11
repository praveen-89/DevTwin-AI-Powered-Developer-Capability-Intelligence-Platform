---
Status: Active
Version: 2.5
Last Updated: 2026-11-12
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
**Test Suite: 385 tests passing** (verified 2026-11-12 — Checkpoint 31 re-verified)

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

### Checkpoint 32 — Phase 14 Evaluation Harness Built & Live-Executed, n=1 (2026-11-12)
- Built: `scripts/evaluation/dataset.md` (repo set + hand-written ground
  truth for this repository; 8 remaining slots pending GitHub App
  installation scope), `scripts/evaluation/run_evaluation.py` (drives the
  real pipeline via `GET /github/repositories` → `POST /projects` →
  `POST /repositories` → `POST /analysis/jobs`, per ADR-007 — no
  clone/public-URL shortcut), and `scripts/evaluation/compute_metrics.py`
  (reads persisted DB state for extraction precision/recall, provenance
  traceability %, CodeRisk rule/severity breakdown, runtime distribution,
  naive baseline). 9 hermetic unit tests in
  `scripts/evaluation/tests/test_compute_metrics.py`, all passing.
- **Live sweep executed** against the local backend + worker + Supabase
  Postgres for Repo 1 (this repository). Run `aa434657-f902-47df-91a5-948cb0a07f6c`
  reached COMPLETED in 47.64s. Measured results: extraction precision
  0.2391 / recall 0.9167 (low precision explained by an under-enumerated
  ground-truth list, not a pipeline defect — see results doc), 100%
  provenance traceability (122/122 capability rows), CodeRisk: 5 SEC-001
  HIGH + 2 REL-002 MEDIUM + 6 LOW findings (all 5 HIGH findings manually
  reviewed and confirmed false positives — mock tokens in test fixtures),
  capability score distribution max 0.99 / median 0.5395 / 6 of 122
  (4.9%) at or above 0.95. Full writeup: `docs/14_PHASE14_EVALUATION_RESULTS.md`.
- **Real bug found and fixed during this evaluation** (two earlier live
  attempts got permanently stuck at `status="CODE_RISK"` with no error
  recorded): `backend/app/skillgraph/mapper.py` persisted
  `MODULE_IMPORTED` observations with `source_reference["module"] = None`
  for plain `import X` statements (`ast.Import` has no `module` attribute
  — only `ast.ImportFrom` does), which then crashed
  `backend/app/evidence/mapper.py:98`'s `ref.get("module", "").strip()`
  (the `.get()` default doesn't apply when the key exists with value
  `None`). Fixed by falling back to the first entry in `names` as the
  effective module in `skillgraph/mapper.py`, skipping the observation if
  still unavailable. `evidence/mapper.py`, `capability/scorer.py`,
  `capability/service.py`, `skillgraph/taxonomy.py`, and
  `coderisk/rules.py` were NOT modified. All 385 pre-existing backend
  tests still pass after the fix.
- **Still open**: Repos 2–9 in `dataset.md` remain `<PENDING SELECTION>` —
  need the developer to extend the GitHub App installation and pick real
  repos before the 8–12 repo sample-size target is met.
- Results land in `scripts/evaluation/results/` (currently untracked by
  `.gitignore` — flagged for the developer to decide whether to ignore
  it; not decided unilaterally here).

### Checkpoint 33 — Marketing Site + GitHub OAuth Login/Signup (2026-11-12)

- **What changed**: Added a public marketing site (`src/app/(marketing)/`:
  `/`, `/how-it-works`, `/about`) and dedicated `/login` + `/signup` routes
  (one shared `AuthPage` component, two URLs) that call Supabase's
  `signInWithOAuth({ provider: "github" })` via the *existing* Supabase
  client singleton (`src/lib/supabase.ts` — not a second instance). A
  visibly disabled "Continue with Google" button is stubbed for later; it
  is not wired to real Google OAuth. Added `/auth/callback` to land the
  OAuth redirect, wait for `AuthProvider` to pick up the new session
  (unchanged `POST /developers/me` provisioning path), and redirect to
  `/dashboard`, or back to `/login` with a visible error on denial/timeout.
- **Route restructuring**: The Overview dashboard moved from `/` to
  `/dashboard` (route group `src/app/(app)/`) because `/` is now the
  marketing landing page. `/repositories`, `/capabilities`, `/coderisk`,
  `/skillgraph`, `/evidence` keep their URLs, just regrouped under
  `(app)`. A new client-side guard (`src/app/(app)/layout.tsx`) redirects
  an unauthenticated visitor to `/login` instead of rendering the
  protected shell — this did not exist before this checkpoint (previously
  any visitor could view the dashboard pages unauthenticated and just see
  empty/error states).
- **Why client-side, not middleware**: Supabase's browser client persists
  the session in `localStorage` (`persistSession: true`), not a cookie, so
  there is no session state available to Next.js middleware without
  introducing `@supabase/ssr` — out of scope for this change. The guard
  lives in `useAuth()` + a client layout instead.
- **Existing `AuthModal` (email/password + dev-token fallback) was left
  untouched** — it still backs the Header's "Sign in" button for local
  dev convenience, but is effectively unreachable on protected routes now
  that the guard redirects before Header renders for an unauthenticated
  visitor.
- **Motion**: `npm install motion` (new dependency) for hero entrance,
  staggered scroll reveals (`Reveal`), and an animated pipeline step
  sequence (`PipelineSequence`, `layoutId` + `AnimatePresence`). All three
  respect `prefers-reduced-motion` via Motion's `useReducedMotion()`.
- **Next.js 16 Cache Components pitfalls hit during this work** (see
  `frontend/AGENTS.md` — this version has breaking changes from training
  data): (1) `new Date()` in a server-rendered footer broke prerendering —
  fixed with a static year; (2) passing an array of Lucide icon
  *component references* as a prop from a Server Component (`page.tsx`,
  which exports `metadata`) into a Client Component failed RSC
  serialization — fixed by moving that data into a client-only wrapper
  (`LandingPipeline`); (3) `useSearchParams()` in `/login`, `/signup`, and
  `/auth/callback` required an explicit `<Suspense>` boundary.
- **Tests updated to match the new, intentional behavior change**:
  `frontend/e2e/helpers.ts` — `ROUTES.home` now points at `/dashboard`
  (was `/`); `frontend/e2e/auth.spec.ts` A1.1 now asserts the
  unauthenticated-redirect-to-`/login` behavior instead of asserting the
  dashboard shell rendered unauthenticated (which is no longer true, by
  design); new A0.1/A0.2 cover the landing CTA and the dashboard redirect
  per this task's explicit testing requirement. All other existing
  Vitest/Playwright tests were re-verified passing, not rewritten.
- **Verified**: `tsc --noEmit` clean; `next build` succeeds (all 13
  routes prerender); Vitest 72/72 passing (64 pre-existing + 8 new in
  `auth-page.test.tsx`); Playwright — all 23 unauthenticated-reachable
  tests pass against a live `next dev` server, 26 authenticated tests
  skipped as before (no `DEVTWIN_DEV_TOKEN` in this environment — not a
  behavior change).
- **Not done / explicitly deferred**: Enabling the Supabase GitHub OAuth
  provider itself is a manual Supabase console step (Authentication →
  Providers → GitHub, with a dedicated GitHub OAuth App distinct from the
  GitHub App used for repository access) — flagged to the developer, not
  attempted from code. Real Google OAuth remains unimplemented by design.

## Forbidden Behaviors
Agents must NOT:
- Invent requirements
- Silently change architecture
- Introduce technologies without justification and ADR
- Modify database design casually
- Create undocumented APIs
- Claim implementation when only specification exists

## Known Limitations (Minor MVP)
- Supabase Auth UI now covers three paths: the original in-app `AuthModal`
  (email/password sign-in/sign-up), and dedicated `/login` + `/signup`
  pages whose primary action is GitHub OAuth (`signInWithOAuth`) — both
  reuse the same Supabase client singleton
- The Supabase GitHub provider itself still needs to be enabled in the
  Supabase console (manual step, not done from code) before GitHub
  sign-in actually completes end-to-end
- Google sign-in is a visibly disabled "Coming soon" stub on `/login` and
  `/signup` — not wired to a real provider
- When Supabase env vars are absent, the UI falls back gracefully to a dev-token textarea form (both in `AuthModal` and on `/login` / `/signup`)
- Worker process is operational and verified end-to-end; can be executed via daemon polling loop (`workers\runner.py --poll`)
- No email/notification on analysis completion
- No multi-developer team features

## Current Technology Stack
- Frontend: Next.js / TypeScript / Tailwind CSS v4 / Motion (`motion/react`, for marketing-site animation only)
- Backend: FastAPI / Python
- Database: PostgreSQL / Supabase (27 tables with RLS)
- Queue: PostgreSQL-native (NOT Redis)
- Testing: pytest (backend), Vitest (frontend — 72 tests), Playwright (E2E)

## Project Concepts Reference
- **Skill ≠ Capability**: "Backend Development" is a Skill. A developer's "Capability in Backend Development" is a scored metric.
- **Observation ≠ Evidence**: Observation = raw fact from code. Evidence = contextualized interpretation.
- **Analysis Job ≠ Analysis Run**: Job = user request to process. Run = single execution attempt.
