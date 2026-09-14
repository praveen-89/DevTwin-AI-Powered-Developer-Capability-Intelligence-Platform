"""
DevTwin Backend — GitHub Exceptions
"""

class GitHubIntegrationError(Exception):
    """Base class for all GitHub integration errors."""
    pass


class GitHubConfigurationError(GitHubIntegrationError):
    """Raised when GitHub configuration is missing or invalid."""
    pass


class GitHubHTTPError(GitHubIntegrationError):
    """Raised when GitHub API returns an HTTP error."""
    pass


class GitHubOAuthError(GitHubIntegrationError):
    """Raised when OAuth token exchange fails."""
    pass


class GitHubResponseError(GitHubIntegrationError):
    """Raised when GitHub returns a malformed response."""
    pass


class GitHubRateLimitError(GitHubHTTPError):
    """Raised when GitHub rate limit is exceeded."""
    pass


class GitHubNetworkError(GitHubIntegrationError):
    """Raised for network or timeout issues communicating with GitHub."""
    pass
