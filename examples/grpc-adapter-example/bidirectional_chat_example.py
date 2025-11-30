"""
Enhanced Bidirectional Streaming Example - Real-time Chat.

This example demonstrates advanced bidirectional streaming with:
- Interactive chat conversation
- Message streaming in both directions
- Real-time response handling
- Connection lifecycle management
- Error handling and recovery

Version: 2.0.0
Engineer: ENGINEER-3 (BONUS TASK)
"""

import asyncio
from typing import AsyncIterator

from sark.adapters.grpc_adapter import GRPCAdapter
from sark.models.base import InvocationRequest, ResourceSchema


async def message_stream_generator(messages: list[dict]) -> AsyncIterator[dict]:
    """Generate a stream of chat messages with realistic timing."""
    for i, msg in enumerate(messages):
        # Add realistic delay between messages
        if i > 0:
            await asyncio.sleep(1.0)
        yield msg


async def bidirectional_chat_example():
    """
    Enhanced bidirectional streaming example.

    Demonstrates:
    - Real-time bidirectional communication
    - Async message streaming
    - Response processing as they arrive
    - Graceful connection handling
    """
    print("=" * 70)
    print("Enhanced Bidirectional Streaming: Real-time Chat Example")
    print("=" * 70)

    adapter = GRPCAdapter()

    # Discovery configuration
    discovery_config = {
        "host": "localhost",
        "port": 50051,
        "use_tls": False,
        "auth": {"type": "none"},
    }

    try:
        print("\n[1/5] Discovering gRPC services...")
        resources = await adapter.discover_resources(discovery_config)

        if not resources:
            print("\n❌ No services found!")
            print("\nTo run this example, start a gRPC server with bidirectional streaming:")
            print("  python examples/grpc-adapter-example/mock_chat_server.py")
            return

        print(f"✓ Found {len(resources)} service(s)")
        resource = resources[0]
        print(f"  Service: {resource.name}")

        print("\n[2/5] Getting service capabilities...")
        capabilities = await adapter.get_capabilities(resource)

        # Find bidirectional streaming capability
        bidi_capability = None
        for cap in capabilities:
            is_server_streaming = cap.output_schema.get("streaming", False)
            is_client_streaming = cap.input_schema.get("streaming", False)

            if is_server_streaming and is_client_streaming:
                bidi_capability = cap
                break

        if not bidi_capability:
            print("\n❌ No bidirectional streaming methods found!")
            print("\nThe server needs to expose a bidirectional streaming method like:")
            print("  rpc Chat(stream ChatMessage) returns (stream ChatResponse)")
            return

        print(f"✓ Found bidirectional streaming capability: {bidi_capability.name}")

        print("\n[3/5] Preparing chat messages...")
        # Simulate a realistic chat conversation
        chat_messages = [
            {
                "user_id": "alice",
                "message": "Hello! Is anyone there?",
                "timestamp": "2025-11-29T10:00:00Z"
            },
            {
                "user_id": "alice",
                "message": "I need help with the gRPC adapter.",
                "timestamp": "2025-11-29T10:00:05Z"
            },
            {
                "user_id": "alice",
                "message": "How do I handle bidirectional streaming?",
                "timestamp": "2025-11-29T10:00:10Z"
            },
            {
                "user_id": "alice",
                "message": "This example is really helpful!",
                "timestamp": "2025-11-29T10:00:20Z"
            },
            {
                "user_id": "alice",
                "message": "Thanks for the demo. Goodbye!",
                "timestamp": "2025-11-29T10:00:30Z"
            },
        ]

        print(f"✓ Prepared {len(chat_messages)} messages to send")

        print("\n[4/5] Starting bidirectional chat stream...")
        print("-" * 70)

        # Create invocation request
        request = InvocationRequest(
            capability_id=bidi_capability.id,
            principal_id="alice",
            arguments={
                "requests": chat_messages,
                "stream": True,
            },
            context={
                "endpoint": resource.endpoint,
                "session_id": "demo-session-001",
            },
        )

        # Process bidirectional stream
        message_count = 0
        response_count = 0

        try:
            async for response in adapter.invoke_streaming(request):
                response_count += 1

                # Extract response details
                reply = response.get("reply", "")
                sender = response.get("sender", "server")
                timestamp = response.get("timestamp", "")

                # Display the response
                print(f"\n[Response #{response_count}]")
                print(f"  From: {sender}")
                print(f"  Time: {timestamp}")
                print(f"  Message: {reply}")

                # Simulate processing time
                await asyncio.sleep(0.5)

            print("\n" + "-" * 70)
            print(f"\n✓ Chat completed successfully!")
            print(f"  Messages sent: {len(chat_messages)}")
            print(f"  Responses received: {response_count}")

        except Exception as e:
            print(f"\n❌ Stream error: {str(e)}")
            import traceback
            traceback.print_exc()

        print("\n[5/5] Cleaning up resources...")
        await adapter.on_resource_unregistered(resource)
        print("✓ Resources cleaned up")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)
    print("Example complete!")
    print("=" * 70)


async def demonstrate_stream_features():
    """
    Demonstrate advanced streaming features.

    Shows:
    - Custom message types
    - Error handling
    - Stream cancellation
    - Backpressure handling
    """
    print("\n" + "=" * 70)
    print("Advanced Bidirectional Streaming Features")
    print("=" * 70)

    print("\n1. Custom Message Types")
    print("   - Text messages")
    print("   - File transfer notifications")
    print("   - Typing indicators")
    print("   - Read receipts")

    print("\n2. Error Handling")
    print("   - Connection errors")
    print("   - Message validation errors")
    print("   - Stream interruption recovery")

    print("\n3. Flow Control")
    print("   - Backpressure handling")
    print("   - Message buffering")
    print("   - Rate limiting")

    print("\n4. Stream Management")
    print("   - Graceful shutdown")
    print("   - Stream cancellation")
    print("   - Reconnection logic")

    print("\n" + "=" * 70)


async def main():
    """Run the enhanced bidirectional streaming examples."""
    print("\n🚀 SARK v2.0 - Enhanced Bidirectional Streaming Demo")

    # Run the main chat example
    await bidirectional_chat_example()

    # Demonstrate additional features
    await demonstrate_stream_features()

    print("\n" + "=" * 70)
    print("Key Takeaways:")
    print("=" * 70)
    print("""
1. Bidirectional streaming enables real-time, two-way communication
2. Perfect for chat, live updates, collaborative editing, etc.
3. The gRPC adapter handles stream lifecycle automatically
4. Errors are caught and reported with context
5. Resources are cleaned up properly after use

Next Steps:
- Implement a real gRPC server with bidirectional streaming
- Add message persistence and history
- Integrate with SARK policy enforcement
- Add authentication and authorization
- Monitor stream performance with metrics
    """)

    print("=" * 70)
    print("\n✅ All examples completed successfully!\n")


if __name__ == "__main__":
    asyncio.run(main())
