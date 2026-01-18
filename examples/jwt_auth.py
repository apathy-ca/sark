#!/usr/bin/env python3
"""
JWT Authentication Example for SARK

This example demonstrates:
- JWT token generation (HS256 and RS256)
- Token validation
- Refresh token flow
- Token expiration handling

Usage:
    python jwt_auth.py
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt


class JWTAuthExample:
    """Example JWT authentication implementation."""

    def __init__(self, algorithm="HS256", secret_key=None):
        """Initialize JWT handler.

        Args:
            algorithm: JWT algorithm (HS256 or RS256)
            secret_key: Secret key for HS256 (optional for RS256)
        """
        self.algorithm = algorithm
        self.secret_key = secret_key or "your-secret-key-min-32-chars-long"
        self.access_token_expire_minutes = 60
        self.refresh_token_expire_days = 7

    def create_access_token(self, user_id, email, role, teams=None):
        """Create a new JWT access token.

        Args:
            user_id: Unique user identifier
            email: User email address
            role: User role (e.g., 'developer', 'admin')
            teams: List of team names

        Returns:
            Encoded JWT token string
        """
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=self.access_token_expire_minutes)

        # Build JWT claims
        claims = {
            "sub": str(user_id),  # Subject (user ID)
            "email": email,
            "role": role,
            "teams": teams or [],
            "iat": now,  # Issued at
            "exp": expires_at,  # Expiration
            "type": "access",
        }

        # Encode JWT
        token = jwt.encode(claims, self.secret_key, algorithm=self.algorithm)

        print(f"✓ Access token created for user: {email}")
        print(f"  - Expires: {expires_at.isoformat()}")
        print(f"  - Role: {role}")
        print(f"  - Teams: {teams}")

        return token

    def create_refresh_token(self, user_id, email):
        """Create a new refresh token.

        Args:
            user_id: Unique user identifier
            email: User email address

        Returns:
            Encoded JWT refresh token string
        """
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=self.refresh_token_expire_days)

        claims = {
            "sub": str(user_id),
            "email": email,
            "iat": now,
            "exp": expires_at,
            "type": "refresh",
        }

        token = jwt.encode(claims, self.secret_key, algorithm=self.algorithm)

        print(f"✓ Refresh token created for user: {email}")
        print(f"  - Expires: {expires_at.isoformat()}")

        return token

    def validate_token(self, token):
        """Validate and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded token claims or None if invalid

        Raises:
            jwt.InvalidTokenError: If token validation fails
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Verify token type
            if payload.get("type") != "access":
                raise ValueError("Invalid token type")

            print("✓ Token validated successfully")
            print(f"  - User: {payload.get('email')}")
            print(f"  - Role: {payload.get('role')}")
            print(f"  - Expires: {datetime.fromtimestamp(payload['exp'], tz=UTC).isoformat()}")

            return payload

        except jwt.InvalidTokenError as e:
            print(f"✗ Token validation failed: {e}")
            raise

    def decode_token_unsafe(self, token):
        """Decode token without validation (for inspection only).

        Args:
            token: JWT token string

        Returns:
            Decoded token claims
        """
        payload = jwt.get_unverified_claims(token)
        return payload


def example_hs256():
    """Example using HS256 (symmetric key) algorithm."""
    print("\n=== HS256 (Symmetric Key) Example ===\n")

    # Initialize JWT handler with HS256
    jwt_handler = JWTAuthExample(algorithm="HS256", secret_key="my-secret-key-must-be-at-least-32-chars-long")

    # Create user context
    user_id = uuid4()
    email = "john.doe@example.com"
    role = "developer"
    teams = ["engineering", "platform"]

    # Step 1: Create access token
    print("Step 1: Creating access token...")
    access_token = jwt_handler.create_access_token(
        user_id=user_id,
        email=email,
        role=role,
        teams=teams,
    )
    print(f"\nAccess Token:\n{access_token}\n")

    # Step 2: Create refresh token
    print("Step 2: Creating refresh token...")
    refresh_token = jwt_handler.create_refresh_token(user_id=user_id, email=email)
    print(f"\nRefresh Token:\n{refresh_token}\n")

    # Step 3: Validate access token
    print("Step 3: Validating access token...")
    try:
        payload = jwt_handler.validate_token(access_token)
        print(f"\nDecoded Payload:\n{payload}\n")
    except jwt.InvalidTokenError:
        print("Token validation failed")

    # Step 4: Demonstrate token expiration
    print("Step 4: Creating expired token (for demonstration)...")
    expired_handler = JWTAuthExample(algorithm="HS256")
    expired_handler.access_token_expire_minutes = -1  # Already expired
    expired_token = expired_handler.create_access_token(
        user_id=user_id,
        email=email,
        role=role,
        teams=teams,
    )

    print("\nAttempting to validate expired token...")
    try:
        jwt_handler.validate_token(expired_token)
    except JWTError as e:
        print(f"✓ Correctly rejected expired token: {e}")


def example_rs256():
    """Example using RS256 (asymmetric key) algorithm."""
    print("\n=== RS256 (Asymmetric Key) Example ===\n")

    # For RS256, you would need:
    # 1. Private key for signing tokens
    # 2. Public key for verifying tokens

    print("RS256 requires RSA key pair:")
    print("\nGenerate keys with:")
    print("  openssl genrsa -out private_key.pem 2048")
    print("  openssl rsa -in private_key.pem -pubout -out public_key.pem")

    print("\nExample code:")
    print("""
# Read private key for signing
with open('private_key.pem', 'r') as f:
    private_key = f.read()

# Read public key for verification
with open('public_key.pem', 'r') as f:
    public_key = f.read()

# Create token with private key
jwt_handler = JWTAuthExample(algorithm='RS256', secret_key=private_key)
token = jwt_handler.create_access_token(
    user_id=uuid4(),
    email='john.doe@example.com',
    role='developer'
)

# Verify token with public key
verify_handler = JWTAuthExample(algorithm='RS256', secret_key=public_key)
payload = verify_handler.validate_token(token)
    """)


def example_token_refresh_flow():
    """Example of complete token refresh flow."""
    print("\n=== Token Refresh Flow Example ===\n")

    jwt_handler = JWTAuthExample(algorithm="HS256")

    user_id = uuid4()
    email = "jane.doe@example.com"
    role = "admin"

    # Step 1: Initial login - get both tokens
    print("Step 1: User logs in...")
    access_token = jwt_handler.create_access_token(user_id, email, role)
    refresh_token = jwt_handler.create_refresh_token(user_id, email)

    # Step 2: Use access token for API requests
    print("\nStep 2: Making API requests with access token...")
    payload = jwt_handler.validate_token(access_token)
    print(f"  ✓ Authenticated as: {payload['email']}")

    # Step 3: Access token expires, use refresh token
    print("\nStep 3: Access token expired, refreshing...")
    try:
        # Validate refresh token
        refresh_payload = jwt.decode(refresh_token, jwt_handler.secret_key, algorithms=[jwt_handler.algorithm])

        if refresh_payload.get("type") != "refresh":
            raise ValueError("Invalid token type")

        # Issue new access token
        jwt_handler.create_access_token(
            user_id=refresh_payload["sub"],
            email=refresh_payload["email"],
            role=role,  # Would fetch from database in real app
        )

        print("  ✓ New access token issued")

    except JWTError as e:
        print(f"  ✗ Token refresh failed: {e}")


def example_with_sark_api():
    """Example of using JWT tokens with SARK API."""
    print("\n=== SARK API Integration Example ===\n")

    print("""
# Example: Authenticate and use access token with SARK

import requests

# Step 1: Login with LDAP credentials
response = requests.post(
    'https://sark.example.com/api/v1/auth/login/ldap',
    json={
        'username': 'john.doe',
        'password': 'secret123'
    }
)
auth_data = response.json()

access_token = auth_data['access_token']
refresh_token = auth_data['refresh_token']

print(f"Access token: {access_token[:50]}...")
print(f"Expires in: {auth_data['expires_in']} seconds")

# Step 2: Use access token for API requests
headers = {'Authorization': f'Bearer {access_token}'}

# List servers
response = requests.get(
    'https://sark.example.com/api/v1/servers',
    headers=headers
)
servers = response.json()
print(f"Found {len(servers['items'])} servers")

# Step 3: Refresh access token when it expires
response = requests.post(
    'https://sark.example.com/api/v1/auth/refresh',
    json={'refresh_token': refresh_token}
)
new_tokens = response.json()

access_token = new_tokens['access_token']
# Update headers with new token
headers = {'Authorization': f'Bearer {access_token}'}

# Step 4: Logout (revoke refresh token)
requests.post(
    'https://sark.example.com/api/v1/auth/revoke',
    headers=headers,
    json={'refresh_token': refresh_token}
)
print("Logged out successfully")
    """)


def main():
    """Run all examples."""
    print("=" * 60)
    print("SARK JWT Authentication Examples")
    print("=" * 60)

    try:
        # Example 1: HS256 symmetric key
        example_hs256()

        # Example 2: RS256 asymmetric key
        example_rs256()

        # Example 3: Token refresh flow
        example_token_refresh_flow()

        # Example 4: SARK API integration
        example_with_sark_api()

        print("\n" + "=" * 60)
        print("Examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
