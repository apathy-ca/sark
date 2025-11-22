"""Tests for SIEM error handler."""

import asyncio
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel
from sark.services.audit.siem.error_handler import (
    ErrorAlert,
    ErrorCategory,
    ErrorRecord,
    ErrorSeverity,
    FallbackLogger,
    RecoveryStrategy,
    SIEMErrorHandler,
    auth_failure_condition,
    critical_error_condition,
    high_error_rate_condition,
)


class TestErrorClassification:
    """Tests for error classification."""

    @pytest.fixture
    def handler(self, tmp_path: Path) -> SIEMErrorHandler:
        """Create error handler for testing."""
        return SIEMErrorHandler(fallback_log_dir=tmp_path, enable_fallback=True)

    def test_classify_network_error(self, handler: SIEMErrorHandler):
        """Test classification of network errors."""
        error = ConnectionError("Network unreachable")
        category, severity = handler.classify_error(error)
        assert category == ErrorCategory.NETWORK
        assert severity == ErrorSeverity.MEDIUM

    def test_classify_timeout_error(self, handler: SIEMErrorHandler):
        """Test classification of timeout errors."""
        error = TimeoutError("Request timed out")
        category, severity = handler.classify_error(error)
        assert category == ErrorCategory.TIMEOUT
        assert severity == ErrorSeverity.MEDIUM

    def test_classify_auth_error(self, handler: SIEMErrorHandler):
        """Test classification of authentication errors."""
        error = Exception("401 unauthorized")
        category, severity = handler.classify_error(error)
        assert category == ErrorCategory.AUTHENTICATION
        assert severity == ErrorSeverity.HIGH

    def test_classify_rate_limit_error(self, handler: SIEMErrorHandler):
        """Test classification of rate limit errors."""
        error = Exception("429 too many requests")
        category, severity = handler.classify_error(error)
        assert category == ErrorCategory.RATE_LIMIT
        assert severity == ErrorSeverity.LOW

    def test_classify_validation_error(self, handler: SIEMErrorHandler):
        """Test classification of validation errors."""
        error = ValueError("Invalid data format")
        category, severity = handler.classify_error(error)
        assert category == ErrorCategory.VALIDATION
        assert severity == ErrorSeverity.MEDIUM

    def test_classify_unknown_error(self, handler: SIEMErrorHandler):
        """Test classification of unknown errors."""
        error = Exception("Something went wrong")
        category, severity = handler.classify_error(error)
        assert category == ErrorCategory.UNKNOWN
        assert severity == ErrorSeverity.MEDIUM


class TestRecoveryStrategy:
    """Tests for recovery strategy determination."""

    @pytest.fixture
    def handler(self, tmp_path: Path) -> SIEMErrorHandler:
        """Create error handler for testing."""
        return SIEMErrorHandler(fallback_log_dir=tmp_path)

    def test_critical_error_strategy(self, handler: SIEMErrorHandler):
        """Test strategy for critical errors."""
        strategy = handler.get_recovery_strategy(ErrorCategory.UNKNOWN, ErrorSeverity.CRITICAL)
        assert strategy == RecoveryStrategy.ALERT

    def test_auth_error_strategy(self, handler: SIEMErrorHandler):
        """Test strategy for authentication errors."""
        strategy = handler.get_recovery_strategy(ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH)
        assert strategy == RecoveryStrategy.CIRCUIT_BREAK

    def test_rate_limit_strategy(self, handler: SIEMErrorHandler):
        """Test strategy for rate limit errors."""
        strategy = handler.get_recovery_strategy(ErrorCategory.RATE_LIMIT, ErrorSeverity.LOW)
        assert strategy == RecoveryStrategy.RETRY

    def test_validation_error_strategy(self, handler: SIEMErrorHandler):
        """Test strategy for validation errors."""
        strategy = handler.get_recovery_strategy(ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM)
        assert strategy == RecoveryStrategy.SKIP

    def test_network_error_strategy(self, handler: SIEMErrorHandler):
        """Test strategy for network errors."""
        strategy = handler.get_recovery_strategy(ErrorCategory.NETWORK, ErrorSeverity.MEDIUM)
        assert strategy == RecoveryStrategy.FALLBACK


class TestFallbackLogger:
    """Tests for fallback file logger."""

    @pytest.fixture
    def logger(self, tmp_path: Path) -> FallbackLogger:
        """Create fallback logger for testing."""
        return FallbackLogger(tmp_path, max_file_size_mb=1)

    @pytest.fixture
    def event(self) -> AuditEvent:
        """Create test audit event."""
        return AuditEvent(
            id=uuid4(),
            timestamp=datetime.now(UTC),
            event_type=AuditEventType.TOOL_INVOKED,
            severity=SeverityLevel.MEDIUM,
            user_email="test@example.com",
            tool_name="bash",
            details={"command": "ls"},
        )

    def test_create_log_file(self, logger: FallbackLogger, event: AuditEvent):
        """Test log file creation."""
        logger.log_event(event)
        assert logger.current_file is not None
        assert logger.current_file.exists()
        assert logger.events_logged == 1

    def test_log_event_content(self, logger: FallbackLogger, event: AuditEvent):
        """Test logged event content."""
        logger.log_event(event)

        with open(logger.current_file) as f:
            line = f.readline()
            data = json.loads(line)

        assert data["id"] == str(event.id)
        assert data["event_type"] == event.event_type.value
        assert data["user_email"] == event.user_email

    def test_log_multiple_events(self, logger: FallbackLogger, event: AuditEvent):
        """Test logging multiple events."""
        logger.log_event(event)
        logger.log_event(event)
        logger.log_event(event)

        assert logger.events_logged == 3

        with open(logger.current_file) as f:
            lines = f.readlines()
        assert len(lines) == 3

    def test_get_stats(self, logger: FallbackLogger, event: AuditEvent):
        """Test getting logger statistics."""
        logger.log_event(event)
        stats = logger.get_stats()

        assert "log_dir" in stats
        assert "current_file" in stats
        assert stats["events_logged"] == 1
        assert stats["current_file_size_mb"] > 0


class TestErrorHandler:
    """Tests for SIEM error handler."""

    @pytest.fixture
    def handler(self, tmp_path: Path) -> SIEMErrorHandler:
        """Create error handler for testing."""
        return SIEMErrorHandler(fallback_log_dir=tmp_path, max_error_history=10)

    @pytest.fixture
    def event(self) -> AuditEvent:
        """Create test audit event."""
        return AuditEvent(
            id=uuid4(),
            timestamp=datetime.now(UTC),
            event_type=AuditEventType.TOOL_INVOKED,
            severity=SeverityLevel.MEDIUM,
            user_email="test@example.com",
            tool_name="bash",
        )

    @pytest.mark.asyncio
    async def test_handle_error_basic(self, handler: SIEMErrorHandler):
        """Test basic error handling."""
        error = Exception("Test error")
        strategy = await handler.handle_error(error)

        assert isinstance(strategy, RecoveryStrategy)
        assert handler.total_errors == 1
        assert len(handler.error_history) == 1

    @pytest.mark.asyncio
    async def test_handle_error_with_event(self, handler: SIEMErrorHandler, event: AuditEvent):
        """Test error handling with event."""
        error = ConnectionError("Network error")
        strategy = await handler.handle_error(error, event=event)

        assert strategy == RecoveryStrategy.FALLBACK
        assert handler.total_errors == 1
        # Check fallback was triggered
        assert handler.fallback_count == 1

    @pytest.mark.asyncio
    async def test_error_metrics_tracking(self, handler: SIEMErrorHandler):
        """Test error metrics are tracked correctly."""
        # Generate different error types
        await handler.handle_error(ConnectionError("Network error"))
        await handler.handle_error(ValueError("Validation error"))
        await handler.handle_error(Exception("401 unauthorized"))

        metrics = handler.get_metrics()

        assert metrics["total_errors"] == 3
        assert ErrorCategory.NETWORK.value in metrics["errors_by_category"]
        assert ErrorCategory.VALIDATION.value in metrics["errors_by_category"]
        assert ErrorCategory.AUTHENTICATION.value in metrics["errors_by_category"]

    @pytest.mark.asyncio
    async def test_error_history_limit(self, handler: SIEMErrorHandler):
        """Test error history respects max size."""
        # Generate more errors than max_error_history (10)
        for i in range(15):
            await handler.handle_error(Exception(f"Error {i}"))

        assert len(handler.error_history) == 10
        assert handler.total_errors == 15

    @pytest.mark.asyncio
    async def test_get_recent_errors(self, handler: SIEMErrorHandler):
        """Test getting recent errors."""
        for i in range(5):
            await handler.handle_error(Exception(f"Error {i}"))

        recent = handler.get_recent_errors(count=3)
        assert len(recent) == 3
        assert all(isinstance(e, dict) for e in recent)

    @pytest.mark.asyncio
    async def test_fallback_disabled(self, tmp_path: Path, event: AuditEvent):
        """Test handler with fallback disabled."""
        handler = SIEMErrorHandler(fallback_log_dir=tmp_path, enable_fallback=False)

        error = ConnectionError("Network error")
        await handler.handle_error(error, event=event)

        assert handler.fallback_logger is None
        assert handler.fallback_count == 0


class TestErrorAlerts:
    """Tests for error alerting."""

    @pytest.fixture
    def handler(self, tmp_path: Path) -> SIEMErrorHandler:
        """Create error handler for testing."""
        return SIEMErrorHandler(fallback_log_dir=tmp_path)

    @pytest.mark.asyncio
    async def test_add_alert(self, handler: SIEMErrorHandler):
        """Test adding alert to handler."""
        alert_fired = False

        def callback(errors):
            nonlocal alert_fired
            alert_fired = True

        alert = ErrorAlert(
            name="test_alert",
            condition=lambda errors: len(errors) > 0,
            callback=callback,
        )

        handler.add_alert(alert)
        assert len(handler.alerts) == 1

        # Trigger error
        await handler.handle_error(Exception("Test error"))

        assert alert_fired is True
        assert alert.alert_count == 1

    @pytest.mark.asyncio
    async def test_alert_cooldown(self, handler: SIEMErrorHandler):
        """Test alert cooldown period."""
        fire_count = 0

        def callback(errors):
            nonlocal fire_count
            fire_count += 1

        alert = ErrorAlert(
            name="test_alert",
            condition=lambda errors: True,
            callback=callback,
            cooldown_seconds=1,  # 1 second cooldown
        )

        handler.add_alert(alert)

        # Fire twice quickly
        await handler.handle_error(Exception("Error 1"))
        await handler.handle_error(Exception("Error 2"))

        # Should only fire once due to cooldown
        assert fire_count == 1

        # Wait for cooldown
        await asyncio.sleep(1.1)

        # Should fire again
        await handler.handle_error(Exception("Error 3"))
        assert fire_count == 2

    @pytest.mark.asyncio
    async def test_high_error_rate_condition(self, handler: SIEMErrorHandler):
        """Test high error rate alert condition."""
        alert_fired = False

        def callback(errors):
            nonlocal alert_fired
            alert_fired = True

        alert = ErrorAlert(
            name="high_error_rate",
            condition=lambda errors: high_error_rate_condition(errors, threshold=3, window_seconds=60),
            callback=callback,
        )

        handler.add_alert(alert)

        # Generate errors below threshold
        await handler.handle_error(Exception("Error 1"))
        await handler.handle_error(Exception("Error 2"))
        assert alert_fired is False

        # Exceed threshold
        await handler.handle_error(Exception("Error 3"))
        assert alert_fired is True

    @pytest.mark.asyncio
    async def test_critical_error_condition(self, handler: SIEMErrorHandler):
        """Test critical error alert condition."""
        # Create alert with critical error condition
        def condition(errors):
            return critical_error_condition(errors)

        fired_errors = None

        def callback(errors):
            nonlocal fired_errors
            fired_errors = errors

        alert = ErrorAlert(name="critical", condition=condition, callback=callback)
        handler.add_alert(alert)

        # Create a critical error by using appropriate error type
        # We need to modify the handler to classify this as CRITICAL
        # For testing, let's directly create an ErrorRecord
        from sark.services.audit.siem.error_handler import ErrorRecord

        critical_record = ErrorRecord(
            error=Exception("Critical failure"),
            category=ErrorCategory.UNKNOWN,
            severity=ErrorSeverity.CRITICAL,
        )
        handler.error_history.append(critical_record)
        await handler._check_alerts()

        assert fired_errors is not None
        assert len(fired_errors) > 0


class TestAlertConditions:
    """Tests for predefined alert conditions."""

    def test_high_error_rate_condition_below_threshold(self):
        """Test high error rate when below threshold."""
        errors = [
            ErrorRecord(Exception("e"), ErrorCategory.UNKNOWN, ErrorSeverity.LOW)
            for _ in range(5)
        ]
        assert high_error_rate_condition(errors, threshold=10) is False

    def test_high_error_rate_condition_above_threshold(self):
        """Test high error rate when above threshold."""
        errors = [
            ErrorRecord(Exception("e"), ErrorCategory.UNKNOWN, ErrorSeverity.LOW)
            for _ in range(15)
        ]
        assert high_error_rate_condition(errors, threshold=10) is True

    def test_critical_error_condition_true(self):
        """Test critical error condition when critical error present."""
        errors = [
            ErrorRecord(Exception("e"), ErrorCategory.UNKNOWN, ErrorSeverity.CRITICAL)
        ]
        assert critical_error_condition(errors) is True

    def test_critical_error_condition_false(self):
        """Test critical error condition with no critical errors."""
        errors = [
            ErrorRecord(Exception("e"), ErrorCategory.UNKNOWN, ErrorSeverity.LOW)
        ]
        assert critical_error_condition(errors) is False

    def test_auth_failure_condition_true(self):
        """Test auth failure condition when auth error present."""
        errors = [
            ErrorRecord(Exception("401"), ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH)
        ]
        assert auth_failure_condition(errors) is True

    def test_auth_failure_condition_false(self):
        """Test auth failure condition with no auth errors."""
        errors = [
            ErrorRecord(Exception("e"), ErrorCategory.NETWORK, ErrorSeverity.LOW)
        ]
        assert auth_failure_condition(errors) is False
