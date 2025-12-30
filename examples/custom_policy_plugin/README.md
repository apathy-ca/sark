# Custom Policy Plugin Example

This directory contains example custom policy plugins for SARK v2.0's programmatic policy system.

## Overview

Policy plugins allow you to implement custom authorization logic in Python instead of (or in addition to) Rego policies. This provides flexibility for complex authorization scenarios that are difficult to express in declarative policy languages.

## Plugin Structure

A policy plugin must:

1. Inherit from `PolicyPlugin` base class
2. Implement the `name` and `version` properties
3. Implement the `evaluate()` method
4. Optionally implement `on_load()` and `on_unload()` lifecycle hooks

## Examples

This directory contains the following example plugins:

### 1. `business_hours_plugin.py`

A simple plugin that restricts resource access to business hours (9 AM - 5 PM, Monday-Friday).

**Use case:** Prevent expensive AI model usage outside of business hours to control costs.

### 2. `rate_limit_plugin.py`

A plugin that implements per-user rate limiting using a sliding window algorithm.

**Use case:** Prevent abuse by limiting how many requests a user can make in a time period.

### 3. `cost_aware_plugin.py`

A plugin that considers estimated costs when making authorization decisions.

**Use case:** Deny high-cost operations when user is close to budget limits.

## Loading Plugins

### Programmatic Loading

```python
from sark.services.policy.plugins import PolicyPluginManager
from examples.custom_policy_plugin.business_hours_plugin import BusinessHoursPlugin

# Create plugin manager
manager = PolicyPluginManager()

# Register plugin
plugin = BusinessHoursPlugin()
await manager.register_plugin(plugin, enabled=True)

# Evaluate policy
from sark.services.policy.plugins import PolicyContext

context = PolicyContext(
    principal_id="user-123",
    resource_id="resource-456",
    capability_id="capability-789",
    action="invoke",
    arguments={},
    environment={},
)

decisions = await manager.evaluate_all(context)
```

### Loading from File

```python
from pathlib import Path
from sark.services.policy.plugins import PolicyPluginManager

manager = PolicyPluginManager()

# Load plugin from file
await manager.load_from_file(
    Path("examples/custom-policy-plugin/business_hours_plugin.py"),
    enabled=True
)
```

## Security Considerations

Policy plugins run with certain security constraints:

1. **Resource Limits**: Memory and CPU time limits are enforced
2. **Import Restrictions**: Dangerous modules (os, subprocess, etc.) are blocked
3. **Execution Timeout**: Plugins must complete evaluation within 5 seconds
4. **Sandboxing**: Plugins run in a controlled environment

### Safe Practices

- ✅ Use only allowed standard library modules (datetime, collections, etc.)
- ✅ Keep evaluation logic simple and fast
- ✅ Handle exceptions gracefully
- ✅ Return clear denial reasons

### Unsafe Practices

- ❌ Don't import os, subprocess, or other system modules
- ❌ Don't use eval() or exec()
- ❌ Don't open files or make network requests
- ❌ Don't use infinite loops or recursive logic

## Testing Your Plugin

```python
import pytest
from your_plugin import YourPlugin
from sark.services.policy.plugins import PolicyContext

@pytest.mark.asyncio
async def test_your_plugin():
    plugin = YourPlugin()

    context = PolicyContext(
        principal_id="test-user",
        resource_id="test-resource",
        capability_id="test-capability",
        action="invoke",
        arguments={},
        environment={},
    )

    decision = await plugin.evaluate(context)

    assert decision.allowed is True
    assert decision.reason is not None
```

## Contributing

When creating custom plugins:

1. Follow the plugin interface exactly
2. Add comprehensive error handling
3. Write clear denial reasons
4. Include unit tests
5. Document configuration options
6. Keep dependencies minimal

## License

These examples are provided under the same license as SARK.
