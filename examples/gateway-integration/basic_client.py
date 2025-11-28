#!/usr/bin/env python3
"""
Basic Gateway Client Example

This example demonstrates how to use the Gateway client to interact with
the MCP Gateway Registry for discovering and connecting to MCP servers.

Best Practices Demonstrated:
- Proper client initialization and cleanup
- Error handling with custom Gateway exceptions
- Using Pydantic models for type safety
- Resource management with async context managers

Author: Engineer 1 (Gateway Models Architect)
"""

import asyncio
from contextlib import asynccontextmanager

from sark.models.gateway import GatewayServerInfo, GatewayToolInfo, SensitivityLevel
from sark.services.gateway import GatewayClient
from sark.services.gateway.exceptions import (
    GatewayConnectionError,
    GatewayTimeoutError,
    GatewayAuthenticationError,
)


@asynccontextmanager
async def get_gateway_client():
    """
    Context manager for Gateway client with automatic cleanup.

    Example usage:
        async with get_gateway_client() as client:
            servers = await client.list_servers()
    """
    client = GatewayClient(
        gateway_url="http://localhost:8080",
        api_key="gw_sk_test_your_api_key_here",
        timeout=10.0,
        max_retries=3,
    )
    try:
        yield client
    finally:
        await client.close()


async def example_list_servers():
    """
    Example: List all available MCP servers in the Gateway registry.

    Returns:
        List of GatewayServerInfo models
    """
    print("=" * 60)
    print("Example 1: Listing Available Servers")
    print("=" * 60)

    async with get_gateway_client() as client:
        try:
            # List all servers
            servers = await client.list_servers()

            print(f"\nFound {len(servers)} MCP servers:\n")

            for server in servers:
                # server is a GatewayServerInfo Pydantic model
                print(f"📦 {server.server_name}")
                print(f"   ID: {server.server_id}")
                print(f"   URL: {server.server_url}")
                print(f"   Health: {server.health_status}")
                print(f"   Sensitivity: {server.sensitivity_level.value}")
                print(f"   Tools: {server.tools_count}")
                print(f"   Teams: {', '.join(server.authorized_teams)}")
                print()

            return servers

        except GatewayConnectionError as e:
            print(f"❌ Connection failed: {e}")
            print("   Ensure the Gateway Registry is running at http://localhost:8080")
            return []

        except GatewayTimeoutError as e:
            print(f"❌ Request timed out: {e}")
            print("   The Gateway may be slow to respond. Consider increasing timeout.")
            return []

        except GatewayAuthenticationError as e:
            print(f"❌ Authentication failed: {e}")
            print("   Check your API key configuration.")
            return []


async def example_filter_servers_by_sensitivity():
    """
    Example: Filter servers by sensitivity level.

    Demonstrates:
    - Using enum values for filtering
    - Type-safe model attribute access
    """
    print("\n" + "=" * 60)
    print("Example 2: Filtering Servers by Sensitivity")
    print("=" * 60)

    async with get_gateway_client() as client:
        servers = await client.list_servers()

        # Filter for high-sensitivity servers
        high_security_servers = [
            server
            for server in servers
            if server.sensitivity_level
            in [SensitivityLevel.HIGH, SensitivityLevel.CRITICAL]
        ]

        print(f"\nHigh-security servers ({len(high_security_servers)}):\n")

        for server in high_security_servers:
            print(f"🔒 {server.server_name}")
            print(f"   Sensitivity: {server.sensitivity_level.value}")
            print(f"   Restrictions: {server.access_restrictions}")
            print()


async def example_get_server_details():
    """
    Example: Get detailed information about a specific server.

    Demonstrates:
    - Fetching individual server info
    - Handling server not found scenarios
    """
    print("\n" + "=" * 60)
    print("Example 3: Getting Server Details")
    print("=" * 60)

    async with get_gateway_client() as client:
        server_name = "postgres-mcp"  # Example server name

        try:
            server_info = await client.get_server_info(server_name)

            print(f"\nServer Details for '{server_name}':\n")
            print(f"ID: {server_info.server_id}")
            print(f"Name: {server_info.server_name}")
            print(f"URL: {server_info.server_url}")
            print(f"Health: {server_info.health_status}")
            print(f"Sensitivity: {server_info.sensitivity_level.value}")
            print(f"Tools Available: {server_info.tools_count}")

            # Access restrictions (if any)
            if server_info.access_restrictions:
                print("\nAccess Restrictions:")
                for key, value in server_info.access_restrictions.items():
                    print(f"  - {key}: {value}")

            return server_info

        except Exception as e:
            print(f"❌ Failed to get server info: {e}")
            return None


async def example_list_tools_for_server():
    """
    Example: List all tools available on a specific server.

    Demonstrates:
    - Tool discovery
    - Understanding tool sensitivity and parameters
    """
    print("\n" + "=" * 60)
    print("Example 4: Listing Tools for a Server")
    print("=" * 60)

    async with get_gateway_client() as client:
        server_name = "postgres-mcp"

        try:
            tools = await client.list_tools(server_name)

            print(f"\nTools available on '{server_name}' ({len(tools)}):\n")

            for tool in tools:
                # tool is a GatewayToolInfo Pydantic model
                print(f"🔧 {tool.tool_name}")
                print(f"   Description: {tool.description}")
                print(f"   Sensitivity: {tool.sensitivity_level.value}")

                # Show parameters
                if tool.parameters:
                    print(f"   Parameters:")
                    for param in tool.parameters:
                        param_name = param.get("name", "unknown")
                        param_type = param.get("type", "any")
                        required = param.get("required", False)
                        req_marker = "required" if required else "optional"
                        print(f"     - {param_name} ({param_type}) [{req_marker}]")

                # Show sensitive parameters
                if tool.sensitive_params:
                    print(f"   Sensitive Params: {', '.join(tool.sensitive_params)}")

                # Show required capabilities
                if tool.required_capabilities:
                    print(
                        f"   Required Capabilities: {', '.join(tool.required_capabilities)}"
                    )

                print()

            return tools

        except Exception as e:
            print(f"❌ Failed to list tools: {e}")
            return []


async def example_health_check():
    """
    Example: Check Gateway health status.

    Demonstrates:
    - Health monitoring
    - Readiness checks before making requests
    """
    print("\n" + "=" * 60)
    print("Example 5: Gateway Health Check")
    print("=" * 60)

    async with get_gateway_client() as client:
        try:
            is_healthy = await client.health_check()

            if is_healthy:
                print("✅ Gateway is healthy and ready")
            else:
                print("❌ Gateway health check failed")

            return is_healthy

        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False


async def main():
    """
    Run all examples in sequence.
    """
    print("\n")
    print("=" * 60)
    print("  MCP GATEWAY CLIENT - BASIC EXAMPLES")
    print("=" * 60)
    print("\nThese examples demonstrate basic Gateway client usage.")
    print("Ensure the Gateway Registry is running before executing.\n")

    # Run examples
    await example_list_servers()
    await example_filter_servers_by_sensitivity()
    await example_get_server_details()
    await example_list_tools_for_server()
    await example_health_check()

    print("\n" + "=" * 60)
    print("  All examples completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
