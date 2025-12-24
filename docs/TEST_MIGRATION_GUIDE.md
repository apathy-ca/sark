# Integration Test Migration Guide

## Overview

This guide helps you migrate existing integration tests from using mocks to using real Docker services. This improves test reliability and gets us to 90%+ pass rate.

## Quick Start

### Before: Using Mocks

```python
"""Old integration test using mocks."""

import pytest
from unittest.mock import MagicMock, AsyncMock

@pytest.fixture
async def mock_db():
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock())
    return session

@pytest.mark.asyncio
async def test_create_server(mock_db):
    # Test uses mocked database
    await mock_db.execute("INSERT ...")
    # Assertions on mocks
```

### After: Using Docker Services

```python
"""New integration test using Docker services."""

import pytest

# Enable Docker fixtures
pytest_plugins = ["tests.fixtures.integration_docker"]

@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_server(postgres_connection):
    # Test uses REAL PostgreSQL database
    async with postgres_connection.acquire() as conn:
        result = await conn.execute("""
            INSERT INTO servers (name, endpoint)
            VALUES ($1, $2)
        """, "test", "http://test.com")
        # Real database assertions
```

## Step-by-Step Migration

### Step 1: Add Docker Fixtures Import

Add this line at the top of your test file:

```python
pytest_plugins = ["tests.fixtures.integration_docker"]
```

### Step 2: Replace Mock Fixtures

#### Database Fixtures

**Before:**
```python
@pytest.fixture
async def test_db():
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    yield session
```

**After:**
```python
# Remove the fixture - use postgres_connection instead

@pytest.mark.asyncio
async def test_something(postgres_connection):
    async with postgres_connection.acquire() as conn:
        # Use real database
        await conn.execute("...")
```

#### Redis Fixtures

**Before:**
```python
@pytest.fixture
def mock_redis():
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    return redis
```

**After:**
```python
# Remove the fixture - use redis_connection or clean_redis

@pytest.mark.asyncio
async def test_something(clean_redis):
    # Use real Redis
    await clean_redis.set("key", "value")
    value = await clean_redis.get("key")
    assert value == "value"
```

#### OPA Fixtures

**Before:**
```python
@pytest.fixture
def mock_opa():
    client = MagicMock()
    client.evaluate_policy = AsyncMock(return_value={"allow": True})
    return client
```

**After:**
```python
# Remove the fixture - use opa_client

def test_something(opa_client):
    # Use real OPA server
    assert opa_client.opa_url == "http://localhost:8181"
```

### Step 3: Update Test Logic

#### Update Database Operations

**Before (with mocks):**
```python
@pytest.mark.asyncio
async def test_create_user(mock_db):
    user = User(id=uuid4(), email="test@example.com")
    mock_db.add(user)
    await mock_db.commit()

    # Assert on mock calls
    mock_db.add.assert_called_once()
```

**After (with real DB):**
```python
@pytest.mark.asyncio
async def test_create_user(postgres_connection):
    async with postgres_connection.acquire() as conn:
        user_id = uuid4()
        await conn.execute("""
            INSERT INTO users (id, email, full_name)
            VALUES ($1, $2, $3)
        """, user_id, "test@example.com", "Test User")

        # Assert on real data
        result = await conn.fetchrow(
            "SELECT * FROM users WHERE id = $1",
            user_id
        )
        assert result["email"] == "test@example.com"
```

#### Update Cache Operations

**Before (with mocks):**
```python
@pytest.mark.asyncio
async def test_cache_policy(mock_redis):
    await mock_redis.set("policy:123", "cached_value")
    mock_redis.set.assert_called_once()
```

**After (with real Redis):**
```python
@pytest.mark.asyncio
async def test_cache_policy(clean_redis):
    await clean_redis.set("policy:123", "cached_value")

    # Verify actual cached value
    value = await clean_redis.get("policy:123")
    assert value == "cached_value"
```

### Step 4: Add Integration Test Marker

Add `@pytest.mark.integration` to all tests using Docker services:

```python
@pytest.mark.integration  # Add this marker
@pytest.mark.asyncio
async def test_something(postgres_connection):
    # Test code
```

This allows filtering:
```bash
# Run only integration tests
pytest -m integration

# Skip integration tests
pytest -m "not integration"
```

## Common Migration Patterns

### Pattern 1: Database Queries

**Before:**
```python
@pytest.mark.asyncio
async def test_query(mock_db):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [server1, server2]
    mock_db.execute.return_value = mock_result

    result = await service.get_servers(mock_db)
    assert len(result) == 2
```

**After:**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_query(postgres_connection):
    # Insert test data
    async with postgres_connection.acquire() as conn:
        await conn.execute("INSERT INTO servers ...")

        # Execute real query
        results = await conn.fetch("SELECT * FROM servers")
        assert len(results) == 2
```

### Pattern 2: Transaction Testing

**Before:**
```python
@pytest.mark.asyncio
async def test_transaction(mock_db):
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()

    # Test logic
    await mock_db.rollback()
    mock_db.rollback.assert_called_once()
```

**After:**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_transaction(postgres_connection):
    async with postgres_connection.acquire() as conn:
        async with conn.transaction():
            await conn.execute("INSERT ...")

            # Transaction automatically rolled back if exception
            # Or committed if successful
```

### Pattern 3: Cache Testing

**Before:**
```python
@pytest.mark.asyncio
async def test_cache_hit(mock_redis):
    mock_redis.get.return_value = "cached_value"

    result = await service.get_from_cache(mock_redis, "key")
    assert result == "cached_value"
```

**After:**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_hit(clean_redis):
    # Set up cache
    await clean_redis.set("key", "cached_value")

    # Test cache hit
    result = await clean_redis.get("key")
    assert result == "cached_value"
```

### Pattern 4: Policy Evaluation

**Before:**
```python
def test_policy(mock_opa):
    mock_opa.evaluate_policy.return_value = {"allow": True}

    result = mock_opa.evaluate_policy("policy", {"user": "admin"})
    assert result["allow"] is True
```

**After:**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_policy(opa_client):
    # Test with real OPA server
    # (requires policies loaded in OPA container)
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{opa_client.opa_url}/v1/data/sark/allow",
            json={"input": {"user": "admin", "action": "read"}}
        )
        assert response.status_code == 200
```

## Checklist for Each Test File

- [ ] Add `pytest_plugins = ["tests.fixtures.integration_docker"]` at top
- [ ] Replace mock fixtures with Docker fixtures
- [ ] Update test logic to use real services
- [ ] Add `@pytest.mark.integration` marker
- [ ] Remove unnecessary mock imports
- [ ] Update assertions to verify real data
- [ ] Test locally with `./scripts/run_integration_tests.sh test`
- [ ] Verify test passes consistently

## Example: Complete Migration

### Before (test_api_integration.py)

```python
"""Integration tests - OLD VERSION with mocks."""

from unittest.mock import AsyncMock, MagicMock
import pytest

@pytest.fixture
async def mock_db():
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session

@pytest.fixture
def mock_redis():
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    return redis

@pytest.mark.asyncio
async def test_create_server(mock_db, mock_redis):
    # Test with mocks
    mock_db.execute.return_value = MagicMock()
    await mock_db.commit()
    mock_db.commit.assert_called_once()
```

### After (test_api_integration.py)

```python
"""Integration tests - NEW VERSION with Docker services."""

import pytest
from uuid import uuid4

# Enable Docker fixtures
pytest_plugins = ["tests.fixtures.integration_docker"]

@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_server(postgres_connection, clean_redis):
    """Test server creation with real database and cache."""
    server_id = uuid4()

    # Insert into real database
    async with postgres_connection.acquire() as conn:
        await conn.execute("""
            INSERT INTO mcp_servers (id, name, transport, endpoint, is_active)
            VALUES ($1, $2, $3, $4, $5)
        """, server_id, "test-server", "http", "http://test.com", True)

        # Verify in database
        result = await conn.fetchrow(
            "SELECT * FROM mcp_servers WHERE id = $1",
            server_id
        )
        assert result["name"] == "test-server"

    # Cache the server
    cache_key = f"server:{server_id}"
    await clean_redis.set(cache_key, "test-server")

    # Verify in cache
    cached = await clean_redis.get(cache_key)
    assert cached == "test-server"
```

## Running Migrated Tests

### Local Development

```bash
# Start services
./scripts/run_integration_tests.sh start

# Run your migrated tests
pytest tests/integration/test_api_integration.py -v

# Stop services
./scripts/run_integration_tests.sh stop
```

### Full Test Run

```bash
# Automated full run
./scripts/run_integration_tests.sh run
```

### CI/CD

Tests will automatically use Docker services in CI when pytest-docker is installed.

## Troubleshooting

### Issue: Test hangs waiting for services

**Solution:** Ensure Docker services are started:
```bash
./scripts/run_integration_tests.sh status
```

### Issue: Connection refused errors

**Solution:** Check service health:
```bash
./scripts/run_integration_tests.sh logs postgres
./scripts/run_integration_tests.sh logs redis
```

### Issue: Database tables don't exist

**Solution:** Use `initialized_db` fixture instead of `postgres_connection`:
```python
async def test_something(initialized_db):
    # Tables are created automatically
```

### Issue: Tests interfere with each other

**Solution:** Use `clean_redis` for Redis tests (auto-flush) or use transactions for database tests.

## Benefits of Migration

✅ **Real Integration Testing** - Tests actually integrate with services
✅ **Higher Confidence** - Catches real integration issues
✅ **Easier Debugging** - Can inspect real database/cache
✅ **Better Coverage** - Tests exercise actual code paths
✅ **CI/CD Ready** - Reproducible in any environment

## Migration Priority

Migrate tests in this order for maximum impact:

1. **High Priority** - Tests that are currently failing
2. **Medium Priority** - Core functionality tests (API, auth, policy)
3. **Low Priority** - Edge cases and specialized tests

## Getting Help

- Review example: `tests/integration/test_docker_infrastructure_example.py`
- Check documentation: `tests/README_INTEGRATION_TESTS.md`
- Test runner help: `./scripts/run_integration_tests.sh --help`
- Open an issue if stuck

## Summary

Migration Steps:
1. Add `pytest_plugins = ["tests.fixtures.integration_docker"]`
2. Replace mock fixtures with Docker fixtures
3. Update test logic for real services
4. Add `@pytest.mark.integration`
5. Test locally
6. Commit

**Goal:** Get integration test pass rate from 27% to 90%+ through reliable Docker-based testing!
