"""Docker-based fixtures for integration testing infrastructure."""

import asyncio
import time
from typing import AsyncGenerator, Generator

import pytest
import httpx
import psycopg2
import redis

# Check if pytest-docker is available
try:
    from pytest_docker.plugin import Services
except ImportError:
    pytest.skip("pytest-docker not installed", allow_module_level=True)


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    """Path to docker-compose.yml file for integration tests."""
    return str(pytestconfig.rootdir / "tests" / "fixtures" / "docker-compose.integration.yml")


@pytest.fixture(scope="session")
def docker_cleanup():
    """Control Docker cleanup behavior."""
    # Keep containers running between test runs for faster iteration
    return "down"  # Options: "down" (cleanup) or "keep" (leave running)


# =============================================================================
# PostgreSQL Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def postgres_service(docker_services: Services) -> Generator[dict, None, None]:
    """
    Start PostgreSQL Docker container and wait for it to be ready.

    Yields:
        Dictionary with PostgreSQL connection details
    """
    # Wait for PostgreSQL to be ready
    docker_services.wait_until_responsive(
        timeout=60.0,
        pause=0.5,
        check=lambda: is_postgres_responsive(
            docker_services.docker_ip,
            docker_services.port_for("postgres", 5432)
        ),
    )

    host = docker_services.docker_ip
    port = docker_services.port_for("postgres", 5432)

    postgres_config = {
        "host": host,
        "port": port,
        "database": "sark_test",
        "user": "sark_test",
        "password": "sark_test",
        "connection_string": f"postgresql://sark_test:sark_test@{host}:{port}/sark_test",
    }

    yield postgres_config


def is_postgres_responsive(host: str, port: int) -> bool:
    """Check if PostgreSQL is responsive."""
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user="sark_test",
            password="sark_test",
            database="sark_test",
            connect_timeout=2
        )
        conn.close()
        return True
    except Exception:
        return False


@pytest.fixture
async def postgres_connection(postgres_service):
    """
    Provide async PostgreSQL connection for tests.

    Args:
        postgres_service: PostgreSQL service fixture

    Returns:
        Async connection pool
    """
    import asyncpg

    pool = await asyncpg.create_pool(
        host=postgres_service["host"],
        port=postgres_service["port"],
        user=postgres_service["user"],
        password=postgres_service["password"],
        database=postgres_service["database"],
        min_size=1,
        max_size=5,
    )

    yield pool

    await pool.close()


# =============================================================================
# TimescaleDB Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def timescaledb_service(docker_services: Services) -> Generator[dict, None, None]:
    """
    Start TimescaleDB Docker container and wait for it to be ready.

    Yields:
        Dictionary with TimescaleDB connection details
    """
    docker_services.wait_until_responsive(
        timeout=60.0,
        pause=0.5,
        check=lambda: is_postgres_responsive(
            docker_services.docker_ip,
            docker_services.port_for("timescaledb", 5432)
        ),
    )

    host = docker_services.docker_ip
    port = docker_services.port_for("timescaledb", 5432)

    timescale_config = {
        "host": host,
        "port": port,
        "database": "sark_audit_test",
        "user": "sark_test",
        "password": "sark_test",
        "connection_string": f"postgresql://sark_test:sark_test@{host}:{port}/sark_audit_test",
    }

    yield timescale_config


@pytest.fixture
async def timescaledb_connection(timescaledb_service):
    """Provide async TimescaleDB connection for tests."""
    import asyncpg

    pool = await asyncpg.create_pool(
        host=timescaledb_service["host"],
        port=timescaledb_service["port"],
        user=timescaledb_service["user"],
        password=timescaledb_service["password"],
        database=timescaledb_service["database"],
        min_size=1,
        max_size=5,
    )

    yield pool

    await pool.close()


# =============================================================================
# Redis Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def redis_service(docker_services: Services) -> Generator[dict, None, None]:
    """
    Start Redis Docker container and wait for it to be ready.

    Yields:
        Dictionary with Redis connection details
    """
    docker_services.wait_until_responsive(
        timeout=60.0,
        pause=0.5,
        check=lambda: is_redis_responsive(
            docker_services.docker_ip,
            docker_services.port_for("redis", 6379)
        ),
    )

    host = docker_services.docker_ip
    port = docker_services.port_for("redis", 6379)

    redis_config = {
        "host": host,
        "port": port,
        "url": f"redis://{host}:{port}",
    }

    yield redis_config


def is_redis_responsive(host: str, port: int) -> bool:
    """Check if Redis is responsive."""
    try:
        client = redis.Redis(host=host, port=port, socket_timeout=2)
        client.ping()
        client.close()
        return True
    except Exception:
        return False


@pytest.fixture
async def redis_connection(redis_service):
    """Provide async Redis connection for tests."""
    import redis.asyncio as aioredis

    client = aioredis.Redis(
        host=redis_service["host"],
        port=redis_service["port"],
        decode_responses=True,
    )

    yield client

    await client.close()


# =============================================================================
# OPA Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def opa_service(docker_services: Services) -> Generator[dict, None, None]:
    """
    Start OPA Docker container and wait for it to be ready.

    Yields:
        Dictionary with OPA connection details
    """
    docker_services.wait_until_responsive(
        timeout=60.0,
        pause=0.5,
        check=lambda: is_opa_responsive(
            docker_services.docker_ip,
            docker_services.port_for("opa", 8181)
        ),
    )

    host = docker_services.docker_ip
    port = docker_services.port_for("opa", 8181)

    opa_config = {
        "host": host,
        "port": port,
        "url": f"http://{host}:{port}",
        "health_url": f"http://{host}:{port}/health",
        "v1_data_url": f"http://{host}:{port}/v1/data",
    }

    yield opa_config


def is_opa_responsive(host: str, port: int) -> bool:
    """Check if OPA is responsive."""
    try:
        response = httpx.get(f"http://{host}:{port}/health", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture
def opa_client(opa_service):
    """Provide OPA client for tests."""
    from sark.services.policy.opa_client import OPAClient

    return OPAClient(opa_url=opa_service["url"])


# =============================================================================
# gRPC Mock Server Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def grpc_mock_service(docker_services: Services) -> Generator[dict, None, None]:
    """
    Start gRPC Mock Server Docker container and wait for it to be ready.

    Yields:
        Dictionary with gRPC mock server connection details
    """
    docker_services.wait_until_responsive(
        timeout=60.0,
        pause=0.5,
        check=lambda: is_grpc_mock_responsive(
            docker_services.docker_ip,
            docker_services.port_for("grpc-mock", 4770)
        ),
    )

    host = docker_services.docker_ip
    grpc_port = docker_services.port_for("grpc-mock", 4770)
    admin_port = docker_services.port_for("grpc-mock", 4771)

    grpc_config = {
        "host": host,
        "grpc_port": grpc_port,
        "admin_port": admin_port,
        "endpoint": f"{host}:{grpc_port}",
        "admin_url": f"http://{host}:{admin_port}",
    }

    yield grpc_config


def is_grpc_mock_responsive(host: str, port: int) -> bool:
    """Check if gRPC mock server is responsive."""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


# =============================================================================
# Combined Fixtures (All Services)
# =============================================================================

@pytest.fixture(scope="session")
def all_services(
    postgres_service,
    timescaledb_service,
    redis_service,
    opa_service,
    grpc_mock_service,
) -> dict:
    """
    Provide all integration test services in one fixture.

    Returns:
        Dictionary with all service configurations
    """
    return {
        "postgres": postgres_service,
        "timescaledb": timescaledb_service,
        "redis": redis_service,
        "opa": opa_service,
        "grpc_mock": grpc_mock_service,
    }


# =============================================================================
# Database Initialization Fixtures
# =============================================================================

@pytest.fixture
async def initialized_db(postgres_connection):
    """
    Provide a PostgreSQL connection with initialized schema.

    This fixture creates all necessary tables for testing.
    """
    async with postgres_connection.acquire() as conn:
        # Create tables (simplified - in real implementation use Alembic)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS mcp_servers (
                id UUID PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                transport VARCHAR(50),
                endpoint VARCHAR(500),
                sensitivity_level VARCHAR(50),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS policies (
                id UUID PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                policy_type VARCHAR(50),
                status VARCHAR(50) DEFAULT 'active',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                full_name VARCHAR(255),
                hashed_password VARCHAR(255),
                role VARCHAR(50),
                is_active BOOLEAN DEFAULT TRUE,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)

    yield postgres_connection

    # Cleanup after tests
    async with postgres_connection.acquire() as conn:
        await conn.execute("DROP TABLE IF EXISTS mcp_servers CASCADE")
        await conn.execute("DROP TABLE IF EXISTS policies CASCADE")
        await conn.execute("DROP TABLE IF EXISTS users CASCADE")


@pytest.fixture
async def clean_redis(redis_connection):
    """
    Provide Redis connection and flush before/after tests.
    """
    # Clean before test
    await redis_connection.flushdb()

    yield redis_connection

    # Clean after test
    await redis_connection.flushdb()
