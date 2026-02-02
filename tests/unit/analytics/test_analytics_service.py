"""Unit tests for AnalyticsService."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sark.services.analytics.analytics import AnalyticsService
from sark.services.analytics.usage_reporter import ReportPeriod


class TestAnalyticsService:
    """Tests for AnalyticsService."""

    @pytest.fixture
    def mock_db(self) -> MagicMock:
        """Create mock database session."""
        db = MagicMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def analytics(self, mock_db: MagicMock) -> AnalyticsService:
        """Create analytics service with mock DB."""
        return AnalyticsService(mock_db)

    @pytest.mark.asyncio
    async def test_get_dashboard_stats(
        self, analytics: AnalyticsService, mock_db: MagicMock
    ) -> None:
        """Test get_dashboard_stats returns comprehensive data."""
        # Mock period stats result
        mock_period = MagicMock()
        mock_period.one.return_value = MagicMock(
            requests=50,
            tokens_prompt=5000,
            tokens_response=2500,
            cost_total=0.50,
            unique_devices=3,
        )

        # Mock top endpoints
        mock_endpoints = MagicMock()
        mock_endpoints.fetchall.return_value = [
            ("openai/chat", 30, 3000, 0.30),
            ("anthropic/messages", 20, 2000, 0.20),
        ]

        # Mock top devices
        mock_devices = MagicMock()
        mock_devices.fetchall.return_value = [
            ("192.168.1.100", "Laptop", 30, 3000, 0.30),
        ]

        # Mock recent activity
        mock_event = MagicMock()
        mock_event.id = 1
        mock_event.timestamp = datetime.now(UTC)
        mock_event.device_ip = "192.168.1.100"
        mock_event.device_name = "Laptop"
        mock_event.endpoint = "openai/chat"
        mock_event.provider = "openai"
        mock_event.model = "gpt-4"
        mock_event.tokens_prompt = 100
        mock_event.tokens_response = 50
        mock_event.total_tokens = 150
        mock_event.cost_estimate = 0.01

        mock_recent = MagicMock()
        mock_recent.scalars.return_value = [mock_event]

        # Mock peak hours
        mock_peak_hours = MagicMock()
        mock_peak_hours.fetchall.return_value = [
            ("10", 20, 2000, 100.0),
        ]

        # Set up execute to return different results for different queries
        mock_db.execute = AsyncMock(
            side_effect=[
                mock_period,  # today
                mock_period,  # week
                mock_period,  # month
                mock_devices,  # top devices
                mock_endpoints,  # top endpoints
                mock_peak_hours,  # peak hours
                mock_recent,  # recent activity
            ]
        )

        result = await analytics.get_dashboard_stats()

        assert "today" in result
        assert "week" in result
        assert "month" in result
        assert "top_devices" in result
        assert "top_endpoints" in result
        assert "peak_hours" in result
        assert "recent_activity" in result
        assert "generated_at" in result

    @pytest.mark.asyncio
    async def test_record_usage(
        self, analytics: AnalyticsService, mock_db: MagicMock
    ) -> None:
        """Test record_usage creates event with cost estimate."""
        # Mock the token tracker's record method
        with patch.object(
            analytics.token_tracker,
            "record",
            new_callable=AsyncMock,
        ) as mock_record:
            mock_event = MagicMock()
            mock_event.id = 1
            mock_event.timestamp = datetime.now(UTC)
            mock_event.device_ip = "192.168.1.100"
            mock_event.endpoint = "openai/chat"
            mock_event.provider = "openai"
            mock_event.model = "gpt-4"
            mock_event.tokens_prompt = 100
            mock_event.tokens_response = 50
            mock_event.total_tokens = 150
            mock_event.cost_estimate = 0.01

            mock_record.return_value = mock_event

            result = await analytics.record_usage(
                device_ip="192.168.1.100",
                endpoint="openai/chat",
                provider="openai",
                tokens_prompt=100,
                tokens_response=50,
                model="gpt-4",
            )

            assert result.id == 1
            mock_record.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_usage_trend(
        self, analytics: AnalyticsService, mock_db: MagicMock
    ) -> None:
        """Test get_usage_trend returns trend data."""
        with patch.object(
            analytics.trend_analyzer,
            "analyze_trend",
            new_callable=AsyncMock,
        ) as mock_analyze:
            mock_analyze.return_value = {
                "metric": "tokens",
                "period_days": 30,
                "trend_direction": "up",
                "change_percent": 15.0,
                "data_points": [],
            }

            result = await analytics.get_usage_trend(days=30)

            assert result["metric"] == "tokens"
            assert result["trend_direction"] == "up"
            mock_analyze.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cost_trend(
        self, analytics: AnalyticsService, mock_db: MagicMock
    ) -> None:
        """Test get_cost_trend returns cost trend data."""
        with patch.object(
            analytics.trend_analyzer,
            "analyze_trend",
            new_callable=AsyncMock,
        ) as mock_analyze:
            mock_analyze.return_value = {
                "metric": "cost",
                "period_days": 30,
                "trend_direction": "stable",
                "change_percent": 2.0,
                "data_points": [],
            }

            result = await analytics.get_cost_trend(days=30)

            assert result["metric"] == "cost"
            mock_analyze.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_report(
        self, analytics: AnalyticsService, mock_db: MagicMock
    ) -> None:
        """Test generate_report returns a report."""
        with patch.object(
            analytics.usage_reporter,
            "generate",
            new_callable=AsyncMock,
        ) as mock_generate:
            mock_generate.return_value = {
                "report_id": "abc123",
                "period": "week",
                "summary": {"request_count": 100},
            }

            result = await analytics.generate_report(period=ReportPeriod.WEEK)

            assert result["report_id"] == "abc123"
            mock_generate.assert_called_once_with(
                period=ReportPeriod.WEEK, device_ip=None
            )

    @pytest.mark.asyncio
    async def test_export_report_csv(
        self, analytics: AnalyticsService, mock_db: MagicMock
    ) -> None:
        """Test export_report_csv returns CSV string."""
        with patch.object(
            analytics.usage_reporter,
            "export_csv",
            new_callable=AsyncMock,
        ) as mock_export:
            mock_export.return_value = "date,device_ip,tokens\n2025-01-15,192.168.1.100,1000\n"

            result = await analytics.export_report_csv(period=ReportPeriod.WEEK)

            assert "date" in result
            assert "device_ip" in result
            mock_export.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_old_data(
        self, analytics: AnalyticsService, mock_db: MagicMock
    ) -> None:
        """Test cleanup_old_data removes old records."""
        mock_events_result = MagicMock()
        mock_events_result.rowcount = 50

        mock_aggregates_result = MagicMock()
        mock_aggregates_result.rowcount = 10

        mock_db.execute = AsyncMock(
            side_effect=[mock_events_result, mock_aggregates_result]
        )

        result = await analytics.cleanup_old_data(retention_days=365)

        assert result["events_deleted"] == 50
        assert result["aggregates_deleted"] == 10
        assert "cutoff_date" in result
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_device_summary(
        self, analytics: AnalyticsService, mock_db: MagicMock
    ) -> None:
        """Test get_device_summary returns comprehensive device data."""
        with patch.object(
            analytics.token_tracker,
            "get_device_stats",
            new_callable=AsyncMock,
        ) as mock_stats, patch.object(
            analytics.trend_analyzer,
            "analyze_trend",
            new_callable=AsyncMock,
        ) as mock_trend, patch.object(
            analytics.trend_analyzer,
            "get_peak_hours",
            new_callable=AsyncMock,
        ) as mock_peak, patch.object(
            analytics.token_tracker,
            "get_hourly_distribution",
            new_callable=AsyncMock,
        ) as mock_hourly:
            mock_stats.return_value = {
                "device_ip": "192.168.1.100",
                "request_count": 100,
                "total_tokens": 10000,
            }
            mock_trend.return_value = {
                "trend_direction": "up",
                "change_percent": 10.0,
                "average_daily": 500,
            }
            mock_peak.return_value = {"peak_hours_by_requests": [10, 14]}
            mock_hourly.return_value = [
                {"hour": 10, "request_count": 20},
                {"hour": 14, "request_count": 15},
            ]

            result = await analytics.get_device_summary("192.168.1.100")

            assert result["device_ip"] == "192.168.1.100"
            assert "stats" in result
            assert "trend" in result
            assert "peak_hours" in result
            assert "hourly_distribution" in result


class TestAnalyticsServiceIntegration:
    """Integration-style tests for AnalyticsService components."""

    @pytest.mark.asyncio
    async def test_services_are_initialized(self) -> None:
        """Test that all sub-services are initialized."""
        mock_db = MagicMock()
        analytics = AnalyticsService(mock_db)

        assert analytics.token_tracker is not None
        assert analytics.cost_calculator is not None
        assert analytics.trend_analyzer is not None
        assert analytics.usage_reporter is not None

    @pytest.mark.asyncio
    async def test_period_stats_structure(self) -> None:
        """Test _get_period_stats returns correct structure."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.one.return_value = MagicMock(
            requests=10,
            tokens_prompt=1000,
            tokens_response=500,
            cost_total=0.10,
            unique_devices=2,
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        analytics = AnalyticsService(mock_db)
        result = await analytics._get_period_stats("today")

        assert result["period"] == "today"
        assert "start_date" in result
        assert "end_date" in result
        assert result["requests"] == 10
        assert result["tokens"] == 1500
        assert result["tokens_prompt"] == 1000
        assert result["tokens_response"] == 500
        assert result["cost_estimate"] == 0.10
        assert result["unique_devices"] == 2
