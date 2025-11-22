"""OpenID Connect (OIDC) authentication provider."""

from typing import Any
from uuid import UUID

import httpx
from pydantic import Field

from sark.services.auth.providers.base import (
    AuthProvider,
    AuthProviderConfig,
    AuthResult,
)


class OIDCProviderConfig(AuthProviderConfig):
    """Configuration for OIDC authentication provider."""

    issuer_url: str
    client_id: str
    client_secret: str
    redirect_uri: str | None = None
    scopes: list[str] = Field(default_factory=lambda: ["openid", "profile", "email"])
    verify_ssl: bool = True


class OIDCProvider(AuthProvider):
    """OpenID Connect authentication provider."""

    def __init__(self, config: OIDCProviderConfig):
        """
        Initialize OIDC provider.

        Args:
            config: OIDC provider configuration
        """
        super().__init__(config)
        self.config: OIDCProviderConfig = config
        self._discovery_cache: dict[str, Any] | None = None

    async def _get_discovery_document(self) -> dict[str, Any]:
        """
        Fetch OIDC discovery document.

        Returns:
            Discovery document containing provider metadata
        """
        if self._discovery_cache:
            return self._discovery_cache

        discovery_url = f"{self.config.issuer_url}/.well-known/openid-configuration"

        async with httpx.AsyncClient(verify=self.config.verify_ssl) as client:
            response = await client.get(
                discovery_url,
                timeout=self.config.timeout_seconds,
            )
            response.raise_for_status()
            self._discovery_cache = response.json()

        self.logger.info("oidc_discovery_fetched", issuer=self.config.issuer_url)
        return self._discovery_cache

    async def authenticate(
        self,
        username: str,
        credential: str,
        **kwargs: Any,
    ) -> AuthResult:
        """
        Authenticate using OIDC (typically via authorization code flow).

        Args:
            username: Username (may not be used in OIDC flow)
            credential: Authorization code or access token
            **kwargs: Additional parameters (e.g., code_verifier for PKCE)

        Returns:
            AuthResult with user information
        """
        try:
            discovery = await self._get_discovery_document()
            token_endpoint = discovery["token_endpoint"]

            # Exchange authorization code for tokens
            async with httpx.AsyncClient(verify=self.config.verify_ssl) as client:
                response = await client.post(
                    token_endpoint,
                    data={
                        "grant_type": "authorization_code",
                        "code": credential,
                        "client_id": self.config.client_id,
                        "client_secret": self.config.client_secret,
                        "redirect_uri": self.config.redirect_uri,
                    },
                    timeout=self.config.timeout_seconds,
                )

                if response.status_code != 200:
                    return AuthResult(
                        success=False,
                        error_message=f"Token exchange failed: {response.text}",
                    )

                token_data = response.json()

            # Validate ID token and extract user info
            id_token = token_data.get("id_token")
            access_token = token_data.get("access_token")

            if not id_token:
                return AuthResult(
                    success=False,
                    error_message="No ID token in response",
                )

            # In production, validate the ID token signature
            # For now, we'll decode it without validation (mock)
            user_info = await self._get_userinfo(access_token)

            return AuthResult(
                success=True,
                user_id=UUID(user_info.get("sub")),
                email=user_info.get("email"),
                display_name=user_info.get("name"),
                groups=user_info.get("groups", []),
                metadata={"provider": "oidc", "issuer": self.config.issuer_url},
            )

        except Exception as e:
            self.logger.error("oidc_auth_failed", error=str(e))
            return AuthResult(
                success=False,
                error_message=str(e),
            )

    async def validate_token(self, token: str) -> AuthResult:
        """
        Validate an OIDC access token.

        Args:
            token: Access token to validate

        Returns:
            AuthResult with user information if valid
        """
        try:
            user_info = await self._get_userinfo(token)

            return AuthResult(
                success=True,
                user_id=UUID(user_info.get("sub")),
                email=user_info.get("email"),
                display_name=user_info.get("name"),
                groups=user_info.get("groups", []),
                metadata={"provider": "oidc"},
            )

        except Exception as e:
            self.logger.error("oidc_token_validation_failed", error=str(e))
            return AuthResult(
                success=False,
                error_message=str(e),
            )

    async def _get_userinfo(self, access_token: str) -> dict[str, Any]:
        """
        Fetch user information from userinfo endpoint.

        Args:
            access_token: Access token

        Returns:
            User information dictionary
        """
        discovery = await self._get_discovery_document()
        userinfo_endpoint = discovery["userinfo_endpoint"]

        async with httpx.AsyncClient(verify=self.config.verify_ssl) as client:
            response = await client.get(
                userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=self.config.timeout_seconds,
            )
            response.raise_for_status()
            return response.json()

    async def get_user_info(self, user_id: UUID | str) -> dict[str, Any]:
        """
        Retrieve user information (OIDC doesn't typically support this directly).

        Args:
            user_id: User identifier

        Returns:
            User information dictionary
        """
        # OIDC doesn't have a standard way to fetch user info by ID
        # This would need to be implemented based on the specific provider
        self.logger.warning("get_user_info_not_supported", user_id=str(user_id))
        return {"user_id": str(user_id)}

    async def health_check(self) -> bool:
        """
        Check OIDC provider health by fetching discovery document.

        Returns:
            True if provider is reachable
        """
        try:
            await self._get_discovery_document()
            return True
        except Exception as e:
            self.logger.error("oidc_health_check_failed", error=str(e))
            return False
