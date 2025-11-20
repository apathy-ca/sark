"""Tests for policy service."""

from uuid import uuid4

import pytest

from sark.services.policy.opa_client import AuthorizationInput, OPAClient


class TestOPAClient:
    """Tests for OPA client."""

    @pytest.mark.asyncio
    async def test_authorization_input_creation(self) -> None:
        """Test creating authorization input."""
        user_id = str(uuid4())
        auth_input = AuthorizationInput(
            user={
                "id": user_id,
                "email": "test@example.com",
                "role": "developer",
                "teams": ["team-1"],
            },
            action="tool:invoke",
            tool={
                "name": "test_tool",
                "sensitivity_level": "medium",
                "owner": user_id,
                "managers": ["team-1"],
            },
            context={"timestamp": 0},
        )

        assert auth_input.user["id"] == user_id
        assert auth_input.action == "tool:invoke"
        assert auth_input.tool["name"] == "test_tool"

    @pytest.mark.asyncio
    async def test_opa_client_fail_closed(self) -> None:
        """Test that OPA client fails closed on error."""
        # Use invalid OPA URL to trigger error
        client = OPAClient(opa_url="http://invalid-opa-host:9999")

        auth_input = AuthorizationInput(
            user={"id": "user-123", "role": "developer", "teams": []},
            action="tool:invoke",
            tool={"name": "test", "sensitivity_level": "high"},
            context={"timestamp": 0},
        )

        decision = await client.evaluate_policy(auth_input)

        # Should deny on error (fail closed)
        assert decision.allow is False
        assert "failed" in decision.reason.lower() or "error" in decision.reason.lower()

        await client.close()


class TestPolicyService:
    """Tests for policy management service."""

    def test_policy_service_placeholder(self) -> None:
        """Placeholder test - will be implemented with database fixtures."""
        # TODO: Implement with pytest-asyncio and database fixtures
        assert True
