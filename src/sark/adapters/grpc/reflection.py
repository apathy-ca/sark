"""
gRPC Reflection Client for Service Discovery.

This module provides a client for the gRPC Server Reflection protocol,
allowing dynamic discovery of services and their methods without
requiring pre-compiled proto files.

Version: 2.0.0
Engineer: ENGINEER-3
"""

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import grpc
from google.protobuf import descriptor_pb2, descriptor_pool, symbol_database
from google.protobuf.descriptor import MethodDescriptor, ServiceDescriptor
from grpc import aio
from grpc_reflection.v1alpha import reflection_pb2, reflection_pb2_grpc

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class MethodInfo:
    """Information about a gRPC method."""

    name: str
    full_name: str
    input_type: str
    output_type: str
    client_streaming: bool
    server_streaming: bool


@dataclass
class ServiceInfo:
    """Information about a gRPC service."""

    name: str
    full_name: str
    methods: List[MethodInfo]
    file_descriptor: Any = None


class GRPCReflectionClient:
    """
    Client for gRPC Server Reflection API.

    Uses the standard gRPC reflection protocol to discover services,
    methods, and message types at runtime without needing .proto files.

    Example:
        channel = grpc.aio.insecure_channel("localhost:50051")
        client = GRPCReflectionClient(channel)
        services = await client.list_services()
        for service_name in services:
            descriptor = await client.get_service_descriptor(service_name)
            print(f"Service: {descriptor.name}")
            for method in descriptor.methods:
                print(f"  Method: {method.name}")
    """

    def __init__(self, channel: aio.Channel):
        """
        Initialize reflection client.

        Args:
            channel: gRPC channel to use for reflection
        """
        self._channel = channel
        self._stub = reflection_pb2_grpc.ServerReflectionStub(channel)
        self._descriptor_pool = descriptor_pool.DescriptorPool()
        self._symbol_db = symbol_database.SymbolDatabase(pool=self._descriptor_pool)

        logger.debug("grpc_reflection_client_initialized")

    async def list_services(self) -> List[str]:
        """
        List all services available on the server.

        Returns:
            List of service names (fully-qualified)

        Raises:
            grpc.RpcError: If reflection call fails

        Example:
            >>> services = await client.list_services()
            >>> print(services)
            ['grpc.health.v1.Health', 'myapp.v1.UserService', 'myapp.v1.OrderService']
        """
        logger.debug("listing_grpc_services")

        try:
            # Create reflection request
            request = reflection_pb2.ServerReflectionRequest(
                list_services=""  # Empty string lists all services
            )

            # Send request
            response_stream = self._stub.ServerReflectionInfo(iter([request]))

            # Get first (and only) response
            response = await response_stream.__anext__()

            if response.HasField("error_response"):
                error = response.error_response
                raise grpc.RpcError(
                    f"Reflection error: {error.error_code} - {error.error_message}"
                )

            # Extract service names
            services = [
                service.name for service in response.list_services_response.service
            ]

            logger.info("grpc_services_listed", count=len(services), services=services)

            return services

        except Exception as e:
            logger.error("grpc_reflection_list_failed", error=str(e))
            raise

    async def get_service_descriptor(self, service_name: str) -> ServiceInfo:
        """
        Get detailed descriptor for a service.

        Args:
            service_name: Fully-qualified service name

        Returns:
            ServiceInfo with methods and type information

        Raises:
            grpc.RpcError: If reflection call fails
            ValueError: If service not found

        Example:
            >>> descriptor = await client.get_service_descriptor("myapp.v1.UserService")
            >>> print(descriptor.name)
            'UserService'
            >>> for method in descriptor.methods:
            ...     print(f"{method.name}: {method.input_type} -> {method.output_type}")
        """
        logger.debug("getting_service_descriptor", service=service_name)

        try:
            # Request file containing service
            request = reflection_pb2.ServerReflectionRequest(
                file_containing_symbol=service_name
            )

            response_stream = self._stub.ServerReflectionInfo(iter([request]))
            response = await response_stream.__anext__()

            if response.HasField("error_response"):
                error = response.error_response
                raise ValueError(
                    f"Service {service_name} not found: {error.error_message}"
                )

            # Parse file descriptor
            file_descriptor_protos = response.file_descriptor_response.file_descriptor_proto

            # Build file descriptors
            file_descriptors = []
            for file_descriptor_proto_bytes in file_descriptor_protos:
                file_descriptor_proto = descriptor_pb2.FileDescriptorProto()
                file_descriptor_proto.ParseFromString(file_descriptor_proto_bytes)

                # Add dependencies first
                for dep_name in file_descriptor_proto.dependency:
                    try:
                        self._descriptor_pool.FindFileByName(dep_name)
                    except KeyError:
                        # Dependency not loaded, fetch it
                        await self._load_file_descriptor(dep_name)

                # Add this file to pool
                try:
                    file_descriptor = self._descriptor_pool.Add(file_descriptor_proto)
                    file_descriptors.append(file_descriptor)
                except Exception:
                    # Already added
                    file_descriptor = self._descriptor_pool.FindFileByName(
                        file_descriptor_proto.name
                    )
                    file_descriptors.append(file_descriptor)

            # Find the service in the file descriptors
            service_descriptor = None
            file_descriptor = None

            for fd in file_descriptors:
                for service in fd.services_by_name.values():
                    if service.full_name == service_name:
                        service_descriptor = service
                        file_descriptor = fd
                        break
                if service_descriptor:
                    break

            if not service_descriptor:
                raise ValueError(f"Service {service_name} not found in descriptors")

            # Extract method information
            methods = []
            for method in service_descriptor.methods:
                methods.append(
                    MethodInfo(
                        name=method.name,
                        full_name=method.full_name,
                        input_type=method.input_type.full_name,
                        output_type=method.output_type.full_name,
                        client_streaming=method.client_streaming,
                        server_streaming=method.server_streaming,
                    )
                )

            service_info = ServiceInfo(
                name=service_descriptor.name,
                full_name=service_descriptor.full_name,
                methods=methods,
                file_descriptor=file_descriptor,
            )

            logger.info(
                "service_descriptor_retrieved",
                service=service_name,
                method_count=len(methods),
            )

            return service_info

        except Exception as e:
            logger.error(
                "service_descriptor_failed", service=service_name, error=str(e)
            )
            raise

    async def get_message_descriptor(self, message_type: str) -> Any:
        """
        Get descriptor for a message type.

        Args:
            message_type: Fully-qualified message type name

        Returns:
            Message descriptor

        Raises:
            ValueError: If message type not found
        """
        logger.debug("getting_message_descriptor", message_type=message_type)

        try:
            # Request file containing symbol
            request = reflection_pb2.ServerReflectionRequest(
                file_containing_symbol=message_type
            )

            response_stream = self._stub.ServerReflectionInfo(iter([request]))
            response = await response_stream.__anext__()

            if response.HasField("error_response"):
                error = response.error_response
                raise ValueError(
                    f"Message type {message_type} not found: {error.error_message}"
                )

            # Parse and add file descriptor
            file_descriptor_protos = response.file_descriptor_response.file_descriptor_proto

            for file_descriptor_proto_bytes in file_descriptor_protos:
                file_descriptor_proto = descriptor_pb2.FileDescriptorProto()
                file_descriptor_proto.ParseFromString(file_descriptor_proto_bytes)

                # Add to pool
                try:
                    self._descriptor_pool.Add(file_descriptor_proto)
                except Exception:
                    pass  # Already added

            # Find message descriptor
            message_descriptor = self._descriptor_pool.FindMessageTypeByName(
                message_type
            )

            logger.debug("message_descriptor_retrieved", message_type=message_type)

            return message_descriptor

        except Exception as e:
            logger.error(
                "message_descriptor_failed", message_type=message_type, error=str(e)
            )
            raise

    async def get_all_service_info(self) -> Dict[str, ServiceInfo]:
        """
        Get detailed information for all services.

        Returns:
            Dictionary mapping service names to ServiceInfo

        Example:
            >>> all_services = await client.get_all_service_info()
            >>> for name, info in all_services.items():
            ...     print(f"{name}: {len(info.methods)} methods")
        """
        logger.debug("getting_all_service_info")

        services = await self.list_services()
        result = {}

        for service_name in services:
            # Skip reflection service itself
            if service_name.startswith("grpc.reflection"):
                continue

            try:
                service_info = await self.get_service_descriptor(service_name)
                result[service_name] = service_info
            except Exception as e:
                logger.warning(
                    "failed_to_get_service_info", service=service_name, error=str(e)
                )
                continue

        logger.info(
            "all_service_info_retrieved", total_services=len(result)
        )

        return result

    async def _load_file_descriptor(self, file_name: str) -> None:
        """
        Load a file descriptor by name.

        Args:
            file_name: Proto file name

        Raises:
            ValueError: If file not found
        """
        logger.debug("loading_file_descriptor", file=file_name)

        request = reflection_pb2.ServerReflectionRequest(
            file_by_filename=file_name
        )

        response_stream = self._stub.ServerReflectionInfo(iter([request]))
        response = await response_stream.__anext__()

        if response.HasField("error_response"):
            error = response.error_response
            raise ValueError(f"File {file_name} not found: {error.error_message}")

        file_descriptor_protos = response.file_descriptor_response.file_descriptor_proto

        for file_descriptor_proto_bytes in file_descriptor_protos:
            file_descriptor_proto = descriptor_pb2.FileDescriptorProto()
            file_descriptor_proto.ParseFromString(file_descriptor_proto_bytes)

            # Add dependencies recursively
            for dep_name in file_descriptor_proto.dependency:
                try:
                    self._descriptor_pool.FindFileByName(dep_name)
                except KeyError:
                    await self._load_file_descriptor(dep_name)

            # Add this file
            try:
                self._descriptor_pool.Add(file_descriptor_proto)
            except Exception:
                pass  # Already added

        logger.debug("file_descriptor_loaded", file=file_name)

    def create_request_message(
        self, message_type: str, data: Dict[str, Any]
    ) -> Any:
        """
        Create a protobuf message from a dictionary.

        Args:
            message_type: Fully-qualified message type name
            data: Dictionary with field values

        Returns:
            Protobuf message instance

        Note:
            This requires the message descriptor to be loaded first.
        """
        try:
            message_class = self._symbol_db.GetSymbol(message_type)
            message = message_class()

            # Set fields from data
            for field_name, value in data.items():
                if hasattr(message, field_name):
                    setattr(message, field_name, value)

            return message

        except Exception as e:
            logger.error(
                "create_request_message_failed",
                message_type=message_type,
                error=str(e),
            )
            raise

    def message_to_dict(self, message: Any) -> Dict[str, Any]:
        """
        Convert a protobuf message to a dictionary.

        Args:
            message: Protobuf message instance

        Returns:
            Dictionary representation
        """
        from google.protobuf import json_format

        try:
            return json_format.MessageToDict(
                message,
                preserving_proto_field_name=True,
                including_default_value_fields=False,
            )
        except Exception as e:
            logger.error("message_to_dict_failed", error=str(e))
            raise


__all__ = [
    "GRPCReflectionClient",
    "ServiceInfo",
    "MethodInfo",
]
