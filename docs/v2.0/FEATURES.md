# SARK v2.0: Feature Overview

**Version:** 2.0.0
**Target Release:** Q2 2026
**Status:** Planning document

---

## Executive Summary

SARK v2.0 transforms from an MCP-specific governance system into the **canonical reference implementation of GRID Protocol v1.0** - a universal governance protocol for any machine-to-machine interaction.

---

## Major Features

### 1. Protocol Abstraction Layer

**What:** Support any protocol, not just MCP

**How:** Pluggable adapter architecture

**Protocols Supported:**
- ✅ MCP (Model Context Protocol)
- ✅ HTTP/REST APIs
- ✅ gRPC Services
- ⏳ OpenAI Functions (planned)
- ⏳ Anthropic Tools (planned)
- ⏳ Custom protocols (via adapter SDK)

**Benefits:**
- Govern all your machine-to-machine interactions in one place
- Consistent policies across different protocols
- Single audit trail for all access
- Easy to add new protocols

**Example:**
```python
# Register an MCP server
await sark.register_resource(
    protocol="mcp",
    config={"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem"]}
)

# Register a REST API
await sark.register_resource(
    protocol="http",
    config={"base_url": "https://api.example.com", "openapi_spec": "..."}
)

# Register a gRPC service
await sark.register_resource(
    protocol="grpc",
    config={"host": "localhost:50051", "proto_file": "/path/to/service.proto"}
)

# Same policies govern all of them!
```

---

### 2. Cross-Organization Federation

**What:** Multiple SARK instances collaborate on governance

**How:** mTLS-secured federation protocol

**Use Cases:**
- Partner organizations sharing resources
- Multi-tenant SaaS platforms
- Distributed teams across organizations
- Supply chain governance

**Benefits:**
- Each org controls their own policies
- Cross-org access is audited by both sides
- No central authority required
- Trust is explicit and revocable

**Example:**
```
Company A's SARK ←→ Company B's SARK

Alice@CompanyA wants to access Database@CompanyB:
1. CompanyA's SARK asks CompanyB's SARK: "Can Alice access Database?"
2. CompanyB evaluates policy: "Yes, if Alice is a developer"
3. Both companies audit the access
4. Complete audit trail: Alice@CompanyA → Database@CompanyB
```

---

### 3. Cost Attribution System

**What:** Track and enforce resource costs

**How:** Pluggable cost estimators + policy integration

**Features:**
- Estimate cost before execution
- Track actual costs in audit logs
- Budget enforcement via policies
- Cost-based rate limiting
- Chargeback reporting

**Benefits:**
- Prevent runaway costs
- Fair resource allocation
- Budget compliance
- Cost visibility

**Example:**
```rego
# Policy: Deny if estimated cost exceeds budget
deny if {
    estimated_cost := cost.estimate(input.capability, input.arguments)
    principal_budget := data.budgets[input.principal.id]
    principal_spent := data.costs.total(input.principal.id, "month")
    
    principal_spent + estimated_cost > principal_budget
}
```

---

### 4. Programmatic Policies

**What:** Custom policy logic beyond Rego

**How:** Sandboxed policy plugins

**Use Cases:**
- ML-based anomaly detection
- Complex business logic
- External system integration
- Real-time risk scoring

**Benefits:**
- Extend beyond declarative policies
- Integrate with existing systems
- Custom decision logic
- Gradual rollout of ML models

**Example:**
```python
class MLAnomalyDetectionPolicy(PolicyPlugin):
    async def evaluate(self, request: PolicyRequest) -> PolicyDecision:
        # Load ML model
        model = await self.load_model("anomaly_detector_v2")
        
        # Extract features
        features = self.extract_features(request)
        
        # Predict
        anomaly_score = model.predict(features)
        
        if anomaly_score > 0.8:
            return PolicyDecision(
                allow=False,
                reason=f"Anomaly detected (score: {anomaly_score})"
            )
        
        return PolicyDecision(allow=True)
```

---

### 5. Enhanced API (v2)

**What:** New API endpoints for v2.0 features

**Endpoints:**
```
# Resources (protocol-agnostic)
POST   /api/v2/resources
GET    /api/v2/resources
GET    /api/v2/resources/{id}
DELETE /api/v2/resources/{id}

# Adapters
GET    /api/v2/adapters
GET    /api/v2/adapters/{protocol}

# Federation
GET    /api/v2/federation/info
POST   /api/v2/federation/authorize
POST   /api/v2/federation/audit/query

# Cost Attribution
POST   /api/v2/cost/estimate
GET    /api/v2/cost/report

# Backward compatibility
POST   /api/v1/servers  → redirects to /api/v2/resources
```

---

### 6. Improved Performance

**Targets:**
- Policy evaluation: <5ms (P95) - maintained from v1.x
- Throughput: >10,000 req/s (2x improvement)
- Adapter overhead: <1ms
- Federation latency: <50ms (P95)

**Optimizations:**
- Adapter result caching
- Federation response caching
- Improved policy cache warming
- Connection pooling for adapters

---

### 7. Developer Experience

**Features:**
- Adapter SDK for custom protocols
- Policy testing framework
- Federation testing tools
- Comprehensive examples
- Interactive API documentation

**Example: Custom Adapter**
```python
from sark.adapters import ProtocolAdapter

class MyProtocolAdapter(ProtocolAdapter):
    @property
    def protocol_name(self) -> str:
        return "myprotocol"
    
    async def discover_resources(self, config):
        # Your discovery logic
        pass
    
    async def invoke(self, request):
        # Your invocation logic
        pass

# Register it
sark.adapters.register(MyProtocolAdapter())
```

---

## Migration from v1.x

**Good News:** Since there are no production users yet, v2.0 will be a clean slate!

**For Development/Testing:**
- v1.x MCP-specific code becomes the MCP adapter
- Existing policies mostly work (minor updates)
- Database schema evolves (migration scripts provided)
- Configuration format changes (documented)

---

## Timeline

```
Nov 2025: v1.0 released
Dec 2025 - Jan 2026: v1.1 Gateway integration
Feb 2026: v2.0 development begins
  ├─ Weeks 1-4: Protocol abstraction
  ├─ Weeks 5-8: Additional adapters
  ├─ Weeks 9-12: Federation
  ├─ Weeks 13-16: Cost attribution
  ├─ Weeks 17-18: Programmatic policies
  └─ Weeks 19-20: Integration & docs
Jun 2026: v2.0 beta
Jul 2026: v2.0 release
```

---

## Success Metrics

### Technical
- ✅ 100% GRID v1.0 compliance
- ✅ 4+ protocol adapters working
- ✅ Federation between 2+ nodes
- ✅ <5ms policy evaluation (maintained)
- ✅ >10,000 req/s throughput
- ✅ 90%+ test coverage

### Adoption
- ✅ Reference implementation for GRID
- ✅ Community adapter contributions
- ✅ Production deployments
- ✅ Positive community feedback

---

## Beyond v2.0

### v2.1 (Q3 2026)
- Additional protocol adapters
- Enhanced federation features
- Advanced cost models
- Performance improvements

### v2.2 (Q4 2026)
- Multi-tenancy support
- GraphQL API
- Mobile app for monitoring
- Advanced ML policies

### v3.0 (2027)
- SaaS offering
- Marketplace for adapters
- Advanced analytics
- Enterprise features

---

**Document Version:** 1.0
**Created:** November 28, 2025
**Status:** Planning document for v2.0