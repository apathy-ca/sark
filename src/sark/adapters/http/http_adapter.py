"""
HTTP/REST Protocol Adapter for SARK v2.0.

This adapter implements the ProtocolAdapter interface for HTTP/REST APIs.

Features:
- OpenAPI/Swagger discovery
- Multiple authentication strategies
- Rate limiting (token bucket algorithm)
- Circuit breaker pattern
- Retry logic with exponential backoff
- Request/response logging
- Streaming support (SSE)

Version: 2.0.0
Engineer: ENGINEER-2
"""

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
import time
from typing import Any
from urllib.parse import urljoin

import httpx
import structlog

from sark.adapters.base import ProtocolAdapter
from sark.adapters.exceptions import (
    ConnectionError as AdapterConnectionError,
)
from sark.adapters.exceptions import (
    DiscoveryError,
    InvocationError,
    StreamingError,
    ValidationError,
)
from sark.adapters.exceptions import (
    TimeoutError as AdapterTimeoutError,
)
from sark.adapters.http.authentication import AuthStrategy, create_auth_strategy
from sark.adapters.http.discovery import OpenAPIDiscovery
from sark.models.base import CapabilitySchema, InvocationRequest, InvocationResult, ResourceSchema

logger = structlog.get_logger(__name__)


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failures exceeded threshold, requests fail fast
    - HALF_OPEN: Testing if service recovered, limited requests allowed
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying again
            expected_exception: Exception type that counts as failure
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    async def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection.

        Args:
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise InvocationError(
                    "Circuit breaker is OPEN",
                    details={
                        "state": self.state,
                        "failure_count": self.failure_count,
                        "last_failure": self.last_failure_time,
                    },
                )

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return (time.time() - self.last_failure_time) >= self.recovery_timeout

    def _on_success(self):
        """Handle successful call."""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            logger.info("Circuit breaker CLOSED after successful recovery")
        self.failure_count = 0

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(
                "Circuit breaker OPEN",
                failure_count=self.failure_count,
                threshold=self.failure_threshold,
            )


class RateLimiter:
    """
    Token bucket rate limiter.

    Limits requests per second with burst capacity.
    """

    def __init__(self, rate: float, burst: int | None = None):
        """
        Initialize rate limiter.

        Args:
            rate: Requests per second
            burst: Burst capacity (defaults to rate)
        """
        self.rate = rate
        self.burst = burst or int(rate)
        self.tokens = float(self.burst)
        self.last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self):
        """
        Acquire token for request.

        Blocks until token is available.
        """
        async with self._lock:
            while True:
                now = time.time()
                elapsed = now - self.last_update
                self.last_update = now

                # Add tokens based on elapsed time
                self.tokens = min(self.burst, self.tokens + elapsed * self.rate)

                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return

                # Wait for next token
                wait_time = (1.0 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)


class HTTPAdapter(ProtocolAdapter):
    """
    HTTP/REST Protocol Adapter.

    Translates REST API operations into GRID's universal abstractions.
    """

    def __init__(
        self,
        base_url: str,
        auth_config: dict[str, Any] | None = None,
        rate_limit: float | None = None,
        circuit_breaker_threshold: int = 5,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """
        Initialize HTTP adapter.

        Args:
            base_url: Base URL of the API
            auth_config: Authentication configuration
            rate_limit: Requests per second limit (None = no limit)
            circuit_breaker_threshold: Failures before opening circuit
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

        # Initialize authentication
        self.auth_strategy: AuthStrategy = (
            create_auth_strategy(auth_config)
            if auth_config
            else create_auth_strategy({"type": "none"})
        )

        # Initialize rate limiter
        self.rate_limiter: RateLimiter | None = RateLimiter(rate=rate_limit) if rate_limit else None

        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_breaker_threshold,
            recovery_timeout=60.0,
            expected_exception=Exception,
        )

        # HTTP client (created lazily)
        self._client: httpx.AsyncClient | None = None

        # Discovery helper
        self._discovery: OpenAPIDiscovery | None = None

    @property
    def protocol_name(self) -> str:
        """Return protocol identifier."""
        return "http"

    @property
    def protocol_version(self) -> str:
        """Return protocol version."""
        return "1.1"

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
            )
        return self._client

    async def discover_resources(self, discovery_config: dict[str, Any]) -> list[ResourceSchema]:
        """
        Discover HTTP API as a resource.

        Args:
            discovery_config: Configuration with base_url and optional spec_url

        Returns:
            List with single ResourceSchema for this API

        Example:
            discovery_config = {
                "base_url": "https://api.example.com",
                "openapi_spec_url": "https://api.example.com/openapi.json",
                "auth": {"type": "bearer", "token": "..."}
            }
        """
        base_url = discovery_config.get("base_url", self.base_url)
        spec_url = discovery_config.get("openapi_spec_url")

        # Initialize discovery
        discovery = OpenAPIDiscovery(base_url=base_url, spec_url=spec_url)

        try:
            # Fetch OpenAPI spec
            spec = await discovery.discover_spec()
            server_info = await discovery.get_server_info(spec)

            # Create resource
            resource_id = (
                f"http:{base_url.replace('https://', '').replace('http://', '').replace('/', '_')}"
            )

            resource = ResourceSchema(
                id=resource_id,
                name=server_info["title"],
                protocol="http",
                endpoint=base_url,
                sensitivity_level="medium",
                metadata={
                    "api_version": server_info["version"],
                    "description": server_info["description"],
                    "openapi_version": server_info["openapi_version"],
                    "openapi_spec_url": discovery.spec_url,
                    "servers": server_info["servers"],
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            logger.info(
                "Discovered HTTP API resource",
                resource_id=resource.id,
                api_title=server_info["title"],
                api_version=server_info["version"],
            )

            return [resource]

        except Exception as e:
            raise DiscoveryError(
                f"Failed to discover HTTP API: {e!s}",
                details={"base_url": base_url, "spec_url": spec_url},
            )

    async def get_capabilities(self, resource: ResourceSchema) -> list[CapabilitySchema]:
        """
        Get capabilities from OpenAPI spec.

        Args:
            resource: The HTTP API resource

        Returns:
            List of capabilities (one per API operation)
        """
        spec_url = resource.metadata.get("openapi_spec_url")

        if not spec_url and not resource.endpoint:
            raise DiscoveryError(
                "No OpenAPI spec URL or endpoint found in resource metadata",
                resource_id=resource.id,
            )

        # Initialize discovery
        discovery = OpenAPIDiscovery(base_url=resource.endpoint, spec_url=spec_url)

        try:
            capabilities = await discovery.discover_capabilities(resource)
            logger.info(
                "Discovered capabilities for HTTP resource",
                resource_id=resource.id,
                count=len(capabilities),
            )
            return capabilities

        except Exception as e:
            raise DiscoveryError(f"Failed to discover capabilities: {e!s}", resource_id=resource.id)

    async def validate_request(self, request: InvocationRequest) -> bool:
        """
        Validate invocation request.

        Args:
            request: The invocation request

        Returns:
            True if valid

        Raises:
            ValidationError: If request is invalid
        """
        # Check required fields
        if not request.capability_id:
            raise ValidationError(
                "capability_id is required", validation_errors=["Missing capability_id"]
            )

        if not request.principal_id:
            raise ValidationError(
                "principal_id is required", validation_errors=["Missing principal_id"]
            )

        # Arguments must be a dict
        if not isinstance(request.arguments, dict):
            raise ValidationError(
                "arguments must be a dictionary",
                validation_errors=[f"Invalid arguments type: {type(request.arguments)}"],
            )

        return True

    async def invoke(self, request: InvocationRequest) -> InvocationResult:
        """
        Invoke HTTP API capability.

        Args:
            request: The invocation request

        Returns:
            Invocation result
        """
        start_time = time.time()

        try:
            # Validate request
            await self.validate_request(request)

            # Apply rate limiting
            if self.rate_limiter:
                await self.rate_limiter.acquire()

            # Execute with circuit breaker
            result = await self.circuit_breaker.call(self._execute_http_request, request)

            duration_ms = (time.time() - start_time) * 1000

            return InvocationResult(
                success=True,
                result=result,
                metadata={
                    "capability_id": request.capability_id,
                    "protocol": "http",
                },
                duration_ms=duration_ms,
            )

        except ValidationError as e:
            duration_ms = (time.time() - start_time) * 1000
            return InvocationResult(
                success=False,
                error=str(e),
                metadata={"error_type": "ValidationError"},
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "HTTP invocation failed",
                capability_id=request.capability_id,
                error=str(e),
                duration_ms=duration_ms,
            )
            return InvocationResult(
                success=False,
                error=str(e),
                metadata={"error_type": type(e).__name__},
                duration_ms=duration_ms,
            )

    async def _execute_http_request(self, request: InvocationRequest) -> Any:
        """
        Execute the actual HTTP request with retry logic.

        Args:
            request: Invocation request

        Returns:
            Response data

        Raises:
            InvocationError: If request fails
        """
        # Parse capability metadata
        capability_metadata = request.context.get("capability_metadata", {})
        http_method = capability_metadata.get("http_method", "GET")
        http_path = capability_metadata.get("http_path", "/")

        # Build request
        url = urljoin(self.base_url, http_path)
        arguments = request.arguments

        # Extract components from arguments
        path_params = {
            k: v for k, v in arguments.items() if not k.startswith(("query_", "header_", "body"))
        }
        query_params = {
            k.replace("query_", ""): v for k, v in arguments.items() if k.startswith("query_")
        }
        headers = {
            k.replace("header_", ""): v for k, v in arguments.items() if k.startswith("header_")
        }
        body = arguments.get("body")

        # Replace path parameters
        for param_name, param_value in path_params.items():
            url = url.replace(f"{{{param_name}}}", str(param_value))

        # Prepare request
        client = self._get_client()
        http_request = client.build_request(
            method=http_method,
            url=url,
            params=query_params,
            headers=headers,
            json=body if body else None,
        )

        # Apply authentication
        self.auth_strategy.apply(http_request)

        # Retry logic
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    "Sending HTTP request", method=http_method, url=url, attempt=attempt + 1
                )

                response = await client.send(http_request)
                response.raise_for_status()

                # Parse response
                try:
                    result = response.json()
                except Exception:
                    result = response.text

                return result

            except httpx.TimeoutException:
                last_exception = AdapterTimeoutError(
                    f"HTTP request timed out after {self.timeout}s",
                    timeout_seconds=self.timeout,
                    details={"url": url, "method": http_method},
                )
                logger.warning("HTTP request timeout", attempt=attempt + 1, url=url)

            except httpx.HTTPStatusError as e:
                # Don't retry client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    raise InvocationError(
                        f"HTTP {e.response.status_code}: {e.response.text}",
                        protocol_error=f"{e.response.status_code}",
                        details={
                            "url": url,
                            "method": http_method,
                            "status_code": e.response.status_code,
                        },
                    )

                # Retry server errors (5xx)
                last_exception = InvocationError(
                    f"HTTP {e.response.status_code}: {e.response.text}",
                    protocol_error=f"{e.response.status_code}",
                    details={
                        "url": url,
                        "method": http_method,
                        "status_code": e.response.status_code,
                    },
                )
                logger.warning(
                    "HTTP server error", attempt=attempt + 1, status=e.response.status_code
                )

            except httpx.RequestError as e:
                last_exception = AdapterConnectionError(
                    f"HTTP request failed: {e!s}", details={"url": url, "method": http_method}
                )
                logger.warning("HTTP request error", attempt=attempt + 1, error=str(e))

            # Exponential backoff
            if attempt < self.max_retries - 1:
                wait_time = 2**attempt
                await asyncio.sleep(wait_time)

        # All retries failed
        raise last_exception or InvocationError("HTTP request failed after all retries")

    async def health_check(self, resource: ResourceSchema) -> bool:
        """
        Check if HTTP API is healthy.

        Args:
            resource: The resource to check

        Returns:
            True if healthy
        """
        try:
            client = self._get_client()
            response = await client.get(resource.endpoint, timeout=5.0)
            return response.status_code < 500
        except Exception as e:
            logger.warning("HTTP health check failed", endpoint=resource.endpoint, error=str(e))
            return False

    async def on_resource_registered(self, resource: ResourceSchema) -> None:
        """Initialize resources when registered."""
        # Initialize discovery helper
        spec_url = resource.metadata.get("openapi_spec_url")
        self._discovery = OpenAPIDiscovery(base_url=resource.endpoint, spec_url=spec_url)

        # Refresh auth tokens if needed
        try:
            await self.auth_strategy.refresh()
        except Exception as e:
            logger.warning("Failed to refresh auth during registration", error=str(e))

    async def on_resource_unregistered(self, resource: ResourceSchema) -> None:
        """Cleanup when resource is unregistered."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def invoke_streaming(self, request: InvocationRequest) -> AsyncIterator[Any]:
        """
        Invoke with Server-Sent Events (SSE) streaming support.

        Args:
            request: Invocation request

        Yields:
            Response chunks

        Raises:
            StreamingError: If streaming fails
        """
        # Validate request
        await self.validate_request(request)

        # Apply rate limiting
        if self.rate_limiter:
            await self.rate_limiter.acquire()

        try:
            # Parse capability metadata
            capability_metadata = request.context.get("capability_metadata", {})
            http_method = capability_metadata.get("http_method", "GET")
            http_path = capability_metadata.get("http_path", "/")

            url = urljoin(self.base_url, http_path)

            # Build request
            client = self._get_client()
            http_request = client.build_request(method=http_method, url=url)
            self.auth_strategy.apply(http_request)

            # Stream response
            chunks_received = 0
            async with client.stream(http_method, url) as response:
                response.raise_for_status()

                async for chunk in response.aiter_bytes():
                    chunks_received += 1
                    yield chunk

        except Exception as e:
            raise StreamingError(
                f"Streaming failed: {e!s}",
                chunks_received=chunks_received,
                details={"url": url, "method": http_method},
            )

    def __repr__(self) -> str:
        """String representation."""
        return f"<HTTPAdapter base_url={self.base_url}>"


__all__ = ["CircuitBreaker", "HTTPAdapter", "RateLimiter"]
