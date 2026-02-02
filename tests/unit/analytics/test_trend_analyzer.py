"""Unit tests for TrendAnalyzerService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from sark.services.analytics.trend_analyzer import (
    TrendAnalyzerService,
    TrendDirection,
    TrendMetric,
)


class TestTrendDirection:
    """Tests for TrendDirection enum."""

    def test_trend_direction_values(self) -> None:
        """Test TrendDirection enum values."""
        assert TrendDirection.UP.value == "up"
        assert TrendDirection.DOWN.value == "down"
        assert TrendDirection.STABLE.value == "stable"


class TestTrendMetric:
    """Tests for TrendMetric enum."""

    def test_trend_metric_values(self) -> None:
        """Test TrendMetric enum values."""
        assert TrendMetric.REQUESTS.value == "requests"
        assert TrendMetric.TOKENS.value == "tokens"
        assert TrendMetric.COST.value == "cost"
        assert TrendMetric.DEVICES.value == "devices"


class TestTrendAnalyzerService:
    """Tests for TrendAnalyzerService."""

    @pytest.fixture
    def mock_db(self) -> MagicMock:
        """Create mock database session."""
        db = MagicMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def analyzer(self, mock_db: MagicMock) -> TrendAnalyzerService:
        """Create trend analyzer with mock DB."""
        return TrendAnalyzerService(mock_db)

    @pytest.mark.asyncio
    async def test_analyze_trend_with_data(
        self, analyzer: TrendAnalyzerService, mock_db: MagicMock
    ) -> None:
        """Test analyze_trend with actual data."""
        # Mock daily data (increasing trend)
        today = datetime.now(UTC).date()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (today - timedelta(days=6), 100),
            (today - timedelta(days=5), 110),
            (today - timedelta(days=4), 120),
            (today - timedelta(days=3), 130),
            (today - timedelta(days=2), 140),
            (today - timedelta(days=1), 150),
            (today, 160),
        ]

        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await analyzer.analyze_trend(metric=TrendMetric.TOKENS, days=7)

        assert result["metric"] == "tokens"
        assert result["period_days"] == 7
        assert len(result["data_points"]) == 7
        assert result["trend_direction"] == TrendDirection.UP.value
        assert result["change_percent"] > 0
        assert result["peak_value"] == 160

    @pytest.mark.asyncio
    async def test_analyze_trend_empty_data(
        self, analyzer: TrendAnalyzerService, mock_db: MagicMock
    ) -> None:
        """Test analyze_trend with no data."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await analyzer.analyze_trend(metric=TrendMetric.TOKENS, days=7)

        assert result["data_points"] == []
        assert result["trend_direction"] == TrendDirection.STABLE.value
        assert result["change_percent"] == 0.0

    @pytest.mark.asyncio
    async def test_analyze_trend_decreasing(
        self, analyzer: TrendAnalyzerService, mock_db: MagicMock
    ) -> None:
        """Test analyze_trend with decreasing values."""
        today = datetime.now(UTC).date()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (today - timedelta(days=3), 200),
            (today - timedelta(days=2), 150),
            (today - timedelta(days=1), 100),
            (today, 50),
        ]

        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await analyzer.analyze_trend(metric=TrendMetric.TOKENS, days=4)

        assert result["trend_direction"] == TrendDirection.DOWN.value
        assert result["change_percent"] < 0

    @pytest.mark.asyncio
    async def test_analyze_trend_stable(
        self, analyzer: TrendAnalyzerService, mock_db: MagicMock
    ) -> None:
        """Test analyze_trend with stable values."""
        today = datetime.now(UTC).date()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (today - timedelta(days=3), 100),
            (today - timedelta(days=2), 102),
            (today - timedelta(days=1), 98),
            (today, 100),
        ]

        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await analyzer.analyze_trend(metric=TrendMetric.TOKENS, days=4)

        assert result["trend_direction"] == TrendDirection.STABLE.value
        assert abs(result["change_percent"]) <= 10

    @pytest.mark.asyncio
    async def test_get_peak_hours(
        self, analyzer: TrendAnalyzerService, mock_db: MagicMock
    ) -> None:
        """Test get_peak_hours returns hourly breakdown."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("09", 10, 1000, 100.0),
            ("10", 25, 2500, 100.0),  # Peak
            ("14", 15, 1500, 100.0),
            ("15", 20, 2000, 100.0),
        ]

        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await analyzer.get_peak_hours(days=7)

        assert "hourly_data" in result
        assert len(result["hourly_data"]) == 4
        assert 10 in result["peak_hours_by_requests"]

    @pytest.mark.asyncio
    async def test_get_weekday_patterns(
        self, analyzer: TrendAnalyzerService, mock_db: MagicMock
    ) -> None:
        """Test get_weekday_patterns returns weekday breakdown."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("0", 50, 5000),   # Sunday
            ("1", 100, 10000), # Monday (busiest)
            ("2", 90, 9000),   # Tuesday
            ("5", 80, 8000),   # Friday
            ("6", 40, 4000),   # Saturday
        ]

        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await analyzer.get_weekday_patterns(days=28)

        assert "weekday_data" in result
        assert "summary" in result
        assert result["summary"]["busiest_day"] == "Monday"

    @pytest.mark.asyncio
    async def test_detect_anomalies(
        self, analyzer: TrendAnalyzerService, mock_db: MagicMock
    ) -> None:
        """Test detect_anomalies identifies unusual days."""
        today = datetime.now(UTC).date()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (today - timedelta(days=4), 100, 10000),
            (today - timedelta(days=3), 105, 10500),
            (today - timedelta(days=2), 95, 9500),
            (today - timedelta(days=1), 300, 30000),  # Anomaly!
            (today, 100, 10000),
        ]

        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await analyzer.detect_anomalies(days=5, threshold_std=2.0)

        assert "anomalies" in result
        assert len(result["anomalies"]) > 0
        assert result["summary"]["total_anomalous_days"] > 0

    @pytest.mark.asyncio
    async def test_detect_anomalies_insufficient_data(
        self, analyzer: TrendAnalyzerService, mock_db: MagicMock
    ) -> None:
        """Test detect_anomalies with insufficient data."""
        today = datetime.now(UTC).date()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (today, 100, 10000),
        ]

        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await analyzer.detect_anomalies(days=7)

        assert result["summary"]["insufficient_data"] is True

    @pytest.mark.asyncio
    async def test_compare_periods(
        self, analyzer: TrendAnalyzerService, mock_db: MagicMock
    ) -> None:
        """Test compare_periods compares current to previous."""
        # Mock current period (higher values)
        mock_current = MagicMock()
        mock_current.one.return_value = MagicMock(
            requests=100, tokens=10000, cost=1.50, devices=5
        )

        # Mock previous period (lower values)
        mock_previous = MagicMock()
        mock_previous.one.return_value = MagicMock(
            requests=80, tokens=8000, cost=1.20, devices=4
        )

        mock_db.execute = AsyncMock(side_effect=[mock_current, mock_previous])

        result = await analyzer.compare_periods(current_days=7)

        assert "comparison" in result
        assert "requests" in result["comparison"]
        assert result["comparison"]["requests"]["current"] == 100
        assert result["comparison"]["requests"]["previous"] == 80
        assert result["comparison"]["requests"]["change"] == 20
        assert result["comparison"]["requests"]["change_percent"] == 25.0  # 20/80 * 100
