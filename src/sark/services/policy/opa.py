"""OPA policy evaluation helper module."""

from typing import Any


async def evaluate_policy(policy_path: str, input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Evaluate OPA policy (wrapper/helper for authorization module).

    This is a simple wrapper that can be mocked in tests or implemented
    to call the actual OPA client.

    Args:
        policy_path: OPA policy path (e.g., "/v1/data/mcp/gateway/allow")
        input_data: Policy input data

    Returns:
        OPA evaluation result
    """
    # Placeholder implementation - in real code this would call OPAClient
    # For now, this allows the authorization module to import successfully
    from sark.services.policy.opa_client import get_opa_client

    client = await get_opa_client()
    # Note: This is simplified - actual implementation would need proper mapping
    # from policy_path and input_data to AuthorizationInput
    raise NotImplementedError("evaluate_policy needs OPAClient integration")
