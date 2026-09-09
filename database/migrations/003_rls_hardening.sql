-- =============================================================================
-- Migration: 003_rls_hardening.sql
-- DevTwin — RLS Security Hardening (v0.1)
--
-- Security Audit Finding:
-- The original `repositories_select_own` policy permitted reading repositories
-- where `project_id IS NULL`. If a project was deleted (ON DELETE SET NULL),
-- its repositories became orphaned and thus globally readable by ALL
-- authenticated users, exposing private metadata (e.g., repository names).
--
-- Fix:
-- Removed the `OR project_id IS NULL` clause. Orphaned repositories are now
-- strictly invisible to authenticated developers and can only be managed by
-- the service_role (which bypasses RLS entirely).
-- =============================================================================

BEGIN;

-- Drop the overly permissive SELECT policy on repositories
DROP POLICY IF EXISTS "repositories_select_own" ON repositories;

-- Recreate the policy with strict project ownership enforcement
CREATE POLICY "repositories_select_own" ON repositories
    FOR SELECT USING (
        project_id IN (
            SELECT p.id FROM projects p
            JOIN developers d ON d.id = p.developer_id
            WHERE d.auth_user_id = auth.uid()
        )
    );

-- Also harden evidence table to ensure no global leakage of manual evidence
-- unless observation_id matches.
DROP POLICY IF EXISTS "evidence_select_own" ON evidence;

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
        -- Manual evidence (observation_id IS NULL) must be restricted.
        -- Given no direct developer_id exists on evidence, manual evidence
        -- shouldn't be globally exposed. We restrict to observation_id match.
    );

COMMIT;
