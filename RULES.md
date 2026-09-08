---
Status: Active
Version: 1.1
Last Updated: 2026-09-08
Source of Truth: RULES.md
---

# DevTwin Engineering Rules

These rules are the engineering constitution of the project. They must be followed by all human engineers and AI coding agents.

## Architecture
*   Respect module boundaries: Do not bleed background worker logic into the FastAPI request lifecycle.
*   No undocumented architectural changes. Any change must trigger a `DECISIONS.md` update.
*   No unnecessary technologies. Do not introduce Kafka, Neo4j, or Kubernetes for the Minor MVP.

## Backend (FastAPI)
*   **API Validation**: Use Pydantic models for all inputs and outputs.
*   **Type Safety**: Strict Python type hints are mandatory.
*   **Service Boundaries**: API routes must not contain complex business logic; delegate to service classes.

## Frontend (Next.js)
*   **Reusable Components**: Rely on a standardized UI component library.
*   **State Management**: Keep client-side state predictable and minimal.
*   **Loading/Error States**: Every async data fetch must have explicit loading skeletons, error boundaries, and empty state representations.

## Database (PostgreSQL)
*   **Identifiers**: Use UUIDv4 for all internal primary keys. Map Supabase Auth explicitly via `developers.auth_user_id`. Keep external IDs (GitHub IDs) strictly separated in their own columns.
*   **Normalization**: Keep the schema normalized. Do not use JSONB blobs unless storing raw, unpredictable 3rd-party source payloads for debugging/provenance.
*   **Constraints**: Ensure strict foreign keys, CHECK constraints (especially the Exclusive Arc for Capability Targets), and appropriate cascading behaviors.
*   **RLS**: Row Level Security is mandatory to protect developer data privacy.
*   **No Destructive Schema Changes**: Never drop columns or tables without an explicit architectural decision.

## Security
*   **Never commit secrets to the repository.**
*   **Never expose GitHub OAuth tokens in plaintext or logs.** `access_token_enc` must be encrypted material or an external reference.
*   Enforce least privilege for database roles and API keys.

## AI/ML
*   No arbitrary AI usage. Use standard software engineering for standard problems.
*   Deterministic logic MUST precede LLM usage.
*   LLMs are for semantic mapping and text generation, NOT for calculating capability scores.
*   No unsupported capability claims.

## Evidence & Attribution (The Golden Rules)
*   **No capability score without evidence.**
*   **No inference without uncertainty.**
*   **No skill-gap conclusion without evidence.**
*   **Risk ≠ Competence**: CodeRisk findings provide evidence about engineering behavior. They do not automatically imply lack of developer competence.
*   **Attribution requires Evidence**: Do not falsely blame a developer for a repository-level risk unless Git history (commit author) directly links them to the observation.

## Git Workflow
*   Follow clean branch conventions.
*   Commit messages must be descriptive.
*   PRs must include updates to living documentation if behavior, architecture, or schemas change.
