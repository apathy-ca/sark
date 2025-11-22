"""OpenID Connect (OIDC) authentication provider.

Supports multiple OIDC providers:
- Google OAuth
- Azure AD
- Okta
- Any OIDC-compliant provider
"""

import time
from typing import Any

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.jose import JsonWebToken, JWTClaims
from authlib.oidc.core import CodeIDToken

from .base import AuthProvider, UserInfo


class OIDCProvider(AuthProvider):
    """OpenID Connect authentication provider.

    Implements OAuth 2.0 / OIDC authentication flow with support for
    major providers (Google, Azure AD, Okta) and any OIDC-compliant service.
    """

    # Well-known OIDC provider configurations
    PROVIDER_CONFIGS = {
        "google": {
            "issuer": "https://accounts.google.com",
            "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_endpoint": "https://oauth2.googleapis.com/token",
            "userinfo_endpoint": "https://openidconnect.googleapis.com/v1/userinfo",
            "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
        },
        "azure": {
            "issuer": "https://login.microsoftonline.com/{tenant}/v2.0",
            "authorization_endpoint": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
            "token_endpoint": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            "userinfo_endpoint": "https://graph.microsoft.com/oidc/userinfo",
            "jwks_uri": "https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys",
        },
        "okta": {
            "issuer": "https://{domain}",
            "authorization_endpoint": "https://{domain}/oauth2/v1/authorize",
            "token_endpoint": "https://{domain}/oauth2/v1/token",
            "userinfo_endpoint": "https://{domain}/oauth2/v1/userinfo",
            "jwks_uri": "https://{domain}/oauth2/v1/keys",
        },
    }

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        provider: str = "google",
        issuer: str | None = None,
        authorization_endpoint: str | None = None,
        token_endpoint: str | None = None,
        userinfo_endpoint: str | None = None,
        jwks_uri: str | None = None,
        scopes: list[str] | None = None,
        tenant: str | None = None,  # For Azure AD
        domain: str | None = None,  # For Okta
    ):
        """Initialize OIDC provider.

        Args:
            client_id: OAuth 2.0 client ID
            client_secret: OAuth 2.0 client secret
            provider: Provider name ('google', 'azure', 'okta', or 'custom')
            issuer: OIDC issuer URL (required for custom provider)
            authorization_endpoint: Authorization endpoint URL
            token_endpoint: Token endpoint URL
            userinfo_endpoint: UserInfo endpoint URL
            jwks_uri: JSON Web Key Set URI
            scopes: OAuth scopes (default: ['openid', 'profile', 'email'])
            tenant: Azure AD tenant ID (required for Azure)
            domain: Okta domain (required for Okta)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.provider = provider.lower()
        self.scopes = scopes or ["openid", "profile", "email"]

        # Get provider configuration
        if self.provider in self.PROVIDER_CONFIGS:
            config = self.PROVIDER_CONFIGS[self.provider].copy()

            # Replace placeholders for Azure AD
            if self.provider == "azure":
                if not tenant:
                    raise ValueError("Azure AD requires 'tenant' parameter")
                for key, value in config.items():
                    config[key] = value.replace("{tenant}", tenant)

            # Replace placeholders for Okta
            elif self.provider == "okta":
                if not domain:
                    raise ValueError("Okta requires 'domain' parameter")
                for key, value in config.items():
                    config[key] = value.replace("{domain}", domain)

            # Set endpoints from provider config
            self.issuer = issuer or config["issuer"]
            self.authorization_endpoint = authorization_endpoint or config["authorization_endpoint"]
            self.token_endpoint = token_endpoint or config["token_endpoint"]
            self.userinfo_endpoint = userinfo_endpoint or config["userinfo_endpoint"]
            self.jwks_uri = jwks_uri or config["jwks_uri"]
        else:
            # Custom provider - all endpoints must be provided
            if not all([issuer, authorization_endpoint, token_endpoint, userinfo_endpoint, jwks_uri]):
                raise ValueError(
                    "Custom OIDC provider requires all endpoints: "
                    "issuer, authorization_endpoint, token_endpoint, userinfo_endpoint, jwks_uri"
                )
            self.issuer = issuer
            self.authorization_endpoint = authorization_endpoint
            self.token_endpoint = token_endpoint
            self.userinfo_endpoint = userinfo_endpoint
            self.jwks_uri = jwks_uri

        # Initialize OAuth client
        self.client = AsyncOAuth2Client(
            client_id=self.client_id,
            client_secret=self.client_secret,
            token_endpoint=self.token_endpoint,
        )

        # JWT validator
        self.jwt = JsonWebToken(["RS256", "HS256"])
        self._jwks_cache: dict[str, Any] | None = None
        self._jwks_cache_time: float = 0
        self._jwks_cache_ttl: int = 3600  # 1 hour

    async def authenticate(self, credentials: dict[str, Any]) -> UserInfo | None:
        """Authenticate user with OIDC token.

        Args:
            credentials: Dictionary with 'access_token' or 'id_token'

        Returns:
            UserInfo object if authentication successful, None otherwise
        """
        token = credentials.get("access_token") or credentials.get("id_token")
        if not token:
            return None

        return await self.validate_token(token)

    async def validate_token(self, token: str) -> UserInfo | None:
        """Validate OIDC token and extract user information.

        Args:
            token: JWT access token or ID token

        Returns:
            UserInfo object if token is valid, None otherwise
        """
        try:
            # Get JWKS for token validation
            jwks = await self._get_jwks()

            # Decode and validate token
            claims = self.jwt.decode(
                token,
                jwks,
                claims_cls=JWTClaims,
                claims_options={
                    "iss": {"essential": True, "value": self.issuer},
                    "aud": {"essential": True, "value": self.client_id},
                },
            )
            claims.validate()

            # Extract user info from claims
            return self._extract_user_info(claims)

        except Exception as e:
            # Log error in production
            print(f"Token validation failed: {e}")
            return None

    async def refresh_token(self, refresh_token: str) -> dict[str, str] | None:
        """Refresh an OIDC access token.

        Args:
            refresh_token: Refresh token

        Returns:
            Dictionary with new access_token and refresh_token, or None if failed
        """
        try:
            token_response = await self.client.refresh_token(
                self.token_endpoint,
                refresh_token=refresh_token,
            )
            return {
                "access_token": token_response["access_token"],
                "refresh_token": token_response.get("refresh_token", refresh_token),
                "expires_in": token_response.get("expires_in", 3600),
                "id_token": token_response.get("id_token"),
            }
        except Exception as e:
            print(f"Token refresh failed: {e}")
            return None

    async def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """Get the OIDC authorization URL.

        Args:
            state: State parameter for CSRF protection
            redirect_uri: Redirect URI after authentication

        Returns:
            Authorization URL
        """
        uri, _ = self.client.create_authorization_url(
            self.authorization_endpoint,
            redirect_uri=redirect_uri,
            scope=" ".join(self.scopes),
            state=state,
        )
        return uri

    async def handle_callback(
        self, code: str, state: str, redirect_uri: str
    ) -> dict[str, str] | None:
        """Handle OIDC callback and exchange code for tokens.

        Args:
            code: Authorization code
            state: State parameter for validation
            redirect_uri: Redirect URI used in authorization request

        Returns:
            Dictionary with access_token, refresh_token, id_token, or None if failed
        """
        try:
            # Exchange authorization code for tokens
            token_response = await self.client.fetch_token(
                self.token_endpoint,
                code=code,
                redirect_uri=redirect_uri,
            )

            return {
                "access_token": token_response["access_token"],
                "refresh_token": token_response.get("refresh_token"),
                "expires_in": token_response.get("expires_in", 3600),
                "id_token": token_response.get("id_token"),
                "token_type": token_response.get("token_type", "Bearer"),
            }
        except Exception as e:
            print(f"Token exchange failed: {e}")
            return None

    async def health_check(self) -> bool:
        """Check if OIDC provider is reachable.

        Returns:
            True if provider is healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_uri, timeout=5.0)
                return response.status_code == 200
        except Exception:
            return False

    async def get_user_info(self, access_token: str) -> UserInfo | None:
        """Fetch user information from userinfo endpoint.

        Args:
            access_token: Valid access token

        Returns:
            UserInfo object or None if failed
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.userinfo_endpoint,
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10.0,
                )
                response.raise_for_status()
                user_data = response.json()
                return self._extract_user_info(user_data)
        except Exception as e:
            print(f"Failed to fetch user info: {e}")
            return None

    async def _get_jwks(self) -> dict[str, Any]:
        """Fetch and cache JSON Web Key Set.

        Returns:
            JWKS dictionary
        """
        # Check cache
        current_time = time.time()
        if self._jwks_cache and (current_time - self._jwks_cache_time) < self._jwks_cache_ttl:
            return self._jwks_cache

        # Fetch JWKS
        async with httpx.AsyncClient() as client:
            response = await client.get(self.jwks_uri, timeout=10.0)
            response.raise_for_status()
            self._jwks_cache = response.json()
            self._jwks_cache_time = current_time
            return self._jwks_cache

    def _extract_user_info(self, data: dict[str, Any] | JWTClaims) -> UserInfo:
        """Extract user information from OIDC claims or userinfo response.

        Args:
            data: Claims dictionary or JWTClaims object

        Returns:
            UserInfo object
        """
        # Convert JWTClaims to dict if needed
        if isinstance(data, JWTClaims):
            claims = dict(data)
        else:
            claims = data

        # Extract standard OIDC claims
        user_id = claims.get("sub") or claims.get("oid") or claims.get("uid", "")
        email = claims.get("email", "")
        name = claims.get("name")
        given_name = claims.get("given_name")
        family_name = claims.get("family_name")
        picture = claims.get("picture")

        # Extract groups (provider-specific)
        groups = None
        if "groups" in claims:
            groups = claims["groups"]
        elif "roles" in claims:
            groups = claims["roles"]

        return UserInfo(
            user_id=user_id,
            email=email,
            name=name,
            given_name=given_name,
            family_name=family_name,
            picture=picture,
            groups=groups,
            attributes=claims,
        )
