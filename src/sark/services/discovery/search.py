"""Search and filtering utilities for MCP server discovery.

This module provides advanced search and filtering capabilities for
querying MCP servers with support for full-text search and multiple filters.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import Select, and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from sark.models.mcp_server import MCPServer, SensitivityLevel, ServerStatus

logger = structlog.get_logger()


class ServerSearchFilter:
    """Search and filter builder for MCP servers.

    Provides methods to build complex queries with multiple filters
    and full-text search capabilities.
    """

    def __init__(self, query: Select) -> None:
        """Initialize search filter with base query.

        Args:
            query: Base SQLAlchemy query to build upon
        """
        self.query = query
        self._filters: list[Any] = []

    def with_status(self, status: ServerStatus | list[ServerStatus] | None) -> "ServerSearchFilter":
        """Filter by server status.

        Args:
            status: Single status or list of statuses to filter by

        Returns:
            Self for method chaining
        """
        if status is None:
            return self

        if isinstance(status, list):
            if status:  # Non-empty list
                self._filters.append(MCPServer.status.in_(status))
        else:
            self._filters.append(MCPServer.status == status)

        return self

    def with_sensitivity(
        self, sensitivity: SensitivityLevel | list[SensitivityLevel] | None
    ) -> "ServerSearchFilter":
        """Filter by sensitivity level.

        Args:
            sensitivity: Single sensitivity level or list of levels to filter by

        Returns:
            Self for method chaining
        """
        if sensitivity is None:
            return self

        if isinstance(sensitivity, list):
            if sensitivity:  # Non-empty list
                self._filters.append(MCPServer.sensitivity_level.in_(sensitivity))
        else:
            self._filters.append(MCPServer.sensitivity_level == sensitivity)

        return self

    def with_team(self, team_id: UUID | str | None) -> "ServerSearchFilter":
        """Filter by team ID.

        Args:
            team_id: Team UUID to filter by

        Returns:
            Self for method chaining
        """
        if team_id is None:
            return self

        # Convert string to UUID if needed
        if isinstance(team_id, str):
            try:
                team_id = UUID(team_id)
            except ValueError:
                logger.warning("invalid_team_id", team_id=team_id)
                return self

        self._filters.append(MCPServer.team_id == team_id)
        return self

    def with_owner(self, owner_id: UUID | str | None) -> "ServerSearchFilter":
        """Filter by owner ID.

        Args:
            owner_id: Owner UUID to filter by

        Returns:
            Self for method chaining
        """
        if owner_id is None:
            return self

        # Convert string to UUID if needed
        if isinstance(owner_id, str):
            try:
                owner_id = UUID(owner_id)
            except ValueError:
                logger.warning("invalid_owner_id", owner_id=owner_id)
                return self

        self._filters.append(MCPServer.owner_id == owner_id)
        return self

    def with_tags(
        self, tags: list[str] | str | None, match_all: bool = False
    ) -> "ServerSearchFilter":
        """Filter by tags.

        Args:
            tags: Single tag or list of tags to filter by
            match_all: If True, server must have ALL tags. If False, ANY tag matches.

        Returns:
            Self for method chaining
        """
        if tags is None:
            return self

        # Normalize to list
        if isinstance(tags, str):
            tags = [tags]

        if not tags:  # Empty list
            return self

        if match_all:
            # Server must contain all tags
            # PostgreSQL: tags @> '["tag1", "tag2"]'::jsonb
            for tag in tags:
                self._filters.append(MCPServer.tags.contains([tag]))
        else:
            # Server must contain at least one tag
            # PostgreSQL: tags && '["tag1", "tag2"]'::jsonb (overlaps)
            tag_conditions = [MCPServer.tags.contains([tag]) for tag in tags]
            if tag_conditions:
                self._filters.append(or_(*tag_conditions))

        return self

    def with_search(self, search_query: str | None) -> "ServerSearchFilter":
        """Filter by full-text search on name and description.

        Performs case-insensitive search on server name and description fields.

        Args:
            search_query: Search query string

        Returns:
            Self for method chaining
        """
        if not search_query or not search_query.strip():
            return self

        # Clean up search query
        search_term = f"%{search_query.strip()}%"

        # Case-insensitive LIKE search on name and description
        search_conditions = [
            func.lower(MCPServer.name).like(func.lower(search_term)),
        ]

        # Include description if it exists
        search_conditions.append(func.lower(MCPServer.description).like(func.lower(search_term)))

        self._filters.append(or_(*search_conditions))
        return self

    def build(self) -> Select:
        """Build final query with all filters applied.

        Returns:
            SQLAlchemy Select query with all filters
        """
        if self._filters:
            self.query = self.query.where(and_(*self._filters))

        return self.query


class ServerSearchService:
    """Service for searching and filtering MCP servers."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize search service.

        Args:
            db: Database session
        """
        self.db = db

    def search_servers(
        self,
        query: Select,
        status: ServerStatus | list[ServerStatus] | None = None,
        sensitivity: SensitivityLevel | list[SensitivityLevel] | None = None,
        team_id: UUID | str | None = None,
        owner_id: UUID | str | None = None,
        tags: list[str] | str | None = None,
        match_all_tags: bool = False,
        search: str | None = None,
    ) -> Select:
        """Apply search and filter criteria to query.

        Args:
            query: Base query to filter
            status: Filter by server status (single or list)
            sensitivity: Filter by sensitivity level (single or list)
            team_id: Filter by team UUID
            owner_id: Filter by owner UUID
            tags: Filter by tags (single or list)
            match_all_tags: If True, match ALL tags; if False, match ANY tag
            search: Full-text search query

        Returns:
            Filtered SQLAlchemy query
        """
        filter_builder = ServerSearchFilter(query)

        filtered_query = (
            filter_builder.with_status(status)
            .with_sensitivity(sensitivity)
            .with_team(team_id)
            .with_owner(owner_id)
            .with_tags(tags, match_all=match_all_tags)
            .with_search(search)
            .build()
        )

        return filtered_query


def parse_status_filter(status_str: str | None) -> ServerStatus | None:
    """Parse status string to ServerStatus enum.

    Args:
        status_str: Status string from query parameter

    Returns:
        ServerStatus enum or None if invalid
    """
    if not status_str:
        return None

    try:
        return ServerStatus(status_str.lower())
    except ValueError:
        logger.warning("invalid_status_filter", status=status_str)
        return None


def parse_status_list(status_list: str | None) -> list[ServerStatus] | None:
    """Parse comma-separated status strings to list of ServerStatus enums.

    Args:
        status_list: Comma-separated status strings

    Returns:
        List of ServerStatus enums or None
    """
    if not status_list:
        return None

    statuses = []
    for status_str in status_list.split(","):
        status = parse_status_filter(status_str.strip())
        if status:
            statuses.append(status)

    return statuses if statuses else None


def parse_sensitivity_filter(sensitivity_str: str | None) -> SensitivityLevel | None:
    """Parse sensitivity string to SensitivityLevel enum.

    Args:
        sensitivity_str: Sensitivity string from query parameter

    Returns:
        SensitivityLevel enum or None if invalid
    """
    if not sensitivity_str:
        return None

    try:
        return SensitivityLevel(sensitivity_str.lower())
    except ValueError:
        logger.warning("invalid_sensitivity_filter", sensitivity=sensitivity_str)
        return None


def parse_sensitivity_list(sensitivity_list: str | None) -> list[SensitivityLevel] | None:
    """Parse comma-separated sensitivity strings to list of SensitivityLevel enums.

    Args:
        sensitivity_list: Comma-separated sensitivity strings

    Returns:
        List of SensitivityLevel enums or None
    """
    if not sensitivity_list:
        return None

    levels = []
    for sensitivity_str in sensitivity_list.split(","):
        level = parse_sensitivity_filter(sensitivity_str.strip())
        if level:
            levels.append(level)

    return levels if levels else None


def parse_tags_filter(tags_str: str | None) -> list[str] | None:
    """Parse comma-separated tags string to list.

    Args:
        tags_str: Comma-separated tags string

    Returns:
        List of tags or None
    """
    if not tags_str:
        return None

    tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]
    return tags if tags else None
