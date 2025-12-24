# Authentication Provider Testing Guide

## Overview

This guide explains the comprehensive testing infrastructure for SARK authentication providers (LDAP, OIDC, SAML). The test infrastructure uses Docker containers to provide real services for integration testing, ensuring high-quality, realistic test coverage.

## Test Structure

```
tests/
├── fixtures/
│   ├── docker-compose.ldap.yml    # LDAP test server
│   ├── docker-compose.oidc.yml    # OIDC mock server
│   ├── docker-compose.saml.yml    # SAML IdP test server
│   ├── ldap_docker.py             # LDAP fixtures
│   ├── oidc_docker.py             # OIDC fixtures
│   └── saml_docker.py             # SAML fixtures
├── unit/auth/providers/
│   ├── test_ldap_provider.py      # LDAP unit tests
│   ├── test_oidc_provider.py      # OIDC unit tests
│   └── test_saml_provider.py      # SAML unit tests
└── integration/auth/
    ├── test_ldap_integration.py   # LDAP integration tests
    ├── test_oidc_integration.py   # OIDC integration tests
    └── test_saml_integration.py   # SAML integration tests
```

## Prerequisites

### Required Software

1. **Python 3.11+** - Core testing framework
2. **Docker & Docker Compose** - Container runtime for test services
3. **pytest-docker** - Docker integration for pytest

### Installation

```bash
# Install development dependencies
pip install -e ".[dev]"

# Install pytest-docker if not already installed
pip install pytest-docker
```

## Test Infrastructure Components

### LDAP Test Infrastructure

**Docker Image:** `osixia/openldap:1.5.0`

**Features:**
- Pre-configured test users (testuser, admin, jdoe)
- Group memberships (developers, admins)
- Full LDAP directory structure

**Test Users:**
```
testuser / testpass (member of: developers)
admin / adminpass (member of: admins)
jdoe / password123 (member of: developers)
```

### OIDC Test Infrastructure

**Docker Image:** `ghcr.io/navikt/mock-oauth2-server:0.5.8`

**Features:**
- Full OIDC discovery document
- Token generation endpoints
- Userinfo endpoint
- JWKS endpoint

**Endpoints:**
- Discovery: `http://localhost:8080/default/.well-known/openid-configuration`
- Authorization: `http://localhost:8080/default/authorize`
- Token: `http://localhost:8080/default/token`
- Userinfo: `http://localhost:8080/default/userinfo`

### SAML Test Infrastructure

**Docker Image:** `kristophjunge/test-saml-idp:1.15`

**Features:**
- SimpleSAMLphp-based test IdP
- Pre-configured test users
- Full SAML 2.0 support

**Test Users:**
```
user1 / user1pass
user2 / user2pass
```

**Endpoints:**
- SSO: `http://localhost:8080/simplesaml/saml2/idp/SSOService.php`
- Metadata: `http://localhost:8080/simplesaml/saml2/idp/metadata.php`

## Running Tests

### Run All Auth Provider Tests

```bash
# All auth provider tests
pytest tests/unit/auth/providers/ tests/integration/auth/ -v

# With coverage report
pytest tests/unit/auth/providers/ tests/integration/auth/ --cov=src/sark/services/auth/providers --cov-report=html
```

### Run Specific Provider Tests

```bash
# LDAP only
pytest tests/unit/auth/providers/test_ldap_provider.py tests/integration/auth/test_ldap_integration.py -v

# OIDC only
pytest tests/unit/auth/providers/test_oidc_provider.py tests/integration/auth/test_oidc_integration.py -v

# SAML only
pytest tests/unit/auth/providers/test_saml_provider.py tests/integration/auth/test_saml_integration.py -v
```

### Run Only Integration Tests

```bash
# All integration tests (requires Docker)
pytest tests/integration/auth/ -v -m integration

# Specific provider integration tests
pytest tests/integration/auth/test_ldap_integration.py -v
pytest tests/integration/auth/test_oidc_integration.py -v
pytest tests/integration/auth/test_saml_integration.py -v
```

### Run Only Unit Tests

```bash
# All unit tests (fast, no Docker required)
pytest tests/unit/auth/providers/ -v -m "not integration"
```

## Test Markers

Use pytest markers to filter tests:

```bash
# Run only integration tests
pytest -m integration

# Skip integration tests (for CI without Docker)
pytest -m "not integration"

# Run only auth-related tests
pytest -m auth
```

## Docker Container Management

### Starting Test Containers Manually

```bash
# LDAP
docker-compose -f tests/fixtures/docker-compose.ldap.yml up -d

# OIDC
docker-compose -f tests/fixtures/docker-compose.oidc.yml up -d

# SAML
docker-compose -f tests/fixtures/docker-compose.saml.yml up -d
```

### Stopping Test Containers

```bash
# Stop specific service
docker-compose -f tests/fixtures/docker-compose.ldap.yml down

# Stop all test containers
docker stop test_ldap test_oidc test_saml_idp
docker rm test_ldap test_oidc test_saml_idp
```

### Troubleshooting Container Issues

```bash
# Check container logs
docker logs test_ldap
docker logs test_oidc
docker logs test_saml_idp

# Check container health
docker ps | grep test_

# Restart a container
docker restart test_ldap
```

## Coverage Goals

**Target Coverage:** 85%+ for each provider

**Current Coverage Status:**
- LDAP: Target 85%+ (was 32.02%)
- OIDC: Target 85%+ (was 28.21%)
- SAML: Target 85%+ (was 22.47%)

### Generating Coverage Reports

```bash
# Generate HTML coverage report
pytest tests/unit/auth/providers/ tests/integration/auth/ \
    --cov=src/sark/services/auth/providers \
    --cov-report=html \
    --cov-report=term-missing

# View report
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html  # Windows
```

## Writing New Tests

### Unit Test Template

```python
import pytest
from sark.services.auth.providers.example import ExampleProvider, ExampleProviderConfig

class TestExampleProvider:
    @pytest.fixture
    def config(self):
        return ExampleProviderConfig(name="test", ...)

    @pytest.fixture
    def provider(self, config):
        return ExampleProvider(config)

    @pytest.mark.asyncio
    async def test_authenticate_success(self, provider):
        result = await provider.authenticate("user", "password")
        assert result.success is True
```

### Integration Test Template

```python
import pytest

pytest_plugins = ["tests.fixtures.example_docker"]

@pytest.mark.integration
class TestExampleIntegration:
    @pytest.mark.asyncio
    async def test_real_authentication(self, example_provider):
        result = await example_provider.authenticate("testuser", "testpass")
        assert result.success is True
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Auth Provider Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      ldap:
        image: osixia/openldap:1.5.0
        ports:
          - 389:389

      oidc:
        image: ghcr.io/navikt/mock-oauth2-server:0.5.8
        ports:
          - 8080:8080

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Run auth provider tests
        run: pytest tests/unit/auth/providers/ tests/integration/auth/ -v --cov

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Common Issues and Solutions

### Issue: Docker containers not starting

**Solution:**
```bash
# Check Docker is running
docker ps

# Check port conflicts
lsof -i :389  # LDAP
lsof -i :8080 # OIDC/SAML

# Remove old containers
docker rm -f test_ldap test_oidc test_saml_idp
```

### Issue: Tests hanging waiting for containers

**Solution:**
```bash
# Increase timeout in pytest.ini
[pytest]
docker_timeout = 120

# Or set environment variable
export PYTEST_DOCKER_TIMEOUT=120
```

### Issue: Connection refused errors

**Solution:**
- Ensure containers have fully started (check health checks)
- Wait a few seconds after container starts
- Check firewall settings
- Verify port mappings are correct

### Issue: Fixture import errors

**Solution:**
```bash
# Ensure pytest_plugins is set correctly
pytest_plugins = ["tests.fixtures.ldap_docker"]

# Or import fixtures explicitly
from tests.fixtures.ldap_docker import ldap_provider
```

## Performance Optimization

### Parallel Test Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (4 workers)
pytest tests/unit/auth/providers/ -n 4

# Auto-detect CPU count
pytest tests/unit/auth/providers/ -n auto
```

### Test Caching

```bash
# Run only failed tests from last run
pytest --lf

# Run failed tests first, then all
pytest --ff
```

## Best Practices

1. **Use Session-Scoped Fixtures** - Docker containers should be session-scoped to avoid restart overhead
2. **Test Isolation** - Each test should be independent and not rely on state from previous tests
3. **Cleanup** - Always clean up resources in fixtures
4. **Realistic Data** - Use realistic test data that mirrors production scenarios
5. **Error Cases** - Test both success and failure paths
6. **Documentation** - Document test intent and expected behavior

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-docker Documentation](https://github.com/avast/pytest-docker)
- [LDAP Testing Guide](https://ldap.com/testing-ldap-applications/)
- [OIDC Testing](https://openid.net/developers/how-to-test/)
- [SAML Testing](https://www.samltool.com/)

## Support

For questions or issues with the auth provider test infrastructure:
1. Check this README
2. Review existing test files for examples
3. Check container logs for errors
4. Consult the main SARK documentation
5. Open an issue on GitHub
