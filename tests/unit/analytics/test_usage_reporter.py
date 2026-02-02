"""Unit tests for UsageReporterService."""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from sark.services.analytics.usage_reporter import (
    ReportFormat,
    ReportPeriod,
    UsageReporterService,
)


class TestReportPeriod:
    """Tests for ReportPeriod enum."""

    def test_report_period_values(self) -> None:
        """Test ReportPeriod enum values."""
        assert ReportPeriod.DAY.value == "day"
        assert ReportPeriod.WEEK.value == "week"
        assert ReportPeriod.MONTH.value == "month"
        assert ReportPeriod.CUSTOM.value == "custom"


class TestReportFormat:
    """Tests for ReportFormat enum."""

    def test_report_format_values(self) -> None:
        """Test ReportFormat enum values."""
        assert ReportFormat.SUMMARY.value == "summary"
        assert ReportFormat.DETAILED.value == "detailed"
        assert ReportFormat.JSON.value == "json"
        assert ReportFormat.CSV.value == "csv"


class TestUsageReporterService:
    """Tests for UsageReporterService."""

    @pytest.fixture
    def mock_db(self) -> MagicMock:
        """Create mock database session."""
        db = MagicMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def reporter(self, mock_db: MagicMock) -> UsageReporterService:
        """Create usage reporter with mock DB."""
        return UsageReporterService(mock_db)

    def test_get_period_dates_day(self, reporter: UsageReporterService) -> None:
        """Test _get_period_dates for day period."""
        ref = date(2025, 1, 15)
        start, end = reporter._get_period_dates(ReportPeriod.DAY, ref)

        assert start.date() == ref
        assert end.date() == ref

    def test_get_period_dates_week(self, reporter: UsageReporterService) -> None:
        """Test _get_period_dates for week period."""
        # Wednesday, January 15, 2025
        ref = date(2025, 1, 15)
        start, end = reporter._get_period_dates(ReportPeriod.WEEK, ref)

        # Week should start on Monday (Jan 13) and end on Sunday (Jan 19)
        assert start.date() == date(2025, 1, 13)
        assert end.date() == date(2025, 1, 19)

    def test_get_period_dates_month(self, reporter: UsageReporterService) -> None:
        """Test _get_period_dates for month period."""
        ref = date(2025, 1, 15)
        start, end = reporter._get_period_dates(ReportPeriod.MONTH, ref)

        assert start.date() == date(2025, 1, 1)
        assert end.date() == date(2025, 1, 31)

    @pytest.mark.asyncio
    async def test_generate_report(
        self, reporter: UsageReporterService, mock_db: MagicMock
    ) -> None:
        """Test generate returns a complete report."""
        # Mock summary result
        mock_summary = MagicMock()
        mock_summary.one.return_value = MagicMock(
            request_count=100,
            tokens_prompt=10000,
            tokens_response=5000,
            cost_total=1.50,
            unique_devices=5,
        )

        # Mock by_device result
        mock_by_device = MagicMock()
        mock_by_device.fetchall.return_value = [
            ("192.168.1.100", "Laptop", 50, 5000, 2500, 0.75),
            ("192.168.1.101", "Desktop", 50, 5000, 2500, 0.75),
        ]

        # Mock by_endpoint result
        mock_by_endpoint = MagicMock()
        mock_by_endpoint.fetchall.return_value = [
            ("openai/chat", 80, 8000, 4000, 1.20),
            ("anthropic/messages", 20, 2000, 1000, 0.30),
        ]

        # Mock by_provider result
        mock_by_provider = MagicMock()
        mock_by_provider.fetchall.return_value = [
            ("openai", "gpt-4", 80, 8000, 4000, 1.20),
            ("anthropic", "claude-3-sonnet", 20, 2000, 1000, 0.30),
        ]

        # Mock daily result
        mock_daily = MagicMock()
        mock_daily.fetchall.return_value = [
            (date(2025, 1, 15), 50, 5000, 2500, 0.75),
            (date(2025, 1, 16), 50, 5000, 2500, 0.75),
        ]

        mock_db.execute = AsyncMock(
            side_effect=[
                mock_summary,
                mock_by_device,
                mock_by_endpoint,
                mock_by_provider,
                mock_daily,
            ]
        )

        result = await reporter.generate(period=ReportPeriod.WEEK)

        assert "report_id" in result
        assert "generated_at" in result
        assert result["period"] == "week"
        assert result["summary"]["request_count"] == 100
        assert result["summary"]["total_tokens"] == 15000
        assert len(result["by_device"]) == 2
        assert len(result["by_endpoint"]) == 2
        assert len(result["by_provider"]) == 2
        assert len(result["daily_breakdown"]) == 2

    @pytest.mark.asyncio
    async def test_generate_report_empty(
        self, reporter: UsageReporterService, mock_db: MagicMock
    ) -> None:
        """Test generate returns empty report when no data."""
        mock_summary = MagicMock()
        mock_summary.one.return_value = MagicMock(
            request_count=0,
            tokens_prompt=None,
            tokens_response=None,
            cost_total=None,
            unique_devices=0,
        )

        mock_empty = MagicMock()
        mock_empty.fetchall.return_value = []

        mock_db.execute = AsyncMock(
            side_effect=[mock_summary, mock_empty, mock_empty, mock_empty, mock_empty]
        )

        result = await reporter.generate(period=ReportPeriod.DAY)

        assert result["summary"]["request_count"] == 0
        assert result["summary"]["total_tokens"] == 0

    @pytest.mark.asyncio
    async def test_export_csv_aggregates(
        self, reporter: UsageReporterService, mock_db: MagicMock
    ) -> None:
        """Test export_csv returns CSV string with aggregates."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (date(2025, 1, 15), "192.168.1.100", "openai/chat", "openai", 50, 5000, 2500, 0.75),
        ]

        mock_db.execute = AsyncMock(return_value=mock_result)

        csv_content = await reporter.export_csv(period=ReportPeriod.DAY)

        assert "date" in csv_content
        assert "device_ip" in csv_content
        assert "192.168.1.100" in csv_content

    @pytest.mark.asyncio
    async def test_export_csv_detailed(
        self, reporter: UsageReporterService, mock_db: MagicMock
    ) -> None:
        """Test export_csv with detailed events."""
        # Mock event
        mock_event = MagicMock()
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
        mock_event.request_id = "req-123"

        mock_result = MagicMock()
        mock_result.scalars.return_value = [mock_event]

        mock_db.execute = AsyncMock(return_value=mock_result)

        csv_content = await reporter.export_csv(
            period=ReportPeriod.DAY, include_details=True
        )

        assert "timestamp" in csv_content
        assert "192.168.1.100" in csv_content
        assert "gpt-4" in csv_content

    @pytest.mark.asyncio
    async def test_export_json(
        self, reporter: UsageReporterService, mock_db: MagicMock
    ) -> None:
        """Test export_json returns JSON string."""
        # Setup mocks for generate
        mock_summary = MagicMock()
        mock_summary.one.return_value = MagicMock(
            request_count=10,
            tokens_prompt=1000,
            tokens_response=500,
            cost_total=0.15,
            unique_devices=1,
        )

        mock_empty = MagicMock()
        mock_empty.fetchall.return_value = []

        mock_db.execute = AsyncMock(
            side_effect=[mock_summary, mock_empty, mock_empty, mock_empty, mock_empty]
        )

        json_content = await reporter.export_json(period=ReportPeriod.DAY)

        assert '"report_id"' in json_content
        assert '"summary"' in json_content
        import json

        parsed = json.loads(json_content)
        assert parsed["summary"]["request_count"] == 10

    @pytest.mark.asyncio
    async def test_get_quick_summary(
        self, reporter: UsageReporterService, mock_db: MagicMock
    ) -> None:
        """Test get_quick_summary returns period summaries."""
        mock_result = MagicMock()
        mock_result.one.return_value = MagicMock(
            requests=50, tokens=5000, cost=0.50
        )

        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await reporter.get_quick_summary()

        assert "today" in result
        assert "week" in result
        assert "month" in result
        assert result["today"]["requests"] == 50
        assert result["today"]["tokens"] == 5000
