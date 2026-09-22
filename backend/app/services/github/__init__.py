"""
DevTwin Backend — GitHub Service Layer
"""

from .auth import generate_app_jwt
from .client import GitHubClient
from .state import (
    generate_raw_state,
    hash_state,
    generate_pkce_verifier,
    create_pending_state,
    claim_state,
    PendingOAuthState,
    GitHubOAuthStateContext,
)
from .types import GitHubUser, GitHubInstallation, OAuthToken
from .exceptions import (
    GitHubIntegrationError,
    GitHubConfigurationError,
    GitHubHTTPError,
    GitHubOAuthError,
    GitHubResponseError,
    GitHubRateLimitError,
    GitHubNetworkError,
    GitHubStateError,
    GitHubStateNotFoundError,
    GitHubStateExpiredError,
    GitHubStatePersistenceError,
    GitHubStateDecryptionError,
)

__all__ = [
    "generate_app_jwt",
    "GitHubClient",
    # State lifecycle
    "generate_raw_state",
    "hash_state",
    "generate_pkce_verifier",
    "create_pending_state",
    "claim_state",
    "PendingOAuthState",
    "GitHubOAuthStateContext",
    # Types
    "GitHubUser",
    "GitHubInstallation",
    "OAuthToken",
    # Exceptions
    "GitHubIntegrationError",
    "GitHubConfigurationError",
    "GitHubHTTPError",
    "GitHubOAuthError",
    "GitHubResponseError",
    "GitHubRateLimitError",
    "GitHubNetworkError",
    "GitHubStateError",
    "GitHubStateNotFoundError",
    "GitHubStateExpiredError",
    "GitHubStatePersistenceError",
    "GitHubStateDecryptionError",
]
