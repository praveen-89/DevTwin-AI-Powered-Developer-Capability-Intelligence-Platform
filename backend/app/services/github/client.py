"""
DevTwin Backend — GitHub HTTP Client
"""

import logging
from typing import List
import httpx

from app.core.config import get_settings
from .exceptions import (
    GitHubConfigurationError,
    GitHubHTTPError,
    GitHubOAuthError,
    GitHubResponseError,
    GitHubRateLimitError,
    GitHubNetworkError,
)
from .types import GitHubUser, GitHubInstallation, OAuthToken

logger = logging.getLogger(__name__)


class GitHubClient:
    """
    Async HTTP client for interacting with GitHub API.
    Handles authentication, error parsing, and safe logging.
    """

    def __init__(self, timeout: float = 10.0):
        settings = get_settings()
        self.base_url = settings.GITHUB_API_BASE_URL.rstrip("/")
        # The OAuth endpoint is generally on github.com, not api.github.com
        # Using a fixed host to avoid caller-provided overrides.
        self.oauth_base_url = "https://github.com"
        self.timeout = timeout
        self.client_id = settings.GITHUB_CLIENT_ID
        self.client_secret = settings.GITHUB_CLIENT_SECRET
        self.redirect_uri = settings.GITHUB_REDIRECT_URL

    async def _request(
        self,
        method: str,
        url: str,
        token: str | None = None,
        data: dict | None = None,
        is_oauth: bool = False,
    ) -> httpx.Response:
        """
        Internal helper for making HTTP requests to GitHub safely.
        """
        headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        
        # Add API version header for normal requests (not OAuth token exchange)
        if not is_oauth:
            headers["X-GitHub-Api-Version"] = "2026-03-10"

        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        full_url = url
        if not url.startswith("http"):
            base = self.oauth_base_url if is_oauth else self.base_url
            full_url = f"{base}/{url.lstrip('/')}"

        # Safe logging: only log method and path, not the full URL or query strings
        logger.debug("GitHub %s request to %s", method, url)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if method == "POST":
                    # GitHub OAuth typically expects form data, but can accept JSON.
                    # We will use JSON if data is passed.
                    if is_oauth:
                        # Ensure we request JSON response from OAuth
                        headers["Accept"] = "application/json"
                    response = await client.post(full_url, json=data, headers=headers)
                else:
                    response = await client.get(full_url, headers=headers)

            if response.status_code == 429:
                raise GitHubRateLimitError("GitHub API rate limit exceeded.")
                
            response.raise_for_status()
            return response

        except httpx.HTTPStatusError as e:
            # We don't log the body which might contain sensitive data in some cases
            logger.error("GitHub HTTP error: %s on %s", e.response.status_code, url)
            if e.response.status_code == 401:
                raise GitHubHTTPError("GitHub authentication failed.") from e
            elif e.response.status_code == 403:
                raise GitHubHTTPError("GitHub forbidden access.") from e
            elif e.response.status_code == 404:
                raise GitHubHTTPError("GitHub resource not found.") from e
            raise GitHubHTTPError(f"GitHub API error: {e.response.status_code}") from e
            
        except httpx.RequestError as e:
            logger.error("Network error communicating with GitHub: %s", type(e).__name__)
            raise GitHubNetworkError("Failed to communicate with GitHub.") from e

    async def exchange_oauth_code(self, code: str, code_verifier: str) -> OAuthToken:
        """
        Exchanges an OAuth authorization code + PKCE verifier for an access token.
        """
        if not self.client_secret:
            raise GitHubConfigurationError("GitHub Client Secret is not configured.")

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code"
        }

        try:
            response = await self._request(
                "POST", "/login/oauth/access_token", data=data, is_oauth=True
            )
            payload = response.json()
        except ValueError as e:
            raise GitHubResponseError("Invalid JSON response from GitHub OAuth.") from e
        except GitHubHTTPError as e:
            raise GitHubOAuthError("Failed to exchange OAuth code.") from e

        if "error" in payload:
            logger.error("GitHub OAuth error returned.")
            raise GitHubOAuthError("GitHub returned an OAuth error.")

        access_token = payload.get("access_token")
        
        # Token type validation
        if not access_token or not isinstance(access_token, str):
            logger.error("Access token missing or invalid type in GitHub OAuth response.")
            raise GitHubOAuthError("Invalid OAuth response: missing or invalid access token.")

        return OAuthToken(access_token=access_token)

    async def get_authenticated_user(self, access_token: str) -> GitHubUser:
        """
        Gets the authenticated user's normalized information.
        """
        response = await self._request("GET", "/user", token=access_token)
        
        try:
            payload = response.json()
        except ValueError as e:
            raise GitHubResponseError("Invalid JSON response from GitHub /user.") from e
            
        github_id = payload.get("id")
        username = payload.get("login")
        
        if github_id is None or username is None:
            raise GitHubResponseError("Missing required fields in GitHub user response.")
            
        return GitHubUser(github_id=github_id, username=username)

    async def list_user_installations(self, access_token: str) -> List[GitHubInstallation]:
        """
        Lists GitHub App installations accessible to the authenticated user.
        """
        response = await self._request("GET", "/user/installations", token=access_token)
        
        try:
            payload = response.json()
        except ValueError as e:
            raise GitHubResponseError("Invalid JSON response from GitHub /user/installations.") from e
            
        installations_data = payload.get("installations", [])
        if not isinstance(installations_data, list):
            raise GitHubResponseError("Invalid installations format in GitHub response.")
            
        installations = []
        for inst in installations_data:
            inst_id = inst.get("id")
            account = inst.get("account", {})
            acc_id = account.get("id")
            acc_login = account.get("login")
            
            if inst_id is not None and acc_id is not None:
                installations.append(GitHubInstallation(
                    installation_id=inst_id,
                    account_github_id=acc_id,
                    account_login=acc_login
                ))
                
        return installations
