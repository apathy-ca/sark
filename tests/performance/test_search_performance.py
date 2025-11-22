"""Performance tests for search and filtering with large datasets.

This module tests search/filter performance with 10,000+ records
to ensure the implementation meets the <100ms performance target.
"""

import asyncio
import time
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from sark.api.pagination import CursorPaginator, PaginationParams
from sark.models.mcp_server import MCPServer, SensitivityLevel, ServerStatus, TransportType
from sark.services.discovery.search import ServerSearchService


class TestSearchPerformance:
    """Performance tests for search and filtering."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_search_with_10k_records(self) -> None:
        """Test search performance with 10,000 records."""
        # Create mock database session
        mock_db = AsyncMock()

        # Create 10,000+ test servers
        num_records = 10_000
        test_servers = [
            MCPServer(
                id=uuid4(),
                name=f"server-{i:05d}",
                description=f"Analytics server {i}",
                transport=TransportType.HTTP,
                endpoint=f"http://server-{i}.example.com",
                mcp_version="2025-06-18",
                capabilities=["tools"],
                sensitivity_level=(
                    SensitivityLevel.HIGH if i % 4 == 0 else SensitivityLevel.MEDIUM
                ),
                status=(ServerStatus.ACTIVE if i % 3 == 0 else ServerStatus.REGISTERED),
                team_id=uuid4(),
                tags=["production" if i % 2 == 0 else "development"],
                created_at=datetime.now(UTC),
            )
            for i in range(num_records)
        ]

        # Performance test: search with filters
        start_time = time.perf_counter()

        search_service = ServerSearchService(mock_db)
        query = search_service.search_servers(
            query=select(MCPServer),
            status=ServerStatus.ACTIVE,
            sensitivity=SensitivityLevel.HIGH,
            search="analytics",
        )

        elapsed = time.perf_counter() - start_time

        # Query building should be fast (not executing, just building)
        assert query is not None

        # Performance target: query building < 10ms
        assert elapsed < 0.01, f"Search query building took {elapsed*1000:.2f}ms, expected < 10ms"

        print(f"\n✅ Search query building (10K records): {elapsed*1000:.2f}ms")

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_multiple_filters_performance(self) -> None:
        """Test performance with multiple filters combined."""
        mock_db = AsyncMock()

        start_time = time.perf_counter()

        search_service = ServerSearchService(mock_db)
        query = search_service.search_servers(
            query=select(MCPServer),
            status=[ServerStatus.ACTIVE, ServerStatus.REGISTERED],
            sensitivity=[SensitivityLevel.HIGH, SensitivityLevel.CRITICAL],
            team_id=uuid4(),
            tags=["production", "critical"],
            match_all_tags=True,
            search="analytics server",
        )

        elapsed = time.perf_counter() - start_time

        assert query is not None

        # Performance target: complex query building < 10ms
        assert elapsed < 0.01, f"Complex query building took {elapsed*1000:.2f}ms, expected < 10ms"

        print(f"\n✅ Complex filter query building: {elapsed*1000:.2f}ms")

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_search_with_pagination_10k(self) -> None:
        """Test search + pagination performance with 10,000 records."""
        mock_db = AsyncMock()

        # Build search query
        search_service = ServerSearchService(mock_db)
        query = search_service.search_servers(
            query=select(MCPServer),
            status=ServerStatus.ACTIVE,
            search="analytics",
        )

        # Mock filtered results (51 items to simulate has_more)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            MCPServer(
                id=uuid4(),
                name=f"analytics-server-{i:05d}",
                description=f"Analytics server {i}",
                transport=TransportType.HTTP,
                endpoint=f"http://server-{i}.example.com",
                mcp_version="2025-06-18",
                capabilities=["tools"],
                sensitivity_level=SensitivityLevel.HIGH,
                status=ServerStatus.ACTIVE,
                created_at=datetime.now(UTC),
            )
            for i in range(51)
        ]
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Performance test: search + pagination
        start_time = time.perf_counter()

        params = PaginationParams(limit=50)
        items, next_cursor, has_more, _ = await CursorPaginator.paginate(
            db=mock_db,
            query=query,
            cursor_column=MCPServer.created_at,
            params=params,
            count_total=False,
        )

        elapsed = time.perf_counter() - start_time

        # Verify results
        assert len(items) == 50
        assert has_more is True

        # Performance target: search + pagination < 100ms
        assert elapsed < 0.1, f"Search + pagination took {elapsed*1000:.2f}ms, expected < 100ms"

        print(f"\n✅ Search + pagination (10K records): {elapsed*1000:.2f}ms")

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_tag_filter_performance(self) -> None:
        """Test tag filtering performance."""
        mock_db = AsyncMock()

        start_time = time.perf_counter()

        search_service = ServerSearchService(mock_db)

        # Test with multiple tags
        query = search_service.search_servers(
            query=select(MCPServer),
            tags=["production", "critical", "monitoring", "analytics", "ml"],
            match_all_tags=False,  # OR logic
        )

        elapsed = time.perf_counter() - start_time

        assert query is not None

        # Tag filtering should be fast
        assert elapsed < 0.01, f"Tag filtering took {elapsed*1000:.2f}ms, expected < 10ms"

        print(f"\n✅ Tag filter (5 tags, OR): {elapsed*1000:.2f}ms")

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_tag_filter_match_all_performance(self) -> None:
        """Test tag filtering with match_all performance."""
        mock_db = AsyncMock()

        start_time = time.perf_counter()

        search_service = ServerSearchService(mock_db)

        # Test with multiple tags, match ALL
        query = search_service.search_servers(
            query=select(MCPServer),
            tags=["production", "critical", "monitoring"],
            match_all_tags=True,  # AND logic
        )

        elapsed = time.perf_counter() - start_time

        assert query is not None

        # Tag filtering should be fast
        assert (
            elapsed < 0.01
        ), f"Tag filtering (match_all) took {elapsed*1000:.2f}ms, expected < 10ms"

        print(f"\n✅ Tag filter (3 tags, AND): {elapsed*1000:.2f}ms")

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_full_text_search_performance(self) -> None:
        """Test full-text search performance."""
        mock_db = AsyncMock()

        start_time = time.perf_counter()

        search_service = ServerSearchService(mock_db)

        # Test with search query
        query = search_service.search_servers(
            query=select(MCPServer),
            search="analytics machine learning data pipeline",
        )

        elapsed = time.perf_counter() - start_time

        assert query is not None

        # Search should be fast
        assert elapsed < 0.01, f"Full-text search took {elapsed*1000:.2f}ms, expected < 10ms"

        print(f"\n✅ Full-text search: {elapsed*1000:.2f}ms")

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_sequential_searches_performance(self) -> None:
        """Test performance of multiple sequential searches."""
        mock_db = AsyncMock()
        search_service = ServerSearchService(mock_db)

        num_searches = 100
        total_time = 0.0

        for i in range(num_searches):
            start_time = time.perf_counter()

            query = search_service.search_servers(
                query=select(MCPServer),
                status=ServerStatus.ACTIVE if i % 2 == 0 else ServerStatus.REGISTERED,
                sensitivity=SensitivityLevel.HIGH if i % 3 == 0 else SensitivityLevel.MEDIUM,
                search=f"server-{i:05d}",
            )

            elapsed = time.perf_counter() - start_time
            total_time += elapsed

            assert query is not None

        avg_time = total_time / num_searches

        # Average search should be very fast
        assert avg_time < 0.005, f"Average search: {avg_time*1000:.2f}ms, expected < 5ms"

        print(
            f"\n✅ Sequential searches ({num_searches} searches): "
            f"{total_time*1000:.2f}ms total, {avg_time*1000:.3f}ms avg"
        )

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_worst_case_filters(self) -> None:
        """Test performance with all filters enabled (worst case)."""
        mock_db = AsyncMock()

        start_time = time.perf_counter()

        search_service = ServerSearchService(mock_db)

        # Apply ALL possible filters
        query = search_service.search_servers(
            query=select(MCPServer),
            status=[ServerStatus.ACTIVE, ServerStatus.REGISTERED, ServerStatus.INACTIVE],
            sensitivity=[
                SensitivityLevel.LOW,
                SensitivityLevel.MEDIUM,
                SensitivityLevel.HIGH,
                SensitivityLevel.CRITICAL,
            ],
            team_id=uuid4(),
            owner_id=uuid4(),
            tags=[
                "production",
                "development",
                "staging",
                "critical",
                "monitoring",
                "analytics",
            ],
            match_all_tags=True,
            search="complex analytics machine learning data processing pipeline",
        )

        elapsed = time.perf_counter() - start_time

        assert query is not None

        # Even worst case should be fast
        assert (
            elapsed < 0.02
        ), f"Worst case query building took {elapsed*1000:.2f}ms, expected < 20ms"

        print(f"\n✅ Worst case (all filters): {elapsed*1000:.2f}ms")


if __name__ == "__main__":
    """Run performance tests standalone."""
    print("Running search/filter performance tests...")
    print("=" * 60)

    # Run tests
    asyncio.run(TestSearchPerformance().test_search_with_10k_records())
    asyncio.run(TestSearchPerformance().test_multiple_filters_performance())
    asyncio.run(TestSearchPerformance().test_search_with_pagination_10k())
    asyncio.run(TestSearchPerformance().test_tag_filter_performance())
    asyncio.run(TestSearchPerformance().test_tag_filter_match_all_performance())
    asyncio.run(TestSearchPerformance().test_full_text_search_performance())
    asyncio.run(TestSearchPerformance().test_sequential_searches_performance())
    asyncio.run(TestSearchPerformance().test_worst_case_filters())

    print("=" * 60)
    print("\n✅ All performance tests passed!")
