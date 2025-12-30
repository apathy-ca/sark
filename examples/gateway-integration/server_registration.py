#!/usr/bin/env python3
"""
Server Registration Example

This example demonstrates how to register an MCP server with the Gateway
Registry, including proper model usage, validation, and error handling.

Best Practices Demonstrated:
- Creating valid GatewayServerInfo instances
- Using Pydantic validation to catch errors early
- Proper sensitivity level classification
- Team-based access control setup
- Health status monitoring

Author: Engineer 1 (Gateway Models Architect)
"""

import asyncio

from pydantic import HttpUrl, ValidationError

from sark.models.gateway import GatewayServerInfo, SensitivityLevel


def create_server_info_example() -> GatewayServerInfo:
    """
    Example: Create a GatewayServerInfo model with proper validation.

    This demonstrates how to construct server metadata that passes
    all Pydantic validators.

    Returns:
        Valid GatewayServerInfo instance
    """
    print("=" * 60)
    print("Example 1: Creating Server Info with Validation")
    print("=" * 60)

    try:
        # Create a properly validated server info object
        server_info = GatewayServerInfo(
            server_id="srv_postgres_prod_001",
            server_name="postgres-mcp-production",
            server_url=HttpUrl("https://postgres-mcp.example.com:8080"),
            sensitivity_level=SensitivityLevel.HIGH,
            authorized_teams=["data-engineering", "backend-team"],
            access_restrictions={
                "require_mfa": True,
                "ip_allowlist": ["10.0.0.0/8", "192.168.1.0/24"],
                "max_concurrent_connections": 50,
            },
            health_status="healthy",
            tools_count=12,
        )

        print("\n✅ Successfully created server info:")
        print(f"   Name: {server_info.server_name}")
        print(f"   URL: {server_info.server_url}")
        print(f"   Sensitivity: {server_info.sensitivity_level.value}")
        print(f"   Teams: {', '.join(server_info.authorized_teams)}")
        print(f"   Tools: {server_info.tools_count}")
        print()

        return server_info

    except ValidationError as e:
        print(f"\n❌ Validation failed: {e}")
        raise


def example_validation_errors():
    """
    Example: Common validation errors and how to avoid them.

    Demonstrates:
    - Invalid URL formats
    - Negative tools_count
    - Invalid sensitivity levels
    """
    print("=" * 60)
    print("Example 2: Handling Validation Errors")
    print("=" * 60 + "\n")

    # Example 1: Invalid URL
    print("Attempting to create server with invalid URL...")
    try:
        GatewayServerInfo(
            server_id="srv_001",
            server_name="test-server",
            server_url="not-a-valid-url",  # ❌ Invalid
            sensitivity_level=SensitivityLevel.LOW,
            authorized_teams=[],
            health_status="healthy",
            tools_count=0,
        )
    except ValidationError as e:
        print(f"❌ Expected error: {e.errors()[0]['msg']}")
        print("   Fix: Use a valid HTTP/HTTPS URL\n")

    # Example 2: Negative tools count
    print("Attempting to create server with negative tools_count...")
    try:
        GatewayServerInfo(
            server_id="srv_002",
            server_name="test-server",
            server_url=HttpUrl("http://localhost:8080"),
            sensitivity_level=SensitivityLevel.LOW,
            authorized_teams=[],
            health_status="healthy",
            tools_count=-5,  # ❌ Invalid
        )
    except ValidationError as e:
        print(f"❌ Expected error: {e.errors()[0]['msg']}")
        print("   Fix: Use tools_count >= 0\n")

    # Example 3: Invalid sensitivity level
    print("Attempting to create server with invalid sensitivity...")
    try:
        # Using raw dict to bypass enum validation
        data = {
            "server_id": "srv_003",
            "server_name": "test-server",
            "server_url": "http://localhost:8080",
            "sensitivity_level": "super-secret",  # ❌ Invalid
            "authorized_teams": [],
            "health_status": "healthy",
            "tools_count": 0,
        }
        GatewayServerInfo(**data)
    except ValidationError as e:
        print(f"❌ Expected error: {e.errors()[0]['msg']}")
        print(
            f"   Fix: Use one of {[s.value for s in SensitivityLevel]}\n"
        )


async def example_register_low_sensitivity_server():
    """
    Example: Register a low-sensitivity development server.

    Demonstrates:
    - Low sensitivity server setup
    - Minimal access restrictions
    - Development environment configuration
    """
    print("=" * 60)
    print("Example 3: Registering Low-Sensitivity Server")
    print("=" * 60)

    # Create server info
    server_info = GatewayServerInfo(
        server_id="srv_sandbox_001",
        server_name="sandbox-tools",
        server_url=HttpUrl("http://sandbox.local:8080"),
        sensitivity_level=SensitivityLevel.LOW,
        authorized_teams=["developers", "qa-team"],
        access_restrictions={
            "environment": "development",
            "require_mfa": False,  # Less strict for dev
        },
        health_status="healthy",
        tools_count=5,
    )

    print("\n📦 Low-Sensitivity Server Config:")
    print(f"   Name: {server_info.server_name}")
    print(f"   Sensitivity: {server_info.sensitivity_level.value}")
    print("   MFA Required: No (development environment)")
    print(f"   Authorized Teams: {', '.join(server_info.authorized_teams)}")
    print()

    # Note: Actual registration would use Gateway API
    print("💡 In production, send this model to:")
    print("   POST /api/v1/gateway/servers")
    print("   Body: server_info.model_dump_json()")


async def example_register_critical_server():
    """
    Example: Register a critical-sensitivity production server.

    Demonstrates:
    - Critical sensitivity server setup
    - Strict access controls
    - Production environment configuration
    - Audit requirements
    """
    print("\n" + "=" * 60)
    print("Example 4: Registering Critical-Sensitivity Server")
    print("=" * 60)

    server_info = GatewayServerInfo(
        server_id="srv_payment_prod_001",
        server_name="payment-processing-mcp",
        server_url=HttpUrl("https://payment-mcp.secure.example.com:8443"),
        sensitivity_level=SensitivityLevel.CRITICAL,
        authorized_teams=["payments-team", "security-team"],
        access_restrictions={
            "environment": "production",
            "require_mfa": True,
            "require_hardware_key": True,
            "ip_allowlist": ["10.0.1.0/24"],  # Highly restricted
            "audit_all_requests": True,
            "max_concurrent_connections": 10,
            "connection_timeout_seconds": 30,
        },
        health_status="healthy",
        tools_count=8,
    )

    print("\n🔒 Critical-Sensitivity Server Config:")
    print(f"   Name: {server_info.server_name}")
    print(f"   Sensitivity: {server_info.sensitivity_level.value}")
    print("   MFA Required: Yes")
    print("   Hardware Key Required: Yes")
    print(f"   IP Allowlist: {server_info.access_restrictions['ip_allowlist']}")
    print("   Audit All Requests: Yes")
    print("   Max Connections: 10")
    print(f"   Teams: {', '.join(server_info.authorized_teams)}")
    print()

    print("⚠️  Critical servers require additional approval workflow")
    print("   Contact security team before registration")


def example_sensitivity_level_guidelines():
    """
    Example: Guidelines for choosing the right sensitivity level.

    Demonstrates:
    - When to use each sensitivity level
    - Security implications
    - Compliance requirements
    """
    print("\n" + "=" * 60)
    print("Example 5: Sensitivity Level Selection Guide")
    print("=" * 60 + "\n")

    guidelines = {
        SensitivityLevel.LOW: {
            "description": "Public or non-sensitive data",
            "examples": ["Documentation servers", "Public API endpoints", "Dev/test tools"],
            "mfa_required": False,
            "audit_level": "Basic",
        },
        SensitivityLevel.MEDIUM: {
            "description": "Internal business data",
            "examples": ["CRM tools", "Analytics servers", "Internal dashboards"],
            "mfa_required": True,
            "audit_level": "Standard",
        },
        SensitivityLevel.HIGH: {
            "description": "Sensitive business data",
            "examples": ["Customer PII", "Financial records", "HR systems"],
            "mfa_required": True,
            "audit_level": "Enhanced",
        },
        SensitivityLevel.CRITICAL: {
            "description": "Highly regulated or critical infrastructure",
            "examples": ["Payment processing", "Healthcare records", "Security systems"],
            "mfa_required": True,
            "audit_level": "Full (all requests logged)",
        },
    }

    for level, info in guidelines.items():
        print(f"{level.value.upper()} Sensitivity:")
        print(f"  Description: {info['description']}")
        print(f"  Examples: {', '.join(info['examples'])}")
        print(f"  MFA Required: {'Yes' if info['mfa_required'] else 'No'}")
        print(f"  Audit Level: {info['audit_level']}")
        print()


def example_team_based_access_control():
    """
    Example: Setting up team-based access control.

    Demonstrates:
    - Multiple team authorization
    - Access restriction inheritance
    - Team hierarchy considerations
    """
    print("=" * 60)
    print("Example 6: Team-Based Access Control")
    print("=" * 60 + "\n")

    # Multi-team server
    server_info = GatewayServerInfo(
        server_id="srv_analytics_001",
        server_name="analytics-platform-mcp",
        server_url=HttpUrl("https://analytics.example.com:8080"),
        sensitivity_level=SensitivityLevel.MEDIUM,
        authorized_teams=[
            "data-engineering",
            "data-science",
            "product-analytics",
            "executive-team",
        ],
        access_restrictions={
            "team_hierarchy_enabled": True,
            "managers_have_full_access": True,
        },
        health_status="healthy",
        tools_count=20,
    )

    print("👥 Multi-Team Access Configuration:")
    print(f"   Server: {server_info.server_name}")
    print(f"   Authorized Teams ({len(server_info.authorized_teams)}):")
    for team in server_info.authorized_teams:
        print(f"     - {team}")
    print()

    print("💡 Access Control Logic:")
    print("   - Members of any authorized team can access the server")
    print("   - Team managers inherit their team's permissions")
    print("   - Executive team has full access across all tools")
    print()


def example_health_status_values():
    """
    Example: Understanding health status values.

    Demonstrates:
    - Valid health status states
    - When to use each status
    - Health monitoring implications
    """
    print("=" * 60)
    print("Example 7: Health Status Management")
    print("=" * 60 + "\n")

    health_statuses = {
        "healthy": "Server is fully operational",
        "degraded": "Server is operational but experiencing issues",
        "unhealthy": "Server is not operational",
        "maintenance": "Server is undergoing planned maintenance",
        "unknown": "Health status cannot be determined",
    }

    print("Valid Health Status Values:\n")
    for status, description in health_statuses.items():
        GatewayServerInfo(
            server_id=f"srv_{status}_001",
            server_name=f"example-{status}",
            server_url=HttpUrl("http://localhost:8080"),
            sensitivity_level=SensitivityLevel.LOW,
            authorized_teams=[],
            health_status=status,
            tools_count=0,
        )
        print(f"  {status.upper()}: {description}")

    print("\n💡 Health Monitoring:")
    print("   - Gateway polls server health every 30 seconds")
    print("   - Unhealthy servers are removed from discovery after 5 minutes")
    print("   - Maintenance mode prevents new connections but allows existing ones")


def main():
    """
    Run all examples.
    """
    print("\n")
    print("=" * 60)
    print("  MCP SERVER REGISTRATION - EXAMPLES")
    print("=" * 60)
    print("\nThese examples demonstrate how to properly register")
    print("MCP servers with the Gateway Registry.\n")

    # Synchronous examples
    create_server_info_example()
    example_validation_errors()
    example_sensitivity_level_guidelines()
    example_team_based_access_control()
    example_health_status_values()

    # Async examples
    asyncio.run(example_register_low_sensitivity_server())
    asyncio.run(example_register_critical_server())

    print("\n" + "=" * 60)
    print("  All examples completed!")
    print("=" * 60)
    print("\n💡 Next Steps:")
    print("   1. Review your server's sensitivity level")
    print("   2. Configure appropriate access restrictions")
    print("   3. Set up team-based authorization")
    print("   4. Register via POST /api/v1/gateway/servers")
    print("   5. Monitor health status in Gateway dashboard\n")


if __name__ == "__main__":
    main()
