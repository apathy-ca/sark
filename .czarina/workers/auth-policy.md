# Workstream 1: Auth & Policy Tests

**Worker ID**: auth-policy
**Branch**: feat/tests-auth-policy
**Duration**: 2-3 days
**Target Coverage**: 20 modules (0% → 85%)

---

## Objective

Write comprehensive tests for authentication, authorization, and policy services to achieve 85% code coverage.

---

## Modules to Test (20 modules)

### Authentication (8 modules)
1. `src/sark/services/auth/jwt.py` (73 lines, 0% coverage)
2. `src/sark/services/auth/api_key.py` (75 lines, 0% coverage)
3. `src/sark/services/auth/api_keys.py` (132 lines, 0% coverage)
4. `src/sark/services/auth/session.py` (97 lines, 0% coverage)
5. `src/sark/services/auth/sessions.py` (148 lines, 0% coverage)
6. `src/sark/services/auth/tokens.py` (88 lines, 0% coverage)
7. `src/sark/services/auth/user_context.py` (19 lines, 0% coverage)
8. `src/sark/services/auth/providers/base.py` (29 lines, 0% coverage)

### Auth Providers (3 modules)
9. `src/sark/services/auth/providers/ldap.py` (127 lines, 0% coverage)
10. `src/sark/services/auth/providers/oidc.py` (95 lines, 0% coverage)
11. `src/sark/services/auth/providers/saml.py` (92 lines, 0% coverage)

### Policy Services (9 modules)
12. `src/sark/services/policy/audit.py` (172 lines, 0% coverage)
13. `src/sark/services/policy/cache.py` (259 lines, 0% coverage)
14. `src/sark/services/policy/metrics.py` (116 lines, 0% coverage)
15. `src/sark/services/policy/opa_client.py` (216 lines, 0% coverage)
16. `src/sark/services/policy/plugins.py` (135 lines, 0% coverage)
17. `src/sark/services/policy/policy_service.py` (58 lines, 0% coverage)
18. `src/sark/services/policy/sandbox.py` (109 lines, 0% coverage)
19. `src/sark/api/v1/auth.py` (182 lines, 0% coverage)
20. `src/sark/api/v1/policies.py` (148 lines, 0% coverage)

---

## Test Strategy

### 1. JWT Authentication Tests
**File**: `tests/unit/auth/test_jwt.py`

**Coverage Goals**:
- Token generation and validation
- Token expiration handling
- Invalid token detection
- Signature verification
- Claims extraction
- Refresh token logic

**Example Test**:
```python
@pytest.mark.asyncio
async def test_jwt_token_generation():
    """Test JWT token generation with valid claims."""
    token = create_access_token(
        data={"sub": "user123", "role": "admin"},
        expires_delta=timedelta(minutes=15)
    )
    assert token is not None

    payload = decode_token(token)
    assert payload["sub"] == "user123"
    assert payload["role"] == "admin"
```

### 2. API Key Tests
**File**: `tests/unit/auth/test_api_keys.py`

**Coverage Goals**:
- API key creation
- Key hashing and validation
- Key rotation
- Expiration handling
- Revocation
- Scope validation

### 3. Session Management Tests
**File**: `tests/unit/auth/test_sessions.py`

**Coverage Goals**:
- Session creation and storage (Valkey)
- Session validation
- Session expiration
- Concurrent session limits
- Session revocation
- Session data persistence

### 4. Auth Provider Tests
**Files**:
- `tests/unit/auth/providers/test_ldap.py`
- `tests/unit/auth/providers/test_oidc.py`
- `tests/unit/auth/providers/test_saml.py`

**Coverage Goals**:
- LDAP: Connection, bind, user search, group membership
- OIDC: Authorization flow, token exchange, userinfo
- SAML: Assertion validation, attribute extraction

### 5. OPA Policy Tests
**File**: `tests/unit/policy/test_opa_client.py`

**Coverage Goals**:
- Policy evaluation
- Decision caching
- Input validation
- Error handling
- Timeout handling
- Retry logic

### 6. Policy Cache Tests
**File**: `tests/unit/policy/test_policy_cache.py`

**Coverage Goals**:
- Cache hit/miss
- TTL expiration
- Cache invalidation
- Valkey integration
- Performance benchmarks

### 7. Policy Audit Tests
**File**: `tests/unit/policy/test_policy_audit.py`

**Coverage Goals**:
- Audit event logging
- TimescaleDB integration
- Batch processing
- Event filtering
- Compliance reporting

---

## Fixtures to Use

From `tests/fixtures/integration_docker.py`:
- `postgres_connection` - For auth database tests
- `valkey_connection` - For session and cache tests
- `opa_client` - For policy evaluation tests
- `initialized_db` - For full auth flow tests

---

## Success Criteria

- ✅ All 20 modules have ≥85% code coverage
- ✅ All tests pass
- ✅ Tests are deterministic (no flaky tests)
- ✅ Tests use proper fixtures (no hardcoded connections)
- ✅ Tests are fast (unit tests <100ms each)
- ✅ Integration tests use docker services
- ✅ All edge cases covered (errors, timeouts, invalid input)

---

## Test Pattern Example

```python
import pytest
from unittest.mock import AsyncMock, patch
from sark.services.auth.jwt import create_access_token, decode_token

class TestJWTAuthentication:
    """Test JWT token generation and validation."""

    def test_create_access_token(self):
        """Test creating a valid access token."""
        token = create_access_token(
            data={"sub": "user123"},
            expires_delta=timedelta(minutes=15)
        )
        assert token is not None
        assert isinstance(token, str)

    def test_decode_valid_token(self):
        """Test decoding a valid token."""
        token = create_access_token(data={"sub": "user123"})
        payload = decode_token(token)
        assert payload["sub"] == "user123"

    def test_decode_expired_token(self):
        """Test that expired tokens raise exception."""
        token = create_access_token(
            data={"sub": "user123"},
            expires_delta=timedelta(seconds=-1)
        )
        with pytest.raises(TokenExpiredError):
            decode_token(token)

    def test_decode_invalid_token(self):
        """Test that invalid tokens raise exception."""
        with pytest.raises(InvalidTokenError):
            decode_token("invalid.token.here")
```

---

## Priority Order

1. **High Priority** (Day 1):
   - JWT tests (core auth)
   - API key tests
   - OPA client tests

2. **Medium Priority** (Day 2):
   - Session management
   - Policy cache
   - Auth providers (OIDC, LDAP)

3. **Low Priority** (Day 3):
   - SAML provider
   - Policy plugins
   - Policy audit
   - API endpoint tests

---

## Deliverables

1. Test files created for all 20 modules
2. Coverage report showing 85%+ coverage
3. All tests passing in CI
4. Documentation updates (if needed)
5. Commit message following format:
   ```
   test: Add comprehensive auth & policy test suite

   - Add JWT authentication tests (85% coverage)
   - Add API key management tests (87% coverage)
   - Add session management tests (90% coverage)
   - Add auth provider tests (LDAP, OIDC, SAML)
   - Add OPA policy client tests (88% coverage)
   - Add policy cache tests (92% coverage)
   - Add policy audit tests (85% coverage)

   Total: 20 modules, 500+ tests, 85%+ coverage

   Part of Phase 3 Workstream 1 (v1.3.1 implementation plan)
   ```

---

## Notes

- Use existing test patterns from `tests/chaos/` as reference
- Follow pytest best practices (AAA pattern: Arrange, Act, Assert)
- Mock external dependencies (LDAP servers, OIDC providers)
- Use `pytest.mark.asyncio` for async tests
- Use `pytest.mark.integration` for integration tests
- Keep unit tests isolated and fast
