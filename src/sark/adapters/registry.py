"""
Protocol adapter registry for SARK v2.0.

This module provides a registry for managing protocol adapters.
In v1.x, this is a stub that will be fully populated in v2.0.
"""

import structlog

from sark.adapters.base import ProtocolAdapter
from sark.config import get_settings

logger = structlog.get_logger(__name__)


class AdapterRegistry:
    """
    Registry for protocol adapters.

    Manages the lifecycle of protocol adapters and provides
    lookup functionality.
    """

    def __init__(self):
        """Initialize the adapter registry."""
        self._adapters: dict[str, ProtocolAdapter] = {}
        self._initialized = False

    def register(self, adapter: ProtocolAdapter) -> None:
        """
        Register a protocol adapter.

        Args:
            adapter: The adapter to register

        Raises:
            ValueError: If an adapter for this protocol is already registered
        """
        protocol = adapter.protocol_name

        if protocol in self._adapters:
            raise ValueError(f"Adapter for protocol '{protocol}' is already registered")

        self._adapters[protocol] = adapter
        logger.info(
            "adapter_registered",
            protocol=protocol,
            version=adapter.protocol_version,
            adapter_class=adapter.__class__.__name__,
        )

    def unregister(self, protocol: str) -> None:
        """
        Unregister a protocol adapter.

        Args:
            protocol: The protocol name to unregister

        Raises:
            KeyError: If no adapter is registered for this protocol
        """
        if protocol not in self._adapters:
            raise KeyError(f"No adapter registered for protocol '{protocol}'")

        adapter = self._adapters.pop(protocol)
        logger.info(
            "adapter_unregistered", protocol=protocol, adapter_class=adapter.__class__.__name__
        )

    def get(self, protocol: str) -> ProtocolAdapter | None:
        """
        Get the adapter for a specific protocol.

        Args:
            protocol: The protocol name

        Returns:
            The adapter instance, or None if not found
        """
        return self._adapters.get(protocol)

    def list_protocols(self) -> list[str]:
        """
        List all registered protocol names.

        Returns:
            List of protocol names
        """
        return list(self._adapters.keys())

    def supports(self, protocol: str) -> bool:
        """
        Check if a protocol is supported.

        Args:
            protocol: The protocol name to check

        Returns:
            True if the protocol is supported, False otherwise
        """
        return protocol in self._adapters

    def initialize(self) -> None:
        """
        Initialize the registry with built-in adapters.

        Registers MCP, HTTP, gRPC, and other adapters based on configuration.
        """
        if self._initialized:
            logger.warning("adapter_registry_already_initialized")
            return

        config = get_settings()

        # Check if protocol adapters feature is enabled
        if not getattr(config.features, "enable_protocol_adapters", False):
            logger.info(
                "protocol_adapters_disabled",
                message="Protocol adapters feature is disabled. Enable with FEATURE_PROTOCOL_ADAPTERS=true",
            )
            self._initialized = True
            return

        # Get enabled protocols from config
        enabled_protocols = getattr(config, "protocols", None)
        enabled_list = (
            getattr(enabled_protocols, "enabled_protocols", ["mcp"])
            if enabled_protocols
            else ["mcp"]
        )

        # Register MCP adapter if enabled
        if "mcp" in enabled_list:
            try:
                from sark.adapters.mcp_adapter import MCPAdapter

                mcp_adapter = MCPAdapter()
                self.register(mcp_adapter)
                logger.info("mcp_adapter_registered", protocol="mcp")
            except Exception as e:
                logger.error("mcp_adapter_registration_failed", error=str(e))

        # Register HTTP adapter if enabled
        if "http" in enabled_list:
            try:
                from sark.adapters.http.http_adapter import HTTPAdapter

                http_adapter = HTTPAdapter()
                self.register(http_adapter)
                logger.info("http_adapter_registered", protocol="http")
            except Exception as e:
                logger.error("http_adapter_registration_failed", error=str(e))

        # Register gRPC adapter if enabled
        if "grpc" in enabled_list:
            try:
                from sark.adapters.grpc_adapter import GRPCAdapter

                grpc_adapter = GRPCAdapter()
                self.register(grpc_adapter)
                logger.info("grpc_adapter_registered", protocol="grpc")
            except Exception as e:
                logger.error("grpc_adapter_registration_failed", error=str(e))

        logger.info(
            "adapter_registry_initialized",
            enabled_protocols=enabled_list,
            registered_count=len(self._adapters),
            registered_protocols=list(self._adapters.keys()),
        )

        self._initialized = True

    def get_info(self) -> dict[str, any]:
        """
        Get registry information.

        Returns:
            Dictionary with registry status and adapter information
        """
        return {
            "initialized": self._initialized,
            "adapter_count": len(self._adapters),
            "protocols": [
                {
                    "name": protocol,
                    "version": adapter.protocol_version,
                    "class": adapter.__class__.__name__,
                }
                for protocol, adapter in self._adapters.items()
            ],
        }


# Global registry instance
_registry: AdapterRegistry | None = None


def get_registry() -> AdapterRegistry:
    """
    Get the global adapter registry instance.

    Returns:
        The global AdapterRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = AdapterRegistry()
        _registry.initialize()
    return _registry


def reset_registry() -> None:
    """
    Reset the global registry (useful for testing).
    """
    global _registry
    _registry = None


__all__ = [
    "AdapterRegistry",
    "get_registry",
    "reset_registry",
]
