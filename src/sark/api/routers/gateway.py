"""Gateway integration API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
import structlog

from sark.models.gateway import (
    A2AAuthorizationRequest,
    GatewayAuditEvent,
    GatewayAuthorizationRequest,
    GatewayAuthorizationResponse,
    GatewayServerInfo,
    GatewayToolInfo,
    SecretScanRequest,
    SecretScanResponse,
)
from sark.services.auth import UserContext, get_current_user

logger = structlog.get_logger()
router = APIRouter(prefix="/gateway", tags=["Gateway Integration"])


@router.post("/authorize", response_model=GatewayAuthorizationResponse)
async def authorize_gateway_operation(
    request: GatewayAuthorizationRequest,
    user: Annotated[UserContext, Depends(get_current_user)],
) -> GatewayAuthorizationResponse:
    """
    Authorize Gateway request (called by Gateway before routing to MCP server).

    Flow:
    1. Extract user context from JWT
    2. Build OPA policy input
    3. Evaluate policy (with caching)
    4. Return decision + filtered parameters
    5. Log audit event

    **Used by:** MCP Gateway
    **Authentication:** User JWT token required

    Returns:
        Authorization decision with optional parameter filtering
    """
    try:
        logger.info(
            "gateway_authorization_request",
            user_id=str(user.user_id),
            action=request.action,
            server=request.server_name,
            tool=request.tool_name,
        )

        from sark.services.gateway.authorization import authorize_gateway_request

        decision = await authorize_gateway_request(
            user=user,
            request=request,
        )

        logger.info(
            "gateway_authorization_decision",
            user_id=str(user.user_id),
            action=request.action,
            decision=decision.allow,
            reason=decision.reason,
        )

        return decision

    except Exception as e:
        logger.error("gateway_authorization_failed", error=str(e), user_id=str(user.user_id))
        return GatewayAuthorizationResponse(
            allow=False,
            reason=f"Authorization error: {e!s}",
            cache_ttl=0,
        )


@router.post("/authorize-a2a", response_model=GatewayAuthorizationResponse)
async def authorize_a2a_communication(
    request: A2AAuthorizationRequest,
    authorization: Annotated[str, Header(description="Agent JWT token")],
) -> GatewayAuthorizationResponse:
    """
    Authorize agent-to-agent communication (called by A2A Hub).

    Flow:
    1. Extract agent context from JWT
    2. Validate trust levels
    3. Check capability permissions
    4. Enforce restrictions (cross-env, rate limits)
    5. Return decision

    **Used by:** Agent-to-Agent Hub
    **Authentication:** Agent JWT token required

    Returns:
        Authorization decision for A2A communication
    """
    try:
        logger.info(
            "a2a_authorization_request",
            source=request.source_agent_id,
            target=request.target_agent_id,
            capability=request.capability,
        )

        from sark.api.middleware.agent_auth import extract_agent_context
        from sark.services.gateway.authorization import authorize_a2a_request

        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format",
            )

        token = authorization.replace("Bearer ", "")
        agent_context = extract_agent_context(token)

        decision = await authorize_a2a_request(
            agent_context=agent_context,
            request=request,
        )

        logger.info(
            "a2a_authorization_decision",
            agent_id=agent_context.agent_id,
            decision=decision.allow,
            reason=decision.reason,
        )

        return decision

    except HTTPException:
        raise
    except Exception as e:
        logger.error("a2a_authorization_failed", error=str(e))
        return GatewayAuthorizationResponse(
            allow=False,
            reason=f"A2A authorization error: {e!s}",
            cache_ttl=0,
        )


@router.get("/servers", response_model=list[GatewayServerInfo])
async def list_authorized_servers(
    user: Annotated[UserContext, Depends(get_current_user)],
) -> list[GatewayServerInfo]:
    """
    List MCP servers available via Gateway, filtered by user permissions.

    Flow:
    1. Fetch all servers from Gateway
    2. Filter by user's authorization
    3. Return only authorized servers

    Returns:
        List of servers user can access
    """
    try:
        from sark.services.gateway.authorization import filter_servers_by_permission
        from sark.services.gateway.client import get_gateway_client

        gateway_client = await get_gateway_client()
        all_servers = await gateway_client.list_servers()

        authorized_servers = await filter_servers_by_permission(
            user=user,
            servers=all_servers,
        )

        logger.info(
            "gateway_list_servers",
            user_id=str(user.user_id),
            total_servers=len(all_servers),
            authorized_servers=len(authorized_servers),
        )

        return authorized_servers

    except Exception as e:
        logger.error("gateway_list_servers_failed", error=str(e), user_id=str(user.user_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list servers: {e!s}",
        )


@router.get("/tools", response_model=list[GatewayToolInfo])
async def list_authorized_tools(
    user: Annotated[UserContext, Depends(get_current_user)],
    server_name: str | None = None,
) -> list[GatewayToolInfo]:
    """
    List tools available via Gateway, filtered by authorization.

    Args:
        server_name: Optional server filter

    Returns:
        List of tools user can invoke
    """
    try:
        from sark.services.gateway.authorization import filter_tools_by_permission
        from sark.services.gateway.client import get_gateway_client

        gateway_client = await get_gateway_client()
        all_tools = await gateway_client.list_tools(server_name=server_name)

        authorized_tools = await filter_tools_by_permission(
            user=user,
            tools=all_tools,
        )

        logger.info(
            "gateway_list_tools",
            user_id=str(user.user_id),
            server_name=server_name,
            total_tools=len(all_tools),
            authorized_tools=len(authorized_tools),
        )

        return authorized_tools

    except Exception as e:
        logger.error("gateway_list_tools_failed", error=str(e), user_id=str(user.user_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tools: {e!s}",
        )


@router.post("/audit", status_code=status.HTTP_201_CREATED)
async def log_gateway_audit_event(
    event: GatewayAuditEvent,
    x_gateway_api_key: Annotated[str, Header(description="Gateway API key")],
) -> dict[str, str]:
    """
    Log audit event from Gateway (requires Gateway API key).

    Used by Gateway to push audit events to SARK for centralized logging.

    **Authentication:** Gateway API key required (in `X-Gateway-Api-Key` header)

    Returns:
        Audit event ID and status
    """
    try:
        from sark.config import get_settings

        settings = get_settings()
        expected_key = settings.gateway_api_key

        if not expected_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Gateway API key not configured",
            )

        if x_gateway_api_key != expected_key:
            logger.warning("gateway_audit_invalid_api_key")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Gateway API key",
            )

        from sark.services.audit.gateway_audit import log_gateway_event

        audit_id = await log_gateway_event(event)

        logger.info(
            "gateway_audit_logged",
            audit_id=audit_id,
            event_type=event.event_type,
            gateway_request_id=event.gateway_request_id,
        )

        return {
            "audit_id": audit_id,
            "status": "logged",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("gateway_audit_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to log audit event: {e!s}",
        )


@router.post("/scan-response", response_model=SecretScanResponse)
async def scan_tool_response(
    request: SecretScanRequest,
    x_gateway_api_key: Annotated[str, Header(description="Gateway API key")],
) -> SecretScanResponse:
    """Scan tool response for secrets and redact if found.

    Called by the Gateway after receiving a tool response from an MCP server
    and before returning it to the client.

    **Authentication:** Gateway API key required (in ``X-Gateway-Api-Key`` header)
    """
    import time

    from sark.config import get_settings
    from sark.security import SecretScanner

    start_time = time.perf_counter()

    try:
        settings = get_settings()

        # Validate Gateway API key
        expected_key = settings.gateway_api_key
        if not expected_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Gateway API key not configured",
            )
        if x_gateway_api_key != expected_key:
            logger.warning("gateway_scan_invalid_api_key")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Gateway API key",
            )

        # Feature flag check
        if not settings.feature_flags.enable_secret_scanning:
            scan_duration = (time.perf_counter() - start_time) * 1000
            return SecretScanResponse(
                redacted_data=request.response_data,
                secrets_found=0,
                secret_types=[],
                alert_sent=False,
                scan_duration_ms=scan_duration,
            )

        scanner = SecretScanner()
        redacted_data, findings = scanner.redact(request.response_data)
        scan_duration = (time.perf_counter() - start_time) * 1000

        if findings:
            secret_types = list({f.secret_type.value for f in findings})

            logger.warning(
                "secrets_detected_in_tool_response",
                server_name=request.server_name,
                tool_name=request.tool_name,
                user_id=request.user_id,
                gateway_request_id=request.gateway_request_id,
                secret_count=len(findings),
                secret_types=secret_types,
                scan_duration_ms=scan_duration,
            )

            alert_sent = await _send_secret_alert(
                findings=findings,
                server_name=request.server_name,
                tool_name=request.tool_name,
                user_id=request.user_id,
                gateway_request_id=request.gateway_request_id,
            )

            return SecretScanResponse(
                redacted_data=redacted_data,
                secrets_found=len(findings),
                secret_types=secret_types,
                alert_sent=alert_sent,
                scan_duration_ms=scan_duration,
            )

        logger.debug(
            "secret_scan_clean",
            server_name=request.server_name,
            tool_name=request.tool_name,
            gateway_request_id=request.gateway_request_id,
            scan_duration_ms=scan_duration,
        )
        return SecretScanResponse(
            redacted_data=redacted_data,
            secrets_found=0,
            secret_types=[],
            alert_sent=False,
            scan_duration_ms=scan_duration,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "gateway_scan_failed",
            error=str(e),
            gateway_request_id=request.gateway_request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scan response: {e!s}",
        )


async def _send_secret_alert(
    findings: list,
    server_name: str,
    tool_name: str,
    user_id: str | None,
    gateway_request_id: str,
) -> bool:
    """Send a CRITICAL audit event when secrets are detected (best-effort)."""
    try:
        from sark.models.audit import AuditEventType, SeverityLevel
        from sark.services.audit.audit_service import AuditService

        audit_service = AuditService()
        secret_details = [
            {
                "type": f.secret_type.value,
                "line_number": f.line_number,
                "length": len(f.full_match),
            }
            for f in findings
        ]

        await audit_service.log_event(
            event_type=AuditEventType.SECURITY_VIOLATION,
            severity=SeverityLevel.CRITICAL,
            user_id=user_id,
            server_name=server_name,
            tool_name=tool_name,
            decision="redacted",
            details={
                "violation_type": "secret_detected",
                "secret_count": len(findings),
                "secrets": secret_details,
                "gateway_request_id": gateway_request_id,
            },
        )
        return True

    except Exception as e:
        logger.error(
            "failed_to_send_secret_alert",
            error=str(e),
            gateway_request_id=gateway_request_id,
        )
        return False
