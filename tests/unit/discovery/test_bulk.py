"""Unit tests for Bulk Operations Service."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sark.models.mcp_server import ServerStatus
from sark.services.bulk import BulkOperationResult, BulkOperationsService


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock(spec=AsyncSession)
    db.begin_nested = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def mock_audit_db():
    """Mock audit database session."""
    return MagicMock(spec=AsyncSession)


@pytest.fixture
def user_context():
    """Sample user context."""
    return {
        "user_id": uuid4(),
        "user_email": "test@example.com",
        "user_role": "developer",
        "user_teams": ["team1", "team2"],
    }


@pytest.fixture
def bulk_service(mock_db, mock_audit_db, user_context):
    """Bulk operations service with mocked dependencies."""
    service = BulkOperationsService(
        db=mock_db,
        audit_db=mock_audit_db,
        user_id=user_context["user_id"],
        user_email=user_context["user_email"],
        user_role=user_context["user_role"],
        user_teams=user_context["user_teams"],
    )
    return service


@pytest.fixture
def sample_server_data():
    """Sample server registration data."""
    return {
        "name": "test-server",
        "transport": "http",
        "endpoint": "http://localhost:8000",
        "version": "2025-06-18",
        "capabilities": ["tools"],
        "tools": [
            {
                "name": "test-tool",
                "description": "Test tool",
                "parameters": {},
                "sensitivity_level": "medium",
            }
        ],
        "description": "Test server",
        "sensitivity_level": "medium",
        "metadata": {},
    }


class TestBulkOperationResult:
    """Test BulkOperationResult class."""

    def test_initialization(self):
        """Test result initialization."""
        result = BulkOperationResult()
        assert result.total == 0
        assert result.succeeded == []
        assert result.failed == []

    def test_add_success(self):
        """Test adding successful operation."""
        result = BulkOperationResult()
        item = {"server_id": "123", "name": "test"}
        result.add_success(item)

        assert result.success_count == 1
        assert result.succeeded[0] == item

    def test_add_failure(self):
        """Test adding failed operation."""
        result = BulkOperationResult()
        item = {"name": "test"}
        error = "Registration failed"
        result.add_failure(item, error)

        assert result.failure_count == 1
        assert result.failed[0]["name"] == "test"
        assert result.failed[0]["error"] == error

    def test_success_count_property(self):
        """Test success_count property."""
        result = BulkOperationResult()
        result.add_success({"id": "1"})
        result.add_success({"id": "2"})

        assert result.success_count == 2

    def test_failure_count_property(self):
        """Test failure_count property."""
        result = BulkOperationResult()
        result.add_failure({"id": "1"}, "Error 1")
        result.add_failure({"id": "2"}, "Error 2")
        result.add_failure({"id": "3"}, "Error 3")

        assert result.failure_count == 3

    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = BulkOperationResult()
        result.total = 5
        result.add_success({"id": "1"})
        result.add_success({"id": "2"})
        result.add_failure({"id": "3"}, "Error")

        dict_result = result.to_dict()

        assert dict_result["total"] == 5
        assert dict_result["succeeded"] == 2
        assert dict_result["failed"] == 1
        assert len(dict_result["succeeded_items"]) == 2
        assert len(dict_result["failed_items"]) == 1


class TestBulkRegisterServers:
    """Test bulk_register_servers method."""

    @pytest.mark.asyncio
    async def test_bulk_register_best_effort_all_success(
        self, bulk_service, sample_server_data, mock_db
    ):
        """Test best-effort bulk registration with all successes."""
        servers = [
            {**sample_server_data, "name": "server-1"},
            {**sample_server_data, "name": "server-2"},
            {**sample_server_data, "name": "server-3"},
        ]

        # Mock policy evaluation
        with patch.object(
            bulk_service,
            "_batch_evaluate_policies",
            new=AsyncMock(
                return_value=[
                    {"allowed": True, "reason": "OK"},
                    {"allowed": True, "reason": "OK"},
                    {"allowed": True, "reason": "OK"},
                ]
            ),
        ):
            # Mock discovery service
            mock_server = MagicMock()
            mock_server.id = uuid4()
            mock_server.name = "server-1"
            mock_server.status = ServerStatus.REGISTERED

            with (
                patch.object(
                    bulk_service.discovery_service,
                    "register_server",
                    new=AsyncMock(return_value=mock_server),
                ),
                patch.object(bulk_service.audit_service, "log_event", new=AsyncMock()),
            ):
                result = await bulk_service.bulk_register_servers(
                    servers=servers,
                    fail_on_first_error=False,
                )

                assert result.total == 3
                assert result.success_count == 3
                assert result.failure_count == 0

    @pytest.mark.asyncio
    async def test_bulk_register_best_effort_partial_failure(
        self, bulk_service, sample_server_data
    ):
        """Test best-effort bulk registration with partial failures."""
        servers = [
            {**sample_server_data, "name": "server-1"},
            {**sample_server_data, "name": "server-2"},
            {**sample_server_data, "name": "server-3"},
        ]

        # Mock policy evaluation - second server denied
        with patch.object(
            bulk_service,
            "_batch_evaluate_policies",
            new=AsyncMock(
                return_value=[
                    {"allowed": True, "reason": "OK"},
                    {"allowed": False, "reason": "Policy denied"},
                    {"allowed": True, "reason": "OK"},
                ]
            ),
        ):
            mock_server = MagicMock()
            mock_server.id = uuid4()
            mock_server.name = "server-1"
            mock_server.status = ServerStatus.REGISTERED

            with (
                patch.object(
                    bulk_service.discovery_service,
                    "register_server",
                    new=AsyncMock(return_value=mock_server),
                ),
                patch.object(bulk_service.audit_service, "log_event", new=AsyncMock()),
            ):
                result = await bulk_service.bulk_register_servers(
                    servers=servers,
                    fail_on_first_error=False,
                )

                assert result.total == 3
                assert result.success_count == 2
                assert result.failure_count == 1
                assert "Policy denied" in result.failed[0]["error"]

    @pytest.mark.asyncio
    async def test_bulk_register_best_effort_registration_error(
        self, bulk_service, sample_server_data
    ):
        """Test best-effort with registration error."""
        servers = [
            {**sample_server_data, "name": "server-1"},
            {**sample_server_data, "name": "server-2"},
        ]

        with patch.object(
            bulk_service,
            "_batch_evaluate_policies",
            new=AsyncMock(
                return_value=[
                    {"allowed": True, "reason": "OK"},
                    {"allowed": True, "reason": "OK"},
                ]
            ),
        ):
            # First succeeds, second fails
            mock_server = MagicMock()
            mock_server.id = uuid4()
            mock_server.name = "server-1"
            mock_server.status = ServerStatus.REGISTERED

            with (
                patch.object(
                    bulk_service.discovery_service,
                    "register_server",
                    new=AsyncMock(side_effect=[mock_server, Exception("DB error")]),
                ),
                patch.object(bulk_service.audit_service, "log_event", new=AsyncMock()),
            ):
                result = await bulk_service.bulk_register_servers(
                    servers=servers,
                    fail_on_first_error=False,
                )

                assert result.total == 2
                assert result.success_count == 1
                assert result.failure_count == 1

    @pytest.mark.asyncio
    async def test_bulk_register_transactional_all_success(
        self, bulk_service, sample_server_data, mock_db
    ):
        """Test transactional bulk registration with all successes."""
        servers = [
            {**sample_server_data, "name": "server-1"},
            {**sample_server_data, "name": "server-2"},
        ]

        # Mock transaction context manager
        mock_transaction = MagicMock()
        mock_transaction.__aenter__ = AsyncMock()
        mock_transaction.__aexit__ = AsyncMock()
        mock_db.begin_nested.return_value = mock_transaction

        with patch.object(
            bulk_service,
            "_batch_evaluate_policies",
            new=AsyncMock(
                return_value=[
                    {"allowed": True, "reason": "OK"},
                    {"allowed": True, "reason": "OK"},
                ]
            ),
        ):
            mock_server = MagicMock()
            mock_server.id = uuid4()
            mock_server.name = "server-1"
            mock_server.status = ServerStatus.REGISTERED

            with (
                patch.object(
                    bulk_service.discovery_service,
                    "register_server",
                    new=AsyncMock(return_value=mock_server),
                ),
                patch.object(bulk_service.audit_service, "log_event", new=AsyncMock()),
            ):
                result = await bulk_service.bulk_register_servers(
                    servers=servers,
                    fail_on_first_error=True,
                )

                assert result.total == 2
                assert result.success_count == 2
                assert result.failure_count == 0

    @pytest.mark.asyncio
    async def test_bulk_register_transactional_policy_denied(
        self, bulk_service, sample_server_data, mock_db
    ):
        """Test transactional registration with policy denial."""
        servers = [
            {**sample_server_data, "name": "server-1"},
            {**sample_server_data, "name": "server-2"},
        ]

        # Second server denied by policy
        with patch.object(
            bulk_service,
            "_batch_evaluate_policies",
            new=AsyncMock(
                return_value=[
                    {"allowed": True, "reason": "OK"},
                    {"allowed": False, "reason": "Insufficient permissions"},
                ]
            ),
        ):
            result = await bulk_service.bulk_register_servers(
                servers=servers,
                fail_on_first_error=True,
            )

            # All should fail due to transactional nature
            assert result.total == 2
            assert result.success_count == 0
            assert result.failure_count == 2

    @pytest.mark.asyncio
    async def test_bulk_register_transactional_registration_error(
        self, bulk_service, sample_server_data, mock_db
    ):
        """Test transactional registration with error during registration."""
        servers = [
            {**sample_server_data, "name": "server-1"},
            {**sample_server_data, "name": "server-2"},
        ]

        mock_transaction = MagicMock()
        mock_transaction.__aenter__ = AsyncMock()
        mock_transaction.__aexit__ = AsyncMock(return_value=None)
        mock_db.begin_nested.return_value = mock_transaction

        with patch.object(
            bulk_service,
            "_batch_evaluate_policies",
            new=AsyncMock(
                return_value=[
                    {"allowed": True, "reason": "OK"},
                    {"allowed": True, "reason": "OK"},
                ]
            ),
        ):
            # Make register_server raise an exception
            with patch.object(
                bulk_service.discovery_service,
                "register_server",
                new=AsyncMock(side_effect=Exception("DB error")),
            ):
                result = await bulk_service.bulk_register_servers(
                    servers=servers,
                    fail_on_first_error=True,
                )

                # All should fail due to transaction rollback
                assert result.total == 2
                assert result.success_count == 0
                assert result.failure_count == 2
                mock_db.rollback.assert_awaited()


class TestBulkUpdateServerStatus:
    """Test bulk_update_server_status method."""

    @pytest.mark.asyncio
    async def test_bulk_update_status_best_effort_all_success(self, bulk_service, mock_db):
        """Test best-effort status update with all successes."""
        updates = [
            {"server_id": str(uuid4()), "status": "active"},
            {"server_id": str(uuid4()), "status": "inactive"},
            {"server_id": str(uuid4()), "status": "active"},
        ]

        mock_server = MagicMock()
        mock_server.id = uuid4()
        mock_server.name = "test-server"
        mock_server.status = ServerStatus.ACTIVE

        with (
            patch.object(
                bulk_service.discovery_service,
                "update_server_status",
                new=AsyncMock(return_value=mock_server),
            ),
            patch.object(bulk_service.audit_service, "log_event", new=AsyncMock()),
        ):
            result = await bulk_service.bulk_update_server_status(
                updates=updates,
                fail_on_first_error=False,
            )

            assert result.total == 3
            assert result.success_count == 3
            assert result.failure_count == 0

    @pytest.mark.asyncio
    async def test_bulk_update_status_best_effort_partial_failure(self, bulk_service):
        """Test best-effort status update with partial failures."""
        updates = [
            {"server_id": str(uuid4()), "status": "active"},
            {"server_id": "invalid-uuid", "status": "active"},
            {"server_id": str(uuid4()), "status": "inactive"},
        ]

        mock_server = MagicMock()
        mock_server.id = uuid4()
        mock_server.name = "test-server"
        mock_server.status = ServerStatus.ACTIVE

        def update_side_effect(server_id, status):
            # Simulate error for invalid UUID
            if str(server_id).startswith("invalid"):
                raise ValueError("Invalid UUID")
            return mock_server

        with (
            patch.object(
                bulk_service.discovery_service,
                "update_server_status",
                new=AsyncMock(side_effect=update_side_effect),
            ),
            patch.object(bulk_service.audit_service, "log_event", new=AsyncMock()),
        ):
            result = await bulk_service.bulk_update_server_status(
                updates=updates,
                fail_on_first_error=False,
            )

            assert result.total == 3
            assert result.success_count == 2
            assert result.failure_count == 1

    @pytest.mark.asyncio
    async def test_bulk_update_status_transactional_all_success(self, bulk_service, mock_db):
        """Test transactional status update with all successes."""
        updates = [
            {"server_id": str(uuid4()), "status": "active"},
            {"server_id": str(uuid4()), "status": "inactive"},
        ]

        mock_transaction = MagicMock()
        mock_transaction.__aenter__ = AsyncMock()
        mock_transaction.__aexit__ = AsyncMock()
        mock_db.begin_nested.return_value = mock_transaction

        mock_server = MagicMock()
        mock_server.id = uuid4()
        mock_server.name = "test-server"
        mock_server.status = ServerStatus.ACTIVE

        with (
            patch.object(
                bulk_service.discovery_service,
                "update_server_status",
                new=AsyncMock(return_value=mock_server),
            ),
            patch.object(bulk_service.audit_service, "log_event", new=AsyncMock()),
        ):
            result = await bulk_service.bulk_update_server_status(
                updates=updates,
                fail_on_first_error=True,
            )

            assert result.total == 2
            assert result.success_count == 2
            assert result.failure_count == 0

    @pytest.mark.asyncio
    async def test_bulk_update_status_transactional_error(self, bulk_service, mock_db):
        """Test transactional status update with error."""
        updates = [
            {"server_id": str(uuid4()), "status": "active"},
            {"server_id": str(uuid4()), "status": "inactive"},
        ]

        mock_transaction = MagicMock()
        mock_transaction.__aenter__ = AsyncMock()
        mock_transaction.__aexit__ = AsyncMock(return_value=None)
        mock_db.begin_nested.return_value = mock_transaction

        # Make update_server_status raise an exception
        with patch.object(
            bulk_service.discovery_service,
            "update_server_status",
            new=AsyncMock(side_effect=Exception("Transaction error")),
        ):
            result = await bulk_service.bulk_update_server_status(
                updates=updates,
                fail_on_first_error=True,
            )

            # All should fail due to transaction rollback
            assert result.total == 2
            assert result.success_count == 0
            assert result.failure_count == 2
            mock_db.rollback.assert_awaited_once()


class TestBatchEvaluatePolicies:
    """Test _batch_evaluate_policies method."""

    @pytest.mark.asyncio
    async def test_batch_evaluate_policies_all_allowed(self, bulk_service):
        """Test batch policy evaluation with all allowed."""
        items = [
            {"name": "server-1", "sensitivity_level": "low", "transport": "http"},
            {"name": "server-2", "sensitivity_level": "medium", "transport": "http"},
            {"name": "server-3", "sensitivity_level": "high", "transport": "http"},
        ]

        with patch.object(
            bulk_service.opa_client,
            "authorize",
            new=AsyncMock(return_value=True),
        ):
            results = await bulk_service._batch_evaluate_policies(
                items=items,
                action="server:register",
            )

            assert len(results) == 3
            assert all(r["allowed"] for r in results)

    @pytest.mark.asyncio
    async def test_batch_evaluate_policies_some_denied(self, bulk_service):
        """Test batch policy evaluation with some denied."""
        items = [
            {"name": "server-1", "sensitivity_level": "low"},
            {"name": "server-2", "sensitivity_level": "critical"},
            {"name": "server-3", "sensitivity_level": "medium"},
        ]

        # Deny critical sensitivity
        def authorize_side_effect(user_id, action, resource, context):
            return context.get("sensitivity_level") != "critical"

        with patch.object(
            bulk_service.opa_client,
            "authorize",
            new=AsyncMock(side_effect=authorize_side_effect),
        ):
            results = await bulk_service._batch_evaluate_policies(
                items=items,
                action="server:register",
            )

            assert len(results) == 3
            assert results[0]["allowed"] is True
            assert results[1]["allowed"] is False
            assert results[2]["allowed"] is True

    @pytest.mark.asyncio
    async def test_batch_evaluate_policies_evaluation_error(self, bulk_service):
        """Test batch policy evaluation with evaluation error."""
        items = [
            {"name": "server-1"},
            {"name": "server-2"},
        ]

        # Simulate OPA error
        with patch.object(
            bulk_service.opa_client,
            "authorize",
            new=AsyncMock(side_effect=Exception("OPA unavailable")),
        ):
            results = await bulk_service._batch_evaluate_policies(
                items=items,
                action="server:register",
            )

            # All should be denied due to fail-closed
            assert len(results) == 2
            assert all(not r["allowed"] for r in results)
            assert all("Policy evaluation error" in r["reason"] for r in results)

    @pytest.mark.asyncio
    async def test_batch_evaluate_policies_includes_context(self, bulk_service, user_context):
        """Test that batch policy evaluation includes user context."""
        items = [{"name": "test-server", "sensitivity_level": "high", "transport": "http"}]

        mock_authorize = AsyncMock(return_value=True)

        with patch.object(
            bulk_service.opa_client,
            "authorize",
            new=mock_authorize,
        ):
            await bulk_service._batch_evaluate_policies(
                items=items,
                action="server:register",
            )

            # Verify authorize was called with correct context
            mock_authorize.assert_awaited_once()
            call_kwargs = mock_authorize.call_args[1]
            assert call_kwargs["user_id"] == str(user_context["user_id"])
            assert call_kwargs["action"] == "server:register"
            assert call_kwargs["context"]["user_role"] == user_context["user_role"]
            assert call_kwargs["context"]["user_teams"] == user_context["user_teams"]
