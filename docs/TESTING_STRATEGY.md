# SARK Testing Strategy

**Version:** 1.0
**Last Updated:** 2025-11-22
**Target Coverage:** 85%+

---

## Table of Contents

1. [Overview](#overview)
2. [Testing Pyramid](#testing-pyramid)
3. [Unit Testing](#unit-testing)
4. [Integration Testing](#integration-testing)
5. [End-to-End Testing](#end-to-end-testing)
6. [Load & Performance Testing](#load--performance-testing)
7. [Security Testing](#security-testing)
8. [Test Data Management](#test-data-management)
9. [CI/CD Integration](#cicd-integration)
10. [Coverage Goals](#coverage-goals)

---

## Overview

SARK employs a comprehensive testing strategy to ensure reliability, security, and performance at scale.

### Testing Principles

1. **Test Pyramid**: Favor fast, isolated unit tests over slow E2E tests
2. **Test Independence**: Each test runs independently with own fixtures
3. **Coverage Goals**: 85%+ code coverage across all modules
4. **Continuous Testing**: All tests run in CI/CD on every commit
5. **Performance Benchmarks**: Load tests validate scalability claims

### Test Categories

| Category | Scope | Speed | Coverage | CI Frequency |
|----------|-------|-------|----------|--------------|
| **Unit** | Single function/class | <1s | 70% | Every commit |
| **Integration** | Multiple components | 1-30s | 15% | Every commit |
| **E2E** | Full system | 30-300s | 5% | Pre-merge, Nightly |
| **Load** | Performance/scale | 5-60min | - | Weekly, Pre-release |
| **Security** | Vulnerabilities | 1-10min | - | Daily, Pre-release |

---

## Testing Pyramid

```
       /\
      /  \  E2E (5%)           - Full user journeys
     /    \                     - Browser/API tests
    /------\
   /        \  Integration (15%) - Multi-component
  /          \                   - Database + API + OPA
 /------------\
/              \  Unit (70%)     - Pure functions
\______________/                 - Mocked dependencies
```

**Distribution:**
- **Unit Tests**: 1,500+ tests, <5 minute total runtime
- **Integration Tests**: 200+ tests, <15 minute total runtime
- **E2E Tests**: 50+ tests, <30 minute total runtime
- **Load Tests**: 10+ scenarios, run weekly

---

## Unit Testing

### Framework & Tools

```bash
# Test runner
pytest>=7.4.0

# Coverage
pytest-cov>=4.1.0
coverage>=7.3.0

# Mocking
pytest-mock>=3.11.0
unittest.mock

# Async testing
pytest-asyncio>=0.21.0

# Fixtures
pytest-fixtures>=0.1.0
```

### Test Structure

```python
# tests/test_services/test_auth/test_jwt.py
import pytest
from unittest.mock import Mock, patch
from sark.services.auth import TokenService
from sark.config import Settings

class TestTokenService:
    """Unit tests for JWT token service."""

    @pytest.fixture
    def settings(self):
        """Mock settings for testing."""
        return Settings(
            jwt_secret_key="test-secret-key-256-bits",
            jwt_algorithm="HS256",
            jwt_expiration_minutes=60
        )

    @pytest.fixture
    def redis_mock(self):
        """Mock Redis client."""
        return Mock()

    @pytest.fixture
    def token_service(self, settings, redis_mock):
        """TokenService instance with mocked dependencies."""
        return TokenService(settings=settings, redis_client=redis_mock)

    def test_create_access_token_success(self, token_service):
        """Test successful access token creation."""
        user_context = {
            "user_id": "user-123",
            "email": "test@example.com",
            "roles": ["developer"]
        }

        token = await token_service.create_access_token(user_context)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long

    def test_create_access_token_validates_user_id(self, token_service):
        """Test that user_id is required."""
        invalid_context = {"email": "test@example.com"}

        with pytest.raises(ValueError, match="user_id required"):
            await token_service.create_access_token(invalid_context)

    @patch('sark.services.auth.jwt.encode')
    def test_create_access_token_calls_jwt_encode(
        self, mock_encode, token_service
    ):
        """Test that JWT library is called correctly."""
        user_context = {"user_id": "user-123"}
        mock_encode.return_value = "mocked.jwt.token"

        token = await token_service.create_access_token(user_context)

        mock_encode.assert_called_once()
        assert token == "mocked.jwt.token"
```

### Coverage by Module

**Target Coverage:**

| Module | Current | Target | Priority |
|--------|---------|--------|----------|
| `services/auth/jwt.py` | 26% | 90% | P0 |
| `services/auth/providers/` | 65% | 85% | P1 |
| `services/policy/opa_client.py` | 71% | 90% | P0 |
| `services/policy/policy_service.py` | 21% | 85% | P0 |
| `services/audit/audit_service.py` | 43% | 85% | P1 |
| `services/discovery/discovery_service.py` | 21% | 85% | P1 |
| `api/routers/` | 62% | 85% | P1 |

### Running Unit Tests

```bash
# Run all unit tests
pytest tests/ -m "not integration and not e2e" -v

# Run with coverage
pytest tests/ -m "not integration" --cov=src/sark --cov-report=html

# Run specific module
pytest tests/test_services/test_auth/ -v

# Run with markers
pytest -m "auth" -v          # Auth-related tests only
pytest -m "slow" -v          # Slow tests only
pytest -m "not slow" -v      # Skip slow tests

# Parallel execution
pytest -n auto tests/        # Auto-detect CPU cores
```

### Test Markers

```python
# tests/conftest.py
import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests (require services)")
    config.addinivalue_line("markers", "e2e: End-to-end tests (slow)")
    config.addinivalue_line("markers", "slow: Slow-running tests")
    config.addinivalue_line("markers", "auth: Authentication tests")
    config.addinivalue_line("markers", "policy: Policy engine tests")
    config.addinivalue_line("markers", "siem: SIEM integration tests")
```

---

## Integration Testing

### Setup & Fixtures

```python
# tests/integration/conftest.py
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

@pytest.fixture(scope="session")
def postgres_container():
    """PostgreSQL test container."""
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres

@pytest.fixture(scope="session")
def redis_container():
    """Redis test container."""
    with RedisContainer("redis:7-alpine") as redis:
        yield redis

@pytest.fixture(scope="session")
async def db_engine(postgres_container):
    """Database engine for testing."""
    engine = create_async_engine(postgres_container.get_connection_url())

    # Run migrations
    from alembic import command
    from alembic.config import Config
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(db_engine):
    """Database session for each test."""
    async with AsyncSession(db_engine) as session:
        yield session
        await session.rollback()  # Rollback after each test
```

### Integration Test Examples

```python
# tests/integration/test_auth_integration.py
import pytest
from sark.services.auth import TokenService
from sark.services.auth.providers import LDAPProvider

@pytest.mark.integration
@pytest.mark.asyncio
async def test_ldap_authentication_flow(redis_container, ldap_container):
    """Test complete LDAP authentication flow."""
    # Setup
    redis_client = await create_redis_client(redis_container.get_connection_url())
    token_service = TokenService(redis_client=redis_client)
    ldap_provider = LDAPProvider(ldap_server=ldap_container.get_ldap_url())

    # Authenticate user
    user_info = ldap_provider.authenticate("testuser", "testpass")
    assert user_info["user_id"] is not None
    assert user_info["email"] == "testuser@example.com"

    # Create tokens
    access_token = await token_service.create_access_token(user_info)
    refresh_token, _ = await token_service.create_refresh_token(user_info["user_id"])

    assert access_token is not None
    assert refresh_token is not None

    # Verify tokens
    decoded = await token_service.decode_access_token(access_token)
    assert decoded["user_id"] == user_info["user_id"]

    # Cleanup
    await redis_client.close()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_server_registration_with_policy(db_session, opa_client):
    """Test server registration with OPA policy evaluation."""
    from sark.services.discovery import DiscoveryService
    from sark.services.policy import PolicyService

    discovery = DiscoveryService(db=db_session)
    policy = PolicyService(opa_client=opa_client)

    # Register server
    server_data = {
        "name": "test-server",
        "endpoint_url": "http://test.example.com",
        "sensitivity_level": "HIGH"
    }

    user_context = {
        "user_id": "admin-123",
        "roles": ["admin"]
    }

    # Evaluate policy
    decision = await policy.evaluate(
        user=user_context,
        action="server:register",
        resource=server_data
    )

    assert decision["decision"] == "allow"

    # Register server
    server = await discovery.register_server(server_data, user_context)
    assert server.id is not None
    assert server.name == "test-server"
```

### Running Integration Tests

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run with Docker containers
docker-compose -f docker-compose.test.yml up -d
pytest tests/integration/ -v
docker-compose -f docker-compose.test.yml down

# Run specific integration test
pytest tests/integration/test_auth_integration.py::test_ldap_authentication_flow -v
```

---

## End-to-End Testing

### E2E Test Framework

```bash
# API testing
pytest>=7.4.0
httpx>=0.24.0

# Test data
faker>=19.0.0
factory-boy>=3.3.0
```

### E2E Test Scenarios

```python
# tests/e2e/test_complete_flows.py
import pytest
import httpx

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_user_journey():
    """Test complete user journey from login to server registration."""
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient(base_url=base_url) as client:
        # Step 1: Login
        login_response = await client.post(
            "/api/auth/login/ldap",
            json={"username": "testuser", "password": "testpass"}
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        access_token = tokens["access_token"]

        # Step 2: Get current user
        headers = {"Authorization": f"Bearer {access_token}"}
        me_response = await client.get("/api/auth/me", headers=headers)
        assert me_response.status_code == 200
        user = me_response.json()
        assert user["username"] == "testuser"

        # Step 3: Register server
        server_data = {
            "name": "e2e-test-server",
            "endpoint_url": "http://test.example.com",
            "sensitivity_level": "MEDIUM"
        }
        register_response = await client.post(
            "/api/servers",
            json=server_data,
            headers=headers
        )
        assert register_response.status_code == 201
        server = register_response.json()["server"]

        # Step 4: List servers
        list_response = await client.get("/api/servers?limit=50", headers=headers)
        assert list_response.status_code == 200
        servers = list_response.json()["items"]
        assert any(s["id"] == server["id"] for s in servers)

        # Step 5: Get specific server
        get_response = await client.get(
            f"/api/servers/{server['id']}",
            headers=headers
        )
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "e2e-test-server"

        # Step 6: Logout
        logout_response = await client.post(
            "/api/auth/revoke",
            json={"refresh_token": tokens["refresh_token"]},
            headers=headers
        )
        assert logout_response.status_code == 200
```

---

## Load & Performance Testing

### Tools

```bash
# Load testing
locust>=2.15.0
k6>=0.46.0

# Profiling
py-spy>=0.3.14
memory_profiler>=0.61.0
```

### Locust Load Tests

```python
# tests/load_testing/locustfile.py
from locust import HttpUser, task, between, events
import random

class SARKUser(HttpUser):
    wait_time = between(1, 3)
    access_token = None

    def on_start(self):
        """Login before starting tasks."""
        response = self.client.post("/api/auth/login/ldap", json={
            "username": f"loadtest_user_{random.randint(1, 100)}",
            "password": "testpass"
        })
        if response.status_code == 200:
            self.access_token = response.json()["access_token"]
            self.client.headers = {"Authorization": f"Bearer {self.access_token}"}

    @task(5)
    def list_servers(self):
        """List servers (most common operation)."""
        self.client.get("/api/servers?limit=50")

    @task(3)
    def get_server(self):
        """Get specific server."""
        server_id = random.choice(self.server_ids) if hasattr(self, 'server_ids') else "test"
        self.client.get(f"/api/servers/{server_id}")

    @task(2)
    def search_servers(self):
        """Search and filter servers."""
        params = {
            "status": random.choice(["active", "inactive"]),
            "limit": 50
        }
        self.client.get("/api/servers", params=params)

    @task(1)
    def register_server(self):
        """Register new server (least common, most expensive)."""
        server_data = {
            "name": f"loadtest-server-{random.randint(1, 10000)}",
            "endpoint_url": f"http://server-{random.randint(1, 1000)}.example.com",
            "sensitivity_level": random.choice(["LOW", "MEDIUM", "HIGH"])
        }
        response = self.client.post("/api/servers", json=server_data)
        if response.status_code == 201:
            server_id = response.json()["server"]["id"]
            if not hasattr(self, 'server_ids'):
                self.server_ids = []
            self.server_ids.append(server_id)

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("Load test starting...")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print(f"Load test completed. Total requests: {environment.stats.total.num_requests}")
```

### Running Load Tests

```bash
# Local load test (1000 users, 50/sec spawn rate)
locust -f tests/load_testing/locustfile.py \
  --host=http://localhost:8000 \
  --users=1000 \
  --spawn-rate=50 \
  --run-time=10m \
  --html=reports/load-test-report.html

# Distributed load test (multiple workers)
# Master
locust -f locustfile.py --master --host=http://api.example.com

# Workers (run on multiple machines)
locust -f locustfile.py --worker --master-host=192.168.1.100
```

### Performance Benchmarks

**API Performance Targets:**

| Endpoint | p50 | p95 | p99 | Target RPS |
|----------|-----|-----|-----|------------|
| `GET /api/servers` | <50ms | <100ms | <200ms | 5,000 |
| `POST /api/servers` | <100ms | <200ms | <500ms | 500 |
| `POST /api/auth/login` | <150ms | <300ms | <600ms | 100 |
| `POST /api/policy/evaluate` | <30ms | <50ms | <100ms | 10,000 |

**Load Test Scenarios:**

1. **Steady State**: 1,000 concurrent users, 10 minutes
2. **Spike Test**: Ramp from 100 to 5,000 users in 1 minute
3. **Soak Test**: 500 concurrent users, 4 hours
4. **Stress Test**: Gradually increase load until failure

---

## Security Testing

### Tools

```bash
# Static analysis
bandit>=1.7.5
safety>=2.3.0

# Dependency scanning
pip-audit>=2.6.0
snyk>=1.1200.0

# Secret scanning
trufflehog>=3.50.0
```

### Security Test Checklist

**OWASP Top 10:**

- [ ] **SQL Injection**: Parameterized queries, ORM usage
- [ ] **XSS**: Input validation, output encoding
- [ ] **Authentication**: JWT validation, session management
- [ ] **Authorization**: OPA policy enforcement
- [ ] **Security Misconfiguration**: Secure defaults
- [ ] **Vulnerable Dependencies**: Regular updates
- [ ] **Logging & Monitoring**: Comprehensive audit logs
- [ ] **CSRF**: CSRF tokens (if applicable)
- [ ] **Deserialization**: Safe JSON parsing
- [ ] **Insufficient Logging**: Audit all security events

### Running Security Tests

```bash
# Static analysis
bandit -r src/ -f json -o reports/bandit.json

# Dependency vulnerabilities
safety check --json > reports/safety.json
pip-audit --desc --format json > reports/pip-audit.json

# Secret scanning
trufflehog filesystem . --json > reports/secrets.json

# SAST scanning
semgrep --config auto src/ --json > reports/semgrep.json
```

---

## Test Data Management

### Test Data Strategy

```python
# tests/factories/user_factory.py
import factory
from faker import Faker
from sark.models import User

fake = Faker()

class UserFactory(factory.Factory):
    class Meta:
        model = User

    user_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    email = factory.LazyFunction(lambda: fake.email())
    username = factory.LazyFunction(lambda: fake.user_name())
    roles = factory.LazyFunction(lambda: ["developer"])
    teams = factory.LazyFunction(lambda: ["engineering"])

# Usage
user = UserFactory.create()
users = UserFactory.create_batch(10)
```

### Test Database Management

```bash
# Reset test database
python scripts/reset_test_db.py

# Seed test data
python scripts/seed_test_data.py --users=100 --servers=1000

# Export test data
pg_dump test_sark > tests/fixtures/test_data.sql
```

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e .[test]

      - name: Run unit tests
        run: |
          pytest tests/ -m "not integration and not e2e" \
            --cov=src/sark \
            --cov-report=xml \
            --cov-report=html \
            --junit-xml=reports/junit.xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s

    steps:
      - uses: actions/checkout@v3
      - name: Run integration tests
        run: |
          pytest tests/integration/ -v

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Bandit
        run: bandit -r src/ -f json -o reports/bandit.json

      - name: Run Safety
        run: safety check --json > reports/safety.json

  load-test:
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule' || contains(github.event.head_commit.message, '[load-test]')
    steps:
      - name: Run load test
        run: |
          locust -f tests/load_testing/locustfile.py \
            --headless \
            --users=100 \
            --spawn-rate=10 \
            --run-time=5m \
            --html=reports/load-test.html
```

---

## Coverage Goals

### Current Status (Week 2)

| Module | Coverage | Goal | Status |
|--------|----------|------|--------|
| **Overall** | 34.59% | 85% | ⚠️ In Progress |
| Auth Services | 45% | 85% | 🟡 |
| Policy Services | 48% | 85% | 🟡 |
| Discovery Services | 21% | 85% | 🔴 |
| Audit Services | 43% | 85% | 🟡 |
| API Routers | 62% | 85% | 🟡 |
| SIEM | 68% | 85% | 🟢 |

### Week 3 Coverage Targets

- **Day 11-12**: Expand auth module tests → 85%+
- **Day 13**: Policy module tests → 85%+
- **Day 14**: Discovery & audit modules → 85%+
- **Day 15**: Final coverage push → 85%+ overall

---

## Related Documentation

- [INTEGRATION_TESTING.md](./INTEGRATION_TESTING.md) - Integration test guide
- [PERFORMANCE_TUNING.md](./PERFORMANCE_TUNING.md) - Performance optimization
- [DEVELOPMENT.md](./DEVELOPMENT.md) - Development setup

---

**Testing Best Practices:**
1. Write tests first (TDD when possible)
2. Keep tests fast and independent
3. Use factories for test data
4. Mock external dependencies
5. Test edge cases and error paths
6. Maintain >85% coverage
7. Run full suite before merging
8. Load test before releases
