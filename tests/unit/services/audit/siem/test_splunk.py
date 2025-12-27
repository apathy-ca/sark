"""Unit tests for Splunk SIEM integration."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import httpx
import pytest

from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel
from sark.services.audit.siem.splunk import SplunkConfig, SplunkSIEM


@pytest.fixture
def splunk_config():
    """Create Splunk configuration for testing."""
    return SplunkConfig(
        hec_url="https://splunk.example.com:8088/services/collector",
        hec_token="test-token-12345",
        index="test_audit",
        sourcetype="test:audit:event",
        source="test_sark",
        host="test-host",
        verify_ssl=False,
        timeout_seconds=10,
    )


@pytest.fixture
def sample_audit_event():
    """Create sample audit event for testing."""
    return AuditEvent(
        id=uuid4(),
        timestamp=datetime.now(UTC),
        event_type=AuditEventType.USER_LOGIN,
        severity=SeverityLevel.LOW,
        user_id=uuid4(),
        user_email="test@example.com",
        details={"action": "login", "success": True},
    )


@pytest.fixture
def mock_http_client():
    """Create mock HTTP client."""
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def splunk_siem(splunk_config, mock_http_client):
    """Create Splunk SIEM instance with mocked client."""
    with patch("sark.services.audit.siem.splunk.httpx.AsyncClient", return_value=mock_http_client):
        siem = SplunkSIEM(config=splunk_config)
        siem._client = mock_http_client
        return siem


class TestSplunkConfiguration:
    """Test Splunk configuration."""

    def test_config_defaults(self):
        """Test that configuration has sensible defaults."""
        config = SplunkConfig(hec_token="test-token")
        assert config.hec_url == "https://localhost:8088/services/collector"
        assert config.index == "sark_audit"
        assert config.sourcetype == "sark:audit:event"
        assert config.source == "sark"
        assert config.enabled is True
        assert config.verify_ssl is True

    def test_config_custom_values(self):
        """Test configuration with custom values."""
        config = SplunkConfig(
            hec_url="https://custom.splunk.com/collector",
            hec_token="custom-token",
            index="custom_index",
            sourcetype="custom:type",
            source="custom_source",
            host="custom-host",
        )
        assert config.hec_url == "https://custom.splunk.com/collector"
        assert config.hec_token == "custom-token"
        assert config.index == "custom_index"
        assert config.host == "custom-host"


class TestSplunkInitialization:
    """Test Splunk SIEM initialization."""

    def test_initialization_success(self, splunk_config):
        """Test successful SIEM initialization."""
        with patch("sark.services.audit.siem.splunk.httpx.AsyncClient"):
            siem = SplunkSIEM(config=splunk_config)
            assert siem.splunk_config == splunk_config
            assert siem._client is not None

    def test_initialization_without_token_warns(self):
        """Test that initialization without token logs warning."""
        config = SplunkConfig(hec_token="")
        with patch("sark.services.audit.siem.splunk.httpx.AsyncClient"):
            siem = SplunkSIEM(config=config)
            # Initialization should still succeed but log warning
            assert siem._client is not None

    def test_http_client_headers(self, splunk_config):
        """Test that HTTP client is configured with correct headers."""
        with patch("sark.services.audit.siem.splunk.httpx.AsyncClient") as mock_client_class:
            SplunkSIEM(config=splunk_config)

            mock_client_class.assert_called_once()
            call_kwargs = mock_client_class.call_args[1]
            assert "Authorization" in call_kwargs["headers"]
            assert call_kwargs["headers"]["Authorization"] == "Splunk test-token-12345"
            assert call_kwargs["headers"]["Content-Type"] == "application/json"


class TestSendEvent:
    """Test sending single events to Splunk."""

    @pytest.mark.asyncio
    async def test_send_event_success(self, splunk_siem, sample_audit_event, mock_http_client):
        """Test successful event send."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_http_client.post = AsyncMock(return_value=mock_response)

        result = await splunk_siem.send_event(sample_audit_event)

        assert result is True
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        assert splunk_siem.splunk_config.hec_url in call_args[0]

    @pytest.mark.asyncio
    async def test_send_event_failure(self, splunk_siem, sample_audit_event, mock_http_client):
        """Test event send failure with non-200 status."""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_http_client.post = AsyncMock(return_value=mock_response)

        result = await splunk_siem.send_event(sample_audit_event)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_event_timeout(self, splunk_siem, sample_audit_event, mock_http_client):
        """Test event send timeout handling."""
        mock_http_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        with pytest.raises(httpx.TimeoutException):
            await splunk_siem.send_event(sample_audit_event)

    @pytest.mark.asyncio
    async def test_send_event_connection_error(self, splunk_siem, sample_audit_event, mock_http_client):
        """Test event send connection error handling."""
        mock_http_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))

        with pytest.raises(httpx.ConnectError):
            await splunk_siem.send_event(sample_audit_event)

    @pytest.mark.asyncio
    async def test_send_event_generic_exception(self, splunk_siem, sample_audit_event, mock_http_client):
        """Test event send with generic exception."""
        mock_http_client.post = AsyncMock(side_effect=Exception("Unknown error"))

        with pytest.raises(Exception):
            await splunk_siem.send_event(sample_audit_event)

    @pytest.mark.asyncio
    async def test_send_event_formats_correctly(self, splunk_siem, sample_audit_event, mock_http_client):
        """Test that event is formatted correctly for HEC."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_http_client.post = AsyncMock(return_value=mock_response)

        await splunk_siem.send_event(sample_audit_event)

        # Check the event payload sent to Splunk
        call_args = mock_http_client.post.call_args
        payload = call_args[1]["json"]

        assert "time" in payload
        assert "source" in payload
        assert "sourcetype" in payload
        assert "index" in payload
        assert "event" in payload
        assert payload["source"] == "test_sark"
        assert payload["sourcetype"] == "test:audit:event"
        assert payload["index"] == "test_audit"
        assert payload["host"] == "test-host"


class TestSendBatch:
    """Test sending batch events to Splunk."""

    @pytest.mark.asyncio
    async def test_send_batch_success(self, splunk_siem, mock_http_client):
        """Test successful batch send."""
        events = [
            AuditEvent(
                id=uuid4(),
                timestamp=datetime.now(UTC),
                event_type=AuditEventType.USER_LOGIN,
                severity=SeverityLevel.LOW,
            )
            for _ in range(5)
        ]

        mock_response = Mock()
        mock_response.status_code = 200
        mock_http_client.post = AsyncMock(return_value=mock_response)

        result = await splunk_siem.send_batch(events)

        assert result is True
        mock_http_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_batch_empty(self, splunk_siem, mock_http_client):
        """Test sending empty batch."""
        result = await splunk_siem.send_batch([])

        assert result is True
        mock_http_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_batch_failure(self, splunk_siem, mock_http_client):
        """Test batch send failure."""
        events = [
            AuditEvent(
                id=uuid4(),
                timestamp=datetime.now(UTC),
                event_type=AuditEventType.USER_LOGIN,
                severity=SeverityLevel.LOW,
            )
            for _ in range(3)
        ]

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_http_client.post = AsyncMock(return_value=mock_response)

        result = await splunk_siem.send_batch(events)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_batch_formats_newline_delimited(self, splunk_siem, mock_http_client):
        """Test that batch is formatted as newline-delimited JSON."""
        events = [
            AuditEvent(
                id=uuid4(),
                timestamp=datetime.now(UTC),
                event_type=AuditEventType.USER_LOGIN,
                severity=SeverityLevel.LOW,
            )
            for _ in range(3)
        ]

        mock_response = Mock()
        mock_response.status_code = 200
        mock_http_client.post = AsyncMock(return_value=mock_response)

        await splunk_siem.send_batch(events)

        call_args = mock_http_client.post.call_args
        payload = call_args[1]["content"]

        # Batch should be newline-delimited JSON
        assert isinstance(payload, str)
        lines = payload.split("\n")
        assert len(lines) == 3

    @pytest.mark.asyncio
    async def test_send_batch_timeout(self, splunk_siem, mock_http_client):
        """Test batch send timeout handling."""
        events = [AuditEvent(id=uuid4(), timestamp=datetime.now(UTC), event_type=AuditEventType.USER_LOGIN, severity=SeverityLevel.LOW)]

        mock_http_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        with pytest.raises(httpx.TimeoutException):
            await splunk_siem.send_batch(events)


class TestHealthCheck:
    """Test Splunk health check."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, splunk_siem, mock_http_client):
        """Test successful health check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "HEC is healthy"
        mock_http_client.get = AsyncMock(return_value=mock_response)

        health = await splunk_siem.health_check()

        assert health.healthy is True
        assert health.latency_ms is not None
        assert "hec_url" in health.details

    @pytest.mark.asyncio
    async def test_health_check_failure(self, splunk_siem, mock_http_client):
        """Test health check failure."""
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"
        mock_http_client.get = AsyncMock(return_value=mock_response)

        health = await splunk_siem.health_check()

        assert health.healthy is False
        assert health.error_message is not None
        assert "503" in health.error_message

    @pytest.mark.asyncio
    async def test_health_check_timeout(self, splunk_siem, mock_http_client):
        """Test health check timeout."""
        mock_http_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        health = await splunk_siem.health_check()

        assert health.healthy is False
        assert "Timeout" in health.error_message

    @pytest.mark.asyncio
    async def test_health_check_connection_error(self, splunk_siem, mock_http_client):
        """Test health check connection error."""
        mock_http_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))

        health = await splunk_siem.health_check()

        assert health.healthy is False
        assert "Connection error" in health.error_message

    @pytest.mark.asyncio
    async def test_health_check_uses_health_endpoint(self, splunk_siem, mock_http_client):
        """Test that health check uses the HEC health endpoint."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_http_client.get = AsyncMock(return_value=mock_response)

        await splunk_siem.health_check()

        call_args = mock_http_client.get.call_args
        url = call_args[0][0]
        assert "/services/collector/health" in url


class TestEventFormatting:
    """Test event formatting for Splunk HEC."""

    def test_format_event(self, splunk_siem, sample_audit_event):
        """Test basic event formatting."""
        formatted = splunk_siem.format_event(sample_audit_event)

        assert isinstance(formatted, dict)
        assert "event_type" in formatted or "type" in str(formatted)

    def test_format_hec_event_structure(self, splunk_siem, sample_audit_event):
        """Test HEC event structure."""
        hec_event = splunk_siem._format_hec_event(sample_audit_event)

        # HEC format requirements
        assert "time" in hec_event
        assert "source" in hec_event
        assert "sourcetype" in hec_event
        assert "index" in hec_event
        assert "event" in hec_event
        assert "host" in hec_event  # Config has host set

    def test_format_hec_event_without_host(self, splunk_config, sample_audit_event):
        """Test HEC event formatting without host configured."""
        config = SplunkConfig(
            hec_token="test-token",
            host=None,  # No host
        )

        with patch("sark.services.audit.siem.splunk.httpx.AsyncClient"):
            siem = SplunkSIEM(config=config)
            hec_event = siem._format_hec_event(sample_audit_event)

            assert "host" not in hec_event

    def test_format_hec_event_timestamp(self, splunk_siem, sample_audit_event):
        """Test that timestamp is converted to Unix timestamp."""
        hec_event = splunk_siem._format_hec_event(sample_audit_event)

        assert isinstance(hec_event["time"], float)
        assert hec_event["time"] > 0


class TestCleanup:
    """Test resource cleanup."""

    @pytest.mark.asyncio
    async def test_close(self, splunk_siem, mock_http_client):
        """Test that close() properly closes the HTTP client."""
        await splunk_siem.close()

        mock_http_client.aclose.assert_called_once()


class TestMetricsTracking:
    """Test metrics tracking during operations."""

    @pytest.mark.asyncio
    async def test_metrics_updated_on_success(self, splunk_siem, sample_audit_event, mock_http_client):
        """Test that metrics are updated on successful send."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_http_client.post = AsyncMock(return_value=mock_response)

        # Initial metrics should be zero
        assert splunk_siem.metrics.events_sent == 0

        await splunk_siem.send_event(sample_audit_event)

        # Metrics should be updated
        assert splunk_siem.metrics.events_sent == 1
        assert splunk_siem.metrics.last_success is not None

    @pytest.mark.asyncio
    async def test_metrics_updated_on_failure(self, splunk_siem, sample_audit_event, mock_http_client):
        """Test that metrics are updated on failed send."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Error"
        mock_http_client.post = AsyncMock(return_value=mock_response)

        await splunk_siem.send_event(sample_audit_event)

        assert splunk_siem.metrics.events_failed == 1
        assert splunk_siem.metrics.last_failure is not None
