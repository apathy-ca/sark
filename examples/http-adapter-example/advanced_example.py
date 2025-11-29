"""
HTTP Adapter Advanced Features Example

This example demonstrates advanced features:
- Rate limiting
- Circuit breaker
- Retry logic
- Error handling

Version: 2.0.0
Engineer: ENGINEER-2
"""

import asyncio
from datetime import datetime

from sark.adapters.http import HTTPAdapter
from sark.models.base import ResourceSchema, InvocationRequest


async def example_rate_limiting():
    """Example: Rate limiting requests."""
    print("\n" + "=" * 60)
    print("Rate Limiting Example")
    print("=" * 60)

    # Create adapter with rate limiting: 5 requests per second
    adapter = HTTPAdapter(
        base_url="https://jsonplaceholder.typicode.com",
        auth_config={"type": "none"},
        rate_limit=5.0,  # 5 requests/second
    )

    resource = ResourceSchema(
        id="http:jsonplaceholder",
        name="JSONPlaceholder API",
        protocol="http",
        endpoint="https://jsonplaceholder.typicode.com",
        sensitivity_level="low",
        metadata={},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    print("✓ Adapter created with rate limiting (5 req/s)")
    print("  Making 10 requests...")

    start_time = asyncio.get_event_loop().time()

    # Make 10 requests
    for i in range(10):
        request = InvocationRequest(
            capability_id=f"{resource.id}:get_posts",
            principal_id="example-user",
            arguments={},
            context={
                "capability_metadata": {
                    "http_method": "GET",
                    "http_path": "/posts"
                }
            }
        )

        result = await adapter.invoke(request)
        print(f"  [{i+1}/10] Request completed: {result.success}")

    end_time = asyncio.get_event_loop().time()
    duration = end_time - start_time

    print(f"\n✓ All requests completed in {duration:.2f}s")
    print(f"  Expected time: ~2s (10 requests at 5/s)")
    print(f"  Rate limiting enforced: {'✓' if duration >= 1.5 else '✗'}")


async def example_circuit_breaker():
    """Example: Circuit breaker protection."""
    print("\n" + "=" * 60)
    print("Circuit Breaker Example")
    print("=" * 60)

    # Create adapter with low circuit breaker threshold for demo
    adapter = HTTPAdapter(
        base_url="https://httpstat.us",  # Service that can return error codes
        auth_config={"type": "none"},
        circuit_breaker_threshold=3,  # Open after 3 failures
        max_retries=1,  # Minimal retries for faster demo
    )

    resource = ResourceSchema(
        id="http:httpstat",
        name="HTTP Status API",
        protocol="http",
        endpoint="https://httpstat.us",
        sensitivity_level="low",
        metadata={},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    print("✓ Adapter created with circuit breaker (threshold=3)")
    print("  Simulating failures by calling /500 endpoint...")

    # Make requests that will fail (HTTP 500)
    for i in range(5):
        request = InvocationRequest(
            capability_id=f"{resource.id}:get_500",
            principal_id="example-user",
            arguments={},
            context={
                "capability_metadata": {
                    "http_method": "GET",
                    "http_path": "/500"  # Always returns 500
                }
            }
        )

        result = await adapter.invoke(request)
        status = "✓" if result.success else "✗"
        print(f"  [{i+1}/5] {status} Success: {result.success}, Error: {result.error or 'None'}")

        # Check circuit breaker state
        state = adapter.circuit_breaker.state
        if state == "OPEN":
            print(f"\n  ⚠ Circuit breaker opened after {i+1} failures!")
            print("  Future requests will fail fast without hitting the API")
            break

        await asyncio.sleep(0.5)  # Small delay between requests

    print(f"\n✓ Circuit breaker state: {adapter.circuit_breaker.state}")


async def example_retry_logic():
    """Example: Automatic retry with exponential backoff."""
    print("\n" + "=" * 60)
    print("Retry Logic Example")
    print("=" * 60)

    adapter = HTTPAdapter(
        base_url="https://httpstat.us",
        auth_config={"type": "none"},
        max_retries=3,  # Try 3 times
        timeout=5.0,
    )

    resource = ResourceSchema(
        id="http:httpstat",
        name="HTTP Status API",
        protocol="http",
        endpoint="https://httpstat.us",
        sensitivity_level="low",
        metadata={},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    print("✓ Adapter created with retry logic (max_retries=3)")
    print("  Making request to simulate server error...")

    request = InvocationRequest(
        capability_id=f"{resource.id}:get_503",
        principal_id="example-user",
        arguments={},
        context={
            "capability_metadata": {
                "http_method": "GET",
                "http_path": "/503"  # Service unavailable
            }
        }
    )

    start_time = asyncio.get_event_loop().time()
    result = await adapter.invoke(request)
    duration = asyncio.get_event_loop().time() - start_time

    print(f"\n  Success: {result.success}")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Error: {result.error}")
    print("\n  Note: With exponential backoff, retries take ~7s total")
    print("  (1s + 2s + 4s between attempts)")


async def example_timeout_handling():
    """Example: Timeout handling."""
    print("\n" + "=" * 60)
    print("Timeout Handling Example")
    print("=" * 60)

    # Create adapter with short timeout
    adapter = HTTPAdapter(
        base_url="https://httpstat.us",
        auth_config={"type": "none"},
        timeout=2.0,  # 2 second timeout
        max_retries=1,  # No retries for cleaner demo
    )

    resource = ResourceSchema(
        id="http:httpstat",
        name="HTTP Status API",
        protocol="http",
        endpoint="https://httpstat.us",
        sensitivity_level="low",
        metadata={},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    print("✓ Adapter created with 2s timeout")
    print("  Making request that sleeps for 5 seconds...")

    request = InvocationRequest(
        capability_id=f"{resource.id}:get_slow",
        principal_id="example-user",
        arguments={},
        context={
            "capability_metadata": {
                "http_method": "GET",
                "http_path": "/200?sleep=5000"  # Sleep 5 seconds
            }
        }
    )

    start_time = asyncio.get_event_loop().time()
    result = await adapter.invoke(request)
    duration = asyncio.get_event_loop().time() - start_time

    print(f"\n  Success: {result.success}")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Error: {result.error}")
    print("\n  Note: Request timed out after 2s as expected")


async def main():
    """Run all advanced feature examples."""
    print("\n" + "=" * 60)
    print("HTTP Adapter - Advanced Features")
    print("=" * 60)

    try:
        await example_rate_limiting()
    except Exception as e:
        print(f"  ⚠ Rate limiting example failed: {e}")

    try:
        await example_circuit_breaker()
    except Exception as e:
        print(f"  ⚠ Circuit breaker example failed: {e}")

    try:
        await example_retry_logic()
    except Exception as e:
        print(f"  ⚠ Retry logic example failed: {e}")

    try:
        await example_timeout_handling()
    except Exception as e:
        print(f"  ⚠ Timeout handling example failed: {e}")

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("1. Rate limiting prevents overwhelming APIs")
    print("2. Circuit breaker provides fail-fast behavior")
    print("3. Automatic retries handle transient failures")
    print("4. Timeouts prevent hanging requests")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
