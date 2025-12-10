"""Docker-based LDAP fixtures for integration testing."""

import time
from typing import Generator

import pytest
from ldap3 import Connection, MODIFY_REPLACE, Server, ALL

# Check if pytest-docker is available
try:
    from pytest_docker.plugin import Services
except ImportError:
    pytest.skip("pytest-docker not installed", allow_module_level=True)


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    """Path to docker-compose.yml file."""
    return str(pytestconfig.rootdir / "tests" / "fixtures" / "docker-compose.ldap.yml")


@pytest.fixture(scope="session")
def ldap_service(docker_services: Services) -> Generator[dict, None, None]:
    """
    Start OpenLDAP Docker container and wait for it to be ready.

    Yields:
        Dictionary with LDAP connection details
    """
    # Wait for LDAP service to be ready
    docker_services.wait_until_responsive(
        timeout=60.0,
        pause=0.5,
        check=lambda: is_ldap_responsive(
            docker_services.docker_ip,
            docker_services.port_for("ldap", 389)
        ),
    )

    # Get connection details
    host = docker_services.docker_ip
    port = docker_services.port_for("ldap", 389)

    ldap_config = {
        "host": host,
        "port": port,
        "server_url": f"ldap://{host}:{port}",
        "base_dn": "dc=example,dc=com",
        "bind_dn": "cn=admin,dc=example,dc=com",
        "bind_password": "admin",
    }

    # Populate LDAP with test data
    populate_ldap_test_data(ldap_config)

    yield ldap_config


def is_ldap_responsive(host: str, port: int) -> bool:
    """
    Check if LDAP server is responsive.

    Args:
        host: LDAP server host
        port: LDAP server port

    Returns:
        True if LDAP server is ready
    """
    try:
        server = Server(f"ldap://{host}:{port}", get_info=ALL)
        conn = Connection(
            server,
            user="cn=admin,dc=example,dc=com",
            password="admin",
            auto_bind=True,
        )
        conn.unbind()
        return True
    except Exception:
        return False


def populate_ldap_test_data(ldap_config: dict) -> None:
    """
    Populate LDAP server with test data.

    Args:
        ldap_config: LDAP connection configuration
    """
    server = Server(ldap_config["server_url"], get_info=ALL)
    conn = Connection(
        server,
        user=ldap_config["bind_dn"],
        password=ldap_config["bind_password"],
        auto_bind=True,
    )

    base_dn = ldap_config["base_dn"]

    try:
        # Create organizational units
        conn.add(f"ou=users,{base_dn}", ["organizationalUnit"], {"ou": "users"})
        conn.add(f"ou=groups,{base_dn}", ["organizationalUnit"], {"ou": "groups"})

        # Add test users
        test_users = [
            {
                "dn": f"uid=testuser,ou=users,{base_dn}",
                "objectClass": ["inetOrgPerson", "posixAccount", "shadowAccount"],
                "attributes": {
                    "uid": "testuser",
                    "cn": "Test User",
                    "sn": "User",
                    "givenName": "Test",
                    "mail": "testuser@example.com",
                    "userPassword": "testpass",
                    "uidNumber": "10001",
                    "gidNumber": "10001",
                    "homeDirectory": "/home/testuser",
                },
            },
            {
                "dn": f"uid=admin,ou=users,{base_dn}",
                "objectClass": ["inetOrgPerson", "posixAccount", "shadowAccount"],
                "attributes": {
                    "uid": "admin",
                    "cn": "Admin User",
                    "sn": "User",
                    "givenName": "Admin",
                    "mail": "admin@example.com",
                    "userPassword": "adminpass",
                    "uidNumber": "10002",
                    "gidNumber": "10002",
                    "homeDirectory": "/home/admin",
                },
            },
            {
                "dn": f"uid=jdoe,ou=users,{base_dn}",
                "objectClass": ["inetOrgPerson", "posixAccount", "shadowAccount"],
                "attributes": {
                    "uid": "jdoe",
                    "cn": "John Doe",
                    "sn": "Doe",
                    "givenName": "John",
                    "mail": "jdoe@example.com",
                    "userPassword": "password123",
                    "uidNumber": "10003",
                    "gidNumber": "10003",
                    "homeDirectory": "/home/jdoe",
                },
            },
        ]

        for user in test_users:
            try:
                conn.add(user["dn"], user["objectClass"], user["attributes"])
            except Exception as e:
                # User might already exist
                pass

        # Add test groups
        test_groups = [
            {
                "dn": f"cn=developers,ou=groups,{base_dn}",
                "objectClass": ["groupOfNames"],
                "attributes": {
                    "cn": "developers",
                    "member": [
                        f"uid=testuser,ou=users,{base_dn}",
                        f"uid=jdoe,ou=users,{base_dn}",
                    ],
                },
            },
            {
                "dn": f"cn=admins,ou=groups,{base_dn}",
                "objectClass": ["groupOfNames"],
                "attributes": {
                    "cn": "admins",
                    "member": [f"uid=admin,ou=users,{base_dn}"],
                },
            },
        ]

        for group in test_groups:
            try:
                conn.add(group["dn"], group["objectClass"], group["attributes"])
            except Exception as e:
                # Group might already exist
                pass

    except Exception as e:
        print(f"Error populating LDAP: {e}")
    finally:
        conn.unbind()


@pytest.fixture
def ldap_provider_config(ldap_service):
    """
    Create LDAP provider configuration for integration tests.

    Args:
        ldap_service: LDAP service fixture

    Returns:
        LDAPProviderConfig instance
    """
    from sark.services.auth.providers.ldap import LDAPProviderConfig

    return LDAPProviderConfig(
        name="test-ldap",
        server_url=ldap_service["server_url"],
        bind_dn=ldap_service["bind_dn"],
        bind_password=ldap_service["bind_password"],
        base_dn=ldap_service["base_dn"],
        group_search_base=f"ou=groups,{ldap_service['base_dn']}",
        use_ssl=False,  # Docker container doesn't use SSL
    )


@pytest.fixture
def ldap_provider(ldap_provider_config):
    """
    Create LDAP provider instance for integration tests.

    Args:
        ldap_provider_config: LDAP provider configuration

    Returns:
        LDAPProvider instance
    """
    from sark.services.auth.providers.ldap import LDAPProvider

    return LDAPProvider(ldap_provider_config)
