-- =============================================================================
-- Migration: 004_v02_auth_github.sql
-- DevTwin — v0.2 Authentication & GitHub Integration Schema
--
-- Implements approved schema changes from docs/11_DATABASE_SCHEMA.md (v0.2)
-- and the frozen Authentication Architecture (ADR-014).
--
-- Changes:
--   1. CREATE TABLE github_connection_states
--      Short-lived, single-use state for the hybrid GitHub App connection flow.
--      Prevents CSRF and replay attacks during the installation callback.
--
--   2. ALTER TABLE github_accounts
--      - DROP COLUMN access_token_enc (persistent tokens are no longer stored)
--      - ADD COLUMN installation_id BIGINT (GitHub App Installation reference)
--
-- Security Notes:
--   - github_connection_states is backend-controlled (written/consumed server-side).
--   - RLS on github_connection_states is defensive. The service-role backend
--     bypasses RLS. Authenticated user RLS prevents cross-user leakage if
--     client-side queries ever occur.
--   - No NULL ownership bypass is introduced.
--   - Existing RLS hardening from migration 003 remains intact.
--   - Installation access tokens are never stored (generated on demand).
--
-- References:
--   ADR-007 (superseded intent), ADR-008 (superseded), ADR-014 (ACTIVE)
--   docs/11_DATABASE_SCHEMA.md
--   docs/05_SYSTEM_ARCHITECTURE.md
-- =============================================================================

BEGIN;

-- =============================================================================
-- SECTION 1: github_connection_states
-- Short-lived, single-use OAuth/installation state records.
-- Written by the backend on GET /github/install.
-- Consumed and invalidated by the backend on GET /github/callback.
-- =============================================================================

CREATE TABLE IF NOT EXISTS github_connection_states (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    developer_id    UUID        NOT NULL REFERENCES developers(id) ON DELETE CASCADE,
    state_hash      TEXT        NOT NULL,   -- Cryptographically random value (e.g., secrets.token_urlsafe(32))
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL,   -- Short TTL, set by backend (e.g., NOW() + INTERVAL '10 minutes')
    used_at         TIMESTAMPTZ,            -- NULL = unused, non-NULL = consumed (replay prevention)

    CONSTRAINT github_connection_states_state_hash_unique UNIQUE (state_hash)
);

COMMENT ON TABLE github_connection_states IS
    'Short-lived, single-use state tokens for the GitHub App installation/callback flow. '
    'Written by the backend on /github/install; consumed and invalidated on /github/callback. '
    'Prevents CSRF and replay attacks. Backend-controlled via service-role.';

COMMENT ON COLUMN github_connection_states.state_hash IS
    'Stores a secure hash (e.g., SHA-256) of the raw random state — never the raw value itself. '
    'Backend flow: generate raw state -> send raw state to GitHub as the OAuth state param -> '
    'store HASH(raw state) here. On callback: hash the returned state param and compare against '
    'this column. Record must be unexpired (NOW() < expires_at) and unused (used_at IS NULL).';

COMMENT ON COLUMN github_connection_states.expires_at IS
    'Absolute expiry timestamp. Backend rejects any record where NOW() > expires_at.';

COMMENT ON COLUMN github_connection_states.used_at IS
    'Set by backend when the state is consumed. Non-NULL records are rejected to prevent replay.';

-- Indexes for github_connection_states
-- NOTE: state_hash lookup is already covered by the UNIQUE constraint index
-- (CONSTRAINT github_connection_states_state_hash_unique). No additional index needed.

-- Ownership lookup: developer_id (for disconnect/cleanup queries)
CREATE INDEX IF NOT EXISTS idx_github_conn_states_developer
    ON github_connection_states (developer_id);

-- Expiration cleanup: expires_at (for future periodic cleanup jobs)
CREATE INDEX IF NOT EXISTS idx_github_conn_states_expires
    ON github_connection_states (expires_at);

-- =============================================================================
-- SECTION 2: Modify github_accounts
--
-- Remove access_token_enc: persistent GitHub user tokens are no longer stored.
-- The hybrid flow uses a temporary user token only for installation verification,
-- then discards it immediately.
--
-- Add installation_id: the GitHub App Installation ID used to generate
-- short-lived installation access tokens on demand.
-- =============================================================================

-- Drop the superseded token column (ADR-008 superseded by ADR-014)
ALTER TABLE github_accounts
    DROP COLUMN IF EXISTS access_token_enc;

-- Add the installation_id used for on-demand token generation
ALTER TABLE github_accounts
    ADD COLUMN IF NOT EXISTS installation_id BIGINT;

COMMENT ON COLUMN github_accounts.installation_id IS
    'GitHub App Installation ID. Used to generate short-lived installation access tokens '
    'on demand via the GitHub App private key. Never store the access token itself.';

-- Update the table-level comment to reflect the new security model
COMMENT ON TABLE github_accounts IS
    'GitHub identity linked to a developer. '
    'installation_id is used to generate short-lived installation access tokens on demand. '
    'No GitHub credentials are stored. See ADR-014.';

-- =============================================================================
-- SECTION 3: RLS — github_connection_states
--
-- The primary access model is backend/service-role only, which bypasses RLS.
-- The following RLS policies are defensive: they ensure that if the anon or
-- authenticated role ever queries this table directly, records remain isolated
-- per developer and cannot be read or modified cross-user.
--
-- Policy decisions:
--   - SELECT: Developer can only see their own state records.
--   - INSERT: Backend uses service-role. No authenticated INSERT policy.
--   - UPDATE: Backend uses service-role. No authenticated UPDATE policy.
--   - DELETE: Backend uses service-role. No authenticated DELETE policy.
--
-- This is intentionally restrictive. The backend writes and validates state
-- entirely via service-role. Authenticated-role access is read-only as a
-- defensive measure only.
-- =============================================================================

ALTER TABLE github_connection_states ENABLE ROW LEVEL SECURITY;

-- Defensive SELECT: authenticated developer may only see their own records.
-- This does NOT weaken security; backend uses service-role which bypasses RLS.
CREATE POLICY "github_conn_states_select_own" ON github_connection_states
    FOR SELECT USING (
        developer_id IN (
            SELECT id FROM developers WHERE auth_user_id = auth.uid()
        )
    );

-- No INSERT/UPDATE/DELETE policies for authenticated role.
-- All mutation operations are performed by the backend via service-role.

COMMIT;
