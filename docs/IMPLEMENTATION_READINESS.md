# Implementation Readiness

## Overview
This document assesses the current state of the DevTwin specification phase before moving into active implementation.

## What is Frozen
-   **The Core Concept**: The distinction between Skill and Capability, and the requirement for evidence-backed inferences.
-   **Tripartite Architecture**: The logical separation into SkillGraph, CodeRisk, and the future StudyTwin.
-   **Technology Stack**: Next.js (Frontend), FastAPI (Backend), PostgreSQL (Database), Python (Workers).
-   **Pipeline Design**: Asynchronous, job-based repository processing.
-   **Minor vs. Major Scope**: Strict boundaries preventing scope creep into personalized learning or autonomous agents for the MVP.

## What Remains Undecided
-   **Specific Static Analysis Tools**: The exact underlying tools used by CodeRisk (e.g., custom AST vs. wrapping Semgrep/CodeQL) will be decided during Phase 3 based on integration ease.
-   **Exact Normalization Constants**: The $Z$ factor in the capability scoring model will require empirical calibration once test data is available.

## What Must Be Specified Next
-   Detailed database migration scripts based on `11_DATABASE_SCHEMA.md`.
-   Specific heuristic rules for the initial CodeRisk categories.

## First Implementation Milestone
**Milestone 1: End-to-End Pipeline Skeleton**
1.  Setup FastAPI backend and Next.js frontend scaffolding.
2.  Setup PostgreSQL database and Redis queue.
3.  Implement a mock background worker that receives a repository URL, simulates processing, and updates the database state to COMPLETED.
4.  Frontend displays the updating status.

## Known Technical Risks
-   **GitHub API Rate Limits**: Mining extensive commit history may hit rate limits; caching and selective fetching will be required.
-   **AST Parsing Performance**: Parsing large repositories (e.g., thousands of files) could bottleneck the workers; optimization or shallow parsing may be necessary for the MVP.
