# Implementation Readiness

## Overview
This document assesses the current state of the DevTwin project before moving into the actual database/backend coding phase.

## What is Frozen
-   **Product Concept**: Developer Capability Intelligence Platform focused on evidence-backed inference.
-   **Minor Scope**: Excludes StudyTwin, personalized learning, and autonomous agents.
-   **Major Conceptual Architecture**: Separation of SkillGraph, CodeRisk, and Evidence engines.
-   **Core Domain Model**: The purpose, ownership, and lifecycle of the 20 core entities.
-   **Database Design**: PostgreSQL/Supabase schema, UUID strategy, ENUMs, and Exclusive Arc target resolution.
-   **Data Relationships**: Exact foreign key mapping and referential integrity constraints.
-   **Evidence Model**: The strict separation of Observation (fact) vs. Evidence (contextualization).
-   **Capability Model**: Temporal history tracking and evidence aggregation.

## What is Pending
-   **Actual Migrations**: Writing the `.sql` or ORM migration files.
-   **GitHub OAuth**: Implementing the secure authentication flow.
-   **Ingestion Implementation**: Building the Git clone/GitHub API fetchers.
-   **Repository Mining Implementation**: Building the AST and dependency parsers.
-   **SkillGraph Engine**: Building the mapping logic.
-   **CodeRisk Engine**: Implementing the static analysis heuristics.
-   **Capability Calculation Implementation**: Writing the math for the scoring model.
-   **API Implementation**: Building the FastAPI endpoints.
-   **Frontend**: Building the Next.js dashboard.

## Next Steps
Do not proceed to implementation until this exact data specification is reviewed and approved. The immediate next engineering task is writing the migration sequence.
