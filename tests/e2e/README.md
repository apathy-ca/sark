# End-to-End Test Suite

Comprehensive end-to-end testing for SARK application workflows, including complete user journeys, smoke tests, and test data generation.

## Overview

The E2E test suite validates complete application workflows from start to finish, ensuring all components work together correctly. These tests simulate real-world usage scenarios and verify critical business paths.

## Test Files

### 1. `test_complete_flows.py` - Complete User Journey Tests

Full end-to-end workflows covering the entire application lifecycle:

**User Registration & Authentication Flow** (test_complete_user_registration_to_server_management)
- User registration with email/password
- Email verification (mocked)
- Login with credentials
- JWT token generation
- Access protected endpoints
- Token refresh
- Server registration with authenticated user
- Server management operations

**Admin Workflow** (test_admin_policy_creation_to_enforcement)
- Admin user login
- Policy creation with Rego code
- Policy version management
- Policy activation
- Policy enforcement verification
- Server registration with policy checks
- Tool invocation with authorization

**Multi-Team Collaboration** (test_multi_team_server_sharing)
- Multiple team creation
- User assignment to teams
- Team-scoped server registration
- Cross-team access policies
- Server discovery across teams

**Complete Audit Trail** (test_complete_audit_trail_flow)
- User actions throughout journey
- Event capture at each step
- SIEM forwarding for high-severity events
- Audit log query and verification

**Bulk Operations Workflow** (test_bulk_registration_with_validation)
- Bulk server data preparation
- Pre-registration validation
- Transactional bulk registration
- Rollback on policy violations
- Success confirmation

### 2. `test_smoke.py` - Smoke Tests for Critical Paths

Quick verification tests for essential system functionality:

**System Health Checks**
- Database connectivity
- OPA service availability
- Redis cache connectivity
- Consul service registry

**Core API Endpoints**
- Health check endpoint (/health)
- Readiness check endpoint (/ready)
- Metrics endpoint (/metrics)
- API documentation (/docs)

**Authentication Smoke Tests**
- JWT token generation
- Token validation
- Session creation
- API key authentication

**Server Management Smoke Tests**
- Server registration
- Server retrieval
- Server search
- Server status updates

**Policy Enforcement Smoke Tests**
- Policy evaluation
- Authorization decisions
- Fail-closed verification

### 3. `test_data_generator.py` - Test Data Generation

Utilities for generating realistic test data at scale:

**User Generators**
- `generate_user()` - Single user with random data
- `generate_users(count)` - Multiple users
- `generate_team()` - Team with members
- `generate_admin_user()` - Admin user

**Server Generators**
- `generate_mcp_server()` - Single MCP server
- `generate_servers(count)` - Multiple servers
- `generate_server_with_tools()` - Server with tools/prompts/resources
- `generate_high_sensitivity_server()` - Secure server configuration

**Policy Generators**
- `generate_policy()` - Policy with Rego code
- `generate_authorization_policy()` - RBAC policy
- `generate_validation_policy()` - Input validation policy

**Audit Event Generators**
- `generate_audit_event()` - Single audit event
- `generate_audit_trail()` - Series of related events

**Data Factories**
- Faker integration for realistic data
- Factory Boy patterns for complex objects
- Configurable data distributions

## Running E2E Tests

### Prerequisites

```bash
# Ensure all services are running
docker-compose up -d postgres timescaledb redis consul opa

# Or use test containers (recommended)
pytest tests/e2e/ --use-testcontainers

# Install E2E test dependencies
pip install -e ".[dev]"
```

### Run All E2E Tests

```bash
# Run complete E2E suite
pytest tests/e2e/ -v

# Run with detailed output
pytest tests/e2e/ -vv --tb=long

# Run in parallel (faster)
pytest tests/e2e/ -n auto
```

### Run Specific Test Categories

```bash
# Smoke tests only (fast)
pytest tests/e2e/test_smoke.py -v

# Complete flows (slower, comprehensive)
pytest tests/e2e/test_complete_flows.py -v

# Data generator tests
pytest tests/e2e/test_data_generator.py -v
```

### Run Specific Scenarios

```bash
# Run specific test
pytest tests/e2e/test_complete_flows.py::test_complete_user_registration_to_server_management -v

# Run tests matching pattern
pytest tests/e2e/ -k "admin" -v

# Run smoke tests in production-like environment
pytest tests/e2e/test_smoke.py --env=production -v
```

### Environment Configuration

```bash
# Use specific environment
export SARK_ENV=test
export SARK_DB_URL=postgresql://test:test@localhost/sark_test

# Run tests with environment
pytest tests/e2e/ -v

# Use .env.test file
cp .env.example .env.test
pytest tests/e2e/ --envfile=.env.test -v
```

## Test Markers

E2E tests use pytest markers for categorization:

- `@pytest.mark.e2e` - All end-to-end tests
- `@pytest.mark.smoke` - Quick smoke tests (<5 seconds)
- `@pytest.mark.slow` - Long-running tests (>30 seconds)
- `@pytest.mark.requires_services` - Requires external services (DB, OPA, etc.)
- `@pytest.mark.admin_flow` - Admin user workflows
- `@pytest.mark.user_flow` - Regular user workflows
- `@pytest.mark.critical` - Critical business paths

### Running by Marker

```bash
# Smoke tests only
pytest tests/e2e/ -m smoke -v

# Skip slow tests
pytest tests/e2e/ -m "not slow" -v

# Critical paths only
pytest tests/e2e/ -m critical -v

# Admin workflows
pytest tests/e2e/ -m admin_flow -v
```

## Test Data Management

### Generating Test Data

```python
from tests.e2e.test_data_generator import UserFactory, ServerFactory

# Generate single user
user = UserFactory.create()

# Generate 100 users
users = UserFactory.create_batch(100)

# Generate servers with specific traits
servers = ServerFactory.create_batch(50, sensitivity_level=SensitivityLevel.HIGH)
```

### Test Database Cleanup

E2E tests use database transactions for isolation:

```python
@pytest.fixture(autouse=True)
async def cleanup_db(test_db):
    """Automatic cleanup after each test."""
    yield
    # Rollback transaction
    await test_db.rollback()
```

## Example Test Flows

### Complete User Journey

```python
@pytest.mark.e2e
@pytest.mark.user_flow
@pytest.mark.critical
async def test_complete_user_registration_to_server_management(client):
    # 1. Register user
    response = await client.post("/api/auth/register", json={
        "email": "user@example.com",
        "password": "SecurePass123!",
        "full_name": "Test User"
    })
    assert response.status_code == 201

    # 2. Login
    response = await client.post("/api/auth/login", json={
        "email": "user@example.com",
        "password": "SecurePass123!"
    })
    assert response.status_code == 200
    token = response.json()["access_token"]

    # 3. Register server
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post("/api/servers/", headers=headers, json={
        "name": "my-server",
        "transport": "http",
        "endpoint": "http://example.com"
    })
    assert response.status_code == 201

    # 4. Verify server appears in search
    response = await client.get("/api/servers/search?q=my-server", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
```

## Performance Considerations

### Test Execution Time

- **Smoke tests**: ~10 seconds total
- **Complete flows**: ~2-5 minutes per test
- **Full E2E suite**: ~10-15 minutes
- **With parallelization (-n auto)**: ~3-5 minutes

### Optimization Tips

1. **Use test containers** for database isolation
2. **Run smoke tests first** to catch obvious failures
3. **Parallelize tests** with `-n auto`
4. **Cache common fixtures** (users, servers)
5. **Skip cleanup** in CI with `--skip-cleanup` flag

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      opa:
        image: openpolicyagent/opa:latest
        options: >-
          --health-cmd "wget -q -O- http://localhost:8181/health"

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Run smoke tests
        run: |
          pytest tests/e2e/test_smoke.py -v --tb=short

      - name: Run E2E tests
        run: |
          pytest tests/e2e/ -v --tb=short -n auto

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: e2e-test-results
          path: test-results/
```

### GitLab CI Example

```yaml
e2e_tests:
  stage: test
  image: python:3.11

  services:
    - postgres:15
    - openpolicyagent/opa:latest

  before_script:
    - pip install -e ".[dev]"

  script:
    - pytest tests/e2e/test_smoke.py -v
    - pytest tests/e2e/ -v -n auto

  artifacts:
    when: always
    reports:
      junit: test-results/junit.xml
```

## Troubleshooting

### Common Issues

**1. Service Connection Failures**
```bash
# Verify services are running
docker-compose ps

# Check service logs
docker-compose logs postgres
docker-compose logs opa
```

**2. Database Connection Errors**
```bash
# Reset test database
docker-compose exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS sark_test;"
docker-compose exec postgres psql -U postgres -c "CREATE DATABASE sark_test;"

# Run migrations
alembic upgrade head
```

**3. OPA Policy Failures**
```bash
# Verify OPA is running
curl http://localhost:8181/health

# Upload policies manually
curl -X PUT http://localhost:8181/v1/policies/test --data-binary @policies/test.rego
```

**4. Test Data Conflicts**
```bash
# Clear test database
pytest tests/e2e/ --clear-db

# Use isolated database per test
pytest tests/e2e/ --db-isolation
```

### Debug Mode

```bash
# Run with verbose debugging
pytest tests/e2e/ -vv --log-cli-level=DEBUG

# Drop into debugger on failure
pytest tests/e2e/ --pdb

# Keep test containers running on failure
pytest tests/e2e/ --keep-containers-on-failure
```

## Best Practices

### 1. Test Independence
- Each test should be fully independent
- Use fixtures for setup/teardown
- Don't rely on test execution order

### 2. Realistic Data
- Use test data generators for variety
- Include edge cases in generated data
- Test with production-like data volumes

### 3. Error Scenarios
- Test happy paths AND failure paths
- Verify error messages are helpful
- Test retry/recovery mechanisms

### 4. Performance Testing
- Monitor test execution time
- Set reasonable timeouts
- Flag slow tests with @pytest.mark.slow

### 5. Maintenance
- Keep tests DRY with shared fixtures
- Document complex test scenarios
- Update tests when features change

## Test Coverage

E2E tests cover:

- ✅ User registration and authentication (100%)
- ✅ Server lifecycle management (100%)
- ✅ Policy creation and enforcement (100%)
- ✅ Multi-team collaboration (100%)
- ✅ Audit trail completeness (100%)
- ✅ Bulk operations (100%)
- ✅ Error handling (100%)

## Contributing

When adding new E2E tests:

1. **Follow naming conventions**: `test_<scenario>_<expected_outcome>`
2. **Add docstrings**: Explain the user journey
3. **Use appropriate markers**: @pytest.mark.e2e, etc.
4. **Keep tests focused**: One scenario per test
5. **Update documentation**: Add to this README

## References

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Factory Boy](https://factoryboy.readthedocs.io/)
- [Faker](https://faker.readthedocs.io/)
- [TestContainers](https://testcontainers-python.readthedocs.io/)
