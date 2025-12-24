"""Docker-based SAML fixtures for integration testing."""

import base64
from typing import Generator

import pytest
import httpx

# Check if pytest-docker is available
try:
    from pytest_docker.plugin import Services
except ImportError:
    pytest.skip("pytest-docker not installed", allow_module_level=True)


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    """Path to docker-compose.yml file."""
    return str(pytestconfig.rootdir / "tests" / "fixtures" / "docker-compose.saml.yml")


@pytest.fixture(scope="session")
def saml_service(docker_services: Services) -> Generator[dict, None, None]:
    """
    Start SAML IdP Docker container and wait for it to be ready.

    Yields:
        Dictionary with SAML connection details
    """
    # Wait for SAML service to be ready
    docker_services.wait_until_responsive(
        timeout=90.0,
        pause=1.0,
        check=lambda: is_saml_responsive(
            docker_services.docker_ip,
            docker_services.port_for("saml-idp", 8080)
        ),
    )

    # Get connection details
    host = docker_services.docker_ip
    port = docker_services.port_for("saml-idp", 8080)
    https_port = docker_services.port_for("saml-idp", 8443)

    saml_config = {
        "host": host,
        "port": port,
        "https_port": https_port,
        "idp_entity_id": f"http://{host}:{port}/simplesaml/saml2/idp/metadata.php",
        "idp_sso_url": f"http://{host}:{port}/simplesaml/saml2/idp/SSOService.php",
        "idp_slo_url": f"http://{host}:{port}/simplesaml/saml2/idp/SingleLogoutService.php",
        "sp_entity_id": "http://localhost:8000/saml/metadata",
        "sp_acs_url": "http://localhost:8000/saml/acs",
        "sp_slo_url": "http://localhost:8000/saml/sls",
        # Test IdP provides test users
        "test_users": [
            {"username": "user1", "password": "user1pass", "email": "user1@example.com", "name": "User 1"},
            {"username": "user2", "password": "user2pass", "email": "user2@example.com", "name": "User 2"},
        ],
    }

    yield saml_config


def is_saml_responsive(host: str, port: int) -> bool:
    """
    Check if SAML IdP is responsive.

    Args:
        host: SAML IdP host
        port: SAML IdP port

    Returns:
        True if SAML IdP is ready
    """
    try:
        response = httpx.get(
            f"http://{host}:{port}/simplesaml/",
            timeout=5.0,
            follow_redirects=True
        )
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture
def saml_provider_config(saml_service):
    """
    Create SAML provider configuration for integration tests.

    Args:
        saml_service: SAML service fixture

    Returns:
        SAMLProviderConfig instance
    """
    from sark.services.auth.providers.saml import SAMLProviderConfig

    # Fetch IdP metadata to get X.509 certificate
    try:
        import httpx
        response = httpx.get(saml_service["idp_entity_id"], timeout=10.0)
        if response.status_code == 200:
            # Extract certificate from metadata (simplified)
            # In real implementation, parse XML properly
            idp_cert = "MIIDEjCCAfqgAwIBAgIJAKoSq..."  # Placeholder
        else:
            idp_cert = "test_certificate"
    except:
        idp_cert = "test_certificate"

    return SAMLProviderConfig(
        name="test-saml",
        idp_entity_id=saml_service["idp_entity_id"],
        idp_sso_url=saml_service["idp_sso_url"],
        idp_slo_url=saml_service["idp_slo_url"],
        idp_x509_cert=idp_cert,
        sp_entity_id=saml_service["sp_entity_id"],
        sp_acs_url=saml_service["sp_acs_url"],
        sp_slo_url=saml_service["sp_slo_url"],
    )


@pytest.fixture
def saml_provider(saml_provider_config):
    """
    Create SAML provider instance for integration tests.

    Args:
        saml_provider_config: SAML provider configuration

    Returns:
        SAMLProvider instance
    """
    from sark.services.auth.providers.saml import SAMLProvider

    return SAMLProvider(saml_provider_config)


@pytest.fixture
def sample_saml_response():
    """
    Generate a sample SAML response for testing.

    Returns:
        Base64-encoded SAML response
    """
    saml_xml = """<?xml version="1.0" encoding="UTF-8"?>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
                ID="_test_response_id"
                Version="2.0"
                IssueInstant="2024-01-01T00:00:00Z"
                Destination="http://localhost:8000/saml/acs">
    <saml:Issuer>http://localhost:8080/simplesaml/saml2/idp/metadata.php</saml:Issuer>
    <samlp:Status>
        <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>
    </samlp:Status>
    <saml:Assertion ID="_test_assertion_id"
                    Version="2.0"
                    IssueInstant="2024-01-01T00:00:00Z">
        <saml:Issuer>http://localhost:8080/simplesaml/saml2/idp/metadata.php</saml:Issuer>
        <saml:Subject>
            <saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">
                user1@example.com
            </saml:NameID>
        </saml:Subject>
        <saml:Conditions NotBefore="2024-01-01T00:00:00Z"
                        NotOnOrAfter="2024-01-01T01:00:00Z">
            <saml:AudienceRestriction>
                <saml:Audience>http://localhost:8000/saml/metadata</saml:Audience>
            </saml:AudienceRestriction>
        </saml:Conditions>
        <saml:AuthnStatement AuthnInstant="2024-01-01T00:00:00Z"
                            SessionIndex="_test_session_index">
            <saml:AuthnContext>
                <saml:AuthnContextClassRef>
                    urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport
                </saml:AuthnContextClassRef>
            </saml:AuthnContext>
        </saml:AuthnStatement>
        <saml:AttributeStatement>
            <saml:Attribute Name="uid">
                <saml:AttributeValue>user1</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="email">
                <saml:AttributeValue>user1@example.com</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="displayName">
                <saml:AttributeValue>User 1</saml:AttributeValue>
            </saml:Attribute>
            <saml:Attribute Name="groups">
                <saml:AttributeValue>developers</saml:AttributeValue>
                <saml:AttributeValue>users</saml:AttributeValue>
            </saml:Attribute>
        </saml:AttributeStatement>
    </saml:Assertion>
</samlp:Response>"""

    # Base64 encode the SAML response
    encoded_response = base64.b64encode(saml_xml.encode("utf-8")).decode("utf-8")
    return encoded_response
