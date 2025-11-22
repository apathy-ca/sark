"""Base authentication provider interface."""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from pydantic import BaseModel
import structlog

logger = structlog.get_logger()


class AuthProviderConfig(BaseModel):
    """Base configuration for authentication providers."""

    enabled: bool = True
    name: str
    timeout_seconds: int = 30


class AuthResult(BaseModel):
    """Result of an authentication attempt."""

    success: bool
    user_id: UUID | None = None
    email: str | None = None
    display_name: str | None = None
    groups: list[str] = []
    metadata: dict[str, Any] = {}
    error_message: str | None = None


class AuthProvider(ABC):
    """Abstract base class for authentication providers."""

    def __init__(self, config: AuthProviderConfig):
        """
        Initialize auth provider.

        Args:
            config: Provider configuration
        """
        self.config = config
        self.logger = logger.bind(provider=config.name)

    @abstractmethod
    async def authenticate(
        self,
        username: str,
        credential: str,
        **kwargs: Any,
    ) -> AuthResult:
        """
        Authenticate a user with credentials.

        Args:
            username: Username or email
            credential: Password, token, or other credential
            **kwargs: Additional provider-specific parameters

        Returns:
            AuthResult indicating success or failure
        """
        pass

    @abstractmethod
    async def validate_token(self, token: str) -> AuthResult:
        """
        Validate an authentication token.

        Args:
            token: Token to validate

        Returns:
            AuthResult with user information if valid
        """
        pass

    @abstractmethod
    async def get_user_info(self, user_id: UUID | str) -> dict[str, Any]:
        """
        Retrieve user information from provider.

        Args:
            user_id: User identifier

        Returns:
            Dictionary containing user information
        """
        pass

    async def health_check(self) -> bool:
        """
        Check if the auth provider is healthy and reachable.

        Returns:
            True if provider is healthy
        """
        try:
            # Default implementation - override in subclasses
            return self.config.enabled
        except Exception as e:
            self.logger.error("health_check_failed", error=str(e))
            return False
