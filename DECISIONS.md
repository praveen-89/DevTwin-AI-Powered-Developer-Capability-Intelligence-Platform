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
*   **Status**: SUPERSEDED
*   **Title**: Delay physical SQL migration files until specification approval
*   **Decision**: Halt before writing code/migrations.
*   **Why This Decision**: Specifications must be verified and consistent.
*   **Superseded By**: Implementation milestone v0.1 where migrations were physically generated.

## ADR-010: Risk Does Not Equal Incompetence
*   **Date**: 2026-09-09
*   **Status**: ACTIVE
*   **Title**: CodeRisk acts as an evidence generator, not a direct competence scorer
*   **Context**: How to penalize capability based on bad code.
*   **Decision**: A risk finding generates negative evidence but does not directly overwrite or reset a capability score to zero.
*   **Why This Decision**: Developers make mistakes or work under constraints. Risk is a behavioral signal to be weighed, not definitive proof of complete incompetence.

## ADR-011: Evidence-Backed Capabilities
*   **Date**: 2026-09-09
*   **Status**: ACTIVE
*   **Title**: No capability score without evidence
*   **Context**: Ensuring the validity of capability metrics.
*   **Decision**: Capability scores must be entirely derived from verifiable evidence (observations).
*   **Why This Decision**: Prevents the platform from guessing or assigning arbitrary scores.

## ADR-012: v0.1 Foundation & StudyTwin Deferral
*   **Date**: 2026-09-09
*   **Status**: ACTIVE
*   **Title**: Focus on Capability Intelligence Foundation (v0.1); Defer StudyTwin (Major)
*   **Context**: Scoping the initial implementation.
*   **Decision**: v0.1 establishes the foundational assessment engine (SkillGraph, CodeRisk, Evidence, Capability). StudyTwin (personalized learning, outcome measurement) is deferred to a future Major phase.
*   **Why This Decision**: Essential to prove the analytical extraction works before building a learning layer on top of it.

## ADR-013: RLS as Defense-in-Depth
*   **Date**: 2026-09-09
*   **Status**: ACTIVE
*   **Title**: Database-level Row Level Security (RLS) for data isolation
*   **Context**: Preventing cross-developer data leakage.
*   **Decision**: Implement strict RLS policies on all developer-owned tables, tracking ownership up to `developers.auth_user_id`.
*   **Why This Decision**: Ensures that even if the API layer has an authorization flaw, the database engine enforces the "Developer A cannot access Developer B's private data" rule.

## ADR-014: Authentication & Identity Architecture
*   **Date**: 2026-09-10
*   **Status**: ACTIVE
*   **Title**: Supabase Auth with JWKS and Hybrid GitHub App Flow
*   **Context**: Securing DevTwin access and safely connecting GitHub repositories without exposing sensitive tokens.
*   **Decision**: 
    1. Verify Supabase JWTs via JWKS instead of the legacy secret.
    2. Explicitly map developers via `POST /developers/me`.
    3. Use a hybrid GitHub App flow: require user authorization during App installation. The authenticated GitHub user access token is used to verify that the user has access to the specified GitHub App installation (`GET /user/installations`). (Note: `GET /user/installations/{installation_id}/repositories` can be used later to determine repository-level access).
    4. Store only the `installation_id` in `github_accounts`. Do not persist user or installation access tokens.
    5. Maintain short-lived OAuth state in PostgreSQL (`github_connection_states`) instead of Redis.
*   **Why This Decision**: It ensures cryptographically proven identity boundaries, eliminates persistent GitHub credentials, prevents installation ID spoofing, and keeps the Minor MVP stack simple (no Redis).
