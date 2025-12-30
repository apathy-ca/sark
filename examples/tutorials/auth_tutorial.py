#!/usr/bin/env python3
"""
SARK Authentication Tutorial - Python Client Example

This script demonstrates all authentication methods supported by SARK:
- API Keys
- LDAP
- OIDC
- JWT Token Management

Usage:
    python auth_tutorial.py --method api-key
    python auth_tutorial.py --method ldap --username john.doe --password secret
    python auth_tutorial.py --method oidc
"""

import argparse
from datetime import datetime, timedelta
import sys
from typing import Optional

import requests
from requests.exceptions import RequestException


class SARKAuthClient:
    """SARK Authentication Client with automatic token refresh."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self.api_key: Optional[str] = None

    # ============================================
    # API Key Authentication
    # ============================================

    def create_api_key(
        self,
        admin_token: str,
        name: str,
        scopes: list[str],
        expires_in_days: int = 30,
    ) -> dict:
        """
        Create a new API key.

        Args:
            admin_token: Admin JWT token for bootstrapping
            name: Descriptive name for the API key
            scopes: List of permission scopes
            expires_in_days: Expiration period

        Returns:
            Dictionary with API key details and the key itself
        """
        url = f"{self.base_url}/api/auth/api-keys"
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "name": name,
            "description": "Created via tutorial script",
            "scopes": scopes,
            "expires_in_days": expires_in_days,
            "environment": "development",
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Save the API key
            self.api_key = data["key"]
            print("✅ API Key created successfully!")
            print(f"   Name: {data['api_key']['name']}")
            print(f"   Prefix: {data['api_key']['key_prefix']}")
            print(f"   Scopes: {', '.join(data['api_key']['scopes'])}")
            print(f"   Expires: {data['api_key']['expires_at']}")
            print(f"\n⚠️  SAVE THIS KEY: {data['key']}")
            print("   It will not be shown again!")

            return data

        except RequestException as e:
            print(f"❌ Failed to create API key: {e}")
            if hasattr(e.response, "text"):
                print(f"   Response: {e.response.text}")
            sys.exit(1)

    def set_api_key(self, api_key: str):
        """Set API key for authentication."""
        self.api_key = api_key
        print(f"✅ API key configured (prefix: {api_key[:16]}...)")

    # ============================================
    # LDAP Authentication
    # ============================================

    def login_ldap(self, username: str, password: str) -> dict:
        """
        Authenticate using LDAP credentials.

        Args:
            username: LDAP username
            password: LDAP password

        Returns:
            Dictionary with access token, refresh token, and user info
        """
        url = f"{self.base_url}/api/v1/auth/login"
        payload = {
            "provider": "ldap",
            "username": username,
            "password": password,
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data["success"]:
                session = data["session"]
                self.access_token = session["access_token"]
                self.refresh_token = session["refresh_token"]
                self.token_expires_at = datetime.now() + timedelta(
                    seconds=session["expires_in"]
                )

                print("✅ LDAP login successful!")
                print(f"   User ID: {data['user_id']}")
                print(f"   Token expires in: {session['expires_in']} seconds")
                return data
            else:
                print(f"❌ Login failed: {data['message']}")
                sys.exit(1)

        except RequestException as e:
            print(f"❌ LDAP authentication failed: {e}")
            if hasattr(e.response, "text"):
                print(f"   Response: {e.response.text}")
            sys.exit(1)

    # ============================================
    # OIDC Authentication
    # ============================================

    def get_oidc_login_url(self) -> str:
        """
        Get OIDC login URL to initiate authentication flow.

        Returns:
            OIDC authorization URL
        """
        url = f"{self.base_url}/api/v1/auth/oidc/login"
        print(f"🔗 OIDC Login URL: {url}")
        print("\n📋 Instructions:")
        print("1. Open this URL in your browser")
        print("2. Log in with your OIDC provider")
        print("3. After successful login, copy the callback URL")
        print("4. Extract the tokens from the callback response")
        return url

    def handle_oidc_callback(self, code: str, state: str) -> dict:
        """
        Handle OIDC callback with authorization code.

        Args:
            code: Authorization code from OIDC provider
            state: State parameter for CSRF protection

        Returns:
            Dictionary with tokens and user info
        """
        url = f"{self.base_url}/api/v1/auth/oidc/callback"
        params = {"code": code, "state": state}

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            self.access_token = data["access_token"]
            self.refresh_token = data["refresh_token"]
            self.token_expires_at = datetime.now() + timedelta(
                seconds=data["expires_in"]
            )

            print("✅ OIDC authentication successful!")
            print(f"   User: {data['user']['name']} ({data['user']['email']})")
            return data

        except RequestException as e:
            print(f"❌ OIDC callback failed: {e}")
            sys.exit(1)

    # ============================================
    # Token Management
    # ============================================

    def refresh_access_token(self) -> dict:
        """
        Refresh the access token using the refresh token.

        Returns:
            Dictionary with new tokens
        """
        if not self.refresh_token:
            raise ValueError("No refresh token available")

        url = f"{self.base_url}/api/v1/auth/refresh"
        payload = {"refresh_token": self.refresh_token}

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            self.access_token = data["access_token"]
            self.token_expires_at = datetime.now() + timedelta(
                seconds=data["expires_in"]
            )

            # Handle token rotation
            if "refresh_token" in data:
                self.refresh_token = data["refresh_token"]
                print("🔄 Refresh token rotated")

            print("✅ Access token refreshed")
            print(f"   Expires in: {data['expires_in']} seconds")
            return data

        except RequestException as e:
            print(f"❌ Token refresh failed: {e}")
            if hasattr(e.response, "text"):
                print(f"   Response: {e.response.text}")
            raise

    def ensure_fresh_token(self):
        """Ensure access token is fresh, refresh if needed."""
        if not self.access_token or not self.token_expires_at:
            return

        # Refresh if token expires in < 5 minutes
        if datetime.now() >= self.token_expires_at - timedelta(minutes=5):
            print("⏰ Token expiring soon, refreshing...")
            self.refresh_access_token()

    def logout(self):
        """Revoke the refresh token (logout)."""
        if not self.access_token or not self.refresh_token:
            print("⚠️  Not logged in")
            return

        url = f"{self.base_url}/api/v1/auth/revoke"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        payload = {"refresh_token": self.refresh_token}

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            self.access_token = None
            self.refresh_token = None
            self.token_expires_at = None

            print(f"✅ {data['message']}")

        except RequestException as e:
            print(f"❌ Logout failed: {e}")

    # ============================================
    # API Requests
    # ============================================

    def get_current_user(self) -> dict:
        """Get current authenticated user information."""
        self.ensure_fresh_token()

        url = f"{self.base_url}/api/v1/auth/me"
        headers = self._get_auth_headers()

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            print("👤 Current User:")
            print(f"   User ID: {data['user_id']}")
            print(f"   Username: {data.get('username', 'N/A')}")
            print(f"   Email: {data.get('email', 'N/A')}")
            print(f"   Role: {data.get('role', 'N/A')}")
            print(f"   Teams: {', '.join(data.get('teams', []))}")
            print(f"   Permissions: {', '.join(data.get('permissions', []))}")

            return data

        except RequestException as e:
            print(f"❌ Failed to get user info: {e}")
            if hasattr(e.response, "text"):
                print(f"   Response: {e.response.text}")
            raise

    def list_servers(self) -> dict:
        """List all registered MCP servers."""
        self.ensure_fresh_token()

        url = f"{self.base_url}/api/v1/servers"
        headers = self._get_auth_headers()

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            print(f"📋 Registered Servers: {len(data['items'])}")
            for server in data["items"]:
                print(f"   - {server['name']} ({server['status']})")

            return data

        except RequestException as e:
            print(f"❌ Failed to list servers: {e}")
            raise

    def _get_auth_headers(self) -> dict:
        """Get authentication headers (API key or JWT token)."""
        if self.api_key:
            return {"X-API-Key": self.api_key}
        elif self.access_token:
            return {"Authorization": f"Bearer {self.access_token}"}
        else:
            raise ValueError("No authentication method configured")


# ============================================
# CLI Interface
# ============================================


def main():
    parser = argparse.ArgumentParser(
        description="SARK Authentication Tutorial",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create and use API key
  python auth_tutorial.py --method api-key --admin-token YOUR_TOKEN

  # Login with LDAP
  python auth_tutorial.py --method ldap --username john.doe --password secret

  # Get OIDC login URL
  python auth_tutorial.py --method oidc

  # Use existing API key
  python auth_tutorial.py --use-api-key sark_dev_abc123...

  # Test token refresh
  python auth_tutorial.py --method ldap --username john.doe --password secret --test-refresh
        """,
    )

    parser.add_argument(
        "--method",
        choices=["api-key", "ldap", "oidc"],
        help="Authentication method to use",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="SARK API base URL (default: http://localhost:8000)",
    )

    # API Key options
    parser.add_argument(
        "--admin-token", help="Admin token for creating API keys (dev only)"
    )
    parser.add_argument(
        "--use-api-key", help="Use an existing API key instead of creating new one"
    )

    # LDAP options
    parser.add_argument("--username", help="LDAP username")
    parser.add_argument("--password", help="LDAP password")

    # Testing options
    parser.add_argument(
        "--test-refresh",
        action="store_true",
        help="Test token refresh flow",
    )
    parser.add_argument(
        "--test-logout",
        action="store_true",
        help="Test logout flow",
    )

    args = parser.parse_args()

    # Initialize client
    client = SARKAuthClient(base_url=args.base_url)

    print("=" * 60)
    print("SARK Authentication Tutorial")
    print("=" * 60)
    print()

    try:
        # Handle authentication method
        if args.use_api_key:
            client.set_api_key(args.use_api_key)

        elif args.method == "api-key":
            if not args.admin_token:
                print("❌ --admin-token required for creating API keys")
                sys.exit(1)

            client.create_api_key(
                admin_token=args.admin_token,
                name="Tutorial API Key",
                scopes=["server:read", "server:write"],
                expires_in_days=30,
            )

        elif args.method == "ldap":
            if not args.username or not args.password:
                print("❌ --username and --password required for LDAP")
                sys.exit(1)

            client.login_ldap(username=args.username, password=args.password)

        elif args.method == "oidc":
            url = client.get_oidc_login_url()
            print(f"\n🌐 Open this URL in your browser:\n{url}\n")
            return

        else:
            parser.print_help()
            return

        # Test authenticated requests
        print("\n" + "=" * 60)
        print("Testing Authenticated Requests")
        print("=" * 60)
        print()

        # Get current user
        client.get_current_user()
        print()

        # List servers
        client.list_servers()
        print()

        # Test token refresh if requested
        if args.test_refresh and client.access_token:
            print("=" * 60)
            print("Testing Token Refresh")
            print("=" * 60)
            print()
            client.refresh_access_token()
            print()

        # Test logout if requested
        if args.test_logout and client.access_token:
            print("=" * 60)
            print("Testing Logout")
            print("=" * 60)
            print()
            client.logout()
            print()

        print("✅ Tutorial completed successfully!")

    except Exception as e:
        print(f"\n❌ Tutorial failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
