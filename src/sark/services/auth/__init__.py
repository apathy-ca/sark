"""Authentication services."""

from sark.services.auth.api_keys import APIKey, APIKeyService, get_api_key, require_scope
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
    # API Keys
    "APIKey",
    "APIKeyService",
    # Providers
    "AuthProvider",
    # JWT
    "JWTHandler",
    "LDAPProvider",
    "OIDCProvider",
    "SAMLProvider",
    # Sessions
    "Session",
    "SessionService",
    "SessionStore",
    # User Context
    "UserContext",
    "extract_user_context",
    "get_api_key",
    "get_current_user",
    "get_session_store",
    "require_scope",
]
