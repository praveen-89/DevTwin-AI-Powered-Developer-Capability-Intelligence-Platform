---
Status: Active
Version: 1.0
Last Updated: 2026-09-08
Source of Truth: MEMORY.md
---

# Project Memory

This document stores stable, long-term project knowledge and context. It is NOT a changelog. It is designed to quickly onboard future human and AI agents.

## Project Identity
**DevTwin** is an AI-powered Developer Capability Intelligence Platform that measures actual engineering capability based on verifiable repository artifacts, rejecting the flawed paradigm of static resumes and arbitrary multiple-choice tests.

## Core Concepts & Domain Vocabulary
To work on this project, you must understand these critical distinctions:
*   **Skill ≠ Capability**: "Backend Development" is a Skill. A developer's "Capability in Backend Development" is a scored metric indicating how well they apply that skill in practice.
*   **Technology ≠ Concept**: "FastAPI" is a concrete Technology. "REST API" is the abstract Concept it involves.
*   **Observation ≠ Evidence**: An Observation is an immutable, raw fact extracted from code (e.g., "Dependency React v18 found"). Evidence is the contextualized interpretation of that fact (e.g., "Developer demonstrates Usage of React").
*   **Risk ≠ Competence**: A CodeRisk finding (e.g., missing tests) highlights an engineering behavior pattern; it does not automatically mean the developer doesn't "know" how to write tests, but it negatively impacts their demonstrated Capability in "Testing".

## Architectural Principles
1.  **Provenance is Paramount**: The system must be able to visually trace a dashboard capability score back to the exact JSON observation or Git commit that generated it.
2.  **Asynchronous by Default**: Repository analysis is heavy. It never happens in a synchronous web request.
3.  **Relational Graph**: We implement our SkillGraph using standard PostgreSQL junction tables, avoiding the operational overhead of a dedicated graph database for the Minor MVP.

## Current Technology Stack
*   Next.js / TypeScript / Tailwind
*   FastAPI / Python
*   PostgreSQL / Supabase
*   Redis

## Current Minor Scope
The Minor phase builds the **Foundation**: fetching repositories, extracting data, running CodeRisk, mapping to the SkillGraph, generating Evidence, and calculating a mathematically normalized Capability score.

## Major Direction
The Major phase builds the **StudyTwin**: taking the Skill Gaps identified by the Minor phase and deploying personalized learning interventions, then re-measuring capability outcomes over time.

## Important Historical Context
Early designs considered using LLMs to ingest entire codebases and output a "Developer Score." This was formally rejected (see `DECISIONS.md`) because it creates a black-box system that cannot provide provenance or trustworthiness. The project pivoted to the **Evidence-Backed Paradigm**, where deterministic parsers find facts, math aggregates them, and LLMs are only used for text explanation.
