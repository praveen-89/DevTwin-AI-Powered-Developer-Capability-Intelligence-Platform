# 12. API Specification

## Overview
The backend provides a RESTful API built with FastAPI. It handles synchronous dashboard requests and asynchronous analysis job management.

## API Resource Mapping (Preparation)
The following routes map directly to the underlying PostgreSQL domain entities specified in the schema:

### Developer & Capability Resources
- `GET /developers` - List developers
- `GET /developers/{id}` - Retrieve developer details
- `GET /developers/{id}/capabilities` - Fetch `developer_capabilities`
- `GET /developers/{id}/capabilities/history` - Fetch `capability_history`
- `GET /developers/{id}/skills/gaps` - Fetch `skill_gaps`
- `GET /developers/{id}/evidence` - Fetch contextual `evidence` for the developer

### Repository & Risk Resources
- `GET /repositories` - List registered repositories
- `GET /repositories/{id}` - Retrieve repository metadata
- `GET /repositories/{id}/risks` - Fetch `risk_findings` for CodeRisk layer

### Analysis Pipeline
- `POST /analysis` - Queue a new `analysis_runs` record
- `GET /analysis/{id}` - Poll status of an `analysis_runs` record

### Taxonomy (SkillGraph)
- `GET /graph/skills`
- `GET /graph/technologies`
- `GET /graph/concepts`
