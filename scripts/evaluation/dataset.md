# Phase 14 Evaluation Dataset

## Purpose

This document defines the repository set used by `run_evaluation.py` and
`compute_metrics.py` to measure DevTwin's existing analysis pipeline. It is
**not** a benchmark suite with externally-sourced labels — it is a small,
hand-curated set of repositories with a human-written expectation of what
`CANONICAL_LANGUAGES` / `CANONICAL_DEPENDENCIES`
(`backend/app/skillgraph/taxonomy.py`) should detect, used to compute
precision/recall against the taxonomy's own known coverage (not against an
idealized "correct" answer — the taxonomy is intentionally small, per
ADR-0xx "no ungrounded/hallucinated capability claims").

Per ADR-007, every repository below MUST be ingested through the existing
GitHub OAuth App installation + repository-selection flow
(`GET /github/repositories` → `POST /repositories` → `POST /analysis/jobs`).
No public-URL or `git clone` shortcut is used anywhere in this evaluation.

## Status of this dataset (IMPORTANT — read before running)

Only **Repo 1** below is confirmed accessible in this environment: it is
this very repository, already verified end-to-end in MEMORY.md Checkpoint 31
(run `3bfc7727-8c19-46da-9490-5faf245e4940`, COMPLETED in ~20s).

Repos 2–10 are **placeholder slots**. This agent run had no authenticated
Supabase session and could not drive an interactive GitHub OAuth consent
screen, so it could not call `GET /github/repositories` to see which of the
developer's (`praveen-89`) repositories are actually installed under the
DevTwin GitHub App. The developer must:

1. Install/extend the DevTwin GitHub App to cover the chosen repositories.
2. Replace each `<PENDING SELECTION>` row below with a real `owner/name`
   and `github_repo_id` (visible from `GET /github/repositories`).
3. Hand-write the ground truth for that repo (languages + dependencies you
   expect `CANONICAL_LANGUAGES` / `CANONICAL_DEPENDENCIES` to catch, and
   dependencies you know are used but are NOT in the taxonomy — those are
   expected misses, not bugs).

Do not run `compute_metrics.py` precision/recall against a repo whose
ground truth row still says `<PENDING SELECTION>` — `compute_metrics.py`
skips any such row automatically and reports it as `ground_truth_missing`.

## Repository Set (target: 8–12 repos)

| # | Repo (owner/name) | Size class | Ground truth defined? |
|---|---|---|---|
| 1 | `praveen-89/DevTwin-AI-Powered-Developer-Capability-Intelligence-Platform` | Mid/large, personal, full-stack | Yes (below) |
| 2 | `<PENDING SELECTION>` | Small/beginner | No |
| 3 | `<PENDING SELECTION>` | Small/beginner | No |
| 4 | `<PENDING SELECTION>` | Small/beginner | No |
| 5 | `<PENDING SELECTION>` | Mid-size personal project | No |
| 6 | `<PENDING SELECTION>` | Mid-size personal project | No |
| 7 | `<PENDING SELECTION>` | Mid-size personal project | No |
| 8 | `<PENDING SELECTION>` | Established OSS library (suggest: `pallets/flask` or `expressjs/express`, if addable to the installation) | No |
| 9 | `<PENDING SELECTION>` | Established OSS library (suggest: `psf/requests`) | No |

Repo count is intentionally 9 (within the 8–12 target), leaving headroom
for the developer to add a 10th/11th without restructuring this table —
add rows in the same format if they do.

---

## Ground Truth — Repo 1: DevTwin (this repository)

Inspected directly from the actual repo tree (`backend/`, `frontend/`,
`workers/`, `database/`) as of commit `337d12b`.

### Expected languages (`repository_languages` / `CANONICAL_LANGUAGES`)

| Language | Expected to be detected? | Notes |
|---|---|---|
| Python | Yes | `backend/`, `workers/` |
| TypeScript | Yes | `frontend/` (Next.js, App Router) |
| JavaScript | Possibly | config files (`next.config.js`-style, if present as `.js` not `.ts`) |
| CSS | Yes | Tailwind CSS v4 source under `frontend/` |
| SQL | Yes | `database/*.sql` migrations |
| HTML | Unlikely | No static `.html` source files checked into the repo |
| Shell | Possibly | any `.sh` helper scripts, if present |

### Expected dependencies (`repository_dependencies` / `CANONICAL_DEPENDENCIES`)

In taxonomy (expected HIT):
- `fastapi` (backend/requirements.txt)
- `sqlalchemy` (backend/requirements.txt — package name `SQLAlchemy`)
- `pydantic` (backend/requirements.txt)
- `pytest` (backend/requirements.txt)
- `httpx` (backend/requirements.txt)
- `react` (frontend/package.json, via Next.js)
- `next` (frontend/package.json)
- `tailwindcss` (frontend/package.json)

Known to be used but NOT in `CANONICAL_DEPENDENCIES` (expected MISS —
this is a taxonomy coverage gap, not a pipeline bug):
- `@supabase/supabase-js` (frontend/package.json — Supabase client)
- `cryptography` (backend/requirements.txt — Fernet token encryption)
- `PyJWT` (backend/requirements.txt — JWKS verification)
- `pydantic-settings` (backend/requirements.txt)
- `cytoscape` (frontend — graph visualization)
- `recharts` (frontend — charts)
- `lucide-react` (frontend — icon set)
- `uvicorn` (backend — ASGI server; arguably "tool", not in taxonomy)

### Expected CodeRisk signals

Checkpoint 31's verified live run recorded exactly 1 `risk_finding` for
this repository on that run. No repo-specific rule predictions are made
here beyond that historical baseline — CodeRisk rule hits are inherently
code-state-dependent (new commits can introduce/remove matches for
`SEC-001`..`TEST-001`), so `compute_metrics.py` reports the actual finding
counts per `rule_id`/severity from whichever run is evaluated, for manual
review, rather than this document predicting them.

---

## Ground Truth — Repos 2–9

Fill in using this template once a repository is selected:

```
### Ground Truth — Repo N: <owner/name>

Expected languages (in CANONICAL_LANGUAGES): ...
Expected languages NOT in taxonomy (expected miss): ...
Expected dependencies (in CANONICAL_DEPENDENCIES): ...
Expected dependencies NOT in taxonomy (expected miss): ...
```

## Why this method, not a "real" benchmark

`docs/16_EVALUATION_PLAN.md` explicitly rejects fabricated research claims
or external benchmarks. This dataset is small, author-curated, and has no
inter-rater reliability check (see "Limitations" in
`docs/14_PHASE14_EVALUATION_RESULTS.md`). It measures DevTwin's pipeline
against its own documented taxonomy boundaries, not against an external
ground truth of "everything a developer actually knows."
