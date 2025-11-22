"""Tests for Tool Registry and Sensitivity Classification Service."""

import pytest
from datetime import UTC, datetime
from uuid import uuid4

from sark.models.mcp_server import MCPServer, MCPTool, SensitivityLevel, ServerStatus, TransportType
from sark.services.discovery.tool_registry import ToolRegistry


@pytest.fixture
def mock_server(db_session):
    """Create a mock MCP server for testing."""
    server = MCPServer(
        id=uuid4(),
        name="test-server",
        description="Test server",
        transport=TransportType.HTTP,
        endpoint="http://localhost:8000",
        mcp_version="2025-06-18",
        capabilities=["tools"],
        sensitivity_level=SensitivityLevel.MEDIUM,
        status=ServerStatus.REGISTERED,
    )
    db_session.add(server)
    db_session.commit()
    return server


@pytest.fixture
def mock_tool(db_session, mock_server):
    """Create a mock MCP tool for testing."""
    tool = MCPTool(
        id=uuid4(),
        server_id=mock_server.id,
        name="test_read_database",
        description="Reads data from the database",
        parameters={"query": "string"},
        sensitivity_level=SensitivityLevel.MEDIUM,
    )
    db_session.add(tool)
    db_session.commit()
    return tool


# ============================================================================
# SENSITIVITY DETECTION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_detect_low_sensitivity(db_session):
    """Test detection of LOW sensitivity tools."""
    registry = ToolRegistry(db_session)

    # Test with read operation
    level = await registry.detect_sensitivity(
        tool_name="get_user_data",
        tool_description="Retrieves user information from the database",
    )
    assert level == SensitivityLevel.LOW

    # Test with list operation
    level = await registry.detect_sensitivity(
        tool_name="list_servers",
        tool_description="Shows all available servers",
    )
    assert level == SensitivityLevel.LOW

    # Test with view operation
    level = await registry.detect_sensitivity(
        tool_name="view_logs",
        tool_description="Display system logs",
    )
    assert level == SensitivityLevel.LOW


@pytest.mark.asyncio
async def test_detect_medium_sensitivity(db_session):
    """Test detection of MEDIUM sensitivity tools."""
    registry = ToolRegistry(db_session)

    # Test with write operation
    level = await registry.detect_sensitivity(
        tool_name="write_config",
        tool_description="Writes configuration to file",
    )
    assert level == SensitivityLevel.MEDIUM

    # Test with update operation
    level = await registry.detect_sensitivity(
        tool_name="update_user",
        tool_description="Updates user information",
    )
    assert level == SensitivityLevel.MEDIUM

    # Test with create operation
    level = await registry.detect_sensitivity(
        tool_name="create_resource",
        tool_description="Creates a new resource",
    )
    assert level == SensitivityLevel.MEDIUM


@pytest.mark.asyncio
async def test_detect_high_sensitivity(db_session):
    """Test detection of HIGH sensitivity tools."""
    registry = ToolRegistry(db_session)

    # Test with delete operation
    level = await registry.detect_sensitivity(
        tool_name="delete_user",
        tool_description="Deletes a user from the system",
    )
    assert level == SensitivityLevel.HIGH

    # Test with exec operation
    level = await registry.detect_sensitivity(
        tool_name="exec_command",
        tool_description="Executes system commands",
    )
    assert level == SensitivityLevel.HIGH

    # Test with admin operation
    level = await registry.detect_sensitivity(
        tool_name="admin_panel",
        tool_description="Administrative operations",
    )
    assert level == SensitivityLevel.HIGH

    # Test with drop operation
    level = await registry.detect_sensitivity(
        tool_name="drop_table",
        tool_description="Drops database table",
    )
    assert level == SensitivityLevel.HIGH


@pytest.mark.asyncio
async def test_detect_critical_sensitivity(db_session):
    """Test detection of CRITICAL sensitivity tools."""
    registry = ToolRegistry(db_session)

    # Test with payment operation
    level = await registry.detect_sensitivity(
        tool_name="process_payment",
        tool_description="Processes credit card transactions",
    )
    assert level == SensitivityLevel.CRITICAL

    # Test with password operation
    level = await registry.detect_sensitivity(
        tool_name="reset_password",
        tool_description="Resets user passwords",
    )
    assert level == SensitivityLevel.CRITICAL

    # Test with encryption operation
    level = await registry.detect_sensitivity(
        tool_name="encrypt_data",
        tool_description="Encrypts sensitive data with secret keys",
    )
    assert level == SensitivityLevel.CRITICAL

    # Test with credential operation
    level = await registry.detect_sensitivity(
        tool_name="manage_credentials",
        tool_description="Manages API credentials and tokens",
    )
    assert level == SensitivityLevel.CRITICAL


@pytest.mark.asyncio
async def test_detect_default_sensitivity(db_session):
    """Test default sensitivity when no keywords match."""
    registry = ToolRegistry(db_session)

    level = await registry.detect_sensitivity(
        tool_name="process_data",
        tool_description="Processes various data operations",
    )
    # Default should be MEDIUM
    assert level == SensitivityLevel.MEDIUM


@pytest.mark.asyncio
async def test_detect_sensitivity_with_parameters(db_session):
    """Test sensitivity detection including parameter names."""
    registry = ToolRegistry(db_session)

    # Parameters contain "password"
    level = await registry.detect_sensitivity(
        tool_name="update_account",
        tool_description="Updates account settings",
        parameters={
            "username": {"type": "string"},
            "new_password": {"type": "string"},
        },
    )
    assert level == SensitivityLevel.CRITICAL

    # Parameters contain "delete"
    level = await registry.detect_sensitivity(
        tool_name="manage_items",
        parameters={
            "action": {"type": "string"},
            "delete_flag": {"type": "boolean"},
        },
    )
    assert level == SensitivityLevel.HIGH


@pytest.mark.asyncio
async def test_word_boundary_matching(db_session):
    """Test that keyword matching uses word boundaries."""
    registry = ToolRegistry(db_session)

    # "administer" contains "admin" but should match due to word boundary
    level = await registry.detect_sensitivity(
        tool_name="administer_system",
        tool_description="System administration tool",
    )
    assert level == SensitivityLevel.HIGH

    # "reading" contains "read" but should match
    level = await registry.detect_sensitivity(
        tool_name="reading_list",
        tool_description="Manage your reading list",
    )
    assert level == SensitivityLevel.LOW


# ============================================================================
# TOOL MANAGEMENT TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_get_tool(db_session, mock_tool):
    """Test retrieving a tool by ID."""
    registry = ToolRegistry(db_session)

    tool = await registry.get_tool(mock_tool.id)
    assert tool is not None
    assert tool.id == mock_tool.id
    assert tool.name == mock_tool.name


@pytest.mark.asyncio
async def test_get_nonexistent_tool(db_session):
    """Test retrieving a non-existent tool."""
    registry = ToolRegistry(db_session)

    tool = await registry.get_tool(uuid4())
    assert tool is None


@pytest.mark.asyncio
async def test_get_tool_by_name(db_session, mock_server, mock_tool):
    """Test retrieving a tool by server ID and name."""
    registry = ToolRegistry(db_session)

    tool = await registry.get_tool_by_name(mock_server.id, mock_tool.name)
    assert tool is not None
    assert tool.id == mock_tool.id
    assert tool.name == mock_tool.name


@pytest.mark.asyncio
async def test_update_sensitivity(db_session, mock_tool):
    """Test manually updating tool sensitivity."""
    registry = ToolRegistry(db_session)
    user_id = uuid4()
    user_email = "test@example.com"

    # Update from MEDIUM to HIGH
    updated_tool = await registry.update_sensitivity(
        tool_id=mock_tool.id,
        new_sensitivity=SensitivityLevel.HIGH,
        user_id=user_id,
        user_email=user_email,
        reason="Security review",
    )

    assert updated_tool.sensitivity_level == SensitivityLevel.HIGH
    assert "sensitivity_override" in updated_tool.extra_metadata
    override = updated_tool.extra_metadata["sensitivity_override"]
    assert override["previous_level"] == "medium"
    assert override["new_level"] == "high"
    assert override["reason"] == "Security review"


@pytest.mark.asyncio
async def test_update_sensitivity_nonexistent_tool(db_session):
    """Test updating sensitivity of non-existent tool."""
    registry = ToolRegistry(db_session)
    user_id = uuid4()

    with pytest.raises(ValueError, match="Tool .* not found"):
        await registry.update_sensitivity(
            tool_id=uuid4(),
            new_sensitivity=SensitivityLevel.HIGH,
            user_id=user_id,
            user_email="test@example.com",
        )


@pytest.mark.asyncio
async def test_get_sensitivity_history(db_session, mock_tool):
    """Test retrieving sensitivity change history."""
    registry = ToolRegistry(db_session)
    user_id = uuid4()

    # Update sensitivity to create history
    await registry.update_sensitivity(
        tool_id=mock_tool.id,
        new_sensitivity=SensitivityLevel.HIGH,
        user_id=user_id,
        user_email="test@example.com",
        reason="Security review",
    )

    history = await registry.get_sensitivity_history(mock_tool.id)

    assert len(history) >= 1
    # Should have the override entry
    override_entry = next((h for h in history if h.get("type") == "manual_override"), None)
    assert override_entry is not None
    assert override_entry["previous_level"] == "medium"
    assert override_entry["new_level"] == "high"


# ============================================================================
# BULK OPERATIONS TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_bulk_detect_sensitivity(db_session, mock_server):
    """Test bulk sensitivity detection for all tools on a server."""
    # Create multiple tools with different names
    tools_data = [
        {"name": "read_data", "description": "Reads data"},
        {"name": "delete_user", "description": "Deletes user"},
        {"name": "process_payment", "description": "Processes payments"},
    ]

    for data in tools_data:
        tool = MCPTool(
            server_id=mock_server.id,
            name=data["name"],
            description=data["description"],
            sensitivity_level=SensitivityLevel.MEDIUM,
        )
        db_session.add(tool)
    db_session.commit()

    registry = ToolRegistry(db_session)
    detections = await registry.bulk_detect_sensitivity(mock_server.id)

    assert len(detections) == 3
    # Verify detections
    detected_values = list(detections.values())
    assert SensitivityLevel.LOW in detected_values  # read_data
    assert SensitivityLevel.HIGH in detected_values  # delete_user
    assert SensitivityLevel.CRITICAL in detected_values  # process_payment


@pytest.mark.asyncio
async def test_get_tools_by_sensitivity(db_session, mock_server):
    """Test retrieving tools by sensitivity level."""
    # Create tools with different sensitivities
    high_tool = MCPTool(
        server_id=mock_server.id,
        name="delete_resource",
        description="Deletes resources",
        sensitivity_level=SensitivityLevel.HIGH,
    )
    low_tool = MCPTool(
        server_id=mock_server.id,
        name="read_resource",
        description="Reads resources",
        sensitivity_level=SensitivityLevel.LOW,
    )
    db_session.add_all([high_tool, low_tool])
    db_session.commit()

    registry = ToolRegistry(db_session)

    # Get HIGH sensitivity tools
    high_tools = await registry.get_tools_by_sensitivity(SensitivityLevel.HIGH)
    high_tool_names = [t.name for t in high_tools]
    assert "delete_resource" in high_tool_names

    # Get LOW sensitivity tools
    low_tools = await registry.get_tools_by_sensitivity(SensitivityLevel.LOW)
    low_tool_names = [t.name for t in low_tools]
    assert "read_resource" in low_tool_names


@pytest.mark.asyncio
async def test_get_sensitivity_statistics(db_session, mock_server):
    """Test getting sensitivity statistics."""
    # Create tools with different sensitivities
    tools = [
        MCPTool(
            server_id=mock_server.id,
            name=f"tool_low_{i}",
            sensitivity_level=SensitivityLevel.LOW,
        )
        for i in range(2)
    ] + [
        MCPTool(
            server_id=mock_server.id,
            name=f"tool_medium_{i}",
            sensitivity_level=SensitivityLevel.MEDIUM,
        )
        for i in range(3)
    ] + [
        MCPTool(
            server_id=mock_server.id,
            name=f"tool_high_{i}",
            sensitivity_level=SensitivityLevel.HIGH,
        )
        for i in range(1)
    ]

    db_session.add_all(tools)
    db_session.commit()

    registry = ToolRegistry(db_session)
    stats = await registry.get_sensitivity_statistics()

    assert stats["total_tools"] >= 6
    assert stats["by_sensitivity"]["low"] >= 2
    assert stats["by_sensitivity"]["medium"] >= 3
    assert stats["by_sensitivity"]["high"] >= 1


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================


@pytest.mark.asyncio
async def test_detect_sensitivity_empty_description(db_session):
    """Test sensitivity detection with empty description."""
    registry = ToolRegistry(db_session)

    level = await registry.detect_sensitivity(
        tool_name="delete_user",
        tool_description=None,
    )
    # Should still detect based on name
    assert level == SensitivityLevel.HIGH


@pytest.mark.asyncio
async def test_detect_sensitivity_case_insensitive(db_session):
    """Test that keyword matching is case-insensitive."""
    registry = ToolRegistry(db_session)

    # Test uppercase
    level = await registry.detect_sensitivity(
        tool_name="DELETE_USER",
        tool_description="DELETES USERS FROM SYSTEM",
    )
    assert level == SensitivityLevel.HIGH

    # Test mixed case
    level = await registry.detect_sensitivity(
        tool_name="ProcessPayment",
        tool_description="Processes Payment Transactions",
    )
    assert level == SensitivityLevel.CRITICAL


@pytest.mark.asyncio
async def test_multiple_keywords_highest_priority(db_session):
    """Test that highest priority keyword takes precedence."""
    registry = ToolRegistry(db_session)

    # Contains both "read" (LOW) and "password" (CRITICAL)
    level = await registry.detect_sensitivity(
        tool_name="read_password_hash",
        tool_description="Reads password hashes from database",
    )
    # CRITICAL should take precedence
    assert level == SensitivityLevel.CRITICAL

    # Contains both "update" (MEDIUM) and "delete" (HIGH)
    level = await registry.detect_sensitivity(
        tool_name="update_and_delete_records",
        tool_description="Updates or deletes database records",
    )
    # HIGH should take precedence
    assert level == SensitivityLevel.HIGH


@pytest.mark.asyncio
async def test_jsonschema_parameters(db_session):
    """Test parameter extraction from JSONSchema-style parameters."""
    registry = ToolRegistry(db_session)

    # JSONSchema style with properties
    level = await registry.detect_sensitivity(
        tool_name="manage_account",
        parameters={
            "type": "object",
            "properties": {
                "username": {"type": "string"},
                "admin_flag": {"type": "boolean"},
            },
        },
    )
    # Should detect "admin" from parameter name
    assert level == SensitivityLevel.HIGH
