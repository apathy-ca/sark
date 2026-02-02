"""Tests for SIEM event formatting verification.

These tests verify that events are correctly formatted for each SIEM platform
without requiring actual SIEM credentials or connectivity.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel
from sark.services.audit.siem import DatadogConfig, DatadogSIEM, SplunkConfig, SplunkSIEM


@pytest.fixture
def sample_event() -> AuditEvent:
    """Create a sample audit event with all fields populated."""
    return AuditEvent(
        id=uuid4(),
        timestamp=datetime.now(UTC),
        event_type=AuditEventType.TOOL_INVOKED,
        severity=SeverityLevel.HIGH,
        user_id=uuid4(),
        user_email="test@example.com",
        server_id=uuid4(),
        tool_name="bash",
        decision="allow",
        policy_id=uuid4(),
        ip_address="192.168.1.1",
        user_agent="TestAgent/1.0",
        request_id=str(uuid4()),
        details={
            "command": "ls -la",
            "exit_code": 0,
            "duration_ms": 123,
            "nested": {"key": "value"},
        },
    )


@pytest.fixture
def minimal_event() -> AuditEvent:
    """Create a minimal audit event with only required fields."""
    return AuditEvent(
        id=uuid4(),
        timestamp=datetime.now(UTC),
        event_type=AuditEventType.USER_LOGIN,
        severity=SeverityLevel.LOW,
        user_email="minimal@example.com",
    )


class TestSplunkEventFormatting:
    """Test Splunk HEC event formatting."""

    @pytest.fixture
    def splunk_siem(self) -> SplunkSIEM:
        """Create Splunk SIEM instance for testing."""
        config = SplunkConfig(
            hec_url="https://localhost:8088/services/collector",
            hec_token="test-token",
            index="test",
            sourcetype="sark:audit:event",
            source="sark_test",
        )
        return SplunkSIEM(config)

    def test_splunk_event_structure(self, splunk_siem: SplunkSIEM, sample_event: AuditEvent):
        """Test that Splunk event has correct HEC structure."""
        formatted = splunk_siem._format_splunk_event(sample_event)

        # Verify HEC format structure
        assert "time" in formatted, "Missing 'time' field (required by HEC)"
        assert "event" in formatted, "Missing 'event' field (required by HEC)"
        assert "source" in formatted, "Missing 'source' field"
        assert "sourcetype" in formatted, "Missing 'sourcetype' field"
        assert "index" in formatted, "Missing 'index' field"
        assert "host" in formatted, "Missing 'host' field"

        # Verify time is epoch timestamp
        assert isinstance(formatted["time"], (int, float)), "Time should be numeric epoch"

        # Verify event contains audit data
        event_data = formatted["event"]
        assert isinstance(event_data, dict), "Event should be a dictionary"

    def test_splunk_event_field_mapping(self, splunk_siem: SplunkSIEM, sample_event: AuditEvent):
        """Test that all audit event fields are correctly mapped."""
        formatted = splunk_siem._format_splunk_event(sample_event)
        event_data = formatted["event"]

        # Verify all key fields are present
        assert event_data["id"] == str(sample_event.id)
        assert event_data["event_type"] == sample_event.event_type.value
        assert event_data["severity"] == sample_event.severity.value
        assert event_data["user_email"] == sample_event.user_email
        assert event_data["tool_name"] == sample_event.tool_name
        assert event_data["decision"] == sample_event.decision
        assert event_data["ip_address"] == sample_event.ip_address
        assert event_data["user_agent"] == sample_event.user_agent
        assert event_data["request_id"] == sample_event.request_id

        # Verify UUIDs are converted to strings
        assert event_data["user_id"] == str(sample_event.user_id)
        assert event_data["server_id"] == str(sample_event.server_id)
        assert event_data["policy_id"] == str(sample_event.policy_id)

        # Verify details are preserved
        assert event_data["details"] == sample_event.details
        assert event_data["details"]["command"] == "ls -la"
        assert event_data["details"]["nested"]["key"] == "value"

    def test_splunk_timestamp_format(self, splunk_siem: SplunkSIEM, sample_event: AuditEvent):
        """Test that timestamp is correctly formatted as epoch time."""
        formatted = splunk_siem._format_splunk_event(sample_event)

        # Verify time field exists and is numeric
        assert "time" in formatted
        assert isinstance(formatted["time"], (int, float))

        # Verify it's a reasonable epoch timestamp (after 2020, before 2100)
        epoch_2020 = 1577836800  # Jan 1, 2020
        epoch_2100 = 4102444800  # Jan 1, 2100
        assert epoch_2020 < formatted["time"] < epoch_2100

        # Verify event also contains timestamp string
        assert "timestamp" in formatted["event"]
        assert isinstance(formatted["event"]["timestamp"], str)

    def test_splunk_metadata_fields(self, splunk_siem: SplunkSIEM, sample_event: AuditEvent):
        """Test that Splunk metadata fields are correctly set."""
        formatted = splunk_siem._format_splunk_event(sample_event)

        # Verify metadata from config
        assert formatted["source"] == splunk_siem.splunk_config.source
        assert formatted["sourcetype"] == splunk_siem.splunk_config.sourcetype
        assert formatted["index"] == splunk_siem.splunk_config.index

        # Verify host is set (should default to server_id)
        assert formatted["host"] is not None

    def test_splunk_minimal_event(self, splunk_siem: SplunkSIEM, minimal_event: AuditEvent):
        """Test formatting of event with minimal fields."""
        formatted = splunk_siem._format_splunk_event(minimal_event)

        # Should still have required HEC fields
        assert "time" in formatted
        assert "event" in formatted
        assert "source" in formatted
        assert "sourcetype" in formatted

        # Event data should have minimal fields
        event_data = formatted["event"]
        assert event_data["id"] == str(minimal_event.id)
        assert event_data["event_type"] == minimal_event.event_type.value
        assert event_data["user_email"] == minimal_event.user_email

        # Optional fields should be None or absent
        assert event_data.get("tool_name") is None
        assert event_data.get("decision") is None
        assert event_data.get("details") in (None, {})

    def test_splunk_special_characters(self, splunk_siem: SplunkSIEM):
        """Test handling of special characters in event data."""
        event = AuditEvent(
            id=uuid4(),
            timestamp=datetime.now(UTC),
            event_type=AuditEventType.TOOL_INVOKED,
            severity=SeverityLevel.MEDIUM,
            user_email="test+special@example.com",
            tool_name="bash",
            details={
                "command": "echo \"Hello, World!\" | grep 'test'",
                "output": "Line 1\nLine 2\nLine 3",
                "special": "Chars: <>&\"'",
            },
        )

        formatted = splunk_siem._format_splunk_event(event)
        event_data = formatted["event"]

        # Verify special characters are preserved
        assert event_data["user_email"] == "test+special@example.com"
        assert '"Hello, World!"' in event_data["details"]["command"]
        assert "\n" in event_data["details"]["output"]
        assert event_data["details"]["special"] == "Chars: <>&\"'"


class TestDatadogEventFormatting:
    """Test Datadog Logs API event formatting."""

    @pytest.fixture
    def datadog_siem(self) -> DatadogSIEM:
        """Create Datadog SIEM instance for testing."""
        config = DatadogConfig(
            api_key="test-api-key",
            site="datadoghq.com",
            service="sark_test",
            environment="test",
        )
        return DatadogSIEM(config)

    def test_datadog_event_structure(self, datadog_siem: DatadogSIEM, sample_event: AuditEvent):
        """Test that Datadog event has correct Logs API structure."""
        formatted = datadog_siem._format_datadog_event(sample_event)

        # Verify Datadog Logs API required fields
        assert "ddsource" in formatted, "Missing 'ddsource' field (required by Datadog)"
        assert "ddtags" in formatted, "Missing 'ddtags' field"
        assert "service" in formatted, "Missing 'service' field"
        assert "message" in formatted, "Missing 'message' field"

        # Verify custom attributes
        assert "sark" in formatted, "Missing nested 'sark' data"
        assert isinstance(formatted["sark"], dict), "Nested SARK data should be dict"

        # Verify top-level searchable fields
        assert "event_id" in formatted
        assert "event_type" in formatted
        assert "severity" in formatted
        assert "user_email" in formatted

    def test_datadog_tags_format(self, datadog_siem: DatadogSIEM, sample_event: AuditEvent):
        """Test that Datadog tags are correctly formatted."""
        formatted = datadog_siem._format_datadog_event(sample_event)

        # Verify tags field exists and is string
        assert "ddtags" in formatted
        assert isinstance(formatted["ddtags"], str), "Tags should be comma-separated string"

        tags = formatted["ddtags"]

        # Verify required tags are present
        assert f"env:{datadog_siem.datadog_config.environment}" in tags
        assert f"service:{datadog_siem.datadog_config.service}" in tags
        assert f"event_type:{sample_event.event_type.value}" in tags
        assert f"severity:{sample_event.severity.value}" in tags

        # Verify tag format (key:value pairs separated by commas)
        for tag in tags.split(","):
            assert ":" in tag, f"Tag '{tag}' should be in key:value format"

    def test_datadog_event_field_mapping(self, datadog_siem: DatadogSIEM, sample_event: AuditEvent):
        """Test that all audit event fields are correctly mapped."""
        formatted = datadog_siem._format_datadog_event(sample_event)

        # Verify top-level searchable fields
        assert formatted["event_id"] == str(sample_event.id)
        assert formatted["event_type"] == sample_event.event_type.value
        assert formatted["severity"] == sample_event.severity.value
        assert formatted["user_email"] == sample_event.user_email
        assert formatted["decision"] == sample_event.decision

        # Verify nested SARK data contains all fields
        sark_data = formatted["sark"]
        assert sark_data["id"] == str(sample_event.id)
        assert sark_data["event_type"] == sample_event.event_type.value
        assert sark_data["user_email"] == sample_event.user_email
        assert sark_data["tool_name"] == sample_event.tool_name
        assert sark_data["details"] == sample_event.details

    def test_datadog_timestamp_format(self, datadog_siem: DatadogSIEM, sample_event: AuditEvent):
        """Test that timestamp is correctly formatted as milliseconds epoch."""
        formatted = datadog_siem._format_datadog_event(sample_event)

        # Verify timestamp field exists
        assert "timestamp" in formatted

        # Should be in milliseconds (13 digits)
        timestamp = formatted["timestamp"]
        assert isinstance(timestamp, int)
        assert len(str(timestamp)) == 13, "Timestamp should be in milliseconds"

        # Verify it's a reasonable timestamp (after 2020, before 2100)
        epoch_2020_ms = 1577836800000  # Jan 1, 2020 in milliseconds
        epoch_2100_ms = 4102444800000  # Jan 1, 2100 in milliseconds
        assert epoch_2020_ms < timestamp < epoch_2100_ms

    def test_datadog_service_fields(self, datadog_siem: DatadogSIEM, sample_event: AuditEvent):
        """Test that Datadog service fields are correctly set."""
        formatted = datadog_siem._format_datadog_event(sample_event)

        # Verify service metadata from config
        assert formatted["ddsource"] == datadog_siem.datadog_config.service
        assert formatted["service"] == datadog_siem.datadog_config.service

    def test_datadog_message_field(self, datadog_siem: DatadogSIEM, sample_event: AuditEvent):
        """Test that message field is meaningful."""
        formatted = datadog_siem._format_datadog_event(sample_event)

        # Verify message exists and contains event type
        assert "message" in formatted
        message = formatted["message"]
        assert isinstance(message, str)
        assert "SARK" in message
        assert sample_event.event_type.value in message

    def test_datadog_minimal_event(self, datadog_siem: DatadogSIEM, minimal_event: AuditEvent):
        """Test formatting of event with minimal fields."""
        formatted = datadog_siem._format_datadog_event(minimal_event)

        # Should still have required Datadog fields
        assert "ddsource" in formatted
        assert "ddtags" in formatted
        assert "service" in formatted
        assert "message" in formatted
        assert "sark" in formatted

        # Verify minimal event data
        assert formatted["event_id"] == str(minimal_event.id)
        assert formatted["event_type"] == minimal_event.event_type.value
        assert formatted["user_email"] == minimal_event.user_email

        # Optional fields should be None
        assert formatted.get("decision") is None

    def test_datadog_hostname_field(self):
        """Test that hostname field is included when configured."""
        config = DatadogConfig(
            api_key="test-api-key",
            site="datadoghq.com",
            service="sark_test",
            hostname="test-host-01",
        )
        datadog_siem = DatadogSIEM(config)

        event = AuditEvent(
            id=uuid4(),
            timestamp=datetime.now(UTC),
            event_type=AuditEventType.TOOL_INVOKED,
            severity=SeverityLevel.MEDIUM,
            user_email="test@example.com",
        )

        formatted = datadog_siem._format_datadog_event(event)

        # Verify hostname is included
        assert "hostname" in formatted
        assert formatted["hostname"] == "test-host-01"

    def test_datadog_special_characters(self, datadog_siem: DatadogSIEM):
        """Test handling of special characters in event data."""
        event = AuditEvent(
            id=uuid4(),
            timestamp=datetime.now(UTC),
            event_type=AuditEventType.TOOL_INVOKED,
            severity=SeverityLevel.MEDIUM,
            user_email="test+special@example.com",
            tool_name="bash",
            details={
                "command": "echo \"Hello, World!\" | grep 'test'",
                "output": "Line 1\nLine 2\nLine 3",
                "special": "Chars: <>&\"'",
            },
        )

        formatted = datadog_siem._format_datadog_event(event)

        # Verify special characters are preserved in nested data
        sark_data = formatted["sark"]
        assert sark_data["user_email"] == "test+special@example.com"
        assert '"Hello, World!"' in sark_data["details"]["command"]
        assert "\n" in sark_data["details"]["output"]
        assert sark_data["details"]["special"] == "Chars: <>&\"'"


class TestEventFormattingConsistency:
    """Test consistency across SIEM formats."""

    @pytest.fixture
    def splunk_siem(self) -> SplunkSIEM:
        """Create Splunk SIEM instance."""
        return SplunkSIEM(
            SplunkConfig(
                hec_url="https://localhost:8088",
                hec_token="test",
                index="test",
            )
        )

    @pytest.fixture
    def datadog_siem(self) -> DatadogSIEM:
        """Create Datadog SIEM instance."""
        return DatadogSIEM(
            DatadogConfig(
                api_key="test",
                site="datadoghq.com",
                service="test",
            )
        )

    def test_both_formats_contain_all_fields(
        self, splunk_siem: SplunkSIEM, datadog_siem: DatadogSIEM, sample_event: AuditEvent
    ):
        """Test that both SIEM formats contain all event fields."""
        splunk_formatted = splunk_siem._format_splunk_event(sample_event)
        datadog_formatted = datadog_siem._format_datadog_event(sample_event)

        # Extract event data from both formats
        splunk_data = splunk_formatted["event"]
        datadog_data = datadog_formatted["sark"]

        # Verify key fields are in both
        key_fields = [
            "id",
            "event_type",
            "severity",
            "user_email",
            "tool_name",
            "decision",
            "details",
        ]

        for field in key_fields:
            assert field in splunk_data, f"Field '{field}' missing from Splunk format"
            assert field in datadog_data, f"Field '{field}' missing from Datadog format"
            # Values should be equal (both convert UUIDs to strings)
            if splunk_data.get(field) is not None:
                assert splunk_data[field] == datadog_data[field], f"Field '{field}' values differ"

    def test_timestamp_precision(
        self, splunk_siem: SplunkSIEM, datadog_siem: DatadogSIEM, sample_event: AuditEvent
    ):
        """Test that timestamps maintain precision across formats."""
        splunk_formatted = splunk_siem._format_splunk_event(sample_event)
        datadog_formatted = datadog_siem._format_datadog_event(sample_event)

        # Convert both to milliseconds for comparison
        splunk_ms = int(splunk_formatted["time"] * 1000)
        datadog_ms = datadog_formatted["timestamp"]

        # Should be within 1 second of each other (1000ms)
        assert abs(splunk_ms - datadog_ms) < 1000, "Timestamps differ by more than 1 second"

    def test_special_field_handling(self, splunk_siem: SplunkSIEM, datadog_siem: DatadogSIEM):
        """Test that both formats handle special field values consistently."""
        # Test with None values
        event = AuditEvent(
            id=uuid4(),
            timestamp=datetime.now(UTC),
            event_type=AuditEventType.TOOL_INVOKED,
            severity=SeverityLevel.LOW,
            user_email="test@example.com",
            tool_name=None,  # Explicitly None
            decision=None,
            details=None,
        )

        splunk_formatted = splunk_siem._format_splunk_event(event)
        datadog_formatted = datadog_siem._format_datadog_event(event)

        # Both should handle None values gracefully
        assert splunk_formatted["event"]["tool_name"] is None
        assert datadog_formatted["sark"]["tool_name"] is None

    def test_details_dictionary_preservation(
        self, splunk_siem: SplunkSIEM, datadog_siem: DatadogSIEM
    ):
        """Test that complex details dictionaries are preserved in both formats."""
        complex_details = {
            "string": "value",
            "number": 123,
            "float": 45.67,
            "boolean": True,
            "list": [1, 2, 3],
            "nested": {
                "deep": {
                    "key": "value",
                },
            },
            "none_value": None,
        }

        event = AuditEvent(
            id=uuid4(),
            timestamp=datetime.now(UTC),
            event_type=AuditEventType.TOOL_INVOKED,
            severity=SeverityLevel.MEDIUM,
            user_email="test@example.com",
            details=complex_details,
        )

        splunk_formatted = splunk_siem._format_splunk_event(event)
        datadog_formatted = datadog_siem._format_datadog_event(event)

        # Both should preserve the complex structure
        assert splunk_formatted["event"]["details"] == complex_details
        assert datadog_formatted["sark"]["details"] == complex_details
