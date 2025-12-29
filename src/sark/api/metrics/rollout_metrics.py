"""
Prometheus metrics for Rust/Python rollout tracking.

This module provides metrics to compare performance between Rust and Python
implementations during gradual rollout.
"""

from prometheus_client import Counter, Histogram

from sark.metrics import registry

# OPA evaluation metrics
opa_evaluation_duration_seconds = Histogram(
    "opa_evaluation_duration_seconds",
    "OPA policy evaluation latency in seconds",
    ["implementation"],  # 'rust' or 'python'
    registry=registry,
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

opa_evaluation_total = Counter(
    "opa_evaluation_total",
    "Total OPA policy evaluations",
    ["implementation", "result"],  # result: 'allow' or 'deny'
    registry=registry,
)

opa_evaluation_errors_total = Counter(
    "opa_evaluation_errors_total",
    "OPA policy evaluation errors",
    ["implementation", "error_type"],  # error_type: 'timeout', 'connection', 'validation', etc.
    registry=registry,
)


# Cache operation metrics
cache_operation_duration_seconds = Histogram(
    "cache_operation_duration_seconds",
    "Cache operation latency in seconds",
    ["implementation", "operation"],  # operation: 'get', 'set', 'delete'
    registry=registry,
    buckets=[0.0001, 0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25],
)

cache_operations_total = Counter(
    "cache_operations_total",
    "Total cache operations",
    ["implementation", "operation", "result"],  # result: 'hit', 'miss', 'error'
    registry=registry,
)


# Feature flag decision metrics
feature_flag_assignments_total = Counter(
    "feature_flag_assignments_total",
    "Feature flag assignment decisions",
    ["feature", "implementation"],  # feature: 'rust_opa', 'rust_cache'
    registry=registry,
)

feature_flag_rollout_percentage = Histogram(
    "feature_flag_rollout_percentage",
    "Current rollout percentage for features",
    ["feature"],
    registry=registry,
    buckets=[0, 5, 10, 25, 50, 75, 100],
)


# Fallback metrics
implementation_fallback_total = Counter(
    "implementation_fallback_total",
    "Number of fallbacks from Rust to Python due to errors",
    ["feature", "error_type"],
    registry=registry,
)


# Implementation comparison metrics
def record_opa_evaluation(
    implementation: str,
    duration_seconds: float,
    result: str,
) -> None:
    """
    Record an OPA evaluation.

    Args:
        implementation: 'rust' or 'python'
        duration_seconds: Evaluation duration in seconds
        result: 'allow' or 'deny'
    """
    opa_evaluation_duration_seconds.labels(implementation=implementation).observe(
        duration_seconds
    )
    opa_evaluation_total.labels(
        implementation=implementation, result=result
    ).inc()


def record_opa_error(
    implementation: str,
    error_type: str,
) -> None:
    """
    Record an OPA evaluation error.

    Args:
        implementation: 'rust' or 'python'
        error_type: Error type (e.g., 'timeout', 'connection', 'validation')
    """
    opa_evaluation_errors_total.labels(
        implementation=implementation, error_type=error_type
    ).inc()


def record_cache_operation(
    implementation: str,
    operation: str,
    duration_seconds: float,
    result: str,
) -> None:
    """
    Record a cache operation.

    Args:
        implementation: 'rust' or 'python'
        operation: 'get', 'set', or 'delete'
        duration_seconds: Operation duration in seconds
        result: 'hit', 'miss', or 'error'
    """
    cache_operation_duration_seconds.labels(
        implementation=implementation, operation=operation
    ).observe(duration_seconds)
    cache_operations_total.labels(
        implementation=implementation, operation=operation, result=result
    ).inc()


def record_feature_flag_assignment(
    feature: str,
    implementation: str,
) -> None:
    """
    Record a feature flag assignment decision.

    Args:
        feature: Feature name (e.g., 'rust_opa', 'rust_cache')
        implementation: Assigned implementation ('rust' or 'python')
    """
    feature_flag_assignments_total.labels(
        feature=feature, implementation=implementation
    ).inc()


def record_rollout_percentage(
    feature: str,
    percentage: int,
) -> None:
    """
    Record current rollout percentage for a feature.

    Args:
        feature: Feature name (e.g., 'rust_opa', 'rust_cache')
        percentage: Rollout percentage (0-100)
    """
    feature_flag_rollout_percentage.labels(feature=feature).observe(percentage)


def record_fallback(
    feature: str,
    error_type: str,
) -> None:
    """
    Record a fallback from Rust to Python implementation.

    Args:
        feature: Feature name (e.g., 'rust_opa', 'rust_cache')
        error_type: Error that triggered fallback
    """
    implementation_fallback_total.labels(
        feature=feature, error_type=error_type
    ).inc()
