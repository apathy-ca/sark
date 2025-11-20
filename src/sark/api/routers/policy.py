"""Policy evaluation endpoints."""

from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from sark.services.policy import OPAClient

logger = structlog.get_logger()
router = APIRouter()


class PolicyEvaluationRequest(BaseModel):
    """Policy evaluation request."""

    user_id: UUID = Field(..., description="User ID making the request")
    action: str = Field(..., description="Action to authorize (e.g., 'tool:invoke')")
    tool: str | None = Field(None, description="Tool name")
    server_id: UUID | None = Field(None, description="Server ID")
    parameters: dict[str, Any] = Field(default_factory=dict)


class PolicyEvaluationResponse(BaseModel):
    """Policy evaluation response."""

    decision: str = Field(..., description="'allow' or 'deny'")
    reason: str = Field(..., description="Reason for decision")
    filtered_parameters: dict[str, Any] | None = None
    audit_id: str | None = None


@router.post("/evaluate", response_model=PolicyEvaluationResponse)
async def evaluate_policy(
    request: PolicyEvaluationRequest,
) -> PolicyEvaluationResponse:
    """
    Evaluate authorization policy for a request.

    This endpoint queries OPA to determine if the requested action
    should be allowed or denied based on configured policies.
    """
    try:
        opa_client = OPAClient()

        # Build authorization input
        from sark.services.policy.opa_client import AuthorizationInput

        auth_input = AuthorizationInput(
            user={
                "id": str(request.user_id),
                "role": "developer",  # TODO: Get from user context
                "teams": [],  # TODO: Get from user context
            },
            action=request.action,
            tool={
                "name": request.tool,
                "sensitivity_level": "medium",  # TODO: Get from server/tool registry
            }
            if request.tool
            else None,
            context={"timestamp": 0},  # TODO: Add real timestamp
        )

        # Evaluate policy
        decision = await opa_client.evaluate_policy(auth_input)

        await opa_client.close()

        return PolicyEvaluationResponse(
            decision="allow" if decision.allow else "deny",
            reason=decision.reason,
            filtered_parameters=decision.filtered_parameters,
            audit_id=decision.audit_id,
        )

    except Exception as e:
        logger.error("policy_evaluation_failed", error=str(e))
        # Fail closed - deny on error
        return PolicyEvaluationResponse(
            decision="deny",
            reason=f"Policy evaluation error: {e!s}",
        )
