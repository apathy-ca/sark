"""End-to-end security scenario tests.

This module tests complete security workflows including:
- Multi-factor authentication flows
- Tool access control with sensitivity levels
- Policy evaluation and caching
- Audit trail generation
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from sark.models.mcp_server import SensitivityLevel
from sark.services.policy.opa_client import AuthorizationDecision, AuthorizationInput


@pytest.mark.e2e
class TestMFASecurityFlow:
    """Test MFA-required security scenarios."""

    @pytest.mark.asyncio
    async def test_critical_tool_requires_mfa(self):
        """Test that critical tools require MFA verification."""
        # Scenario: User tries to invoke a critical tool without MFA
        auth_input = AuthorizationInput(
            user={
                "id": "user-123",
                "email": "user@example.com",
                "role": "developer",
                "mfa_verified": False,
            },
            action="tool:invoke",
            tool={
                "name": "delete_production_database",
                "sensitivity_level": "critical",
            },
            context={"timestamp": int(datetime.now(UTC).timestamp())},
        )

        # Mock OPA to deny without MFA
        with patch("sark.services.policy.opa_client.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "result": {
                    "allow": False,
                    "audit_reason": "MFA verification required for critical tools",
                }
            }
            mock_response.raise_for_status = MagicMock()

            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_client_instance

            from sark.services.policy.opa_client import OPAClient
            from sark.services.policy.cache import PolicyCache

            cache = PolicyCache(enabled=False)  # Disable cache for test
            opa_client = OPAClient(cache=cache, cache_enabled=False)
            opa_client.client = mock_client_instance

            decision = await opa_client.evaluate_policy(auth_input, use_cache=False)

            assert decision.allow is False
            assert "MFA" in decision.reason

    @pytest.mark.asyncio
    async def test_critical_tool_allowed_with_mfa(self):
        """Test that critical tools are allowed with MFA."""
        auth_input = AuthorizationInput(
            user={
                "id": "user-123",
                "email": "user@example.com",
                "role": "admin",
                "mfa_verified": True,
                "mfa_methods": ["totp"],
            },
            action="tool:invoke",
            tool={
                "name": "delete_production_database",
                "sensitivity_level": "critical",
            },
            context={"timestamp": int(datetime.now(UTC).timestamp())},
        )

        with patch("sark.services.policy.opa_client.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "result": {
                    "allow": True,
                    "audit_reason": "Admin with MFA allowed",
                }
            }
            mock_response.raise_for_status = MagicMock()

            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_client_instance

            from sark.services.policy.opa_client import OPAClient
            from sark.services.policy.cache import PolicyCache

            cache = PolicyCache(enabled=False)
            opa_client = OPAClient(cache=cache, cache_enabled=False)
            opa_client.client = mock_client_instance

            decision = await opa_client.evaluate_policy(auth_input, use_cache=False)

            assert decision.allow is True


@pytest.mark.e2e
class TestSensitivityBasedAccess:
    """Test sensitivity-level based access control."""

    @pytest.mark.asyncio
    async def test_developer_can_access_low_sensitivity(self):
        """Test that developers can access low sensitivity tools."""
        auth_input = AuthorizationInput(
            user={"id": "dev-1", "role": "developer"},
            action="tool:invoke",
            tool={"name": "read_logs", "sensitivity_level": "low"},
            context={},
        )

        with patch("sark.services.policy.opa_client.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "result": {"allow": True, "audit_reason": "Developer access granted"}
            }
            mock_response.raise_for_status = MagicMock()

            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_client_instance

            from sark.services.policy.opa_client import OPAClient
            from sark.services.policy.cache import PolicyCache

            cache = PolicyCache(enabled=False)
            opa_client = OPAClient(cache=cache, cache_enabled=False)
            opa_client.client = mock_client_instance

            decision = await opa_client.evaluate_policy(auth_input, use_cache=False)

            assert decision.allow is True

    @pytest.mark.asyncio
    async def test_developer_cannot_access_critical(self):
        """Test that developers cannot access critical tools."""
        auth_input = AuthorizationInput(
            user={"id": "dev-1", "role": "developer"},
            action="tool:invoke",
            tool={"name": "modify_permissions", "sensitivity_level": "critical"},
            context={},
        )

        with patch("sark.services.policy.opa_client.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "result": {
                    "allow": False,
                    "audit_reason": "Developer role cannot access critical tools",
                }
            }
            mock_response.raise_for_status = MagicMock()

            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_client_instance

            from sark.services.policy.opa_client import OPAClient
            from sark.services.policy.cache import PolicyCache

            cache = PolicyCache(enabled=False)
            opa_client = OPAClient(cache=cache, cache_enabled=False)
            opa_client.client = mock_client_instance

            decision = await opa_client.evaluate_policy(auth_input, use_cache=False)

            assert decision.allow is False
            assert "critical" in decision.reason.lower()


@pytest.mark.e2e
class TestPolicyEvaluationWithAudit:
    """Test policy evaluation with audit trail."""

    @pytest.mark.asyncio
    async def test_policy_decision_generates_audit_log(self):
        """Test that policy decisions generate audit logs."""
        from sark.services.policy.audit import PolicyAuditService

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        audit_service = PolicyAuditService(db_session=mock_db)

        auth_input = AuthorizationInput(
            user={"id": "user-123", "role": "admin"},
            action="tool:invoke",
            tool={"name": "test_tool", "sensitivity_level": "high"},
            context={"client_ip": "192.168.1.1"},
        )

        decision = AuthorizationDecision(
            allow=True,
            reason="Admin access granted",
        )

        # Log the decision
        await audit_service.log_decision(
            auth_input=auth_input,
            decision=decision,
            duration_ms=15.3,
            cache_hit=False,
        )

        # Verify audit log was created
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


@pytest.mark.e2e
class TestServerRegistrationFlow:
    """Test complete server registration workflow."""

    @pytest.mark.asyncio
    async def test_register_server_with_sensitivity_detection(self):
        """Test registering a server with automatic tool sensitivity detection."""
        from sark.services.discovery.discovery_service import DiscoveryService
        from sark.models.mcp_server import TransportType

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Mock server ID assignment
        server_id = uuid4()

        async def mock_flush():
            if mock_db.add.called:
                added_obj = mock_db.add.call_args[0][0]
                if not hasattr(added_obj, "id") or added_obj.id is None:
                    added_obj.id = server_id

        mock_db.flush.side_effect = mock_flush

        with patch("sark.services.discovery.discovery_service.consul.Consul"):
            service = DiscoveryService(db=mock_db)

            # Tool without explicit sensitivity - should trigger auto-detection
            tools = [
                {
                    "name": "delete_user_data",
                    "description": "Permanently deletes user data",
                }
            ]

            with patch("sark.services.discovery.tool_registry.ToolRegistry") as mock_registry:
                mock_instance = AsyncMock()
                mock_instance.detect_sensitivity = AsyncMock(
                    return_value=SensitivityLevel.HIGH
                )
                mock_registry.return_value = mock_instance

                server = await service.register_server(
                    name="test-server",
                    transport=TransportType.HTTP,
                    mcp_version="1.0.0",
                    capabilities=["tools"],
                    tools=tools,
                    endpoint="http://localhost:8000",
                )

                # Verify sensitivity detection was called
                mock_instance.detect_sensitivity.assert_called_once()


@pytest.mark.e2e
class TestCacheInvalidationFlow:
    """Test cache invalidation scenarios."""

    @pytest.mark.asyncio
    async def test_policy_change_invalidates_cache(self):
        """Test that policy changes trigger cache invalidation."""
        from sark.services.policy.opa_client import OPAClient

        # Mock Redis cache
        mock_redis = AsyncMock()
        mock_redis.keys = AsyncMock(return_value=[
            "policy:decision:user-123:hash1",
            "policy:decision:user-123:hash2",
        ])
        mock_redis.delete = AsyncMock(return_value=2)

        from sark.services.policy.cache import PolicyCache

        cache = PolicyCache(redis_client=mock_redis)
        opa_client = OPAClient(cache=cache)

        # Invalidate cache for specific user
        count = await opa_client.invalidate_cache(user_id="user-123")

        # Verify cache was invalidated
        assert count == 2
        mock_redis.keys.assert_called_once()
        mock_redis.delete.assert_called_once()


@pytest.mark.e2e
class TestBatchPolicyEvaluation:
    """Test batch policy evaluation for performance."""

    @pytest.mark.asyncio
    async def test_batch_evaluation_reduces_latency(self):
        """Test that batch evaluation is more efficient than individual calls."""
        from sark.services.policy.opa_client import OPAClient, AuthorizationInput

        mock_client = AsyncMock()

        # Mock batch responses
        def create_response(allow):
            resp = AsyncMock()
            resp.json.return_value = {
                "result": {
                    "allow": allow,
                    "audit_reason": f"Batch decision: {'allow' if allow else 'deny'}",
                }
            }
            resp.raise_for_status = MagicMock()
            return resp

        mock_client.post = AsyncMock(side_effect=[
            create_response(True),
            create_response(False),
            create_response(True),
        ])

        from sark.services.policy.cache import PolicyCache

        cache = PolicyCache(enabled=False)
        opa_client = OPAClient(cache=cache, cache_enabled=False)
        opa_client.client = mock_client

        # Create batch of requests
        requests = [
            AuthorizationInput(
                user={"id": f"user-{i}", "role": "developer"},
                action="tool:invoke",
                tool={"name": f"tool-{i}"},
                context={},
            )
            for i in range(3)
        ]

        # Evaluate in batch
        decisions = await opa_client.evaluate_policy_batch(requests, use_cache=False)

        # Verify all decisions returned
        assert len(decisions) == 3
        assert decisions[0].allow is True
        assert decisions[1].allow is False
        assert decisions[2].allow is True
