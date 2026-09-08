---
Status: Active
Version: 1.0
Last Updated: 2026-09-08
Source of Truth: AGENTS.md
---

# DevTwin Agent Operating Manual

## Project Context
DevTwin is an AI-powered Developer Capability Intelligence Platform. It maintains an evolving representation of a developer's capabilities based on evidence extracted from repositories.

## Current Development Stage
**Implementation-Ready System Specification.**
*Note: Do NOT claim features, APIs, migrations, or application code are implemented. The project currently exists purely as a set of rigorous architectural and domain specifications.*

## Repository Structure
*   `docs/` - Canonical technical specifications (DB schema, API contracts, domain model).
*   `backend/` - (Pending) FastAPI backend services.
*   `frontend/` - (Pending) Next.js frontend application.
*   `workers/` - (Pending) Background Python analysis workers.
*   `database/` - (Pending) SQL migrations.
*   `scripts/`, `tests/` - (Pending) Utilities and test suites.

## Technology Stack (Approved)
*   **Frontend**: Next.js, TypeScript, Tailwind CSS.
*   **Backend**: FastAPI, Python.
*   **Database**: PostgreSQL / Supabase.
*   **Queue**: Redis.

## Architecture Rules
*   **Frontend**: Responsible purely for UI, state, and API consumption. Does no repository analysis.
*   **Backend**: Responsible for synchronous API requests, database querying, and queue management.
*   **Workers**: Responsible for heavy repository mining, Git fetching, AST parsing, and executing the capability math.
*   **Database**: The ultimate source of truth, enforcing referential integrity and tracking temporal history.
*   **AI/ML**: Used strictly for explanation generation and semantic mapping. Core capability scoring is deterministic math.

## Development Workflow
When an agent is invoked:
1. Inspect the repository structure.
2. Inspect relevant documentation (e.g., `PRD.md`, `DOMAIN_MODEL.md`).
3. Understand existing architecture before proposing changes.
4. Identify dependencies.
5. Plan changes explicitly.
6. Implement code/SQL.
7. Test the implementation.
8. **Update documentation** based on the Documentation Synchronization Rule.
9. Check for contradictions.
10. Report changes.

## Change Protocol
*   **Modifying Architecture**: Inspect `ARCHITECTURE.md` and `DECISIONS.md`.
*   **Modifying Product Behavior**: Inspect `PRD.md`.
*   **Modifying UI**: Inspect `DESIGN.md`.
*   **Modifying Tests**: Inspect `TESTING.md`.

## Documentation Synchronization Rule (CRITICAL)
Every meaningful codebase change MUST trigger a documentation impact analysis. You must explicitly ask and answer:
1. What changed?
2. Which documents are affected?
3. Do those documents need updating?
4. Did this change create a new decision?
5. Did this change invalidate an existing assumption?

### Documentation Change Matrix

| Change | Required Documentation Review |
| :--- | :--- |
| New feature | PRD, ARCHITECTURE, TESTING |
| API change | API, ARCHITECTURE, TESTING |
| DB change | DATABASE, DOMAIN, ARCHITECTURE, TESTING |
| UI change | DESIGN, PRD, TESTING |
| New technology | ARCHITECTURE, RULES, DECISIONS |
| Architecture change| ARCHITECTURE, DECISIONS, AGENTS |
| AI/ML change | ARCHITECTURE, DECISIONS, TESTING |
| Security change | RULES, ARCHITECTURE, TESTING |
| New domain entity | DOMAIN, DATABASE, API |
| New engineering rule| RULES, AGENTS |
| Important discovery| MEMORY |
| Superseded decision| DECISIONS + affected docs |
| Bug fix | TESTING + affected docs if behavior changes |

## Prevent Documentation Drift
A pull request or implementation task is NOT considered complete if the implementation materially changes documented behavior but the relevant living documentation remains stale. Agents must explicitly report the Documentation Impact in their final output.

## Forbidden Behaviors
Agents must NOT:
*   Invent requirements.
*   Silently change architecture.
*   Introduce technologies (Kafka, Neo4j, K8s) without justification and ADR.
*   Modify database design casually.
*   Create undocumented APIs.
*   Bypass tests.
*   Delete important functionality without recording it.
*   Claim implementation when only specification exists.
*   Use AI/LLM where deterministic logic is sufficient.
*   Turn DevTwin into a generic chatbot.
*   Over-engineer the Minor project MVP.
