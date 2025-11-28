"""Gateway metrics collector for Prometheus."""

from prometheus_client import Counter, Histogram, Gauge, Summary
import time
from typing import Optional
from contextlib import contextmanager

# ============================================================================
# Request Metrics
# ============================================================================

gateway_requests_total = Counter(
    "sark_gateway_requests_total",
    "Total Gateway requests",
    ["method", "endpoint", "status", "user", "tool"],
)

gateway_requests_in_flight = Gauge(
    "sark_gateway_requests_in_flight",
    "Current number of Gateway requests being processed",
)

gateway_request_duration_seconds = Histogram(
    "sark_gateway_request_duration_seconds",
    "Gateway request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# ============================================================================
# Tool Invocation Metrics
# ============================================================================

gateway_tool_invocations_total = Counter(
    "sark_gateway_tool_invocations_total",
    "Total tool invocations",
    ["tool", "server", "status", "user"],
)

gateway_tool_execution_duration_seconds = Histogram(
    "sark_gateway_tool_execution_duration_seconds",
    "Tool execution duration in seconds",
    ["tool", "server"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

gateway_tool_invocation_rate = Summary(
    "sark_gateway_tool_invocation_rate",
    "Tool invocation rate per minute",
    ["tool"],
)

# ============================================================================
# Connection Metrics
# ============================================================================

gateway_active_connections = Gauge(
    "sark_gateway_active_connections",
    "Number of active Gateway connections",
    ["connection_type"],
)

gateway_connection_pool_size = Gauge(
    "sark_gateway_connection_pool_size",
    "Connection pool size",
    ["pool_name"],
)

gateway_connection_pool_active = Gauge(
    "sark_gateway_connection_pool_active",
    "Active connections in pool",
    ["pool_name"],
)

# ============================================================================
# Error Metrics
# ============================================================================

gateway_errors_total = Counter(
    "sark_gateway_errors_total",
    "Total Gateway errors",
    ["error_type", "component", "severity"],
)

gateway_auth_failures_total = Counter(
    "sark_gateway_auth_failures_total",
    "Authentication failures",
    ["reason", "user"],
)

gateway_rate_limit_exceeded_total = Counter(
    "sark_gateway_rate_limit_exceeded_total",
    "Rate limit violations",
    ["user", "limit_type"],
)

# ============================================================================
# Cache Metrics
# ============================================================================

gateway_cache_operations_total = Counter(
    "sark_gateway_cache_operations_total",
    "Cache operations",
    ["operation", "cache_name", "result"],
)

gateway_cache_size_bytes = Gauge(
    "sark_gateway_cache_size_bytes",
    "Cache size in bytes",
    ["cache_name"],
)

gateway_cache_evictions_total = Counter(
    "sark_gateway_cache_evictions_total",
    "Cache evictions",
    ["cache_name", "reason"],
)

# ============================================================================
# User Activity Metrics
# ============================================================================

gateway_unique_users = Gauge(
    "sark_gateway_unique_users",
    "Number of unique active users",
)

gateway_requests_by_user = Counter(
    "sark_gateway_requests_by_user",
    "Requests per user",
    ["user_id"],
)

gateway_user_sessions_active = Gauge(
    "sark_gateway_user_sessions_active",
    "Active user sessions",
)


class GatewayMetricsCollector:
    """Comprehensive metrics collector for Gateway operations."""

    def __init__(self):
        """Initialize the metrics collector."""
        self._request_start_times = {}

    @contextmanager
    def track_request(self, method: str, endpoint: str, user: Optional[str] = None):
        """
        Context manager to track request metrics.

        Args:
            method: HTTP method
            endpoint: API endpoint
            user: User ID (optional)
        """
        gateway_requests_in_flight.inc()
        start_time = time.time()

        try:
            yield
            # Success case
            duration = time.time() - start_time
            gateway_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)

            gateway_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status="success",
                user=user or "anonymous",
                tool="",
            ).inc()

        except Exception as e:
            # Error case
            gateway_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status="error",
                user=user or "anonymous",
                tool="",
            ).inc()
            raise

        finally:
            gateway_requests_in_flight.dec()

    def record_tool_invocation(
        self,
        tool: str,
        server: str,
        user: str,
        duration: float,
        status: str = "success",
    ):
        """
        Record a tool invocation.

        Args:
            tool: Tool name
            server: Server name
            user: User ID
            duration: Execution duration in seconds
            status: success or error
        """
        gateway_tool_invocations_total.labels(
            tool=tool,
            server=server,
            status=status,
            user=user,
        ).inc()

        gateway_tool_execution_duration_seconds.labels(
            tool=tool,
            server=server,
        ).observe(duration)

    def record_connection(self, connection_type: str, action: str):
        """
        Record connection activity.

        Args:
            connection_type: Type of connection (websocket, http, grpc)
            action: open or close
        """
        if action == "open":
            gateway_active_connections.labels(connection_type=connection_type).inc()
        elif action == "close":
            gateway_active_connections.labels(connection_type=connection_type).dec()

    def record_error(
        self,
        error_type: str,
        component: str,
        severity: str = "error",
    ):
        """
        Record an error.

        Args:
            error_type: Type of error
            component: Component where error occurred
            severity: Error severity (info, warning, error, critical)
        """
        gateway_errors_total.labels(
            error_type=error_type,
            component=component,
            severity=severity,
        ).inc()

    def record_auth_failure(self, reason: str, user: Optional[str] = None):
        """
        Record authentication failure.

        Args:
            reason: Failure reason
            user: User ID (if available)
        """
        gateway_auth_failures_total.labels(
            reason=reason,
            user=user or "unknown",
        ).inc()

    def record_rate_limit(self, user: str, limit_type: str):
        """
        Record rate limit violation.

        Args:
            user: User ID
            limit_type: Type of rate limit (requests, tokens, bandwidth)
        """
        gateway_rate_limit_exceeded_total.labels(
            user=user,
            limit_type=limit_type,
        ).inc()

    def record_cache_operation(
        self,
        operation: str,
        cache_name: str,
        result: str,
    ):
        """
        Record cache operation.

        Args:
            operation: get, set, delete
            cache_name: Name of cache
            result: hit, miss, error
        """
        gateway_cache_operations_total.labels(
            operation=operation,
            cache_name=cache_name,
            result=result,
        ).inc()

    def update_cache_size(self, cache_name: str, size_bytes: int):
        """
        Update cache size metric.

        Args:
            cache_name: Name of cache
            size_bytes: Size in bytes
        """
        gateway_cache_size_bytes.labels(cache_name=cache_name).set(size_bytes)

    def record_cache_eviction(self, cache_name: str, reason: str):
        """
        Record cache eviction.

        Args:
            cache_name: Name of cache
            reason: Eviction reason (ttl, size, manual)
        """
        gateway_cache_evictions_total.labels(
            cache_name=cache_name,
            reason=reason,
        ).inc()

    def update_unique_users(self, count: int):
        """
        Update unique user count.

        Args:
            count: Number of unique users
        """
        gateway_unique_users.set(count)

    def update_active_sessions(self, count: int):
        """
        Update active session count.

        Args:
            count: Number of active sessions
        """
        gateway_user_sessions_active.set(count)


# Global instance
_collector = GatewayMetricsCollector()


# Convenience functions
def record_request(method: str, endpoint: str, user: Optional[str] = None):
    """Record a request."""
    return _collector.track_request(method, endpoint, user)


def record_tool_invocation(
    tool: str,
    server: str,
    user: str,
    duration: float,
    status: str = "success",
):
    """Record a tool invocation."""
    _collector.record_tool_invocation(tool, server, user, duration, status)


def record_error(error_type: str, component: str, severity: str = "error"):
    """Record an error."""
    _collector.record_error(error_type, component, severity)
