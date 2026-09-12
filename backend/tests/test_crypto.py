"""
DevTwin Backend Tests — PKCE Crypto Utility

Tests for the authenticated encryption utility used to protect
the PKCE code_verifier at rest.
"""

import pytest
from cryptography.fernet import Fernet
from app.core.crypto import (
    encrypt_pkce_verifier,
    decrypt_pkce_verifier,
    PKCEEncryptionError,
    PKCEDecryptionError,
)


@pytest.fixture(autouse=True)
def setup_valid_crypto_env(monkeypatch):
    """Provide a valid configuration environment for crypto tests."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service")
    monkeypatch.setenv("SECRET_KEY", "secret")
    monkeypatch.setenv("GITHUB_APP_ID", "123")
    monkeypatch.setenv("GITHUB_APP_SLUG", "app")
    monkeypatch.setenv("GITHUB_CLIENT_ID", "client")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "secret")
    monkeypatch.setenv("GITHUB_PRIVATE_KEY", "pem")
    monkeypatch.setenv("GITHUB_REDIRECT_URL", "http://localhost:8000/callback")
    
    # Use a known valid Fernet key for tests
    test_key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setenv("GITHUB_STATE_ENCRYPTION_KEY", test_key)
    
    # Clear settings cache so new env is loaded
    from app.core.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_encrypt_decrypt_round_trip():
    """Encrypt/decrypt round trip succeeds."""
    verifier = "secure_random_verifier_string_123"
    ciphertext = encrypt_pkce_verifier(verifier)
    assert isinstance(ciphertext, bytes)
    
    decrypted = decrypt_pkce_verifier(ciphertext)
    assert decrypted == verifier


def test_empty_verifier_rejected():
    """Empty verifier is rejected for encryption and decryption."""
    with pytest.raises(PKCEEncryptionError):
        encrypt_pkce_verifier("")
        
    with pytest.raises(PKCEDecryptionError):
        decrypt_pkce_verifier(b"")


def test_different_encryptions_produce_different_ciphertext():
    """Different encryptions of the same verifier produce different ciphertext."""
    verifier = "same_verifier_string"
    ct1 = encrypt_pkce_verifier(verifier)
    ct2 = encrypt_pkce_verifier(verifier)
    assert ct1 != ct2
    assert decrypt_pkce_verifier(ct1) == verifier
    assert decrypt_pkce_verifier(ct2) == verifier


def test_tampered_ciphertext_fails():
    """Tampered ciphertext fails to decrypt."""
    verifier = "test_verifier"
    ciphertext = encrypt_pkce_verifier(verifier)
    
    # Tamper with the ciphertext
    tampered = bytearray(ciphertext)
    tampered[-1] ^= 0x01
    
    with pytest.raises(PKCEDecryptionError):
        decrypt_pkce_verifier(bytes(tampered))


def test_wrong_encryption_key_fails(monkeypatch):
    """Decrypting with the wrong key fails securely."""
    verifier = "test_verifier"
    ciphertext = encrypt_pkce_verifier(verifier)
    
    # Change the key in settings
    wrong_key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setenv("GITHUB_STATE_ENCRYPTION_KEY", wrong_key)
    
    # Clear cache to load new key
    from app.core.config import get_settings
    get_settings.cache_clear()
    
    with pytest.raises(PKCEDecryptionError):
        decrypt_pkce_verifier(ciphertext)


def test_unicode_utf8_verifier_round_trip():
    """Unicode/UTF-8 verifier round trip works."""
    verifier = "unicode_verifier_🌟_тест"
    ciphertext = encrypt_pkce_verifier(verifier)
    decrypted = decrypt_pkce_verifier(ciphertext)
    assert decrypted == verifier


def test_plaintext_not_in_ciphertext():
    """Plaintext verifier does not appear in ciphertext."""
    verifier = "SUPER_SECRET_VERIFIER_STRING"
    ciphertext = encrypt_pkce_verifier(verifier)
    # The plaintext bytes should not be in the ciphertext
    assert verifier.encode("utf-8") not in ciphertext


def test_crypto_utility_does_not_log_secrets(caplog):
    """Encryption utility does not log plaintext or keys on failure."""
    import logging
    caplog.set_level(logging.DEBUG)
    
    # Induce an error
    with pytest.raises(PKCEDecryptionError):
        decrypt_pkce_verifier(b"invalid_garbage_bytes")
        
    for record in caplog.records:
        assert "invalid_garbage_bytes" not in record.message
        assert "GITHUB_STATE_ENCRYPTION_KEY" not in record.message
