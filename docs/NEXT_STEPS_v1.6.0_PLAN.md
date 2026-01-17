# SARK Next Steps: Version Strategy & v1.6.0 Plan

**Date**: 2026-01-17
**Current Version**: 1.3.0 (in code) / 1.5.0 (just merged)
**Analysis**: Post-czarina recovery roadmap reconciliation

---

## Current State Analysis

### What We Have (As of 2026-01-17)

**Merged to Main:**
- ✅ v1.3.0: Advanced Security Features (Dec 2025)
  - Prompt injection detection
  - Anomaly detection
  - Secret scanning
  - MFA support
  - Network controls

- ✅ v1.4.0: Rust Foundation (PR #57)
  - Rust OPA engine integration
  - Rust in-memory cache
  - Python bindings (PyO3)
  - Build system (maturin)
  - **Version not bumped in code**

- ✅ v1.5.0: Production Readiness (PR #59 - just merged)
  - Gateway HTTP transport
  - Gateway SSE transport
  - Gateway stdio transport
  - Security fixes (LDAP, CSRF, credentials)
  - Frontend authentication UI
  - E2E integration tests
  - Performance benchmarks infrastructure
  - **Version not bumped in code**

**Code Version**: Still shows `1.3.0` in `pyproject.toml` and `src/sark/__init__.py`

---

## Roadmap Reconciliation

### Original Roadmap Plan

```
v1.3.0 → v1.4.0 (Rust OPA/Cache) → v1.5.0 (Rust Detection) → v2.0.0 (Production)
```

### What Actually Happened

```
v1.3.0 → v1.4.0 (Rust OPA/Cache) → v1.5.0 (Gateway Transports) → v1.6.0? → v2.0.0?
                                         ⬆
                                   Different from plan!
```

**Gap Identified**: The planned v1.5.0 work (Rust Detection - injection, anomaly, MCP parsing) was **NOT** done. What was merged was "Production Readiness" work.

---

## Immediate Actions Required

### 1. Version Bump (Immediate - Today)

**Update version from 1.3.0 → 1.5.0** to match merged work:

**Files to update:**
- `pyproject.toml`: line 3 (`version = "1.5.0"`)
- `src/sark/__init__.py`: line 3 (`__version__ = "1.5.0"`)
- `docker-compose.yml`: Update image tag if needed
- `README.md`: Update version references
- `docs/ROADMAP.md`: Update current version

**Commit message:**
```
chore: Bump version to 1.5.0 - Production Readiness Release

Updates version across codebase to reflect merged v1.5.0 work:
- Gateway transport implementations (HTTP, SSE, stdio)
- Security fixes (LDAP injection, CSRF, credentials)
- Frontend authentication UI
- E2E integration tests
- Performance benchmark infrastructure

Part of post-czarina recovery cleanup.
```

---

## Strategic Options for Next Version

### Option 1: v1.6.0 - Rust Detection Optimization (Original v1.5.0 Plan)

**Duration**: 4-5 weeks
**Scope**: Port detection algorithms to Rust for 10-100x performance

**Work Streams:**
1. **Rust Injection Detector** (2 weeks)
   - Port prompt injection patterns to Rust regex
   - SIMD-optimized entropy calculation
   - Parallel processing with Rayon
   - Target: <1ms (from 10-50ms Python)

2. **Rust Anomaly Detector** (2 weeks)
   - Port behavioral analysis to Rust
   - Statistical anomaly detection (z-scores)
   - Fast baseline caching
   - Target: <1ms (from 5-20ms Python)

3. **Rust MCP Parser** (1 week)
   - Zero-copy JSON parsing with serde
   - Parallel batch processing
   - Target: <1ms (from 5-10ms Python)

4. **Integration & Testing** (1 week)
   - Feature flags and fallbacks
   - Performance benchmarks
   - Load testing validation

**Benefits:**
- ✅ Completes the Rust optimization journey
- ✅ Achieves 5,000+ req/s throughput (vs 2,000 currently)
- ✅ Sub-millisecond security checks
- ✅ Maintains incremental release strategy

**Risks:**
- ⚠️ Delays production readiness by 1 month
- ⚠️ May not be critical path for v2.0

**See**: `docs/v1.5.0/IMPLEMENTATION_PLAN.md` (original plan)

---

### Option 2: Skip to v2.0.0 - GRID Reference Implementation

**Duration**: 16-20 weeks
**Scope**: Transform SARK into universal GRID v1.0 reference implementation

**Major Changes:**
1. **Protocol Abstraction** (4 weeks)
   - Generic `ProtocolAdapter` interface
   - Extract MCPAdapter from core
   - Generic Resource/Principal/Action models
   - Refactor 15-20 files, 3,000+ lines changed

2. **Additional Adapters** (4 weeks)
   - HTTPAdapter (REST APIs)
   - gRPCAdapter (gRPC services)
   - OpenAIAdapter (OpenAI function calling)
   - Adapter registry and discovery

3. **Federation** (4 weeks)
   - Cross-org policy evaluation
   - Node discovery (DNS/mDNS)
   - mTLS trust establishment
   - Audit trail correlation

4. **Cost Attribution** (3 weeks)
   - Cost model abstraction
   - Budget tracking
   - Cost-based policy decisions

5. **Integration & Testing** (5 weeks)
   - Migration from v1.x
   - Full integration testing
   - GRID v1.0 compliance verification

**Benefits:**
- ✅ Positions SARK as THE reference implementation
- ✅ Universal governance (not just MCP)
- ✅ Federation unlocks enterprise use cases
- ✅ Major architectural evolution

**Risks:**
- ⚠️ Breaking changes (adapters)
- ⚠️ 4-5 month timeline
- ⚠️ Significant refactoring effort

**See**: `docs/planning/SARK_v2.0_ROADMAP.md`

---

### Option 3: v1.6.0 - Bug Fixes & Polish

**Duration**: 2-3 weeks
**Scope**: Quick wins and production polish before v2.0

**Work Items:**
1. **Version Bump** (immediate)
   - Update to 1.5.0 across codebase

2. **Test Suite Fixes** (1 week)
   - Fix remaining export router tests (13 failed)
   - Fix remaining tools router tests (21 failed)
   - Achieve 95%+ test pass rate

3. **Documentation Updates** (3 days)
   - Update ROADMAP.md with actual progress
   - Create v1.5.0 release notes
   - Update architecture docs

4. **Dependabot Fixes** (2 days)
   - Address remaining 4 vulnerabilities flagged by GitHub
   - Update dependencies

5. **Performance Validation** (3 days)
   - Run benchmark suite in proper environment
   - Validate Rust performance claims
   - Generate performance report

**Benefits:**
- ✅ Quick wins (2-3 weeks)
- ✅ Production-ready polish
- ✅ Solid foundation for v2.0
- ✅ Cleans up technical debt

**Risks:**
- ⚠️ Doesn't add major features
- ⚠️ Minor version increment only

---

## Recommendation: Hybrid Approach

### Recommended Path: v1.6.0 (Polish) → v2.0.0 (GRID)

**Phase 1: v1.6.0 - Production Polish (2-3 weeks)**
1. ✅ Bump version to 1.5.0 (immediate)
2. ✅ Fix test suite (achieve 95%+ pass rate)
3. ✅ Address Dependabot vulnerabilities
4. ✅ Run performance benchmarks and validate
5. ✅ Update documentation
6. ✅ Create v1.5.0 release notes
7. ✅ Tag v1.6.0 when complete

**Phase 2: v2.0.0 - GRID Reference Implementation (16-20 weeks)**
1. Protocol abstraction
2. Additional adapters
3. Federation layer
4. Cost attribution
5. Production deployment

**Rationale:**
- v1.6.0 gives us a solid, production-ready foundation
- Addresses technical debt before major refactor
- Creates clean milestone before v2.0 architectural changes
- Validates current Rust performance before adding more
- 2-3 weeks is acceptable delay before v2.0

---

## v1.6.0 Implementation Plan (RECOMMENDED)

### Week 1: Version & Tests

**Days 1-2: Version Bump & Documentation**
- Update version to 1.5.0 across codebase
- Create v1.5.0 release notes
- Update ROADMAP.md with actual state
- Update architecture documentation

**Days 3-5: Test Suite Fixes**
- Fix export router database mocking (13 tests)
- Fix tools router implementation/mocking (21 tests)
- Achieve 95%+ test pass rate (170+/179 tests)
- Update test documentation

### Week 2: Security & Performance

**Days 1-2: Dependabot & Security**
- Address remaining GitHub vulnerabilities
- Update dependencies
- Security scan and validation

**Days 3-5: Performance Validation**
- Set up build environment with Rust toolchain
- Run full benchmark suite
- Validate performance claims:
  - Cache p95 <0.5ms
  - Cache vs Redis 10-50x speedup
  - OPA vs HTTP 4-10x speedup
- Generate performance report

### Week 3: Polish & Release

**Days 1-2: Final Polish**
- Code cleanup
- Documentation review
- CI/CD validation

**Days 3-4: Release Preparation**
- Create v1.6.0 release notes
- Update migration guides
- Final testing

**Day 5: v1.6.0 Release**
- Tag and release v1.6.0
- Publish release notes
- Update roadmap for v2.0.0

---

## Success Criteria

### v1.6.0 Acceptance Criteria

**Code Quality:**
- [ ] Version updated to 1.5.0 in all files
- [ ] Test pass rate ≥95% (170+/179 tests)
- [ ] No P0/P1 GitHub vulnerabilities
- [ ] All dependencies up to date

**Performance:**
- [ ] Benchmarks executed in proper environment
- [ ] Cache p95 <0.5ms validated
- [ ] Cache vs Redis ≥10x validated
- [ ] OPA vs HTTP ≥4x validated
- [ ] Performance report published

**Documentation:**
- [ ] v1.5.0 release notes created
- [ ] ROADMAP.md updated with actual state
- [ ] Architecture docs current
- [ ] v1.6.0 release notes prepared

**Release:**
- [ ] v1.6.0 tag created
- [ ] Release published
- [ ] CI/CD green
- [ ] Ready for v2.0.0 planning

---

## Next Steps (Immediate)

### Today (2026-01-17):

1. **Version Bump** (30 mins)
   ```bash
   # Update version to 1.5.0
   vim pyproject.toml  # Change version = "1.3.0" to "1.5.0"
   vim src/sark/__init__.py  # Change __version__ = "1.3.0" to "1.5.0"
   git commit -am "chore: Bump version to 1.5.0"
   git push origin main
   ```

2. **Create v1.5.0 Release Notes** (1 hour)
   - Document all 10 workers merged
   - List key features
   - Breaking changes (if any)
   - Migration guide

3. **Update Roadmap** (30 mins)
   - Mark v1.5.0 as complete
   - Add v1.6.0 to timeline
   - Update v2.0.0 target date

### This Week:

4. **Fix Test Suite** (2-3 days)
   - Export router mocking
   - Tools router implementation
   - Achieve 95%+ pass rate

5. **Dependabot** (1 day)
   - Review and merge vulnerability fixes
   - Update dependencies

### Next Week:

6. **Performance Validation** (2-3 days)
   - Set up environment
   - Run benchmarks
   - Generate report

7. **Release v1.6.0** (1 day)
   - Tag and publish
   - Update docs

---

## Files to Create/Update

### Immediate:
- [ ] `docs/v1.5.0/RELEASE_NOTES.md` (NEW)
- [ ] `docs/ROADMAP.md` (UPDATE - mark v1.5.0 complete, add v1.6.0)
- [ ] `docs/NEXT_STEPS_v1.6.0_PLAN.md` (THIS FILE)
- [ ] `pyproject.toml` (UPDATE version)
- [ ] `src/sark/__init__.py` (UPDATE version)

### This Week:
- [ ] `tests/test_api/test_routers/test_export.py` (FIX mocking)
- [ ] `tests/test_api/test_routers/test_tools.py` (FIX or implement router)
- [ ] `docs/v1.6.0/IMPLEMENTATION_PLAN.md` (NEW)

### Next Week:
- [ ] `reports/performance/benchmark_report_YYYYMMDD.md` (GENERATED)
- [ ] `docs/v1.6.0/RELEASE_NOTES.md` (NEW)

---

## Budget & Timeline

### v1.6.0 Effort Estimate

| Task | Duration | Effort |
|------|----------|--------|
| Version bump & docs | 1 day | 0.5 person-days |
| Test suite fixes | 3 days | 3 person-days |
| Dependabot fixes | 1 day | 1 person-day |
| Performance validation | 3 days | 2 person-days |
| Polish & release | 2 days | 1 person-day |
| **Total** | **10 days** | **7.5 person-days** |

**Timeline**: 2 weeks (with some buffer)
**Cost**: ~$3,750 (7.5 days × $500/day)

### v2.0.0 Effort Estimate (Future)

**Total**: 16-20 weeks, ~20 person-weeks
**Cost**: ~$50,000 (20 weeks FTE × $2,500/week)
**See**: `docs/planning/SARK_v2.0_ROADMAP.md` for details

---

## Decision Required

**Question**: Which path should we take?

**Options:**
1. ✅ **v1.6.0 Polish → v2.0.0 GRID** (RECOMMENDED)
2. v1.6.0 Rust Detection → v2.0.0 GRID
3. Skip v1.6.0 → Go directly to v2.0.0

**Recommendation**: Option 1 (v1.6.0 Polish)
- Quick wins (2-3 weeks)
- Solid foundation
- Addresses debt
- Ready for v2.0

**Next Action**: Approve plan and start v1.6.0 version bump

---

**Document Version**: 1.0
**Status**: Ready for Review
**Next Review**: After v1.6.0 completion
