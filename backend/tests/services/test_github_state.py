"""
DevTwin Backend Tests — GitHub OAuth State + PKCE Persistence Service

All database-dependent tests use mocked AsyncSession (matching the project's
existing test strategy in test_developers.py). No real database is required.

Security sentinel values are used throughout to verify secrets never appear
in exception strings or log output.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import Optional

import pytest

from app.services.github.state import (
    generate_raw_state,
    hash_state,
    generate_pkce_verifier,
    create_pending_state,
    claim_state,
    GitHubOAuthStateContext,
    PendingOAuthState,
)
from app.services.github.exceptions import (
    GitHubStateNotFoundError,
    GitHubStateExpiredError,
    GitHubStatePersistenceError,
    GitHubStateDecryptionError,
)
from app.core.crypto import PKCEDecryptionError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# A valid Fernet key for testing — generated once per session.
TEST_FERNET_KEY = "N2F0d1VNb2h3Nnl4S3hZYmF0bzh1amV6dVpZcDJ2bXg="


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    """Inject required environment variables for all tests in this module."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service")
    monkeypatch.setenv("SECRET_KEY", "secret")
    monkeypatch.setenv("GITHUB_APP_ID", "123")
    monkeypatch.setenv("GITHUB_APP_SLUG", "app")
    monkeypatch.setenv("GITHUB_CLIENT_ID", "client")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "secret")
    monkeypatch.setenv("GITHUB_PRIVATE_KEY", "key")
    monkeypatch.setenv("GITHUB_REDIRECT_URL", "http://localhost/cb")
    monkeypatch.setenv("GITHUB_STATE_ENCRYPTION_KEY", TEST_FERNET_KEY)
    monkeypatch.setenv("GITHUB_STATE_TTL_SECONDS", "600")

    from app.core.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _make_mock_session() -> AsyncMock:
    """Return a minimal async session mock matching the existing test pattern."""
    session = AsyncMock()
    session.add = MagicMock()  # add() is synchronous in SQLAlchemy
    return session


# ===========================================================================
# 1. State generation — no database
# ===========================================================================

def test_generate_raw_state_is_non_empty():
    """Raw state is a non-empty string."""
    state = generate_raw_state()
    assert isinstance(state, str)
    assert len(state) > 0


def test_generate_raw_state_is_url_safe():
    """Raw state uses URL-safe characters (no + or /)."""
    state = generate_raw_state()
    assert "+" not in state
    assert "/" not in state


def test_generate_raw_state_is_unique():
    """Two independent state generations produce different values."""
    states = {generate_raw_state() for _ in range(100)}
    assert len(states) == 100, "Duplicate state generated — entropy failure."


def test_generate_raw_state_has_sufficient_length():
    """secrets.token_urlsafe(32) produces at least 43 characters."""
    state = generate_raw_state()
    # base64url of 32 bytes = ceil(32*4/3) = 43 chars
    assert len(state) >= 43


# ===========================================================================
# 2. State hashing
# ===========================================================================

def test_hash_state_returns_hex_sha256():
    """hash_state returns a lowercase hex SHA-256 digest."""
    raw = "test_raw_state_value"
    digest = hash_state(raw)
    expected = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    assert digest == expected
    assert len(digest) == 64


def test_hash_state_is_deterministic():
    """Same raw state always produces the same hash."""
    raw = generate_raw_state()
    assert hash_state(raw) == hash_state(raw)


def test_hash_state_different_inputs_different_outputs():
    """Different raw states produce different hashes."""
    raw_a = generate_raw_state()
    raw_b = generate_raw_state()
    assert raw_a != raw_b
    assert hash_state(raw_a) != hash_state(raw_b)


def test_raw_state_not_in_hash():
    """The raw state must not appear in its own hash."""
    raw = generate_raw_state()
    digest = hash_state(raw)
    assert raw not in digest


# ===========================================================================
# 3. PKCE verifier generation — no database
# ===========================================================================

def test_generate_pkce_verifier_is_non_empty():
    """PKCE verifier is a non-empty string."""
    verifier = generate_pkce_verifier()
    assert isinstance(verifier, str)
    assert len(verifier) > 0


def test_generate_pkce_verifier_meets_rfc7636_length():
    """PKCE verifier must be between 43 and 128 characters (RFC 7636 §4.1)."""
    verifier = generate_pkce_verifier()
    assert 43 <= len(verifier) <= 128


def test_generate_pkce_verifier_is_unique():
    """Two independent verifier generations produce different values."""
    verifiers = {generate_pkce_verifier() for _ in range(100)}
    assert len(verifiers) == 100, "Duplicate PKCE verifier — entropy failure."


def test_generate_pkce_verifier_is_url_safe():
    """PKCE verifier uses URL-safe characters."""
    verifier = generate_pkce_verifier()
    assert "+" not in verifier
    assert "/" not in verifier


# ===========================================================================
# 4–7. PKCE verifier encryption (no database; uses real crypto utility)
# ===========================================================================

def test_pkce_verifier_encrypts_and_decrypts():
    """Encrypt a verifier, then decrypt it and get the same value back."""
    from app.core.crypto import encrypt_pkce_verifier, decrypt_pkce_verifier
    verifier = generate_pkce_verifier()
    ciphertext = encrypt_pkce_verifier(verifier)
    recovered = decrypt_pkce_verifier(ciphertext)
    assert recovered == verifier


def test_pkce_verifier_ciphertext_is_bytes():
    """Encrypted verifier is bytes, suitable for BYTEA storage."""
    from app.core.crypto import encrypt_pkce_verifier
    verifier = generate_pkce_verifier()
    ciphertext = encrypt_pkce_verifier(verifier)
    assert isinstance(ciphertext, bytes)


def test_pkce_verifier_plaintext_not_in_ciphertext():
    """Plaintext verifier must not appear verbatim in the ciphertext."""
    from app.core.crypto import encrypt_pkce_verifier
    verifier = generate_pkce_verifier()
    ciphertext = encrypt_pkce_verifier(verifier)
    assert verifier.encode("utf-8") not in ciphertext


def test_pkce_verifier_different_calls_produce_different_ciphertext():
    """Fernet uses random IV: same plaintext → different ciphertext each call."""
    from app.core.crypto import encrypt_pkce_verifier
    verifier = generate_pkce_verifier()
    ct_a = encrypt_pkce_verifier(verifier)
    ct_b = encrypt_pkce_verifier(verifier)
    assert ct_a != ct_b


# ===========================================================================
# 8–9. create_pending_state — mocked AsyncSession
# ===========================================================================

@pytest.mark.asyncio
async def test_create_pending_state_inserts_correct_fields():
    """
    create_pending_state inserts a state row with:
      - developer_id matching the input
      - a non-empty state_hash (SHA-256 hex)
      - expires_at in the future
      - encrypted code_verifier_enc (bytes)
    """
    developer_id = uuid.uuid4()
    session = _make_mock_session()

    async def mock_refresh(instance):
        instance.id = uuid.uuid4()

    session.refresh.side_effect = mock_refresh

    result = await create_pending_state(session, developer_id)

    # session.add called once with a GitHubConnectionState
    session.add.assert_called_once()
    added_row = session.add.call_args[0][0]

    from app.models.github_connection_state import GitHubConnectionState
    assert isinstance(added_row, GitHubConnectionState)
    assert added_row.developer_id == developer_id

    # state_hash must be a 64-char hex string (SHA-256)
    assert isinstance(added_row.state_hash, str)
    assert len(added_row.state_hash) == 64

    # expires_at must be in the future
    now = datetime.now(timezone.utc)
    assert added_row.expires_at > now

    # code_verifier_enc must be bytes (encrypted)
    assert isinstance(added_row.code_verifier_enc, bytes)
    assert len(added_row.code_verifier_enc) > 0

    # commit must have been awaited
    session.commit.assert_awaited_once()

    # result must be a PendingOAuthState with a non-empty raw_state
    assert isinstance(result, PendingOAuthState)
    assert isinstance(result.raw_state, str)
    assert len(result.raw_state) > 0
    # code_verifier is intentionally absent from PendingOAuthState —
    # GitHub's /installations/new does not support PKCE binding.
    assert not hasattr(result, "code_verifier")


@pytest.mark.asyncio
async def test_create_pending_state_raw_state_not_stored():
    """
    The persisted state_hash must differ from the raw_state —
    confirming raw state is hashed before persistence.
    """
    developer_id = uuid.uuid4()
    session = _make_mock_session()

    async def mock_refresh(instance):
        instance.id = uuid.uuid4()

    session.refresh.side_effect = mock_refresh

    result = await create_pending_state(session, developer_id)
    added_row = session.add.call_args[0][0]

    assert added_row.state_hash != result.raw_state


@pytest.mark.asyncio
async def test_create_pending_state_hash_matches_sha256_of_raw_state():
    """
    hash_state(raw_state) must equal what was stored in state_hash.
    """
    developer_id = uuid.uuid4()
    session = _make_mock_session()

    async def mock_refresh(instance):
        instance.id = uuid.uuid4()

    session.refresh.side_effect = mock_refresh

    result = await create_pending_state(session, developer_id)
    added_row = session.add.call_args[0][0]

    expected_hash = hash_state(result.raw_state)
    assert added_row.state_hash == expected_hash


@pytest.mark.asyncio
async def test_create_pending_state_ttl_from_config():
    """
    expires_at must be approximately NOW() + GITHUB_STATE_TTL_SECONDS.
    """
    developer_id = uuid.uuid4()
    session = _make_mock_session()

    async def mock_refresh(instance):
        instance.id = uuid.uuid4()

    session.refresh.side_effect = mock_refresh

    before = datetime.now(timezone.utc)
    result = await create_pending_state(session, developer_id)
    after = datetime.now(timezone.utc)

    # TTL is 600 seconds from env; allow 5s tolerance
    lower = before + timedelta(seconds=595)
    upper = after + timedelta(seconds=605)
    assert lower <= result.expires_at <= upper


@pytest.mark.asyncio
async def test_create_pending_state_plaintext_verifier_not_persisted():
    """
    The plaintext PKCE verifier must NOT appear verbatim in code_verifier_enc.
    """
    developer_id = uuid.uuid4()
    session = _make_mock_session()

    async def mock_refresh(instance):
        instance.id = uuid.uuid4()

    session.refresh.side_effect = mock_refresh

    # Intercept the verifier before encryption by patching generate_pkce_verifier
    captured_verifier = []

    original_gen = generate_pkce_verifier

    def capturing_gen():
        v = original_gen()
        captured_verifier.append(v)
        return v

    with patch(
        "app.services.github.state.generate_pkce_verifier",
        side_effect=capturing_gen,
    ):
        await create_pending_state(session, developer_id)

    added_row = session.add.call_args[0][0]
    assert len(captured_verifier) == 1
    plaintext = captured_verifier[0]
    # Plaintext must NOT appear verbatim in the stored ciphertext
    assert plaintext.encode("utf-8") not in added_row.code_verifier_enc


@pytest.mark.asyncio
async def test_create_pending_state_db_error_raises_persistence_error():
    """
    SQLAlchemy error during commit raises GitHubStatePersistenceError.
    """
    from sqlalchemy.exc import SQLAlchemyError

    developer_id = uuid.uuid4()
    session = _make_mock_session()
    session.commit.side_effect = SQLAlchemyError("db error")

    with pytest.raises(GitHubStatePersistenceError):
        await create_pending_state(session, developer_id)

    session.rollback.assert_awaited_once()


# ===========================================================================
# 10–17. claim_state — mocked AsyncSession
# ===========================================================================

def _make_mock_row(
    state_id: uuid.UUID,
    developer_id: uuid.UUID,
    code_verifier_enc: Optional[bytes],
    expires_at: Optional[datetime] = None,
    used_at: Optional[datetime] = None,
):
    """Build a fake row tuple as returned by SQLAlchemy result.fetchone()."""
    expires_at = expires_at or datetime.now(timezone.utc) + timedelta(seconds=300)
    row = MagicMock()
    row.__getitem__ = MagicMock(
        side_effect=lambda i: [state_id, developer_id, code_verifier_enc, expires_at, used_at][i]
    )
    return row


@pytest.mark.asyncio
async def test_claim_state_success():
    """
    A valid, unexpired, unused state is claimed successfully.
    Returns GitHubOAuthStateContext with correct developer_id and verifier.
    """
    from app.core.crypto import encrypt_pkce_verifier

    developer_id = uuid.uuid4()
    state_id = uuid.uuid4()
    raw_state = generate_raw_state()
    plaintext_verifier = generate_pkce_verifier()
    ciphertext = encrypt_pkce_verifier(plaintext_verifier)

    mock_row = _make_mock_row(state_id, developer_id, ciphertext)

    session = _make_mock_session()
    claim_result = MagicMock()
    claim_result.fetchone.return_value = mock_row
    session.execute.return_value = claim_result

    context = await claim_state(session, raw_state)

    assert isinstance(context, GitHubOAuthStateContext)
    assert context.developer_id == developer_id
    assert context.code_verifier == plaintext_verifier
    assert context.state_id == state_id

    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_claim_state_sets_used_at_atomically():
    """
    The claim uses a single UPDATE ... RETURNING (one execute call for the update).
    It must NOT use SELECT then UPDATE.
    """
    from app.core.crypto import encrypt_pkce_verifier

    developer_id = uuid.uuid4()
    state_id = uuid.uuid4()
    raw_state = generate_raw_state()
    ciphertext = encrypt_pkce_verifier(generate_pkce_verifier())

    mock_row = _make_mock_row(state_id, developer_id, ciphertext)
    session = _make_mock_session()
    claim_result = MagicMock()
    claim_result.fetchone.return_value = mock_row
    session.execute.return_value = claim_result

    await claim_state(session, raw_state)

    # Must issue exactly ONE execute for the atomic UPDATE (the success path
    # does not need the secondary existence check).
    assert session.execute.call_count == 1
    sql_called = str(session.execute.call_args_list[0][0][0])
    assert "UPDATE" in sql_called.upper()


@pytest.mark.asyncio
async def test_claim_state_unknown_state_raises_not_found():
    """
    When no row exists for the given state hash, raise GitHubStateNotFoundError.
    """
    raw_state = generate_raw_state()
    session = _make_mock_session()

    # First execute (UPDATE) returns no row
    update_result = MagicMock()
    update_result.fetchone.return_value = None

    # Second execute (SELECT check) also returns no row
    check_result = MagicMock()
    check_result.fetchone.return_value = None

    session.execute.side_effect = [update_result, check_result]

    with pytest.raises(GitHubStateNotFoundError):
        await claim_state(session, raw_state)


@pytest.mark.asyncio
async def test_claim_state_expired_or_used_raises_expired_error():
    """
    When a row exists but is expired or already used,
    raise GitHubStateExpiredError.
    """
    raw_state = generate_raw_state()
    state_id = uuid.uuid4()
    session = _make_mock_session()

    # First execute (UPDATE) returns no row — row failed WHERE clause
    update_result = MagicMock()
    update_result.fetchone.return_value = None

    # Second execute (SELECT check) finds the existing row
    existing_row = MagicMock()
    existing_row.__getitem__ = MagicMock(side_effect=lambda i: [state_id][i])
    check_result = MagicMock()
    check_result.fetchone.return_value = existing_row

    session.execute.side_effect = [update_result, check_result]

    with pytest.raises(GitHubStateExpiredError):
        await claim_state(session, raw_state)


@pytest.mark.asyncio
async def test_claim_state_wrong_state_raises_not_found():
    """
    A completely wrong (invented) raw state raises GitHubStateNotFoundError.
    """
    raw_state = "THIS_IS_A_COMPLETELY_WRONG_STATE_VALUE"
    session = _make_mock_session()

    update_result = MagicMock()
    update_result.fetchone.return_value = None
    check_result = MagicMock()
    check_result.fetchone.return_value = None
    session.execute.side_effect = [update_result, check_result]

    with pytest.raises(GitHubStateNotFoundError):
        await claim_state(session, raw_state)


@pytest.mark.asyncio
async def test_claim_state_second_claim_fails():
    """
    Simulates a second claim attempt on an already-used state.
    The first claim succeeds (UPDATE matched); second finds the row
    but the WHERE clause excludes it (used_at IS NOT NULL) → GitHubStateExpiredError.
    """
    from app.core.crypto import encrypt_pkce_verifier

    developer_id = uuid.uuid4()
    state_id = uuid.uuid4()
    raw_state = generate_raw_state()
    ciphertext = encrypt_pkce_verifier(generate_pkce_verifier())

    # --- First claim ---
    session1 = _make_mock_session()
    row = _make_mock_row(state_id, developer_id, ciphertext)
    first_result = MagicMock()
    first_result.fetchone.return_value = row
    session1.execute.return_value = first_result

    await claim_state(session1, raw_state)

    # --- Second claim: UPDATE returns nothing; SELECT finds the (used) row ---
    session2 = _make_mock_session()

    update_result = MagicMock()
    update_result.fetchone.return_value = None

    existing_row = MagicMock()
    existing_row.__getitem__ = MagicMock(side_effect=lambda i: [state_id][i])
    check_result = MagicMock()
    check_result.fetchone.return_value = existing_row

    session2.execute.side_effect = [update_result, check_result]

    with pytest.raises(GitHubStateExpiredError):
        await claim_state(session2, raw_state)


@pytest.mark.asyncio
async def test_claim_state_corrupted_verifier_raises_decryption_error():
    """
    If the stored code_verifier_enc is corrupted / tampered with,
    raise GitHubStateDecryptionError.
    """
    developer_id = uuid.uuid4()
    state_id = uuid.uuid4()
    raw_state = generate_raw_state()

    # Corrupted ciphertext
    bad_ciphertext = b"totally_invalid_fernet_ciphertext"

    session = _make_mock_session()
    row = _make_mock_row(state_id, developer_id, bad_ciphertext)
    result = MagicMock()
    result.fetchone.return_value = row
    session.execute.return_value = result

    with pytest.raises(GitHubStateDecryptionError):
        await claim_state(session, raw_state)


@pytest.mark.asyncio
async def test_claim_state_missing_verifier_raises_decryption_error():
    """
    If code_verifier_enc is None (missing), raise GitHubStateDecryptionError.
    """
    developer_id = uuid.uuid4()
    state_id = uuid.uuid4()
    raw_state = generate_raw_state()

    session = _make_mock_session()
    row = _make_mock_row(state_id, developer_id, None)
    result = MagicMock()
    result.fetchone.return_value = row
    session.execute.return_value = result

    with pytest.raises(GitHubStateDecryptionError):
        await claim_state(session, raw_state)


@pytest.mark.asyncio
async def test_claim_state_decrypted_verifier_equals_original():
    """
    After a successful claim, context.code_verifier equals the original
    plaintext verifier used during create_pending_state.
    """
    from app.core.crypto import encrypt_pkce_verifier

    developer_id = uuid.uuid4()
    state_id = uuid.uuid4()
    raw_state = generate_raw_state()
    plaintext_verifier = generate_pkce_verifier()
    ciphertext = encrypt_pkce_verifier(plaintext_verifier)

    session = _make_mock_session()
    row = _make_mock_row(state_id, developer_id, ciphertext)
    result = MagicMock()
    result.fetchone.return_value = row
    session.execute.return_value = result

    context = await claim_state(session, raw_state)
    assert context.code_verifier == plaintext_verifier


@pytest.mark.asyncio
async def test_claim_state_db_error_during_commit_raises_persistence_error():
    """
    SQLAlchemy error during the final commit raises GitHubStatePersistenceError.
    """
    from app.core.crypto import encrypt_pkce_verifier
    from sqlalchemy.exc import SQLAlchemyError

    developer_id = uuid.uuid4()
    state_id = uuid.uuid4()
    raw_state = generate_raw_state()
    ciphertext = encrypt_pkce_verifier(generate_pkce_verifier())

    session = _make_mock_session()
    row = _make_mock_row(state_id, developer_id, ciphertext)
    result = MagicMock()
    result.fetchone.return_value = row
    session.execute.return_value = result
    session.commit.side_effect = SQLAlchemyError("commit failed")

    with pytest.raises(GitHubStatePersistenceError):
        await claim_state(session, raw_state)

    session.rollback.assert_awaited_once()


# ===========================================================================
# 18. Security: raw state and verifier must never appear in logs
# ===========================================================================

@pytest.mark.asyncio
async def test_no_raw_state_in_logs_on_create(caplog):
    """Raw state must not appear in any log output during state creation."""
    developer_id = uuid.uuid4()
    session = _make_mock_session()

    captured_raw_state: list[str] = []

    original_gen = generate_raw_state

    def capturing_gen():
        s = original_gen()
        captured_raw_state.append(s)
        return s

    with caplog.at_level(logging.DEBUG), patch(
        "app.services.github.state.generate_raw_state",
        side_effect=capturing_gen,
    ):
        async def mock_refresh(instance):
            instance.id = uuid.uuid4()

        session.refresh.side_effect = mock_refresh
        await create_pending_state(session, developer_id)

    assert len(captured_raw_state) == 1
    raw = captured_raw_state[0]
    for record in caplog.records:
        assert raw not in record.message


@pytest.mark.asyncio
async def test_no_raw_verifier_in_logs_on_create(caplog):
    """Plaintext PKCE verifier must not appear in any log output during creation."""
    developer_id = uuid.uuid4()
    session = _make_mock_session()

    captured_verifier: list[str] = []

    original_gen = generate_pkce_verifier

    def capturing_gen():
        v = original_gen()
        captured_verifier.append(v)
        return v

    with caplog.at_level(logging.DEBUG), patch(
        "app.services.github.state.generate_pkce_verifier",
        side_effect=capturing_gen,
    ):
        async def mock_refresh(instance):
            instance.id = uuid.uuid4()

        session.refresh.side_effect = mock_refresh
        await create_pending_state(session, developer_id)

    assert len(captured_verifier) == 1
    verifier = captured_verifier[0]
    for record in caplog.records:
        assert verifier not in record.message


@pytest.mark.asyncio
async def test_no_raw_state_in_exception_messages():
    """
    Raw state must not appear in exception messages raised during claim.
    """
    raw_state = "SENTINEL_RAW_STATE_VALUE_FOR_TESTING"
    session = _make_mock_session()

    update_result = MagicMock()
    update_result.fetchone.return_value = None
    check_result = MagicMock()
    check_result.fetchone.return_value = None
    session.execute.side_effect = [update_result, check_result]

    try:
        await claim_state(session, raw_state)
    except GitHubStateNotFoundError as exc:
        assert raw_state not in str(exc)
    else:
        pytest.fail("Expected GitHubStateNotFoundError not raised.")


# ===========================================================================
# 19. Concurrent claim (structural test)
# ===========================================================================

@pytest.mark.asyncio
async def test_concurrent_claim_only_one_succeeds():
    """
    Structural test: claim is an atomic UPDATE. The second session, which
    does not find a pending row (simulating the DB already having used_at set),
    raises GitHubStateExpiredError — confirming single-use semantics.
    """
    from app.core.crypto import encrypt_pkce_verifier

    developer_id = uuid.uuid4()
    state_id = uuid.uuid4()
    raw_state = generate_raw_state()
    ciphertext = encrypt_pkce_verifier(generate_pkce_verifier())

    # Session 1: wins the race — UPDATE returns the row
    session_winner = _make_mock_session()
    row = _make_mock_row(state_id, developer_id, ciphertext)
    win_result = MagicMock()
    win_result.fetchone.return_value = row
    session_winner.execute.return_value = win_result

    ctx = await claim_state(session_winner, raw_state)
    assert isinstance(ctx, GitHubOAuthStateContext)

    # Session 2: loses the race — UPDATE returns nothing; SELECT finds used row
    session_loser = _make_mock_session()
    lose_update = MagicMock()
    lose_update.fetchone.return_value = None
    used_row = MagicMock()
    used_row.__getitem__ = MagicMock(side_effect=lambda i: [state_id][i])
    lose_check = MagicMock()
    lose_check.fetchone.return_value = used_row
    session_loser.execute.side_effect = [lose_update, lose_check]

    with pytest.raises(GitHubStateExpiredError):
        await claim_state(session_loser, raw_state)
