"""
Unit tests for rollout metrics.

Tests metric recording functions for OPA evaluations, cache operations,
and feature flag assignments.
"""


from sark.api.metrics.rollout_metrics import (
    cache_operation_duration_seconds,
    cache_operations_total,
    feature_flag_assignments_total,
    feature_flag_rollout_percentage,
    implementation_fallback_total,
    opa_evaluation_duration_seconds,
    opa_evaluation_errors_total,
    opa_evaluation_total,
    record_cache_operation,
    record_fallback,
    record_feature_flag_assignment,
    record_opa_error,
    record_opa_evaluation,
    record_rollout_percentage,
)


class TestOPAMetrics:
    """Test suite for OPA evaluation metrics."""

    def test_record_opa_evaluation(self):
        """Test recording OPA evaluation."""
        # Record an evaluation
        record_opa_evaluation(
            implementation="rust",
            duration_seconds=0.005,
            result="allow",
        )

        # Verify metrics were recorded
        # Note: We can't easily assert exact values because metrics are cumulative,
        # but we can verify the metric exists and has samples
        samples = opa_evaluation_duration_seconds.collect()[0].samples
        assert any(
            s.labels.get("implementation") == "rust"
            for s in samples
        )

        samples = opa_evaluation_total.collect()[0].samples
        assert any(
            s.labels.get("implementation") == "rust"
            and s.labels.get("result") == "allow"
            for s in samples
        )

    def test_record_opa_error(self):
        """Test recording OPA error."""
        record_opa_error(
            implementation="python",
            error_type="timeout",
        )

        # Verify error metric was recorded
        samples = opa_evaluation_errors_total.collect()[0].samples
        assert any(
            s.labels.get("implementation") == "python"
            and s.labels.get("error_type") == "timeout"
            for s in samples
        )


class TestCacheMetrics:
    """Test suite for cache operation metrics."""

    def test_record_cache_operation_hit(self):
        """Test recording cache hit."""
        record_cache_operation(
            implementation="rust",
            operation="get",
            duration_seconds=0.001,
            result="hit",
        )

        # Verify metrics were recorded
        samples = cache_operation_duration_seconds.collect()[0].samples
        assert any(
            s.labels.get("implementation") == "rust"
            and s.labels.get("operation") == "get"
            for s in samples
        )

        samples = cache_operations_total.collect()[0].samples
        assert any(
            s.labels.get("implementation") == "rust"
            and s.labels.get("operation") == "get"
            and s.labels.get("result") == "hit"
            for s in samples
        )

    def test_record_cache_operation_miss(self):
        """Test recording cache miss."""
        record_cache_operation(
            implementation="python",
            operation="get",
            duration_seconds=0.002,
            result="miss",
        )

        # Verify miss was recorded
        samples = cache_operations_total.collect()[0].samples
        assert any(
            s.labels.get("implementation") == "python"
            and s.labels.get("operation") == "get"
            and s.labels.get("result") == "miss"
            for s in samples
        )

    def test_record_cache_operation_set(self):
        """Test recording cache set."""
        record_cache_operation(
            implementation="rust",
            operation="set",
            duration_seconds=0.0015,
            result="hit",
        )

        # Verify set was recorded
        samples = cache_operations_total.collect()[0].samples
        assert any(
            s.labels.get("implementation") == "rust"
            and s.labels.get("operation") == "set"
            for s in samples
        )


class TestFeatureFlagMetrics:
    """Test suite for feature flag metrics."""

    def test_record_feature_flag_assignment_rust(self):
        """Test recording Rust assignment."""
        record_feature_flag_assignment(
            feature="rust_opa",
            implementation="rust",
        )

        # Verify assignment was recorded
        samples = feature_flag_assignments_total.collect()[0].samples
        assert any(
            s.labels.get("feature") == "rust_opa"
            and s.labels.get("implementation") == "rust"
            for s in samples
        )

    def test_record_feature_flag_assignment_python(self):
        """Test recording Python assignment."""
        record_feature_flag_assignment(
            feature="rust_cache",
            implementation="python",
        )

        # Verify assignment was recorded
        samples = feature_flag_assignments_total.collect()[0].samples
        assert any(
            s.labels.get("feature") == "rust_cache"
            and s.labels.get("implementation") == "python"
            for s in samples
        )

    def test_record_rollout_percentage(self):
        """Test recording rollout percentage."""
        record_rollout_percentage(
            feature="rust_opa",
            percentage=50,
        )

        # Verify percentage was recorded
        samples = feature_flag_rollout_percentage.collect()[0].samples
        assert any(
            s.labels.get("feature") == "rust_opa"
            for s in samples
        )


class TestFallbackMetrics:
    """Test suite for fallback metrics."""

    def test_record_fallback(self):
        """Test recording fallback event."""
        record_fallback(
            feature="rust_opa",
            error_type="initialization_error",
        )

        # Verify fallback was recorded
        samples = implementation_fallback_total.collect()[0].samples
        assert any(
            s.labels.get("feature") == "rust_opa"
            and s.labels.get("error_type") == "initialization_error"
            for s in samples
        )


class TestMetricLabels:
    """Test suite for metric label validation."""

    def test_opa_evaluation_labels(self):
        """Test OPA evaluation metric labels."""
        # Record with different implementations
        record_opa_evaluation("rust", 0.01, "allow")
        record_opa_evaluation("python", 0.02, "deny")

        # Verify both implementations are tracked
        samples = opa_evaluation_total.collect()[0].samples
        implementations = {s.labels.get("implementation") for s in samples}
        assert "rust" in implementations
        assert "python" in implementations

        results = {s.labels.get("result") for s in samples}
        assert "allow" in results
        assert "deny" in results

    def test_cache_operation_labels(self):
        """Test cache operation metric labels."""
        # Record different operations
        record_cache_operation("rust", "get", 0.001, "hit")
        record_cache_operation("rust", "set", 0.002, "hit")
        record_cache_operation("python", "delete", 0.003, "hit")

        # Verify all operations are tracked
        samples = cache_operations_total.collect()[0].samples
        operations = {s.labels.get("operation") for s in samples}
        assert "get" in operations
        assert "set" in operations
        assert "delete" in operations

    def test_multiple_features_tracked(self):
        """Test that multiple features are tracked separately."""
        record_feature_flag_assignment("rust_opa", "rust")
        record_feature_flag_assignment("rust_cache", "python")

        # Verify both features are tracked
        samples = feature_flag_assignments_total.collect()[0].samples
        features = {s.labels.get("feature") for s in samples}
        assert "rust_opa" in features
        assert "rust_cache" in features


class TestMetricTypes:
    """Test suite for verifying metric types."""

    def test_duration_metrics_are_histograms(self):
        """Test that duration metrics are histograms."""
        # Histograms should have buckets
        opa_samples = opa_evaluation_duration_seconds.collect()[0].samples
        assert any("_bucket" in s.name for s in opa_samples)

        cache_samples = cache_operation_duration_seconds.collect()[0].samples
        assert any("_bucket" in s.name for s in cache_samples)

    def test_count_metrics_are_counters(self):
        """Test that count metrics are counters."""
        # Counters should have _total suffix in their metric name (not internal _name)
        # Verify they are Counter type
        from prometheus_client import Counter
        assert isinstance(opa_evaluation_total, Counter)
        assert isinstance(cache_operations_total, Counter)
        assert isinstance(feature_flag_assignments_total, Counter)
        assert isinstance(implementation_fallback_total, Counter)


class TestMetricIntegration:
    """Integration tests for metrics workflow."""

    def test_complete_opa_workflow(self):
        """Test complete OPA evaluation workflow with metrics."""
        # Simulate successful evaluation
        record_feature_flag_assignment("rust_opa", "rust")
        record_opa_evaluation("rust", 0.005, "allow")

        # Verify both metrics recorded
        assert any(
            s.labels.get("feature") == "rust_opa"
            for s in feature_flag_assignments_total.collect()[0].samples
        )
        assert any(
            s.labels.get("implementation") == "rust"
            for s in opa_evaluation_total.collect()[0].samples
        )

    def test_complete_cache_workflow(self):
        """Test complete cache workflow with metrics."""
        # Simulate cache operations
        record_feature_flag_assignment("rust_cache", "rust")
        record_cache_operation("rust", "get", 0.001, "hit")
        record_cache_operation("rust", "set", 0.002, "hit")

        # Verify metrics recorded
        assert any(
            s.labels.get("feature") == "rust_cache"
            for s in feature_flag_assignments_total.collect()[0].samples
        )
        samples = cache_operations_total.collect()[0].samples
        assert any(
            s.labels.get("implementation") == "rust"
            and s.labels.get("operation") == "get"
            for s in samples
        )

    def test_error_and_fallback_workflow(self):
        """Test error and fallback workflow."""
        # Simulate error and fallback
        record_feature_flag_assignment("rust_opa", "rust")
        record_opa_error("rust", "initialization_error")
        record_fallback("rust_opa", "initialization_error")
        record_feature_flag_assignment("rust_opa", "python")

        # Verify error and fallback recorded
        assert any(
            s.labels.get("error_type") == "initialization_error"
            for s in opa_evaluation_errors_total.collect()[0].samples
        )
        assert any(
            s.labels.get("error_type") == "initialization_error"
            for s in implementation_fallback_total.collect()[0].samples
        )
