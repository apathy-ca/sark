#!/usr/bin/env python3
"""
Policy Evaluation Example for SARK

This example demonstrates:
- Evaluating OPA policies for authorization decisions
- Tool sensitivity checks
- Policy caching for performance
- Handling policy decisions

Usage:
    python policy_evaluation.py
"""

import os
from typing import Dict, Optional
from uuid import UUID, uuid4

import requests


class SARKPolicyClient:
    """Handle policy evaluation for SARK."""

    def __init__(self, base_url: str, access_token: str):
        """Initialize policy client.

        Args:
            base_url: SARK API base URL
            access_token: JWT access token
        """
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    def evaluate_policy(
        self,
        action: str,
        tool: Optional[str] = None,
        server_id: Optional[str] = None,
        parameters: Optional[Dict] = None,
        user_id: Optional[str] = None,
    ) -> Dict:
        """Evaluate policy for an action.

        Args:
            action: Action to authorize (e.g., 'tool:invoke', 'server:register')
            tool: Tool name (optional)
            server_id: Server ID (optional)
            parameters: Action parameters (optional)
            user_id: User ID (defaults to authenticated user)

        Returns:
            Policy decision
        """
        payload = {"action": action, "parameters": parameters or {}}

        if user_id:
            payload["user_id"] = user_id
        if tool:
            payload["tool"] = tool
        if server_id:
            payload["server_id"] = server_id

        response = requests.post(f"{self.base_url}/api/v1/policy/evaluate", headers=self.headers, json=payload)

        response.raise_for_status()
        return response.json()


def example_basic_evaluation():
    """Example: Basic policy evaluation."""
    print("\n" + "=" * 60)
    print("Example 1: Basic Policy Evaluation")
    print("=" * 60)

    base_url = os.getenv("SARK_API_URL", "https://sark.example.com")
    access_token = os.getenv("SARK_ACCESS_TOKEN", "your-jwt-token")

    client = SARKPolicyClient(base_url, access_token)

    print("\nEvaluating policy for tool invocation...")

    try:
        decision = client.evaluate_policy(
            action="tool:invoke",
            tool="execute_query",
            parameters={"query": "SELECT * FROM users", "database": "production"},
        )

        print(f"\nDecision: {decision['decision']}")
        print(f"Reason: {decision['reason']}")

        if decision.get("filtered_parameters"):
            print(f"Filtered parameters: {decision['filtered_parameters']}")

        if decision.get("audit_id"):
            print(f"Audit ID: {decision['audit_id']}")

    except requests.exceptions.RequestException as e:
        print(f"\n✗ Evaluation failed: {e}")


def example_server_registration():
    """Example: Evaluate server registration policy."""
    print("\n" + "=" * 60)
    print("Example 2: Server Registration Policy")
    print("=" * 60)

    print("""
# Check if user can register a server

decision = client.evaluate_policy(
    action='server:register',
    parameters={
        'server_name': 'analytics-server-1',
        'sensitivity_level': 'high',
        'transport': 'http'
    }
)

if decision['decision'] == 'allow':
    print("✓ Server registration allowed")

    # Proceed with registration
    response = requests.post(
        f"{base_url}/api/v1/servers",
        headers=headers,
        json=server_data
    )

else:
    print(f"✗ Server registration denied: {decision['reason']}")

# Example output:
# ✓ Server registration allowed
# Reason: User has 'developer' role and server sensitivity is within allowed level
    """)


def example_tool_sensitivity():
    """Example: Check tool sensitivity and policy."""
    print("\n" + "=" * 60)
    print("Example 3: Tool Sensitivity Check")
    print("=" * 60)

    print("""
# Check tool sensitivity and evaluate policy

# 1. Get tool sensitivity level
response = requests.get(
    f"{base_url}/api/v1/tools/{tool_id}/sensitivity",
    headers=headers
)
tool_info = response.json()

print(f"Tool: {tool_info['tool_name']}")
print(f"Sensitivity: {tool_info['sensitivity_level']}")
print(f"Overridden: {tool_info['is_overridden']}")

# 2. Evaluate policy based on sensitivity
decision = client.evaluate_policy(
    action='tool:invoke',
    tool=tool_info['tool_name'],
    parameters={'arg1': 'value1'}
)

if decision['decision'] == 'deny':
    if 'sensitivity' in decision['reason'].lower():
        print(f"✗ Tool sensitivity {tool_info['sensitivity_level']} "
              f"exceeds user's allowed level")
    else:
        print(f"✗ Denied: {decision['reason']}")
else:
    print("✓ Tool invocation allowed")

# Example output:
# Tool: execute_query
# Sensitivity: high
# Overridden: false
# ✗ Tool sensitivity high exceeds user's allowed level
    """)


def example_role_based_access():
    """Example: Role-based access control."""
    print("\n" + "=" * 60)
    print("Example 4: Role-Based Access Control")
    print("=" * 60)

    print("""
# Different users with different roles

# Admin user - full access
admin_client = SARKPolicyClient(base_url, admin_token)
decision = admin_client.evaluate_policy(
    action='server:delete',
    server_id='550e8400-e29b-41d4-a716-446655440000'
)
# Result: allow (admins can delete servers)

# Developer user - limited access
dev_client = SARKPolicyClient(base_url, dev_token)
decision = dev_client.evaluate_policy(
    action='server:delete',
    server_id='550e8400-e29b-41d4-a716-446655440000'
)
# Result: deny (developers cannot delete servers)

# Viewer user - read-only
viewer_client = SARKPolicyClient(base_url, viewer_token)
decision = viewer_client.evaluate_policy(
    action='server:write',
    parameters={'server_name': 'new-server'}
)
# Result: deny (viewers cannot modify servers)

# Example output:
# Admin: ✓ Server deletion allowed
# Developer: ✗ Server deletion denied (role 'developer' cannot delete servers)
# Viewer: ✗ Server modification denied (role 'viewer' is read-only)
    """)


def example_team_based_access():
    """Example: Team-based access control."""
    print("\n" + "=" * 60)
    print("Example 5: Team-Based Access Control")
    print("=" * 60)

    print("""
# Team-based policies

# User in 'platform' team can access platform servers
decision = client.evaluate_policy(
    action='server:read',
    server_id='550e8400-e29b-41d4-a716-446655440000',
    # User's teams checked from JWT token
)

if decision['decision'] == 'allow':
    print("✓ Access granted (user in correct team)")
else:
    print(f"✗ Access denied: {decision['reason']}")

# Policies can check:
# - User's team membership
# - Server's team assignment
# - Cross-team access rules

# Example OPA policy snippet:
# allow {
#   input.user.teams[_] == input.resource.team
# }
#
# allow {
#   input.user.role == "admin"
# }

# Example output:
# ✓ Access granted (user in 'platform' team matches server's team)
    """)


def example_parameter_filtering():
    """Example: Policy-based parameter filtering."""
    print("\n" + "=" * 60)
    print("Example 6: Parameter Filtering")
    print("=" * 60)

    print("""
# Some policies may filter/redact parameters

# Example: SQL query filtering
decision = client.evaluate_policy(
    action='tool:invoke',
    tool='execute_query',
    parameters={
        'query': 'SELECT * FROM users WHERE id = 1',
        'database': 'production'
    }
)

if decision['decision'] == 'allow':
    if decision.get('filtered_parameters'):
        # Policy modified the parameters
        print("✓ Allowed with filtered parameters:")
        print(f"  Original: {decision['parameters']}")
        print(f"  Filtered: {decision['filtered_parameters']}")

        # Use filtered parameters for execution
        safe_params = decision['filtered_parameters']
    else:
        print("✓ Allowed (no filtering)")

# Example OPA policy:
# result := {
#   "allow": true,
#   "filtered_parameters": {
#     "query": redact_sensitive_columns(input.parameters.query),
#     "database": input.parameters.database
#   }
# }

# Example output:
# ✓ Allowed with filtered parameters:
#   Original: SELECT * FROM users WHERE id = 1
#   Filtered: SELECT id, name FROM users WHERE id = 1
    """)


def example_caching():
    """Example: Policy caching for performance."""
    print("\n" + "=" * 60)
    print("Example 7: Policy Caching")
    print("=" * 60)

    print("""
# Policy decisions are cached for performance

import time

# First call - cache miss (slower)
start = time.time()
decision1 = client.evaluate_policy(
    action='tool:invoke',
    tool='execute_query'
)
duration1 = (time.time() - start) * 1000
print(f"First call: {duration1:.2f}ms (cache miss)")

# Second call - cache hit (faster)
start = time.time()
decision2 = client.evaluate_policy(
    action='tool:invoke',
    tool='execute_query'
)
duration2 = (time.time() - start) * 1000
print(f"Second call: {duration2:.2f}ms (cache hit)")

# Typical results:
# First call: 45.23ms (cache miss - OPA evaluation)
# Second call: 3.15ms (cache hit - Redis lookup)

# Cache configuration (from server):
# - TTL: 300 seconds (5 minutes)
# - Backend: Redis
# - Key format: policy:<action>:<tool>:<user_role>
    """)


def example_integration_workflow():
    """Example: Complete integration workflow."""
    print("\n" + "=" * 60)
    print("Example 8: Complete Integration Workflow")
    print("=" * 60)

    print("""
# Complete workflow: Policy evaluation → Action execution

def invoke_tool_with_policy_check(tool_name, parameters):
    \"\"\"Invoke tool after policy check.\"\"\"

    # Step 1: Evaluate policy
    print(f"Checking policy for tool: {tool_name}")
    decision = client.evaluate_policy(
        action='tool:invoke',
        tool=tool_name,
        parameters=parameters
    )

    # Step 2: Handle decision
    if decision['decision'] == 'deny':
        print(f"✗ Policy denied: {decision['reason']}")
        return None

    print(f"✓ Policy allowed: {decision['reason']}")

    # Step 3: Use filtered parameters if provided
    exec_params = decision.get('filtered_parameters', parameters)

    # Step 4: Execute tool with approved parameters
    print(f"Executing tool with parameters: {exec_params}")
    result = execute_tool(tool_name, exec_params)

    # Step 5: Log audit event
    if decision.get('audit_id'):
        print(f"Audit ID: {decision['audit_id']}")

    return result

# Example usage:
result = invoke_tool_with_policy_check(
    'execute_query',
    {
        'query': 'SELECT * FROM users',
        'database': 'production'
    }
)

if result:
    print(f"Tool execution result: {result}")
    """)


def example_error_handling():
    """Example: Error handling for policy evaluation."""
    print("\n" + "=" * 60)
    print("Example 9: Error Handling")
    print("=" * 60)

    print("""
# Error handling for policy evaluation

try:
    decision = client.evaluate_policy(
        action='tool:invoke',
        tool='execute_query'
    )

    if decision['decision'] == 'allow':
        # Proceed with action
        execute_action()
    else:
        # Handle denial
        log_denial(decision['reason'])

except requests.exceptions.HTTPError as e:
    if e.response.status_code == 400:
        print("Invalid policy evaluation request")

    elif e.response.status_code == 503:
        print("OPA service unavailable")
        # Fail-safe: deny by default
        decision = {'decision': 'deny', 'reason': 'Policy service unavailable'}

    else:
        print(f"Policy evaluation error: {e}")
        # Fail-safe: deny by default
        decision = {'decision': 'deny', 'reason': 'Policy evaluation failed'}

except Exception as e:
    print(f"Unexpected error: {e}")
    # Fail-safe: deny by default
    decision = {'decision': 'deny', 'reason': 'Internal error'}

# IMPORTANT: Always fail closed (deny) on errors
# Never allow actions when policy evaluation fails
    """)


def main():
    """Run all examples."""
    print("=" * 60)
    print("SARK Policy Evaluation Examples")
    print("=" * 60)

    print("\nNote: Set environment variables:")
    print("  export SARK_API_URL=https://sark.example.com")
    print("  export SARK_ACCESS_TOKEN=your-jwt-access-token")

    # Example 1: Basic evaluation
    # example_basic_evaluation()

    # Example 2: Server registration
    example_server_registration()

    # Example 3: Tool sensitivity
    example_tool_sensitivity()

    # Example 4: Role-based access
    example_role_based_access()

    # Example 5: Team-based access
    example_team_based_access()

    # Example 6: Parameter filtering
    example_parameter_filtering()

    # Example 7: Caching
    example_caching()

    # Example 8: Integration workflow
    example_integration_workflow()

    # Example 9: Error handling
    example_error_handling()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)

    print("\nTo run live examples, uncomment the calls in main()")


if __name__ == "__main__":
    main()
