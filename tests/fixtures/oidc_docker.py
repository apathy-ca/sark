"""Docker-based OIDC fixtures for integration testing."""

import time
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
    return str(pytestconfig.rootdir / "tests" / "fixtures" / "docker-compose.oidc.yml")


@pytest.fixture(scope="session")
def oidc_service(docker_services: Services) -> Generator[dict, None, None]:
    """
    Start OIDC Mock Server Docker container and wait for it to be ready.

    Yields:
        Dictionary with OIDC connection details
    """
    # Wait for OIDC service to be ready
    docker_services.wait_until_responsive(
        timeout=60.0,
        pause=0.5,
        check=lambda: is_oidc_responsive(
            "localhost",
            docker_services.port_for("oidc-mock", 8080)
        ),
    )

    # Get connection details
    host = "localhost"
    port = docker_services.port_for("oidc-mock", 8080)

    oidc_config = {
        "host": host,
        "port": port,
        "issuer_url": f"http://{host}:{port}/default",
        "auth_endpoint": f"http://{host}:{port}/default/authorize",
        "token_endpoint": f"http://{host}:{port}/default/token",
        "userinfo_endpoint": f"http://{host}:{port}/default/userinfo",
        "jwks_uri": f"http://{host}:{port}/default/jwks",
        "client_id": "test_client",
        "client_secret": "test_secret",
        "redirect_uri": "http://localhost:8000/callback",
    }

    yield oidc_config


def is_oidc_responsive(host: str, port: int) -> bool:
    """
    Check if OIDC server is responsive.

    Args:
        host: OIDC server host
        port: OIDC server port

    Returns:
        True if OIDC server is ready
    """
    try:
        response = httpx.get(
            f"http://{host}:{port}/default/.well-known/openid-configuration",
            timeout=2.0
        )
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture
def oidc_provider_config(oidc_service):
    """
    Create OIDC provider configuration for integration tests.

    Args:
        oidc_service: OIDC service fixture

    Returns:
        OIDCProviderConfig instance
    """
    from sark.services.auth.providers.oidc import OIDCProviderConfig

    return OIDCProviderConfig(
        name="test-oidc",
        issuer_url=oidc_service["issuer_url"],
        client_id=oidc_service["client_id"],
        client_secret=oidc_service["client_secret"],
        redirect_uri=oidc_service["redirect_uri"],
        scopes=["openid", "profile", "email"],
    )


@pytest.fixture
def oidc_provider(oidc_provider_config):
    """
    Create OIDC provider instance for integration tests.

    Args:
        oidc_provider_config: OIDC provider configuration

    Returns:
        OIDCProvider instance
    """
    from sark.services.auth.providers.oidc import OIDCProvider

    return OIDCProvider(oidc_provider_config)


@pytest.fixture
async def oidc_test_token(oidc_service):
    """
    Generate a test access token from the OIDC mock server.

    Args:
        oidc_service: OIDC service fixture

    Returns:
        Dictionary with test tokens and user info
    """
    # Mock OAuth2 server accepts any request and returns valid tokens
    # We can simulate token generation by calling the token endpoint directly
    async with httpx.AsyncClient() as client:
        # The mock server allows us to create tokens with custom claims
        token_response = await client.post(
            f"{oidc_service['token_endpoint']}",
            data={
                "grant_type": "client_credentials",
                "client_id": oidc_service["client_id"],
                "client_secret": oidc_service["client_secret"],
                "scope": "openid profile email",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if token_response.status_code == 200:
            token_data = token_response.json()
            return {
                "access_token": token_data.get("access_token"),
                "id_token": token_data.get("id_token"),
                "token_type": token_data.get("token_type", "Bearer"),
                "expires_in": token_data.get("expires_in", 3600),
            }
        else:
            # Return a mock token structure if direct generation fails
            return {
                "access_token": "mock_access_token",
                "id_token": "mock_id_token",
                "token_type": "Bearer",
                "expires_in": 3600,
            }
