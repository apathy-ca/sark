"""Tests for pagination utilities."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import Column, DateTime, String, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from sark.api.pagination import CursorPaginator, PaginatedResponse, PaginationParams
from sark.db.base import Base


# Test model for pagination
class TestModel(Base):
    """Test model for pagination."""

    __tablename__ = "test_pagination_model"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


class TestPaginationParams:
    """Test PaginationParams model."""

    def test_default_values(self) -> None:
        """Test default pagination parameter values."""
        params = PaginationParams()

        assert params.limit == 50
        assert params.cursor is None
        assert params.sort_order == "desc"

    def test_custom_values(self) -> None:
        """Test custom pagination parameter values."""
        params = PaginationParams(limit=100, cursor="abc123", sort_order="asc")

        assert params.limit == 100
        assert params.cursor == "abc123"
        assert params.sort_order == "asc"

    def test_limit_validation_min(self) -> None:
        """Test minimum limit validation."""
        with pytest.raises(ValueError):
            PaginationParams(limit=0)

    def test_limit_validation_max(self) -> None:
        """Test maximum limit validation."""
        with pytest.raises(ValueError):
            PaginationParams(limit=201)

    def test_sort_order_validation(self) -> None:
        """Test sort order validation."""
        with pytest.raises(ValueError):
            PaginationParams(sort_order="invalid")


class TestPaginatedResponse:
    """Test PaginatedResponse model."""

    def test_basic_response(self) -> None:
        """Test basic paginated response."""
        response = PaginatedResponse(
            items=[{"id": 1}, {"id": 2}],
            next_cursor="cursor123",
            has_more=True,
            total=100,
        )

        assert len(response.items) == 2
        assert response.next_cursor == "cursor123"
        assert response.has_more is True
        assert response.total == 100

    def test_last_page_response(self) -> None:
        """Test last page response."""
        response = PaginatedResponse(
            items=[{"id": 1}],
            next_cursor=None,
            has_more=False,
            total=1,
        )

        assert len(response.items) == 1
        assert response.next_cursor is None
        assert response.has_more is False

    def test_optional_total(self) -> None:
        """Test response without total count."""
        response = PaginatedResponse(
            items=[{"id": 1}],
            next_cursor="cursor123",
            has_more=True,
        )

        assert response.total is None


class TestCursorPaginator:
    """Test CursorPaginator class."""

    def test_encode_uuid(self) -> None:
        """Test encoding UUID cursor."""
        test_uuid = uuid4()
        cursor = CursorPaginator.encode_cursor(test_uuid)

        assert isinstance(cursor, str)
        assert len(cursor) > 0

    def test_encode_string(self) -> None:
        """Test encoding string cursor."""
        test_string = "test_value_123"
        cursor = CursorPaginator.encode_cursor(test_string)

        assert isinstance(cursor, str)
        assert len(cursor) > 0

    def test_encode_int(self) -> None:
        """Test encoding integer cursor."""
        test_int = 12345
        cursor = CursorPaginator.encode_cursor(test_int)

        assert isinstance(cursor, str)
        assert len(cursor) > 0

    def test_decode_cursor(self) -> None:
        """Test decoding cursor."""
        original = "test_value_123"
        encoded = CursorPaginator.encode_cursor(original)
        decoded = CursorPaginator.decode_cursor(encoded)

        assert decoded == original

    def test_decode_invalid_cursor(self) -> None:
        """Test decoding invalid cursor."""
        with pytest.raises(ValueError, match="Invalid pagination cursor"):
            CursorPaginator.decode_cursor("invalid!!!cursor")

    def test_encode_decode_uuid_roundtrip(self) -> None:
        """Test UUID encode/decode round trip."""
        test_uuid = uuid4()
        encoded = CursorPaginator.encode_cursor(test_uuid)
        decoded = CursorPaginator.decode_cursor(encoded)

        assert decoded == str(test_uuid)

    @pytest.mark.asyncio
    async def test_paginate_first_page(self) -> None:
        """Test paginating first page."""
        # Create mock database session
        mock_db = AsyncMock(spec=AsyncSession)

        # Create test data
        test_items = [
            TestModel(id=uuid4(), name=f"Item {i}", created_at=datetime.now(UTC)) for i in range(60)
        ]

        # Mock query execution - return first 51 items (limit + 1)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = test_items[:51]
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Create pagination params
        params = PaginationParams(limit=50)

        # Execute pagination
        items, next_cursor, has_more, total = await CursorPaginator.paginate(
            db=mock_db,
            query=select(TestModel),
            cursor_column=TestModel.created_at,
            params=params,
            count_total=False,
        )

        # Verify results
        assert len(items) == 50  # Should trim to limit
        assert has_more is True
        assert next_cursor is not None
        assert total is None

    @pytest.mark.asyncio
    async def test_paginate_last_page(self) -> None:
        """Test paginating last page."""
        # Create mock database session
        mock_db = AsyncMock(spec=AsyncSession)

        # Create test data - only 30 items left
        test_items = [
            TestModel(id=uuid4(), name=f"Item {i}", created_at=datetime.now(UTC)) for i in range(30)
        ]

        # Mock query execution
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = test_items
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Create pagination params with cursor
        params = PaginationParams(limit=50, cursor="some_cursor")

        # Execute pagination
        items, next_cursor, has_more, total = await CursorPaginator.paginate(
            db=mock_db,
            query=select(TestModel),
            cursor_column=TestModel.created_at,
            params=params,
            count_total=False,
        )

        # Verify results
        assert len(items) == 30
        assert has_more is False
        assert next_cursor is None
        assert total is None

    @pytest.mark.asyncio
    async def test_paginate_with_total_count(self) -> None:
        """Test pagination with total count."""
        # Create mock database session
        mock_db = AsyncMock(spec=AsyncSession)

        # Create test data
        test_items = [
            TestModel(id=uuid4(), name=f"Item {i}", created_at=datetime.now(UTC)) for i in range(51)
        ]

        # Mock query execution
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = test_items
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Mock count query - side effect for multiple execute calls
        async def mock_execute(query):
            """Mock execute that returns different results."""
            if "count" in str(query).lower():
                count_result = MagicMock()
                count_result.scalar.return_value = 150
                return count_result
            else:
                return mock_result

        mock_db.execute = AsyncMock(side_effect=mock_execute)

        # Create pagination params
        params = PaginationParams(limit=50)

        # Execute pagination with count
        items, next_cursor, has_more, total = await CursorPaginator.paginate(
            db=mock_db,
            query=select(TestModel),
            cursor_column=TestModel.created_at,
            params=params,
            count_total=True,
        )

        # Verify results
        assert len(items) == 50
        assert has_more is True
        assert next_cursor is not None
        assert total == 150

    @pytest.mark.asyncio
    async def test_paginate_ascending_order(self) -> None:
        """Test pagination with ascending sort order."""
        # Create mock database session
        mock_db = AsyncMock(spec=AsyncSession)

        # Create test data
        test_items = [
            TestModel(id=uuid4(), name=f"Item {i}", created_at=datetime.now(UTC)) for i in range(30)
        ]

        # Mock query execution
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = test_items
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Create pagination params with ascending order
        params = PaginationParams(limit=50, sort_order="asc")

        # Execute pagination
        items, next_cursor, has_more, total = await CursorPaginator.paginate(
            db=mock_db,
            query=select(TestModel),
            cursor_column=TestModel.created_at,
            params=params,
            count_total=False,
        )

        # Verify results
        assert len(items) == 30
        assert has_more is False

    @pytest.mark.asyncio
    async def test_paginate_empty_results(self) -> None:
        """Test pagination with no results."""
        # Create mock database session
        mock_db = AsyncMock(spec=AsyncSession)

        # Mock query execution with empty results
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Create pagination params
        params = PaginationParams(limit=50)

        # Execute pagination
        items, next_cursor, has_more, total = await CursorPaginator.paginate(
            db=mock_db,
            query=select(TestModel),
            cursor_column=TestModel.created_at,
            params=params,
            count_total=False,
        )

        # Verify results
        assert len(items) == 0
        assert has_more is False
        assert next_cursor is None
        assert total is None

    @pytest.mark.asyncio
    async def test_paginate_invalid_cursor_ignored(self) -> None:
        """Test that invalid cursor is ignored and pagination starts from beginning."""
        # Create mock database session
        mock_db = AsyncMock(spec=AsyncSession)

        # Create test data
        test_items = [
            TestModel(id=uuid4(), name=f"Item {i}", created_at=datetime.now(UTC)) for i in range(30)
        ]

        # Mock query execution
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = test_items
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Create pagination params with invalid cursor
        params = PaginationParams(limit=50, cursor="invalid!!!cursor")

        # Execute pagination - should not raise error
        items, next_cursor, has_more, total = await CursorPaginator.paginate(
            db=mock_db,
            query=select(TestModel),
            cursor_column=TestModel.created_at,
            params=params,
            count_total=False,
        )

        # Verify results - should work as if no cursor provided
        assert len(items) == 30
        assert has_more is False
