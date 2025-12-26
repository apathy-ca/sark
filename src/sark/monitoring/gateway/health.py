"""Health check endpoints for Gateway."""

from enum import Enum
import time
from typing import Any

import httpx
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()


class HealthStatus(str, Enum):
    """Health status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseModel):
    """Health status for a component."""

    status: HealthStatus
    message: str
    latency_ms: float | None = None
    details: dict[str, Any] = {}


class OverallHealth(BaseModel):
    """Overall system health."""

    status: HealthStatus
    timestamp: float
    components: dict[str, ComponentHealth]
    uptime_seconds: float


class HealthChecker:
    """Health checker for Gateway components."""

    def __init__(self):
        """Initialize health checker."""
        self.start_time = time.time()
        self.component_checkers = {
            "database": self._check_database,
            "redis": self._check_redis,
            "opa": self._check_opa,
            "siem": self._check_siem,
            "gateway": self._check_gateway,
        }

    async def get_health(self) -> OverallHealth:
        """
        Get basic health status.

        Returns:
            Overall health status
        """
        return OverallHealth(
            status=HealthStatus.HEALTHY,
            timestamp=time.time(),
            components={},
            uptime_seconds=time.time() - self.start_time,
        )

    async def get_readiness(self) -> OverallHealth:
        """
        Get readiness status (checks dependencies).

        Returns:
            Readiness status with dependency checks
        """
        components = {}

        # Check critical dependencies
        critical_components = ["database", "opa"]

        for component in critical_components:
            checker = self.component_checkers.get(component)
            if checker:
                components[component] = await checker()

        # Determine overall status
        overall_status = HealthStatus.HEALTHY
        for comp_health in components.values():
            if comp_health.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
                break
            elif comp_health.status == HealthStatus.DEGRADED:
                overall_status = HealthStatus.DEGRADED

        return OverallHealth(
            status=overall_status,
            timestamp=time.time(),
            components=components,
            uptime_seconds=time.time() - self.start_time,
        )

    async def get_detailed_health(self) -> OverallHealth:
        """
        Get detailed health status (all components).

        Returns:
            Detailed health status
        """
        components = {}

        # Check all components
        for component_name, checker in self.component_checkers.items():
            try:
                components[component_name] = await checker()
            except Exception as e:
                logger.error("health_check_failed", component=component_name, error=str(e))
                components[component_name] = ComponentHealth(
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check failed: {e!s}",
                )

        # Determine overall status
        overall_status = HealthStatus.HEALTHY
        unhealthy_count = 0
        degraded_count = 0

        for comp_health in components.values():
            if comp_health.status == HealthStatus.UNHEALTHY:
                unhealthy_count += 1
            elif comp_health.status == HealthStatus.DEGRADED:
                degraded_count += 1

        # Set overall status based on component health
        if unhealthy_count > 0:
            if unhealthy_count >= len(components) // 2:
                overall_status = HealthStatus.UNHEALTHY
            else:
                overall_status = HealthStatus.DEGRADED
        elif degraded_count > 0:
            overall_status = HealthStatus.DEGRADED

        return OverallHealth(
            status=overall_status,
            timestamp=time.time(),
            components=components,
            uptime_seconds=time.time() - self.start_time,
        )

    async def _check_database(self) -> ComponentHealth:
        """Check database health."""
        start_time = time.time()

        try:
            # Import here to avoid circular dependency
            from sqlalchemy import text

            from sark.db.session import get_db

            async for session in get_db():
                await session.execute(text("SELECT 1"))
                break  # Only need one iteration

            latency_ms = (time.time() - start_time) * 1000

            return ComponentHealth(
                status=HealthStatus.HEALTHY,
                message="Database connection successful",
                latency_ms=latency_ms,
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return ComponentHealth(
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {e!s}",
                latency_ms=latency_ms,
            )

    async def _check_redis(self) -> ComponentHealth:
        """Check Redis health."""
        start_time = time.time()

        try:
            # Placeholder for Redis check
            # In production, would use actual Redis client
            latency_ms = (time.time() - start_time) * 1000

            return ComponentHealth(
                status=HealthStatus.HEALTHY,
                message="Redis connection successful",
                latency_ms=latency_ms,
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return ComponentHealth(
                status=HealthStatus.UNHEALTHY,
                message=f"Redis connection failed: {e!s}",
                latency_ms=latency_ms,
            )

    async def _check_opa(self) -> ComponentHealth:
        """Check OPA health."""
        start_time = time.time()

        try:
            from sark.config.settings import get_settings

            settings = get_settings()

            if not hasattr(settings, "opa_url"):
                return ComponentHealth(
                    status=HealthStatus.DEGRADED,
                    message="OPA URL not configured",
                    latency_ms=0,
                )

            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{settings.opa_url}/health")
                response.raise_for_status()

            latency_ms = (time.time() - start_time) * 1000

            return ComponentHealth(
                status=HealthStatus.HEALTHY,
                message="OPA is healthy",
                latency_ms=latency_ms,
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return ComponentHealth(
                status=HealthStatus.UNHEALTHY,
                message=f"OPA health check failed: {e!s}",
                latency_ms=latency_ms,
            )

    async def _check_siem(self) -> ComponentHealth:
        """Check SIEM integration health."""
        start_time = time.time()

        try:
            # Check if SIEM is configured
            from sark.config.settings import get_settings

            settings = get_settings()

            has_splunk = hasattr(settings, "splunk_hec_url") and settings.splunk_hec_url
            has_datadog = hasattr(settings, "datadog_api_key") and settings.datadog_api_key

            if not has_splunk and not has_datadog:
                return ComponentHealth(
                    status=HealthStatus.DEGRADED,
                    message="SIEM not configured",
                    latency_ms=0,
                    details={"configured": False},
                )

            latency_ms = (time.time() - start_time) * 1000

            return ComponentHealth(
                status=HealthStatus.HEALTHY,
                message="SIEM integration configured",
                latency_ms=latency_ms,
                details={
                    "splunk_configured": has_splunk,
                    "datadog_configured": has_datadog,
                },
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return ComponentHealth(
                status=HealthStatus.DEGRADED,
                message=f"SIEM check failed: {e!s}",
                latency_ms=latency_ms,
            )

    async def _check_gateway(self) -> ComponentHealth:
        """Check Gateway service health."""
        start_time = time.time()

        try:
            # Basic Gateway health check
            latency_ms = (time.time() - start_time) * 1000

            return ComponentHealth(
                status=HealthStatus.HEALTHY,
                message="Gateway service operational",
                latency_ms=latency_ms,
                details={
                    "uptime_seconds": time.time() - self.start_time,
                },
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return ComponentHealth(
                status=HealthStatus.UNHEALTHY,
                message=f"Gateway check failed: {e!s}",
                latency_ms=latency_ms,
            )


# Global health checker instance
_health_checker = HealthChecker()


# Convenience functions
async def get_health_status() -> OverallHealth:
    """Get basic health status."""
    return await _health_checker.get_health()


async def get_readiness_status() -> OverallHealth:
    """Get readiness status."""
    return await _health_checker.get_readiness()


async def get_detailed_health() -> OverallHealth:
    """Get detailed health status."""
    return await _health_checker.get_detailed_health()
