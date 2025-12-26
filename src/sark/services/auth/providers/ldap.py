"""LDAP authentication provider."""

import asyncio
from typing import Any
from uuid import UUID, uuid5

from ldap3 import ALL, SIMPLE, Connection, Server
from ldap3.core.exceptions import LDAPBindError, LDAPException
from pydantic import Field

from sark.services.auth.providers.base import (
    AuthProvider,
    AuthProviderConfig,
    AuthResult,
)


class LDAPProviderConfig(AuthProviderConfig):
    """Configuration for LDAP authentication provider."""

    server_url: str
    bind_dn: str | None = None
    bind_password: str | None = None
    base_dn: str
    user_search_filter: str = "(uid={username})"
    group_search_base: str | None = None
    group_search_filter: str = "(member={user_dn})"
    attributes: list[str] = Field(default_factory=lambda: ["uid", "mail", "cn", "memberOf"])
    use_ssl: bool = True
    use_tls: bool = False


class LDAPProvider(AuthProvider):
    """LDAP authentication provider."""

    def __init__(self, config: LDAPProviderConfig):
        """
        Initialize LDAP provider.

        Args:
            config: LDAP provider configuration
        """
        super().__init__(config)
        self.config: LDAPProviderConfig = config
        # In production, initialize LDAP connection here
        # For mock implementation, we'll simulate connections

    async def authenticate(
        self,
        username: str,
        credential: str,
        **kwargs: Any,
    ) -> AuthResult:
        """
        Authenticate a user against LDAP directory.

        Args:
            username: LDAP username
            credential: Password
            **kwargs: Additional parameters

        Returns:
            AuthResult with user information if authentication succeeds
        """
        try:
            # Search for user in LDAP
            user_dn, user_attrs = await self._search_user(username)

            if not user_dn:
                return AuthResult(
                    success=False,
                    error_message="User not found in LDAP directory",
                )

            # Attempt bind with user credentials to verify password
            if not await self._bind_user(user_dn, credential):
                return AuthResult(
                    success=False,
                    error_message="Invalid credentials",
                )

            # Get user groups
            groups = await self._get_user_groups(user_dn)

            # Generate stable UUID from LDAP DN
            namespace = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
            user_id = uuid5(namespace, user_dn)

            return AuthResult(
                success=True,
                user_id=user_id,
                email=user_attrs.get("mail"),
                display_name=user_attrs.get("cn"),
                groups=groups,
                metadata={
                    "provider": "ldap",
                    "dn": user_dn,
                    "attributes": user_attrs,
                },
            )

        except Exception as e:
            self.logger.error("ldap_auth_failed", error=str(e), username=username)
            return AuthResult(
                success=False,
                error_message=str(e),
            )

    async def validate_token(self, token: str) -> AuthResult:
        """
        LDAP doesn't use tokens - this method is not applicable.

        Args:
            token: Not used

        Returns:
            AuthResult indicating method not supported
        """
        self.logger.warning("ldap_token_validation_not_supported")
        return AuthResult(
            success=False,
            error_message="Token validation not supported for LDAP provider",
        )

    async def get_user_info(self, user_id: UUID | str) -> dict[str, Any]:
        """
        Retrieve user information from LDAP by user_id (DN).

        Args:
            user_id: User DN or UUID

        Returns:
            User information dictionary
        """
        try:
            # In production, search LDAP for user
            # For mock, return basic info
            return {
                "user_id": str(user_id),
                "provider": "ldap",
            }

        except Exception as e:
            self.logger.error("ldap_get_user_info_failed", error=str(e))
            return {}

    async def _search_user(self, username: str) -> tuple[str | None, dict[str, Any]]:
        """
        Search for user in LDAP directory.

        Args:
            username: Username to search for

        Returns:
            Tuple of (user_dn, user_attributes)
        """
        search_filter = self.config.user_search_filter.format(username=username)

        self.logger.debug(
            "ldap_user_search",
            base_dn=self.config.base_dn,
            filter=search_filter,
        )

        def _sync_search():
            """Synchronous LDAP search operation."""
            try:
                # Create server object
                server = Server(
                    self.config.server_url,
                    get_info=ALL,
                    use_ssl=self.config.use_ssl,
                )

                # Create connection for service account
                conn = Connection(
                    server,
                    user=self.config.bind_dn,
                    password=self.config.bind_password,
                    authentication=SIMPLE,
                    auto_bind=True,
                )

                # Search for user
                conn.search(
                    search_base=self.config.base_dn,
                    search_filter=search_filter,
                    attributes=self.config.attributes,
                )

                if not conn.entries:
                    conn.unbind()
                    return None, {}

                # Get first entry
                entry = conn.entries[0]
                user_dn = entry.entry_dn

                # Extract attributes
                user_attrs = {}
                for attr in self.config.attributes:
                    if hasattr(entry, attr):
                        attr_value = getattr(entry, attr)
                        if hasattr(attr_value, "value"):
                            user_attrs[attr] = attr_value.value
                        else:
                            user_attrs[attr] = str(attr_value)

                conn.unbind()
                return user_dn, user_attrs

            except LDAPException as e:
                self.logger.error("ldap_search_failed", error=str(e))
                return None, {}

        # Run synchronous LDAP operation in thread pool
        return await asyncio.get_event_loop().run_in_executor(None, _sync_search)

    async def _bind_user(self, user_dn: str, password: str) -> bool:
        """
        Attempt to bind as user to verify credentials.

        Args:
            user_dn: User distinguished name
            password: User password

        Returns:
            True if bind succeeds
        """
        self.logger.debug("ldap_bind_attempt", user_dn=user_dn)

        def _sync_bind():
            """Synchronous LDAP bind operation."""
            try:
                server = Server(
                    self.config.server_url,
                    get_info=ALL,
                    use_ssl=self.config.use_ssl,
                )

                # Attempt to bind as the user
                conn = Connection(
                    server,
                    user=user_dn,
                    password=password,
                    authentication=SIMPLE,
                    auto_bind=True,
                )

                # If we get here, bind succeeded
                conn.unbind()
                return True

            except LDAPBindError:
                self.logger.debug("ldap_bind_failed", user_dn=user_dn)
                return False
            except LDAPException as e:
                self.logger.error("ldap_bind_error", user_dn=user_dn, error=str(e))
                return False

        return await asyncio.get_event_loop().run_in_executor(None, _sync_bind)

    async def _get_user_groups(self, user_dn: str) -> list[str]:
        """
        Get groups for a user.

        Args:
            user_dn: User distinguished name

        Returns:
            List of group names
        """
        if not self.config.group_search_base:
            return []

        search_filter = self.config.group_search_filter.format(user_dn=user_dn)

        self.logger.debug(
            "ldap_group_search",
            base_dn=self.config.group_search_base,
            filter=search_filter,
        )

        def _sync_group_search():
            """Synchronous LDAP group search."""
            try:
                server = Server(
                    self.config.server_url,
                    get_info=ALL,
                    use_ssl=self.config.use_ssl,
                )

                conn = Connection(
                    server,
                    user=self.config.bind_dn,
                    password=self.config.bind_password,
                    authentication=SIMPLE,
                    auto_bind=True,
                )

                # Search for groups
                conn.search(
                    search_base=self.config.group_search_base,
                    search_filter=search_filter,
                    attributes=["cn"],
                )

                groups = []
                for entry in conn.entries:
                    if hasattr(entry, "cn"):
                        cn_value = entry.cn
                        if hasattr(cn_value, "value"):
                            groups.append(cn_value.value)
                        else:
                            groups.append(str(cn_value))

                conn.unbind()
                return groups

            except LDAPException as e:
                self.logger.error("ldap_group_search_failed", error=str(e))
                return []

        return await asyncio.get_event_loop().run_in_executor(None, _sync_group_search)

    async def health_check(self) -> bool:
        """
        Check LDAP server connectivity.

        Returns:
            True if LDAP server is reachable
        """
        if not self.config.enabled or not self.config.server_url:
            return False

        def _sync_health_check():
            """Synchronous LDAP health check."""
            try:
                server = Server(
                    self.config.server_url,
                    get_info=ALL,
                    use_ssl=self.config.use_ssl,
                    connect_timeout=5,
                )

                conn = Connection(
                    server,
                    user=self.config.bind_dn,
                    password=self.config.bind_password,
                    authentication=SIMPLE,
                    auto_bind=True,
                )

                # Perform a simple search to verify connectivity
                conn.search(
                    search_base=self.config.base_dn,
                    search_filter="(objectClass=*)",
                    search_scope="BASE",
                    attributes=["objectClass"],
                )

                conn.unbind()
                return True

            except Exception as e:
                self.logger.error("ldap_health_check_failed", error=str(e))
                return False

        try:
            return await asyncio.get_event_loop().run_in_executor(None, _sync_health_check)
        except Exception as e:
            self.logger.error("ldap_health_check_failed", error=str(e))
            return False
