"""
DevTwin Backend Tests — GitHub HTTP Client Service
"""

import pytest
import logging
from unittest.mock import AsyncMock, patch
import httpx
from app.services.github.client import GitHubClient
from app.services.github.exceptions import (
    GitHubConfigurationError,
    GitHubOAuthError,
    GitHubResponseError,
    GitHubHTTPError,
)


@pytest.fixture(autouse=True)
def setup_github_client_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service")
    monkeypatch.setenv("SECRET_KEY", "secret")
    
    monkeypatch.setenv("GITHUB_APP_ID", "123")
    monkeypatch.setenv("GITHUB_APP_SLUG", "app")
    monkeypatch.setenv("GITHUB_CLIENT_ID", "TEST_CLIENT_ID")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "TEST_CLIENT_SECRET")
    monkeypatch.setenv("GITHUB_PRIVATE_KEY", "pem")
    monkeypatch.setenv("GITHUB_REDIRECT_URL", "http://localhost/cb")
    monkeypatch.setenv("GITHUB_STATE_ENCRYPTION_KEY", "N2F0d1VNb2h3Nnl4S3hZYmF0bzh1amV6dVpZcDJ2bXg=")
    
    from app.core.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
@patch("app.services.github.client.httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_exchange_oauth_code_success(mock_post):
    """Exchanges an OAuth authorization code successfully."""
    
    # Mock the HTTP response
    mock_request = httpx.Request("POST", "https://github.com/login/oauth/access_token")
    mock_response = httpx.Response(200, json={"access_token": "TEST_ACCESS_TOKEN", "token_type": "bearer"}, request=mock_request)
    mock_post.return_value = mock_response
    
    client = GitHubClient()
    token = await client.exchange_oauth_code("TEST_AUTH_CODE", "TEST_PKCE_VERIFIER")
    
    assert token.access_token == "TEST_ACCESS_TOKEN"
    
    # Ensure correct request payload
    mock_post.assert_called_once()
    kwargs = mock_post.call_args.kwargs
    assert kwargs["json"]["code"] == "TEST_AUTH_CODE"
    assert kwargs["json"]["code_verifier"] == "TEST_PKCE_VERIFIER"
    assert kwargs["json"]["client_id"] == "TEST_CLIENT_ID"
    assert kwargs["json"]["client_secret"] == "TEST_CLIENT_SECRET"
    assert kwargs["json"]["redirect_uri"] == "http://localhost/cb"
    assert kwargs["headers"]["Accept"] == "application/json"


@pytest.mark.asyncio
@patch("app.services.github.client.httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_exchange_oauth_code_github_error(mock_post):
    """Fails safely when GitHub returns an OAuth error payload."""
    mock_request = httpx.Request("POST", "https://github.com/login/oauth/access_token")
    mock_response = httpx.Response(200, json={"error": "bad_verification_code"}, request=mock_request)
    mock_post.return_value = mock_response
    
    client = GitHubClient()
    with pytest.raises(GitHubOAuthError):
        await client.exchange_oauth_code("code", "verifier")


@pytest.mark.asyncio
@patch("app.services.github.client.httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_exchange_oauth_code_missing_token(mock_post):
    """Fails safely if access token is missing."""
    mock_request = httpx.Request("POST", "https://github.com/login/oauth/access_token")
    mock_response = httpx.Response(200, json={"some_other_field": "foo"}, request=mock_request)
    mock_post.return_value = mock_response
    
    client = GitHubClient()
    with pytest.raises(GitHubOAuthError):
        await client.exchange_oauth_code("code", "verifier")


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_token", [
    None, 123, ["token"], {"access_token": "token"}, ""
])
@patch("app.services.github.client.httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_exchange_oauth_code_invalid_token_types(mock_post, invalid_token):
    """Fails safely if access token is an invalid type or empty string."""
    mock_request = httpx.Request("POST", "https://github.com/login/oauth/access_token")
    mock_response = httpx.Response(200, json={"access_token": invalid_token}, request=mock_request)
    mock_post.return_value = mock_response
    
    client = GitHubClient()
    with pytest.raises(GitHubOAuthError):
        await client.exchange_oauth_code("code", "verifier")


@pytest.mark.asyncio
@patch("app.services.github.client.httpx.AsyncClient.get", new_callable=AsyncMock)
async def test_get_authenticated_user_success(mock_get):
    """Parses authenticated user successfully and sends API version."""
    mock_request = httpx.Request("GET", "https://api.github.com/user")
    mock_response = httpx.Response(200, json={"id": 89, "login": "praveen-89", "email": "test@test.com"}, request=mock_request)
    mock_get.return_value = mock_response
    
    client = GitHubClient()
    user = await client.get_authenticated_user("TEST_ACCESS_TOKEN")
    
    assert user.github_id == 89
    assert user.username == "praveen-89"
    
    # Assert header
    mock_get.assert_called_once()
    kwargs = mock_get.call_args.kwargs
    assert kwargs["headers"]["X-GitHub-Api-Version"] == "2026-03-10"


@pytest.mark.asyncio
@patch("app.services.github.client.httpx.AsyncClient.get", new_callable=AsyncMock)
async def test_get_authenticated_user_missing_fields(mock_get):
    """Fails if required fields are missing."""
    mock_request = httpx.Request("GET", "https://api.github.com/user")
    mock_response = httpx.Response(200, json={"id": 89}, request=mock_request)
    mock_get.return_value = mock_response
    
    client = GitHubClient()
    with pytest.raises(GitHubResponseError):
        await client.get_authenticated_user("TEST_ACCESS_TOKEN")


@pytest.mark.asyncio
@patch("app.services.github.client.httpx.AsyncClient.get", new_callable=AsyncMock)
async def test_list_user_installations_success(mock_get):
    """Parses user installations successfully and sends API version."""
    mock_request = httpx.Request("GET", "https://api.github.com/user/installations")
    mock_response = httpx.Response(200, json={
        "total_count": 1,
        "installations": [
            {
                "id": 1001,
                "account": {"id": 89, "login": "praveen-89"}
            }
        ]
    }, request=mock_request)
    mock_get.return_value = mock_response
    
    client = GitHubClient()
    installations = await client.list_user_installations("TEST_ACCESS_TOKEN")
    
    assert len(installations) == 1
    assert installations[0].installation_id == 1001
    assert installations[0].account_github_id == 89
    assert installations[0].account_login == "praveen-89"
    
    # Assert header
    mock_get.assert_called_once()
    kwargs = mock_get.call_args.kwargs
    assert kwargs["headers"]["X-GitHub-Api-Version"] == "2026-03-10"


@pytest.mark.asyncio
@patch("app.services.github.client.httpx.AsyncClient.get", new_callable=AsyncMock)
async def test_http_401_error(mock_get):
    """Validates HTTP 401 returns typed exception."""
    mock_response = httpx.Response(401, json={"message": "Bad credentials"}, request=httpx.Request("GET", "https://api.github.com/user"))
    mock_get.side_effect = httpx.HTTPStatusError("401", request=mock_response.request, response=mock_response)
    
    client = GitHubClient()
    with pytest.raises(GitHubHTTPError) as exc_info:
        await client.get_authenticated_user("TEST_ACCESS_TOKEN")
    assert "authentication failed" in str(exc_info.value).lower()


@pytest.mark.asyncio
@patch("app.services.github.client.httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_secrets_not_logged(mock_post, caplog):
    """Ensure secrets do not leak into logs upon HTTP failure."""
    caplog.set_level(logging.DEBUG)
    
    mock_response = httpx.Response(404, json={"message": "Not Found"}, request=httpx.Request("POST", "https://github.com/login/oauth/access_token"))
    mock_post.side_effect = httpx.HTTPStatusError("404", request=mock_response.request, response=mock_response)
    
    client = GitHubClient()
    with pytest.raises(GitHubOAuthError):
        await client.exchange_oauth_code("TEST_AUTH_CODE", "TEST_PKCE_VERIFIER")
        
    for record in caplog.records:
        assert "TEST_CLIENT_SECRET" not in record.message
        assert "TEST_AUTH_CODE" not in record.message
        assert "TEST_PKCE_VERIFIER" not in record.message
        assert "TEST_ACCESS_TOKEN" not in record.message

