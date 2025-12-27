# Workstream 4: Services & API Tests

**Worker ID**: services-api
**Branch**: feat/tests-services-api
**Duration**: 2-3 days
**Target Coverage**: 18 modules (0-20% → 85%)

---

## Objective

Write comprehensive tests for core services, SIEM integration, rate limiting, bulk operations, and API routers to achieve 85% code coverage.

---

## Modules to Test (18 modules)

### Audit & SIEM (5 modules)
1. `src/sark/services/audit/audit_service.py` (current: low coverage)
2. `src/sark/services/audit/gateway_audit.py` (current: low coverage)
3. `src/sark/services/siem/splunk.py` (current: 0% coverage)
4. `src/sark/services/siem/datadog.py` (current: 0% coverage)
5. `src/sark/services/siem/gateway_forwarder.py` (61 lines, 27% coverage)

### Rate Limiting & Bulk (2 modules)
6. `src/sark/services/rate_limiter.py` (77 lines, 0% coverage)
7. `src/sark/services/bulk/__init__.py` (143 lines, 0% coverage)

### Cost Tracking (4 modules)
8. `src/sark/services/cost/estimator.py` (48 lines, 0% coverage)
9. `src/sark/services/cost/tracker.py` (66 lines, 0% coverage)
10. `src/sark/services/cost/providers/anthropic.py` (65 lines, 0% coverage)
11. `src/sark/services/cost/providers/openai.py` (66 lines, 0% coverage)

### Database (3 modules)
12. `src/sark/db/pools.py` (current: low coverage)
13. `src/sark/db/session.py` (current: low coverage)
14. `src/sark/db/migrations.py` (current: 0% coverage)

### API Routers (4 modules)
15. `src/sark/api/v1/admin.py` (current: 0% coverage)
16. `src/sark/api/v1/audit.py` (current: 0% coverage)
17. `src/sark/api/v1/users.py` (current: 0% coverage)
18. `src/sark/api/middleware/rate_limit.py` (current: 0% coverage)

---

## Test Strategy

### 1. Audit Service Tests
**File**: `tests/unit/audit/test_audit_service.py`

**Coverage Goals**:
- Event logging
- Event batching
- TimescaleDB integration
- Event filtering
- Event querying
- Retention policies
- Performance benchmarks

**Example Test**:
```python
@pytest.mark.asyncio
async def test_audit_event_logging(audit_service, timescaledb_connection):
    """Test audit event logging to TimescaleDB."""
    event = {
        "user_id": "user123",
        "action": "tool_invoke",
        "resource": "server1",
        "outcome": "success",
        "timestamp": datetime.utcnow()
    }

    await audit_service.log_event(event)

    # Verify event in database
    async with timescaledb_connection.acquire() as conn:
        result = await conn.fetchrow(
            "SELECT * FROM audit_events WHERE user_id = $1",
            "user123"
        )
        assert result is not None
        assert result["action"] == "tool_invoke"
```

### 2. SIEM Integration Tests
**Files**:
- `tests/unit/siem/test_splunk_integration.py`
- `tests/unit/siem/test_datadog_integration.py`

**Coverage Goals**:
- Event forwarding
- Batch processing
- HEC token validation (Splunk)
- API key validation (Datadog)
- Retry logic
- Error handling
- Event formatting

### 3. Rate Limiter Tests
**File**: `tests/unit/services/test_rate_limiter.py`

**Coverage Goals**:
- Token bucket algorithm
- Sliding window
- Valkey storage
- Rate limit exceeded handling
- Per-user limits
- Per-IP limits
- Custom rate limit headers

### 4. Bulk Operations Tests
**File**: `tests/unit/services/test_bulk_operations.py`

**Coverage Goals**:
- Bulk server creation
- Bulk policy updates
- Transaction handling
- Rollback on failure
- Progress tracking
- Validation
- Error aggregation

### 5. Cost Tracking Tests
**Files**:
- `tests/unit/cost/test_cost_estimator.py`
- `tests/unit/cost/test_cost_tracker.py`
- `tests/unit/cost/test_anthropic_provider.py`
- `tests/unit/cost/test_openai_provider.py`

**Coverage Goals**:
- Token counting
- Cost calculation
- Provider-specific pricing
- Usage tracking
- Cost attribution
- Billing integration

### 6. Database Tests
**Files**:
- `tests/unit/db/test_connection_pools.py`
- `tests/unit/db/test_session_management.py`
- `tests/unit/db/test_migrations.py`

**Coverage Goals**:
- Connection pool management
- Session lifecycle
- Transaction handling
- Migration execution
- Migration rollback
- Schema validation

### 7. API Router Tests
**Files**:
- `tests/unit/api/test_admin_router.py`
- `tests/unit/api/test_audit_router.py`
- `tests/unit/api/test_users_router.py`
- `tests/unit/api/test_rate_limit_middleware.py`

**Coverage Goals**:
- Request validation
- Response formatting
- Error handling
- Authentication
- Authorization
- Pagination
- Filtering
- Sorting

---

## Fixtures to Use

From `tests/fixtures/integration_docker.py`:
- `postgres_connection` - For database tests
- `timescaledb_connection` - For audit tests
- `valkey_connection` - For rate limiting and caching
- `initialized_db` - For API integration tests

---

## Success Criteria

- ✅ All 18 modules have ≥85% code coverage
- ✅ All tests pass
- ✅ Audit events properly logged to TimescaleDB
- ✅ SIEM integration tested with mock servers
- ✅ Rate limiting working correctly
- ✅ Bulk operations transactional
- ✅ Cost tracking accurate
- ✅ Database migrations tested
- ✅ API endpoints fully tested

---

## Test Pattern Example

```python
import pytest
from sark.services.rate_limiter import RateLimiter, RateLimitExceeded

class TestRateLimiter:
    """Test rate limiting functionality."""

    @pytest.fixture
    async def rate_limiter(self, valkey_connection):
        """Create rate limiter instance."""
        return RateLimiter(
            redis=valkey_connection,
            default_limit=10,
            window=60  # 10 requests per 60 seconds
        )

    @pytest.mark.asyncio
    async def test_rate_limit_allows_within_limit(self, rate_limiter):
        """Test requests within rate limit are allowed."""
        user_id = "user123"

        for i in range(10):
            allowed = await rate_limiter.check_rate_limit(user_id)
            assert allowed is True

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_over_limit(self, rate_limiter):
        """Test requests over rate limit are blocked."""
        user_id = "user456"

        # Use up all tokens
        for i in range(10):
            await rate_limiter.check_rate_limit(user_id)

        # Next request should be blocked
        with pytest.raises(RateLimitExceeded):
            await rate_limiter.check_rate_limit(user_id)

    @pytest.mark.asyncio
    async def test_rate_limit_resets_after_window(
        self,
        rate_limiter,
        freezegun
    ):
        """Test rate limit resets after time window."""
        user_id = "user789"

        # Use up all tokens
        for i in range(10):
            await rate_limiter.check_rate_limit(user_id)

        # Advance time past window
        freezegun.tick(delta=timedelta(seconds=61))

        # Should allow again
        allowed = await rate_limiter.check_rate_limit(user_id)
        assert allowed is True
```

---

## Priority Order

1. **High Priority** (Day 1):
   - Audit service tests
   - Rate limiter tests
   - Database tests

2. **Medium Priority** (Day 2):
   - SIEM integration tests
   - Cost tracking tests
   - Bulk operations tests

3. **Low Priority** (Day 3):
   - API router tests
   - Migration tests
   - Performance tests

---

## Deliverables

1. Test files for all 18 modules
2. Coverage report showing 85%+ coverage
3. All tests passing in CI
4. Mock SIEM servers for testing
5. Commit message:
   ```
   test: Add services & API test suite

   - Add audit service tests (87% coverage)
   - Add SIEM integration tests (Splunk: 85%, Datadog: 86%)
   - Add rate limiter tests (92% coverage)
   - Add bulk operations tests (88% coverage)
   - Add cost tracking tests (84% coverage)
   - Add database tests (90% coverage)
   - Add API router tests (85% coverage)

   Total: 18 modules, 450+ tests, 85%+ coverage

   Part of Phase 3 Workstream 4 (v1.3.1 implementation plan)
   ```

---

## Notes

- Mock Splunk HEC endpoint for testing
- Mock Datadog API for testing
- Use pytest-freezegun for time-dependent tests
- Test rate limiting under concurrent load
- Validate audit log queryability
- Test database connection pool exhaustion
