"""Tests for search and filtering utilities."""

from uuid import uuid4

import pytest
from sqlalchemy import select

from sark.models.mcp_server import MCPServer, SensitivityLevel, ServerStatus
from sark.services.discovery.search import (
    ServerSearchFilter,
    ServerSearchService,
    parse_sensitivity_filter,
    parse_sensitivity_list,
    parse_status_filter,
    parse_status_list,
    parse_tags_filter,
)


class TestServerSearchFilter:
    """Test ServerSearchFilter class."""

    def test_empty_filter(self) -> None:
        """Test filter with no conditions."""
        base_query = select(MCPServer)
        filter_builder = ServerSearchFilter(base_query)

        result = filter_builder.build()

        # Should return query unchanged
        assert result is not None

    def test_status_filter_single(self) -> None:
        """Test filtering by single status."""
        base_query = select(MCPServer)
        filter_builder = ServerSearchFilter(base_query)

        result = filter_builder.with_status(ServerStatus.ACTIVE).build()

        assert result is not None

    def test_status_filter_list(self) -> None:
        """Test filtering by multiple statuses."""
        base_query = select(MCPServer)
        filter_builder = ServerSearchFilter(base_query)

        result = filter_builder.with_status([ServerStatus.ACTIVE, ServerStatus.REGISTERED]).build()

        assert result is not None

    def test_status_filter_empty_list(self) -> None:
        """Test filtering with empty status list."""
        base_query = select(MCPServer)
        filter_builder = ServerSearchFilter(base_query)

        result = filter_builder.with_status([]).build()

        assert result is not None

    def test_status_filter_none(self) -> None:
        """Test filtering with None status."""
        base_query = select(MCPServer)
        filter_builder = ServerSearchFilter(base_query)

        result = filter_builder.with_status(None).build()

        assert result is not None

    def test_sensitivity_filter_single(self) -> None:
        """Test filtering by single sensitivity level."""
        base_query = select(MCPServer)
        filter_builder = ServerSearchFilter(base_query)

        result = filter_builder.with_sensitivity(SensitivityLevel.HIGH).build()

        assert result is not None

    def test_sensitivity_filter_list(self) -> None:
        """Test filtering by multiple sensitivity levels."""
        base_query = select(MCPServer)
        filter_builder = ServerSearchFilter(base_query)

        result = filter_builder.with_sensitivity(
            [SensitivityLevel.HIGH, SensitivityLevel.CRITICAL]
        ).build()

        assert result is not None

    def test_team_filter_uuid(self) -> None:
        """Test filtering by team UUID."""
        base_query = select(MCPServer)
        filter_builder = ServerSearchFilter(base_query)

        test_uuid = uuid4()
        result = filter_builder.with_team(test_uuid).build()

        assert result is not None

    def test_team_filter_string(self) -> None:
        """Test filtering by team UUID as string."""
        base_query = select(MCPServer)
        filter_builder = ServerSearchFilter(base_query)

        test_uuid = str(uuid4())
        result = filter_builder.with_team(test_uuid).build()

        assert result is not None

    def test_team_filter_invalid_string(self) -> None:
        """Test filtering with invalid team UUID string."""
        base_query = select(MCPServer)
        filter_builder = ServerSearchFilter(base_query)

        result = filter_builder.with_team("invalid-uuid").build()

        assert result is not None

    def test_owner_filter_uuid(self) -> None:
        """Test filtering by owner UUID."""
        base_query = select(MCPServer)
        filter_builder = ServerSearchFilter(base_query)

        test_uuid = uuid4()
        result = filter_builder.with_owner(test_uuid).build()

        assert result is not None

    def test_tags_filter_single_string(self) -> None:
        """Test filtering by single tag as string."""
        base_query = select(MCPServer)
        filter_builder = ServerSearchFilter(base_query)

        result = filter_builder.with_tags("production").build()

        assert result is not None

    def test_tags_filter_list(self) -> None:
        """Test filtering by list of tags."""
        base_query = select(MCPServer)
        filter_builder = ServerSearchFilter(base_query)

        result = filter_builder.with_tags(["production", "critical"]).build()

        assert result is not None

    def test_tags_filter_match_all(self) -> None:
        """Test filtering by tags with match_all=True."""
        base_query = select(MCPServer)
        filter_builder = ServerSearchFilter(base_query)

        result = filter_builder.with_tags(["production", "critical"], match_all=True).build()

        assert result is not None

    def test_tags_filter_empty_list(self) -> None:
        """Test filtering with empty tags list."""
        base_query = select(MCPServer)
        filter_builder = ServerSearchFilter(base_query)

        result = filter_builder.with_tags([]).build()

        assert result is not None

    def test_search_filter(self) -> None:
        """Test full-text search filter."""
        base_query = select(MCPServer)
        filter_builder = ServerSearchFilter(base_query)

        result = filter_builder.with_search("analytics").build()

        assert result is not None

    def test_search_filter_empty(self) -> None:
        """Test full-text search with empty string."""
        base_query = select(MCPServer)
        filter_builder = ServerSearchFilter(base_query)

        result = filter_builder.with_search("").build()

        assert result is not None

    def test_search_filter_whitespace(self) -> None:
        """Test full-text search with whitespace only."""
        base_query = select(MCPServer)
        filter_builder = ServerSearchFilter(base_query)

        result = filter_builder.with_search("   ").build()

        assert result is not None

    def test_combined_filters(self) -> None:
        """Test combining multiple filters."""
        base_query = select(MCPServer)
        filter_builder = ServerSearchFilter(base_query)

        result = (
            filter_builder.with_status(ServerStatus.ACTIVE)
            .with_sensitivity(SensitivityLevel.HIGH)
            .with_team(uuid4())
            .with_tags(["production"])
            .with_search("analytics")
            .build()
        )

        assert result is not None

    def test_method_chaining(self) -> None:
        """Test that methods return self for chaining."""
        base_query = select(MCPServer)
        filter_builder = ServerSearchFilter(base_query)

        # All methods should return self
        assert isinstance(filter_builder.with_status(ServerStatus.ACTIVE), ServerSearchFilter)
        assert isinstance(
            filter_builder.with_sensitivity(SensitivityLevel.HIGH), ServerSearchFilter
        )
        assert isinstance(filter_builder.with_team(uuid4()), ServerSearchFilter)
        assert isinstance(filter_builder.with_owner(uuid4()), ServerSearchFilter)
        assert isinstance(filter_builder.with_tags(["test"]), ServerSearchFilter)
        assert isinstance(filter_builder.with_search("test"), ServerSearchFilter)


class TestServerSearchService:
    """Test ServerSearchService class."""

    def test_search_servers_no_filters(self) -> None:
        """Test search with no filters applied."""
        from unittest.mock import MagicMock

        mock_db = MagicMock()
        service = ServerSearchService(mock_db)

        base_query = select(MCPServer)
        result = service.search_servers(base_query)

        assert result is not None

    def test_search_servers_all_filters(self) -> None:
        """Test search with all filters applied."""
        from unittest.mock import MagicMock

        mock_db = MagicMock()
        service = ServerSearchService(mock_db)

        base_query = select(MCPServer)
        result = service.search_servers(
            base_query,
            status=ServerStatus.ACTIVE,
            sensitivity=SensitivityLevel.HIGH,
            team_id=uuid4(),
            owner_id=uuid4(),
            tags=["production", "critical"],
            match_all_tags=True,
            search="analytics",
        )

        assert result is not None


class TestParserFunctions:
    """Test parsing utility functions."""

    def test_parse_status_filter_valid(self) -> None:
        """Test parsing valid status string."""
        result = parse_status_filter("active")
        assert result == ServerStatus.ACTIVE

    def test_parse_status_filter_uppercase(self) -> None:
        """Test parsing uppercase status string."""
        result = parse_status_filter("ACTIVE")
        assert result == ServerStatus.ACTIVE

    def test_parse_status_filter_mixed_case(self) -> None:
        """Test parsing mixed case status string."""
        result = parse_status_filter("Active")
        assert result == ServerStatus.ACTIVE

    def test_parse_status_filter_invalid(self) -> None:
        """Test parsing invalid status string."""
        result = parse_status_filter("invalid_status")
        assert result is None

    def test_parse_status_filter_none(self) -> None:
        """Test parsing None status."""
        result = parse_status_filter(None)
        assert result is None

    def test_parse_status_list_single(self) -> None:
        """Test parsing single status in list."""
        result = parse_status_list("active")
        assert result == [ServerStatus.ACTIVE]

    def test_parse_status_list_multiple(self) -> None:
        """Test parsing multiple statuses."""
        result = parse_status_list("active,registered,inactive")
        assert len(result) == 3
        assert ServerStatus.ACTIVE in result
        assert ServerStatus.REGISTERED in result
        assert ServerStatus.INACTIVE in result

    def test_parse_status_list_with_spaces(self) -> None:
        """Test parsing status list with spaces."""
        result = parse_status_list("active, registered, inactive")
        assert len(result) == 3

    def test_parse_status_list_with_invalid(self) -> None:
        """Test parsing status list with some invalid values."""
        result = parse_status_list("active,invalid,registered")
        assert len(result) == 2
        assert ServerStatus.ACTIVE in result
        assert ServerStatus.REGISTERED in result

    def test_parse_status_list_all_invalid(self) -> None:
        """Test parsing status list with all invalid values."""
        result = parse_status_list("invalid1,invalid2")
        assert result is None

    def test_parse_status_list_none(self) -> None:
        """Test parsing None status list."""
        result = parse_status_list(None)
        assert result is None

    def test_parse_status_list_empty(self) -> None:
        """Test parsing empty status list."""
        result = parse_status_list("")
        assert result is None

    def test_parse_sensitivity_filter_valid(self) -> None:
        """Test parsing valid sensitivity string."""
        result = parse_sensitivity_filter("high")
        assert result == SensitivityLevel.HIGH

    def test_parse_sensitivity_filter_invalid(self) -> None:
        """Test parsing invalid sensitivity string."""
        result = parse_sensitivity_filter("invalid")
        assert result is None

    def test_parse_sensitivity_list_single(self) -> None:
        """Test parsing single sensitivity in list."""
        result = parse_sensitivity_list("high")
        assert result == [SensitivityLevel.HIGH]

    def test_parse_sensitivity_list_multiple(self) -> None:
        """Test parsing multiple sensitivities."""
        result = parse_sensitivity_list("high,critical,medium")
        assert len(result) == 3

    def test_parse_tags_filter_single(self) -> None:
        """Test parsing single tag."""
        result = parse_tags_filter("production")
        assert result == ["production"]

    def test_parse_tags_filter_multiple(self) -> None:
        """Test parsing multiple tags."""
        result = parse_tags_filter("production,critical,monitoring")
        assert len(result) == 3
        assert "production" in result
        assert "critical" in result
        assert "monitoring" in result

    def test_parse_tags_filter_with_spaces(self) -> None:
        """Test parsing tags with spaces."""
        result = parse_tags_filter("production, critical, monitoring")
        assert len(result) == 3

    def test_parse_tags_filter_empty(self) -> None:
        """Test parsing empty tags string."""
        result = parse_tags_filter("")
        assert result is None

    def test_parse_tags_filter_none(self) -> None:
        """Test parsing None tags."""
        result = parse_tags_filter(None)
        assert result is None

    def test_parse_tags_filter_only_commas(self) -> None:
        """Test parsing tags with only commas."""
        result = parse_tags_filter(",,,")
        assert result is None

    def test_parse_tags_filter_mixed_empty(self) -> None:
        """Test parsing tags with some empty values."""
        result = parse_tags_filter("production,,critical, ,monitoring")
        assert len(result) == 3
        assert "production" in result
        assert "critical" in result
        assert "monitoring" in result
