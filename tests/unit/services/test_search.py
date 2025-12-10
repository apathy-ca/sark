"""Comprehensive tests for ServerSearchService and ServerSearchFilter.

This module tests:
- Search filter building with method chaining
- Status, sensitivity, team, owner filtering
- Tag filtering (match all vs match any)
- Full-text search
- Parse helper functions
"""

from unittest.mock import MagicMock
from uuid import UUID, uuid4

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

    def test_initialization(self):
        """Test filter initializes with base query."""
        query = select(MCPServer)
        filter_builder = ServerSearchFilter(query)

        assert filter_builder.query is not None
        assert filter_builder._filters == []

    def test_with_status_single(self):
        """Test filtering by single status."""
        query = select(MCPServer)
        filter_builder = ServerSearchFilter(query)

        result = filter_builder.with_status(ServerStatus.ACTIVE)

        assert result is filter_builder  # Method chaining
        assert len(filter_builder._filters) == 1

    def test_with_status_list(self):
        """Test filtering by list of statuses."""
        query = select(MCPServer)
        filter_builder = ServerSearchFilter(query)

        statuses = [ServerStatus.ACTIVE, ServerStatus.REGISTERED]
        result = filter_builder.with_status(statuses)

        assert len(filter_builder._filters) == 1

    def test_with_status_none(self):
        """Test that None status doesn't add filter."""
        query = select(MCPServer)
        filter_builder = ServerSearchFilter(query)

        result = filter_builder.with_status(None)

        assert len(filter_builder._filters) == 0

    def test_with_status_empty_list(self):
        """Test that empty list doesn't add filter."""
        query = select(MCPServer)
        filter_builder = ServerSearchFilter(query)

        result = filter_builder.with_status([])

        assert len(filter_builder._filters) == 0

    def test_with_sensitivity_single(self):
        """Test filtering by single sensitivity level."""
        query = select(MCPServer)
        filter_builder = ServerSearchFilter(query)

        result = filter_builder.with_sensitivity(SensitivityLevel.HIGH)

        assert len(filter_builder._filters) == 1

    def test_with_sensitivity_list(self):
        """Test filtering by list of sensitivity levels."""
        query = select(MCPServer)
        filter_builder = ServerSearchFilter(query)

        levels = [SensitivityLevel.HIGH, SensitivityLevel.CRITICAL]
        result = filter_builder.with_sensitivity(levels)

        assert len(filter_builder._filters) == 1

    def test_with_team_uuid(self):
        """Test filtering by team UUID."""
        query = select(MCPServer)
        filter_builder = ServerSearchFilter(query)

        team_id = uuid4()
        result = filter_builder.with_team(team_id)

        assert len(filter_builder._filters) == 1

    def test_with_team_string_uuid(self):
        """Test filtering by team UUID as string."""
        query = select(MCPServer)
        filter_builder = ServerSearchFilter(query)

        team_id = str(uuid4())
        result = filter_builder.with_team(team_id)

        assert len(filter_builder._filters) == 1

    def test_with_team_invalid_string(self):
        """Test that invalid team ID string is skipped."""
        query = select(MCPServer)
        filter_builder = ServerSearchFilter(query)

        result = filter_builder.with_team("invalid-uuid")

        assert len(filter_builder._filters) == 0

    def test_with_team_none(self):
        """Test that None team doesn't add filter."""
        query = select(MCPServer)
        filter_builder = ServerSearchFilter(query)

        result = filter_builder.with_team(None)

        assert len(filter_builder._filters) == 0

    def test_with_owner_uuid(self):
        """Test filtering by owner UUID."""
        query = select(MCPServer)
        filter_builder = ServerSearchFilter(query)

        owner_id = uuid4()
        result = filter_builder.with_owner(owner_id)

        assert len(filter_builder._filters) == 1

    def test_with_owner_string_uuid(self):
        """Test filtering by owner UUID as string."""
        query = select(MCPServer)
        filter_builder = ServerSearchFilter(query)

        owner_id = str(uuid4())
        result = filter_builder.with_owner(owner_id)

        assert len(filter_builder._filters) == 1

    def test_with_tags_single_string(self):
        """Test filtering by single tag as string."""
        query = select(MCPServer)
        filter_builder = ServerSearchFilter(query)

        result = filter_builder.with_tags("production")

        assert len(filter_builder._filters) == 1

    def test_with_tags_list_match_any(self):
        """Test filtering by list of tags (match any)."""
        query = select(MCPServer)
        filter_builder = ServerSearchFilter(query)

        tags = ["production", "staging"]
        result = filter_builder.with_tags(tags, match_all=False)

        assert len(filter_builder._filters) == 1

    def test_with_tags_list_match_all(self):
        """Test filtering by list of tags (match all)."""
        query = select(MCPServer)
        filter_builder = ServerSearchFilter(query)

        tags = ["production", "verified"]
        result = filter_builder.with_tags(tags, match_all=True)

        # Each tag adds a separate filter for match_all
        assert len(filter_builder._filters) == 2

    def test_with_tags_none(self):
        """Test that None tags doesn't add filter."""
        query = select(MCPServer)
        filter_builder = ServerSearchFilter(query)

        result = filter_builder.with_tags(None)

        assert len(filter_builder._filters) == 0

    def test_with_tags_empty_list(self):
        """Test that empty list doesn't add filter."""
        query = select(MCPServer)
        filter_builder = ServerSearchFilter(query)

        result = filter_builder.with_tags([])

        assert len(filter_builder._filters) == 0

    def test_with_search(self):
        """Test full-text search filter."""
        query = select(MCPServer)
        filter_builder = ServerSearchFilter(query)

        result = filter_builder.with_search("test server")

        assert len(filter_builder._filters) == 1

    def test_with_search_empty_string(self):
        """Test that empty search string doesn't add filter."""
        query = select(MCPServer)
        filter_builder = ServerSearchFilter(query)

        result = filter_builder.with_search("")

        assert len(filter_builder._filters) == 0

    def test_with_search_whitespace_only(self):
        """Test that whitespace-only search doesn't add filter."""
        query = select(MCPServer)
        filter_builder = ServerSearchFilter(query)

        result = filter_builder.with_search("   ")

        assert len(filter_builder._filters) == 0

    def test_with_search_none(self):
        """Test that None search doesn't add filter."""
        query = select(MCPServer)
        filter_builder = ServerSearchFilter(query)

        result = filter_builder.with_search(None)

        assert len(filter_builder._filters) == 0

    def test_method_chaining(self):
        """Test that filters can be chained together."""
        query = select(MCPServer)
        filter_builder = ServerSearchFilter(query)

        result = (
            filter_builder.with_status(ServerStatus.ACTIVE)
            .with_sensitivity(SensitivityLevel.HIGH)
            .with_team(uuid4())
            .with_tags(["production"])
            .with_search("test")
        )

        assert result is filter_builder
        assert len(filter_builder._filters) == 5

    def test_build(self):
        """Test building final query."""
        query = select(MCPServer)
        filter_builder = ServerSearchFilter(query)

        filter_builder.with_status(ServerStatus.ACTIVE)
        built_query = filter_builder.build()

        assert built_query is not None

    def test_build_no_filters(self):
        """Test building query with no filters."""
        query = select(MCPServer)
        filter_builder = ServerSearchFilter(query)

        built_query = filter_builder.build()

        # Should return original query
        assert built_query is not None


class TestServerSearchService:
    """Test ServerSearchService class."""

    def test_initialization(self):
        """Test service initializes with database session."""
        mock_db = MagicMock()
        service = ServerSearchService(db=mock_db)

        assert service.db == mock_db

    def test_search_servers_with_all_filters(self):
        """Test search with all filter types."""
        mock_db = MagicMock()
        service = ServerSearchService(db=mock_db)

        query = select(MCPServer)
        result = service.search_servers(
            query=query,
            status=ServerStatus.ACTIVE,
            sensitivity=SensitivityLevel.HIGH,
            team_id=uuid4(),
            owner_id=uuid4(),
            tags=["production", "verified"],
            match_all_tags=True,
            search="test server",
        )

        assert result is not None

    def test_search_servers_with_no_filters(self):
        """Test search with no filters."""
        mock_db = MagicMock()
        service = ServerSearchService(db=mock_db)

        query = select(MCPServer)
        result = service.search_servers(query=query)

        assert result is not None

    def test_search_servers_with_status_list(self):
        """Test search with list of statuses."""
        mock_db = MagicMock()
        service = ServerSearchService(db=mock_db)

        query = select(MCPServer)
        statuses = [ServerStatus.ACTIVE, ServerStatus.REGISTERED]
        result = service.search_servers(query=query, status=statuses)

        assert result is not None

    def test_search_servers_with_sensitivity_list(self):
        """Test search with list of sensitivity levels."""
        mock_db = MagicMock()
        service = ServerSearchService(db=mock_db)

        query = select(MCPServer)
        levels = [SensitivityLevel.HIGH, SensitivityLevel.CRITICAL]
        result = service.search_servers(query=query, sensitivity=levels)

        assert result is not None


class TestParseStatusFilter:
    """Test parse_status_filter helper function."""

    def test_parse_valid_status(self):
        """Test parsing valid status string."""
        result = parse_status_filter("active")

        assert result == ServerStatus.ACTIVE

    def test_parse_status_case_insensitive(self):
        """Test that parsing is case insensitive."""
        result = parse_status_filter("ACTIVE")

        assert result == ServerStatus.ACTIVE

    def test_parse_invalid_status(self):
        """Test parsing invalid status returns None."""
        result = parse_status_filter("invalid_status")

        assert result is None

    def test_parse_none_status(self):
        """Test parsing None returns None."""
        result = parse_status_filter(None)

        assert result is None

    def test_parse_empty_string(self):
        """Test parsing empty string returns None."""
        result = parse_status_filter("")

        assert result is None


class TestParseStatusList:
    """Test parse_status_list helper function."""

    def test_parse_valid_status_list(self):
        """Test parsing comma-separated status list."""
        result = parse_status_list("active,registered,decommissioned")

        assert len(result) == 3
        assert ServerStatus.ACTIVE in result
        assert ServerStatus.REGISTERED in result
        assert ServerStatus.DECOMMISSIONED in result

    def test_parse_status_list_with_whitespace(self):
        """Test parsing handles whitespace."""
        result = parse_status_list("active, registered, decommissioned")

        assert len(result) == 3

    def test_parse_single_status(self):
        """Test parsing single status."""
        result = parse_status_list("active")

        assert len(result) == 1
        assert result[0] == ServerStatus.ACTIVE

    def test_parse_invalid_statuses_filtered_out(self):
        """Test that invalid statuses are filtered out."""
        result = parse_status_list("active,invalid,registered")

        assert len(result) == 2
        assert ServerStatus.ACTIVE in result
        assert ServerStatus.REGISTERED in result

    def test_parse_all_invalid_returns_none(self):
        """Test that all invalid statuses returns None."""
        result = parse_status_list("invalid1,invalid2")

        assert result is None

    def test_parse_none_returns_none(self):
        """Test parsing None returns None."""
        result = parse_status_list(None)

        assert result is None


class TestParseSensitivityFilter:
    """Test parse_sensitivity_filter helper function."""

    def test_parse_valid_sensitivity(self):
        """Test parsing valid sensitivity string."""
        result = parse_sensitivity_filter("high")

        assert result == SensitivityLevel.HIGH

    def test_parse_sensitivity_case_insensitive(self):
        """Test that parsing is case insensitive."""
        result = parse_sensitivity_filter("CRITICAL")

        assert result == SensitivityLevel.CRITICAL

    def test_parse_invalid_sensitivity(self):
        """Test parsing invalid sensitivity returns None."""
        result = parse_sensitivity_filter("invalid_level")

        assert result is None

    def test_parse_none_sensitivity(self):
        """Test parsing None returns None."""
        result = parse_sensitivity_filter(None)

        assert result is None


class TestParseSensitivityList:
    """Test parse_sensitivity_list helper function."""

    def test_parse_valid_sensitivity_list(self):
        """Test parsing comma-separated sensitivity list."""
        result = parse_sensitivity_list("low,medium,high,critical")

        assert len(result) == 4
        assert SensitivityLevel.LOW in result
        assert SensitivityLevel.MEDIUM in result
        assert SensitivityLevel.HIGH in result
        assert SensitivityLevel.CRITICAL in result

    def test_parse_sensitivity_list_with_whitespace(self):
        """Test parsing handles whitespace."""
        result = parse_sensitivity_list("low, medium, high")

        assert len(result) == 3

    def test_parse_invalid_filtered_out(self):
        """Test that invalid sensitivities are filtered out."""
        result = parse_sensitivity_list("low,invalid,high")

        assert len(result) == 2
        assert SensitivityLevel.LOW in result
        assert SensitivityLevel.HIGH in result

    def test_parse_all_invalid_returns_none(self):
        """Test that all invalid returns None."""
        result = parse_sensitivity_list("invalid1,invalid2")

        assert result is None


class TestParseTagsFilter:
    """Test parse_tags_filter helper function."""

    def test_parse_valid_tags(self):
        """Test parsing comma-separated tags."""
        result = parse_tags_filter("production,staging,development")

        assert len(result) == 3
        assert "production" in result
        assert "staging" in result
        assert "development" in result

    def test_parse_tags_with_whitespace(self):
        """Test parsing handles whitespace."""
        result = parse_tags_filter("production, staging, development")

        assert len(result) == 3

    def test_parse_single_tag(self):
        """Test parsing single tag."""
        result = parse_tags_filter("production")

        assert result == ["production"]

    def test_parse_empty_tags_filtered_out(self):
        """Test that empty tags are filtered out."""
        result = parse_tags_filter("production,,staging,")

        assert len(result) == 2
        assert "production" in result
        assert "staging" in result

    def test_parse_all_empty_returns_none(self):
        """Test that all empty returns None."""
        result = parse_tags_filter(",,,")

        assert result is None

    def test_parse_none_returns_none(self):
        """Test parsing None returns None."""
        result = parse_tags_filter(None)

        assert result is None

    def test_parse_empty_string_returns_none(self):
        """Test parsing empty string returns None."""
        result = parse_tags_filter("")

        assert result is None
