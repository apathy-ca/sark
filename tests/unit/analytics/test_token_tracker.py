"""Unit tests for TokenTrackerService."""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sark.services.analytics.token_tracker import TokenTrackerService, TokenUsage


class TestTokenUsage:
    """Tests for TokenUsage dataclass."""

    def test_total_tokens(self) -> None:
        """Test total_tokens property."""
        usage = TokenUsage(
            device_ip="192.168.1.100",
            endpoint="openai/chat",
            provider="openai",
            tokens_prompt=100,
            tokens_response=50,
        )

        assert usage.total_tokens == 150

    def test_token_usage_with_optional_fields(self) -> None:
        """Test TokenUsage with all optional fields."""
        usage = TokenUsage(
            device_ip="192.168.1.100",
            endpoint="openai/chat",
            provider="openai",
            tokens_prompt=100,
            tokens_response=50,
            model="gpt-4",
            device_name="My Laptop",
            cost_estimate=0.05,
            request_id="req-123",
            timestamp=datetime.now(UTC),
        )

        assert usage.model == "gpt-4"
        assert usage.device_name == "My Laptop"
        assert usage.cost_estimate == 0.05
        assert usage.request_id == "req-123"


class TestTokenTrackerService:
    """Tests for TokenTrackerService."""

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
    def tracker(self, mock_db: MagicMock) -> TokenTrackerService:
        """Create token tracker with mock DB."""
        return TokenTrackerService(mock_db)

    @pytest.mark.asyncio
    async def test_record_creates_usage_event(
        self, tracker: TokenTrackerService, mock_db: MagicMock
    ) -> None:
        """Test that record creates a usage event."""
        await tracker.record(
            device_ip="192.168.1.100",
            endpoint="openai/chat",
            provider="openai",
            tokens_prompt=100,
            tokens_response=50,
        )

        # Verify add was called
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_with_all_fields(
        self, tracker: TokenTrackerService, mock_db: MagicMock
    ) -> None:
        """Test record with all optional fields."""
        await tracker.record(
            device_ip="192.168.1.100",
            endpoint="openai/chat",
            provider="openai",
            tokens_prompt=100,
            tokens_response=50,
            model="gpt-4",
            device_name="My Laptop",
            cost_estimate=0.05,
            request_id="req-123",
            metadata={"key": "value"},
        )

        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_batch(
        self, tracker: TokenTrackerService, mock_db: MagicMock
    ) -> None:
        """Test batch recording."""
        usages = [
            TokenUsage(
                device_ip="192.168.1.100",
                endpoint="openai/chat",
                provider="openai",
                tokens_prompt=100,
                tokens_response=50,
            ),
            TokenUsage(
                device_ip="192.168.1.101",
                endpoint="anthropic/messages",
                provider="anthropic",
                tokens_prompt=200,
                tokens_response=100,
            ),
        ]

        await tracker.record_batch(usages)

        # Should add 2 events
        assert mock_db.add.call_count == 2
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_daily_returns_stats(
        self, tracker: TokenTrackerService, mock_db: MagicMock
    ) -> None:
        """Test get_daily returns aggregated stats."""
        # Mock the execute result for summary
        mock_row = MagicMock()
        mock_row.request_count = 10
        mock_row.tokens_prompt = 1000
        mock_row.tokens_response = 500
        mock_row.cost_total = 0.15

        mock_result = MagicMock()
        mock_result.one.return_value = mock_row
        mock_result.fetchall.return_value = [("openai/chat", 10, 1500)]

        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await tracker.get_daily(device_ip="192.168.1.100")

        assert result["device_ip"] == "192.168.1.100"
        assert result["request_count"] == 10
        assert result["total"] == 1500  # 1000 + 500
        assert result["prompt"] == 1000
        assert result["response"] == 500

    @pytest.mark.asyncio
    async def test_get_daily_with_specific_date(
        self, tracker: TokenTrackerService, mock_db: MagicMock
    ) -> None:
        """Test get_daily with a specific date."""
        mock_row = MagicMock()
        mock_row.request_count = 5
        mock_row.tokens_prompt = 500
        mock_row.tokens_response = 250
        mock_row.cost_total = None

        mock_result = MagicMock()
        mock_result.one.return_value = mock_row
        mock_result.fetchall.return_value = []

        mock_db.execute = AsyncMock(return_value=mock_result)

        specific_date = date(2025, 1, 15)
        result = await tracker.get_daily(
            device_ip="192.168.1.100",
            day=specific_date,
        )

        assert result["date"] == "2025-01-15"

    @pytest.mark.asyncio
    async def test_get_device_stats(
        self, tracker: TokenTrackerService, mock_db: MagicMock
    ) -> None:
        """Test get_device_stats returns period stats."""
        mock_row = MagicMock()
        mock_row.request_count = 100
        mock_row.tokens_prompt = 10000
        mock_row.tokens_response = 5000
        mock_row.cost_total = 1.50

        mock_result = MagicMock()
        mock_result.one.return_value = mock_row
        mock_result.fetchall.return_value = [
            ("2025-01-20", 15, 2000),
            ("2025-01-21", 20, 3000),
        ]

        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await tracker.get_device_stats(device_ip="192.168.1.100", days=7)

        assert result["device_ip"] == "192.168.1.100"
        assert result["period_days"] == 7
        assert result["request_count"] == 100
        assert result["total_tokens"] == 15000
        assert len(result["daily"]) == 2

    @pytest.mark.asyncio
    async def test_get_top_devices(
        self, tracker: TokenTrackerService, mock_db: MagicMock
    ) -> None:
        """Test get_top_devices returns ranked devices."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("192.168.1.100", "Laptop", 50, 10000, 1.00),
            ("192.168.1.101", "Desktop", 30, 5000, 0.50),
        ]

        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await tracker.get_top_devices(days=7, limit=5)

        assert len(result) == 2
        assert result[0]["device_ip"] == "192.168.1.100"
        assert result[0]["total_tokens"] == 10000
        assert result[1]["device_ip"] == "192.168.1.101"

    @pytest.mark.asyncio
    async def test_get_hourly_distribution(
        self, tracker: TokenTrackerService, mock_db: MagicMock
    ) -> None:
        """Test get_hourly_distribution returns hourly breakdown."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("09", 10, 1000),
            ("10", 15, 1500),
            ("14", 20, 2000),
        ]

        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await tracker.get_hourly_distribution(days=7)

        assert len(result) == 3
        assert result[0]["hour"] == 9
        assert result[1]["hour"] == 10
        assert result[2]["hour"] == 14

    @pytest.mark.asyncio
    async def test_update_daily_aggregates(
        self, tracker: TokenTrackerService, mock_db: MagicMock
    ) -> None:
        """Test update_daily_aggregates creates aggregates."""
        # Mock the query results
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("192.168.1.100", "openai/chat", "openai", 10, 1000, 500, 0.15),
        ]

        mock_existing = MagicMock()
        mock_existing.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[mock_result, mock_existing])

        count = await tracker.update_daily_aggregates()

        assert count == 1
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
