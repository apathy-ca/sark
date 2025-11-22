"""Unit tests for Server Search and Filtering."""

from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Select, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

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


@pytest.fixture
def base_query():
    """Base SQLAlchemy query."""
    return select(MCPServer)


@pytest.fixture
def mock_db():
    """Mock database session."""
    return MagicMock(spec=AsyncSession)


class TestServerSearchFilter:
    """Test ServerSearchFilter builder."""

    def test_filter_initialization(self, base_query):
        """Test filter initialization."""
        filter_builder = ServerSearchFilter(base_query)
        assert filter_builder.query is not None
        assert filter_builder._filters == []

    def test_with_status_single(self, base_query):
        """Test filtering by single status."""
        filter_builder = ServerSearchFilter(base_query)
        result = filter_builder.with_status(ServerStatus.ACTIVE)

        assert result is filter_builder  # Method chaining
        assert len(filter_builder._filters) == 1

    def test_with_status_list(self, base_query):
        """Test filtering by multiple statuses."""
        filter_builder = ServerSearchFilter(base_query)
        statuses = [ServerStatus.ACTIVE, ServerStatus.REGISTERED]
        result = filter_builder.with_status(statuses)

        assert result is filter_builder
        assert len(filter_builder._filters) == 1

    def test_with_status_none(self, base_query):
        """Test with None status (should not add filter)."""
        filter_builder = ServerSearchFilter(base_query)
        result = filter_builder.with_status(None)

        assert result is filter_builder
        assert len(filter_builder._filters) == 0

    def test_with_status_empty_list(self, base_query):
        """Test with empty status list (should not add filter)."""
        filter_builder = ServerSearchFilter(base_query)
        result = filter_builder.with_status([])

        assert result is filter_builder
        assert len(filter_builder._filters) == 0

    def test_with_sensitivity_single(self, base_query):
        """Test filtering by single sensitivity level."""
        filter_builder = ServerSearchFilter(base_query)
        result = filter_builder.with_sensitivity(SensitivityLevel.HIGH)

        assert result is filter_builder
        assert len(filter_builder._filters) == 1

    def test_with_sensitivity_list(self, base_query):
        """Test filtering by multiple sensitivity levels."""
        filter_builder = ServerSearchFilter(base_query)
        levels = [SensitivityLevel.HIGH, SensitivityLevel.CRITICAL]
        result = filter_builder.with_sensitivity(levels)

        assert result is filter_builder
        assert len(filter_builder._filters) == 1

    def test_with_sensitivity_none(self, base_query):
        """Test with None sensitivity (should not add filter)."""
        filter_builder = ServerSearchFilter(base_query)
        result = filter_builder.with_sensitivity(None)

        assert result is filter_builder
        assert len(filter_builder._filters) == 0

    def test_with_team_uuid(self, base_query):
        """Test filtering by team UUID."""
        filter_builder = ServerSearchFilter(base_query)
        team_id = uuid4()
        result = filter_builder.with_team(team_id)

        assert result is filter_builder
        assert len(filter_builder._filters) == 1

    def test_with_team_string_uuid(self, base_query):
        """Test filtering by team UUID as string."""
        filter_builder = ServerSearchFilter(base_query)
        team_id = str(uuid4())
        result = filter_builder.with_team(team_id)

        assert result is filter_builder
        assert len(filter_builder._filters) == 1

    def test_with_team_invalid_uuid(self, base_query):
        """Test with invalid team UUID string (should not add filter)."""
        filter_builder = ServerSearchFilter(base_query)
        result = filter_builder.with_team("invalid-uuid")

        assert result is filter_builder
        assert len(filter_builder._filters) == 0

    def test_with_team_none(self, base_query):
        """Test with None team (should not add filter)."""
        filter_builder = ServerSearchFilter(base_query)
        result = filter_builder.with_team(None)

        assert result is filter_builder
        assert len(filter_builder._filters) == 0

    def test_with_owner_uuid(self, base_query):
        """Test filtering by owner UUID."""
        filter_builder = ServerSearchFilter(base_query)
        owner_id = uuid4()
        result = filter_builder.with_owner(owner_id)

        assert result is filter_builder
        assert len(filter_builder._filters) == 1

    def test_with_owner_string_uuid(self, base_query):
        """Test filtering by owner UUID as string."""
        filter_builder = ServerSearchFilter(base_query)
        owner_id = str(uuid4())
        result = filter_builder.with_owner(owner_id)

        assert result is filter_builder
        assert len(filter_builder._filters) == 1

    def test_with_owner_invalid_uuid(self, base_query):
        """Test with invalid owner UUID string (should not add filter)."""
        filter_builder = ServerSearchFilter(base_query)
        result = filter_builder.with_owner("not-a-uuid")

        assert result is filter_builder
        assert len(filter_builder._filters) == 0

    def test_with_tags_single_string(self, base_query):
        """Test filtering by single tag as string."""
        filter_builder = ServerSearchFilter(base_query)
        result = filter_builder.with_tags("production")

        assert result is filter_builder
        assert len(filter_builder._filters) == 1

    def test_with_tags_list_match_any(self, base_query):
        """Test filtering by multiple tags with ANY matching."""
        filter_builder = ServerSearchFilter(base_query)
        tags = ["production", "critical"]
        result = filter_builder.with_tags(tags, match_all=False)

        assert result is filter_builder
        assert len(filter_builder._filters) == 1

    def test_with_tags_list_match_all(self, base_query):
        """Test filtering by multiple tags with ALL matching."""
        filter_builder = ServerSearchFilter(base_query)
        tags = ["production", "critical", "analytics"]
        result = filter_builder.with_tags(tags, match_all=True)

        assert result is filter_builder
        # Should add one filter per tag when match_all=True
        assert len(filter_builder._filters) == 3

    def test_with_tags_none(self, base_query):
        """Test with None tags (should not add filter)."""
        filter_builder = ServerSearchFilter(base_query)
        result = filter_builder.with_tags(None)

        assert result is filter_builder
        assert len(filter_builder._filters) == 0

    def test_with_tags_empty_list(self, base_query):
        """Test with empty tags list (should not add filter)."""
        filter_builder = ServerSearchFilter(base_query)
        result = filter_builder.with_tags([])

        assert result is filter_builder
        assert len(filter_builder._filters) == 0

    def test_with_search_query(self, base_query):
        """Test full-text search."""
        filter_builder = ServerSearchFilter(base_query)
        result = filter_builder.with_search("analytics server")

        assert result is filter_builder
        assert len(filter_builder._filters) == 1

    def test_with_search_empty_string(self, base_query):
        """Test with empty search string (should not add filter)."""
        filter_builder = ServerSearchFilter(base_query)
        result = filter_builder.with_search("")

        assert result is filter_builder
        assert len(filter_builder._filters) == 0

    def test_with_search_whitespace_only(self, base_query):
        """Test with whitespace-only search (should not add filter)."""
        filter_builder = ServerSearchFilter(base_query)
        result = filter_builder.with_search("   ")

        assert result is filter_builder
        assert len(filter_builder._filters) == 0

    def test_with_search_none(self, base_query):
        """Test with None search (should not add filter)."""
        filter_builder = ServerSearchFilter(base_query)
        result = filter_builder.with_search(None)

        assert result is filter_builder
        assert len(filter_builder._filters) == 0

    def test_build_no_filters(self, base_query):
        """Test building query with no filters."""
        filter_builder = ServerSearchFilter(base_query)
        query = filter_builder.build()

        # Should return original query
        assert query is not None

    def test_build_with_filters(self, base_query):
        """Test building query with filters."""
        filter_builder = ServerSearchFilter(base_query)
        filter_builder.with_status(ServerStatus.ACTIVE)
        filter_builder.with_sensitivity(SensitivityLevel.HIGH)
        query = filter_builder.build()

        assert query is not None
        assert len(filter_builder._filters) == 2

    def test_method_chaining(self, base_query):
        """Test method chaining for fluent interface."""
        filter_builder = ServerSearchFilter(base_query)

        result = (
            filter_builder.with_status(ServerStatus.ACTIVE)
            .with_sensitivity(SensitivityLevel.HIGH)
            .with_team(uuid4())
            .with_owner(uuid4())
            .with_tags(["production"])
            .with_search("analytics")
        )

        assert result is filter_builder
        assert len(filter_builder._filters) == 6


class TestServerSearchService:
    """Test ServerSearchService."""

    def test_service_initialization(self, mock_db):
        """Test service initialization."""
        service = ServerSearchService(mock_db)
        assert service.db is mock_db

    def test_search_servers_no_filters(self, mock_db, base_query):
        """Test search with no filters."""
        service = ServerSearchService(mock_db)
        result = service.search_servers(base_query)

        assert result is not None

    def test_search_servers_with_status(self, mock_db, base_query):
        """Test search with status filter."""
        service = ServerSearchService(mock_db)
        result = service.search_servers(base_query, status=ServerStatus.ACTIVE)

        assert result is not None

    def test_search_servers_with_multiple_statuses(self, mock_db, base_query):
        """Test search with multiple status filters."""
        service = ServerSearchService(mock_db)
        result = service.search_servers(
            base_query,
            status=[ServerStatus.ACTIVE, ServerStatus.REGISTERED],
        )

        assert result is not None

    def test_search_servers_with_sensitivity(self, mock_db, base_query):
        """Test search with sensitivity filter."""
        service = ServerSearchService(mock_db)
        result = service.search_servers(
            base_query,
            sensitivity=SensitivityLevel.HIGH,
        )

        assert result is not None

    def test_search_servers_with_team_and_owner(self, mock_db, base_query):
        """Test search with team and owner filters."""
        service = ServerSearchService(mock_db)
        team_id = uuid4()
        owner_id = uuid4()

        result = service.search_servers(
            base_query,
            team_id=team_id,
            owner_id=owner_id,
        )

        assert result is not None

    def test_search_servers_with_tags_any(self, mock_db, base_query):
        """Test search with tags (match any)."""
        service = ServerSearchService(mock_db)
        result = service.search_servers(
            base_query,
            tags=["production", "staging"],
            match_all_tags=False,
        )

        assert result is not None

    def test_search_servers_with_tags_all(self, mock_db, base_query):
        """Test search with tags (match all)."""
        service = ServerSearchService(mock_db)
        result = service.search_servers(
            base_query,
            tags=["production", "critical"],
            match_all_tags=True,
        )

        assert result is not None

    def test_search_servers_with_search_query(self, mock_db, base_query):
        """Test search with full-text search."""
        service = ServerSearchService(mock_db)
        result = service.search_servers(
            base_query,
            search="analytics server",
        )

        assert result is not None

    def test_search_servers_with_all_filters(self, mock_db, base_query):
        """Test search with all filters combined."""
        service = ServerSearchService(mock_db)
        result = service.search_servers(
            base_query,
            status=ServerStatus.ACTIVE,
            sensitivity=SensitivityLevel.HIGH,
            team_id=uuid4(),
            owner_id=uuid4(),
            tags=["production"],
            match_all_tags=True,
            search="analytics",
        )

        assert result is not None


class TestParseStatusFilter:
    """Test parse_status_filter utility."""

    def test_parse_valid_status(self):
        """Test parsing valid status string."""
        result = parse_status_filter("active")
        assert result == ServerStatus.ACTIVE

    def test_parse_registered_status(self):
        """Test parsing registered status."""
        result = parse_status_filter("registered")
        assert result == ServerStatus.REGISTERED

    def test_parse_uppercase_status(self):
        """Test parsing uppercase status string."""
        result = parse_status_filter("ACTIVE")
        assert result == ServerStatus.ACTIVE

    def test_parse_mixed_case_status(self):
        """Test parsing mixed case status string."""
        result = parse_status_filter("AcTiVe")
        assert result == ServerStatus.ACTIVE

    def test_parse_invalid_status(self):
        """Test parsing invalid status string."""
        result = parse_status_filter("invalid")
        assert result is None

    def test_parse_none_status(self):
        """Test parsing None status."""
        result = parse_status_filter(None)
        assert result is None

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        result = parse_status_filter("")
        assert result is None


class TestParseStatusList:
    """Test parse_status_list utility."""

    def test_parse_single_status(self):
        """Test parsing single status in list."""
        result = parse_status_list("active")
        assert result == [ServerStatus.ACTIVE]

    def test_parse_multiple_statuses(self):
        """Test parsing multiple statuses."""
        result = parse_status_list("active,registered,inactive")
        assert len(result) == 3
        assert ServerStatus.ACTIVE in result
        assert ServerStatus.REGISTERED in result
        assert ServerStatus.INACTIVE in result

    def test_parse_statuses_with_whitespace(self):
        """Test parsing statuses with extra whitespace."""
        result = parse_status_list("active , registered , inactive")
        assert len(result) == 3

    def test_parse_statuses_with_invalid(self):
        """Test parsing list with some invalid statuses."""
        result = parse_status_list("active,invalid,registered")
        assert len(result) == 2
        assert ServerStatus.ACTIVE in result
        assert ServerStatus.REGISTERED in result

    def test_parse_all_invalid_statuses(self):
        """Test parsing list with all invalid statuses."""
        result = parse_status_list("invalid1,invalid2")
        assert result is None

    def test_parse_none_list(self):
        """Test parsing None list."""
        result = parse_status_list(None)
        assert result is None

    def test_parse_empty_string_list(self):
        """Test parsing empty string list."""
        result = parse_status_list("")
        assert result is None


class TestParseSensitivityFilter:
    """Test parse_sensitivity_filter utility."""

    def test_parse_valid_sensitivity(self):
        """Test parsing valid sensitivity string."""
        result = parse_sensitivity_filter("high")
        assert result == SensitivityLevel.HIGH

    def test_parse_critical_sensitivity(self):
        """Test parsing critical sensitivity."""
        result = parse_sensitivity_filter("critical")
        assert result == SensitivityLevel.CRITICAL

    def test_parse_uppercase_sensitivity(self):
        """Test parsing uppercase sensitivity."""
        result = parse_sensitivity_filter("HIGH")
        assert result == SensitivityLevel.HIGH

    def test_parse_mixed_case_sensitivity(self):
        """Test parsing mixed case sensitivity."""
        result = parse_sensitivity_filter("CrItIcAl")
        assert result == SensitivityLevel.CRITICAL

    def test_parse_invalid_sensitivity(self):
        """Test parsing invalid sensitivity."""
        result = parse_sensitivity_filter("invalid")
        assert result is None

    def test_parse_none_sensitivity(self):
        """Test parsing None sensitivity."""
        result = parse_sensitivity_filter(None)
        assert result is None


class TestParseSensitivityList:
    """Test parse_sensitivity_list utility."""

    def test_parse_single_sensitivity(self):
        """Test parsing single sensitivity in list."""
        result = parse_sensitivity_list("high")
        assert result == [SensitivityLevel.HIGH]

    def test_parse_multiple_sensitivities(self):
        """Test parsing multiple sensitivities."""
        result = parse_sensitivity_list("low,medium,high,critical")
        assert len(result) == 4
        assert SensitivityLevel.LOW in result
        assert SensitivityLevel.HIGH in result
        assert SensitivityLevel.CRITICAL in result

    def test_parse_sensitivities_with_whitespace(self):
        """Test parsing sensitivities with whitespace."""
        result = parse_sensitivity_list("high , critical , medium")
        assert len(result) == 3

    def test_parse_sensitivities_with_invalid(self):
        """Test parsing list with invalid sensitivities."""
        result = parse_sensitivity_list("high,invalid,low")
        assert len(result) == 2

    def test_parse_all_invalid_sensitivities(self):
        """Test parsing all invalid sensitivities."""
        result = parse_sensitivity_list("invalid1,invalid2")
        assert result is None

    def test_parse_none_sensitivity_list(self):
        """Test parsing None sensitivity list."""
        result = parse_sensitivity_list(None)
        assert result is None


class TestParseTagsFilter:
    """Test parse_tags_filter utility."""

    def test_parse_single_tag(self):
        """Test parsing single tag."""
        result = parse_tags_filter("production")
        assert result == ["production"]

    def test_parse_multiple_tags(self):
        """Test parsing multiple tags."""
        result = parse_tags_filter("production,staging,development")
        assert len(result) == 3
        assert "production" in result
        assert "staging" in result
        assert "development" in result

    def test_parse_tags_with_whitespace(self):
        """Test parsing tags with whitespace."""
        result = parse_tags_filter("production , staging , development")
        assert len(result) == 3
        assert "production" in result

    def test_parse_tags_with_empty_values(self):
        """Test parsing tags with empty values."""
        result = parse_tags_filter("production,,staging,")
        assert len(result) == 2
        assert "production" in result
        assert "staging" in result

    def test_parse_none_tags(self):
        """Test parsing None tags."""
        result = parse_tags_filter(None)
        assert result is None

    def test_parse_empty_string_tags(self):
        """Test parsing empty string tags."""
        result = parse_tags_filter("")
        assert result is None

    def test_parse_all_empty_tags(self):
        """Test parsing all empty tag values."""
        result = parse_tags_filter(",,,")
        assert result is None
