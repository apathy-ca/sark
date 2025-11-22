"""Authentication services."""

from sark.services.auth.api_key import APIKey, APIKeyService, get_api_key, require_scope
from sark.services.auth.jwt import JWTHandler, get_current_user
from sark.services.auth.providers import (
    AuthProvider,
    LDAPProvider,
    OIDCProvider,
    SAMLProvider,
)
from sark.services.auth.session import (
    Session,
    SessionService,
    SessionStore,
    get_session_store,
)
from sark.services.auth.user_context import UserContext, extract_user_context

__all__ = [
    # JWT
    "JWTHandler",
    "get_current_user",
    # User Context
    "UserContext",
    "extract_user_context",
    # API Keys
    "APIKey",
    "APIKeyService",
    "get_api_key",
    "require_scope",
    # Sessions
    "Session",
    "SessionService",
    "SessionStore",
    "get_session_store",
    # Providers
    "AuthProvider",
    "LDAPProvider",
    "OIDCProvider",
    "SAMLProvider",
]
