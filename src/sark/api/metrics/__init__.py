"""Prometheus metrics for SARK."""

from sark.api.metrics.gateway_metrics import (
    record_authorization,
    record_cache_hit,
    record_cache_miss,
    record_client_error,
    record_audit_event,
    record_a2a_authorization,
    increment_active_connections,
    decrement_active_connections,
)

__all__ = [
    "record_authorization",
    "record_cache_hit",
    "record_cache_miss",
    "record_client_error",
    "record_audit_event",
    "record_a2a_authorization",
    "increment_active_connections",
    "decrement_active_connections",
]
