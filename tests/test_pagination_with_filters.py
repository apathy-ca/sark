"""Integration tests for pagination with search and filters."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from sark.api.pagination import CursorPaginator, PaginationParams
from sark.models.mcp_server import MCPServer, SensitivityLevel, ServerStatus, TransportType
from sark.services.discovery.search import ServerSearchService


class TestPaginationWithFilters:
    """Test that pagination works correctly with search and filters."""

    @pytest.mark.asyncio
    async def test_pagination_with_status_filter(self) -> None:
        """Test pagination combined with status filter."""
        mock_db = AsyncMock()

        # Build filtered query
        search_service = ServerSearchService(mock_db)
        query = search_service.search_servers(
            query=select(MCPServer),
            status=ServerStatus.ACTIVE,
        )

        # Mock results
        mock_servers = [
            MCPServer(
                id=uuid4(),
                name=f"server-{i}",
                description="Test server",
                transport=TransportType.HTTP,
                endpoint="http://test.com",
                mcp_version="2025-06-18",
                capabilities=["tools"],
                sensitivity_level=SensitivityLevel.MEDIUM,
                status=ServerStatus.ACTIVE,
                created_at=datetime.now(UTC),
            )
            for i in range(51)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_servers
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Apply pagination
        params = PaginationParams(limit=50)
        items, next_cursor, has_more, _ = await CursorPaginator.paginate(
            db=mock_db,
            query=query,
            cursor_column=MCPServer.created_at,
            params=params,
            count_total=False,
        )

        # Verify results
        assert len(items) == 50
        assert has_more is True
        assert next_cursor is not None

    @pytest.mark.asyncio
    async def test_pagination_with_multiple_filters(self) -> None:
        """Test pagination with multiple filters combined."""
        mock_db = AsyncMock()

        # Build query with multiple filters
        search_service = ServerSearchService(mock_db)
        query = search_service.search_servers(
            query=select(MCPServer),
            status=ServerStatus.ACTIVE,
            sensitivity=SensitivityLevel.HIGH,
            tags=["production"],
        )

        # Mock results
        mock_servers = [
            MCPServer(
                id=uuid4(),
                name=f"server-{i}",
                description="Production server",
                transport=TransportType.HTTP,
                endpoint="http://test.com",
                mcp_version="2025-06-18",
                capabilities=["tools"],
                sensitivity_level=SensitivityLevel.HIGH,
                status=ServerStatus.ACTIVE,
                tags=["production"],
                created_at=datetime.now(UTC),
            )
            for i in range(30)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_servers
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Apply pagination
        params = PaginationParams(limit=50)
        items, next_cursor, has_more, _ = await CursorPaginator.paginate(
            db=mock_db,
            query=query,
            cursor_column=MCPServer.created_at,
            params=params,
            count_total=False,
        )

        # Verify results
        assert len(items) == 30
        assert has_more is False
        assert next_cursor is None

    @pytest.mark.asyncio
    async def test_pagination_with_search(self) -> None:
        """Test pagination with full-text search."""
        mock_db = AsyncMock()

        # Build search query
        search_service = ServerSearchService(mock_db)
        query = search_service.search_servers(
            query=select(MCPServer),
            search="analytics",
        )

        # Mock results
        mock_servers = [
            MCPServer(
                id=uuid4(),
                name=f"analytics-server-{i}",
                description="Analytics processing server",
                transport=TransportType.HTTP,
                endpoint="http://test.com",
                mcp_version="2025-06-18",
                capabilities=["tools"],
                sensitivity_level=SensitivityLevel.MEDIUM,
                status=ServerStatus.ACTIVE,
                created_at=datetime.now(UTC),
            )
            for i in range(51)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_servers
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Apply pagination
        params = PaginationParams(limit=50)
        items, next_cursor, has_more, _ = await CursorPaginator.paginate(
            db=mock_db,
            query=query,
            cursor_column=MCPServer.created_at,
            params=params,
            count_total=False,
        )

        # Verify results
        assert len(items) == 50
        assert has_more is True

    @pytest.mark.asyncio
    async def test_pagination_with_search_and_filters(self) -> None:
        """Test pagination with both search and filters."""
        mock_db = AsyncMock()

        # Build complex query
        search_service = ServerSearchService(mock_db)
        query = search_service.search_servers(
            query=select(MCPServer),
            status=[ServerStatus.ACTIVE, ServerStatus.REGISTERED],
            sensitivity=SensitivityLevel.HIGH,
            tags=["production", "critical"],
            search="analytics",
        )

        # Mock results
        mock_servers = [
            MCPServer(
                id=uuid4(),
                name=f"analytics-server-{i}",
                description="Analytics server",
                transport=TransportType.HTTP,
                endpoint="http://test.com",
                mcp_version="2025-06-18",
                capabilities=["tools"],
                sensitivity_level=SensitivityLevel.HIGH,
                status=ServerStatus.ACTIVE if i % 2 == 0 else ServerStatus.REGISTERED,
                tags=["production", "critical"],
                created_at=datetime.now(UTC),
            )
            for i in range(25)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_servers
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Apply pagination
        params = PaginationParams(limit=50)
        items, next_cursor, has_more, _ = await CursorPaginator.paginate(
            db=mock_db,
            query=query,
            cursor_column=MCPServer.created_at,
            params=params,
            count_total=False,
        )

        # Verify results
        assert len(items) == 25
        assert has_more is False

    @pytest.mark.asyncio
    async def test_filtered_pagination_multiple_pages(self) -> None:
        """Test that filters work across multiple paginated pages."""
        mock_db = AsyncMock()

        # Build filtered query
        search_service = ServerSearchService(mock_db)
        query = search_service.search_servers(
            query=select(MCPServer),
            status=ServerStatus.ACTIVE,
        )

        # First page - 51 items (has more)
        first_page = [
            MCPServer(
                id=uuid4(),
                name=f"server-{i}",
                description="Test server",
                transport=TransportType.HTTP,
                endpoint="http://test.com",
                mcp_version="2025-06-18",
                capabilities=["tools"],
                sensitivity_level=SensitivityLevel.MEDIUM,
                status=ServerStatus.ACTIVE,
                created_at=datetime.now(UTC),
            )
            for i in range(51)
        ]

        # Second page - 30 items (no more)
        second_page = [
            MCPServer(
                id=uuid4(),
                name=f"server-{i}",
                description="Test server",
                transport=TransportType.HTTP,
                endpoint="http://test.com",
                mcp_version="2025-06-18",
                capabilities=["tools"],
                sensitivity_level=SensitivityLevel.MEDIUM,
                status=ServerStatus.ACTIVE,
                created_at=datetime.now(UTC),
            )
            for i in range(50, 80)
        ]

        # Mock first call
        mock_result_1 = MagicMock()
        mock_result_1.scalars.return_value.all.return_value = first_page

        # Mock second call
        mock_result_2 = MagicMock()
        mock_result_2.scalars.return_value.all.return_value = second_page

        mock_db.execute = AsyncMock(side_effect=[mock_result_1, mock_result_2])

        # Get first page
        params = PaginationParams(limit=50)
        items_1, cursor_1, has_more_1, _ = await CursorPaginator.paginate(
            db=mock_db,
            query=query,
            cursor_column=MCPServer.created_at,
            params=params,
            count_total=False,
        )

        assert len(items_1) == 50
        assert has_more_1 is True
        assert cursor_1 is not None

        # Get second page
        params_2 = PaginationParams(limit=50, cursor=cursor_1)
        items_2, cursor_2, has_more_2, _ = await CursorPaginator.paginate(
            db=mock_db,
            query=query,
            cursor_column=MCPServer.created_at,
            params=params_2,
            count_total=False,
        )

        assert len(items_2) == 30
        assert has_more_2 is False
        assert cursor_2 is None

    @pytest.mark.asyncio
    async def test_empty_results_with_filters(self) -> None:
        """Test pagination with filters that return no results."""
        mock_db = AsyncMock()

        # Build filtered query with restrictive filters
        search_service = ServerSearchService(mock_db)
        query = search_service.search_servers(
            query=select(MCPServer),
            status=ServerStatus.DECOMMISSIONED,
            sensitivity=SensitivityLevel.CRITICAL,
            search="nonexistent",
        )

        # Mock empty results
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Apply pagination
        params = PaginationParams(limit=50)
        items, next_cursor, has_more, _ = await CursorPaginator.paginate(
            db=mock_db,
            query=query,
            cursor_column=MCPServer.created_at,
            params=params,
            count_total=False,
        )

        # Verify empty results
        assert len(items) == 0
        assert has_more is False
        assert next_cursor is None
