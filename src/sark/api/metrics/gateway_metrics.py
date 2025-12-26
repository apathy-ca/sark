"""Prometheus metrics for Gateway integration."""

from prometheus_client import Counter, Gauge, Histogram

# ============================================================================
# Authorization Metrics
# ============================================================================

# Authorization requests
gateway_authorization_requests_total = Counter(
    "sark_gateway_authz_requests_total",
    "Total Gateway authorization requests",
    ["decision", "action", "server"],
)

# Authorization latency
gateway_authorization_latency_seconds = Histogram(
    "sark_gateway_authz_latency_seconds",
    "Gateway authorization latency in seconds",
    ["action"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

# ============================================================================
# Cache Metrics
# ============================================================================

gateway_policy_cache_hits_total = Counter(
    "sark_gateway_cache_hits_total",
    "Gateway policy cache hits",
)

gateway_policy_cache_misses_total = Counter(
    "sark_gateway_cache_misses_total",
    "Gateway policy cache misses",
)

# ============================================================================
# A2A Metrics
# ============================================================================

a2a_authorization_requests_total = Counter(
    "sark_a2a_authz_requests_total",
    "A2A authorization requests",
    ["decision", "source_type", "target_type"],
)

# ============================================================================
# Error Metrics
# ============================================================================

gateway_client_errors_total = Counter(
    "sark_gateway_client_errors_total",
    "Gateway client errors",
    ["operation", "error_type"],
)

# ============================================================================
# Audit Metrics
# ============================================================================

gateway_audit_events_total = Counter(
    "sark_gateway_audit_events_total",
    "Gateway audit events logged",
    ["event_type", "decision"],
)

# ============================================================================
# Connection Metrics
# ============================================================================

gateway_active_connections = Gauge(
    "sark_gateway_active_connections",
    "Active Gateway connections",
)

# ============================================================================
# Helper Functions
# ============================================================================


def record_authorization(decision: str, action: str, server: str, latency: float):
    """
    Record authorization metrics.

    Args:
        decision: Authorization decision (allow/deny)
        action: Action being authorized
        server: Server name
        latency: Request latency in seconds
    """
    gateway_authorization_requests_total.labels(
        decision=decision,
        action=action,
        server=server,
    ).inc()

    gateway_authorization_latency_seconds.labels(
        action=action,
    ).observe(latency)


def record_cache_hit():
    """Record cache hit."""
    gateway_policy_cache_hits_total.inc()


def record_cache_miss():
    """Record cache miss."""
    gateway_policy_cache_misses_total.inc()


def record_client_error(operation: str, error_type: str):
    """
    Record Gateway client error.

    Args:
        operation: Operation that failed
        error_type: Error type/category
    """
    gateway_client_errors_total.labels(
        operation=operation,
        error_type=error_type,
    ).inc()


def record_audit_event(event_type: str, decision: str):
    """
    Record audit event.

    Args:
        event_type: Type of audit event
        decision: Authorization decision
    """
    gateway_audit_events_total.labels(
        event_type=event_type,
        decision=decision,
    ).inc()


def record_a2a_authorization(decision: str, source_type: str, target_type: str):
    """
    Record A2A authorization.

    Args:
        decision: Authorization decision
        source_type: Source agent type
        target_type: Target agent type
    """
    a2a_authorization_requests_total.labels(
        decision=decision,
        source_type=source_type,
        target_type=target_type,
    ).inc()


def increment_active_connections():
    """Increment active connections gauge."""
    gateway_active_connections.inc()


def decrement_active_connections():
    """Decrement active connections gauge."""
    gateway_active_connections.dec()
