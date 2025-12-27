"""
Unit tests for behavioral anomaly detection system

Tests cover:
- Baseline building from historical events
- Detection of 7 anomaly types
- Storage integration
- Edge cases and error handling
- Performance requirements
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from collections import Counter

from sark.security.behavioral_analyzer import (
    BehavioralAnalyzer,
    BehavioralBaseline,
    BehavioralAuditEvent,
    Anomaly,
    AnomalyType,
    AnomalySeverity,
)


class TestBehavioralAuditEvent:
    """Test BehavioralAuditEvent dataclass"""

    def test_create_minimal_event(self):
        """Test creating event with minimal required fields"""
        event = BehavioralAuditEvent(
            user_id="user123",
            timestamp=datetime(2024, 1, 15, 10, 30),
            tool_name="database_query",
            sensitivity="medium",
        )

        assert event.user_id == "user123"
        assert event.tool_name == "database_query"
        assert event.sensitivity == "medium"
        assert event.result_size == 0
        assert event.location is None
        assert event.request_id is None

    def test_create_full_event(self):
        """Test creating event with all fields"""
        event = BehavioralAuditEvent(
            user_id="user123",
            timestamp=datetime(2024, 1, 15, 10, 30),
            tool_name="database_query",
            sensitivity="high",
            result_size=1000,
            location="US-EAST",
            request_id="req-abc-123",
        )

        assert event.result_size == 1000
        assert event.location == "US-EAST"
        assert event.request_id == "req-abc-123"


class TestBehavioralBaseline:
    """Test BehavioralBaseline dataclass"""

    def test_create_baseline(self):
        """Test creating a behavioral baseline"""
        baseline = BehavioralBaseline(
            user_id="user123",
            created_at=datetime.now(),
            lookback_days=30,
            common_tools=["tool1", "tool2", "tool3"],
            avg_calls_per_day=25.5,
            max_calls_per_day=50,
            typical_hours={9, 10, 11, 14, 15, 16},
            typical_days={0, 1, 2, 3, 4},  # Mon-Fri
            avg_records_per_query=100.0,
            max_records_per_query=500,
            max_sensitivity_level="high",
            typical_sensitivity="medium",
            typical_locations={"US-EAST", "US-WEST"},
        )

        assert baseline.user_id == "user123"
        assert baseline.lookback_days == 30
        assert len(baseline.common_tools) == 3
        assert baseline.avg_calls_per_day == 25.5
        assert 0 in baseline.typical_days  # Monday
        assert 5 not in baseline.typical_days  # Saturday


class TestAnomaly:
    """Test Anomaly dataclass"""

    def test_create_anomaly_minimal(self):
        """Test creating anomaly with minimal fields"""
        anomaly = Anomaly(
            type=AnomalyType.UNUSUAL_TOOL,
            severity=AnomalySeverity.LOW,
            description="User accessed uncommon tool",
        )

        assert anomaly.type == AnomalyType.UNUSUAL_TOOL
        assert anomaly.severity == AnomalySeverity.LOW
        assert anomaly.confidence == 1.0
        assert anomaly.baseline_value is None

    def test_create_anomaly_full(self):
        """Test creating anomaly with all fields"""
        anomaly = Anomaly(
            type=AnomalyType.EXCESSIVE_DATA,
            severity=AnomalySeverity.HIGH,
            description="Excessive data access detected",
            baseline_value=500,
            observed_value=2000,
            confidence=0.9,
        )

        assert anomaly.baseline_value == 500
        assert anomaly.observed_value == 2000
        assert anomaly.confidence == 0.9


class TestBehavioralAnalyzer:
    """Test BehavioralAnalyzer class"""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer without storage"""
        return BehavioralAnalyzer()

    @pytest.fixture
    def analyzer_with_storage(self):
        """Create analyzer with mock storage"""
        baseline_storage = AsyncMock()
        audit_storage = AsyncMock()
        return BehavioralAnalyzer(
            baseline_storage=baseline_storage, audit_storage=audit_storage
        )

    @pytest.fixture
    def sample_events(self):
        """Create sample audit events for testing"""
        base_time = datetime(2024, 1, 1, 10, 0)
        events = []

        # Create 30 days of events, weekdays only, business hours
        for day in range(30):
            current_date = base_time + timedelta(days=day)

            # Skip weekends
            if current_date.weekday() >= 5:
                continue

            # Add 3-5 events per day
            for hour in [9, 10, 14, 15, 16]:
                events.append(
                    BehavioralAuditEvent(
                        user_id="user123",
                        timestamp=current_date.replace(hour=hour),
                        tool_name="database_query" if hour < 12 else "api_call",
                        sensitivity="medium",
                        result_size=100,
                        location="US-EAST",
                    )
                )

        return events

    # Baseline Building Tests

    @pytest.mark.asyncio
    async def test_build_baseline_new_user_no_events(self, analyzer):
        """Test building baseline for new user with no events"""
        baseline = await analyzer.build_baseline("new_user", lookback_days=30, events=[])

        assert baseline.user_id == "new_user"
        assert baseline.lookback_days == 30
        assert baseline.common_tools == []
        assert baseline.avg_calls_per_day == 0.0
        assert baseline.max_calls_per_day == 0
        assert baseline.typical_hours == set()
        assert baseline.typical_days == set()
        assert baseline.avg_records_per_query == 0.0
        assert baseline.max_records_per_query == 0
        assert baseline.max_sensitivity_level == "none"
        assert baseline.typical_sensitivity == "none"
        assert baseline.typical_locations == set()

    @pytest.mark.asyncio
    async def test_build_baseline_from_events(self, analyzer, sample_events):
        """Test building baseline from historical events"""
        baseline = await analyzer.build_baseline(
            "user123", lookback_days=30, events=sample_events
        )

        assert baseline.user_id == "user123"
        assert baseline.lookback_days == 30

        # Check common tools
        assert "database_query" in baseline.common_tools
        assert "api_call" in baseline.common_tools

        # Check timing patterns
        assert 9 in baseline.typical_hours
        assert 10 in baseline.typical_hours
        assert 14 in baseline.typical_hours
        assert 2 not in baseline.typical_hours  # 2 AM not in pattern

        # Check weekday pattern (Mon-Fri only)
        assert 0 in baseline.typical_days  # Monday
        assert 4 in baseline.typical_days  # Friday
        assert 5 not in baseline.typical_days  # Saturday
        assert 6 not in baseline.typical_days  # Sunday

        # Check data patterns
        assert baseline.avg_records_per_query > 0
        assert baseline.max_records_per_query >= 100

        # Check sensitivity
        assert baseline.max_sensitivity_level == "medium"
        assert baseline.typical_sensitivity == "medium"

        # Check location
        assert "US-EAST" in baseline.typical_locations

    @pytest.mark.asyncio
    async def test_build_baseline_saves_to_storage(self, analyzer_with_storage):
        """Test that baseline is saved to storage"""
        events = [
            BehavioralAuditEvent(
                user_id="user123",
                timestamp=datetime.now(),
                tool_name="tool1",
                sensitivity="low",
            )
        ]

        baseline = await analyzer_with_storage.build_baseline(
            "user123", events=events
        )

        # Verify save was called
        analyzer_with_storage.baseline_storage.save.assert_called_once()
        call_args = analyzer_with_storage.baseline_storage.save.call_args
        assert call_args[0][0] == "user123"
        assert call_args[0][1].user_id == "user123"

    @pytest.mark.asyncio
    async def test_build_baseline_handles_storage_error(
        self, analyzer_with_storage, caplog
    ):
        """Test that baseline building continues even if storage fails"""
        analyzer_with_storage.baseline_storage.save.side_effect = Exception(
            "Storage error"
        )

        events = [
            BehavioralAuditEvent(
                user_id="user123",
                timestamp=datetime.now(),
                tool_name="tool1",
                sensitivity="low",
            )
        ]

        # Should not raise exception
        baseline = await analyzer_with_storage.build_baseline(
            "user123", events=events
        )

        assert baseline is not None
        assert "Failed to save baseline" in caplog.text

    @pytest.mark.asyncio
    async def test_build_baseline_fetches_from_audit_storage(
        self, analyzer_with_storage
    ):
        """Test that baseline fetches events from audit storage if not provided"""
        # Mock audit storage to return events
        mock_events = [
            BehavioralAuditEvent(
                user_id="user123",
                timestamp=datetime.now(),
                tool_name="tool1",
                sensitivity="low",
            )
        ]
        analyzer_with_storage.audit_storage.query.return_value = mock_events

        baseline = await analyzer_with_storage.build_baseline("user123")

        # Verify query was called
        analyzer_with_storage.audit_storage.query.assert_called_once()
        assert baseline.common_tools == ["tool1"]

    # Anomaly Detection Tests

    @pytest.mark.asyncio
    async def test_detect_no_baseline_returns_empty(self, analyzer):
        """Test that detection returns empty list without baseline"""
        event = BehavioralAuditEvent(
            user_id="user123",
            timestamp=datetime.now(),
            tool_name="tool1",
            sensitivity="low",
        )

        anomalies = await analyzer.detect_anomalies(event, baseline=None)

        assert anomalies == []

    @pytest.mark.asyncio
    async def test_detect_unusual_tool(self, analyzer):
        """Test detection of unusual tool access"""
        baseline = BehavioralBaseline(
            user_id="user123",
            created_at=datetime.now(),
            lookback_days=30,
            common_tools=["tool1", "tool2", "tool3"],
            avg_calls_per_day=10.0,
            max_calls_per_day=20,
            typical_hours={9, 10, 11},
            typical_days={0, 1, 2, 3, 4},
            avg_records_per_query=100.0,
            max_records_per_query=500,
            max_sensitivity_level="medium",
            typical_sensitivity="low",
            typical_locations=set(),
        )

        event = BehavioralAuditEvent(
            user_id="user123",
            timestamp=datetime(2024, 1, 15, 10, 0),  # Monday, 10 AM
            tool_name="unusual_tool",  # Not in common_tools
            sensitivity="low",
        )

        anomalies = await analyzer.detect_anomalies(event, baseline=baseline)

        unusual_tool_anomalies = [
            a for a in anomalies if a.type == AnomalyType.UNUSUAL_TOOL
        ]
        assert len(unusual_tool_anomalies) == 1
        anomaly = unusual_tool_anomalies[0]
        assert anomaly.severity == AnomalySeverity.LOW
        assert "unusual_tool" in anomaly.description
        assert anomaly.observed_value == "unusual_tool"
        assert anomaly.confidence == 0.7

    @pytest.mark.asyncio
    async def test_detect_unusual_time(self, analyzer):
        """Test detection of unusual access time"""
        baseline = BehavioralBaseline(
            user_id="user123",
            created_at=datetime.now(),
            lookback_days=30,
            common_tools=["tool1"],
            avg_calls_per_day=10.0,
            max_calls_per_day=20,
            typical_hours={9, 10, 11, 14, 15, 16},  # Business hours
            typical_days={0, 1, 2, 3, 4},
            avg_records_per_query=100.0,
            max_records_per_query=500,
            max_sensitivity_level="medium",
            typical_sensitivity="low",
            typical_locations=set(),
        )

        event = BehavioralAuditEvent(
            user_id="user123",
            timestamp=datetime(2024, 1, 15, 2, 0),  # 2 AM - unusual!
            tool_name="tool1",
            sensitivity="low",
        )

        anomalies = await analyzer.detect_anomalies(event, baseline=baseline)

        unusual_time_anomalies = [
            a for a in anomalies if a.type == AnomalyType.UNUSUAL_TIME
        ]
        assert len(unusual_time_anomalies) == 1
        anomaly = unusual_time_anomalies[0]
        assert anomaly.severity == AnomalySeverity.MEDIUM
        assert "2:00" in anomaly.description
        assert anomaly.observed_value == 2
        assert anomaly.confidence == 0.8

    @pytest.mark.asyncio
    async def test_detect_unusual_day(self, analyzer):
        """Test detection of unusual day of week"""
        baseline = BehavioralBaseline(
            user_id="user123",
            created_at=datetime.now(),
            lookback_days=30,
            common_tools=["tool1"],
            avg_calls_per_day=10.0,
            max_calls_per_day=20,
            typical_hours={9, 10, 11},
            typical_days={0, 1, 2, 3, 4},  # Mon-Fri
            avg_records_per_query=100.0,
            max_records_per_query=500,
            max_sensitivity_level="medium",
            typical_sensitivity="low",
            typical_locations=set(),
        )

        # January 13, 2024 is a Saturday
        event = BehavioralAuditEvent(
            user_id="user123",
            timestamp=datetime(2024, 1, 13, 10, 0),
            tool_name="tool1",
            sensitivity="low",
        )

        anomalies = await analyzer.detect_anomalies(event, baseline=baseline)

        unusual_day_anomalies = [
            a for a in anomalies if a.type == AnomalyType.UNUSUAL_DAY
        ]
        assert len(unusual_day_anomalies) == 1
        anomaly = unusual_day_anomalies[0]
        assert anomaly.severity == AnomalySeverity.LOW
        assert "Saturday" in anomaly.description
        assert anomaly.confidence == 0.6

    @pytest.mark.asyncio
    async def test_detect_excessive_data(self, analyzer):
        """Test detection of excessive data access"""
        baseline = BehavioralBaseline(
            user_id="user123",
            created_at=datetime.now(),
            lookback_days=30,
            common_tools=["tool1"],
            avg_calls_per_day=10.0,
            max_calls_per_day=20,
            typical_hours={9, 10, 11},
            typical_days={0, 1, 2, 3, 4},
            avg_records_per_query=100.0,
            max_records_per_query=500,  # Max is 500
            max_sensitivity_level="medium",
            typical_sensitivity="low",
            typical_locations=set(),
        )

        # 3x threshold = 500 * 3 = 1500
        event = BehavioralAuditEvent(
            user_id="user123",
            timestamp=datetime(2024, 1, 15, 10, 0),
            tool_name="tool1",
            sensitivity="low",
            result_size=2000,  # Exceeds 3x threshold
        )

        anomalies = await analyzer.detect_anomalies(event, baseline=baseline)

        excessive_data_anomalies = [
            a for a in anomalies if a.type == AnomalyType.EXCESSIVE_DATA
        ]
        assert len(excessive_data_anomalies) == 1
        anomaly = excessive_data_anomalies[0]
        assert anomaly.severity == AnomalySeverity.HIGH
        assert "2000 records" in anomaly.description
        assert anomaly.baseline_value == 500
        assert anomaly.observed_value == 2000
        assert anomaly.confidence == 0.9

    @pytest.mark.asyncio
    async def test_detect_sensitivity_escalation(self, analyzer):
        """Test detection of sensitivity escalation"""
        baseline = BehavioralBaseline(
            user_id="user123",
            created_at=datetime.now(),
            lookback_days=30,
            common_tools=["tool1"],
            avg_calls_per_day=10.0,
            max_calls_per_day=20,
            typical_hours={9, 10, 11},
            typical_days={0, 1, 2, 3, 4},
            avg_records_per_query=100.0,
            max_records_per_query=500,
            max_sensitivity_level="medium",  # Historical max is medium
            typical_sensitivity="low",
            typical_locations=set(),
        )

        event = BehavioralAuditEvent(
            user_id="user123",
            timestamp=datetime(2024, 1, 15, 10, 0),
            tool_name="tool1",
            sensitivity="critical",  # Escalation to critical!
        )

        anomalies = await analyzer.detect_anomalies(event, baseline=baseline)

        escalation_anomalies = [
            a for a in anomalies if a.type == AnomalyType.SENSITIVITY_ESCALATION
        ]
        assert len(escalation_anomalies) == 1
        anomaly = escalation_anomalies[0]
        assert anomaly.severity == AnomalySeverity.HIGH
        assert "critical" in anomaly.description
        assert anomaly.baseline_value == "medium"
        assert anomaly.observed_value == "critical"
        assert anomaly.confidence == 0.95

    @pytest.mark.asyncio
    async def test_detect_rapid_requests(self, analyzer):
        """Test detection of rapid request patterns"""
        baseline = BehavioralBaseline(
            user_id="user123",
            created_at=datetime.now(),
            lookback_days=30,
            common_tools=["tool1"],
            avg_calls_per_day=10.0,
            max_calls_per_day=20,
            typical_hours={9, 10, 11},
            typical_days={0, 1, 2, 3, 4},
            avg_records_per_query=100.0,
            max_records_per_query=500,
            max_sensitivity_level="medium",
            typical_sensitivity="low",
            typical_locations=set(),
        )

        current_time = datetime(2024, 1, 15, 10, 0)

        # Create 11 recent events within 60 seconds
        recent_events = [
            BehavioralAuditEvent(
                user_id="user123",
                timestamp=current_time - timedelta(seconds=i * 5),
                tool_name="tool1",
                sensitivity="low",
            )
            for i in range(11)
        ]

        event = BehavioralAuditEvent(
            user_id="user123",
            timestamp=current_time,
            tool_name="tool1",
            sensitivity="low",
        )

        anomalies = await analyzer.detect_anomalies(
            event, baseline=baseline, recent_events=recent_events
        )

        rapid_request_anomalies = [
            a for a in anomalies if a.type == AnomalyType.RAPID_REQUESTS
        ]
        assert len(rapid_request_anomalies) == 1
        anomaly = rapid_request_anomalies[0]
        assert anomaly.severity == AnomalySeverity.MEDIUM
        assert "60 seconds" in anomaly.description
        assert anomaly.observed_value >= 10
        assert anomaly.confidence == 0.85

    @pytest.mark.asyncio
    async def test_detect_geographic_anomaly(self, analyzer):
        """Test detection of geographic anomaly"""
        baseline = BehavioralBaseline(
            user_id="user123",
            created_at=datetime.now(),
            lookback_days=30,
            common_tools=["tool1"],
            avg_calls_per_day=10.0,
            max_calls_per_day=20,
            typical_hours={9, 10, 11},
            typical_days={0, 1, 2, 3, 4},
            avg_records_per_query=100.0,
            max_records_per_query=500,
            max_sensitivity_level="medium",
            typical_sensitivity="low",
            typical_locations={"US-EAST", "US-WEST"},  # Typical locations
        )

        event = BehavioralAuditEvent(
            user_id="user123",
            timestamp=datetime(2024, 1, 15, 10, 0),
            tool_name="tool1",
            sensitivity="low",
            location="EU-WEST",  # Unusual location!
        )

        anomalies = await analyzer.detect_anomalies(event, baseline=baseline)

        geo_anomalies = [
            a for a in anomalies if a.type == AnomalyType.GEOGRAPHIC_ANOMALY
        ]
        assert len(geo_anomalies) == 1
        anomaly = geo_anomalies[0]
        assert anomaly.severity == AnomalySeverity.MEDIUM
        assert "EU-WEST" in anomaly.description
        assert anomaly.observed_value == "EU-WEST"
        assert anomaly.confidence == 0.75

    @pytest.mark.asyncio
    async def test_detect_multiple_anomalies(self, analyzer):
        """Test detection of multiple simultaneous anomalies"""
        baseline = BehavioralBaseline(
            user_id="user123",
            created_at=datetime.now(),
            lookback_days=30,
            common_tools=["tool1", "tool2"],
            avg_calls_per_day=10.0,
            max_calls_per_day=20,
            typical_hours={9, 10, 11, 14, 15},
            typical_days={0, 1, 2, 3, 4},
            avg_records_per_query=100.0,
            max_records_per_query=500,
            max_sensitivity_level="medium",
            typical_sensitivity="low",
            typical_locations={"US-EAST"},
        )

        # Event with multiple anomalies
        event = BehavioralAuditEvent(
            user_id="user123",
            timestamp=datetime(2024, 1, 13, 2, 0),  # Saturday at 2 AM
            tool_name="unusual_tool",  # Unusual tool
            sensitivity="critical",  # Sensitivity escalation
            result_size=2000,  # Excessive data
            location="EU-WEST",  # Geographic anomaly
        )

        anomalies = await analyzer.detect_anomalies(event, baseline=baseline)

        # Should detect at least 5 anomalies
        assert len(anomalies) >= 5

        anomaly_types = {a.type for a in anomalies}
        assert AnomalyType.UNUSUAL_TOOL in anomaly_types
        assert AnomalyType.UNUSUAL_TIME in anomaly_types
        assert AnomalyType.UNUSUAL_DAY in anomaly_types
        assert AnomalyType.EXCESSIVE_DATA in anomaly_types
        assert AnomalyType.SENSITIVITY_ESCALATION in anomaly_types
        assert AnomalyType.GEOGRAPHIC_ANOMALY in anomaly_types

    @pytest.mark.asyncio
    async def test_detect_fetches_baseline_from_storage(self, analyzer_with_storage):
        """Test that detection fetches baseline from storage if not provided"""
        mock_baseline = BehavioralBaseline(
            user_id="user123",
            created_at=datetime.now(),
            lookback_days=30,
            common_tools=["tool1"],
            avg_calls_per_day=10.0,
            max_calls_per_day=20,
            typical_hours={9, 10, 11},
            typical_days={0, 1, 2, 3, 4},
            avg_records_per_query=100.0,
            max_records_per_query=500,
            max_sensitivity_level="medium",
            typical_sensitivity="low",
            typical_locations=set(),
        )
        analyzer_with_storage.baseline_storage.get.return_value = mock_baseline

        event = BehavioralAuditEvent(
            user_id="user123",
            timestamp=datetime(2024, 1, 15, 10, 0),
            tool_name="tool1",
            sensitivity="low",
        )

        anomalies = await analyzer_with_storage.detect_anomalies(event)

        # Verify storage.get was called
        analyzer_with_storage.baseline_storage.get.assert_called_once_with("user123")

    # Helper Method Tests

    def test_get_common_tools(self, analyzer):
        """Test extraction of common tools"""
        events = [
            BehavioralAuditEvent(
                user_id="user123",
                timestamp=datetime.now(),
                tool_name="tool1",
                sensitivity="low",
            )
            for _ in range(10)
        ] + [
            BehavioralAuditEvent(
                user_id="user123",
                timestamp=datetime.now(),
                tool_name="tool2",
                sensitivity="low",
            )
            for _ in range(5)
        ]

        common_tools = analyzer._get_common_tools(events, top_n=3)

        assert common_tools[0] == "tool1"  # Most common
        assert common_tools[1] == "tool2"  # Second most common
        assert len(common_tools) <= 3

    def test_get_max_calls_per_day(self, analyzer):
        """Test calculation of max calls per day"""
        # Create events with varying daily counts
        events = []
        base_time = datetime(2024, 1, 1, 10, 0)

        # Day 1: 5 calls
        for i in range(5):
            events.append(
                BehavioralAuditEvent(
                    user_id="user123",
                    timestamp=base_time + timedelta(hours=i),
                    tool_name="tool1",
                    sensitivity="low",
                )
            )

        # Day 2: 10 calls (max)
        for i in range(10):
            events.append(
                BehavioralAuditEvent(
                    user_id="user123",
                    timestamp=base_time + timedelta(days=1, hours=i),
                    tool_name="tool1",
                    sensitivity="low",
                )
            )

        # Day 3: 3 calls
        for i in range(3):
            events.append(
                BehavioralAuditEvent(
                    user_id="user123",
                    timestamp=base_time + timedelta(days=2, hours=i),
                    tool_name="tool1",
                    sensitivity="low",
                )
            )

        max_calls = analyzer._get_max_calls_per_day(events)
        assert max_calls == 10

    def test_get_max_calls_per_day_empty(self, analyzer):
        """Test max calls with no events"""
        assert analyzer._get_max_calls_per_day([]) == 0

    def test_get_typical_hours(self, analyzer):
        """Test extraction of typical hours"""
        events = []
        base_time = datetime(2024, 1, 1, 0, 0)

        # Create events at hours 9, 10, 11 (30 events each)
        for hour in [9, 10, 11]:
            for _ in range(30):
                events.append(
                    BehavioralAuditEvent(
                        user_id="user123",
                        timestamp=base_time.replace(hour=hour),
                        tool_name="tool1",
                        sensitivity="low",
                    )
                )

        # Add single event at hour 2 (should not be included)
        events.append(
            BehavioralAuditEvent(
                user_id="user123",
                timestamp=base_time.replace(hour=2),
                tool_name="tool1",
                sensitivity="low",
            )
        )

        typical_hours = analyzer._get_typical_hours(events, threshold=0.1)

        assert 9 in typical_hours
        assert 10 in typical_hours
        assert 11 in typical_hours
        assert 2 not in typical_hours  # Below 10% threshold

    def test_get_typical_days(self, analyzer):
        """Test extraction of typical days"""
        events = []
        base_time = datetime(2024, 1, 1, 10, 0)  # Monday

        # Create events for Mon-Fri (30 events each)
        for day_offset in range(5):
            for _ in range(30):
                events.append(
                    BehavioralAuditEvent(
                        user_id="user123",
                        timestamp=base_time + timedelta(days=day_offset),
                        tool_name="tool1",
                        sensitivity="low",
                    )
                )

        # Add single Saturday event
        events.append(
            BehavioralAuditEvent(
                user_id="user123",
                timestamp=base_time + timedelta(days=5),
                tool_name="tool1",
                sensitivity="low",
            )
        )

        typical_days = analyzer._get_typical_days(events, threshold=0.1)

        assert 0 in typical_days  # Monday
        assert 4 in typical_days  # Friday
        assert 5 not in typical_days  # Saturday (below threshold)

    def test_get_avg_result_size(self, analyzer):
        """Test calculation of average result size"""
        events = [
            BehavioralAuditEvent(
                user_id="user123",
                timestamp=datetime.now(),
                tool_name="tool1",
                sensitivity="low",
                result_size=100,
            ),
            BehavioralAuditEvent(
                user_id="user123",
                timestamp=datetime.now(),
                tool_name="tool1",
                sensitivity="low",
                result_size=200,
            ),
            BehavioralAuditEvent(
                user_id="user123",
                timestamp=datetime.now(),
                tool_name="tool1",
                sensitivity="low",
                result_size=0,  # Should be excluded
            ),
        ]

        avg_size = analyzer._get_avg_result_size(events)
        assert avg_size == 150.0

    def test_get_avg_result_size_empty(self, analyzer):
        """Test average result size with no data"""
        events = [
            BehavioralAuditEvent(
                user_id="user123",
                timestamp=datetime.now(),
                tool_name="tool1",
                sensitivity="low",
                result_size=0,
            )
        ]

        avg_size = analyzer._get_avg_result_size(events)
        assert avg_size == 0.0

    def test_get_max_sensitivity(self, analyzer):
        """Test extraction of maximum sensitivity level"""
        events = [
            BehavioralAuditEvent(
                user_id="user123",
                timestamp=datetime.now(),
                tool_name="tool1",
                sensitivity="low",
            ),
            BehavioralAuditEvent(
                user_id="user123",
                timestamp=datetime.now(),
                tool_name="tool1",
                sensitivity="high",
            ),
            BehavioralAuditEvent(
                user_id="user123",
                timestamp=datetime.now(),
                tool_name="tool1",
                sensitivity="medium",
            ),
        ]

        max_sensitivity = analyzer._get_max_sensitivity(events)
        assert max_sensitivity == "high"

    def test_get_max_sensitivity_critical(self, analyzer):
        """Test that critical is highest sensitivity"""
        events = [
            BehavioralAuditEvent(
                user_id="user123",
                timestamp=datetime.now(),
                tool_name="tool1",
                sensitivity="critical",
            ),
            BehavioralAuditEvent(
                user_id="user123",
                timestamp=datetime.now(),
                tool_name="tool1",
                sensitivity="high",
            ),
        ]

        max_sensitivity = analyzer._get_max_sensitivity(events)
        assert max_sensitivity == "critical"

    def test_get_typical_sensitivity(self, analyzer):
        """Test extraction of typical (most common) sensitivity"""
        events = [
            BehavioralAuditEvent(
                user_id="user123",
                timestamp=datetime.now(),
                tool_name="tool1",
                sensitivity="low",
            )
            for _ in range(10)
        ] + [
            BehavioralAuditEvent(
                user_id="user123",
                timestamp=datetime.now(),
                tool_name="tool1",
                sensitivity="high",
            )
            for _ in range(2)
        ]

        typical_sensitivity = analyzer._get_typical_sensitivity(events)
        assert typical_sensitivity == "low"

    def test_get_typical_sensitivity_empty(self, analyzer):
        """Test typical sensitivity with no events"""
        assert analyzer._get_typical_sensitivity([]) == "none"

    def test_get_typical_locations(self, analyzer):
        """Test extraction of typical locations"""
        events = [
            BehavioralAuditEvent(
                user_id="user123",
                timestamp=datetime.now(),
                tool_name="tool1",
                sensitivity="low",
                location="US-EAST",
            ),
            BehavioralAuditEvent(
                user_id="user123",
                timestamp=datetime.now(),
                tool_name="tool1",
                sensitivity="low",
                location="US-WEST",
            ),
            BehavioralAuditEvent(
                user_id="user123",
                timestamp=datetime.now(),
                tool_name="tool1",
                sensitivity="low",
                location=None,
            ),
        ]

        locations = analyzer._get_typical_locations(events)
        assert "US-EAST" in locations
        assert "US-WEST" in locations
        assert len(locations) == 2

    # Edge Case Tests

    @pytest.mark.asyncio
    async def test_no_anomalies_for_normal_behavior(self, analyzer):
        """Test that normal behavior doesn't trigger anomalies"""
        baseline = BehavioralBaseline(
            user_id="user123",
            created_at=datetime.now(),
            lookback_days=30,
            common_tools=["tool1", "tool2"],
            avg_calls_per_day=10.0,
            max_calls_per_day=20,
            typical_hours={9, 10, 11},
            typical_days={0, 1, 2, 3, 4},
            avg_records_per_query=100.0,
            max_records_per_query=500,
            max_sensitivity_level="medium",
            typical_sensitivity="low",
            typical_locations={"US-EAST"},
        )

        # Completely normal event
        event = BehavioralAuditEvent(
            user_id="user123",
            timestamp=datetime(2024, 1, 15, 10, 0),  # Monday, 10 AM
            tool_name="tool1",  # Common tool
            sensitivity="low",  # Normal sensitivity
            result_size=100,  # Normal data size
            location="US-EAST",  # Normal location
        )

        anomalies = await analyzer.detect_anomalies(event, baseline=baseline)

        assert len(anomalies) == 0

    @pytest.mark.asyncio
    async def test_excessive_data_not_triggered_below_threshold(self, analyzer):
        """Test that data below 3x threshold doesn't trigger anomaly"""
        baseline = BehavioralBaseline(
            user_id="user123",
            created_at=datetime.now(),
            lookback_days=30,
            common_tools=["tool1"],
            avg_calls_per_day=10.0,
            max_calls_per_day=20,
            typical_hours={9, 10, 11},
            typical_days={0, 1, 2, 3, 4},
            avg_records_per_query=100.0,
            max_records_per_query=500,
            max_sensitivity_level="medium",
            typical_sensitivity="low",
            typical_locations=set(),
        )

        # 2.5x = 1250, which is below 3x threshold
        event = BehavioralAuditEvent(
            user_id="user123",
            timestamp=datetime(2024, 1, 15, 10, 0),
            tool_name="tool1",
            sensitivity="low",
            result_size=1250,
        )

        anomalies = await analyzer.detect_anomalies(event, baseline=baseline)

        excessive_data_anomalies = [
            a for a in anomalies if a.type == AnomalyType.EXCESSIVE_DATA
        ]
        assert len(excessive_data_anomalies) == 0

    @pytest.mark.asyncio
    async def test_no_sensitivity_escalation_for_equal_level(self, analyzer):
        """Test that same sensitivity level doesn't trigger escalation"""
        baseline = BehavioralBaseline(
            user_id="user123",
            created_at=datetime.now(),
            lookback_days=30,
            common_tools=["tool1"],
            avg_calls_per_day=10.0,
            max_calls_per_day=20,
            typical_hours={9, 10, 11},
            typical_days={0, 1, 2, 3, 4},
            avg_records_per_query=100.0,
            max_records_per_query=500,
            max_sensitivity_level="medium",
            typical_sensitivity="low",
            typical_locations=set(),
        )

        event = BehavioralAuditEvent(
            user_id="user123",
            timestamp=datetime(2024, 1, 15, 10, 0),
            tool_name="tool1",
            sensitivity="medium",  # Equal to baseline max
        )

        anomalies = await analyzer.detect_anomalies(event, baseline=baseline)

        escalation_anomalies = [
            a for a in anomalies if a.type == AnomalyType.SENSITIVITY_ESCALATION
        ]
        assert len(escalation_anomalies) == 0

    # Performance Tests

    @pytest.mark.asyncio
    async def test_baseline_building_performance(self, analyzer):
        """Test that baseline building completes quickly"""
        import time

        # Create large dataset
        events = [
            BehavioralAuditEvent(
                user_id="user123",
                timestamp=datetime.now() - timedelta(days=i, hours=h),
                tool_name=f"tool{i % 5}",
                sensitivity=["low", "medium", "high"][i % 3],
                result_size=i * 10,
            )
            for i in range(100)
            for h in range(5)
        ]

        start = time.time()
        result = await analyzer.build_baseline("user123", lookback_days=30, events=events)
        elapsed = time.time() - start

        assert result is not None
        # Building baseline should be fast even with 500 events
        assert elapsed < 0.1  # 100ms

    @pytest.mark.asyncio
    async def test_anomaly_detection_performance(self, analyzer):
        """Test that anomaly detection is fast"""
        import time

        baseline = BehavioralBaseline(
            user_id="user123",
            created_at=datetime.now(),
            lookback_days=30,
            common_tools=["tool1", "tool2"],
            avg_calls_per_day=10.0,
            max_calls_per_day=20,
            typical_hours={9, 10, 11},
            typical_days={0, 1, 2, 3, 4},
            avg_records_per_query=100.0,
            max_records_per_query=500,
            max_sensitivity_level="medium",
            typical_sensitivity="low",
            typical_locations={"US-EAST"},
        )

        event = BehavioralAuditEvent(
            user_id="user123",
            timestamp=datetime(2024, 1, 15, 2, 0),
            tool_name="unusual_tool",
            sensitivity="critical",
            result_size=2000,
            location="EU-WEST",
        )

        start = time.time()
        result = await analyzer.detect_anomalies(event, baseline=baseline)
        elapsed = time.time() - start

        assert len(result) > 0
        # Detection should be very fast
        assert elapsed < 0.01  # 10ms
