"""Authentication providers for external identity systems."""

from sark.services.auth.providers.base import AuthProvider, AuthProviderConfig
from sark.services.auth.providers.ldap import LDAPProvider, LDAPProviderConfig
from sark.services.auth.providers.oidc import OIDCProvider, OIDCProviderConfig
from sark.services.auth.providers.saml import SAMLProvider, SAMLProviderConfig

__all__ = [
    "AuthProvider",
    "AuthProviderConfig",
    "LDAPProvider",
    "LDAPProviderConfig",
    "OIDCProvider",
    "OIDCProviderConfig",
    "SAMLProvider",
    "SAMLProviderConfig",
]
