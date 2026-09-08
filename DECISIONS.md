---
Status: Active
Version: 1.1
Last Updated: 2026-09-08
Source of Truth: DECISIONS.md
---

# Architecture Decision Records (ADRs)

*Source of Truth Context: This document defines why important choices were made.*

## ADR-001: Relational Database over Graph DB
*   **Date**: 2026-09-08
*   **Status**: ACTIVE
*   **Title**: Use PostgreSQL to represent the SkillGraph
*   **Context**: The SkillGraph inherently models nodes and edges.
*   **Decision**: Use PostgreSQL with relational junction tables.
*   **Alternatives Considered**: Neo4j, ArangoDB.
*   **Why This Decision**: DevTwin Minor needs to establish the data foundation without over-engineering. PostgreSQL recursive CTEs and JOINs handle the MVP scope perfectly.

## ADR-002: Internal Identifiers & Auth Mapping
*   **Date**: 2026-09-08
*   **Status**: ACTIVE
*   **Title**: Explicit Developer Identity Mapping
*   **Context**: Mapping Supabase authentication users to DevTwin Developer records.
*   **Decision**: `Supabase auth.users.id -> developers.auth_user_id`. `developers.id` remains an internal UUIDv4. GitHub IDs remain separate.
*   **Alternatives Considered**: `developers.id = auth.uid()`.
*   **Why This Decision**: Decouples identity from the authentication provider, ensuring DevTwin can migrate auth or support complex merges later without breaking the entire schema's internal primary keys.

## ADR-003: Observation vs. Evidence Separation
*   **Date**: 2026-09-08
*   **Status**: ACTIVE
*   **Title**: Split raw facts from contextualized evidence
*   **Decision**: Separate `observations` from `evidence`.
*   **Why This Decision**: An observation is an immutable fact ("Dependency X found"). Evidence is an interpretation ("Demonstrates Usage") that might change if scoring models update.

## ADR-004: Append-Only Capability History
*   **Date**: 2026-09-08
*   **Status**: ACTIVE
*   **Title**: Capability scores must track temporal history
*   **Decision**: Create an append-only `capability_history` table. Do NOT overwrite states.
*   **Why This Decision**: Enables tracking growth, measuring intervention outcomes, and temporal trend analysis.

## ADR-005: Exclusive Arc Capability Target
*   **Date**: 2026-09-08
*   **Status**: ACTIVE
*   **Title**: Avoid polymorphic foreign keys for capability targets
*   **Decision**: Use an Exclusive Arc: `skill_id`, `technology_id`, `concept_id` as nullable FKs with a `CHECK (num_nonnulls(...) = 1)`.
*   **Why This Decision**: Guarantees true database foreign keys and `ON DELETE CASCADE` behaviors, unlike generic `target_type/id`.

## ADR-006: Analysis Job vs. Analysis Run
*   **Date**: 2026-09-08
*   **Status**: ACTIVE
*   **Title**: Differentiate Request vs. Execution
*   **Context**: Jobs fail and need retries.
*   **Decision**: `analysis_jobs` tracks the user request. `analysis_runs` tracks discrete execution attempts.
*   **Why This Decision**: Properly supports retry mechanics, error logging per attempt, and reproducing specific executions.

## ADR-007: GitHub Ingestion Mechanism (Minor Scope)
*   **Date**: 2026-09-08
*   **Status**: ACTIVE
*   **Title**: Freeze GitHub OAuth + Repository Selection
*   **Decision**: The ingestion workflow is strictly OAuth-based repository selection. Public URL ingestion is excluded from Minor.
*   **Why This Decision**: Aligns with the developer-centric workflow and simplifies authorization/privacy boundaries.

## ADR-008: GitHub Token Security
*   **Date**: 2026-09-08
*   **Status**: ACTIVE
*   **Title**: Secure Token Storage
*   **Decision**: Plaintext OAuth tokens are never stored in the database. `access_token_enc` implies encrypted material or an external Vault reference.
*   **Why This Decision**: Prevents catastrophic exposure of developer source code if the database is compromised.

## ADR-009: Delaying Migration Generation
*   **Date**: 2026-09-08
*   **Status**: ACTIVE
*   **Title**: Delay physical SQL migration files until specification approval
*   **Decision**: Halt before writing code/migrations.
*   **Why This Decision**: Specifications must be verified and consistent. ORM choice will dictate the physical generation.
