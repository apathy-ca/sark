# SARK v2.0 Advanced Features Usage Guide

This guide demonstrates how to use SARK v2.0's advanced features: **Cost Attribution** and **Policy Plugins**.

## Table of Contents

1. [Cost Attribution & Tracking](#cost-attribution--tracking)
2. [Policy Plugins](#policy-plugins)
3. [Integration Examples](#integration-examples)

---

## Cost Attribution & Tracking

SARK v2.0 provides a comprehensive cost tracking system that attributes costs to principals and enforces budget limits.

### Basic Cost Estimation

```python
from decimal import Decimal
from sark.services.cost.estimator import CostEstimator
from sark.services.cost.providers.openai import OpenAICostEstimator
from sark.models.base import InvocationRequest

# Create OpenAI cost estimator
estimator = OpenAICostEstimator()

# Create a request
request = InvocationRequest(
    principal_id="user-123",
    resource_id="openai-gpt4",
    capability_id="chat-completion",
    arguments={
        "messages": [
            {"role": "user", "content": "What is the capital of France?"}
        ],
        "max_tokens": 100
    }
)

# Estimate cost
resource_metadata = {"model": "gpt-4-turbo"}
estimate = await estimator.estimate_cost(request, resource_metadata)

print(f"Estimated cost: ${estimate.estimated_cost:.4f}")
print(f"Input tokens: {estimate.breakdown['input_tokens']}")
print(f"Output tokens: {estimate.breakdown['output_tokens']}")
```

**Output:**
```
Estimated cost: $0.0012
Input tokens: 14
Output tokens: 100
```

### Recording Actual Costs

```python
from sark.models.base import InvocationResult

# After getting response from OpenAI
result = InvocationResult(
    success=True,
    result={"choices": [{"message": {"content": "Paris"}}]},
    metadata={
        "usage": {
            "prompt_tokens": 14,
            "completion_tokens": 5,
            "total_tokens": 19
        }
    }
)

# Extract actual cost
actual_cost = await estimator.record_actual_cost(request, result, resource_metadata)

print(f"Actual cost: ${actual_cost.estimated_cost:.6f}")
print(f"Actual completion tokens: {actual_cost.breakdown['output_tokens']}")
```

**Output:**
```
Actual cost: $0.000290
Actual completion tokens: 5
```

### Cost Attribution Service

The `CostAttributionService` tracks costs per principal and enforces budgets:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sark.models.cost_attribution import CostAttributionService
from decimal import Decimal

# Initialize service (requires database session)
service = CostAttributionService(db_session)

# Set budget for a principal
await service.set_budget(
    principal_id="user-123",
    daily_budget=Decimal("10.00"),    # $10/day
    monthly_budget=Decimal("100.00"),  # $100/month
    currency="USD"
)

# Check budget before operation
allowed, reason = await service.check_budget(
    principal_id="user-123",
    estimated_cost=estimate.estimated_cost
)

if allowed:
    # Execute operation
    # ...

    # Record the cost
    await service.record_cost(
        principal_id="user-123",
        resource_id="openai-gpt4",
        capability_id="chat-completion",
        estimated_cost=estimate.estimated_cost,
        actual_cost=actual_cost.estimated_cost if actual_cost else None,
        metadata={
            "model": "gpt-4-turbo",
            "provider": "openai",
            "breakdown": actual_cost.breakdown if actual_cost else estimate.breakdown
        }
    )
else:
    print(f"Operation denied: {reason}")
```

### Getting Budget Status

```python
# Get current budget status
status = await service.get_budget_status("user-123")

print(f"Daily budget: ${status.daily_budget}")
print(f"Daily spent: ${status.daily_spent}")
print(f"Daily remaining: ${status.daily_remaining}")
print(f"Daily usage: {status.daily_percent_used:.1f}%")
```

**Output:**
```
Daily budget: $10.00
Daily spent: $2.47
Daily remaining: $7.53
Daily usage: 24.7%
```

### Cost Reporting

```python
from datetime import datetime, timedelta

# Get cost summary for a principal
summary = await service.get_cost_summary(
    principal_id="user-123",
    period_start=datetime.now() - timedelta(days=7),
    period_end=datetime.now()
)

print(f"Total cost (7 days): ${summary.total_cost}")
print(f"Number of calls: {summary.record_count}")

# Get cost by resource
resource_summary = await service.get_cost_summary(
    resource_id="openai-gpt4",
    period_start=datetime.now() - timedelta(days=30)
)

print(f"Resource total cost: ${resource_summary.total_cost}")
```

### Provider-Specific Estimators

#### OpenAI Estimator

```python
from sark.services.cost.providers.openai import OpenAICostEstimator

estimator = OpenAICostEstimator()

# Supports all OpenAI models
models = ["gpt-4-turbo", "gpt-3.5-turbo", "text-embedding-3-small"]

for model in models:
    estimate = await estimator.estimate_cost(
        request,
        {"model": model}
    )
    print(f"{model}: ${estimate.estimated_cost:.6f}")
```

#### Anthropic Estimator

```python
from sark.services.cost.providers.anthropic import AnthropicCostEstimator

estimator = AnthropicCostEstimator()

# Claude models
request = InvocationRequest(
    principal_id="user-123",
    resource_id="anthropic-claude",
    capability_id="message",
    arguments={
        "messages": [
            {"role": "user", "content": "Explain quantum computing"}
        ],
        "max_tokens": 1000
    }
)

estimate = await estimator.estimate_cost(
    request,
    {"model": "claude-3-opus-20240229"}
)

print(f"Estimated cost: ${estimate.estimated_cost:.4f}")
```

#### Custom Fixed Cost

```python
from sark.services.cost.estimator import FixedCostEstimator
from decimal import Decimal

# For APIs with flat per-call pricing
estimator = FixedCostEstimator(
    cost_per_call=Decimal("0.05"),  # $0.05 per call
    provider="my-api"
)

estimate = await estimator.estimate_cost(request, {})
print(f"Cost: ${estimate.estimated_cost}")  # Always $0.05
```

---

## Policy Plugins

Policy plugins allow custom authorization logic in Python, complementing or replacing Rego policies.

### Creating a Simple Plugin

```python
from sark.services.policy.plugins import (
    PolicyPlugin,
    PolicyContext,
    PolicyDecision
)

class SimplePlugin(PolicyPlugin):
    @property
    def name(self) -> str:
        return "simple-example"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Example policy plugin"

    async def evaluate(self, context: PolicyContext) -> PolicyDecision:
        # Allow everything for demo user
        if context.principal_id == "demo-user":
            return PolicyDecision(
                allowed=True,
                reason="Demo user has unrestricted access"
            )

        # Deny unknown users
        return PolicyDecision(
            allowed=False,
            reason="Unknown principal"
        )
```

### Using the Plugin Manager

```python
from sark.services.policy.plugins import PolicyPluginManager, PolicyContext

# Create manager
manager = PolicyPluginManager()

# Register plugin
plugin = SimplePlugin()
await manager.register_plugin(plugin, enabled=True)

# Evaluate
context = PolicyContext(
    principal_id="demo-user",
    resource_id="resource-123",
    capability_id="read",
    action="invoke",
    arguments={},
    environment={}
)

decisions = await manager.evaluate_all(context)

for decision in decisions:
    print(f"Plugin: {decision.plugin_name}")
    print(f"Allowed: {decision.allowed}")
    print(f"Reason: {decision.reason}")
```

### Business Hours Plugin

The business hours plugin restricts access to specific time windows:

```python
from examples.custom_policy_plugin.business_hours_plugin import BusinessHoursPlugin

# Configure business hours
plugin = BusinessHoursPlugin(
    start_hour=9,    # 9 AM
    end_hour=17,     # 5 PM
    allowed_days=[0, 1, 2, 3, 4]  # Monday-Friday
)

await manager.register_plugin(plugin, enabled=True)

# Test during business hours
from datetime import datetime

context = PolicyContext(
    principal_id="user-123",
    resource_id="expensive-model",
    capability_id="invoke",
    action="invoke",
    arguments={},
    environment={},
    timestamp=datetime(2024, 12, 18, 14, 0)  # Wednesday 2 PM
)

decisions = await manager.evaluate_all(context)
# Result: allowed=True
```

### Rate Limiting Plugin

```python
from examples.custom_policy_plugin.rate_limit_plugin import RateLimitPlugin

# Limit users to 100 requests per hour
plugin = RateLimitPlugin(
    max_requests=100,
    window_seconds=3600
)

await manager.register_plugin(plugin, enabled=True)

# Each evaluation counts as a request
for i in range(101):
    decisions = await manager.evaluate_all(context)

# 101st request will be denied: "Rate limit exceeded"
```

### Cost-Aware Plugin

The cost-aware plugin makes authorization decisions based on costs and budgets:

```python
from examples.custom_policy_plugin.cost_aware_plugin import CostAwarePlugin

# Initialize with cost service
plugin = CostAwarePlugin(
    cost_service=cost_attribution_service,
    warning_threshold=0.8,  # Warn at 80% budget
    deny_threshold=0.95     # Deny at 95% budget
)

await manager.register_plugin(plugin, enabled=True)

# Plugin will check budget and deny if too close to limit
context = PolicyContext(
    principal_id="user-123",
    resource_id="expensive-model",
    capability_id="invoke",
    action="invoke",
    arguments={},
    environment={
        "estimated_cost": "5.00"  # $5 operation
    }
)

decisions = await manager.evaluate_all(context)
# If user has spent $9 of $10 daily budget, this will be denied
```

### Plugin Priorities

Plugins are evaluated in priority order (lower = earlier):

```python
class HighPriorityPlugin(PolicyPlugin):
    @property
    def priority(self) -> int:
        return 10  # Evaluated first

    # ... rest of implementation

class LowPriorityPlugin(PolicyPlugin):
    @property
    def priority(self) -> int:
        return 100  # Evaluated later

    # ... rest of implementation
```

**Note:** If any plugin returns `allowed=False`, evaluation stops immediately.

### Loading Plugins from Files

```python
from pathlib import Path

# Load plugin from Python file
await manager.load_from_file(
    Path("examples/custom-policy-plugin/business_hours_plugin.py"),
    enabled=True
)

# List all loaded plugins
plugins = manager.list_plugins(enabled_only=True)
for p in plugins:
    print(f"{p['name']} v{p['version']} (priority: {p['priority']})")
```

### Plugin Lifecycle Hooks

```python
class LifecyclePlugin(PolicyPlugin):
    async def on_load(self) -> None:
        """Called when plugin is registered"""
        # Initialize resources
        self.db_connection = await connect_to_db()
        print("Plugin loaded and ready")

    async def on_unload(self) -> None:
        """Called when plugin is unregistered"""
        # Clean up resources
        await self.db_connection.close()
        print("Plugin unloaded")

    async def evaluate(self, context: PolicyContext) -> PolicyDecision:
        # Use initialized resources
        user_data = await self.db_connection.fetch_user(context.principal_id)

        if user_data.is_active:
            return PolicyDecision(allowed=True, reason="Active user")
        else:
            return PolicyDecision(allowed=False, reason="Inactive user")
```

---

## Integration Examples

### Full SARK Gateway Integration

Here's how cost tracking and policy plugins work together in a real SARK gateway:

```python
from sark.gateway import SARKGateway
from sark.services.cost.tracker import CostTracker
from sark.services.policy.plugins import PolicyPluginManager
from examples.custom_policy_plugin.business_hours_plugin import BusinessHoursPlugin
from examples.custom_policy_plugin.cost_aware_plugin import CostAwarePlugin

async def setup_gateway():
    # Initialize gateway
    gateway = SARKGateway()

    # Setup cost tracking
    cost_service = CostAttributionService(gateway.db)
    cost_tracker = CostTracker(cost_service)

    # Setup policy plugins
    policy_manager = PolicyPluginManager()

    # Add business hours restriction
    await policy_manager.register_plugin(
        BusinessHoursPlugin(start_hour=9, end_hour=17),
        enabled=True
    )

    # Add cost-aware authorization
    await policy_manager.register_plugin(
        CostAwarePlugin(cost_service=cost_service),
        enabled=True
    )

    # Register with gateway
    gateway.policy_manager = policy_manager
    gateway.cost_tracker = cost_tracker

    return gateway

# Use gateway
gateway = await setup_gateway()

# Invoke a capability
result = await gateway.invoke(
    principal_id="user-123",
    resource_id="openai-gpt4",
    capability_id="chat-completion",
    arguments={
        "messages": [{"role": "user", "content": "Hello!"}]
    }
)

# Cost is automatically tracked
# Policies are automatically evaluated
```

### Custom Integration with Adapters

```python
from sark.adapters.base import ProtocolAdapter
from sark.services.cost.providers.openai import OpenAICostEstimator

class CostAwareAdapter(ProtocolAdapter):
    def __init__(self, cost_service: CostAttributionService):
        super().__init__()
        self.cost_service = cost_service
        self.estimator = OpenAICostEstimator()

    async def invoke(self, request: InvocationRequest) -> InvocationResult:
        # Estimate cost before invocation
        estimate = await self.estimator.estimate_cost(
            request,
            self.get_resource_metadata(request.resource_id)
        )

        # Check budget
        allowed, reason = await self.cost_service.check_budget(
            request.principal_id,
            estimate.estimated_cost
        )

        if not allowed:
            return InvocationResult(
                success=False,
                error=f"Budget exceeded: {reason}"
            )

        # Execute actual invocation
        result = await super().invoke(request)

        # Record actual cost
        actual_cost = await self.estimator.record_actual_cost(
            request, result, self.get_resource_metadata(request.resource_id)
        )

        await self.cost_service.record_cost(
            principal_id=request.principal_id,
            resource_id=request.resource_id,
            capability_id=request.capability_id,
            estimated_cost=estimate.estimated_cost,
            actual_cost=actual_cost.estimated_cost if actual_cost else None,
            metadata={
                "provider": self.estimator.provider_name,
                "breakdown": actual_cost.breakdown if actual_cost else estimate.breakdown
            }
        )

        return result
```

### Multi-Provider Cost Tracking

```python
from sark.services.cost.providers.openai import OpenAICostEstimator
from sark.services.cost.providers.anthropic import AnthropicCostEstimator

class MultiProviderCostTracker:
    def __init__(self, cost_service: CostAttributionService):
        self.cost_service = cost_service
        self.estimators = {
            "openai": OpenAICostEstimator(),
            "anthropic": AnthropicCostEstimator()
        }

    async def track_invocation(
        self,
        request: InvocationRequest,
        result: InvocationResult,
        provider: str,
        resource_metadata: dict
    ):
        estimator = self.estimators.get(provider)
        if not estimator:
            return  # Unknown provider

        # Get estimate
        estimate = await estimator.estimate_cost(request, resource_metadata)

        # Get actual cost if available
        actual_cost = await estimator.record_actual_cost(
            request, result, resource_metadata
        )

        # Record
        await self.cost_service.record_cost(
            principal_id=request.principal_id,
            resource_id=request.resource_id,
            capability_id=request.capability_id,
            estimated_cost=estimate.estimated_cost,
            actual_cost=actual_cost.estimated_cost if actual_cost else None,
            metadata={
                "provider": provider,
                "model": resource_metadata.get("model"),
                "breakdown": actual_cost.breakdown if actual_cost else estimate.breakdown
            }
        )
```

---

## Best Practices

### Cost Tracking

1. **Always check budgets before expensive operations**
2. **Record both estimated and actual costs** when available
3. **Set reasonable budget limits** to prevent runaway costs
4. **Monitor budget status regularly** and alert users at thresholds
5. **Use provider-specific estimators** for accuracy

### Policy Plugins

1. **Keep plugins simple and fast** (< 100ms evaluation time)
2. **Use priority ordering** to fail fast on common denials
3. **Return clear, actionable denial reasons**
4. **Handle errors gracefully** in plugin code
5. **Test plugins thoroughly** before production use
6. **Avoid external I/O** in plugin evaluation when possible

### Security

1. **Validate plugin code** before loading
2. **Use sandbox mode** for untrusted plugins
3. **Monitor plugin performance** and set timeouts
4. **Audit policy decisions** for compliance
5. **Rotate cost data** to manage database growth

---

## Troubleshooting

### Cost Estimation Issues

**Problem:** "Missing 'model' in resource metadata"

**Solution:** Ensure resource metadata includes the model name:
```python
resource_metadata = {"model": "gpt-4-turbo"}
```

**Problem:** Estimated costs seem too high/low

**Solution:** Check pricing table is up to date. OpenAI/Anthropic pricing changes periodically.

### Plugin Issues

**Problem:** Plugin timeout errors

**Solution:** Reduce plugin complexity or increase timeout:
```python
decisions = await manager.evaluate_all(context, timeout=10.0)
```

**Problem:** Plugin not being evaluated

**Solution:** Check plugin is enabled:
```python
manager.enable_plugin("plugin-name")
```

### Budget Issues

**Problem:** Budget not resetting daily/monthly

**Solution:** Check system clock and database timestamp handling. Budget resets are timezone-aware.

---

## Additional Resources

- [SARK v2.0 Implementation Plan](../../docs/v2.0/SARK_v2.0_ORCHESTRATED_IMPLEMENTATION_PLAN.md)
- [Cost Estimator API Reference](../../docs/api/v2/cost_estimator.md)
- [Policy Plugin API Reference](../../docs/api/v2/policy_plugins.md)
- [Example Plugins](../../examples/custom-policy-plugin/)
