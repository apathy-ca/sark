"""Bulk operations service for efficient batch processing.

This module provides bulk operations with transaction support,
batch policy evaluation, and comprehensive error handling.
"""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from sark.models.audit import AuditEventType, SeverityLevel
from sark.models.mcp_server import MCPServer, ServerStatus, TransportType
from sark.services.audit import AuditService
from sark.services.discovery import DiscoveryService
from sark.services.policy import OPAClient

logger = structlog.get_logger()


class BulkOperationResult:
    """Result of a bulk operation with success/failure tracking."""

    def __init__(self) -> None:
        """Initialize bulk operation result."""
        self.succeeded: list[dict[str, Any]] = []
        self.failed: list[dict[str, Any]] = []
        self.total: int = 0

    def add_success(self, item: dict[str, Any]) -> None:
        """Add successful operation."""
        self.succeeded.append(item)

    def add_failure(self, item: dict[str, Any], error: str) -> None:
        """Add failed operation."""
        self.failed.append({**item, "error": error})

    @property
    def success_count(self) -> int:
        """Get count of successful operations."""
        return len(self.succeeded)

    @property
    def failure_count(self) -> int:
        """Get count of failed operations."""
        return len(self.failed)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "total": self.total,
            "succeeded": self.success_count,
            "failed": self.failure_count,
            "succeeded_items": self.succeeded,
            "failed_items": self.failed,
        }


class BulkOperationsService:
    """Service for bulk operations on MCP servers."""

    def __init__(
        self,
        db: AsyncSession,
        audit_db: AsyncSession,
        user_id: UUID,
        user_email: str,
        user_role: str,
        user_teams: list[str],
    ) -> None:
        """Initialize bulk operations service.

        Args:
            db: Database session for main operations
            audit_db: Database session for audit logging
            user_id: Current user ID
            user_email: Current user email
            user_role: Current user role
            user_teams: Current user teams
        """
        self.db = db
        self.audit_db = audit_db
        self.user_id = user_id
        self.user_email = user_email
        self.user_role = user_role
        self.user_teams = user_teams
        self.discovery_service = DiscoveryService(db)
        self.audit_service = AuditService(audit_db)
        self.opa_client = OPAClient()

    async def bulk_register_servers(
        self,
        servers: list[dict[str, Any]],
        fail_on_first_error: bool = False,
    ) -> BulkOperationResult:
        """
        Bulk register MCP servers with transaction support.

        Args:
            servers: List of server registration requests
            fail_on_first_error: If True, rollback all on first error

        Returns:
            BulkOperationResult with success/failure details
        """
        result = BulkOperationResult()
        result.total = len(servers)

        if fail_on_first_error:
            # All-or-nothing: use transaction
            return await self._bulk_register_transactional(servers)
        else:
            # Best-effort: process individually
            return await self._bulk_register_best_effort(servers)

    async def _bulk_register_transactional(
        self,
        servers: list[dict[str, Any]],
    ) -> BulkOperationResult:
        """Register servers in a single transaction (all-or-nothing).

        Args:
            servers: List of server registration requests

        Returns:
            BulkOperationResult
        """
        result = BulkOperationResult()
        result.total = len(servers)

        try:
            # Batch policy evaluation first
            policy_results = await self._batch_evaluate_policies(servers, action="server:register")

            # Check if any denied
            denied = [r for r in policy_results if not r["allowed"]]
            if denied:
                for server_data, policy_result in zip(servers, policy_results, strict=True):
                    if not policy_result["allowed"]:
                        result.add_failure(
                            {"name": server_data.get("name")},
                            f"Policy denied: {policy_result.get('reason', 'Unknown')}",
                        )
                    else:
                        result.add_failure(
                            {"name": server_data.get("name")},
                            "Transaction rolled back due to policy failures",
                        )
                return result

            # All policies approved, register servers in transaction
            async with self.db.begin_nested():
                for server_data in servers:
                    try:
                        server = await self.discovery_service.register_server(
                            name=server_data["name"],
                            transport=TransportType(server_data["transport"]),
                            mcp_version=server_data.get("version", "2025-06-18"),
                            capabilities=server_data.get("capabilities", []),
                            tools=server_data.get("tools", []),
                            endpoint=server_data.get("endpoint"),
                            command=server_data.get("command"),
                            description=server_data.get("description"),
                            sensitivity_level=server_data.get("sensitivity_level", "medium"),
                            signature=server_data.get("signature"),
                            metadata=server_data.get("metadata", {}),
                        )

                        result.add_success(
                            {
                                "server_id": str(server.id),
                                "name": server.name,
                                "status": server.status.value,
                            }
                        )

                        # Log audit event
                        await self.audit_service.log_event(
                            event_type=AuditEventType.SERVER_REGISTERED,
                            severity=SeverityLevel.MEDIUM,
                            user_id=self.user_id,
                            user_email=self.user_email,
                            server_id=server.id,
                            details={
                                "server_name": server.name,
                                "bulk_operation": True,
                            },
                        )

                    except Exception as e:
                        # Rollback entire transaction
                        logger.error("bulk_register_failed", server=server_data, error=str(e))
                        raise

                await self.db.commit()

            logger.info(
                "bulk_register_success",
                total=result.total,
                succeeded=result.success_count,
            )

        except Exception as e:
            # Transaction failed, mark all as failed
            await self.db.rollback()
            for server_data in servers:
                result.add_failure(
                    {"name": server_data.get("name")},
                    f"Transaction failed: {e!s}",
                )
            logger.error("bulk_register_transaction_failed", error=str(e))

        return result

    async def _bulk_register_best_effort(
        self,
        servers: list[dict[str, Any]],
    ) -> BulkOperationResult:
        """Register servers with best-effort (continue on errors).

        Args:
            servers: List of server registration requests

        Returns:
            BulkOperationResult
        """
        result = BulkOperationResult()
        result.total = len(servers)

        # Batch policy evaluation
        policy_results = await self._batch_evaluate_policies(servers, action="server:register")

        # Process each server individually
        for server_data, policy_result in zip(servers, policy_results, strict=True):
            try:
                # Check policy
                if not policy_result["allowed"]:
                    result.add_failure(
                        {"name": server_data.get("name")},
                        f"Policy denied: {policy_result.get('reason', 'Unknown')}",
                    )
                    continue

                # Register server
                server = await self.discovery_service.register_server(
                    name=server_data["name"],
                    transport=TransportType(server_data["transport"]),
                    mcp_version=server_data.get("version", "2025-06-18"),
                    capabilities=server_data.get("capabilities", []),
                    tools=server_data.get("tools", []),
                    endpoint=server_data.get("endpoint"),
                    command=server_data.get("command"),
                    description=server_data.get("description"),
                    sensitivity_level=server_data.get("sensitivity_level", "medium"),
                    signature=server_data.get("signature"),
                    metadata=server_data.get("metadata", {}),
                )

                result.add_success(
                    {
                        "server_id": str(server.id),
                        "name": server.name,
                        "status": server.status.value,
                    }
                )

                # Log audit event
                await self.audit_service.log_event(
                    event_type=AuditEventType.SERVER_REGISTERED,
                    severity=SeverityLevel.MEDIUM,
                    user_id=self.user_id,
                    user_email=self.user_email,
                    server_id=server.id,
                    details={
                        "server_name": server.name,
                        "bulk_operation": True,
                    },
                )

            except Exception as e:
                result.add_failure(
                    {"name": server_data.get("name")},
                    str(e),
                )
                logger.warning(
                    "server_registration_failed",
                    server=server_data.get("name"),
                    error=str(e),
                )

        logger.info(
            "bulk_register_complete",
            total=result.total,
            succeeded=result.success_count,
            failed=result.failure_count,
        )

        return result

    async def bulk_update_server_status(
        self,
        updates: list[dict[str, Any]],
        fail_on_first_error: bool = False,
    ) -> BulkOperationResult:
        """
        Bulk update server statuses.

        Args:
            updates: List of {server_id, status} updates
            fail_on_first_error: If True, rollback all on first error

        Returns:
            BulkOperationResult with success/failure details
        """
        result = BulkOperationResult()
        result.total = len(updates)

        if fail_on_first_error:
            return await self._bulk_update_status_transactional(updates)
        else:
            return await self._bulk_update_status_best_effort(updates)

    async def _bulk_update_status_transactional(
        self,
        updates: list[dict[str, Any]],
    ) -> BulkOperationResult:
        """Update statuses in a single transaction.

        Args:
            updates: List of status updates

        Returns:
            BulkOperationResult
        """
        result = BulkOperationResult()
        result.total = len(updates)

        try:
            async with self.db.begin_nested():
                for update in updates:
                    try:
                        server_id = UUID(update["server_id"])
                        new_status = ServerStatus(update["status"])

                        server = await self.discovery_service.update_server_status(
                            server_id=server_id,
                            status=new_status,
                        )

                        result.add_success(
                            {
                                "server_id": str(server.id),
                                "name": server.name,
                                "status": server.status.value,
                            }
                        )

                        # Log audit event
                        await self.audit_service.log_event(
                            event_type=AuditEventType.SERVER_UPDATED,
                            severity=SeverityLevel.LOW,
                            user_id=self.user_id,
                            user_email=self.user_email,
                            server_id=server.id,
                            details={
                                "status_change": {
                                    "new": new_status.value,
                                },
                                "bulk_operation": True,
                            },
                        )

                    except Exception as e:
                        logger.error("bulk_status_update_failed", update=update, error=str(e))
                        raise

                await self.db.commit()

        except Exception as e:
            await self.db.rollback()
            for update in updates:
                result.add_failure(
                    {"server_id": update.get("server_id")},
                    f"Transaction failed: {e!s}",
                )
            logger.error("bulk_status_update_transaction_failed", error=str(e))

        return result

    async def _bulk_update_status_best_effort(
        self,
        updates: list[dict[str, Any]],
    ) -> BulkOperationResult:
        """Update statuses with best-effort.

        Args:
            updates: List of status updates

        Returns:
            BulkOperationResult
        """
        result = BulkOperationResult()
        result.total = len(updates)

        for update in updates:
            try:
                server_id = UUID(update["server_id"])
                new_status = ServerStatus(update["status"])

                server = await self.discovery_service.update_server_status(
                    server_id=server_id,
                    status=new_status,
                )

                result.add_success(
                    {
                        "server_id": str(server.id),
                        "name": server.name,
                        "status": server.status.value,
                    }
                )

                # Log audit event
                await self.audit_service.log_event(
                    event_type=AuditEventType.SERVER_UPDATED,
                    severity=SeverityLevel.LOW,
                    user_id=self.user_id,
                    user_email=self.user_email,
                    server_id=server.id,
                    details={
                        "status_change": {
                            "new": new_status.value,
                        },
                        "bulk_operation": True,
                    },
                )

            except Exception as e:
                result.add_failure(
                    {"server_id": update.get("server_id")},
                    str(e),
                )
                logger.warning("status_update_failed", update=update, error=str(e))

        logger.info(
            "bulk_status_update_complete",
            total=result.total,
            succeeded=result.success_count,
            failed=result.failure_count,
        )

        return result

    async def _batch_evaluate_policies(
        self,
        items: list[dict[str, Any]],
        action: str,
    ) -> list[dict[str, Any]]:
        """
        Batch evaluate policies for multiple items.

        Args:
            items: List of items to evaluate
            action: Action to authorize (e.g., "server:register")

        Returns:
            List of policy evaluation results
        """
        results = []

        # Evaluate each policy (could be parallelized with asyncio.gather)
        for item in items:
            try:
                allowed = await self.opa_client.authorize(
                    user_id=str(self.user_id),
                    action=action,
                    resource=f"server:{item.get('name', 'unknown')}",
                    context={
                        "user_role": self.user_role,
                        "user_teams": self.user_teams,
                        "server_name": item.get("name"),
                        "sensitivity_level": item.get("sensitivity_level", "medium"),
                        "transport": item.get("transport"),
                    },
                )

                results.append(
                    {
                        "allowed": allowed,
                        "reason": "Policy evaluation completed",
                    }
                )

            except Exception as e:
                logger.error("policy_evaluation_failed", item=item, error=str(e))
                results.append(
                    {
                        "allowed": False,
                        "reason": f"Policy evaluation error: {e!s}",
                    }
                )

        return results
