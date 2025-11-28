# SARK v2.0 Preparation Tasks

**Status:** Preparation work that can be done during v1.1 development
**Goal:** Reduce v2.0 implementation friction, get architecture ready
**Created:** November 28, 2025
**Context:** No production users yet - v2.0 will likely be first real deployment

---

## Overview

These tasks prepare the codebase for v2.0's protocol abstraction and federation features. Since there are no production users, we can focus on clean architecture without worrying about migration paths or backward compatibility.

---

## Category 1: Code Organization & Refactoring

### 1.1 Extract MCP-Specific Logic into Dedicated Module

**Why:** Makes it easier to convert to an adapter pattern in v2.0

**Tasks:**
- [ ] Create `src/sark/protocols/mcp/` directory structure
- [ ] Move MCP-specific models to `src/sark/protocols/mcp/models.py`
- [ ] Move MCP-specific utilities to `src/sark/protocols/mcp/utils.py`
- [ ] Update imports across codebase
- [ ] Ensure all tests still pass

**Files to refactor:**
```
src/sark/models/mcp_server.py → src/sark/protocols/mcp/models.py
src/sark/services/discovery.py → src/sark/protocols/mcp/discovery.py
```

**Effort:** 2-3 days
**Risk:** Low (just moving code, no logic changes)
**Benefit:** Clean separation makes adapter extraction trivial in v2.0

---

### 1.2 Introduce Generic Resource Terminology (Aliases)

**Why:** Start using v2.0 terminology alongside v1.x without breaking changes

**Tasks:**
- [ ] Add type aliases: `Resource = MCPServer`, `Capability = MCPTool`
- [ ] Update docstrings to mention both terms
- [ ] Update new code to prefer generic terms

**Example:**
```python
# src/sark/models/__init__.py
from .mcp_server import MCPServer, MCPTool

# Type aliases for v2.0 - will become base classes
Resource = MCPServer
Capability = MCPTool

__all__ = ["MCPServer", "MCPTool", "Resource", "Capability"]
```

**Effort:** 1 day
**Risk:** Very low (just aliases)
**Benefit:** Start using v2.0 terminology now

---

### 1.3 Abstract Database Models from Business Logic

**Why:** v2.0 will need generic resource models, not MCP-specific

**Tasks:**
- [ ] Create `src/sark/models/base.py` with generic base classes
- [ ] Add `ResourceBase` abstract model
- [ ] Add `CapabilityBase` abstract model
- [ ] Make `MCPServer` inherit from `ResourceBase`
- [ ] Make `MCPTool` inherit from `CapabilityBase`

**Effort:** 3-4 days
**Risk:** Medium (database schema changes)
**Benefit:** v2.0 adapter models just inherit from these bases

---

## Category 2: Configuration & Settings

### 2.1 Introduce Protocol-Agnostic Configuration Structure

**Why:** v2.0 will support multiple protocols, need flexible config

**Tasks:**
- [ ] Add `protocols` section to settings
- [ ] Move MCP settings under `protocols.mcp`
- [ ] Clean up old settings (no need for backward compat)

**Effort:** 1 day
**Risk:** Very low (no users to break)
**Benefit:** v2.0 just adds new protocol sections

---

### 2.2 Add Feature Flags for v2.0 Features

**Why:** Enable gradual rollout of v2.0 features

**Tasks:**
- [ ] Add `feature_flags` to settings
- [ ] Add flags: `enable_protocol_adapters`, `enable_federation`, `enable_cost_attribution`
- [ ] Default all to `False` for now
- [ ] Document flag behavior

**Effort:** 1 day
**Risk:** Very low
**Benefit:** Can enable v2.0 features incrementally during development

---

## Category 3: API & Interface Design

### 3.1 Design Protocol Adapter Interface (Specification Only)

**Why:** Define the contract before implementation

**Tasks:**
- [ ] Create `docs/v2.0/PROTOCOL_ADAPTER_SPEC.md`
- [ ] Define `ProtocolAdapter` abstract interface
- [ ] Document required methods: `discover()`, `invoke()`, `validate()`
- [ ] Create example adapter pseudocode
- [ ] Get community feedback

**Deliverable:** Specification document, no code changes

**Effort:** 3-4 days
**Risk:** None (documentation only)
**Benefit:** Clear contract for v2.0 implementation, community input

---

### 3.2 Design Federation Protocol (Specification Only)

**Why:** Define federation before implementation

**Tasks:**
- [ ] Create `docs/v2.0/FEDERATION_SPEC.md`
- [ ] Define node discovery protocol
- [ ] Define trust establishment (mTLS)
- [ ] Define cross-org policy evaluation
- [ ] Define audit correlation format
- [ ] Get community feedback

**Deliverable:** Specification document, no code changes

**Effort:** 4-5 days
**Risk:** None (documentation only)
**Benefit:** Clear roadmap, community validation

---

### 3.3 Add Versioned API Endpoints (v2 Namespace)

**Why:** Prepare for v2.0 API without breaking v1.x

**Tasks:**
- [ ] Create `src/sark/api/v2/` directory
- [ ] Add `/api/v2/` router (initially empty or redirects to v1)
- [ ] Document API versioning strategy
- [ ] Add version negotiation middleware

**Effort:** 1 day
**Risk:** Very low
**Benefit:** v2.0 API can be developed alongside v1.x

---

## Category 4: Testing Infrastructure

### 4.1 Create Protocol Adapter Test Framework

**Why:** v2.0 will need to test multiple adapters consistently

**Tasks:**
- [ ] Create `tests/protocols/` directory
- [ ] Create `tests/protocols/base_adapter_test.py` with common tests
- [ ] Create `tests/protocols/test_mcp_adapter.py` (when MCP becomes adapter)
- [ ] Document adapter testing requirements

**Effort:** 2 days
**Risk:** Low
**Benefit:** Consistent adapter testing in v2.0

---

### 4.2 Add Performance Benchmarks for Core Operations

**Why:** v2.0 must maintain <5ms policy evaluation

**Tasks:**
- [ ] Create `tests/benchmarks/` directory
- [ ] Add benchmark for policy evaluation
- [ ] Add benchmark for audit logging
- [ ] Add benchmark for resource lookup
- [ ] Document baseline performance (v1.x)

**Effort:** 2-3 days
**Risk:** Low
**Benefit:** Ensure v2.0 doesn't regress performance

---

## Category 5: Documentation

### 5.1 Create v2.0 Feature Overview

**Why:** Document what v2.0 will deliver

**Tasks:**
- [ ] Create `docs/v2.0/FEATURES.md`
- [ ] Document protocol abstraction architecture
- [ ] Document federation capabilities
- [ ] Document cost attribution system
- [ ] Document programmatic policies

**Effort:** 2 days
**Risk:** None
**Benefit:** Clear vision of v2.0 capabilities

---

### 5.2 Document Current Architecture for Comparison

**Why:** Show what's changing in v2.0

**Tasks:**
- [ ] Create `docs/v1.x/ARCHITECTURE_SNAPSHOT.md`
- [ ] Document current MCP-specific architecture
- [ ] Create architecture diagrams
- [ ] Document current limitations
- [ ] Highlight what v2.0 will improve

**Effort:** 2 days
**Risk:** None
**Benefit:** Clear before/after comparison

---

## Category 6: Dependencies & Infrastructure

### 6.1 Audit Dependencies for v2.0 Compatibility

**Why:** Ensure dependencies support v2.0 features

**Tasks:**
- [ ] Check FastAPI version supports multiple routers
- [ ] Check SQLAlchemy supports polymorphic models
- [ ] Check OPA supports dynamic policy loading
- [ ] Document any required upgrades
- [ ] Test upgrades in dev environment

**Effort:** 2 days
**Risk:** Low
**Benefit:** No surprises during v2.0 development

---

### 6.2 Add Adapter Registry Infrastructure (Stub)

**Why:** v2.0 needs dynamic adapter registration

**Tasks:**
- [ ] Create `src/sark/adapters/` directory
- [ ] Create `src/sark/adapters/registry.py` (stub)
- [ ] Add adapter registration mechanism (no-op in v1.x)
- [ ] Document registry design

**Effort:** 1 day
**Risk:** Very low (no-op in v1.x)
**Benefit:** Infrastructure ready for v2.0

---

## Prioritized Execution Plan

### Phase 1: Low-Risk Documentation (Week 1)
- [ ] 3.1 Protocol Adapter Spec
- [ ] 3.2 Federation Spec
- [ ] 5.1 v2.0 Feature Overview
- [ ] 5.2 Architecture Snapshot

**Effort:** 1 week
**Benefit:** Clear v2.0 vision and architecture

---

### Phase 2: Code Organization (Week 2-3)
- [ ] 1.1 Extract MCP Logic
- [ ] 1.2 Generic Resource Aliases
- [ ] 2.1 Protocol-Agnostic Config
- [ ] 2.2 Feature Flags

**Effort:** 2 weeks
**Benefit:** Cleaner codebase, easier v2.0 transition

---

### Phase 3: Infrastructure (Week 4)
- [ ] 3.3 Versioned API Endpoints
- [ ] 6.2 Adapter Registry (Stub)
- [ ] 4.1 Adapter Test Framework
- [ ] 6.1 Dependency Audit

**Effort:** 1 week
**Benefit:** v2.0 infrastructure in place

---

### Phase 4: Advanced Prep (Week 5-6, Optional)
- [ ] 1.3 Abstract Database Models
- [ ] 4.2 Performance Benchmarks

**Effort:** 2 weeks
**Benefit:** Deeper preparation, but can wait until v2.0 starts

---

## Success Criteria

### For Each Task
- ✅ All existing tests still pass
- ✅ Documentation updated
- ✅ Code is clean and well-organized

### For Overall Prep
- ✅ v2.0 specifications complete
- ✅ MCP logic isolated and ready for adapter extraction
- ✅ Configuration supports protocol abstraction
- ✅ API versioning in place
- ✅ Test infrastructure ready for adapters
- ✅ No performance regressions

---

## Risk Management

| Risk | Mitigation |
|------|-----------|
| **Prep work conflicts with v1.1** | Only do tasks in separate modules/files |
| **Wasted effort if v2.0 changes** | Focus on specs first |
| **Team bandwidth** | All tasks are optional, prioritize Phase 1-2 |

---

## Timeline Recommendation

**Conservative (Recommended):**
- Do Phase 1 (specs) during v1.1 development
- Do Phase 2-3 after v1.1 release, before v2.0 starts
- Skip Phase 4 (do during v2.0)

**Aggressive:**
- Do Phase 1-3 in parallel with v1.1
- Do Phase 4 before v2.0 kickoff
- Start v2.0 with clean architecture

**Recommended:** Conservative approach
- Less risk of conflicts with v1.1 work
- Prep work happens in parallel or between releases

---

## Conclusion

These preparation tasks will:
1. **Reduce v2.0 implementation time** by 20-30%
2. **Reduce v2.0 risk** through early specification
3. **Improve codebase** organization and maintainability
4. **Enable incremental development** through feature flags
5. **Provide clear architecture** before implementation starts

**Next Steps:**
1. Start with Phase 1 (specifications) - low risk, high value
2. Do Phase 2-3 when bandwidth allows
3. Phase 4 is optional - can be done during v2.0 if needed

---

**Document Version:** 1.0
**Created:** November 28, 2025
**Status:** Ready for review
**Recommended Start:** After v1.1 kickoff, during parallel development