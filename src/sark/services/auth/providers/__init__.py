"""Authentication providers for SARK.

This package contains authentication providers for different
identity systems including LDAP, SAML, and OIDC.
"""

from sark.services.auth.providers.ldap import LDAPProvider

__all__ = ["LDAPProvider"]
