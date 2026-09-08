-- =============================================================================
-- Migration: 002_rls_policies.sql
-- DevTwin — Row Level Security Policies
--
-- Implements the RLS strategy documented in docs/11_DATABASE_SCHEMA.md
-- and ARCHITECTURE.md (ADR-007).
--
-- Core Principle: Developer A cannot access Developer B's private data.
-- Service-role operations bypass RLS via the service_role key — this key
-- must NEVER be exposed to the frontend or logs.
--
-- Assumes Supabase Auth is the authentication provider.
-- auth.uid() returns the UUID of the authenticated Supabase user.
-- developers.auth_user_id maps to auth.uid() per ADR-002.
-- =============================================================================

-- =============================================================================
-- Enable RLS on all tables that contain developer-owned data
-- =============================================================================

ALTER TABLE developers                  ENABLE ROW LEVEL SECURITY;
ALTER TABLE github_accounts             ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects                    ENABLE ROW LEVEL SECURITY;
ALTER TABLE repositories                ENABLE ROW LEVEL SECURITY;
ALTER TABLE repository_languages        ENABLE ROW LEVEL SECURITY;
ALTER TABLE repository_dependencies     ENABLE ROW LEVEL SECURITY;
ALTER TABLE commits                     ENABLE ROW LEVEL SECURITY;
ALTER TABLE pull_requests               ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_jobs               ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_runs               ENABLE ROW LEVEL SECURITY;
ALTER TABLE observations                ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence                    ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_skills             ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_technologies       ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_concepts           ENABLE ROW LEVEL SECURITY;
ALTER TABLE developer_capabilities      ENABLE ROW LEVEL SECURITY;
ALTER TABLE capability_history          ENABLE ROW LEVEL SECURITY;
ALTER TABLE skill_gaps                  ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_findings               ENABLE ROW LEVEL SECURITY;

-- Public taxonomy tables (read-only for all authenticated users)
ALTER TABLE skills                      ENABLE ROW LEVEL SECURITY;
ALTER TABLE technologies                ENABLE ROW LEVEL SECURITY;
ALTER TABLE concepts                    ENABLE ROW LEVEL SECURITY;
ALTER TABLE skill_technologies          ENABLE ROW LEVEL SECURITY;
ALTER TABLE skill_concepts              ENABLE ROW LEVEL SECURITY;
ALTER TABLE technology_concepts         ENABLE ROW LEVEL SECURITY;
ALTER TABLE skill_relationships         ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- DEVELOPERS
-- A developer can only see and modify their own record.
-- =============================================================================

CREATE POLICY "developers_select_own" ON developers
    FOR SELECT USING (auth_user_id = auth.uid());

CREATE POLICY "developers_insert_own" ON developers
    FOR INSERT WITH CHECK (auth_user_id = auth.uid());

CREATE POLICY "developers_update_own" ON developers
    FOR UPDATE USING (auth_user_id = auth.uid());

-- Developers cannot delete themselves via the API (admin-only operation)

-- =============================================================================
-- GITHUB ACCOUNTS
-- Accessible only to the owning developer.
-- =============================================================================

CREATE POLICY "github_accounts_select_own" ON github_accounts
    FOR SELECT USING (
        developer_id IN (
            SELECT id FROM developers WHERE auth_user_id = auth.uid()
        )
    );

CREATE POLICY "github_accounts_insert_own" ON github_accounts
    FOR INSERT WITH CHECK (
        developer_id IN (
            SELECT id FROM developers WHERE auth_user_id = auth.uid()
        )
    );

CREATE POLICY "github_accounts_update_own" ON github_accounts
    FOR UPDATE USING (
        developer_id IN (
            SELECT id FROM developers WHERE auth_user_id = auth.uid()
        )
    );

-- =============================================================================
-- PROJECTS
-- =============================================================================

CREATE POLICY "projects_select_own" ON projects
    FOR SELECT USING (
        developer_id IN (
            SELECT id FROM developers WHERE auth_user_id = auth.uid()
        )
    );

CREATE POLICY "projects_insert_own" ON projects
    FOR INSERT WITH CHECK (
        developer_id IN (
            SELECT id FROM developers WHERE auth_user_id = auth.uid()
        )
    );

CREATE POLICY "projects_update_own" ON projects
    FOR UPDATE USING (
        developer_id IN (
            SELECT id FROM developers WHERE auth_user_id = auth.uid()
        )
    );

-- =============================================================================
-- REPOSITORIES
-- Accessible only to developer who owns the project they belong to.
-- =============================================================================

CREATE POLICY "repositories_select_own" ON repositories
    FOR SELECT USING (
        project_id IN (
            SELECT p.id FROM projects p
            JOIN developers d ON d.id = p.developer_id
            WHERE d.auth_user_id = auth.uid()
        )
        OR project_id IS NULL  -- Unassigned repos: access controlled elsewhere
    );

CREATE POLICY "repositories_insert_own" ON repositories
    FOR INSERT WITH CHECK (
        project_id IN (
            SELECT p.id FROM projects p
            JOIN developers d ON d.id = p.developer_id
            WHERE d.auth_user_id = auth.uid()
        )
    );

-- =============================================================================
-- REPOSITORY sub-tables (languages, dependencies, commits, PRs)
-- Inherit access through repository ownership.
-- =============================================================================

CREATE POLICY "repo_languages_select_own" ON repository_languages
    FOR SELECT USING (
        repository_id IN (
            SELECT r.id FROM repositories r
            JOIN projects p ON p.id = r.project_id
            JOIN developers d ON d.id = p.developer_id
            WHERE d.auth_user_id = auth.uid()
        )
    );

CREATE POLICY "repo_dependencies_select_own" ON repository_dependencies
    FOR SELECT USING (
        repository_id IN (
            SELECT r.id FROM repositories r
            JOIN projects p ON p.id = r.project_id
            JOIN developers d ON d.id = p.developer_id
            WHERE d.auth_user_id = auth.uid()
        )
    );

CREATE POLICY "commits_select_own" ON commits
    FOR SELECT USING (
        repository_id IN (
            SELECT r.id FROM repositories r
            JOIN projects p ON p.id = r.project_id
            JOIN developers d ON d.id = p.developer_id
            WHERE d.auth_user_id = auth.uid()
        )
    );

CREATE POLICY "pull_requests_select_own" ON pull_requests
    FOR SELECT USING (
        repository_id IN (
            SELECT r.id FROM repositories r
            JOIN projects p ON p.id = r.project_id
            JOIN developers d ON d.id = p.developer_id
            WHERE d.auth_user_id = auth.uid()
        )
    );

-- =============================================================================
-- ANALYSIS PIPELINE (jobs, runs, observations)
-- =============================================================================

CREATE POLICY "analysis_jobs_select_own" ON analysis_jobs
    FOR SELECT USING (
        repository_id IN (
            SELECT r.id FROM repositories r
            JOIN projects p ON p.id = r.project_id
            JOIN developers d ON d.id = p.developer_id
            WHERE d.auth_user_id = auth.uid()
        )
    );

CREATE POLICY "analysis_runs_select_own" ON analysis_runs
    FOR SELECT USING (
        repository_id IN (
            SELECT r.id FROM repositories r
            JOIN projects p ON p.id = r.project_id
            JOIN developers d ON d.id = p.developer_id
            WHERE d.auth_user_id = auth.uid()
        )
    );

CREATE POLICY "observations_select_own" ON observations
    FOR SELECT USING (
        analysis_run_id IN (
            SELECT ar.id FROM analysis_runs ar
            JOIN repositories r ON r.id = ar.repository_id
            JOIN projects p ON p.id = r.project_id
            JOIN developers d ON d.id = p.developer_id
            WHERE d.auth_user_id = auth.uid()
        )
    );

-- =============================================================================
-- TAXONOMY (Skills, Technologies, Concepts)
-- Read-only for all authenticated users. Writes are service-role only.
-- =============================================================================

CREATE POLICY "skills_select_authenticated" ON skills
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "technologies_select_authenticated" ON technologies
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "concepts_select_authenticated" ON concepts
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "skill_technologies_select_authenticated" ON skill_technologies
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "skill_concepts_select_authenticated" ON skill_concepts
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "technology_concepts_select_authenticated" ON technology_concepts
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "skill_relationships_select_authenticated" ON skill_relationships
    FOR SELECT TO authenticated USING (true);

-- =============================================================================
-- EVIDENCE
-- =============================================================================

CREATE POLICY "evidence_select_own" ON evidence
    FOR SELECT USING (
        observation_id IN (
            SELECT o.id FROM observations o
            JOIN analysis_runs ar ON ar.id = o.analysis_run_id
            JOIN repositories r ON r.id = ar.repository_id
            JOIN projects p ON p.id = r.project_id
            JOIN developers d ON d.id = p.developer_id
            WHERE d.auth_user_id = auth.uid()
        )
        OR observation_id IS NULL  -- Manual/system evidence
    );

CREATE POLICY "evidence_skills_select_own" ON evidence_skills
    FOR SELECT USING (
        evidence_id IN (
            SELECT e.id FROM evidence e
            JOIN observations o ON o.id = e.observation_id
            JOIN analysis_runs ar ON ar.id = o.analysis_run_id
            JOIN repositories r ON r.id = ar.repository_id
            JOIN projects p ON p.id = r.project_id
            JOIN developers d ON d.id = p.developer_id
            WHERE d.auth_user_id = auth.uid()
        )
    );

CREATE POLICY "evidence_technologies_select_own" ON evidence_technologies
    FOR SELECT USING (
        evidence_id IN (
            SELECT e.id FROM evidence e
            JOIN observations o ON o.id = e.observation_id
            JOIN analysis_runs ar ON ar.id = o.analysis_run_id
            JOIN repositories r ON r.id = ar.repository_id
            JOIN projects p ON p.id = r.project_id
            JOIN developers d ON d.id = p.developer_id
            WHERE d.auth_user_id = auth.uid()
        )
    );

CREATE POLICY "evidence_concepts_select_own" ON evidence_concepts
    FOR SELECT USING (
        evidence_id IN (
            SELECT e.id FROM evidence e
            JOIN observations o ON o.id = e.observation_id
            JOIN analysis_runs ar ON ar.id = o.analysis_run_id
            JOIN repositories r ON r.id = ar.repository_id
            JOIN projects p ON p.id = r.project_id
            JOIN developers d ON d.id = p.developer_id
            WHERE d.auth_user_id = auth.uid()
        )
    );

-- =============================================================================
-- CAPABILITIES & HISTORY
-- =============================================================================

CREATE POLICY "dev_capabilities_select_own" ON developer_capabilities
    FOR SELECT USING (
        developer_id IN (
            SELECT id FROM developers WHERE auth_user_id = auth.uid()
        )
    );

CREATE POLICY "capability_history_select_own" ON capability_history
    FOR SELECT USING (
        capability_id IN (
            SELECT dc.id FROM developer_capabilities dc
            JOIN developers d ON d.id = dc.developer_id
            WHERE d.auth_user_id = auth.uid()
        )
    );

CREATE POLICY "skill_gaps_select_own" ON skill_gaps
    FOR SELECT USING (
        developer_id IN (
            SELECT id FROM developers WHERE auth_user_id = auth.uid()
        )
    );

-- =============================================================================
-- RISK FINDINGS
-- =============================================================================

CREATE POLICY "risk_findings_select_own" ON risk_findings
    FOR SELECT USING (
        repository_id IN (
            SELECT r.id FROM repositories r
            JOIN projects p ON p.id = r.project_id
            JOIN developers d ON d.id = p.developer_id
            WHERE d.auth_user_id = auth.uid()
        )
    );
