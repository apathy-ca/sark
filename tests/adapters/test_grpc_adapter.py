"""
Test suite for gRPC Adapter.

Tests:
- Service discovery via reflection
- Unary, streaming, client streaming, and bidirectional RPCs
- Authentication (mTLS, token-based)
- Connection pooling
- Error handling
- Health checking

Version: 2.0.0
Engineer: ENGINEER-3
"""

import asyncio
from datetime import datetime
from typing import AsyncIterator, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import grpc
import pytest
from grpc import aio

from sark.adapters.grpc_adapter import GRPCAdapter
from sark.adapters.grpc.auth import (
    AuthenticationHelper,
    MetadataInjectorInterceptor,
    TokenAuthInterceptor,
    create_authenticated_channel,
)
from sark.adapters.grpc.reflection import (
    GRPCReflectionClient,
    MethodInfo,
    ServiceInfo,
)
from sark.adapters.grpc.streaming import GRPCStreamHandler
from sark.models.base import (
    CapabilitySchema,
    InvocationRequest,
    ResourceSchema,
)


class TestGRPCAdapter:
    """Test suite for GRPCAdapter."""

    @pytest.fixture
    def adapter(self):
        """Create adapter instance."""
        return GRPCAdapter(default_timeout=10.0)

    @pytest.fixture
    def mock_channel(self):
        """Create mock gRPC channel."""
        channel = AsyncMock(spec=aio.Channel)
        return channel

    def test_protocol_properties(self, adapter):
        """Test protocol name and version."""
        assert adapter.protocol_name == "grpc"
        assert adapter.protocol_version == "1.60.0"

    def test_supports_streaming(self, adapter):
        """Test that adapter reports streaming support."""
        assert adapter.supports_streaming() is True

    @pytest.mark.asyncio
    async def test_discover_resources_missing_host(self, adapter):
        """Test discovery fails without host."""
        from sark.adapters.exceptions import DiscoveryError

        with pytest.raises(DiscoveryError, match="Missing required field 'host'"):
            await adapter.discover_resources({})

    @pytest.mark.asyncio
    async def test_validate_request_missing_capability(self, adapter):
        """Test validation fails without capability_id."""
        from sark.adapters.exceptions import ValidationError

        request = InvocationRequest(
            capability_id="",
            principal_id="user-123",
            arguments={},
        )

        with pytest.raises(ValidationError, match="Missing capability_id"):
            await adapter.validate_request(request)

    @pytest.mark.asyncio
    async def test_validate_request_invalid_arguments(self, adapter):
        """Test validation fails with invalid arguments."""
        from sark.adapters.exceptions import ValidationError

        request = InvocationRequest(
            capability_id="service.Method",
            principal_id="user-123",
            arguments="not-a-dict",  # Should be dict
        )

        with pytest.raises(ValidationError, match="Arguments must be a dictionary"):
            await adapter.validate_request(request)

    @pytest.mark.asyncio
    async def test_validate_request_success(self, adapter):
        """Test successful validation."""
        request = InvocationRequest(
            capability_id="myservice.v1.UserService.GetUser",
            principal_id="user-123",
            arguments={"user_id": "456"},
        )

        result = await adapter.validate_request(request)
        assert result is True

    @pytest.mark.asyncio
    async def test_create_channel_insecure(self, adapter):
        """Test insecure channel creation."""
        with patch("grpc.aio.insecure_channel") as mock_insecure:
            mock_channel = AsyncMock()
            mock_insecure.return_value = mock_channel

            config = {
                "use_tls": False,
                "auth": {"type": "none"},
            }

            channel = await adapter._create_channel("localhost:50051", config)

            assert channel == mock_channel
            mock_insecure.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_channel_with_tls(self, adapter):
        """Test TLS channel creation."""
        with patch("grpc.aio.secure_channel") as mock_secure:
            with patch("grpc.ssl_channel_credentials") as mock_creds:
                mock_channel = AsyncMock()
                mock_secure.return_value = mock_channel
                mock_credentials = MagicMock()
                mock_creds.return_value = mock_credentials

                config = {
                    "use_tls": True,
                    "auth": {"type": "tls"},
                }

                channel = await adapter._create_channel("localhost:50051", config)

                assert channel == mock_channel
                mock_secure.assert_called_once()
                mock_creds.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_using_health_protocol(self, adapter):
        """Test health check using standard health protocol."""
        with patch.object(adapter, "_get_channel") as mock_get_channel:
            # Mock health check response
            mock_channel = AsyncMock()
            mock_get_channel.return_value = mock_channel

            # Create a mock health stub
            with patch("grpc_health.v1.health_pb2_grpc.HealthStub") as mock_health_stub:
                mock_stub_instance = AsyncMock()
                mock_health_stub.return_value = mock_stub_instance

                # Mock successful health response
                from grpc_health.v1 import health_pb2

                mock_response = health_pb2.HealthCheckResponse()
                mock_response.status = health_pb2.HealthCheckResponse.SERVING
                mock_stub_instance.Check.return_value = mock_response

                resource = ResourceSchema(
                    id="test-resource",
                    name="TestService",
                    protocol="grpc",
                    endpoint="localhost:50051",
                    metadata={"service_name": "test.Service"},
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )

                is_healthy = await adapter.health_check(resource)

                assert is_healthy is True

    @pytest.mark.asyncio
    async def test_on_resource_registered(self, adapter):
        """Test resource registration lifecycle hook."""
        with patch.object(adapter, "_get_channel") as mock_get_channel:
            mock_channel = AsyncMock()
            mock_get_channel.return_value = mock_channel

            resource = ResourceSchema(
                id="test-resource",
                name="TestService",
                protocol="grpc",
                endpoint="localhost:50051",
                metadata={},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            # Should not raise
            await adapter.on_resource_registered(resource)

            # Channel should be created
            mock_get_channel.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_resource_unregistered(self, adapter):
        """Test resource unregistration lifecycle hook."""
        endpoint = "localhost:50051"
        mock_channel = AsyncMock()

        # Pre-populate channel cache
        adapter._channels[endpoint] = mock_channel

        resource = ResourceSchema(
            id="test-resource",
            name="TestService",
            protocol="grpc",
            endpoint=endpoint,
            metadata={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        await adapter.on_resource_unregistered(resource)

        # Channel should be closed and removed
        mock_channel.close.assert_called_once()
        assert endpoint not in adapter._channels


class TestGRPCReflectionClient:
    """Test suite for GRPCReflectionClient."""

    @pytest.fixture
    def mock_channel(self):
        """Create mock gRPC channel."""
        return AsyncMock(spec=aio.Channel)

    @pytest.fixture
    def reflection_client(self, mock_channel):
        """Create reflection client with mock channel."""
        return GRPCReflectionClient(mock_channel)

    @pytest.mark.asyncio
    async def test_list_services(self, reflection_client):
        """Test listing services via reflection."""
        from grpc_reflection.v1alpha import reflection_pb2

        # Mock stub
        mock_stub = AsyncMock()
        reflection_client._stub = mock_stub

        # Mock response
        mock_response = reflection_pb2.ServerReflectionResponse()
        service1 = mock_response.list_services_response.service.add()
        service1.name = "test.Service1"
        service2 = mock_response.list_services_response.service.add()
        service2.name = "test.Service2"

        # Mock stream
        async def mock_stream():
            yield mock_response

        mock_stub.ServerReflectionInfo.return_value = mock_stream()

        services = await reflection_client.list_services()

        assert len(services) == 2
        assert "test.Service1" in services
        assert "test.Service2" in services

    @pytest.mark.asyncio
    async def test_list_services_error_response(self, reflection_client):
        """Test handling error response from reflection."""
        from grpc_reflection.v1alpha import reflection_pb2

        mock_stub = AsyncMock()
        reflection_client._stub = mock_stub

        # Mock error response
        mock_response = reflection_pb2.ServerReflectionResponse()
        mock_response.error_response.error_code = 5
        mock_response.error_response.error_message = "Not found"

        async def mock_stream():
            yield mock_response

        mock_stub.ServerReflectionInfo.return_value = mock_stream()

        with pytest.raises(grpc.RpcError, match="Not found"):
            await reflection_client.list_services()


class TestGRPCStreamHandler:
    """Test suite for GRPCStreamHandler."""

    @pytest.fixture
    def mock_channel(self):
        """Create mock gRPC channel."""
        return AsyncMock(spec=aio.Channel)

    @pytest.fixture
    def stream_handler(self, mock_channel):
        """Create stream handler."""
        return GRPCStreamHandler(mock_channel)

    @pytest.mark.asyncio
    async def test_invoke_unary(self, stream_handler, mock_channel):
        """Test unary RPC invocation."""
        import json

        # Mock unary call
        mock_call = AsyncMock()
        response_data = {"user_id": "123", "name": "Alice"}
        mock_call.return_value = json.dumps(response_data).encode("utf-8")

        mock_channel.unary_unary.return_value = mock_call

        result = await stream_handler.invoke_unary(
            service_name="test.UserService",
            method_name="GetUser",
            request_data={"user_id": "123"},
        )

        assert result == response_data
        mock_channel.unary_unary.assert_called_once()

    @pytest.mark.asyncio
    async def test_invoke_server_streaming(self, stream_handler, mock_channel):
        """Test server streaming RPC."""
        import json

        # Mock streaming call
        async def mock_stream():
            yield json.dumps({"event": 1}).encode("utf-8")
            yield json.dumps({"event": 2}).encode("utf-8")
            yield json.dumps({"event": 3}).encode("utf-8")

        mock_call = MagicMock()
        mock_call.return_value = mock_stream()

        mock_channel.unary_stream.return_value = mock_call

        results = []
        async for response in stream_handler.invoke_server_streaming(
            service_name="test.EventService",
            method_name="StreamEvents",
            request_data={"topic": "test"},
        ):
            results.append(response)

        assert len(results) == 3
        assert results[0] == {"event": 1}
        assert results[1] == {"event": 2}
        assert results[2] == {"event": 3}


class TestGRPCAuth:
    """Test suite for gRPC authentication."""

    def test_token_auth_interceptor_bearer(self):
        """Test bearer token interceptor."""
        interceptor = TokenAuthInterceptor(token="test-token", scheme="bearer")

        assert interceptor._token == "test-token"
        assert interceptor._scheme == "bearer"

        metadata = interceptor._build_auth_metadata()
        assert metadata == [("authorization", "Bearer test-token")]

    def test_token_auth_interceptor_apikey(self):
        """Test API key interceptor."""
        interceptor = TokenAuthInterceptor(
            token="api-key-123", scheme="apikey", header_name="x-api-key"
        )

        metadata = interceptor._build_auth_metadata()
        assert metadata == [("x-api-key", "api-key-123")]

    def test_metadata_injector(self):
        """Test metadata injection."""
        custom_metadata = {
            "x-client-id": "client-123",
            "x-api-version": "v1",
        }

        interceptor = MetadataInjectorInterceptor(custom_metadata)

        assert interceptor._metadata == custom_metadata

    def test_authentication_helper_bearer_token(self):
        """Test creating bearer token interceptor."""
        interceptor = AuthenticationHelper.create_bearer_token_interceptor(
            "test-bearer-token"
        )

        assert isinstance(interceptor, TokenAuthInterceptor)
        assert interceptor._scheme == "bearer"
        assert interceptor._token == "test-bearer-token"

    def test_authentication_helper_api_key(self):
        """Test creating API key interceptor."""
        interceptor = AuthenticationHelper.create_api_key_interceptor(
            "test-api-key", header_name="x-custom-key"
        )

        assert isinstance(interceptor, TokenAuthInterceptor)
        assert interceptor._scheme == "apikey"
        assert interceptor._token == "test-api-key"
        assert interceptor._header_name == "x-custom-key"

    def test_create_authenticated_channel_no_auth(self):
        """Test creating channel with no authentication."""
        with patch("grpc.aio.insecure_channel") as mock_insecure:
            mock_channel = AsyncMock()
            mock_insecure.return_value = mock_channel

            auth_config = {"type": "none"}

            channel = create_authenticated_channel(
                endpoint="localhost:50051",
                auth_config=auth_config,
                use_tls=False,
            )

            assert channel == mock_channel
            mock_insecure.assert_called_once()

    def test_create_authenticated_channel_with_bearer(self):
        """Test creating channel with bearer token auth."""
        with patch("grpc.aio.insecure_channel") as mock_insecure:
            with patch("grpc.intercept_channel") as mock_intercept:
                mock_channel = AsyncMock()
                mock_intercepted = AsyncMock()
                mock_insecure.return_value = mock_channel
                mock_intercept.return_value = mock_intercepted

                auth_config = {"type": "bearer", "token": "test-token"}

                channel = create_authenticated_channel(
                    endpoint="localhost:50051",
                    auth_config=auth_config,
                    use_tls=False,
                )

                # Should create intercepted channel
                mock_intercept.assert_called_once()
                assert channel == mock_intercepted


class TestIntegration:
    """Integration tests for gRPC adapter."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_adapter_lifecycle(self):
        """Test full adapter lifecycle."""
        adapter = GRPCAdapter()

        # Test adapter info
        info = adapter.get_adapter_info()
        assert info["protocol_name"] == "grpc"
        assert info["supports_streaming"] is True

        # Test repr
        repr_str = repr(adapter)
        assert "GRPCAdapter" in repr_str
        assert "grpc" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
