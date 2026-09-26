---
Status: Active
Version: 1.2
Last Updated: 2026-09-26
Source of Truth: MEMORY.md
---

# Project Memory

*Source of Truth Context: This document defines durable, long-term project knowledge to quickly onboard future human and AI agents. It is NOT a changelog.*

## Checkpoint Status

CURRENT PROJECT:
DevTwin — AI-Powered Developer Capability Intelligence Platform

CURRENT PHASE:
GitHub App Integration

⚠ DO NOT REIMPLEMENT STEP 4, STEP 5A, STEP 5B, OR STEP 5C.
These are complete and must be treated as frozen.

COMPLETED:
- Steps 1–4A
- GET /github/install
- OAuth state/PKCE persistence
- state claiming
- S256 PKCE challenge
- GitHub service layer
- security hardening
- Step 5A: OAuth callback foundation
- Step 5B: GitHub identity verification (get_authenticated_user)
- Step 5B: GitHub installation verification (list_user_installations)
- Step 5C: GitHub account linking

CURRENT CHECKPOINT:
Step 5C complete and committed

NEXT STEP:
Step 5D feature-selection checkpoint / architecture decision

MIGRATIONS CHANGED: NO
SCHEMA CHANGED: NO
INSTALLATION_ID PERSISTED: NO (intentionally deferred to a later step)
/github/status IMPLEMENTED: NO
/github/disconnect IMPLEMENTED: NO
INSTALLATION ACCESS TOKENS IMPLEMENTED: NO
REPOSITORY REGISTRATION IMPLEMENTED: NO

STEP 5C ACCOUNT LINKING — WHAT WAS IMPLEMENTED:
- After OAuth token exchange and GitHub identity/installation verification:
  - Query github_accounts WHERE github_id = github_user.github_id
  - Case 1 (no row): INSERT new GitHubAccount with developer_id, github_id,
    username; installation_id=NULL, disconnected_at=NULL
  - Case 2 (same developer): UPDATE username, clear disconnected_at (reconnect)
  - Case 3 (different developer): HTTP 409 Conflict (sanitized, no IDs exposed)
  - IntegrityError race condition: rollback → re-query → resolve case
  - OAuth token deleted immediately before DB operations
  - Response: {status, detail, github_username} only — no token, no IDs
- Developer identity source: state_context.developer_id (from DB claim, NOT browser)
- GitHub identity source: github_user.github_id / .username (from GitHub API)

NOT YET IMPLEMENTED:
- installation_id persistence (intentionally deferred — schema has single nullable column, multiple installs possible)
- /github/status
- /github/disconnect
- installation access tokens
- repository registration
- repository analysis

NEXT STEP:
Step 5D — installation_id persistence OR /github/status endpoint
(Decide based on product priority — installation_id persistence is a prerequisite
for any repository-level operations)

## Project Identity
**DevTwin** is an AI-powered Developer Capability Intelligence Platform that measures actual engineering capability based on verifiable repository artifacts, rejecting the flawed paradigm of static resumes and arbitrary multiple-choice tests.

## Core Concepts & Domain Vocabulary
To work on this project, you must understand these critical distinctions:
*   **Skill ≠ Capability**: "Backend Development" is a Skill. A developer's "Capability in Backend Development" is a scored metric indicating how well they apply that skill in practice.
*   **Technology ≠ Concept**: "FastAPI" is a concrete Technology. "REST API" is the abstract Concept it involves.
*   **Observation ≠ Evidence**: An Observation is an immutable, raw fact extracted from code (e.g., "Dependency React v18 found"). Evidence is the contextualized interpretation of that fact (e.g., "Developer demonstrates Usage of React").
*   **Risk ≠ Competence**: A CodeRisk finding (e.g., missing tests) highlights an engineering behavior pattern. It is *evidence*, not proof of incompetence. It weighs into the Capability Model, but does not unilaterally wipe out capability.
*   **Analysis Job ≠ Analysis Run**: A Job is the user/system request to process a repo. A Run is a single concrete execution attempt. A Job may contain multiple Runs (retries, failures, successes).

## Architectural Principles
1.  **Provenance is Paramount**: The system must be able to visually trace a dashboard capability score back to the exact JSON observation or Git commit that generated it.
2.  **Asynchronous by Default**: Repository analysis is heavy. It never happens in a synchronous web request.
3.  **Relational Graph**: We implement our SkillGraph using standard PostgreSQL junction tables, avoiding the operational overhead of a dedicated graph database for the Minor MVP.

## Current Technology Stack
*   Next.js / TypeScript / Tailwind
*   FastAPI / Python
*   PostgreSQL / Supabase
*   Redis

## Minor vs. Major Scope
*   **Minor Scope (Current)**: GitHub ingestion (OAuth + Selection), Repository mining, SkillGraph mapping, CodeRisk engine, Evidence generation, Capability modeling, Dashboard explainability.
*   **Major Scope (Future)**: StudyTwin, personalized learning interventions, knowledge tracing, adaptive outcomes.

## Important Historical Context
Early designs considered using LLMs to ingest entire codebases and output a "Developer Score." This was formally rejected (see `DECISIONS.md`) because it creates a black-box system that cannot provide provenance or trustworthiness. The project pivoted to the **Evidence-Backed Paradigm**, where deterministic parsers find facts, math aggregates them, and LLMs are only used for text explanation.
