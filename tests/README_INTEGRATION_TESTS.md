# Integration Testing Guide

## Overview

This guide explains the comprehensive Docker-based integration testing infrastructure for SARK. The infrastructure provides real services (PostgreSQL, Redis, OPA, etc.) for realistic integration testing.

## Test Infrastructure

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              Integration Test Infrastructure                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────┐ ┌─────┐ ┌─────────┐       │
│  │PostgreSQL│ │TimescaleDB│ │Redis│ │ OPA │ │gRPC Mock│       │
│  │   :5433  │ │   :5434   │ │:6380│ │:8181│ │  :50051 │       │
│  └────┬─────┘ └─────┬─────┘ └──┬───┘ └──┬──┘ └────┬────┘       │
│       │             │           │        │         │             │
│       └─────────────┴───────────┴────────┴─────────┘             │
│                            │                                      │
│                     ┌──────▼───────┐                             │
│                     │pytest-docker │                             │
│                     │   Fixtures   │                             │
│                     └──────┬───────┘                             │
│                            │                                      │
│                ┌───────────┴────────────┐                        │
│                │  Integration Tests     │                        │
│                │  - API Tests          │                        │
│                │  - Auth Tests         │                        │
│                │  - Policy Tests       │                        │
│                │  - Gateway Tests      │                        │
│                │  - Database Tests     │                        │
│                └────────────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

### Services Provided

1. **PostgreSQL** (port 5433)
   - Main application database
   - Test data isolation with tmpfs
   - Automatic schema initialization

2. **TimescaleDB** (port 5434)
   - Audit log storage
   - Time-series data testing
   - Hypertable support

3. **Redis** (port 6380)
   - Caching layer
   - Session storage
   - Policy cache

4. **OPA** (port 8181)
   - Policy engine
   - Authorization decisions
   - Policy validation

5. **gRPC Mock Server** (port 50051)
   - gRPC adapter testing
   - Protocol testing
   - Stub configuration

## Prerequisites

### Required Software

1. **Python 3.11+**
2. **Docker & Docker Compose**
3. **pytest-docker** - `pip install pytest-docker`
4. **Development dependencies** - `pip install -e ".[dev]"`

### Port Requirements

Ensure the following ports are available:
- 5433 (PostgreSQL)
- 5434 (TimescaleDB)
- 6380 (Redis)
- 8181 (OPA)
- 50051 (gRPC Mock)

## Quick Start

### 1. Install Dependencies

```bash
pip install -e ".[dev]"
pip install pytest-docker
```

### 2. Run All Integration Tests

```bash
# Full automated run (start services, test, cleanup)
./scripts/run_integration_tests.sh run

# With coverage report
./scripts/run_integration_tests.sh run coverage
```

### 3. Manual Service Management

```bash
# Start services for manual testing/debugging
./scripts/run_integration_tests.sh start

# Run tests against running services
pytest tests/integration/ -v

# Stop services when done
./scripts/run_integration_tests.sh stop
```

## Running Tests

### Run All Integration Tests

```bash
./scripts/run_integration_tests.sh run
```

### Run Specific Test Categories

```bash
# API integration tests
./scripts/run_integration_tests.sh run api

# Authentication tests
./scripts/run_integration_tests.sh run auth

# Policy engine tests
./scripts/run_integration_tests.sh run policy

# Gateway tests
./scripts/run_integration_tests.sh run gateway

# Database tests
./scripts/run_integration_tests.sh run database

# Fast tests only (exclude slow ones)
./scripts/run_integration_tests.sh run fast
```

### Run with Coverage

```bash
./scripts/run_integration_tests.sh run coverage
```

### Using Docker Services Directly

```bash
# Start services
./scripts/run_integration_tests.sh start

# Run specific test files
pytest tests/integration/test_api_integration.py -v
pytest tests/integration/test_policy_integration.py -v

# Run with markers
pytest tests/integration/ -v -m "not slow"

# Stop services
./scripts/run_integration_tests.sh stop
```

## Service Management

### Check Service Status

```bash
./scripts/run_integration_tests.sh status
```

### View Service Logs

```bash
# All services
./scripts/run_integration_tests.sh logs

# Specific service
./scripts/run_integration_tests.sh logs postgres
./scripts/run_integration_tests.sh logs redis
./scripts/run_integration_tests.sh logs opa
```

### Interactive Shells

```bash
# PostgreSQL shell
./scripts/run_integration_tests.sh shell postgres

# Redis shell
./scripts/run_integration_tests.sh shell redis

# TimescaleDB shell
./scripts/run_integration_tests.sh shell timescale
```

## Using Docker Fixtures in Tests

### Method 1: Import in Test File

```python
"""Integration test using Docker services."""

import pytest

# Import Docker fixtures
pytest_plugins = ["tests.fixtures.integration_docker"]


@pytest.mark.integration
class TestDatabaseIntegration:
    @pytest.mark.asyncio
    async def test_postgres_connection(self, postgres_connection):
        """Test PostgreSQL connection."""
        async with postgres_connection.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            assert result == 1

    @pytest.mark.asyncio
    async def test_redis_operations(self, redis_connection):
        """Test Redis operations."""
        await redis_connection.set("test_key", "test_value")
        value = await redis_connection.get("test_key")
        assert value == "test_value"

    def test_opa_client(self, opa_client):
        """Test OPA client."""
        assert opa_client is not None
```

### Method 2: Use Combined Fixture

```python
"""Integration test using all services."""

import pytest

pytest_plugins = ["tests.fixtures.integration_docker"]


@pytest.mark.integration
class TestFullStack:
    def test_all_services(self, all_services):
        """Test that all services are available."""
        assert "postgres" in all_services
        assert "redis" in all_services
        assert "opa" in all_services
        assert "timescaledb" in all_services
        assert "grpc_mock" in all_services
```

### Available Fixtures

#### Service Fixtures (session-scoped)
- `postgres_service` - PostgreSQL connection details
- `timescaledb_service` - TimescaleDB connection details
- `redis_service` - Redis connection details
- `opa_service` - OPA connection details
- `grpc_mock_service` - gRPC mock server details
- `all_services` - All service details combined

#### Connection Fixtures (function-scoped)
- `postgres_connection` - Async PostgreSQL connection pool
- `timescaledb_connection` - Async TimescaleDB connection pool
- `redis_connection` - Async Redis client
- `opa_client` - OPA client instance

#### Helper Fixtures
- `initialized_db` - PostgreSQL with initialized schema
- `clean_redis` - Redis with flush before/after test

## Test Organization

### Current Integration Tests

```
tests/integration/
├── auth/
│   ├── test_ldap_integration.py       # LDAP auth (65 tests)
│   ├── test_oidc_integration.py       # OIDC auth (20+ tests)
│   └── test_saml_integration.py       # SAML auth (25+ tests)
├── gateway/
│   ├── test_audit_integration.py      # Audit logging
│   ├── test_gateway_authorization_flow.py
│   ├── test_gateway_e2e.py           # End-to-end flows
│   ├── test_multi_server_orchestration.py
│   ├── test_policy_integration.py    # Policy enforcement
│   └── test_tool_chains.py
├── v2/
│   ├── test_adapter_integration.py   # Protocol adapters
│   ├── test_federation_flow.py       # Federation
│   └── test_multi_protocol.py        # Multi-protocol
├── test_api_integration.py            # API endpoints
├── test_auth_integration.py           # Auth flows
├── test_datadog_integration.py        # Datadog SIEM
├── test_large_scale_operations.py     # Performance/scale
├── test_policy_integration.py         # Policy engine
├── test_siem_integration.py           # SIEM integration
├── test_siem_load.py                  # SIEM load testing
└── test_splunk_integration.py         # Splunk SIEM
```

## Coverage Goals

**Target:** 90%+ integration test pass rate

**Baseline:** 27% (32/119 passing)

**Strategy:**
1. Fix fixture dependencies (mocks → real services)
2. Fix database initialization issues
3. Fix OPA policy loading
4. Fix service connection issues
5. Add missing test cases

## Troubleshooting

### Services Won't Start

```bash
# Check Docker is running
docker ps

# Check for port conflicts
lsof -i :5433  # PostgreSQL
lsof -i :6380  # Redis
lsof -i :8181  # OPA

# Force cleanup and restart
./scripts/run_integration_tests.sh stop
./scripts/run_integration_tests.sh start
```

### Tests Hang or Timeout

```bash
# Check service health
./scripts/run_integration_tests.sh status

# View service logs
./scripts/run_integration_tests.sh logs postgres

# Increase timeouts in pytest
pytest tests/integration/ --timeout=300 -v
```

### Database Connection Errors

```bash
# Verify PostgreSQL is accessible
docker exec sark_test_postgres psql -U sark_test -d sark_test -c "SELECT 1"

# Check connection from host
psql -h localhost -p 5433 -U sark_test -d sark_test

# Reinitialize database
./scripts/run_integration_tests.sh restart
```

### Redis Connection Errors

```bash
# Verify Redis is accessible
docker exec sark_test_redis redis-cli ping

# Test from host
redis-cli -p 6380 ping

# Flush and restart
docker exec sark_test_redis redis-cli FLUSHALL
```

### OPA Policy Errors

```bash
# Check OPA health
curl http://localhost:8181/health

# List loaded policies
curl http://localhost:8181/v1/policies

# View OPA logs
./scripts/run_integration_tests.sh logs opa
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
          pip install pytest-docker

      - name: Run integration tests
        run: |
          ./scripts/run_integration_tests.sh run coverage

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

### Docker Compose in CI

The `docker-compose.integration.yml` file is optimized for CI:
- Uses tmpfs for database storage (faster, no cleanup needed)
- Disables Redis persistence
- Shorter health check intervals
- Automatic container cleanup

## Performance

### Test Execution Speed

- **Service Startup:** ~10-15 seconds (all services)
- **Average Test:** 50-200ms
- **Full Suite:** ~5-10 minutes (depending on test count)

### Optimization Tips

1. **Use tmpfs for databases** (already configured)
2. **Run fast tests during development**
   ```bash
   ./scripts/run_integration_tests.sh run fast
   ```
3. **Keep services running** during development
   ```bash
   ./scripts/run_integration_tests.sh start
   pytest tests/integration/test_api_integration.py -v
   # Services stay running for next test run
   ```
4. **Parallel execution** (with xdist)
   ```bash
   pytest tests/integration/ -n auto
   ```

## Best Practices

1. **Always use fixtures** - Don't hardcode connection strings
2. **Clean up after tests** - Use fixtures with cleanup
3. **Isolate test data** - Each test should be independent
4. **Use transactions** - Rollback database changes when possible
5. **Mark slow tests** - Use `@pytest.mark.slow` for long-running tests
6. **Mock external services** - SIEM, external APIs (use real only when needed)

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-docker Documentation](https://github.com/avast/pytest-docker)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Testing](https://www.postgresql.org/docs/current/regress.html)
- [Redis Testing](https://redis.io/docs/manual/testing/)
- [OPA Testing](https://www.openpolicyagent.org/docs/latest/policy-testing/)

## Support

For issues with integration test infrastructure:
1. Check this README
2. Review service logs: `./scripts/run_integration_tests.sh logs`
3. Check service status: `./scripts/run_integration_tests.sh status`
4. Try restart: `./scripts/run_integration_tests.sh restart`
5. Open an issue on GitHub

## Summary

The integration test infrastructure provides:
- ✅ Real services via Docker (not mocks)
- ✅ Easy service management with scripts
- ✅ Fast test execution with tmpfs
- ✅ CI/CD ready
- ✅ Comprehensive fixtures
- ✅ Good documentation

**Next steps:** Run the tests and fix failures to achieve 90%+ pass rate!
