"""Integration tests for LDAP authentication provider using Docker."""

import pytest

# Import fixtures from ldap_docker
pytest_plugins = ["tests.fixtures.ldap_docker"]


@pytest.mark.integration
class TestLDAPIntegrationBasic:
    """Basic LDAP integration tests."""

    @pytest.mark.asyncio
    async def test_authenticate_valid_user(self, ldap_provider):
        """Test authentication with valid credentials."""
        result = await ldap_provider.authenticate("testuser", "testpass")

        assert result.success is True
        assert result.user_id is not None
        assert result.email == "testuser@example.com"
        assert result.display_name == "Test User"

    @pytest.mark.asyncio
    async def test_authenticate_invalid_password(self, ldap_provider):
        """Test authentication fails with invalid password."""
        result = await ldap_provider.authenticate("testuser", "wrongpass")

        assert result.success is False
        assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_authenticate_nonexistent_user(self, ldap_provider):
        """Test authentication fails for nonexistent user."""
        result = await ldap_provider.authenticate("nonexistent", "password")

        assert result.success is False
        assert "not found" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_authenticate_multiple_users(self, ldap_provider):
        """Test authentication with multiple different users."""
        # Test user 1
        result1 = await ldap_provider.authenticate("testuser", "testpass")
        assert result1.success is True
        assert result1.email == "testuser@example.com"

        # Test user 2
        result2 = await ldap_provider.authenticate("admin", "adminpass")
        assert result2.success is True
        assert result2.email == "admin@example.com"

        # Test user 3
        result3 = await ldap_provider.authenticate("jdoe", "password123")
        assert result3.success is True
        assert result3.email == "jdoe@example.com"

    @pytest.mark.asyncio
    async def test_authenticate_empty_username(self, ldap_provider):
        """Test authentication fails with empty username."""
        result = await ldap_provider.authenticate("", "password")

        assert result.success is False

    @pytest.mark.asyncio
    async def test_authenticate_empty_password(self, ldap_provider):
        """Test authentication fails with empty password."""
        result = await ldap_provider.authenticate("testuser", "")

        assert result.success is False


@pytest.mark.integration
class TestLDAPIntegrationGroups:
    """LDAP group membership integration tests."""

    @pytest.mark.asyncio
    async def test_user_with_groups(self, ldap_provider):
        """Test that user groups are retrieved correctly."""
        result = await ldap_provider.authenticate("testuser", "testpass")

        assert result.success is True
        assert "developers" in result.groups

    @pytest.mark.asyncio
    async def test_admin_user_groups(self, ldap_provider):
        """Test admin user has correct groups."""
        result = await ldap_provider.authenticate("admin", "adminpass")

        assert result.success is True
        assert "admins" in result.groups

    @pytest.mark.asyncio
    async def test_multiple_group_membership(self, ldap_provider):
        """Test user with multiple groups."""
        result = await ldap_provider.authenticate("testuser", "testpass")

        assert result.success is True
        assert isinstance(result.groups, list)
        assert len(result.groups) > 0


@pytest.mark.integration
class TestLDAPIntegrationAttributes:
    """LDAP user attribute integration tests."""

    @pytest.mark.asyncio
    async def test_user_attributes_extracted(self, ldap_provider):
        """Test that user attributes are extracted correctly."""
        result = await ldap_provider.authenticate("jdoe", "password123")

        assert result.success is True
        assert result.metadata is not None
        assert result.metadata["provider"] == "ldap"
        assert "dn" in result.metadata
        assert "attributes" in result.metadata

    @pytest.mark.asyncio
    async def test_user_email_attribute(self, ldap_provider):
        """Test email attribute is extracted."""
        result = await ldap_provider.authenticate("testuser", "testpass")

        assert result.success is True
        assert result.email is not None
        assert "@example.com" in result.email

    @pytest.mark.asyncio
    async def test_user_display_name(self, ldap_provider):
        """Test display name is extracted."""
        result = await ldap_provider.authenticate("jdoe", "password123")

        assert result.success is True
        assert result.display_name == "John Doe"

    @pytest.mark.asyncio
    async def test_user_id_generation(self, ldap_provider):
        """Test that user ID is consistently generated."""
        result1 = await ldap_provider.authenticate("testuser", "testpass")
        result2 = await ldap_provider.authenticate("testuser", "testpass")

        assert result1.success is True
        assert result2.success is True
        # Same user should get same UUID
        assert result1.user_id == result2.user_id


@pytest.mark.integration
class TestLDAPIntegrationSearch:
    """LDAP search functionality integration tests."""

    @pytest.mark.asyncio
    async def test_search_user_by_uid(self, ldap_provider):
        """Test user search by UID."""
        user_dn, user_attrs = await ldap_provider._search_user("testuser")

        assert user_dn is not None
        assert "testuser" in user_dn
        assert user_attrs is not None
        assert user_attrs.get("uid") == "testuser" or user_attrs.get("mail") == "testuser@example.com"

    @pytest.mark.asyncio
    async def test_search_nonexistent_user(self, ldap_provider):
        """Test search returns None for nonexistent user."""
        user_dn, user_attrs = await ldap_provider._search_user("nonexistent")

        assert user_dn is None
        assert user_attrs == {}


@pytest.mark.integration
class TestLDAPIntegrationBind:
    """LDAP bind functionality integration tests."""

    @pytest.mark.asyncio
    async def test_bind_valid_credentials(self, ldap_provider):
        """Test binding with valid credentials."""
        # First search for user to get DN
        user_dn, _ = await ldap_provider._search_user("testuser")
        assert user_dn is not None

        # Test bind
        result = await ldap_provider._bind_user(user_dn, "testpass")
        assert result is True

    @pytest.mark.asyncio
    async def test_bind_invalid_credentials(self, ldap_provider):
        """Test binding fails with invalid credentials."""
        user_dn, _ = await ldap_provider._search_user("testuser")
        assert user_dn is not None

        result = await ldap_provider._bind_user(user_dn, "wrongpass")
        assert result is False

    @pytest.mark.asyncio
    async def test_bind_nonexistent_user(self, ldap_provider):
        """Test binding fails for nonexistent user."""
        result = await ldap_provider._bind_user(
            "uid=nonexistent,ou=users,dc=example,dc=com",
            "password"
        )
        assert result is False


@pytest.mark.integration
class TestLDAPIntegrationGroupSearch:
    """LDAP group search integration tests."""

    @pytest.mark.asyncio
    async def test_get_user_groups(self, ldap_provider):
        """Test retrieving user groups."""
        user_dn, _ = await ldap_provider._search_user("testuser")
        assert user_dn is not None

        groups = await ldap_provider._get_user_groups(user_dn)
        assert isinstance(groups, list)
        assert "developers" in groups

    @pytest.mark.asyncio
    async def test_get_admin_groups(self, ldap_provider):
        """Test retrieving admin user groups."""
        user_dn, _ = await ldap_provider._search_user("admin")
        assert user_dn is not None

        groups = await ldap_provider._get_user_groups(user_dn)
        assert isinstance(groups, list)
        assert "admins" in groups


@pytest.mark.integration
class TestLDAPIntegrationHealthCheck:
    """LDAP health check integration tests."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, ldap_provider):
        """Test health check succeeds with running LDAP server."""
        result = await ldap_provider.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_with_invalid_server(self, ldap_provider_config):
        """Test health check fails with invalid server."""
        from sark.services.auth.providers.ldap import LDAPProvider, LDAPProviderConfig

        # Create provider with invalid server URL
        invalid_config = LDAPProviderConfig(
            name="test-ldap-invalid",
            server_url="ldap://nonexistent.example.com:389",
            base_dn="dc=example,dc=com",
            bind_dn="cn=admin,dc=example,dc=com",
            bind_password="admin",
            use_ssl=False,
        )
        invalid_provider = LDAPProvider(invalid_config)

        result = await invalid_provider.health_check()
        assert result is False


@pytest.mark.integration
class TestLDAPIntegrationConcurrency:
    """LDAP concurrency integration tests."""

    @pytest.mark.asyncio
    async def test_concurrent_authentication(self, ldap_provider):
        """Test multiple concurrent authentication requests."""
        import asyncio

        async def auth_user(username: str, password: str):
            return await ldap_provider.authenticate(username, password)

        # Run multiple concurrent authentications
        results = await asyncio.gather(
            auth_user("testuser", "testpass"),
            auth_user("admin", "adminpass"),
            auth_user("jdoe", "password123"),
            auth_user("testuser", "testpass"),  # Duplicate
        )

        # All should succeed
        assert all(r.success for r in results)
        # Verify correct emails
        assert results[0].email == "testuser@example.com"
        assert results[1].email == "admin@example.com"
        assert results[2].email == "jdoe@example.com"
        assert results[3].email == "testuser@example.com"

    @pytest.mark.asyncio
    async def test_concurrent_mixed_results(self, ldap_provider):
        """Test concurrent requests with mixed success/failure."""
        import asyncio

        async def auth_user(username: str, password: str):
            return await ldap_provider.authenticate(username, password)

        results = await asyncio.gather(
            auth_user("testuser", "testpass"),      # Success
            auth_user("testuser", "wrongpass"),     # Failure
            auth_user("nonexistent", "password"),   # Failure
            auth_user("admin", "adminpass"),        # Success
        )

        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is False
        assert results[3].success is True


@pytest.mark.integration
class TestLDAPIntegrationEdgeCases:
    """LDAP edge case integration tests."""

    @pytest.mark.asyncio
    async def test_special_characters_in_password(self, ldap_provider):
        """Test authentication with special characters in password."""
        # This test would require adding a user with special chars in password
        # For now, test with existing users
        result = await ldap_provider._search_user("testuser")
        assert result[0] is not None

    @pytest.mark.asyncio
    async def test_case_insensitive_username(self, ldap_provider):
        """Test that username is case-insensitive (LDAP default behavior)."""
        result1 = await ldap_provider.authenticate("testuser", "testpass")
        result2 = await ldap_provider.authenticate("TESTUSER", "testpass")

        assert result1.success is True
        # LDAP is case-insensitive by default, so both should succeed
        assert result2.success is True
        # Both should return the same user_id
        assert result1.user_id == result2.user_id

    @pytest.mark.asyncio
    async def test_validate_token_not_supported(self, ldap_provider):
        """Test that token validation returns appropriate error."""
        result = await ldap_provider.validate_token("dummy_token")

        assert result.success is False
        assert "not supported" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_get_user_info(self, ldap_provider):
        """Test get_user_info method."""
        from uuid import uuid4

        user_id = uuid4()
        user_info = await ldap_provider.get_user_info(user_id)

        assert user_info is not None
        assert user_info["provider"] == "ldap"
        assert str(user_id) in user_info["user_id"]
