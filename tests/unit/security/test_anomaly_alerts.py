"""
Unit tests for anomaly alert management system

Tests cover:
- Alert configuration
- Anomaly processing and severity counting
- Alert level determination (critical/warning/none)
- Multi-channel alerting (PagerDuty, Slack, Email)
- Auto-suspend functionality
- Audit logging
- Error handling
"""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from sark.security.anomaly_alerts import (
    AlertConfig,
    AnomalyAlertManager,
)
from sark.security.behavioral_analyzer import (
    Anomaly,
    AnomalySeverity,
    AnomalyType,
    BehavioralAuditEvent,
)


class TestAlertConfig:
    """Test AlertConfig dataclass"""

    def test_default_config(self):
        """Test creating config with defaults"""
        config = AlertConfig()

        assert config.critical_high_count == 2
        assert config.warning_high_count == 1
        assert config.warning_medium_count == 3
        assert config.auto_suspend_enabled is False
        assert config.auto_suspend_on_critical is True
        assert config.pagerduty_enabled is False
        assert config.slack_enabled is True
        assert config.email_enabled is True

    def test_custom_config(self):
        """Test creating config with custom values"""
        config = AlertConfig(
            critical_high_count=3,
            warning_high_count=2,
            warning_medium_count=5,
            auto_suspend_enabled=True,
            auto_suspend_on_critical=False,
            pagerduty_enabled=True,
            slack_enabled=False,
            email_enabled=False,
        )

        assert config.critical_high_count == 3
        assert config.warning_high_count == 2
        assert config.warning_medium_count == 5
        assert config.auto_suspend_enabled is True
        assert config.auto_suspend_on_critical is False
        assert config.pagerduty_enabled is True
        assert config.slack_enabled is False
        assert config.email_enabled is False


class TestAnomalyAlertManager:
    """Test anomaly alert manager"""

    @pytest.fixture
    def mock_services(self):
        """Create mock service dependencies"""
        return {
            "audit_logger": AsyncMock(),
            "alert_service": AsyncMock(),
            "user_management": AsyncMock(),
        }

    @pytest.fixture
    def alert_manager(self, mock_services):
        """Create alert manager with default config"""
        return AnomalyAlertManager(
            audit_logger=mock_services["audit_logger"],
            alert_service=mock_services["alert_service"],
            user_management=mock_services["user_management"],
        )

    @pytest.fixture
    def sample_event(self):
        """Create sample audit event"""
        return BehavioralAuditEvent(
            user_id="user123",
            timestamp=datetime(2024, 1, 15, 10, 30),
            tool_name="database_query",
            sensitivity="high",
            result_size=1000,
            location="US-EAST",
            request_id="req-abc-123",
        )

    # Severity Counting Tests

    def test_count_by_severity_empty(self, alert_manager):
        """Test counting with no anomalies"""
        counts = alert_manager._count_by_severity([])

        assert counts["critical"] == 0
        assert counts["high"] == 0
        assert counts["medium"] == 0
        assert counts["low"] == 0

    def test_count_by_severity_mixed(self, alert_manager):
        """Test counting with mixed severity anomalies"""
        anomalies = [
            Anomaly(
                type=AnomalyType.UNUSUAL_TOOL,
                severity=AnomalySeverity.LOW,
                description="Low severity",
            ),
            Anomaly(
                type=AnomalyType.UNUSUAL_TIME,
                severity=AnomalySeverity.MEDIUM,
                description="Medium severity",
            ),
            Anomaly(
                type=AnomalyType.EXCESSIVE_DATA,
                severity=AnomalySeverity.HIGH,
                description="High severity",
            ),
            Anomaly(
                type=AnomalyType.EXCESSIVE_DATA,
                severity=AnomalySeverity.HIGH,
                description="Another high",
            ),
            Anomaly(
                type=AnomalyType.SENSITIVITY_ESCALATION,
                severity=AnomalySeverity.CRITICAL,
                description="Critical severity",
            ),
        ]

        counts = alert_manager._count_by_severity(anomalies)

        assert counts["critical"] == 1
        assert counts["high"] == 2
        assert counts["medium"] == 1
        assert counts["low"] == 1

    # Alert Level Determination Tests

    def test_determine_alert_level_none(self, alert_manager):
        """Test that low severity only returns 'none'"""
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 5}

        alert_level = alert_manager._determine_alert_level(counts)

        assert alert_level == "none"

    def test_determine_alert_level_critical_from_critical_severity(self, alert_manager):
        """Test that any critical severity triggers critical alert"""
        counts = {"critical": 1, "high": 0, "medium": 0, "low": 0}

        alert_level = alert_manager._determine_alert_level(counts)

        assert alert_level == "critical"

    def test_determine_alert_level_critical_from_multiple_high(self, alert_manager):
        """Test that 2+ high severity triggers critical alert"""
        counts = {"critical": 0, "high": 2, "medium": 0, "low": 0}

        alert_level = alert_manager._determine_alert_level(counts)

        assert alert_level == "critical"

    def test_determine_alert_level_critical_threshold_configurable(self):
        """Test that critical high count threshold is configurable"""
        config = AlertConfig(critical_high_count=3)
        manager = AnomalyAlertManager(config=config)

        # 2 high should not trigger critical with threshold=3
        counts = {"critical": 0, "high": 2, "medium": 0, "low": 0}
        assert manager._determine_alert_level(counts) == "warning"

        # 3 high should trigger critical
        counts = {"critical": 0, "high": 3, "medium": 0, "low": 0}
        assert manager._determine_alert_level(counts) == "critical"

    def test_determine_alert_level_warning_from_single_high(self, alert_manager):
        """Test that 1 high severity triggers warning alert"""
        counts = {"critical": 0, "high": 1, "medium": 0, "low": 0}

        alert_level = alert_manager._determine_alert_level(counts)

        assert alert_level == "warning"

    def test_determine_alert_level_warning_from_multiple_medium(self, alert_manager):
        """Test that 3+ medium severity triggers warning alert"""
        counts = {"critical": 0, "high": 0, "medium": 3, "low": 0}

        alert_level = alert_manager._determine_alert_level(counts)

        assert alert_level == "warning"

    def test_determine_alert_level_warning_threshold_configurable(self):
        """Test that warning thresholds are configurable"""
        config = AlertConfig(warning_medium_count=5)
        manager = AnomalyAlertManager(config=config)

        # 3 medium should not trigger warning with threshold=5
        counts = {"critical": 0, "high": 0, "medium": 3, "low": 0}
        assert manager._determine_alert_level(counts) == "none"

        # 5 medium should trigger warning
        counts = {"critical": 0, "high": 0, "medium": 5, "low": 0}
        assert manager._determine_alert_level(counts) == "warning"

    def test_determine_alert_level_none_below_thresholds(self, alert_manager):
        """Test that counts below thresholds return 'none'"""
        # 0 high, 2 medium - below thresholds
        counts = {"critical": 0, "high": 0, "medium": 2, "low": 1}

        alert_level = alert_manager._determine_alert_level(counts)

        assert alert_level == "none"

    # Process Anomalies Tests

    @pytest.mark.asyncio
    async def test_process_no_anomalies(self, alert_manager, sample_event):
        """Test processing with no anomalies"""
        result = await alert_manager.process_anomalies([], sample_event)

        assert result["action"] == "none"
        assert result["reason"] == "no anomalies detected"

    @pytest.mark.asyncio
    async def test_process_low_severity_only(
        self, alert_manager, sample_event, mock_services
    ):
        """Test processing low severity anomalies only logs"""
        anomalies = [
            Anomaly(
                type=AnomalyType.UNUSUAL_TOOL,
                severity=AnomalySeverity.LOW,
                description="Low severity",
            )
        ]

        result = await alert_manager.process_anomalies(anomalies, sample_event)

        assert result["action"] == "logged"
        assert result["alert_level"] == "none"
        assert result["anomaly_count"] == 1
        # Should log but not send alerts
        mock_services["audit_logger"].log_event.assert_called_once()
        mock_services["alert_service"].send_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_warning_level(
        self, alert_manager, sample_event, mock_services
    ):
        """Test processing warning level anomalies"""
        anomalies = [
            Anomaly(
                type=AnomalyType.EXCESSIVE_DATA,
                severity=AnomalySeverity.HIGH,
                description="High severity",
            )
        ]

        result = await alert_manager.process_anomalies(anomalies, sample_event)

        assert result["action"] == "alerted"
        assert result["alert_level"] == "warning"
        assert result["anomaly_count"] == 1
        assert result["severity_counts"]["high"] == 1

        # Should log and send warning alert
        mock_services["audit_logger"].log_event.assert_called_once()
        mock_services["alert_service"].send_alert.assert_called()

    @pytest.mark.asyncio
    async def test_process_critical_level(
        self, alert_manager, sample_event, mock_services
    ):
        """Test processing critical level anomalies"""
        anomalies = [
            Anomaly(
                type=AnomalyType.EXCESSIVE_DATA,
                severity=AnomalySeverity.HIGH,
                description="High 1",
            ),
            Anomaly(
                type=AnomalyType.SENSITIVITY_ESCALATION,
                severity=AnomalySeverity.HIGH,
                description="High 2",
            ),
        ]

        result = await alert_manager.process_anomalies(anomalies, sample_event)

        assert result["action"] == "alerted"
        assert result["alert_level"] == "critical"
        assert result["anomaly_count"] == 2
        assert result["severity_counts"]["high"] == 2

        # Should log and send critical alert
        mock_services["audit_logger"].log_event.assert_called_once()
        mock_services["alert_service"].send_alert.assert_called()

    @pytest.mark.asyncio
    async def test_process_with_metadata(
        self, alert_manager, sample_event, mock_services
    ):
        """Test that metadata is included in logging"""
        anomalies = [
            Anomaly(
                type=AnomalyType.UNUSUAL_TIME,
                severity=AnomalySeverity.MEDIUM,
                description="Medium",
            )
        ]

        metadata = {"ip_address": "192.168.1.1", "user_agent": "TestAgent"}

        await alert_manager.process_anomalies(anomalies, sample_event, metadata)

        # Verify metadata was passed to logging
        call_args = mock_services["audit_logger"].log_event.call_args[1]
        assert call_args["metadata"] == metadata

    # Auto-Suspend Tests

    @pytest.mark.asyncio
    async def test_auto_suspend_disabled_by_default(
        self, alert_manager, sample_event, mock_services
    ):
        """Test that auto-suspend is disabled by default"""
        anomalies = [
            Anomaly(
                type=AnomalyType.SENSITIVITY_ESCALATION,
                severity=AnomalySeverity.CRITICAL,
                description="Critical",
            )
        ]

        result = await alert_manager.process_anomalies(anomalies, sample_event)

        # Should not suspend
        assert result["action"] == "alerted"
        mock_services["user_management"].suspend_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_auto_suspend_on_critical(self, sample_event, mock_services):
        """Test auto-suspend when enabled"""
        config = AlertConfig(
            auto_suspend_enabled=True, auto_suspend_on_critical=True
        )
        manager = AnomalyAlertManager(
            audit_logger=mock_services["audit_logger"],
            alert_service=mock_services["alert_service"],
            user_management=mock_services["user_management"],
            config=config,
        )

        anomalies = [
            Anomaly(
                type=AnomalyType.SENSITIVITY_ESCALATION,
                severity=AnomalySeverity.CRITICAL,
                description="Critical",
            )
        ]

        result = await manager.process_anomalies(anomalies, sample_event)

        # Should suspend user
        assert result["action"] == "suspended"
        assert result["alert_level"] == "critical"
        mock_services["user_management"].suspend_user.assert_called_once()

        call_args = mock_services["user_management"].suspend_user.call_args[1]
        assert call_args["user_id"] == "user123"
        assert call_args["suspended_by"] == "system:anomaly_detection"
        assert "Auto-suspended" in call_args["reason"]

    @pytest.mark.asyncio
    async def test_auto_suspend_logs_event(self, sample_event, mock_services):
        """Test that auto-suspend logs to audit"""
        config = AlertConfig(
            auto_suspend_enabled=True, auto_suspend_on_critical=True
        )
        manager = AnomalyAlertManager(
            audit_logger=mock_services["audit_logger"],
            alert_service=mock_services["alert_service"],
            user_management=mock_services["user_management"],
            config=config,
        )

        anomalies = [
            Anomaly(
                type=AnomalyType.SENSITIVITY_ESCALATION,
                severity=AnomalySeverity.CRITICAL,
                description="Critical",
            )
        ]

        await manager.process_anomalies(anomalies, sample_event)

        # Should log both anomaly and suspension
        assert mock_services["audit_logger"].log_event.call_count == 2

        # Check suspension log
        suspension_call = [
            call
            for call in mock_services["audit_logger"].log_event.call_args_list
            if call[1].get("event_type") == "user_auto_suspended"
        ]
        assert len(suspension_call) == 1
        assert suspension_call[0][1]["user_id"] == "user123"

    @pytest.mark.asyncio
    async def test_suspend_user_without_user_management(
        self, alert_manager, sample_event, caplog
    ):
        """Test that suspend logs warning without user management service"""
        anomalies = [
            Anomaly(
                type=AnomalyType.SENSITIVITY_ESCALATION,
                severity=AnomalySeverity.CRITICAL,
                description="Critical",
            )
        ]

        # Create manager without user_management
        manager = AnomalyAlertManager(user_management=None)

        await manager._suspend_user("user123", anomalies, sample_event)

        assert "No user management service" in caplog.text

    @pytest.mark.asyncio
    async def test_suspend_user_handles_error(
        self, sample_event, mock_services, caplog
    ):
        """Test that suspend errors are caught and logged"""
        mock_services["user_management"].suspend_user.side_effect = Exception(
            "Suspend failed"
        )

        config = AlertConfig(
            auto_suspend_enabled=True, auto_suspend_on_critical=True
        )
        manager = AnomalyAlertManager(
            audit_logger=mock_services["audit_logger"],
            alert_service=mock_services["alert_service"],
            user_management=mock_services["user_management"],
            config=config,
        )

        anomalies = [
            Anomaly(
                type=AnomalyType.SENSITIVITY_ESCALATION,
                severity=AnomalySeverity.CRITICAL,
                description="Critical",
            )
        ]

        # Should not raise exception
        await manager.process_anomalies(anomalies, sample_event)

        assert "Failed to suspend user" in caplog.text

    # Audit Logging Tests

    @pytest.mark.asyncio
    async def test_log_anomalies_called(
        self, alert_manager, sample_event, mock_services
    ):
        """Test that anomalies are logged to audit system"""
        anomalies = [
            Anomaly(
                type=AnomalyType.UNUSUAL_TOOL,
                severity=AnomalySeverity.LOW,
                description="Test anomaly",
                baseline_value=["tool1", "tool2"],
                observed_value="unusual_tool",
                confidence=0.7,
            )
        ]

        await alert_manager.process_anomalies(anomalies, sample_event)

        mock_services["audit_logger"].log_event.assert_called_once()
        call_args = mock_services["audit_logger"].log_event.call_args[1]

        assert call_args["event_type"] == "anomaly_detected"
        assert call_args["user_id"] == "user123"
        assert call_args["tool_name"] == "database_query"
        assert call_args["alert_level"] == "none"
        assert call_args["anomaly_count"] == 1
        assert len(call_args["anomalies"]) == 1

        # Check anomaly details
        anomaly_data = call_args["anomalies"][0]
        assert anomaly_data["type"] == "unusual_tool"
        assert anomaly_data["severity"] == "low"
        assert anomaly_data["description"] == "Test anomaly"
        assert anomaly_data["confidence"] == 0.7

    @pytest.mark.asyncio
    async def test_log_anomalies_truncates_long_values(
        self, alert_manager, sample_event, mock_services
    ):
        """Test that long baseline/observed values are truncated"""
        long_value = "x" * 200

        anomalies = [
            Anomaly(
                type=AnomalyType.EXCESSIVE_DATA,
                severity=AnomalySeverity.HIGH,
                description="Test",
                baseline_value=long_value,
                observed_value=long_value,
            )
        ]

        await alert_manager.process_anomalies(anomalies, sample_event)

        call_args = mock_services["audit_logger"].log_event.call_args[1]
        anomaly_data = call_args["anomalies"][0]

        # Should be truncated to 100 chars
        assert len(anomaly_data["baseline"]) == 100
        assert len(anomaly_data["observed"]) == 100

    @pytest.mark.asyncio
    async def test_log_anomalies_without_audit_logger(self, sample_event):
        """Test that logging works without audit logger"""
        manager = AnomalyAlertManager(audit_logger=None)

        anomalies = [
            Anomaly(
                type=AnomalyType.UNUSUAL_TIME,
                severity=AnomalySeverity.MEDIUM,
                description="Test",
            )
        ]

        # Should not raise error
        await manager.process_anomalies(anomalies, sample_event)

    @pytest.mark.asyncio
    async def test_log_anomalies_handles_error(
        self, alert_manager, sample_event, mock_services, caplog
    ):
        """Test that logging errors are caught"""
        mock_services["audit_logger"].log_event.side_effect = Exception("Log failed")

        anomalies = [
            Anomaly(
                type=AnomalyType.UNUSUAL_DAY,
                severity=AnomalySeverity.LOW,
                description="Test",
            )
        ]

        # Should not raise exception
        await alert_manager.process_anomalies(anomalies, sample_event)

        assert "Failed to log anomalies" in caplog.text

    # Critical Alert Tests

    @pytest.mark.asyncio
    async def test_critical_alert_sends_to_pagerduty(
        self, sample_event, mock_services
    ):
        """Test critical alert sent to PagerDuty when enabled"""
        config = AlertConfig(pagerduty_enabled=True, slack_enabled=False)
        manager = AnomalyAlertManager(
            audit_logger=mock_services["audit_logger"],
            alert_service=mock_services["alert_service"],
            config=config,
        )

        anomalies = [
            Anomaly(
                type=AnomalyType.SENSITIVITY_ESCALATION,
                severity=AnomalySeverity.CRITICAL,
                description="Critical anomaly",
            )
        ]

        await manager.process_anomalies(anomalies, sample_event)

        # Verify PagerDuty alert was sent
        calls = mock_services["alert_service"].send_alert.call_args_list
        pagerduty_calls = [c for c in calls if c[1]["channel"] == "pagerduty"]

        assert len(pagerduty_calls) == 1
        call_args = pagerduty_calls[0][1]
        assert call_args["severity"] == "critical"
        assert "user123" in call_args["title"]
        assert call_args["details"]["user_id"] == "user123"
        assert call_args["details"]["anomaly_count"] == 1

    @pytest.mark.asyncio
    async def test_critical_alert_sends_to_slack(
        self, sample_event, mock_services
    ):
        """Test critical alert sent to Slack when enabled"""
        config = AlertConfig(slack_enabled=True, pagerduty_enabled=False)
        manager = AnomalyAlertManager(
            audit_logger=mock_services["audit_logger"],
            alert_service=mock_services["alert_service"],
            config=config,
        )

        anomalies = [
            Anomaly(
                type=AnomalyType.SENSITIVITY_ESCALATION,
                severity=AnomalySeverity.CRITICAL,
                description="Critical anomaly",
            )
        ]

        await manager.process_anomalies(anomalies, sample_event)

        # Verify Slack alert was sent
        calls = mock_services["alert_service"].send_alert.call_args_list
        slack_calls = [c for c in calls if c[1]["channel"] == "slack"]

        assert len(slack_calls) == 1
        call_args = slack_calls[0][1]
        assert call_args["severity"] == "critical"
        assert "🚨" in call_args["title"]

    @pytest.mark.asyncio
    async def test_critical_alert_without_alert_service(
        self, sample_event, caplog
    ):
        """Test critical alert logs warning without alert service"""
        manager = AnomalyAlertManager(alert_service=None)

        anomalies = [
            Anomaly(
                type=AnomalyType.SENSITIVITY_ESCALATION,
                severity=AnomalySeverity.CRITICAL,
                description="Critical",
            )
        ]

        await manager.process_anomalies(anomalies, sample_event)

        assert "No alert service configured" in caplog.text

    @pytest.mark.asyncio
    async def test_critical_alert_handles_error(
        self, sample_event, mock_services, caplog
    ):
        """Test that critical alert errors are caught"""
        mock_services["alert_service"].send_alert.side_effect = Exception(
            "Alert failed"
        )

        config = AlertConfig(slack_enabled=True)
        manager = AnomalyAlertManager(
            alert_service=mock_services["alert_service"], config=config
        )

        anomalies = [
            Anomaly(
                type=AnomalyType.SENSITIVITY_ESCALATION,
                severity=AnomalySeverity.CRITICAL,
                description="Critical",
            )
        ]

        # Should not raise exception
        await manager.process_anomalies(anomalies, sample_event)

        assert "Failed to send critical alert" in caplog.text

    # Warning Alert Tests

    @pytest.mark.asyncio
    async def test_warning_alert_sends_to_slack(
        self, alert_manager, sample_event, mock_services
    ):
        """Test warning alert sent to Slack"""
        anomalies = [
            Anomaly(
                type=AnomalyType.EXCESSIVE_DATA,
                severity=AnomalySeverity.HIGH,
                description="High severity",
            )
        ]

        await alert_manager.process_anomalies(anomalies, sample_event)

        # Verify Slack alert was sent
        calls = mock_services["alert_service"].send_alert.call_args_list
        slack_calls = [c for c in calls if c[1]["channel"] == "slack"]

        assert len(slack_calls) == 1
        call_args = slack_calls[0][1]
        assert call_args["severity"] == "warning"
        assert "⚠️" in call_args["title"]

    @pytest.mark.asyncio
    async def test_warning_alert_sends_to_email(
        self, alert_manager, sample_event, mock_services
    ):
        """Test warning alert sent to Email"""
        anomalies = [
            Anomaly(
                type=AnomalyType.UNUSUAL_TIME,
                severity=AnomalySeverity.MEDIUM,
                description="Unusual time",
            ),
            Anomaly(
                type=AnomalyType.UNUSUAL_DAY,
                severity=AnomalySeverity.MEDIUM,
                description="Unusual day",
            ),
            Anomaly(
                type=AnomalyType.UNUSUAL_TOOL,
                severity=AnomalySeverity.MEDIUM,
                description="Unusual tool",
            ),
        ]

        await alert_manager.process_anomalies(anomalies, sample_event)

        # Verify Email alert was sent
        calls = mock_services["alert_service"].send_alert.call_args_list
        email_calls = [c for c in calls if c[1]["channel"] == "email"]

        assert len(email_calls) == 1
        call_args = email_calls[0][1]
        assert call_args["severity"] == "warning"
        assert "user123" in call_args["title"]

    @pytest.mark.asyncio
    async def test_warning_alert_without_alert_service(
        self, sample_event, caplog
    ):
        """Test warning alert logs warning without alert service"""
        manager = AnomalyAlertManager(alert_service=None)

        anomalies = [
            Anomaly(
                type=AnomalyType.EXCESSIVE_DATA,
                severity=AnomalySeverity.HIGH,
                description="High",
            )
        ]

        await manager.process_anomalies(anomalies, sample_event)

        assert "No alert service configured" in caplog.text

    @pytest.mark.asyncio
    async def test_warning_alert_handles_error(
        self, sample_event, mock_services, caplog
    ):
        """Test that warning alert errors are caught"""
        mock_services["alert_service"].send_alert.side_effect = Exception(
            "Alert failed"
        )

        manager = AnomalyAlertManager(
            alert_service=mock_services["alert_service"]
        )

        anomalies = [
            Anomaly(
                type=AnomalyType.UNUSUAL_TIME,
                severity=AnomalySeverity.MEDIUM,
                description="Unusual time",
            ),
            Anomaly(
                type=AnomalyType.UNUSUAL_DAY,
                severity=AnomalySeverity.MEDIUM,
                description="Unusual day",
            ),
            Anomaly(
                type=AnomalyType.UNUSUAL_TOOL,
                severity=AnomalySeverity.MEDIUM,
                description="Unusual tool",
            ),
        ]

        # Should not raise exception
        await manager.process_anomalies(anomalies, sample_event)

        assert "Failed to send warning alert" in caplog.text

    # Anomaly Summary Tests

    def test_build_anomaly_summary(self, alert_manager):
        """Test building anomaly summary for alerts"""
        anomalies = [
            Anomaly(
                type=AnomalyType.UNUSUAL_TOOL,
                severity=AnomalySeverity.LOW,
                description="Unusual tool access",
                confidence=0.7,
            ),
            Anomaly(
                type=AnomalyType.EXCESSIVE_DATA,
                severity=AnomalySeverity.HIGH,
                description="Excessive data",
                confidence=0.95,
            ),
        ]

        summary = alert_manager._build_anomaly_summary(anomalies)

        assert len(summary) == 2
        assert summary[0]["type"] == "unusual_tool"
        assert summary[0]["severity"] == "low"
        assert summary[0]["description"] == "Unusual tool access"
        assert summary[0]["confidence"] == "70%"

        assert summary[1]["type"] == "excessive_data"
        assert summary[1]["severity"] == "high"
        assert summary[1]["confidence"] == "95%"

    def test_build_anomaly_summary_formats_confidence(self, alert_manager):
        """Test that confidence is formatted as percentage"""
        anomalies = [
            Anomaly(
                type=AnomalyType.RAPID_REQUESTS,
                severity=AnomalySeverity.MEDIUM,
                description="Rapid requests",
                confidence=0.856,
            )
        ]

        summary = alert_manager._build_anomaly_summary(anomalies)

        # Should be rounded to integer percentage
        assert summary[0]["confidence"] == "86%"

    # Integration Tests

    @pytest.mark.asyncio
    async def test_complete_flow_low_severity(
        self, alert_manager, sample_event, mock_services
    ):
        """Test complete flow for low severity anomalies"""
        anomalies = [
            Anomaly(
                type=AnomalyType.UNUSUAL_TOOL,
                severity=AnomalySeverity.LOW,
                description="Low",
            ),
            Anomaly(
                type=AnomalyType.UNUSUAL_DAY,
                severity=AnomalySeverity.LOW,
                description="Low",
            ),
        ]

        result = await alert_manager.process_anomalies(anomalies, sample_event)

        # Should log only, no alerts
        assert result["action"] == "logged"
        assert result["alert_level"] == "none"
        mock_services["audit_logger"].log_event.assert_called_once()
        mock_services["alert_service"].send_alert.assert_not_called()
        mock_services["user_management"].suspend_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_complete_flow_warning_severity(
        self, alert_manager, sample_event, mock_services
    ):
        """Test complete flow for warning severity anomalies"""
        anomalies = [
            Anomaly(
                type=AnomalyType.EXCESSIVE_DATA,
                severity=AnomalySeverity.HIGH,
                description="High",
            )
        ]

        result = await alert_manager.process_anomalies(anomalies, sample_event)

        # Should log and alert (Slack + Email)
        assert result["action"] == "alerted"
        assert result["alert_level"] == "warning"
        mock_services["audit_logger"].log_event.assert_called_once()
        assert mock_services["alert_service"].send_alert.call_count == 2
        mock_services["user_management"].suspend_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_complete_flow_critical_with_auto_suspend(
        self, sample_event, mock_services
    ):
        """Test complete flow for critical anomalies with auto-suspend"""
        config = AlertConfig(
            auto_suspend_enabled=True,
            auto_suspend_on_critical=True,
            pagerduty_enabled=True,
            slack_enabled=True,
        )
        manager = AnomalyAlertManager(
            audit_logger=mock_services["audit_logger"],
            alert_service=mock_services["alert_service"],
            user_management=mock_services["user_management"],
            config=config,
        )

        anomalies = [
            Anomaly(
                type=AnomalyType.SENSITIVITY_ESCALATION,
                severity=AnomalySeverity.CRITICAL,
                description="Critical",
            )
        ]

        result = await manager.process_anomalies(anomalies, sample_event)

        # Should log, alert (PagerDuty + Slack), and suspend
        assert result["action"] == "suspended"
        assert result["alert_level"] == "critical"
        assert mock_services["audit_logger"].log_event.call_count == 2  # Anomaly + suspension
        assert mock_services["alert_service"].send_alert.call_count == 2
        mock_services["user_management"].suspend_user.assert_called_once()
