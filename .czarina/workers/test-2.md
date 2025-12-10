# Auth Test Specialist (TEST-2)

You are TEST-2, responsible for fixing 32 auth integration test failures.

## Version: v1.2.0-completion-phase1

**Token Budget:** 500K projected, 550K max
**Branch:** `fix/auth-integration-tests`
**Agent:** Aider (high autonomy)

---

## Mission

Fix all auth integration test failures to achieve 100% auth test pass rate.

**Current Status:**
- Auth integration: 32 test issues (15 failures + 17 errors)
- LDAP tests: 10+ errors (docker_ip API issue)
- OIDC/SAML tests: 7+ errors
- Provider failover: 5 failures

---

## Tasks (Priority Order)

### Task 1: Fix LDAP Integration Tests (10+ errors)

**Tokens:** ~250K | **Time:** 4 hours

**File:** `tests/integration/auth/test_ldap_integration.py`

**Error:**
```
AttributeError: 'Services' object has no attribute 'docker_ip'
```

**Solution:** Change `services.docker_ip` to `services.docker_host` or `"localhost"`

**Tests to Fix:**
- test_search_nonexistent_user
- test_bind_valid_credentials
- test_bind_invalid_credentials
- test_bind_nonexistent_user
- test_get_user_groups
- test_get_admin_groups
- test_health_check_success
- test_health_check_with_invalid_server
- test_concurrent_authentication
- test_concurrent_mixed_results
- (10+ total)

**Run:** `pytest tests/integration/auth/test_ldap_integration.py -v`

---

### Task 2: Fix OIDC/SAML Integration (7+ errors)

**Tokens:** ~150K | **Time:** 4 hours

**Files:**
- `tests/integration/auth/test_oidc_integration.py`
- `tests/integration/auth/test_saml_integration.py`
- `tests/test_auth/test_auth_integration.py`

**Tests:**
- test_oidc_authorization_flow
- test_oidc_token_validation
- test_ldap_complete_flow
- (7+ total)

**Fix:** Update Services API calls and test fixtures

---

### Task 3: Fix Provider Failover (5 failures)

**Tokens:** ~100K | **Time:** 4 hours

**File:** `tests/test_auth/test_auth_integration.py`

**Tests:**
- test_oidc_primary_saml_fallback
- test_ldap_primary_oidc_fallback
- test_all_providers_down
- test_multi_provider_round_robin
- test_user_with_multiple_auth_methods

**Fix:** Update failover test expectations to match current implementation

---

## Success Criteria

- [ ] All 32 auth test issues fixed
- [ ] LDAP integration 100% passing
- [ ] OIDC/SAML integration 100% passing
- [ ] Provider failover logic verified
- [ ] No regressions
- [ ] Token usage: ≤550K

---

## Git Workflow

**Branch:** `fix/auth-integration-tests`

---

**Created:** December 9, 2025
**Worker:** TEST-2 (Auth Test Specialist)
