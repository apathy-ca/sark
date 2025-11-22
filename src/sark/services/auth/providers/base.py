"""Base authentication provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class UserInfo:
    """User information extracted from authentication provider."""

    user_id: str  # Unique user identifier
    email: str  # User email address
    name: str | None = None  # Full name
    given_name: str | None = None  # First name
    family_name: str | None = None  # Last name
    picture: str | None = None  # Profile picture URL
    groups: list[str] | None = None  # User groups/roles
    attributes: dict[str, Any] | None = None  # Additional provider-specific attributes


class AuthProvider(ABC):
    """Abstract base class for authentication providers.

    All authentication providers (OIDC, LDAP, SAML) must implement this interface.
    """

    @abstractmethod
    async def authenticate(self, credentials: dict[str, Any]) -> UserInfo | None:
        """Authenticate user with provided credentials.

        Args:
            credentials: Provider-specific credentials (e.g., token, username/password)

        Returns:
            UserInfo object if authentication successful, None otherwise
        """
        pass

    @abstractmethod
    async def validate_token(self, token: str) -> UserInfo | None:
        """Validate an authentication token and extract user information.

        Args:
            token: Authentication token to validate

        Returns:
            UserInfo object if token is valid, None otherwise
        """
        pass

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> dict[str, str] | None:
        """Refresh an authentication token.

        Args:
            refresh_token: Refresh token

        Returns:
            Dictionary with new access_token and refresh_token, or None if failed
        """
        pass

    @abstractmethod
    async def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """Get the authorization URL for initiating OAuth/OIDC flow.

        Args:
            state: State parameter for CSRF protection
            redirect_uri: Redirect URI after authentication

        Returns:
            Authorization URL
        """
        pass

    @abstractmethod
    async def handle_callback(
        self, code: str, state: str, redirect_uri: str
    ) -> dict[str, str] | None:
        """Handle OAuth/OIDC callback and exchange code for tokens.

        Args:
            code: Authorization code
            state: State parameter for validation
            redirect_uri: Redirect URI used in authorization request

        Returns:
            Dictionary with access_token, refresh_token, etc., or None if failed
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the authentication provider is reachable and healthy.

        Returns:
            True if provider is healthy, False otherwise
        """
        pass
