#!/usr/bin/env python3
"""
Error Handling and Validation Examples

This example demonstrates comprehensive error handling for Gateway operations,
including validation errors, network failures, and authorization denials.

Best Practices Demonstrated:
- Pydantic validation error handling
- Network error recovery with retry logic
- Authorization failure graceful degradation
- User-friendly error messages
- Logging and debugging strategies

Author: Engineer 1 (Gateway Models Architect)
"""

import asyncio
from typing import Any

from pydantic import HttpUrl, ValidationError

from sark.models.gateway import (
    GatewayAuthorizationRequest,
    GatewayServerInfo,
    GatewayToolInfo,
    SensitivityLevel,
)
from sark.services.gateway import GatewayClient
from sark.services.gateway.exceptions import (
    GatewayAuthenticationError,
    GatewayConnectionError,
    GatewayError,
    GatewayTimeoutError,
)


def example_validation_error_handling():
    """
    Example: Handle Pydantic validation errors gracefully.

    Demonstrates:
    - Catching ValidationError
    - Extracting error details
    - Providing user-friendly feedback
    """
    print("=" * 60)
    print("Example 1: Handling Validation Errors")
    print("=" * 60 + "\n")

    # Attempt to create invalid server info
    invalid_data = {
        "server_id": "srv_001",
        "server_name": "test-server",
        "server_url": "not-a-url",  # ❌ Invalid
        "sensitivity_level": "ultra-secret",  # ❌ Invalid
        "authorized_teams": [],
        "health_status": "healthy",
        "tools_count": -5,  # ❌ Invalid
    }

    try:
        GatewayServerInfo(**invalid_data)
    except ValidationError as e:
        print("❌ Validation failed with multiple errors:\n")

        for error in e.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            error_type = error["type"]

            print(f"   Field: {field}")
            print(f"   Error: {message}")
            print(f"   Type: {error_type}")
            print()

        # Extract specific error types for targeted handling
        print("💡 Error Handling Strategy:\n")
        for error in e.errors():
            field = error["loc"][0]
            if field == "server_url":
                print("   - server_url: Validate URL format before submission")
            elif field == "sensitivity_level":
                print(
                    f"   - sensitivity_level: Use one of {[s.value for s in SensitivityLevel]}"
                )
            elif field == "tools_count":
                print("   - tools_count: Ensure value is >= 0")
        print()


def example_custom_error_messages():
    """
    Example: Create user-friendly error messages from validation errors.

    Demonstrates:
    - Error message transformation
    - Context-aware messaging
    - Actionable guidance
    """
    print("=" * 60)
    print("Example 2: User-Friendly Error Messages")
    print("=" * 60 + "\n")

    def create_user_friendly_error(e: ValidationError) -> list[str]:
        """Convert Pydantic errors to user-friendly messages."""
        friendly_messages = []

        for error in e.errors():
            field = error["loc"][0] if error["loc"] else "unknown"
            error_type = error["type"]

            if error_type == "url_parsing":
                friendly_messages.append(
                    f"❌ {field}: Please provide a valid HTTP or HTTPS URL "
                    f"(e.g., https://example.com:8080)"
                )
            elif error_type == "enum":
                friendly_messages.append(
                    f"❌ {field}: Invalid value. "
                    f"Choose from: {', '.join([s.value for s in SensitivityLevel])}"
                )
            elif error_type == "greater_than_equal":
                friendly_messages.append(
                    f"❌ {field}: Value must be greater than or equal to 0"
                )
            elif error_type == "missing":
                friendly_messages.append(f"❌ {field}: This field is required")
            else:
                friendly_messages.append(f"❌ {field}: {error['msg']}")

        return friendly_messages

    # Test with invalid data
    try:
        GatewayAuthorizationRequest(
            action="invalid:action",  # Will fail validation
            parameters={},
            gateway_metadata={},
        )
    except ValidationError as e:
        messages = create_user_friendly_error(e)
        print("User-Friendly Error Messages:\n")
        for msg in messages:
            print(f"   {msg}")
        print()


async def example_network_error_handling():
    """
    Example: Handle network errors with proper exception handling.

    Demonstrates:
    - GatewayConnectionError handling
    - GatewayTimeoutError handling
    - GatewayAuthenticationError handling
    - Retry logic
    """
    print("=" * 60)
    print("Example 3: Network Error Handling")
    print("=" * 60 + "\n")

    # Intentionally use invalid Gateway URL to trigger errors
    client = GatewayClient(
        gateway_url="http://localhost:9999",  # Non-existent server
        api_key="invalid_key",
        timeout=2.0,  # Short timeout
        max_retries=2,
    )

    # Example 1: Connection Error
    print("1️⃣  Testing Connection Error:")
    try:
        await client.health_check()
    except GatewayConnectionError as e:
        print(f"   ❌ Connection failed: {e}")
        print("   💡 Solution: Verify Gateway URL and network connectivity")
        print(f"      - Check if Gateway is running")
        print(f"      - Verify firewall rules allow access")
        print(f"      - Confirm URL is correct: {client.gateway_url}")
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
    print()

    # Example 2: Timeout Error
    print("2️⃣  Testing Timeout Error:")
    try:
        # This will timeout after 2 seconds
        await client.list_servers()
    except GatewayTimeoutError as e:
        print(f"   ❌ Request timed out: {e}")
        print("   💡 Solution: Increase timeout or check Gateway performance")
        print(f"      - Current timeout: {client.timeout}s")
        print(f"      - Consider increasing to 10-30s for slow networks")
    except GatewayConnectionError:
        print("   ❌ Connection error (expected for this example)")
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
    print()

    await client.close()


async def example_retry_logic():
    """
    Example: Implement custom retry logic for transient failures.

    Demonstrates:
    - Exponential backoff
    - Maximum retry attempts
    - Retry-able vs non-retryable errors
    """
    print("=" * 60)
    print("Example 4: Custom Retry Logic")
    print("=" * 60 + "\n")

    async def fetch_with_retry(
        client: GatewayClient, max_retries: int = 3
    ) -> list[Any]:
        """Fetch servers with custom retry logic."""
        for attempt in range(1, max_retries + 1):
            try:
                print(f"   Attempt {attempt}/{max_retries}...")
                servers = await client.list_servers()
                print(f"   ✅ Success on attempt {attempt}")
                return servers

            except GatewayTimeoutError:
                # Retryable error
                if attempt < max_retries:
                    backoff = 2**attempt  # Exponential backoff: 2s, 4s, 8s
                    print(f"   ⏳ Timeout, retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                else:
                    print("   ❌ Max retries exceeded")
                    raise

            except GatewayAuthenticationError:
                # Non-retryable error
                print("   ❌ Authentication error (not retrying)")
                raise

            except GatewayConnectionError:
                # Retryable error
                if attempt < max_retries:
                    backoff = 2**attempt
                    print(f"   ⚠️  Connection error, retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                else:
                    print("   ❌ Max retries exceeded")
                    raise

    client = GatewayClient(
        gateway_url="http://localhost:9999",
        api_key="test_key",
        timeout=1.0,
        max_retries=1,  # Disable built-in retry to demo custom logic
    )

    try:
        await fetch_with_retry(client, max_retries=3)
    except GatewayError as e:
        print(f"\n   Final error: {e}")

    await client.close()
    print()


def example_authorization_error_scenarios():
    """
    Example: Handle authorization-specific errors.

    Demonstrates:
    - Authorization denial handling
    - Missing permissions
    - Sensitivity level mismatches
    - Time-based restrictions
    """
    print("=" * 60)
    print("Example 5: Authorization Error Scenarios")
    print("=" * 60 + "\n")

    authorization_errors = [
        {
            "scenario": "Missing Capability",
            "allowed": False,
            "reason": "User lacks required capability: data:delete",
            "fix": "Request 'data:delete' capability from team admin",
        },
        {
            "scenario": "Sensitivity Mismatch",
            "allowed": False,
            "reason": "Tool sensitivity (critical) > user clearance (medium)",
            "fix": "Contact security team for elevated access",
        },
        {
            "scenario": "Time Restriction",
            "allowed": False,
            "reason": "Tool access restricted to business hours (9-18)",
            "fix": "Wait until business hours or request emergency override",
        },
        {
            "scenario": "MFA Required",
            "allowed": False,
            "reason": "Multi-factor authentication required but not provided",
            "fix": "Complete MFA verification and retry",
        },
        {
            "scenario": "IP Restriction",
            "allowed": False,
            "reason": "Client IP 203.0.113.45 not in allowlist",
            "fix": "Connect via approved network or request IP allowlist update",
        },
    ]

    for error in authorization_errors:
        print(f"Scenario: {error['scenario']}")
        print(f"   Status: {'✅ Allowed' if error['allowed'] else '❌ Denied'}")
        print(f"   Reason: {error['reason']}")
        print(f"   Fix: {error['fix']}")
        print()


def example_graceful_degradation():
    """
    Example: Implement graceful degradation when services are unavailable.

    Demonstrates:
    - Fallback mechanisms
    - Cached data usage
    - Degraded mode operation
    """
    print("=" * 60)
    print("Example 6: Graceful Degradation")
    print("=" * 60 + "\n")

    # Simulated cache
    cached_servers = [
        {
            "server_name": "postgres-mcp",
            "cached_at": "2024-01-15T10:00:00Z",
            "status": "cached",
        },
        {
            "server_name": "redis-mcp",
            "cached_at": "2024-01-15T10:00:00Z",
            "status": "cached",
        },
    ]

    async def get_servers_with_fallback(
        client: GatewayClient,
    ) -> tuple[list[Any], bool]:
        """Get servers with fallback to cache."""
        try:
            # Try to fetch from Gateway
            servers = await client.list_servers()
            return servers, False  # Not using cache

        except GatewayError as e:
            print(f"   ⚠️  Gateway unavailable: {e}")
            print(f"   💡 Falling back to cached data...")
            return cached_servers, True  # Using cache

    client = GatewayClient(
        gateway_url="http://localhost:9999",  # Unavailable
        api_key="test",
        timeout=1.0,
        max_retries=1,
    )

    servers, using_cache = await get_servers_with_fallback(client)

    if using_cache:
        print(f"\n   📦 Retrieved {len(servers)} servers from cache")
        print("   ⚠️  Data may be stale - some servers may be offline")
        for server in servers:
            print(f"      - {server['server_name']} (cached {server['cached_at']})")
    else:
        print(f"\n   ✅ Retrieved {len(servers)} servers from Gateway (live)")

    await client.close()
    print()


def example_debugging_strategies():
    """
    Example: Debugging strategies for Gateway integration issues.

    Demonstrates:
    - Structured logging
    - Error context capture
    - Request/response tracing
    """
    print("=" * 60)
    print("Example 7: Debugging Strategies")
    print("=" * 60 + "\n")

    debugging_checklist = {
        "Validation Errors": [
            "Check Pydantic model field types match data",
            "Verify enum values are from valid sets",
            "Ensure required fields are provided",
            "Review field validators for custom rules",
        ],
        "Network Errors": [
            "Verify Gateway URL is correct and reachable",
            "Check firewall rules allow outbound connections",
            "Test network connectivity with curl/wget",
            "Review timeout settings (increase if needed)",
        ],
        "Authorization Errors": [
            "Confirm user has required capabilities",
            "Check tool sensitivity vs user clearance",
            "Verify time-based restrictions (business hours)",
            "Review IP allowlist configuration",
        ],
        "Performance Issues": [
            "Enable client-side caching",
            "Review retry configuration (may cause delays)",
            "Check Gateway server performance metrics",
            "Consider connection pooling settings",
        ],
    }

    for category, checklist in debugging_checklist.items():
        print(f"🔍 {category}:")
        for item in checklist:
            print(f"   □ {item}")
        print()

    print("💡 Logging Best Practices:")
    print("   - Log request_id for correlation")
    print("   - Include user_id and action in logs")
    print("   - Log retry attempts and backoff times")
    print("   - Redact sensitive parameters before logging")
    print()


async def main():
    """
    Run all examples.
    """
    print("\n")
    print("=" * 60)
    print("  MCP GATEWAY ERROR HANDLING - EXAMPLES")
    print("=" * 60)
    print("\nThese examples demonstrate comprehensive error handling")
    print("for Gateway operations.\n")

    # Synchronous examples
    example_validation_error_handling()
    example_custom_error_messages()
    example_authorization_error_scenarios()
    example_debugging_strategies()

    # Async examples
    await example_network_error_handling()
    await example_retry_logic()
    await example_graceful_degradation()

    print("=" * 60)
    print("  All examples completed!")
    print("=" * 60)
    print("\n💡 Key Takeaways:")
    print("   1. Handle Pydantic validation errors with user-friendly messages")
    print("   2. Implement retry logic for transient network failures")
    print("   3. Distinguish retryable vs non-retryable errors")
    print("   4. Provide clear guidance when authorization fails")
    print("   5. Use graceful degradation with cached data")
    print("   6. Follow debugging checklist for systematic troubleshooting")
    print("   7. Log errors with context for easier debugging\n")


if __name__ == "__main__":
    asyncio.run(main())
