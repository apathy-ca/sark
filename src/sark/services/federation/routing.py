"""
Federated routing service for SARK v2.0.

This module implements resource routing and invocation across federation nodes:
- Federated resource lookup and resolution
- Cross-organization capability invocation
- Load balancing across multiple nodes
- Circuit breaking and failover
- Request routing optimization
- Audit correlation for cross-node operations

The routing service enables SARK to invoke capabilities on resources
hosted by other SARK instances in the federation.
"""

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Any
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from sark.models.base import FederationNode, Resource
from sark.models.federation import (
    AuditCorrelationQuery,
    AuditCorrelationResponse,
    FederatedAuditEvent,
    FederatedResourceRequest,
    FederatedResourceResponse,
    NodeHealthCheck,
    NodeStatus,
    RouteEntry,
    RouteQuery,
    RouteResponse,
    RoutingTable,
)

logger = structlog.get_logger(__name__)


class CircuitBreaker:
    """
    Circuit breaker for federation node connections.

    Prevents cascading failures by temporarily disabling connections
    to unhealthy nodes.
    """

    def __init__(
        self, failure_threshold: int = 5, timeout_seconds: int = 60, half_open_requests: int = 1
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: How long to wait before trying again
            half_open_requests: Number of test requests in half-open state
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.half_open_requests = half_open_requests

        # Circuit state per node
        self._states: dict[str, str] = defaultdict(lambda: "closed")
        self._failure_counts: dict[str, int] = defaultdict(int)
        self._last_failure_time: dict[str, datetime] = {}
        self._half_open_attempts: dict[str, int] = defaultdict(int)

        self.logger = logger.bind(component="circuit-breaker")

    def is_available(self, node_id: str) -> bool:
        """
        Check if node is available for requests.

        Args:
            node_id: Node to check

        Returns:
            True if node is available, False if circuit is open
        """
        state = self._states[node_id]

        if state == "closed":
            return True

        if state == "open":
            # Check if timeout has elapsed
            if node_id in self._last_failure_time:
                elapsed = (datetime.utcnow() - self._last_failure_time[node_id]).total_seconds()
                if elapsed >= self.timeout_seconds:
                    # Transition to half-open
                    self._states[node_id] = "half-open"
                    self._half_open_attempts[node_id] = 0
                    self.logger.info("circuit_half_open", node_id=node_id)
                    return True
            return False

        if state == "half-open":
            # Allow limited requests
            if self._half_open_attempts[node_id] < self.half_open_requests:
                self._half_open_attempts[node_id] += 1
                return True
            return False

        return True

    def record_success(self, node_id: str):
        """
        Record successful request.

        Args:
            node_id: Node that succeeded
        """
        state = self._states[node_id]

        if state == "half-open":
            # Success in half-open state closes the circuit
            self._states[node_id] = "closed"
            self._failure_counts[node_id] = 0
            self._half_open_attempts[node_id] = 0
            self.logger.info("circuit_closed", node_id=node_id)
        elif state == "closed":
            # Reset failure count on success
            self._failure_counts[node_id] = 0

    def record_failure(self, node_id: str):
        """
        Record failed request.

        Args:
            node_id: Node that failed
        """
        state = self._states[node_id]
        self._failure_counts[node_id] += 1
        self._last_failure_time[node_id] = datetime.utcnow()

        if state == "half-open":
            # Failure in half-open reopens the circuit
            self._states[node_id] = "open"
            self.logger.warning("circuit_reopened", node_id=node_id)
        elif state == "closed":
            # Check if we should open the circuit
            if self._failure_counts[node_id] >= self.failure_threshold:
                self._states[node_id] = "open"
                self.logger.warning(
                    "circuit_opened", node_id=node_id, failures=self._failure_counts[node_id]
                )

    def get_state(self, node_id: str) -> str:
        """
        Get circuit breaker state for node.

        Args:
            node_id: Node to check

        Returns:
            Circuit state: "closed", "open", or "half-open"
        """
        return self._states[node_id]


class RoutingService:
    """
    Federated resource routing and invocation service.

    Handles routing requests to resources on other federation nodes,
    with load balancing, failover, and circuit breaking.
    """

    def __init__(
        self, local_node_id: str, ssl_context: Any | None = None, timeout_seconds: int = 30
    ):
        """
        Initialize routing service.

        Args:
            local_node_id: This node's unique identifier
            ssl_context: SSL context for mTLS connections
            timeout_seconds: Default request timeout
        """
        self.local_node_id = local_node_id
        self.ssl_context = ssl_context
        self.timeout_seconds = timeout_seconds

        self.logger = logger.bind(component="routing-service")

        # HTTP client for federation requests
        self.client = httpx.AsyncClient(
            timeout=timeout_seconds, verify=ssl_context if ssl_context else True
        )

        # Circuit breaker for node health management
        self.circuit_breaker = CircuitBreaker()

        # Routing table cache
        self._routing_table: dict[str, list[RouteEntry]] = {}
        self._routing_table_updated: datetime = datetime.utcnow()

        # Audit event buffer for correlation
        self._audit_events: list[FederatedAuditEvent] = []

    async def close(self):
        """Close HTTP client and cleanup resources."""
        await self.client.aclose()

    async def find_route(self, query: RouteQuery, db: AsyncSession) -> RouteResponse:
        """
        Find routes to a resource.

        Args:
            query: Route query
            db: Database session

        Returns:
            Route response with available routes
        """
        self.logger.info(
            "finding_route", resource_id=query.resource_id, preferred_node=query.preferred_node
        )

        # Check local routing table cache
        available_routes = []

        if query.resource_id in self._routing_table:
            cached_routes = self._routing_table[query.resource_id]

            # Filter based on query parameters
            for route in cached_routes:
                # Skip unhealthy routes unless explicitly requested
                if not query.include_unhealthy:
                    if route.health_status != NodeStatus.ONLINE:
                        continue

                # Check circuit breaker
                if not self.circuit_breaker.is_available(route.node_id):
                    continue

                available_routes.append(route)

        # If no cached routes, query federation nodes
        if not available_routes:
            available_routes = await self._discover_routes(query.resource_id, db)

        # Select recommended route
        recommended_route = None
        if available_routes:
            if query.preferred_node:
                # Try to find preferred node
                for route in available_routes:
                    if route.node_id == query.preferred_node:
                        recommended_route = route
                        break

            if not recommended_route:
                # Select route with lowest latency
                recommended_route = min(
                    available_routes, key=lambda r: r.latency_ms if r.latency_ms else float("inf")
                )

        self.logger.info(
            "route_found",
            resource_id=query.resource_id,
            available_routes=len(available_routes),
            recommended_node=recommended_route.node_id if recommended_route else None,
        )

        return RouteResponse(
            resource_id=query.resource_id,
            available_routes=available_routes,
            recommended_route=recommended_route,
        )

    async def invoke_federated(
        self, request: FederatedResourceRequest, db: AsyncSession
    ) -> FederatedResourceResponse:
        """
        Invoke a capability on a federated resource.

        Args:
            request: Federated invocation request
            db: Database session

        Returns:
            Federated invocation response
        """
        correlation_id = str(uuid.uuid4())

        self.logger.info(
            "invoking_federated_resource",
            target_node=request.target_node_id,
            resource_id=request.resource_id,
            capability_id=request.capability_id,
            correlation_id=correlation_id,
        )

        start_time = asyncio.get_event_loop().time()

        try:
            # Get target node details
            result = await db.execute(
                select(FederationNode).where(FederationNode.node_id == request.target_node_id)
            )
            node = result.scalar_one_or_none()

            if not node:
                raise ValueError(f"Federation node not found: {request.target_node_id}")

            if not node.enabled:
                raise ValueError(f"Federation node is disabled: {request.target_node_id}")

            # Check circuit breaker
            if not self.circuit_breaker.is_available(request.target_node_id):
                raise ValueError(
                    f"Federation node is unavailable (circuit open): {request.target_node_id}"
                )

            # Build federated invocation request
            invocation_url = f"{node.endpoint}/api/v2/federation/invoke"

            payload = {
                "resource_id": request.resource_id,
                "capability_id": request.capability_id,
                "principal_id": request.principal_id,
                "arguments": request.arguments,
                "context": {
                    **request.context,
                    "source_node_id": self.local_node_id,
                    "correlation_id": correlation_id,
                },
            }

            # Make federated request
            response = await self.client.post(
                invocation_url, json=payload, timeout=self.timeout_seconds
            )

            response.raise_for_status()
            result_data = response.json()

            # Record success
            self.circuit_breaker.record_success(request.target_node_id)

            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            # Create audit event
            audit_event = FederatedAuditEvent(
                correlation_id=correlation_id,
                source_node_id=self.local_node_id,
                target_node_id=request.target_node_id,
                principal_id=request.principal_id,
                resource_id=request.resource_id,
                capability_id=request.capability_id,
                action="invoke",
                success=True,
                duration_ms=duration_ms,
                metadata=request.context,
            )
            self._audit_events.append(audit_event)

            self.logger.info(
                "federated_invocation_success",
                target_node=request.target_node_id,
                resource_id=request.resource_id,
                correlation_id=correlation_id,
                duration_ms=duration_ms,
            )

            return FederatedResourceResponse(
                success=True,
                node_id=request.target_node_id,
                resource_id=request.resource_id,
                result=result_data.get("result"),
                metadata=result_data.get("metadata", {}),
                duration_ms=duration_ms,
                audit_correlation_id=correlation_id,
            )

        except Exception as e:
            # Record failure
            self.circuit_breaker.record_failure(request.target_node_id)

            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            # Create audit event for failure
            audit_event = FederatedAuditEvent(
                correlation_id=correlation_id,
                source_node_id=self.local_node_id,
                target_node_id=request.target_node_id,
                principal_id=request.principal_id,
                resource_id=request.resource_id,
                capability_id=request.capability_id,
                action="invoke",
                success=False,
                duration_ms=duration_ms,
                metadata={"error": str(e)},
            )
            self._audit_events.append(audit_event)

            self.logger.error(
                "federated_invocation_failed",
                target_node=request.target_node_id,
                resource_id=request.resource_id,
                correlation_id=correlation_id,
                error=str(e),
            )

            return FederatedResourceResponse(
                success=False,
                node_id=request.target_node_id,
                resource_id=request.resource_id,
                error=str(e),
                duration_ms=duration_ms,
                audit_correlation_id=correlation_id,
            )

    async def check_node_health(self, node: FederationNode) -> NodeHealthCheck:
        """
        Check health of a federation node.

        Args:
            node: Federation node to check

        Returns:
            Node health check result
        """
        self.logger.debug("checking_node_health", node_id=node.node_id)

        start_time = asyncio.get_event_loop().time()

        try:
            health_url = f"{node.endpoint}/api/v2/health"

            response = await self.client.get(
                health_url, timeout=5.0  # Short timeout for health checks
            )

            response_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                status = (
                    NodeStatus.ONLINE if data.get("status") == "healthy" else NodeStatus.DEGRADED
                )

                return NodeHealthCheck(
                    node_id=node.node_id,
                    status=status,
                    last_check=datetime.utcnow(),
                    response_time_ms=response_time_ms,
                    metadata=data,
                )
            else:
                return NodeHealthCheck(
                    node_id=node.node_id,
                    status=NodeStatus.DEGRADED,
                    last_check=datetime.utcnow(),
                    response_time_ms=response_time_ms,
                    error=f"HTTP {response.status_code}",
                )

        except Exception as e:
            response_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            self.logger.warning("node_health_check_failed", node_id=node.node_id, error=str(e))

            return NodeHealthCheck(
                node_id=node.node_id,
                status=NodeStatus.OFFLINE,
                last_check=datetime.utcnow(),
                response_time_ms=response_time_ms,
                error=str(e),
            )

    async def correlate_audit_events(
        self, query: AuditCorrelationQuery, db: AsyncSession
    ) -> AuditCorrelationResponse:
        """
        Correlate audit events across federation nodes.

        Args:
            query: Audit correlation query
            db: Database session

        Returns:
            Correlated audit events
        """
        self.logger.info(
            "correlating_audit_events",
            correlation_id=query.correlation_id,
            principal_id=query.principal_id,
        )

        start_time = asyncio.get_event_loop().time()

        # Filter local events
        local_events = []
        for event in self._audit_events:
            if query.correlation_id and event.correlation_id != query.correlation_id:
                continue
            if query.principal_id and event.principal_id != query.principal_id:
                continue
            if query.resource_id and event.resource_id != query.resource_id:
                continue
            if query.start_time and event.timestamp < query.start_time:
                continue
            if query.end_time and event.timestamp > query.end_time:
                continue

            local_events.append(event)

        # If specific nodes requested, query them
        if query.node_ids:
            # In production, query other nodes for their audit events
            # For now, just return local events
            pass

        query_duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000

        self.logger.info(
            "audit_correlation_complete",
            events_found=len(local_events),
            duration_ms=query_duration_ms,
        )

        return AuditCorrelationResponse(
            events=local_events,
            total_events=len(local_events),
            nodes_queried=[self.local_node_id],
            query_duration_ms=query_duration_ms,
        )

    async def _discover_routes(self, resource_id: str, db: AsyncSession) -> list[RouteEntry]:
        """
        Discover routes to a resource across federation.

        Args:
            resource_id: Resource to find
            db: Database session

        Returns:
            List of available routes
        """
        self.logger.debug("discovering_routes", resource_id=resource_id)

        routes = []

        # Check if resource exists locally
        local_result = await db.execute(select(Resource).where(Resource.id == resource_id))
        local_resource = local_result.scalar_one_or_none()

        if local_resource:
            # Resource is local
            route = RouteEntry(
                resource_id=resource_id,
                node_id=self.local_node_id,
                endpoint="http://localhost:8000",  # Local endpoint
                last_verified=datetime.utcnow(),
                health_status=NodeStatus.ONLINE,
                latency_ms=0.1,  # Essentially zero latency for local
                metadata={"local": True},
            )
            routes.append(route)

        # Query federation nodes
        federation_result = await db.execute(
            select(FederationNode).where(FederationNode.enabled == True)
        )
        nodes = federation_result.scalars().all()

        # Query each node for the resource
        for node in nodes:
            if not self.circuit_breaker.is_available(node.node_id):
                continue

            try:
                # Query node for resource
                resource_url = f"{node.endpoint}/api/v2/resources/{resource_id}"
                response = await self.client.get(resource_url, timeout=5.0)

                if response.status_code == 200:
                    # Resource found on this node
                    route = RouteEntry(
                        resource_id=resource_id,
                        node_id=node.node_id,
                        endpoint=node.endpoint,
                        last_verified=datetime.utcnow(),
                        health_status=NodeStatus.ONLINE,
                        latency_ms=response.elapsed.total_seconds() * 1000,
                        metadata={"remote": True},
                    )
                    routes.append(route)

            except Exception as e:
                self.logger.warning(
                    "route_discovery_failed",
                    node_id=node.node_id,
                    resource_id=resource_id,
                    error=str(e),
                )

        # Update routing table cache
        self._routing_table[resource_id] = routes
        self._routing_table_updated = datetime.utcnow()

        return routes

    async def get_routing_table(self) -> RoutingTable:
        """
        Get current routing table.

        Returns:
            Routing table with all cached routes
        """
        all_entries = []
        for routes in self._routing_table.values():
            all_entries.extend(routes)

        return RoutingTable(entries=all_entries, last_updated=self._routing_table_updated)

    def clear_routing_cache(self):
        """Clear routing table cache."""
        self._routing_table.clear()
        self._routing_table_updated = datetime.utcnow()
        self.logger.info("routing_cache_cleared")


__all__ = ["CircuitBreaker", "RoutingService"]
