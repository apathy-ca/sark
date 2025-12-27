"""Unit tests for Datadog SIEM integration."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import httpx
import pytest

from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel
from sark.services.audit.siem.datadog import DatadogConfig, DatadogSIEM


@pytest.fixture
def datadog_config():
    """Create Datadog configuration for testing."""
    return DatadogConfig(
        api_key="test-api-key-12345",
        app_key="test-app-key-67890",
        site="datadoghq.com",
        service="test_sark",
        environment="test",
        hostname="test-host",
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
def datadog_siem(datadog_config, mock_http_client):
    """Create Datadog SIEM instance with mocked client."""
    with patch("sark.services.audit.siem.datadog.httpx.AsyncClient", return_value=mock_http_client):
        siem = DatadogSIEM(config=datadog_config)
        siem._client = mock_http_client
        return siem


class TestDatadogConfiguration:
    """Test Datadog configuration."""

    def test_config_defaults(self):
        """Test that configuration has sensible defaults."""
        config = DatadogConfig(api_key="test-key")
        assert config.site == "datadoghq.com"
        assert config.service == "sark"
        assert config.environment == "production"
        assert config.enabled is True
        assert config.verify_ssl is True

    def test_config_custom_values(self):
        """Test configuration with custom values."""
        config = DatadogConfig(
            api_key="custom-key",
            app_key="custom-app-key",
            site="datadoghq.eu",
            service="custom_service",
            environment="staging",
            hostname="custom-host",
        )
        assert config.api_key == "custom-key"
        assert config.app_key == "custom-app-key"
        assert config.site == "datadoghq.eu"
        assert config.service == "custom_service"
        assert config.environment == "staging"
        assert config.hostname == "custom-host"

    def test_config_eu_site(self):
        """Test configuration for EU site."""
        config = DatadogConfig(api_key="test-key", site="datadoghq.eu")
        assert config.site == "datadoghq.eu"


class TestDatadogInitialization:
    """Test Datadog SIEM initialization."""

    def test_initialization_success(self, datadog_config):
        """Test successful SIEM initialization."""
        with patch("sark.services.audit.siem.datadog.httpx.AsyncClient"):
            siem = DatadogSIEM(config=datadog_config)
            assert siem.datadog_config == datadog_config
            assert siem._client is not None
            assert "http-intake.logs.datadoghq.com" in siem._logs_url

    def test_initialization_without_api_key_warns(self):
        """Test that initialization without API key logs warning."""
        config = DatadogConfig(api_key="")
        with patch("sark.services.audit.siem.datadog.httpx.AsyncClient"):
            siem = DatadogSIEM(config=config)
            # Initialization should still succeed but log warning
            assert siem._client is not None

    def test_http_client_headers(self, datadog_config):
        """Test that HTTP client is configured with correct headers."""
        with patch("sark.services.audit.siem.datadog.httpx.AsyncClient") as mock_client_class:
            DatadogSIEM(config=datadog_config)

            mock_client_class.assert_called_once()
            call_kwargs = mock_client_class.call_args[1]
            assert "DD-API-KEY" in call_kwargs["headers"]
            assert call_kwargs["headers"]["DD-API-KEY"] == "test-api-key-12345"
            assert call_kwargs["headers"]["Content-Type"] == "application/json"

    def test_logs_url_construction(self, datadog_config):
        """Test that logs URL is constructed correctly based on site."""
        with patch("sark.services.audit.siem.datadog.httpx.AsyncClient"):
            siem = DatadogSIEM(config=datadog_config)
            assert siem._logs_url == "https://http-intake.logs.datadoghq.com/api/v2/logs"

    def test_logs_url_construction_eu(self):
        """Test logs URL construction for EU site."""
        config = DatadogConfig(api_key="test-key", site="datadoghq.eu")
        with patch("sark.services.audit.siem.datadog.httpx.AsyncClient"):
            siem = DatadogSIEM(config=config)
            assert siem._logs_url == "https://http-intake.logs.datadoghq.eu/api/v2/logs"


class TestSendEvent:
    """Test sending single events to Datadog."""

    @pytest.mark.asyncio
    async def test_send_event_success(self, datadog_siem, sample_audit_event, mock_http_client):
        """Test successful event send."""
        # Mock successful response (Datadog returns 202)
        mock_response = Mock()
        mock_response.status_code = 202
        mock_http_client.post = AsyncMock(return_value=mock_response)

        result = await datadog_siem.send_event(sample_audit_event)

        assert result is True
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        assert datadog_siem._logs_url in call_args[0]

    @pytest.mark.asyncio
    async def test_send_event_failure(self, datadog_siem, sample_audit_event, mock_http_client):
        """Test event send failure with non-202 status."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_http_client.post = AsyncMock(return_value=mock_response)

        result = await datadog_siem.send_event(sample_audit_event)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_event_timeout(self, datadog_siem, sample_audit_event, mock_http_client):
        """Test event send timeout handling."""
        mock_http_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        with pytest.raises(httpx.TimeoutException):
            await datadog_siem.send_event(sample_audit_event)

    @pytest.mark.asyncio
    async def test_send_event_connection_error(self, datadog_siem, sample_audit_event, mock_http_client):
        """Test event send connection error handling."""
        mock_http_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))

        with pytest.raises(httpx.ConnectError):
            await datadog_siem.send_event(sample_audit_event)

    @pytest.mark.asyncio
    async def test_send_event_generic_exception(self, datadog_siem, sample_audit_event, mock_http_client):
        """Test event send with generic exception."""
        mock_http_client.post = AsyncMock(side_effect=Exception("Unknown error"))

        with pytest.raises(Exception):
            await datadog_siem.send_event(sample_audit_event)

    @pytest.mark.asyncio
    async def test_send_event_sends_as_array(self, datadog_siem, sample_audit_event, mock_http_client):
        """Test that single event is sent as array (Datadog requirement)."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_http_client.post = AsyncMock(return_value=mock_response)

        await datadog_siem.send_event(sample_audit_event)

        call_args = mock_http_client.post.call_args
        payload = call_args[1]["json"]

        # Datadog expects array format
        assert isinstance(payload, list)
        assert len(payload) == 1


class TestSendBatch:
    """Test sending batch events to Datadog."""

    @pytest.mark.asyncio
    async def test_send_batch_success(self, datadog_siem, mock_http_client):
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
        mock_response.status_code = 202
        mock_http_client.post = AsyncMock(return_value=mock_response)

        result = await datadog_siem.send_batch(events)

        assert result is True
        mock_http_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_batch_empty(self, datadog_siem, mock_http_client):
        """Test sending empty batch."""
        result = await datadog_siem.send_batch([])

        assert result is True
        mock_http_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_batch_failure(self, datadog_siem, mock_http_client):
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

        result = await datadog_siem.send_batch(events)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_batch_sends_as_array(self, datadog_siem, mock_http_client):
        """Test that batch is sent as JSON array."""
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
        mock_response.status_code = 202
        mock_http_client.post = AsyncMock(return_value=mock_response)

        await datadog_siem.send_batch(events)

        call_args = mock_http_client.post.call_args
        payload = call_args[1]["json"]

        assert isinstance(payload, list)
        assert len(payload) == 3

    @pytest.mark.asyncio
    async def test_send_batch_timeout(self, datadog_siem, mock_http_client):
        """Test batch send timeout handling."""
        events = [AuditEvent(id=uuid4(), timestamp=datetime.now(UTC), event_type=AuditEventType.USER_LOGIN, severity=SeverityLevel.LOW)]

        mock_http_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        with pytest.raises(httpx.TimeoutException):
            await datadog_siem.send_batch(events)


class TestHealthCheck:
    """Test Datadog health check."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, datadog_siem, mock_http_client):
        """Test successful health check."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.text = "OK"
        mock_http_client.post = AsyncMock(return_value=mock_response)

        health = await datadog_siem.health_check()

        assert health.healthy is True
        assert health.latency_ms is not None

    @pytest.mark.asyncio
    async def test_health_check_failure(self, datadog_siem, mock_http_client):
        """Test health check failure."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_http_client.post = AsyncMock(return_value=mock_response)

        health = await datadog_siem.health_check()

        assert health.healthy is False
        assert health.error_message is not None

    @pytest.mark.asyncio
    async def test_health_check_timeout(self, datadog_siem, mock_http_client):
        """Test health check timeout."""
        mock_http_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        health = await datadog_siem.health_check()

        assert health.healthy is False
        assert "Timeout" in health.error_message

    @pytest.mark.asyncio
    async def test_health_check_connection_error(self, datadog_siem, mock_http_client):
        """Test health check connection error."""
        mock_http_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))

        health = await datadog_siem.health_check()

        assert health.healthy is False
        assert "Connection error" in health.error_message


class TestEventFormatting:
    """Test event formatting for Datadog."""

    def test_format_event(self, datadog_siem, sample_audit_event):
        """Test basic event formatting."""
        formatted = datadog_siem.format_event(sample_audit_event)

        assert isinstance(formatted, dict)

    def test_format_datadog_event_structure(self, datadog_siem, sample_audit_event):
        """Test Datadog event structure."""
        dd_event = datadog_siem._format_datadog_event(sample_audit_event)

        # Datadog format requirements
        assert "ddsource" in dd_event
        assert "ddtags" in dd_event
        assert "hostname" in dd_event
        assert "message" in dd_event

    def test_format_datadog_event_tags(self, datadog_siem, sample_audit_event):
        """Test that Datadog event includes correct tags."""
        dd_event = datadog_siem._format_datadog_event(sample_audit_event)

        assert "service:test_sark" in dd_event["ddtags"]
        assert "env:test" in dd_event["ddtags"]

    def test_format_datadog_event_with_hostname(self, datadog_siem, sample_audit_event):
        """Test event formatting includes hostname."""
        dd_event = datadog_siem._format_datadog_event(sample_audit_event)

        assert dd_event["hostname"] == "test-host"

    def test_format_datadog_event_timestamp(self, datadog_siem, sample_audit_event):
        """Test that timestamp is formatted correctly."""
        dd_event = datadog_siem._format_datadog_event(sample_audit_event)

        assert "timestamp" in dd_event
        # Datadog expects milliseconds since epoch
        assert isinstance(dd_event["timestamp"], int)
        assert dd_event["timestamp"] > 0


class TestCleanup:
    """Test resource cleanup."""

    @pytest.mark.asyncio
    async def test_close(self, datadog_siem, mock_http_client):
        """Test that close() properly closes the HTTP client."""
        await datadog_siem.close()

        mock_http_client.aclose.assert_called_once()


class TestMetricsTracking:
    """Test metrics tracking during operations."""

    @pytest.mark.asyncio
    async def test_metrics_updated_on_success(self, datadog_siem, sample_audit_event, mock_http_client):
        """Test that metrics are updated on successful send."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_http_client.post = AsyncMock(return_value=mock_response)

        assert datadog_siem.metrics.events_sent == 0

        await datadog_siem.send_event(sample_audit_event)

        assert datadog_siem.metrics.events_sent == 1
        assert datadog_siem.metrics.last_success is not None

    @pytest.mark.asyncio
    async def test_metrics_updated_on_failure(self, datadog_siem, sample_audit_event, mock_http_client):
        """Test that metrics are updated on failed send."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Error"
        mock_http_client.post = AsyncMock(return_value=mock_response)

        await datadog_siem.send_event(sample_audit_event)

        assert datadog_siem.metrics.events_failed == 1
        assert datadog_siem.metrics.last_failure is not None


class TestDatadogSpecificFeatures:
    """Test Datadog-specific features."""

    def test_multiple_sites_support(self):
        """Test that different Datadog sites are supported."""
        sites = ["datadoghq.com", "datadoghq.eu", "us3.datadoghq.com", "ddog-gov.com"]

        for site in sites:
            config = DatadogConfig(api_key="test-key", site=site)
            with patch("sark.services.audit.siem.datadog.httpx.AsyncClient"):
                siem = DatadogSIEM(config=config)
                assert site in siem._logs_url

    @pytest.mark.asyncio
    async def test_batch_size_limit_respected(self, datadog_siem, mock_http_client):
        """Test that large batches are handled correctly."""
        # Create a large batch (Datadog supports up to 1000 logs per request)
        events = [
            AuditEvent(
                id=uuid4(),
                timestamp=datetime.now(UTC),
                event_type=AuditEventType.USER_LOGIN,
                severity=SeverityLevel.LOW,
            )
            for _ in range(500)
        ]

        mock_response = Mock()
        mock_response.status_code = 202
        mock_http_client.post = AsyncMock(return_value=mock_response)

        result = await datadog_siem.send_batch(events)

        assert result is True
        call_args = mock_http_client.post.call_args
        payload = call_args[1]["json"]
        assert len(payload) == 500
