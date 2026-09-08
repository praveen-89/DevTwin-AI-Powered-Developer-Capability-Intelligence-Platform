---
Status: Active
Version: 1.1
Last Updated: 2026-09-08
Source of Truth: MEMORY.md
---

# Project Memory

*Source of Truth Context: This document defines durable, long-term project knowledge to quickly onboard future human and AI agents. It is NOT a changelog.*

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
