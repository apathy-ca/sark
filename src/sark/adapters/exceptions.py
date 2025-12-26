"""
Exception hierarchy for protocol adapters.

This module defines a comprehensive exception hierarchy for all adapter-related
errors. All adapters should raise these exceptions for consistent error handling.
"""

from typing import Any


class AdapterError(Exception):
    """Base exception for all adapter errors."""

    def __init__(
        self,
        message: str,
        *,
        adapter_name: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """
        Initialize adapter error.

        Args:
            message: Human-readable error message
            adapter_name: Name of the adapter that raised the error
            resource_id: ID of the resource involved (if applicable)
            details: Additional error details (protocol-specific)
        """
        super().__init__(message)
        self.message = message
        self.adapter_name = adapter_name
        self.resource_id = resource_id
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """
        Convert exception to dictionary for API responses.

        Returns:
            Dictionary representation of the error
        """
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "adapter": self.adapter_name,
            "resource_id": self.resource_id,
            "details": self.details,
        }


class DiscoveryError(AdapterError):
    """Raised when resource discovery fails."""

    pass


class ConnectionError(AdapterError):
    """Raised when adapter cannot connect to the resource."""

    pass


class AuthenticationError(AdapterError):
    """Raised when authentication fails."""

    pass


class ValidationError(AdapterError):
    """Raised when request validation fails."""

    def __init__(self, message: str, *, validation_errors: list | None = None, **kwargs):
        """
        Initialize validation error.

        Args:
            message: Human-readable error message
            validation_errors: List of specific validation errors
            **kwargs: Additional AdapterError arguments
        """
        super().__init__(message, **kwargs)
        self.validation_errors = validation_errors or []
        self.details["validation_errors"] = self.validation_errors


class InvocationError(AdapterError):
    """Raised when capability invocation fails."""

    def __init__(
        self,
        message: str,
        *,
        capability_id: str | None = None,
        protocol_error: str | None = None,
        **kwargs,
    ):
        """
        Initialize invocation error.

        Args:
            message: Human-readable error message
            capability_id: ID of the capability that failed
            protocol_error: Protocol-specific error message
            **kwargs: Additional AdapterError arguments
        """
        super().__init__(message, **kwargs)
        self.capability_id = capability_id
        self.protocol_error = protocol_error
        if protocol_error:
            self.details["protocol_error"] = protocol_error


class ResourceNotFoundError(AdapterError):
    """Raised when a resource cannot be found."""

    pass


class CapabilityNotFoundError(AdapterError):
    """Raised when a capability cannot be found on a resource."""

    def __init__(
        self,
        message: str,
        *,
        capability_id: str | None = None,
        available_capabilities: list | None = None,
        **kwargs,
    ):
        """
        Initialize capability not found error.

        Args:
            message: Human-readable error message
            capability_id: ID of the capability that was not found
            available_capabilities: List of available capability IDs
            **kwargs: Additional AdapterError arguments
        """
        super().__init__(message, **kwargs)
        self.capability_id = capability_id
        if available_capabilities:
            self.details["available_capabilities"] = available_capabilities


class TimeoutError(AdapterError):
    """Raised when an operation times out."""

    def __init__(self, message: str, *, timeout_seconds: float | None = None, **kwargs):
        """
        Initialize timeout error.

        Args:
            message: Human-readable error message
            timeout_seconds: Timeout duration in seconds
            **kwargs: Additional AdapterError arguments
        """
        super().__init__(message, **kwargs)
        if timeout_seconds:
            self.details["timeout_seconds"] = timeout_seconds


class ProtocolError(AdapterError):
    """Raised when there's a protocol-specific error."""

    def __init__(
        self,
        message: str,
        *,
        protocol_name: str | None = None,
        protocol_version: str | None = None,
        protocol_details: dict[str, Any] | None = None,
        **kwargs,
    ):
        """
        Initialize protocol error.

        Args:
            message: Human-readable error message
            protocol_name: Name of the protocol (e.g., 'mcp', 'http')
            protocol_version: Protocol version
            protocol_details: Protocol-specific error details
            **kwargs: Additional AdapterError arguments
        """
        super().__init__(message, **kwargs)
        if protocol_name:
            self.details["protocol_name"] = protocol_name
        if protocol_version:
            self.details["protocol_version"] = protocol_version
        if protocol_details:
            self.details["protocol"] = protocol_details


class StreamingError(AdapterError):
    """Raised when streaming operations fail."""

    def __init__(self, message: str, *, chunks_received: int | None = None, **kwargs):
        """
        Initialize streaming error.

        Args:
            message: Human-readable error message
            chunks_received: Number of chunks successfully received before error
            **kwargs: Additional AdapterError arguments
        """
        super().__init__(message, **kwargs)
        if chunks_received is not None:
            self.details["chunks_received"] = chunks_received


class AdapterConfigurationError(AdapterError):
    """Raised when adapter configuration is invalid."""

    pass


class UnsupportedOperationError(AdapterError):
    """Raised when an operation is not supported by the adapter."""

    def __init__(self, message: str, *, operation: str | None = None, **kwargs):
        """
        Initialize unsupported operation error.

        Args:
            message: Human-readable error message
            operation: Name of the unsupported operation
            **kwargs: Additional AdapterError arguments
        """
        super().__init__(message, **kwargs)
        if operation:
            self.details["operation"] = operation


__all__ = [
    "AdapterConfigurationError",
    "AdapterError",
    "AuthenticationError",
    "CapabilityNotFoundError",
    "ConnectionError",
    "DiscoveryError",
    "InvocationError",
    "ProtocolError",
    "ResourceNotFoundError",
    "StreamingError",
    "TimeoutError",
    "UnsupportedOperationError",
    "ValidationError",
]
