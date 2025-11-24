# Engineer Assignments - Iteration 2

**Quick Reference Card**

---

## 👷 Engineer 1: Critical Test Fixes
**Priority:** 🔴 CRITICAL | **Est:** 4-5 hours

### Tasks
- [ ] 1.1: Fix API Router Test Fixtures (29 errors → 0)
- [ ] 1.2: Fix Integration Test Fixtures (9 errors → 0)
- [ ] 1.3: Fix SIEM Event Formatting (2 errors → 0)
- [ ] 1.4: Fix Auth Provider Tests (53 failures → 0-5)
- [ ] 1.5: Fix API Pagination Tests (12 failures → 0)

### Impact
- +115 tests passing
- 40 errors → 0
- 183 failures → 80

### Files to Touch
- `tests/test_api/conftest.py` (new file)
- `tests/test_api/test_routers/test_tools.py`
- `tests/integration/test_auth_integration.py`
- `tests/integration/test_policy_integration.py`
- `tests/test_audit/test_siem_event_formatting.py`
- `tests/test_auth/test_saml_provider.py`
- `tests/test_auth/test_ldap_provider.py`
- `tests/test_api_pagination.py`

---

## 👷 Engineer 2: Coverage Expansion
**Priority:** 🟡 HIGH | **Est:** 4-5 hours

### Tasks
- [ ] 2.1: API Router Coverage (55% → 85%)
- [ ] 2.2: Auth Provider Coverage (28% → 70%)
- [ ] 2.3: Database Layer Coverage (45% → 75%)
- [ ] 2.4: Service Layer Coverage (67% → 85%)

### Impact
- +120-150 new tests
- Coverage: 75% → 85%

### New Files to Create
- `tests/test_api/test_routers/test_auth_complete.py`
- `tests/test_api/test_routers/test_policy_complete.py`
- `tests/test_api/test_routers/test_sessions_complete.py`
- `tests/test_services/auth/test_providers_complete.py`
- `tests/test_db/test_pools.py`
- `tests/test_db/test_session.py`

---

## 👷 Engineer 3: Security & TODO Resolution
**Priority:** 🔴 CRITICAL | **Est:** 3-4 hours

### Tasks
- [ ] 3.1: OAuth State Validation (SECURITY)
- [ ] 3.2: API Key User Isolation (SECURITY)
- [ ] 3.3: Auth Provider App State
- [ ] 3.4: CSRF Token Validation
- [ ] 3.5: Remove Obsolete SIEM TODO

### Impact
- 6 high-priority security TODOs → 0
- Security rating: Good → Excellent

### Files to Touch
- `src/sark/api/routers/auth.py`
- `src/sark/api/routers/api_keys.py`
- `src/sark/api/main.py`
- `src/sark/api/middleware/security_headers.py`
- `src/sark/services/audit/audit_service.py`

---

## 👷 Engineer 4: Documentation & Final QA
**Priority:** 🟡 HIGH | **Est:** 2-3 hours

### Tasks
- [ ] 4.1: Update Test Documentation
- [ ] 4.2: Create Final Coverage Report
- [ ] 4.3: Run Full CI/CD Validation
- [ ] 4.4: Create Production Handoff Document
- [ ] 4.5: Mark DOCUMENTATION_TASKS.md Complete

### Impact
- Documentation: 100% accurate
- Production: Fully validated
- Handoff: Ready

### Files to Touch
- `docs/KNOWN_ISSUES.md`
- `docs/TEST_EXECUTION_SUMMARY.md`
- `docs/PRODUCTION_READINESS.md`
- `docs/README.md`
- `docs/COVERAGE_REPORT_FINAL.md` (new)
- `docs/PRODUCTION_HANDOFF_FINAL.md` (new)
- `docs/DOCUMENTATION_TASKS.md`

---

## 📅 Execution Timeline

### Phase 1 (Hours 0-2)
- **Engineer 1:** Tasks 1.1-1.3
- **Engineer 3:** Tasks 3.1-3.2
- **Engineer 2:** Wait for test fixtures
- **Engineer 4:** Wait for others

### Phase 2 (Hours 2-4)
- **Engineer 1:** Tasks 1.4-1.5
- **Engineer 2:** Tasks 2.1-2.2
- **Engineer 3:** Tasks 3.3-3.5
- **Engineer 4:** Wait for others

### Phase 3 (Hours 4-6)
- **Engineer 2:** Tasks 2.3-2.4
- **Engineer 4:** All tasks
- **Engineer 1 & 3:** Complete

---

## ✅ Completion Checklist

### Before Starting
- [ ] All engineers have latest code
- [ ] Each engineer on separate branch
- [ ] Task assignments confirmed

### During Execution
- [ ] Regular status updates
- [ ] Flag any blockers immediately
- [ ] Coordinate on shared files

### Before Merging
- [ ] All tasks complete
- [ ] All tests passing locally
- [ ] No merge conflicts
- [ ] CI/CD checks passing
- [ ] Documentation updated

---

## 🚨 Conflict Risk Areas

**High Risk (coordinate carefully):**
- `tests/conftest.py` - Engineers 1 & 2
- `src/sark/api/main.py` - Engineer 3
- `docs/KNOWN_ISSUES.md` - Engineers 1 & 4

**Medium Risk:**
- `src/sark/api/routers/auth.py` - Engineer 3
- Test files - Engineers 1 & 2

**Low Risk:**
- Documentation files - Engineer 4
- Source code (non-API) - Engineer 3

---

## 📞 Communication Protocol

**Report Progress:**
- After each task completion
- When encountering blockers
- Before starting shared files

**Merge Order:**
1. Engineer 1 (test infrastructure)
2. Engineer 3 (security fixes)
3. Engineer 2 (coverage expansion)
4. Engineer 4 (documentation)

---

**Full Details:** See `ITERATION_2_TASKS.md`
