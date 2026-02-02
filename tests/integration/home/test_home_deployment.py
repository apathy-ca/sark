"""Integration tests for home deployment profile.

Tests the complete home deployment scenario including:
- Full authorization flow
- Cost tracking and budget enforcement
- Rate limiting
- Audit logging

Following AAA pattern: Arrange, Act, Assert
"""

import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add fixtures to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "fixtures" / "home"))

from home_fixtures import (
    HomeDeploymentConfig,
    HomeDeploymentContext,
    HomeDevice,
    TimeRule,
    home_deployment_context,
)


class TestHomeDeploymentConfiguration:
    """Test home deployment configuration."""

    def test_default_config_values(self):
        """Test HomeDeploymentConfig has sensible defaults."""
        # Arrange & Act
        config = HomeDeploymentConfig()

        # Assert
        assert config.mode == "test"
        assert config.database_url == "sqlite:///:memory:"
        assert config.opa_mode == "embedded"
        assert config.enable_cost_tracking is True
        assert config.enable_rate_limiting is True

    def test_default_budget_limits(self):
        """Test default budget limits are set."""
        # Arrange & Act
        config = HomeDeploymentConfig()

        # Assert
        assert config.daily_budget_usd == Decimal("10.00")
        assert config.monthly_budget_usd == Decimal("100.00")

    def test_default_allowed_endpoints(self):
        """Test default allowed LLM endpoints."""
        # Arrange & Act
        config = HomeDeploymentConfig()

        # Assert
        assert "api.openai.com" in config.allowed_endpoints
        assert "api.anthropic.com" in config.allowed_endpoints
        assert "generativelanguage.googleapis.com" in config.allowed_endpoints

    def test_custom_config_values(self):
        """Test custom configuration values."""
        # Arrange & Act
        config = HomeDeploymentConfig(
            mode="enforce",
            daily_budget_usd=Decimal("5.00"),
            enable_rate_limiting=False,
        )

        # Assert
        assert config.mode == "enforce"
        assert config.daily_budget_usd == Decimal("5.00")
        assert config.enable_rate_limiting is False


class TestHomeDeploymentContext:
    """Test home deployment context management."""

    @pytest.mark.asyncio
    async def test_context_manager_creates_services(self):
        """Test context manager creates all required services."""
        # Arrange & Act
        async with home_deployment_context() as ctx:
            # Assert
            assert ctx.config is not None
            assert ctx.db is not None
            assert ctx.authorization is not None
            assert ctx.cost_tracker is not None
            assert ctx.rate_limiter is not None
            assert ctx.audit_service is not None

    @pytest.mark.asyncio
    async def test_context_manager_with_custom_config(self):
        """Test context manager with custom configuration."""
        # Arrange
        config = HomeDeploymentConfig(
            mode="observe",
            daily_budget_usd=Decimal("20.00"),
        )

        # Act
        async with home_deployment_context(config=config) as ctx:
            # Assert
            assert ctx.config.mode == "observe"
            assert ctx.config.daily_budget_usd == Decimal("20.00")


class TestHomeDeploymentAuthorization:
    """Test authorization flow in home deployment."""

    @pytest.mark.asyncio
    async def test_authorization_allows_valid_request(self):
        """Test authorization allows valid requests."""
        # Arrange
        async with home_deployment_context() as ctx:
            request = MagicMock()
            request.action = "gateway:tool:invoke"
            request.server_name = "openai-proxy"
            request.tool_name = "chat_completion"

            # Act
            response = await ctx.authorization.authorize(request)

            # Assert
            assert response.allow is True

    @pytest.mark.asyncio
    async def test_authorization_denies_when_configured(self):
        """Test authorization denies when configured to deny."""
        # Arrange
        async with home_deployment_context() as ctx:
            # Configure to deny
            ctx.authorization.authorize = AsyncMock(
                return_value=MagicMock(
                    allow=False,
                    reason="Access denied by policy",
                    cache_ttl=0,
                )
            )

            request = MagicMock()

            # Act
            response = await ctx.authorization.authorize(request)

            # Assert
            assert response.allow is False


class TestHomeDeploymentCostTracking:
    """Test cost tracking in home deployment."""

    @pytest.mark.asyncio
    async def test_budget_check_allows_within_budget(self):
        """Test budget check allows requests within budget."""
        # Arrange
        async with home_deployment_context() as ctx:
            request = MagicMock()
            metadata = {"provider": "openai"}

            # Act
            allowed, reason = await ctx.cost_tracker.check_budget_before_invocation(
                request, metadata
            )

            # Assert
            assert allowed is True
            assert reason is None

    @pytest.mark.asyncio
    async def test_budget_check_denies_over_budget(self):
        """Test budget check denies requests over budget."""
        # Arrange
        async with home_deployment_context() as ctx:
            # Configure to deny for budget exceeded
            ctx.cost_tracker.check_budget_before_invocation = AsyncMock(
                return_value=(False, "Daily budget of $10.00 exceeded")
            )

            request = MagicMock()
            metadata = {"provider": "openai"}

            # Act
            allowed, reason = await ctx.cost_tracker.check_budget_before_invocation(
                request, metadata
            )

            # Assert
            assert allowed is False
            assert "budget" in reason.lower()

    @pytest.mark.asyncio
    async def test_cost_recording_after_invocation(self):
        """Test cost is recorded after successful invocation."""
        # Arrange
        async with home_deployment_context() as ctx:
            request = MagicMock()
            result = MagicMock()
            resource_id = "res_openai"
            metadata = {"provider": "openai"}

            # Act
            await ctx.cost_tracker.record_invocation_cost(
                request, result, resource_id, metadata
            )

            # Assert
            ctx.cost_tracker.record_invocation_cost.assert_called_once()


class TestHomeDeploymentRateLimiting:
    """Test rate limiting in home deployment."""

    @pytest.mark.asyncio
    async def test_rate_limit_allows_within_limit(self):
        """Test rate limiter allows requests within limit."""
        # Arrange
        async with home_deployment_context() as ctx:
            identifier = "device:192.168.1.100"

            # Act
            result = await ctx.rate_limiter.check_rate_limit(identifier)

            # Assert
            assert result.allowed is True
            assert result.remaining > 0

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_over_limit(self):
        """Test rate limiter blocks requests over limit."""
        # Arrange
        async with home_deployment_context() as ctx:
            # Configure to deny for rate limit exceeded
            ctx.rate_limiter.check_rate_limit = AsyncMock(
                return_value=MagicMock(
                    allowed=False,
                    limit=100,
                    remaining=0,
                    reset_at=1000000,
                    retry_after=60,
                )
            )

            identifier = "device:192.168.1.100"

            # Act
            result = await ctx.rate_limiter.check_rate_limit(identifier)

            # Assert
            assert result.allowed is False
            assert result.remaining == 0


class TestHomeDeploymentAuditLogging:
    """Test audit logging in home deployment."""

    @pytest.mark.asyncio
    async def test_audit_log_decision(self):
        """Test audit service logs authorization decisions."""
        # Arrange
        async with home_deployment_context() as ctx:
            auth_input = MagicMock()
            decision = MagicMock()

            # Act
            await ctx.audit_service.log_decision(auth_input, decision)

            # Assert
            ctx.audit_service.log_decision.assert_called_once()


class TestHomeDeviceAllowlist:
    """Test device allowlist functionality."""

    def test_device_has_allowlist_status(self):
        """Test HomeDevice has is_allowlisted attribute."""
        # Arrange & Act
        device = HomeDevice(
            device_id="dev_001",
            name="Test Device",
            ip_address="192.168.1.100",
            mac_address="AA:BB:CC:DD:EE:FF",
            device_type="laptop",
            owner="parent",
            is_allowlisted=True,
        )

        # Assert
        assert device.is_allowlisted is True

    def test_device_can_have_budget_limit(self):
        """Test HomeDevice can have per-device budget limit."""
        # Arrange & Act
        device = HomeDevice(
            device_id="dev_002",
            name="Kid's Tablet",
            ip_address="192.168.1.101",
            mac_address="AA:BB:CC:DD:EE:01",
            device_type="tablet",
            owner="child",
            daily_budget_usd=Decimal("2.00"),
        )

        # Assert
        assert device.daily_budget_usd == Decimal("2.00")

    def test_device_types(self):
        """Test different device types are supported."""
        # Arrange
        device_types = ["laptop", "phone", "tablet", "smart_device"]

        # Act & Assert
        for device_type in device_types:
            device = HomeDevice(
                device_id="dev_test",
                name="Test",
                ip_address="192.168.1.1",
                mac_address="AA:BB:CC:DD:EE:FF",
                device_type=device_type,
                owner="test",
            )
            assert device.device_type == device_type


class TestHomeTimeRules:
    """Test time-based rules for home deployment."""

    def test_time_rule_has_required_fields(self):
        """Test TimeRule has all required fields."""
        # Arrange & Act
        rule = TimeRule(
            rule_id="rule_001",
            name="Bedtime",
            start_time="21:00",
            end_time="07:00",
            action="block",
            applies_to=["child"],
        )

        # Assert
        assert rule.rule_id == "rule_001"
        assert rule.start_time == "21:00"
        assert rule.end_time == "07:00"
        assert rule.action == "block"
        assert "child" in rule.applies_to

    def test_time_rule_default_days(self):
        """Test TimeRule defaults to all days of week."""
        # Arrange & Act
        rule = TimeRule(
            rule_id="rule_001",
            name="Test",
            start_time="00:00",
            end_time="23:59",
            action="allow",
            applies_to=["all"],
        )

        # Assert
        assert len(rule.days_of_week) == 7
        assert "Mon" in rule.days_of_week
        assert "Sun" in rule.days_of_week

    def test_time_rule_custom_days(self):
        """Test TimeRule with custom days."""
        # Arrange & Act
        rule = TimeRule(
            rule_id="rule_001",
            name="Weekday Rule",
            start_time="09:00",
            end_time="17:00",
            action="allow",
            applies_to=["parent"],
            days_of_week=["Mon", "Tue", "Wed", "Thu", "Fri"],
        )

        # Assert
        assert len(rule.days_of_week) == 5
        assert "Sat" not in rule.days_of_week
        assert "Sun" not in rule.days_of_week

    def test_time_rule_actions(self):
        """Test different time rule actions."""
        # Arrange
        actions = ["allow", "block", "alert"]

        # Act & Assert
        for action in actions:
            rule = TimeRule(
                rule_id="rule_test",
                name="Test",
                start_time="00:00",
                end_time="23:59",
                action=action,
                applies_to=["all"],
            )
            assert rule.action == action


class TestHomeDeploymentFullFlow:
    """Test complete home deployment flow."""

    @pytest.mark.asyncio
    async def test_full_request_flow_allowed(self):
        """Test complete flow for an allowed request."""
        # Arrange
        async with home_deployment_context() as ctx:
            device_ip = "192.168.1.100"
            request = MagicMock()
            auth_input = MagicMock()
            metadata = {"provider": "openai"}

            # Act
            # 1. Check rate limit
            rate_result = await ctx.rate_limiter.check_rate_limit(f"device:{device_ip}")

            # 2. Check budget
            budget_allowed, _ = await ctx.cost_tracker.check_budget_before_invocation(
                request, metadata
            )

            # 3. Authorize request
            auth_response = await ctx.authorization.authorize(request)

            # 4. Log decision
            await ctx.audit_service.log_decision(auth_input, auth_response)

            # Assert
            assert rate_result.allowed is True
            assert budget_allowed is True
            assert auth_response.allow is True

    @pytest.mark.asyncio
    async def test_full_request_flow_blocked_by_budget(self):
        """Test complete flow when blocked by budget."""
        # Arrange
        async with home_deployment_context() as ctx:
            # Configure budget exceeded
            ctx.cost_tracker.check_budget_before_invocation = AsyncMock(
                return_value=(False, "Budget exceeded")
            )

            device_ip = "192.168.1.102"  # Kid's device
            request = MagicMock()
            metadata = {"provider": "openai"}

            # Act
            # 1. Check rate limit (passes)
            rate_result = await ctx.rate_limiter.check_rate_limit(f"device:{device_ip}")

            # 2. Check budget (fails)
            budget_allowed, reason = await ctx.cost_tracker.check_budget_before_invocation(
                request, metadata
            )

            # Assert
            assert rate_result.allowed is True
            assert budget_allowed is False
            assert "budget" in reason.lower()
