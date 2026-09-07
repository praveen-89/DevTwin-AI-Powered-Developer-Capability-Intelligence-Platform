# 13. Analysis Pipeline

## Overview
Repository analysis in DevTwin MUST NOT happen inside a synchronous HTTP request. The process is resource-intensive and requires a job-based architecture.

## Pipeline Architecture
`POST /analysis -> Create Analysis Job -> Queue -> Worker -> Process -> Database -> Frontend`

## Analysis States
An `analysis_runs` record progresses through the following strict states (mapped as a PostgreSQL ENUM):
1.  **QUEUED**: Job is in Redis waiting for a worker.
2.  **FETCHING**: Worker is downloading repository metadata and cloning code.
3.  **MINING**: Extracting raw `observations` (AST parsing, dependencies).
4.  **SKILL_GRAPH**: Mapping observations to the SkillGraph taxonomy.
5.  **CODE_RISK**: Running static analysis to generate `risk_findings`.
6.  **CAPABILITY**: Aggregating `evidence` and updating `developer_capabilities` and `capability_history`.
7.  **COMPLETED**: Analysis finished successfully.
8.  **FAILED**: Analysis encountered an error, captured in `error_info`.

## Worker Processing
Workers (e.g., Python processes using Celery or RQ) pull jobs from a Redis queue. They execute the discrete intelligence layers (Miner, CodeRisk Engine, SkillGraph Builder, Capability Scorer) sequentially, persisting the generated `Observation`, `RiskSignal`, and `EvidenceItem` objects to the PostgreSQL database.
