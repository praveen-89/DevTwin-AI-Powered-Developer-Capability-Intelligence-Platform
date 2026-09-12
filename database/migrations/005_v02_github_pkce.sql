-- =============================================================================
-- Migration: 005_v02_github_pkce.sql
-- DevTwin — v0.2 GitHub App PKCE & Disconnect Semantics
--
-- Changes:
--   1. ALTER TABLE github_connection_states ADD COLUMN code_verifier_enc BYTEA
--   2. ALTER TABLE github_accounts ADD CONSTRAINT github_accounts_developer_id_unique UNIQUE(developer_id)
--   3. ALTER TABLE github_accounts ADD COLUMN disconnected_at TIMESTAMPTZ
--
-- Security Notes:
--   - PKCE verifier is stored encrypted at rest. It must NOT be hashed.
--   - Disconnect preserves historical data and only inactivates the connection.
-- =============================================================================

BEGIN;

-- 1. PKCE VERIFIER STORAGE
ALTER TABLE github_connection_states
    ADD COLUMN code_verifier_enc BYTEA;

COMMENT ON COLUMN github_connection_states.code_verifier_enc IS
    'Encrypted PKCE code_verifier. Must be decrypted server-side during the GitHub OAuth callback exchange. Never stored as a one-way hash. The encryption key is application-managed and is not stored in the database.';

-- 2. ONE-TO-ONE GITHUB LINKING
-- Ensure a strict 1:1 mapping between Developer and GitHub Account
ALTER TABLE github_accounts
    ADD CONSTRAINT github_accounts_developer_id_unique UNIQUE (developer_id);

-- 3. DISCONNECT SEMANTICS
ALTER TABLE github_accounts
    ADD COLUMN disconnected_at TIMESTAMPTZ;

COMMENT ON COLUMN github_accounts.disconnected_at IS
    'When NULL, the GitHub connection is currently active. When non-NULL, the connection has been disconnected. Historical repositories, commits, pull requests, observations, evidence, risk findings, and capability history must remain preserved.';

COMMIT;
