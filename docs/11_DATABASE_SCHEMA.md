# 11. Database Schema

*Source of Truth Context: This document defines how persistent domain data is represented in PostgreSQL.*

## Overview
This document specifies the PostgreSQL schema. It uses normalized tables, UUID primary keys for internal data, and strictly separates external IDs.

## Capability Target Design Decision
**Decision**: Exclusive Arc.
By using three nullable foreign keys (`skill_id`, `technology_id`, `concept_id`) and a `CHECK (num_nonnulls(skill_id, technology_id, concept_id) = 1)`, we guarantee strict foreign key constraints.

## Table Specifications

### 1. Identity & Projects

**`developers`**
| Column | Type | Nullable | Default | Constraints | Description |
|---|---|---|---|---|---|
| id | uuid | NO | uuid_generate_v4() | PK | Internal Developer ID |
| auth_user_id | uuid | NO | | UNIQUE | Maps to Supabase auth.users.id |
| created_at | timestamptz | NO | now() | | |
| updated_at | timestamptz | NO | now() | | |

**`github_accounts`**
| Column | Type | Nullable | Default | Constraints | Description |
|---|---|---|---|---|---|
| id | uuid | NO | uuid_generate_v4() | PK | Internal ID |
| developer_id | uuid | NO | | FK(developers.id) ON DELETE CASCADE | |
| github_id | bigint | NO | | UNIQUE | GitHub's immutable User ID |
| username | text | NO | | | |
| installation_id | bigint | YES | | | GitHub App Installation ID |

**`github_connection_states`**
| Column | Type | Nullable | Default | Constraints | Description |
|---|---|---|---|---|---|
| id | uuid | NO | uuid_generate_v4() | PK | Internal ID |
| developer_id | uuid | NO | | FK(developers.id) ON DELETE CASCADE | |
| state_hash | text | NO | | UNIQUE | Cryptographically random single-use state |
| created_at | timestamptz | NO | now() | | |
| expires_at | timestamptz | NO | | | |
| used_at | timestamptz | YES | | | |

**`projects`**
| Column | Type | Nullable | Default | Constraints | Description |
|---|---|---|---|---|---|
| id | uuid | NO | uuid_generate_v4() | PK | Internal ID |
| developer_id | uuid | NO | | FK(developers.id) ON DELETE CASCADE | |
| name | text | NO | | | |

### 2. Repository Domain

**`repositories`**
| Column | Type | Nullable | Default | Constraints | Description |
|---|---|---|---|---|---|
| id | uuid | NO | uuid_generate_v4() | PK | Internal ID |
| project_id | uuid | YES | | FK(projects.id) ON DELETE SET NULL | |
| github_repo_id | bigint | YES | | UNIQUE | |
| owner_login | text | NO | | | |
| name | text | NO | | | |
| full_name | text | NO | | UNIQUE | |
| url | text | NO | | | |
| default_branch | text | NO | 'main' | | |
| visibility | text | NO | | | |

**`commits`**
| Column | Type | Nullable | Default | Constraints | Description |
|---|---|---|---|---|---|
| id | uuid | NO | uuid_generate_v4() | PK | Internal ID |
| repository_id | uuid | NO | | FK(repositories.id) ON DELETE CASCADE | |
| sha | text | NO | | | |
| author_name | text | YES | | | |
| author_email | text | YES | | | |
| committed_at | timestamptz | NO | | | |

**`pull_requests`**
| Column | Type | Nullable | Default | Constraints | Description |
|---|---|---|---|---|---|
| id | uuid | NO | uuid_generate_v4() | PK | Internal ID |
| repository_id | uuid | NO | | FK(repositories.id) ON DELETE CASCADE | |
| github_pr_id | bigint | YES | | UNIQUE | |
| pr_number | integer| NO | | | |
| author_username | text | YES | | | |
| state | text | NO | | | 'open', 'closed', 'merged' |
| created_at | timestamptz | NO | | | |

### 3. Analysis Pipeline

**`analysis_jobs`**
Purpose: The user/system request to analyze a repository.
| Column | Type | Nullable | Default | Constraints | Description |
|---|---|---|---|---|---|
| id | uuid | NO | uuid_generate_v4() | PK | Internal ID |
| repository_id | uuid | NO | | FK(repositories.id) ON DELETE CASCADE | |
| status | text | NO | 'QUEUED' | | QUEUED, PROCESSING, COMPLETED, FAILED |
| attempt_count | integer| NO | 0 | | Number of runs executed |
| requested_at | timestamptz | NO | now() | | |
| completed_at | timestamptz | YES | | | |

**`analysis_runs`**
Purpose: A concrete execution attempt.
| Column | Type | Nullable | Default | Constraints | Description |
|---|---|---|---|---|---|
| id | uuid | NO | uuid_generate_v4() | PK | Internal ID |
| analysis_job_id | uuid | NO | | FK(analysis_jobs.id) ON DELETE CASCADE | |
| repository_id | uuid | NO | | FK(repositories.id) ON DELETE CASCADE | |
| status | text | NO | | CHECK(status IN ('QUEUED', 'FETCHING', 'MINING', 'SKILL_GRAPH', 'CODE_RISK', 'CAPABILITY', 'COMPLETED', 'FAILED')) | |
| analyzer_version| text | NO | | | |
| schema_version | text | NO | | | |
| error_code | text | YES | | | |
| error_message | text | YES | | | |
| started_at | timestamptz | YES | | | |
| completed_at | timestamptz | YES | | | |

**`observations`**
| Column | Type | Nullable | Default | Constraints | Description |
|---|---|---|---|---|---|
| id | uuid | NO | uuid_generate_v4() | PK | Internal ID |
| analysis_run_id | uuid | NO | | FK(analysis_runs.id) ON DELETE CASCADE | |
| type | text | NO | | | |
| source_tool | text | NO | | | |
| source_reference| jsonb| YES | | | |
| confidence | numeric| YES | | CHECK(confidence BETWEEN 0 AND 1) | |

### 4. SkillGraph Taxonomy & Evidence

**`skills`**, **`technologies`**, **`concepts`**
Columns: `id` (uuid PK), `name` (text UNIQUE).

**`skill_relationships`** (Internal graph edges)
| Column | Type | Nullable | Default | Constraints | Description |
|---|---|---|---|---|---|
| source_id | uuid | NO | | FK(skills.id) ON DELETE CASCADE | |
| target_id | uuid | NO | | FK(skills.id) ON DELETE CASCADE | |
| relation_type | text | NO | | | e.g., 'REQUIRES', 'RELATED_TO' |

**`evidence`**
| Column | Type | Nullable | Default | Constraints | Description |
|---|---|---|---|---|---|
| id | uuid | NO | uuid_generate_v4() | PK | Internal ID |
| observation_id | uuid | YES | | FK(observations.id) ON DELETE SET NULL | |
| type | text | NO | | | |
| strength | numeric| NO | | CHECK(strength BETWEEN 0 AND 1) | |
| polarity | numeric| NO | | CHECK(polarity BETWEEN -1 AND 1) | Positive/Negative evidence |

### 5. Capability

**`developer_capabilities`**
| Column | Type | Nullable | Default | Constraints | Description |
|---|---|---|---|---|---|
| id | uuid | NO | uuid_generate_v4() | PK | Internal ID |
| developer_id | uuid | NO | | FK(developers.id) ON DELETE CASCADE | |
| skill_id | uuid | YES | | FK(skills.id) ON DELETE CASCADE | |
| technology_id | uuid | YES | | FK(technologies.id) ON DELETE CASCADE | |
| concept_id | uuid | YES | | FK(concepts.id) ON DELETE CASCADE | |
| score | numeric| NO | | CHECK(score BETWEEN 0 AND 1) | |
| confidence | numeric| NO | | CHECK(confidence BETWEEN 0 AND 1) | |
| scoring_version | text | NO | | | |
*Constraints*: CHECK `(num_nonnulls(skill_id, technology_id, concept_id) = 1)`

**`capability_history`**
Append-only log of `developer_capabilities`. `score`, `confidence`, `analysis_run_id`, `recorded_at`.

### 6. CodeRisk

**`risk_findings`**
| Column | Type | Nullable | Default | Constraints | Description |
|---|---|---|---|---|---|
| id | uuid | NO | uuid_generate_v4() | PK | Internal ID |
| repository_id | uuid | NO | | FK(repositories.id) ON DELETE CASCADE | |
| analysis_run_id | uuid | NO | | FK(analysis_runs.id) ON DELETE CASCADE | |
| observation_id | uuid | NO | | FK(observations.id) ON DELETE CASCADE | |
| commit_id | uuid | YES | | FK(commits.id) ON DELETE SET NULL | Optional evidence attribution |
| category | text | NO | | | |
| severity | text | NO | | CHECK(severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')) | |
| confidence | numeric| NO | | CHECK(confidence BETWEEN 0 AND 1) | |
| risk_type | text | NO | | | |
