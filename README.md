# DevTwin

**DevTwin — AI-Powered Developer Capability Intelligence Platform**

Development Stage: v0.8 — Full-Stack MVP Implemented & Live-Verified (Checkpoint 31)

## Problem
Current methods for evaluating developer capability rely on static resumes, generic GitHub dashboards, or simple code assessments. These fail to capture the true, evolving nature of a developer's technical knowledge, practical application, and engineering behavior over time. They lack evidence-backed explanations and do not account for engineering risks or contextual application of skills.

## Core Idea
DevTwin connects what a developer knows, how they actually build, what engineering signals/risks appear, what capabilities those signals support, and how the capability state evolves over time. 

The technical intelligence loop is:
KNOW → BUILD → DETECT → LEARN → IMPROVE → RE-EVALUATE

The system is evidence-backed and explainable. No capability score without evidence. No inference without uncertainty. No skill-gap conclusion without distinguishing observed evidence from inferred causes.

## Architecture Overview
DevTwin consists of three core intelligence layers:
1. **SkillGraph**: Represents relationships between developers, skills, concepts, technologies, projects, evidence, and capabilities.
2. **CodeRisk**: An engineering-risk intelligence layer that analyzes repository signals to generate explainable risk signals which feed into the capability model.
3. **StudyTwin**: The future adaptive learning/growth layer (Major roadmap).

## Minor Scope (Developer Capability Intelligence Foundation)
The Minor Project implements the foundation to answer: "Can heterogeneous evidence extracted from GitHub activity and software repositories be transformed into an explainable, evidence-backed representation of a developer's technical capabilities and engineering characteristics?"

Included:
- GitHub ingestion (GitHub App OAuth + Installation flow)
- Safe repository fetching & extraction
- Repository mining (Languages, manifests, Python AST)
- SkillGraph mapping & relational persistence
- CodeRisk static analysis heuristics (8 rules)
- Evidence engine (Strength, directness, reliability, polarity)
- Capability model v1 (Sigmoid aggregation, diminishing returns, half-life temporal decay)
- Append-only capability history tracking
- Interactive dashboard UI (Next.js 16, Tailwind CSS v4, Cytoscape, Recharts)
- Evidence Explorer & CodeRisk findings inspector

## Major Roadmap (Future)
The Major roadmap will extend the platform to include the StudyTwin layer, featuring:
- Knowledge tracing
- Temporal capability prediction
- Personalized learning
- Intervention tracking
- Outcome measurement
- What-if simulation
- Adaptive recommendations
- Richer graph/ML models

## Technology Stack
- **Frontend**: Next.js 16 (App Router, Turbopack), React 19, TypeScript, Tailwind CSS v4, Cytoscape, Recharts, Lucide React
- **Backend**: FastAPI, Python 3.11/3.12, SQLAlchemy (asyncpg), Pydantic v2, PyJWT (JWKS verification), Cryptography (Fernet)
- **Database**: PostgreSQL / Supabase (27 tables with Row-Level Security policies, 5 SQL migrations)
- **Queue**: PostgreSQL-native (`analysis_jobs` table using `SELECT ... FOR UPDATE SKIP LOCKED` atomic claiming, NOT Redis)
- **Code Analysis**: Custom AST parsers, language classifiers, manifest extractors, static rule analyzers
- **Testing**: pytest (385 backend tests), Vitest (64 frontend unit/integration tests), Playwright (47 E2E tests)

## Repository Structure
- `docs/` - Canonical technical specifications (Domain Model, DB Schema, API Contracts, Pipeline)
- `backend/` - FastAPI backend application, REST APIs, authentication dependencies, and test suite
- `frontend/` - Next.js 16 web application with design system and interactive visualizers
- `workers/` - Background Python analysis workers (`workers/runner.py`) executing the 8-stage pipeline
- `database/` - SQL migration files (001–005) with RLS policies and hardening
- `scripts/` - Operational scripts and database utilities
- `tests/` - System and end-to-end integration tests

## Frontend Routes
The frontend is split into a public marketing site and an authenticated app, as two
separate Next.js route groups that share no layout:
- **Public (marketing)** — `src/app/(marketing)/`: `/` (landing), `/how-it-works`
  (expanded pipeline breakdown), `/about` (project context).
- **Auth** — `/login`, `/signup` (one shared component, two URLs; GitHub OAuth
  primary, Google sign-in visibly disabled as a future stub), `/auth/callback`
  (OAuth redirect landing).
- **Authenticated app** — `src/app/(app)/`: `/dashboard` (Overview, formerly at
  `/`), `/repositories`, `/capabilities`, `/coderisk`, `/skillgraph`, `/evidence`.
  A client-side route guard (`src/app/(app)/layout.tsx`) redirects an
  unauthenticated visitor to `/login` instead of rendering a broken dashboard.

### Deployment prerequisite: Supabase GitHub provider
"Continue with GitHub" calls Supabase's `signInWithOAuth({ provider: "github" })`
using the existing `@supabase/supabase-js` client (`frontend/src/lib/supabase.ts`).
Before this works end-to-end, the project owner must, in the Supabase dashboard:
1. Go to **Authentication → Providers → GitHub** and enable it.
2. Create a dedicated **GitHub OAuth App** (not the GitHub App used for
   repository access/installation — a separate app, scoped only to sign-in)
   and supply its Client ID/Secret to the Supabase provider config.
3. Set that OAuth App's **Authorization callback URL** to the Supabase
   project's callback endpoint (`https://<project-ref>.supabase.co/auth/v1/callback`).
This is a manual console step — it is not configured from application code.

## Development Philosophy
- The repository documentation is the source of truth.
- AI is an intelligence layer, NOT the entire product.
- Evidence-backed: Every capability estimate must be supported by evidence.
- Interpretable: The system must remain interpretable and manageable.
- **Risk ≠ Competence**: CodeRisk findings are evidence signals, not blame verdicts.

## Current Project Status

**Current Stage:** v0.8 — Full-Stack MVP Complete & Verified End-to-End (Checkpoint 31)

---

### ✅ IMPLEMENTED & VERIFIED COMPONENTS

| Area | Component | Implementation Details |
|---|---|---|
| **Backend API** | FastAPI + Uvicorn | 18 active REST endpoints across `/health`, `/developers`, `/github`, `/projects`, `/repositories`, and `/analysis`. |
| **Authentication** | Supabase Auth + JWKS | RS256/ES256 verification against Supabase JWKS, automatic developer provisioning (`POST /developers/me`), dev-token bypass support. |
| **GitHub App Integration** | OAuth + Installation | `GET /github/install`, `GET /github/callback`, `GET /github/status`, `DELETE /github/disconnect`, `GET /github/repositories` (ephemeral installation token). |
| **Database & Security** | PostgreSQL + RLS | 27 tables with strict Row-Level Security, 5 SQL migrations applied, defense-in-depth isolation by `auth_user_id`. |
| **Queue & Worker Runner** | PostgreSQL-native | Atomic `SELECT ... FOR UPDATE SKIP LOCKED` claiming on `analysis_jobs`, retry limits (`MAX_JOB_ATTEMPTS=3`), sanitized error mapping. |
| **Analysis Pipeline** | 8-Stage Architecture | `QUEUED → FETCHING → MINING → SKILL_GRAPH → CODE_RISK → EVIDENCE → CAPABILITY → COMPLETED`. |
| **Repository Mining** | Safe Traversal & AST | Safe tarball streaming, exclusions (`.git`, `node_modules`, `venv`), language detection, manifest extraction (`package.json`, `requirements.txt`, `Cargo.toml`), Python AST parsing. |
| **SkillGraph Engine** | Taxonomy Mapping | Grounded language & dependency mapping, ungrounded package handling, deduplication, snapshot persistence. |
| **CodeRisk Engine** | Static Analysis | 8 static rules (`SEC-001`, `SEC-002`, `SEC-003`, `REL-001`, `REL-002`, `MAINT-001`, `MAINT-002`, `TEST-001`), secret redaction, safe AST detection. |
| **Evidence Engine** | Observation Contextualization | Strength (`0..1`), directness, reliability, polarity (`-1..+1`). Negative polarity evidence for risk findings (Risk ≠ Competence). |
| **Capability Engine** | Mathematical Scoring v1 | Sigmoid non-linear saturation `clamp(sigmoid(sum / 3.0), 0.01, 0.99)`, diminishing returns `w_k / sqrt(k)`, 365-day half-life decay, append-only history. |
| **Frontend Dashboard** | Next.js 16 + Tailwind CSS v4 | 6 core views (`/` Overview, `/repositories`, `/capabilities`, `/coderisk`, `/skillgraph`, `/evidence`). |
| **Interactive Visualizations** | Cytoscape & Recharts | Cytoscape force-directed taxonomy canvas with tabular toggle; Recharts temporal capability trend lines. |
| **In-App Authentication** | Supabase Auth Modal | Modal with Sign In / Sign Up tabs, session auto-restoration via `@supabase/supabase-js`, and graceful dev-token fallback. |
| **Test Suite** | Comprehensive Pyramid | **385 backend pytest tests passing**, **64 frontend Vitest tests passing**, 47 Playwright tests. |

---

### 🔍 VERIFIED END-TO-END PIPELINE RUN (Checkpoint 31)

- **Execution Run ID:** `3bfc7727-8c19-46da-9490-5faf245e4940`
- **Execution Time:** ~20 seconds to process full multi-language repository across all 8 stages.
- **Persisted Artifacts:**
  - **86 raw observations** (languages, dependencies, AST classes, async functions, modules)
  - **35 contextualized evidence items** with taxonomy links
  - **38 developer capabilities** scored with uncertainty-aware confidence
  - **1 risk finding** with provenance and negative polarity evidence
  - **4 core skill nodes** linked in repository SkillGraph
- **Frontend Verification:** All 6 views verified displaying live persisted data with zero console errors.

---

### 🔜 NEXT MILESTONES (Phase 14 & Major Scope)

1. **Phase 14: Research Evaluation**: Curated multi-repository benchmark suite for evidence-backed capability validation.
2. **Multi-Repository Aggregation**: Synthesizing developer capability scores across multiple repositories with cross-repository weighting.
3. **StudyTwin Integration (Major Scope)**: Personalized learning paths, knowledge tracing, and outcome measurement.
