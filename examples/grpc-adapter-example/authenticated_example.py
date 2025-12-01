"""
gRPC Authentication Example.

Demonstrates:
- Bearer token authentication
- API key authentication
- Custom metadata injection
- mTLS configuration

Version: 2.0.0
Engineer: ENGINEER-3
"""

import asyncio

from sark.adapters.grpc_adapter import GRPCAdapter
from sark.adapters.grpc.auth import (
    AuthenticationHelper,
    create_authenticated_channel,
)


async def bearer_token_example():
    """Demonstrate Bearer token authentication."""
    print("\n=== Bearer Token Authentication ===")

    adapter = GRPCAdapter()

    # Discovery with Bearer token
    discovery_config = {
        "host": "localhost",
        "port": 50051,
        "use_tls": False,  # Set True for production
        "auth": {
            "type": "bearer",
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.example.token",
        },
    }

    print("Discovering services with Bearer token authentication...")

    try:
        resources = await adapter.discover_resources(discovery_config)
        print(f"  Found {len(resources)} services")

        # The token is automatically included in all gRPC calls
        # as "Authorization: Bearer <token>"

    except Exception as e:
        print(f"  Error: {str(e)}")


async def api_key_example():
    """Demonstrate API key authentication."""
    print("\n=== API Key Authentication ===")

    adapter = GRPCAdapter()

    # Discovery with API key
    discovery_config = {
        "host": "localhost",
        "port": 50051,
        "use_tls": False,
        "auth": {
            "type": "apikey",
            "token": "sk-1234567890abcdef",
            "header_name": "x-api-key",  # Custom header name
        },
    }

    print("Discovering services with API key authentication...")

    try:
        resources = await adapter.discover_resources(discovery_config)
        print(f"  Found {len(resources)} services")

        # The API key is automatically included as
        # "x-api-key: sk-1234567890abcdef"

    except Exception as e:
        print(f"  Error: {str(e)}")


async def custom_metadata_example():
    """Demonstrate custom metadata injection."""
    print("\n=== Custom Metadata Injection ===")

    adapter = GRPCAdapter()

    # Discovery with custom metadata
    discovery_config = {
        "host": "localhost",
        "port": 50051,
        "use_tls": False,
        "auth": {
            "type": "bearer",
            "token": "my-token",
            "metadata": {
                # Custom headers added to all requests
                "x-client-id": "client-123",
                "x-api-version": "v1",
                "x-request-id": "req-456",
                "x-tenant-id": "tenant-789",
            },
        },
    }

    print("Discovering services with custom metadata...")

    try:
        resources = await adapter.discover_resources(discovery_config)
        print(f"  Found {len(resources)} services")
        print("  Custom metadata included in all requests:")
        for key, value in discovery_config["auth"]["metadata"].items():
            print(f"    {key}: {value}")

    except Exception as e:
        print(f"  Error: {str(e)}")


async def mtls_example():
    """Demonstrate mTLS configuration."""
    print("\n=== mTLS Authentication ===")

    adapter = GRPCAdapter()

    # Discovery with mTLS
    discovery_config = {
        "host": "secure.example.com",
        "port": 443,
        "use_tls": True,  # Required for mTLS
        "auth": {
            "type": "mtls",
            "cert_path": "/path/to/client-cert.pem",
            "key_path": "/path/to/client-key.pem",
            "ca_path": "/path/to/ca-cert.pem",
        },
    }

    print("Configuration for mTLS:")
    print(f"  Server: {discovery_config['host']}:{discovery_config['port']}")
    print(f"  Client cert: {discovery_config['auth']['cert_path']}")
    print(f"  Client key: {discovery_config['auth']['key_path']}")
    print(f"  CA cert: {discovery_config['auth']['ca_path']}")

    # Note: This will fail without actual certificates
    print("\n  (Skipping actual connection - requires valid certificates)")

    # In production, this would be:
    # resources = await adapter.discover_resources(discovery_config)


async def direct_channel_creation_example():
    """Demonstrate direct authenticated channel creation."""
    print("\n=== Direct Channel Creation ===")

    # Create channel with bearer token
    print("Creating authenticated channel directly...")

    auth_config = {
        "type": "bearer",
        "token": "my-bearer-token",
        "metadata": {
            "x-client-id": "direct-client",
        },
    }

    channel = create_authenticated_channel(
        endpoint="localhost:50051",
        auth_config=auth_config,
        use_tls=False,
    )

    print("  Channel created with authentication")
    print(f"  Auth type: {auth_config['type']}")

    # Use this channel for manual gRPC calls
    # Or pass to reflection client, stream handler, etc.

    await channel.close()
    print("  Channel closed")


async def interceptor_example():
    """Demonstrate using interceptors directly."""
    print("\n=== Using Interceptors Directly ===")

    import grpc

    # Create base channel
    base_channel = grpc.aio.insecure_channel("localhost:50051")

    # Create interceptors
    bearer_interceptor = AuthenticationHelper.create_bearer_token_interceptor(
        "my-token"
    )

    api_key_interceptor = AuthenticationHelper.create_api_key_interceptor(
        "api-key-123", header_name="x-api-key"
    )

    # Apply interceptors
    channel = AuthenticationHelper.apply_interceptors(
        base_channel, [bearer_interceptor, api_key_interceptor]
    )

    print("  Created channel with multiple interceptors")
    print("    - Bearer token interceptor")
    print("    - API key interceptor")

    await channel.close()
    print("  Channel closed")


async def main():
    """Run authentication examples."""
    print("=== gRPC Authentication Examples ===")

    # Run examples
    await bearer_token_example()
    await api_key_example()
    await custom_metadata_example()
    await mtls_example()
    await direct_channel_creation_example()
    await interceptor_example()

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
