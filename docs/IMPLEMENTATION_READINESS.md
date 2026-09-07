# Implementation Readiness

## Overview
This document assesses the current state of the DevTwin specification phase before moving into active implementation.

## What is Frozen
-   **The Core Concept**: The distinction between Skill and Capability, and the requirement for evidence-backed inferences.
-   **Domain Model & DB Schema**: The exact tables, columns, constraints, exclusive arcs for polymorphism, and ENUM structures defined in `DOMAIN_MODEL.md`.
-   **Tripartite Architecture**: The logical separation into SkillGraph, CodeRisk, and the future StudyTwin.
-   **Technology Stack**: Next.js (Frontend), FastAPI (Backend), PostgreSQL (Database), Python (Workers).
-   **Pipeline Design**: Asynchronous, job-based repository processing (`analysis_runs`).

## What Remains Undecided
-   **Specific Static Analysis Tools**: The exact underlying tools used by CodeRisk (e.g., custom AST vs. wrapping Semgrep/CodeQL).
-   **Exact Normalization Constants**: The capability scoring math calibration.

## What Must Be Specified Next
-   Backend FastAPI boilerplate and ORM (e.g., SQLAlchemy/SQLModel) setup.

## First Implementation Milestone
**Milestone 1: Database Initialization & Pipeline Skeleton**
1.  Setup PostgreSQL/Supabase database.
2.  Write and execute the SQL migration scripts based on `DOMAIN_MODEL.md` (Migrations 001-007).
3.  Setup FastAPI backend scaffolding.
4.  Implement a mock background worker that receives a repository URL, simulates processing, and updates the `analysis_runs` database state to COMPLETED.

## Known Technical Risks
-   **GitHub API Rate Limits**: Mining extensive commit history may hit rate limits; caching and selective fetching will be required.
-   **AST Parsing Performance**: Parsing large repositories could bottleneck the workers; optimization or shallow parsing may be necessary for the MVP.
