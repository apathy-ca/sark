# Workstream 3: Gateway & Adapters Tests

**Worker ID**: gateway-adapters
**Branch**: feat/tests-gateway-adapters
**Duration**: 2-3 days
**Target Coverage**: 12 modules (0-20% → 85%)

---

## Objective

Write comprehensive tests for Gateway client, transports, protocol adapters, and error handling to achieve 85% code coverage.

---

## Modules to Test (12 modules)

### Gateway Core (4 modules)
1. `src/sark/gateway/client.py` (30 lines, 0% coverage)
2. `src/sark/gateway/error_handler.py` (current: low coverage)
3. `src/sark/services/gateway/client.py` (30 lines, 0% coverage)
4. `src/sark/services/gateway/authorization.py` (78 lines, 0% coverage)

### Gateway Transports (3 modules)
5. `src/sark/gateway/transports/http_client.py` (current: low coverage)
6. `src/sark/gateway/transports/sse_client.py` (current: low coverage)
7. `src/sark/gateway/transports/stdio_client.py` (current: low coverage)

### Protocol Adapters (5 modules)
8. `src/sark/adapters/grpc_adapter.py` (current: 0% coverage)
9. `src/sark/adapters/http_adapter.py` (current: 0% coverage)
10. `src/sark/adapters/mcp_adapter.py` (current: 0% coverage)
11. `src/sark/adapters/base.py` (current: 0% coverage)
12. `src/sark/api/v1/gateway.py` (142 lines, 0% coverage)

---

## Test Strategy

### 1. Gateway Client Tests
**File**: `tests/unit/gateway/test_gateway_client.py`

**Coverage Goals**:
- Client initialization
- Transport selection (HTTP, SSE, stdio)
- Server connection
- Tool invocation
- Response parsing
- Connection pooling
- Error handling

**Example Test**:
```python
@pytest.mark.asyncio
async def test_gateway_client_http_transport():
    """Test Gateway client with HTTP transport."""
    client = GatewayClient(
        endpoint="http://localhost:8080",
        transport=TransportMode.HTTP
    )

    # Connect
    await client.connect()
    assert client.is_connected

    # Invoke tool
    result = await client.invoke_tool(
        tool_name="test_tool",
        parameters={"input": "test"}
    )
    assert result is not None

    # Disconnect
    await client.disconnect()
    assert not client.is_connected
```

### 2. HTTP Transport Tests
**File**: `tests/unit/gateway/transports/test_http_client.py`

**Coverage Goals**:
- HTTP request/response
- Connection pooling
- Timeout handling
- Retry logic
- Error codes (4xx, 5xx)
- Request headers
- Response parsing

### 3. SSE Transport Tests
**File**: `tests/unit/gateway/transports/test_sse_client.py`

**Coverage Goals**:
- SSE connection establishment
- Event stream parsing
- Reconnection logic
- Heartbeat handling
- Connection state management
- Error handling
- Event filtering

### 4. stdio Transport Tests
**File**: `tests/unit/gateway/transports/test_stdio_client.py`

**Coverage Goals**:
- Process spawning
- stdin/stdout communication
- JSON-RPC message passing
- Process lifecycle
- Error handling
- Timeout handling
- Resource cleanup

### 5. Circuit Breaker Tests
**File**: `tests/unit/gateway/test_circuit_breaker.py`

**Coverage Goals**:
- State transitions (CLOSED → OPEN → HALF_OPEN)
- Failure threshold
- Timeout period
- Success threshold for half-open
- Error rate calculation
- Manual reset
- State persistence

### 6. Retry Logic Tests
**File**: `tests/unit/gateway/test_retry_handler.py`

**Coverage Goals**:
- Exponential backoff
- Max retry attempts
- Retry conditions
- Timeout between retries
- Jitter calculation
- Retry exhaustion

### 7. Protocol Adapter Tests
**Files**:
- `tests/unit/adapters/test_grpc_adapter.py`
- `tests/unit/adapters/test_http_adapter.py`
- `tests/unit/adapters/test_mcp_adapter.py`

**Coverage Goals**:
- Protocol translation
- Request/response mapping
- Error handling
- Streaming support
- Metadata handling
- Connection management

---

## Fixtures to Use

From `tests/fixtures/integration_docker.py`:
- `grpc_mock_service` - For gRPC adapter tests
- `all_services` - For full integration tests

Additional fixtures needed:
- `mock_http_server` - For HTTP transport tests
- `mock_sse_server` - For SSE transport tests
- `mock_stdio_process` - For stdio transport tests

---

## Success Criteria

- ✅ All 12 modules have ≥85% code coverage
- ✅ All tests pass
- ✅ Tests cover all three transports (HTTP, SSE, stdio)
- ✅ Circuit breaker state machine fully tested
- ✅ Retry logic thoroughly tested
- ✅ Protocol adapters tested with mock servers
- ✅ Error scenarios covered (timeouts, network failures, invalid responses)

---

## Test Pattern Example

```python
import pytest
from unittest.mock import AsyncMock, patch
from sark.gateway import CircuitBreaker, CircuitState

class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    @pytest.fixture
    def circuit_breaker(self):
        """Create circuit breaker instance."""
        return CircuitBreaker(
            failure_threshold=3,
            timeout=5.0,
            success_threshold=2
        )

    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self, circuit_breaker):
        """Test that circuit opens after threshold failures."""
        failing_func = AsyncMock(side_effect=Exception("Error"))

        # Should fail threshold times
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)

        # Circuit should now be open
        assert circuit_breaker.state == CircuitState.OPEN

        # Next call should fail fast
        with pytest.raises(CircuitBreakerError):
            await circuit_breaker.call(failing_func)

    @pytest.mark.asyncio
    async def test_circuit_recovers_after_success(self, circuit_breaker):
        """Test circuit recovery after successful calls."""
        # Open the circuit
        circuit_breaker._state = CircuitState.HALF_OPEN

        success_func = AsyncMock(return_value="success")

        # Success threshold calls
        for _ in range(2):
            result = await circuit_breaker.call(success_func)
            assert result == "success"

        # Circuit should close
        assert circuit_breaker.state == CircuitState.CLOSED
```

---

## Priority Order

1. **High Priority** (Day 1):
   - Gateway client tests
   - HTTP transport tests
   - Circuit breaker tests

2. **Medium Priority** (Day 2):
   - SSE transport tests
   - stdio transport tests
   - Retry handler tests

3. **Low Priority** (Day 3):
   - Protocol adapter tests (gRPC, HTTP, MCP)
   - Gateway authorization tests
   - API endpoint tests

---

## Deliverables

1. Test files for all 12 modules
2. Coverage report showing 85%+ coverage
3. All tests passing in CI
4. Mock server implementations for testing
5. Commit message:
   ```
   test: Add gateway & adapter test suite

   - Add Gateway client tests (90% coverage)
   - Add HTTP transport tests (88% coverage)
   - Add SSE transport tests (85% coverage)
   - Add stdio transport tests (86% coverage)
   - Add circuit breaker tests (95% coverage)
   - Add retry handler tests (92% coverage)
   - Add protocol adapter tests (84% coverage)

   Total: 12 modules, 350+ tests, 85%+ coverage

   Part of Phase 3 Workstream 3 (v1.3.1 implementation plan)
   ```

---

## Notes

- Use pytest-httpx for HTTP mocking
- Use pytest-mock for process mocking
- Test all error scenarios (network failures, timeouts, invalid responses)
- Validate circuit breaker state transitions
- Test retry backoff timing
