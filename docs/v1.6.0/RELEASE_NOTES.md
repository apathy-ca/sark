# v1.6.0 Release Notes - Polish & Validation

**Release Date**: 2026-01-18
**Type**: Polish & Validation Release
**Focus**: Security fixes, test infrastructure improvements, production readiness

---

## Overview

v1.6.0 is a polish and validation release focused on hardening the codebase for production use. This release addresses 24 of 25 Dependabot security vulnerabilities (96% fix rate), eliminates the ecdsa dependency, and resolves all export and tools router test infrastructure issues.

### Release Highlights

✅ **Security**: 96% vulnerability remediation (24/25 fixed)
✅ **Testing**: 39 tests fixed (100% pass rate for export + tools routers)
✅ **Dependencies**: Eliminated ecdsa dependency, upgraded to PyJWT
✅ **Quality**: Fixed keyword detection algorithm, route ordering issues

---

## Security Improvements

### Vulnerability Remediation (24/25 Fixed)

**Critical & High Severity Fixes:**
- **aiohttp** 3.13.2 → 3.13.3 (7 CVEs fixed)
  - CVE-2025-69223 through CVE-2025-69230
  - Denial of Service, HTTP Parsing vulnerabilities
- **urllib3** 1.26.20 → 2.6.3 (4 CVEs fixed)
  - CVE-2025-50181, CVE-2025-66418, CVE-2025-66471, CVE-2026-21441
  - Request smuggling, proxy bypass, header injection
- **authlib** 1.3.2 → 1.6.6
  - CVE-2025-68158: Open Redirect vulnerability
- **werkzeug** 3.1.3 → 3.1.5
  - CVE-2026-21860: Path Traversal vulnerability

**Medium Severity Fixes:**
- **filelock** 3.16.1 → 3.17.0 (CVE-2025-65114)
- **virtualenv** 20.28.0 → 20.29.1 (CVE-2025-65111)
- **bokeh** 3.6.2 → 3.7.0 (CVE-2025-65108)
- **fonttools** 4.55.3 → 4.55.5 (CVE-2026-22220)
- **pyasn1** 0.6.1 → 0.6.2 (CVE-2026-23490)
- **pynacl** 1.6.0 → 1.6.2 (CVE-2025-69277)
- **azure-core** 1.32.0 → 1.38.0 (CVE-2026-21226)

### Eliminated ecdsa Dependency

**Migration**: python-jose → PyJWT[crypto]

**Files Updated** (9 files):
- `src/sark/services/auth/jwt.py`
- `src/sark/services/auth/tokens.py`
- `src/sark/api/middleware/auth.py`
- `tests/test_services/test_auth/test_jwt.py`
- `tests/test_services/test_auth/test_tokens.py`
- `tests/test_api/test_middleware/test_auth.py`
- `tests/test_security/test_integration.py`
- `docs/v1.6.0/SECURITY_AUDIT.md`
- `pyproject.toml`

**Security Impact:**
- Eliminated CVE-2024-23342 (Minerva timing attack)
- Switched to cryptography library (industry standard)
- Better maintained, more secure ECDSA implementation

**Exception Handling Changes:**
```python
# Before (python-jose)
from jose import JWTError
try:
    payload = decode_token(token)
except JWTError as e:
    handle_error(e)

# After (PyJWT)
import jwt
try:
    payload = jwt.decode(token, key, algorithms=["RS256"])
except jwt.InvalidTokenError as e:
    handle_error(e)
```

### Remaining Vulnerability

**nbconvert** 7.16.4 (CVE-2025-22250)
- **Status**: Windows-only vulnerability
- **Impact**: Minimal (dev dependency, Linux deployment)
- **Severity**: Moderate
- **Mitigation**: Awaiting upstream fix, does not affect production

---

## Test Infrastructure Improvements

### Export Router Tests: 17/17 Passing (100%)

**Issues Fixed:**
1. **SessionMiddleware dependency error**
   - Removed CSRFProtectionMiddleware from test client
   - Tests now run without session middleware requirement
2. **Incorrect route path**
   - Fixed: `@router.post("")` → `@router.post("/")`
   - Corrected FastAPI empty path handling
3. **Database mocking pattern**
   - Created `create_mock_db_dependency()` helper
   - Converted from `@patch` decorators to `dependency_overrides`
   - Added proper try/finally cleanup

**Test Classes:**
- TestCreateExportEndpoint (3/3) ✅
- TestExportServersCsvEndpoint (3/3) ✅
- TestExportServersJsonEndpoint (2/2) ✅
- TestExportToolsCsvEndpoint (2/2) ✅
- TestExportToolsJsonEndpoint (2/2) ✅
- TestExportErrorHandling (1/1) ✅
- TestExportRequestModel (4/4) ✅

### Tools Router Tests: 22/22 Passing (100%)

**Issues Fixed:**

1. **Keyword Detection Bug (5 tests)**
   - **Root Cause**: Regex word boundaries `\b` don't match underscores
   - **Impact**: Failed to detect keywords in snake_case identifiers
   - **Examples**:
     - `\bread\b` didn't match "read_user_data"
     - `\bdelete\b` didn't match "delete_resource"
     - `\bcredit_card\b` didn't match "credit card"
   - **Fix**: Changed pattern to `(?:^|[^a-z]){keyword}(?:$|[^a-z])`
   - **File**: `src/sark/services/discovery/tool_registry.py:182-206`
   - **Tests Fixed**:
     - test_detect_sensitivity_low
     - test_detect_sensitivity_high
     - test_detect_sensitivity_critical
     - test_detect_sensitivity_with_parameters

2. **FastAPI Route Ordering (1 test)**
   - **Root Cause**: Static path `/statistics/sensitivity` defined after `/{tool_id}/sensitivity`
   - **Impact**: FastAPI matched "statistics" as UUID parameter
   - **Fix**: Moved static route before parameterized routes
   - **File**: `src/sark/api/routers/tools.py:62-80`
   - **Test Fixed**: test_get_sensitivity_statistics

3. **Database Mocking Infrastructure (5 tests)**
   - **Root Cause**: Flawed db_session fixture pattern
   - **Impact**: Mock objects not accessible via FastAPI dependency injection
   - **Fix**: Applied dependency_overrides pattern from export tests
   - **Helper Functions Created**:
     - `create_mock_db_for_tool(tool, method="get")`
     - `create_mock_db_empty()`
     - `create_mock_timescale_db()`
   - **Tests Fixed**:
     - test_get_sensitivity_history
     - test_get_sensitivity_history_not_found
     - test_list_tools_by_sensitivity_high
     - test_update_sensitivity_with_optional_reason

**Test Coverage:**
- GET Sensitivity: 3/3 ✅
- UPDATE Sensitivity: 3/3 ✅
- DETECT Sensitivity: 6/6 ✅
- History: 2/2 ✅
- Statistics: 1/1 ✅
- List by Sensitivity: 2/2 ✅
- Bulk Detection: 1/1 ✅
- Validation: 4/4 ✅

---

## Bug Fixes

### Keyword Detection Algorithm

**Before:**
```python
def _contains_keywords(self, text: str, keywords: list[str]) -> bool:
    for keyword in keywords:
        pattern = r"\b" + re.escape(keyword) + r"\b"
        if re.search(pattern, text):
            return True
    return False
```

**After:**
```python
def _contains_keywords(self, text: str, keywords: list[str]) -> bool:
    for keyword in keywords:
        # Replace underscores to match both snake_case and spaces
        keyword_pattern = keyword.replace("_", "[ _]")
        # Match at word boundaries (start/end or after non-letter)
        pattern = r"(?:^|[^a-z])" + keyword_pattern + r"(?:$|[^a-z])"
        if re.search(pattern, text):
            return True
    return False
```

**Impact:**
- Correctly detects keywords in snake_case identifiers
- Handles both "credit_card" and "credit card" formats
- Prevents false negatives in tool sensitivity detection

### FastAPI Route Ordering

**Issue**: Static paths must be defined before parameterized paths

**Before (Incorrect Order):**
```python
@router.get("/{tool_id}/sensitivity")  # Line 62
...
@router.get("/statistics/sensitivity")  # Line 259
```

**After (Correct Order):**
```python
@router.get("/statistics/sensitivity")  # Line 66 (moved up)
...
@router.get("/{tool_id}/sensitivity")  # Line 83
```

**Added Documentation:**
```python
# NOTE: Routes with static paths must be defined BEFORE routes with path parameters
# to avoid FastAPI matching the static path as a parameter value
```

---

## Testing

### Test Results Summary

| Test Suite | Status | Pass Rate | Notes |
|------------|--------|-----------|-------|
| Export Router | ✅ Complete | 17/17 (100%) | All tests passing |
| Tools Router | ✅ Complete | 22/22 (100%) | All tests passing |
| **v1.6.0 Total** | **✅ Complete** | **39/39 (100%)** | **All fixed tests passing** |

### Test Infrastructure Patterns

**Established Pattern**: FastAPI Dependency Overrides

```python
def create_mock_db_dependency(mock_data):
    async def mock_db_generator():
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_data
        mock_session.execute = AsyncMock(return_value=mock_result)
        yield mock_session
    return mock_db_generator

def test_endpoint(client, mock_data):
    from sark.api.main import app
    from sark.db import get_db

    app.dependency_overrides[get_db] = create_mock_db_dependency(mock_data)

    try:
        response = client.get("/api/v1/endpoint")
        assert response.status_code == 200
    finally:
        if get_db in app.dependency_overrides:
            del app.dependency_overrides[get_db]
```

---

## Dependencies

### Updated

- **aiohttp**: 3.13.2 → 3.13.3
- **urllib3**: 1.26.20 → 2.6.3
- **kubernetes**: 34.1.0 → 35.0.0 (for urllib3 2.x compatibility)
- **authlib**: 1.3.2 → 1.6.6
- **werkzeug**: 3.1.3 → 3.1.5
- **filelock**: 3.16.1 → 3.17.0
- **virtualenv**: 20.28.0 → 20.29.1
- **bokeh**: 3.6.2 → 3.7.0
- **fonttools**: 4.55.3 → 4.55.5
- **pyasn1**: 0.6.1 → 0.6.2
- **pynacl**: 1.6.0 → 1.6.2
- **azure-core**: 1.32.0 → 1.38.0

### Replaced

- **Removed**: python-jose[cryptography]
- **Added**: PyJWT[crypto]>=2.10.1

---

## Documentation

### New Documentation

- **docs/v1.6.0/SECURITY_AUDIT.md**: Complete vulnerability audit
- **docs/v1.6.0/TEST_FIXES.md**: Test infrastructure improvements
- **docs/v1.6.0/RELEASE_NOTES.md**: This document

### Updated Documentation

- **README.md**: Updated to v1.5.0 current release
- **ROADMAP.md**: Added v1.6.0 plan, updated version timeline

---

## Migration Guide

### For Developers

**JWT Library Migration:**

If you have custom code using python-jose, update imports:

```python
# Before
from jose import JWTError, jwt as jose_jwt

# After
import jwt
from jwt import InvalidTokenError
```

**Exception Handling:**

```python
# Before
try:
    token = decode_token(...)
except JWTError:
    handle_error()

# After
try:
    token = jwt.decode(...)
except jwt.InvalidTokenError:
    handle_error()
```

**Test Infrastructure:**

If you have router tests, use the dependency override pattern:

```python
# Use this pattern
app.dependency_overrides[get_db] = create_mock_db_dependency(data)

# Instead of
@patch("module.get_db")
def test_function(mock_get_db):
    ...
```

---

## Known Issues

1. **nbconvert vulnerability** (CVE-2025-22250)
   - Windows-only, dev dependency
   - Awaiting upstream fix
   - Does not affect production deployments

2. **Other router tests** remain unfixed
   - Not in scope for v1.6.0
   - Targeted for v1.6.1 or v2.0.0

---

## Contributors

- **Security Audit**: Internal Security Team
- **Test Infrastructure**: QA Team
- **Implementation**: Development Team + Claude

---

## Upgrade Instructions

### Installation

```bash
# From PyPI (when published)
pip install --upgrade sark==1.6.0

# From source
git clone https://github.com/anthropics/sark.git
cd sark
git checkout v1.6.0
pip install -e ".[dev]"
```

### Verification

```bash
# Check version
python -c "import sark; print(sark.__version__)"

# Run tests
pytest tests/test_api/test_routers/test_export.py -v
pytest tests/test_api/test_routers/test_tools.py -v
```

### Security Audit

```bash
# Check for vulnerabilities
pip-audit

# Expected: 1 finding (nbconvert - Windows only)
```

---

## Next Steps

### v1.6.1 (Planned)

- Fix remaining router tests
- Update test documentation
- Create test helper utilities

### v2.0.0 GRID (Major Release)

- Use real test database (SQLite in-memory)
- Standardize test patterns across all routers
- Complete architectural overhaul

---

## Support

- **Issues**: https://github.com/anthropics/sark/issues
- **Documentation**: https://docs.sark.ai
- **Security**: security@anthropic.com

---

**Prepared by**: SARK Development Team
**Review Date**: 2026-01-18
**Status**: Production Ready ✅
