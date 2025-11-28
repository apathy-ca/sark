# Gateway Integration Test Strategy

## Testing Philosophy

Our testing approach for Gateway integration follows the **Test Pyramid** principle with a strong emphasis on:

1. **Fast Feedback** - Unit tests run on every commit
2. **Comprehensive Coverage** - Integration tests cover all critical paths
3. **Performance Validation** - Continuous performance benchmarking
4. **Security First** - Security tests are mandatory, not optional
5. **Chaos Resilience** - System must handle failures gracefully

## Test Pyramid for Gateway Integration

```
         /\
        /  \  E2E Tests (Manual & Automated)
       /____\
      /      \  Integration Tests
     /________\
    /          \  Unit Tests
   /__________  \
```

### Distribution
- **Unit Tests**: 60% - Fast, isolated component tests
- **Integration Tests**: 30% - Multi-component interaction tests
- **E2E Tests**: 8% - Full system validation
- **Chaos Tests**: 2% - Resilience and fault tolerance

## Test Categories

### 1. Integration Tests (`tests/integration/gateway/`)

**Purpose**: Validate interactions between Gateway components

**Test Files**:
- `test_gateway_authorization_flow.py` - Core authorization workflows
- `test_multi_server_orchestration.py` - Multi-server coordination (8 scenarios)
- `test_tool_chains.py` - Complex tool chain execution (14 scenarios)
- `test_policy_integration.py` - OPA policy enforcement (9 scenarios)
- `test_audit_integration.py` - Audit trail validation (10 scenarios)

**Total**: 48 integration test scenarios

**Coverage Goals**:
- All API endpoints exercised
- All error paths tested
- All success paths validated
- Edge cases covered

**Run Command**:
```bash
pytest tests/integration/gateway/ -v
```

### 2. Performance Tests (`tests/performance/gateway/`)

**Purpose**: Ensure performance targets are met

**Test Files**:
- `test_authorization_latency.py` - Latency benchmarks (5 scenarios)
- `test_gateway_throughput.py` - Throughput testing
- `test_gateway_latency.py` - Detailed latency analysis
- `test_resource_usage.py` - Memory and CPU monitoring
- `test_stress.py` - Stress and load testing

**Performance Targets**:
- P50 Latency: < 20ms
- P95 Latency: < 50ms
- P99 Latency: < 100ms
- Throughput: > 1,000 req/s sustained
- Cache Hit Latency: < 10ms (P95)

**Run Command**:
```bash
pytest tests/performance/gateway/ -m performance -v
```

### 3. Security Tests (`tests/security/gateway/`)

**Purpose**: Validate security controls and prevent vulnerabilities

**Test Files**:
- `test_gateway_security.py` - Core security tests (14 scenarios)
- `test_auth_security.py` - Authentication/authorization
- `test_input_validation.py` - Injection prevention (11 scenarios)
- `test_rate_limiting.py` - Rate limit enforcement (4 scenarios)
- `test_data_exposure.py` - Data leakage prevention (4 scenarios)

**OWASP Top 10 Coverage**:
- ✅ A01: Broken Access Control
- ✅ A02: Cryptographic Failures
- ✅ A03: Injection (SQL, Command, XSS, Path Traversal, XXE, LDAP, NoSQL)
- ✅ A04: Insecure Design
- ✅ A05: Security Misconfiguration
- ✅ A06: Vulnerable Components
- ✅ A07: Authentication Failures
- ✅ A08: Software and Data Integrity
- ✅ A09: Logging Failures
- ✅ A10: Server-Side Request Forgery

**Run Command**:
```bash
pytest tests/security/gateway/ -m security -v
```

### 4. Chaos Engineering Tests (`tests/chaos/gateway/`)

**Purpose**: Validate resilience and fault tolerance

**Test Files**:
- `test_network_chaos.py` - Network failure scenarios (3 scenarios)
- `test_dependency_chaos.py` - Service dependency failures (3 scenarios)
- `test_resource_chaos.py` - Resource exhaustion scenarios

**Chaos Scenarios**:
- Slow network conditions
- Intermittent connection failures
- Network partitions
- OPA service unavailable (fail-closed validation)
- Database connection failures
- Cache service failures

**Run Command**:
```bash
pytest tests/chaos/gateway/ -m chaos -v
```

## Coverage Goals and Current Status

### Overall Coverage Target: >80%

| Component | Target | Status |
|-----------|--------|--------|
| Gateway Client | 85% | ✅ In Progress |
| Gateway API Router | 90% | ✅ In Progress |
| Policy Integration | 85% | ✅ In Progress |
| Audit Service | 80% | ✅ In Progress |
| Models | 100% | ✅ In Progress |

### Measuring Coverage

```bash
# Full coverage report
pytest tests/integration/gateway/ \
  --cov=src/sark/services/gateway \
  --cov=src/sark/api/routers/gateway \
  --cov-report=html \
  --cov-report=term \
  --cov-report=xml

# View HTML report
open htmlcov/index.html
```

## How to Run Different Test Suites

### Quick Smoke Test
```bash
# Run only fast tests
pytest tests/integration/gateway/test_gateway_authorization_flow.py -v
```

### Full Integration Test Suite
```bash
# All integration tests
pytest tests/integration/gateway/ -v

# With coverage
pytest tests/integration/gateway/ --cov --cov-report=term
```

### Performance Benchmarks
```bash
# All performance tests
pytest tests/performance/gateway/ -m performance -v

# Specific benchmark
pytest tests/performance/gateway/test_authorization_latency.py::test_authorization_latency_p95 -v
```

### Security Validation
```bash
# All security tests
pytest tests/security/gateway/ -m security -v

# Specific security category
pytest tests/security/gateway/test_input_validation.py -v
```

### Chaos Engineering
```bash
# All chaos tests
pytest tests/chaos/gateway/ -m chaos -v
```

### Run Everything
```bash
# All gateway tests (long running)
pytest tests/integration/gateway/ tests/performance/gateway/ tests/security/gateway/ tests/chaos/gateway/ -v

# Parallel execution (faster)
pytest tests/integration/gateway/ -n auto
```

## Test Environment Setup

### Prerequisites
```bash
# Install test dependencies
pip install -e ".[dev]"

# Install additional testing tools
pip install pytest-benchmark pytest-xdist locust
```

### Environment Variables
```bash
# Test configuration
export TEST_DATABASE_URL="postgresql://test:test@localhost:5432/sark_test"
export TEST_REDIS_URL="redis://localhost:6379/1"
export TEST_OPA_URL="http://localhost:8181"
export GATEWAY_ENABLED="true"
export GATEWAY_URL="http://localhost:8000"
```

### Docker Compose for Testing
```bash
# Start test services
docker-compose -f docker-compose.test.yml up -d

# Run tests
pytest tests/integration/gateway/ -v

# Cleanup
docker-compose -f docker-compose.test.yml down -v
```

## CI/CD Integration

### GitHub Actions Workflow

Tests run automatically on:
- Every pull request
- Pushes to main branch
- Nightly (performance tests)
- Weekly (security scans)

### Pipeline Stages

1. **Linting** (< 1 min)
   - ruff, black, mypy

2. **Unit Tests** (< 2 min)
   - Fast, isolated tests

3. **Integration Tests** (< 5 min)
   - Full integration scenarios

4. **Performance Tests** (< 10 min, nightly)
   - Benchmarking and profiling

5. **Security Tests** (< 5 min)
   - OWASP validation

6. **Chaos Tests** (< 3 min, weekly)
   - Resilience validation

### Quality Gates

**Merge Requirements**:
- ✅ All tests passing
- ✅ Coverage > 80%
- ✅ No high/critical security vulnerabilities
- ✅ Performance within targets
- ✅ No linting errors

## Test Data Management

### Mock Data
- Located in `tests/utils/gateway/fixtures.py`
- Reusable across test suites
- Realistic sample data

### Test Isolation
- Each test uses fresh database state
- Redis cache cleared between tests
- OPA policies reset to defaults

### Cleanup
```python
@pytest.fixture(autouse=True)
async def cleanup(db_session):
    """Auto-cleanup after each test."""
    yield
    await db_session.rollback()
    await clear_test_cache()
```

## Continuous Improvement

### Adding New Tests
1. Identify gap in coverage
2. Write failing test first (TDD)
3. Implement feature
4. Verify test passes
5. Update documentation

### Performance Regression Detection
- Baseline stored in `docs/testing/PERFORMANCE_BASELINES.md`
- Automatic comparison in CI
- Alert on >10% regression

### Security Updates
- OWASP list reviewed quarterly
- New vulnerabilities added to test suite
- Security scans run weekly

## Resources

- [Performance Baselines](./PERFORMANCE_BASELINES.md)
- [Security Test Results](./SECURITY_TEST_RESULTS.md)
- [Test Utilities README](../../tests/gateway/README.md)
- [QA Worker Tasks](../gateway-integration/tasks/QA_WORKER_TASKS.md)

## Contact

For questions about testing strategy:
- See test documentation in `tests/gateway/README.md`
- Review test code for examples
- Check CI/CD logs for failures

---

**Last Updated**: November 27, 2025
**Test Suite Version**: 2.0 (Bonus Tasks Complete)
