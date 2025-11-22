"""Integration tests for API pagination."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from sark.models.mcp_server import MCPServer, SensitivityLevel, ServerStatus, TransportType


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    from sark.api.main import app

    return TestClient(app)


@pytest.fixture
def mock_servers():
    """Create mock server data."""
    servers = []
    base_time = datetime.now(UTC)

    for i in range(100):
        server = MCPServer(
            id=uuid4(),
            name=f"test-server-{i}",
            description=f"Test server {i}",
            transport=TransportType.HTTP,
            endpoint=f"http://test-{i}.example.com",
            mcp_version="2025-06-18",
            capabilities=["tools"],
            sensitivity_level=SensitivityLevel.MEDIUM,
            status=ServerStatus.ACTIVE,
            created_at=base_time,
        )
        servers.append(server)

    return servers


class TestServerListPagination:
    """Test server list endpoint pagination."""

    def test_list_servers_default_pagination(self, client: TestClient) -> None:
        """Test listing servers with default pagination parameters."""
        # Mock the database and discovery service
        with patch("sark.api.routers.servers.DiscoveryService") as mock_service:
            # Create mock discovery service instance
            mock_instance = MagicMock()
            mock_service.return_value = mock_instance

            # Mock paginated response
            mock_servers = [
                MagicMock(
                    id=uuid4(),
                    name=f"server-{i}",
                    transport=TransportType.HTTP,
                    status=ServerStatus.ACTIVE,
                    sensitivity_level=SensitivityLevel.MEDIUM,
                    created_at=datetime.now(UTC),
                )
                for i in range(50)
            ]

            mock_instance.list_servers_paginated = AsyncMock(
                return_value=(mock_servers, "next_cursor_123", True, None)
            )

            # Make request
            response = client.get("/api/servers/")

            # Verify response
            assert response.status_code == 200
            data = response.json()

            assert "items" in data
            assert "next_cursor" in data
            assert "has_more" in data
            assert len(data["items"]) == 50
            assert data["next_cursor"] == "next_cursor_123"
            assert data["has_more"] is True

    def test_list_servers_custom_limit(self, client: TestClient) -> None:
        """Test listing servers with custom page limit."""
        with patch("sark.api.routers.servers.DiscoveryService") as mock_service:
            mock_instance = MagicMock()
            mock_service.return_value = mock_instance

            mock_servers = [
                MagicMock(
                    id=uuid4(),
                    name=f"server-{i}",
                    transport=TransportType.HTTP,
                    status=ServerStatus.ACTIVE,
                    sensitivity_level=SensitivityLevel.MEDIUM,
                    created_at=datetime.now(UTC),
                )
                for i in range(10)
            ]

            mock_instance.list_servers_paginated = AsyncMock(
                return_value=(mock_servers, None, False, None)
            )

            # Make request with custom limit
            response = client.get("/api/servers/?limit=10")

            assert response.status_code == 200
            data = response.json()

            assert len(data["items"]) == 10
            assert data["next_cursor"] is None
            assert data["has_more"] is False

    def test_list_servers_with_cursor(self, client: TestClient) -> None:
        """Test listing servers with pagination cursor."""
        with patch("sark.api.routers.servers.DiscoveryService") as mock_service:
            mock_instance = MagicMock()
            mock_service.return_value = mock_instance

            mock_servers = [
                MagicMock(
                    id=uuid4(),
                    name=f"server-{i}",
                    transport=TransportType.HTTP,
                    status=ServerStatus.ACTIVE,
                    sensitivity_level=SensitivityLevel.MEDIUM,
                    created_at=datetime.now(UTC),
                )
                for i in range(50)
            ]

            mock_instance.list_servers_paginated = AsyncMock(
                return_value=(mock_servers, "next_cursor_456", True, None)
            )

            # Make request with cursor
            response = client.get("/api/servers/?cursor=cursor_123")

            assert response.status_code == 200
            data = response.json()

            assert data["next_cursor"] == "next_cursor_456"
            assert data["has_more"] is True

    def test_list_servers_ascending_order(self, client: TestClient) -> None:
        """Test listing servers with ascending sort order."""
        with patch("sark.api.routers.servers.DiscoveryService") as mock_service:
            mock_instance = MagicMock()
            mock_service.return_value = mock_instance

            mock_servers = [
                MagicMock(
                    id=uuid4(),
                    name=f"server-{i}",
                    transport=TransportType.HTTP,
                    status=ServerStatus.ACTIVE,
                    sensitivity_level=SensitivityLevel.MEDIUM,
                    created_at=datetime.now(UTC),
                )
                for i in range(25)
            ]

            mock_instance.list_servers_paginated = AsyncMock(
                return_value=(mock_servers, None, False, None)
            )

            # Make request with ascending sort
            response = client.get("/api/servers/?sort_order=asc")

            assert response.status_code == 200
            data = response.json()

            assert len(data["items"]) == 25

    def test_list_servers_with_total(self, client: TestClient) -> None:
        """Test listing servers with total count."""
        with patch("sark.api.routers.servers.DiscoveryService") as mock_service:
            mock_instance = MagicMock()
            mock_service.return_value = mock_instance

            mock_servers = [
                MagicMock(
                    id=uuid4(),
                    name=f"server-{i}",
                    transport=TransportType.HTTP,
                    status=ServerStatus.ACTIVE,
                    sensitivity_level=SensitivityLevel.MEDIUM,
                    created_at=datetime.now(UTC),
                )
                for i in range(50)
            ]

            mock_instance.list_servers_paginated = AsyncMock(
                return_value=(mock_servers, "cursor_789", True, 250)
            )

            # Make request with total count
            response = client.get("/api/servers/?include_total=true")

            assert response.status_code == 200
            data = response.json()

            assert data["total"] == 250
            assert data["has_more"] is True

    def test_list_servers_invalid_limit_too_low(self, client: TestClient) -> None:
        """Test listing servers with invalid limit (too low)."""
        response = client.get("/api/servers/?limit=0")

        assert response.status_code == 422  # Validation error

    def test_list_servers_invalid_limit_too_high(self, client: TestClient) -> None:
        """Test listing servers with invalid limit (too high)."""
        response = client.get("/api/servers/?limit=201")

        assert response.status_code == 422  # Validation error

    def test_list_servers_invalid_sort_order(self, client: TestClient) -> None:
        """Test listing servers with invalid sort order."""
        response = client.get("/api/servers/?sort_order=invalid")

        assert response.status_code == 422  # Validation error

    def test_list_servers_empty_results(self, client: TestClient) -> None:
        """Test listing servers with no results."""
        with patch("sark.api.routers.servers.DiscoveryService") as mock_service:
            mock_instance = MagicMock()
            mock_service.return_value = mock_instance

            mock_instance.list_servers_paginated = AsyncMock(return_value=([], None, False, 0))

            response = client.get("/api/servers/")

            assert response.status_code == 200
            data = response.json()

            assert len(data["items"]) == 0
            assert data["next_cursor"] is None
            assert data["has_more"] is False

    def test_list_servers_response_schema(self, client: TestClient) -> None:
        """Test that server list response matches expected schema."""
        with patch("sark.api.routers.servers.DiscoveryService") as mock_service:
            mock_instance = MagicMock()
            mock_service.return_value = mock_instance

            test_id = uuid4()
            test_time = datetime.now(UTC)

            mock_server = MagicMock(
                id=test_id,
                name="test-server",
                transport=TransportType.HTTP,
                status=ServerStatus.ACTIVE,
                sensitivity_level=SensitivityLevel.HIGH,
                created_at=test_time,
            )

            mock_instance.list_servers_paginated = AsyncMock(
                return_value=([mock_server], None, False, None)
            )

            response = client.get("/api/servers/")

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "items" in data
            assert "next_cursor" in data
            assert "has_more" in data
            assert "total" in data

            # Verify item structure
            item = data["items"][0]
            assert item["id"] == str(test_id)
            assert item["name"] == "test-server"
            assert item["transport"] == "http"
            assert item["status"] == "active"
            assert item["sensitivity_level"] == "high"
            assert "created_at" in item

    def test_list_servers_multiple_pages(self, client: TestClient) -> None:
        """Test pagination across multiple pages."""
        with patch("sark.api.routers.servers.DiscoveryService") as mock_service:
            mock_instance = MagicMock()
            mock_service.return_value = mock_instance

            # First page - 50 items with cursor
            first_page_servers = [
                MagicMock(
                    id=uuid4(),
                    name=f"server-{i}",
                    transport=TransportType.HTTP,
                    status=ServerStatus.ACTIVE,
                    sensitivity_level=SensitivityLevel.MEDIUM,
                    created_at=datetime.now(UTC),
                )
                for i in range(50)
            ]

            # Second page - 30 items, no more pages
            second_page_servers = [
                MagicMock(
                    id=uuid4(),
                    name=f"server-{i}",
                    transport=TransportType.HTTP,
                    status=ServerStatus.ACTIVE,
                    sensitivity_level=SensitivityLevel.MEDIUM,
                    created_at=datetime.now(UTC),
                )
                for i in range(50, 80)
            ]

            # Configure mock to return different results for different calls
            mock_instance.list_servers_paginated = AsyncMock(
                side_effect=[
                    (first_page_servers, "cursor_page2", True, None),
                    (second_page_servers, None, False, None),
                ]
            )

            # Get first page
            response1 = client.get("/api/servers/")
            assert response1.status_code == 200
            data1 = response1.json()

            assert len(data1["items"]) == 50
            assert data1["has_more"] is True
            cursor = data1["next_cursor"]

            # Get second page
            response2 = client.get(f"/api/servers/?cursor={cursor}")
            assert response2.status_code == 200
            data2 = response2.json()

            assert len(data2["items"]) == 30
            assert data2["has_more"] is False
            assert data2["next_cursor"] is None

    def test_openapi_schema_includes_pagination(self, client: TestClient) -> None:
        """Test that OpenAPI schema includes pagination models."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()

        # Verify pagination query parameters are documented
        servers_path = schema["paths"].get("/api/servers/", {}).get("get", {})
        parameters = servers_path.get("parameters", [])

        param_names = [p["name"] for p in parameters]
        assert "limit" in param_names
        assert "cursor" in param_names
        assert "sort_order" in param_names

        # Verify PaginatedResponse schema exists
        components = schema.get("components", {}).get("schemas", {})
        assert any("Paginated" in key for key in components.keys())
