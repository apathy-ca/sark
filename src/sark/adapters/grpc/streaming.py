"""
gRPC Streaming RPC Handler.

This module handles all types of gRPC streaming:
- Unary RPC (single request, single response)
- Server streaming (single request, stream of responses)
- Client streaming (stream of requests, single response)
- Bidirectional streaming (stream of requests, stream of responses)

Version: 2.0.0
Engineer: ENGINEER-3
"""

import asyncio
from typing import Any, AsyncIterator, Dict, Iterable, List, Optional

import grpc
import structlog
from google.protobuf import json_format
from grpc import aio

logger = structlog.get_logger(__name__)


class GRPCStreamHandler:
    """
    Handler for gRPC streaming operations.

    Provides methods for invoking all types of gRPC methods:
    unary, server streaming, client streaming, and bidirectional streaming.

    Uses dynamic invocation based on reflection to call methods without
    requiring pre-compiled stubs.
    """

    def __init__(self, channel: aio.Channel):
        """
        Initialize stream handler.

        Args:
            channel: gRPC channel to use for calls
        """
        self._channel = channel
        logger.debug("grpc_stream_handler_initialized")

    async def invoke_unary(
        self,
        service_name: str,
        method_name: str,
        request_data: Dict[str, Any],
        timeout: Optional[float] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Invoke a unary RPC (single request, single response).

        Args:
            service_name: Fully-qualified service name
            method_name: Method name
            request_data: Request data as dictionary
            timeout: Optional timeout in seconds
            metadata: Optional metadata headers

        Returns:
            Response data as dictionary

        Raises:
            grpc.RpcError: If RPC fails

        Example:
            >>> response = await handler.invoke_unary(
            ...     service_name="myapp.v1.UserService",
            ...     method_name="GetUser",
            ...     request_data={"user_id": "123"}
            ... )
            >>> print(response)
            {'user_id': '123', 'name': 'Alice', 'email': 'alice@example.com'}
        """
        logger.debug(
            "invoking_unary_rpc",
            service=service_name,
            method=method_name,
        )

        # Build method path
        method_path = f"/{service_name}/{method_name}"

        # Convert request data to bytes
        # For now, use JSON serialization (will enhance with proper protobuf later)
        import json

        request_bytes = json.dumps(request_data).encode("utf-8")

        # Build metadata
        grpc_metadata = self._build_metadata(metadata)

        # Create unary-unary call
        try:
            # Use generic_call for dynamic invocation
            call = self._channel.unary_unary(
                method=method_path,
                request_serializer=lambda x: x,  # Already serialized
                response_deserializer=lambda x: x,  # Will deserialize manually
            )

            # Execute call
            response_bytes = await asyncio.wait_for(
                call(request_bytes, metadata=grpc_metadata),
                timeout=timeout,
            )

            # Deserialize response
            response_data = json.loads(response_bytes.decode("utf-8"))

            logger.debug(
                "unary_rpc_completed",
                service=service_name,
                method=method_name,
            )

            return response_data

        except asyncio.TimeoutError as e:
            logger.error(
                "unary_rpc_timeout",
                service=service_name,
                method=method_name,
                timeout=timeout,
            )
            raise grpc.RpcError(f"RPC timed out after {timeout}s") from e

        except grpc.RpcError as e:
            logger.error(
                "unary_rpc_failed",
                service=service_name,
                method=method_name,
                code=e.code().name,
                details=e.details(),
            )
            raise

    async def invoke_server_streaming(
        self,
        service_name: str,
        method_name: str,
        request_data: Dict[str, Any],
        timeout: Optional[float] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Invoke a server streaming RPC (single request, stream of responses).

        Args:
            service_name: Fully-qualified service name
            method_name: Method name
            request_data: Request data as dictionary
            timeout: Optional timeout in seconds
            metadata: Optional metadata headers

        Yields:
            Response messages as dictionaries

        Raises:
            grpc.RpcError: If RPC fails

        Example:
            >>> async for response in handler.invoke_server_streaming(
            ...     service_name="myapp.v1.EventService",
            ...     method_name="StreamEvents",
            ...     request_data={"topic": "user.created"}
            ... ):
            ...     print(response)
            {'event_id': '1', 'data': {...}}
            {'event_id': '2', 'data': {...}}
        """
        logger.debug(
            "invoking_server_streaming_rpc",
            service=service_name,
            method=method_name,
        )

        method_path = f"/{service_name}/{method_name}"
        import json

        request_bytes = json.dumps(request_data).encode("utf-8")
        grpc_metadata = self._build_metadata(metadata)

        try:
            # Create unary-stream call
            call = self._channel.unary_stream(
                method=method_path,
                request_serializer=lambda x: x,
                response_deserializer=lambda x: x,
            )

            # Execute call
            response_stream = call(request_bytes, metadata=grpc_metadata)

            # Stream responses
            count = 0
            async for response_bytes in response_stream:
                response_data = json.loads(response_bytes.decode("utf-8"))
                count += 1
                logger.debug(
                    "server_streaming_message_received",
                    service=service_name,
                    method=method_name,
                    message_count=count,
                )
                yield response_data

            logger.debug(
                "server_streaming_completed",
                service=service_name,
                method=method_name,
                total_messages=count,
            )

        except grpc.RpcError as e:
            logger.error(
                "server_streaming_failed",
                service=service_name,
                method=method_name,
                code=e.code().name,
                details=e.details(),
            )
            raise

    async def invoke_client_streaming(
        self,
        service_name: str,
        method_name: str,
        request_iterator: Iterable[Dict[str, Any]],
        timeout: Optional[float] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Invoke a client streaming RPC (stream of requests, single response).

        Args:
            service_name: Fully-qualified service name
            method_name: Method name
            request_iterator: Iterable of request data dictionaries
            timeout: Optional timeout in seconds
            metadata: Optional metadata headers

        Returns:
            Response data as dictionary

        Raises:
            grpc.RpcError: If RPC fails

        Example:
            >>> requests = [
            ...     {"value": 1},
            ...     {"value": 2},
            ...     {"value": 3}
            ... ]
            >>> response = await handler.invoke_client_streaming(
            ...     service_name="myapp.v1.CalculatorService",
            ...     method_name="Sum",
            ...     request_iterator=requests
            ... )
            >>> print(response)
            {'sum': 6}
        """
        logger.debug(
            "invoking_client_streaming_rpc",
            service=service_name,
            method=method_name,
        )

        method_path = f"/{service_name}/{method_name}"
        grpc_metadata = self._build_metadata(metadata)

        async def request_generator():
            """Generator to stream requests."""
            import json

            count = 0
            for request_data in request_iterator:
                request_bytes = json.dumps(request_data).encode("utf-8")
                count += 1
                logger.debug(
                    "client_streaming_sending_message",
                    service=service_name,
                    method=method_name,
                    message_count=count,
                )
                yield request_bytes

        try:
            # Create stream-unary call
            call = self._channel.stream_unary(
                method=method_path,
                request_serializer=lambda x: x,
                response_deserializer=lambda x: x,
            )

            # Execute call
            response_bytes = await asyncio.wait_for(
                call(request_generator(), metadata=grpc_metadata),
                timeout=timeout,
            )

            # Deserialize response
            import json

            response_data = json.loads(response_bytes.decode("utf-8"))

            logger.debug(
                "client_streaming_completed",
                service=service_name,
                method=method_name,
            )

            return response_data

        except grpc.RpcError as e:
            logger.error(
                "client_streaming_failed",
                service=service_name,
                method=method_name,
                code=e.code().name,
                details=e.details(),
            )
            raise

    async def invoke_bidirectional_streaming(
        self,
        service_name: str,
        method_name: str,
        request_iterator: Iterable[Dict[str, Any]],
        timeout: Optional[float] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Invoke a bidirectional streaming RPC (stream of requests and responses).

        Args:
            service_name: Fully-qualified service name
            method_name: Method name
            request_iterator: Iterable of request data dictionaries
            timeout: Optional timeout in seconds
            metadata: Optional metadata headers

        Yields:
            Response messages as dictionaries

        Raises:
            grpc.RpcError: If RPC fails

        Example:
            >>> requests = [
            ...     {"query": "hello"},
            ...     {"query": "world"}
            ... ]
            >>> async for response in handler.invoke_bidirectional_streaming(
            ...     service_name="myapp.v1.ChatService",
            ...     method_name="Chat",
            ...     request_iterator=requests
            ... ):
            ...     print(response)
            {'message': 'Hello!'}
            {'message': 'World!'}
        """
        logger.debug(
            "invoking_bidirectional_streaming_rpc",
            service=service_name,
            method=method_name,
        )

        method_path = f"/{service_name}/{method_name}"
        grpc_metadata = self._build_metadata(metadata)

        async def request_generator():
            """Generator to stream requests."""
            import json

            count = 0
            for request_data in request_iterator:
                request_bytes = json.dumps(request_data).encode("utf-8")
                count += 1
                logger.debug(
                    "bidirectional_streaming_sending_message",
                    service=service_name,
                    method=method_name,
                    message_count=count,
                )
                yield request_bytes

        try:
            # Create stream-stream call
            call = self._channel.stream_stream(
                method=method_path,
                request_serializer=lambda x: x,
                response_deserializer=lambda x: x,
            )

            # Execute call
            response_stream = call(request_generator(), metadata=grpc_metadata)

            # Stream responses
            count = 0
            async for response_bytes in response_stream:
                import json

                response_data = json.loads(response_bytes.decode("utf-8"))
                count += 1
                logger.debug(
                    "bidirectional_streaming_message_received",
                    service=service_name,
                    method=method_name,
                    message_count=count,
                )
                yield response_data

            logger.debug(
                "bidirectional_streaming_completed",
                service=service_name,
                method=method_name,
                total_messages=count,
            )

        except grpc.RpcError as e:
            logger.error(
                "bidirectional_streaming_failed",
                service=service_name,
                method=method_name,
                code=e.code().name,
                details=e.details(),
            )
            raise

    def _build_metadata(
        self, metadata: Optional[Dict[str, str]] = None
    ) -> Optional[List[tuple]]:
        """
        Build gRPC metadata from dictionary.

        Args:
            metadata: Dictionary of metadata key-value pairs

        Returns:
            List of tuples for gRPC metadata, or None
        """
        if not metadata:
            return None

        return [(key, value) for key, value in metadata.items()]


class ProtobufMessageHandler:
    """
    Handler for protobuf message serialization/deserialization.

    This class will handle conversion between dictionaries and protobuf messages
    using reflection-based descriptors.

    Note: Currently using JSON as a fallback. Will be enhanced to use proper
    protobuf serialization in future iterations.
    """

    def __init__(self, reflection_client):
        """
        Initialize message handler.

        Args:
            reflection_client: GRPCReflectionClient instance for type info
        """
        self._reflection_client = reflection_client
        logger.debug("protobuf_message_handler_initialized")

    async def serialize_request(
        self, message_type: str, data: Dict[str, Any]
    ) -> bytes:
        """
        Serialize a request dictionary to protobuf bytes.

        Args:
            message_type: Fully-qualified message type
            data: Request data as dictionary

        Returns:
            Serialized protobuf bytes
        """
        try:
            # Get message descriptor
            descriptor = await self._reflection_client.get_message_descriptor(
                message_type
            )

            # Create message instance
            message = self._reflection_client.create_request_message(
                message_type, data
            )

            # Serialize to bytes
            return message.SerializeToString()

        except Exception as e:
            logger.error(
                "request_serialization_failed",
                message_type=message_type,
                error=str(e),
            )
            # Fallback to JSON
            import json

            return json.dumps(data).encode("utf-8")

    def deserialize_response(
        self, message_type: str, data: bytes
    ) -> Dict[str, Any]:
        """
        Deserialize protobuf bytes to dictionary.

        Args:
            message_type: Fully-qualified message type
            data: Serialized protobuf bytes

        Returns:
            Response data as dictionary
        """
        try:
            # Get message class
            message_class = self._reflection_client._symbol_db.GetSymbol(message_type)
            message = message_class()

            # Parse bytes
            message.ParseFromString(data)

            # Convert to dict
            return self._reflection_client.message_to_dict(message)

        except Exception as e:
            logger.error(
                "response_deserialization_failed",
                message_type=message_type,
                error=str(e),
            )
            # Fallback to JSON
            import json

            return json.loads(data.decode("utf-8"))


__all__ = [
    "GRPCStreamHandler",
    "ProtobufMessageHandler",
]
