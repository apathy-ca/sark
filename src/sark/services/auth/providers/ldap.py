"""LDAP/Active Directory authentication provider.

This module provides LDAP authentication and user attribute extraction
for enterprise single sign-on (SSO) integration.

Features:
- LDAP bind authentication
- LDAPS (SSL/TLS) support
- User attribute extraction (email, name, groups)
- Group-to-role mapping
- Connection pooling
- Comprehensive error handling
"""

from typing import Dict, List, Optional

import ldap3
from ldap3 import ALL, ALL_ATTRIBUTES, Connection, Server, Tls
from ldap3.core.exceptions import LDAPException
import structlog

from sark.config import Settings, get_settings

logger = structlog.get_logger(__name__)


class LDAPAuthenticationError(Exception):
    """Exception raised for LDAP authentication failures."""

    pass


class LDAPConnectionError(Exception):
    """Exception raised for LDAP connection failures."""

    pass


class LDAPProvider:
    """LDAP/Active Directory authentication provider.

    Provides authentication and user attribute extraction from LDAP
    directories including Microsoft Active Directory.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize LDAP provider.

        Args:
            settings: Settings instance (defaults to get_settings())

        Raises:
            ValueError: If LDAP is enabled but required settings are missing
        """
        self.settings = settings or get_settings()

        if not self.settings.ldap_enabled:
            logger.info("ldap_provider_disabled")
            return

        # Validate required settings
        if not self.settings.ldap_server:
            raise ValueError("LDAP_SERVER is required when LDAP is enabled")
        if not self.settings.ldap_bind_dn:
            raise ValueError("LDAP_BIND_DN is required when LDAP is enabled")
        if not self.settings.ldap_bind_password:
            raise ValueError("LDAP_BIND_PASSWORD is required when LDAP is enabled")
        if not self.settings.ldap_user_base_dn:
            raise ValueError("LDAP_USER_BASE_DN is required when LDAP is enabled")

        # Configure LDAP server
        self.server = self._create_server()
        self.pool = None  # Connection pool will be initialized when needed

        logger.info(
            "ldap_provider_initialized",
            server=self.settings.ldap_server,
            use_ssl=self.settings.ldap_use_ssl,
        )

    def _create_server(self) -> Server:
        """Create LDAP server object with TLS configuration.

        Returns:
            Configured LDAP Server object
        """
        # Configure TLS if using LDAPS
        tls = None
        if self.settings.ldap_use_ssl:
            tls = Tls()

        # Create server object
        server = Server(
            self.settings.ldap_server,
            get_info=ALL,
            tls=tls,
            connect_timeout=self.settings.ldap_timeout,
        )

        return server

    def _get_connection(
        self, user_dn: Optional[str] = None, password: Optional[str] = None
    ) -> Connection:
        """Get LDAP connection.

        Args:
            user_dn: User DN for binding (defaults to service account)
            password: Password for binding (defaults to service account)

        Returns:
            LDAP Connection object

        Raises:
            LDAPConnectionError: If connection fails
        """
        bind_dn = user_dn or self.settings.ldap_bind_dn
        bind_password = password or self.settings.ldap_bind_password

        try:
            connection = Connection(
                self.server,
                user=bind_dn,
                password=bind_password,
                auto_bind=True,
                raise_exceptions=True,
            )

            logger.debug("ldap_connection_established", bind_dn=bind_dn)
            return connection

        except LDAPException as e:
            logger.error(
                "ldap_connection_failed",
                bind_dn=bind_dn,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise LDAPConnectionError(f"Failed to connect to LDAP server: {e}") from e

    def authenticate(self, username: str, password: str) -> Dict[str, any]:
        """Authenticate user against LDAP directory.

        Args:
            username: Username to authenticate
            password: User password

        Returns:
            Dictionary containing user information:
            - user_id: Unique user identifier (DN or uid)
            - email: User email address
            - name: User display name
            - groups: List of LDAP groups
            - roles: List of SARK roles (mapped from groups)
            - attributes: Dictionary of all user LDAP attributes

        Raises:
            LDAPAuthenticationError: If authentication fails
            LDAPConnectionError: If LDAP connection fails
        """
        if not self.settings.ldap_enabled:
            raise LDAPAuthenticationError("LDAP authentication is not enabled")

        logger.info("ldap_authentication_attempt", username=username)

        # Step 1: Search for user DN using service account
        user_dn = self._find_user_dn(username)
        if not user_dn:
            logger.warning("ldap_user_not_found", username=username)
            raise LDAPAuthenticationError(f"User '{username}' not found in LDAP")

        # Step 2: Attempt to bind as the user (authenticate)
        try:
            connection = self._get_connection(user_dn=user_dn, password=password)
            connection.unbind()
            logger.info("ldap_authentication_success", username=username, user_dn=user_dn)
        except LDAPConnectionError as e:
            logger.warning(
                "ldap_authentication_failed",
                username=username,
                user_dn=user_dn,
                error=str(e),
            )
            raise LDAPAuthenticationError("Invalid username or password") from e

        # Step 3: Extract user attributes and groups
        user_info = self._get_user_info(user_dn)

        return user_info

    def _find_user_dn(self, username: str) -> Optional[str]:
        """Find user DN by username.

        Args:
            username: Username to search for

        Returns:
            User DN if found, None otherwise

        Raises:
            LDAPConnectionError: If LDAP connection fails
        """
        connection = self._get_connection()

        try:
            # Build search filter from template
            search_filter = self.settings.ldap_user_filter.format(username=username)

            # Search for user
            connection.search(
                search_base=self.settings.ldap_user_base_dn,
                search_filter=search_filter,
                search_scope=ldap3.SUBTREE,
                attributes=["dn"],
            )

            if connection.entries:
                user_dn = connection.entries[0].entry_dn
                logger.debug("ldap_user_found", username=username, user_dn=user_dn)
                return user_dn

            return None

        except LDAPException as e:
            logger.error(
                "ldap_user_search_failed",
                username=username,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise LDAPConnectionError(f"Failed to search for user: {e}") from e
        finally:
            connection.unbind()

    def _get_user_info(self, user_dn: str) -> Dict[str, any]:
        """Get user information and groups from LDAP.

        Args:
            user_dn: User distinguished name

        Returns:
            Dictionary containing user information

        Raises:
            LDAPConnectionError: If LDAP connection fails
        """
        connection = self._get_connection()

        try:
            # Get user attributes
            connection.search(
                search_base=user_dn,
                search_filter="(objectClass=*)",
                search_scope=ldap3.BASE,
                attributes=ALL_ATTRIBUTES,
            )

            if not connection.entries:
                logger.warning("ldap_user_info_not_found", user_dn=user_dn)
                raise LDAPConnectionError(f"User DN not found: {user_dn}")

            entry = connection.entries[0]

            # Extract common attributes (with defaults)
            email = self._get_attribute(entry, ["mail", "userPrincipalName", "email"])
            name = self._get_attribute(
                entry,
                ["displayName", "cn", "name"],
            )
            username = self._get_attribute(entry, ["uid", "sAMAccountName", "cn"])

            # Get user groups
            groups = self._get_user_groups(user_dn)

            # Map LDAP groups to SARK roles
            roles = self._map_groups_to_roles(groups)

            # Build user info dictionary
            user_info = {
                "user_id": user_dn,  # Use DN as unique identifier
                "username": username,
                "email": email,
                "name": name,
                "groups": groups,
                "roles": roles,
                "teams": groups,  # Use groups as teams
                "permissions": [],  # Will be determined by OPA policies
                "attributes": dict(entry.entry_attributes_as_dict),  # All LDAP attributes
            }

            logger.info(
                "ldap_user_info_retrieved",
                user_dn=user_dn,
                email=email,
                groups=groups,
                roles=roles,
            )

            return user_info

        except LDAPException as e:
            logger.error(
                "ldap_user_info_retrieval_failed",
                user_dn=user_dn,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise LDAPConnectionError(f"Failed to retrieve user info: {e}") from e
        finally:
            connection.unbind()

    def _get_attribute(self, entry: any, attribute_names: List[str]) -> Optional[str]:
        """Get first available attribute value from entry.

        Args:
            entry: LDAP entry object
            attribute_names: List of attribute names to try (in order)

        Returns:
            First non-None attribute value, or None if all are missing
        """
        for attr_name in attribute_names:
            if hasattr(entry, attr_name):
                value = getattr(entry, attr_name).value
                if value:
                    return value if isinstance(value, str) else value[0]
        return None

    def _get_user_groups(self, user_dn: str) -> List[str]:
        """Get groups that user belongs to.

        Args:
            user_dn: User distinguished name

        Returns:
            List of group names

        Raises:
            LDAPConnectionError: If LDAP connection fails
        """
        if not self.settings.ldap_group_base_dn:
            logger.debug("ldap_group_search_disabled", reason="no_group_base_dn")
            return []

        connection = self._get_connection()

        try:
            # Build group search filter
            search_filter = self.settings.ldap_group_filter.format(user_dn=user_dn)

            # Search for groups
            connection.search(
                search_base=self.settings.ldap_group_base_dn,
                search_filter=search_filter,
                search_scope=ldap3.SUBTREE,
                attributes=["cn", "name"],
            )

            groups = []
            for entry in connection.entries:
                group_name = self._get_attribute(entry, ["cn", "name"])
                if group_name:
                    groups.append(group_name)

            logger.debug("ldap_user_groups_retrieved", user_dn=user_dn, groups=groups)
            return groups

        except LDAPException as e:
            logger.warning(
                "ldap_group_search_failed",
                user_dn=user_dn,
                error=str(e),
                error_type=type(e).__name__,
            )
            # Don't fail authentication if group search fails
            return []
        finally:
            connection.unbind()

    def _map_groups_to_roles(self, groups: List[str]) -> List[str]:
        """Map LDAP groups to SARK roles.

        Args:
            groups: List of LDAP group names

        Returns:
            List of SARK role names
        """
        if not self.settings.ldap_role_mapping:
            # If no mapping configured, use groups as roles
            return groups

        roles = set()
        for group in groups:
            # Check if there's a mapping for this group
            mapped_role = self.settings.ldap_role_mapping.get(group)
            if mapped_role:
                roles.add(mapped_role)
            else:
                # No mapping, use group name as role
                roles.add(group)

        return list(roles)

    def validate_connection(self) -> bool:
        """Validate LDAP connection.

        Returns:
            True if connection is successful, False otherwise
        """
        if not self.settings.ldap_enabled:
            return False

        try:
            connection = self._get_connection()
            connection.unbind()
            logger.info("ldap_connection_validation_success")
            return True
        except Exception as e:
            logger.error(
                "ldap_connection_validation_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False
