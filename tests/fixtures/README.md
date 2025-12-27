# SARK Test Fixtures Documentation

**Last Updated**: December 26, 2025
**SARK Version**: 1.3.0

---

## Overview

This directory contains reusable pytest fixtures for SARK integration and unit testing. The fixtures provide:

- **Docker-based integration test infrastructure** (PostgreSQL, TimescaleDB, Valkey, OPA, gRPC Mock)
- **Database connections** (async and sync)
- **Service clients** (OPA, Valkey, Gateway)
- **Test data factories**
- **Cleanup utilities**

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Available Fixtures](#available-fixtures)
3. [Docker Integration Fixtures](#docker-integration-fixtures)
4. [Database Fixtures](#database-fixtures)
5. [Service Fixtures](#service-fixtures)
6. [Usage Examples](#usage-examples)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

```bash
# Install test dependencies
pip install -e ".[test]"

# Ensure Docker is running
docker --version
docker compose version
```

### Running Integration Tests

```bash
# Start integration test infrastructure
docker compose -f tests/fixtures/docker-compose.integration.yml up -d

# Run integration tests
pytest tests/integration/ -v

# Cleanup
docker compose -f tests/fixtures/docker-compose.integration.yml down
```

### Using Fixtures in Tests

```python
import pytest

@pytest.mark.asyncio
async def test_with_database(postgres_connection):
    """Test using PostgreSQL connection fixture."""
    async with postgres_connection.acquire() as conn:
        result = await conn.fetchval("SELECT 1")
        assert result == 1

@pytest.mark.asyncio
async def test_with_valkey(valkey_connection):
    """Test using Valkey (cache) connection fixture."""
    await valkey_connection.set("key", "value")
    result = await valkey_connection.get("key")
    assert result == "value"

def test_with_opa(opa_client):
    """Test using OPA client fixture."""
    decision = opa_client.evaluate_policy(
        policy_path="/v1/data/mcp/allow",
        input_data={"user": "test"}
    )
    assert decision.allowed is not None
```

---

## Available Fixtures

### Docker Service Fixtures (Session-scoped)

| Fixture | Type | Scope | Description |
|---------|------|-------|-------------|
| `docker_compose_file` | str | session | Path to docker-compose.integration.yml |
| `docker_cleanup` | str | session | Docker cleanup behavior ("down" or "keep") |
| `postgres_service` | dict | session | PostgreSQL service configuration |
| `timescaledb_service` | dict | session | TimescaleDB service configuration |
| `valkey_service` | dict | session | Valkey (cache) service configuration |
| `opa_service` | dict | session | OPA service configuration |
| `grpc_mock_service` | dict | session | gRPC mock server configuration |
| `all_services` | dict | session | All services combined |

### Database Connection Fixtures (Function-scoped)

| Fixture | Type | Scope | Description |
|---------|------|-------|-------------|
| `postgres_connection` | asyncpg.Pool | function | Async PostgreSQL connection pool |
| `timescaledb_connection` | asyncpg.Pool | function | Async TimescaleDB connection pool |
| `valkey_connection` | valkey.asyncio.Valkey | function | Async Valkey client |
| `initialized_db` | asyncpg.Pool | function | PostgreSQL with schema initialized |
| `clean_valkey` | valkey.asyncio.Valkey | function | Valkey with flushed database |

### Service Client Fixtures (Function-scoped)

| Fixture | Type | Scope | Description |
|---------|------|-------|-------------|
| `opa_client` | OPAClient | function | OPA policy evaluation client |

---

## Docker Integration Fixtures

### File: `integration_docker.py`

Provides Docker-based integration test infrastructure using `pytest-docker`.

#### PostgreSQL Fixtures

**`postgres_service`** (session-scoped)
- **Returns**: `dict` with connection details
- **Keys**: `host`, `port`, `database`, `user`, `password`, `connection_string`
- **Port**: 5433 (to avoid conflicts)
- **Container**: `sark_test_postgres`

**`postgres_connection`** (function-scoped)
- **Returns**: `asyncpg.Pool` with 1-5 connections
- **Usage**: For tests requiring async database access
- **Cleanup**: Pool closed automatically after test

```python
@pytest.mark.asyncio
async def test_database_query(postgres_connection):
    async with postgres_connection.acquire() as conn:
        result = await conn.fetchval("SELECT 1 + 1")
        assert result == 2
```

#### TimescaleDB Fixtures

**`timescaledb_service`** (session-scoped)
- **Returns**: `dict` with connection details
- **Database**: `sark_audit_test`
- **Port**: 5434
- **Container**: `sark_test_timescale`

**`timescaledb_connection`** (function-scoped)
- **Returns**: `asyncpg.Pool`
- **Usage**: For audit log testing with time-series data

#### Valkey (Cache) Fixtures

**`valkey_service`** (session-scoped)
- **Returns**: `dict` with connection details
- **Keys**: `host`, `port`, `url`
- **Port**: 6380
- **Container**: `sark_test_valkey`
- **Note**: Persistence disabled for faster tests

**`valkey_connection`** (function-scoped)
- **Returns**: `valkey.asyncio.Valkey` client
- **Decode Responses**: Enabled (returns strings, not bytes)
- **Cleanup**: Client closed automatically

```python
@pytest.mark.asyncio
async def test_cache(valkey_connection):
    await valkey_connection.set("foo", "bar", ex=60)
    value = await valkey_connection.get("foo")
    assert value == "bar"
```

**`clean_valkey`** (function-scoped)
- **Returns**: `valkey.asyncio.Valkey` client
- **Cleanup**: Database flushed before AND after test
- **Usage**: For tests requiring a clean cache state

#### OPA Fixtures

**`opa_service`** (session-scoped)
- **Returns**: `dict` with connection details
- **Keys**: `host`, `port`, `url`, `health_url`, `v1_data_url`
- **Port**: 8181
- **Container**: `sark_test_opa`
- **Policies**: Mounted from `opa/policies/` directory

**`opa_client`** (function-scoped)
- **Returns**: `OPAClient` instance
- **Usage**: For policy evaluation testing

```python
def test_policy_evaluation(opa_client):
    decision = opa_client.evaluate(
        policy_path="/v1/data/mcp/allow",
        input_data={"user": "admin", "resource": "server1"}
    )
    assert decision.allowed
```

#### gRPC Mock Server Fixtures

**`grpc_mock_service`** (session-scoped)
- **Returns**: `dict` with connection details
- **gRPC Port**: 50051
- **Admin Port**: 4771
- **Container**: `sark_test_grpc_mock`
- **Usage**: For testing gRPC adapters

#### Combined Fixtures

**`all_services`** (session-scoped)
- **Returns**: `dict` with all service configurations
- **Keys**: `postgres`, `timescaledb`, `valkey`, `opa`, `grpc_mock`
- **Usage**: For tests requiring multiple services

```python
def test_full_integration(all_services):
    postgres = all_services["postgres"]
    valkey = all_services["valkey"]
    opa = all_services["opa"]
    # Test cross-service functionality
```

---

## Database Fixtures

### Initialized Database

**`initialized_db`** (function-scoped)

Creates a PostgreSQL connection with schema initialized.

**Tables Created**:
- `mcp_servers` - MCP server registry
- `policies` - Policy definitions
- `users` - User accounts

**Usage**:
```python
@pytest.mark.asyncio
async def test_with_schema(initialized_db):
    async with initialized_db.acquire() as conn:
        # Tables already exist
        server_count = await conn.fetchval(
            "SELECT COUNT(*) FROM mcp_servers"
        )
        assert server_count == 0  # Empty but table exists
```

**Cleanup**: Tables dropped after test

---

## Service Fixtures

### Valkey (Cache) Client

**Fixture**: `valkey_connection`, `clean_valkey`

**Connection Details**:
- Host: Resolved from Docker service
- Port: 6380 (mapped from 6379)
- Decode Responses: True (strings, not bytes)

**API Examples**:
```python
# String operations
await valkey_connection.set("key", "value")
value = await valkey_connection.get("key")

# Set expiration
await valkey_connection.setex("key", 60, "value")  # 60s TTL

# Hash operations
await valkey_connection.hset("user:1", "name", "Alice")
name = await valkey_connection.hget("user:1", "name")

# List operations
await valkey_connection.lpush("queue", "task1", "task2")
task = await valkey_connection.rpop("queue")

# Check existence
exists = await valkey_connection.exists("key")

# Delete
await valkey_connection.delete("key")
```

### OPA Policy Client

**Fixture**: `opa_client`

**Connection Details**:
- URL: http://localhost:8181
- Policy Path: `/v1/data/mcp/allow` (default)

**API Examples**:
```python
# Evaluate policy
decision = opa_client.evaluate(
    policy_path="/v1/data/mcp/allow",
    input_data={
        "user": {"id": "user123", "role": "admin"},
        "resource": {"type": "server", "id": "srv-001"},
        "action": "read"
    }
)

if decision.allowed:
    # Access granted
    print(decision.reason)
else:
    # Access denied
    print(decision.denial_reason)
```

---

## Usage Examples

### Example 1: Database Integration Test

```python
import pytest
from uuid import uuid4

@pytest.mark.asyncio
async def test_user_crud(initialized_db):
    """Test user CRUD operations."""
    user_id = uuid4()

    async with initialized_db.acquire() as conn:
        # Create
        await conn.execute(
            """
            INSERT INTO users (id, email, full_name, role)
            VALUES ($1, $2, $3, $4)
            """,
            user_id, "alice@example.com", "Alice Smith", "admin"
        )

        # Read
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE id = $1", user_id
        )
        assert user["email"] == "alice@example.com"

        # Update
        await conn.execute(
            "UPDATE users SET role = $1 WHERE id = $2",
            "viewer", user_id
        )

        # Delete
        await conn.execute(
            "DELETE FROM users WHERE id = $1", user_id
        )
```

### Example 2: Cache Integration Test

```python
import pytest

@pytest.mark.asyncio
async def test_policy_caching(clean_valkey, opa_client):
    """Test policy result caching."""
    cache_key = "policy:user123:server1:read"

    # Check cache (should be empty)
    cached = await clean_valkey.get(cache_key)
    assert cached is None

    # Evaluate policy (cache miss)
    decision = opa_client.evaluate(
        policy_path="/v1/data/mcp/allow",
        input_data={"user": "user123", "resource": "server1"}
    )

    # Cache result
    await clean_valkey.setex(
        cache_key,
        300,  # 5 minutes
        "allowed" if decision.allowed else "denied"
    )

    # Check cache (should be populated)
    cached = await clean_valkey.get(cache_key)
    assert cached == "allowed"
```

### Example 3: Multi-Service Integration Test

```python
import pytest

@pytest.mark.asyncio
async def test_authorization_flow(
    initialized_db,
    valkey_connection,
    opa_client
):
    """Test complete authorization flow with caching."""
    user_id = "user123"
    server_id = "server1"
    cache_key = f"authz:{user_id}:{server_id}"

    # 1. Check cache
    cached_decision = await valkey_connection.get(cache_key)
    if cached_decision:
        decision = {"allowed": cached_decision == "true"}
    else:
        # 2. Evaluate with OPA
        decision = opa_client.evaluate(
            policy_path="/v1/data/mcp/allow",
            input_data={"user": user_id, "server": server_id}
        )

        # 3. Cache result
        await valkey_connection.setex(
            cache_key,
            60,
            "true" if decision.allowed else "false"
        )

    # 4. Log to database
    async with initialized_db.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO audit_log (user_id, server_id, allowed)
            VALUES ($1, $2, $3)
            """,
            user_id, server_id, decision.allowed
        )

    assert decision.allowed
```

---

## Troubleshooting

### Issue 1: Docker Containers Not Starting

**Symptom**:
```
Error: Cannot connect to Docker daemon
```

**Solution**:
```bash
# Check Docker is running
docker ps

# Start Docker (Linux)
sudo systemctl start docker

# Start Docker (macOS)
open -a Docker
```

### Issue 2: Port Conflicts

**Symptom**:
```
Error: Port 5433 is already allocated
```

**Solution**:
```bash
# Find process using port
lsof -i :5433

# Kill process or change port in docker-compose.integration.yml
```

### Issue 3: Valkey Connection Refused

**Symptom**:
```
valkey.exceptions.ConnectionError: Connection refused
```

**Solution**:
```bash
# Check Valkey is running
docker compose -f tests/fixtures/docker-compose.integration.yml ps cache

# Restart Valkey
docker compose -f tests/fixtures/docker-compose.integration.yml restart cache

# Check logs
docker compose -f tests/fixtures/docker-compose.integration.yml logs cache
```

### Issue 4: Database Initialization Failures

**Symptom**:
```
asyncpg.exceptions.DuplicateTableError: relation "users" already exists
```

**Solution**:
```bash
# Clean database
docker compose -f tests/fixtures/docker-compose.integration.yml down -v

# Restart with fresh volumes
docker compose -f tests/fixtures/docker-compose.integration.yml up -d
```

### Issue 5: pytest-docker Not Found

**Symptom**:
```
ModuleNotFoundError: No module named 'pytest_docker'
```

**Solution**:
```bash
# Install pytest-docker
pip install pytest-docker

# Or install all test dependencies
pip install -e ".[test]"
```

### Issue 6: Async Fixture Scope Warnings

**Symptom**:
```
ScopeMismatch: async fixture depends on session-scoped fixture
```

**Solution**:
- All async fixtures are now explicitly `scope="function"`
- Session-scoped fixtures are sync only
- This is the recommended pattern for pytest-asyncio

### Issue 7: Test Collection Errors

**Symptom**:
```
ImportError: cannot import name 'CircuitBreaker' from 'sark.gateway'
```

**Solution**:
```bash
# Reinstall package in editable mode
pip install -e . --force-reinstall

# Verify installation
pip show sark
```

---

## Best Practices

### 1. Fixture Scope

- **Session**: Docker services (expensive to create)
- **Function**: Database connections, cache clients (need cleanup)

### 2. Cleanup

- All async fixtures have explicit cleanup (close pools, flush cache)
- Database fixtures drop tables after tests
- Use `clean_valkey` for isolated cache tests

### 3. Performance

- Docker containers use `tmpfs` for PostgreSQL data (faster tests)
- Valkey persistence is disabled (`--save ""`)
- Connection pools sized for test workloads (1-5 connections)

### 4. Isolation

- Each test gets a fresh connection from the pool
- `clean_valkey` flushes database before/after
- `initialized_db` creates and drops tables

### 5. Parallel Testing

- Session-scoped fixtures are shared across workers
- Function-scoped fixtures are isolated per test
- Use `pytest-xdist` for parallel execution

```bash
# Run tests in parallel (4 workers)
pytest tests/integration/ -n 4
```

---

## Reference

- **pytest**: https://docs.pytest.org/
- **pytest-asyncio**: https://pytest-asyncio.readthedocs.io/
- **pytest-docker**: https://github.com/avast/pytest-docker
- **asyncpg**: https://magicstack.github.io/asyncpg/
- **valkey-py**: https://github.com/valkey-io/valkey-py

---

**Maintained by**: SARK Development Team
**Issues**: https://github.com/apathy-ca/sark/issues
**Version**: SARK v1.3.0
