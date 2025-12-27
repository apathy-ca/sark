# SARK Integration Testing Guide

This guide covers testing strategies, test execution, and best practices for SARK.

---

## Table of Contents

1. [Test Structure](#test-structure)
2. [Prerequisites](#prerequisites)
3. [Running Tests](#running-tests)
4. [End-to-End Scenarios](#end-to-end-scenarios)
5. [CI/CD Integration](#cicd-integration)
6. [Troubleshooting](#troubleshooting)

---

## Test Structure

```
tests/
├── unit/                       # Unit tests
├── integration/                # Integration tests
├── test_auth/                  # Authentication tests
│   ├── test_auth_integration.py
│   └── test_api_keys.py
├── test_api/                   # API endpoint tests
├── test_services/              # Service layer tests
├── benchmarks/                 # Performance benchmarks
│   ├── test_end_to_end_performance.py
│   ├── test_policy_cache_performance.py
│   └── test_tool_sensitivity_performance.py
├── load_testing/               # Load tests
│   ├── test_siem_load.py
│   └── test_siem_batch_load.py
├── performance/                # Performance tests
│   ├── test_pagination_performance.py
│   └── test_search_performance.py
├── test_bulk_operations.py
├── test_pagination.py
├── test_search.py
└── conftest.py                # Shared fixtures
```

---

## Prerequisites

### 1. Install Dependencies

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Or install specific packages
pip install pytest pytest-asyncio pytest-cov httpx
```

### 2. Start Services

SARK integration tests require running services:

```bash
# Using Docker Compose
docker-compose up -d postgres redis opa

# Or individually
docker run -d --name postgres -p 5432:5432 -e POSTGRES_PASSWORD=sark postgres:15
docker run -d --name redis -p 6379:6379 redis:7-alpine
docker run -d --name opa -p 8181:8181 openpolicyagent/opa:latest run --server
```

### 3. Set Environment Variables

```bash
# .env.test
export POSTGRES_DSN=postgresql+asyncpg://sark:sark@localhost:5432/sark_test
export VALKEY_DSN=redis://localhost:6379/1
export OPA_URL=http://localhost:8181
export JWT_SECRET_KEY=test-secret-key-for-testing-only
```

### 4. Initialize Test Database

```bash
# Run migrations
alembic upgrade head

# Or use test setup script
python scripts/setup_test_db.py
```

---

## Running Tests

### All Tests

```bash
# Run all tests
pytest

# With verbose output
pytest -v

# With coverage
pytest --cov=sark --cov-report=html

# Parallel execution (faster)
pytest -n auto
```

### Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Authentication tests
pytest tests/test_auth/

# Performance benchmarks
pytest tests/benchmarks/

# Load tests (slower)
pytest tests/load_testing/
```

### Specific Test Files

```bash
# Single file
pytest tests/test_bulk_operations.py

# Specific test
pytest tests/test_bulk_operations.py::test_bulk_register_servers

# Tests matching pattern
pytest -k "bulk"
```

### Watch Mode

```bash
# Re-run tests on file changes
pytest-watch

# Or use pytest-xdist
pytest --looponfail
```

---

## End-to-End Scenarios

### Scenario 1: Complete Authentication Flow

**Test**: LDAP Login → Token Refresh → API Access → Logout

```python
# File: tests/integration/test_e2e_auth.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_complete_auth_flow(api_client: AsyncClient):
    # Step 1: LDAP Login
    login_response = await api_client.post(
        "/api/v1/auth/login/ldap",
        json={"username": "test_user", "password": "password"}
    )
    assert login_response.status_code == 200

    tokens = login_response.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    # Step 2: Access Protected Endpoint
    headers = {"Authorization": f"Bearer {access_token}"}
    servers_response = await api_client.get("/api/v1/servers", headers=headers)
    assert servers_response.status_code == 200

    # Step 3: Refresh Token
    refresh_response = await api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 200

    new_access_token = refresh_response.json()["access_token"]

    # Step 4: Logout (Revoke)
    revoke_response = await api_client.post(
        "/api/v1/auth/revoke",
        headers={"Authorization": f"Bearer {new_access_token}"},
        json={"refresh_token": refresh_token}
    )
    assert revoke_response.status_code == 200
```

### Scenario 2: Server Registration with Policy

**Test**: Auth → Policy Check → Register Server → Audit Log

```python
@pytest.mark.asyncio
async def test_server_registration_flow(api_client: AsyncClient, auth_headers):
    # Step 1: Evaluate Policy
    policy_response = await api_client.post(
        "/api/v1/policy/evaluate",
        headers=auth_headers,
        json={
            "action": "server:register",
            "parameters": {"sensitivity_level": "high"}
        }
    )
    assert policy_response.json()["decision"] == "allow"

    # Step 2: Register Server
    server_data = {
        "name": "test-server",
        "transport": "http",
        "endpoint": "http://localhost:8080",
        "capabilities": ["tools"],
        "tools": [],
        "sensitivity_level": "high"
    }

    register_response = await api_client.post(
        "/api/v1/servers",
        headers=auth_headers,
        json=server_data
    )
    assert register_response.status_code == 201

    server_id = register_response.json()["server_id"]

    # Step 3: Verify Audit Log
    # (Would check audit database or API)
```

### Scenario 3: Bulk Operations with Transactions

**Test**: Bulk Register → Status Update → SIEM Forwarding

```python
@pytest.mark.asyncio
async def test_bulk_operations_flow(api_client: AsyncClient, auth_headers):
    # Step 1: Bulk Register Servers
    servers = [
        {"name": f"server-{i}", "transport": "http", ...}
        for i in range(10)
    ]

    bulk_response = await api_client.post(
        "/api/v1/bulk/servers/register",
        headers=auth_headers,
        json={"servers": servers, "fail_on_first_error": False}
    )

    result = bulk_response.json()
    assert result["succeeded"] == 10
    assert result["failed"] == 0

    # Step 2: Bulk Update Status
    server_ids = [item["server_id"] for item in result["succeeded_items"]]

    update_response = await api_client.patch(
        "/api/v1/bulk/servers/status",
        headers=auth_headers,
        json={
            "updates": [
                {"server_id": sid, "status": "active"}
                for sid in server_ids
            ],
            "fail_on_first_error": False
        }
    )

    assert update_response.json()["succeeded"] == 10
```

### Scenario 4: Search and Filter

**Test**: Register Servers → Search → Filter → Paginate

```python
@pytest.mark.asyncio
async def test_search_and_filter_flow(api_client: AsyncClient, auth_headers):
    # Setup: Register test servers
    # ...

    # Test 1: Full-text search
    search_response = await api_client.get(
        "/api/v1/servers?search=analytics",
        headers=auth_headers
    )
    assert len(search_response.json()["items"]) > 0

    # Test 2: Filter by sensitivity
    filter_response = await api_client.get(
        "/api/v1/servers?sensitivity=high,critical",
        headers=auth_headers
    )
    items = filter_response.json()["items"]
    assert all(s["sensitivity_level"] in ["high", "critical"] for s in items)

    # Test 3: Pagination
    page1 = await api_client.get(
        "/api/v1/servers?limit=10",
        headers=auth_headers
    )
    assert len(page1.json()["items"]) <= 10

    if page1.json()["has_more"]:
        cursor = page1.json()["next_cursor"]
        page2 = await api_client.get(
            f"/api/v1/servers?limit=10&cursor={cursor}",
            headers=auth_headers
        )
        assert page2.status_code == 200
```

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: sark
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      opa:
        image: openpolicyagent/opa:latest
        options: >-
          --health-cmd "wget -q -O- http://localhost:8181/health || exit 1"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run migrations
        run: alembic upgrade head
        env:
          POSTGRES_DSN: postgresql+asyncpg://sark:sark@postgres:5432/sark_test

      - name: Run tests
        run: pytest --cov=sark --cov-report=xml
        env:
          POSTGRES_DSN: postgresql+asyncpg://sark:sark@postgres:5432/sark_test
          VALKEY_DSN: redis://redis:6379/1
          OPA_URL: http://opa:8181

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

### Test Coverage Requirements

```bash
# Fail if coverage below threshold
pytest --cov=sark --cov-fail-under=80

# Generate HTML report
pytest --cov=sark --cov-report=html

# View report
open htmlcov/index.html
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
```

---

## Troubleshooting

### Test Failures

#### Database Connection Errors

**Error**: `asyncpg.exceptions.CannotConnectNowError`

**Solution**:
```bash
# Verify PostgreSQL is running
docker ps | grep postgres

# Check connection
psql -h localhost -U sark -d sark_test

# Recreate test database
dropdb sark_test && createdb sark_test
alembic upgrade head
```

#### Redis Connection Errors

**Error**: `redis.exceptions.ConnectionError`

**Solution**:
```bash
# Verify Redis is running
docker ps | grep redis

# Test connection
redis-cli -h localhost ping

# Restart Redis
docker restart redis
```

#### OPA Connection Errors

**Error**: `httpx.ConnectError`

**Solution**:
```bash
# Verify OPA is running
curl http://localhost:8181/health

# Restart OPA
docker restart opa
```

### Slow Tests

```bash
# Identify slow tests
pytest --durations=10

# Run only fast tests
pytest -m "not slow"

# Use markers in tests
@pytest.mark.slow
def test_expensive_operation():
    ...
```

### Flaky Tests

```bash
# Rerun failed tests
pytest --lf  # Last failed

# Retry failed tests
pytest --reruns 3

# Show warnings
pytest -W all
```

### Debug Mode

```bash
# Drop into debugger on failure
pytest --pdb

# Show print statements
pytest -s

# Very verbose
pytest -vv
```

---

## Best Practices

### 1. Test Organization

- **One test per behavior**
- **Clear test names**: `test_<action>_<expected_result>`
- **Arrange-Act-Assert pattern**

```python
def test_server_registration_succeeds_with_valid_data():
    # Arrange
    server_data = {"name": "test-server", ...}

    # Act
    response = api_client.post("/api/v1/servers", json=server_data)

    # Assert
    assert response.status_code == 201
    assert response.json()["server_id"] is not None
```

### 2. Fixtures

```python
# conftest.py
@pytest.fixture
async def api_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
async def auth_headers(api_client):
    # Login and return headers
    response = await api_client.post("/api/v1/auth/login/ldap", ...)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

### 3. Test Data

```python
# Use factories
from tests.factories import ServerFactory

def test_with_test_data():
    server = ServerFactory.build()
    assert server.name is not None
```

### 4. Cleanup

```python
@pytest.fixture(autouse=True)
async def cleanup_database(db_session):
    yield
    # Cleanup after each test
    await db_session.rollback()
```

---

## Performance Testing

### Benchmarks

```bash
# Run performance benchmarks
pytest tests/benchmarks/ -v

# With profiling
pytest tests/benchmarks/ --profile

# Generate report
pytest tests/benchmarks/ --benchmark-only --benchmark-autosave
```

### Load Testing

```bash
# SIEM load test
pytest tests/load_testing/test_siem_load.py

# Pagination performance
pytest tests/performance/test_pagination_performance.py
```

**Target Performance:**
- API endpoints: <100ms P95
- Policy evaluation: <50ms P95
- Cache hit: <5ms P95
- Database queries: <10ms P95

---

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [GitHub Actions](https://docs.github.com/actions)
- [Code Coverage](https://coverage.readthedocs.io/)
