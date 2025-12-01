"""Prometheus metrics collection for observability."""

from collections.abc import Callable
import time

from fastapi import Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware

# Create a custom registry for better control
registry = CollectorRegistry()

# HTTP request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=registry,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    registry=registry,
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently being processed",
    ["method", "endpoint"],
    registry=registry,
)

# Application metrics
app_info = Gauge(
    "app_info",
    "Application information",
    ["version", "environment"],
    registry=registry,
)

# Business metrics (examples - customize for your application)
business_operations_total = Counter(
    "business_operations_total",
    "Total business operations",
    ["operation", "status"],
    registry=registry,
)

business_operation_duration_seconds = Histogram(
    "business_operation_duration_seconds",
    "Business operation duration in seconds",
    ["operation"],
    registry=registry,
)

# Resource metrics
active_connections = Gauge(
    "active_connections",
    "Number of active connections",
    registry=registry,
)

# Error metrics
errors_total = Counter(
    "errors_total",
    "Total errors",
    ["error_type", "endpoint"],
    registry=registry,
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics for HTTP requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics."""
        method = request.method
        path = request.url.path

        # Skip metrics endpoint itself
        if path == "/metrics":
            return await call_next(request)

        # Track in-progress requests
        http_requests_in_progress.labels(method=method, endpoint=path).inc()

        # Track request duration
        start_time = time.time()
        try:
            response = await call_next(request)
            status = response.status_code

            # Record metrics
            http_requests_total.labels(method=method, endpoint=path, status=status).inc()

            duration = time.time() - start_time
            http_request_duration_seconds.labels(method=method, endpoint=path).observe(duration)

            # Track errors (4xx and 5xx)
            if status >= 400:
                error_type = "client_error" if status < 500 else "server_error"
                errors_total.labels(error_type=error_type, endpoint=path).inc()

            return response
        except Exception as exc:
            # Track exceptions
            errors_total.labels(error_type="exception", endpoint=path).inc()
            raise exc
        finally:
            # Always decrement in-progress counter
            http_requests_in_progress.labels(method=method, endpoint=path).dec()


def get_metrics() -> tuple[bytes, str]:
    """
    Generate Prometheus metrics in text format.

    Returns:
        tuple: (metrics_data, content_type)
    """
    return generate_latest(registry), CONTENT_TYPE_LATEST


def initialize_metrics(version: str = "2.0.0", environment: str = "development") -> None:
    """
    Initialize application metrics with static information.

    Args:
        version: Application version
        environment: Deployment environment (development, staging, production)
    """
    app_info.labels(version=version, environment=environment).set(1)
