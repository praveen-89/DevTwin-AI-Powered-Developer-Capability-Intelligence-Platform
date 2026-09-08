# 18. Decisions Log

## Architectural Rule
Whenever implementation later changes an architectural decision:
1. Update the relevant documentation.
2. Add the decision to this log.
3. Explain why the decision changed.

---

## Log

### Decision: Relational Database over Graph DB
*   **Context**: The SkillGraph inherently models nodes and edges.
*   **Options**: 1) Neo4j, 2) PostgreSQL, 3) ArangoDB.
*   **Chosen Approach**: PostgreSQL.
*   **Reason**: DevTwin Minor needs to establish the data foundation without over-engineering or requiring specialized DB ops. PostgreSQL handles junctions and recursive queries well enough for the MVP scope.
*   **Consequences**: Graph traversals are simulated via JOINs and recursive CTEs.

### Decision: Internal vs. External Identifiers
*   **Context**: DevTwin interacts with GitHub, which provides its own immutable IDs.
*   **Options**: 1) Use GitHub IDs as primary keys, 2) Auto-incrementing integers, 3) Internal UUIDv4.
*   **Chosen Approach**: Internal UUIDv4 for PKs. Separate `github_id` columns.
*   **Reason**: Decouples the core identity system from GitHub, allowing future extensibility (GitLab, Bitbucket) and preventing collisions.
*   **Consequences**: Requires mapping lookups when syncing data from GitHub webhooks.

### Decision: Observation vs. Evidence Separation
*   **Context**: Analysis generates raw facts, which then imply capability.
*   **Options**: 1) Single `evidence` table, 2) Split `observations` (facts) and `evidence` (contextualized facts).
*   **Chosen Approach**: Split models.
*   **Reason**: Separation of concerns. An Observation (e.g., "Found Dockerfile") is immutable. Evidence ("Developer applied Containerization, strength 0.8") is an interpretation that might change if the scoring model updates.
*   **Consequences**: Slightly more complex pipeline (Mining -> Observation -> Evidence Engine -> Evidence).

### Decision: Capability History
*   **Context**: Need to track how a developer improves.
*   **Options**: 1) Update score in place, 2) Append-only history table.
*   **Chosen Approach**: Append-only `capability_history` table linked to `developer_capabilities` (current state).
*   **Reason**: Enables temporal trend analysis, visualization of skill gaps over time, and reproducible audits.
*   **Consequences**: Database storage will grow proportionally to the number of analysis runs over time.

### Decision: Capability Target Strategy
*   **Context**: Capabilities can target a Skill, Technology, or Concept.
*   **Options**: 1) Polymorphic FK (`target_id`, `target_type`), 2) Separate tables, 3) Exclusive Arc (multiple nullable FKs).
*   **Chosen Approach**: Exclusive Arc (nullable `skill_id`, `technology_id`, `concept_id` with `CHECK` constraint).
*   **Reason**: Preserves database-level referential integrity and cascading deletes, which option 1 breaks.
*   **Consequences**: Slightly wider table, strict `CHECK` constraint required.

### Decision: Asynchronous Analysis Runs
*   **Context**: Repository mining takes minutes.
*   **Options**: 1) Inline HTTP processing, 2) Background jobs with state tracking.
*   **Chosen Approach**: `analysis_jobs` and `analysis_runs` tables with explicit ENUM states.
*   **Reason**: Prevents API timeouts, enables reproducible runs, and handles failure gracefully.
*   **Consequences**: Requires a Redis/Worker architecture.

### Decision: Row Level Security (RLS) Approach
*   **Context**: Protecting developer privacy.
*   **Options**: 1) Application-level checks, 2) Database RLS.
*   **Chosen Approach**: Database RLS using Supabase conventions.
*   **Reason**: Defense in depth. Ensures a developer can only query records tracing back to their `developer_id`.
*   **Consequences**: Requires complex RLS policies for deep relationships (e.g., viewing `risk_findings` requires joining through `repositories` and `projects`).

### Decision: Delaying SQL Migrations
*   **Context**: The database specification is complete, but SQL files are not written.
*   **Options**: 1) Write migrations now, 2) Wait for next phase.
*   **Chosen Approach**: Wait.
*   **Reason**: The specification must be reviewed before committing to SQL syntax, ensuring the ORM choice (SQLAlchemy vs Prisma vs Raw SQL) dictates how migrations are physically generated.
*   **Consequences**: The repository remains conceptually complete but requires an implementation step before code runs.
