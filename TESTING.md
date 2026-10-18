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
*   **Current Status**: `pytest -q` -> 218 passed, 15 pre-existing mock warnings.
*   **Scope**: Covers foundation, health checks, configuration, developer registration, projects, repositories (registration, listing, retrieval), GitHub connection/disconnect flows, analysis pipeline job submission/polling (`test_analysis.py`), worker runner queue claiming, attempt tracking, safe repository extraction, isolated temporary workspace lifecycle, non-terminal `FETCHING`/`PROCESSING` lifecycle state, repeated-invocation safety, and error sanitization (`test_worker.py`), and RLS NULL ownership regression guards.
*   **API Tests**: Validate REST endpoints, payload shapes, ownership isolation, and HTTP status codes using FastAPI test clients.
*   **Worker & Fetcher Tests**: Validate atomic queue claiming (`FOR UPDATE SKIP LOCKED`), maximum attempt bounding (`MAX_JOB_ATTEMPTS = 3`), non-terminal Stage 2 lifecycle preservation, repeated-invocation safety, Zip Slip / path traversal protection, corrupt archive recovery, ephemeral token cleanup, and sanitized error mapping.
*   **Service Tests**: Isolate business logic from database boundaries.
*   **Repository Mining Tests**: Run extractors against known mock repositories with predefined Git histories and file trees to ensure deterministic extraction.
*   **Job & Run Lifecycle**: Verify that job submission sets status to QUEUED and that discrete `analysis_runs` attempts track retries and error reporting.

## SkillGraph Testing
*   **Entity Extraction**: Ensure correct parsing of technologies.
*   **Relationships**: Validate the graph topology after insertions.
*   **Consistency**: Ensure graph cycles or invalid relations (e.g., missing concepts) are rejected.
*   **Duplicate Handling**: Verify unique constraints prevent duplicate nodes.

## CodeRisk Testing
*   **Finding Detection**: Run CodeRisk engine against known vulnerable/smelly code snippets to verify detection.
*   **Attribution correctness**: **CRITICAL**. Verify that a CodeRisk finding is only attributed to a developer if a Git commit directly links them to the exact introduced lines. Repository-wide risks must not be automatically blamed on all contributors.
*   **Severity & Confidence**: Ensure heuristics apply the correct severity and confidence levels.
*   **Provenance**: Verify risk signals correctly store file/line number references.

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
