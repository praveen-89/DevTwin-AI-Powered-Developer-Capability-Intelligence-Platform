---
Status: Active
Version: 1.0
Last Updated: 2026-09-08
Source of Truth: DECISIONS.md
---

# Architecture Decision Records (ADRs)

## ADR-001: Relational Database over Graph DB
*   **Date**: 2026-09-08
*   **Status**: ACTIVE
*   **Title**: Use PostgreSQL to represent the SkillGraph
*   **Context**: The SkillGraph inherently models nodes (Skills, Techs) and edges (Relationships).
*   **Problem**: Do we need a dedicated graph database (Neo4j)?
*   **Decision**: Use PostgreSQL with relational junction tables.
*   **Alternatives Considered**: Neo4j, ArangoDB.
*   **Why This Decision**: DevTwin Minor needs to establish the data foundation without over-engineering or requiring specialized ops. PostgreSQL recursive CTEs and JOINs handle the MVP scope perfectly.
*   **Consequences**: Graph traversals are simulated via SQL.
*   **Affected Components**: Database, SkillGraph Builder.
*   **Related Documentation**: `docs/11_DATABASE_SCHEMA.md`

## ADR-002: Internal vs. External Identifiers
*   **Date**: 2026-09-08
*   **Status**: ACTIVE
*   **Title**: Use UUIDv4 for internal PKs, segregate GitHub IDs
*   **Context**: DevTwin integrates deeply with GitHub, which has its own IDs.
*   **Problem**: Should `repositories.id` be the GitHub Repo ID?
*   **Decision**: No. All internal tables use UUIDv4 for primary keys. External IDs are separate tracking columns (e.g., `github_repo_id BIGINT`).
*   **Alternatives Considered**: Using external IDs as PKs, Auto-increment integers.
*   **Why This Decision**: Decouples identity from GitHub, ensuring DevTwin can support GitLab, Bitbucket, or local projects later without schema changes.
*   **Consequences**: Requires mapping lookups during webhook syncs.
*   **Affected Components**: Database Schema.
*   **Related Documentation**: `docs/11_DATABASE_SCHEMA.md`

## ADR-003: Observation vs. Evidence Separation
*   **Date**: 2026-09-08
*   **Status**: ACTIVE
*   **Title**: Split raw facts from contextualized evidence
*   **Context**: Analysis produces facts which imply capabilities.
*   **Problem**: Should they be stored in one table?
*   **Decision**: Separate `observations` from `evidence`.
*   **Why This Decision**: An observation is immutable ("Dependency X found"). Evidence is an interpretation ("Demonstrates Usage") that might change if scoring models update.
*   **Consequences**: Requires an Evidence Engine step in the pipeline.

## ADR-004: Append-Only Capability History
*   **Date**: 2026-09-08
*   **Status**: ACTIVE
*   **Title**: Capability scores must track temporal history
*   **Decision**: Create an append-only `capability_history` table rather than just updating the score in `developer_capabilities` in place.
*   **Why This Decision**: Enables tracking growth, measuring intervention outcomes, and temporal trend analysis.

## ADR-005: Exclusive Arc Capability Target
*   **Date**: 2026-09-08
*   **Status**: ACTIVE
*   **Title**: Avoid polymorphic foreign keys for capability targets
*   **Context**: A Capability can target a Skill, Tech, or Concept.
*   **Problem**: Standard `(target_id, target_type)` breaks database referential integrity.
*   **Decision**: Use an Exclusive Arc: `skill_id`, `technology_id`, `concept_id` as nullable FKs with a `CHECK` constraint ensuring exactly one is populated.
*   **Why This Decision**: Guarantees true database foreign keys and `ON DELETE CASCADE` behaviors.

## ADR-006: Asynchronous Worker Architecture
*   **Date**: 2026-09-08
*   **Status**: ACTIVE
*   **Title**: Repository analysis must be fully asynchronous
*   **Decision**: Use `analysis_jobs` (queue) and `analysis_runs` (stateful execution) tables with strict ENUM states.
*   **Why This Decision**: Repository mining is too slow for synchronous HTTP requests.

## ADR-007: Database Row Level Security
*   **Date**: 2026-09-08
*   **Status**: ACTIVE
*   **Title**: Employ PostgreSQL RLS for authorization
*   **Decision**: Use Supabase/PostgreSQL RLS policies.
*   **Why This Decision**: Defense in depth. A developer must never be able to query another developer's capabilities.

## ADR-008: Delaying Migration Generation
*   **Date**: 2026-09-08
*   **Status**: ACTIVE
*   **Title**: Delay physical SQL migration files until specification approval
*   **Context**: Schema is defined conceptually but `.sql` files are missing.
*   **Decision**: Halt before writing code/migrations.
*   **Why This Decision**: Specifications must be approved, and the choice of ORM (SQLAlchemy vs Prisma) will dictate how migrations are actually authored.
