"""Pagination utilities for API endpoints.

This module provides cursor-based pagination for efficient querying
of large datasets with configurable page sizes.
"""

from base64 import b64decode, b64encode
from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import Select, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

logger = structlog.get_logger()

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Pagination query parameters.

    Args:
        limit: Number of items per page (1-200, default: 50)
        cursor: Opaque cursor for pagination position
        sort_order: Sort order (asc or desc, default: desc)
    """

    limit: int = Field(default=50, ge=1, le=200, description="Items per page")
    cursor: str | None = Field(None, description="Pagination cursor")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="Sort order")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper.

    Args:
        items: List of items in current page
        next_cursor: Cursor for next page (None if last page)
        has_more: Whether more items exist
        total: Total count of items (optional, expensive to compute)
    """

    items: list[T]
    next_cursor: str | None = Field(None, description="Cursor for next page")
    has_more: bool = Field(description="Whether more items exist")
    total: int | None = Field(None, description="Total count (optional)")


class CursorPaginator:
    """Cursor-based pagination helper.

    Uses base64-encoded cursor containing the last item's sort key
    for efficient pagination without offset.
    """

    @staticmethod
    def encode_cursor(value: str | UUID | int | datetime) -> str:
        """Encode a cursor value.

        Args:
            value: Value to encode (UUID, string, int, or datetime)

        Returns:
            Base64-encoded cursor string
        """
        if isinstance(value, (UUID, int)):
            value_str = str(value)
        elif isinstance(value, datetime):
            value_str = value.isoformat()
        else:
            value_str = value

        return b64encode(value_str.encode("utf-8")).decode("utf-8")

    @staticmethod
    def decode_cursor(cursor: str) -> str:
        """Decode a cursor value.

        Args:
            cursor: Base64-encoded cursor string

        Returns:
            Decoded cursor value as string

        Raises:
            ValueError: If cursor is invalid
        """
        try:
            return b64decode(cursor.encode("utf-8")).decode("utf-8")
        except Exception as e:
            logger.warning("invalid_cursor", cursor=cursor, error=str(e))
            raise ValueError("Invalid pagination cursor") from e

    @staticmethod
    async def paginate(
        db: AsyncSession,
        query: Select,
        cursor_column: Any,
        params: PaginationParams,
        count_total: bool = False,
    ) -> tuple[list[Any], str | None, bool, int | None]:
        """Execute paginated query.

        Args:
            db: Database session
            query: Base SQLAlchemy query
            cursor_column: Column to use for cursor (e.g., model.created_at)
            params: Pagination parameters
            count_total: Whether to count total items (expensive)

        Returns:
            Tuple of (items, next_cursor, has_more, total)
        """
        # Apply cursor if provided
        if params.cursor:
            try:
                cursor_value = CursorPaginator.decode_cursor(params.cursor)

                if params.sort_order == "desc":
                    query = query.where(cursor_column < cursor_value)
                else:
                    query = query.where(cursor_column > cursor_value)
            except ValueError:
                # Invalid cursor, ignore and start from beginning
                logger.warning("invalid_cursor_ignored", cursor=params.cursor)

        # Apply sorting
        if params.sort_order == "desc":
            query = query.order_by(desc(cursor_column))
        else:
            query = query.order_by(asc(cursor_column))

        # Fetch limit + 1 to check if more items exist
        query = query.limit(params.limit + 1)

        # Execute query
        result = await db.execute(query)
        items = list(result.scalars().all())

        # Check if more items exist
        has_more = len(items) > params.limit
        if has_more:
            items = items[: params.limit]

        # Generate next cursor
        next_cursor = None
        if has_more and items:
            last_item = items[-1]
            cursor_value = getattr(last_item, cursor_column.name)
            next_cursor = CursorPaginator.encode_cursor(cursor_value)

        # Count total if requested (expensive operation)
        total = None
        if count_total:
            # Import here to avoid circular dependency
            from sqlalchemy import func, select

            count_query = select(func.count()).select_from(query.froms[0])
            count_result = await db.execute(count_query)
            total = count_result.scalar()

        return items, next_cursor, has_more, total
