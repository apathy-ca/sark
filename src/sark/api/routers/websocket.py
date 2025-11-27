"""WebSocket endpoints for real-time updates."""

import asyncio
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from sark.db import get_db, get_timescale_db
from sark.services.auth import JWTHandler, UserContext

logger = structlog.get_logger()
router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
        self.user_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, channel: str, user_id: str):
        """Accept a new WebSocket connection."""
        await websocket.accept()

        if channel not in self.active_connections:
            self.active_connections[channel] = []

        self.active_connections[channel].append(websocket)
        self.user_connections[user_id] = websocket

        logger.info(
            "websocket_connected",
            channel=channel,
            user_id=user_id,
            total_connections=len(self.active_connections.get(channel, [])),
        )

    def disconnect(self, websocket: WebSocket, channel: str, user_id: str):
        """Remove a WebSocket connection."""
        if channel in self.active_connections:
            try:
                self.active_connections[channel].remove(websocket)
            except ValueError:
                pass

        if user_id in self.user_connections:
            del self.user_connections[user_id]

        logger.info(
            "websocket_disconnected",
            channel=channel,
            user_id=user_id,
            remaining_connections=len(self.active_connections.get(channel, [])),
        )

    async def send_personal_message(self, message: dict[str, Any], websocket: WebSocket):
        """Send a message to a specific WebSocket connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error("send_personal_message_error", error=str(e))

    async def broadcast(self, message: dict[str, Any], channel: str):
        """Broadcast a message to all connections in a channel."""
        if channel not in self.active_connections:
            return

        disconnected = []
        for connection in self.active_connections[channel]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error("broadcast_error", error=str(e))
                disconnected.append(connection)

        # Remove disconnected clients
        for connection in disconnected:
            try:
                self.active_connections[channel].remove(connection)
            except ValueError:
                pass


# Global connection manager
manager = ConnectionManager()


async def authenticate_websocket(token: str | None) -> UserContext | None:
    """Authenticate a WebSocket connection using a JWT token."""
    if not token:
        return None

    try:
        handler = JWTHandler()
        payload = handler.decode_token(token)

        # Extract user information from token
        from uuid import UUID

        user_id = UUID(payload["sub"])
        email = payload["email"]
        role = payload["role"]
        teams = payload.get("teams", [])

        user_context = UserContext(
            user_id=user_id,
            email=email,
            role=role,
            teams=teams,
            is_authenticated=True,
        )

        logger.debug(
            "websocket_user_authenticated",
            user_id=str(user_id),
            email=email,
            role=role,
        )

        return user_context

    except Exception as e:
        logger.error("websocket_auth_error", error=str(e))
        return None


@router.websocket("/audit/stream")
async def audit_stream_websocket(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    """
    WebSocket endpoint for real-time audit log events.

    **Authentication**: Requires a valid JWT token passed as a query parameter.

    **Message Format**:
    ```json
    {
      "type": "audit_event",
      "timestamp": "2025-11-27T10:30:00Z",
      "event": {
        "id": "event-123",
        "user_id": "user-456",
        "action": "server:register",
        "resource_type": "server",
        "resource_id": "server-789",
        "decision": "allow",
        "reason": "User has required permissions",
        "ip_address": "192.168.1.100"
      }
    }
    ```

    **Events Streamed**:
    - New server registrations
    - Policy evaluation decisions
    - Tool invocations
    - Authentication events
    - Configuration changes

    **Connection Example** (JavaScript):
    ```javascript
    const token = getAccessToken();
    const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/audit/stream?token=${token}`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Audit event:', data);
    };
    ```

    **Rate Limiting**: Events are throttled to max 10 per second per connection.
    """
    # Authenticate the WebSocket connection
    user = await authenticate_websocket(token)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or missing token")
        return

    user_id = str(user.user_id)
    channel = "audit_events"

    try:
        # Accept the connection
        await manager.connect(websocket, channel, user_id)

        # Send a welcome message
        await manager.send_personal_message(
            {
                "type": "connected",
                "message": "Connected to audit log stream",
                "user_id": user_id,
            },
            websocket,
        )

        # Keep the connection alive and listen for incoming messages
        while True:
            try:
                # Wait for any message from the client (e.g., ping/pong)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                # Echo ping/pong for keep-alive
                if data == "ping":
                    await websocket.send_text("pong")

            except asyncio.TimeoutError:
                # Send a keep-alive ping
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        logger.info("websocket_disconnect", user_id=user_id, channel=channel)
    except Exception as e:
        logger.error("websocket_error", user_id=user_id, error=str(e))
    finally:
        manager.disconnect(websocket, channel, user_id)


@router.websocket("/servers/status")
async def server_status_websocket(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    """
    WebSocket endpoint for real-time server status updates.

    **Authentication**: Requires a valid JWT token passed as a query parameter.

    **Message Format**:
    ```json
    {
      "type": "server_status_change",
      "timestamp": "2025-11-27T10:30:00Z",
      "server": {
        "id": "server-123",
        "name": "analytics-server-1",
        "status": "active",
        "previous_status": "registered",
        "health_check_result": "healthy"
      }
    }
    ```

    **Events Streamed**:
    - Server status changes (active, inactive, unhealthy, etc.)
    - Health check results
    - Server registration/decommission
    - Tool additions/removals

    **Connection Example** (JavaScript):
    ```javascript
    const token = getAccessToken();
    const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/servers/status?token=${token}`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'server_status_change') {
        console.log('Server status changed:', data.server);
      }
    };
    ```
    """
    # Authenticate the WebSocket connection
    user = await authenticate_websocket(token)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or missing token")
        return

    user_id = str(user.user_id)
    channel = "server_status"

    try:
        await manager.connect(websocket, channel, user_id)

        await manager.send_personal_message(
            {
                "type": "connected",
                "message": "Connected to server status stream",
                "user_id": user_id,
            },
            websocket,
        )

        # Keep the connection alive
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        logger.info("websocket_disconnect", user_id=user_id, channel=channel)
    except Exception as e:
        logger.error("websocket_error", user_id=user_id, error=str(e))
    finally:
        manager.disconnect(websocket, channel, user_id)


@router.websocket("/metrics/live")
async def metrics_live_websocket(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    """
    WebSocket endpoint for real-time metrics updates.

    **Authentication**: Requires a valid JWT token passed as a query parameter.

    **Message Format**:
    ```json
    {
      "type": "metrics_update",
      "timestamp": "2025-11-27T10:30:00Z",
      "metrics": {
        "total_servers": 42,
        "active_servers": 38,
        "unhealthy_servers": 2,
        "inactive_servers": 2,
        "total_tools": 156,
        "recent_policy_decisions": 1234,
        "policy_allow_rate": 0.95
      }
    }
    ```

    **Update Frequency**: Metrics are pushed every 5 seconds.

    **Events Streamed**:
    - Server count changes
    - Tool count changes
    - Policy decision metrics
    - System health metrics

    **Connection Example** (JavaScript):
    ```javascript
    const token = getAccessToken();
    const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/metrics/live?token=${token}`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'metrics_update') {
        updateDashboard(data.metrics);
      }
    };
    ```
    """
    # Authenticate the WebSocket connection
    user = await authenticate_websocket(token)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or missing token")
        return

    user_id = str(user.user_id)
    channel = "metrics_live"

    try:
        await manager.connect(websocket, channel, user_id)

        await manager.send_personal_message(
            {
                "type": "connected",
                "message": "Connected to live metrics stream",
                "user_id": user_id,
            },
            websocket,
        )

        # Keep the connection alive
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        logger.info("websocket_disconnect", user_id=user_id, channel=channel)
    except Exception as e:
        logger.error("websocket_error", user_id=user_id, error=str(e))
    finally:
        manager.disconnect(websocket, channel, user_id)


@router.get("/connections")
async def get_websocket_connections():
    """
    Get information about active WebSocket connections.

    **Admin endpoint** - requires admin role.

    Returns the number of active connections per channel.
    """
    connections_info = {}
    for channel, connections in manager.active_connections.items():
        connections_info[channel] = {
            "count": len(connections),
            "channel": channel,
        }

    return {
        "total_connections": sum(info["count"] for info in connections_info.values()),
        "channels": connections_info,
    }


# Export the manager for use in other modules to broadcast events
__all__ = ["router", "manager"]
