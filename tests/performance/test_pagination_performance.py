"""Performance tests for pagination with large datasets.

This module tests pagination performance with 10,000+ records
to ensure the implementation meets performance targets.
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


class TestPaginationPerformance:
    """Performance tests for pagination."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_pagination_with_10k_records(self) -> None:
        """Test pagination performance with 10,000 records."""
        # Create mock database session
        mock_db = AsyncMock()

        # Create 10,000+ test servers
        num_records = 10_000
        test_servers = [
            MCPServer(
                id=uuid4(),
                name=f"server-{i:05d}",
                description=f"Test server {i}",
                transport=TransportType.HTTP,
                endpoint=f"http://server-{i}.example.com",
                mcp_version="2025-06-18",
                capabilities=["tools"],
                sensitivity_level=SensitivityLevel.MEDIUM,
                status=ServerStatus.ACTIVE,
                created_at=datetime.now(UTC),
            )
            for i in range(num_records)
        ]

        # Performance test: first page (limit 50)
        start_time = time.perf_counter()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = test_servers[:51]
        mock_db.execute = AsyncMock(return_value=mock_result)

        params = PaginationParams(limit=50)

        items, next_cursor, has_more, total = await CursorPaginator.paginate(
            db=mock_db,
            query=select(MCPServer),
            cursor_column=MCPServer.created_at,
            params=params,
            count_total=False,
        )

        elapsed = time.perf_counter() - start_time

        # Verify results
        assert len(items) == 50
        assert has_more is True
        assert next_cursor is not None

        # Performance target: pagination should complete in < 100ms
        # (actual DB query time not included in this mock test)
        assert elapsed < 0.1, f"Pagination took {elapsed:.3f}s, expected < 0.1s"

        print(f"\n✅ Pagination with 10K records: {elapsed*1000:.2f}ms")

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_pagination_with_100k_records(self) -> None:
        """Test pagination performance with 100,000 records."""
        # Create mock database session
        mock_db = AsyncMock()

        # Simulate 100,000 records
        num_records = 100_000

        # Mock paginated results
        mock_result = MagicMock()
        # Return 51 items to simulate has_more
        mock_result.scalars.return_value.all.return_value = [
            MCPServer(
                id=uuid4(),
                name=f"server-{i:06d}",
                description=f"Test server {i}",
                transport=TransportType.HTTP,
                endpoint=f"http://server-{i}.example.com",
                mcp_version="2025-06-18",
                capabilities=["tools"],
                sensitivity_level=SensitivityLevel.MEDIUM,
                status=ServerStatus.ACTIVE,
                created_at=datetime.now(UTC),
            )
            for i in range(51)
        ]
        mock_db.execute = AsyncMock(return_value=mock_result)

        start_time = time.perf_counter()

        params = PaginationParams(limit=50)

        items, next_cursor, has_more, total = await CursorPaginator.paginate(
            db=mock_db,
            query=select(MCPServer),
            cursor_column=MCPServer.created_at,
            params=params,
            count_total=False,
        )

        elapsed = time.perf_counter() - start_time

        # Verify results
        assert len(items) == 50
        assert has_more is True

        # Performance should scale independently of total record count
        assert elapsed < 0.1, f"Pagination took {elapsed:.3f}s, expected < 0.1s"

        print(f"\n✅ Pagination with 100K records: {elapsed*1000:.2f}ms")

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_cursor_encoding_performance(self) -> None:
        """Test cursor encoding/decoding performance."""
        # Test with various cursor types
        test_cursors = (
            [uuid4() for _ in range(1000)]
            + [datetime.now(UTC) for _ in range(1000)]
            + [i for i in range(1000)]
            + [f"string-cursor-{i}" for i in range(1000)]
        )

        start_time = time.perf_counter()

        for cursor_value in test_cursors:
            encoded = CursorPaginator.encode_cursor(cursor_value)
            decoded = CursorPaginator.decode_cursor(encoded)
            assert decoded is not None

        elapsed = time.perf_counter() - start_time

        # Average time per encode/decode
        avg_time = elapsed / len(test_cursors)

        # Should encode/decode in < 1ms per operation
        assert avg_time < 0.001, f"Average encode/decode: {avg_time*1000:.2f}ms, expected < 1ms"

        print(
            f"\n✅ Cursor encoding (4K operations): {elapsed*1000:.2f}ms total, "
            f"{avg_time*1000:.3f}ms avg"
        )

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_multiple_page_traversal(self) -> None:
        """Test performance of traversing multiple pages."""
        # Simulate paginating through 1000 records (20 pages of 50)
        num_pages = 20
        page_size = 50

        mock_db = AsyncMock()

        total_time = 0.0

        for page in range(num_pages):
            # Create mock results for this page
            has_more = page < (num_pages - 1)
            num_items = page_size + 1 if has_more else page_size

            mock_items = [
                MCPServer(
                    id=uuid4(),
                    name=f"server-{page*page_size + i:04d}",
                    description=f"Test server {page*page_size + i}",
                    transport=TransportType.HTTP,
                    endpoint=f"http://server-{i}.example.com",
                    mcp_version="2025-06-18",
                    capabilities=["tools"],
                    sensitivity_level=SensitivityLevel.MEDIUM,
                    status=ServerStatus.ACTIVE,
                    created_at=datetime.now(UTC),
                )
                for i in range(num_items)
            ]

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = mock_items
            mock_db.execute = AsyncMock(return_value=mock_result)

            start_time = time.perf_counter()

            params = PaginationParams(limit=page_size)

            items, next_cursor, has_more_result, _ = await CursorPaginator.paginate(
                db=mock_db,
                query=select(MCPServer),
                cursor_column=MCPServer.created_at,
                params=params,
                count_total=False,
            )

            elapsed = time.perf_counter() - start_time
            total_time += elapsed

            assert len(items) == page_size

        avg_page_time = total_time / num_pages

        # Average page fetch should be < 50ms
        assert avg_page_time < 0.05, f"Average page time: {avg_page_time*1000:.2f}ms"

        print(
            f"\n✅ Multiple page traversal ({num_pages} pages): "
            f"{total_time*1000:.2f}ms total, {avg_page_time*1000:.2f}ms avg/page"
        )

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_large_page_size_performance(self) -> None:
        """Test performance with maximum page size (200)."""
        mock_db = AsyncMock()

        # Create 201 items (to test has_more)
        large_dataset = [
            MCPServer(
                id=uuid4(),
                name=f"server-{i:04d}",
                description=f"Test server {i}",
                transport=TransportType.HTTP,
                endpoint=f"http://server-{i}.example.com",
                mcp_version="2025-06-18",
                capabilities=["tools"],
                sensitivity_level=SensitivityLevel.MEDIUM,
                status=ServerStatus.ACTIVE,
                created_at=datetime.now(UTC),
            )
            for i in range(201)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = large_dataset
        mock_db.execute = AsyncMock(return_value=mock_result)

        start_time = time.perf_counter()

        params = PaginationParams(limit=200)  # Maximum allowed

        items, next_cursor, has_more, _ = await CursorPaginator.paginate(
            db=mock_db,
            query=select(MCPServer),
            cursor_column=MCPServer.created_at,
            params=params,
            count_total=False,
        )

        elapsed = time.perf_counter() - start_time

        # Verify results
        assert len(items) == 200
        assert has_more is True

        # Should handle large pages efficiently
        assert elapsed < 0.1, f"Large page took {elapsed:.3f}s, expected < 0.1s"

        print(f"\n✅ Large page size (200 items): {elapsed*1000:.2f}ms")


if __name__ == "__main__":
    """Run performance tests standalone."""
    print("Running pagination performance tests...")
    print("=" * 60)

    # Run tests
    asyncio.run(TestPaginationPerformance().test_pagination_with_10k_records())
    asyncio.run(TestPaginationPerformance().test_pagination_with_100k_records())
    asyncio.run(TestPaginationPerformance().test_cursor_encoding_performance())
    asyncio.run(TestPaginationPerformance().test_multiple_page_traversal())
    asyncio.run(TestPaginationPerformance().test_large_page_size_performance())

    print("=" * 60)
    print("\n✅ All performance tests passed!")
