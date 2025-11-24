# TODO Comment Audit Report

**Generated:** 2025-11-24
**Total TODOs Found:** 15
**Status:** Documented for prioritization

---

## Summary by Category

| Category | Count | Priority | Status |
|----------|-------|----------|--------|
| **SIEM Integration** | 1 | LOW | Outdated (already implemented) |
| **Authentication/User Context** | 9 | MEDIUM | Needs auth middleware implementation |
| **CSRF Token Validation** | 2 | MEDIUM | Tracked in KNOWN_ISSUES.md |
| **Context Enrichment** | 3 | LOW | Minor improvements |

---

## Detailed TODO List

### 1. SIEM Integration (OUTDATED ✅)

**File:** `src/sark/services/audit/audit_service.py:246`
```python
# TODO: Implement SIEM integration (Splunk, Datadog, etc.)
```

**Status:** ✅ **OBSOLETE** - SIEM integration already exists
- `src/sark/services/audit/siem/splunk.py` - Splunk HEC integration
- `src/sark/services/audit/siem/datadog.py` - Datadog Logs API
- Full framework with batch handling, circuit breakers, retry logic

**Recommendation:** Remove TODO and update `_forward_to_siem()` to use actual SIEM adapters

**Impact:** Documentation cleanup

---

### 2. Authentication/User Context (9 TODOs)

#### 2.1 API Keys Router

**File:** `src/sark/api/routers/api_keys.py`

**Lines 107, 123, 158, 185, 260:**
```python
# TODO: Add authentication dependency to get current user
# TODO: Replace with actual user ID from authentication
# TODO: Check if current user owns this key or has admin access
# TODO: Get actual user ID from authentication
```

**Status:** 🔧 **NEEDS IMPLEMENTATION**

**Root Cause:** Authentication middleware exists but not properly integrated with API key endpoints

**Recommendation:**
1. Add `current_user` dependency from `src/sark/api/dependencies.py`
2. Replace hardcoded user IDs with authenticated user context
3. Add authorization checks (user owns key or is admin)

**Impact:** MEDIUM - Security gap (no user isolation on API keys)

**Estimated Effort:** 2-3 hours

---

#### 2.2 Auth Router

**File:** `src/sark/api/routers/auth.py`

**Lines 119, 132, 469:**
```python
# TODO: Get from app state
# TODO: Get from app state
# TODO: Validate state parameter against stored value
```

**Status:** 🔧 **NEEDS IMPLEMENTATION**

**Details:**
- Auth providers should be stored in FastAPI app state
- OAuth state parameters need validation against session storage

**Recommendation:**
1. Add providers to app.state during startup
2. Store OAuth state in Redis with TTL
3. Validate state on callback to prevent CSRF

**Impact:** MEDIUM - Security gap (OAuth CSRF vulnerability)

**Estimated Effort:** 2-3 hours

---

#### 2.3 Sessions Router

**File:** `src/sark/api/routers/sessions.py`

**Lines 25, 40:**
```python
# TODO: Get from app state
# TODO: Get from authentication context
```

**Status:** 🔧 **NEEDS IMPLEMENTATION**

**Details:**
- Session service should be in app state
- User ID should come from authenticated context

**Recommendation:**
1. Inject session service via dependency
2. Add authentication dependency to get current user

**Impact:** LOW - Endpoints likely not in use yet

**Estimated Effort:** 1 hour

---

### 3. CSRF Token Validation

**File:** `src/sark/api/middleware/security_headers.py`

**Lines 163, 199:**
```python
# TODO: Implement proper token generation and validation with sessions
# TODO: Implement proper token validation
```

**Status:** 📋 **TRACKED** in `docs/KNOWN_ISSUES.md`

**Details:**
- Current CSRF implementation only checks token presence
- Needs session-based token generation and validation
- Tokens should rotate on authentication

**Recommendation:** Already documented in Security Fixes Report

**Impact:** MEDIUM - Security enhancement

**Estimated Effort:** 3-4 hours

---

### 4. Context Enrichment

#### 4.1 Policy Router

**File:** `src/sark/api/routers/policy.py`

**Lines 68, 73:**
```python
"sensitivity_level": "medium",  # TODO: Get from server/tool registry
context={"timestamp": 0},  # TODO: Add real timestamp
```

**Status:** 🔧 **MINOR IMPROVEMENT**

**Details:**
- Sensitivity level should be fetched from tool registry
- Timestamp should use `datetime.now(UTC).timestamp()`

**Recommendation:**
```python
from datetime import UTC, datetime
from sark.services.discovery.tool_registry import ToolRegistry

# Get sensitivity from registry
tool_registry = ToolRegistry(db)
sensitivity = await tool_registry.get_sensitivity(tool_name)

# Add real timestamp
context = {"timestamp": datetime.now(UTC).timestamp()}
```

**Impact:** LOW - Test/demo code improvement

**Estimated Effort:** 30 minutes

---

## Priority Recommendations

### 🔴 **High Priority** (Security Gaps)

1. **OAuth State Validation** (`auth.py:469`)
   - CSRF vulnerability in OAuth flow
   - Implement state validation against Redis storage

2. **API Key User Isolation** (`api_keys.py:107, 123, 158, 185, 260`)
   - Users can access other users' API keys
   - Add authentication + authorization checks

### 🟡 **Medium Priority** (Architecture Improvements)

3. **App State Management** (`auth.py:119, 132`, `sessions.py:25`)
   - Auth providers and services should be in app.state
   - Reduces initialization overhead per request

4. **CSRF Token Enhancement** (`security_headers.py:163, 199`)
   - Already tracked in KNOWN_ISSUES.md
   - Implement session-based token validation

### 🟢 **Low Priority** (Nice to Have)

5. **Remove Obsolete SIEM TODO** (`audit_service.py:246`)
   - Documentation cleanup
   - Update method to use actual SIEM adapters

6. **Context Enrichment** (`policy.py:68, 73`)
   - Minor improvements to test code
   - Add real timestamps and registry lookups

---

## Summary Statistics

```
Total TODOs: 15
├─ Obsolete (can remove): 1
├─ Security gaps: 6
├─ Architecture improvements: 5
└─ Minor improvements: 3

Risk Level Distribution:
├─ HIGH (security): 6 TODOs (40%)
├─ MEDIUM (quality): 5 TODOs (33%)
└─ LOW (cleanup): 4 TODOs (27%)
```

---

## Next Steps

1. **Immediate:** Fix high-priority security gaps (API key isolation, OAuth state validation)
2. **Short-term:** Implement app state management for services
3. **Later:** Address minor improvements and documentation cleanup

---

**Document Owner:** Claude (Cleanup Agent)
**Last Updated:** 2025-11-24
**Next Review:** After Engineer 1 (Backend) completes auth provider work
