# SARK v2.0 Roadmap: GRID Reference Implementation

**Status:** Planning document for SARK v2.0 → GRID v1.0 alignment
**Target Release:** 2026 Q1-Q2
**Scope:** Transform SARK from MCP-specific to universal GRID reference implementation

---

## Executive Summary

SARK v1.0 is a phenomenal enterprise MCP governance system (85% GRID v0.1 compliant). SARK v2.0 should transform it into the authoritative **reference implementation of GRID v1.0** by:

1. **Abstracting protocols** – Move from MCP-specific to adapter-based architecture
2. **Adding federation** – Enable cross-org governance
3. **Expanding capabilities** – Cost attribution, programmatic policies, verification workflows

**Decision Point:** Should we do SARK v1.1 or jump to v2.0?

**Recommendation:** **Go directly to v2.0** because:
- Protocol abstraction is architectural (can't be done incrementally)
- GRID v1.0 will define federation (not in v0.1)
- v1.1 would be a minor iteration, v2.0 is a major evolution
- Major version bump signals "reference implementation for universal GRID"

---

## SARK v1.1 vs v2.0: Decision Matrix

| Aspect | v1.1 (Planned) | v2.0 (Proposed) |
|--------|---|---|
| **Timeline** | 6-8 weeks | 16-20 weeks |
| **Scope** | Bug fixes + quick wins | Architectural transformation |
| **MCP Focus** | ✅ Primary | ⚠️ One of many protocols |
| **Federation** | ❌ No | ✅ Yes |
| **Protocol Adapters** | ❌ No | ✅ Yes (MCP, HTTP, gRPC, OpenAI) |
| **Multi-protocol** | ❌ No | ✅ Yes |
| **Cost Attribution** | ❌ No | ✅ Yes |
| **GRID Alignment** | 85% v0.1 | 100% v1.0 |
| **Breaking Changes** | ❌ None | ✅ Some (adapters) |
| **Use Case** | MCP excellence | Universal governance |

---

## Proposed Path: SARK v1.1 → v2.0

### Phase 1: SARK v1.1 (Q4 2025 - Early Q1 2026) - 6-8 weeks
**Goal:** Polish and quick wins while planning v2.0

**Scope (Small, Focused):**
- ✅ Standardize rate limit headers (RFC-compliant)
- ✅ Formalize delegation tracking (audit fields)
- ✅ Add resource provider verification workflow
- ✅ MFA support (infrastructure ready)
- ✅ Documentation updates linking to GRID
- ✅ Bug fixes and stability improvements

**Effort:** ~4-6 weeks (2-3 person-months)

**Output:**
- SARK v1.1: Final MCP-focused version
- Clear link to GRID specification
- Foundation for v2.0 planning
- Community feedback collection

### Phase 2: SARK v2.0 (Q1-Q2 2026) - 16-20 weeks
**Goal:** Universal GRID v1.0 reference implementation

**Scope (Major Refactor):**

#### Sprint 1-2: Protocol Abstraction (Weeks 1-4)
- Design `ProtocolAdapter` interface
- Extract `MCPAdapter` from core
- Create generic `Resource` model (replace `MCPServer`)
- Refactor API endpoints to use adapters
- Unit tests for adapter interface

**Files affected:** ~15-20 files, 3,000+ lines changed
**Effort:** 3-4 person-weeks

#### Sprint 3-4: Additional Adapters (Weeks 5-8)
- Implement `HTTPAdapter` (REST APIs)
- Implement `gRPCAdapter` (gRPC services)
- Add adapter registry and discovery
- Integration tests for each adapter
- Documentation for adapter development

**Files affected:** ~8-12 new files
**Effort:** 3-4 person-weeks

#### Sprint 5-6: Federation (Weeks 9-12)
- Design federation protocol
- Implement node discovery (DNS/mDNS)
- Cross-org policy evaluation
- Federation trust establishment (mTLS)
- Audit trail correlation across orgs
- Federation integration tests

**Files affected:** ~10-15 new files, 2,000+ lines
**Effort:** 4-5 person-weeks

#### Sprint 7-8: Cost Attribution (Weeks 13-16)
- Design cost model abstraction
- Implement cost estimation interface
- Integrate with policies (cost-based decisions)
- Cost tracking in audit logs
- Example cost attributors (simple, ML-based, etc.)

**Files affected:** ~8-10 new files
**Effort:** 2-3 person-weeks

#### Sprint 9: Programmatic Policies (Weeks 17-18)
- Policy plugin interface
- Custom policy execution environment
- Sandboxing and security
- Policy testing framework

**Files affected:** ~5-8 new files
**Effort:** 2 person-weeks

#### Sprint 10: Integration & Documentation (Weeks 19-20)
- Integration testing (all adapters + federation)
- Migration guide from v1.x
- Reference adapter implementations
- GRID v1.0 alignment verification
- Documentation updates

**Effort:** 2 person-weeks

**Total v2.0 Effort:** 20 person-weeks (~5 person-months for 1 person, ~2.5 months with 2-3 people)

---

## Architecture Changes: v1.0 → v2.0

### Before (v1.0 - MCP-Centric)

```
FastAPI Endpoints
    ↓
MCP-Specific Logic
    ├─ MCPServer model
    ├─ MCPTool registry
    ├─ MCP policy concepts
    └─ MCP-specific discovery
    ↓
OPA Policy Engine
    ↓
TimescaleDB Audit
```

### After (v2.0 - Universal GRID)

```
FastAPI Endpoints
    ↓
Protocol Adapters (Interface)
├─ MCPAdapter ──→ MCP Servers
├─ HTTPAdapter ──→ REST APIs
├─ gRPCAdapter ──→ gRPC Services
├─ OpenAIAdapter ──→ OpenAI Functions
└─ CustomAdapter ──→ Your Protocol
    ↓
Adapter Registry & Discovery
    ↓
Generic Resource Model
    ├─ Resource (abstract)
    ├─ Principal (universal)
    ├─ Action (universal)
    └─ Policy (protocol-agnostic)
    ↓
Policy Evaluation (OPA/Cedar/Custom)
    ↓
Federation Layer
    ├─ Node discovery
    ├─ Cross-org policy evaluation
    └─ Audit correlation
    ↓
Cost Attribution
    ├─ Cost estimation
    ├─ Budget tracking
    └─ Cost-based policies
    ↓
TimescaleDB Audit
```

---

## Code Changes by Component

### 1. Models Layer
**Current (v1.0):**
```python
# src/sark/models/mcp_server.py
class MCPServer(Base): ...
class MCPTool(Base): ...
class TransportType(Enum): ...
```

**Future (v2.0):**
```python
# src/sark/models/resource.py
class Resource(Base): ...  # Generic, replaces MCPServer
class Capability(Base): ...  # Generic, replaces MCPTool
class ProtocolType(Enum): ...  # Extensible

# src/sark/models/mcp.py (MCP-specific extensions)
class MCPResource(Resource): ...
class MCPCapability(Capability): ...
```

**Impact:** Breaking change (migration guide required)

### 2. Adapter Architecture
**New files (v2.0):**
```
src/sark/adapters/
├─ __init__.py
├─ base.py              # ProtocolAdapter ABC
├─ interface.py         # Type definitions
├─ mcp_adapter.py       # MCP (extracted from core)
├─ http_adapter.py      # HTTP/REST (new)
├─ grpc_adapter.py      # gRPC (new)
├─ openai_adapter.py    # OpenAI (new)
├─ registry.py          # Adapter discovery
└─ tests/
    ├─ test_base.py
    ├─ test_mcp_adapter.py
    ├─ test_http_adapter.py
    └─ test_grpc_adapter.py
```

### 3. API Changes
**v1.0 (MCP-centric):**
```
POST /api/v1/servers          # Register MCP server
GET /api/v1/tools             # List tools
POST /api/v1/policy/evaluate  # Evaluate policy
```

**v2.0 (Universal):**
```
POST /api/v1/resources        # Register any resource
GET /api/v1/resources         # List resources
GET /api/v1/adapters          # List available adapters
POST /api/v1/policy/evaluate  # Same, works with any resource

# Backward compatibility (v1.0 endpoints still work)
POST /api/v1/servers          # → /api/v1/resources (redirects)
```

### 4. Configuration
**v1.0:**
```python
class Settings(BaseSettings):
    # MCP-specific
    mcp_discovery_enabled: bool
    mcp_transport: TransportType
```

**v2.0:**
```python
class Settings(BaseSettings):
    # Protocol-agnostic
    enabled_adapters: List[str]  # ["mcp", "http", "grpc"]
    adapter_config: dict          # Per-adapter config
    federation_enabled: bool
    cost_attribution_enabled: bool
```

---

## Feature Breakdown: What Goes in v1.1 vs v2.0

### SARK v1.1 (Quick Wins)

| Feature | Effort | Impact | Include? |
|---------|--------|--------|----------|
| Standardize rate limit headers | 1 week | High | ✅ YES |
| Formalize delegation audit fields | 1 week | Medium | ✅ YES |
| Resource provider verification workflow | 2 weeks | High | ✅ YES |
| MFA support | 1 week | Medium | ✅ YES |
| Fix reported bugs | 2 weeks | High | ✅ YES |
| Link to GRID specification | 2 days | Low | ✅ YES |
| **Total v1.1 Effort** | **7 weeks** | | |

### SARK v2.0 (Architectural)

| Feature | Effort | Impact | Include? |
|---------|--------|--------|----------|
| Protocol adapter abstraction | 4 weeks | Critical | ✅ YES |
| MCP adapter extraction | 3 weeks | Critical | ✅ YES |
| HTTP adapter | 2 weeks | High | ✅ YES |
| gRPC adapter | 2 weeks | High | ✅ YES |
| OpenAI adapter | 1 week | Medium | ✅ YES |
| Federation support | 5 weeks | Critical | ✅ YES |
| Cost attribution system | 3 weeks | High | ✅ YES |
| Programmatic policies | 2 weeks | Medium | ✅ YES |
| Tests and documentation | 4 weeks | High | ✅ YES |
| **Total v2.0 Effort** | **26 weeks** | | |

---

## Migration Strategy: v1.x → v2.0

### For Existing SARK v1.x Users

**Goal:** Make migration smooth, provide backward compatibility path

**Phase 1: Dual-Mode (v2.0 launch)**
- v2.0 API endpoints coexist with v1.x
- Automated translators for v1.x concepts to v2.0
- v1.x configurations still work (deprecated warnings)
- Easy migration guide

**Phase 2: Soft Deprecation (v2.1-v2.3)**
- v1.x endpoints marked deprecated but functional
- Migration tooling provided
- Documentation emphasizes v2.0 path
- Community migration support

**Phase 3: Hard Deprecation (v3.0)**
- Remove v1.x compatibility
- v1.x → v2.x upgrade guide required

### Migration Path Example

**SARK v1.0 Policy:**
```rego
package grid.authorization

allow if {
    input.principal.role == "developer"
    input.action == "invoke_tool"
    input.resource.sensitivity_level == "medium"
}
```

**SARK v2.0 Policy (Same!):**
```rego
package grid.authorization

allow if {
    input.principal.role == "developer"
    input.action == "execute"
    input.resource.sensitivity_level == "medium"
}
```

**→ Policies are mostly compatible** (just rename `invoke_tool` → `execute`)

---

## Success Criteria: v2.0 Release

### Technical Criteria
- ✅ 100% GRID v1.0 specification compliance
- ✅ At least 4 protocol adapters (MCP, HTTP, gRPC, OpenAI)
- ✅ Federation working across 2+ SARK instances
- ✅ Cost attribution integrated with policies
- ✅ 90%+ test coverage (maintained)
- ✅ <5ms policy evaluation (maintained)
- ✅ 0 P0/P1 security vulnerabilities

### Documentation Criteria
- ✅ Complete migration guide (v1.x → v2.0)
- ✅ Protocol adapter development guide
- ✅ Federation setup guide
- ✅ Reference adapter implementations (HTTP, gRPC, etc.)
- ✅ GRID alignment documentation
- ✅ All examples updated

### Community Criteria
- ✅ Community feedback from v1.x users
- ✅ Beta testing period (2-4 weeks)
- ✅ Issue resolution before release
- ✅ Announcement to GRID community

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Architectural complexity | High | Prototype adapters early, extensive testing |
| Breaking API changes | High | Backward compatibility layer, migration guide |
| Federation complexity | High | Start simple (2-node), expand incrementally |
| Schedule slippage | Medium | Buffer built in, prioritize MVP features |
| Community adoption | Medium | Clear migration path, excellent documentation |

---

## Recommendation: v1.1 + Fast-Track to v2.0

**Option 1: Sequential (Safe but Slower)**
- v1.1: 6-8 weeks
- v2.0: 16-20 weeks after v1.1
- **Total: 22-28 weeks**

**Option 2: Overlapping (Faster, Recommended)**
- v1.1: 6-8 weeks (with v2.0 planning in parallel)
- v2.0: Starts week 5-6 (overlap with v1.1 final phase)
- **Total: 18-24 weeks**

**Option 3: Direct v2.0 (Aggressive, High Risk)**
- Skip v1.1 entirely
- Go straight to v2.0 development
- **Total: 16-20 weeks** (but no v1.1 polish)

**My Recommendation:** **Option 2 (Overlapping)**

**Rationale:**
1. v1.1 delivers promised quick wins to users
2. v2.0 planning/architecture happens in parallel
3. v2.0 development starts before v1.1 release
4. Faster time to GRID v1.0 reference implementation
5. User base gets intermediate release before major overhaul

---

## Timeline: Recommended Path

```
Nov 2025 (Current)
  └─ SARK v1.0 released, GRID v0.1 specification released ✅

Dec 2025 - Jan 2026 (8 weeks)
  ├─ SARK v1.1 development (rate limits, delegation, verification)
  ├─ v2.0 architecture design (adapters, federation, costs)
  └─ GRID v1.0 spec development

Feb 2026 (v1.1 Release)
  ├─ SARK v1.1: MCP excellence + quick wins ✅
  └─ v2.0 development begins in earnest

Feb - May 2026 (16 weeks)
  ├─ Sprint 1-2: Adapter abstraction + extraction
  ├─ Sprint 3-4: Additional adapters (HTTP, gRPC, OpenAI)
  ├─ Sprint 5-6: Federation support
  ├─ Sprint 7-8: Cost attribution
  ├─ Sprint 9: Programmatic policies
  └─ Sprint 10: Integration, tests, docs

Jun 2026 (v2.0 Beta)
  └─ Beta testing, community feedback, bug fixes

Jul 2026 (v2.0 Release)
  ├─ SARK v2.0: GRID v1.0 reference implementation ✅
  └─ Multi-protocol governance ready for production

Q3 2026 (YORI Planning)
  └─ Start work on GRID-Home reference implementation
```

---

## SARK v2.0 as GRID Reference Implementation

### What This Means

SARK v2.0 will be **the canonical example** of how to implement GRID v1.0:

- ✅ Shows how to build protocol adapters
- ✅ Demonstrates federation in practice
- ✅ Reference implementation for all GRID concepts
- ✅ Blueprint for other GRID implementations
- ✅ Community standard for governance

### Impact

Other teams implementing GRID can:
- Study SARK v2.0 source code
- Use SARK as deployment target
- Build adapters compatible with SARK
- Join federated governance network
- Contribute improvements back

This is **BIND's role for DNS** – SARK becomes the trusted reference everyone uses and builds on.

---

## Conclusion

**Should SARK go to v2.0?**

**YES, absolutely.** Here's why:

1. **GRID is big enough** – Protocol-agnostic governance spans industries
2. **v2.0 is justified** – Major architectural changes (adapters + federation)
3. **Timing is perfect** – GRID v0.1 spec complete, v1.0 roadmap clear
4. **User base is ready** – SARK v1.0 will be battle-tested by then
5. **Community impact** – SARK v2.0 as GRID reference implementation is powerful

**Path:** Do v1.1 (quick wins + polish) while planning v2.0, then launch v2.0 as the GRID v1.0 reference implementation.

This positions SARK and GRID for long-term success and community adoption.

---

**Document:** SARK v2.0 Roadmap
**Status:** Planning document for team review
**Next Step:** Leadership decision on v1.1 vs v2.0 vs overlapping path
**Generated:** November 27, 2025
