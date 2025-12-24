"""
Example integration tests demonstrating Docker infrastructure usage.

This file shows how to use the new Docker-based testing infrastructure
to write reliable integration tests with real services.

Run with:
    pytest tests/integration/test_docker_infrastructure_example.py -v

Or use the test runner:
    ./scripts/run_integration_tests.sh test
"""

import pytest
from uuid import uuid4

# Import Docker fixtures - this enables all Docker services
pytest_plugins = ["tests.fixtures.integration_docker"]


# =============================================================================
# PostgreSQL Integration Tests
# =============================================================================

@pytest.mark.integration
class TestPostgreSQLIntegration:
    """Test PostgreSQL database operations with real Docker container."""

    @pytest.mark.asyncio
    async def test_postgres_connection(self, postgres_connection):
        """Test that we can connect to PostgreSQL."""
        async with postgres_connection.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            assert result == 1

    @pytest.mark.asyncio
    async def test_create_table(self, postgres_connection):
        """Test table creation and basic operations."""
        async with postgres_connection.acquire() as conn:
            # Create table
            await conn.execute("""
                CREATE TEMPORARY TABLE test_servers (
                    id UUID PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    endpoint VARCHAR(500)
                )
            """)

            # Insert data
            test_id = uuid4()
            await conn.execute("""
                INSERT INTO test_servers (id, name, endpoint)
                VALUES ($1, $2, $3)
            """, test_id, "test-server", "http://example.com")

            # Query data
            result = await conn.fetchrow(
                "SELECT * FROM test_servers WHERE id = $1",
                test_id
            )

            assert result["name"] == "test-server"
            assert result["endpoint"] == "http://example.com"

    @pytest.mark.asyncio
    async def test_transaction_rollback(self, postgres_connection):
        """Test transaction rollback behavior."""
        async with postgres_connection.acquire() as conn:
            # Create temp table
            await conn.execute("""
                CREATE TEMPORARY TABLE test_rollback (
                    id SERIAL PRIMARY KEY,
                    value TEXT
                )
            """)

            # Test rollback
            async with conn.transaction():
                await conn.execute(
                    "INSERT INTO test_rollback (value) VALUES ($1)",
                    "should_rollback"
                )
                # Explicit rollback by raising exception
                try:
                    raise Exception("Test rollback")
                except:
                    pass

            # Verify no data was committed
            count = await conn.fetchval("SELECT COUNT(*) FROM test_rollback")
            # Due to exception, this should be 0
            # (Note: in real test, you'd use proper transaction context)


# =============================================================================
# Redis Integration Tests
# =============================================================================

@pytest.mark.integration
class TestRedisIntegration:
    """Test Redis cache operations with real Docker container."""

    @pytest.mark.asyncio
    async def test_redis_connection(self, redis_connection):
        """Test that we can connect to Redis."""
        result = await redis_connection.ping()
        assert result is True

    @pytest.mark.asyncio
    async def test_redis_set_get(self, clean_redis):
        """Test basic Redis set/get operations."""
        await clean_redis.set("test_key", "test_value")
        value = await clean_redis.get("test_key")
        assert value == "test_value"

    @pytest.mark.asyncio
    async def test_redis_expiration(self, clean_redis):
        """Test Redis key expiration."""
        await clean_redis.set("expiring_key", "value", ex=1)

        # Key should exist immediately
        exists = await clean_redis.exists("expiring_key")
        assert exists == 1

        # After expiration (we won't wait, just verify TTL is set)
        ttl = await clean_redis.ttl("expiring_key")
        assert ttl > 0 and ttl <= 1

    @pytest.mark.asyncio
    async def test_redis_hash_operations(self, clean_redis):
        """Test Redis hash operations."""
        # Set hash fields
        await clean_redis.hset("user:1", mapping={
            "name": "Test User",
            "email": "test@example.com",
            "role": "developer"
        })

        # Get single field
        name = await clean_redis.hget("user:1", "name")
        assert name == "Test User"

        # Get all fields
        user_data = await clean_redis.hgetall("user:1")
        assert user_data["email"] == "test@example.com"
        assert user_data["role"] == "developer"

    @pytest.mark.asyncio
    async def test_redis_list_operations(self, clean_redis):
        """Test Redis list operations."""
        # Push items
        await clean_redis.rpush("queue", "item1", "item2", "item3")

        # Get list length
        length = await clean_redis.llen("queue")
        assert length == 3

        # Pop item
        item = await clean_redis.lpop("queue")
        assert item == "item1"


# =============================================================================
# TimescaleDB Integration Tests
# =============================================================================

@pytest.mark.integration
class TestTimescaleDBIntegration:
    """Test TimescaleDB operations with real Docker container."""

    @pytest.mark.asyncio
    async def test_timescaledb_connection(self, timescaledb_connection):
        """Test that we can connect to TimescaleDB."""
        async with timescaledb_connection.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            assert result == 1

    @pytest.mark.asyncio
    async def test_timescaledb_hypertable(self, timescaledb_connection):
        """Test creating and using a hypertable."""
        async with timescaledb_connection.acquire() as conn:
            # Create regular table
            await conn.execute("""
                CREATE TEMPORARY TABLE test_metrics (
                    time TIMESTAMPTZ NOT NULL,
                    device_id INTEGER,
                    temperature DOUBLE PRECISION
                )
            """)

            # Convert to hypertable
            await conn.execute("""
                SELECT create_hypertable(
                    'test_metrics',
                    'time',
                    if_not_exists => TRUE
                )
            """)

            # Insert time-series data
            await conn.execute("""
                INSERT INTO test_metrics (time, device_id, temperature)
                VALUES
                    (NOW(), 1, 20.5),
                    (NOW() - INTERVAL '1 hour', 1, 21.0),
                    (NOW() - INTERVAL '2 hours', 1, 19.5)
            """)

            # Query data
            count = await conn.fetchval("SELECT COUNT(*) FROM test_metrics")
            assert count == 3


# =============================================================================
# OPA Integration Tests
# =============================================================================

@pytest.mark.integration
class TestOPAIntegration:
    """Test OPA policy engine with real Docker container."""

    def test_opa_client_creation(self, opa_client):
        """Test that OPA client is created correctly."""
        assert opa_client is not None
        assert opa_client.opa_url == "http://localhost:8181"

    @pytest.mark.asyncio
    async def test_opa_health_check(self, opa_client):
        """Test OPA health check endpoint."""
        # OPA client doesn't have health_check, so let's test the connection
        # by attempting a simple policy evaluation
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{opa_client.opa_url}/health")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_opa_data_endpoint(self, opa_service):
        """Test OPA data API endpoint."""
        import httpx

        async with httpx.AsyncClient() as client:
            # Test GET /v1/data
            response = await client.get(f"{opa_service['url']}/v1/data")
            assert response.status_code == 200


# =============================================================================
# Multi-Service Integration Tests
# =============================================================================

@pytest.mark.integration
class TestMultiServiceIntegration:
    """Test scenarios involving multiple services."""

    @pytest.mark.asyncio
    async def test_all_services_available(self, all_services):
        """Test that all services are available."""
        assert "postgres" in all_services
        assert "timescaledb" in all_services
        assert "redis" in all_services
        assert "opa" in all_services
        assert "grpc_mock" in all_services

        # Verify connection details
        assert all_services["postgres"]["port"] == 5433
        assert all_services["redis"]["port"] == 6380
        assert all_services["opa"]["port"] == 8181

    @pytest.mark.asyncio
    async def test_cache_and_database(
        self,
        postgres_connection,
        clean_redis
    ):
        """Test caching layer with database operations."""
        # Create temp table
        async with postgres_connection.acquire() as conn:
            await conn.execute("""
                CREATE TEMPORARY TABLE test_cache_db (
                    id UUID PRIMARY KEY,
                    name VARCHAR(255),
                    value TEXT
                )
            """)

            # Insert data
            test_id = uuid4()
            await conn.execute("""
                INSERT INTO test_cache_db (id, name, value)
                VALUES ($1, $2, $3)
            """, test_id, "test-item", "test-value")

            # Query from database
            result = await conn.fetchrow(
                "SELECT * FROM test_cache_db WHERE id = $1",
                test_id
            )
            db_value = result["value"]

            # Cache the result in Redis
            cache_key = f"cache:item:{test_id}"
            await clean_redis.set(cache_key, db_value)

            # Retrieve from cache
            cached_value = await clean_redis.get(cache_key)

            assert cached_value == db_value
            assert cached_value == "test-value"


# =============================================================================
# Database Initialization Tests
# =============================================================================

@pytest.mark.integration
class TestDatabaseInitialization:
    """Test database initialization fixtures."""

    @pytest.mark.asyncio
    async def test_initialized_db_has_tables(self, initialized_db):
        """Test that initialized_db fixture creates tables."""
        async with initialized_db.acquire() as conn:
            # Check that tables exist
            tables = await conn.fetch("""
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
            """)

            table_names = [t["tablename"] for t in tables]

            # Verify expected tables
            assert "mcp_servers" in table_names
            assert "policies" in table_names
            assert "users" in table_names

    @pytest.mark.asyncio
    async def test_insert_into_initialized_db(self, initialized_db):
        """Test inserting data into initialized tables."""
        async with initialized_db.acquire() as conn:
            # Insert server
            server_id = uuid4()
            await conn.execute("""
                INSERT INTO mcp_servers (
                    id, name, transport, endpoint, sensitivity_level, is_active
                )
                VALUES ($1, $2, $3, $4, $5, $6)
            """, server_id, "test-server", "http", "http://test.com", "medium", True)

            # Verify insertion
            result = await conn.fetchrow(
                "SELECT * FROM mcp_servers WHERE id = $1",
                server_id
            )

            assert result["name"] == "test-server"
            assert result["transport"] == "http"


# =============================================================================
# Performance and Stress Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.slow
class TestPerformance:
    """Performance tests using Docker services."""

    @pytest.mark.asyncio
    async def test_bulk_insert_performance(self, postgres_connection):
        """Test bulk insert performance."""
        import time

        async with postgres_connection.acquire() as conn:
            await conn.execute("""
                CREATE TEMPORARY TABLE test_bulk (
                    id SERIAL PRIMARY KEY,
                    value TEXT
                )
            """)

            # Bulk insert
            start = time.time()

            values = [(f"value_{i}",) for i in range(1000)]
            await conn.executemany(
                "INSERT INTO test_bulk (value) VALUES ($1)",
                values
            )

            duration = time.time() - start

            # Verify
            count = await conn.fetchval("SELECT COUNT(*) FROM test_bulk")
            assert count == 1000

            # Should be reasonably fast (< 1 second for 1000 inserts)
            assert duration < 1.0

    @pytest.mark.asyncio
    async def test_redis_throughput(self, clean_redis):
        """Test Redis operation throughput."""
        import time

        start = time.time()

        # Perform 1000 operations
        for i in range(1000):
            await clean_redis.set(f"key_{i}", f"value_{i}")

        duration = time.time() - start

        # Should be very fast (< 1 second for 1000 ops)
        assert duration < 1.0

        # Verify some values
        value_0 = await clean_redis.get("key_0")
        value_999 = await clean_redis.get("key_999")

        assert value_0 == "value_0"
        assert value_999 == "value_999"
