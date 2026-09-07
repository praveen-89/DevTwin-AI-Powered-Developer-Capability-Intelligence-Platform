# 13. Analysis Pipeline

## Overview
Repository analysis in DevTwin MUST NOT happen inside a synchronous HTTP request. The process is resource-intensive and requires a job-based architecture.

## Pipeline Architecture
`POST /analysis -> Create Analysis Job -> Queue -> Worker -> Process -> Database -> Frontend`

## Analysis States
A job progresses through the following states:
1.  **QUEUED**: Job is waiting for an available worker.
2.  **FETCHING**: Worker is downloading repository metadata and cloning the source code.
3.  **MINING**: Extracting raw observations (AST parsing, dependency tree resolution).
4.  **SKILL_GRAPH**: Mapping mined technologies and concepts to the developer's graph.
5.  **CODE_RISK**: Running static analysis, security checks, and code quality heuristics.
6.  **CAPABILITY**: Aggregating new evidence and recalculating capability scores and confidence.
7.  **COMPLETED**: Analysis finished successfully.
8.  **FAILED**: Analysis encountered an unrecoverable error.

## Worker Processing
Workers (e.g., Python processes using Celery or RQ) pull jobs from a Redis queue. They execute the discrete intelligence layers (Miner, CodeRisk Engine, SkillGraph Builder, Capability Scorer) sequentially, persisting the generated `Observation`, `RiskSignal`, and `EvidenceItem` objects to the PostgreSQL database.
