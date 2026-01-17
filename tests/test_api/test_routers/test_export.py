"""Comprehensive tests for export router endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sark.models.mcp_server import MCPServer, MCPTool, SensitivityLevel, ServerStatus, TransportType


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    from sark.services.auth import UserContext

    return UserContext(
        user_id=uuid4(),
        email="test@example.com",
        role="user",
        teams=["team1"],
        is_authenticated=True,
    )


@pytest.fixture
def mock_servers():
    """Create mock server data."""
    return [
        MCPServer(
            id=uuid4(),
            name="test-server-1",
            description="Test server 1",
            transport=TransportType.STDIO,
            endpoint="/path/to/server1",
            status=ServerStatus.ACTIVE,
            sensitivity_level=SensitivityLevel.LOW,
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0),
            extra_metadata={"key": "value"},
        ),
        MCPServer(
            id=uuid4(),
            name="test-server-2",
            description="Test server 2",
            transport=TransportType.HTTP,
            endpoint="http://localhost:8080",
            status=ServerStatus.REGISTERED,
            sensitivity_level=SensitivityLevel.MEDIUM,
            created_at=datetime(2025, 1, 2, 12, 0, 0),
            updated_at=datetime(2025, 1, 2, 12, 0, 0),
            extra_metadata={},
        ),
    ]


@pytest.fixture
def mock_tools():
    """Create mock tool data."""
    server_id = uuid4()
    return [
        MCPTool(
            id=uuid4(),
            name="test-tool-1",
            description="Test tool 1",
            server_id=server_id,
            sensitivity_level=SensitivityLevel.LOW,
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            extra_metadata={"requires_approval": False},
        ),
        MCPTool(
            id=uuid4(),
            name="test-tool-2",
            description="Test tool 2",
            server_id=server_id,
            sensitivity_level=SensitivityLevel.HIGH,
            created_at=datetime(2025, 1, 2, 12, 0, 0),
            extra_metadata={"requires_approval": True},
        ),
    ]


class TestCreateExportEndpoint:
    """Tests for POST /export endpoint."""

    @patch("sark.api.routers.export.get_db")
    @patch("sark.api.routers.export.get_current_user")
    def test_create_export_servers_json(self, mock_get_user, mock_get_db, client, mock_user, mock_servers):
        """Test creating export job for servers in JSON format."""
        mock_get_user.return_value = mock_user

        # Mock database session
        mock_db_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_servers
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_get_db.return_value = mock_db_session

        response = client.post(
            "/export",
            json={
                "format": "json",
                "resource_type": "servers",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "json"
        assert data["resource_type"] == "servers"
        assert data["record_count"] == len(mock_servers)
        assert "exported_at" in data
        assert data["download_url"] == "/api/v1/export/download/servers.json"

    @patch("sark.api.routers.export.get_db")
    @patch("sark.api.routers.export.get_current_user")
    def test_create_export_tools_csv(self, mock_get_user, mock_get_db, client, mock_user, mock_tools):
        """Test creating export job for tools in CSV format."""
        mock_get_user.return_value = mock_user

        # Mock database session
        mock_db_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_tools
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_get_db.return_value = mock_db_session

        response = client.post(
            "/export",
            json={
                "format": "csv",
                "resource_type": "tools",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "csv"
        assert data["resource_type"] == "tools"
        assert data["record_count"] == len(mock_tools)

    @patch("sark.api.routers.export.get_db")
    @patch("sark.api.routers.export.get_current_user")
    def test_create_export_audit_logs(self, mock_get_user, mock_get_db, client, mock_user):
        """Test creating export job for audit logs."""
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = AsyncMock(spec=AsyncSession)

        response = client.post(
            "/export",
            json={
                "format": "json",
                "resource_type": "audit",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["resource_type"] == "audit"
        # Audit logs not yet implemented, so record_count should be 0
        assert data["record_count"] == 0


class TestExportServersCsvEndpoint:
    """Tests for GET /servers.csv endpoint."""

    @patch("sark.api.routers.export.get_db")
    @patch("sark.api.routers.export.get_current_user")
    def test_export_servers_csv_success(self, mock_get_user, mock_get_db, client, mock_user, mock_servers):
        """Test successful export of servers as CSV."""
        mock_get_user.return_value = mock_user

        # Mock database session
        mock_db_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_servers
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_get_db.return_value = mock_db_session

        response = client.get("/servers.csv")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "Content-Disposition" in response.headers
        assert "servers_" in response.headers["Content-Disposition"]
        assert ".csv" in response.headers["Content-Disposition"]

        # Verify CSV content contains server data
        csv_content = response.text
        assert "id,name,description,transport,endpoint,status,sensitivity_level,created_at" in csv_content
        assert "test-server-1" in csv_content
        assert "test-server-2" in csv_content

    @patch("sark.api.routers.export.get_db")
    @patch("sark.api.routers.export.get_current_user")
    def test_export_servers_csv_with_filter(
        self, mock_get_user, mock_get_db, client, mock_user, mock_servers
    ):
        """Test export servers CSV with status filter."""
        mock_get_user.return_value = mock_user

        mock_db_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_servers
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_get_db.return_value = mock_db_session

        response = client.get("/servers.csv?status_filter=active")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"

    @patch("sark.api.routers.export.get_db")
    @patch("sark.api.routers.export.get_current_user")
    def test_export_servers_csv_empty_result(self, mock_get_user, mock_get_db, client, mock_user):
        """Test export servers CSV with no data."""
        mock_get_user.return_value = mock_user

        mock_db_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_get_db.return_value = mock_db_session

        response = client.get("/servers.csv")

        assert response.status_code == 200
        csv_content = response.text
        # Should still have header row
        assert "id,name,description" in csv_content


class TestExportServersJsonEndpoint:
    """Tests for GET /servers.json endpoint."""

    @patch("sark.api.routers.export.get_db")
    @patch("sark.api.routers.export.get_current_user")
    def test_export_servers_json_success(self, mock_get_user, mock_get_db, client, mock_user, mock_servers):
        """Test successful export of servers as JSON."""
        mock_get_user.return_value = mock_user

        mock_db_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_servers
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_get_db.return_value = mock_db_session

        response = client.get("/servers.json")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert "Content-Disposition" in response.headers
        assert ".json" in response.headers["Content-Disposition"]

        data = response.json()
        assert data["export_type"] == "servers"
        assert "exported_at" in data
        assert data["total_records"] == len(mock_servers)
        assert "servers" in data
        assert len(data["servers"]) == len(mock_servers)

        # Verify server data structure
        server = data["servers"][0]
        assert "id" in server
        assert "name" in server
        assert "transport" in server
        assert "status" in server
        assert "sensitivity_level" in server

    @patch("sark.api.routers.export.get_db")
    @patch("sark.api.routers.export.get_current_user")
    def test_export_servers_json_pretty_print(
        self, mock_get_user, mock_get_db, client, mock_user, mock_servers
    ):
        """Test export servers JSON with pretty printing."""
        mock_get_user.return_value = mock_user

        mock_db_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_servers
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_get_db.return_value = mock_db_session

        response = client.get("/servers.json?pretty=true")

        assert response.status_code == 200
        json_content = response.text
        # Pretty-printed JSON should have newlines and indentation
        assert "\n" in json_content
        assert "  " in json_content or "\t" in json_content


class TestExportToolsCsvEndpoint:
    """Tests for GET /tools.csv endpoint."""

    @patch("sark.api.routers.export.get_db")
    @patch("sark.api.routers.export.get_current_user")
    def test_export_tools_csv_success(self, mock_get_user, mock_get_db, client, mock_user, mock_tools):
        """Test successful export of tools as CSV."""
        mock_get_user.return_value = mock_user

        mock_db_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_tools
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_get_db.return_value = mock_db_session

        response = client.get("/tools.csv")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "Content-Disposition" in response.headers
        assert "tools_" in response.headers["Content-Disposition"]

        # Verify CSV content
        csv_content = response.text
        assert "id,name,description,server_id,server_name,sensitivity_level" in csv_content
        assert "test-tool-1" in csv_content
        assert "test-tool-2" in csv_content

    @patch("sark.api.routers.export.get_db")
    @patch("sark.api.routers.export.get_current_user")
    def test_export_tools_csv_handles_null_description(
        self, mock_get_user, mock_get_db, client, mock_user
    ):
        """Test export tools CSV handles null descriptions."""
        mock_get_user.return_value = mock_user

        tool_with_null = MCPTool(
            id=uuid4(),
            name="null-desc-tool",
            description=None,
            server_id=uuid4(),
            sensitivity_level=SensitivityLevel.LOW,
            created_at=datetime.now(),
            extra_metadata=None,
        )

        mock_db_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [tool_with_null]
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_get_db.return_value = mock_db_session

        response = client.get("/tools.csv")

        assert response.status_code == 200
        csv_content = response.text
        assert "null-desc-tool" in csv_content


class TestExportToolsJsonEndpoint:
    """Tests for GET /tools.json endpoint."""

    @patch("sark.api.routers.export.get_db")
    @patch("sark.api.routers.export.get_current_user")
    def test_export_tools_json_success(self, mock_get_user, mock_get_db, client, mock_user, mock_tools):
        """Test successful export of tools as JSON."""
        mock_get_user.return_value = mock_user

        mock_db_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_tools
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_get_db.return_value = mock_db_session

        response = client.get("/tools.json")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        data = response.json()
        assert data["export_type"] == "tools"
        assert "exported_at" in data
        assert data["total_records"] == len(mock_tools)
        assert "tools" in data
        assert len(data["tools"]) == len(mock_tools)

        # Verify tool data structure
        tool = data["tools"][0]
        assert "id" in tool
        assert "name" in tool
        assert "server_id" in tool
        assert "sensitivity_level" in tool

    @patch("sark.api.routers.export.get_db")
    @patch("sark.api.routers.export.get_current_user")
    def test_export_tools_json_with_pretty(self, mock_get_user, mock_get_db, client, mock_user, mock_tools):
        """Test export tools JSON with pretty formatting."""
        mock_get_user.return_value = mock_user

        mock_db_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_tools
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_get_db.return_value = mock_db_session

        response = client.get("/tools.json?pretty=true")

        assert response.status_code == 200
        json_content = response.text
        # Pretty-printed JSON should have formatting
        assert "\n" in json_content


class TestExportErrorHandling:
    """Tests for error handling in export endpoints."""

    @patch("sark.api.routers.export.get_db")
    @patch("sark.api.routers.export.get_current_user")
    def test_export_handles_database_error(self, mock_get_user, mock_get_db, client, mock_user):
        """Test export handles database errors gracefully."""
        mock_get_user.return_value = mock_user

        mock_db_session = AsyncMock(spec=AsyncSession)
        mock_db_session.execute = AsyncMock(side_effect=Exception("Database error"))
        mock_get_db.return_value = mock_db_session

        response = client.get("/servers.csv")

        assert response.status_code == 500
        assert "Failed to export" in response.json()["detail"]


class TestExportRequestModel:
    """Tests for ExportRequest model validation."""

    def test_export_request_valid_formats(self):
        """Test ExportRequest accepts valid formats."""
        from sark.api.routers.export import ExportRequest

        # Test JSON format
        request = ExportRequest(format="json", resource_type="servers")
        assert request.format == "json"

        # Test CSV format
        request = ExportRequest(format="csv", resource_type="tools")
        assert request.format == "csv"

    def test_export_request_valid_resource_types(self):
        """Test ExportRequest accepts valid resource types."""
        from sark.api.routers.export import ExportRequest

        for resource_type in ["servers", "tools", "audit"]:
            request = ExportRequest(format="json", resource_type=resource_type)
            assert request.resource_type == resource_type

    def test_export_request_with_filters(self):
        """Test ExportRequest with optional filters."""
        from sark.api.routers.export import ExportRequest

        request = ExportRequest(
            format="json",
            resource_type="servers",
            filters={"status": "active", "sensitivity": "internal"},
        )
        assert request.filters is not None
        assert request.filters["status"] == "active"

    def test_export_request_with_fields(self):
        """Test ExportRequest with specific fields."""
        from sark.api.routers.export import ExportRequest

        request = ExportRequest(
            format="csv",
            resource_type="servers",
            fields=["id", "name", "status"],
        )
        assert request.fields is not None
        assert len(request.fields) == 3
