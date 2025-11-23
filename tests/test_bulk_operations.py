"""Tests for bulk operations service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from sark.models.mcp_server import MCPServer, SensitivityLevel, ServerStatus, TransportType
from sark.services.bulk import BulkOperationResult, BulkOperationsService


class TestBulkOperationResult:
    """Test BulkOperationResult class."""

    def test_initial_state(self) -> None:
        """Test initial state of result."""
        result = BulkOperationResult()

        assert result.success_count == 0
        assert result.failure_count == 0
        assert result.total == 0

    def test_add_success(self) -> None:
        """Test adding successful operation."""
        result = BulkOperationResult()
        result.add_success({"server_id": "123", "name": "test"})

        assert result.success_count == 1
        assert result.failure_count == 0
        assert len(result.succeeded) == 1

    def test_add_failure(self) -> None:
        """Test adding failed operation."""
        result = BulkOperationResult()
        result.add_failure({"name": "test"}, "Error message")

        assert result.success_count == 0
        assert result.failure_count == 1
        assert len(result.failed) == 1
        assert result.failed[0]["error"] == "Error message"

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        result = BulkOperationResult()
        result.total = 2
        result.add_success({"server_id": "123"})
        result.add_failure({"name": "test"}, "Error")

        data = result.to_dict()

        assert data["total"] == 2
        assert data["succeeded"] == 1
        assert data["failed"] == 1
        assert len(data["succeeded_items"]) == 1
        assert len(data["failed_items"]) == 1


class TestBulkOperationsService:
    """Test BulkOperationsService class."""

    @pytest.fixture
    def bulk_service(self) -> BulkOperationsService:
        """Create bulk operations service for testing."""
        mock_db = AsyncMock()
        mock_audit_db = AsyncMock()

        service = BulkOperationsService(
            db=mock_db,
            audit_db=mock_audit_db,
            user_id=uuid4(),
            user_email="test@example.com",
            user_role="admin",
            user_teams=["team1"],
        )

        return service

    @pytest.mark.asyncio
    async def test_bulk_register_best_effort_all_success(self, bulk_service) -> None:
        """Test bulk registration in best-effort mode with all success."""
        servers = [
            {
                "name": f"server-{i}",
                "transport": "http",
                "endpoint": f"http://server-{i}.com",
                "capabilities": [],
                "tools": [],
            }
            for i in range(3)
        ]

        # Mock policy evaluation - all approved
        bulk_service.opa_client.authorize = AsyncMock(return_value=True)

        # Mock server registration
        async def mock_register(**kwargs):
            return MCPServer(
                id=uuid4(),
                name=kwargs["name"],
                transport=kwargs["transport"],
                status=ServerStatus.REGISTERED,
                sensitivity_level=SensitivityLevel.MEDIUM,
                mcp_version="2025-06-18",
                capabilities=[],
                created_at=datetime.now(UTC),
            )

        bulk_service.discovery_service.register_server = AsyncMock(side_effect=mock_register)
        bulk_service.audit_service.log_event = AsyncMock()

        # Execute bulk registration
        result = await bulk_service.bulk_register_servers(
            servers=servers, fail_on_first_error=False
        )

        # Verify results
        assert result.total == 3
        assert result.success_count == 3
        assert result.failure_count == 0

    @pytest.mark.asyncio
    async def test_bulk_register_best_effort_partial_success(self, bulk_service) -> None:
        """Test bulk registration in best-effort mode with partial success."""
        servers = [
            {"name": "server-1", "transport": "http", "endpoint": "http://s1.com", "tools": []},
            {"name": "server-2", "transport": "http", "endpoint": "http://s2.com", "tools": []},
            {"name": "server-3", "transport": "http", "endpoint": "http://s3.com", "tools": []},
        ]

        # Mock policy evaluation - first two approved, third denied
        bulk_service.opa_client.authorize = AsyncMock(side_effect=[True, True, False])

        # Mock server registration
        async def mock_register(**kwargs):
            return MCPServer(
                id=uuid4(),
                name=kwargs["name"],
                transport=kwargs["transport"],
                status=ServerStatus.REGISTERED,
                sensitivity_level=SensitivityLevel.MEDIUM,
                mcp_version="2025-06-18",
                capabilities=[],
                created_at=datetime.now(UTC),
            )

        bulk_service.discovery_service.register_server = AsyncMock(side_effect=mock_register)
        bulk_service.audit_service.log_event = AsyncMock()

        # Execute bulk registration
        result = await bulk_service.bulk_register_servers(
            servers=servers, fail_on_first_error=False
        )

        # Verify results
        assert result.total == 3
        assert result.success_count == 2
        assert result.failure_count == 1
        assert "Policy denied" in result.failed[0]["error"]

    @pytest.mark.asyncio
    async def test_bulk_register_transactional_all_success(self, bulk_service) -> None:
        """Test bulk registration in transactional mode with all success."""
        servers = [
            {
                "name": f"server-{i}",
                "transport": "http",
                "endpoint": f"http://s{i}.com",
                "tools": [],
            }
            for i in range(3)
        ]

        # Mock policy evaluation - all approved
        bulk_service.opa_client.authorize = AsyncMock(return_value=True)

        # Mock server registration
        async def mock_register(**kwargs):
            return MCPServer(
                id=uuid4(),
                name=kwargs["name"],
                transport=kwargs["transport"],
                status=ServerStatus.REGISTERED,
                sensitivity_level=SensitivityLevel.MEDIUM,
                mcp_version="2025-06-18",
                capabilities=[],
                created_at=datetime.now(UTC),
            )

        bulk_service.discovery_service.register_server = AsyncMock(side_effect=mock_register)
        bulk_service.audit_service.log_event = AsyncMock()

        # Mock transaction properly
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_context)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        bulk_service.db.begin_nested = MagicMock(return_value=mock_context)
        bulk_service.db.commit = AsyncMock()

        # Execute bulk registration
        result = await bulk_service.bulk_register_servers(servers=servers, fail_on_first_error=True)

        # Verify results
        assert result.total == 3
        assert result.success_count == 3
        assert result.failure_count == 0

    @pytest.mark.asyncio
    async def test_bulk_register_transactional_policy_denied(self, bulk_service) -> None:
        """Test bulk registration in transactional mode with policy denial."""
        servers = [
            {"name": "server-1", "transport": "http", "endpoint": "http://s1.com", "tools": []},
            {"name": "server-2", "transport": "http", "endpoint": "http://s2.com", "tools": []},
        ]

        # Mock policy evaluation - second one denied
        bulk_service.opa_client.authorize = AsyncMock(side_effect=[True, False])

        # Execute bulk registration
        result = await bulk_service.bulk_register_servers(servers=servers, fail_on_first_error=True)

        # Verify results - ALL should fail due to policy denial
        assert result.total == 2
        assert result.success_count == 0
        assert result.failure_count == 2

    @pytest.mark.asyncio
    async def test_bulk_register_transactional_rollback_on_error(self, bulk_service) -> None:
        """Test transaction rollback on registration error."""
        servers = [
            {"name": "server-1", "transport": "http", "endpoint": "http://s1.com", "tools": []},
            {"name": "server-2", "transport": "http", "endpoint": "http://s2.com", "tools": []},
        ]

        # Mock policy evaluation - all approved
        bulk_service.opa_client.authorize = AsyncMock(return_value=True)

        # Mock server registration - second one fails
        registration_count = 0

        async def mock_register(**kwargs):
            nonlocal registration_count
            registration_count += 1
            if registration_count == 2:
                raise Exception("Database error")
            return MCPServer(
                id=uuid4(),
                name=kwargs["name"],
                transport=kwargs["transport"],
                status=ServerStatus.REGISTERED,
                sensitivity_level=SensitivityLevel.MEDIUM,
                mcp_version="2025-06-18",
                capabilities=[],
                created_at=datetime.now(UTC),
            )

        bulk_service.discovery_service.register_server = AsyncMock(side_effect=mock_register)
        bulk_service.audit_service.log_event = AsyncMock()

        # Mock transaction with exception
        mock_nested = MagicMock()
        mock_nested.__aenter__ = AsyncMock(return_value=mock_nested)
        mock_nested.__aexit__ = AsyncMock()
        bulk_service.db.begin_nested = AsyncMock(return_value=mock_nested)
        bulk_service.db.commit = AsyncMock()
        bulk_service.db.rollback = AsyncMock()

        # Execute bulk registration
        result = await bulk_service.bulk_register_servers(servers=servers, fail_on_first_error=True)

        # Verify results - all should fail due to rollback
        assert result.total == 2
        assert result.success_count == 0
        assert result.failure_count == 2
        assert "Transaction failed" in result.failed[0]["error"]

        # Verify rollback was called
        bulk_service.db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_update_status_best_effort(self, bulk_service) -> None:
        """Test bulk status update in best-effort mode."""
        updates = [
            {"server_id": str(uuid4()), "status": "active"},
            {"server_id": str(uuid4()), "status": "inactive"},
        ]

        # Mock status update
        async def mock_update(server_id, status):
            return MCPServer(
                id=server_id,
                name=f"server-{server_id}",
                transport=TransportType.HTTP,
                status=status,
                sensitivity_level=SensitivityLevel.MEDIUM,
                mcp_version="2025-06-18",
                capabilities=[],
                created_at=datetime.now(UTC),
            )

        bulk_service.discovery_service.update_server_status = AsyncMock(side_effect=mock_update)
        bulk_service.audit_service.log_event = AsyncMock()

        # Execute bulk update
        result = await bulk_service.bulk_update_server_status(
            updates=updates, fail_on_first_error=False
        )

        # Verify results
        assert result.total == 2
        assert result.success_count == 2
        assert result.failure_count == 0

    @pytest.mark.asyncio
    async def test_bulk_update_status_best_effort_partial_failure(self, bulk_service) -> None:
        """Test bulk status update with partial failure."""
        server_id_1 = uuid4()
        server_id_2 = uuid4()  # Will fail
        server_id_3 = uuid4()

        updates = [
            {"server_id": str(server_id_1), "status": "active"},
            {"server_id": str(server_id_2), "status": "inactive"},
            {"server_id": str(server_id_3), "status": "active"},
        ]

        # Mock status update - second one fails
        call_count = 0

        async def mock_update(server_id, status):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise ValueError("Invalid server ID")
            return MCPServer(
                id=server_id,
                name=f"server-{server_id}",
                transport=TransportType.HTTP,
                status=status,
                sensitivity_level=SensitivityLevel.MEDIUM,
                mcp_version="2025-06-18",
                capabilities=[],
                created_at=datetime.now(UTC),
            )

        bulk_service.discovery_service.update_server_status = AsyncMock(side_effect=mock_update)
        bulk_service.audit_service.log_event = AsyncMock()

        # Execute bulk update
        result = await bulk_service.bulk_update_server_status(
            updates=updates, fail_on_first_error=False
        )

        # Verify results
        assert result.total == 3
        assert result.success_count == 2
        assert result.failure_count == 1

    @pytest.mark.asyncio
    async def test_batch_policy_evaluation(self, bulk_service) -> None:
        """Test batch policy evaluation."""
        items = [
            {"name": "server-1", "sensitivity_level": "high"},
            {"name": "server-2", "sensitivity_level": "medium"},
            {"name": "server-3", "sensitivity_level": "critical"},
        ]

        # Mock policy evaluation
        bulk_service.opa_client.authorize = AsyncMock(side_effect=[True, True, False])

        # Execute batch evaluation
        results = await bulk_service._batch_evaluate_policies(items, action="server:register")

        # Verify results
        assert len(results) == 3
        assert results[0]["allowed"] is True
        assert results[1]["allowed"] is True
        assert results[2]["allowed"] is False

    @pytest.mark.asyncio
    async def test_batch_policy_evaluation_error(self, bulk_service) -> None:
        """Test batch policy evaluation with error."""
        items = [
            {"name": "server-1", "sensitivity_level": "high"},
            {"name": "server-2", "sensitivity_level": "medium"},
        ]

        # Mock policy evaluation - second one throws error
        bulk_service.opa_client.authorize = AsyncMock(
            side_effect=[True, Exception("Policy service unavailable")]
        )

        # Execute batch evaluation
        results = await bulk_service._batch_evaluate_policies(items, action="server:register")

        # Verify results
        assert len(results) == 2
        assert results[0]["allowed"] is True
        assert results[1]["allowed"] is False
        assert "Policy evaluation error" in results[1]["reason"]
