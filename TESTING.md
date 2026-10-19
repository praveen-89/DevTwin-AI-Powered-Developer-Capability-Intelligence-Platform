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
*   **Current Status**: `pytest -q` -> 266 passed, 15 pre-existing mock warnings.
*   **Scope**: Covers foundation, health checks, configuration, developer registration, projects, repositories (registration, listing, retrieval), GitHub connection/disconnect flows, analysis pipeline job submission/polling (`test_analysis.py`), worker runner queue claiming, attempt tracking, safe repository extraction, isolated temporary workspace lifecycle, non-terminal `CODE_RISK`/`PROCESSING` lifecycle state, repeated-invocation safety, error sanitization (`test_worker.py`), repository mining file-tree traversal, exclusions, language classification, defensive manifest extraction (`package.json`, `requirements.txt`, `Cargo.toml`), Python AST parsing, archive streaming/extraction limits (`test_mining.py`), SkillGraph deterministic entity and taxonomy mapping, AST concept extraction, provenance-backed observations, deduplication, snapshot persistence (`test_skillgraph.py`), CodeRisk static risk analysis rules (hardcoded secrets, code execution constructs, insecure deserialization, bare excepts, empty exception handlers, excessive function parameters, syntax errors, missing test suites), secret evidence redaction, snapshot persistence, and worker lifecycle integration (`test_coderisk.py`), and RLS NULL ownership regression guards.
*   **API Tests**: Validate REST endpoints, payload shapes, ownership isolation, and HTTP status codes using FastAPI test clients.
*   **Worker & Fetcher Tests**: Validate atomic queue claiming (`FOR UPDATE SKIP LOCKED`), maximum attempt bounding (`MAX_JOB_ATTEMPTS = 3`), non-terminal Stage 5 lifecycle preservation, repeated-invocation safety, Zip Slip / path traversal protection, corrupt archive recovery, ephemeral token cleanup, and sanitized error mapping.
*   **Repository Mining Tests** (`test_mining.py`): Validate safe file-tree traversal, exclusion of `.git`/dependency/build/cache directories, symlink rejection, binary detection, language metrics calculation, `package.json`/`requirements.txt`/`Cargo.toml` extraction, syntax error tolerance, Python AST function/class/import extraction, and archive member/size limit enforcement.
*   **SkillGraph Tests** (`test_skillgraph.py`): Validate token normalization, canonical language and dependency taxonomy mapping, ungrounded package handling without hallucination, AST class/async function/import concept extraction, parse error and warning observation mapping, empty repository safety, entity deduplication, database snapshot persistence, and worker status lifecycle.
*   **CodeRisk Tests** (`test_coderisk.py`): Validate positive and negative detection across all 8 static rules (`SEC-001`, `SEC-002`, `SEC-003`, `REL-001`, `REL-002`, `MAINT-001`, `MAINT-002`, `TEST-001`), placeholder suppression, secret redaction, deterministic output sorting, binary/empty file safety, database snapshot replacement, observation pairing, rollback handling, and worker status lifecycle.
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
*   **Risk != Competence**: Verify that when a Risk finding is processed, it generates evidence that influences capability, but does *not* hard-reset a capability score to zero.

## Capability Testing
*   **Score Calculation**: Provide a fixed set of mock Evidence weights to the Capability Engine and assert the resulting mathematically normalized score matches expectations.
*   **History Logs**: Verify that updating a capability score correctly appends an immutable record to `capability_history`.
*   **Skill Gaps**: Verify gap calculations delta correctly against targets.

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
