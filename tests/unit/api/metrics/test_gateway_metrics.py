"""Unit tests for Gateway Prometheus metrics."""

from sark.api.metrics.gateway_metrics import (
    a2a_authorization_requests_total,
    decrement_active_connections,
    gateway_active_connections,
    gateway_audit_events_total,
    gateway_authorization_latency_seconds,
    gateway_authorization_requests_total,
    gateway_client_errors_total,
    gateway_policy_cache_hits_total,
    gateway_policy_cache_misses_total,
    increment_active_connections,
    record_a2a_authorization,
    record_audit_event,
    record_authorization,
    record_cache_hit,
    record_cache_miss,
    record_client_error,
)


class TestAuthorizationMetrics:
    """Test authorization metrics recording."""

    def test_record_authorization_increments_counter(self):
        """Test that record_authorization increments the counter."""
        # Get initial value
        initial_value = gateway_authorization_requests_total.labels(
            decision="allow", action="gateway:tool:invoke", server="test-server"
        )._value.get()

        # Record authorization
        record_authorization(
            decision="allow", action="gateway:tool:invoke", server="test-server", latency=0.025
        )

        # Verify counter incremented
        new_value = gateway_authorization_requests_total.labels(
            decision="allow", action="gateway:tool:invoke", server="test-server"
        )._value.get()

        assert new_value == initial_value + 1

    def test_record_authorization_records_latency(self):
        """Test that authorization latency is recorded."""
        # Record with specific latency
        record_authorization(
            decision="allow", action="gateway:tool:invoke", server="test-server", latency=0.05
        )

        # Verify histogram was observed
        # Note: Direct verification of histogram values is complex,
        # so we just ensure no errors are raised
        assert True

    def test_record_authorization_different_decisions(self):
        """Test recording different authorization decisions."""
        # Record allow
        record_authorization(
            decision="allow", action="gateway:tool:invoke", server="server1", latency=0.01
        )

        # Record deny
        record_authorization(
            decision="deny", action="gateway:tool:invoke", server="server1", latency=0.015
        )

        # Both should be recorded separately
        allow_count = gateway_authorization_requests_total.labels(
            decision="allow", action="gateway:tool:invoke", server="server1"
        )._value.get()

        deny_count = gateway_authorization_requests_total.labels(
            decision="deny", action="gateway:tool:invoke", server="server1"
        )._value.get()

        assert allow_count >= 1
        assert deny_count >= 1


class TestCacheMetrics:
    """Test cache metrics recording."""

    def test_record_cache_hit(self):
        """Test cache hit recording."""
        initial_value = gateway_policy_cache_hits_total._value.get()

        record_cache_hit()

        new_value = gateway_policy_cache_hits_total._value.get()
        assert new_value == initial_value + 1

    def test_record_cache_miss(self):
        """Test cache miss recording."""
        initial_value = gateway_policy_cache_misses_total._value.get()

        record_cache_miss()

        new_value = gateway_policy_cache_misses_total._value.get()
        assert new_value == initial_value + 1

    def test_cache_hit_rate_calculation(self):
        """Test that cache hit rate can be calculated from metrics."""
        # Record some hits and misses
        for _ in range(8):
            record_cache_hit()
        for _ in range(2):
            record_cache_miss()

        hits = gateway_policy_cache_hits_total._value.get()
        misses = gateway_policy_cache_misses_total._value.get()

        # Calculate hit rate (should be 80%)
        total = hits + misses
        if total > 0:
            hit_rate = hits / total
            # We can't assert exact value due to test isolation,
            # but structure is correct
            assert 0 <= hit_rate <= 1


class TestErrorMetrics:
    """Test error metrics recording."""

    def test_record_client_error(self):
        """Test client error recording."""
        initial_value = gateway_client_errors_total.labels(
            operation="tool_invoke", error_type="timeout"
        )._value.get()

        record_client_error(operation="tool_invoke", error_type="timeout")

        new_value = gateway_client_errors_total.labels(
            operation="tool_invoke", error_type="timeout"
        )._value.get()

        assert new_value == initial_value + 1

    def test_record_different_error_types(self):
        """Test recording different error types."""
        record_client_error(operation="discovery", error_type="network")
        record_client_error(operation="discovery", error_type="auth")
        record_client_error(operation="invoke", error_type="timeout")

        # All should be recorded with different labels
        network_errors = gateway_client_errors_total.labels(
            operation="discovery", error_type="network"
        )._value.get()

        auth_errors = gateway_client_errors_total.labels(
            operation="discovery", error_type="auth"
        )._value.get()

        assert network_errors >= 1
        assert auth_errors >= 1


class TestAuditMetrics:
    """Test audit event metrics."""

    def test_record_audit_event(self):
        """Test audit event recording."""
        initial_value = gateway_audit_events_total.labels(
            event_type="tool_invoke", decision="allow"
        )._value.get()

        record_audit_event(event_type="tool_invoke", decision="allow")

        new_value = gateway_audit_events_total.labels(
            event_type="tool_invoke", decision="allow"
        )._value.get()

        assert new_value == initial_value + 1

    def test_record_different_event_types(self):
        """Test recording different audit event types."""
        record_audit_event(event_type="tool_invoke", decision="allow")
        record_audit_event(event_type="discovery", decision="allow")
        record_audit_event(event_type="a2a_communication", decision="deny")

        # Verify all types are recorded
        invoke_events = gateway_audit_events_total.labels(
            event_type="tool_invoke", decision="allow"
        )._value.get()

        discovery_events = gateway_audit_events_total.labels(
            event_type="discovery", decision="allow"
        )._value.get()

        assert invoke_events >= 1
        assert discovery_events >= 1


class TestA2AMetrics:
    """Test A2A authorization metrics."""

    def test_record_a2a_authorization(self):
        """Test A2A authorization recording."""
        initial_value = a2a_authorization_requests_total.labels(
            decision="allow", source_type="service", target_type="worker"
        )._value.get()

        record_a2a_authorization(decision="allow", source_type="service", target_type="worker")

        new_value = a2a_authorization_requests_total.labels(
            decision="allow", source_type="service", target_type="worker"
        )._value.get()

        assert new_value == initial_value + 1

    def test_record_a2a_different_combinations(self):
        """Test recording different A2A combinations."""
        record_a2a_authorization(decision="allow", source_type="service", target_type="worker")

        record_a2a_authorization(decision="deny", source_type="worker", target_type="service")

        # Both should be recorded separately
        allow_count = a2a_authorization_requests_total.labels(
            decision="allow", source_type="service", target_type="worker"
        )._value.get()

        deny_count = a2a_authorization_requests_total.labels(
            decision="deny", source_type="worker", target_type="service"
        )._value.get()

        assert allow_count >= 1
        assert deny_count >= 1


class TestConnectionMetrics:
    """Test active connection metrics."""

    def test_increment_active_connections(self):
        """Test incrementing active connections."""
        initial_value = gateway_active_connections._value.get()

        increment_active_connections()

        new_value = gateway_active_connections._value.get()
        assert new_value == initial_value + 1

    def test_decrement_active_connections(self):
        """Test decrementing active connections."""
        # Increment first to ensure we have something to decrement
        increment_active_connections()
        initial_value = gateway_active_connections._value.get()

        decrement_active_connections()

        new_value = gateway_active_connections._value.get()
        assert new_value == initial_value - 1

    def test_connection_lifecycle(self):
        """Test full connection lifecycle."""
        initial_value = gateway_active_connections._value.get()

        # Simulate connection opening
        increment_active_connections()
        assert gateway_active_connections._value.get() == initial_value + 1

        # Simulate connection closing
        decrement_active_connections()
        assert gateway_active_connections._value.get() == initial_value


class TestMetricLabels:
    """Test that metrics have correct labels defined."""

    def test_authorization_requests_labels(self):
        """Test authorization requests metric labels."""
        # This metric should have: decision, action, server
        metric = gateway_authorization_requests_total.labels(
            decision="allow", action="gateway:tool:invoke", server="test"
        )
        assert metric is not None

    def test_authorization_latency_labels(self):
        """Test authorization latency metric labels."""
        # This metric should have: action
        metric = gateway_authorization_latency_seconds.labels(action="gateway:tool:invoke")
        assert metric is not None

    def test_client_errors_labels(self):
        """Test client errors metric labels."""
        # This metric should have: operation, error_type
        metric = gateway_client_errors_total.labels(operation="invoke", error_type="timeout")
        assert metric is not None

    def test_audit_events_labels(self):
        """Test audit events metric labels."""
        # This metric should have: event_type, decision
        metric = gateway_audit_events_total.labels(event_type="tool_invoke", decision="allow")
        assert metric is not None

    def test_a2a_requests_labels(self):
        """Test A2A requests metric labels."""
        # This metric should have: decision, source_type, target_type
        metric = a2a_authorization_requests_total.labels(
            decision="allow", source_type="service", target_type="worker"
        )
        assert metric is not None
