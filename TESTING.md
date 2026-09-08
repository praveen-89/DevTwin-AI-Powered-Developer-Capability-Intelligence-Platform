---
Status: Active
Version: 1.0
Last Updated: 2026-09-08
Source of Truth: TESTING.md
---

# Testing Strategy

## Testing Philosophy
DevTwin relies on high-fidelity deterministic analysis. A bug in the analysis pipeline will corrupt the capability history, which defeats the purpose of the product. Testing must prioritize pipeline correctness, database integrity, and UI explainability.

## Testing Pyramid
`Unit -> Integration -> System -> End-to-End`

## Backend Testing
*   **API Tests**: Validate REST endpoints, payload shapes, and HTTP status codes using FastAPI test clients.
*   **Service Tests**: Isolate business logic from database boundaries.
*   **Repository Mining Tests**: Run extractors against known mock repositories with predefined Git histories and file trees to ensure deterministic extraction.
*   **Validation Tests**: Ensure Pydantic models reject invalid states.

## SkillGraph Testing
*   **Entity Extraction**: Ensure correct parsing of technologies.
*   **Relationships**: Validate the graph topology after insertions.
*   **Consistency**: Ensure graph cycles or invalid relations (e.g., missing concepts) are rejected.
*   **Duplicate Handling**: Verify unique constraints prevent duplicate nodes.

## CodeRisk Testing
*   **Finding Detection**: Run CodeRisk engine against known vulnerable/smelly code snippets to verify detection.
*   **Severity & Confidence**: Ensure heuristics apply the correct severity and confidence levels.
*   **False Positives/Negatives**: Maintain a benchmark test suite of real-world code to track heuristic accuracy.
*   **Provenance**: Verify risk signals correctly store file/line number references.

## Evidence Testing
*   **Observation -> Evidence**: Verify the logic that translates a raw fact into contextualized evidence.
*   **Strength & Polarity**: Ensure negative observations result in negative polarity evidence.

## Capability Testing
*   **Score Calculation**: Provide a fixed set of mock Evidence weights to the Capability Engine and assert the resulting mathematically normalized score matches expectations.
*   **History Logs**: Verify that updating a capability score correctly appends an immutable record to `capability_history`.
*   **Skill Gaps**: Verify gap calculations delta correctly against targets.

## Database Testing
*   **Constraints**: Attempt to insert invalid data (e.g., polymorphic violation in Exclusive Arcs) to ensure `CHECK` constraints trigger.
*   **RLS**: Authenticate as Developer A and attempt to query Developer B's data; assert access is denied.
*   **Migrations**: Test applying and rolling back migration scripts against an empty test database.

## Frontend Testing
*   **Components**: Unit test UI components (e.g., the Capability Radar chart) with mock JSON props.
*   **States**: Test loading skeletons, error boundaries, and empty state visuals.
*   **Accessibility**: Automated a11y checking for dashboard elements.

## End-to-End (E2E)
Critical user flows must be tested via browser automation (e.g., Playwright/Cypress):
`Signup/Login -> GitHub Connection -> Repository Selection -> Analysis Queue -> Dashboard Render -> Capability Drilldown -> Evidence Provenance Check`

## Regression Testing
Every bug fix involving data extraction, capability scoring, or UI rendering must have a regression test added to the suite where practical.

## Evaluation
For academic/research-level evaluation regarding the validity of the "Evidence-Backed Capability Paradigm," refer to `docs/16_EVALUATION_PLAN.md`.
