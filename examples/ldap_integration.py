#!/usr/bin/env python3
"""
LDAP Integration Example for SARK

This example demonstrates:
- LDAP server connection
- User authentication
- Group lookup
- Role mapping
- Error handling

Usage:
    python ldap_integration.py
"""

import os
from typing import Dict, List, Optional

# Note: ldap3 must be installed: pip install ldap3
try:
    from ldap3 import ALL, SIMPLE, SUBTREE, Connection, Server
    from ldap3.core.exceptions import LDAPBindError, LDAPException

    LDAP3_AVAILABLE = True
except ImportError:
    LDAP3_AVAILABLE = False
    print("Warning: ldap3 not installed. Run: pip install ldap3")


class LDAPIntegrationExample:
    """Example LDAP integration for SARK authentication."""

    def __init__(
        self,
        server_uri: str,
        bind_dn: str,
        bind_password: str,
        user_base_dn: str,
        group_base_dn: Optional[str] = None,
        use_ssl: bool = True,
    ):
        """Initialize LDAP connection.

        Args:
            server_uri: LDAP server URI (e.g., ldaps://ldap.example.com:636)
            bind_dn: Service account DN for binding
            bind_password: Service account password
            user_base_dn: Base DN for user searches
            group_base_dn: Base DN for group searches (optional)
            use_ssl: Whether to use SSL/TLS
        """
        if not LDAP3_AVAILABLE:
            raise ImportError("ldap3 library is required. Install with: pip install ldap3")

        self.server_uri = server_uri
        self.bind_dn = bind_dn
        self.bind_password = bind_password
        self.user_base_dn = user_base_dn
        self.group_base_dn = group_base_dn
        self.use_ssl = use_ssl

        # Create server object
        self.server = Server(server_uri, get_info=ALL, use_ssl=use_ssl)

    def test_connection(self) -> bool:
        """Test LDAP server connectivity.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            print("Testing LDAP connection...")
            conn = Connection(
                self.server,
                user=self.bind_dn,
                password=self.bind_password,
                authentication=SIMPLE,
                auto_bind=True,
            )

            print(f"✓ Successfully connected to: {self.server_uri}")
            print(f"  - Server info: {self.server.info}")
            conn.unbind()
            return True

        except LDAPException as e:
            print(f"✗ Connection failed: {e}")
            return False

    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user with LDAP.

        Args:
            username: Username to authenticate
            password: User password

        Returns:
            User information dict if successful, None otherwise
        """
        try:
            print(f"\nAuthenticating user: {username}")

            # Step 1: Search for user DN using service account
            conn = Connection(
                self.server,
                user=self.bind_dn,
                password=self.bind_password,
                authentication=SIMPLE,
                auto_bind=True,
            )

            search_filter = f"(uid={username})"
            conn.search(
                search_base=self.user_base_dn,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=["mail", "cn", "givenName", "sn", "uid"],
            )

            if not conn.entries:
                print(f"✗ User not found: {username}")
                conn.unbind()
                return None

            # Get user entry and DN
            user_entry = conn.entries[0]
            user_dn = user_entry.entry_dn
            print(f"  - Found user DN: {user_dn}")

            # Extract user attributes
            user_info = {
                "user_id": user_dn,
                "username": str(user_entry.uid) if hasattr(user_entry, "uid") else username,
                "email": str(user_entry.mail) if hasattr(user_entry, "mail") else "",
                "name": str(user_entry.cn) if hasattr(user_entry, "cn") else "",
                "given_name": str(user_entry.givenName) if hasattr(user_entry, "givenName") else "",
                "family_name": str(user_entry.sn) if hasattr(user_entry, "sn") else "",
            }

            conn.unbind()

            # Step 2: Bind as user to verify password
            try:
                user_conn = Connection(
                    self.server,
                    user=user_dn,
                    password=password,
                    authentication=SIMPLE,
                    auto_bind=True,
                )
                user_conn.unbind()

                print(f"✓ Authentication successful for: {username}")

            except LDAPBindError:
                print(f"✗ Invalid password for: {username}")
                return None

            # Step 3: Get user groups
            if self.group_base_dn:
                user_info["groups"] = self.get_user_groups(user_dn)
                print(f"  - Groups: {user_info['groups']}")

            return user_info

        except LDAPException as e:
            print(f"✗ Authentication error: {e}")
            return None

    def get_user_groups(self, user_dn: str) -> List[str]:
        """Get groups for a user.

        Args:
            user_dn: User DN

        Returns:
            List of group names
        """
        if not self.group_base_dn:
            return []

        try:
            conn = Connection(
                self.server,
                user=self.bind_dn,
                password=self.bind_password,
                authentication=SIMPLE,
                auto_bind=True,
            )

            # Search for groups where user is a member
            search_filter = f"(member={user_dn})"
            conn.search(
                search_base=self.group_base_dn,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=["cn"],
            )

            groups = [str(entry.cn) for entry in conn.entries if hasattr(entry, "cn")]
            conn.unbind()

            return groups

        except LDAPException as e:
            print(f"✗ Group lookup error: {e}")
            return []

    def search_users(self, search_filter: str = "(objectClass=person)", limit: int = 10) -> List[Dict]:
        """Search for users in LDAP.

        Args:
            search_filter: LDAP search filter
            limit: Maximum number of results

        Returns:
            List of user dictionaries
        """
        try:
            print(f"\nSearching users with filter: {search_filter}")

            conn = Connection(
                self.server,
                user=self.bind_dn,
                password=self.bind_password,
                authentication=SIMPLE,
                auto_bind=True,
            )

            conn.search(
                search_base=self.user_base_dn,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=["uid", "mail", "cn"],
                size_limit=limit,
            )

            users = []
            for entry in conn.entries:
                users.append(
                    {
                        "dn": entry.entry_dn,
                        "username": str(entry.uid) if hasattr(entry, "uid") else "",
                        "email": str(entry.mail) if hasattr(entry, "mail") else "",
                        "name": str(entry.cn) if hasattr(entry, "cn") else "",
                    }
                )

            conn.unbind()

            print(f"✓ Found {len(users)} users")
            for user in users:
                print(f"  - {user['username']} ({user['email']})")

            return users

        except LDAPException as e:
            print(f"✗ Search error: {e}")
            return []


def map_groups_to_roles(groups: List[str], role_mapping: Dict[str, str]) -> List[str]:
    """Map LDAP groups to SARK roles.

    Args:
        groups: List of LDAP group names
        role_mapping: Dictionary mapping group names to role names

    Returns:
        List of SARK roles
    """
    roles = []
    for group in groups:
        if group in role_mapping:
            roles.append(role_mapping[group])

    return roles


def example_openldap():
    """Example with OpenLDAP server."""
    print("\n" + "=" * 60)
    print("OpenLDAP Integration Example")
    print("=" * 60)

    if not LDAP3_AVAILABLE:
        print("ldap3 not available, skipping example")
        return

    # Configuration
    config = {
        "server_uri": os.getenv("LDAP_SERVER", "ldap://localhost:389"),
        "bind_dn": os.getenv("LDAP_BIND_DN", "cn=admin,dc=example,dc=com"),
        "bind_password": os.getenv("LDAP_BIND_PASSWORD", "admin"),
        "user_base_dn": os.getenv("LDAP_USER_BASE_DN", "ou=users,dc=example,dc=com"),
        "group_base_dn": os.getenv("LDAP_GROUP_BASE_DN", "ou=groups,dc=example,dc=com"),
        "use_ssl": False,  # Use True for ldaps://
    }

    print(f"\nConfiguration:")
    for key, value in config.items():
        if "password" in key.lower():
            print(f"  {key}: ********")
        else:
            print(f"  {key}: {value}")

    try:
        ldap = LDAPIntegrationExample(**config)

        # Test connection
        if not ldap.test_connection():
            print("\n✗ Connection test failed. Check your configuration.")
            return

        # Example authentication
        # Note: Replace with actual test user
        # user_info = ldap.authenticate_user("testuser", "password123")
        # if user_info:
        #     print(f"\nUser Info: {user_info}")

        # Example user search
        # users = ldap.search_users(limit=5)

    except Exception as e:
        print(f"\n✗ Error: {e}")


def example_active_directory():
    """Example with Active Directory."""
    print("\n" + "=" * 60)
    print("Active Directory Integration Example")
    print("=" * 60)

    if not LDAP3_AVAILABLE:
        print("ldap3 not available, skipping example")
        return

    # Active Directory configuration
    config = {
        "server_uri": os.getenv("LDAP_SERVER", "ldaps://ad.corp.example.com:636"),
        "bind_dn": os.getenv("LDAP_BIND_DN", "CN=SARK Service,OU=Service Accounts,DC=corp,DC=example,DC=com"),
        "bind_password": os.getenv("LDAP_BIND_PASSWORD", "service_password"),
        "user_base_dn": os.getenv("LDAP_USER_BASE_DN", "OU=Users,DC=corp,DC=example,DC=com"),
        "group_base_dn": os.getenv("LDAP_GROUP_BASE_DN", "OU=Groups,DC=corp,DC=example,DC=com"),
        "use_ssl": True,
    }

    print("\nActive Directory specific filters:")
    print("  User filter: (sAMAccountName={username})")
    print("  User filter (UPN): (userPrincipalName={username}@example.com)")
    print("  Group filter: (member={user_dn})")
    print("  Nested groups: (member:1.2.840.113556.1.4.1941:={user_dn})")


def example_role_mapping():
    """Example of mapping LDAP groups to SARK roles."""
    print("\n" + "=" * 60)
    print("Role Mapping Example")
    print("=" * 60)

    # LDAP groups
    user_groups = ["cn=developers,ou=groups,dc=example,dc=com", "cn=platform-team,ou=groups,dc=example,dc=com", "cn=sre,ou=groups,dc=example,dc=com"]

    # Role mapping configuration
    role_mapping = {
        "cn=admins,ou=groups,dc=example,dc=com": "admin",
        "cn=developers,ou=groups,dc=example,dc=com": "developer",
        "cn=platform-team,ou=groups,dc=example,dc=com": "developer",
        "cn=sre,ou=groups,dc=example,dc=com": "operator",
        "cn=readonly,ou=groups,dc=example,dc=com": "viewer",
    }

    print(f"\nUser's LDAP groups:")
    for group in user_groups:
        print(f"  - {group}")

    print(f"\nRole mapping configuration:")
    for group, role in role_mapping.items():
        print(f"  {group} → {role}")

    # Map groups to roles
    roles = map_groups_to_roles(user_groups, role_mapping)

    print(f"\nMapped SARK roles:")
    for role in roles:
        print(f"  - {role}")


def example_sark_integration():
    """Example of integrating LDAP with SARK API."""
    print("\n" + "=" * 60)
    print("SARK API Integration Example")
    print("=" * 60)

    print("""
# Complete flow: LDAP authentication → JWT tokens → API access

import requests

# Step 1: Authenticate with LDAP credentials
response = requests.post(
    'https://sark.example.com/api/v1/auth/login/ldap',
    json={
        'username': 'john.doe',
        'password': 'secret123'
    }
)

auth_data = response.json()
print(f"Authenticated as: {auth_data['user']['email']}")
print(f"Roles: {auth_data['user']['roles']}")
print(f"Teams: {auth_data['user']['teams']}")

# Access and refresh tokens
access_token = auth_data['access_token']
refresh_token = auth_data['refresh_token']

# Step 2: Use access token for API requests
headers = {'Authorization': f'Bearer {access_token}'}

response = requests.get(
    'https://sark.example.com/api/v1/servers',
    headers=headers
)
servers = response.json()
print(f"Found {len(servers['items'])} servers")

# Step 3: Refresh token when access token expires
response = requests.post(
    'https://sark.example.com/api/v1/auth/refresh',
    json={'refresh_token': refresh_token}
)
new_tokens = response.json()
access_token = new_tokens['access_token']
    """)


def main():
    """Run all examples."""
    print("=" * 60)
    print("SARK LDAP Integration Examples")
    print("=" * 60)

    print("\nNote: Set environment variables for your LDAP server:")
    print("  - LDAP_SERVER")
    print("  - LDAP_BIND_DN")
    print("  - LDAP_BIND_PASSWORD")
    print("  - LDAP_USER_BASE_DN")
    print("  - LDAP_GROUP_BASE_DN")

    # Example 1: OpenLDAP
    example_openldap()

    # Example 2: Active Directory
    example_active_directory()

    # Example 3: Role mapping
    example_role_mapping()

    # Example 4: SARK API integration
    example_sark_integration()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
