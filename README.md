# DevTwin

**DevTwin — AI-Powered Developer Capability Intelligence Platform**

Development Stage: Implementation-Ready System Specification

## Problem
Current methods for evaluating developer capability rely on static resumes, generic GitHub dashboards, or simple code assessments. These fail to capture the true, evolving nature of a developer's technical knowledge, practical application, and engineering behavior over time. They lack evidence-backed explanations and do not account for engineering risks or contextual application of skills.

## Core Idea
DevTwin connects what a developer knows, how they actually build, what engineering signals/risks appear, what capabilities those signals support, and how the capability state evolves over time. 

The technical intelligence loop is:
KNOW → BUILD → DETECT → LEARN → IMPROVE → RE-EVALUATE

The system is evidence-backed and explainable. No capability score without evidence. No inference without uncertainty. No skill-gap conclusion without distinguishing observed evidence from inferred causes.

## Architecture Overview
DevTwin consists of three core intelligence layers:
1. **SkillGraph**: Represents relationships between developers, skills, concepts, technologies, projects, evidence, and capabilities.
2. **CodeRisk**: An engineering-risk intelligence layer that analyzes repository signals to generate explainable risk signals which feed into the capability model.
3. **StudyTwin**: The future adaptive learning/growth layer (Major roadmap).

## Minor Scope (Developer Capability Intelligence Foundation)
The Minor Project implements the foundation to answer: "Can heterogeneous evidence extracted from GitHub activity and software repositories be transformed into an explainable, evidence-backed representation of a developer's technical capabilities and engineering characteristics?"

Included:
- GitHub ingestion
- Repository mining
- SkillGraph
- Evidence engine
- CodeRisk
- Capability model
- Capability history
- Basic skill-gap identification
- Explainable dashboard
- Evidence Explorer

## Major Roadmap (Future)
The Major roadmap will extend the platform to include the StudyTwin layer, featuring:
- Knowledge tracing
- Temporal capability prediction
- Personalized learning
- Intervention tracking
- Outcome measurement
- What-if simulation
- Adaptive recommendations
- Richer graph/ML models

## Technology Stack
- **Frontend**: Next.js, TypeScript, Tailwind CSS
- **Backend**: FastAPI, Python
- **Database**: PostgreSQL / Supabase
- **AI/ML**: Python, scikit-learn, embeddings, LLM APIs
- **Code Analysis**: Custom analyzers, CodeQL / static-analysis tools

## Repository Structure
- `docs/` - Canonical technical specifications (Domain Model, DB Schema, API Contracts, Pipeline)
- `backend/` - (Pending) FastAPI backend services
- `frontend/` - (Pending) Next.js frontend application
- `workers/` - (Pending) Background Python analysis workers
- `database/` - (Pending) SQL migration files
- `scripts/` - (Pending) Utility scripts
- `tests/` - (Pending) Test suites

## Development Philosophy
- The repository documentation is the source of truth.
- AI is an intelligence layer, NOT the entire product.
- Evidence-backed: Every capability estimate must be supported by evidence.
- Interpretable: The system must remain interpretable and manageable.
- **Risk ≠ Competence**: CodeRisk findings are evidence signals, not blame verdicts.

## Current Project Status
**Stage**: Architecture & Specification Freeze
**Implementation**: Not Started
**Status**: Research + System Design + Implementation Preparation

The full architectural specification is frozen. See `docs/IMPLEMENTATION_READINESS.md` for the complete status of each component.
