"""
Basic gRPC Adapter Example.

Demonstrates:
- Service discovery via reflection
- Listing capabilities
- Invoking unary RPC

Version: 2.0.0
Engineer: ENGINEER-3
"""

import asyncio
from datetime import datetime

from sark.adapters.grpc_adapter import GRPCAdapter
from sark.models.base import InvocationRequest


async def main():
    """Run basic gRPC adapter example."""
    print("=== gRPC Adapter Basic Example ===\n")

    # Create adapter
    adapter = GRPCAdapter(default_timeout=10.0)

    # Discovery configuration
    discovery_config = {
        "host": "localhost",
        "port": 50051,
        "use_tls": False,
        "auth": {"type": "none"},
        "timeout_seconds": 10,
    }

    try:
        # 1. Discover services
        print("1. Discovering gRPC services...")
        resources = await adapter.discover_resources(discovery_config)

        if not resources:
            print("   No services found. Is the gRPC server running?")
            return

        print(f"   Found {len(resources)} services:")
        for resource in resources:
            print(f"     - {resource.name}")
        print()

        # 2. List capabilities for first service
        print("2. Listing capabilities...")
        if resources:
            resource = resources[0]
            capabilities = await adapter.get_capabilities(resource)

            print(f"   Service: {resource.name}")
            for cap in capabilities:
                streaming_info = ""
                if cap.input_schema.get("streaming"):
                    streaming_info += " (client streaming)"
                if cap.output_schema.get("streaming"):
                    streaming_info += " (server streaming)"

                print(f"     - {cap.name}{streaming_info}")
        print()

        # 3. Invoke a method (example: GetUser)
        print("3. Invoking GetUser (unary RPC)...")

        # Find GetUser capability
        get_user_cap = None
        for cap in capabilities:
            if cap.name == "GetUser":
                get_user_cap = cap
                break

        if get_user_cap:
            # Create invocation request
            request = InvocationRequest(
                capability_id=get_user_cap.id,
                principal_id="example-user",
                arguments={"user_id": "123"},
                context={"endpoint": resource.endpoint},
            )

            # Validate request
            is_valid = await adapter.validate_request(request)
            print(f"   Request valid: {is_valid}")

            # Invoke
            result = await adapter.invoke(request)

            if result.success:
                print(f"   Success! Response: {result.result}")
                print(f"   Duration: {result.duration_ms:.2f}ms")
            else:
                print(f"   Failed: {result.error}")
        else:
            print("   GetUser method not found")
        print()

        # 4. Health check
        print("4. Health check...")
        is_healthy = await adapter.health_check(resource)
        print(f"   Service health: {'UP ✓' if is_healthy else 'DOWN ✗'}")
        print()

        # 5. Adapter info
        print("5. Adapter information:")
        info = adapter.get_adapter_info()
        for key, value in info.items():
            print(f"   {key}: {value}")

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback

        traceback.print_exc()

    finally:
        # Cleanup
        if resources:
            for resource in resources:
                await adapter.on_resource_unregistered(resource)

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
