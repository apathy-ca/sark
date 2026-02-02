"""
Unit tests for EnforcementService.
"""

import pytest

from sark.models.governance import AllowlistEntryType, TimeRuleAction
from sark.services.governance.enforcement import EnforcementService


class TestEnforcementService:
    """Tests for EnforcementService."""

    @pytest.mark.asyncio
    async def test_evaluate_default_allow(self, enforcement_service: EnforcementService):
        """Test evaluation returns allow by default (no rules)."""
        decision = await enforcement_service.evaluate(
            {"device_ip": "192.168.1.50"}
        )

        assert decision.allowed is True
        assert decision.decision_source == "opa"  # Falls through to OPA

    @pytest.mark.asyncio
    async def test_evaluate_emergency_override(
        self,
        enforcement_service: EnforcementService,
        emergency_service,
    ):
        """Test emergency override bypasses all policies."""
        # Activate emergency
        await emergency_service.activate(duration_minutes=60, reason="test")

        decision = await enforcement_service.evaluate(
            {"device_ip": "192.168.1.50"}
        )

        assert decision.allowed is True
        assert decision.decision_source == "emergency"

    @pytest.mark.asyncio
    async def test_evaluate_allowlist_device(
        self,
        enforcement_service: EnforcementService,
        allowlist_service,
    ):
        """Test allowlisted device bypasses policies."""
        # Add to allowlist
        await allowlist_service.add_device("192.168.1.50", name="admin-device")

        decision = await enforcement_service.evaluate(
            {"device_ip": "192.168.1.50"}
        )

        assert decision.allowed is True
        assert decision.decision_source == "allowlist"

    @pytest.mark.asyncio
    async def test_evaluate_allowlist_user(
        self,
        enforcement_service: EnforcementService,
        allowlist_service,
    ):
        """Test allowlisted user bypasses policies."""
        # Add user to allowlist
        await allowlist_service.add_entry(
            "admin@example.com",
            AllowlistEntryType.USER,
            name="admin-user",
        )

        decision = await enforcement_service.evaluate(
            {"user_id": "admin@example.com"}
        )

        assert decision.allowed is True
        assert decision.decision_source == "allowlist"

    @pytest.mark.asyncio
    async def test_evaluate_per_request_override(
        self,
        enforcement_service: EnforcementService,
        override_service,
    ):
        """Test per-request override with PIN."""
        # Create override
        await override_service.create_override(
            request_id="req-123",
            pin="1234",
        )

        decision = await enforcement_service.evaluate(
            {"request_id": "req-123", "override_pin": "1234"}
        )

        assert decision.allowed is True
        assert decision.decision_source == "override"

    @pytest.mark.asyncio
    async def test_evaluate_time_rule_blocks(
        self,
        enforcement_service: EnforcementService,
        time_rules_service,
    ):
        """Test time rule blocking."""
        # Add blocking rule for all times
        await time_rules_service.add_rule(
            name="always-block",
            start="00:00",
            end="23:59",
            action=TimeRuleAction.BLOCK,
        )

        decision = await enforcement_service.evaluate(
            {"device_ip": "192.168.1.50"}
        )

        assert decision.allowed is False
        assert decision.decision_source == "time_rule"
        assert decision.rule == "always-block"

    @pytest.mark.asyncio
    async def test_evaluate_time_rule_alert_allows(
        self,
        enforcement_service: EnforcementService,
        time_rules_service,
    ):
        """Test time rule with alert action allows request."""
        # Add alert rule
        await time_rules_service.add_rule(
            name="alert-only",
            start="00:00",
            end="23:59",
            action=TimeRuleAction.ALERT,
        )

        decision = await enforcement_service.evaluate(
            {"device_ip": "192.168.1.50"}
        )

        # Alert action should allow but not mark as time_rule source
        assert decision.allowed is True

    @pytest.mark.asyncio
    async def test_evaluate_priority_emergency_over_time_rule(
        self,
        enforcement_service: EnforcementService,
        emergency_service,
        time_rules_service,
    ):
        """Test emergency override takes priority over time rules."""
        # Add blocking time rule
        await time_rules_service.add_rule(
            name="always-block",
            start="00:00",
            end="23:59",
            action=TimeRuleAction.BLOCK,
        )

        # Activate emergency
        await emergency_service.activate(duration_minutes=60, reason="test")

        decision = await enforcement_service.evaluate(
            {"device_ip": "192.168.1.50"}
        )

        # Emergency should take priority
        assert decision.allowed is True
        assert decision.decision_source == "emergency"

    @pytest.mark.asyncio
    async def test_evaluate_priority_allowlist_over_time_rule(
        self,
        enforcement_service: EnforcementService,
        allowlist_service,
        time_rules_service,
    ):
        """Test allowlist takes priority over time rules."""
        # Add blocking time rule
        await time_rules_service.add_rule(
            name="always-block",
            start="00:00",
            end="23:59",
            action=TimeRuleAction.BLOCK,
        )

        # Add to allowlist
        await allowlist_service.add_device("192.168.1.50", name="admin-device")

        decision = await enforcement_service.evaluate(
            {"device_ip": "192.168.1.50"}
        )

        # Allowlist should take priority
        assert decision.allowed is True
        assert decision.decision_source == "allowlist"

    @pytest.mark.asyncio
    async def test_evaluate_simple(
        self,
        enforcement_service: EnforcementService,
        allowlist_service,
    ):
        """Test simple evaluation method."""
        await allowlist_service.add_device("192.168.1.50")

        result = await enforcement_service.evaluate_simple("192.168.1.50")
        assert result is True

        result = await enforcement_service.evaluate_simple("192.168.1.100")
        assert result is True  # Default allow (no blocking rules)

    @pytest.mark.asyncio
    async def test_evaluate_logs_decision(
        self,
        enforcement_service: EnforcementService,
    ):
        """Test evaluation logs decision to database."""
        await enforcement_service.evaluate(
            {"request_id": "req-123", "device_ip": "192.168.1.50"},
            log_decision=True,
        )

        # Check log was created
        logs = await enforcement_service.get_decision_log(request_id="req-123")
        assert len(logs) == 1
        assert logs[0].request_id == "req-123"

    @pytest.mark.asyncio
    async def test_evaluate_no_log(
        self,
        enforcement_service: EnforcementService,
    ):
        """Test evaluation without logging."""
        await enforcement_service.evaluate(
            {"request_id": "req-456", "device_ip": "192.168.1.50"},
            log_decision=False,
        )

        # Check no log was created
        logs = await enforcement_service.get_decision_log(request_id="req-456")
        assert len(logs) == 0

    @pytest.mark.asyncio
    async def test_get_decision_log_filters(
        self,
        enforcement_service: EnforcementService,
        allowlist_service,
        time_rules_service,
    ):
        """Test decision log filtering."""
        # Create mixed decisions
        await allowlist_service.add_device("192.168.1.50")
        await time_rules_service.add_rule(
            name="block",
            start="00:00",
            end="23:59",
            action=TimeRuleAction.BLOCK,
        )

        # Allowed (allowlist)
        await enforcement_service.evaluate({"device_ip": "192.168.1.50"})

        # Denied (time rule)
        await enforcement_service.evaluate({"device_ip": "192.168.1.100"})

        # Filter by allowed
        allowed_logs = await enforcement_service.get_decision_log(allowed=True)
        assert len(allowed_logs) == 1

        denied_logs = await enforcement_service.get_decision_log(allowed=False)
        assert len(denied_logs) == 1

    @pytest.mark.asyncio
    async def test_get_statistics(
        self,
        enforcement_service: EnforcementService,
        allowlist_service,
    ):
        """Test getting enforcement statistics."""
        await allowlist_service.add_device("192.168.1.50")

        # Make some decisions
        await enforcement_service.evaluate({"device_ip": "192.168.1.50"})
        await enforcement_service.evaluate({"device_ip": "192.168.1.51"})

        stats = await enforcement_service.get_statistics()
        assert stats["total_decisions"] == 2
        assert "allowed" in stats
        assert "denied" in stats
        assert "by_source" in stats

    @pytest.mark.asyncio
    async def test_evaluate_generates_request_id(
        self,
        enforcement_service: EnforcementService,
    ):
        """Test evaluation generates request ID if not provided."""
        await enforcement_service.evaluate({"device_ip": "192.168.1.50"})

        # Check log has a request ID
        logs = await enforcement_service.get_decision_log()
        assert len(logs) == 1
        assert logs[0].request_id is not None
