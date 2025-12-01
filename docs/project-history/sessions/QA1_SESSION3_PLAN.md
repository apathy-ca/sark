# QA-1 Session 3: Post-Merge Integration Testing Plan

**Role:** QA-1 Integration Testing Lead
**Session:** CZAR Session 3 - Code Review & PR Merging
**Status:** READY ✅

---

## Primary Responsibility

**Run integration tests after EACH merge to validate integrated system**

---

## Merge Order & Testing Plan

### 1. Database (Foundation) - FIRST
**Branch:** `feat/v2-database`
**Engineer:** ENGINEER-6

**Tests to Run:**
```bash
# After database merge to main
git checkout main
git pull origin main

# Run database-specific tests
pytest tests/migrations/ -v
pytest tests/db/ -v

# Run integration tests to ensure no regressions
pytest tests/integration/v2/ -v --cov=src/sark
```

**Success Criteria:**
- ✅ All migration tests pass
- ✅ Database session/pool tests pass
- ✅ Integration tests still pass (no regression)
- ✅ Coverage maintained or improved

---

### 2. MCP Adapter (If Complete) - SECOND
**Branch:** `feat/v2-lead-architect` (ENGINEER-1 Phase 2)
**Engineer:** ENGINEER-1

**Tests to Run:**
```bash
# After MCP adapter merge
git checkout main
git pull origin main

# Run MCP-specific integration tests
pytest tests/integration/v2/test_adapter_integration.py::TestMCPAdapter -v

# Run full adapter suite
pytest tests/integration/v2/test_adapter_integration.py -v

# Check for any breakage in multi-protocol
pytest tests/integration/v2/test_multi_protocol.py -v
```

**Success Criteria:**
- ✅ All MCP adapter tests pass
- ✅ Adapter registry works with MCP
- ✅ Multi-protocol workflows include MCP
- ✅ No regression in HTTP/gRPC tests

---

### 3. HTTP & gRPC Adapters (Parallel) - THIRD
**Branches:**
- `feat/v2-http-adapter` (ENGINEER-2)
- `feat/v2-grpc-adapter` (ENGINEER-3)

**Tests to Run (after HTTP merge):**
```bash
git checkout main
git pull origin main

# HTTP adapter tests
pytest tests/integration/v2/test_adapter_integration.py::TestHTTPAdapter -v

# Multi-protocol with HTTP
pytest tests/integration/v2/test_multi_protocol.py -v
```

**Tests to Run (after gRPC merge):**
```bash
git checkout main
git pull origin main

# gRPC adapter tests
pytest tests/integration/v2/test_adapter_integration.py::TestGRPCAdapter -v

# Full integration suite
pytest tests/integration/v2/ -v --cov=src/sark
```

**Success Criteria:**
- ✅ HTTP adapter tests pass
- ✅ gRPC adapter tests pass (including streaming)
- ✅ Cross-adapter integration works
- ✅ Multi-protocol workflows validated
- ✅ Coverage ≥ 10% maintained

---

### 4. Federation - FOURTH
**Branch:** `feat/v2-federation`
**Engineer:** ENGINEER-4

**Tests to Run:**
```bash
git checkout main
git pull origin main

# Federation-specific tests
pytest tests/integration/v2/test_federation_flow.py -v

# Multi-protocol with federation
pytest tests/integration/v2/test_multi_protocol.py -v

# Full suite
pytest tests/integration/v2/ -v --cov=src/sark
```

**Success Criteria:**
- ✅ All 28 federation tests pass
- ✅ mTLS trust establishment works
- ✅ Cross-org authorization validated
- ✅ Multi-node federation functional
- ✅ No regression in adapters

---

### 5. Advanced Features - FIFTH
**Branch:** `feat/v2-advanced-features`
**Engineer:** ENGINEER-5

**Tests to Run:**
```bash
git checkout main
git pull origin main

# Full integration test suite
pytest tests/integration/v2/ -v --cov=src/sark

# Performance regression check
pytest tests/performance/v2/ -v

# Security validation
pytest tests/security/v2/ -v
```

**Success Criteria:**
- ✅ All integration tests pass
- ✅ Advanced features don't break existing functionality
- ✅ Performance benchmarks within tolerance
- ✅ Security tests pass
- ✅ Final coverage ≥ 10%

---

## Continuous Monitoring

### After EACH Merge:

1. **Pull Latest Main**
   ```bash
   git checkout main
   git pull origin main
   ```

2. **Run Quick Smoke Tests**
   ```bash
   pytest tests/integration/v2/ -v -k "test_register_adapter or test_static_node or test_mcp_to_http"
   ```

3. **Run Full Integration Suite**
   ```bash
   pytest tests/integration/v2/ -v --cov=src/sark --cov-report=term-missing
   ```

4. **Check Coverage**
   - Ensure coverage ≥ 10% maintained
   - Identify any coverage drops

5. **Report Results**
   - Post results to team
   - Flag any regressions immediately
   - Document any new failures

---

## Regression Detection

### Red Flags to Watch:
- ❌ Previously passing tests now fail
- ❌ Coverage drops below 10%
- ❌ Import errors or module issues
- ❌ Test execution time increases >50%
- ❌ New warnings or deprecations

### Response Protocol:
1. **STOP** further merges
2. **NOTIFY** ENGINEER-1 and relevant engineer
3. **BISECT** to identify breaking commit
4. **REVERT** if necessary
5. **FIX** and re-test before continuing

---

## Success Metrics

### Overall Session 3 Goals:
- ✅ All PRs merged to main
- ✅ 79/79 integration tests passing
- ✅ Coverage maintained ≥ 10%
- ✅ Zero regressions
- ✅ All adapters functional
- ✅ Federation working
- ✅ Multi-protocol workflows validated

### Final Validation:
```bash
# After ALL merges complete
git checkout main
git pull origin main

# Complete test suite
pytest tests/integration/v2/ -v --cov=src/sark --cov-report=html --cov-report=json

# Generate final report
# Save coverage.json for comparison
# Create SESSION_3_FINAL_TEST_REPORT.md
```

---

## Test Infrastructure Status

### Current Status: ✅ READY

- ✅ Integration test framework operational (79 tests)
- ✅ pytest configuration complete
- ✅ Coverage reporting configured
- ✅ Test fixtures working
- ✅ Bug fixes applied (get_config → get_settings)
- ✅ Markers registered (v2, federation, chaos)

### Known Limitations:
- ⚠️ Chaos tests need fixtures (26 tests inactive)
- ⚠️ Pydantic deprecation warnings (non-blocking)
- ℹ️ Coverage focused on integration contracts, not implementation

---

## Communication Plan

### After Each Test Run:

**Format:**
```
🧪 QA-1 POST-MERGE TEST REPORT
Merge: [Engineer] - [Feature]
Status: ✅ PASS / ❌ FAIL
Tests: XX/YY passed
Coverage: X.XX%
Regressions: None / [Details]
Time: X.XXs
Next: Ready for [Next Merge]
```

### Escalation Path:
1. Minor issues → Notify engineer directly
2. Test failures → Notify ENGINEER-1 + engineer
3. System breakage → STOP all merges, notify CZAR

---

## Preparation Checklist

- [x] Integration test suite validated (79/79 passing)
- [x] Test execution report created
- [x] Bug fixes committed
- [x] Coverage baseline established (10.94%)
- [x] Test infrastructure documented
- [x] Session 3 plan created
- [ ] Monitor for PR creation
- [ ] Ready to test first merge

---

## QA-1 Sign-Off

**Status:** READY FOR SESSION 3 ✅

**Confidence:** HIGH
**Infrastructure:** OPERATIONAL
**Response Time:** <5 minutes per merge

**Standing By:** Monitoring for PRs and merge notifications

🤖 *QA-1 Integration Testing Lead - Session 3 Ready*
