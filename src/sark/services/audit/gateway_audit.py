"""Gateway audit event logging."""

import uuid
import asyncio
from datetime import datetime
import structlog
from sqlalchemy import text

from sark.models.gateway import GatewayAuditEvent
from sark.db.session import get_db_session

logger = structlog.get_logger()


async def log_gateway_event(event: GatewayAuditEvent) -> str:
    """
    Log Gateway audit event to PostgreSQL.

    Args:
        event: Gateway audit event

    Returns:
        Audit event ID

    Raises:
        Exception: If database write fails
    """
    audit_id = str(uuid.uuid4())

    try:
        async with get_db_session() as session:
            await session.execute(
                text("""
                    INSERT INTO gateway_audit_events (
                        id, event_type, user_id, agent_id, server_name, tool_name,
                        decision, reason, timestamp, gateway_request_id, metadata
                    ) VALUES (
                        :id, :event_type, :user_id, :agent_id, :server_name, :tool_name,
                        :decision, :reason, :timestamp, :gateway_request_id, :metadata
                    )
                """),
                {
                    "id": audit_id,
                    "event_type": event.event_type,
                    "user_id": event.user_id,
                    "agent_id": event.agent_id,
                    "server_name": event.server_name,
                    "tool_name": event.tool_name,
                    "decision": event.decision,
                    "reason": event.reason,
                    "timestamp": datetime.fromtimestamp(event.timestamp),
                    "gateway_request_id": event.gateway_request_id,
                    "metadata": event.metadata,
                }
            )
            await session.commit()

        logger.info(
            "gateway_audit_event_logged",
            audit_id=audit_id,
            event_type=event.event_type,
            decision=event.decision,
            server_name=event.server_name,
            tool_name=event.tool_name,
        )

        # Forward to SIEM asynchronously (fire and forget)
        try:
            from sark.services.siem.gateway_forwarder import forward_gateway_event
            asyncio.create_task(forward_gateway_event(event, audit_id))
        except ImportError:
            # SIEM integration not available yet
            logger.debug("siem_integration_not_available")

        return audit_id

    except Exception as e:
        logger.error(
            "gateway_audit_event_failed",
            error=str(e),
            event_type=event.event_type,
            gateway_request_id=event.gateway_request_id,
        )
        raise
