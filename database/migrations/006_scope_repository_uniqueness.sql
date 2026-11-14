-- =============================================================================
-- Migration: 006_scope_repository_uniqueness.sql
-- DevTwin — Scope repository uniqueness per-project instead of globally
--
-- Problem:
--   repositories carried TWO bare global UNIQUE constraints:
--     repositories_github_repo_id_key  UNIQUE (github_repo_id)
--     repositories_full_name_key       UNIQUE (full_name)
--   making registration of a given GitHub repository global across ALL
--   developers. Two different DevTwin developers attempting to register
--   the same GitHub repository (including the same public repo, or a
--   developer re-registering after a stale/orphaned row from another
--   account) would incorrectly collide with HTTP 409
--   "Repository already registered.", even though the rows belong to
--   entirely different developers/projects.
--
-- Fix:
--   Drop both global UNIQUE constraints and the now-redundant
--   github_repo_id index, and add composite UNIQUE(project_id, <col>)
--   constraints instead. Since each project belongs to exactly one
--   developer (projects.developer_id NOT NULL), this prevents a given
--   project from registering the same GitHub repository twice, while
--   allowing different developers (and different projects owned by the
--   same developer) to each register the same GitHub repository
--   independently.
--
-- Note:
--   repositories.project_id is nullable (ON DELETE SET NULL on project
--   deletion). Standard SQL unique constraints treat NULL as distinct from
--   any other value, so orphaned repositories (project_id IS NULL) are not
--   constrained against each other by this composite key. This matches
--   existing behavior for orphaned rows elsewhere in the schema and is not
--   a regression introduced by this migration.
-- =============================================================================

BEGIN;

-- 1. Drop the now-redundant single-column index (the new composite unique
--    constraint below creates its own covering index).
DROP INDEX IF EXISTS idx_repositories_github_id;

-- 2. Drop the global uniqueness constraints on github_repo_id and full_name.
ALTER TABLE repositories
    DROP CONSTRAINT IF EXISTS repositories_github_repo_id_key;

ALTER TABLE repositories
    DROP CONSTRAINT IF EXISTS repositories_full_name_key;

-- 3. Add project-scoped composite uniqueness constraints.
ALTER TABLE repositories
    ADD CONSTRAINT repositories_project_id_github_repo_id_key
        UNIQUE (project_id, github_repo_id);

ALTER TABLE repositories
    ADD CONSTRAINT repositories_project_id_full_name_key
        UNIQUE (project_id, full_name);

COMMENT ON CONSTRAINT repositories_project_id_github_repo_id_key ON repositories IS
    'Prevents the same GitHub repository from being registered twice within the same project, while allowing different developers/projects to independently register the same GitHub repository. Replaces the global UNIQUE(github_repo_id) constraint from 001_initial_schema.sql.';

COMMENT ON CONSTRAINT repositories_project_id_full_name_key ON repositories IS
    'Prevents the same full_name (owner/repo) from being registered twice within the same project, while allowing different developers/projects to independently register a repository with the same full_name. Replaces the global UNIQUE(full_name) constraint from 001_initial_schema.sql.';

COMMIT;
