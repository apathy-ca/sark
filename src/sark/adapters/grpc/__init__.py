"""
gRPC adapter submodule for SARK v2.0.

This submodule provides gRPC-specific components:
- GRPCReflectionClient: Service discovery via reflection
- GRPCStreamHandler: Streaming RPC handling
- ProtobufMessageHandler: Message serialization/deserialization

Version: 2.0.0
Engineer: ENGINEER-3
"""

from sark.adapters.grpc.reflection import (
    GRPCReflectionClient,
    MethodInfo,
    ServiceInfo,
)
from sark.adapters.grpc.streaming import (
    GRPCStreamHandler,
    ProtobufMessageHandler,
)

__all__ = [
    "GRPCReflectionClient",
    "ServiceInfo",
    "MethodInfo",
    "GRPCStreamHandler",
    "ProtobufMessageHandler",
]
