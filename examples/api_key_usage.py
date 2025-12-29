#!/usr/bin/env python3
"""
API Key Usage Example for SARK

This example demonstrates:
- Creating API keys with scoped permissions
- Using API keys for authentication
- Rotating API keys
- Managing API key lifecycle

Usage:
    python api_key_usage.py
"""

import os
from typing import Optional

import requests


class SARKAPIKeyManager:
    """Manage SARK API keys."""

    def __init__(self, base_url: str, access_token: str):
        """Initialize API key manager.

        Args:
            base_url: SARK API base URL
            access_token: JWT access token for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    def create_api_key(
        self,
        name: str,
        scopes: list[str],
        description: Optional[str] = None,
        rate_limit: int = 1000,
        expires_in_days: Optional[int] = 90,
        environment: str = "live",
    ) -> dict:
        """Create a new API key.

        Args:
            name: Human-readable key name
            scopes: List of permission scopes
            description: Optional description
            rate_limit: Requests per minute (1-10000)
            expires_in_days: Expiration in days (None for no expiration)
            environment: Environment (live, test, dev)

        Returns:
            API key creation response with full key
        """
        print(f"\nCreating API key: {name}")
        print(f"  Scopes: {', '.join(scopes)}")
        print(f"  Rate limit: {rate_limit} req/min")
        print(f"  Expires in: {expires_in_days} days")

        payload = {
            "name": name,
            "scopes": scopes,
            "description": description,
            "rate_limit": rate_limit,
            "expires_in_days": expires_in_days,
            "environment": environment,
        }

        response = requests.post(f"{self.base_url}/api/auth/api-keys", headers=self.headers, json=payload)

        response.raise_for_status()
        data = response.json()

        print("✓ API key created successfully")
        print(f"  ID: {data['api_key']['id']}")
        print(f"  Prefix: {data['api_key']['key_prefix']}")
        print(f"  Full key: {data['key']}")
        print("\n⚠️  Save this key securely - it won't be shown again!")

        return data

    def list_api_keys(self, include_revoked: bool = False) -> list[dict]:
        """List API keys.

        Args:
            include_revoked: Include revoked keys

        Returns:
            List of API keys
        """
        print(f"\nListing API keys (include_revoked={include_revoked})")

        params = {"include_revoked": include_revoked}
        response = requests.get(f"{self.base_url}/api/auth/api-keys", headers=self.headers, params=params)

        response.raise_for_status()
        keys = response.json()

        print(f"✓ Found {len(keys)} API keys")
        for key in keys:
            status = "✗ revoked" if key.get("revoked_at") else ("✓ active" if key["is_active"] else "⏸ inactive")
            print(f"  [{status}] {key['name']} ({key['key_prefix']}***)")
            print(f"      Scopes: {', '.join(key['scopes'])}")
            print(f"      Usage: {key['usage_count']} requests")
            if key.get("last_used_at"):
                print(f"      Last used: {key['last_used_at']}")

        return keys

    def get_api_key(self, key_id: str) -> dict:
        """Get API key details.

        Args:
            key_id: API key ID

        Returns:
            API key details
        """
        print(f"\nFetching API key: {key_id}")

        response = requests.get(f"{self.base_url}/api/auth/api-keys/{key_id}", headers=self.headers)

        response.raise_for_status()
        key = response.json()

        print("✓ API key details:")
        print(f"  Name: {key['name']}")
        print(f"  Prefix: {key['key_prefix']}")
        print(f"  Scopes: {', '.join(key['scopes'])}")
        print(f"  Rate limit: {key['rate_limit']} req/min")
        print(f"  Active: {key['is_active']}")

        return key

    def update_api_key(
        self, key_id: str, name: Optional[str] = None, scopes: Optional[list[str]] = None, rate_limit: Optional[int] = None, is_active: Optional[bool] = None
    ) -> dict:
        """Update API key metadata.

        Args:
            key_id: API key ID
            name: New name
            scopes: New scopes
            rate_limit: New rate limit
            is_active: Active status

        Returns:
            Updated API key
        """
        print(f"\nUpdating API key: {key_id}")

        payload = {}
        if name is not None:
            payload["name"] = name
            print(f"  Setting name: {name}")
        if scopes is not None:
            payload["scopes"] = scopes
            print(f"  Setting scopes: {', '.join(scopes)}")
        if rate_limit is not None:
            payload["rate_limit"] = rate_limit
            print(f"  Setting rate limit: {rate_limit}")
        if is_active is not None:
            payload["is_active"] = is_active
            print(f"  Setting active: {is_active}")

        response = requests.patch(f"{self.base_url}/api/auth/api-keys/{key_id}", headers=self.headers, json=payload)

        response.raise_for_status()
        key = response.json()

        print("✓ API key updated successfully")
        return key

    def rotate_api_key(self, key_id: str, environment: str = "live") -> dict:
        """Rotate API key (generate new credentials).

        Args:
            key_id: API key ID
            environment: Environment

        Returns:
            Rotated API key with new full key
        """
        print(f"\nRotating API key: {key_id}")

        params = {"environment": environment}
        response = requests.post(f"{self.base_url}/api/auth/api-keys/{key_id}/rotate", headers=self.headers, params=params)

        response.raise_for_status()
        data = response.json()

        print("✓ API key rotated successfully")
        print(f"  New prefix: {data['api_key']['key_prefix']}")
        print(f"  New full key: {data['key']}")
        print("\n⚠️  Update your applications with the new key!")

        return data

    def revoke_api_key(self, key_id: str) -> None:
        """Revoke API key.

        Args:
            key_id: API key ID
        """
        print(f"\nRevoking API key: {key_id}")

        response = requests.delete(f"{self.base_url}/api/auth/api-keys/{key_id}", headers=self.headers)

        response.raise_for_status()
        print("✓ API key revoked successfully")


def use_api_key_for_requests(base_url: str, api_key: str):
    """Demonstrate using API key for authenticated requests.

    Args:
        base_url: SARK API base URL
        api_key: Full API key
    """
    print("\n" + "=" * 60)
    print("Using API Key for Authenticated Requests")
    print("=" * 60)

    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}

    # Example 1: List servers
    print("\n1. Listing servers with API key...")
    response = requests.get(f"{base_url}/api/v1/servers", headers=headers, params={"limit": 5})

    if response.status_code == 200:
        servers = response.json()
        print(f"✓ Found {len(servers.get('items', []))} servers")
        for server in servers.get("items", []):
            print(f"  - {server['name']} ({server['status']})")
    else:
        print(f"✗ Request failed: {response.status_code}")

    # Example 2: Register server
    print("\n2. Registering server with API key...")
    server_data = {
        "name": "example-server-1",
        "transport": "http",
        "endpoint": "http://example.com:8080",
        "capabilities": ["tools"],
        "tools": [],
        "sensitivity_level": "medium",
    }

    response = requests.post(f"{base_url}/api/v1/servers", headers=headers, json=server_data)

    if response.status_code == 201:
        result = response.json()
        print(f"✓ Server registered: {result['server_id']}")
    elif response.status_code == 403:
        print("✗ Permission denied - API key lacks 'server:write' scope")
    else:
        print(f"✗ Request failed: {response.status_code}")


def example_api_key_lifecycle():
    """Complete API key lifecycle example."""
    print("\n" + "=" * 60)
    print("API Key Lifecycle Example")
    print("=" * 60)

    # Configuration
    base_url = os.getenv("SARK_API_URL", "https://sark.example.com")
    access_token = os.getenv("SARK_ACCESS_TOKEN", "your-jwt-token")

    print(f"\nBase URL: {base_url}")
    print(f"Access Token: {access_token[:20]}...")

    # Initialize manager
    manager = SARKAPIKeyManager(base_url, access_token)

    try:
        # Step 1: Create API key
        print("\n" + "-" * 60)
        print("Step 1: Create API Key")
        print("-" * 60)

        key_data = manager.create_api_key(
            name="CI/CD Pipeline Key",
            description="API key for automated deployments",
            scopes=["server:read", "server:write"],
            rate_limit=500,
            expires_in_days=90,
        )

        key_id = key_data["api_key"]["id"]
        key_data["key"]

        # Step 2: List all keys
        print("\n" + "-" * 60)
        print("Step 2: List API Keys")
        print("-" * 60)

        manager.list_api_keys()

        # Step 3: Get specific key
        print("\n" + "-" * 60)
        print("Step 3: Get API Key Details")
        print("-" * 60)

        manager.get_api_key(key_id)

        # Step 4: Use the key
        print("\n" + "-" * 60)
        print("Step 4: Use API Key")
        print("-" * 60)

        # use_api_key_for_requests(base_url, full_key)
        print("(Skipped in example - uncomment to test)")

        # Step 5: Update key metadata
        print("\n" + "-" * 60)
        print("Step 5: Update API Key")
        print("-" * 60)

        manager.update_api_key(key_id, rate_limit=1000, is_active=True)

        # Step 6: Rotate key
        print("\n" + "-" * 60)
        print("Step 6: Rotate API Key")
        print("-" * 60)

        # rotated_data = manager.rotate_api_key(key_id)
        # new_key = rotated_data['key']
        print("(Skipped in example - uncomment to test)")

        # Step 7: Revoke key
        print("\n" + "-" * 60)
        print("Step 7: Revoke API Key")
        print("-" * 60)

        # manager.revoke_api_key(key_id)
        print("(Skipped in example - uncomment to test)")

    except requests.exceptions.RequestException as e:
        print(f"\n✗ API request failed: {e}")


def example_scoped_keys():
    """Example of creating keys with different scopes."""
    print("\n" + "=" * 60)
    print("Scoped API Keys Example")
    print("=" * 60)

    print("""
# Different API keys for different purposes

# 1. Read-only key for monitoring
manager.create_api_key(
    name="Monitoring Dashboard",
    scopes=["server:read", "audit:read"],
    rate_limit=2000,
    expires_in_days=None  # No expiration
)

# 2. Full access key for admins
manager.create_api_key(
    name="Admin Automation",
    scopes=["admin"],  # Full admin access
    rate_limit=500,
    expires_in_days=30
)

# 3. Limited key for CI/CD
manager.create_api_key(
    name="CI/CD Pipeline",
    scopes=["server:read", "server:write"],
    rate_limit=100,
    expires_in_days=90
)

# 4. Policy management key
manager.create_api_key(
    name="Policy Updates",
    scopes=["policy:read", "policy:write"],
    rate_limit=50,
    expires_in_days=180
)
    """)


def example_rate_limiting():
    """Example demonstrating rate limiting."""
    print("\n" + "=" * 60)
    print("Rate Limiting Example")
    print("=" * 60)

    print("""
# API keys have configurable rate limits

import time
import requests

base_url = "https://sark.example.com"
api_key = "sark_live_abc123..."
headers = {"X-API-Key": api_key}

# Make rapid requests to hit rate limit
for i in range(150):
    response = requests.get(f"{base_url}/api/v1/servers", headers=headers)

    if response.status_code == 429:
        # Rate limit exceeded
        print(f"Rate limit exceeded on request {i}")

        # Check retry-after header
        retry_after = response.headers.get('Retry-After', 60)
        print(f"Retry after: {retry_after} seconds")

        # Implement exponential backoff
        time.sleep(int(retry_after))

    elif response.status_code == 200:
        # Check rate limit headers
        limit = response.headers.get('X-RateLimit-Limit')
        remaining = response.headers.get('X-RateLimit-Remaining')
        reset = response.headers.get('X-RateLimit-Reset')

        print(f"Request {i}: {remaining}/{limit} remaining, resets at {reset}")

    # Add small delay between requests
    time.sleep(0.01)
    """)


def main():
    """Run all examples."""
    print("=" * 60)
    print("SARK API Key Usage Examples")
    print("=" * 60)

    print("\nNote: Set environment variables:")
    print("  export SARK_API_URL=https://sark.example.com")
    print("  export SARK_ACCESS_TOKEN=your-jwt-access-token")

    # Example 1: API key lifecycle
    # example_api_key_lifecycle()

    # Example 2: Scoped keys
    example_scoped_keys()

    # Example 3: Rate limiting
    example_rate_limiting()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)

    print("\nTo run the lifecycle example, uncomment the call in main()")


if __name__ == "__main__":
    main()
