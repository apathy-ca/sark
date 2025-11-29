"""
HTTP Adapter Authentication Examples

This example demonstrates different authentication strategies supported
by the HTTP adapter.

Version: 2.0.0
Engineer: ENGINEER-2
"""

import asyncio

from sark.adapters.http import HTTPAdapter
from sark.adapters.http.authentication import (
    NoAuthStrategy,
    BasicAuthStrategy,
    BearerAuthStrategy,
    OAuth2Strategy,
    APIKeyStrategy,
)


async def example_no_auth():
    """Example: No authentication (public APIs)."""
    print("\n" + "=" * 60)
    print("No Authentication Example")
    print("=" * 60)

    adapter = HTTPAdapter(
        base_url="https://api.publicapis.org",
        auth_config={"type": "none"}
    )

    print("✓ Adapter created with no authentication")
    print(f"  Auth strategy: {type(adapter.auth_strategy).__name__}")


async def example_basic_auth():
    """Example: HTTP Basic Authentication."""
    print("\n" + "=" * 60)
    print("Basic Authentication Example")
    print("=" * 60)

    adapter = HTTPAdapter(
        base_url="https://httpbin.org",
        auth_config={
            "type": "basic",
            "username": "testuser",
            "password": "testpass"
        }
    )

    print("✓ Adapter created with Basic Auth")
    print(f"  Auth strategy: {type(adapter.auth_strategy).__name__}")
    print(f"  Username: testuser")


async def example_bearer_token():
    """Example: Bearer Token Authentication."""
    print("\n" + "=" * 60)
    print("Bearer Token Example")
    print("=" * 60)

    adapter = HTTPAdapter(
        base_url="https://api.github.com",
        auth_config={
            "type": "bearer",
            "token": "ghp_exampletoken123456789"
        }
    )

    print("✓ Adapter created with Bearer Token")
    print(f"  Auth strategy: {type(adapter.auth_strategy).__name__}")
    print(f"  Token: ghp_example... (truncated)")


async def example_oauth2():
    """Example: OAuth2 Client Credentials."""
    print("\n" + "=" * 60)
    print("OAuth2 Client Credentials Example")
    print("=" * 60)

    adapter = HTTPAdapter(
        base_url="https://api.example.com",
        auth_config={
            "type": "oauth2",
            "token_url": "https://auth.example.com/oauth/token",
            "client_id": "your-client-id",
            "client_secret": "your-client-secret",
            "grant_type": "client_credentials",
            "scope": "read write"
        }
    )

    print("✓ Adapter created with OAuth2")
    print(f"  Auth strategy: {type(adapter.auth_strategy).__name__}")
    print(f"  Grant type: client_credentials")
    print(f"  Token URL: https://auth.example.com/oauth/token")

    # Note: In production, you would call:
    # await adapter.auth_strategy.refresh()
    # to obtain the access token before making requests


async def example_api_key_header():
    """Example: API Key in Header."""
    print("\n" + "=" * 60)
    print("API Key (Header) Example")
    print("=" * 60)

    adapter = HTTPAdapter(
        base_url="https://api.example.com",
        auth_config={
            "type": "api_key",
            "api_key": "sk-1234567890abcdef",
            "location": "header",
            "key_name": "X-API-Key"
        }
    )

    print("✓ Adapter created with API Key")
    print(f"  Auth strategy: {type(adapter.auth_strategy).__name__}")
    print(f"  Location: header")
    print(f"  Key name: X-API-Key")


async def example_api_key_query():
    """Example: API Key in Query Parameter."""
    print("\n" + "=" * 60)
    print("API Key (Query Parameter) Example")
    print("=" * 60)

    adapter = HTTPAdapter(
        base_url="https://api.example.com",
        auth_config={
            "type": "api_key",
            "api_key": "abc123xyz",
            "location": "query",
            "key_name": "api_key"
        }
    )

    print("✓ Adapter created with API Key (query)")
    print(f"  Auth strategy: {type(adapter.auth_strategy).__name__}")
    print(f"  Location: query parameter")
    print(f"  Key name: api_key")


async def example_custom_headers():
    """Example: Custom headers with Bearer token."""
    print("\n" + "=" * 60)
    print("Custom Headers Example")
    print("=" * 60)

    # For APIs that need custom headers beyond authentication
    # You can combine auth with custom headers in invocation requests

    adapter = HTTPAdapter(
        base_url="https://api.example.com",
        auth_config={
            "type": "bearer",
            "token": "your-access-token"
        }
    )

    print("✓ Adapter created")
    print("  Note: Add custom headers via InvocationRequest arguments:")
    print("  arguments = {")
    print("    'header_X-Custom-Header': 'value',")
    print("    'header_X-Request-ID': 'req-123',")
    print("    ...")
    print("  }")


async def main():
    """Run all authentication examples."""
    print("\n" + "=" * 60)
    print("HTTP Adapter - Authentication Examples")
    print("=" * 60)
    print("\nThis example shows different authentication strategies")
    print("supported by the HTTP adapter.")

    await example_no_auth()
    await example_basic_auth()
    await example_bearer_token()
    await example_oauth2()
    await example_api_key_header()
    await example_api_key_query()
    await example_custom_headers()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("1. HTTP adapter supports multiple auth strategies")
    print("2. Auth is configured via auth_config parameter")
    print("3. Strategies handle token refresh automatically")
    print("4. Custom headers can be added per request")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
