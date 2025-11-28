# Gateway Integration Test Suite

## Test Organization

- `integration/` - End-to-end integration tests
- `performance/` - Performance and load tests
- `security/` - Security and penetration tests
- `utils/` - Test utilities and mocks

## Running Tests

```bash
# All gateway tests
pytest tests/integration/gateway/ tests/performance/gateway/ tests/security/gateway/ -v

# Integration tests only
pytest tests/integration/gateway/ -v

# Performance tests (marked)
pytest tests/performance/gateway/ -m performance -v

# Security tests
pytest tests/security/gateway/ -m security -v

# Specific test file
pytest tests/integration/gateway/test_gateway_authorization_flow.py -v
```

## Test Coverage

Run with coverage:
```bash
pytest tests/integration/gateway/ \
  --cov=src/sark/services/gateway \
  --cov=src/sark/api/routers/gateway \
  --cov-report=html \
  --cov-report=term
```

Target: >85% coverage

## Performance Benchmarks

### Authorization Latency Targets
- **P50:** < 20ms
- **P95:** < 50ms
- **P99:** < 100ms

### Throughput Targets
- **Sustained:** > 1,000 req/s
- **Peak:** > 5,000 req/s
- **Concurrent:** 100+ simultaneous requests

### Cache Performance
- **Cache Hit Latency:** < 10ms (P95)
- **Cache Miss Latency:** < 50ms (P95)

## Security Test Coverage

### OWASP Top 10
- ✅ A01: Broken Access Control
- ✅ A02: Cryptographic Failures
- ✅ A03: Injection (SQL, XSS, Command)
- ✅ A04: Insecure Design
- ✅ A05: Security Misconfiguration
- ✅ A06: Vulnerable Components
- ✅ A07: Authentication Failures
- ✅ A08: Software and Data Integrity
- ✅ A09: Logging Failures
- ✅ A10: Server-Side Request Forgery

### Security Tests
- Invalid token rejection
- Expired token rejection
- SQL injection protection
- XSS prevention
- Command injection blocking
- Path traversal protection
- Fail-closed behavior
- Rate limiting
- CSRF protection
- Privilege escalation prevention

## Test Utilities

### Mock Gateway API
Location: `tests/utils/gateway/mock_gateway.py`

Simulates MCP Gateway Registry API for testing without real Gateway dependency.

Usage:
```python
from tests.utils.gateway.mock_gateway import mock_gateway_client

response = mock_gateway_client.get("/api/servers")
assert response.status_code == 200
```

### Mock OPA Server
Location: `tests/utils/gateway/mock_opa.py`

Simulates OPA policy evaluation for testing.

Usage:
```python
from tests.utils.gateway.mock_opa import app
from fastapi.testclient import TestClient

client = TestClient(app)
response = client.post("/v1/data/mcp/gateway/allow", json={...})
```

### Test Fixtures
Location: `tests/utils/gateway/fixtures.py`

Provides pytest fixtures for common test data:
- `sample_gateway_server` - Sample Gateway server info
- `sample_authorization_request` - Sample authorization request
- `mock_user_context` - Mock user context
- `admin_user_context` - Admin user for testing
- `restricted_user_context` - Restricted user for testing

## CI/CD Integration

Tests run automatically on PR via `.github/workflows/gateway-integration-tests.yml`

### CI Pipeline
1. **Linting & Type Checking**
   - ruff (linting)
   - black (formatting)
   - mypy (type checking)

2. **Unit Tests**
   - All gateway-related unit tests
   - Coverage >85%

3. **Integration Tests**
   - Full authorization flow
   - Parameter filtering
   - Cache behavior
   - Audit logging

4. **Performance Tests**
   - Latency benchmarks
   - Throughput tests
   - Cache performance

5. **Security Tests**
   - OWASP Top 10
   - Authentication/Authorization
   - Injection prevention

## Test Data

### Sample Users
- **Admin User:** `admin@example.com` (role: admin)
- **Developer User:** `test@example.com` (role: developer)
- **Viewer User:** `restricted@example.com` (role: viewer)

### Sample Servers
- **test-server-1:** Medium sensitivity, 5 tools
- **test-server-2:** High sensitivity, 10 tools

### Sample Actions
- `gateway:tool:invoke` - Tool invocation
- `gateway:tool:list` - List tools
- `gateway:server:read` - Read server info
- `gateway:admin:delete` - Admin delete (restricted)

## Debugging Tests

### Run with verbose output
```bash
pytest tests/integration/gateway/ -v -s
```

### Run specific test
```bash
pytest tests/integration/gateway/test_gateway_authorization_flow.py::test_full_authorization_flow_allow -v
```

### Run with debugging
```bash
pytest tests/integration/gateway/ --pdb
```

### Check test performance
```bash
pytest tests/integration/gateway/ --durations=10
```

## Writing New Tests

### Integration Test Template
```python
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_my_feature(app_client, mock_user_token):
    """Test description."""

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "test"},
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code == 200
    assert response.json()["allow"] is True
```

### Performance Test Template
```python
import pytest
import time

@pytest.mark.performance
async def test_my_performance(app_client, mock_user_token):
    """Test performance description."""

    latencies = []

    for _ in range(1000):
        start = time.perf_counter()
        response = await app_client.post(...)
        latency = (time.perf_counter() - start) * 1000
        latencies.append(latency)
        assert response.status_code == 200

    p95 = sorted(latencies)[int(len(latencies) * 0.95)]
    assert p95 < 50.0
```

### Security Test Template
```python
import pytest

@pytest.mark.security
async def test_my_security(app_client, mock_user_token):
    """Test security description."""

    response = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "malicious:action"},
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )

    assert response.status_code == 200
    assert response.json()["allow"] is False
```

## Troubleshooting

### Tests fail with connection errors
- Ensure test database is running
- Check that Redis is available
- Verify OPA server is accessible

### Performance tests timeout
- Increase timeout: `pytest --timeout=300`
- Run fewer iterations for local testing
- Check system resources

### Security tests fail
- Verify security policies are loaded
- Check OPA policies are correct
- Ensure authentication is configured

## Resources

- [Gateway Integration Plan](../../docs/gateway-integration/MCP_GATEWAY_INTEGRATION_PLAN.md)
- [QA Worker Tasks](../../docs/gateway-integration/tasks/QA_WORKER_TASKS.md)
- [Engineer Task Files](../../docs/gateway-integration/tasks/)

## Maintenance

### Updating Tests
1. Keep tests in sync with API changes
2. Update fixtures when models change
3. Adjust performance targets as needed
4. Add new security tests for new vulnerabilities

### Test Review Checklist
- [ ] Tests are clear and well-documented
- [ ] Assertions are specific and meaningful
- [ ] Test data is realistic
- [ ] Edge cases are covered
- [ ] Performance targets are reasonable
- [ ] Security tests cover common attacks

---

**Test Coverage Status:**
- Integration Tests: ✅ Complete
- Performance Tests: ✅ Complete
- Security Tests: ✅ Complete
- Documentation: ✅ Complete

**Ready for Gateway Integration Testing!** 🧪
