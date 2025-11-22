"""Example: OIDC Integration with Google, Azure AD, and Okta.

This example demonstrates how to use the OIDC provider for authentication.
"""

import asyncio
import os

from sark.services.auth.providers.oidc import OIDCProvider


async def google_example():
    """Example: Google OAuth authentication."""
    print("\n=== Google OAuth Example ===")

    # Initialize Google provider
    provider = OIDCProvider(
        client_id=os.getenv("GOOGLE_CLIENT_ID", "your-client-id"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "your-client-secret"),
        provider="google",
    )

    # Step 1: Get authorization URL
    auth_url = await provider.get_authorization_url(
        state="random-state-value",
        redirect_uri="http://localhost:8000/callback",
    )
    print(f"1. Redirect user to: {auth_url}")

    # Step 2: After user authorizes, handle callback
    # (In real app, this would be called from your callback endpoint)
    # tokens = await provider.handle_callback(
    #     code="authorization-code-from-callback",
    #     state="random-state-value",
    #     redirect_uri="http://localhost:8000/callback",
    # )

    # Step 3: Validate token and get user info
    # user_info = await provider.validate_token(tokens["access_token"])
    # print(f"User: {user_info.email}")

    # Check provider health
    is_healthy = await provider.health_check()
    print(f"2. Provider health: {'OK' if is_healthy else 'FAILED'}")


async def azure_ad_example():
    """Example: Azure AD authentication."""
    print("\n=== Azure AD Example ===")

    # Initialize Azure AD provider
    provider = OIDCProvider(
        client_id=os.getenv("AZURE_CLIENT_ID", "your-client-id"),
        client_secret=os.getenv("AZURE_CLIENT_SECRET", "your-client-secret"),
        provider="azure",
        tenant=os.getenv("AZURE_TENANT_ID", "your-tenant-id"),
    )

    # Get authorization URL
    auth_url = await provider.get_authorization_url(
        state="random-state-value",
        redirect_uri="http://localhost:8000/callback",
    )
    print(f"1. Redirect user to: {auth_url[:100]}...")

    # Check provider health
    is_healthy = await provider.health_check()
    print(f"2. Provider health: {'OK' if is_healthy else 'FAILED'}")


async def okta_example():
    """Example: Okta authentication."""
    print("\n=== Okta Example ===")

    # Initialize Okta provider
    provider = OIDCProvider(
        client_id=os.getenv("OKTA_CLIENT_ID", "your-client-id"),
        client_secret=os.getenv("OKTA_CLIENT_SECRET", "your-client-secret"),
        provider="okta",
        domain=os.getenv("OKTA_DOMAIN", "your-domain.okta.com"),
    )

    # Get authorization URL
    auth_url = await provider.get_authorization_url(
        state="random-state-value",
        redirect_uri="http://localhost:8000/callback",
    )
    print(f"1. Redirect user to: {auth_url[:100]}...")

    # Check provider health
    is_healthy = await provider.health_check()
    print(f"2. Provider health: {'OK' if is_healthy else 'FAILED'}")


async def custom_provider_example():
    """Example: Custom OIDC provider."""
    print("\n=== Custom OIDC Provider Example ===")

    # Initialize custom provider
    provider = OIDCProvider(
        client_id="your-client-id",
        client_secret="your-client-secret",
        provider="custom",
        issuer="https://auth.example.com",
        authorization_endpoint="https://auth.example.com/oauth/authorize",
        token_endpoint="https://auth.example.com/oauth/token",
        userinfo_endpoint="https://auth.example.com/oauth/userinfo",
        jwks_uri="https://auth.example.com/oauth/jwks",
        scopes=["openid", "profile", "email", "custom_scope"],
    )

    print(f"1. Custom provider configured with issuer: {provider.issuer}")
    print(f"2. Custom scopes: {provider.scopes}")


async def main():
    """Run all examples."""
    print("SARK OIDC Provider Examples")
    print("=" * 50)

    await google_example()
    await azure_ad_example()
    await okta_example()
    await custom_provider_example()

    print("\n" + "=" * 50)
    print("✓ All examples completed!")
    print("\nTo use in production:")
    print("1. Set environment variables for client credentials")
    print("2. Configure OIDC settings in .env or settings")
    print("3. Implement callback endpoints in your API")
    print("4. Add proper error handling and logging")


if __name__ == "__main__":
    asyncio.run(main())
