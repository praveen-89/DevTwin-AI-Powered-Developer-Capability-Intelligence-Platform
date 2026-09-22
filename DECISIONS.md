---
Status: Active
Version: 1.2
Last Updated: 2026-09-23
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
*   **Date**: 2026-09-10 (Revised 2026-09-12)
*   **Status**: SUPERSEDED by ADR-015 (PKCE clause removed)
*   **Title**: Supabase Auth with JWKS and Hybrid GitHub App Flow
*   **Context**: Securing DevTwin access and safely connecting GitHub repositories without exposing sensitive tokens.
*   **Decision**:
    1. Verify Supabase JWTs via JWKS instead of the legacy secret.
    2. Explicitly map developers via `POST /developers/me`.
    3. Use a hybrid GitHub App flow: require user authorization during App installation (`Request user authorization (OAuth) during installation` enabled). A secure random `state` token binds the callback to the developer who initiated the flow.
    4. Store only the `installation_id` in `github_accounts`. Do not persist user or installation access tokens.
    5. Maintain short-lived OAuth state with an explicit atomic claim mechanism in PostgreSQL (`github_connection_states`).
    6. Safe Disconnect: `DELETE /github/disconnect` removes the active connection but preserves historical analysis data.
*   **Why This Decision**: It ensures cryptographically proven identity boundaries, eliminates persistent GitHub credentials, prevents installation ID spoofing, mitigates concurrent state consumption, and safely retains analytical intelligence data after disconnect.
*   **Superseded By**: ADR-015 clarifies the PKCE posture.

## ADR-015: PKCE Removed from GitHub App Installation Flow
*   **Date**: 2026-09-23
*   **Status**: ACTIVE
*   **Title**: GitHub /installations/new does not support PKCE; removed from install flow
*   **Context**: During the Step 4 final audit, a verification search against current GitHub documentation and behavior confirmed that the GitHub App installation endpoint (`https://github.com/apps/<slug>/installations/new`) ignores PKCE parameters (`code_challenge`, `code_challenge_method`). These parameters are only processed by the dedicated OAuth authorization endpoint (`https://github.com/login/oauth/authorize`). Because `GET /github/install` redirects to `/installations/new`, any PKCE challenge appended to the URL is silently dropped by GitHub. The resulting authorization `code` is therefore never bound to the PKCE verifier, rendering the entire PKCE layer ineffective and creating false security confidence.
*   **Decision**:
    1. Remove `code_verifier` from `PendingOAuthState` (it was only used in the route to construct a challenge that GitHub ignored).
    2. Remove PKCE challenge generation from `GET /github/install`.
    3. Retain `code_verifier_enc` in the `github_connection_states` DB column and the `GitHubOAuthStateContext` dataclass for schema stability (avoids a migration). The stored value is harmless noise.
    4. Rely on `client_secret` (confidential client) + `state` parameter (CSRF guard + developer-binding) as the security mechanism for the token exchange.
*   **Alternatives Considered**:
    - **2-step flow** (Option B): Redirect to `/login/oauth/authorize` with PKCE first, then redirect to `/installations/new` afterward. This supports PKCE properly but forces two separate GitHub consent screens, significantly degrading UX. Rejected for MVP scope.
*   **Why This Decision**: DevTwin is a confidential client (server-side `client_secret` is never exposed). Per OAuth 2.1, PKCE is mandatory for public clients but defense-in-depth for confidential ones. The `state` parameter provides the same CSRF guarantee and developer-identity binding that PKCE would have added. Removing it eliminates dead code and eliminates false security confidence.
