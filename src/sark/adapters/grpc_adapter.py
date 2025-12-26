"""
gRPC Protocol Adapter for SARK v2.0.

This adapter enables SARK to govern gRPC services by translating gRPC concepts
into GRID's universal abstractions (Resource, Capability, Action).

Features:
- Service discovery via gRPC reflection
- Support for all RPC types (unary, server streaming, client streaming, bidirectional)
- mTLS and token-based authentication
- Connection pooling and load balancing
- Health checking

Version: 2.0.0
Engineer: ENGINEER-3 (gRPC Adapter Lead)
"""

import asyncio
import builtins
from collections.abc import AsyncIterator
import time
from typing import Any

import grpc
from grpc import aio
import structlog

from sark.adapters.base import ProtocolAdapter
from sark.adapters.exceptions import (
    AuthenticationError,
    ConnectionError,
    DiscoveryError,
    InvocationError,
    StreamingError,
    TimeoutError,
    UnsupportedOperationError,
    ValidationError,
)
from sark.models.base import (
    CapabilitySchema,
    InvocationRequest,
    InvocationResult,
    ResourceSchema,
)

logger = structlog.get_logger(__name__)


class GRPCAdapter(ProtocolAdapter):
    """
    gRPC Protocol Adapter.

    Provides governance for gRPC services by discovering services via reflection,
    translating gRPC methods into capabilities, and executing RPCs with full
    policy enforcement.

    Configuration:
        discovery_config = {
            "host": "grpc.example.com",
            "port": 50051,
            "use_tls": true,
            "auth": {
                "type": "mtls",  # or "token", "none"
                "cert_path": "/path/to/cert.pem",
                "key_path": "/path/to/key.pem",
                "ca_path": "/path/to/ca.pem"
            },
            "timeout_seconds": 30,
            "max_connections": 10
        }
    """

    def __init__(
        self,
        default_timeout: float = 30.0,
        max_message_length: int = 100 * 1024 * 1024,  # 100MB
    ):
        """
        Initialize gRPC adapter.

        Args:
            default_timeout: Default timeout for gRPC calls in seconds
            max_message_length: Maximum message size in bytes
        """
        self._default_timeout = default_timeout
        self._max_message_length = max_message_length
        self._channels: dict[str, aio.Channel] = {}
        self._stubs: dict[str, Any] = {}
        logger.info(
            "grpc_adapter_initialized",
            timeout=default_timeout,
            max_message_length=max_message_length,
        )

    @property
    def protocol_name(self) -> str:
        """Return protocol identifier."""
        return "grpc"

    @property
    def protocol_version(self) -> str:
        """Return gRPC version supported."""
        return "1.60.0"

    async def discover_resources(self, discovery_config: dict[str, Any]) -> list[ResourceSchema]:
        """
        Discover gRPC services using reflection.

        Args:
            discovery_config: Configuration for service discovery
                - host: gRPC server host
                - port: gRPC server port
                - use_tls: Whether to use TLS
                - auth: Authentication configuration
                - timeout_seconds: Discovery timeout

        Returns:
            List of discovered resources (gRPC services)

        Raises:
            DiscoveryError: If service discovery fails
            ConnectionError: If cannot connect to server
            AuthenticationError: If authentication fails
        """
        host = discovery_config.get("host")
        port = discovery_config.get("port", 50051)
        use_tls = discovery_config.get("use_tls", False)
        timeout = discovery_config.get("timeout_seconds", self._default_timeout)

        if not host:
            raise DiscoveryError(
                "Missing required field 'host' in discovery_config",
                adapter_name=self.protocol_name,
            )

        endpoint = f"{host}:{port}"
        logger.info(
            "discovering_grpc_services",
            endpoint=endpoint,
            use_tls=use_tls,
        )

        try:
            # Create channel
            channel = await self._create_channel(endpoint, discovery_config)

            # Use reflection to discover services
            from sark.adapters.grpc.reflection import GRPCReflectionClient

            reflection_client = GRPCReflectionClient(channel)
            services = await asyncio.wait_for(reflection_client.list_services(), timeout=timeout)

            resources = []
            for service_name in services:
                # Skip reflection service itself
                if service_name.startswith("grpc.reflection"):
                    continue

                # Get service descriptor
                service_descriptor = await reflection_client.get_service_descriptor(service_name)

                # Extract capabilities (methods) from service
                capabilities = []
                for method in service_descriptor.methods:
                    capability_id = f"{service_name}.{method.name}"
                    capabilities.append(
                        CapabilitySchema(
                            id=capability_id,
                            resource_id=endpoint,
                            name=method.name,
                            description=f"gRPC method {method.name} on service {service_name}",
                            input_schema={
                                "type": "grpc",
                                "message_type": method.input_type,
                                "streaming": method.client_streaming,
                            },
                            output_schema={
                                "type": "grpc",
                                "message_type": method.output_type,
                                "streaming": method.server_streaming,
                            },
                            sensitivity_level="medium",
                            metadata={
                                "service_name": service_name,
                                "method_name": method.name,
                                "client_streaming": method.client_streaming,
                                "server_streaming": method.server_streaming,
                                "full_method": f"/{service_name}/{method.name}",
                            },
                        )
                    )

                # Create resource for this service
                resource = ResourceSchema(
                    id=f"grpc-{endpoint}-{service_name}",
                    name=service_name,
                    protocol=self.protocol_name,
                    endpoint=endpoint,
                    sensitivity_level="medium",
                    metadata={
                        "host": host,
                        "port": port,
                        "use_tls": use_tls,
                        "auth": discovery_config.get("auth", {}),
                        "service_name": service_name,
                        "capabilities": [c.dict() for c in capabilities],
                    },
                    created_at=time.time(),
                    updated_at=time.time(),
                )
                resources.append(resource)

            # Cache the channel for later use
            self._channels[endpoint] = channel

            logger.info(
                "grpc_services_discovered",
                endpoint=endpoint,
                service_count=len(resources),
                services=[r.name for r in resources],
            )

            return resources

        except builtins.TimeoutError as e:
            raise TimeoutError(
                f"Service discovery timed out after {timeout}s",
                adapter_name=self.protocol_name,
                resource_id=endpoint,
                timeout_seconds=timeout,
            ) from e
        except grpc.RpcError as e:
            raise ConnectionError(
                f"Failed to connect to gRPC server: {e.details()}",
                adapter_name=self.protocol_name,
                resource_id=endpoint,
                details={"code": e.code().name, "details": e.details()},
            ) from e
        except Exception as e:
            raise DiscoveryError(
                f"Service discovery failed: {e!s}",
                adapter_name=self.protocol_name,
                resource_id=endpoint,
            ) from e

    async def get_capabilities(self, resource: ResourceSchema) -> list[CapabilitySchema]:
        """
        Get all capabilities (methods) for a gRPC service.

        Args:
            resource: The gRPC service resource

        Returns:
            List of capabilities (gRPC methods)
        """
        capabilities_data = resource.metadata.get("capabilities", [])
        return [CapabilitySchema(**cap) for cap in capabilities_data]

    async def validate_request(self, request: InvocationRequest) -> bool:
        """
        Validate a gRPC invocation request.

        Args:
            request: The invocation request

        Returns:
            True if valid

        Raises:
            ValidationError: If request is invalid
        """
        if not request.capability_id:
            raise ValidationError(
                "Missing capability_id",
                adapter_name=self.protocol_name,
            )

        if not isinstance(request.arguments, dict):
            raise ValidationError(
                "Arguments must be a dictionary",
                adapter_name=self.protocol_name,
            )

        return True

    async def invoke(self, request: InvocationRequest) -> InvocationResult:
        """
        Invoke a gRPC method.

        Args:
            request: The invocation request with:
                - capability_id: Full method name (e.g., "my.service.v1.MyService.GetUser")
                - arguments: Request message as dict
                - context: Additional context (timeout, metadata, etc.)

        Returns:
            InvocationResult with response or error

        Note:
            This handles unary RPCs. For streaming, use invoke_streaming().
        """
        start_time = time.time()
        capability_id = request.capability_id

        try:
            # Parse capability ID to get service and method
            # Format: "service.name.MethodName" or full path "/{service}/{method}"
            service_name, method_name, endpoint = await self._parse_capability_id(
                capability_id, request.context
            )

            logger.info(
                "invoking_grpc_method",
                service=service_name,
                method=method_name,
                endpoint=endpoint,
                principal=request.principal_id,
            )

            # Get or create channel
            channel = await self._get_channel(endpoint, request.context)

            # Import reflection to get method descriptor
            from sark.adapters.grpc.reflection import GRPCReflectionClient

            reflection_client = GRPCReflectionClient(channel)
            service_descriptor = await reflection_client.get_service_descriptor(service_name)

            # Find method descriptor
            method_descriptor = None
            for method in service_descriptor.methods:
                if method.name == method_name:
                    method_descriptor = method
                    break

            if not method_descriptor:
                raise InvocationError(
                    f"Method {method_name} not found on service {service_name}",
                    capability_id=capability_id,
                    adapter_name=self.protocol_name,
                )

            # Check if this is a streaming method
            if method_descriptor.client_streaming or method_descriptor.server_streaming:
                raise UnsupportedOperationError(
                    "Streaming methods must use invoke_streaming()",
                    operation="invoke",
                    adapter_name=self.protocol_name,
                )

            # Execute unary RPC
            from sark.adapters.grpc.streaming import GRPCStreamHandler

            stream_handler = GRPCStreamHandler(channel)
            response = await stream_handler.invoke_unary(
                service_name=service_name,
                method_name=method_name,
                request_data=request.arguments,
                timeout=request.context.get("timeout", self._default_timeout),
                metadata=request.context.get("metadata", {}),
            )

            duration_ms = (time.time() - start_time) * 1000

            logger.info(
                "grpc_invocation_success",
                service=service_name,
                method=method_name,
                duration_ms=duration_ms,
            )

            return InvocationResult(
                success=True,
                result=response,
                metadata={
                    "service": service_name,
                    "method": method_name,
                    "endpoint": endpoint,
                },
                duration_ms=duration_ms,
            )

        except grpc.RpcError as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"gRPC error: {e.code().name} - {e.details()}"

            logger.error(
                "grpc_invocation_failed",
                error=error_msg,
                code=e.code().name,
                duration_ms=duration_ms,
            )

            return InvocationResult(
                success=False,
                error=error_msg,
                metadata={
                    "grpc_code": e.code().name,
                    "grpc_details": e.details(),
                },
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"Invocation failed: {e!s}"

            logger.error(
                "grpc_invocation_error",
                error=error_msg,
                duration_ms=duration_ms,
            )

            return InvocationResult(
                success=False,
                error=error_msg,
                duration_ms=duration_ms,
            )

    async def invoke_streaming(self, request: InvocationRequest) -> AsyncIterator[Any]:
        """
        Invoke a gRPC streaming method.

        Supports:
        - Server streaming (one request, multiple responses)
        - Client streaming (multiple requests, one response)
        - Bidirectional streaming (multiple requests and responses)

        Args:
            request: The invocation request

        Yields:
            Response messages as they arrive

        Raises:
            StreamingError: If streaming fails
            UnsupportedOperationError: If method is not streaming
        """
        capability_id = request.capability_id

        try:
            # Parse capability ID
            service_name, method_name, endpoint = await self._parse_capability_id(
                capability_id, request.context
            )

            # Get channel
            channel = await self._get_channel(endpoint, request.context)

            # Get method descriptor
            from sark.adapters.grpc.reflection import GRPCReflectionClient

            reflection_client = GRPCReflectionClient(channel)
            service_descriptor = await reflection_client.get_service_descriptor(service_name)

            method_descriptor = None
            for method in service_descriptor.methods:
                if method.name == method_name:
                    method_descriptor = method
                    break

            if not method_descriptor:
                raise InvocationError(
                    f"Method {method_name} not found",
                    capability_id=capability_id,
                    adapter_name=self.protocol_name,
                )

            # Determine streaming type and invoke
            from sark.adapters.grpc.streaming import GRPCStreamHandler

            stream_handler = GRPCStreamHandler(channel)

            if method_descriptor.server_streaming and not method_descriptor.client_streaming:
                # Server streaming
                async for response in stream_handler.invoke_server_streaming(
                    service_name=service_name,
                    method_name=method_name,
                    request_data=request.arguments,
                    timeout=request.context.get("timeout"),
                    metadata=request.context.get("metadata", {}),
                ):
                    yield response

            elif method_descriptor.client_streaming and not method_descriptor.server_streaming:
                # Client streaming
                request_iterator = request.arguments.get("requests", [])
                response = await stream_handler.invoke_client_streaming(
                    service_name=service_name,
                    method_name=method_name,
                    request_iterator=request_iterator,
                    timeout=request.context.get("timeout"),
                    metadata=request.context.get("metadata", {}),
                )
                yield response

            elif method_descriptor.client_streaming and method_descriptor.server_streaming:
                # Bidirectional streaming
                request_iterator = request.arguments.get("requests", [])
                async for response in stream_handler.invoke_bidirectional_streaming(
                    service_name=service_name,
                    method_name=method_name,
                    request_iterator=request_iterator,
                    timeout=request.context.get("timeout"),
                    metadata=request.context.get("metadata", {}),
                ):
                    yield response

            else:
                raise UnsupportedOperationError(
                    "Non-streaming methods should use invoke()",
                    operation="invoke_streaming",
                    adapter_name=self.protocol_name,
                )

        except grpc.RpcError as e:
            raise StreamingError(
                f"Streaming failed: {e.code().name} - {e.details()}",
                adapter_name=self.protocol_name,
                details={"code": e.code().name, "details": e.details()},
            ) from e
        except Exception as e:
            raise StreamingError(
                f"Streaming error: {e!s}",
                adapter_name=self.protocol_name,
            ) from e

    async def health_check(self, resource: ResourceSchema) -> bool:
        """
        Check if gRPC service is healthy.

        Uses standard gRPC health checking protocol if available,
        otherwise attempts a reflection call.

        Args:
            resource: The gRPC service resource

        Returns:
            True if healthy, False otherwise
        """
        endpoint = resource.endpoint

        try:
            channel = await self._get_channel(endpoint, resource.metadata)

            # Try standard health check
            try:
                from grpc_health.v1 import health_pb2, health_pb2_grpc

                health_stub = health_pb2_grpc.HealthStub(channel)
                health_request = health_pb2.HealthCheckRequest(
                    service=resource.metadata.get("service_name", "")
                )
                response = await asyncio.wait_for(health_stub.Check(health_request), timeout=5.0)
                is_healthy = response.status == health_pb2.HealthCheckResponse.SERVING

                logger.info(
                    "grpc_health_check",
                    endpoint=endpoint,
                    service=resource.name,
                    healthy=is_healthy,
                    method="health_protocol",
                )
                return is_healthy

            except Exception:
                # Fallback: try reflection as health check
                from sark.adapters.grpc.reflection import GRPCReflectionClient

                reflection_client = GRPCReflectionClient(channel)
                await asyncio.wait_for(reflection_client.list_services(), timeout=5.0)

                logger.info(
                    "grpc_health_check",
                    endpoint=endpoint,
                    service=resource.name,
                    healthy=True,
                    method="reflection_fallback",
                )
                return True

        except Exception as e:
            logger.warning(
                "grpc_health_check_failed",
                endpoint=endpoint,
                service=resource.name,
                error=str(e),
            )
            return False

    async def on_resource_registered(self, resource: ResourceSchema) -> None:
        """
        Called when a gRPC service is registered.

        Pre-creates channel for better performance.
        """
        endpoint = resource.endpoint
        logger.info("grpc_resource_registered", endpoint=endpoint, service=resource.name)

        try:
            # Pre-create channel
            await self._get_channel(endpoint, resource.metadata)
        except Exception as e:
            logger.warning(
                "grpc_channel_precreation_failed",
                endpoint=endpoint,
                error=str(e),
            )

    async def on_resource_unregistered(self, resource: ResourceSchema) -> None:
        """
        Called when a gRPC service is unregistered.

        Closes channel and releases resources.
        """
        endpoint = resource.endpoint

        if endpoint in self._channels:
            channel = self._channels.pop(endpoint)
            await channel.close()
            logger.info(
                "grpc_channel_closed",
                endpoint=endpoint,
                service=resource.name,
            )

    # Private helper methods

    async def _create_channel(self, endpoint: str, config: dict[str, Any]) -> aio.Channel:
        """
        Create a gRPC channel with configuration.

        Args:
            endpoint: Server endpoint (host:port)
            config: Configuration including auth and TLS settings

        Returns:
            Configured gRPC channel
        """
        use_tls = config.get("use_tls", False)
        auth_config = config.get("auth", {})
        config.get("max_connections", 10)

        # Channel options
        options = [
            ("grpc.max_send_message_length", self._max_message_length),
            ("grpc.max_receive_message_length", self._max_message_length),
            ("grpc.keepalive_time_ms", 30000),
            ("grpc.keepalive_timeout_ms", 10000),
            ("grpc.http2.max_pings_without_data", 0),
            ("grpc.keepalive_permit_without_calls", 1),
        ]

        # Create channel based on TLS settings
        if use_tls:
            credentials = await self._create_credentials(auth_config)
            channel = aio.secure_channel(endpoint, credentials, options=options)
        else:
            channel = aio.insecure_channel(endpoint, options=options)

        logger.info(
            "grpc_channel_created",
            endpoint=endpoint,
            use_tls=use_tls,
            auth_type=auth_config.get("type", "none"),
        )

        return channel

    async def _create_credentials(self, auth_config: dict[str, Any]) -> grpc.ChannelCredentials:
        """
        Create gRPC credentials from auth configuration.

        Args:
            auth_config: Authentication configuration

        Returns:
            gRPC credentials

        Raises:
            AuthenticationError: If credential creation fails
        """
        auth_type = auth_config.get("type", "none")

        try:
            if auth_type == "mtls":
                # Mutual TLS
                cert_path = auth_config.get("cert_path")
                key_path = auth_config.get("key_path")
                ca_path = auth_config.get("ca_path")

                if not all([cert_path, key_path, ca_path]):
                    raise AuthenticationError(
                        "mTLS requires cert_path, key_path, and ca_path",
                        adapter_name=self.protocol_name,
                    )

                with open(ca_path, "rb") as f:
                    ca_cert = f.read()
                with open(cert_path, "rb") as f:
                    cert = f.read()
                with open(key_path, "rb") as f:
                    key = f.read()

                return grpc.ssl_channel_credentials(
                    root_certificates=ca_cert,
                    private_key=key,
                    certificate_chain=cert,
                )

            elif auth_type == "tls":
                # TLS only (no client cert)
                ca_path = auth_config.get("ca_path")

                if ca_path:
                    with open(ca_path, "rb") as f:
                        ca_cert = f.read()
                    return grpc.ssl_channel_credentials(root_certificates=ca_cert)
                else:
                    return grpc.ssl_channel_credentials()

            else:
                # Default TLS
                return grpc.ssl_channel_credentials()

        except FileNotFoundError as e:
            raise AuthenticationError(
                f"Credential file not found: {e!s}",
                adapter_name=self.protocol_name,
            ) from e
        except Exception as e:
            raise AuthenticationError(
                f"Failed to create credentials: {e!s}",
                adapter_name=self.protocol_name,
            ) from e

    async def _get_channel(self, endpoint: str, context: dict[str, Any]) -> aio.Channel:
        """
        Get or create a channel for an endpoint.

        Args:
            endpoint: Server endpoint
            context: Context with configuration

        Returns:
            gRPC channel
        """
        if endpoint not in self._channels:
            self._channels[endpoint] = await self._create_channel(endpoint, context)

        return self._channels[endpoint]

    async def _parse_capability_id(
        self, capability_id: str, context: dict[str, Any]
    ) -> tuple[str, str, str]:
        """
        Parse capability ID to extract service, method, and endpoint.

        Args:
            capability_id: Capability identifier
            context: Request context with metadata

        Returns:
            Tuple of (service_name, method_name, endpoint)

        Raises:
            ValidationError: If capability ID is invalid
        """
        # Format: "service.name.MethodName" or from metadata
        parts = capability_id.rsplit(".", 1)
        if len(parts) != 2:
            raise ValidationError(
                f"Invalid capability_id format: {capability_id}",
                adapter_name=self.protocol_name,
            )

        service_name = parts[0]
        method_name = parts[1]
        endpoint = context.get("endpoint", "")

        if not endpoint:
            raise ValidationError(
                "Missing endpoint in context",
                adapter_name=self.protocol_name,
            )

        return service_name, method_name, endpoint

    def supports_streaming(self) -> bool:
        """gRPC adapter supports streaming."""
        return True


__all__ = ["GRPCAdapter"]
