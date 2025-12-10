# SARK Testing Guide

## Overview

This directory contains comprehensive tests for the SARK (Security Audit and Resource Kontroler) system. The test suite is organized into multiple layers to ensure thorough coverage of all functionality.

## Test Organization

```
tests/
├── unit/                      # Unit tests for individual components
│   ├── auth/                  # Authentication tests
│   │   └── providers/         # Auth provider unit tests (52 tests)
│   ├── gateway/               # Gateway component tests
│   ├── services/              # Service layer tests
│   └── ...
├── integration/               # Integration tests
│   └── auth/                  # Auth provider integration tests (30 tests)
├── e2e/                       # End-to-end scenario tests
├── fixtures/                  # Test fixtures and Docker infrastructure
│   ├── ldap_docker.py         # LDAP Docker container fixtures
│   └── docker-compose.ldap.yml
├── performance/               # Performance and load tests
└── security/                  # Security-focused tests
```

## Test Categories

### Unit Tests

Unit tests focus on testing individual components in isolation with mocked dependencies.

**Auth Providers** (`tests/unit/auth/providers/`)
- **LDAP** (18 tests): Configuration, authentication, search, bind, groups, health checks
- **SAML** (20 tests): Configuration, XML parsing, user info extraction, authentication, metadata
- **OIDC** (14 tests): Configuration, discovery, authentication, token validation, user info

**Total Unit Tests: 52**

### Integration Tests

Integration tests verify components work correctly with real dependencies (databases, Docker containers, etc.).

**LDAP Integration** (`tests/integration/auth/test_ldap_integration.py`) - **30 tests**:

1. **Basic Authentication** (6 tests)
   - Valid user authentication
   - Invalid password handling
   - Nonexistent user handling
   - Multiple user authentication
   - Empty username/password validation

2. **Group Membership** (3 tests)
   - User groups retrieval
   - Admin groups verification
   - Multiple group membership

3. **User Attributes** (4 tests)
   - Attribute extraction
   - Email attribute handling
   - Display name extraction
   - Consistent user ID generation

4. **Search Functionality** (2 tests)
   - User search by UID
   - Nonexistent user search

5. **Bind Operations** (3 tests)
   - Valid credential binding
   - Invalid credential binding
   - Nonexistent user binding

6. **Group Search** (2 tests)
   - User group retrieval
   - Admin group retrieval

7. **Health Checks** (2 tests)
   - Successful health check
   - Failed health check with invalid server

8. **Concurrency** (2 tests)
   - Concurrent authentication requests
   - Mixed success/failure concurrent requests

9. **Edge Cases** (6 tests)
   - Special characters in passwords
   - Case-sensitive usernames
   - Token validation not supported
   - User info retrieval

**Total Integration Tests: 30**

## Running Tests

### Prerequisites

```bash
# Install test dependencies
pip install -e ".[dev]"

# For LDAP integration tests, install pytest-docker
pip install pytest-docker

# Ensure Docker is running
docker ps
```

### Running All Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html
```

### Running Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/

# Auth provider unit tests
pytest tests/unit/auth/providers/

# Integration tests (requires Docker)
pytest tests/integration/ -m integration

# LDAP integration tests specifically
pytest tests/integration/auth/test_ldap_integration.py

# Specific test class
pytest tests/unit/auth/providers/test_ldap_provider.py::TestLDAPProvider

# Specific test
pytest tests/unit/auth/providers/test_ldap_provider.py::TestLDAPProvider::test_authenticate_success
```

### Test Markers

Tests are marked with pytest markers for selective execution:

```bash
# Run only integration tests
pytest -m integration

# Run only unit tests
pytest -m unit

# Exclude slow tests
pytest -m "not slow"

# Run only LDAP-related tests
pytest -k ldap
```

## LDAP Integration Testing with Docker

### Setup

The LDAP integration tests use a Docker container running OpenLDAP (osixia/openldap:1.5.0).

**Docker Compose Configuration**: `tests/fixtures/docker-compose.ldap.yml`

**Test Fixtures**: `tests/fixtures/ldap_docker.py`

### Test Data

The LDAP container is automatically populated with test data:

**Users**:
- `testuser` (password: `testpass`) - Member of `developers` group
- `admin` (password: `adminpass`) - Member of `admins` group
- `jdoe` (password: `password123`) - Member of `developers` group

**Groups**:
- `developers` - Contains testuser and jdoe
- `admins` - Contains admin

**Base DN**: `dc=example,dc=com`

### Running LDAP Integration Tests

```bash
# Run all LDAP integration tests
pytest tests/integration/auth/test_ldap_integration.py -v

# Run specific test class
pytest tests/integration/auth/test_ldap_integration.py::TestLDAPIntegrationBasic -v

# Run with Docker logs
pytest tests/integration/auth/test_ldap_integration.py -v -s
```

### Troubleshooting LDAP Tests

If LDAP integration tests fail:

1. **Check Docker is running**:
   ```bash
   docker ps
   ```

2. **Check LDAP container health**:
   ```bash
   docker ps | grep test_ldap
   docker logs test_ldap
   ```

3. **Test LDAP connectivity manually**:
   ```bash
   ldapsearch -x -H ldap://localhost:389 -b dc=example,dc=com \
     -D "cn=admin,dc=example,dc=com" -w admin
   ```

4. **Clean up containers**:
   ```bash
   docker-compose -f tests/fixtures/docker-compose.ldap.yml down -v
   ```

## Test Coverage

Current test coverage focuses on authentication providers with comprehensive unit and integration testing.

### Coverage Goals

- **Overall**: 85%+ code coverage
- **Auth Providers**: 90%+ coverage ✅
- **Gateway**: 80%+ coverage (in progress)
- **Services**: 85%+ coverage (in progress)

### Generating Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# View report
open htmlcov/index.html

# Generate terminal report
pytest --cov=src --cov-report=term-missing

# Generate XML report (for CI/CD)
pytest --cov=src --cov-report=xml
```

## Continuous Integration

Tests are run automatically in CI/CD pipelines:

### Required Checks
- All unit tests must pass
- Code coverage must meet thresholds
- No new linting errors
- Security checks pass

### Docker in CI
Integration tests requiring Docker are run in CI environments with Docker support.

## Writing New Tests

### Unit Test Template

```python
"""Tests for <component>."""

import pytest
from unittest.mock import patch, Mock

from sark.<module> import <Component>


class Test<Component>:
    """Test suite for <Component>."""

    @pytest.fixture
    def component(self):
        """Create component instance for testing."""
        return <Component>(...)

    @pytest.mark.asyncio
    async def test_<functionality>(self, component):
        """Test <specific functionality>."""
        # Arrange
        ...

        # Act
        result = await component.method(...)

        # Assert
        assert result.success is True
        assert result.value == expected
```

### Integration Test Template

```python
"""Integration tests for <component>."""

import pytest

# Import Docker fixtures if needed
pytest_plugins = ["tests.fixtures.<fixture_module>"]


@pytest.mark.integration
class Test<Component>Integration:
    """Integration tests for <Component>."""

    @pytest.mark.asyncio
    async def test_<functionality>_integration(self, component_fixture):
        """Test <functionality> with real dependencies."""
        # Test with real database/service/etc
        ...
```

## Best Practices

1. **Test Isolation**: Each test should be independent and not rely on state from other tests
2. **Meaningful Names**: Test names should clearly describe what is being tested
3. **AAA Pattern**: Arrange, Act, Assert structure
4. **Mock External Dependencies**: Unit tests should mock external services
5. **Use Fixtures**: Leverage pytest fixtures for common setup
6. **Test Edge Cases**: Include tests for error conditions and edge cases
7. **Async Tests**: Use `@pytest.mark.asyncio` for async code
8. **Documentation**: Include docstrings explaining what each test verifies

## Test Infrastructure

### Pytest Plugins Used

- `pytest-asyncio`: Async test support
- `pytest-cov`: Coverage reporting
- `pytest-docker`: Docker container management
- `pytest-mock`: Mocking utilities
- `pytest-httpx`: HTTP mocking

### Custom Fixtures

Located in `tests/fixtures/`:
- `ldap_docker.py`: LDAP Docker container fixtures
- More fixtures coming for SAML, OIDC, etc.

## Future Test Development

### Planned Additions

1. **SAML Integration Tests** (pending)
   - Certificate handling
   - XML signature validation
   - Multiple IdP configurations

2. **OIDC Integration Tests** (pending)
   - Time-based token expiry (with freezegun)
   - JWKS validation
   - Multiple provider configurations

3. **E2E Scenario Tests** (pending)
   - Complete authentication flows
   - Multi-layer authorization
   - Audit logging verification
   - Performance under load

4. **Gateway Tests** (pending)
   - HTTP/SSE transport tests
   - Authorization flow tests
   - Parameter filtering tests

## Reporting Issues

If you encounter test failures:

1. Check if the issue is environmental (Docker, network, etc.)
2. Run tests in verbose mode: `pytest -vv`
3. Check test logs and error messages
4. Verify all dependencies are installed
5. Report persistent failures with full error output

## Contributing

When adding new tests:

1. Follow existing patterns and structure
2. Add appropriate markers (`@pytest.mark.integration`, etc.)
3. Update this README with new test categories
4. Ensure tests pass locally before committing
5. Add fixtures to `tests/fixtures/` for reusable test infrastructure

## Contact

For questions about testing infrastructure, contact the QA team or refer to the main SARK documentation.
