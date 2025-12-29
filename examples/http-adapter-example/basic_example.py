"""
Basic HTTP Adapter Example

This example demonstrates basic usage of the HTTP adapter with a public API.

We'll use JSONPlaceholder (https://jsonplaceholder.typicode.com/), a free
fake REST API for testing.

Version: 2.0.0
Engineer: ENGINEER-2
"""

import asyncio
from datetime import datetime

from sark.adapters.http import HTTPAdapter
from sark.models.base import InvocationRequest, ResourceSchema


async def main():
    """Basic HTTP adapter usage example."""

    print("=" * 60)
    print("HTTP Adapter - Basic Example")
    print("=" * 60)

    # Step 1: Create HTTP adapter
    print("\n1. Creating HTTP adapter for JSONPlaceholder API...")
    adapter = HTTPAdapter(
        base_url="https://jsonplaceholder.typicode.com",
        auth_config={"type": "none"},  # Public API, no auth needed
        timeout=10.0,
    )

    print(f"   ✓ Adapter created: {adapter}")
    print(f"   - Protocol: {adapter.protocol_name}")
    print(f"   - Version: {adapter.protocol_version}")

    # Step 2: Discover the resource
    print("\n2. Discovering API resource...")
    try:
        resources = await adapter.discover_resources({
            "base_url": "https://jsonplaceholder.typicode.com",
        })

        if resources:
            resource = resources[0]
            print(f"   ✓ Discovered resource: {resource.name}")
            print(f"   - ID: {resource.id}")
            print(f"   - Protocol: {resource.protocol}")
            print(f"   - Endpoint: {resource.endpoint}")
        else:
            print("   ⚠ No resources discovered (API may not have OpenAPI spec)")
            # Create a manual resource for demonstration
            resource = ResourceSchema(
                id="http:jsonplaceholder",
                name="JSONPlaceholder API",
                protocol="http",
                endpoint="https://jsonplaceholder.typicode.com",
                sensitivity_level="low",
                metadata={
                    "description": "Free fake REST API for testing",
                    "manual_config": True,
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            print(f"   ✓ Created manual resource: {resource.name}")

    except Exception as e:
        print(f"   ⚠ Discovery failed: {e}")
        # Create a manual resource
        resource = ResourceSchema(
            id="http:jsonplaceholder",
            name="JSONPlaceholder API",
            protocol="http",
            endpoint="https://jsonplaceholder.typicode.com",
            sensitivity_level="low",
            metadata={
                "description": "Free fake REST API for testing",
                "manual_config": True,
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        print(f"   ✓ Created manual resource: {resource.name}")

    # Step 3: Health check
    print("\n3. Checking API health...")
    is_healthy = await adapter.health_check(resource)
    print(f"   {'✓' if is_healthy else '✗'} API is {'healthy' if is_healthy else 'unhealthy'}")

    # Step 4: Make a simple request
    print("\n4. Making a simple GET request to /posts/1...")

    # Create a manual invocation request
    # In production, this would use discovered capabilities
    request = InvocationRequest(
        capability_id=f"{resource.id}:get_post",
        principal_id="example-user",
        arguments={
            "id": "1"  # Post ID
        },
        context={
            "capability_metadata": {
                "http_method": "GET",
                "http_path": "/posts/1"
            }
        }
    )

    result = await adapter.invoke(request)

    if result.success:
        print("   ✓ Request successful!")
        print(f"   - Duration: {result.duration_ms:.2f}ms")
        print(f"   - Result: {result.result}")
    else:
        print(f"   ✗ Request failed: {result.error}")

    # Step 5: Make a POST request
    print("\n5. Making a POST request to create a post...")

    create_request = InvocationRequest(
        capability_id=f"{resource.id}:create_post",
        principal_id="example-user",
        arguments={
            "body": {
                "title": "Test Post from SARK",
                "body": "This is a test post created via the HTTP adapter",
                "userId": 1
            }
        },
        context={
            "capability_metadata": {
                "http_method": "POST",
                "http_path": "/posts"
            }
        }
    )

    create_result = await adapter.invoke(create_request)

    if create_result.success:
        print("   ✓ Post created!")
        print(f"   - Duration: {create_result.duration_ms:.2f}ms")
        print(f"   - Created post ID: {create_result.result.get('id')}")
    else:
        print(f"   ✗ Request failed: {create_result.error}")

    # Step 6: Cleanup
    print("\n6. Cleaning up...")
    await adapter.on_resource_unregistered(resource)
    print("   ✓ Adapter cleaned up")

    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
