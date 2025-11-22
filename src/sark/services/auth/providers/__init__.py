"""Authentication providers for SARK.

This package contains authentication providers for different
identity systems including LDAP and OIDC.
"""

from .base import AuthProvider, UserInfo
from sark.services.auth.providers.ldap import LDAPProvider
from sark.services.auth.providers.oidc import OIDCProvider

__all__ = ["AuthProvider", "UserInfo", "LDAPProvider", "OIDCProvider"]
