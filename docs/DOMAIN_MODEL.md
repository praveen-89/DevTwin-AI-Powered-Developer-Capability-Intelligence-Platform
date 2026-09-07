# Domain Model & Database Specification

## Overview
This document specifies the implementation-ready domain model and PostgreSQL database schema for the DevTwin platform. It details all tables, columns, constraints, and relationships required to support the Developer Twin capability intelligence loop.

## Identifiers Strategy
**Primary Keys**: UUIDv4 is used for all internal primary keys. 
**Reasoning**: UUIDs allow for decentralized ID generation, prevent enumeration attacks, and simplify data merging across potential future shards or microservices. 
**External IDs**: External identifiers (like GitHub User ID or Repository ID) are stored in dedicated columns (e.g., `github_id BIGINT`) but are NEVER used as internal primary keys. This decouples DevTwin from a single provider, allowing future integrations (e.g., GitLab, Bitbucket) without breaking the core schema.

## Capability Target Design (Polymorphic Avoidance)
To associate a `DeveloperCapability` or `SkillGap` with a target entity (Skill, Technology, or Concept), we avoid anti-patterns like `(target_id, target_type)`. 
**Decision**: We use the **Exclusive Arc** pattern. The table contains separate nullable foreign keys (`skill_id`, `technology_id`, `concept_id`) with a `CHECK` constraint ensuring exactly *one* is non-null. This guarantees database-level referential integrity and cascading deletes.
For `Evidence`, the design uses explicit junction tables (`evidence_skills`, etc.) to allow one evidence item to potentially support multiple targets.

## Core Entities

### 1. Identity & Projects

**`developers`**
Purpose: The core identity representing a human developer in the system.
| Column | Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| id | uuid | NO | PK | Internal identifier |
| created_at | timestamptz | NO | DEFAULT now() | Record creation time |
| updated_at | timestamptz | NO | DEFAULT now() | Last update time |

**`github_accounts`**
Purpose: Stores GitHub-specific integration details for a developer. Secrets are handled externally or encrypted.
| Column | Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| id | uuid | NO | PK | Internal identifier |
| developer_id | uuid | NO | FK(developers.id) | Owning developer |
| github_id | bigint | NO | UNIQUE | External GitHub user ID |
| username | text | NO | | GitHub login username |
| avatar_url | text | YES | | URL to GitHub avatar |
| access_token_enc | text | YES | | Encrypted OAuth token (never plaintext) |
| created_at | timestamptz | NO | DEFAULT now() | Record creation time |

**`projects`**
Purpose: Logical grouping of repositories or work associated with a developer.
| Column | Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| id | uuid | NO | PK | Internal identifier |
| developer_id | uuid | NO | FK(developers.id) | Owning developer |
| name | text | NO | | Project name |
| description | text | YES | | Project description |
| created_at | timestamptz | NO | DEFAULT now() | Record creation time |

### 2. Repository Domain

**`repositories`**
Purpose: Represents a tracked codebase.
| Column | Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| id | uuid | NO | PK | Internal identifier |
| project_id | uuid | YES | FK(projects.id) | Associated project |
| github_repo_id | bigint | YES | UNIQUE | External GitHub repository ID |
| name | text | NO | | Repository name |
| full_name | text | NO | | Owner/Name format |
| url | text | NO | | Clone or web URL |
| visibility | text | NO | | 'public' or 'private' |
| default_branch | text | NO | DEFAULT 'main' | Default branch name |
| owner_login | text | NO | | GitHub owner name |
| created_at | timestamptz | NO | DEFAULT now() | Record creation time |

**`repository_languages`**
Purpose: Extracted language usage statistics.
| Column | Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| id | uuid | NO | PK | Internal identifier |
| repository_id | uuid | NO | FK(repositories.id) | Associated repo |
| language | text | NO | | Language name (e.g., Python) |
| bytes | bigint | NO | | Bytes of code |
| UNIQUE(repository_id, language) | | | | Prevents duplicate language entries per repo |

**`repository_dependencies`**
Purpose: Tracked dependencies for CodeRisk and SkillGraph.
| Column | Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| id | uuid | NO | PK | Internal identifier |
| repository_id | uuid | NO | FK(repositories.id) | Associated repo |
| ecosystem | text | NO | | e.g., npm, pip |
| package_name | text | NO | | Name of the package |
| version_constraint| text | YES | | Version used |
| UNIQUE(repository_id, ecosystem, package_name) | | | | Prevents duplicates |

**`commits`**
Purpose: Stores relevant commit metadata for developer attribution.
| Column | Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| id | uuid | NO | PK | Internal identifier |
| repository_id | uuid | NO | FK(repositories.id) | Associated repo |
| sha | text | NO | | Git commit SHA |
| author_email | text | YES | | Extracted author email |
| author_name | text | YES | | Extracted author name |
| message | text | YES | | Commit message |
| committed_at | timestamptz | NO | | Git commit timestamp |
| UNIQUE(repository_id, sha) | | | | Prevents duplicate commits |

**`pull_requests`**
Purpose: Stores PR metadata for collaboration evidence.
| Column | Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| id | uuid | NO | PK | Internal identifier |
| repository_id | uuid | NO | FK(repositories.id) | Associated repo |
| pr_number | integer| NO | | GitHub PR number |
| title | text | NO | | PR title |
| state | text | NO | | 'open', 'closed', 'merged' |
| created_at | timestamptz | NO | | PR creation time |
| merged_at | timestamptz | YES | | PR merge time |
| UNIQUE(repository_id, pr_number) | | | | Prevents duplicate PRs |

### 3. Analysis & Observation Domain

**`analysis_runs`**
Purpose: Tracks a distinct execution of the DevTwin analysis pipeline.
| Column | Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| id | uuid | NO | PK | Internal identifier |
| repository_id | uuid | NO | FK(repositories.id) | Analyzed repo |
| status | analysis_status| NO | | ENUM: QUEUED, FETCHING, MINING, SKILL_GRAPH, CODE_RISK, CAPABILITY, COMPLETED, FAILED |
| started_at | timestamptz | YES | | When processing began |
| completed_at | timestamptz | YES | | When processing ended |
| analyzer_version| text | NO | | Version of the extraction engine |
| schema_version | text | NO | | Data schema version |
| error_info | jsonb | YES | | Structured error log |

**`observations`**
Purpose: Directly detected facts from an analysis run.
| Column | Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| id | uuid | NO | PK | Internal identifier |
| analysis_run_id | uuid | NO | FK(analysis_runs.id) | Generating run |
| type | text | NO | | What was observed |
| source_tool | text | NO | | Tool used (e.g., 'AST_PARSER') |
| source_reference| jsonb | YES | | Line number, commit, or file pointer |
| confidence | numeric| YES | CHECK(confidence BETWEEN 0 AND 1) | Raw detection confidence |
| observed_at | timestamptz | NO | DEFAULT now() | Time of observation |

### 4. SkillGraph Domain

**`skills`** (Broad competencies)
| Column | Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| id | uuid | NO | PK | Internal identifier |
| name | text | NO | UNIQUE | e.g., 'Backend Development' |
| domain | text | YES | | e.g., 'Software Engineering' |

**`technologies`** (Concrete tools/languages)
| Column | Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| id | uuid | NO | PK | Internal identifier |
| name | text | NO | UNIQUE | e.g., 'FastAPI' |
| type | text | NO | | e.g., 'FRAMEWORK', 'LANGUAGE' |

**`concepts`** (Theoretical knowledge)
| Column | Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| id | uuid | NO | PK | Internal identifier |
| name | text | NO | UNIQUE | e.g., 'REST API' |

**SkillGraph Relationships (Junctions)**
- `skill_technologies` (skill_id, technology_id) - PK(skill_id, technology_id)
- `skill_concepts` (skill_id, concept_id) - PK(skill_id, concept_id)
- `technology_concepts` (technology_id, concept_id) - PK(technology_id, concept_id)
- `skill_relationships` (skill_id_1, skill_id_2, relation_type) - PK(skill_id_1, skill_id_2)

### 5. Evidence Domain

**`evidence`**
Purpose: Contextualized support for capabilities derived from observations.
| Column | Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| id | uuid | NO | PK | Internal identifier |
| observation_id | uuid | YES | FK(observations.id) | Source observation (nullable if manual) |
| type | evidence_type | NO | | ENUM: MENTION, USAGE, APPLIED_ENGINEERING, DEMONSTRATED_OUTCOME |
| strength | numeric| NO | CHECK(strength BETWEEN 0 AND 1) | Base hierarchy weight |
| directness | numeric| NO | CHECK(directness BETWEEN 0 AND 1) | Relation to target |
| reliability | numeric| NO | CHECK(reliability BETWEEN 0 AND 1) | Source trustworthiness |
| recency | timestamptz | NO | | Time basis for decay |
| polarity | numeric| NO | CHECK(polarity BETWEEN -1 AND 1) | Positive or negative evidence |

**Evidence Targets (Junctions)**
- `evidence_skills` (evidence_id, skill_id) - PK(evidence_id, skill_id)
- `evidence_technologies` (evidence_id, technology_id) - PK(evidence_id, technology_id)
- `evidence_concepts` (evidence_id, concept_id) - PK(evidence_id, concept_id)

### 6. Capability & CodeRisk Domain

**`developer_capabilities`**
Purpose: Current state of a developer's capability.
| Column | Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| id | uuid | NO | PK | Internal identifier |
| developer_id | uuid | NO | FK(developers.id) | Target developer |
| skill_id | uuid | YES | FK(skills.id) | Target skill |
| technology_id | uuid | YES | FK(technologies.id)| Target tech |
| concept_id | uuid | YES | FK(concepts.id) | Target concept |
| score | numeric| NO | CHECK(score BETWEEN 0 AND 1) | Capability score |
| confidence | numeric| NO | CHECK(confidence BETWEEN 0 AND 1) | Estimate confidence |
| scoring_version | text | NO | | Model version used |
| updated_at | timestamptz | NO | DEFAULT now() | Last state update |
| CHECK | | | | `num_nonnulls(skill_id, technology_id, concept_id) = 1` |
| UNIQUE | | | | `(developer_id, skill_id, technology_id, concept_id)` |

**`capability_history`**
Purpose: Immutable temporal log of capability changes.
| Column | Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| id | uuid | NO | PK | Internal identifier |
| capability_id | uuid | NO | FK(developer_capabilities.id) | The capability being tracked |
| score | numeric| NO | | Historical score |
| confidence | numeric| NO | | Historical confidence |
| model_version | text | NO | | Scoring model version |
| analysis_run_id | uuid | YES | FK(analysis_runs.id) | Run that caused the update |
| recorded_at | timestamptz | NO | DEFAULT now() | Timestamp of change |

**`skill_gaps`**
Purpose: Tracks calculated deltas between required and actual capability.
| Column | Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| id | uuid | NO | PK | Internal identifier |
| developer_id | uuid | NO | FK(developers.id) | The developer |
| target_skill_id | uuid | YES | FK(skills.id) | |
| target_technology_id | uuid | YES | FK(technologies.id)| |
| target_concept_id | uuid | YES | FK(concepts.id) | |
| target_score | numeric| NO | | Required capability level |
| current_score | numeric| NO | | Developer's current capability |
| confidence | numeric| NO | | Confidence in the current score |
| gap_value | numeric| NO | | Calculated gap |
| model_version | text | NO | | Calculation version |
| calculated_at | timestamptz | NO | DEFAULT now() | Calculation timestamp |
| CHECK | | | | `num_nonnulls(target_skill_id, target_technology_id, target_concept_id) = 1` |

**`risk_findings`**
Purpose: Repository and commit-level risk signals (CodeRisk).
| Column | Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| id | uuid | NO | PK | Internal identifier |
| repository_id | uuid | NO | FK(repositories.id) | Affected repo |
| analysis_run_id | uuid | NO | FK(analysis_runs.id) | Run that found the risk |
| observation_id | uuid | NO | FK(observations.id)| Underlying observation |
| commit_id | uuid | YES | FK(commits.id) | Attributed commit (if applicable) |
| file_path | text | YES | | Location in repo |
| line_start | integer| YES | | Code block start |
| line_end | integer| YES | | Code block end |
| category | risk_category | NO | | ENUM: SECURITY, RELIABILITY, TESTING, MAINTAINABILITY, DEPENDENCY, ARCHITECTURE |
| risk_type | text | NO | | Specific rule (e.g., 'HARDCODED_SECRET') |
| severity | risk_severity | NO | | ENUM: LOW, MEDIUM, HIGH, CRITICAL |
| confidence | numeric| NO | CHECK(confidence BETWEEN 0 AND 1) | Heuristic certainty |
| source_tool | text | NO | | e.g., 'CodeQL', 'CustomAST' |
| detected_at | timestamptz | NO | DEFAULT now() | Timestamp |

## Indexes
- `developer_capabilities (developer_id)` - Fast lookups for dashboard.
- `capability_history (capability_id, recorded_at DESC)` - Time-series retrieval.
- `evidence_skills/techs/concepts (*_id)` - Reverse lookups to find what evidence supports a skill.
- `risk_findings (repository_id, severity)` - Dashboard filtering.
- `analysis_runs (repository_id, started_at DESC)` - Finding the latest analysis state.
- `observations (analysis_run_id)` - Retrieving raw data for a run.

## Row Level Security (RLS) Strategy
- **Developers**: Can read their own `developers`, `github_accounts`, and `projects` records.
- **Capabilities & Evidence**: A developer can only query `developer_capabilities`, `capability_history`, `skill_gaps`, and `evidence` where the record traces back to their `developer_id`.
- **Repositories & Risks**: A developer can read `repositories`, `analysis_runs`, and `risk_findings` if the repository belongs to a project they own.
- **SkillGraph Taxonomy**: `skills`, `technologies`, `concepts`, and their relationships are universally readable by authenticated users as they form a public, shared taxonomy.

## Migration Strategy
- **Migration 001**: Core identities (`developers`, `github_accounts`, `projects`).
- **Migration 002**: GitHub/repository domain (`repositories`, dependencies, commits, PRs).
- **Migration 003**: Analysis/observation domain (ENUMs, `analysis_runs`, `observations`).
- **Migration 004**: SkillGraph domain (Taxonomy tables and junction relationships).
- **Migration 005**: Evidence/capability domain (Evidence tables, exclusive arc `developer_capabilities`, `capability_history`, `skill_gaps`).
- **Migration 006**: CodeRisk domain (`risk_findings`).
- **Migration 007**: RLS policies, indexing, and final constraints.
