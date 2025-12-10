# SARK v1.2.0 Completion Plan
## Test Fixes & Coverage Boost - Czarina Orchestration

**Version:** 1.0
**Date:** December 9, 2025
**Current Status:** Code Complete (4,593 lines), Test Quality Work Needed
**Target:** v1.2.0 Release
**Duration:** 2-3 weeks
**Orchestration:** Czarina multi-agent system

---

## Executive Summary

**Current State:**
- ✅ Gateway implementation: 100% code complete (PRs #44-47 merged)
- ✅ Policy validation: 100% code complete
- ❌ Test pass rate: 89.8% (1,469 passing, 166 failing, 278 errors)
- ❌ Code coverage: 13.64% (target: 85%+)
- ❌ E2E integration: Blocked by import error

**What v1.2.0 Completion Delivers:**
- ✅ 100% test pass rate (zero failures)
- ✅ 85%+ code coverage
- ✅ E2E integration tests working
- ✅ Performance verified (<100ms p95)
- ✅ Ready for v1.2.0 release

**Timeline:** 2-3 weeks
**Team:** 3-4 workers in parallel via Czarina

---

## Current Test Status Analysis

### Test Results (Full Suite)

```
Total Tests: 2,037
├── ✅ Passing:  1,469 (89.8%)
├── ❌ Failing:    166 (10.2%)
├── ❌ Errors:     278
└── ⏭️  Skipped:   124

Coverage: 13.64% (Target: 85%+)
Gap: 71.36 percentage points
```

### Failure Breakdown by Category

| Category | Failures | Errors | Total Issues | Priority |
|----------|----------|--------|--------------|----------|
| **Auth Integration** | 15 | 17 | 32 | 🔴 High |
| **API Pagination** | 12 | 0 | 12 | 🟡 Medium |
| **SIEM Formatting** | 8 | 0 | 8 | 🟡 Medium |
| **Gateway Transport** | 11 | 2 | 13 | 🔴 High |
| **Provider Failover** | 5 | 0 | 5 | 🟡 Medium |
| **Discovery Services** | 20 | 180 | 200 | 🔴 High |
| **Policy OPA Client** | 3 | 0 | 3 | 🟡 Medium |
| **Other** | 92 | 79 | 171 | 🟡 Medium |
| **Total** | **166** | **278** | **444** | |

---

## Work Stream Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CZARINA ORCHESTRATION                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Stream 1: Gateway Test Fixes  Stream 2: Auth Test Fixes        │
│  ┌──────────────────┐          ┌──────────────────┐            │
│  │ Worker: TEST-1   │          │ Worker: TEST-2   │            │
│  │ Week 1           │          │ Week 1           │            │
│  │ +E2E import fix  │          │ +LDAP integration│            │
│  │ +SSE async fix   │          │ +SAML integration│            │
│  │ +HTTP mock fix   │          │ +OIDC integration│            │
│  └──────────────────┘          └──────────────────┘            │
│                                                                   │
│  Stream 3: Integration Tests   Stream 4: Coverage Boost         │
│  ┌──────────────────┐          ┌──────────────────┐            │
│  │ Worker: TEST-3   │          │ Worker: TEST-4   │            │
│  │ Week 2           │          │ Weeks 2-3        │            │
│  │ +API pagination  │          │ +Unit tests      │            │
│  │ +SIEM formatting │          │ +Error paths     │            │
│  │ +Discovery fix   │          │ +Edge cases      │            │
│  └──────────────────┘          └──────────────────┘            │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

**Parallelization:**
- Week 1: Streams 1 & 2 run in parallel (fix critical test failures)
- Week 2: Streams 3 & 4 run in parallel (fix remaining + boost coverage)
- Week 3: Final integration, performance testing, release prep

---

## Stream 1: Gateway Test Fixes (TEST-1)

**Worker Assignment:** `TEST-1` (Aider recommended for test automation)
**Duration:** Week 1 (5-7 days)
**Branch:** `fix/gateway-test-failures`
**Dependencies:** None
**Estimated Effort:** 1 week, 1 worker

### Priority: 🔴 CRITICAL - Blocks E2E Integration

**Total Issues:** 13 failures + 2 errors = 15 issues

### Task 1.1: Fix E2E Import Error (BLOCKER)

**Issue:**
```python
# tests/integration/gateway/test_gateway_e2e.py:32
from sark.gateway import GatewayClient  # ❌ ImportError
```

**Root Cause:** `src/sark/gateway/__init__.py` doesn't export GatewayClient

**Solution:**
- **File:** `src/sark/gateway/__init__.py` (UPDATE)
- **Change:**
  ```python
  """Gateway module for SARK."""

  from sark.gateway.client import GatewayClient
  from sark.gateway.error_handler import (
      GatewayErrorHandler,
      CircuitBreakerState,
  )
  from sark.gateway.transports.http_client import HTTPTransport
  from sark.gateway.transports.sse_client import SSETransport
  from sark.gateway.transports.stdio_client import StdioTransport

  __all__ = [
      "GatewayClient",
      "GatewayErrorHandler",
      "CircuitBreakerState",
      "HTTPTransport",
      "SSETransport",
      "StdioTransport",
  ]
  ```

**Time:** 30 minutes
**Impact:** Unblocks 65+ E2E tests

### Task 1.2: Fix SSE Async Context Manager (8 failures)

**Failing Tests:**
```
test_stream_events_basic
test_stream_events_with_filter
test_stream_audit_events
test_stream_server_events
test_reconnection_on_error
test_no_reconnection_when_disabled
test_max_retries_exceeded
test_no_retry_on_client_error
```

**Error:**
```
TypeError: 'coroutine' object does not support the asynchronous context manager protocol
```

**Root Cause:** SSE client's `stream()` method is async but not properly defined as async context manager

**Solution:**
- **File:** `src/sark/gateway/transports/sse_client.py` (UPDATE)
- **Current Code:**
  ```python
  async def stream(self, url: str, **kwargs):
      # Returns coroutine, not async context manager
      return self._stream_events(url, **kwargs)
  ```

- **Fixed Code:**
  ```python
  async def stream(self, url: str, **kwargs):
      # Return async context manager
      return StreamContext(self, url, **kwargs)

  class StreamContext:
      async def __aenter__(self):
          # Setup connection
          return self

      async def __aexit__(self, exc_type, exc_val, exc_tb):
          # Cleanup connection
          pass

      def __aiter__(self):
          return self._stream_events()
  ```

**Time:** 4 hours
**Impact:** Fixes 8 test failures

### Task 1.3: Fix HTTP Connection Pooling (2 failures)

**Failing Tests:**
```
test_connection_pooling_limits (HTTP)
test_connection_pooling_limits (SSE)
```

**Error:**
```
AttributeError: 'AsyncClient' object has no attribute 'limits'
```

**Root Cause:** httpx AsyncClient API changed - `limits` was replaced with different attribute

**Solution:**
- **File:** `tests/unit/gateway/transports/test_http_client.py` (UPDATE)
- **Change:**
  ```python
  # OLD (incorrect)
  assert client.http_client.limits.max_connections == 100

  # NEW (correct for httpx 0.25+)
  assert client.http_client._transport._pool._max_connections == 100
  # OR check via different mechanism
  ```

**Time:** 2 hours
**Impact:** Fixes 2 test failures

### Task 1.4: Fix HTTP Mock Matching (1 failure + 2 errors)

**Failing Tests:**
```
test_invoke_tool_not_cached (FAILED + ERROR)
test_health_check_failure (ERROR)
```

**Error:**
```
httpx.TimeoutException: No response can be found for POST request
AssertionError: The following requests were not expected
```

**Root Cause:** pytest_httpx mock needs to allow multiple requests to same endpoint

**Solution:**
- **File:** `tests/unit/gateway/transports/test_http_client.py` (UPDATE)
- **Change:**
  ```python
  # Add allow_duplicates for retried requests
  httpx_mock.add_response(
      method="POST",
      url="http://test-gateway:8080/api/v1/invoke",
      json={"result": "success"},
  )
  httpx_mock.add_response(...)  # Allow duplicate

  # OR use non_mocked_hosts for health checks
  httpx_mock.non_mocked_hosts.add("test-gateway")
  ```

**Time:** 2 hours
**Impact:** Fixes 1 failure + 2 errors

### Deliverables

**Code Changes:**
- ✅ `src/sark/gateway/__init__.py` - Export GatewayClient
- ✅ `src/sark/gateway/transports/sse_client.py` - Fix async context manager
- ✅ `tests/unit/gateway/transports/test_http_client.py` - Fix mocking
- ✅ `tests/unit/gateway/transports/test_sse_client.py` - Fix async tests

**Results:**
- [ ] 13 gateway test failures fixed
- [ ] E2E test suite unblocked (65+ tests can run)
- [ ] Gateway module 100% test pass rate

**Time:** 5-7 days (1 week)

---

## Stream 2: Auth Integration Test Fixes (TEST-2)

**Worker Assignment:** `TEST-2` (Aider recommended)
**Duration:** Week 1 (5-7 days)
**Branch:** `fix/auth-integration-tests`
**Dependencies:** None (runs parallel to Stream 1)
**Estimated Effort:** 1 week, 1 worker

### Priority: 🔴 CRITICAL - Auth Tests Failing

**Total Issues:** 15 failures + 17 errors = 32 issues

### Task 2.1: Fix LDAP Integration Tests (10+ errors)

**Failing Tests:**
```
TestLDAPIntegrationSearch::test_search_nonexistent_user - ERROR
TestLDAPIntegrationBind::test_bind_valid_credentials - ERROR
TestLDAPIntegrationBind::test_bind_invalid_credentials - ERROR
... (10+ LDAP tests)
```

**Error:**
```
AttributeError: 'Services' object has no attribute 'docker_ip'
```

**Root Cause:** pytest-docker Services object API changed or fixture incorrect

**Solution:**
- **File:** `tests/integration/auth/test_ldap_integration.py` (UPDATE)
- **Fix:**
  ```python
  # OLD (incorrect)
  ldap_host = services.docker_ip

  # NEW (correct for pytest-docker 3.x)
  ldap_host = services.docker_host
  # OR
  ldap_host = "localhost"  # If using port mapping
  ```

**Time:** 4 hours
**Impact:** Fixes 10+ LDAP test errors

### Task 2.2: Fix OIDC/SAML Integration Tests (7+ errors)

**Failing Tests:**
```
TestCompleteAuthFlows::test_oidc_authorization_flow - ERROR
TestCompleteAuthFlows::test_oidc_token_validation - ERROR
TestProviderFailover::test_oidc_primary_saml_fallback - ERROR
... (7+ auth flow tests)
```

**Error:** Similar Services API issues or missing test fixtures

**Solution:**
- **File:** `tests/integration/auth/test_oidc_integration.py` (UPDATE)
- **File:** `tests/integration/auth/test_saml_integration.py` (UPDATE)
- Fix Services API calls
- Update test fixtures for current provider implementations

**Time:** 4 hours
**Impact:** Fixes 7+ auth test errors

### Task 2.3: Fix Provider Failover Tests (5 failures)

**Failing Tests:**
```
test_oidc_primary_saml_fallback
test_ldap_primary_oidc_fallback
test_all_providers_down
test_multi_provider_round_robin
test_user_with_multiple_auth_methods
```

**Issue:** Provider failover logic changed or test expectations outdated

**Solution:**
- **File:** `tests/test_auth/test_auth_integration.py` (UPDATE)
- Update test expectations to match current failover implementation
- Fix mock responses for multiple providers

**Time:** 4 hours
**Impact:** Fixes 5 test failures

### Deliverables

**Code Changes:**
- ✅ `tests/integration/auth/test_ldap_integration.py` - Fix docker_ip issues
- ✅ `tests/integration/auth/test_oidc_integration.py` - Fix OIDC tests
- ✅ `tests/integration/auth/test_saml_integration.py` - Fix SAML tests
- ✅ `tests/test_auth/test_auth_integration.py` - Fix failover tests

**Results:**
- [ ] 32 auth test issues fixed
- [ ] Auth integration 100% pass rate

**Time:** 5-7 days (1 week)

---

## Stream 3: Integration Test Fixes (TEST-3)

**Worker Assignment:** `TEST-3` (Continue.dev or Cursor)
**Duration:** Week 2 (5-7 days)
**Branch:** `fix/integration-tests`
**Dependencies:** None
**Estimated Effort:** 1 week, 1 worker

### Priority: 🟡 MEDIUM - Integration Tests

**Total Issues:** 20 failures + 180 errors in discovery services

### Task 3.1: Fix API Pagination Tests (12 failures)

**Failing Tests:**
```
test_list_servers_pagination
test_list_servers_invalid_cursor
test_list_servers_invalid_limit_too_high
test_list_servers_invalid_sort_order
test_list_servers_empty_results
test_list_servers_response_schema
test_list_servers_multiple_pages
test_openapi_schema_includes_pagination
... (12 total)
```

**Root Cause:** API pagination implementation changed or test expectations incorrect

**Solution:**
- **File:** `tests/test_api_pagination.py` (UPDATE)
- Update test expectations to match current pagination API
- Fix cursor validation logic
- Update OpenAPI schema assertions

**Time:** 1 day
**Impact:** Fixes 12 test failures

### Task 3.2: Fix SIEM Event Formatting Tests (8 failures)

**Failing Tests:**
```
TestSplunkEventFormatting::test_splunk_minimal_event
TestDatadogEventFormatting::test_datadog_minimal_event
... (8 total)
```

**Root Cause:** SIEM event format changed or test fixtures outdated

**Solution:**
- **File:** `tests/test_audit/test_siem_event_formatting.py` (UPDATE)
- Update event format expectations
- Fix Splunk HEC format
- Fix Datadog log format

**Time:** 1 day
**Impact:** Fixes 8 test failures

### Task 3.3: Fix Discovery Services Tests (180 errors)

**Failing Area:** `src/sark/services/discovery/` tests

**Issue:** Discovery service tests have high error rate (180 errors)

**Analysis Needed:**
1. What are the actual errors?
2. Are these new tests or existing tests breaking?
3. Import errors or logic errors?

**Solution:**
- **Files:** `tests/unit/services/test_discovery*.py` (UPDATE)
- Fix import errors
- Update service mocks
- Fix discovery service API calls

**Time:** 3 days
**Impact:** Fixes 180+ test errors

### Deliverables

**Code Changes:**
- ✅ `tests/test_api_pagination.py` - 12 fixes
- ✅ `tests/test_audit/test_siem_event_formatting.py` - 8 fixes
- ✅ `tests/unit/services/test_discovery*.py` - 180+ fixes

**Results:**
- [ ] 200 integration test issues fixed
- [ ] Integration tests 100% pass rate

**Time:** 5-7 days (1 week)

---

## Stream 4: Coverage Boost (TEST-4)

**Worker Assignment:** `TEST-4` (Aider recommended for test generation)
**Duration:** Weeks 2-3 (10-14 days)
**Branch:** `feat/coverage-boost`
**Dependencies:** Streams 1, 2, 3 should be mostly complete
**Estimated Effort:** 2 weeks, 1 worker

### Priority: 🔴 HIGH - Coverage is 13.64%, need 85%+

**Current Coverage:** 13.64%
**Target Coverage:** 85%+
**Gap:** 71.36 percentage points
**New Tests Needed:** ~800-1,000 test cases

### Task 4.1: Add Gateway Coverage (Week 2, 3 days)

**Current Coverage:**
- HTTP transport: ~60%
- SSE transport: ~50%
- stdio transport: ~70%
- Error handler: 0%
- Client: ~40%

**Target:** 90%+ for all gateway modules

**New Tests Needed:**
- Error handler edge cases (20+ tests)
- Circuit breaker scenarios (15+ tests)
- Retry logic variations (10+ tests)
- Transport failover (10+ tests)
- Health check scenarios (10+ tests)

**Files:**
- `tests/unit/gateway/test_error_handler.py` (NEW - 200+ lines)
- `tests/unit/gateway/test_client.py` (UPDATE - add 150+ lines)
- `tests/unit/gateway/transports/test_http_client.py` (UPDATE - add 100+ lines)

**Time:** 3 days
**Impact:** +15-20% overall coverage

### Task 4.2: Add Policy Coverage (Week 2, 2 days)

**Current Coverage:**
- Policy validator: ~24.59%
- OPA client: ~35.82%
- Policy audit: 0%
- Policy cache: 17.46%

**Target:** 90%+ for all policy modules

**New Tests Needed:**
- OPA client error paths (25+ tests)
- Policy audit scenarios (20+ tests)
- Policy cache edge cases (15+ tests)
- Validator edge cases (10+ tests)

**Files:**
- `tests/unit/policy/test_opa_client.py` (UPDATE - add 200+ lines)
- `tests/unit/policy/test_audit.py` (NEW - 200+ lines)
- `tests/unit/policy/test_cache.py` (NEW - 150+ lines)

**Time:** 2 days
**Impact:** +10-15% overall coverage

### Task 4.3: Add Services Coverage (Week 2-3, 4 days)

**Current Coverage:**
- Discovery services: 13.71-19.64%
- Federation services: 10.71-16.67%
- SIEM services: 0-27.40%
- Auth services: Varies

**Target:** 85%+ for critical services

**New Tests Needed:**
- Discovery service unit tests (50+ tests)
- Federation service unit tests (40+ tests)
- SIEM service unit tests (30+ tests)
- Auth service unit tests (50+ tests)

**Files:**
- `tests/unit/services/test_discovery_service.py` (NEW - 300+ lines)
- `tests/unit/services/test_federation_*.py` (NEW - 250+ lines)
- `tests/unit/services/test_siem_*.py` (NEW - 200+ lines)

**Time:** 4 days
**Impact:** +20-25% overall coverage

### Task 4.4: Add E2E Scenario Coverage (Week 3, 3 days)

**Current:** E2E tests exist but can't run (import error)

**After Stream 1 fixes:** E2E tests runnable

**New Scenarios Needed:**
1. Complete authorization flow (user → API → OPA → Gateway → MCP)
2. Multi-layer security (auth + authz + filtering + audit)
3. Error propagation (MCP error → Gateway → API → User)
4. Performance under load (100+ concurrent requests)
5. Cache effectiveness (hit rate >80%)
6. Circuit breaker activation
7. Retry logic with backoff
8. Provider failover
9. Sensitive data filtering
10. Audit log verification

**Files:**
- `tests/e2e/test_complete_flows.py` (NEW - 500+ lines)
- `tests/e2e/test_security_scenarios.py` (NEW - 400+ lines)
- `tests/e2e/test_performance.py` (NEW - 300+ lines)

**Time:** 3 days
**Impact:** +15-20% overall coverage, critical path validation

### Deliverables

**Code Changes:**
- ✅ 800-1,000 new test cases
- ✅ ~2,500 lines of new test code
- ✅ E2E scenario coverage

**Results:**
- [ ] Coverage increased from 13.64% to 85%+
- [ ] Critical paths fully tested
- [ ] E2E scenarios validated

**Time:** 10-14 days (2 weeks)

---

## Integration & Release Prep (Week 3)

### Task: Final Integration

**Responsibilities:**
1. Merge all fix branches to main
2. Run full test suite (should be 100% passing)
3. Verify coverage report (should be 85%+)
4. Run performance benchmarks
5. Update documentation
6. Create release notes

**Timeline:**
- Monday: Merge all branches
- Tuesday-Wednesday: Integration testing
- Thursday: Performance verification
- Friday: Release prep

**Deliverables:**
- [ ] All branches merged
- [ ] 100% test pass rate achieved
- [ ] 85%+ coverage achieved
- [ ] Performance verified (<100ms p95)
- [ ] Release notes published

---

## Czarina Configuration

### `.czarina/config.json` (v1.2.0 Completion)

```json
{
  "project": "sark",
  "version": "1.2.0-completion",
  "phase": "test-quality",
  "workers": {
    "test-1": {
      "name": "Gateway Test Fixer",
      "branch": "fix/gateway-test-failures",
      "agent": "aider",
      "autonomy": "high",
      "budget": {
        "tokens": 2000000,
        "weeks": 1
      },
      "tasks": [
        "Fix E2E import error (GatewayClient export)",
        "Fix SSE async context manager (8 tests)",
        "Fix HTTP connection pooling (2 tests)",
        "Fix HTTP mock matching (3 issues)"
      ]
    },
    "test-2": {
      "name": "Auth Test Fixer",
      "branch": "fix/auth-integration-tests",
      "agent": "aider",
      "autonomy": "high",
      "budget": {
        "tokens": 2500000,
        "weeks": 1
      },
      "tasks": [
        "Fix LDAP integration tests (10+ errors)",
        "Fix OIDC integration tests (7+ errors)",
        "Fix SAML integration tests",
        "Fix provider failover tests (5 failures)"
      ]
    },
    "test-3": {
      "name": "Integration Test Fixer",
      "branch": "fix/integration-tests",
      "agent": "cursor",
      "autonomy": "medium",
      "budget": {
        "tokens": 3000000,
        "weeks": 1
      },
      "tasks": [
        "Fix API pagination tests (12 failures)",
        "Fix SIEM formatting tests (8 failures)",
        "Fix discovery services tests (180+ errors)"
      ]
    },
    "test-4": {
      "name": "Coverage Booster",
      "branch": "feat/coverage-boost",
      "agent": "aider",
      "autonomy": "high",
      "budget": {
        "tokens": 5000000,
        "weeks": 2
      },
      "tasks": [
        "Add gateway error handler tests (20+ tests)",
        "Add policy OPA client tests (25+ tests)",
        "Add services unit tests (170+ tests)",
        "Add E2E scenario tests (30+ tests)",
        "Target: 85%+ overall coverage"
      ]
    }
  },
  "daemon": {
    "auto_approve": true,
    "patterns": ["test", "fix", "coverage"]
  },
  "milestones": {
    "week_1_end": {
      "test_pass_rate": "95%+",
      "gateway_tests": "100% passing",
      "auth_tests": "100% passing"
    },
    "week_2_end": {
      "test_pass_rate": "100%",
      "integration_tests": "100% passing",
      "coverage": "60%+"
    },
    "week_3_end": {
      "coverage": "85%+",
      "performance": "<100ms p95",
      "release": "v1.2.0"
    }
  }
}
```

### Worker Prompts

**`.czarina/workers/test-1.md`**
```markdown
# Gateway Test Fixer (TEST-1)

You are TEST-1, responsible for fixing Gateway test failures.

## Your Mission (Week 1)

Fix 15 critical Gateway test issues blocking v1.2.0 release.

## Priority 1: Fix E2E Import Error (BLOCKER)
**Time: 30 minutes**

File: `src/sark/gateway/__init__.py`

Problem: E2E tests cannot import GatewayClient

Fix: Export GatewayClient and related classes from __init__.py

```python
from sark.gateway.client import GatewayClient
from sark.gateway.error_handler import GatewayErrorHandler
# ... export all public APIs
```

Verify: `python -c "from sark.gateway import GatewayClient; print('OK')"`

## Priority 2: Fix SSE Async Context Manager (8 failures)
**Time: 4 hours**

File: `src/sark/gateway/transports/sse_client.py`

Problem: SSE stream() returns coroutine instead of async context manager

Error: `TypeError: 'coroutine' object does not support the asynchronous context manager protocol`

Fix: Implement proper async context manager protocol

Tests: `pytest tests/unit/gateway/transports/test_sse_client.py -v`

## Priority 3: Fix HTTP Mocking Issues (3 issues)
**Time: 4 hours**

File: `tests/unit/gateway/transports/test_http_client.py`

Problems:
1. AttributeError: AsyncClient has no 'limits' attribute
2. httpx mock not allowing duplicate requests
3. Unexpected health check requests

Fix: Update httpx API usage and pytest_httpx mocking

Tests: `pytest tests/unit/gateway/transports/test_http_client.py -v`

## Success Criteria
- [ ] All 15 gateway test issues fixed
- [ ] E2E test suite can run
- [ ] Gateway module 100% test pass rate
- [ ] No regressions in passing tests

## Reference
- See: `docs/v1.2.0/COMPLETION_PLAN.md` Section "Stream 1"
- Gateway code: `src/sark/gateway/`
- Tests: `tests/unit/gateway/`, `tests/integration/gateway/`
```

**`.czarina/workers/test-2.md`**
```markdown
# Auth Test Fixer (TEST-2)

You are TEST-2, responsible for fixing Auth integration test failures.

## Your Mission (Week 1)

Fix 32 auth test issues (15 failures + 17 errors).

## Priority 1: Fix LDAP Docker Integration (10+ errors)
**Time: 4 hours**

File: `tests/integration/auth/test_ldap_integration.py`

Error: `AttributeError: 'Services' object has no attribute 'docker_ip'`

Fix: Update pytest-docker Services API calls
- Change `services.docker_ip` to `services.docker_host`
- Or use "localhost" with port mapping

Tests: `pytest tests/integration/auth/test_ldap_integration.py -v`

## Priority 2: Fix OIDC/SAML Integration (7+ errors)
**Time: 4 hours**

Files:
- `tests/integration/auth/test_oidc_integration.py`
- `tests/integration/auth/test_saml_integration.py`
- `tests/test_auth/test_auth_integration.py`

Fix Services API calls and update test fixtures

## Priority 3: Fix Provider Failover (5 failures)
**Time: 4 hours**

File: `tests/test_auth/test_auth_integration.py`

Update failover test expectations to match current implementation

## Success Criteria
- [ ] All 32 auth test issues fixed
- [ ] Auth integration 100% pass rate
- [ ] LDAP, OIDC, SAML providers all tested
- [ ] Failover logic verified

## Reference
- See: `docs/v1.2.0/COMPLETION_PLAN.md` Section "Stream 2"
```

**`.czarina/workers/test-3.md`**
```markdown
# Integration Test Fixer (TEST-3)

You are TEST-3, responsible for fixing integration test failures.

## Your Mission (Week 2)

Fix 200+ integration test issues (20 failures + 180 errors).

## Tasks

1. **API Pagination Tests** (1 day) - 12 failures
2. **SIEM Event Formatting** (1 day) - 8 failures
3. **Discovery Services** (3 days) - 180+ errors

## Success Criteria
- [ ] 200 integration test issues fixed
- [ ] API pagination working
- [ ] SIEM integration verified
- [ ] Discovery services functional

## Reference
- See: `docs/v1.2.0/COMPLETION_PLAN.md` Section "Stream 3"
```

**`.czarina/workers/test-4.md`**
```markdown
# Coverage Booster (TEST-4)

You are TEST-4, responsible for boosting code coverage from 13.64% to 85%+.

## Your Mission (Weeks 2-3)

Add 800-1,000 new test cases to achieve 85%+ coverage.

## Week 2: Unit Test Coverage (60%+ target)

1. **Gateway Tests** (3 days)
   - Error handler: 0% → 90%+ (20+ tests)
   - Client: 40% → 90%+ (15+ tests)
   - Transport edge cases (25+ tests)

2. **Policy Tests** (2 days)
   - OPA client: 35% → 90%+ (25+ tests)
   - Policy audit: 0% → 90%+ (20+ tests)
   - Policy cache: 17% → 90%+ (15+ tests)

## Week 3: Services & E2E Coverage (85%+ target)

3. **Services Tests** (4 days)
   - Discovery: 13-19% → 85%+ (50+ tests)
   - Federation: 10-16% → 85%+ (40+ tests)
   - SIEM: 0-27% → 85%+ (30+ tests)

4. **E2E Scenarios** (3 days)
   - Complete authorization flows (10 scenarios)
   - Security scenarios (10 scenarios)
   - Performance scenarios (10 scenarios)

## Success Criteria
- [ ] Overall coverage ≥85%
- [ ] All critical modules ≥90%
- [ ] E2E scenarios cover major workflows
- [ ] No coverage regressions

## Reference
- See: `docs/v1.2.0/COMPLETION_PLAN.md` Section "Stream 4"
- Coverage report: `htmlcov/index.html`
```

---

## Timeline & Milestones

### Week 1: Critical Fixes (Parallel)

**Monday-Friday:**
- Stream 1 (TEST-1): Fix 15 gateway test issues
- Stream 2 (TEST-2): Fix 32 auth test issues

**Milestone (End of Week 1):**
- [ ] E2E tests unblocked
- [ ] Gateway tests 100% passing
- [ ] Auth tests 100% passing
- [ ] Test pass rate: 95%+

### Week 2: Integration Fixes & Coverage Boost (Parallel)

**Monday-Friday:**
- Stream 3 (TEST-3): Fix 200 integration issues
- Stream 4 (TEST-4): Add gateway/policy tests

**Milestone (End of Week 2):**
- [ ] All integration tests passing
- [ ] Test pass rate: 100%
- [ ] Coverage: 60%+

### Week 3: Final Coverage & Release Prep

**Monday-Thursday:**
- Stream 4 (TEST-4): Add services/E2E tests

**Friday:**
- Integration & release prep

**Milestone (End of Week 3):**
- [ ] Coverage: 85%+
- [ ] Performance verified
- [ ] Release v1.2.0

---

## Success Metrics

### Test Quality Gates

| Metric | Current | Week 1 Target | Week 2 Target | Week 3 Target (Release) |
|--------|---------|---------------|---------------|------------------------|
| **Test Pass Rate** | 89.8% | 95%+ | 100% | 100% |
| **Test Failures** | 166 | <20 | 0 | 0 |
| **Test Errors** | 278 | <50 | 0 | 0 |
| **Code Coverage** | 13.64% | 20%+ | 60%+ | 85%+ |
| **E2E Tests** | Blocked | Working | Enhanced | Complete |

### Module Coverage Targets

| Module | Current | Target | Priority |
|--------|---------|--------|----------|
| **Gateway** | 40-70% | 90%+ | 🔴 Critical |
| **Policy** | 17-35% | 90%+ | 🔴 Critical |
| **Auth** | Varies | 85%+ | 🔴 Critical |
| **Services** | 0-27% | 85%+ | 🟡 High |
| **API** | Unknown | 85%+ | 🟡 High |

---

## Risk Management

### Critical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Test fixes create new failures** | High | Comprehensive regression testing after each fix |
| **Coverage gaps in untested modules** | Medium | Focus on critical paths first, accept 80% if needed |
| **Integration test fixes complex** | High | Allocate extra time, consider skipping non-critical tests |
| **E2E import fix breaks other imports** | Medium | Careful __init__.py updates, verify all imports |

### Contingency Plans

**If test pass rate can't reach 100%:**
- Accept 98% if remaining failures are in non-critical paths
- Skip/disable tests that can't be fixed
- Document known issues for v1.2.1

**If coverage can't reach 85%:**
- Accept 80% for v1.2.0
- Target 85%+ for v1.2.1
- Focus coverage on critical paths (gateway, policy, auth)

**If timeline exceeds 3 weeks:**
- Release v1.2.0-beta with current status
- Continue fixes in v1.2.1

---

## Launch Commands

### Week 1: Critical Fixes
```bash
cd ~/Source/sark

# Launch test fixers in parallel
czarina launch test-1 test-2

# Start daemon for auto-approvals
czarina daemon start

# Monitor progress
czarina status
czarina logs test-1
czarina logs test-2

# Check test results after fixes
pytest tests/unit/gateway/ -v
pytest tests/integration/auth/ -v
```

### Week 2: Integration & Coverage
```bash
# Launch integration fixer and coverage booster
czarina launch test-3 test-4

# Monitor coverage improvements
pytest --cov=src/sark --cov-report=html

# Check coverage report
open htmlcov/index.html
```

### Week 3: Release
```bash
# All workers complete
czarina stop --all

# Merge all fix branches
gh pr list
gh pr merge <pr-numbers>

# Tag v1.2.0
git tag -a v1.2.0 -m "Release v1.2.0: Gateway + Policy + Tests"
git push origin v1.2.0

# Publish release
gh release create v1.2.0 --notes-file docs/v1.2.0/RELEASE_NOTES.md
```

---

## v1.2.0 Release Checklist

### Code Quality
- [ ] All code merged to main
- [ ] No merge conflicts
- [ ] All tests passing (100%)
- [ ] Code coverage ≥85%
- [ ] No linting warnings

### Functionality
- [ ] Gateway client functional (HTTP, SSE, stdio)
- [ ] Policy validation operational
- [ ] Authorization flow end-to-end verified
- [ ] Audit logging working
- [ ] Performance targets met (<100ms p95)

### Documentation
- [ ] Release notes published
- [ ] CHANGELOG.md updated
- [ ] API documentation updated
- [ ] Migration guide (if needed)

### Testing
- [ ] Unit tests: 100% pass rate
- [ ] Integration tests: 100% pass rate
- [ ] E2E tests: All scenarios passing
- [ ] Performance tests: Benchmarks met
- [ ] Regression tests: No regressions

### Deployment
- [ ] Docker Compose works
- [ ] Kubernetes manifests updated
- [ ] Helm charts updated
- [ ] Version strings updated everywhere

**Release Date:** End of Week 3
**Version:** v1.2.0
**Next:** v1.3.0 (Advanced Security) or v2.0.0 (Security Audit)

---

## Appendix: Test Failure Categories

### By Severity

**🔴 CRITICAL (Blocks Release):**
- E2E import error (blocks 65+ tests)
- Gateway transport failures (13 issues)
- Auth integration errors (32 issues)
- **Total: 110+ issues**

**🟡 HIGH (Impacts Coverage):**
- API pagination (12 failures)
- SIEM formatting (8 failures)
- Discovery services (180+ errors)
- **Total: 200+ issues**

**🟢 MEDIUM (Nice to Fix):**
- Policy OPA health checks (3 failures)
- Misc integration tests (~100 issues)
- **Total: ~103 issues**

### By Module

**Gateway (15 issues):**
- Import error: 1
- SSE async: 8
- HTTP mocking: 3
- HTTP errors: 2
- OPA health: 3

**Auth (32 issues):**
- LDAP: 10+ errors
- OIDC: 7+ errors
- SAML: ~5 errors
- Failover: 5 failures
- Provider scenarios: 5+ failures

**Integration (200+ issues):**
- API pagination: 12
- SIEM: 8
- Discovery: 180+

---

## Expected Outcomes

### Week 1 (End of Week)
```
Test Pass Rate: 89.8% → 95%+
Failures: 166 → <20
Errors: 278 → <50
Coverage: 13.64% → 20%+
```

### Week 2 (End of Week)
```
Test Pass Rate: 95%+ → 100%
Failures: <20 → 0
Errors: <50 → 0
Coverage: 20%+ → 60%+
```

### Week 3 (v1.2.0 Release)
```
Test Pass Rate: 100%
Failures: 0
Errors: 0
Coverage: 85%+
Performance: <100ms p95 ✅
```

---

## Document Control

**Version:** 1.0
**Date:** December 9, 2025
**Author:** SARK Team
**Purpose:** v1.2.0 completion via Czarina orchestration

**Related Documents:**
- `docs/v1.2.0/IMPLEMENTATION_PLAN.md` - Original implementation plan
- `STATUS.md` - Current project status
- `docs/ROADMAP.md` - Overall roadmap
- `VERSION_RENUMBERING.md` - Version strategy

**Next Steps:**
1. Review and approve this plan
2. Set up Czarina configuration (copy from this doc)
3. Create worker prompts (copy from this doc)
4. Launch test-1 and test-2 workers (Week 1)
5. Launch test-3 and test-4 workers (Week 2)
6. Release v1.2.0 (Week 3)
