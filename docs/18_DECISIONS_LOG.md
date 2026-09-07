# 18. Decisions Log

## Architectural Rule
Whenever implementation later changes an architectural decision:
1. Update the relevant documentation.
2. Add the decision to this log.
3. Explain why the decision changed.

---

## Log

### [Date: 2026-09-08] - Initial System Specification
-   **Decision**: Adopted a relational database (PostgreSQL) instead of a graph database (Neo4j) for the Minor MVP.
-   **Rationale**: To reduce infrastructure complexity while building the foundation. The relational schema is designed with junction tables to simulate graph traversal for the SkillGraph.
-   **Status**: Accepted.

### [Date: 2026-09-08] - Pipeline Architecture
-   **Decision**: Repository mining must occur in background workers, decoupled from HTTP requests.
-   **Rationale**: Repository fetching and AST parsing are I/O and CPU bound, which would cause API timeouts and poor UX if handled synchronously.
-   **Status**: Accepted.

### [Date: 2026-09-08] - AI Philosophy Boundary
-   **Decision**: Prohibit LLMs from directly generating capability scores from raw repository data.
-   **Rationale**: Ensures the system remains explainable and strictly adheres to the "No score without evidence" rule. LLMs are restricted to explanation generation and semantic mapping.
-   **Status**: Accepted.

### [Date: 2026-09-08] - Capability Target Polymorphism
-   **Decision**: Use the "Exclusive Arc" pattern (multiple nullable foreign keys with a CHECK constraint) instead of a generic `(target_id, target_type)` for `developer_capabilities`. Use junction tables for `evidence` targets.
-   **Rationale**: Preserves database-level referential integrity. Generic polymorphic foreign keys prevent the use of true database foreign key constraints, leading to orphaned records.
-   **Status**: Accepted.

### [Date: 2026-09-08] - State Tracking Enums
-   **Decision**: Use PostgreSQL ENUM types for `analysis_status`, `evidence_type`, `risk_category`, and `risk_severity`.
-   **Rationale**: Enforces strict typing at the database level, preventing invalid state insertions without relying solely on application-level validation.
-   **Status**: Accepted.
