"""
gRPC Streaming Example.

Demonstrates:
- Server streaming RPC
- Client streaming RPC
- Bidirectional streaming RPC

Version: 2.0.0
Engineer: ENGINEER-3
"""

import asyncio

from sark.adapters.grpc_adapter import GRPCAdapter
from sark.models.base import InvocationRequest


async def server_streaming_example(adapter, resource, capability):
    """Demonstrate server streaming RPC."""
    print("\n=== Server Streaming Example ===")
    print("Requesting stream of events...")

    request = InvocationRequest(
        capability_id=capability.id,
        principal_id="example-user",
        arguments={"topic": "user.created", "limit": 5},
        context={"endpoint": resource.endpoint},
    )

    try:
        count = 0
        async for response in adapter.invoke_streaming(request):
            count += 1
            print(f"  Event {count}: {response}")

        print(f"Received {count} events total")

    except Exception as e:
        print(f"Streaming failed: {str(e)}")


async def client_streaming_example(adapter, resource, capability):
    """Demonstrate client streaming RPC."""
    print("\n=== Client Streaming Example ===")
    print("Sending stream of values to sum...")

    # Prepare requests to stream
    values = [
        {"value": 1},
        {"value": 2},
        {"value": 3},
        {"value": 4},
        {"value": 5},
    ]

    request = InvocationRequest(
        capability_id=capability.id,
        principal_id="example-user",
        arguments={"requests": values},
        context={"endpoint": resource.endpoint},
    )

    try:
        # Client streaming returns single response
        async for response in adapter.invoke_streaming(request):
            print(f"  Sum result: {response}")

    except Exception as e:
        print(f"Streaming failed: {str(e)}")


async def bidirectional_streaming_example(adapter, resource, capability):
    """Demonstrate bidirectional streaming RPC."""
    print("\n=== Bidirectional Streaming Example ===")
    print("Chat conversation (stream in both directions)...")

    messages = [
        {"message": "Hello"},
        {"message": "How are you?"},
        {"message": "Goodbye"},
    ]

    request = InvocationRequest(
        capability_id=capability.id,
        principal_id="example-user",
        arguments={"requests": messages},
        context={"endpoint": resource.endpoint},
    )

    try:
        count = 0
        async for response in adapter.invoke_streaming(request):
            count += 1
            print(f"  Server: {response.get('reply', response)}")

        print(f"Exchanged {count} messages")

    except Exception as e:
        print(f"Streaming failed: {str(e)}")


async def main():
    """Run streaming examples."""
    print("=== gRPC Streaming Examples ===\n")

    adapter = GRPCAdapter()

    discovery_config = {
        "host": "localhost",
        "port": 50051,
        "use_tls": False,
        "auth": {"type": "none"},
    }

    try:
        # Discover services
        print("Discovering services...")
        resources = await adapter.discover_resources(discovery_config)

        if not resources:
            print("No services found. Start the mock server first:")
            print("  python mock_grpc_server.py")
            return

        # Find streaming capabilities
        resource = resources[0]
        capabilities = await adapter.get_capabilities(resource)

        # Look for streaming methods
        server_streaming_cap = None
        client_streaming_cap = None
        bidi_streaming_cap = None

        for cap in capabilities:
            metadata = cap.metadata
            is_server_streaming = cap.output_schema.get("streaming", False)
            is_client_streaming = cap.input_schema.get("streaming", False)

            if is_server_streaming and not is_client_streaming:
                server_streaming_cap = cap
            elif is_client_streaming and not is_server_streaming:
                client_streaming_cap = cap
            elif is_server_streaming and is_client_streaming:
                bidi_streaming_cap = cap

        # Run examples
        if server_streaming_cap:
            await server_streaming_example(adapter, resource, server_streaming_cap)
        else:
            print("\nNo server streaming methods found")

        if client_streaming_cap:
            await client_streaming_example(adapter, resource, client_streaming_cap)
        else:
            print("\nNo client streaming methods found")

        if bidi_streaming_cap:
            await bidirectional_streaming_example(
                adapter, resource, bidi_streaming_cap
            )
        else:
            print("\nNo bidirectional streaming methods found")

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback

        traceback.print_exc()

    finally:
        if resources:
            for resource in resources:
                await adapter.on_resource_unregistered(resource)

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
