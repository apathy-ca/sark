"""Tests for Datadog SIEM integration."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import httpx
import pytest

from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel
from sark.services.audit.siem.datadog import DatadogConfig, DatadogSIEM


@pytest.fixture
def datadog_config() -> DatadogConfig:
    """Create a test Datadog configuration."""
    return DatadogConfig(
        api_key="test-api-key-12345",
        app_key="test-app-key-67890",
        site="datadoghq.com",
        service="test_sark",
        environment="test",
        hostname="test-host-01",
        verify_ssl=True,
        timeout_seconds=30,
    )


@pytest.fixture
def datadog_siem(datadog_config: DatadogConfig) -> DatadogSIEM:
    """Create a test Datadog SIEM instance."""
    return DatadogSIEM(datadog_config)


@pytest.fixture
def audit_event() -> AuditEvent:
    """Create a test audit event."""
    return AuditEvent(
        id=uuid4(),
        timestamp=datetime.now(UTC),
        event_type=AuditEventType.AUTHORIZATION_DENIED,
        severity=SeverityLevel.CRITICAL,
        user_id=uuid4(),
        user_email="test@example.com",
        server_id=uuid4(),
        tool_name="test_tool",
        decision="deny",
        policy_id=uuid4(),
        ip_address="192.168.1.1",
        user_agent="TestAgent/1.0",
        request_id="test-request-123",
        details={"key": "value", "user_role": "developer"},
    )


class TestDatadogConfig:
    """Tests for DatadogConfig."""

    def test_default_config(self):
        """Test default Datadog configuration."""
        config = DatadogConfig()
        assert config.api_key == ""
        assert config.app_key == ""
        assert config.site == "datadoghq.com"
        assert config.service == "sark"
        assert config.environment == "production"
        assert config.hostname is None
        assert config.verify_ssl is True

    def test_custom_config(self):
        """Test custom Datadog configuration."""
        config = DatadogConfig(
            api_key="custom-api-key",
            app_key="custom-app-key",
            site="datadoghq.eu",
            service="custom-service",
            environment="staging",
            hostname="custom-host",
            verify_ssl=False,
        )
        assert config.api_key == "custom-api-key"
        assert config.app_key == "custom-app-key"
        assert config.site == "datadoghq.eu"
        assert config.service == "custom-service"
        assert config.environment == "staging"
        assert config.hostname == "custom-host"
        assert config.verify_ssl is False

    def test_different_sites(self):
        """Test configuration for different Datadog sites."""
        # US site
        us_config = DatadogConfig(site="datadoghq.com")
        assert us_config.site == "datadoghq.com"

        # EU site
        eu_config = DatadogConfig(site="datadoghq.eu")
        assert eu_config.site == "datadoghq.eu"

        # US3 site
        us3_config = DatadogConfig(site="us3.datadoghq.com")
        assert us3_config.site == "us3.datadoghq.com"


class TestDatadogSIEM:
    """Tests for DatadogSIEM."""

    def test_initialization(self, datadog_config: DatadogConfig):
        """Test Datadog SIEM initialization."""
        siem = DatadogSIEM(datadog_config)
        assert siem.datadog_config == datadog_config
        assert siem._client is not None
        assert siem._logs_url == "https://http-intake.logs.datadoghq.com/api/v2/logs"

    def test_initialization_without_api_key(self):
        """Test initialization without API key logs warning."""
        config = DatadogConfig(api_key="")
        siem = DatadogSIEM(config)
        assert siem.datadog_config.api_key == ""

    def test_logs_url_construction(self):
        """Test logs URL construction for different sites."""
        # US site
        us_config = DatadogConfig(site="datadoghq.com")
        us_siem = DatadogSIEM(us_config)
        assert us_siem._logs_url == "https://http-intake.logs.datadoghq.com/api/v2/logs"

        # EU site
        eu_config = DatadogConfig(site="datadoghq.eu")
        eu_siem = DatadogSIEM(eu_config)
        assert eu_siem._logs_url == "https://http-intake.logs.datadoghq.eu/api/v2/logs"

    def test_format_event(self, datadog_siem: DatadogSIEM, audit_event: AuditEvent):
        """Test event formatting."""
        formatted = datadog_siem.format_event(audit_event)
        assert isinstance(formatted, dict)
        assert formatted["event_type"] == AuditEventType.AUTHORIZATION_DENIED.value
        assert formatted["severity"] == SeverityLevel.CRITICAL.value
        assert formatted["user_email"] == "test@example.com"

    def test_format_datadog_event(self, datadog_siem: DatadogSIEM, audit_event: AuditEvent):
        """Test Datadog-specific event formatting."""
        datadog_event = datadog_siem._format_datadog_event(audit_event)

        # Check required Datadog fields
        assert datadog_event["ddsource"] == "test_sark"
        assert datadog_event["service"] == "test_sark"
        assert "ddtags" in datadog_event
        assert "env:test" in datadog_event["ddtags"]
        assert "service:test_sark" in datadog_event["ddtags"]
        assert f"event_type:{AuditEventType.AUTHORIZATION_DENIED.value}" in datadog_event["ddtags"]
        assert f"severity:{SeverityLevel.CRITICAL.value}" in datadog_event["ddtags"]
        assert "user_role:developer" in datadog_event["ddtags"]

        # Check custom attributes
        assert "sark" in datadog_event
        assert isinstance(datadog_event["sark"], dict)

        # Check top-level fields
        assert datadog_event["event_type"] == AuditEventType.AUTHORIZATION_DENIED.value
        assert datadog_event["severity"] == SeverityLevel.CRITICAL.value
        assert datadog_event["user_email"] == "test@example.com"
        assert datadog_event["decision"] == "deny"

        # Check hostname
        assert datadog_event["hostname"] == "test-host-01"

        # Check timestamp
        assert "timestamp" in datadog_event
        assert isinstance(datadog_event["timestamp"], int)

    def test_format_datadog_event_without_hostname(
        self, datadog_config: DatadogConfig, audit_event: AuditEvent
    ):
        """Test Datadog event formatting without hostname."""
        config = DatadogConfig(
            api_key=datadog_config.api_key,
            hostname=None,
        )
        siem = DatadogSIEM(config)
        datadog_event = siem._format_datadog_event(audit_event)

        assert "hostname" not in datadog_event

    @pytest.mark.asyncio
    async def test_send_event_success(self, datadog_siem: DatadogSIEM, audit_event: AuditEvent):
        """Test successful single event send."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.text = '{"status":"ok"}'

        with patch.object(datadog_siem._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await datadog_siem.send_event(audit_event)

            assert result is True
            assert mock_post.call_count == 1
            assert datadog_siem.metrics.events_sent == 1
            assert datadog_siem.metrics.events_failed == 0

            # Verify the request payload was an array
            call_args = mock_post.call_args
            assert "json" in call_args.kwargs
            assert isinstance(call_args.kwargs["json"], list)
            assert len(call_args.kwargs["json"]) == 1

    @pytest.mark.asyncio
    async def test_send_event_http_error(self, datadog_siem: DatadogSIEM, audit_event: AuditEvent):
        """Test event send with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = '{"error":"Invalid API key"}'

        with patch.object(datadog_siem._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await datadog_siem.send_event(audit_event)

            assert result is False
            assert datadog_siem.metrics.events_sent == 0
            assert datadog_siem.metrics.events_failed == 1
            assert "http_403" in datadog_siem.metrics.error_counts

    @pytest.mark.asyncio
    async def test_send_event_timeout(self, datadog_siem: DatadogSIEM, audit_event: AuditEvent):
        """Test event send with timeout."""
        with patch.object(
            datadog_siem._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timeout")

            with pytest.raises(httpx.TimeoutException):
                await datadog_siem.send_event(audit_event)

            assert datadog_siem.metrics.events_failed == 1
            assert "timeout" in datadog_siem.metrics.error_counts

    @pytest.mark.asyncio
    async def test_send_event_connection_error(
        self, datadog_siem: DatadogSIEM, audit_event: AuditEvent
    ):
        """Test event send with connection error."""
        with patch.object(
            datadog_siem._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection refused")

            with pytest.raises(httpx.ConnectError):
                await datadog_siem.send_event(audit_event)

            assert datadog_siem.metrics.events_failed == 1
            assert "connection_error" in datadog_siem.metrics.error_counts

    @pytest.mark.asyncio
    async def test_send_event_generic_exception(
        self, datadog_siem: DatadogSIEM, audit_event: AuditEvent
    ):
        """Test event send with generic exception."""
        with patch.object(
            datadog_siem._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.side_effect = ValueError("Invalid data")

            with pytest.raises(ValueError):
                await datadog_siem.send_event(audit_event)

            assert datadog_siem.metrics.events_failed == 1
            assert "ValueError" in datadog_siem.metrics.error_counts

    @pytest.mark.asyncio
    async def test_send_batch_success(self, datadog_siem: DatadogSIEM, audit_event: AuditEvent):
        """Test successful batch send."""
        events = [audit_event, audit_event, audit_event]

        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.text = '{"status":"ok"}'

        with patch.object(datadog_siem._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await datadog_siem.send_batch(events)

            assert result is True
            assert mock_post.call_count == 1
            assert datadog_siem.metrics.events_sent == 3
            assert datadog_siem.metrics.batches_sent == 1

            # Verify the request payload was an array with 3 items
            call_args = mock_post.call_args
            assert "json" in call_args.kwargs
            assert isinstance(call_args.kwargs["json"], list)
            assert len(call_args.kwargs["json"]) == 3

    @pytest.mark.asyncio
    async def test_send_batch_empty(self, datadog_siem: DatadogSIEM):
        """Test sending an empty batch."""
        result = await datadog_siem.send_batch([])
        assert result is True

    @pytest.mark.asyncio
    async def test_send_batch_http_error(self, datadog_siem: DatadogSIEM, audit_event: AuditEvent):
        """Test batch send with HTTP error."""
        events = [audit_event, audit_event]

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = '{"error":"Internal server error"}'

        with patch.object(datadog_siem._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await datadog_siem.send_batch(events)

            assert result is False
            assert datadog_siem.metrics.events_failed == 2
            assert datadog_siem.metrics.batches_failed == 1

    @pytest.mark.asyncio
    async def test_send_batch_timeout(self, datadog_siem: DatadogSIEM, audit_event: AuditEvent):
        """Test batch send with timeout."""
        events = [audit_event, audit_event]

        with patch.object(
            datadog_siem._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timeout")

            with pytest.raises(httpx.TimeoutException):
                await datadog_siem.send_batch(events)

            assert datadog_siem.metrics.events_failed == 2
            assert "timeout" in datadog_siem.metrics.error_counts

    @pytest.mark.asyncio
    async def test_health_check_success(self, datadog_siem: DatadogSIEM):
        """Test successful health check."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.text = '{"status":"ok"}'

        with patch.object(datadog_siem._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            health = await datadog_siem.health_check()

            assert health.healthy is True
            assert health.latency_ms is not None
            assert health.latency_ms > 0
            assert health.error_message is None
            assert "logs_url" in health.details
            assert mock_post.call_count == 1

    @pytest.mark.asyncio
    async def test_health_check_failure(self, datadog_siem: DatadogSIEM):
        """Test health check with failure."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = '{"error":"Unauthorized"}'

        with patch.object(datadog_siem._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            health = await datadog_siem.health_check()

            assert health.healthy is False
            assert health.error_message is not None
            assert "401" in health.error_message

    @pytest.mark.asyncio
    async def test_health_check_timeout(self, datadog_siem: DatadogSIEM):
        """Test health check with timeout."""
        with patch.object(datadog_siem._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timeout")

            health = await datadog_siem.health_check()

            assert health.healthy is False
            assert "Timeout" in health.error_message

    @pytest.mark.asyncio
    async def test_health_check_connection_error(self, datadog_siem: DatadogSIEM):
        """Test health check with connection error."""
        with patch.object(datadog_siem._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection refused")

            health = await datadog_siem.health_check()

            assert health.healthy is False
            assert "Connection error" in health.error_message

    @pytest.mark.asyncio
    async def test_health_check_generic_exception(self, datadog_siem: DatadogSIEM):
        """Test health check with generic exception."""
        with patch.object(datadog_siem._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = ValueError("Invalid configuration")

            health = await datadog_siem.health_check()

            assert health.healthy is False
            assert "ValueError" in health.error_message

    @pytest.mark.asyncio
    async def test_close(self, datadog_siem: DatadogSIEM):
        """Test closing the SIEM connection."""
        with patch.object(
            datadog_siem._client, "aclose", new_callable=AsyncMock
        ) as mock_close:
            await datadog_siem.close()
            assert mock_close.call_count == 1

    @pytest.mark.asyncio
    async def test_metrics_tracking(self, datadog_siem: DatadogSIEM, audit_event: AuditEvent):
        """Test that metrics are properly tracked."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.text = '{"status":"ok"}'

        with patch.object(datadog_siem._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            # Send 3 events
            await datadog_siem.send_event(audit_event)
            await datadog_siem.send_event(audit_event)
            await datadog_siem.send_event(audit_event)

            metrics = datadog_siem.get_metrics()
            assert metrics.events_sent == 3
            assert metrics.batches_sent == 3
            assert metrics.success_rate == 100.0
            assert metrics.last_success is not None

    def test_event_timestamp_format(self, datadog_siem: DatadogSIEM, audit_event: AuditEvent):
        """Test that event timestamp is in milliseconds format."""
        datadog_event = datadog_siem._format_datadog_event(audit_event)

        assert "timestamp" in datadog_event
        # Timestamp should be in milliseconds
        assert isinstance(datadog_event["timestamp"], int)
        # Should be a reasonable timestamp (after 2020 in milliseconds)
        assert datadog_event["timestamp"] > 1577836800000  # Jan 1, 2020 in ms

    def test_tags_formatting(self, datadog_siem: DatadogSIEM, audit_event: AuditEvent):
        """Test that tags are properly formatted."""
        datadog_event = datadog_siem._format_datadog_event(audit_event)

        # Tags should be comma-separated string
        assert isinstance(datadog_event["ddtags"], str)

        # Split tags and verify
        tags = datadog_event["ddtags"].split(",")
        tag_dict = {tag.split(":")[0]: tag.split(":")[1] for tag in tags if ":" in tag}

        assert tag_dict["env"] == "test"
        assert tag_dict["service"] == "test_sark"
        assert tag_dict["event_type"] == AuditEventType.AUTHORIZATION_DENIED.value
        assert tag_dict["severity"] == SeverityLevel.CRITICAL.value
        assert tag_dict["user_role"] == "developer"

    def test_custom_attributes_structure(self, datadog_siem: DatadogSIEM, audit_event: AuditEvent):
        """Test that custom attributes are properly structured."""
        datadog_event = datadog_siem._format_datadog_event(audit_event)

        # All SARK data should be under 'sark' key
        assert "sark" in datadog_event
        sark_data = datadog_event["sark"]

        assert "id" in sark_data
        assert "timestamp" in sark_data
        assert "event_type" in sark_data
        assert "severity" in sark_data
        assert "user_email" in sark_data
        assert "details" in sark_data
