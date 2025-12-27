"""Comprehensive tests for policy plugin system."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sark.services.policy.plugins import (
    PolicyContext,
    PolicyDecision,
    PolicyEvaluationError,
    PolicyPlugin,
    PolicyPluginManager,
)


class TestPolicyContext:
    """Test suite for PolicyContext dataclass."""

    def test_context_initialization_full(self):
        """Test PolicyContext initialization with all fields."""
        timestamp = datetime.now(UTC)
        context = PolicyContext(
            principal_id="user-123",
            resource_id="resource-456",
            capability_id="capability-789",
            action="tool:invoke",
            arguments={"arg1": "value1"},
            environment={"env": "production"},
            timestamp=timestamp,
        )

        assert context.principal_id == "user-123"
        assert context.resource_id == "resource-456"
        assert context.capability_id == "capability-789"
        assert context.action == "tool:invoke"
        assert context.arguments == {"arg1": "value1"}
        assert context.environment == {"env": "production"}
        assert context.timestamp == timestamp

    def test_context_initialization_minimal(self):
        """Test PolicyContext initialization with minimal fields."""
        context = PolicyContext(
            principal_id="user-123",
            resource_id="resource-456",
            capability_id="capability-789",
            action="read",
            arguments={},
            environment={},
        )

        assert context.principal_id == "user-123"
        assert context.timestamp is not None
        assert isinstance(context.timestamp, datetime)

    def test_context_timestamp_auto_generated(self):
        """Test that timestamp is auto-generated if not provided."""
        before = datetime.now(UTC)
        context = PolicyContext(
            principal_id="user-123",
            resource_id="resource-456",
            capability_id="capability-789",
            action="write",
            arguments={},
            environment={},
        )
        after = datetime.now(UTC)

        assert before <= context.timestamp <= after


class TestPolicyDecision:
    """Test suite for PolicyDecision dataclass."""

    def test_decision_allow(self):
        """Test PolicyDecision for allow decision."""
        decision = PolicyDecision(
            allowed=True,
            reason="User has required permissions",
            metadata={"source": "rbac"},
            plugin_name="rbac_plugin",
        )

        assert decision.allowed is True
        assert "permissions" in decision.reason
        assert decision.metadata == {"source": "rbac"}
        assert decision.plugin_name == "rbac_plugin"

    def test_decision_deny(self):
        """Test PolicyDecision for deny decision."""
        decision = PolicyDecision(
            allowed=False,
            reason="Insufficient permissions",
        )

        assert decision.allowed is False
        assert "Insufficient" in decision.reason
        assert decision.metadata == {}
        assert decision.plugin_name is None

    def test_decision_metadata_auto_initialized(self):
        """Test that metadata is auto-initialized to empty dict."""
        decision = PolicyDecision(
            allowed=True,
            reason="OK",
        )

        assert decision.metadata == {}
        assert isinstance(decision.metadata, dict)


class TestPolicyPlugin:
    """Test suite for PolicyPlugin abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that PolicyPlugin cannot be instantiated directly."""
        with pytest.raises(TypeError):
            PolicyPlugin()  # type: ignore

    def test_plugin_interface_methods_exist(self):
        """Test that PolicyPlugin has all required abstract methods."""
        abstract_methods = {"name", "version", "evaluate"}
        actual_abstract_methods = {
            method
            for method in dir(PolicyPlugin)
            if getattr(getattr(PolicyPlugin, method, None), "__isabstractmethod__", False)
        }

        assert abstract_methods.issubset(actual_abstract_methods)


class MockPolicyPlugin(PolicyPlugin):
    """Mock policy plugin for testing."""

    def __init__(self, name="mock_plugin", version="1.0.0", priority=100):
        self._name = name
        self._version = version
        self._priority = priority
        self.evaluate_called = False
        self.on_load_called = False
        self.on_unload_called = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def description(self) -> str:
        return "Mock plugin for testing"

    async def evaluate(self, context: PolicyContext) -> PolicyDecision:
        self.evaluate_called = True
        return PolicyDecision(
            allowed=True,
            reason="Mock plugin always allows",
            plugin_name=self.name,
        )

    async def on_load(self) -> None:
        self.on_load_called = True

    async def on_unload(self) -> None:
        self.on_unload_called = True


class FailingPlugin(PolicyPlugin):
    """Plugin that fails during evaluation."""

    @property
    def name(self) -> str:
        return "failing_plugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def evaluate(self, context: PolicyContext) -> PolicyDecision:
        raise RuntimeError("Plugin evaluation failed")


class SlowPlugin(PolicyPlugin):
    """Plugin that takes a long time to evaluate."""

    @property
    def name(self) -> str:
        return "slow_plugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def evaluate(self, context: PolicyContext) -> PolicyDecision:
        await asyncio.sleep(10)  # Sleep longer than timeout
        return PolicyDecision(allowed=True, reason="Slow evaluation")


class DenyPlugin(PolicyPlugin):
    """Plugin that always denies."""

    @property
    def name(self) -> str:
        return "deny_plugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def evaluate(self, context: PolicyContext) -> PolicyDecision:
        return PolicyDecision(
            allowed=False,
            reason="Access denied by policy",
            plugin_name=self.name,
        )


class TestPolicyPluginManager:
    """Test suite for PolicyPluginManager class."""

    @pytest.fixture
    def manager(self):
        """Create a fresh plugin manager instance."""
        return PolicyPluginManager()

    @pytest.fixture
    def sample_context(self):
        """Sample policy context for testing."""
        return PolicyContext(
            principal_id="user-123",
            resource_id="resource-456",
            capability_id="capability-789",
            action="tool:invoke",
            arguments={},
            environment={},
        )

    # ===== Registration Tests =====

    @pytest.mark.asyncio
    async def test_register_plugin(self, manager):
        """Test registering a plugin."""
        plugin = MockPolicyPlugin()
        await manager.register_plugin(plugin)

        assert plugin.name in manager._plugins
        assert plugin.name in manager._enabled_plugins
        assert plugin.on_load_called is True

    @pytest.mark.asyncio
    async def test_register_plugin_disabled(self, manager):
        """Test registering a plugin in disabled state."""
        plugin = MockPolicyPlugin()
        await manager.register_plugin(plugin, enabled=False)

        assert plugin.name in manager._plugins
        assert plugin.name not in manager._enabled_plugins

    @pytest.mark.asyncio
    async def test_register_duplicate_plugin_raises(self, manager):
        """Test that registering duplicate plugin raises ValueError."""
        plugin1 = MockPolicyPlugin(name="test_plugin")
        plugin2 = MockPolicyPlugin(name="test_plugin")

        await manager.register_plugin(plugin1)

        with pytest.raises(ValueError) as exc_info:
            await manager.register_plugin(plugin2)

        assert "already registered" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_register_plugin_load_failure(self, manager):
        """Test that plugin registration handles on_load failure."""
        plugin = MockPolicyPlugin()

        # Make on_load raise an exception
        async def failing_on_load():
            raise RuntimeError("Load failed")

        plugin.on_load = failing_on_load

        with pytest.raises(RuntimeError):
            await manager.register_plugin(plugin)

        # Plugin should not be enabled after failed load
        assert plugin.name not in manager._enabled_plugins

    # ===== Unregistration Tests =====

    @pytest.mark.asyncio
    async def test_unregister_plugin(self, manager):
        """Test unregistering a plugin."""
        plugin = MockPolicyPlugin()
        await manager.register_plugin(plugin)

        await manager.unregister_plugin(plugin.name)

        assert plugin.name not in manager._plugins
        assert plugin.name not in manager._enabled_plugins
        assert plugin.on_unload_called is True

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_plugin(self, manager):
        """Test unregistering nonexistent plugin does nothing."""
        await manager.unregister_plugin("nonexistent")
        # Should not raise an exception

    @pytest.mark.asyncio
    async def test_unregister_plugin_unload_failure(self, manager):
        """Test that unregister handles on_unload failure gracefully."""
        plugin = MockPolicyPlugin()
        await manager.register_plugin(plugin)

        # Make on_unload raise an exception
        async def failing_on_unload():
            raise RuntimeError("Unload failed")

        plugin.on_unload = failing_on_unload

        # Should not raise, just log
        await manager.unregister_plugin(plugin.name)

        # Plugin should still be removed despite unload failure
        assert plugin.name not in manager._plugins

    # ===== Enable/Disable Tests =====

    def test_enable_plugin(self, manager):
        """Test enabling a registered plugin."""
        plugin = MockPolicyPlugin()
        asyncio.run(manager.register_plugin(plugin, enabled=False))

        manager.enable_plugin(plugin.name)

        assert plugin.name in manager._enabled_plugins

    def test_enable_nonexistent_plugin_raises(self, manager):
        """Test enabling nonexistent plugin raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            manager.enable_plugin("nonexistent")

        assert "not registered" in str(exc_info.value)

    def test_disable_plugin(self, manager):
        """Test disabling a registered plugin."""
        plugin = MockPolicyPlugin()
        asyncio.run(manager.register_plugin(plugin))

        manager.disable_plugin(plugin.name)

        assert plugin.name not in manager._enabled_plugins

    def test_disable_nonexistent_plugin(self, manager):
        """Test disabling nonexistent plugin does nothing."""
        manager.disable_plugin("nonexistent")
        # Should not raise an exception

    # ===== Query Tests =====

    def test_get_plugin(self, manager):
        """Test retrieving a registered plugin."""
        plugin = MockPolicyPlugin()
        asyncio.run(manager.register_plugin(plugin))

        retrieved = manager.get_plugin(plugin.name)

        assert retrieved is plugin

    def test_get_nonexistent_plugin(self, manager):
        """Test retrieving nonexistent plugin returns None."""
        result = manager.get_plugin("nonexistent")
        assert result is None

    def test_list_plugins_empty(self, manager):
        """Test listing plugins when none registered."""
        plugins = manager.list_plugins()
        assert plugins == []

    def test_list_plugins_all(self, manager):
        """Test listing all registered plugins."""
        plugin1 = MockPolicyPlugin(name="plugin1", priority=100)
        plugin2 = MockPolicyPlugin(name="plugin2", priority=50)

        asyncio.run(manager.register_plugin(plugin1))
        asyncio.run(manager.register_plugin(plugin2))

        plugins = manager.list_plugins()

        assert len(plugins) == 2
        # Should be sorted by priority
        assert plugins[0]["name"] == "plugin2"  # Lower priority first
        assert plugins[1]["name"] == "plugin1"

    def test_list_plugins_enabled_only(self, manager):
        """Test listing only enabled plugins."""
        plugin1 = MockPolicyPlugin(name="plugin1")
        plugin2 = MockPolicyPlugin(name="plugin2")

        asyncio.run(manager.register_plugin(plugin1, enabled=True))
        asyncio.run(manager.register_plugin(plugin2, enabled=False))

        plugins = manager.list_plugins(enabled_only=True)

        assert len(plugins) == 1
        assert plugins[0]["name"] == "plugin1"

    def test_list_plugins_metadata(self, manager):
        """Test that plugin metadata is correctly returned."""
        plugin = MockPolicyPlugin(name="test", version="2.0.0", priority=75)
        asyncio.run(manager.register_plugin(plugin))

        plugins = manager.list_plugins()

        assert len(plugins) == 1
        metadata = plugins[0]
        assert metadata["name"] == "test"
        assert metadata["version"] == "2.0.0"
        assert metadata["priority"] == 75
        assert metadata["description"] == "Mock plugin for testing"
        assert metadata["enabled"] is True

    # ===== Evaluation Tests =====

    @pytest.mark.asyncio
    async def test_evaluate_all_single_plugin(self, manager, sample_context):
        """Test evaluating with a single plugin."""
        plugin = MockPolicyPlugin()
        await manager.register_plugin(plugin)

        decisions = await manager.evaluate_all(sample_context)

        assert len(decisions) == 1
        assert decisions[0].allowed is True
        assert decisions[0].plugin_name == plugin.name
        assert plugin.evaluate_called is True

    @pytest.mark.asyncio
    async def test_evaluate_all_multiple_plugins(self, manager, sample_context):
        """Test evaluating with multiple plugins in priority order."""
        plugin1 = MockPolicyPlugin(name="plugin1", priority=100)
        plugin2 = MockPolicyPlugin(name="plugin2", priority=50)
        plugin3 = MockPolicyPlugin(name="plugin3", priority=75)

        await manager.register_plugin(plugin1)
        await manager.register_plugin(plugin2)
        await manager.register_plugin(plugin3)

        decisions = await manager.evaluate_all(sample_context)

        assert len(decisions) == 3
        # Should be evaluated in priority order
        assert decisions[0].plugin_name == "plugin2"  # Priority 50
        assert decisions[1].plugin_name == "plugin3"  # Priority 75
        assert decisions[2].plugin_name == "plugin1"  # Priority 100

    @pytest.mark.asyncio
    async def test_evaluate_all_early_termination_on_deny(self, manager, sample_context):
        """Test that evaluation stops when a plugin denies."""
        plugin1 = MockPolicyPlugin(name="allow1", priority=50)
        plugin2 = DenyPlugin()  # Will deny
        plugin3 = MockPolicyPlugin(name="allow3", priority=150)

        # Manually set priority for DenyPlugin
        plugin2._priority = 100

        await manager.register_plugin(plugin1)
        await manager.register_plugin(plugin2)
        await manager.register_plugin(plugin3)

        decisions = await manager.evaluate_all(sample_context)

        # Should stop after deny plugin
        assert len(decisions) == 2
        assert decisions[0].plugin_name == "allow1"
        assert decisions[1].plugin_name == "deny_plugin"
        assert decisions[1].allowed is False
        # plugin3 should not be evaluated
        assert plugin3.evaluate_called is False

    @pytest.mark.asyncio
    async def test_evaluate_all_disabled_plugins_skipped(self, manager, sample_context):
        """Test that disabled plugins are not evaluated."""
        plugin1 = MockPolicyPlugin(name="enabled")
        plugin2 = MockPolicyPlugin(name="disabled")

        await manager.register_plugin(plugin1, enabled=True)
        await manager.register_plugin(plugin2, enabled=False)

        decisions = await manager.evaluate_all(sample_context)

        assert len(decisions) == 1
        assert decisions[0].plugin_name == "enabled"
        assert plugin2.evaluate_called is False

    @pytest.mark.asyncio
    async def test_evaluate_all_timeout(self, manager, sample_context):
        """Test that slow plugins timeout."""
        plugin = SlowPlugin()
        await manager.register_plugin(plugin)

        decisions = await manager.evaluate_all(sample_context, timeout=0.1)

        assert len(decisions) == 1
        assert decisions[0].allowed is False
        assert "timed out" in decisions[0].reason
        assert decisions[0].metadata.get("timeout") is True

    @pytest.mark.asyncio
    async def test_evaluate_all_plugin_error(self, manager, sample_context):
        """Test that plugin evaluation errors are handled."""
        plugin = FailingPlugin()
        await manager.register_plugin(plugin)

        decisions = await manager.evaluate_all(sample_context)

        assert len(decisions) == 1
        assert decisions[0].allowed is False
        assert "evaluation failed" in decisions[0].reason
        assert "error" in decisions[0].metadata

    @pytest.mark.asyncio
    async def test_evaluate_all_empty_manager(self, manager, sample_context):
        """Test evaluating with no plugins registered."""
        decisions = await manager.evaluate_all(sample_context)

        assert decisions == []


class TestPolicyEvaluationError:
    """Test suite for PolicyEvaluationError exception."""

    def test_error_creation(self):
        """Test creating PolicyEvaluationError."""
        error = PolicyEvaluationError(
            "Evaluation failed",
            plugin_name="test_plugin",
            detail="Additional detail",
        )

        assert str(error) == "Evaluation failed"
        assert error.plugin_name == "test_plugin"
        assert error.metadata == {"detail": "Additional detail"}

    def test_error_without_plugin_name(self):
        """Test creating error without plugin name."""
        error = PolicyEvaluationError("Evaluation failed")

        assert error.plugin_name is None
        assert error.metadata == {}

    def test_error_raises(self):
        """Test that PolicyEvaluationError can be raised and caught."""
        with pytest.raises(PolicyEvaluationError) as exc_info:
            raise PolicyEvaluationError("Test error", plugin_name="test")

        assert exc_info.value.plugin_name == "test"
