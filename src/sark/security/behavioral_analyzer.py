"""
Behavioral Anomaly Detection System

Builds behavioral baselines for users and detects anomalous activity:
- Unusual tools accessed
- Unusual access times
- Excessive data volume
- Sensitivity escalation
"""

from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from statistics import mode, mean
from collections import Counter
import logging

logger = logging.getLogger(__name__)


class AnomalyType(str, Enum):
    """Types of behavioral anomalies"""
    UNUSUAL_TOOL = "unusual_tool"
    UNUSUAL_TIME = "unusual_time"
    UNUSUAL_DAY = "unusual_day"
    EXCESSIVE_DATA = "excessive_data"
    SENSITIVITY_ESCALATION = "sensitivity_escalation"
    RAPID_REQUESTS = "rapid_requests"
    GEOGRAPHIC_ANOMALY = "geographic_anomaly"


class AnomalySeverity(str, Enum):
    """Severity levels for anomalies"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Anomaly:
    """Represents a detected behavioral anomaly"""
    type: AnomalyType
    severity: AnomalySeverity
    description: str
    baseline_value: Optional[Any] = None
    observed_value: Optional[Any] = None
    confidence: float = 1.0  # 0.0 to 1.0


@dataclass
class BehavioralBaseline:
    """User's normal behavior profile"""
    user_id: str
    created_at: datetime
    lookback_days: int

    # Tool usage
    common_tools: List[str]
    avg_calls_per_day: float
    max_calls_per_day: int

    # Timing patterns
    typical_hours: Set[int]  # Hours of day (0-23)
    typical_days: Set[int]   # Days of week (0-6, 0=Monday)

    # Data volume
    avg_records_per_query: float
    max_records_per_query: int

    # Sensitivity
    max_sensitivity_level: str
    typical_sensitivity: str

    # Geographic (optional)
    typical_locations: Set[str]


@dataclass
class AuditEvent:
    """Simplified audit event for anomaly detection"""
    user_id: str
    timestamp: datetime
    tool_name: str
    sensitivity: str
    result_size: int = 0
    location: Optional[str] = None
    request_id: Optional[str] = None


class BehavioralAnalyzer:
    """Analyzes user behavior and detects anomalies"""

    # Anomaly detection thresholds
    TOOL_UNCOMMON_THRESHOLD = 0.1  # Tool must be in top 90% of usage
    DATA_MULTIPLIER_THRESHOLD = 3.0  # 3x normal data volume
    RAPID_REQUEST_THRESHOLD = 10  # 10 requests in 60 seconds

    def __init__(self, baseline_storage: Optional[Any] = None, audit_storage: Optional[Any] = None):
        """
        Initialize behavioral analyzer

        Args:
            baseline_storage: Storage backend for baselines (optional)
            audit_storage: Storage backend for audit events (optional)
        """
        self.baseline_storage = baseline_storage
        self.audit_storage = audit_storage

    async def build_baseline(
        self,
        user_id: str,
        lookback_days: int = 30,
        events: Optional[List[AuditEvent]] = None
    ) -> BehavioralBaseline:
        """
        Build normal behavior profile for a user

        Args:
            user_id: User ID to build baseline for
            lookback_days: Number of days to analyze (default: 30)
            events: Optional pre-fetched events (fetches from storage if not provided)

        Returns:
            BehavioralBaseline profile
        """
        # Fetch events if not provided
        if events is None:
            if self.audit_storage:
                start_date = datetime.now() - timedelta(days=lookback_days)
                events = await self.audit_storage.query(
                    user_id=user_id,
                    start_date=start_date
                )
            else:
                events = []

        if not events:
            # Return minimal baseline for new users
            return BehavioralBaseline(
                user_id=user_id,
                created_at=datetime.now(),
                lookback_days=lookback_days,
                common_tools=[],
                avg_calls_per_day=0.0,
                max_calls_per_day=0,
                typical_hours=set(),
                typical_days=set(),
                avg_records_per_query=0.0,
                max_records_per_query=0,
                max_sensitivity_level="none",
                typical_sensitivity="none",
                typical_locations=set()
            )

        # Build baseline from events
        baseline = BehavioralBaseline(
            user_id=user_id,
            created_at=datetime.now(),
            lookback_days=lookback_days,
            common_tools=self._get_common_tools(events, top_n=10),
            avg_calls_per_day=len(events) / lookback_days,
            max_calls_per_day=self._get_max_calls_per_day(events),
            typical_hours=self._get_typical_hours(events),
            typical_days=self._get_typical_days(events),
            avg_records_per_query=self._get_avg_result_size(events),
            max_records_per_query=max((e.result_size for e in events), default=0),
            max_sensitivity_level=self._get_max_sensitivity(events),
            typical_sensitivity=self._get_typical_sensitivity(events),
            typical_locations=self._get_typical_locations(events)
        )

        # Store baseline
        if self.baseline_storage:
            try:
                await self.baseline_storage.save(user_id, baseline)
            except Exception as e:
                logger.error(f"Failed to save baseline for {user_id}: {e}")

        return baseline

    async def detect_anomalies(
        self,
        event: AuditEvent,
        baseline: Optional[BehavioralBaseline] = None,
        recent_events: Optional[List[AuditEvent]] = None
    ) -> List[Anomaly]:
        """
        Detect anomalies in an event

        Args:
            event: Current event to analyze
            baseline: User's baseline (fetches from storage if not provided)
            recent_events: Recent events for rate limiting check

        Returns:
            List of detected anomalies
        """
        # Get baseline
        if baseline is None and self.baseline_storage:
            baseline = await self.baseline_storage.get(event.user_id)

        if baseline is None:
            # No baseline yet, can't detect anomalies
            return []

        anomalies = []

        # Check unusual tool
        if event.tool_name not in baseline.common_tools:
            anomalies.append(Anomaly(
                type=AnomalyType.UNUSUAL_TOOL,
                severity=AnomalySeverity.LOW,
                description=f"User accessed uncommon tool: {event.tool_name}",
                baseline_value=baseline.common_tools[:3],
                observed_value=event.tool_name,
                confidence=0.7
            ))

        # Check unusual time
        event_hour = event.timestamp.hour
        if event_hour not in baseline.typical_hours and baseline.typical_hours:
            anomalies.append(Anomaly(
                type=AnomalyType.UNUSUAL_TIME,
                severity=AnomalySeverity.MEDIUM,
                description=f"Access at unusual hour: {event_hour}:00",
                baseline_value=list(baseline.typical_hours),
                observed_value=event_hour,
                confidence=0.8
            ))

        # Check unusual day
        event_day = event.timestamp.weekday()
        if event_day not in baseline.typical_days and baseline.typical_days:
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            anomalies.append(Anomaly(
                type=AnomalyType.UNUSUAL_DAY,
                severity=AnomalySeverity.LOW,
                description=f"Access on unusual day: {day_names[event_day]}",
                baseline_value=[day_names[d] for d in baseline.typical_days],
                observed_value=day_names[event_day],
                confidence=0.6
            ))

        # Check excessive data access
        if baseline.max_records_per_query > 0:
            threshold = baseline.max_records_per_query * self.DATA_MULTIPLIER_THRESHOLD
            if event.result_size > threshold:
                anomalies.append(Anomaly(
                    type=AnomalyType.EXCESSIVE_DATA,
                    severity=AnomalySeverity.HIGH,
                    description=f"Excessive data access: {event.result_size} records (baseline max: {baseline.max_records_per_query})",
                    baseline_value=baseline.max_records_per_query,
                    observed_value=event.result_size,
                    confidence=0.9
                ))

        # Check sensitivity escalation
        sensitivity_levels = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
        baseline_level = sensitivity_levels.get(baseline.max_sensitivity_level, 0)
        event_level = sensitivity_levels.get(event.sensitivity, 0)

        if event_level > baseline_level:
            anomalies.append(Anomaly(
                type=AnomalyType.SENSITIVITY_ESCALATION,
                severity=AnomalySeverity.HIGH,
                description=f"Sensitivity escalation: {event.sensitivity} (baseline max: {baseline.max_sensitivity_level})",
                baseline_value=baseline.max_sensitivity_level,
                observed_value=event.sensitivity,
                confidence=0.95
            ))

        # Check rapid requests
        if recent_events:
            recent_count = len([
                e for e in recent_events
                if (event.timestamp - e.timestamp).total_seconds() < 60
            ])
            if recent_count >= self.RAPID_REQUEST_THRESHOLD:
                anomalies.append(Anomaly(
                    type=AnomalyType.RAPID_REQUESTS,
                    severity=AnomalySeverity.MEDIUM,
                    description=f"Rapid requests: {recent_count} in 60 seconds",
                    baseline_value=self.RAPID_REQUEST_THRESHOLD,
                    observed_value=recent_count,
                    confidence=0.85
                ))

        # Check geographic anomaly
        if event.location and baseline.typical_locations:
            if event.location not in baseline.typical_locations:
                anomalies.append(Anomaly(
                    type=AnomalyType.GEOGRAPHIC_ANOMALY,
                    severity=AnomalySeverity.MEDIUM,
                    description=f"Access from unusual location: {event.location}",
                    baseline_value=list(baseline.typical_locations),
                    observed_value=event.location,
                    confidence=0.75
                ))

        return anomalies

    def _get_common_tools(self, events: List[AuditEvent], top_n: int = 10) -> List[str]:
        """Get most commonly used tools"""
        tool_counts = Counter(e.tool_name for e in events)
        return [tool for tool, _ in tool_counts.most_common(top_n)]

    def _get_max_calls_per_day(self, events: List[AuditEvent]) -> int:
        """Get maximum calls in a single day"""
        if not events:
            return 0

        daily_counts: Dict[str, int] = {}
        for event in events:
            day_key = event.timestamp.strftime("%Y-%m-%d")
            daily_counts[day_key] = daily_counts.get(day_key, 0) + 1

        return max(daily_counts.values()) if daily_counts else 0

    def _get_typical_hours(self, events: List[AuditEvent], threshold: float = 0.1) -> Set[int]:
        """Get typical hours of activity"""
        if not events:
            return set()

        hour_counts = Counter(e.timestamp.hour for e in events)
        total = len(events)

        # Include hours with at least threshold% of activity
        return {
            hour for hour, count in hour_counts.items()
            if count / total >= threshold
        }

    def _get_typical_days(self, events: List[AuditEvent], threshold: float = 0.1) -> Set[int]:
        """Get typical days of week"""
        if not events:
            return set()

        day_counts = Counter(e.timestamp.weekday() for e in events)
        total = len(events)

        # Include days with at least threshold% of activity
        return {
            day for day, count in day_counts.items()
            if count / total >= threshold
        }

    def _get_avg_result_size(self, events: List[AuditEvent]) -> float:
        """Get average result size"""
        sizes = [e.result_size for e in events if e.result_size > 0]
        return mean(sizes) if sizes else 0.0

    def _get_max_sensitivity(self, events: List[AuditEvent]) -> str:
        """Get maximum sensitivity level seen"""
        sensitivity_order = ["none", "low", "medium", "high", "critical"]
        max_level = "none"

        for event in events:
            if event.sensitivity in sensitivity_order:
                current_idx = sensitivity_order.index(event.sensitivity)
                max_idx = sensitivity_order.index(max_level)
                if current_idx > max_idx:
                    max_level = event.sensitivity

        return max_level

    def _get_typical_sensitivity(self, events: List[AuditEvent]) -> str:
        """Get most common sensitivity level"""
        sensitivities = [e.sensitivity for e in events if e.sensitivity]
        try:
            return mode(sensitivities) if sensitivities else "none"
        except:
            # Multiple modes, return most common
            counts = Counter(sensitivities)
            return counts.most_common(1)[0][0] if counts else "none"

    def _get_typical_locations(self, events: List[AuditEvent]) -> Set[str]:
        """Get typical access locations"""
        locations = {e.location for e in events if e.location}
        return locations
