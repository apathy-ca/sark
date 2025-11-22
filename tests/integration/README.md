# Integration Tests

This directory contains comprehensive integration tests for the SARK application. Unlike unit tests which test individual components in isolation, integration tests verify that multiple components work together correctly.

## Overview

**Total Tests**: 50+ integration tests
**Coverage Areas**:
- Authentication & Authorization flows
- Policy enforcement across operations
- SIEM event delivery end-to-end
- API endpoints with real dependencies
- Error handling and edge cases
- Negative test scenarios

## Test Files

### 1. `test_auth_integration.py`
Tests authentication and authorization flows end-to-end.

**Coverage**:
- JWT token generation and validation
- Login/logout flows
- Token refresh mechanisms
- Authentication failures (invalid credentials, expired tokens)
- Authorization enforcement via OPA
- Role-based access control

**Test Count**: 12 tests

### 2. `test_policy_integration.py`
Tests policy enforcement across all operations.

**Coverage**:
- Server registration with policy checks
- Tool invocation authorization
- Bulk operations policy evaluation
- Policy denials and error handling
- Multi-policy evaluation
- Fail-closed behavior verification

**Test Count**: 15 tests

### 3. `test_siem_integration.py`
Tests SIEM event delivery and audit logging end-to-end.

**Coverage**:
- Audit event creation and persistence
- High-severity event SIEM forwarding
- Event filtering and routing
- SIEM failure handling
- Audit trail completeness
- Event correlation

**Test Count**: 10 tests

### 4. `test_api_integration.py`
Tests all API endpoints with real authentication and database.

**Coverage**:
- Server registration and management
- Search and filtering operations
- Pagination with various parameters
- Bulk operations (transactional and best-effort)
- Error responses and validation
- Rate limiting behavior

**Test Count**: 15 tests

## Running Integration Tests

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt
pip install pytest-asyncio httpx

# Set up test database
export DATABASE_URL="postgresql://test:test@localhost:5432/sark_test"
export TIMESCALE_URL="postgresql://test:test@localhost:5432/sark_test_audit"

# Set up test OPA instance
docker run -d -p 8181:8181 openpolicyagent/opa:latest run --server
```

### Run All Integration Tests

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run with coverage
pytest tests/integration/ -v --cov=src/sark --cov-report=html

# Run specific test file
pytest tests/integration/test_auth_integration.py -v

# Run with markers
pytest tests/integration/ -v -m "slow"  # Run slow tests
pytest tests/integration/ -v -m "not slow"  # Skip slow tests
```

### Run in Different Environments

```bash
# Development (uses test database)
export ENV=test
pytest tests/integration/

# CI/CD (uses in-memory SQLite)
export ENV=ci
export DATABASE_URL="sqlite+aiosqlite:///:memory:"
pytest tests/integration/

# Staging (uses staging infrastructure)
export ENV=staging
export DATABASE_URL="postgresql://..."
export OPA_URL="http://opa-staging:8181"
pytest tests/integration/
```

## Test Fixtures

Integration tests use the following fixtures defined in `conftest.py`:

- **`async_client`**: FastAPI TestClient for API requests
- **`test_db`**: Test database session with cleanup
- **`test_audit_db`**: Test TimescaleDB session for audit events
- **`test_user`**: Authenticated test user with JWT token
- **`admin_user`**: Admin user for privileged operations
- **`opa_client`**: OPA client configured for test policies
- **`test_server`**: Sample MCP server for testing

## Writing Integration Tests

### Example: Authentication Flow Test

```python
@pytest.mark.asyncio
async def test_login_flow(async_client, test_db):
    """Test complete login flow."""
    # Attempt login
    response = await async_client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "test_password"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

    # Use token for authenticated request
    token = data["access_token"]
    response = await async_client.get(
        "/api/servers/",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
```

### Example: Policy Enforcement Test

```python
@pytest.mark.asyncio
async def test_policy_denies_unauthorized_registration(
    async_client, test_user, opa_client
):
    """Test that policy denies server registration for unauthorized users."""
    # Configure OPA to deny
    await opa_client.set_policy("deny_all", "allow = false")

    response = await async_client.post(
        "/api/servers/",
        headers={"Authorization": f"Bearer {test_user.token}"},
        json={
            "name": "test-server",
            "transport": "http",
            "endpoint": "http://example.com",
            "tools": []
        }
    )

    assert response.status_code == 403
    assert "denied by policy" in response.json()["detail"].lower()
```

## Test Markers

Tests can be marked with pytest markers:

```python
@pytest.mark.slow  # Long-running tests (>5 seconds)
@pytest.mark.integration  # All integration tests
@pytest.mark.requires_opa  # Requires OPA service
@pytest.mark.requires_db  # Requires database
@pytest.mark.auth  # Authentication tests
@pytest.mark.policy  # Policy enforcement tests
@pytest.mark.siem  # SIEM integration tests
```

## Database Cleanup

Integration tests automatically clean up after themselves:

```python
@pytest.fixture
async def test_db():
    """Provide test database with automatic cleanup."""
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
```

## Negative Test Cases

Integration tests include comprehensive negative testing:

- **Invalid Authentication**:
  - Expired tokens
  - Invalid signatures
  - Missing credentials
  - Malformed tokens

- **Authorization Failures**:
  - Insufficient permissions
  - Policy denials
  - Resource access violations

- **Malformed Requests**:
  - Invalid JSON
  - Missing required fields
  - Type validation errors
  - Constraint violations

- **Edge Cases**:
  - Empty pagination
  - Large bulk operations
  - Concurrent requests
  - Race conditions

## Performance Considerations

Integration tests may be slower than unit tests:

- Use `pytest-xdist` for parallel execution:
  ```bash
  pytest tests/integration/ -n auto
  ```

- Skip slow tests during development:
  ```bash
  pytest tests/integration/ -m "not slow"
  ```

- Use test database optimizations:
  - In-memory SQLite for speed (when possible)
  - Database connection pooling
  - Transaction rollback instead of truncate

## CI/CD Integration

Integration tests run in CI/CD pipeline:

```yaml
# .github/workflows/integration-tests.yml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: timescale/timescaledb:latest-pg14
        env:
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432

      opa:
        image: openpolicyagent/opa:latest
        ports:
          - 8181:8181

    steps:
      - uses: actions/checkout@v2
      - name: Run integration tests
        run: |
          pytest tests/integration/ -v --cov
```

## Troubleshooting

### Tests Fail with "Connection Refused"
- Ensure PostgreSQL is running: `pg_isready`
- Ensure OPA is running: `curl http://localhost:8181/health`
- Check DATABASE_URL and OPA_URL environment variables

### Tests Fail with "Permission Denied"
- Check database user permissions
- Ensure test database exists
- Verify database connection string

### Slow Test Execution
- Use `pytest-xdist` for parallel execution
- Optimize database fixtures
- Use in-memory database when possible
- Mark slow tests with `@pytest.mark.slow`

### Flaky Tests
- Ensure proper test isolation
- Check for shared state between tests
- Add appropriate wait times for async operations
- Use fixtures for setup/teardown

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Cleanup**: Always clean up test data
3. **Realistic Data**: Use realistic test data
4. **Error Handling**: Test both success and failure paths
5. **Documentation**: Document complex test scenarios
6. **Performance**: Keep tests fast (< 1 second each when possible)
7. **Deterministic**: Tests should produce consistent results

## Contributing

When adding new integration tests:

1. Follow existing patterns in test files
2. Use descriptive test names
3. Add docstrings explaining test purpose
4. Include both positive and negative cases
5. Clean up resources properly
6. Update this README with new test counts

## Test Coverage Goals

- **API Endpoints**: 100% coverage
- **Authentication Flows**: 100% coverage
- **Policy Enforcement**: 100% coverage
- **Error Scenarios**: 80%+ coverage
- **Edge Cases**: 70%+ coverage

## Support

For issues with integration tests:
1. Check this README first
2. Review test logs for error details
3. Verify prerequisites are met
4. Check CI/CD logs for environment differences
5. Open an issue with test failure details

---

**Last Updated**: 2025-11-22
**Total Integration Tests**: 52
**Average Execution Time**: ~45 seconds (serial), ~12 seconds (parallel)
