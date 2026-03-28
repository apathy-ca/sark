"""LDAP authentication provider."""

from typing import Any
from uuid import UUID, uuid5

import bonsai
from pydantic import Field

from sark.services.auth.providers.base import (
    AuthProvider,
    AuthProviderConfig,
    AuthResult,
)


def _escape_filter_chars(value: str) -> str:
    """Escape special characters in an LDAP filter value per RFC 4515."""
    value = value.replace("\\", "\\5c")
    value = value.replace("*", "\\2a")
    value = value.replace("(", "\\28")
    value = value.replace(")", "\\29")
    value = value.replace("\x00", "\\00")
    return value


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
        # Escape username to prevent LDAP injection
        safe_username = _escape_filter_chars(username)
        search_filter = self.config.user_search_filter.format(username=safe_username)

        self.logger.debug(
            "ldap_user_search",
            base_dn=self.config.base_dn,
            filter=search_filter,
        )

        try:
            client = bonsai.LDAPClient(self.config.server_url)
            if self.config.bind_dn and self.config.bind_password:
                client.set_credentials(
                    "SIMPLE", self.config.bind_dn, self.config.bind_password
                )

            async with await client.connect(is_async=True) as conn:
                results = await conn.search(
                    self.config.base_dn,
                    bonsai.LDAPSearchScope.SUB,
                    search_filter,
                    attrlist=self.config.attributes,
                )

                if not results:
                    return None, {}

                entry = results[0]
                user_dn = str(entry.dn)

                # Extract attributes
                user_attrs = {}
                for attr in self.config.attributes:
                    try:
                        user_attrs[attr] = entry[attr][0]
                    except (KeyError, IndexError):
                        pass

                return user_dn, user_attrs

        except bonsai.LDAPError as e:
            self.logger.error("ldap_search_failed", error=str(e))
            return None, {}

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

        try:
            client = bonsai.LDAPClient(self.config.server_url)
            client.set_credentials("SIMPLE", user_dn, password)

            async with await client.connect(is_async=True):
                return True

        except bonsai.AuthenticationError:
            self.logger.debug("ldap_bind_failed", user_dn=user_dn)
            return False
        except bonsai.LDAPError as e:
            self.logger.error("ldap_bind_error", user_dn=user_dn, error=str(e))
            return False

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

        # Escape user_dn to prevent LDAP injection
        safe_user_dn = _escape_filter_chars(user_dn)
        search_filter = self.config.group_search_filter.format(user_dn=safe_user_dn)

        self.logger.debug(
            "ldap_group_search",
            base_dn=self.config.group_search_base,
            filter=search_filter,
        )

        try:
            client = bonsai.LDAPClient(self.config.server_url)
            if self.config.bind_dn and self.config.bind_password:
                client.set_credentials(
                    "SIMPLE", self.config.bind_dn, self.config.bind_password
                )

            async with await client.connect(is_async=True) as conn:
                results = await conn.search(
                    self.config.group_search_base,
                    bonsai.LDAPSearchScope.SUB,
                    search_filter,
                    attrlist=["cn"],
                )

                groups = []
                for entry in results:
                    try:
                        groups.append(entry["cn"][0])
                    except (KeyError, IndexError):
                        pass

                return groups

        except bonsai.LDAPError as e:
            self.logger.error("ldap_group_search_failed", error=str(e))
            return []

    async def health_check(self) -> bool:
        """
        Check LDAP server connectivity.

        Returns:
            True if LDAP server is reachable
        """
        if not self.config.enabled or not self.config.server_url:
            return False

        try:
            client = bonsai.LDAPClient(self.config.server_url)
            if self.config.bind_dn and self.config.bind_password:
                client.set_credentials(
                    "SIMPLE", self.config.bind_dn, self.config.bind_password
                )
            client.set_connect_timeout(5)

            async with await client.connect(is_async=True) as conn:
                await conn.search(
                    self.config.base_dn,
                    bonsai.LDAPSearchScope.BASE,
                    "(objectClass=*)",
                    attrlist=["objectClass"],
                )
                return True

        except Exception as e:
            self.logger.error("ldap_health_check_failed", error=str(e))
            return False
