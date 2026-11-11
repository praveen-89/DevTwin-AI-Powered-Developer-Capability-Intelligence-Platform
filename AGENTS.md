---
Status: Active
Version: 2.0
Last Updated: 2026-11-12
Source of Truth: AGENTS.md
---

# DevTwin Agent Operating Manual

## Project Context
DevTwin is an AI-powered Developer Capability Intelligence Platform. It maintains an evolving representation of a developer's capabilities based on evidence extracted from repositories.

## Current Development Stage
**Full-Stack MVP Implemented & Live-Verified (v0.8 / Checkpoint 31).**
*Note: Backend API, database migrations, asynchronous worker pipeline (all 8 stages), Supabase auth session integration, GitHub App connection, and interactive Next.js dashboard are fully implemented and verified with 385 backend tests and 64 frontend tests passing. Adhere strictly to the documented domain models, contracts, and RLS policies when extending the platform.*

## Source-of-Truth Hierarchy
The system enforces strict document boundaries. No document should claim universal authority over unrelated layers.
*   `PRD.md`: **Product intent** (What the product should accomplish and why).
*   `DESIGN.md`: **UX intent** (How users interact with the product).
*   `ARCHITECTURE.md`: **Architecture** (How the system is structurally designed).
*   `docs/DOMAIN_MODEL.md`: **Domain** (What the system's concepts and relationships mean).
*   `docs/11_DATABASE_SCHEMA.md`: **Database** (How persistent domain data is represented).
*   `docs/12_API_SPECIFICATION.md`: **API** (External/backend contracts).
*   **Actual Code**: **Implementation** (What is currently implemented).
*   **Tests**: **Tests** (What behavior is mechanically verified).
*   `DECISIONS.md`: **Decisions** (Why important choices were made).
*   `MEMORY.md`: **Memory** (Durable project knowledge).

## Repository Structure
*   `docs/` - Canonical technical specifications.
*   `backend/` - FastAPI backend services, REST APIs, and JWKS authentication.
*   `frontend/` - Next.js 16 (App Router, Turbopack, Tailwind CSS v4, Cytoscape, Recharts) application.
*   `workers/` - Background Python analysis workers (`workers/runner.py`) executing the 8-stage pipeline.
*   `database/` - SQL migrations (001-005) for PostgreSQL/Supabase with RLS.
*   `scripts/`, `tests/` - Utilities and end-to-end integration test suites.

## Identity & Mapping Rules
*   **Developer Identity Mapping**: We strictly map: `Supabase auth.users.id -> developers.auth_user_id`. `developers.id` remains a unique internal UUID. Do NOT force `developers.id = auth.uid()`. GitHub IDs remain purely external identifiers.

## Technology Stack (Approved)
*   **Frontend**: Next.js 16, React 19, TypeScript, Tailwind CSS v4, Cytoscape, Recharts, Lucide React.
*   **Backend**: FastAPI, Python 3.11/3.12, SQLAlchemy, Pydantic v2, PyJWT (JWKS), Cryptography (Fernet).
*   **Database**: PostgreSQL / Supabase (27 tables with Row-Level Security).
*   **Queue**: PostgreSQL-native (`analysis_jobs` table using `SELECT ... FOR UPDATE SKIP LOCKED` polling, NOT Redis).

## Development Workflow
When an agent is invoked:
1. Inspect the repository structure.
2. Inspect relevant documentation.
3. Understand existing architecture before proposing changes.
4. Identify dependencies.
5. Plan changes explicitly.
6. Implement code/SQL.
7. Test the implementation.
8. **Update documentation** based on the Documentation Synchronization Rule.
9. Check for contradictions.
10. Report changes.

## Documentation Synchronization Rule (CRITICAL)
Every meaningful codebase change MUST trigger a documentation impact analysis. You must explicitly ask and answer:
1. What changed?
2. Which documents are affected?
3. Do those documents need updating?
4. Did this change create a new decision?

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
