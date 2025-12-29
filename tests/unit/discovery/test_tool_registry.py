"""Unit tests for Tool Registry and Sensitivity Classification."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sark.models.mcp_server import MCPTool, SensitivityLevel
from sark.services.discovery.tool_registry import ToolRegistry


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.get = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_audit_db():
    """Mock audit database session."""
    db = MagicMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def tool_registry(mock_db):
    """Tool registry with mocked database."""
    return ToolRegistry(mock_db)


@pytest.fixture
def tool_registry_with_audit(mock_db, mock_audit_db):
    """Tool registry with mocked database and audit."""
    return ToolRegistry(mock_db, mock_audit_db)


@pytest.fixture
def sample_tool():
    """Sample MCP tool."""
    tool_id = uuid4()
    server_id = uuid4()
    return MCPTool(
        id=tool_id,
        server_id=server_id,
        name="test-tool",
        description="Test tool for unit tests",
        parameters={"type": "object", "properties": {"param1": {"type": "string"}}},
        sensitivity_level=SensitivityLevel.MEDIUM,
        signature=None,
        requires_approval=False,
        extra_metadata={},
        invocation_count=0,
        last_invoked=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestToolRegistryDetectSensitivity:
    """Test detect_sensitivity method."""

    @pytest.mark.asyncio
    async def test_detect_critical_keywords(self, tool_registry):
        """Test detection of critical sensitivity keywords."""
        result = await tool_registry.detect_sensitivity(
            tool_name="process_payment",
            tool_description="Process payment transactions",
        )
        assert result == SensitivityLevel.CRITICAL

    @pytest.mark.asyncio
    async def test_detect_critical_from_password(self, tool_registry):
        """Test critical detection from password keyword."""
        result = await tool_registry.detect_sensitivity(
            tool_name="update_password",
            tool_description="Update user password",
        )
        assert result == SensitivityLevel.CRITICAL

    @pytest.mark.asyncio
    async def test_detect_critical_from_secret(self, tool_registry):
        """Test critical detection from secret keyword."""
        result = await tool_registry.detect_sensitivity(
            tool_name="get_api_secret",
            tool_description="Retrieve API secret key",
        )
        assert result == SensitivityLevel.CRITICAL

    @pytest.mark.asyncio
    async def test_detect_high_keywords(self, tool_registry):
        """Test detection of high sensitivity keywords."""
        result = await tool_registry.detect_sensitivity(
            tool_name="delete_user",
            tool_description="Delete a user account",
        )
        assert result == SensitivityLevel.HIGH

    @pytest.mark.asyncio
    async def test_detect_high_from_exec(self, tool_registry):
        """Test high detection from exec keyword."""
        result = await tool_registry.detect_sensitivity(
            tool_name="execute_command",
            tool_description="Execute system command",
        )
        assert result == SensitivityLevel.HIGH

    @pytest.mark.asyncio
    async def test_detect_medium_keywords(self, tool_registry):
        """Test detection of medium sensitivity keywords."""
        result = await tool_registry.detect_sensitivity(
            tool_name="update_profile",
            tool_description="Update user profile information",
        )
        assert result == SensitivityLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_detect_medium_from_write(self, tool_registry):
        """Test medium detection from write keyword."""
        result = await tool_registry.detect_sensitivity(
            tool_name="write_file",
            tool_description="Write data to file",
        )
        assert result == SensitivityLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_detect_low_keywords(self, tool_registry):
        """Test detection of low sensitivity keywords."""
        result = await tool_registry.detect_sensitivity(
            tool_name="get_user",
            tool_description="Retrieve user information",
        )
        assert result == SensitivityLevel.LOW

    @pytest.mark.asyncio
    async def test_detect_low_from_read(self, tool_registry):
        """Test low detection from read keyword."""
        result = await tool_registry.detect_sensitivity(
            tool_name="read_config",
            tool_description="Read configuration settings",
        )
        assert result == SensitivityLevel.LOW

    @pytest.mark.asyncio
    async def test_detect_default_medium(self, tool_registry):
        """Test default sensitivity when no keywords match."""
        result = await tool_registry.detect_sensitivity(
            tool_name="analyze_data",
            tool_description="Analyze data patterns",
        )
        assert result == SensitivityLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_detect_with_parameters(self, tool_registry):
        """Test sensitivity detection including parameter names."""
        result = await tool_registry.detect_sensitivity(
            tool_name="process_data",
            tool_description="Process data",
            parameters={
                "properties": {
                    "credit_card": {"type": "string"},
                    "cvv": {"type": "string"},
                }
            },
        )
        assert result == SensitivityLevel.CRITICAL

    @pytest.mark.asyncio
    async def test_detect_case_insensitive(self, tool_registry):
        """Test that detection is case-insensitive."""
        result = await tool_registry.detect_sensitivity(
            tool_name="DELETE_USER",
            tool_description="DELETE A USER ACCOUNT",
        )
        assert result == SensitivityLevel.HIGH

    @pytest.mark.asyncio
    async def test_detect_word_boundaries(self, tool_registry):
        """Test that keyword matching uses word boundaries."""
        # "deleted" contains "delete" but shouldn't match due to word boundaries
        result = await tool_registry.detect_sensitivity(
            tool_name="get_deleted_items",
            tool_description="Retrieve deleted items list",
        )
        # Should be LOW (from "get" and "retrieve"), not HIGH (from partial "delete" in "deleted")
        assert result == SensitivityLevel.LOW

    @pytest.mark.asyncio
    async def test_detect_priority_order(self, tool_registry):
        """Test that critical keywords take priority over high keywords."""
        result = await tool_registry.detect_sensitivity(
            tool_name="delete_password",
            tool_description="Delete user password (critical operation)",
        )
        # "password" (critical) should take priority over "delete" (high)
        assert result == SensitivityLevel.CRITICAL


class TestToolRegistryContainsKeywords:
    """Test _contains_keywords method."""

    def test_contains_keywords_match(self, tool_registry):
        """Test keyword matching."""
        result = tool_registry._contains_keywords(
            "delete user account",
            ["delete", "remove", "purge"],
        )
        assert result is True

    def test_contains_keywords_no_match(self, tool_registry):
        """Test no keyword match."""
        result = tool_registry._contains_keywords(
            "get user information",
            ["delete", "remove", "purge"],
        )
        assert result is False

    def test_contains_keywords_word_boundary(self, tool_registry):
        """Test that word boundaries are respected."""
        # "deleted" contains "delete" but as part of another word
        # Word boundaries should prevent matching "delete" inside "deleted"
        result = tool_registry._contains_keywords(
            "get deleted items",
            ["delete"],
        )
        assert result is False  # "delete" should NOT match inside "deleted" due to word boundaries

    def test_contains_keywords_multiple_keywords(self, tool_registry):
        """Test matching with multiple keywords."""
        result = tool_registry._contains_keywords(
            "read and write files",
            ["read", "write"],
        )
        assert result is True

    def test_contains_keywords_empty_text(self, tool_registry):
        """Test with empty text."""
        result = tool_registry._contains_keywords(
            "",
            ["delete"],
        )
        assert result is False

    def test_contains_keywords_empty_list(self, tool_registry):
        """Test with empty keyword list."""
        result = tool_registry._contains_keywords(
            "delete user",
            [],
        )
        assert result is False


class TestToolRegistryExtractParameterNames:
    """Test _extract_parameter_names method."""

    def test_extract_jsonschema_parameters(self, tool_registry):
        """Test extracting parameters from JSONSchema format."""
        parameters = {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "email": {"type": "string"},
                "password": {"type": "string"},
            },
        }
        result = tool_registry._extract_parameter_names(parameters)
        assert "user_id" in result
        assert "email" in result
        assert "password" in result
        assert len(result) == 3

    def test_extract_simple_dict_parameters(self, tool_registry):
        """Test extracting parameters from simple dict."""
        parameters = {
            "username": "string",
            "age": "integer",
        }
        result = tool_registry._extract_parameter_names(parameters)
        assert "username" in result
        assert "age" in result

    def test_extract_nested_properties(self, tool_registry):
        """Test extracting from nested properties."""
        parameters = {
            "properties": {
                "name": {"type": "string"},
                "address": {"type": "object"},
            }
        }
        result = tool_registry._extract_parameter_names(parameters)
        assert "name" in result
        assert "address" in result

    def test_extract_empty_parameters(self, tool_registry):
        """Test extracting from empty parameters."""
        result = tool_registry._extract_parameter_names({})
        assert result == []

    def test_extract_non_dict_parameters(self, tool_registry):
        """Test with non-dict parameters."""
        result = tool_registry._extract_parameter_names("not a dict")
        assert result == []


class TestToolRegistryGetTool:
    """Test get_tool method."""

    @pytest.mark.asyncio
    async def test_get_tool_found(self, tool_registry, mock_db, sample_tool):
        """Test getting an existing tool."""
        mock_db.get.return_value = sample_tool

        result = await tool_registry.get_tool(sample_tool.id)

        assert result == sample_tool
        mock_db.get.assert_awaited_once_with(MCPTool, sample_tool.id)

    @pytest.mark.asyncio
    async def test_get_tool_not_found(self, tool_registry, mock_db):
        """Test getting a non-existent tool."""
        mock_db.get.return_value = None

        result = await tool_registry.get_tool(uuid4())

        assert result is None


class TestToolRegistryGetToolByName:
    """Test get_tool_by_name method."""

    @pytest.mark.asyncio
    async def test_get_tool_by_name_found(self, tool_registry, mock_db, sample_tool):
        """Test getting tool by server ID and name."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_tool
        mock_db.execute.return_value = mock_result

        result = await tool_registry.get_tool_by_name(sample_tool.server_id, "test-tool")

        assert result == sample_tool
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_tool_by_name_not_found(self, tool_registry, mock_db):
        """Test getting non-existent tool by name."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await tool_registry.get_tool_by_name(uuid4(), "nonexistent")

        assert result is None


class TestToolRegistryUpdateSensitivity:
    """Test update_sensitivity method."""

    @pytest.mark.asyncio
    async def test_update_sensitivity_success(
        self, tool_registry_with_audit, mock_db, mock_audit_db, sample_tool
    ):
        """Test successful sensitivity update with audit."""
        mock_db.get.return_value = sample_tool
        user_id = uuid4()
        user_email = "admin@example.com"

        updated_tool = await tool_registry_with_audit.update_sensitivity(
            tool_id=sample_tool.id,
            new_sensitivity=SensitivityLevel.HIGH,
            user_id=user_id,
            user_email=user_email,
            reason="Security review",
        )

        assert updated_tool.sensitivity_level == SensitivityLevel.HIGH
        assert "sensitivity_override" in updated_tool.extra_metadata
        assert updated_tool.extra_metadata["sensitivity_override"]["previous_level"] == "medium"
        assert updated_tool.extra_metadata["sensitivity_override"]["new_level"] == "high"
        assert updated_tool.extra_metadata["sensitivity_override"]["reason"] == "Security review"

        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_sensitivity_without_audit_db(self, tool_registry, mock_db, sample_tool):
        """Test sensitivity update without audit database."""
        mock_db.get.return_value = sample_tool
        user_id = uuid4()

        updated_tool = await tool_registry.update_sensitivity(
            tool_id=sample_tool.id,
            new_sensitivity=SensitivityLevel.CRITICAL,
            user_id=user_id,
            user_email="user@example.com",
        )

        assert updated_tool.sensitivity_level == SensitivityLevel.CRITICAL
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_sensitivity_tool_not_found(self, tool_registry, mock_db):
        """Test updating sensitivity for non-existent tool."""
        mock_db.get.return_value = None

        with pytest.raises(ValueError, match="Tool .* not found"):
            await tool_registry.update_sensitivity(
                tool_id=uuid4(),
                new_sensitivity=SensitivityLevel.HIGH,
                user_id=uuid4(),
                user_email="user@example.com",
            )

    @pytest.mark.asyncio
    async def test_update_sensitivity_with_reason(self, tool_registry, mock_db, sample_tool):
        """Test sensitivity update includes reason in metadata."""
        mock_db.get.return_value = sample_tool
        reason = "Compliance requirement"

        updated_tool = await tool_registry.update_sensitivity(
            tool_id=sample_tool.id,
            new_sensitivity=SensitivityLevel.CRITICAL,
            user_id=uuid4(),
            user_email="admin@example.com",
            reason=reason,
        )

        assert updated_tool.extra_metadata["sensitivity_override"]["reason"] == reason


class TestToolRegistryGetSensitivityHistory:
    """Test get_sensitivity_history method."""

    @pytest.mark.asyncio
    async def test_get_sensitivity_history_with_override(self, tool_registry, mock_db, sample_tool):
        """Test getting sensitivity history with override."""
        sample_tool.extra_metadata = {
            "sensitivity_override": {
                "previous_level": "low",
                "new_level": "high",
                "updated_by": str(uuid4()),
                "updated_at": "2025-01-01T00:00:00",
                "reason": "Security review",
            }
        }
        mock_db.get.return_value = sample_tool

        history = await tool_registry.get_sensitivity_history(sample_tool.id)

        assert len(history) == 2
        assert history[0]["type"] == "manual_override"
        assert history[0]["previous_level"] == "low"
        assert history[0]["new_level"] == "high"
        assert history[1]["type"] == "current"

    @pytest.mark.asyncio
    async def test_get_sensitivity_history_no_override(self, tool_registry, mock_db, sample_tool):
        """Test getting sensitivity history without override."""
        sample_tool.extra_metadata = {}
        mock_db.get.return_value = sample_tool

        history = await tool_registry.get_sensitivity_history(sample_tool.id)

        assert len(history) == 1
        assert history[0]["type"] == "current"

    @pytest.mark.asyncio
    async def test_get_sensitivity_history_tool_not_found(self, tool_registry, mock_db):
        """Test getting history for non-existent tool."""
        mock_db.get.return_value = None

        with pytest.raises(ValueError, match="Tool .* not found"):
            await tool_registry.get_sensitivity_history(uuid4())


class TestToolRegistryBulkDetectSensitivity:
    """Test bulk_detect_sensitivity method."""

    @pytest.mark.asyncio
    async def test_bulk_detect_sensitivity(self, tool_registry, mock_db):
        """Test bulk sensitivity detection for all tools on a server."""
        server_id = uuid4()
        tools = [
            MCPTool(
                id=uuid4(),
                server_id=server_id,
                name="delete_user",
                description="Delete user account",
                parameters={},
                sensitivity_level=SensitivityLevel.LOW,  # Wrong classification
            ),
            MCPTool(
                id=uuid4(),
                server_id=server_id,
                name="get_user",
                description="Get user information",
                parameters={},
                sensitivity_level=SensitivityLevel.MEDIUM,
            ),
            MCPTool(
                id=uuid4(),
                server_id=server_id,
                name="process_payment",
                description="Process credit card payment",
                parameters={},
                sensitivity_level=SensitivityLevel.MEDIUM,  # Wrong classification
            ),
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = tools
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        detections = await tool_registry.bulk_detect_sensitivity(server_id)

        assert len(detections) == 3
        # Verify correct sensitivities were detected
        tool_ids = [str(t.id) for t in tools]
        assert detections[tool_ids[0]] == SensitivityLevel.HIGH  # delete_user
        assert detections[tool_ids[1]] == SensitivityLevel.LOW  # get_user
        assert detections[tool_ids[2]] == SensitivityLevel.CRITICAL  # process_payment

    @pytest.mark.asyncio
    async def test_bulk_detect_sensitivity_empty_server(self, tool_registry, mock_db):
        """Test bulk detection for server with no tools."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        detections = await tool_registry.bulk_detect_sensitivity(uuid4())

        assert len(detections) == 0


class TestToolRegistryGetToolsBySensitivity:
    """Test get_tools_by_sensitivity method."""

    @pytest.mark.asyncio
    async def test_get_tools_by_sensitivity(self, tool_registry, mock_db, sample_tool):
        """Test getting tools filtered by sensitivity level."""
        tools = [sample_tool]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = tools
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await tool_registry.get_tools_by_sensitivity(SensitivityLevel.MEDIUM)

        assert len(result) == 1
        assert result[0] == sample_tool

    @pytest.mark.asyncio
    async def test_get_tools_by_sensitivity_no_matches(self, tool_registry, mock_db):
        """Test getting tools with no matches."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await tool_registry.get_tools_by_sensitivity(SensitivityLevel.CRITICAL)

        assert len(result) == 0


class TestToolRegistryGetSensitivityStatistics:
    """Test get_sensitivity_statistics method."""

    @pytest.mark.asyncio
    async def test_get_sensitivity_statistics(self, tool_registry, mock_db):
        """Test getting sensitivity distribution statistics."""
        server_id = uuid4()
        tools = [
            MCPTool(
                id=uuid4(),
                server_id=server_id,
                name="tool1",
                sensitivity_level=SensitivityLevel.LOW,
                extra_metadata={},
            ),
            MCPTool(
                id=uuid4(),
                server_id=server_id,
                name="tool2",
                sensitivity_level=SensitivityLevel.MEDIUM,
                extra_metadata={},
            ),
            MCPTool(
                id=uuid4(),
                server_id=server_id,
                name="tool3",
                sensitivity_level=SensitivityLevel.HIGH,
                extra_metadata={"sensitivity_override": {"reason": "Manual review"}},
            ),
            MCPTool(
                id=uuid4(),
                server_id=server_id,
                name="tool4",
                sensitivity_level=SensitivityLevel.CRITICAL,
                extra_metadata={},
            ),
            MCPTool(
                id=uuid4(),
                server_id=server_id,
                name="tool5",
                sensitivity_level=SensitivityLevel.MEDIUM,
                extra_metadata={},
            ),
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = tools
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        stats = await tool_registry.get_sensitivity_statistics()

        assert stats["total_tools"] == 5
        assert stats["by_sensitivity"]["low"] == 1
        assert stats["by_sensitivity"]["medium"] == 2
        assert stats["by_sensitivity"]["high"] == 1
        assert stats["by_sensitivity"]["critical"] == 1
        assert stats["overridden_count"] == 1

    @pytest.mark.asyncio
    async def test_get_sensitivity_statistics_empty(self, tool_registry, mock_db):
        """Test statistics with no tools."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        stats = await tool_registry.get_sensitivity_statistics()

        assert stats["total_tools"] == 0
        assert stats["by_sensitivity"]["low"] == 0
        assert stats["by_sensitivity"]["medium"] == 0
        assert stats["by_sensitivity"]["high"] == 0
        assert stats["by_sensitivity"]["critical"] == 0
        assert stats["overridden_count"] == 0
