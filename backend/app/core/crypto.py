import logging
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class PKCECryptoError(Exception):
    """Base exception for PKCE cryptographic operations."""
    pass

class PKCEDecryptionError(PKCECryptoError):
    """Raised when PKCE decryption fails (tampered or invalid ciphertext)."""
    pass

class PKCEEncryptionError(PKCECryptoError):
    """Raised when PKCE encryption fails (invalid input)."""
    pass

def _get_fernet() -> Fernet:
    """Helper to instantiate Fernet with the current settings key."""
    settings = get_settings()
    # Pydantic already validated that this is a valid Fernet key
    return Fernet(settings.GITHUB_STATE_ENCRYPTION_KEY.encode("utf-8"))

def encrypt_pkce_verifier(verifier: str) -> bytes:
    """
    Encrypts a PKCE code_verifier using authenticated encryption.
    
    Args:
        verifier: The plaintext PKCE code verifier string.
        
    Returns:
        bytes: The ciphertext, suitable for BYTEA database storage.
        
    Raises:
        PKCEEncryptionError: If the verifier is empty or invalid.
    """
    if not verifier:
        raise PKCEEncryptionError("Cannot encrypt an empty verifier.")
    
    try:
        fernet = _get_fernet()
        # Fernet encrypt returns bytes
        return fernet.encrypt(verifier.encode("utf-8"))
    except Exception as e:
        logger.error("Failed to encrypt PKCE verifier.")
        raise PKCEEncryptionError("Encryption failed.") from e

def decrypt_pkce_verifier(ciphertext: bytes) -> str:
    """
    Decrypts a PKCE code_verifier.
    
    Args:
        ciphertext: The encrypted verifier bytes.
        
    Returns:
        str: The original plaintext verifier.
        
    Raises:
        PKCEDecryptionError: If the ciphertext is invalid or tampered with.
    """
    if not ciphertext:
        raise PKCEDecryptionError("Cannot decrypt empty ciphertext.")
    
    try:
        fernet = _get_fernet()
        decrypted_bytes = fernet.decrypt(ciphertext)
        return decrypted_bytes.decode("utf-8")
    except InvalidToken as e:
        logger.error("Failed to decrypt PKCE verifier: Invalid or tampered token.")
        raise PKCEDecryptionError("Decryption failed: Invalid token.") from e
    except UnicodeDecodeError as e:
        logger.error("Failed to decode decrypted PKCE verifier to UTF-8.")
        raise PKCEDecryptionError("Decryption failed: Invalid UTF-8.") from e
    except Exception as e:
        logger.error("Unexpected error during PKCE verifier decryption.")
        raise PKCEDecryptionError("Decryption failed.") from e
