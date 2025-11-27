#!/usr/bin/env python3
"""
Example 1: Basic MCP Tool Invocation

This example demonstrates the simplest case of invoking an MCP tool through SARK.
It shows authentication, tool invocation, and response handling.

Prerequisites:
- SARK running at http://localhost:8000
- Valid API credentials
- At least one registered MCP server with tools

Usage:
    python examples/01_basic_tool_invocation.py
"""

import json
import os
from typing import Any, Dict

import requests


class SARKClient:
    """Simple SARK API client for examples."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.access_token: str | None = None

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate with SARK using LDAP credentials."""
        print(f"\n📡 Authenticating as {username}...")

        response = self.session.post(
            f"{self.base_url}/api/v1/auth/login/ldap",
            json={"username": username, "password": password},
        )

        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
            print(f"✅ Authenticated successfully!")
            print(f"   User: {data['user']['email']}")
            print(f"   Roles: {', '.join(data['user']['roles'])}")
            return data
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            print(f"   Error: {response.json()}")
            raise Exception("Authentication failed")

    def list_servers(self) -> list[Dict[str, Any]]:
        """List all available MCP servers."""
        print(f"\n📋 Fetching available MCP servers...")

        response = self.session.get(f"{self.base_url}/api/v1/servers")

        if response.status_code == 200:
            servers = response.json()["items"]
            print(f"✅ Found {len(servers)} MCP servers:")
            for server in servers:
                print(f"   - {server['name']} ({server['status']}) - {len(server.get('tools', []))} tools")
            return servers
        else:
            print(f"❌ Failed to fetch servers: {response.status_code}")
            return []

    def list_tools(self, server_id: str | None = None) -> list[Dict[str, Any]]:
        """List available MCP tools, optionally filtered by server."""
        print(f"\n🔧 Fetching available MCP tools...")

        url = f"{self.base_url}/api/v1/tools"
        if server_id:
            url += f"?server_id={server_id}"

        response = self.session.get(url)

        if response.status_code == 200:
            tools = response.json()["items"]
            print(f"✅ Found {len(tools)} tools:")
            for tool in tools:
                sensitivity = tool.get('sensitivity_level', 'unknown')
                approval = " [REQUIRES APPROVAL]" if tool.get('requires_approval') else ""
                print(f"   - {tool['name']} ({sensitivity}){approval}")
                print(f"     {tool.get('description', 'No description')}")
            return tools
        else:
            print(f"❌ Failed to fetch tools: {response.status_code}")
            return []

    def invoke_tool(
        self,
        tool_id: str,
        arguments: Dict[str, Any],
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Invoke an MCP tool through SARK."""
        print(f"\n🚀 Invoking tool...")
        print(f"   Tool ID: {tool_id}")
        print(f"   Arguments: {json.dumps(arguments, indent=2)}")

        response = self.session.post(
            f"{self.base_url}/api/v1/tools/invoke",
            json={
                "tool_id": tool_id,
                "arguments": arguments,
                "timeout": timeout
            },
        )

        print(f"\n📊 Response Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Tool invocation successful!")
            print(f"   Request ID: {result.get('request_id')}")
            print(f"   Audit ID: {result.get('audit_id')}")

            # Check for cache status
            cache_status = response.headers.get('X-Cache-Status', 'UNKNOWN')
            print(f"   Cache Status: {cache_status}")

            # Check for policy decision
            policy_decision = response.headers.get('X-Policy-Decision', 'UNKNOWN')
            print(f"   Policy Decision: {policy_decision}")

            return result
        elif response.status_code == 403:
            error = response.json()
            print(f"🚫 Access Denied!")
            print(f"   Reason: {error.get('reason', 'Unknown')}")
            print(f"   Required roles: {error.get('required_roles', [])}")
            raise Exception("Access denied")
        elif response.status_code == 404:
            print(f"❌ Tool not found")
            raise Exception("Tool not found")
        else:
            print(f"❌ Tool invocation failed")
            print(f"   Error: {response.json()}")
            raise Exception(f"Tool invocation failed: {response.status_code}")


def main():
    """Run the basic tool invocation example."""
    print("=" * 80)
    print("SARK MCP Example 1: Basic Tool Invocation")
    print("=" * 80)

    # Configuration (use environment variables or defaults)
    SARK_URL = os.getenv("SARK_URL", "http://localhost:8000")
    USERNAME = os.getenv("SARK_USERNAME", "admin")
    PASSWORD = os.getenv("SARK_PASSWORD", "password")

    # Create client
    client = SARKClient(base_url=SARK_URL)

    try:
        # Step 1: Authenticate
        auth_result = client.login(USERNAME, PASSWORD)

        # Step 2: List available MCP servers
        servers = client.list_servers()

        if not servers:
            print("\n⚠️  No MCP servers registered. Please register a server first.")
            print("   See: examples/register_server.py")
            return

        # Step 3: List available tools
        tools = client.list_tools()

        if not tools:
            print("\n⚠️  No MCP tools available.")
            return

        # Step 4: Select a tool to invoke (use first low/medium sensitivity tool)
        selected_tool = None
        for tool in tools:
            if tool.get('sensitivity_level') in ['low', 'medium'] and not tool.get('requires_approval'):
                selected_tool = tool
                break

        if not selected_tool:
            print("\n⚠️  No suitable tools found for this example.")
            print("   Looking for: low/medium sensitivity, no approval required")
            return

        print(f"\n🎯 Selected tool: {selected_tool['name']}")

        # Step 5: Prepare arguments (example: if tool accepts query parameter)
        # This is a generic example - adjust based on your tool's schema
        arguments = {}

        # Check tool parameters to build appropriate arguments
        parameters = selected_tool.get('parameters', {})
        if parameters.get('properties'):
            # Build sample arguments based on schema
            for param_name, param_schema in parameters['properties'].items():
                param_type = param_schema.get('type', 'string')

                if param_type == 'string':
                    arguments[param_name] = "example_value"
                elif param_type == 'integer':
                    arguments[param_name] = 100
                elif param_type == 'boolean':
                    arguments[param_name] = True
                elif param_type == 'array':
                    arguments[param_name] = []
                elif param_type == 'object':
                    arguments[param_name] = {}

        # If tool has no parameters, use empty dict
        if not arguments:
            print("   (Tool accepts no parameters)")

        # Step 6: Invoke the tool
        result = client.invoke_tool(
            tool_id=selected_tool['id'],
            arguments=arguments
        )

        # Step 7: Display results
        print("\n📦 Tool Results:")
        print(json.dumps(result.get('result', {}), indent=2))

        print("\n" + "=" * 80)
        print("✅ Example completed successfully!")
        print("=" * 80)

        # Show what happened behind the scenes
        print("\n💡 What happened:")
        print("   1. ✅ Authenticated with SARK (LDAP)")
        print("   2. ✅ Listed available MCP servers")
        print("   3. ✅ Listed available MCP tools")
        print("   4. ✅ OPA evaluated authorization policy")
        print("   5. ✅ SARK proxied request to MCP server")
        print("   6. ✅ MCP server executed the tool")
        print("   7. ✅ Result returned through SARK")
        print("   8. ✅ Audit event logged to TimescaleDB")
        print("   9. ✅ Event forwarded to SIEM (if configured)")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
