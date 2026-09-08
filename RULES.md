---
Status: Active
Version: 1.0
Last Updated: 2026-09-08
Source of Truth: RULES.md
---

# DevTwin Engineering Rules

These rules are the engineering constitution of the project. They must be followed by all human engineers and AI coding agents.

## Architecture
*   Respect module boundaries: Do not bleed background worker logic into the FastAPI request lifecycle.
*   No undocumented architectural changes. Any change must trigger a `DECISIONS.md` update.
*   No unnecessary technologies. Do not introduce Kafka, Neo4j, or Kubernetes without a formal ADR proving absolute necessity for the Minor MVP.

## Backend (FastAPI)
*   **API Validation**: Use Pydantic models for all inputs and outputs.
*   **Type Safety**: Strict Python type hints are mandatory.
*   **Service Boundaries**: API routes must not contain complex business logic; delegate to service classes.

## Frontend (Next.js)
*   **Reusable Components**: Rely on a standardized UI component library.
*   **State Management**: Keep client-side state predictable and minimal.
*   **Loading/Error States**: Every async data fetch must have explicit loading skeletons, error boundaries, and empty state representations.

## Database (PostgreSQL)
*   **Identifiers**: Use UUIDv4 for all internal primary keys. Keep external IDs (GitHub IDs) strictly separated in their own columns.
*   **Normalization**: Keep the schema normalized. Do not use JSONB blobs to avoid defining proper tables, unless storing raw, unpredictable 3rd-party source payloads.
*   **Constraints**: Ensure strict foreign keys, CHECK constraints, and appropriate `ON DELETE CASCADE`/`SET NULL` behaviors.
*   **RLS**: Row Level Security is mandatory to protect developer data privacy.
*   **No Destructive Schema Changes**: Never drop columns or tables without an explicit architectural decision and data migration plan.

## Security
*   Never commit secrets to the repository.
*   Never expose GitHub OAuth tokens in plaintext or logs.
*   Enforce least privilege for database roles and API keys.

## AI/ML
*   No arbitrary AI usage. Use standard software engineering for standard problems.
*   Deterministic logic MUST precede LLM usage.
*   LLMs are for semantic mapping and text generation, NOT for calculating capability scores.
*   No unsupported capability claims.

## Evidence (The Golden Rule)
*   **No capability score without evidence.**
*   **No inference without uncertainty.**
*   **No skill-gap conclusion without evidence.**

## Code Quality
*   Mandatory linting, formatting, and static type checking.
*   Comprehensive testing is required for all new logic.

## Git Workflow
*   Follow clean branch conventions (e.g., `feature/`, `fix/`).
*   Commit messages must be descriptive.
*   Pull Requests must pass all CI tests before merging.
*   **Documentation Expectation**: PRs must include updates to living documentation if behavior, architecture, or schemas change.
