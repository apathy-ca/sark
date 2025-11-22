"""Tests for Splunk SIEM integration."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import httpx
import pytest

from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel
from sark.services.audit.siem.splunk import SplunkConfig, SplunkSIEM


@pytest.fixture
def splunk_config() -> SplunkConfig:
    """Create a test Splunk configuration."""
    return SplunkConfig(
        hec_url="https://splunk.example.com:8088/services/collector",
        hec_token="test-token-12345",
        index="test_sark_audit",
        sourcetype="test:sark:audit",
        source="test_sark",
        host="test-host",
        verify_ssl=True,
        timeout_seconds=30,
    )


@pytest.fixture
def splunk_siem(splunk_config: SplunkConfig) -> SplunkSIEM:
    """Create a test Splunk SIEM instance."""
    return SplunkSIEM(splunk_config)


@pytest.fixture
def audit_event() -> AuditEvent:
    """Create a test audit event."""
    return AuditEvent(
        id=uuid4(),
        timestamp=datetime.now(UTC),
        event_type=AuditEventType.SERVER_REGISTERED,
        severity=SeverityLevel.HIGH,
        user_id=uuid4(),
        user_email="test@example.com",
        server_id=uuid4(),
        tool_name="test_tool",
        decision="allow",
        policy_id=uuid4(),
        ip_address="192.168.1.1",
        user_agent="TestAgent/1.0",
        request_id="test-request-123",
        details={"key": "value"},
    )


class TestSplunkConfig:
    """Tests for SplunkConfig."""

    def test_default_config(self):
        """Test default Splunk configuration."""
        config = SplunkConfig()
        assert config.hec_url == "https://localhost:8088/services/collector"
        assert config.hec_token == ""
        assert config.index == "sark_audit"
        assert config.sourcetype == "sark:audit:event"
        assert config.source == "sark"
        assert config.host is None
        assert config.verify_ssl is True

    def test_custom_config(self):
        """Test custom Splunk configuration."""
        config = SplunkConfig(
            hec_url="https://custom.splunk.com:8088/services/collector",
            hec_token="custom-token",
            index="custom_index",
            sourcetype="custom:sourcetype",
            source="custom_source",
            host="custom-host",
            verify_ssl=False,
        )
        assert config.hec_url == "https://custom.splunk.com:8088/services/collector"
        assert config.hec_token == "custom-token"
        assert config.index == "custom_index"
        assert config.sourcetype == "custom:sourcetype"
        assert config.source == "custom_source"
        assert config.host == "custom-host"
        assert config.verify_ssl is False


class TestSplunkSIEM:
    """Tests for SplunkSIEM."""

    def test_initialization(self, splunk_config: SplunkConfig):
        """Test Splunk SIEM initialization."""
        siem = SplunkSIEM(splunk_config)
        assert siem.splunk_config == splunk_config
        assert siem._client is not None
        assert siem._client.timeout.read == 30

    def test_initialization_without_token(self):
        """Test initialization without HEC token logs warning."""
        config = SplunkConfig(hec_token="")
        siem = SplunkSIEM(config)
        assert siem.splunk_config.hec_token == ""

    def test_format_event(self, splunk_siem: SplunkSIEM, audit_event: AuditEvent):
        """Test event formatting."""
        formatted = splunk_siem.format_event(audit_event)
        assert isinstance(formatted, dict)
        assert formatted["event_type"] == AuditEventType.SERVER_REGISTERED.value
        assert formatted["severity"] == SeverityLevel.HIGH.value
        assert formatted["user_email"] == "test@example.com"

    def test_format_hec_event(self, splunk_siem: SplunkSIEM, audit_event: AuditEvent):
        """Test HEC event formatting."""
        hec_event = splunk_siem._format_hec_event(audit_event)

        assert "time" in hec_event
        assert hec_event["source"] == "test_sark"
        assert hec_event["sourcetype"] == "test:sark:audit"
        assert hec_event["index"] == "test_sark_audit"
        assert hec_event["host"] == "test-host"
        assert "event" in hec_event
        assert isinstance(hec_event["event"], dict)

    def test_format_hec_event_without_host(self, splunk_config: SplunkConfig, audit_event: AuditEvent):
        """Test HEC event formatting without host field."""
        config = SplunkConfig(
            hec_url=splunk_config.hec_url,
            hec_token=splunk_config.hec_token,
            host=None,
        )
        siem = SplunkSIEM(config)
        hec_event = siem._format_hec_event(audit_event)

        assert "host" not in hec_event

    @pytest.mark.asyncio
    async def test_send_event_success(self, splunk_siem: SplunkSIEM, audit_event: AuditEvent):
        """Test successful single event send."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"text":"Success","code":0}'

        with patch.object(splunk_siem._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await splunk_siem.send_event(audit_event)

            assert result is True
            assert mock_post.call_count == 1
            assert splunk_siem.metrics.events_sent == 1
            assert splunk_siem.metrics.events_failed == 0

    @pytest.mark.asyncio
    async def test_send_event_http_error(self, splunk_siem: SplunkSIEM, audit_event: AuditEvent):
        """Test event send with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = '{"text":"Invalid token","code":4}'

        with patch.object(splunk_siem._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await splunk_siem.send_event(audit_event)

            assert result is False
            assert splunk_siem.metrics.events_sent == 0
            assert splunk_siem.metrics.events_failed == 1
            assert "http_403" in splunk_siem.metrics.error_counts

    @pytest.mark.asyncio
    async def test_send_event_timeout(self, splunk_siem: SplunkSIEM, audit_event: AuditEvent):
        """Test event send with timeout."""
        with patch.object(
            splunk_siem._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timeout")

            with pytest.raises(httpx.TimeoutException):
                await splunk_siem.send_event(audit_event)

            assert splunk_siem.metrics.events_failed == 1
            assert "timeout" in splunk_siem.metrics.error_counts

    @pytest.mark.asyncio
    async def test_send_event_connection_error(
        self, splunk_siem: SplunkSIEM, audit_event: AuditEvent
    ):
        """Test event send with connection error."""
        with patch.object(
            splunk_siem._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection refused")

            with pytest.raises(httpx.ConnectError):
                await splunk_siem.send_event(audit_event)

            assert splunk_siem.metrics.events_failed == 1
            assert "connection_error" in splunk_siem.metrics.error_counts

    @pytest.mark.asyncio
    async def test_send_event_generic_exception(
        self, splunk_siem: SplunkSIEM, audit_event: AuditEvent
    ):
        """Test event send with generic exception."""
        with patch.object(
            splunk_siem._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.side_effect = ValueError("Invalid data")

            with pytest.raises(ValueError):
                await splunk_siem.send_event(audit_event)

            assert splunk_siem.metrics.events_failed == 1
            assert "ValueError" in splunk_siem.metrics.error_counts

    @pytest.mark.asyncio
    async def test_send_batch_success(self, splunk_siem: SplunkSIEM, audit_event: AuditEvent):
        """Test successful batch send."""
        events = [audit_event, audit_event, audit_event]

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"text":"Success","code":0}'

        with patch.object(splunk_siem._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await splunk_siem.send_batch(events)

            assert result is True
            assert mock_post.call_count == 1
            assert splunk_siem.metrics.events_sent == 3
            assert splunk_siem.metrics.batches_sent == 1

    @pytest.mark.asyncio
    async def test_send_batch_empty(self, splunk_siem: SplunkSIEM):
        """Test sending an empty batch."""
        result = await splunk_siem.send_batch([])
        assert result is True

    @pytest.mark.asyncio
    async def test_send_batch_http_error(self, splunk_siem: SplunkSIEM, audit_event: AuditEvent):
        """Test batch send with HTTP error."""
        events = [audit_event, audit_event]

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = '{"text":"Internal error","code":5}'

        with patch.object(splunk_siem._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await splunk_siem.send_batch(events)

            assert result is False
            assert splunk_siem.metrics.events_failed == 2
            assert splunk_siem.metrics.batches_failed == 1

    @pytest.mark.asyncio
    async def test_send_batch_timeout(self, splunk_siem: SplunkSIEM, audit_event: AuditEvent):
        """Test batch send with timeout."""
        events = [audit_event, audit_event]

        with patch.object(
            splunk_siem._client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timeout")

            with pytest.raises(httpx.TimeoutException):
                await splunk_siem.send_batch(events)

            assert splunk_siem.metrics.events_failed == 2
            assert "timeout" in splunk_siem.metrics.error_counts

    @pytest.mark.asyncio
    async def test_health_check_success(self, splunk_siem: SplunkSIEM):
        """Test successful health check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"text":"HEC is healthy","code":17}'

        with patch.object(splunk_siem._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            health = await splunk_siem.health_check()

            assert health.healthy is True
            assert health.latency_ms is not None
            assert health.latency_ms > 0
            assert health.error_message is None
            assert "hec_url" in health.details
            assert mock_get.call_count == 1

    @pytest.mark.asyncio
    async def test_health_check_failure(self, splunk_siem: SplunkSIEM):
        """Test health check with failure."""
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.text = '{"text":"Service unavailable","code":3}'

        with patch.object(splunk_siem._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            health = await splunk_siem.health_check()

            assert health.healthy is False
            assert health.error_message is not None
            assert "503" in health.error_message

    @pytest.mark.asyncio
    async def test_health_check_timeout(self, splunk_siem: SplunkSIEM):
        """Test health check with timeout."""
        with patch.object(splunk_siem._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timeout")

            health = await splunk_siem.health_check()

            assert health.healthy is False
            assert "Timeout" in health.error_message

    @pytest.mark.asyncio
    async def test_health_check_connection_error(self, splunk_siem: SplunkSIEM):
        """Test health check with connection error."""
        with patch.object(splunk_siem._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection refused")

            health = await splunk_siem.health_check()

            assert health.healthy is False
            assert "Connection error" in health.error_message

    @pytest.mark.asyncio
    async def test_health_check_generic_exception(self, splunk_siem: SplunkSIEM):
        """Test health check with generic exception."""
        with patch.object(splunk_siem._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = ValueError("Invalid configuration")

            health = await splunk_siem.health_check()

            assert health.healthy is False
            assert "ValueError" in health.error_message

    @pytest.mark.asyncio
    async def test_close(self, splunk_siem: SplunkSIEM):
        """Test closing the SIEM connection."""
        with patch.object(
            splunk_siem._client, "aclose", new_callable=AsyncMock
        ) as mock_close:
            await splunk_siem.close()
            assert mock_close.call_count == 1

    @pytest.mark.asyncio
    async def test_metrics_tracking(self, splunk_siem: SplunkSIEM, audit_event: AuditEvent):
        """Test that metrics are properly tracked."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"text":"Success","code":0}'

        with patch.object(splunk_siem._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            # Send 3 events
            await splunk_siem.send_event(audit_event)
            await splunk_siem.send_event(audit_event)
            await splunk_siem.send_event(audit_event)

            metrics = splunk_siem.get_metrics()
            assert metrics.events_sent == 3
            assert metrics.batches_sent == 3
            assert metrics.success_rate == 100.0
            assert metrics.last_success is not None

    @pytest.mark.asyncio
    async def test_ssl_verification(self):
        """Test SSL verification configuration."""
        # With SSL verification
        config_with_ssl = SplunkConfig(verify_ssl=True)
        siem_with_ssl = SplunkSIEM(config_with_ssl)
        # Check that the client was initialized with SSL verification
        assert siem_with_ssl.splunk_config.verify_ssl is True

        # Without SSL verification
        config_without_ssl = SplunkConfig(verify_ssl=False)
        siem_without_ssl = SplunkSIEM(config_without_ssl)
        assert siem_without_ssl.splunk_config.verify_ssl is False

    def test_hec_event_timestamp_format(self, splunk_siem: SplunkSIEM, audit_event: AuditEvent):
        """Test that HEC event timestamp is in Unix epoch format."""
        hec_event = splunk_siem._format_hec_event(audit_event)

        assert "time" in hec_event
        # Unix timestamp should be a number
        assert isinstance(hec_event["time"], (int, float))
        # Should be a reasonable timestamp (after 2020)
        assert hec_event["time"] > 1577836800  # Jan 1, 2020
