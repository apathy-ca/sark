"""Comprehensive error handling for SIEM integrations.

Provides robust error handling with:
- Error classification and recovery strategies
- Graceful degradation with fallback to file logging
- Error alerting and notification
- Integration with retry logic and circuit breaker
- Structured error tracking and metrics
"""

import asyncio
import json
from collections import deque
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable

import structlog

from sark.models.audit import AuditEvent

logger = structlog.get_logger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels."""

    LOW = "low"  # Transient errors, will retry
    MEDIUM = "medium"  # Recoverable errors, may need attention
    HIGH = "high"  # Serious errors, requires investigation
    CRITICAL = "critical"  # Service degraded, immediate action needed


class ErrorCategory(str, Enum):
    """Error categories for classification."""

    NETWORK = "network"  # Network connectivity issues
    AUTHENTICATION = "authentication"  # Auth/authorization failures
    RATE_LIMIT = "rate_limit"  # Rate limiting
    VALIDATION = "validation"  # Data validation errors
    TIMEOUT = "timeout"  # Request timeouts
    SIEM_ERROR = "siem_error"  # SIEM-specific errors
    UNKNOWN = "unknown"  # Unclassified errors


class RecoveryStrategy(str, Enum):
    """Recovery strategies for different error types."""

    RETRY = "retry"  # Retry with exponential backoff
    FALLBACK = "fallback"  # Fall back to file logging
    CIRCUIT_BREAK = "circuit_break"  # Open circuit breaker
    ALERT = "alert"  # Alert operators
    SKIP = "skip"  # Skip and continue


class ErrorRecord:
    """Record of an error occurrence."""

    def __init__(
        self,
        error: Exception,
        category: ErrorCategory,
        severity: ErrorSeverity,
        context: dict[str, Any] | None = None,
    ):
        """Initialize error record.

        Args:
            error: The exception that occurred
            category: Error category
            severity: Error severity
            context: Additional context about the error
        """
        self.error = error
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.timestamp = datetime.now(UTC)
        self.error_type = type(error).__name__
        self.error_message = str(error)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "error_type": self.error_type,
            "error_message": self.error_message,
            "category": self.category.value,
            "severity": self.severity.value,
            "context": self.context,
        }


class FallbackLogger:
    """Fallback file logger for when SIEM is unavailable."""

    def __init__(self, log_dir: Path | str, max_file_size_mb: int = 100):
        """Initialize fallback logger.

        Args:
            log_dir: Directory for fallback logs
            max_file_size_mb: Maximum file size before rotation
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.current_file: Path | None = None
        self.events_logged = 0

    def log_event(self, event: AuditEvent) -> None:
        """Log event to file.

        Args:
            event: Audit event to log
        """
        # Rotate if needed
        if self._should_rotate():
            self._rotate_log_file()

        # Ensure we have a log file
        if self.current_file is None:
            self._create_new_log_file()

        # Write event
        event_data = {
            "id": str(event.id),
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
            "event_type": event.event_type.value if event.event_type else None,
            "severity": event.severity.value if event.severity else None,
            "user_email": event.user_email,
            "tool_name": event.tool_name,
            "decision": event.decision,
            "ip_address": event.ip_address,
            "details": event.details,
        }

        with open(self.current_file, "a") as f:
            f.write(json.dumps(event_data) + "\n")

        self.events_logged += 1

        logger.info(
            "event_logged_to_fallback",
            file=str(self.current_file),
            event_id=str(event.id),
            total_logged=self.events_logged,
        )

    def _should_rotate(self) -> bool:
        """Check if log file should be rotated."""
        if self.current_file is None:
            return False
        if not self.current_file.exists():
            return False
        return self.current_file.stat().st_size >= self.max_file_size_bytes

    def _rotate_log_file(self) -> None:
        """Rotate current log file."""
        if self.current_file and self.current_file.exists():
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            rotated_name = f"{self.current_file.stem}_{timestamp}.log"
            rotated_path = self.current_file.parent / rotated_name
            self.current_file.rename(rotated_path)
            logger.info("fallback_log_rotated", old_file=str(self.current_file), new_file=str(rotated_path))

        self._create_new_log_file()

    def _create_new_log_file(self) -> None:
        """Create new log file."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d")
        self.current_file = self.log_dir / f"siem_fallback_{timestamp}.log"
        logger.info("fallback_log_created", file=str(self.current_file))

    def get_stats(self) -> dict[str, Any]:
        """Get fallback logger statistics."""
        return {
            "log_dir": str(self.log_dir),
            "current_file": str(self.current_file) if self.current_file else None,
            "events_logged": self.events_logged,
            "current_file_size_mb": (
                self.current_file.stat().st_size / (1024 * 1024)
                if self.current_file and self.current_file.exists()
                else 0
            ),
        }


class ErrorAlert:
    """Error alert configuration."""

    def __init__(
        self,
        name: str,
        condition: Callable[[list[ErrorRecord]], bool],
        callback: Callable[[list[ErrorRecord]], None],
        cooldown_seconds: int = 300,
    ):
        """Initialize error alert.

        Args:
            name: Alert name
            condition: Function to check if alert should fire
            callback: Function to call when alert fires
            cooldown_seconds: Minimum seconds between alerts
        """
        self.name = name
        self.condition = condition
        self.callback = callback
        self.cooldown_seconds = cooldown_seconds
        self.last_alert_time: datetime | None = None
        self.alert_count = 0

    def should_fire(self, errors: list[ErrorRecord]) -> bool:
        """Check if alert should fire.

        Args:
            errors: Recent error records

        Returns:
            True if alert should fire
        """
        # Check cooldown
        if self.last_alert_time:
            elapsed = (datetime.now(UTC) - self.last_alert_time).total_seconds()
            if elapsed < self.cooldown_seconds:
                return False

        # Check condition
        return self.condition(errors)

    def fire(self, errors: list[ErrorRecord]) -> None:
        """Fire the alert.

        Args:
            errors: Error records that triggered alert
        """
        try:
            self.callback(errors)
            self.last_alert_time = datetime.now(UTC)
            self.alert_count += 1
            logger.warning(
                "error_alert_fired",
                alert=self.name,
                error_count=len(errors),
                total_alerts=self.alert_count,
            )
        except Exception as e:
            logger.error("error_alert_callback_failed", alert=self.name, error=str(e))


class SIEMErrorHandler:
    """Comprehensive error handler for SIEM integrations."""

    def __init__(
        self,
        fallback_log_dir: Path | str | None = None,
        max_error_history: int = 100,
        enable_fallback: bool = True,
    ):
        """Initialize error handler.

        Args:
            fallback_log_dir: Directory for fallback logs
            max_error_history: Maximum errors to keep in history
            enable_fallback: Whether to enable fallback logging
        """
        self.fallback_log_dir = Path(fallback_log_dir) if fallback_log_dir else Path("/tmp/siem_fallback")
        self.max_error_history = max_error_history
        self.enable_fallback = enable_fallback

        # Components
        self.fallback_logger = FallbackLogger(self.fallback_log_dir) if enable_fallback else None
        self.error_history: deque[ErrorRecord] = deque(maxlen=max_error_history)
        self.alerts: list[ErrorAlert] = []

        # Metrics
        self.total_errors = 0
        self.errors_by_category: dict[ErrorCategory, int] = {}
        self.errors_by_severity: dict[ErrorSeverity, int] = {}
        self.fallback_count = 0

        logger.info(
            "siem_error_handler_initialized",
            fallback_enabled=enable_fallback,
            fallback_dir=str(self.fallback_log_dir),
            max_history=max_error_history,
        )

    def classify_error(self, error: Exception) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify error by category and severity.

        Args:
            error: Exception to classify

        Returns:
            Tuple of (category, severity)
        """
        error_type = type(error).__name__
        error_msg = str(error).lower()

        # Network errors
        if any(
            x in error_type.lower()
            for x in ["connection", "network", "socket", "dns", "timeout"]
        ):
            if "timeout" in error_type.lower() or "timeout" in error_msg:
                return ErrorCategory.TIMEOUT, ErrorSeverity.MEDIUM
            return ErrorCategory.NETWORK, ErrorSeverity.MEDIUM

        # Authentication errors
        if any(x in error_msg for x in ["auth", "unauthorized", "forbidden", "401", "403"]):
            return ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH

        # Rate limiting
        if any(x in error_msg for x in ["rate limit", "too many requests", "429"]):
            return ErrorCategory.RATE_LIMIT, ErrorSeverity.LOW

        # Validation errors
        if any(x in error_type.lower() for x in ["validation", "value", "type"]):
            return ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM

        # SIEM-specific errors
        if any(x in error_msg for x in ["siem", "splunk", "datadog", "hec"]):
            return ErrorCategory.SIEM_ERROR, ErrorSeverity.HIGH

        # Unknown
        return ErrorCategory.UNKNOWN, ErrorSeverity.MEDIUM

    def get_recovery_strategy(
        self, category: ErrorCategory, severity: ErrorSeverity
    ) -> RecoveryStrategy:
        """Determine recovery strategy based on error.

        Args:
            category: Error category
            severity: Error severity

        Returns:
            Recommended recovery strategy
        """
        # Critical errors -> alert + fallback
        if severity == ErrorSeverity.CRITICAL:
            return RecoveryStrategy.ALERT

        # Authentication errors -> circuit break
        if category == ErrorCategory.AUTHENTICATION:
            return RecoveryStrategy.CIRCUIT_BREAK

        # Rate limiting -> retry with backoff
        if category == ErrorCategory.RATE_LIMIT:
            return RecoveryStrategy.RETRY

        # Validation errors -> skip
        if category == ErrorCategory.VALIDATION:
            return RecoveryStrategy.SKIP

        # Network/timeout errors -> retry + fallback
        if category in (ErrorCategory.NETWORK, ErrorCategory.TIMEOUT):
            return RecoveryStrategy.FALLBACK

        # Default -> retry
        return RecoveryStrategy.RETRY

    async def handle_error(
        self,
        error: Exception,
        event: AuditEvent | None = None,
        context: dict[str, Any] | None = None,
    ) -> RecoveryStrategy:
        """Handle an error occurrence.

        Args:
            error: Exception that occurred
            event: Audit event being processed (if any)
            context: Additional context

        Returns:
            Recommended recovery strategy
        """
        # Classify error
        category, severity = self.classify_error(error)

        # Create error record
        error_context = context or {}
        if event:
            error_context["event_id"] = str(event.id)
            error_context["event_type"] = event.event_type.value if event.event_type else None

        error_record = ErrorRecord(error, category, severity, error_context)

        # Update metrics
        self.total_errors += 1
        self.errors_by_category[category] = self.errors_by_category.get(category, 0) + 1
        self.errors_by_severity[severity] = self.errors_by_severity.get(severity, 0) + 1

        # Add to history
        self.error_history.append(error_record)

        # Log error
        logger.error(
            "siem_error_occurred",
            error_type=error_record.error_type,
            error_message=error_record.error_message,
            category=category.value,
            severity=severity.value,
            context=error_context,
        )

        # Get recovery strategy
        strategy = self.get_recovery_strategy(category, severity)

        # Execute fallback if needed
        if strategy == RecoveryStrategy.FALLBACK and event and self.enable_fallback:
            await self._execute_fallback(event)

        # Check alerts
        await self._check_alerts()

        return strategy

    async def _execute_fallback(self, event: AuditEvent) -> None:
        """Execute fallback logging.

        Args:
            event: Event to log to fallback
        """
        if self.fallback_logger:
            try:
                self.fallback_logger.log_event(event)
                self.fallback_count += 1
                logger.info("event_sent_to_fallback", event_id=str(event.id))
            except Exception as e:
                logger.error("fallback_logging_failed", error=str(e), event_id=str(event.id))

    async def _check_alerts(self) -> None:
        """Check if any alerts should fire."""
        recent_errors = list(self.error_history)

        for alert in self.alerts:
            if alert.should_fire(recent_errors):
                alert.fire(recent_errors)

    def add_alert(self, alert: ErrorAlert) -> None:
        """Add an error alert.

        Args:
            alert: Alert to add
        """
        self.alerts.append(alert)
        logger.info("error_alert_added", alert=alert.name, total_alerts=len(self.alerts))

    def get_metrics(self) -> dict[str, Any]:
        """Get error handler metrics.

        Returns:
            Dictionary with metrics
        """
        metrics = {
            "total_errors": self.total_errors,
            "fallback_count": self.fallback_count,
            "errors_by_category": {k.value: v for k, v in self.errors_by_category.items()},
            "errors_by_severity": {k.value: v for k, v in self.errors_by_severity.items()},
            "recent_errors": len(self.error_history),
            "alerts_configured": len(self.alerts),
            "alerts_fired": sum(a.alert_count for a in self.alerts),
        }

        if self.fallback_logger:
            metrics["fallback_logger"] = self.fallback_logger.get_stats()

        return metrics

    def get_recent_errors(self, count: int = 10) -> list[dict[str, Any]]:
        """Get recent errors.

        Args:
            count: Number of recent errors to return

        Returns:
            List of error dictionaries
        """
        return [e.to_dict() for e in list(self.error_history)[-count:]]


# Predefined alert conditions
def high_error_rate_condition(errors: list[ErrorRecord], threshold: int = 10, window_seconds: int = 60) -> bool:
    """Alert if error rate exceeds threshold.

    Args:
        errors: Error history
        threshold: Error count threshold
        window_seconds: Time window in seconds

    Returns:
        True if condition met
    """
    if len(errors) < threshold:
        return False

    cutoff = datetime.now(UTC).timestamp() - window_seconds
    recent = [e for e in errors if e.timestamp.timestamp() > cutoff]
    return len(recent) >= threshold


def critical_error_condition(errors: list[ErrorRecord]) -> bool:
    """Alert on any critical error.

    Args:
        errors: Error history

    Returns:
        True if any critical error in last error
    """
    if not errors:
        return False
    return errors[-1].severity == ErrorSeverity.CRITICAL


def auth_failure_condition(errors: list[ErrorRecord]) -> bool:
    """Alert on authentication failures.

    Args:
        errors: Error history

    Returns:
        True if recent auth failure
    """
    if not errors:
        return False
    return errors[-1].category == ErrorCategory.AUTHENTICATION
