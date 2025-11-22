"""Tests for circuit breaker pattern."""

import asyncio
import time
from unittest.mock import AsyncMock

import pytest

from sark.services.audit.siem.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitState,
)


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60
        assert config.success_threshold == 2
        assert config.timeout == 30

    def test_custom_config(self):
        """Test custom configuration values."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30,
            success_threshold=1,
            timeout=15,
        )
        assert config.failure_threshold == 3
        assert config.recovery_timeout == 30
        assert config.success_threshold == 1
        assert config.timeout == 15


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    @pytest.fixture
    def config(self) -> CircuitBreakerConfig:
        """Create circuit breaker config for testing."""
        return CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=2,  # Short timeout for testing
            success_threshold=2,
            timeout=5,
        )

    @pytest.fixture
    def breaker(self, config: CircuitBreakerConfig) -> CircuitBreaker:
        """Create circuit breaker for testing."""
        return CircuitBreaker("test", config)

    @pytest.mark.asyncio
    async def test_initial_state(self, breaker: CircuitBreaker):
        """Test initial circuit breaker state."""
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.success_count == 0

    @pytest.mark.asyncio
    async def test_successful_call(self, breaker: CircuitBreaker):
        """Test successful operation call."""
        mock_op = AsyncMock(return_value="success")
        result = await breaker.call(mock_op)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_failed_call(self, breaker: CircuitBreaker):
        """Test failed operation call."""
        mock_op = AsyncMock(side_effect=Exception("Test error"))

        with pytest.raises(Exception, match="Test error"):
            await breaker.call(mock_op)

        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 1

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self, breaker: CircuitBreaker):
        """Test circuit opens after failure threshold."""
        mock_op = AsyncMock(side_effect=Exception("Test error"))

        # Fail 3 times (threshold)
        for i in range(3):
            with pytest.raises(Exception):
                await breaker.call(mock_op)

        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 3
        assert breaker.opened_at is not None

    @pytest.mark.asyncio
    async def test_circuit_breaker_error_when_open(self, breaker: CircuitBreaker):
        """Test CircuitBreakerError is raised when circuit is open."""
        mock_op = AsyncMock(side_effect=Exception("Test error"))

        # Open the circuit
        for i in range(3):
            with pytest.raises(Exception):
                await breaker.call(mock_op)

        # Next call should raise CircuitBreakerError
        with pytest.raises(CircuitBreakerError) as exc_info:
            await breaker.call(mock_op)

        assert "Circuit breaker 'test' is open" in str(exc_info.value)
        assert exc_info.value.retry_after > 0

    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open(self, breaker: CircuitBreaker):
        """Test circuit transitions to half-open after timeout."""
        mock_op = AsyncMock(side_effect=Exception("Test error"))

        # Open the circuit
        for i in range(3):
            with pytest.raises(Exception):
                await breaker.call(mock_op)

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(2.1)

        # Next call should transition to half-open (and fail)
        mock_op.side_effect = Exception("Still failing")
        with pytest.raises(Exception):
            await breaker.call(mock_op)

        # Should be back to OPEN after failure in HALF_OPEN
        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_closes_after_successful_recovery(self, breaker: CircuitBreaker):
        """Test circuit closes after successful operations in half-open."""
        mock_op = AsyncMock(side_effect=Exception("Test error"))

        # Open the circuit
        for i in range(3):
            with pytest.raises(Exception):
                await breaker.call(mock_op)

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(2.1)

        # Succeed in half-open state (need 2 successes)
        mock_op.side_effect = None
        mock_op.return_value = "success"

        result1 = await breaker.call(mock_op)
        assert result1 == "success"
        assert breaker.state == CircuitState.HALF_OPEN

        result2 = await breaker.call(mock_op)
        assert result2 == "success"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_timeout_counts_as_failure(self, breaker: CircuitBreaker):
        """Test operation timeout counts as failure."""
        async def slow_op():
            await asyncio.sleep(10)  # Longer than timeout
            return "success"

        with pytest.raises(asyncio.TimeoutError):
            await breaker.call(slow_op)

        assert breaker.failure_count == 1

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self, breaker: CircuitBreaker):
        """Test successful operation resets failure count."""
        mock_op = AsyncMock()

        # Fail twice
        mock_op.side_effect = Exception("Error")
        for i in range(2):
            with pytest.raises(Exception):
                await breaker.call(mock_op)

        assert breaker.failure_count == 2

        # Succeed
        mock_op.side_effect = None
        mock_op.return_value = "success"
        await breaker.call(mock_op)

        assert breaker.failure_count == 0
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_get_state(self, breaker: CircuitBreaker):
        """Test get_state returns correct information."""
        state = breaker.get_state()

        assert state["name"] == "test"
        assert state["state"] == "closed"
        assert state["failure_count"] == 0
        assert state["success_count"] == 0
        assert state["failure_threshold"] == 3
        assert state["success_threshold"] == 2
        assert state["recovery_timeout"] == 2
        assert state["opened_at"] is None
        assert state["retry_after"] == 0

    @pytest.mark.asyncio
    async def test_get_state_when_open(self, breaker: CircuitBreaker):
        """Test get_state when circuit is open."""
        mock_op = AsyncMock(side_effect=Exception("Error"))

        # Open the circuit
        for i in range(3):
            with pytest.raises(Exception):
                await breaker.call(mock_op)

        state = breaker.get_state()

        assert state["state"] == "open"
        assert state["failure_count"] == 3
        assert state["opened_at"] is not None
        assert state["retry_after"] > 0

    @pytest.mark.asyncio
    async def test_manual_reset(self, breaker: CircuitBreaker):
        """Test manual circuit reset."""
        mock_op = AsyncMock(side_effect=Exception("Error"))

        # Open the circuit
        for i in range(3):
            with pytest.raises(Exception):
                await breaker.call(mock_op)

        assert breaker.state == CircuitState.OPEN

        # Manually reset
        breaker.reset()

        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.success_count == 0
        assert breaker.opened_at is None

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self, breaker: CircuitBreaker):
        """Test failure in half-open state reopens circuit."""
        mock_op = AsyncMock(side_effect=Exception("Error"))

        # Open the circuit
        for i in range(3):
            with pytest.raises(Exception):
                await breaker.call(mock_op)

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery
        await asyncio.sleep(2.1)

        # Fail in half-open (should reopen)
        with pytest.raises(Exception):
            await breaker.call(mock_op)

        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_concurrent_calls(self, breaker: CircuitBreaker):
        """Test concurrent calls are properly synchronized."""
        call_count = 0

        async def counting_op():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return call_count

        # Make concurrent calls
        results = await asyncio.gather(*[breaker.call(counting_op) for _ in range(10)])

        assert len(results) == 10
        assert all(isinstance(r, int) for r in results)
        assert call_count == 10

    @pytest.mark.asyncio
    async def test_retry_after_decreases(self, breaker: CircuitBreaker):
        """Test retry_after value decreases over time."""
        mock_op = AsyncMock(side_effect=Exception("Error"))

        # Open the circuit
        for i in range(3):
            with pytest.raises(Exception):
                await breaker.call(mock_op)

        state1 = breaker.get_state()
        retry_after_1 = state1["retry_after"]

        # Wait a bit
        await asyncio.sleep(0.5)

        state2 = breaker.get_state()
        retry_after_2 = state2["retry_after"]

        assert retry_after_2 < retry_after_1
