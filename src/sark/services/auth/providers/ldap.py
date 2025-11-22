"""LDAP/Active Directory authentication provider."""

import logging
from typing import Any

from ldap3 import Connection, Server, ALL, SIMPLE, SUBTREE
from ldap3.core.exceptions import LDAPException, LDAPBindError

from .base import AuthProvider, UserInfo

logger = logging.getLogger(__name__)


class LDAPProvider(AuthProvider):
    """LDAP/Active Directory authentication provider.

    Supports both simple bind authentication and user/group lookup.
    Uses connection pooling for performance.

    Example:
        >>> provider = LDAPProvider(
        ...     server_uri="ldap://ldap.example.com:389",
        ...     bind_dn="cn=admin,dc=example,dc=com",
        ...     bind_password="password",
        ...     user_base_dn="ou=users,dc=example,dc=com",
        ...     group_base_dn="ou=groups,dc=example,dc=com"
        ... )
        >>> user_info = await provider.authenticate({
        ...     "username": "jdoe",
        ...     "password": "secret"
        ... })
    """

    def __init__(
        self,
        server_uri: str,
        bind_dn: str,
        bind_password: str,
        user_base_dn: str,
        group_base_dn: str | None = None,
        user_search_filter: str = "(uid={username})",
        group_search_filter: str = "(member={user_dn})",
        email_attribute: str = "mail",
        name_attribute: str = "cn",
        given_name_attribute: str = "givenName",
        family_name_attribute: str = "sn",
        use_ssl: bool = False,
        pool_size: int = 10,
    ):
        """Initialize LDAP provider.

        Args:
            server_uri: LDAP server URI (e.g., ldap://localhost:389)
            bind_dn: DN for binding to LDAP server
            bind_password: Password for bind DN
            user_base_dn: Base DN for user searches
            group_base_dn: Base DN for group searches (optional)
            user_search_filter: LDAP filter for user search (default: uid={username})
            group_search_filter: LDAP filter for group search (default: member={user_dn})
            email_attribute: LDAP attribute for email (default: mail)
            name_attribute: LDAP attribute for full name (default: cn)
            given_name_attribute: LDAP attribute for first name (default: givenName)
            family_name_attribute: LDAP attribute for last name (default: sn)
            use_ssl: Whether to use SSL/TLS (default: False)
            pool_size: Connection pool size (default: 10)
        """
        self.server_uri = server_uri
        self.bind_dn = bind_dn
        self.bind_password = bind_password
        self.user_base_dn = user_base_dn
        self.group_base_dn = group_base_dn
        self.user_search_filter = user_search_filter
        self.group_search_filter = group_search_filter
        self.email_attribute = email_attribute
        self.name_attribute = name_attribute
        self.given_name_attribute = given_name_attribute
        self.family_name_attribute = family_name_attribute
        self.use_ssl = use_ssl
        self.pool_size = pool_size

        # Create LDAP server object
        self.server = Server(server_uri, get_info=ALL, use_ssl=use_ssl)

    def _get_connection(self, user_dn: str | None = None, password: str | None = None) -> Connection:
        """Get LDAP connection (for user or service account).

        Args:
            user_dn: User DN for binding (optional, uses service account if not provided)
            password: Password for user binding

        Returns:
            LDAP Connection object
        """
        if user_dn and password:
            # User authentication connection
            return Connection(
                self.server,
                user=user_dn,
                password=password,
                authentication=SIMPLE,
                auto_bind=True,
                pool_size=self.pool_size,
                pool_name=f"ldap_user_{user_dn}",
            )
        else:
            # Service account connection
            return Connection(
                self.server,
                user=self.bind_dn,
                password=self.bind_password,
                authentication=SIMPLE,
                auto_bind=True,
                pool_size=self.pool_size,
                pool_name="ldap_service",
            )

    async def authenticate(self, credentials: dict[str, Any]) -> UserInfo | None:
        """Authenticate user with LDAP username and password.

        Args:
            credentials: Dictionary with 'username' and 'password' keys

        Returns:
            UserInfo object if authentication successful, None otherwise
        """
        username = credentials.get("username")
        password = credentials.get("password")

        if not username or not password:
            logger.warning("LDAP authentication failed: missing username or password")
            return None

        try:
            # First, search for user DN using service account
            conn = self._get_connection()
            search_filter = self.user_search_filter.format(username=username)

            conn.search(
                search_base=self.user_base_dn,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=[
                    self.email_attribute,
                    self.name_attribute,
                    self.given_name_attribute,
                    self.family_name_attribute,
                ],
            )

            if not conn.entries:
                logger.warning(f"LDAP user not found: {username}")
                conn.unbind()
                return None

            # Get user entry and DN
            user_entry = conn.entries[0]
            user_dn = user_entry.entry_dn
            conn.unbind()

            # Try to bind as the user to verify password
            try:
                user_conn = self._get_connection(user_dn, password)
                user_conn.unbind()
            except LDAPBindError:
                logger.warning(f"LDAP authentication failed for user: {username}")
                return None

            # Extract user information
            user_info = self._extract_user_info(user_entry, user_dn)

            # Get user groups if group_base_dn is configured
            if self.group_base_dn:
                user_info.groups = await self._get_user_groups(user_dn)

            logger.info(f"LDAP authentication successful for user: {username}")
            return user_info

        except LDAPException as e:
            logger.error(f"LDAP authentication error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during LDAP authentication: {e}")
            return None

    async def validate_token(self, token: str) -> UserInfo | None:
        """LDAP does not use tokens for authentication.

        Args:
            token: Not used for LDAP

        Returns:
            None (LDAP doesn't support token validation)
        """
        logger.warning("Token validation not supported for LDAP provider")
        return None

    async def refresh_token(self, refresh_token: str) -> dict[str, str] | None:
        """LDAP does not support token refresh.

        Args:
            refresh_token: Not used for LDAP

        Returns:
            None (LDAP doesn't support token refresh)
        """
        logger.warning("Token refresh not supported for LDAP provider")
        return None

    async def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """LDAP does not use OAuth flow.

        Args:
            state: Not used for LDAP
            redirect_uri: Not used for LDAP

        Returns:
            Empty string (LDAP doesn't use authorization URLs)
        """
        logger.warning("Authorization URL not supported for LDAP provider")
        return ""

    async def handle_callback(
        self, code: str, state: str, redirect_uri: str
    ) -> dict[str, str] | None:
        """LDAP does not use OAuth callback flow.

        Args:
            code: Not used for LDAP
            state: Not used for LDAP
            redirect_uri: Not used for LDAP

        Returns:
            None (LDAP doesn't use OAuth callbacks)
        """
        logger.warning("OAuth callback not supported for LDAP provider")
        return None

    async def health_check(self) -> bool:
        """Check if LDAP server is reachable.

        Returns:
            True if LDAP server is accessible, False otherwise
        """
        try:
            conn = self._get_connection()
            # Try a simple search to verify connectivity
            conn.search(
                search_base=self.user_base_dn,
                search_filter="(objectClass=*)",
                search_scope=SUBTREE,
                attributes=["dn"],
                size_limit=1,
            )
            conn.unbind()
            return True
        except LDAPException as e:
            logger.error(f"LDAP health check failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during LDAP health check: {e}")
            return False

    async def lookup_user(self, username: str) -> UserInfo | None:
        """Look up user information without authentication.

        Args:
            username: Username to look up

        Returns:
            UserInfo object if user found, None otherwise
        """
        try:
            conn = self._get_connection()
            search_filter = self.user_search_filter.format(username=username)

            conn.search(
                search_base=self.user_base_dn,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=[
                    self.email_attribute,
                    self.name_attribute,
                    self.given_name_attribute,
                    self.family_name_attribute,
                ],
            )

            if not conn.entries:
                logger.warning(f"LDAP user not found: {username}")
                conn.unbind()
                return None

            user_entry = conn.entries[0]
            user_dn = user_entry.entry_dn
            conn.unbind()

            # Extract user information
            user_info = self._extract_user_info(user_entry, user_dn)

            # Get user groups if group_base_dn is configured
            if self.group_base_dn:
                user_info.groups = await self._get_user_groups(user_dn)

            return user_info

        except LDAPException as e:
            logger.error(f"LDAP user lookup error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during LDAP user lookup: {e}")
            return None

    async def _get_user_groups(self, user_dn: str) -> list[str]:
        """Get groups for a user.

        Args:
            user_dn: User DN

        Returns:
            List of group names
        """
        if not self.group_base_dn:
            return []

        try:
            conn = self._get_connection()
            search_filter = self.group_search_filter.format(user_dn=user_dn)

            conn.search(
                search_base=self.group_base_dn,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=["cn"],
            )

            groups = [entry.cn.value for entry in conn.entries if hasattr(entry, "cn")]
            conn.unbind()
            return groups

        except LDAPException as e:
            logger.error(f"LDAP group lookup error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during LDAP group lookup: {e}")
            return []

    def _extract_user_info(self, user_entry: Any, user_dn: str) -> UserInfo:
        """Extract user information from LDAP entry.

        Args:
            user_entry: LDAP entry object
            user_dn: User DN

        Returns:
            UserInfo object
        """
        # Extract attributes safely
        email = getattr(user_entry, self.email_attribute, None)
        email = email.value if email else ""

        name = getattr(user_entry, self.name_attribute, None)
        name = name.value if name else None

        given_name = getattr(user_entry, self.given_name_attribute, None)
        given_name = given_name.value if given_name else None

        family_name = getattr(user_entry, self.family_name_attribute, None)
        family_name = family_name.value if family_name else None

        return UserInfo(
            user_id=user_dn,
            email=email,
            name=name,
            given_name=given_name,
            family_name=family_name,
            groups=[],  # Will be populated by caller if needed
            attributes={"dn": user_dn},
        )
