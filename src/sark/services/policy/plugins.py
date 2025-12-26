"""
Programmatic policy plugin system for SARK v2.0.

Allows custom policy logic to be implemented in Python instead of (or in addition to) Rego.
Plugins run in a controlled environment with resource limits and security constraints.
"""

from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
import importlib.util
import inspect
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class PolicyContext:
    """
    Context passed to policy plugins during evaluation.

    Contains all information needed to make authorization decisions.
    """

    principal_id: str
    resource_id: str
    capability_id: str
    action: str
    arguments: dict[str, Any]
    environment: dict[str, Any]
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(UTC)


@dataclass
class PolicyDecision:
    """
    Decision returned by a policy plugin.

    Attributes:
        allowed: Whether the action is allowed
        reason: Human-readable reason for the decision
        metadata: Additional metadata (e.g., conditions, obligations)
        plugin_name: Name of plugin that made the decision
    """

    allowed: bool
    reason: str
    metadata: dict[str, Any] = None
    plugin_name: str = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class PolicyPlugin(ABC):
    """
    Abstract base class for policy plugins.

    Custom policy logic should inherit from this class and implement
    the evaluate() method.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Return the plugin name.

        Returns:
            str: Unique plugin identifier
        """
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """
        Return the plugin version.

        Returns:
            str: Semantic version string
        """
        pass

    @property
    def description(self) -> str:
        """
        Return a human-readable description of what this plugin does.

        Returns:
            str: Plugin description
        """
        return ""

    @property
    def priority(self) -> int:
        """
        Return plugin evaluation priority (lower = earlier evaluation).

        Returns:
            int: Priority value (default: 100)
        """
        return 100

    @abstractmethod
    async def evaluate(self, context: PolicyContext) -> PolicyDecision:
        """
        Evaluate the policy for a given context.

        Args:
            context: Policy evaluation context

        Returns:
            Policy decision

        Raises:
            PolicyEvaluationError: If evaluation fails
        """
        pass

    async def on_load(self) -> None:
        """
        Called when plugin is loaded.

        Override to perform initialization (e.g., load config, connect to services).
        """
        pass

    async def on_unload(self) -> None:
        """
        Called when plugin is unloaded.

        Override to perform cleanup (e.g., close connections).
        """
        pass

    def get_metadata(self) -> dict[str, Any]:
        """
        Get plugin metadata.

        Returns:
            Dictionary with plugin information
        """
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "priority": self.priority,
            "class": self.__class__.__name__,
            "module": self.__class__.__module__,
        }


class PolicyPluginManager:
    """
    Manager for policy plugins.

    Handles plugin registration, loading, and evaluation coordination.
    """

    def __init__(self):
        """Initialize plugin manager."""
        self._plugins: dict[str, PolicyPlugin] = {}
        self._enabled_plugins: set[str] = set()

    async def register_plugin(self, plugin: PolicyPlugin, enabled: bool = True) -> None:
        """
        Register a policy plugin.

        Args:
            plugin: Plugin instance
            enabled: Whether to enable the plugin immediately

        Raises:
            ValueError: If plugin with same name already registered
        """
        if plugin.name in self._plugins:
            raise ValueError(f"Plugin '{plugin.name}' is already registered")

        self._plugins[plugin.name] = plugin

        if enabled:
            self._enabled_plugins.add(plugin.name)

        # Call on_load hook
        try:
            await plugin.on_load()
            logger.info(
                "policy_plugin_registered",
                plugin_name=plugin.name,
                version=plugin.version,
                enabled=enabled,
            )
        except Exception as e:
            logger.error("policy_plugin_load_failed", plugin_name=plugin.name, error=str(e))
            # Remove from enabled set if load failed
            self._enabled_plugins.discard(plugin.name)
            raise

    async def unregister_plugin(self, plugin_name: str) -> None:
        """
        Unregister a policy plugin.

        Args:
            plugin_name: Name of plugin to unregister
        """
        plugin = self._plugins.get(plugin_name)
        if not plugin:
            return

        # Call on_unload hook
        try:
            await plugin.on_unload()
        except Exception as e:
            logger.error("policy_plugin_unload_failed", plugin_name=plugin_name, error=str(e))

        # Remove from registry
        del self._plugins[plugin_name]
        self._enabled_plugins.discard(plugin_name)

        logger.info("policy_plugin_unregistered", plugin_name=plugin_name)

    def enable_plugin(self, plugin_name: str) -> None:
        """
        Enable a registered plugin.

        Args:
            plugin_name: Name of plugin to enable

        Raises:
            ValueError: If plugin not registered
        """
        if plugin_name not in self._plugins:
            raise ValueError(f"Plugin '{plugin_name}' is not registered")

        self._enabled_plugins.add(plugin_name)
        logger.info("policy_plugin_enabled", plugin_name=plugin_name)

    def disable_plugin(self, plugin_name: str) -> None:
        """
        Disable a registered plugin.

        Args:
            plugin_name: Name of plugin to disable
        """
        self._enabled_plugins.discard(plugin_name)
        logger.info("policy_plugin_disabled", plugin_name=plugin_name)

    def get_plugin(self, plugin_name: str) -> PolicyPlugin | None:
        """
        Get a registered plugin.

        Args:
            plugin_name: Name of plugin

        Returns:
            Plugin instance or None if not found
        """
        return self._plugins.get(plugin_name)

    def list_plugins(self, enabled_only: bool = False) -> list[dict[str, Any]]:
        """
        List registered plugins.

        Args:
            enabled_only: Only return enabled plugins

        Returns:
            List of plugin metadata dictionaries
        """
        plugins = []
        for name, plugin in self._plugins.items():
            if enabled_only and name not in self._enabled_plugins:
                continue

            metadata = plugin.get_metadata()
            metadata["enabled"] = name in self._enabled_plugins
            plugins.append(metadata)

        return sorted(plugins, key=lambda p: p["priority"])

    async def evaluate_all(
        self, context: PolicyContext, timeout: float = 5.0
    ) -> list[PolicyDecision]:
        """
        Evaluate all enabled plugins for a context.

        Plugins are evaluated in priority order (lower priority first).

        Args:
            context: Policy evaluation context
            timeout: Maximum time in seconds for evaluation

        Returns:
            List of policy decisions from all enabled plugins
        """
        # Get enabled plugins sorted by priority
        enabled_plugins = [
            self._plugins[name] for name in self._enabled_plugins if name in self._plugins
        ]
        enabled_plugins.sort(key=lambda p: p.priority)

        decisions = []

        for plugin in enabled_plugins:
            try:
                # Evaluate with timeout
                decision = await asyncio.wait_for(plugin.evaluate(context), timeout=timeout)
                decision.plugin_name = plugin.name
                decisions.append(decision)

                logger.debug(
                    "policy_plugin_evaluated",
                    plugin_name=plugin.name,
                    allowed=decision.allowed,
                    reason=decision.reason,
                )

                # Early termination if any plugin denies
                if not decision.allowed:
                    logger.info(
                        "policy_plugin_denied",
                        plugin_name=plugin.name,
                        reason=decision.reason,
                        principal_id=context.principal_id,
                        capability_id=context.capability_id,
                    )
                    break

            except TimeoutError:
                logger.error("policy_plugin_timeout", plugin_name=plugin.name, timeout=timeout)
                decisions.append(
                    PolicyDecision(
                        allowed=False,
                        reason=f"Plugin '{plugin.name}' evaluation timed out",
                        plugin_name=plugin.name,
                        metadata={"timeout": True},
                    )
                )
                break

            except Exception as e:
                logger.error(
                    "policy_plugin_evaluation_error", plugin_name=plugin.name, error=str(e)
                )
                decisions.append(
                    PolicyDecision(
                        allowed=False,
                        reason=f"Plugin '{plugin.name}' evaluation failed: {e!s}",
                        plugin_name=plugin.name,
                        metadata={"error": str(e)},
                    )
                )
                break

        return decisions

    async def load_from_file(self, file_path: Path, enabled: bool = True) -> None:
        """
        Load a plugin from a Python file.

        The file should define a class that inherits from PolicyPlugin.

        Args:
            file_path: Path to plugin Python file
            enabled: Whether to enable the plugin immediately

        Raises:
            ValueError: If file doesn't contain a valid plugin
        """
        # Load module from file
        spec = importlib.util.spec_from_file_location(
            f"sark.policy.plugin.{file_path.stem}", file_path
        )
        if not spec or not spec.loader:
            raise ValueError(f"Cannot load module from {file_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find PolicyPlugin subclass
        plugin_class = None
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, PolicyPlugin)
                and obj is not PolicyPlugin
                and obj.__module__ == module.__name__
            ):
                plugin_class = obj
                break

        if not plugin_class:
            raise ValueError(f"No PolicyPlugin subclass found in {file_path}")

        # Instantiate and register
        plugin = plugin_class()
        await self.register_plugin(plugin, enabled=enabled)

        logger.info(
            "policy_plugin_loaded_from_file",
            file_path=str(file_path),
            plugin_name=plugin.name,
            plugin_class=plugin_class.__name__,
        )


class PolicyEvaluationError(Exception):
    """Raised when policy evaluation fails."""

    def __init__(self, message: str, plugin_name: str = None, **kwargs):
        super().__init__(message)
        self.plugin_name = plugin_name
        self.metadata = kwargs


__all__ = [
    "PolicyContext",
    "PolicyDecision",
    "PolicyEvaluationError",
    "PolicyPlugin",
    "PolicyPluginManager",
]
