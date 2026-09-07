# 17. Development Roadmap

## Phase 1: Foundation & Specification (Current)
- Define system architecture, data models, and intelligence layers.
- Initialize repository structure and documentation.

## Phase 2: Data Ingestion & Mining
- Implement GitHub API integration for fetching repositories.
- Build the Repository Miner (AST parsing, dependency extraction).
- Implement background worker queue architecture.

## Phase 3: Intelligence Layers
- Implement the basic CodeRisk engine (heuristics for security, testing, maintainability).
- Implement the SkillGraph builder (mapping mined data to technologies/concepts).
- Implement the Evidence Engine (translating observations to weighted evidence).

## Phase 4: Capability Modeling
- Implement the Capability Scorer (aggregating evidence into scores and confidence).
- Implement historical state tracking.

## Phase 5: API & Frontend Integration
- Develop the FastAPI endpoints for querying the intelligence layers.
- Build the Next.js Developer Dashboard.
- Build the Evidence Explorer UI for explainability.

## Phase 6: Testing & Evaluation
- Run evaluation plan against sample repositories.
- Refine evidence weighting and CodeRisk heuristics.
- Finalize Minor MVP documentation.
