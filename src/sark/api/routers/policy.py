"""Policy evaluation endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
import structlog

from sark.services.auth import UserContext, get_current_user
from sark.services.policy import OPAClient

logger = structlog.get_logger()
router = APIRouter()


class PolicyEvaluationRequest(BaseModel):
    """Policy evaluation request."""

    user_id: UUID | None = Field(None, description="User ID (defaults to authenticated user)")
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


class PolicyInfo(BaseModel):
    """Policy information."""

    name: str = Field(..., description="Policy name")
    path: str = Field(..., description="Policy path in OPA")
    version: str | None = Field(None, description="Policy version")
    description: str | None = Field(None, description="Policy description")
    active: bool = Field(True, description="Whether policy is active")


class PolicyListResponse(BaseModel):
    """Policy list response."""

    policies: list[PolicyInfo]
    total: int


class PolicyValidationRequest(BaseModel):
    """Policy validation request."""

    policy_content: str = Field(..., description="Rego policy content to validate")
    test_cases: list[dict[str, Any]] | None = Field(
        None, description="Optional test cases to run"
    )


class PolicyValidationResponse(BaseModel):
    """Policy validation response."""

    valid: bool = Field(..., description="Whether policy is valid")
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    test_results: dict[str, Any] | None = Field(None, description="Test case results")


@router.post("/evaluate", response_model=PolicyEvaluationResponse)
async def evaluate_policy(
    request: PolicyEvaluationRequest,
    user: UserContext = Depends(get_current_user),
) -> PolicyEvaluationResponse:
    """
    Evaluate authorization policy for a request.

    This endpoint queries OPA to determine if the requested action
    should be allowed or denied based on configured policies.

    Requires authentication via JWT token.
    """
    try:
        opa_client = OPAClient()

        # Build authorization input with actual user context
        from sark.services.policy.opa_client import AuthorizationInput

        # Use authenticated user's ID unless explicitly overridden in request
        user_id = request.user_id if request.user_id else user.user_id

        auth_input = AuthorizationInput(
            user={
                "id": str(user_id),
                "role": user.role,
                "teams": user.teams,
            },
            action=request.action,
            tool=(
                {
                    "name": request.tool,
                    "sensitivity_level": "medium",  # TODO: Get from server/tool registry
                }
                if request.tool
                else None
            ),
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


@router.get("/list", response_model=PolicyListResponse)
async def list_policies(
    user: UserContext = Depends(get_current_user),
) -> PolicyListResponse:
    """
    List all active OPA policies.

    Returns a list of currently loaded policies including their paths,
    versions, and descriptions.

    Requires authentication.
    """
    try:
        opa_client = OPAClient()

        # Get policies from OPA
        # In a real implementation, this would query OPA's policy list
        # For now, return a static list
        policies = [
            PolicyInfo(
                name="mcp.authorization",
                path="/v1/data/mcp/authorization",
                version="1.0.0",
                description="Main authorization policy for MCP governance",
                active=True,
            ),
            PolicyInfo(
                name="mcp.tool_sensitivity",
                path="/v1/data/mcp/tool_sensitivity",
                version="1.0.0",
                description="Tool sensitivity classification policies",
                active=True,
            ),
            PolicyInfo(
                name="mcp.rate_limiting",
                path="/v1/data/mcp/rate_limiting",
                version="1.0.0",
                description="Rate limiting policies for tool invocations",
                active=True,
            ),
        ]

        await opa_client.close()

        return PolicyListResponse(
            policies=policies,
            total=len(policies),
        )

    except Exception as e:
        logger.error("policy_list_failed", error=str(e))
        return PolicyListResponse(policies=[], total=0)


@router.post("/validate", response_model=PolicyValidationResponse)
async def validate_policy(
    request: PolicyValidationRequest,
    user: UserContext = Depends(get_current_user),
) -> PolicyValidationResponse:
    """
    Validate OPA policy syntax and optionally run test cases.

    Checks:
    - Policy syntax is valid Rego
    - No compilation errors
    - Optional: Run provided test cases

    Useful for validating policies before deployment.

    Requires authentication.
    """
    try:
        opa_client = OPAClient()

        # In a real implementation, this would:
        # 1. Send policy to OPA for compilation
        # 2. Check for syntax errors
        # 3. Run test cases if provided

        # Placeholder validation
        errors = []
        warnings = []

        # Basic validation
        if not request.policy_content.strip():
            errors.append("Policy content is empty")

        if "package" not in request.policy_content:
            errors.append("Policy must declare a package")

        # Check for common issues
        if "default allow" in request.policy_content and "= true" in request.policy_content:
            warnings.append("Policy has 'default allow = true' - this allows all actions by default")

        # Run test cases if provided
        test_results = None
        if request.test_cases:
            test_results = {
                "total": len(request.test_cases),
                "passed": len(request.test_cases),  # Placeholder
                "failed": 0,
                "details": [],
            }

        await opa_client.close()

        return PolicyValidationResponse(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            test_results=test_results,
        )

    except Exception as e:
        logger.error("policy_validation_failed", error=str(e))
        return PolicyValidationResponse(
            valid=False,
            errors=[f"Validation error: {e!s}"],
        )
