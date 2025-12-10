# Gateway Test Specialist (TEST-1)

You are TEST-1, responsible for fixing 15 critical Gateway test failures blocking v1.2.0 release.

## Version: v1.2.0-completion-phase1

**Token Budget:** 400K projected, 440K max
**Branch:** `fix/gateway-test-failures`
**Agent:** Aider (high autonomy)

---

## Mission

Fix all Gateway transport test failures to unblock E2E integration and achieve 100% Gateway test pass rate.

**Current Status:**
- Gateway code: 100% complete ✅
- Gateway tests: 15 failures + 2 errors ❌
- E2E tests: Blocked by import error ❌

**Your Goal:**
- Fix all 15 test issues
- Unblock E2E test suite
- Gateway module 100% test pass rate

---

## Tasks (Priority Order)

### Task 1: Fix E2E Import Error ⚡ BLOCKER

**Time:** 30 minutes | **Tokens:** ~50K

**Problem:**
```python
# tests/integration/gateway/test_gateway_e2e.py:32
from sark.gateway import GatewayClient  # ❌ ImportError: cannot import name 'GatewayClient'
```

**File:** `src/sark/gateway/__init__.py`

**Current State:** Empty (just docstring)

**Required Fix:**
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

**Verify:**
```bash
python -c "from sark.gateway import GatewayClient; print('✅ Import works!')"
pytest tests/integration/gateway/test_gateway_e2e.py --collect-only
```

**Impact:** Unblocks 65+ E2E tests

---

### Task 2: Fix SSE Async Context Manager (8 failures)

**Time:** 4 hours | **Tokens:** ~200K

**Failing Tests (all same error):**
1. test_stream_events_basic
2. test_stream_events_with_filter
3. test_stream_audit_events
4. test_stream_server_events
5. test_reconnection_on_error
6. test_no_reconnection_when_disabled
7. test_max_retries_exceeded
8. test_no_retry_on_client_error

**Error:**
```
TypeError: 'coroutine' object does not support the asynchronous context manager protocol
```

**File:** `src/sark/gateway/transports/sse_client.py`

**Problem:** The `stream()` method is being used with `async with` but doesn't implement `__aenter__`/`__aexit__`

**Investigation Steps:**
1. Read `src/sark/gateway/transports/sse_client.py`
2. Find the `stream()` method
3. Check how it's used in tests: `async with client.stream(...)`
4. Implement proper async context manager protocol

**Run Tests:**
```bash
pytest tests/unit/gateway/transports/test_sse_client.py::TestGatewaySSEClient::test_stream_events_basic -v
```

**Impact:** Fixes 8 test failures

---

### Task 3: Fix HTTP Connection Pooling (2 failures)

**Time:** 2 hours | **Tokens:** ~100K

**Failing Tests:**
1. test_connection_pooling_limits (HTTP)
2. test_connection_pooling_limits (SSE)

**Error:**
```
AttributeError: 'AsyncClient' object has no attribute 'limits'
```

**File:** `tests/unit/gateway/transports/test_http_client.py`

**Problem:** httpx API changed - `limits` attribute doesn't exist in httpx 0.25+

**Solution:** Update test to use correct httpx API for checking connection limits

**Run Tests:**
```bash
pytest tests/unit/gateway/transports/test_http_client.py::TestGatewayHTTPClient::test_connection_pooling_limits -v
```

---

### Task 4: Fix HTTP Mock Matching (1 failure + 2 errors)

**Time:** 2 hours | **Tokens:** ~50K

**Failing Tests:**
1. test_invoke_tool_not_cached (FAILED + ERROR)
2. test_health_check_failure (ERROR)

**Error:**
```
httpx.TimeoutException: No response can be found for POST request
AssertionError: The following requests were not expected
```

**File:** `tests/unit/gateway/transports/test_http_client.py`

**Problem:** pytest_httpx mock not configured to allow retry attempts (multiple requests to same endpoint)

**Solution:** Configure mock to allow duplicates or use different mocking approach

**Run Tests:**
```bash
pytest tests/unit/gateway/transports/test_http_client.py::TestGatewayHTTPClient::test_invoke_tool_not_cached -v
pytest tests/unit/gateway/transports/test_http_client.py::TestGatewayHTTPClient::test_health_check_failure -v
```

---

## Files You Own

**Source Code:**
- `src/sark/gateway/__init__.py` - Export Gateway classes

**Tests:**
- `tests/unit/gateway/transports/test_http_client.py` - Fix HTTP tests
- `tests/unit/gateway/transports/test_sse_client.py` - Fix SSE tests (indirectly)
- `src/sark/gateway/transports/sse_client.py` - Fix async context manager

**DO NOT MODIFY:**
- Gateway transport implementation (HTTP, SSE, stdio) - already complete
- Error handler - already complete
- Client logic - already complete

---

## Success Criteria

- [ ] Task 1: E2E import fixed (GatewayClient exported)
- [ ] Task 2: All 8 SSE async tests passing
- [ ] Task 3: Both connection pooling tests fixed
- [ ] Task 4: HTTP mock matching tests fixed
- [ ] **TOTAL: All 15 issues resolved**
- [ ] Gateway module 100% test pass rate
- [ ] E2E test suite can collect and run
- [ ] No regressions (all previously passing tests still pass)
- [ ] Token usage: ≤440K

---

## Verification Commands

```bash
# Run all gateway unit tests
pytest tests/unit/gateway/ -v

# Run E2E tests (after import fix)
pytest tests/integration/gateway/test_gateway_e2e.py -v

# Check for regressions
pytest tests/unit/gateway/ --tb=no -q

# Verify import works
python -c "from sark.gateway import GatewayClient, HTTPTransport, SSETransport, StdioTransport; print('✅ All imports work')"
```

---

## Git Workflow

```bash
# Create branch
git checkout -b fix/gateway-test-failures

# Make fixes
# ...

# Run tests frequently
pytest tests/unit/gateway/ -v

# Commit when tests pass
git add .
git commit -m "fix: Resolve Gateway test failures for v1.2.0

Fixes 15 test issues:
- E2E import error (GatewayClient export)
- SSE async context manager (8 tests)
- HTTP connection pooling (2 tests)
- HTTP mock matching (3 tests)

All Gateway tests now passing."

# Push and create PR
git push origin fix/gateway-test-failures
gh pr create --title "fix: Gateway test failures (v1.2.0)" --body "Resolves 15 Gateway test issues blocking v1.2.0 release"
```

---

## Reference Documents

- **Completion Plan:** `docs/v1.2.0/COMPLETION_PLAN.md` (Stream 1)
- **Gateway Code:** `src/sark/gateway/`
- **Project Status:** `STATUS.md`

---

**Created:** December 9, 2025
**Worker:** TEST-1 (Gateway Test Specialist)
**Version:** v1.2.0-completion-phase1
