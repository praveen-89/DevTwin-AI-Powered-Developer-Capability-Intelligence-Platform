"""
DevTwin Backend — GitHub Types
"""

from typing import Optional
from pydantic import BaseModel


class GitHubUser(BaseModel):
    """Normalized GitHub user data."""
    github_id: int
    username: str


class GitHubInstallation(BaseModel):
    """Normalized GitHub App installation data."""
    installation_id: int
    account_github_id: int
    account_login: Optional[str] = None


class OAuthToken(BaseModel):
    """Temporary GitHub user access token."""
    access_token: str
