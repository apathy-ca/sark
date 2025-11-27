# QA Worker: Testing & Validation

**Branch:** `feat/gateway-tests`
**Duration:** 6-8 days (parallel with engineering)
**Focus:** Comprehensive testing across all components
**Dependencies:** Mock interfaces (Day 1), real implementations (Day 4+)

---

## Testing Strategy

Work in parallel with engineers using mocks, then integrate with real components as they're completed.

---

## Day 1-2: Test Infrastructure & Unit Tests

### Task 1.1: Mock Gateway API
**File:** `tests/utils/gateway/mock_gateway.py`

```python
"""Mock MCP Gateway API for testing."""

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

app = FastAPI()

# Mock server data
MOCK_SERVERS = [
    {
        "server_id": "srv_1",
        "server_name": "test-server-1",
        "server_url": "http://test1:8080",
        "sensitivity_level": "medium",
        "health_status": "healthy",
        "tools_count": 5
    },
    {
        "server_id": "srv_2",
        "server_name": "test-server-2",
        "server_url": "http://test2:8080",
        "sensitivity_level": "high",
        "health_status": "healthy",
        "tools_count": 10
    }
]


@app.get("/api/servers")
async def list_servers():
    return MOCK_SERVERS


@app.get("/api/servers/{server_name}")
async def get_server(server_name: str):
    server = next((s for s in MOCK_SERVERS if s["server_name"] == server_name), None)
    if not server:
        raise HTTPException(404, "Server not found")
    return server


@app.get("/health")
async def health():
    return {"status": "ok"}


# Test client
mock_gateway_client = TestClient(app)
```

### Task 1.2: Mock OPA Server
**File:** `tests/utils/gateway/mock_opa.py`

```python
"""Mock OPA server for testing."""

from fastapi import FastAPI

app = FastAPI()


@app.post("/v1/data/mcp/gateway/allow")
async def evaluate_gateway_policy(request: dict):
    """Mock policy evaluation."""
    user_role = request["input"]["user"]["role"]
    action = request["input"]["action"]
    
    # Simple mock logic
    allow = user_role in ["admin", "developer"]
    
    return {
        "result": {
            "allow": allow,
            "reason": f"{action} allowed for {user_role}" if allow else "Denied",
            "filtered_parameters": request["input"].get("parameters", {}),
        }
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
```

### Task 1.3: Test Fixtures
**File:** `tests/utils/gateway/fixtures.py`

```python
"""Pytest fixtures for Gateway tests."""

import pytest
from sark.models.gateway import *


@pytest.fixture
def sample_gateway_server():
    return GatewayServerInfo(
        server_id="srv_test",
        server_name="test-server",
        server_url="http://localhost:8080",
        sensitivity_level="medium",
        health_status="healthy",
        tools_count=5
    )


@pytest.fixture
def sample_authorization_request():
    return GatewayAuthorizationRequest(
        action="gateway:tool:invoke",
        server_name="test-server",
        tool_name="test-tool",
        parameters={"param1": "value1"},
        gateway_metadata={"request_id": "req_123"}
    )


@pytest.fixture
def mock_user_context():
    from sark.services.auth import UserContext
    return UserContext(
        user_id="user_123",
        email="test@example.com",
        role="developer",
        teams=["team1"]
    )
```

**Checklist:**
- [ ] Mock Gateway API complete
- [ ] Mock OPA server complete
- [ ] Test fixtures for all models
- [ ] Helper functions for test data generation

---

## Day 3-4: Integration Tests

### Task 2.1: Gateway Authorization Flow
**File:** `tests/integration/gateway/test_gateway_authorization_flow.py`

```python
"""End-to-end Gateway authorization tests."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_full_authorization_flow_allow(app_client, mock_user):
    """Test complete authorization flow (allow)."""
    
    # Step 1: Authenticate user
    auth_response = await app_client.post("/api/v1/auth/login", json={
        "username": "test@example.com",
        "password": "password"
    })
    assert auth_response.status_code == 200
    token = auth_response.json()["access_token"]
    
    # Step 2: Authorize Gateway request
    authz_response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "test-server",
            "tool_name": "safe-tool",
            "parameters": {"key": "value"}
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert authz_response.status_code == 200
    data = authz_response.json()
    assert data["allow"] is True
    assert "filtered_parameters" in data
    assert "audit_id" in data
    
    # Step 3: Verify audit event logged
    # Query audit database
    # Verify event in SIEM (mock)


async def test_parameter_filtering(app_client, mock_user_token):
    """Test sensitive parameter filtering."""
    
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "server_name": "db-server",
            "tool_name": "query",
            "parameters": {
                "query": "SELECT * FROM users",
                "password": "secret123",  # Should be filtered
                "api_key": "key_abc"      # Should be filtered
            }
        },
        headers={"Authorization": f"Bearer {mock_user_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Filtered parameters should not contain secrets
    assert "password" not in data["filtered_parameters"]
    assert "api_key" not in data["filtered_parameters"]
    assert "query" in data["filtered_parameters"]


async def test_cache_behavior(app_client, mock_user_token):
    """Test policy cache hit/miss."""
    
    # First request - cache miss
    response1 = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "test"},
        headers={"Authorization": f"Bearer {mock_user_token}"}
    )
    
    # Second identical request - cache hit
    response2 = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "test"},
        headers={"Authorization": f"Bearer {mock_user_token}"}
    )
    
    # Both should succeed
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    # Check cache metrics (second request should be faster)
    # Verify cache hit counter incremented
```

**Checklist:**
- [ ] Full authorization flow (allow)
- [ ] Full authorization flow (deny)
- [ ] Parameter filtering validation
- [ ] Cache hit/miss behavior
- [ ] Audit logging verification
- [ ] Error handling scenarios

---

## Day 5: Performance Tests

### Task 3.1: Authorization Latency
**File:** `tests/performance/gateway/test_authorization_latency.py`

```python
"""Gateway authorization latency tests."""

import pytest
import asyncio
import statistics
import time
from httpx import AsyncClient


@pytest.mark.performance
async def test_authorization_latency_p95(app_client, mock_user_token):
    """Test P95 authorization latency < 50ms."""
    
    latencies = []
    iterations = 1000
    
    for _ in range(iterations):
        start = time.perf_counter()
        
        response = await app_client.post(
            "/api/v1/gateway/authorize",
            json={
                "action": "gateway:tool:invoke",
                "tool_name": "test-tool"
            },
            headers={"Authorization": f"Bearer {mock_user_token}"}
        )
        
        latency = (time.perf_counter() - start) * 1000  # Convert to ms
        latencies.append(latency)
        
        assert response.status_code == 200
    
    # Calculate percentiles
    latencies.sort()
    p50 = latencies[int(len(latencies) * 0.50)]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]
    
    print(f"\nLatency Results (ms):")
    print(f"  P50: {p50:.2f}")
    print(f"  P95: {p95:.2f}")
    print(f"  P99: {p99:.2f}")
    
    # Assert performance targets
    assert p95 < 50.0, f"P95 latency {p95:.2f}ms exceeds 50ms target"


@pytest.mark.performance
async def test_concurrent_requests(app_client, mock_user_token):
    """Test authorization under concurrent load."""
    
    async def make_request():
        response = await app_client.post(
            "/api/v1/gateway/authorize",
            json={"action": "gateway:tool:invoke", "tool_name": "test"},
            headers={"Authorization": f"Bearer {mock_user_token}"}
        )
        return response.status_code
    
    # Run 100 concurrent requests
    tasks = [make_request() for _ in range(100)]
    results = await asyncio.gather(*tasks)
    
    # All should succeed
    assert all(status == 200 for status in results)
```

**Checklist:**
- [ ] P50/P95/P99 latency measurement
- [ ] Concurrent request handling
- [ ] Sustained load test (1000+ req/s)
- [ ] Spike test (0→10k req/s)
- [ ] Cache performance under load

---

## Day 6: Security Tests

### Task 4.1: Authentication & Authorization Security
**File:** `tests/security/gateway/test_gateway_security.py`

```python
"""Security tests for Gateway integration."""

import pytest


@pytest.mark.security
async def test_invalid_jwt_rejected(app_client):
    """Test invalid JWT tokens are rejected."""
    
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "test"},
        headers={"Authorization": "Bearer invalid_token"}
    )
    
    assert response.status_code == 401


@pytest.mark.security
async def test_expired_token_rejected(app_client, expired_token):
    """Test expired tokens are rejected."""
    
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "test"},
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    
    assert response.status_code == 401


@pytest.mark.security
async def test_parameter_injection_blocked(app_client, mock_user_token):
    """Test SQL injection attempts are blocked."""
    
    malicious_params = {
        "query": "'; DROP TABLE users; --",
        "command": "$(rm -rf /)",
        "path": "../../etc/passwd"
    }
    
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={
            "action": "gateway:tool:invoke",
            "tool_name": "test",
            "parameters": malicious_params
        },
        headers={"Authorization": f"Bearer {mock_user_token}"}
    )
    
    # Should either deny or sanitize
    data = response.json()
    if data["allow"]:
        # Check parameters are sanitized
        assert "DROP TABLE" not in str(data.get("filtered_parameters", {}))


@pytest.mark.security
async def test_fail_closed_on_opa_error(app_client, mock_user_token, monkeypatch):
    """Test system fails closed when OPA is unavailable."""
    
    # Simulate OPA failure
    monkeypatch.setenv("OPA_URL", "http://invalid:9999")
    
    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "test"},
        headers={"Authorization": f"Bearer {mock_user_token}"}
    )
    
    # Should deny when OPA is unavailable
    assert response.status_code == 200
    assert response.json()["allow"] is False
```

**Checklist:**
- [ ] Invalid token rejection
- [ ] Expired token rejection
- [ ] SQL injection protection
- [ ] Command injection protection
- [ ] Path traversal protection
- [ ] Fail-closed behavior
- [ ] Rate limiting enforcement

---

## Day 7: Test Documentation & Reporting

### Task 5.1: Test Suite Documentation
**File:** `tests/gateway/README.md`

```markdown
# Gateway Integration Test Suite

## Test Organization

- `integration/` - End-to-end integration tests
- `performance/` - Performance and load tests  
- `security/` - Security and penetration tests
- `contract/` - API contract validation tests
- `utils/` - Test utilities and mocks

## Running Tests

```bash
# All tests
pytest tests/gateway/

# Integration tests only
pytest tests/integration/gateway/ -v

# Performance tests (marked)
pytest tests/performance/gateway/ -m performance

# Security tests
pytest tests/security/gateway/ -m security
```

## Test Coverage

Run with coverage:
```bash
pytest --cov=src/sark/services/gateway --cov=src/sark/api/routers/gateway
```

Target: >85% coverage

## CI/CD Integration

Tests run automatically on PR via `.github/workflows/gateway-integration-tests.yml`
```

**Checklist:**
- [ ] Test suite documentation complete
- [ ] Coverage report generated
- [ ] Performance test results documented
- [ ] Security test results documented

---

## CI/CD Integration

**File:** `.github/workflows/gateway-integration-tests.yml`

```yaml
name: Gateway Integration Tests

on:
  pull_request:
    paths:
      - 'src/sark/services/gateway/**'
      - 'src/sark/api/routers/gateway.py'
      - 'opa/policies/gateway_*.rego'
      - 'tests/integration/gateway/**'

jobs:
  test:
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
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      opa:
        image: openpolicyagent/opa:latest
        options: >-
          --entrypoint "opa run --server"
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      
      - name: Run integration tests
        run: |
          pytest tests/integration/gateway/ -v --cov
      
      - name: Run security tests
        run: |
          pytest tests/security/gateway/ -m security -v
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Delivery Checklist

- [ ] Mock utilities complete
- [ ] Integration tests pass
- [ ] Performance tests meet targets
- [ ] Security tests pass
- [ ] Contract tests validate APIs
- [ ] Test documentation complete
- [ ] CI/CD workflow configured
- [ ] Coverage >80%
- [ ] PR created

Ready! 🧪
