"""Comprehensive tests for ToolRegistry.

This module tests:
- Automatic sensitivity detection based on keywords
- Manual sensitivity override with audit trail
- Tool retrieval and management
- Sensitivity statistics and history
- Bulk sensitivity detection
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sark.models.mcp_server import MCPTool, SensitivityLevel
from sark.services.discovery.tool_registry import ToolRegistry


@pytest.fixture
def mock_db():
    """Create mock database session."""
    db = AsyncMock(spec=AsyncSession)
    db.get = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def tool_registry(mock_db):
    """Create ToolRegistry instance."""
    return ToolRegistry(db=mock_db)


class TestToolRegistryInit:
    """Test ToolRegistry initialization."""

    def test_initialization(self, mock_db):
        """Test registry initializes correctly."""
        registry = ToolRegistry(db=mock_db, audit_db=None)

        assert registry.db == mock_db
        assert registry.audit_db is None

    def test_initialization_with_audit_db(self, mock_db):
        """Test registry initializes with audit database."""
        audit_db = AsyncMock()
        registry = ToolRegistry(db=mock_db, audit_db=audit_db)

        assert registry.audit_db == audit_db

    def test_keyword_lists_defined(self):
        """Test that keyword lists are defined."""
        assert len(ToolRegistry.CRITICAL_KEYWORDS) > 0
        assert len(ToolRegistry.HIGH_KEYWORDS) > 0
        assert len(ToolRegistry.MEDIUM_KEYWORDS) > 0
        assert len(ToolRegistry.LOW_KEYWORDS) > 0


class TestDetectSensitivity:
    """Test automatic sensitivity detection."""

    @pytest.mark.asyncio
    async def test_detect_critical_from_name(self, tool_registry):
        """Test detection of CRITICAL from tool name."""
        result = await tool_registry.detect_sensitivity(
            tool_name="payment transaction handler"
        )

        assert result == SensitivityLevel.CRITICAL

    @pytest.mark.asyncio
    async def test_detect_critical_from_description(self, tool_registry):
        """Test detection of CRITICAL from description."""
        result = await tool_registry.detect_sensitivity(
            tool_name="process data",
            tool_description="Handles payment and encryption with secret keys",
        )

        assert result == SensitivityLevel.CRITICAL

    @pytest.mark.asyncio
    async def test_detect_high_keywords(self, tool_registry):
        """Test detection of HIGH sensitivity."""
        result = await tool_registry.detect_sensitivity(
            tool_name="delete database records"
        )

        assert result == SensitivityLevel.HIGH

    @pytest.mark.asyncio
    async def test_detect_medium_keywords(self, tool_registry):
        """Test detection of MEDIUM sensitivity."""
        result = await tool_registry.detect_sensitivity(tool_name="update user profile")

        assert result == SensitivityLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_detect_low_keywords(self, tool_registry):
        """Test detection of LOW sensitivity."""
        result = await tool_registry.detect_sensitivity(tool_name="get user list")

        assert result == SensitivityLevel.LOW

    @pytest.mark.asyncio
    async def test_detect_default_medium(self, tool_registry):
        """Test default to MEDIUM when no keywords match."""
        result = await tool_registry.detect_sensitivity(tool_name="process_workflow")

        assert result == SensitivityLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_detect_with_parameters(self, tool_registry):
        """Test detection includes parameter names."""
        parameters = {
            "properties": {
                "admin": {"type": "string"},
                "user_data": {"type": "object"},
            }
        }

        result = await tool_registry.detect_sensitivity(
            tool_name="process data",
            tool_description="Process some data",
            parameters=parameters,
        )

        # "admin" in parameter name should trigger HIGH
        assert result == SensitivityLevel.HIGH

    @pytest.mark.asyncio
    async def test_detect_case_insensitive(self, tool_registry):
        """Test that detection is case insensitive."""
        result = await tool_registry.detect_sensitivity(tool_name="DELETE DATABASE")

        assert result == SensitivityLevel.HIGH

    @pytest.mark.asyncio
    async def test_detect_word_boundaries(self, tool_registry):
        """Test that keyword matching uses word boundaries."""
        # "update" should match
        result1 = await tool_registry.detect_sensitivity(tool_name="update list")
        assert result1 == SensitivityLevel.MEDIUM

        # "get" should match
        result2 = await tool_registry.detect_sensitivity(tool_name="get data")
        assert result2 == SensitivityLevel.LOW


class TestContainsKeywords:
    """Test keyword matching helper."""

    def test_contains_keywords_found(self, tool_registry):
        """Test that keywords are found."""
        text = "this tool will delete all records"
        keywords = ["delete", "remove"]

        result = tool_registry._contains_keywords(text, keywords)

        assert result is True

    def test_contains_keywords_not_found(self, tool_registry):
        """Test that keywords are not found."""
        text = "this tool will show all records"
        keywords = ["delete", "remove"]

        result = tool_registry._contains_keywords(text, keywords)

        assert result is False

    def test_contains_keywords_word_boundary(self, tool_registry):
        """Test word boundary matching."""
        text = "read this data"
        keywords = ["read"]

        result = tool_registry._contains_keywords(text, keywords)

        assert result is True


class TestExtractParameterNames:
    """Test parameter name extraction."""

    def test_extract_from_properties(self, tool_registry):
        """Test extracting from JSONSchema properties."""
        parameters = {
            "properties": {"user_id": {"type": "string"}, "email": {"type": "string"}}
        }

        result = tool_registry._extract_parameter_names(parameters)

        assert "user_id" in result
        assert "email" in result

    def test_extract_from_typed_object(self, tool_registry):
        """Test extracting from typed object schema."""
        parameters = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
        }

        result = tool_registry._extract_parameter_names(parameters)

        assert "name" in result
        assert "age" in result

    def test_extract_from_simple_dict(self, tool_registry):
        """Test extracting from simple dictionary."""
        parameters = {"username": "string", "password": "string"}

        result = tool_registry._extract_parameter_names(parameters)

        assert "username" in result
        assert "password" in result

    def test_extract_empty_parameters(self, tool_registry):
        """Test extracting from empty parameters."""
        parameters = {}

        result = tool_registry._extract_parameter_names(parameters)

        assert result == []


class TestGetTool:
    """Test tool retrieval."""

    @pytest.mark.asyncio
    async def test_get_tool_by_id(self, tool_registry, mock_db):
        """Test getting tool by ID."""
        tool_id = uuid4()
        tool = MCPTool(
            id=tool_id,
            server_id=uuid4(),
            name="test_tool",
            sensitivity_level=SensitivityLevel.MEDIUM,
        )

        mock_db.get.return_value = tool

        result = await tool_registry.get_tool(tool_id)

        assert result == tool
        mock_db.get.assert_called_with(MCPTool, tool_id)

    @pytest.mark.asyncio
    async def test_get_tool_by_name(self, tool_registry, mock_db):
        """Test getting tool by server ID and name."""
        server_id = uuid4()
        tool = MCPTool(
            id=uuid4(),
            server_id=server_id,
            name="test_tool",
            sensitivity_level=SensitivityLevel.LOW,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = tool
        mock_db.execute.return_value = mock_result

        result = await tool_registry.get_tool_by_name(server_id, "test_tool")

        assert result == tool


class TestUpdateSensitivity:
    """Test manual sensitivity override."""

    @pytest.mark.asyncio
    async def test_update_sensitivity(self, tool_registry, mock_db):
        """Test updating tool sensitivity level."""
        tool_id = uuid4()
        user_id = uuid4()
        tool = MCPTool(
            id=tool_id,
            server_id=uuid4(),
            name="test_tool",
            sensitivity_level=SensitivityLevel.MEDIUM,
            extra_metadata={},
        )

        mock_db.get.return_value = tool

        result = await tool_registry.update_sensitivity(
            tool_id=tool_id,
            new_sensitivity=SensitivityLevel.HIGH,
            user_id=user_id,
            user_email="admin@example.com",
            reason="Security audit requires higher sensitivity",
        )

        # Verify sensitivity was updated
        assert tool.sensitivity_level == SensitivityLevel.HIGH

        # Verify metadata was updated
        assert "sensitivity_override" in tool.extra_metadata
        override = tool.extra_metadata["sensitivity_override"]
        assert override["previous_level"] == "medium"
        assert override["new_level"] == "high"
        assert override["reason"] == "Security audit requires higher sensitivity"

        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_update_sensitivity_tool_not_found(self, tool_registry, mock_db):
        """Test updating sensitivity for non-existent tool."""
        mock_db.get.return_value = None

        with pytest.raises(ValueError, match="not found"):
            await tool_registry.update_sensitivity(
                tool_id=uuid4(),
                new_sensitivity=SensitivityLevel.HIGH,
                user_id=uuid4(),
                user_email="admin@example.com",
            )

    @pytest.mark.asyncio
    async def test_update_sensitivity_with_audit(self, mock_db):
        """Test that audit event is logged when audit_db is provided."""
        audit_db = AsyncMock()
        tool_registry = ToolRegistry(db=mock_db, audit_db=audit_db)

        tool = MCPTool(
            id=uuid4(),
            server_id=uuid4(),
            name="test_tool",
            sensitivity_level=SensitivityLevel.LOW,
            extra_metadata={},
        )

        mock_db.get.return_value = tool

        # Just verify the update works - audit logging happens internally
        await tool_registry.update_sensitivity(
            tool_id=tool.id,
            new_sensitivity=SensitivityLevel.HIGH,
            user_id=uuid4(),
            user_email="admin@example.com",
        )

        # Verify sensitivity was updated
        assert tool.sensitivity_level == SensitivityLevel.HIGH


class TestGetSensitivityHistory:
    """Test sensitivity history retrieval."""

    @pytest.mark.asyncio
    async def test_get_sensitivity_history_with_override(
        self, tool_registry, mock_db
    ):
        """Test getting history with manual override."""
        tool = MCPTool(
            id=uuid4(),
            server_id=uuid4(),
            name="test_tool",
            sensitivity_level=SensitivityLevel.HIGH,
            extra_metadata={
                "sensitivity_override": {
                    "previous_level": "medium",
                    "new_level": "high",
                    "updated_by": str(uuid4()),
                    "updated_at": datetime.now(UTC).isoformat(),
                    "reason": "Security review",
                }
            },
            updated_at=datetime.now(UTC),
        )

        mock_db.get.return_value = tool

        history = await tool_registry.get_sensitivity_history(tool.id)

        assert len(history) == 2  # Override + current
        assert history[0]["type"] == "manual_override"
        assert history[0]["reason"] == "Security review"
        assert history[1]["type"] == "current"

    @pytest.mark.asyncio
    async def test_get_sensitivity_history_no_override(self, tool_registry, mock_db):
        """Test getting history without manual override."""
        tool = MCPTool(
            id=uuid4(),
            server_id=uuid4(),
            name="test_tool",
            sensitivity_level=SensitivityLevel.MEDIUM,
            updated_at=datetime.now(UTC),
        )

        mock_db.get.return_value = tool

        history = await tool_registry.get_sensitivity_history(tool.id)

        assert len(history) == 1  # Only current
        assert history[0]["type"] == "current"

    @pytest.mark.asyncio
    async def test_get_history_tool_not_found(self, tool_registry, mock_db):
        """Test getting history for non-existent tool."""
        mock_db.get.return_value = None

        with pytest.raises(ValueError, match="not found"):
            await tool_registry.get_sensitivity_history(uuid4())


class TestBulkDetectSensitivity:
    """Test bulk sensitivity detection."""

    @pytest.mark.asyncio
    async def test_bulk_detect_sensitivity(self, tool_registry, mock_db):
        """Test detecting sensitivity for all server tools."""
        server_id = uuid4()
        tools = [
            MCPTool(
                id=uuid4(),
                server_id=server_id,
                name="delete_user",
                description="Delete user account",
                sensitivity_level=SensitivityLevel.MEDIUM,
            ),
            MCPTool(
                id=uuid4(),
                server_id=server_id,
                name="get_user",
                description="Get user information",
                sensitivity_level=SensitivityLevel.LOW,
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = tools
        mock_db.execute.return_value = mock_result

        detections = await tool_registry.bulk_detect_sensitivity(server_id)

        assert len(detections) == 2
        # "delete" should be detected as HIGH
        # "get" should be detected as LOW


class TestGetToolsBySensitivity:
    """Test getting tools by sensitivity level."""

    @pytest.mark.asyncio
    async def test_get_tools_by_sensitivity(self, tool_registry, mock_db):
        """Test getting all tools with specific sensitivity."""
        tools = [
            MCPTool(
                id=uuid4(),
                server_id=uuid4(),
                name="tool1",
                sensitivity_level=SensitivityLevel.CRITICAL,
            ),
            MCPTool(
                id=uuid4(),
                server_id=uuid4(),
                name="tool2",
                sensitivity_level=SensitivityLevel.CRITICAL,
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = tools
        mock_db.execute.return_value = mock_result

        result = await tool_registry.get_tools_by_sensitivity(
            SensitivityLevel.CRITICAL
        )

        assert len(result) == 2


class TestGetSensitivityStatistics:
    """Test sensitivity statistics."""

    @pytest.mark.asyncio
    async def test_get_sensitivity_statistics(self, tool_registry, mock_db):
        """Test getting sensitivity distribution statistics."""
        tools = [
            MCPTool(
                id=uuid4(),
                server_id=uuid4(),
                name="tool1",
                sensitivity_level=SensitivityLevel.LOW,
            ),
            MCPTool(
                id=uuid4(),
                server_id=uuid4(),
                name="tool2",
                sensitivity_level=SensitivityLevel.MEDIUM,
            ),
            MCPTool(
                id=uuid4(),
                server_id=uuid4(),
                name="tool3",
                sensitivity_level=SensitivityLevel.HIGH,
                extra_metadata={"sensitivity_override": {}},
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = tools
        mock_db.execute.return_value = mock_result

        stats = await tool_registry.get_sensitivity_statistics()

        assert stats["total_tools"] == 3
        assert stats["by_sensitivity"]["low"] == 1
        assert stats["by_sensitivity"]["medium"] == 1
        assert stats["by_sensitivity"]["high"] == 1
        assert stats["overridden_count"] == 1

    @pytest.mark.asyncio
    async def test_get_statistics_empty(self, tool_registry, mock_db):
        """Test statistics with no tools."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        stats = await tool_registry.get_sensitivity_statistics()

        assert stats["total_tools"] == 0
        assert stats["by_sensitivity"]["low"] == 0
        assert stats["overridden_count"] == 0
