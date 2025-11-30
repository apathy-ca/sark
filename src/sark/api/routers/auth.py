"""Unified authentication router for multi-provider auth."""

from datetime import datetime
import logging
import secrets
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

from sark.config.settings import Settings
from sark.models.session import Session, SessionResponse
from sark.services.auth.providers import LDAPProvider, OIDCProvider, SAMLProvider
from sark.services.auth.sessions import SessionService

logger = logging.getLogger(__name__)

# Namespace UUID for generating deterministic user UUIDs
USER_UUID_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def user_id_to_uuid(user_id: str, provider: str) -> UUID:
    """Convert arbitrary user ID to deterministic UUID.

    Uses UUID v5 (name-based) to create consistent UUIDs from user IDs.
    The namespace includes the provider to avoid collisions.

    Args:
        user_id: User identifier from auth provider
        provider: Provider name (oidc, ldap, saml, etc.)

    Returns:
        Deterministic UUID for the user
    """
    # Combine provider and user_id to create a unique name
    name = f"{provider}:{user_id}"
    return uuid.uuid5(USER_UUID_NAMESPACE, name)


router = APIRouter(prefix="/api/auth", tags=["authentication"])


# Pydantic Models


class ProviderInfo(BaseModel):
    """Information about an authentication provider."""

    id: str
    name: str
    type: str  # oidc, saml, ldap, api_key
    enabled: bool
    authorization_url: str | None = None
    description: str | None = None


class ProvidersResponse(BaseModel):
    """List of available authentication providers."""

    providers: list[ProviderInfo]
    total: int


class LoginRequest(BaseModel):
    """Login request for credential-based auth (LDAP, username/password)."""

    provider: str
    username: str
    password: str
    remember_me: bool = False


class LoginResponse(BaseModel):
    """Login response with session information."""

    success: bool
    message: str
    session: SessionResponse | None = None
    user_id: UUID | None = None
    redirect_url: str | None = None


class AuthStatusResponse(BaseModel):
    """Current authentication status."""

    authenticated: bool
    user_id: UUID | None = None
    session_id: str | None = None
    session: SessionResponse | None = None
    provider: str | None = None
    expires_at: datetime | None = None


class LogoutResponse(BaseModel):
    """Logout response."""

    success: bool
    message: str
    sessions_invalidated: int = 0


class OAuthCallbackResponse(BaseModel):
    """OAuth callback response."""

    success: bool
    message: str
    session: SessionResponse | None = None
    user_id: UUID | None = None


# Dependencies


async def get_settings() -> Settings:
    """Get application settings.

    This is a placeholder for dependency injection.
    In production, retrieve from app state.
    """
    # TODO: Get from app state
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Settings dependency not configured",
    )


async def get_session_service() -> SessionService:
    """Get session service instance.

    This is a placeholder for dependency injection.
    In production, retrieve from app state.
    """
    # TODO: Get from app state
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Session service dependency not configured",
    )


async def get_current_session(
    request: Request,
    session_service: SessionService = Depends(get_session_service),
) -> Session | None:
    """Get current session from request (optional).

    Checks for session_id in:
    1. Cookies
    2. Authorization header (Bearer token)

    Args:
        request: FastAPI request
        session_service: Session service instance

    Returns:
        Session object if valid, None otherwise
    """
    # Check cookie
    session_id = request.cookies.get("session_id")

    # Check Authorization header if no cookie
    if not session_id:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            session_id = auth_header[7:]

    if session_id:
        return await session_service.validate_session(session_id)

    return None


async def require_auth(
    session: Session | None = Depends(get_current_session),
) -> Session:
    """Require authentication (session must exist).

    Args:
        session: Current session (from dependency)

    Returns:
        Session object

    Raises:
        401: Not authenticated
    """
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return session


# Endpoints


@router.get("/providers", response_model=ProvidersResponse)
async def list_providers(settings: Settings = Depends(get_settings)):
    """List all available authentication providers.

    Returns information about each enabled provider including
    authorization URLs for OAuth/OIDC providers.

    Args:
        settings: Application settings

    Returns:
        List of available providers with metadata
    """
    providers = []

    # OIDC Provider
    if settings.oidc_enabled:
        # Create temporary provider instance to get authorization URL
        OIDCProvider(
            client_id=settings.oidc_client_id,
            client_secret=settings.oidc_client_secret,
            provider=settings.oidc_provider,
            issuer=settings.oidc_issuer,
            tenant=settings.oidc_azure_tenant,
            domain=settings.oidc_okta_domain,
        )

        # Get authorization URL (will need state and redirect_uri from frontend)
        providers.append(
            ProviderInfo(
                id="oidc",
                name=f"OIDC ({settings.oidc_provider.title()})",
                type="oidc",
                enabled=True,
                authorization_url="/api/auth/oidc/authorize",
                description=f"Login with {settings.oidc_provider.title()}",
            )
        )

    # SAML Provider
    if settings.saml_enabled:
        providers.append(
            ProviderInfo(
                id="saml",
                name="SAML SSO",
                type="saml",
                enabled=True,
                authorization_url="/api/auth/saml/login",
                description="Enterprise SSO via SAML 2.0",
            )
        )

    # LDAP Provider
    if settings.ldap_enabled:
        providers.append(
            ProviderInfo(
                id="ldap",
                name="LDAP / Active Directory",
                type="ldap",
                enabled=True,
                authorization_url=None,  # Credential-based, no redirect
                description="Login with corporate credentials",
            )
        )

    # API Key (always available)
    providers.append(
        ProviderInfo(
            id="api_key",
            name="API Key",
            type="api_key",
            enabled=True,
            authorization_url=None,
            description="Programmatic access with API keys",
        )
    )

    return ProvidersResponse(
        providers=providers,
        total=len(providers),
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    login_request: LoginRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    session_service: SessionService = Depends(get_session_service),
):
    """Login with username and password (LDAP/AD).

    This endpoint handles credential-based authentication.
    OAuth/OIDC providers should use the authorize endpoint instead.

    Args:
        login_request: Login credentials
        request: FastAPI request
        settings: Application settings
        session_service: Session service instance

    Returns:
        Login response with session information

    Raises:
        400: Invalid provider
        401: Authentication failed
    """
    if login_request.provider == "ldap":
        if not settings.ldap_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="LDAP authentication is not enabled",
            )

        # Create LDAP provider
        ldap_provider = LDAPProvider(
            server_uri=settings.ldap_server,
            bind_dn=settings.ldap_bind_dn,
            bind_password=settings.ldap_bind_password,
            user_base_dn=settings.ldap_user_base_dn,
            group_base_dn=settings.ldap_group_base_dn,
        )

        # Authenticate
        user_info = await ldap_provider.authenticate(
            {
                "username": login_request.username,
                "password": login_request.password,
            }
        )

        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        # Create session
        timeout = settings.session_timeout_seconds
        if login_request.remember_me:
            timeout = timeout * 30  # Extend to 30 days for remember me

        # Convert user_id to UUID
        user_uuid = user_id_to_uuid(user_info.user_id, "ldap")

        session, _session_id = await session_service.create_session(
            user_id=user_uuid,
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent", ""),
            timeout_seconds=timeout,
            metadata={
                "provider": "ldap",
                "email": user_info.email,
                "original_user_id": user_info.user_id,
            },
        )

        return LoginResponse(
            success=True,
            message="Login successful",
            session=SessionResponse(
                session_id=session.session_id,
                user_id=session.user_id,
                created_at=session.created_at,
                expires_at=session.expires_at,
                last_activity=session.last_activity,
                ip_address=session.ip_address,
                user_agent=session.user_agent,
                is_expired=False,
            ),
            user_id=session.user_id,
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider: {login_request.provider}",
        )


@router.get("/oidc/authorize")
async def oidc_authorize(
    redirect_uri: str,
    state: str | None = None,
    settings: Settings = Depends(get_settings),
    session_service: SessionService = Depends(get_session_service),
):
    """Get OIDC authorization URL.

    Returns the authorization URL to redirect the user to the OIDC provider.

    Args:
        redirect_uri: Callback URL after authentication
        state: CSRF protection state parameter (auto-generated if not provided)
        settings: Application settings
        session_service: Session service for state storage

    Returns:
        Redirect response to OIDC provider

    Raises:
        400: OIDC not enabled
    """
    if not settings.oidc_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OIDC authentication is not enabled",
        )

    # Generate secure random state parameter for CSRF protection
    if not state:
        state = secrets.token_urlsafe(32)

    # Store state in Redis with 5-minute TTL (OAuth flow should complete quickly)
    state_key = f"oidc_state:{state}"
    await session_service.redis.setex(
        state_key,
        300,  # 5 minutes
        redirect_uri,  # Store redirect_uri for validation
    )
    logger.info(f"Stored OIDC state {state[:8]}... for CSRF validation")

    # Create OIDC provider
    oidc_provider = OIDCProvider(
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret,
        provider=settings.oidc_provider,
        issuer=settings.oidc_issuer,
        tenant=settings.oidc_azure_tenant,
        domain=settings.oidc_okta_domain,
    )

    # Get authorization URL
    auth_url = await oidc_provider.get_authorization_url(
        state=state,
        redirect_uri=redirect_uri,
    )

    # Redirect to authorization URL
    return Response(
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        headers={"Location": auth_url},
    )


@router.get("/oidc/callback", response_model=OAuthCallbackResponse)
async def oidc_callback(
    code: str,
    state: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    session_service: SessionService = Depends(get_session_service),
):
    """Handle OIDC callback after authentication.

    Exchanges authorization code for tokens and creates a session.

    Args:
        code: Authorization code
        state: State parameter for CSRF validation
        request: FastAPI request
        settings: Application settings
        session_service: Session service instance

    Returns:
        OAuth callback response with session

    Raises:
        400: OIDC not enabled
        401: Authentication failed
    """
    if not settings.oidc_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OIDC authentication is not enabled",
        )

    # Create OIDC provider
    oidc_provider = OIDCProvider(
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret,
        provider=settings.oidc_provider,
        issuer=settings.oidc_issuer,
        tenant=settings.oidc_azure_tenant,
        domain=settings.oidc_okta_domain,
    )

    # SECURITY: Validate state parameter against stored value (CSRF protection)
    state_key = f"oidc_state:{state}"
    stored_redirect_uri = await session_service.redis.get(state_key)

    if not stored_redirect_uri:
        logger.warning(f"OIDC callback with invalid/expired state: {state[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired state parameter. Please restart the login process.",
        )

    # Delete state after validation (one-time use)
    await session_service.redis.delete(state_key)
    logger.info(f"Validated and consumed OIDC state {state[:8]}...")

    # Handle callback and get tokens
    redirect_uri = stored_redirect_uri.decode("utf-8")
    tokens = await oidc_provider.handle_callback(code, state, redirect_uri)

    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to authenticate with OIDC provider",
        )

    # Validate token and get user info
    user_info = await oidc_provider.validate_token(tokens.get("access_token", ""))

    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to get user information",
        )

    # Convert user_id to UUID
    user_uuid = user_id_to_uuid(user_info.user_id, "oidc")

    # Create session
    session, _session_id = await session_service.create_session(
        user_id=user_uuid,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent", ""),
        metadata={
            "provider": "oidc",
            "email": user_info.email,
            "name": user_info.name,
            "original_user_id": user_info.user_id,
        },
    )

    return OAuthCallbackResponse(
        success=True,
        message="Authentication successful",
        session=SessionResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            created_at=session.created_at,
            expires_at=session.expires_at,
            last_activity=session.last_activity,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            is_expired=False,
        ),
        user_id=session.user_id,
    )


@router.get("/status", response_model=AuthStatusResponse)
async def auth_status(
    session: Session | None = Depends(get_current_session),
):
    """Get current authentication status.

    Returns information about the current session if authenticated.

    Args:
        session: Current session (from dependency)

    Returns:
        Authentication status with session information
    """
    if not session:
        return AuthStatusResponse(
            authenticated=False,
            user_id=None,
            session_id=None,
            session=None,
            provider=None,
            expires_at=None,
        )

    return AuthStatusResponse(
        authenticated=True,
        user_id=session.user_id,
        session_id=session.session_id,
        session=SessionResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            created_at=session.created_at,
            expires_at=session.expires_at,
            last_activity=session.last_activity,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            is_expired=session.is_expired(),
        ),
        provider=session.metadata.get("provider"),
        expires_at=session.expires_at,
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    response: Response,
    session: Session = Depends(require_auth),
    session_service: SessionService = Depends(get_session_service),
):
    """Logout and invalidate current session.

    Args:
        response: FastAPI response
        session: Current session (required)
        session_service: Session service instance

    Returns:
        Logout confirmation
    """
    # Invalidate session
    await session_service.invalidate_session(session.session_id)

    # Clear session cookie
    response.delete_cookie("session_id")

    return LogoutResponse(
        success=True,
        message="Logout successful",
        sessions_invalidated=1,
    )


@router.post("/logout/all", response_model=LogoutResponse)
async def logout_all(
    response: Response,
    session: Session = Depends(require_auth),
    session_service: SessionService = Depends(get_session_service),
):
    """Logout from all devices (invalidate all user sessions).

    Args:
        response: FastAPI response
        session: Current session (required)
        session_service: Session service instance

    Returns:
        Logout confirmation with count of invalidated sessions
    """
    # Invalidate all user sessions
    count = await session_service.invalidate_all_user_sessions(session.user_id)

    # Clear session cookie
    response.delete_cookie("session_id")

    return LogoutResponse(
        success=True,
        message="Logged out from all devices",
        sessions_invalidated=count,
    )


@router.get("/health")
async def auth_health(
    settings: Settings = Depends(get_settings),
):
    """Health check for authentication providers.

    Checks connectivity to all enabled auth providers.

    Args:
        settings: Application settings

    Returns:
        Health status of each provider
    """
    health_status = {}

    # Check OIDC
    if settings.oidc_enabled:
        try:
            oidc_provider = OIDCProvider(
                client_id=settings.oidc_client_id,
                client_secret=settings.oidc_client_secret,
                provider=settings.oidc_provider,
            )
            health_status["oidc"] = await oidc_provider.health_check()
        except Exception as e:
            logger.error(f"OIDC health check failed: {e}")
            health_status["oidc"] = False

    # Check SAML
    if settings.saml_enabled:
        try:
            saml_provider = SAMLProvider(
                sp_entity_id=settings.saml_sp_entity_id,
                sp_acs_url=settings.saml_sp_acs_url,
                sp_sls_url=settings.saml_sp_sls_url,
                idp_entity_id=settings.saml_idp_entity_id,
                idp_sso_url=settings.saml_idp_sso_url,
            )
            health_status["saml"] = await saml_provider.health_check()
        except Exception as e:
            logger.error(f"SAML health check failed: {e}")
            health_status["saml"] = False

    # Check LDAP
    if settings.ldap_enabled:
        try:
            ldap_provider = LDAPProvider(
                server_uri=settings.ldap_server,
                bind_dn=settings.ldap_bind_dn,
                bind_password=settings.ldap_bind_password,
                user_base_dn=settings.ldap_user_base_dn,
            )
            health_status["ldap"] = await ldap_provider.health_check()
        except Exception as e:
            logger.error(f"LDAP health check failed: {e}")
            health_status["ldap"] = False

    # Overall health
    healthy_count = sum(1 for v in health_status.values() if v)
    total_count = len(health_status)

    return {
        "status": "healthy" if healthy_count == total_count else "degraded",
        "providers": health_status,
        "healthy": healthy_count,
        "total": total_count,
    }
