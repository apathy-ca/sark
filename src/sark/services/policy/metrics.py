"""Prometheus metrics for policy evaluation performance.

This module provides comprehensive metrics collection for policy evaluation
including latency, cache performance, and policy decision tracking.
"""

from functools import wraps
import time

from prometheus_client import Counter, Gauge, Histogram, Info

# ============================================================================
# POLICY EVALUATION METRICS
# ============================================================================

# Request counters
policy_evaluations_total = Counter(
    "sark_policy_evaluations_total",
    "Total number of policy evaluations",
    ["action", "sensitivity_level", "result"],
)

policy_evaluation_errors = Counter(
    "sark_policy_evaluation_errors_total",
    "Total number of policy evaluation errors",
    ["error_type"],
)

# Latency histograms
policy_evaluation_duration = Histogram(
    "sark_policy_evaluation_duration_seconds",
    "Policy evaluation latency in seconds",
    ["action", "sensitivity_level", "cache_status"],
    buckets=(
        0.001,
        0.005,
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1.0,
        2.5,
        5.0,
        7.5,
        10.0,
    ),
)

opa_request_duration = Histogram(
    "sark_opa_request_duration_seconds",
    "OPA HTTP request latency in seconds",
    ["policy"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# Batch evaluation metrics
batch_policy_evaluations_total = Counter(
    "sark_batch_policy_evaluations_total",
    "Total number of batch policy evaluations",
)

batch_evaluation_size = Histogram(
    "sark_batch_evaluation_size",
    "Number of policies in batch evaluation",
    buckets=(1, 5, 10, 25, 50, 100, 250, 500, 1000),
)

batch_evaluation_duration = Histogram(
    "sark_batch_evaluation_duration_seconds",
    "Batch policy evaluation total duration in seconds",
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# ============================================================================
# CACHE METRICS
# ============================================================================

cache_operations_total = Counter(
    "sark_policy_cache_operations_total",
    "Total number of cache operations",
    ["operation", "result"],
)

cache_hits_total = Counter(
    "sark_policy_cache_hits_total",
    "Total number of cache hits",
    ["sensitivity_level"],
)

cache_misses_total = Counter(
    "sark_policy_cache_misses_total",
    "Total number of cache misses",
    ["sensitivity_level"],
)

cache_latency = Histogram(
    "sark_policy_cache_latency_seconds",
    "Cache operation latency in seconds",
    ["operation"],
    buckets=(0.0001, 0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1),
)

cache_size_bytes = Gauge(
    "sark_policy_cache_size_bytes",
    "Current size of policy cache in bytes",
)

cache_entries = Gauge(
    "sark_policy_cache_entries",
    "Current number of entries in policy cache",
)

# Cache optimization metrics (v2)
cache_stale_hits_total = Counter(
    "sark_policy_cache_stale_hits_total",
    "Total number of stale cache hits (stale-while-revalidate)",
    ["sensitivity_level"],
)

cache_revalidations_total = Counter(
    "sark_policy_cache_revalidations_total",
    "Total number of background cache revalidations",
    ["status"],  # success, failure
)

cache_batch_operations_total = Counter(
    "sark_policy_cache_batch_operations_total",
    "Total number of batch cache operations",
    ["operation"],  # get_batch, set_batch
)

cache_batch_items = Histogram(
    "sark_policy_cache_batch_items",
    "Number of items in batch cache operations",
    ["operation"],
    buckets=(1, 5, 10, 25, 50, 100, 250, 500, 1000),
)

cache_batch_hit_rate = Histogram(
    "sark_policy_cache_batch_hit_rate",
    "Hit rate for batch cache operations (percentage)",
    buckets=(0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100),
)

# ============================================================================
# POLICY DECISION METRICS
# ============================================================================

policy_allows_total = Counter(
    "sark_policy_allows_total",
    "Total number of allowed policy decisions",
    ["action", "sensitivity_level"],
)

policy_denials_total = Counter(
    "sark_policy_denials_total",
    "Total number of denied policy decisions",
    ["action", "sensitivity_level", "denial_reason"],
)

policy_violations_total = Counter(
    "sark_policy_violations_total",
    "Total number of policy violations detected",
    ["policy_name", "violation_type"],
)

# ============================================================================
# ADVANCED POLICY METRICS
# ============================================================================

time_based_restrictions_total = Counter(
    "sark_time_based_restrictions_total",
    "Total number of time-based restriction checks",
    ["result", "is_business_hours"],
)

ip_filtering_checks_total = Counter(
    "sark_ip_filtering_checks_total",
    "Total number of IP filtering checks",
    ["result", "is_private_ip", "vpn_required"],
)

mfa_requirement_checks_total = Counter(
    "sark_mfa_requirement_checks_total",
    "Total number of MFA requirement checks",
    ["result", "mfa_verified", "session_valid"],
)

# ============================================================================
# SYSTEM METRICS
# ============================================================================

active_policy_evaluations = Gauge(
    "sark_active_policy_evaluations",
    "Number of currently active policy evaluations",
)

redis_connection_pool_size = Gauge(
    "sark_redis_connection_pool_size",
    "Current size of Redis connection pool",
)

redis_connection_errors = Counter(
    "sark_redis_connection_errors_total",
    "Total number of Redis connection errors",
)

# ============================================================================
# INFO METRICS
# ============================================================================

policy_service_info = Info(
    "sark_policy_service",
    "Policy service version and configuration",
)

# ============================================================================
# DECORATORS FOR AUTOMATIC METRICS
# ============================================================================


def track_policy_evaluation(func):
    """Decorator to automatically track policy evaluation metrics."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract auth input from args or kwargs
        auth_input = args[1] if len(args) > 1 else kwargs.get("auth_input")

        action = auth_input.action if auth_input else "unknown"
        sensitivity = (
            auth_input.tool.get("sensitivity_level", "unknown")
            if auth_input and hasattr(auth_input, "tool")
            else "unknown"
        )

        # Track active evaluations
        active_policy_evaluations.inc()
        start_time = time.perf_counter()

        try:
            result = await func(*args, **kwargs)

            # Track evaluation duration
            duration = time.perf_counter() - start_time
            cache_status = (
                "hit" if hasattr(result, "_from_cache") and result._from_cache else "miss"
            )

            policy_evaluation_duration.labels(
                action=action, sensitivity_level=sensitivity, cache_status=cache_status
            ).observe(duration)

            # Track result
            result_label = "allow" if result.allow else "deny"
            policy_evaluations_total.labels(
                action=action, sensitivity_level=sensitivity, result=result_label
            ).inc()

            if result.allow:
                policy_allows_total.labels(action=action, sensitivity_level=sensitivity).inc()
            else:
                # Extract denial reason
                denial_reason = result.reason[:50] if result.reason else "unknown"
                policy_denials_total.labels(
                    action=action, sensitivity_level=sensitivity, denial_reason=denial_reason
                ).inc()

            return result

        except Exception as e:
            # Track errors
            error_type = type(e).__name__
            policy_evaluation_errors.labels(error_type=error_type).inc()
            raise

        finally:
            active_policy_evaluations.dec()

    return wrapper


def track_cache_operation(operation: str):
    """Decorator to track cache operations."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()

            try:
                result = await func(*args, **kwargs)

                # Track latency
                duration = time.perf_counter() - start_time
                cache_latency.labels(operation=operation).observe(duration)

                # Track operation result
                result_label = "success" if result is not None else "miss"
                cache_operations_total.labels(operation=operation, result=result_label).inc()

                return result

            except Exception:
                # Track errors
                cache_operations_total.labels(operation=operation, result="error").inc()
                redis_connection_errors.inc()
                raise

        return wrapper

    return decorator


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def record_cache_hit(sensitivity_level: str = "unknown"):
    """Record a cache hit."""
    cache_hits_total.labels(sensitivity_level=sensitivity_level).inc()


def record_cache_miss(sensitivity_level: str = "unknown"):
    """Record a cache miss."""
    cache_misses_total.labels(sensitivity_level=sensitivity_level).inc()


def record_policy_violation(policy_name: str, violation_type: str):
    """Record a policy violation."""
    policy_violations_total.labels(policy_name=policy_name, violation_type=violation_type).inc()


def record_time_based_check(result: str, is_business_hours: bool):
    """Record a time-based restriction check."""
    time_based_restrictions_total.labels(
        result=result, is_business_hours=str(is_business_hours)
    ).inc()


def record_ip_filtering_check(result: str, is_private_ip: bool, vpn_required: bool):
    """Record an IP filtering check."""
    ip_filtering_checks_total.labels(
        result=result, is_private_ip=str(is_private_ip), vpn_required=str(vpn_required)
    ).inc()


def record_mfa_check(result: str, mfa_verified: bool, session_valid: bool):
    """Record an MFA requirement check."""
    mfa_requirement_checks_total.labels(
        result=result, mfa_verified=str(mfa_verified), session_valid=str(session_valid)
    ).inc()


def update_cache_size(size_bytes: int, entry_count: int):
    """Update cache size metrics."""
    cache_size_bytes.set(size_bytes)
    cache_entries.set(entry_count)


def set_service_info(version: str, cache_enabled: bool, opa_url: str):
    """Set policy service info."""
    policy_service_info.info(
        {
            "version": version,
            "cache_enabled": str(cache_enabled),
            "opa_url": opa_url,
        }
    )


# ============================================================================
# METRICS COLLECTOR
# ============================================================================


class PolicyMetricsCollector:
    """Collects and aggregates policy evaluation metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self.evaluations = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.allows = 0
        self.denials = 0
        self.errors = 0

    def record_evaluation(
        self,
        duration: float,
        allow: bool,
        cached: bool,
        action: str,
        sensitivity: str,
    ):
        """Record a policy evaluation."""
        self.evaluations += 1

        if cached:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

        if allow:
            self.allows += 1
        else:
            self.denials += 1

    def get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total * 100) if total > 0 else 0.0

    def get_denial_rate(self) -> float:
        """Calculate denial rate."""
        total = self.allows + self.denials
        return (self.denials / total * 100) if total > 0 else 0.0

    def get_summary(self) -> dict:
        """Get metrics summary."""
        return {
            "evaluations": self.evaluations,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.get_cache_hit_rate(),
            "allows": self.allows,
            "denials": self.denials,
            "denial_rate": self.get_denial_rate(),
            "errors": self.errors,
        }
