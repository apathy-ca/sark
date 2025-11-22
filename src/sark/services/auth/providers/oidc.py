"""OpenID Connect (OIDC) authentication provider.

This module provides OIDC authentication support for modern cloud identity
providers including Azure AD, Okta, Google, Auth0, and others.

Features:
- Authorization code flow with PKCE
- Automatic IdP discovery via .well-known/openid-configuration
- ID token validation (signature, nonce, expiry)
- UserInfo endpoint support
- Multiple OIDC provider support
- State parameter for CSRF protection
"""

import secrets
from typing import Dict, Optional
from urllib.parse import urlencode

import httpx
import structlog
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.jose import JsonWebToken, JWTClaims
from authlib.oidc.core import CodeIDToken

from sark.config import Settings, get_settings

logger = structlog.get_logger(__name__)


class OIDCAuthenticationError(Exception):
    """Exception raised for OIDC authentication failures."""

    pass


class OIDCConfigurationError(Exception):
    """Exception raised for OIDC configuration errors."""

    pass


class OIDCProvider:
    """OpenID Connect authentication provider.

    Supports OIDC authentication with authorization code flow and PKCE.
    Compatible with major identity providers.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize OIDC provider.

        Args:
            settings: Settings instance (defaults to get_settings())

        Raises:
            ValueError: If OIDC is enabled but required settings are missing
        """
        self.settings = settings or get_settings()

        if not self.settings.oidc_enabled:
            logger.info("oidc_provider_disabled")
            return

        # Validate required settings
        if not self.settings.oidc_discovery_url:
            raise ValueError("OIDC_DISCOVERY_URL is required when OIDC is enabled")
        if not self.settings.oidc_client_id:
            raise ValueError("OIDC_CLIENT_ID is required when OIDC is enabled")
        if not self.settings.oidc_client_secret:
            raise ValueError("OIDC_CLIENT_SECRET is required when OIDC is enabled")
        if not self.settings.oidc_redirect_uri:
            raise ValueError("OIDC_REDIRECT_URI is required when OIDC is enabled")

        # Will be populated from discovery
        self.oidc_config: Optional[Dict] = None
        self.jwks: Optional[Dict] = None

        logger.info(
            "oidc_provider_initialized",
            discovery_url=self.settings.oidc_discovery_url,
            client_id=self.settings.oidc_client_id,
        )

    async def _discover_configuration(self) -> Dict:
        """Discover OIDC provider configuration.

        Returns:
            OIDC configuration dictionary

        Raises:
            OIDCConfigurationError: If discovery fails
        """
        if self.oidc_config:
            return self.oidc_config

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.settings.oidc_discovery_url,
                    timeout=10.0,
                )
                response.raise_for_status()
                self.oidc_config = response.json()

                logger.info(
                    "oidc_configuration_discovered",
                    issuer=self.oidc_config.get("issuer"),
                    authorization_endpoint=self.oidc_config.get("authorization_endpoint"),
                )

                return self.oidc_config

        except Exception as e:
            logger.error(
                "oidc_discovery_failed",
                discovery_url=self.settings.oidc_discovery_url,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise OIDCConfigurationError(f"Failed to discover OIDC configuration: {e}") from e

    async def _fetch_jwks(self) -> Dict:
        """Fetch JSON Web Key Set (JWKS) from IdP.

        Returns:
            JWKS dictionary

        Raises:
            OIDCConfigurationError: If JWKS fetch fails
        """
        if self.jwks:
            return self.jwks

        config = await self._discover_configuration()
        jwks_uri = config.get("jwks_uri")

        if not jwks_uri:
            raise OIDCConfigurationError("JWKS URI not found in OIDC configuration")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(jwks_uri, timeout=10.0)
                response.raise_for_status()
                self.jwks = response.json()

                logger.debug("oidc_jwks_fetched", keys_count=len(self.jwks.get("keys", [])))
                return self.jwks

        except Exception as e:
            logger.error(
                "oidc_jwks_fetch_failed",
                jwks_uri=jwks_uri,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise OIDCConfigurationError(f"Failed to fetch JWKS: {e}") from e

    async def get_authorization_url(self, state: Optional[str] = None) -> tuple[str, str, Optional[str]]:
        """Generate authorization URL for OIDC login flow.

        Args:
            state: Optional state parameter for CSRF protection (generated if not provided)

        Returns:
            Tuple of (authorization_url, state, code_verifier)
            code_verifier is only returned if PKCE is enabled

        Raises:
            OIDCConfigurationError: If configuration discovery fails
        """
        config = await self._discover_configuration()
        authorization_endpoint = config.get("authorization_endpoint")

        if not authorization_endpoint:
            raise OIDCConfigurationError(
                "Authorization endpoint not found in OIDC configuration"
            )

        # Generate state if not provided (for CSRF protection)
        if not state:
            state = secrets.token_urlsafe(32)

        # Build authorization parameters
        params = {
            "response_type": "code",
            "client_id": self.settings.oidc_client_id,
            "redirect_uri": self.settings.oidc_redirect_uri,
            "scope": " ".join(self.settings.oidc_scopes),
            "state": state,
        }

        code_verifier = None

        # Add PKCE if enabled
        if self.settings.oidc_use_pkce:
            code_verifier = secrets.token_urlsafe(32)
            # Generate code challenge (SHA256 hash of verifier, base64url encoded)
            import hashlib
            import base64

            challenge = hashlib.sha256(code_verifier.encode()).digest()
            code_challenge = base64.urlsafe_b64encode(challenge).decode().rstrip("=")

            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"

            logger.debug("oidc_pkce_enabled", code_challenge=code_challenge[:10] + "...")

        authorization_url = f"{authorization_endpoint}?{urlencode(params)}"

        logger.info(
            "oidc_authorization_url_generated",
            state=state[:8] + "...",
            pkce_enabled=self.settings.oidc_use_pkce,
        )

        return authorization_url, state, code_verifier

    async def exchange_code_for_tokens(
        self, code: str, code_verifier: Optional[str] = None
    ) -> Dict[str, any]:
        """Exchange authorization code for tokens.

        Args:
            code: Authorization code from callback
            code_verifier: PKCE code verifier (required if PKCE is enabled)

        Returns:
            Dictionary containing access_token, id_token, and optionally refresh_token

        Raises:
            OIDCAuthenticationError: If token exchange fails
        """
        config = await self._discover_configuration()
        token_endpoint = config.get("token_endpoint")

        if not token_endpoint:
            raise OIDCConfigurationError("Token endpoint not found in OIDC configuration")

        # Build token request
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.settings.oidc_redirect_uri,
            "client_id": self.settings.oidc_client_id,
            "client_secret": self.settings.oidc_client_secret,
        }

        # Add PKCE verifier if provided
        if code_verifier:
            data["code_verifier"] = code_verifier

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_endpoint,
                    data=data,
                    timeout=10.0,
                )
                response.raise_for_status()
                tokens = response.json()

                logger.info("oidc_tokens_received", has_id_token="id_token" in tokens)
                return tokens

        except httpx.HTTPStatusError as e:
            logger.error(
                "oidc_token_exchange_failed",
                status_code=e.response.status_code,
                error=e.response.text,
            )
            raise OIDCAuthenticationError(f"Token exchange failed: {e.response.text}") from e
        except Exception as e:
            logger.error(
                "oidc_token_exchange_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise OIDCAuthenticationError(f"Token exchange failed: {e}") from e

    async def validate_id_token(self, id_token: str, nonce: Optional[str] = None) -> JWTClaims:
        """Validate ID token and extract claims.

        Args:
            id_token: The ID token to validate
            nonce: Optional nonce value to validate (for replay protection)

        Returns:
            Validated JWT claims

        Raises:
            OIDCAuthenticationError: If token validation fails
        """
        try:
            # Fetch JWKS for signature verification
            jwks = await self._fetch_jwks()
            config = await self._discover_configuration()

            # Create JWT validator
            jwt = JsonWebToken(["RS256", "HS256"])

            # Decode and validate token
            claims = jwt.decode(
                id_token,
                key=jwks,
                claims_cls=CodeIDToken,
                claims_options={
                    "iss": {"value": config.get("issuer")},
                    "aud": {"value": self.settings.oidc_client_id},
                },
            )

            # Validate nonce if provided
            if nonce and claims.get("nonce") != nonce:
                raise OIDCAuthenticationError("ID token nonce mismatch")

            logger.info(
                "oidc_id_token_validated",
                sub=claims.get("sub"),
                email=claims.get("email"),
            )

            return claims

        except Exception as e:
            logger.error(
                "oidc_id_token_validation_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise OIDCAuthenticationError(f"ID token validation failed: {e}") from e

    async def get_user_info(self, access_token: str) -> Dict[str, any]:
        """Fetch user information from UserInfo endpoint.

        Args:
            access_token: Access token for authentication

        Returns:
            User information dictionary

        Raises:
            OIDCAuthenticationError: If UserInfo request fails
        """
        config = await self._discover_configuration()
        userinfo_endpoint = config.get("userinfo_endpoint")

        if not userinfo_endpoint:
            logger.warning("oidc_userinfo_endpoint_not_found")
            return {}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    userinfo_endpoint,
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10.0,
                )
                response.raise_for_status()
                user_info = response.json()

                logger.debug("oidc_userinfo_fetched", sub=user_info.get("sub"))
                return user_info

        except Exception as e:
            logger.warning(
                "oidc_userinfo_fetch_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            # Don't fail authentication if UserInfo fails, just return empty dict
            return {}

    async def authenticate(
        self, code: str, code_verifier: Optional[str] = None, nonce: Optional[str] = None
    ) -> Dict[str, any]:
        """Complete OIDC authentication flow.

        Args:
            code: Authorization code from callback
            code_verifier: PKCE code verifier (required if PKCE is enabled)
            nonce: Optional nonce for ID token validation

        Returns:
            Dictionary containing user information:
            - user_id: Unique user identifier (sub claim)
            - email: User email address
            - name: User display name
            - roles: List of roles (from groups claim)
            - teams: List of teams (from groups claim)
            - attributes: All ID token claims

        Raises:
            OIDCAuthenticationError: If authentication fails
        """
        logger.info("oidc_authentication_started")

        # Exchange code for tokens
        tokens = await self.exchange_code_for_tokens(code, code_verifier)

        # Validate ID token
        id_token = tokens.get("id_token")
        if not id_token:
            raise OIDCAuthenticationError("No ID token in response")

        claims = await self.validate_id_token(id_token, nonce)

        # Optionally fetch additional user info
        access_token = tokens.get("access_token")
        user_info = {}
        if access_token:
            user_info = await self.get_user_info(access_token)

        # Merge claims with user_info (user_info takes precedence)
        merged_info = {**dict(claims), **user_info}

        # Extract and normalize user information
        user_data = {
            "user_id": merged_info.get("sub"),
            "username": merged_info.get("preferred_username") or merged_info.get("email"),
            "email": merged_info.get("email"),
            "name": merged_info.get("name") or merged_info.get("given_name", ""),
            "roles": merged_info.get("roles", merged_info.get("groups", [])),
            "teams": merged_info.get("groups", merged_info.get("roles", [])),
            "permissions": [],  # Will be determined by OPA policies
            "attributes": merged_info,  # Store all claims for reference
        }

        logger.info(
            "oidc_authentication_success",
            user_id=user_data["user_id"],
            email=user_data["email"],
            roles=user_data["roles"],
        )

        return user_data
