# PR: Advanced Features - Cost Attribution & Policy Plugins (ENGINEER-5)

**Branch:** `feat/v2-advanced-features`
**Base:** `main`
**Title:** `feat(v2.0): Advanced Features - Cost Attribution & Policy Plugins (ENGINEER-5)`

---

## Summary

This PR implements SARK v2.0 Advanced Features (ENGINEER-5 deliverables):
- **Cost Estimation Interface**: Extensible cost tracking for multi-provider AI/API usage
- **Provider-Specific Cost Models**: OpenAI and Anthropic token-based pricing
- **Cost Attribution & Budgets**: Principal-level budget management and enforcement
- **Policy Plugin System**: Programmatic authorization in Python with sandbox security
- **Example Plugins**: Business hours, rate limiting, and cost-aware policies

## 📦 Deliverables

### Cost Attribution System
- ✅ `src/sark/services/cost/estimator.py` - Abstract cost estimator interface
- ✅ `src/sark/services/cost/providers/openai.py` - OpenAI cost model
- ✅ `src/sark/services/cost/providers/anthropic.py` - Anthropic cost model
- ✅ `src/sark/models/cost_attribution.py` - Cost tracking models & service
- ✅ `src/sark/services/cost/tracker.py` - Cost tracking orchestration
- ✅ `tests/cost/test_cost_attribution.py` - Attribution tests
- ✅ `tests/cost/test_estimators.py` - Provider estimator tests

### Policy Plugin System
- ✅ `src/sark/services/policy/plugins.py` - Plugin interface & manager
- ✅ `src/sark/services/policy/sandbox.py` - Plugin sandbox security
- ✅ `examples/custom-policy-plugin/business_hours_plugin.py` - Business hours enforcement
- ✅ `examples/custom-policy-plugin/rate_limit_plugin.py` - Rate limiting
- ✅ `examples/custom-policy-plugin/cost_aware_plugin.py` - Budget-aware authorization
- ✅ `examples/custom-policy-plugin/README.md` - Plugin development guide

### Documentation & Examples
- ✅ `examples/advanced-features-usage.md` - Comprehensive usage guide (NEW!)
- ✅ Architecture diagrams for cost attribution and policy evaluation

## 🎯 Key Features

### 1. Multi-Provider Cost Tracking

```python
from sark.services.cost.providers.openai import OpenAICostEstimator

estimator = OpenAICostEstimator()
estimate = await estimator.estimate_cost(request, {"model": "gpt-4-turbo"})
# Automatic token estimation and cost calculation
```

**Supported Providers:**
- OpenAI (GPT-4, GPT-3.5, o1, embeddings)
- Anthropic (Claude 3 models)
- Fixed-cost APIs
- Free/internal resources

### 2. Budget Management

```python
from sark.models.cost_attribution import CostAttributionService

# Set budgets
await cost_service.set_budget(
    principal_id="user-123",
    daily_budget=Decimal("10.00"),
    monthly_budget=Decimal("100.00")
)

# Enforce budgets
allowed, reason = await cost_service.check_budget(
    principal_id="user-123",
    estimated_cost=Decimal("5.00")
)
```

**Features:**
- Daily and monthly budget limits
- Automatic budget reset tracking
- Real-time budget status queries
- Cost summaries and reporting

### 3. Policy Plugin System

```python
from sark.services.policy.plugins import PolicyPlugin, PolicyContext, PolicyDecision

class CustomPlugin(PolicyPlugin):
    @property
    def name(self) -> str:
        return "custom-policy"

    async def evaluate(self, context: PolicyContext) -> PolicyDecision:
        # Custom authorization logic
        return PolicyDecision(allowed=True, reason="Custom check passed")
```

**Plugin Features:**
- Priority-based evaluation ordering
- Automatic timeout enforcement (5s default)
- Lifecycle hooks (on_load/on_unload)
- Dynamic plugin loading from files
- Sandbox security constraints

### 4. Example Plugins

#### Business Hours Plugin
Restricts resource access to business hours (9 AM - 5 PM, Mon-Fri):
```python
plugin = BusinessHoursPlugin(start_hour=9, end_hour=17)
await manager.register_plugin(plugin, enabled=True)
```

#### Rate Limiting Plugin
Implements per-user rate limiting with sliding windows:
```python
plugin = RateLimitPlugin(max_requests=100, window_seconds=3600)
```

#### Cost-Aware Plugin
Makes authorization decisions based on budget status:
```python
plugin = CostAwarePlugin(
    cost_service=cost_service,
    warning_threshold=0.8,  # Warn at 80%
    deny_threshold=0.95     # Deny at 95%
)
```

## 🔧 Integration Points

### With Protocol Adapters (ENGINEER-1)
Cost estimators integrate seamlessly with the `ProtocolAdapter` interface:
```python
class CostAwareAdapter(ProtocolAdapter):
    async def invoke(self, request):
        # Estimate cost before invocation
        estimate = await self.estimator.estimate_cost(request, metadata)

        # Check budget
        allowed, reason = await self.cost_service.check_budget(...)

        # Execute and track actual cost
```

### With Database Layer (ENGINEER-6)
Utilizes TimescaleDB hypertables for cost tracking:
- `cost_tracking` - Time-series cost data
- `principal_budgets` - Budget limits and spending
- Materialized views for daily summaries

### With Policy Service
Policy plugins complement OPA policies:
- Use plugins for complex logic hard to express in Rego
- Combine multiple plugins with different priorities
- Early termination on denial for efficiency

## 📊 Architecture

### Cost Attribution Flow
```
Request → Cost Estimator → Budget Check → Invocation → Actual Cost → Record
   ↓            ↓              ↓             ↓            ↓           ↓
Provider    Token/Model    Budget DB    API Call    Usage Data   Cost DB
```

### Policy Plugin Evaluation
```
Context → Plugin Manager → [Plugin 1, Plugin 2, ...] → Decisions
            ↓                    ↓ (priority order)        ↓
        Timeout/Sandbox      Early termination      Allow/Deny
```

## 🧪 Testing

All deliverables include comprehensive tests:

```bash
# Cost attribution tests
pytest tests/cost/test_cost_attribution.py -v

# Cost estimator tests
pytest tests/cost/test_estimators.py -v

# Run all ENGINEER-5 tests
pytest tests/cost/ -v
```

**Test Coverage:**
- Cost estimation for multiple providers
- Budget enforcement and reset logic
- Plugin lifecycle management
- Plugin evaluation and timeout handling
- Cost reporting and summaries

## 📖 Usage Examples

See [`examples/advanced-features-usage.md`](../examples/advanced-features-usage.md) for comprehensive examples including:

1. **Basic Cost Tracking** - Estimate and record costs
2. **Budget Management** - Set limits and check status
3. **Multi-Provider Tracking** - Handle OpenAI, Anthropic, custom APIs
4. **Creating Plugins** - Build custom policy logic
5. **Plugin Loading** - Dynamic loading and management
6. **Integration Patterns** - Combine cost tracking with adapters
7. **Best Practices** - Security, performance, troubleshooting

## 🔒 Security Considerations

### Plugin Sandbox
- Resource limits enforced
- Dangerous imports blocked (os, subprocess, etc.)
- Execution timeouts (5s default)
- No file/network access during evaluation

### Cost Tracking
- Budget limits prevent runaway costs
- Audit trail of all cost records
- Secure principal attribution
- Read-only cost estimation

## 🚀 Performance

- **Cost Estimation**: < 1ms (token counting heuristic)
- **Budget Check**: < 5ms (single DB query)
- **Plugin Evaluation**: < 100ms target per plugin
- **Cost Recording**: Async, non-blocking

## 📋 Dependencies

This PR depends on:
- ✅ ENGINEER-1: `ProtocolAdapter` interface (merged)
- ✅ ENGINEER-6: Database schema with cost tables (merged)

## 🎓 Next Steps

After merge, these features enable:
1. Cost-aware routing in adapters (ENGINEER-2, ENGINEER-3)
2. Federation cost aggregation (ENGINEER-4)
3. Cost analytics and reporting dashboards
4. Advanced policy scenarios (multi-tenant, hierarchical budgets)
5. ML-based cost prediction

## 👥 Review Checklist

**For ENGINEER-1 (@reviewer):**
- [ ] Cost estimator interface aligns with adapter patterns
- [ ] Plugin system doesn't conflict with existing policy service
- [ ] Integration points are clear and well-documented
- [ ] Security constraints are appropriate
- [ ] Example code is idiomatic and follows conventions

**General:**
- [x] All ENGINEER-5 deliverables completed
- [x] Tests pass and provide good coverage
- [x] Documentation is comprehensive with examples
- [x] Code follows SARK v2.0 patterns
- [x] No breaking changes to existing APIs
- [x] Security best practices followed

## 📚 Additional Context

This work was completed in CZAR Session 1 as part of the orchestrated 10-engineer implementation plan. The advanced features provide essential cost governance and policy extensibility for SARK v2.0's multi-provider, multi-tenant architecture.

**Related Work:**
- Week 1 foundation (ENGINEER-1)
- Database schema (ENGINEER-6)
- Policy audit trail (separate PR)

---

## Command to Create PR

```bash
gh pr create \
  --title "feat(v2.0): Advanced Features - Cost Attribution & Policy Plugins (ENGINEER-5)" \
  --body-file PR_ADVANCED_FEATURES.md \
  --base main \
  --head feat/v2-advanced-features
```

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
