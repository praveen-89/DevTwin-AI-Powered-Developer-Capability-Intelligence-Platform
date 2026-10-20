---
Status: Active
Version: 1.1
Last Updated: 2026-09-08
Source of Truth: TESTING.md
---

# Testing Strategy

*Source of Truth Context: This document defines what behavior is mechanically verified.*

## Testing Philosophy
DevTwin relies on high-fidelity deterministic analysis. A bug in the analysis pipeline will corrupt the capability history. Testing must prioritize pipeline correctness, database integrity, and UI explainability.

## Testing Pyramid
`Unit -> Integration -> System -> End-to-End`

## Backend Testing
*   **Current Status**: `pytest -q` -> 348 passed, 15 pre-existing mock warnings.
*   **Scope**: Covers foundation, health checks, configuration, developer registration, projects, repositories (registration, listing, retrieval), GitHub connection/disconnect flows, analysis pipeline job submission/polling (`test_analysis.py`), worker runner queue claiming, attempt tracking, safe repository extraction, isolated temporary workspace lifecycle, non-terminal `CAPABILITY`/`PROCESSING` lifecycle state, repeated-invocation safety, error sanitization (`test_worker.py`), repository mining file-tree traversal, exclusions, language classification, defensive manifest extraction (`package.json`, `requirements.txt`, `Cargo.toml`), Python AST parsing, archive streaming/extraction limits (`test_mining.py`), SkillGraph deterministic entity and taxonomy mapping, AST concept extraction, provenance-backed observations, deduplication, snapshot persistence (`test_skillgraph.py`), CodeRisk static risk analysis rules, secret redaction, safe AST detection for subprocess with shell=True, run-scoped idempotency without observation orphaning, snapshot persistence, and worker lifecycle integration (`test_coderisk.py`), Evidence Generation observation contextualization, reliability/strength/polarity assignment, taxonomy junction linking, idempotency, and rollback handling (`test_evidence.py`), Capability Scoring Engine deterministic mathematical aggregation, fine-grained evidence strength preservation, diminishing returns, temporal half-life decay, uncertainty-aware confidence calculation, exclusive-arc validation, run-scoped idempotency, and history append logging (`test_capability.py`), and RLS NULL ownership regression guards.
*   **API Tests**: Validate REST endpoints, payload shapes, ownership isolation, and HTTP status codes using FastAPI test clients.
*   **Worker & Fetcher Tests**: Validate atomic queue claiming (`FOR UPDATE SKIP LOCKED`), maximum attempt bounding (`MAX_JOB_ATTEMPTS = 3`), non-terminal Stage 7 lifecycle preservation (`CAPABILITY` status / `PROCESSING` job), repeated-invocation safety, Zip Slip / path traversal protection, corrupt archive recovery, ephemeral token cleanup, and sanitized error mapping.
*   **Repository Mining Tests** (`test_mining.py`): Validate safe file-tree traversal, exclusion of `.git`/dependency/build/cache directories, symlink rejection, binary detection, language metrics calculation, `package.json`/`requirements.txt`/`Cargo.toml` extraction, syntax error tolerance, Python AST function/class/import extraction, and archive member/size limit enforcement.
*   **SkillGraph Tests** (`test_skillgraph.py`): Validate token normalization, canonical language and dependency taxonomy mapping, ungrounded package handling without hallucination, AST class/async function/import concept extraction, parse error and warning observation mapping, empty repository safety, entity deduplication, database snapshot persistence, and worker status lifecycle.
*   **CodeRisk Tests** (`test_coderisk.py`): Validate positive and negative detection across all 8 static rules (`SEC-001`, `SEC-002`, `SEC-003`, `REL-001`, `REL-002`, `MAINT-001`, `MAINT-002`, `TEST-001`), including safe AST detection for `subprocess.Popen/run(..., shell=True)`, placeholder suppression, secret redaction, deterministic output sorting, binary/empty file safety, run-scoped idempotency without orphaning parent observations (D-1 fix), rollback handling, and worker status lifecycle.
*   **Evidence Tests** (`test_evidence.py`): Validate deterministic mapping from raw observations to evidence records across all types (`DEPENDENCY_FOUND` -> `MENTION`, `MODULE_IMPORTED` -> `USAGE`, `LANGUAGE_DETECTED` -> `USAGE`/`MENTION`, `CLASS_DEFINED` -> `APPLIED_ENGINEERING`, `FUNCTION_DEFINED` -> async/docstring `APPLIED_ENGINEERING` vs `USAGE`, `RISK_OBSERVED` -> severity-weighted negative polarity evidence), exclusion of diagnostic warnings from capability evidence, junction linking (`evidence_skills`, `evidence_technologies`, `evidence_concepts`), run-level repeated-execution idempotency, transaction rollback on failure, and worker pipeline integration.
*   **Capability Tests** (`test_capability.py`): Validate 66 hermetic unit and integration tests covering: evidence weighting components (`S * D * R * T * P`), persisted fine-grained evidence strength preservation across different constructs of the same type, zero-strength preservation, type-strength fallback if strength is None, 365-day half-life temporal decay, rank-ordered diminishing returns `w_k / sqrt(k)`, sigmoid aggregation `clamp(sigmoid(sum / 3.0), 0.01, 0.99)`, uncertainty-aware confidence bounds `[0.05, 0.98]`, negative evidence score suppression without zeroing (ADR-010), Exclusive Arc polymorph check constraints (`CHECK (num_nonnulls(skill_id, technology_id, concept_id) = 1)`), idempotency via run-scoped history purge and upsert, and pipeline worker runner execution advancing to Stage 7 `CAPABILITY`.
*   **Service Tests**: Isolate business logic from database boundaries.
*   **Job & Run Lifecycle**: Verify that job submission sets status to QUEUED and that discrete `analysis_runs` attempts track retries and error reporting.

## SkillGraph Testing
*   **Entity Extraction**: Ensure correct parsing of technologies, concepts, and skills from mined languages, manifests, and AST summaries.
*   **Relationships**: Validate the graph topology after insertions (skill_technologies, technology_concepts, skill_relationships).
*   **Consistency**: Ensure graph relationships adhere to schema constraints without orphaned or invalid keys.
*   **Duplicate Handling**: Verify unique constraints and in-memory deduplication prevent duplicate nodes and edges across repeated analysis runs.

## CodeRisk Testing
*   **Finding Detection**: Run CodeRisk engine against known vulnerable/smelly code snippets to verify detection across security, reliability, maintainability, and testing rules.
*   **Attribution correctness**: **CRITICAL**. Verify that a CodeRisk finding is only attributed to a developer if a Git commit directly links them to the exact introduced lines. Repository-wide risks (e.g. missing tests) must not be automatically blamed on all contributors.
*   **Severity & Confidence**: Ensure heuristics apply the correct schema-valid severity and confidence levels.
*   **Provenance**: Verify risk signals correctly store file/line number references and are paired with immutable `Observation` records.

## Evidence Testing
*   **Observation -> Evidence**: Verify the logic that translates a raw fact into contextualized evidence.
*   **Risk != Competence**: Verify that when a Risk finding is processed, it generates negative polarity evidence (`-1.0` to `-0.2`) that influences capability aggregation, but does *not* hard-reset a capability score to zero.
*   **Idempotency & Cleanliness**: Verify that repeated execution on the same run cleans up previous evidence and does not leave duplicate evidence rows or orphan junction links.

## Capability Testing
*   **Score Calculation**: Provide a fixed set of mock Evidence weights to the Capability Engine and assert the resulting mathematically normalized score matches expectations (`score = clamp(sigmoid(sum / 3.0), 0.01, 0.99)`).
*   **History Logs**: Verify that updating a capability score correctly appends an immutable record to `capability_history` tracking run attribution and deltas.
*   **Diminishing Returns & Half-Life**: Verify that 10 duplicate signals decay as `1/sqrt(k)` rather than linearly inflating the score, and evidence older than 365 days decays by 50%.
*   **Uncertainty-Aware Confidence**: Verify that single observations yield low confidence while diverse, recent, high-reliability evidence scales toward 0.98.
*   **Idempotency & Worker Integration**: Verify run-scoped history cleanup on re-run, developer capability upsert, and pipeline progression to `CAPABILITY`.

## Database Testing
*   **Constraints**: Attempt to insert invalid data (e.g., polymorphic violation in Exclusive Arcs) to ensure `CHECK` constraints trigger.
*   **RLS Security Regression**: Static security regression test to prevent RLS ownership bypasses (e.g., missing project_id).
*   **RLS Integration**: (Future hardening) Runtime database-level RLS integration test to authenticate as Developer A and attempt to query Developer B's data.

## Frontend Testing
*   **Components**: Unit test UI components (e.g., the Capability Radar chart) with mock JSON props.
*   **States**: Test loading skeletons, error boundaries, and empty state visuals.

## End-to-End (E2E)
Critical user flows must be tested via browser automation:
`Signup/Login -> GitHub Connection -> Repository Selection -> Analysis Job Queued -> Dashboard Render -> Capability Drilldown -> Evidence Provenance Check`

## Regression Testing
Every bug fix involving data extraction, capability scoring, or UI rendering must have a regression test added.
