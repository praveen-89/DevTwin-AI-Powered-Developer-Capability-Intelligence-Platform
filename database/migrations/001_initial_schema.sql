-- =============================================================================
-- Migration: 001_initial_schema.sql
-- DevTwin — Core Domain Schema
--
-- Creates all tables, constraints, indexes, and junction tables
-- exactly as specified in docs/11_DATABASE_SCHEMA.md and docs/DOMAIN_MODEL.md.
--
-- Ordered to respect foreign key dependencies.
-- Safe to run on a clean Supabase PostgreSQL database.
-- =============================================================================

-- Enable UUID generation (Supabase provides this by default via pgcrypto)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- SECTION 1: Identity & Projects
-- =============================================================================

-- developers
-- Core developer identity. auth_user_id maps to Supabase auth.users.id.
-- developers.id is an independent internal UUID per ADR-002.
CREATE TABLE IF NOT EXISTS developers (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    auth_user_id    UUID        NOT NULL UNIQUE, -- Maps to auth.users.id
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE developers IS 'Internal developer identity. auth_user_id maps to Supabase auth.users.id.';
COMMENT ON COLUMN developers.auth_user_id IS 'Foreign reference to Supabase auth.users.id. NOT a direct FK to allow RLS decoupling.';

-- github_accounts
-- External GitHub identity linked to a developer.
-- access_token_enc is for encrypted material or an external Vault reference — NEVER plaintext.
CREATE TABLE IF NOT EXISTS github_accounts (
    id                  UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    developer_id        UUID    NOT NULL REFERENCES developers(id) ON DELETE CASCADE,
    github_id           BIGINT  NOT NULL UNIQUE, -- GitHub's immutable user ID
    username            TEXT    NOT NULL,
    access_token_enc    TEXT,   -- Encrypted token or external ref. NULL until connected.
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE github_accounts IS 'GitHub identity linked to a developer. access_token_enc is encrypted or an external Vault reference — never plaintext.';

-- projects
-- Logical groupings of repositories owned by a developer.
CREATE TABLE IF NOT EXISTS projects (
    id              UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    developer_id    UUID    NOT NULL REFERENCES developers(id) ON DELETE CASCADE,
    name            TEXT    NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- SECTION 2: Repository Domain
-- =============================================================================

-- repositories
-- Tracked codebases. github_repo_id is separate from the internal id per ADR-002.
CREATE TABLE IF NOT EXISTS repositories (
    id              UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID    REFERENCES projects(id) ON DELETE SET NULL,
    github_repo_id  BIGINT  UNIQUE,                -- GitHub's external repo ID
    owner_login     TEXT    NOT NULL,
    name            TEXT    NOT NULL,
    full_name       TEXT    NOT NULL UNIQUE,        -- e.g. 'facebook/react'
    url             TEXT    NOT NULL,
    default_branch  TEXT    NOT NULL DEFAULT 'main',
    visibility      TEXT    NOT NULL,              -- 'public' | 'private'
    synced_at       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- repository_languages
-- Language breakdown per repository (updated by analysis runs).
CREATE TABLE IF NOT EXISTS repository_languages (
    id              UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository_id   UUID    NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    language        TEXT    NOT NULL,
    bytes           BIGINT  NOT NULL DEFAULT 0,
    UNIQUE (repository_id, language)
);

-- repository_dependencies
-- Tracked package dependencies per repository.
CREATE TABLE IF NOT EXISTS repository_dependencies (
    id              UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository_id   UUID    NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    ecosystem       TEXT    NOT NULL, -- 'npm', 'pip', 'cargo', etc.
    package_name    TEXT    NOT NULL,
    version_constraint TEXT,
    UNIQUE (repository_id, ecosystem, package_name)
);

-- commits
-- Git commit records. Used for CodeRisk attribution.
CREATE TABLE IF NOT EXISTS commits (
    id              UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository_id   UUID    NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    sha             TEXT    NOT NULL,
    author_name     TEXT,
    author_email    TEXT,
    committed_at    TIMESTAMPTZ NOT NULL,
    UNIQUE (repository_id, sha)
);

-- pull_requests
-- Pull request records. Used as collaboration evidence.
CREATE TABLE IF NOT EXISTS pull_requests (
    id              UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository_id   UUID    NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    github_pr_id    BIGINT  UNIQUE,     -- External GitHub PR ID
    pr_number       INTEGER NOT NULL,
    author_username TEXT,
    state           TEXT    NOT NULL,   -- 'open' | 'closed' | 'merged'
    created_at      TIMESTAMPTZ NOT NULL,
    UNIQUE (repository_id, pr_number)
);

-- =============================================================================
-- SECTION 3: Analysis Pipeline
-- =============================================================================

-- analysis_jobs
-- Represents the user/system request to analyze a repository.
-- A single job may contain multiple analysis_runs (retries).
CREATE TABLE IF NOT EXISTS analysis_jobs (
    id              UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository_id   UUID    NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    status          TEXT    NOT NULL DEFAULT 'QUEUED'
                    CHECK (status IN ('QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED')),
    attempt_count   INTEGER NOT NULL DEFAULT 0,
    requested_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

COMMENT ON TABLE analysis_jobs IS 'User/system request to analyze a repository. May contain multiple analysis_runs (retries).';

-- analysis_runs
-- A concrete, bounded execution attempt of an analysis_job.
-- Immutable once completed/failed. Multiple runs may belong to one job.
CREATE TABLE IF NOT EXISTS analysis_runs (
    id                  UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_job_id     UUID    NOT NULL REFERENCES analysis_jobs(id) ON DELETE CASCADE,
    repository_id       UUID    NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    status              TEXT    NOT NULL DEFAULT 'QUEUED'
                        CHECK (status IN (
                            'QUEUED', 'FETCHING', 'MINING',
                            'SKILL_GRAPH', 'CODE_RISK', 'CAPABILITY',
                            'COMPLETED', 'FAILED'
                        )),
    analyzer_version    TEXT    NOT NULL,
    schema_version      TEXT    NOT NULL,
    error_code          TEXT,
    error_message       TEXT,
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE analysis_runs IS 'Concrete execution attempt. Immutable once COMPLETED or FAILED. Multiple runs belong to one analysis_job (retries).';

-- observations
-- Directly detected, immutable facts produced by an analysis run.
-- Observation ≠ Evidence. See DOMAIN_MODEL.md.
CREATE TABLE IF NOT EXISTS observations (
    id              UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_run_id UUID    NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    type            TEXT    NOT NULL,               -- e.g. 'DEPENDENCY_FOUND', 'FILE_EXISTS'
    source_tool     TEXT    NOT NULL,               -- e.g. 'ast-parser-v1'
    source_reference JSONB,                         -- e.g. {"file": "src/app.py", "line": 5}
    confidence      NUMERIC CHECK (confidence BETWEEN 0 AND 1),
    observed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE observations IS 'Immutable raw facts extracted by an analysis run. Observation ≠ Evidence.';

-- =============================================================================
-- SECTION 4: SkillGraph Taxonomy
-- =============================================================================

-- skills
-- Broad competency areas (e.g., 'Backend Development'). Global/shared taxonomy.
CREATE TABLE IF NOT EXISTS skills (
    id      UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    name    TEXT    NOT NULL UNIQUE,
    domain  TEXT
);

-- technologies
-- Concrete implementation technologies (e.g., 'FastAPI'). Global taxonomy.
CREATE TABLE IF NOT EXISTS technologies (
    id      UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    name    TEXT    NOT NULL UNIQUE,
    type    TEXT    -- e.g. 'framework', 'language', 'tool'
);

-- concepts
-- Underlying technical concepts (e.g., 'REST API'). Global taxonomy.
CREATE TABLE IF NOT EXISTS concepts (
    id      UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    name    TEXT    NOT NULL UNIQUE
);

-- skill_technologies (Junction: Skill ↔ Technology)
CREATE TABLE IF NOT EXISTS skill_technologies (
    skill_id        UUID    NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    technology_id   UUID    NOT NULL REFERENCES technologies(id) ON DELETE CASCADE,
    PRIMARY KEY (skill_id, technology_id)
);

-- skill_concepts (Junction: Skill ↔ Concept)
CREATE TABLE IF NOT EXISTS skill_concepts (
    skill_id        UUID    NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    concept_id      UUID    NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    PRIMARY KEY (skill_id, concept_id)
);

-- technology_concepts (Junction: Technology ↔ Concept)
CREATE TABLE IF NOT EXISTS technology_concepts (
    technology_id   UUID    NOT NULL REFERENCES technologies(id) ON DELETE CASCADE,
    concept_id      UUID    NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    PRIMARY KEY (technology_id, concept_id)
);

-- skill_relationships
-- Directed edges in the SkillGraph (e.g., React REQUIRES JavaScript).
CREATE TABLE IF NOT EXISTS skill_relationships (
    source_id       UUID    NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    target_id       UUID    NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    relation_type   TEXT    NOT NULL CHECK (relation_type IN ('REQUIRES', 'RELATED_TO', 'PART_OF')),
    PRIMARY KEY (source_id, target_id, relation_type)
);

-- =============================================================================
-- SECTION 5: Evidence
-- =============================================================================

-- evidence
-- Contextualized, developer-associated interpretation of observations.
-- Evidence ≠ Observation. See DOMAIN_MODEL.md.
CREATE TABLE IF NOT EXISTS evidence (
    id              UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    observation_id  UUID    REFERENCES observations(id) ON DELETE SET NULL,
    type            TEXT    NOT NULL
                    CHECK (type IN ('MENTION', 'USAGE', 'APPLIED_ENGINEERING', 'DEMONSTRATED_OUTCOME')),
    strength        NUMERIC NOT NULL CHECK (strength BETWEEN 0 AND 1),
    directness      NUMERIC NOT NULL DEFAULT 1.0 CHECK (directness BETWEEN 0 AND 1),
    reliability     NUMERIC NOT NULL DEFAULT 1.0 CHECK (reliability BETWEEN 0 AND 1),
    polarity        NUMERIC NOT NULL CHECK (polarity BETWEEN -1 AND 1), -- negative for risks
    recency         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE evidence IS 'Contextualized interpretation of an observation. Polarity is negative for risk-derived evidence. Evidence ≠ Observation.';

-- evidence_skills (Junction: Evidence → Skill it supports)
CREATE TABLE IF NOT EXISTS evidence_skills (
    evidence_id     UUID    NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    skill_id        UUID    NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (evidence_id, skill_id)
);

-- evidence_technologies (Junction: Evidence → Technology it supports)
CREATE TABLE IF NOT EXISTS evidence_technologies (
    evidence_id     UUID    NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    technology_id   UUID    NOT NULL REFERENCES technologies(id) ON DELETE CASCADE,
    PRIMARY KEY (evidence_id, technology_id)
);

-- evidence_concepts (Junction: Evidence → Concept it supports)
CREATE TABLE IF NOT EXISTS evidence_concepts (
    evidence_id     UUID    NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    concept_id      UUID    NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    PRIMARY KEY (evidence_id, concept_id)
);

-- =============================================================================
-- SECTION 6: Capability
-- =============================================================================

-- developer_capabilities
-- The current inferred capability for a (developer, target) pair.
-- Uses Exclusive Arc: exactly one of skill_id, technology_id, concept_id must be set.
-- Per ADR-005.
CREATE TABLE IF NOT EXISTS developer_capabilities (
    id              UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    developer_id    UUID    NOT NULL REFERENCES developers(id) ON DELETE CASCADE,

    -- Exclusive Arc: exactly one of these must be non-null (ADR-005)
    skill_id        UUID    REFERENCES skills(id) ON DELETE CASCADE,
    technology_id   UUID    REFERENCES technologies(id) ON DELETE CASCADE,
    concept_id      UUID    REFERENCES concepts(id) ON DELETE CASCADE,

    score           NUMERIC NOT NULL CHECK (score BETWEEN 0 AND 1),
    confidence      NUMERIC NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    scoring_version TEXT    NOT NULL, -- Model version used to produce this score

    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Enforce the Exclusive Arc
    CONSTRAINT capability_target_exclusive_arc
        CHECK (num_nonnulls(skill_id, technology_id, concept_id) = 1),

    -- Prevent duplicate (developer, target) combinations
    CONSTRAINT capability_unique_target
        UNIQUE NULLS NOT DISTINCT (developer_id, skill_id, technology_id, concept_id)
);

COMMENT ON TABLE developer_capabilities IS 'Current capability state per developer per target. Exclusive Arc ensures exactly one target FK is populated (ADR-005).';

-- capability_history
-- Append-only, immutable log of every capability state.
-- NEVER update or delete rows from this table.
CREATE TABLE IF NOT EXISTS capability_history (
    id              UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    capability_id   UUID    NOT NULL REFERENCES developer_capabilities(id) ON DELETE CASCADE,
    analysis_run_id UUID    REFERENCES analysis_runs(id) ON DELETE SET NULL,
    score           NUMERIC NOT NULL CHECK (score BETWEEN 0 AND 1),
    confidence      NUMERIC NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    scoring_version TEXT    NOT NULL,
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE capability_history IS 'Append-only history of capability states. Never overwrite. Query for trend analysis.';

-- skill_gaps
-- Delta between required capability target and current developer capability.
-- Uses Exclusive Arc same as developer_capabilities.
CREATE TABLE IF NOT EXISTS skill_gaps (
    id                      UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    developer_id            UUID    NOT NULL REFERENCES developers(id) ON DELETE CASCADE,

    target_skill_id         UUID    REFERENCES skills(id) ON DELETE CASCADE,
    target_technology_id    UUID    REFERENCES technologies(id) ON DELETE CASCADE,
    target_concept_id       UUID    REFERENCES concepts(id) ON DELETE CASCADE,

    target_score    NUMERIC NOT NULL CHECK (target_score BETWEEN 0 AND 1),
    current_score   NUMERIC NOT NULL CHECK (current_score BETWEEN 0 AND 1),
    gap_value       NUMERIC NOT NULL,
    confidence      NUMERIC NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    calculated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT skill_gap_target_exclusive_arc
        CHECK (num_nonnulls(target_skill_id, target_technology_id, target_concept_id) = 1)
);

-- =============================================================================
-- SECTION 7: CodeRisk
-- =============================================================================

-- risk_findings
-- CodeRisk signals. Risk ≠ Competence — see DOMAIN_MODEL.md and RULES.md.
-- commit_id is nullable; only set when Git history attributes the risk to a specific commit.
CREATE TABLE IF NOT EXISTS risk_findings (
    id              UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository_id   UUID    NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    analysis_run_id UUID    NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    observation_id  UUID    NOT NULL REFERENCES observations(id) ON DELETE CASCADE,
    commit_id       UUID    REFERENCES commits(id) ON DELETE SET NULL, -- Optional attribution
    category        TEXT    NOT NULL
                    CHECK (category IN ('SECURITY', 'RELIABILITY', 'TESTING', 'MAINTAINABILITY', 'DEPENDENCY', 'ARCHITECTURE')),
    severity        TEXT    NOT NULL
                    CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    confidence      NUMERIC NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    risk_type       TEXT    NOT NULL,   -- Specific rule/pattern ID
    file_path       TEXT,
    line_start      INTEGER,
    line_end        INTEGER,
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE risk_findings IS 'CodeRisk signals. Risk ≠ Competence. commit_id set only when Git history attributes finding to a specific commit.';

-- =============================================================================
-- SECTION 8: Indexes
-- Defined based on anticipated query patterns from docs/11_DATABASE_SCHEMA.md
-- =============================================================================

-- Developer lookups
CREATE INDEX IF NOT EXISTS idx_developers_auth_user ON developers(auth_user_id);
CREATE INDEX IF NOT EXISTS idx_github_accounts_developer ON github_accounts(developer_id);

-- Repository lookups
CREATE INDEX IF NOT EXISTS idx_repositories_project ON repositories(project_id);
CREATE INDEX IF NOT EXISTS idx_repositories_github_id ON repositories(github_repo_id);

-- Analysis pipeline
CREATE INDEX IF NOT EXISTS idx_jobs_repository ON analysis_jobs(repository_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON analysis_jobs(status);
CREATE INDEX IF NOT EXISTS idx_runs_job ON analysis_runs(analysis_job_id);
CREATE INDEX IF NOT EXISTS idx_runs_repository ON analysis_runs(repository_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON analysis_runs(status);
CREATE INDEX IF NOT EXISTS idx_observations_run ON observations(analysis_run_id);

-- Capability queries (most common dashboard queries)
CREATE INDEX IF NOT EXISTS idx_capabilities_developer ON developer_capabilities(developer_id);
CREATE INDEX IF NOT EXISTS idx_cap_history_capability ON capability_history(capability_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_skill_gaps_developer ON skill_gaps(developer_id);

-- Evidence
CREATE INDEX IF NOT EXISTS idx_evidence_observation ON evidence(observation_id);

-- CodeRisk
CREATE INDEX IF NOT EXISTS idx_risks_repository ON risk_findings(repository_id);
CREATE INDEX IF NOT EXISTS idx_risks_run ON risk_findings(analysis_run_id);
CREATE INDEX IF NOT EXISTS idx_risks_severity ON risk_findings(repository_id, severity);

-- =============================================================================
-- SECTION 9: Updated_at Trigger
-- Automatically maintains updated_at timestamps.
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_developers_updated_at
    BEFORE UPDATE ON developers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
