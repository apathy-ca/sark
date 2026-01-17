"""Tests for Tools API endpoints."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi import status
import pytest

from sark.models.mcp_server import MCPServer, MCPTool, SensitivityLevel, ServerStatus, TransportType


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    user = MagicMock()
    user.user_id = uuid4()
    user.email = "admin@example.com"
    user.role = "admin"
    user.teams = []
    return user


@pytest.fixture
def mock_server(db_session):
    """Create a mock MCP server."""
    server = MCPServer(
        id=uuid4(),
        name="test-server",
        transport=TransportType.HTTP,
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
    """Create a mock tool."""
    tool = MCPTool(
        id=uuid4(),
        server_id=mock_server.id,
        name="test_delete_user",
        description="Deletes a user from the system",
        sensitivity_level=SensitivityLevel.HIGH,
    )
    db_session.add(tool)
    db_session.commit()
    return tool


# ============================================================================
# GET TOOL SENSITIVITY TESTS
# ============================================================================



def test_get_tool_sensitivity_success(client, mock_tool):
    """Test getting tool sensitivity level."""
    response = client.get(f"/api/v1/tools/{mock_tool.id}/sensitivity")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["tool_id"] == str(mock_tool.id)
    assert data["tool_name"] == mock_tool.name
    assert data["sensitivity_level"] == "high"
    assert data["is_overridden"] is False



def test_get_tool_sensitivity_not_found(client):
    """Test getting sensitivity for non-existent tool."""
    fake_id = uuid4()
    response = client.get(f"/api/v1/tools/{fake_id}/sensitivity")

    assert response.status_code == status.HTTP_404_NOT_FOUND



def test_get_tool_sensitivity_with_override(client, db_session, mock_tool):
    """Test getting tool sensitivity that has been manually overridden."""
    # Add override metadata
    mock_tool.extra_metadata = {
        "sensitivity_override": {
            "previous_level": "medium",
            "new_level": "high",
            "updated_by": str(uuid4()),
            "updated_at": "2025-11-22T10:00:00Z",
            "reason": "Security review",
        }
    }
    db_session.commit()

    response = client.get(f"/api/v1/tools/{mock_tool.id}/sensitivity")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["is_overridden"] is True


# ============================================================================
# UPDATE TOOL SENSITIVITY TESTS
# ============================================================================



@patch("sark.services.policy.OPAClient.authorize", return_value=True)
def test_update_tool_sensitivity_success(
    mock_authorize, client, mock_tool, mock_user
):
    """Test manually updating tool sensitivity level."""
    with patch("sark.services.auth.get_current_user", return_value=mock_user):
        response = client.post(
            f"/api/v1/tools/{mock_tool.id}/sensitivity",
            json={
                "sensitivity_level": "critical",
                "reason": "Handles sensitive data",
            },
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["sensitivity_level"] == "critical"
    assert data["is_overridden"] is True



@patch("sark.services.policy.OPAClient.authorize", return_value=False)
def test_update_tool_sensitivity_forbidden(
    mock_authorize, client, mock_tool, mock_user
):
    """Test updating tool sensitivity without authorization."""
    with patch("sark.services.auth.get_current_user", return_value=mock_user):
        response = client.post(
            f"/api/v1/tools/{mock_tool.id}/sensitivity",
            json={
                "sensitivity_level": "critical",
                "reason": "Test",
            },
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN



@patch("sark.services.policy.OPAClient.authorize", return_value=True)
def test_update_tool_sensitivity_invalid_level(
    mock_authorize, client, mock_tool, mock_user
):
    """Test updating tool with invalid sensitivity level."""
    with patch("sark.services.auth.get_current_user", return_value=mock_user):
        response = client.post(
            f"/api/v1/tools/{mock_tool.id}/sensitivity",
            json={
                "sensitivity_level": "super-critical",  # Invalid
                "reason": "Test",
            },
        )

    # Should fail validation
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY



@patch("sark.services.policy.OPAClient.authorize", return_value=True)
def test_update_tool_sensitivity_not_found(mock_authorize, client, mock_user):
    """Test updating sensitivity for non-existent tool."""
    fake_id = uuid4()

    with patch("sark.services.auth.get_current_user", return_value=mock_user):
        response = client.post(
            f"/api/v1/tools/{fake_id}/sensitivity",
            json={
                "sensitivity_level": "high",
                "reason": "Test",
            },
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# DETECT SENSITIVITY TESTS
# ============================================================================



def test_detect_sensitivity_low(client):
    """Test detecting LOW sensitivity."""
    response = client.post(
        "/api/v1/tools/detect-sensitivity",
        json={
            "tool_name": "read_user_data",
            "tool_description": "Retrieves user information from database",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["detected_level"] == "low"
    assert data["detection_method"] == "low_keywords"
    assert "read" in data.get("keywords_matched", [])



def test_detect_sensitivity_medium(client):
    """Test detecting MEDIUM sensitivity."""
    response = client.post(
        "/api/v1/tools/detect-sensitivity",
        json={
            "tool_name": "update_settings",
            "tool_description": "Modifies system configuration",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["detected_level"] == "medium"
    assert data["detection_method"] == "medium_keywords"



def test_detect_sensitivity_high(client):
    """Test detecting HIGH sensitivity."""
    response = client.post(
        "/api/v1/tools/detect-sensitivity",
        json={
            "tool_name": "delete_resource",
            "tool_description": "Permanently removes resources",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["detected_level"] == "high"
    assert data["detection_method"] == "high_keywords"
    assert "delete" in data.get("keywords_matched", [])



def test_detect_sensitivity_critical(client):
    """Test detecting CRITICAL sensitivity."""
    response = client.post(
        "/api/v1/tools/detect-sensitivity",
        json={
            "tool_name": "process_payment",
            "tool_description": "Handles credit card transactions",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["detected_level"] == "critical"
    assert data["detection_method"] == "critical_keywords"



def test_detect_sensitivity_default(client):
    """Test default sensitivity detection."""
    response = client.post(
        "/api/v1/tools/detect-sensitivity",
        json={
            "tool_name": "process_data",
            "tool_description": "General data processing",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["detected_level"] == "medium"
    assert data["detection_method"] == "default"



def test_detect_sensitivity_with_parameters(client):
    """Test sensitivity detection with parameters."""
    response = client.post(
        "/api/v1/tools/detect-sensitivity",
        json={
            "tool_name": "manage_account",
            "tool_description": "Account management",
            "parameters": {
                "username": {"type": "string"},
                "new_password": {"type": "string"},
            },
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    # Should detect CRITICAL due to "password" in parameters
    assert data["detected_level"] == "critical"


# ============================================================================
# SENSITIVITY HISTORY TESTS
# ============================================================================



def test_get_sensitivity_history(client, mock_tool):
    """Test getting sensitivity change history."""
    response = client.get(f"/api/v1/tools/{mock_tool.id}/sensitivity/history")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    # Should have at least current state
    assert len(data) >= 1



def test_get_sensitivity_history_not_found(client):
    """Test getting history for non-existent tool."""
    fake_id = uuid4()
    response = client.get(f"/api/v1/tools/{fake_id}/sensitivity/history")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# STATISTICS TESTS
# ============================================================================



def test_get_sensitivity_statistics(client, mock_tool):
    """Test getting sensitivity statistics."""
    response = client.get("/api/v1/tools/statistics/sensitivity")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "total_tools" in data
    assert "by_sensitivity" in data
    assert "overridden_count" in data
    assert data["total_tools"] >= 1
    assert "low" in data["by_sensitivity"]
    assert "medium" in data["by_sensitivity"]
    assert "high" in data["by_sensitivity"]
    assert "critical" in data["by_sensitivity"]


# ============================================================================
# LIST BY SENSITIVITY TESTS
# ============================================================================



def test_list_tools_by_sensitivity_high(client, mock_tool):
    """Test listing tools by sensitivity level."""
    response = client.get("/api/v1/tools/sensitivity/high")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    # Should include our mock tool
    tool_ids = [item["id"] for item in data]
    assert str(mock_tool.id) in tool_ids



def test_list_tools_by_sensitivity_invalid_level(client):
    """Test listing tools with invalid sensitivity level."""
    response = client.get("/api/v1/tools/sensitivity/invalid")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# BULK DETECTION TESTS
# ============================================================================



def test_bulk_detect_sensitivity(client, mock_server, mock_user):
    """Test bulk sensitivity detection for a server."""
    with patch("sark.services.auth.get_current_user", return_value=mock_user):
        response = client.post(f"/api/v1/tools/servers/{mock_server.id}/tools/detect-all")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "server_id" in data
    assert "tool_count" in data
    assert "detections" in data
    assert data["server_id"] == str(mock_server.id)


# ============================================================================
# VALIDATION TESTS
# ============================================================================



def test_update_sensitivity_missing_level(client, mock_tool, mock_user):
    """Test update with missing sensitivity level."""
    with patch("sark.services.auth.get_current_user", return_value=mock_user):
        response = client.post(
            f"/api/v1/tools/{mock_tool.id}/sensitivity",
            json={
                "reason": "Test",
                # Missing sensitivity_level
            },
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY



def test_detect_sensitivity_missing_name(client):
    """Test detect with missing tool name."""
    response = client.post(
        "/api/v1/tools/detect-sensitivity",
        json={
            "tool_description": "Test description",
            # Missing tool_name
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY



def test_update_sensitivity_with_optional_reason(client, mock_tool, mock_user):
    """Test update with optional reason field."""
    with patch("sark.services.policy.OPAClient.authorize", return_value=True):
        with patch("sark.services.auth.get_current_user", return_value=mock_user):
            response = client.post(
                f"/api/v1/tools/{mock_tool.id}/sensitivity",
                json={
                    "sensitivity_level": "critical",
                    # Reason is optional
                },
            )

    assert response.status_code == status.HTTP_200_OK
