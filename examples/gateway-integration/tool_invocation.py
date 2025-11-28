#!/usr/bin/env python3
"""
Tool Invocation with Validation Example

This example demonstrates how to properly invoke MCP tools through the Gateway,
including authorization checks, parameter validation, and sensitive data filtering.

Best Practices Demonstrated:
- Using GatewayAuthorizationRequest for type-safe requests
- Proper action string formatting
- Parameter validation and filtering
- Error handling for authorization failures
- Audit trail integration

Author: Engineer 1 (Gateway Models Architect)
"""

import asyncio
from datetime import datetime, UTC

from pydantic import ValidationError

from sark.models.gateway import (
    GatewayAuthorizationRequest,
    GatewayAuthorizationResponse,
    GatewayToolInfo,
    SensitivityLevel,
)


def example_create_authorization_request():
    """
    Example: Create a properly validated authorization request.

    Demonstrates:
    - Constructing GatewayAuthorizationRequest
    - Action string validation
    - Parameter specification
    """
    print("=" * 60)
    print("Example 1: Creating Authorization Request")
    print("=" * 60)

    try:
        # Create a valid authorization request
        auth_request = GatewayAuthorizationRequest(
            action="gateway:tool:invoke",
            server_name="postgres-mcp",
            tool_name="execute_query",
            parameters={
                "query": "SELECT * FROM users WHERE id = $1",
                "params": [123],
                "timeout": 30,
            },
            gateway_metadata={
                "user_id": "user_12345",
                "session_id": "session_abc",
                "request_id": "req_xyz789",
            },
        )

        print("\n✅ Successfully created authorization request:")
        print(f"   Action: {auth_request.action}")
        print(f"   Server: {auth_request.server_name}")
        print(f"   Tool: {auth_request.tool_name}")
        print(f"   Parameters: {len(auth_request.parameters)} provided")
        print()

        return auth_request

    except ValidationError as e:
        print(f"\n❌ Validation failed: {e}")
        raise


def example_invalid_action_strings():
    """
    Example: Common action string validation errors.

    Demonstrates:
    - Valid vs invalid action formats
    - Action string conventions
    """
    print("=" * 60)
    print("Example 2: Action String Validation")
    print("=" * 60 + "\n")

    invalid_actions = [
        "invoke_tool",  # Missing gateway: prefix
        "gateway:invoke",  # Wrong format
        "gateway:tool:execute",  # Not in valid_actions list
        "tool:invoke",  # Missing gateway: prefix
    ]

    print("❌ Invalid action strings (will fail validation):")
    for action in invalid_actions:
        print(f"   - \"{action}\"")
        try:
            GatewayAuthorizationRequest(
                action=action,
                tool_name="test-tool",
                parameters={},
                gateway_metadata={},
            )
        except ValidationError as e:
            print(f"     Error: {e.errors()[0]['msg'][:60]}...")

    print("\n✅ Valid action strings:")
    valid_actions = [
        "gateway:tool:invoke",
        "gateway:server:list",
        "gateway:tool:discover",
        "gateway:server:info",
    ]
    for action in valid_actions:
        print(f"   - \"{action}\"")
    print()


def example_parameter_filtering():
    """
    Example: Filter sensitive parameters before logging/auditing.

    Demonstrates:
    - Using GatewayToolInfo.sensitive_params
    - Filtering logic
    - Safe parameter logging
    """
    print("=" * 60)
    print("Example 3: Sensitive Parameter Filtering")
    print("=" * 60)

    # Define a tool with sensitive parameters
    tool_info = GatewayToolInfo(
        tool_name="create_user",
        server_name="auth-mcp",
        description="Create a new user account",
        sensitivity_level=SensitivityLevel.HIGH,
        parameters=[
            {"name": "username", "type": "string", "required": True},
            {"name": "email", "type": "string", "required": True},
            {"name": "password", "type": "string", "required": True},  # Sensitive!
            {"name": "api_key", "type": "string", "required": False},  # Sensitive!
        ],
        sensitive_params=["password", "api_key", "secret", "token"],
        required_capabilities=["user:create"],
    )

    # Raw parameters including sensitive data
    raw_parameters = {
        "username": "john_doe",
        "email": "john@example.com",
        "password": "super_secret_password_123",  # Should be filtered
        "api_key": "sk_live_abc123xyz789",  # Should be filtered
    }

    print(f"\n🔧 Tool: {tool_info.tool_name}")
    print(f"   Sensitivity: {tool_info.sensitivity_level.value}")
    print(f"   Sensitive Params: {', '.join(tool_info.sensitive_params)}\n")

    # Filter sensitive parameters
    def filter_sensitive_params(params: dict, sensitive_list: list[str]) -> dict:
        """Filter out sensitive parameters for safe logging."""
        filtered = {}
        for key, value in params.items():
            if key in sensitive_list:
                filtered[key] = "***REDACTED***"
            else:
                filtered[key] = value
        return filtered

    filtered_parameters = filter_sensitive_params(
        raw_parameters, tool_info.sensitive_params
    )

    print("Raw Parameters (UNSAFE for logging):")
    for key, value in raw_parameters.items():
        marker = "⚠️ " if key in tool_info.sensitive_params else "✅ "
        print(f"   {marker}{key}: {value}")

    print("\nFiltered Parameters (SAFE for logging/audit):")
    for key, value in filtered_parameters.items():
        print(f"   ✅ {key}: {value}")
    print()


async def example_tool_invocation_with_authorization():
    """
    Example: Complete tool invocation flow with authorization.

    Demonstrates:
    - Authorization request
    - Authorization response handling
    - Audit trail correlation
    - Error handling
    """
    print("=" * 60)
    print("Example 4: Complete Tool Invocation Flow")
    print("=" * 60)

    # Step 1: Create authorization request
    auth_request = GatewayAuthorizationRequest(
        action="gateway:tool:invoke",
        server_name="postgres-mcp",
        tool_name="execute_query",
        parameters={
            "query": "SELECT COUNT(*) FROM orders WHERE status = 'pending'",
        },
        gateway_metadata={
            "user_id": "user_12345",
            "request_id": "req_abc123",
            "timestamp": int(datetime.now(UTC).timestamp()),
        },
    )

    print("\n1️⃣  Authorization Request:")
    print(f"   Action: {auth_request.action}")
    print(f"   Server: {auth_request.server_name}")
    print(f"   Tool: {auth_request.tool_name}")

    # Step 2: Simulate authorization response
    # In production, this would come from the OPA policy evaluation
    auth_response = GatewayAuthorizationResponse(
        allowed=True,
        reason="User has required capability: database:read",
        filtered_metadata={
            "policy_evaluated": "rbac_v1",
            "evaluation_time_ms": 15.3,
        },
        audit_id="audit_xyz789",
        cache_ttl=300,
    )

    print("\n2️⃣  Authorization Response:")
    print(f"   Allowed: {'✅ Yes' if auth_response.allowed else '❌ No'}")
    print(f"   Reason: {auth_response.reason}")
    print(f"   Audit ID: {auth_response.audit_id}")
    print(f"   Cache TTL: {auth_response.cache_ttl}s")

    if auth_response.allowed:
        print("\n3️⃣  Tool Invocation:")
        print("   ✅ Authorization approved, proceeding with tool invocation")
        print(f"   📝 Audit trail: {auth_response.audit_id}")
        print("   🔧 Invoking tool...")
        # Actual tool invocation would happen here
        print("   ✅ Tool executed successfully")
    else:
        print("\n3️⃣  Tool Invocation:")
        print("   ❌ Authorization denied, aborting invocation")
        print(f"   Reason: {auth_response.reason}")


async def example_authorization_denied_scenarios():
    """
    Example: Handling authorization denial scenarios.

    Demonstrates:
    - Different denial reasons
    - Appropriate error messages
    - User guidance
    """
    print("\n" + "=" * 60)
    print("Example 5: Authorization Denial Scenarios")
    print("=" * 60 + "\n")

    denial_scenarios = [
        {
            "reason": "User lacks required capability: database:write",
            "guidance": "Request 'database:write' capability from your team admin",
        },
        {
            "reason": "Tool sensitivity level (critical) exceeds user clearance (medium)",
            "guidance": "Contact security team for elevated access approval",
        },
        {
            "reason": "Outside of allowed hours (9 AM - 6 PM)",
            "guidance": "Wait until business hours or request emergency override",
        },
        {
            "reason": "MFA verification required but not provided",
            "guidance": "Complete MFA verification and retry request",
        },
        {
            "reason": "Rate limit exceeded (100 requests/minute)",
            "guidance": "Wait 60 seconds before retrying",
        },
    ]

    for i, scenario in enumerate(denial_scenarios, 1):
        auth_response = GatewayAuthorizationResponse(
            allowed=False,
            reason=scenario["reason"],
            filtered_metadata={},
            audit_id=f"audit_denial_{i}",
            cache_ttl=60,
        )

        print(f"Scenario {i}:")
        print(f"   ❌ Denied: {auth_response.reason}")
        print(f"   💡 Guidance: {scenario['guidance']}")
        print(f"   📝 Audit ID: {auth_response.audit_id}")
        print()


def example_capability_based_access_control():
    """
    Example: Using required capabilities for access control.

    Demonstrates:
    - Tool capability requirements
    - User capability matching
    - Capability-based authorization logic
    """
    print("=" * 60)
    print("Example 6: Capability-Based Access Control")
    print("=" * 60)

    # Define tools with different capability requirements
    tools = [
        GatewayToolInfo(
            tool_name="read_data",
            server_name="database-mcp",
            description="Read-only data access",
            sensitivity_level=SensitivityLevel.LOW,
            parameters=[],
            sensitive_params=[],
            required_capabilities=["data:read"],
        ),
        GatewayToolInfo(
            tool_name="write_data",
            server_name="database-mcp",
            description="Write data",
            sensitivity_level=SensitivityLevel.MEDIUM,
            parameters=[],
            sensitive_params=[],
            required_capabilities=["data:read", "data:write"],
        ),
        GatewayToolInfo(
            tool_name="delete_data",
            server_name="database-mcp",
            description="Delete data (dangerous)",
            sensitivity_level=SensitivityLevel.HIGH,
            parameters=[],
            sensitive_params=[],
            required_capabilities=["data:read", "data:write", "data:delete"],
        ),
    ]

    # User with limited capabilities
    user_capabilities = ["data:read", "data:write"]

    print("\n👤 User Capabilities:")
    print(f"   {', '.join(user_capabilities)}\n")

    print("🔧 Tool Access Check:\n")
    for tool in tools:
        required = set(tool.required_capabilities)
        user_caps = set(user_capabilities)
        has_access = required.issubset(user_caps)

        missing = required - user_caps

        status = "✅ ALLOWED" if has_access else "❌ DENIED"
        print(f"   {tool.tool_name}:")
        print(f"      Status: {status}")
        print(f"      Required: {', '.join(tool.required_capabilities)}")
        if missing:
            print(f"      Missing: {', '.join(missing)}")
        print()


def main():
    """
    Run all examples.
    """
    print("\n")
    print("=" * 60)
    print("  MCP TOOL INVOCATION - EXAMPLES")
    print("=" * 60)
    print("\nThese examples demonstrate proper tool invocation")
    print("with authorization, validation, and error handling.\n")

    # Synchronous examples
    example_create_authorization_request()
    example_invalid_action_strings()
    example_parameter_filtering()
    example_capability_based_access_control()

    # Async examples
    asyncio.run(example_tool_invocation_with_authorization())
    asyncio.run(example_authorization_denied_scenarios())

    print("=" * 60)
    print("  All examples completed!")
    print("=" * 60)
    print("\n💡 Key Takeaways:")
    print("   1. Always validate action strings against allowed values")
    print("   2. Filter sensitive parameters before logging")
    print("   3. Check authorization before invoking tools")
    print("   4. Preserve audit trail with audit_id correlation")
    print("   5. Handle denial scenarios gracefully with user guidance\n")


if __name__ == "__main__":
    main()
