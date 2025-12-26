"""Agent authentication middleware.

Provides JWT authentication and context extraction for agent-to-agent communication.
"""

from typing import Annotated

from fastapi import Header, HTTPException, status
import jwt
import structlog

from sark.models.gateway import AgentContext, AgentType, TrustLevel

logger = structlog.get_logger()


def extract_agent_context(token: str) -> AgentContext:
    """
    Extract agent context from JWT token.

    Agent JWT tokens are issued by SARK's agent provisioning system and contain:
    - agent_id: Unique agent identifier
    - agent_type: service, worker, or query
    - trust_level: trusted, limited, or untrusted
    - capabilities: List of capabilities (e.g., ["data_access", "computation"])
    - environment: Environment name (e.g., "production", "staging")

    Args:
        token: JWT token string (without "Bearer " prefix)

    Returns:
        AgentContext with extracted claims

    Raises:
        HTTPException: If token is invalid or missing required claims
    """
    try:
        from sark.config import get_settings

        settings = get_settings()

        # Decode and validate JWT with full signature verification
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"verify_signature": True},
        )

        # Extract required claims
        agent_id = payload.get("agent_id")
        if not agent_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing agent_id claim in token",
            )

        # Parse agent type
        agent_type_str = payload.get("agent_type", "service")
        try:
            agent_type = AgentType(agent_type_str)
        except ValueError:
            logger.warning(
                "invalid_agent_type",
                agent_id=agent_id,
                agent_type=agent_type_str,
            )
            agent_type = AgentType.SERVICE

        # Parse trust level
        trust_level_str = payload.get("trust_level", "limited")
        try:
            trust_level = TrustLevel(trust_level_str)
        except ValueError:
            logger.warning(
                "invalid_trust_level",
                agent_id=agent_id,
                trust_level=trust_level_str,
            )
            trust_level = TrustLevel.LIMITED

        # Extract capabilities and environment
        capabilities = payload.get("capabilities", [])
        environment = payload.get("environment", "unknown")

        logger.info(
            "agent_context_extracted",
            agent_id=agent_id,
            agent_type=agent_type.value,
            trust_level=trust_level.value,
            environment=environment,
        )

        return AgentContext(
            agent_id=agent_id,
            agent_type=agent_type,
            trust_level=trust_level,
            capabilities=capabilities,
            environment=environment,
        )

    except jwt.ExpiredSignatureError:
        logger.warning("agent_token_expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agent token has expired",
        )
    except jwt.InvalidTokenError as e:
        logger.warning("agent_token_invalid", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid agent token: {e!s}",
        )
    except Exception as e:
        logger.error("agent_context_extraction_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract agent context",
        )


async def get_current_agent(
    authorization: Annotated[str, Header(description="Agent JWT token")],
) -> AgentContext:
    """
    FastAPI dependency for agent authentication.

    Extracts and validates agent context from Authorization header.

    Usage:
        @router.post("/agent-endpoint")
        async def agent_endpoint(
            agent: Annotated[AgentContext, Depends(get_current_agent)],
        ):
            # Use agent.agent_id, agent.trust_level, etc.
            pass

    Args:
        authorization: Authorization header value (must be "Bearer <token>")

    Returns:
        AgentContext with validated agent information

    Raises:
        HTTPException: If authorization header is missing or invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format (must be 'Bearer <token>')",
        )

    token = authorization.replace("Bearer ", "")
    return extract_agent_context(token)
