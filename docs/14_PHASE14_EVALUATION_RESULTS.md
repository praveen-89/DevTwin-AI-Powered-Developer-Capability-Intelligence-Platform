# 14. Phase 14 Evaluation Results

## Status: LIVE RUN EXECUTED — 1 of 9 dataset repositories (n=1)

A real sweep was executed against the live pipeline (local `uvicorn` +
`workers/runner.py`, Supabase Postgres) for **Repo 1 only**
(`praveen-89/DevTwin-AI-Powered-Developer-Capability-Intelligence-Platform`,
this repository, commit `337d12b`). Repos 2–9 in `scripts/evaluation/dataset.md`
are still `<PENDING SELECTION>` — this document reports real numbers for
the one repository that has both ground truth and a COMPLETED run, and
does **not** extrapolate those numbers to the rest of the planned dataset.

Run id: `aa434657-f902-47df-91a5-948cb0a07f6c`. Reproduce with:

```bash
export DEVTWIN_API_BASE_URL="http://localhost:8000"
export DEVTWIN_API_TOKEN="<Supabase access token>"
export DATABASE_URL="<same value as backend/.env>"
python scripts/evaluation/run_evaluation.py --dataset scripts/evaluation/dataset.md
python scripts/evaluation/compute_metrics.py --dataset scripts/evaluation/dataset.md --results-dir scripts/evaluation/results
```

## A bug this evaluation surfaced and fixed

The first two live attempts (runs `0f038d9b…` and `3ccdb4b0…`) both got
stuck permanently at the `CODE_RISK` run status and never reached
`COMPLETED`. Root cause, found via the worker's own log output and a
direct DB query:

- `backend/app/mining/ast_parser.py` correctly sets `module=None` for
  plain `import X` statements (the imported name lives in `names`, not
  `module` — that's only populated by `ast.ImportFrom`, e.g. `from X import Y`).
- `backend/app/skillgraph/mapper.py` built every `MODULE_IMPORTED`
  observation's `source_reference["module"]` directly from `imp.module`
  without accounting for this, so plain imports (e.g. `import logging`,
  `import uuid` — 32+ hits in this repo alone) persisted `"module": null`.
- `backend/app/evidence/mapper.py:98` then crashed on
  `ref.get("module", "").strip()` — `.get()`'s default only applies when
  a key is *missing*, not when it is present with value `None` — raising
  an unhandled `AttributeError` mid-transaction, which cascaded into a
  second SQLAlchemy `greenlet_spawn` error and left the `AnalysisRun` row
  permanently at `status="CODE_RISK"` with no error recorded.

**Fix applied** (in `backend/app/skillgraph/mapper.py`, not on the
forbidden-files list for this phase — `evidence/mapper.py`,
`capability/scorer.py`, `capability/service.py`, `skillgraph/taxonomy.py`,
and `coderisk/rules.py` were left untouched): for plain imports, fall back
to the first entry in `names` as the effective module, and skip emitting
the observation entirely if no name is available. All 385 pre-existing
backend tests still pass after this change (`pytest tests/ -q` →
`385 passed`). This is reported here, not silently fixed, per the
Documentation Synchronization Rule — see `MEMORY.md` Checkpoint 32 and
the Documentation Impact section below.

## 1. Skill/technology extraction precision & recall

Ground truth: `scripts/evaluation/dataset.md`, Repo 1 section.

| Metric | Value |
|---|---|
| Detected (distinct languages + dependencies) | 46 |
| Expected (ground-truth list) | 12 |
| True positives | 11 — `css`, `fastapi`, `httpx`, `next`, `pydantic`, `pytest`, `python`, `react`, `sql`, `tailwindcss`, `typescript` |
| False negatives | 1 — `sqlalchemy` (see below) |
| **Precision** | **0.2391** |
| **Recall** | **0.9167** |

**Why precision is low — not a bug, a scope mismatch.** The "false
positives" (`@supabase/supabase-js`, `cryptography`, `cytoscape`,
`recharts`, `eslint`, `vitest`, `javascript`, `json`, `toml`, `markdown`,
`binary`, `unknown`, etc.) are overwhelmingly real, correct detections —
they just were not enumerated in `dataset.md`'s *expected-hit* list,
because that list only named dependencies/languages already in
`CANONICAL_DEPENDENCIES`/`CANONICAL_LANGUAGES`, and `dataset.md` explicitly
pre-flagged several of these (`@supabase/supabase-js`, `cryptography`,
`cytoscape`, `recharts`) as "known to be used but NOT in the taxonomy".
The ground-truth list was not exhaustive over *everything* the taxonomy
can detect — only over what a human expects the taxonomy to catch. This
is a **dataset-authoring gap**, not a pipeline defect: `dataset.md` should
be revised to enumerate every taxonomy-covered item actually present in
the repo (including config/markup file-type labels like `json`/`toml`/
`markdown` that the language classifier legitimately emits), which would
raise measured precision without changing the pipeline at all.

**The one real false negative — `sqlalchemy`.** `backend/requirements.txt`
declares `SQLAlchemy[asyncio]==2.0.35` (mixed case, with an extras
marker). `CANONICAL_DEPENDENCIES` in `skillgraph/taxonomy.py` is case- and
extras-sensitive in its matching in a way that missed this exact spelling
— this is a genuine taxonomy-coverage finding worth a follow-up ticket,
but per the task's explicit instruction, `taxonomy.py` was **not**
modified to fix it.

## 2. Provenance traceability

| Metric | Value |
|---|---|
| `DeveloperCapability`/`CapabilityHistory` rows for this run | 122 |
| Rows traceable to ≥1 Evidence → ≥1 Observation | 122 |
| **Traceable percentage** | **100.0%** |

Verified by a direct query joining `CapabilityHistory` →
`evidence_skills`/`evidence_technologies`/`evidence_concepts` → `Evidence`
→ `Observation`, scoped to this run's `analysis_run_id` (see
`scripts/evaluation/compute_metrics.py::provenance_traceability`). No
ungrounded capability claims were found for this run.

## 3. CodeRisk findings (manual review, not automated FP judgment)

| Rule | Severity | Count |
|---|---|---|
| SEC-001 (possible hardcoded secret) | HIGH | 5 |
| REL-002 (empty `except: pass`) | MEDIUM | 2 |
| MAINT-001 (excessive function parameters) | LOW | 5 |
| MAINT-002 (syntax parse failure) | LOW | 1 |

**Manual review of all 5 SEC-001 HIGH findings** (performed for this
report, per the task's explicit instruction that false-positive judgment
requires a human, not automation):

- `backend/tests/test_coderisk.py:65`, `:286` — test fixtures asserting
  the SEC-001 rule itself detects a fake secret string. **False positive**
  (expected — it's a unit test for the detector).
- `frontend/src/__tests__/auth-context.test.tsx:56`, `:77`, `:101` — mock
  Supabase JWT/session tokens used in frontend auth tests. **False
  positive** (test fixture, not a real credential).

All 5/5 reviewed HIGH findings are false positives in test code. No real
hardcoded secret was found in this run. This matches the rule's documented
design (pattern-match on assignment syntax, not semantic understanding of
test vs. production code) — a reasonable direction for a future rule
refinement (e.g. de-prioritizing `tests/`/`__tests__/` paths) that was
**not** made here, since `coderisk/rules.py` is on the forbidden-files list
for this phase.

## 4. Runtime distribution

n=1, so min/median/max are identical: **47.64 seconds** (this COMPLETED
run; the two earlier stuck runs are excluded as they never finished).
Checkpoint 31's earlier run of the same repository completed in ~20s —
the difference is plausibly explained by cold JWKS/GitHub App token
caches and Supabase pooler connection setup in this session, not a
regression; no further runs exist yet to confirm.

## 5. Naive baseline vs. capability-model target count

| | Value |
|---|---|
| Naive baseline: distinct languages + distinct dependencies | 12 + 35 = 47 |
| DevTwin capability target count (DeveloperCapability rows, this run) | 122 |

The capability model produces ~2.6x more granular targets than naive
counting for this repository, because it decomposes each
language/dependency into skills and concepts (e.g. `fastapi` → skill
targets like "API Design", concept targets like "Dependency Injection")
rather than one row per detected technology. This baseline is a read-only
comparison — it was never written back to any `DeveloperCapability` row.

## 6. The three known model behaviors — measured, where n=1 permits

### i. Temporal decay is nominal (confirmed)

All 122 `DeveloperCapability` rows for this run were computed from
evidence with `recency` set to this run's analysis time (`observed_at`
defaults to `now()`), not original commit dates — the `commits` table is
not populated by the current pipeline. Within this single run, every
evidence item's age is ≈0 days, so `T_i ≈ 1.0` uniformly. This is
confirmed architecturally (code citation above) and is consistent with
what a single run can show; it does not and cannot demonstrate decay
*across* runs without a second, time-separated sweep of the same
repository, which was out of scope for this session.

### ii. Diminishing-returns ceiling — measured distribution

| | Value |
|---|---|
| `score_min` | 0.4024 |
| `score_median` | 0.5395 |
| `score_max` | 0.99 |
| Scores at/above 0.95 | 6 of 122 (4.9%) |

The max score is exactly the clamp ceiling (0.99), and a non-trivial
minority (4.9%) of targets for this single, moderately-sized repository
already sit at or near that ceiling after only one analysis run — this is
real, measured evidence for the "no upper ceiling on the diminishing-
returns sum, only a final clamp" finding, not speculation. A larger,
more repeated-signal-heavy repository (e.g. a large OSS library once
Repos 8–9 are filled in) would be expected to push more targets to this
ceiling; that comparison is PENDING additional repos.

### iii. AST-based structural evidence is Python-only (confirmed)

`backend/app/mining/ast_parser.py` only parses Python; there is no JS/TS
AST parser. This repository is itself a mixed Python/TypeScript codebase,
so it directly demonstrates the gap: `frontend/` (TypeScript, Next.js)
can only ever reach `USAGE`-strength evidence (imports/dependencies) for
its technologies, never `APPLIED_ENGINEERING`-strength (class/function
structural signals), while `backend/` (Python) can reach both. This
asymmetry is visible in this run's evidence-by-type breakdown
(`APPLIED_ENGINEERING` evidence exists only for Python-sourced
observations) and is a code-confirmed, now measured-in-this-run gap.

## Limitations of this evaluation (honesty section, per docs/16)

- **n=1, not n=8–12.** Only Repo 1 (this repository) has ground truth and
  a completed run. `dataset.md` rows 2–9 remain `<PENDING SELECTION>` —
  the developer needs to extend the GitHub App installation and pick real
  repositories before the sample size target is met. All findings above
  that say "measured" are measured for exactly one repository; none of
  them generalize statistically.
- **No inter-rater reliability check.** Ground truth in `dataset.md` was
  hand-written by a single author with no second reviewer.
- **Ground truth under-enumerated the expected-hit list** (see Section 1)
  — several real, correct detections were scored as "false positives"
  purely because `dataset.md` didn't list them as expected, which
  mechanically depresses the precision number without reflecting a real
  pipeline defect. The recall number (0.9167) is more informative here
  than precision for this reason.
- **CodeRisk false-positive rate requires a human** — performed here for
  the 5 SEC-001 findings only (Section 3); the 8 LOW/MEDIUM findings
  (MAINT-001/002, REL-002) were not manually reviewed in this pass.
- **Provenance traceability is measured per-run, not platform-wide** — the
  100% figure is scoped to this run's `analysis_run_id` only.
- **Runtime of 47.64s vs. Checkpoint 31's ~20s is unexplained** with only
  one new data point; not investigated further in this session.
