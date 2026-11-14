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

### Checkpoint 34 — Authenticated Dashboard Motion Polish (Presentation Only) (2026-11-12)

- **Scope**: Presentation/animation layer only, frontend-only. No data
  fetching, API calls, scoring logic, or backend file was touched. The
  `motion` dependency already existed from Checkpoint 33 — not reinstalled.
- **What changed**:
  - `src/components/ui/stage-stepper.tsx` — the analysis-run stage pills
    (`QUEUED → FETCHING → MINING → SKILL_GRAPH → CODE_RISK → CAPABILITY →
    COMPLETED`, the real `AnalysisRunStatus` enum from `types/api.ts`, no
    invented stage names) now morph between icons via `AnimatePresence`
    and `layout`, and the connector line / label color tween instead of
    snapping. Falls back to the original static markup verbatim when
    `prefers-reduced-motion` is set.
  - `src/components/ui/score-gauge.tsx` — score and confidence numbers now
    tween via a new shared `AnimatedNumber` component
    (`src/components/ui/animated-number.tsx`, uses Motion's imperative
    `animate()`), and the score/confidence bar widths animate with
    `motion.div` instead of snapping. This is the component shared by the
    Capabilities page, the Overview dashboard, and anywhere else a
    capability score is rendered, so the tween applies everywhere
    consistently without per-page duplication.
  - `src/components/capabilities/capability-history-chart.tsx` — the
    Recharts `<Line>` now draws in on initial render
    (`isAnimationActive={!reduceMotion}`, `animationDuration={900}`)
    instead of `isAnimationActive={false}`. No chart library change.
  - `src/app/(app)/capabilities/page.tsx` — the per-target capability
    cards get a staggered mount entrance, `whileHover`/`whileTap`
    micro-interactions, all via conditional `motion.div` props (empty
    object when `prefers-reduced-motion`, so the element renders as a
    plain div with no transform animation).
  - `src/app/(app)/evidence/page.tsx` — evidence table rows get the same
    staggered entrance pattern via a new shared `StaggerItem` component
    (`src/components/ui/stagger-item.tsx`, supports `div`/`li`/`tr`) for
    visual consistency with the capability cards.
  - New shared primitives: `src/components/ui/animated-number.tsx`,
    `src/components/ui/stagger-item.tsx`.
- **Bklit UI**: evaluated and **not installed**. The existing Recharts
  line chart already does what's needed (temporal line + custom tooltip +
  reference line) once its built-in animation is turned on; installing a
  second chart library for one chart would mean running two charting
  approaches side by side with no component it clearly replaces — against
  this task's own instruction not to leave permanent duplication. Decision
  recorded here rather than silently skipped.
- **Preserved untouched**: both "Run-Scoped Scoring" / "Run-Scoped
  History" disclaimer banners (not animated, not auto-dismissing, no
  opacity fade), all existing ARIA attributes (`role="list"`,
  `aria-label`, `aria-hidden`, `role="progressbar"` with its
  `aria-valuenow`/`aria-valuemin`/`aria-valuemax`/`aria-label`), and all
  data-fetching/polling logic in `repositories/page.tsx`,
  `capabilities/page.tsx`, `evidence/page.tsx`, and `overview-view.tsx`.
  The marketing site, `/login`, `/signup`, and `/auth/callback` from
  Checkpoint 33 were not touched.
- **Verified**: `tsc --noEmit` clean; `next build` succeeds (all 13
  app routes prerender, same route list as Checkpoint 33); Vitest 72/72
  passing, unchanged from Checkpoint 33 (no test needed rewriting —
  `repositories-page.test.tsx`'s assertions target `StatusBadge` text and
  button roles, which this change does not alter; motion-wrapped elements
  still forward `role`/`aria-label`/`onClick` to the underlying DOM node).
- **Not done**: No new Vitest tests were added specifically for the
  animations themselves (e.g. asserting `AnimatePresence` transition
  timing) — out of scope for a presentation-only pass and consistent with
  how Checkpoint 33's marketing animations were verified (build + existing
  suite, not new animation-specific tests).

### Checkpoint 35 — Access-Control Regression: Unauthenticated `/dashboard` Shell Fixed (2026-11-12)

- **Severity**: Real access-control bug, not cosmetic. A visitor with no
  valid session could see the full protected dashboard shell (sidebar,
  all six nav items) at `/dashboard`, even though the header correctly
  showed "Sign in". Confirmed and reproduced (not hypothetical) before any
  fix was written.
- **Confirmed root cause**: `src/app/(app)/layout.tsx`'s guard and
  `src/components/layout/header.tsx` both read the same `useAuth()`
  context, but applied **different predicates** for "authenticated":
  the guard checked `!!token` only; the header checked `!!(token &&
  developer)`. When a bearer token is present in storage but stale,
  expired, or otherwise rejected by the backend, `AuthProvider`'s
  `fetchDeveloper()` fails on a path that does **not** clear the token
  (only an explicit HTTP 401 from `/developers/me` clears it — a network-
  level failure, e.g. "Failed to fetch", falls through to a generic error
  branch that leaves `token` set and `developer` null forever). Result:
  `token` truthy + `developer` null → guard says "authenticated" (renders
  dashboard shell), header says "not authenticated" (shows "Sign in") —
  the two disagreed, which should never be possible from one source of
  truth. Reproduced directly: injecting an invalid token into
  `sessionStorage` and reloading `/dashboard` rendered the full shell with
  "Failed to fetch" errors in every data widget, while the header showed
  "Sign in to connect" / "Sign in" — the exact symptom from the reported
  screenshot.
- **Fix**: Added a single derived `isAuthenticated: boolean` field to
  `AuthState` (`src/lib/auth-context.tsx`), computed as `!!(token &&
  developer)` — i.e. the header's stricter, already-correct predicate.
  Both the `(app)` guard and the header now read this one field; neither
  computes its own notion of "authenticated" anymore, so they cannot
  disagree again by construction.
  - `src/components/layout/app-auth-guard.tsx` (new): the guard's client
    logic, moved out of `layout.tsx` (see below). Blocks rendering of
    `{children}` until `loading` resolves (shows a spinner), then
    redirects to `/login` via `router.replace` the moment
    `isAuthenticated` resolves false, and renders `null` while that
    redirect is in flight (no flash of protected content).
  - `src/app/(app)/layout.tsx`: now a thin Server Component that renders
    `<AppAuthGuard>` and declares `export const instant = false` (see
    Issue 2 below). Moved out of a `"use client"` file because Next 16's
    `instant` route segment config throws if exported from a Client
    Component — this split was required, not optional.
  - `src/components/layout/header.tsx`: now destructures `isAuthenticated`
    from `useAuth()` instead of re-deriving `token && developer` inline.
  - OAuth callback race (`src/app/auth/callback/page.tsx`) was inspected
    and left unchanged — it already waits on `!loading && token` before
    redirecting to `/dashboard`, and `loading` does not resolve to `false`
    until `fetchDeveloper()` has settled, so a freshly-completed GitHub
    OAuth sign-in is never bounced back to `/login` before the session
    (and `isAuthenticated`) has had a chance to resolve.
- **Deliberate trade-off (documented, not silent)**: `isAuthenticated`
  requiring a backend-confirmed `developer` profile (not just a live
  Supabase/dev token) means a user with a perfectly valid session will
  still be redirected to `/login` if the backend is transiently
  unreachable when `/developers/me` is called. This is intentional here:
  the dashboard is unusable without the backend regardless, and silently
  treating an unconfirmable token as "authenticated" is exactly the bug
  being fixed. If this trade-off becomes a UX problem later, the right
  fix is distinguishing "network error talking to a reachable backend"
  from "token rejected", not reverting to token-only gating.
- **Issue 2 (cosmetic, dev-only)**: Next 16 Cache Components
  (`cacheComponents: true` in `next.config.ts`) logged `Could not
  validate that a segment in your UI has instant navigation... Dropped
  segment: src/app/(app)/dashboard/page.tsx` because the segment's
  content depends on client-side auth state unknowable at prerender time.
  `export const instant = false` was added to `src/app/(app)/layout.tsx`
  as specified, plus — confirmed necessary by testing, since Next
  validates the Page segment independently of its layout — directly to
  `src/app/(app)/dashboard/page.tsx` (the only Server Component page in
  the group; the literal warning quoted in the bug report named this
  exact segment and is now gone). The other five `(app)` pages
  (`repositories`, `capabilities`, `coderisk`, `skillgraph`, `evidence`)
  are themselves `"use client"` pages, so they cannot export `instant`
  without the same Server/Client split applied to the layout and
  dashboard page; each logs its own instance of the same dev-only warning
  independently. Not restructured in this pass: two of those five files
  (`capabilities/page.tsx`, `evidence/page.tsx`) had unrelated, unfinished
  uncommitted animation-pass edits from Checkpoint 34 in the same working
  tree, and a Server/Client split is a structural change to exactly the
  files that pass is mid-edit on — doing it here risked colliding with
  that unrelated work. Tracked as a known limitation below, not silently
  dropped.
- **Tests added** (`frontend/e2e/auth.spec.ts`):
  - `A0.3` — reproduces the regression directly (stale/invalid token in
    `sessionStorage`) and asserts `/dashboard` redirects to `/login` and
    the sidebar never renders.
  - `A1b.1` — mocks a backend-confirmed session (`/developers/me` returns
    200) and asserts the header's signed-in state and the dashboard
    shell's protected content render together, on `/dashboard`, in the
    same pass — i.e. the two can no longer disagree.
- **Verified**: `tsc --noEmit` clean. `next build` succeeds (same 13
  prerendered `(app)`/marketing/auth routes as Checkpoint 34). Vitest
  72/72 passing (4 existing test files' `useAuth()` mocks updated to
  include the new `isAuthenticated` field — no behavioral test changes).
  Playwright: all `auth.spec.ts` tests pass (13 total, 10 run + 3 skipped
  without `DEVTWIN_DEV_TOKEN`, including both new tests). Full suite:
  23 passed, 2 pre-existing failures unrelated to this change
  (`mocked-flows.spec.ts` M5 SkillGraph canvas visibility, M6 Capabilities
  "Run-Scoped" text visibility — both touch files already modified by the
  concurrent, uncommitted Checkpoint 34 animation pass; neither test
  exercises auth/guard/header code, and this change does not touch
  `skillgraph/page.tsx`, `capability-history-chart.tsx`, or
  `score-gauge.tsx`). Dev server log confirmed the instant-navigation
  warning is gone for `/dashboard` specifically after the fix, across a
  fresh `next dev` restart.
- **Known limitation carried forward**: the instant-navigation dev
  warning still logs once per non-`/dashboard` `(app)` route
  (`repositories`, `capabilities`, `coderisk`, `skillgraph`, `evidence`)
  because those pages are Client Components and cannot export `instant`
  themselves. Fully silencing it for all six routes requires the same
  Server-page/Client-content split used for `dashboard/page.tsx` and
  `layout.tsx`, applied to the remaining five pages — left for a future,
  dedicated pass once the concurrent animation-pass edits to those files
  are committed.

### Checkpoint 36 — GitHub App Install Callback Redirected to Stale Root Path (2026-11-13)
- **Bug**: After installing the DevTwin GitHub App on GitHub's side, the
  browser did not land back on the authenticated dashboard — it appeared
  stranded, with GitHub connection status not visibly updating.
- **Confirmed root cause (code, not a GitHub console setting)**:
  `backend/app/api/routes/github.py`'s `_frontend_redirect()` helper built
  every post-callback redirect as `f"{base_url}/?{query}"` — a hardcoded
  root path. This was correct when `/` was the dashboard, but Checkpoint
  33/34's marketing site took over `/` and moved the authenticated
  dashboard to `/dashboard` (see `(marketing)` vs `(app)` route groups in
  `ARCHITECTURE.md`). The existing backend test suite had the bug baked in
  as an assertion: every `test_github.py` callback test asserted
  `location == "http://localhost:3000/?github=..."`. Confirmed by reading
  `frontend/src/app/(app)/dashboard/page.tsx` (dashboard lives at
  `/dashboard`) and `frontend/src/app/(marketing)/page.tsx` (marketing
  landing page now owns `/`) — the callback was redirecting every install
  attempt (success and failure) onto the public marketing page, which has
  no handler for `?github=success` / `?github_error=...` query params, so
  nothing on screen ever changed.
- **Fix**: Added `FRONTEND_DASHBOARD_PATH` (default `/dashboard`) to
  `backend/app/core/config.py` (`Settings`), validated to start with `/`
  and normalized of a trailing slash. `_frontend_redirect()` in
  `backend/app/api/routes/github.py` now builds the target URL as
  `{FRONTEND_URL}{FRONTEND_DASHBOARD_PATH}?{query}` instead of a hardcoded
  `/`, for both the success (`?github=success`) and every failure
  (`?github_error=...`) branch. No change to installation_id persistence,
  token handling, or OAuth state logic — only the redirect target.
  `frontend/src/components/overview/overview-view.tsx` already intercepts
  `?github=success` / `?github_error=...` on mount and refetches GitHub
  status + repositories without a manual refresh — confirmed by reading
  it; no frontend change was needed.
- **Verified**: Updated all ~23 existing `test_github.py` redirect
  assertions from `.../?github...` to `.../dashboard?github...`; added
  `test_github_callback_redirects_to_configured_dashboard_path_not_hardcoded_root`
  (proves the path comes from settings, not a literal `/`) and three new
  `test_config.py` tests for `FRONTEND_DASHBOARD_PATH` validation. Full
  backend suite: 389 passed (up from the prior 385-test baseline). No
  frontend files were changed by this fix, so `tsc`/`next build` were not
  re-run for this task.
- **Not verified live**: did not run a real GitHub App install round-trip
  in this environment (no browser/GitHub session available here) — relying
  on the unit/integration test instead, as instructed. The developer
  should do one manual end-to-end install against their existing test
  GitHub App installation to confirm the full round trip now lands on
  `/dashboard` with GitHub shown as connected.
- **No GitHub App console change was required for this fix** — the bug
  was fully a backend code defect (hardcoded redirect path), not a Setup
  URL / OAuth callback URL misconfiguration in the GitHub App's own
  settings.

### Checkpoint 37 — Live GitHub Connect Debugging: Two Real Bugs Found via Manual Testing (2026-11-13)
- Checkpoint 36's redirect-path fix was verified live by the developer
  against the real GitHub App installation flow, with two further issues
  surfacing only through actual manual testing (not reproducible from
  code review alone):
- **Bug A — cross-developer `account_conflict` false positive**: the
  developer's real account (`praveen.strange0@gmail.com`) could not link
  its GitHub identity (`praveen-89`) because a `github_accounts` row
  already existed for that GitHub identity under a leftover test
  developer profile (`test1@gmail.com`, used during Checkpoint 32's Phase
  14 evaluation testing). Confirmed via live Network-tab tracing that the
  GitHub OAuth-during-installation redirect mechanism itself works
  correctly (`github.com/apps/devtwin2/installations/new` →
  `select_target` → `localhost:8000/github/callback` →
  `localhost:3000/dashboard?github_error=account_conflict`) — this was
  stale test data, not a code defect. `DELETE /github/disconnect` does
  NOT free a GitHub identity for a different developer (per ADR-014, it
  only soft-disconnects within the same developer); the stale
  `github_accounts` row was deleted directly from the DB with the
  developer's explicit approval. Also noted: GitHub's
  `/installations/new` skips the full Install & Authorize + redirect
  cycle entirely when the app is already installed for that account —
  retesting requires a genuine uninstall first, not just a backend-side
  DB cleanup.
- **Bug B — global repository uniqueness constraints (real, fixed)**:
  `repositories` carried bare global `UNIQUE(github_repo_id)` and
  `UNIQUE(full_name)` constraints from `001_initial_schema.sql`, making
  repository registration global across ALL developers instead of scoped
  per-project. A repo already registered by any developer (including
  leftover test data) would incorrectly return HTTP 409 "Repository
  already registered." for every other developer. Fixed via
  `database/migrations/006_scope_repository_uniqueness.sql`
  (ADR-020 in DECISIONS.md), replacing both with composite
  `UNIQUE(project_id, github_repo_id)` / `UNIQUE(project_id, full_name)`
  constraints. Applied directly to the live Supabase DB with the
  developer's explicit approval. `docs/11_DATABASE_SCHEMA.md` updated.
  `backend/app/api/routes/repositories.py`'s duplicate-detection code
  needed no change (it already catches any `IntegrityError` with SQLSTATE
  23505 generically). Full backend suite re-run after the migration:
  389/389 passing.
- **Noted, not fixed**: `DECISIONS.md` ADR-015 (status ACTIVE) already
  documented that GitHub's `/installations/new` endpoint ignores PKCE
  parameters and decided to remove `code_challenge`/`code_challenge_method`
  from `GET /github/install`'s construction of that URL — but the current
  code in `backend/app/api/routes/github.py` still sends them, and the
  function's own docstring contradicts the ADR. Confirmed harmless (GitHub
  silently ignores them, consistent with the ADR's own finding) and not
  the cause of any bug fixed in this checkpoint, so left as a flagged
  documentation/implementation drift for a future cleanup rather than
  fixed opportunistically here.
- End state: GitHub App connection flow fully verified working live by
  the developer (`@praveen-89` shows connected, repository
  `praveen-89/SevaGrid` registered and visible on the dashboard).
- **Still open, not addressed this session**: the dev-only
  "could not validate instant navigation" warning still fires for
  `repositories`, `capabilities`, `coderisk`, `skillgraph`, `evidence`
  (all client-component pages) — same limitation already recorded in
  Checkpoint 35.

### Checkpoint 38 — Marketing/Auth Visual Redesign: Illustrations, Glassmorphism, Light/Dark/System Theme (2026-11-14)
- Scope was intentionally narrow: public marketing site (`/`, `/how-it-works`,
  `/about`), `/login` + `/signup` (via `src/components/auth/auth-page.tsx`),
  and new theme infrastructure. The authenticated `(app)` dashboard, backend,
  and database were explicitly out of scope and were not touched by this
  checkpoint (verified — see below).
- **New dependency — `next-themes@^0.4.6`** (installed with
  `--legacy-peer-deps`, matching this environment's existing pre-existing
  `vitest`/`@types/node` peer-conflict workaround; unrelated to this change).
  Chosen because it is the standard, minimal, FOUC-safe way to implement
  Light/Dark/System theme selection with SSR-safe hydration, avoiding a
  hand-rolled theme system that would be easy to get wrong (flash-of-wrong-theme,
  `localStorage` read timing, etc.). **Flagged for the developer's explicit
  ADR decision** per AGENTS.md's "new technology" rule — no ADR was written
  as part of this checkpoint, by design (that decision belongs to the
  developer).
- Added `frontend/src/components/theme/theme-provider.tsx` (wraps
  `next-themes`' `ThemeProvider`, `attribute="class"`, `defaultTheme="system"`)
  and `frontend/src/components/theme/theme-toggle.tsx` (3-way Light/System/Dark
  control). Wired into `frontend/src/app/layout.tsx` as the one minimal root
  change required (`<ThemeProvider>` wraps the existing `<AuthProvider>`;
  `suppressHydrationWarning` added to `<html>`, which is `next-themes`' own
  documented requirement). No other root-layout behavior changed.
- **Dashboard safety verification**: confirmed via `grep` *before* making any
  change that zero `dark:`-prefixed Tailwind utilities and zero
  `bg-background`/`text-foreground`/`var(--background)`-style theme-variable
  usages exist anywhere under `(app)/`, `components/layout`, `components/ui`,
  or any dashboard feature component — the dashboard is 100% hardcoded
  hex/slate classes. Added a global `@custom-variant dark (&:where(.dark, .dark *));`
  to `globals.css` so `dark:` utilities respond to the class `next-themes`
  toggles on `<html>` — since the dashboard uses no `dark:` utilities at all,
  toggling that class is a visual no-op there. Re-verified after all edits
  (same grep, zero hits outside the marketing/auth/theme scope) — the
  dashboard's dark-only appearance is unchanged regardless of the selected
  theme. `tech-grid`'s light-mode line color was given an explicit
  `:root:not(.dark) .tech-grid` override in `globals.css` (only reachable on
  marketing/auth routes, for the same reason).
- **Visual redesign**: added `frontend/src/components/marketing/illustrations.tsx`
  (five custom inline-SVG illustrations — `GraphIllustration` (SkillGraph
  node/edge motif), `PipelineFlowIllustration`, `EvidenceStackIllustration`,
  `RadarScoreIllustration`, `AuthMotifIllustration` — no external image
  generation tool was available in this environment, and abstract technical
  SVGs are the right call for this product regardless) and
  `frontend/src/components/marketing/glass-card.tsx` (shared
  `backdrop-blur-md` translucent card, light/dark aware). Applied these plus
  the existing `Reveal`/`HeroEntrance`/`PipelineSequence` animation
  primitives (reused, not replaced) across `page.tsx`, `how-it-works/page.tsx`,
  `about/page.tsx`, `marketing-nav.tsx`, `marketing-footer.tsx`, and
  `auth-page.tsx`. All existing marketing/auth copy was preserved verbatim —
  this was a visual/structural pass only, no new product claims were added.
  `auth-page.tsx`'s actual auth logic (`signInWithGithub` call, dev-token
  fallback, error handling, redirect-if-authenticated effect) was not
  touched — only its JSX/styling.
- Tests: `npx tsc --noEmit` clean. `npx next build` succeeded (Turbopack,
  all 13 app routes + `_not-found` prerendered as static, same route list as
  prior checkpoints). `npx vitest run --pool=forks` (full suite): 72/72
  passing, including the existing 8 `auth-page.test.tsx` tests unmodified —
  confirming the visual changes did not break any role/text/placeholder
  query. The previously-reported Vitest/`src/types/api.ts` toolchain issue
  did not reproduce in this session with `--pool=forks` run against the
  full suite; left unexplained rather than claimed fixed, since no code
  that would plausibly fix a toolchain issue was touched this checkpoint.
- Files touched: `frontend/src/app/layout.tsx`,
  `frontend/src/app/globals.css`,
  `frontend/src/app/(marketing)/{layout,page}.tsx`,
  `frontend/src/app/(marketing)/how-it-works/page.tsx`,
  `frontend/src/app/(marketing)/about/page.tsx`,
  `frontend/src/components/marketing/{marketing-nav,marketing-footer}.tsx`,
  `frontend/src/components/auth/auth-page.tsx`,
  `frontend/package.json` / `package-lock.json` (new dependency only).
  New files: `frontend/src/components/theme/{theme-provider,theme-toggle}.tsx`,
  `frontend/src/components/marketing/{illustrations,glass-card}.tsx`.
- **Not touched** (confirmed by diff/grep): `backend/`, `database/`, any
  `(app)/` dashboard page or component, `frontend/src/lib/auth-context.tsx`'s
  logic, and all other uncommitted work already in the working tree from
  prior sessions (the marketing/OAuth build-out, dashboard motion pass,
  auth-guard fix, GitHub App install redirect fix, repository-uniqueness
  migration, and the dashboard Server/Client component split).

### Checkpoint 39 — Removed `/signup`, Wired Real Google OAuth (2026-11-14)
- **Why**: `/signup` added no real signup flow — it only offered the same
  GitHub OAuth button as `/login` (Supabase auto-provisions an account on
  first OAuth login regardless of URL), plus an email/password path that was
  never wired to the UI. Keeping it implied an email-signup flow existed
  when it didn't, and an unverified email field is an open door to fake
  signups. Decision: one sign-in entry point (`/login`), two real OAuth
  providers (GitHub + Google), no email/password UI.
- Deleted `frontend/src/app/signup/page.tsx`. Redirected every marketing
  `Link href="/signup"` (nav, footer, home/about/how-it-works CTAs) to
  `/login`; renamed the generic "Connect with GitHub" CTA label to "Get
  Started" since the login page now offers two providers. Removed the
  footer's redundant "Create account" link (same destination as "Sign in").
- `frontend/src/components/auth/auth-page.tsx`: dropped the `mode: "login" |
  "signup"` prop and its `COPY` branching — now a single sign-in experience.
  Enabled the previously-disabled "Continue with Google" stub by adding
  `signInWithGoogle` to `frontend/src/lib/auth-context.tsx` (mirrors
  `signInWithGithub`: `supabase.auth.signInWithOAuth({ provider: "google",
  ... })`, same `/auth/callback` redirect, same failure-only return
  semantics). Both provider buttons now track submission state
  independently (`submittingProvider: "github" | "google" | null`).
- **Google OAuth still needs manual external setup** before it will
  actually authenticate end-to-end: a Google Cloud OAuth client (redirect
  URI = Supabase's `/auth/v1/callback`) and enabling + configuring the
  Google provider in the Supabase dashboard with that client's ID/secret.
  Verified via the Supabase `/auth/v1/settings` endpoint with the anon key
  that GitHub is already enabled (`external.github: true`) and signups are
  not disabled (`disable_signup: false`) — Google was not yet enabled as of
  this checkpoint.
- Updated 4 test files to add a `signInWithGoogle` mock alongside existing
  `signInWithGithub` mocks (`auth-page.test.tsx` rewritten for the
  single-mode page and both providers; `auth-modal.test.tsx`,
  `overview-callback.test.tsx`, `repositories-page.test.tsx` got the mock
  added). Tests: `npx tsc --noEmit` clean, `next build` succeeded (12 routes,
  down from 13 — `/signup` gone), 23 affected tests passing.

### Checkpoint 40 — Dashboard Explainability: `PageExplainer` + Summary Charts on All 6 Pages (2026-11-14)
- **Why**: every dashboard page (Overview, Repositories, Capabilities,
  CodeRisk, SkillGraph, Evidence) showed raw analysis output — tables,
  scores, graph nodes — with no explanation of what any column or term
  meant (Directness, Polarity, Confidence, Severity, etc.). A first-time
  user had no way to understand results without reading source code.
- Presentation-layer only, no backend/API changes, no new data fetches —
  every chart is computed client-side (`useMemo`) from data each page
  already had in state.
- New shared components: `frontend/src/components/dashboard/page-explainer.tsx`
  (`PageExplainer` — collapsible glossary panel, expanded by default on
  first visit then remembered per-page via `localStorage`, `motion/react`
  height animation respecting `useReducedMotion`) and
  `frontend/src/components/dashboard/breakdown-chart.tsx` (`BreakdownChart`,
  a Recharts horizontal bar chart reused for severity/type/visibility
  breakdowns; `CompositionPieChart`, reused for SkillGraph's language
  composition).
- Wired into all 6 views, each with its own plain-language description +
  glossary and summary chart: Overview (risk-by-severity bar), Repositories
  (visibility bar — a per-repo analysis-status breakdown was considered but
  rejected: job/run data is only fetched for the *selected* repo, not all
  of them, and fetching it for every repo would have violated the
  no-new-API-calls constraint), Capabilities (explainer only — the existing
  `CapabilityHistoryChart` already sits below the hero and was kept as-is),
  CodeRisk (severity bar), SkillGraph (explainer + a new language-bytes pie
  chart, in addition to the existing detailed language bar-list further
  down the page), Evidence (evidence-by-type bar).
- **Bug caught before landing**: the Overview page's `useMemo` for its risk
  chart was initially placed after the component's early `if (!token)
  return` / `if (state.initialLoading) return` blocks — a React
  rules-of-hooks violation ("Rendered more hooks than during the previous
  render"), caught by `vitest run` on `overview-callback.test.tsx` (3
  failures), not by `tsc` or `next build` (neither type-checks hook order).
  Fixed by moving the `useMemo` above both early returns. Lesson: hook
  placement bugs like this only surface via actually rendering the
  component through multiple render paths — a type-check and a production
  build are not sufficient verification for hook-order correctness.
- Tests: `npx tsc --noEmit` clean, `next build` succeeded (12 routes),
  `npx vitest run --pool=forks` full suite 72/72 passing after the fix.
- `DESIGN.md` updated with a new "Page Explainability Pattern" section
  documenting `PageExplainer` and the summary-chart convention.

### Checkpoint 41 — Zero-Cost Deployment: Render Free Web Service + In-Process Worker, Vercel (2026-11-14)
- **Why**: Render's free tier has no background-worker instance type, and
  the project currently runs the backend and the analysis worker
  (`workers/runner.py`) as two separate processes. Needed a path to deploy
  at zero cost without losing the two-process architecture for anyone who
  later upgrades to a paid plan.
- Inspected `backend/app/workers/runner.py` first: `worker_loop()` is
  already fully `async` (uses `asyncio.sleep` for its poll interval) and
  already catches `asyncio.CancelledError` internally to exit cleanly —
  no synchronous/blocking code, so `asyncio.create_task()` was the right
  approach (no `asyncio.to_thread` needed).
- Added `RUN_WORKER_IN_PROCESS: bool = False` to
  `backend/app/core/config.py` (same explicit/fail-fast style as existing
  settings). Default false = zero behavior change for the existing
  two-process setup.
- `backend/app/main.py`: replaced the previous no-op app with a
  `lifespan` async context manager (modern FastAPI pattern — `@app.on_event`
  was tried first but is deprecated as of this FastAPI version, so switched
  before landing). When `RUN_WORKER_IN_PROCESS` is true, it calls the
  existing `app.workers.runner.worker_loop()` via `asyncio.create_task` on
  startup and does `task.cancel()` + `await task` on shutdown — the
  worker's own job-claiming logic was not touched or duplicated.
- New `render.yaml` Blueprint at the repo root: one `type: web`, `plan:
  free` service; build installs `backend/requirements.txt`; start runs
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT` from `backend/`.
  `RUN_WORKER_IN_PROCESS=true` and `PYTHON_VERSION=3.11.9` are set as real
  (non-secret) values; every other env var from the root `.env.example` is
  declared with `sync: false` so Render prompts for them in its dashboard
  — nothing committed.
- New `DEPLOYMENT.md`: the Render setup, the sleep/in-process-worker
  trade-off, how to move to a separate paid worker later (flip
  `RUN_WORKER_IN_PROCESS` to false + deploy `workers/runner.py` as its own
  service — no code change), the Vercel dashboard steps (Root Directory =
  `frontend`, the 3 `NEXT_PUBLIC_*` vars), and that Supabase needs no
  changes.
- New `backend/tests/test_worker_lifespan.py`: 2 smoke tests (worker
  disabled / enabled) driving `app.router.lifespan_context(app)` directly
  — confirms the app starts and stops cleanly in both states without
  hanging or raising. Does not re-test worker job-claiming logic (already
  covered by `tests/test_worker.py`).
- Tests: full backend suite `391 passed` (389 before this checkpoint +
  2 new), same pre-existing warnings in `test_github.py` (unrelated
  `AsyncMock` coroutine-not-awaited warnings, not introduced by this
  change). `render.yaml` validated as parseable YAML.
- Not touched, per task scope: GitHub App/Supabase Auth logic, Docker (not
  introduced), Redis (not introduced), frontend code (Vercel needs no repo
  file).
- Left uncommitted on request — developer commits and pushes manually.

## Forbidden Behaviors
Agents must NOT:
- Invent requirements
- Silently change architecture
- Introduce technologies without justification and ADR
- Modify database design casually
- Create undocumented APIs
- Claim implementation when only specification exists

## Known Limitations (Minor MVP)
- Supabase Auth UI now covers two paths: the original in-app `AuthModal`
  (email/password sign-in/sign-up, used elsewhere in the app) and a single
  dedicated `/login` page whose two actions are GitHub and Google OAuth
  (`signInWithOAuth`) — both reuse the same Supabase client singleton.
  There is no `/signup` route — GitHub/Google OAuth auto-provisions an
  account on first use, so login and signup are the same action (see
  Checkpoint 39).
- The Supabase GitHub provider is enabled and verified live (Checkpoint
  37/39). The Google provider is wired in code (Checkpoint 39) but still
  needs the Google Cloud OAuth client + Supabase dashboard configuration
  done manually before it completes end-to-end — not yet confirmed live.
- When Supabase env vars are absent, the UI falls back gracefully to a dev-token textarea form (both in `AuthModal` and on `/login`)
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
