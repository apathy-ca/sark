"""
Authentication strategies for HTTP adapter.

This module implements various HTTP authentication methods:
- No Auth (public APIs)
- Basic Authentication
- Bearer Token
- OAuth2 (client credentials, authorization code)
- API Key (header, query parameter)

Version: 2.0.0
Engineer: ENGINEER-2
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
import base64
import structlog
import httpx

from sark.adapters.exceptions import AuthenticationError

logger = structlog.get_logger(__name__)


class AuthStrategy(ABC):
    """
    Abstract base class for HTTP authentication strategies.

    Each strategy knows how to:
    1. Add authentication headers/parameters to requests
    2. Refresh credentials when needed
    3. Validate credential configuration
    """

    @abstractmethod
    def apply(self, request: httpx.Request) -> None:
        """
        Apply authentication to an HTTP request.

        Args:
            request: The HTTP request to authenticate
        """
        pass

    @abstractmethod
    async def refresh(self) -> None:
        """
        Refresh authentication credentials if needed.

        Raises:
            AuthenticationError: If refresh fails
        """
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate authentication configuration.

        Args:
            config: Configuration dictionary

        Returns:
            True if valid

        Raises:
            AuthenticationError: If configuration is invalid
        """
        pass


class NoAuthStrategy(AuthStrategy):
    """No authentication - for public APIs."""

    def apply(self, request: httpx.Request) -> None:
        """No authentication needed."""
        pass

    async def refresh(self) -> None:
        """No credentials to refresh."""
        pass

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """No configuration needed."""
        return True


class BasicAuthStrategy(AuthStrategy):
    """
    HTTP Basic Authentication.

    Encodes username:password in Base64 and sends as Authorization header.
    """

    def __init__(self, username: str, password: str):
        """
        Initialize Basic Auth strategy.

        Args:
            username: Username
            password: Password
        """
        self.username = username
        self.password = password

    def apply(self, request: httpx.Request) -> None:
        """Add Basic Auth header to request."""
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        request.headers["Authorization"] = f"Basic {encoded}"

    async def refresh(self) -> None:
        """Basic auth doesn't need refresh."""
        pass

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate Basic Auth configuration."""
        if "username" not in config or "password" not in config:
            raise AuthenticationError(
                "Basic auth requires 'username' and 'password'",
                details={"config_keys": list(config.keys())}
            )
        return True


class BearerAuthStrategy(AuthStrategy):
    """
    Bearer Token Authentication.

    Sends token in Authorization: Bearer <token> header.
    Supports optional token refresh.
    """

    def __init__(
        self,
        token: str,
        refresh_url: Optional[str] = None,
        refresh_token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        """
        Initialize Bearer Auth strategy.

        Args:
            token: Bearer token
            refresh_url: URL to refresh token (optional)
            refresh_token: Refresh token (optional)
            client_id: Client ID for refresh (optional)
            client_secret: Client secret for refresh (optional)
        """
        self.token = token
        self.refresh_url = refresh_url
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_expiry: Optional[datetime] = None

    def apply(self, request: httpx.Request) -> None:
        """Add Bearer token to request."""
        request.headers["Authorization"] = f"Bearer {self.token}"

    async def refresh(self) -> None:
        """
        Refresh the bearer token if refresh_url is configured.

        Raises:
            AuthenticationError: If refresh fails
        """
        if not self.refresh_url or not self.refresh_token:
            logger.debug("Bearer token refresh not configured, skipping")
            return

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.refresh_url,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": self.refresh_token,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    }
                )
                response.raise_for_status()

                data = response.json()
                self.token = data["access_token"]

                # Update refresh token if provided
                if "refresh_token" in data:
                    self.refresh_token = data["refresh_token"]

                # Set expiry time
                if "expires_in" in data:
                    self.token_expiry = datetime.utcnow() + timedelta(seconds=data["expires_in"])

                logger.info("Bearer token refreshed successfully")

        except Exception as e:
            raise AuthenticationError(
                f"Failed to refresh bearer token: {str(e)}",
                details={"refresh_url": self.refresh_url}
            )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate Bearer Auth configuration."""
        if "token" not in config:
            raise AuthenticationError(
                "Bearer auth requires 'token'",
                details={"config_keys": list(config.keys())}
            )
        return True


class OAuth2Strategy(AuthStrategy):
    """
    OAuth2 Authentication.

    Supports multiple grant types:
    - Client Credentials
    - Authorization Code (with refresh)
    - Password Grant
    """

    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        grant_type: str = "client_credentials",
        scope: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        Initialize OAuth2 strategy.

        Args:
            token_url: OAuth2 token endpoint
            client_id: Client ID
            client_secret: Client secret
            grant_type: Grant type (client_credentials, password, etc.)
            scope: OAuth2 scope (optional)
            username: Username for password grant (optional)
            password: Password for password grant (optional)
        """
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.grant_type = grant_type
        self.scope = scope
        self.username = username
        self.password = password
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None

    def apply(self, request: httpx.Request) -> None:
        """Add OAuth2 token to request."""
        if not self.access_token:
            raise AuthenticationError(
                "OAuth2 token not available. Call refresh() first.",
                details={"grant_type": self.grant_type}
            )
        request.headers["Authorization"] = f"Bearer {self.access_token}"

    async def refresh(self) -> None:
        """
        Obtain or refresh OAuth2 token.

        Raises:
            AuthenticationError: If token request fails
        """
        try:
            data: Dict[str, Any] = {
                "grant_type": self.grant_type,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }

            if self.scope:
                data["scope"] = self.scope

            if self.grant_type == "password":
                if not self.username or not self.password:
                    raise AuthenticationError(
                        "Password grant requires username and password",
                        details={"grant_type": "password"}
                    )
                data["username"] = self.username
                data["password"] = self.password
            elif self.grant_type == "refresh_token":
                if not self.refresh_token:
                    raise AuthenticationError(
                        "Refresh token not available",
                        details={"grant_type": "refresh_token"}
                    )
                data["refresh_token"] = self.refresh_token

            async with httpx.AsyncClient() as client:
                response = await client.post(self.token_url, data=data)
                response.raise_for_status()

                token_data = response.json()
                self.access_token = token_data["access_token"]

                if "refresh_token" in token_data:
                    self.refresh_token = token_data["refresh_token"]

                if "expires_in" in token_data:
                    self.token_expiry = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])

                logger.info(
                    "OAuth2 token obtained",
                    grant_type=self.grant_type,
                    expires_in=token_data.get("expires_in")
                )

        except httpx.HTTPStatusError as e:
            raise AuthenticationError(
                f"OAuth2 token request failed: {e.response.status_code}",
                details={
                    "token_url": self.token_url,
                    "grant_type": self.grant_type,
                    "response": e.response.text,
                }
            )
        except Exception as e:
            raise AuthenticationError(
                f"OAuth2 authentication failed: {str(e)}",
                details={"token_url": self.token_url, "grant_type": self.grant_type}
            )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate OAuth2 configuration."""
        required = ["token_url", "client_id", "client_secret"]
        missing = [key for key in required if key not in config]

        if missing:
            raise AuthenticationError(
                f"OAuth2 auth requires: {', '.join(required)}",
                details={"missing_keys": missing, "provided_keys": list(config.keys())}
            )

        if config.get("grant_type") == "password":
            if "username" not in config or "password" not in config:
                raise AuthenticationError(
                    "Password grant requires 'username' and 'password'",
                    details={"grant_type": "password"}
                )

        return True


class APIKeyStrategy(AuthStrategy):
    """
    API Key Authentication.

    Supports API keys in:
    - Headers (most common)
    - Query parameters
    - Cookies
    """

    def __init__(
        self,
        api_key: str,
        location: str = "header",
        key_name: str = "X-API-Key",
    ):
        """
        Initialize API Key strategy.

        Args:
            api_key: The API key
            location: Where to send the key (header, query, cookie)
            key_name: Name of the header/parameter/cookie
        """
        self.api_key = api_key
        self.location = location.lower()
        self.key_name = key_name

        if self.location not in ("header", "query", "cookie"):
            raise AuthenticationError(
                f"Invalid API key location: {location}",
                details={"valid_locations": ["header", "query", "cookie"]}
            )

    def apply(self, request: httpx.Request) -> None:
        """Add API key to request."""
        if self.location == "header":
            request.headers[self.key_name] = self.api_key
        elif self.location == "query":
            # Add to query parameters
            url = str(request.url)
            separator = "&" if "?" in url else "?"
            request.url = httpx.URL(f"{url}{separator}{self.key_name}={self.api_key}")
        elif self.location == "cookie":
            request.headers["Cookie"] = f"{self.key_name}={self.api_key}"

    async def refresh(self) -> None:
        """API keys don't need refresh."""
        pass

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate API Key configuration."""
        if "api_key" not in config:
            raise AuthenticationError(
                "API key auth requires 'api_key'",
                details={"config_keys": list(config.keys())}
            )

        location = config.get("location", "header")
        if location not in ("header", "query", "cookie"):
            raise AuthenticationError(
                f"Invalid API key location: {location}",
                details={"valid_locations": ["header", "query", "cookie"]}
            )

        return True


def create_auth_strategy(auth_config: Dict[str, Any]) -> AuthStrategy:
    """
    Factory function to create authentication strategy from configuration.

    Args:
        auth_config: Authentication configuration dictionary

    Returns:
        Appropriate AuthStrategy instance

    Raises:
        AuthenticationError: If auth type is unsupported or config is invalid

    Example configurations:
        # No auth
        {"type": "none"}

        # Basic auth
        {"type": "basic", "username": "user", "password": "pass"}

        # Bearer token
        {"type": "bearer", "token": "abc123"}

        # OAuth2
        {
            "type": "oauth2",
            "token_url": "https://auth.example.com/token",
            "client_id": "client",
            "client_secret": "secret",
            "grant_type": "client_credentials"
        }

        # API Key
        {"type": "api_key", "api_key": "key123", "location": "header", "key_name": "X-API-Key"}
    """
    auth_type = auth_config.get("type", "none").lower()

    if auth_type == "none":
        strategy = NoAuthStrategy()
    elif auth_type == "basic":
        strategy = BasicAuthStrategy(
            username=auth_config["username"],
            password=auth_config["password"]
        )
    elif auth_type == "bearer":
        strategy = BearerAuthStrategy(
            token=auth_config["token"],
            refresh_url=auth_config.get("refresh_url"),
            refresh_token=auth_config.get("refresh_token"),
            client_id=auth_config.get("client_id"),
            client_secret=auth_config.get("client_secret"),
        )
    elif auth_type == "oauth2":
        strategy = OAuth2Strategy(
            token_url=auth_config["token_url"],
            client_id=auth_config["client_id"],
            client_secret=auth_config["client_secret"],
            grant_type=auth_config.get("grant_type", "client_credentials"),
            scope=auth_config.get("scope"),
            username=auth_config.get("username"),
            password=auth_config.get("password"),
        )
    elif auth_type == "api_key":
        strategy = APIKeyStrategy(
            api_key=auth_config["api_key"],
            location=auth_config.get("location", "header"),
            key_name=auth_config.get("key_name", "X-API-Key"),
        )
    else:
        raise AuthenticationError(
            f"Unsupported authentication type: {auth_type}",
            details={
                "supported_types": ["none", "basic", "bearer", "oauth2", "api_key"]
            }
        )

    # Validate configuration
    strategy.validate_config(auth_config)

    return strategy


__all__ = [
    "AuthStrategy",
    "NoAuthStrategy",
    "BasicAuthStrategy",
    "BearerAuthStrategy",
    "OAuth2Strategy",
    "APIKeyStrategy",
    "create_auth_strategy",
]
