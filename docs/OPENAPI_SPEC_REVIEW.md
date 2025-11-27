# OpenAPI Spec Completeness Review

**Date:** 2025-11-27
**Reviewer:** Engineer 2 (Backend/API Specialist)
**Version:** 0.1.0

## Executive Summary

This document reviews the completeness of the SARK OpenAPI specification for use with UI generation, API client generation, and developer documentation.

## Current State

### ✅ Strengths

1. **Auto-Generated Spec**: FastAPI automatically generates OpenAPI 3.0 spec at `/openapi.json`
2. **Response Models**: Most endpoints use Pydantic models for response validation
3. **Request Models**: All POST/PUT endpoints have well-defined request schemas
4. **Field Validation**: Extensive use of Field() with constraints and descriptions
5. **Documentation Strings**: Most endpoints have docstrings explaining functionality
6. **Tags**: API organized with logical tags (health, authentication, servers, policy, tools, bulk)

### ⚠️ Areas for Improvement

#### 1. Missing Response Models

**Issue**: Some endpoints return `dict[str, Any]` instead of typed response models.

**Affected Endpoints**:
- `GET /api/v1/servers/{server_id}` - Returns dict instead of ServerDetailResponse
- Some authentication endpoints may lack structured responses

**Impact**:
- API clients can't auto-generate strongly-typed response objects
- No validation of response structure
- Harder for UI developers to understand response shape

**Recommendation**: Create Pydantic response models for all endpoints.

---

#### 2. Missing Error Response Models

**Issue**: Error responses are HTTPException with string details, not structured models.

**Current**:
```python
raise HTTPException(status_code=404, detail="Server not found")
```

**Needed**: Structured error response model:
```python
class ErrorResponse(BaseModel):
    error: str
    message: str
    details: dict[str, Any] | None
    request_id: str | None
```

**Impact**:
- Clients can't programmatically parse error details
- Harder to handle errors in UI

**Recommendation**: Define standard error response models and document them in OpenAPI.

---

#### 3. Missing Request/Response Examples

**Issue**: Pydantic models don't include `Config.schema_extra` with examples.

**Current**: Models have field descriptions but no full examples.

**Needed**:
```python
class ServerRegistrationRequest(BaseModel):
    name: str
    transport: str
    # ... fields ...

    class Config:
        schema_extra = {
            "example": {
                "name": "analytics-server",
                "transport": "http",
                "endpoint": "https://analytics.example.com",
                # ... complete example
            }
        }
```

**Impact**:
- OpenAPI spec lacks realistic examples
- API documentation (Swagger UI) less helpful
- Client generators produce less useful code

**Recommendation**: Add examples to all request/response models.

---

#### 4. Incomplete Security Scheme Documentation

**Issue**: Multiple auth methods (JWT, API Key, OIDC, SAML) not fully documented in OpenAPI security schemes.

**Current**: Basic authentication dependency injection.

**Needed**: Explicit security scheme definitions in FastAPI app:
```python
app = FastAPI(
    title="SARK API",
    # ...
    swagger_ui_init_oauth={
        "clientId": "sark-api",
        "scopes": "openid profile email"
    }
)
```

**Impact**:
- Swagger UI can't provide "Try it out" functionality
- API documentation doesn't show auth requirements clearly

**Recommendation**: Add explicit security scheme definitions to OpenAPI spec.

---

#### 5. Missing Endpoint Grouping and Ordering

**Issue**: Endpoints could be better organized with more granular tags.

**Current Tags**: health, authentication, servers, policy, tools, bulk

**Suggested Additional Tags**:
- `sessions` - Session management endpoints
- `api-keys` - API key CRUD operations
- `audit` - Audit log endpoints
- `admin` - Administrative endpoints

**Impact**: Large APIs become hard to navigate in documentation.

**Recommendation**: Review and refine endpoint tags for better organization.

---

#### 6. Missing API Versioning in Paths

**Issue**: Some endpoints use `/api/auth` while others use `/api/v1/auth`.

**Current**:
- `/api/v1/servers`
- `/api/auth` (inconsistent)

**Impact**: API versioning strategy unclear.

**Recommendation**: Standardize on `/api/v1/` prefix for all endpoints.

---

#### 7. Missing Pagination Response Schema

**Issue**: PaginatedResponse is generic but might not show clearly in OpenAPI spec.

**Current**: `PaginatedResponse[ServerListItem]`

**Needed**: Ensure OpenAPI shows the full paginated structure with typed items.

**Recommendation**: Verify generic response models render correctly in OpenAPI spec.

---

## Recommendations Summary

### Priority 1 (Critical for UI Development)

1. **Add Response Models**: Convert all `dict` returns to Pydantic models
   - Affected: `GET /api/v1/servers/{server_id}`, others
   - Estimated effort: 2-3 hours

2. **Add Request/Response Examples**: Add `schema_extra` to all models
   - Affected: All request/response models
   - Estimated effort: 3-4 hours

3. **Standardize Error Responses**: Create ErrorResponse model and use consistently
   - Estimated effort: 2 hours

### Priority 2 (Important for API Client Generation)

4. **Document Security Schemes**: Add explicit OpenAPI security definitions
   - Estimated effort: 1-2 hours

5. **Fix API Versioning**: Standardize all endpoints to `/api/v1/` prefix
   - Estimated effort: 1 hour

### Priority 3 (Nice to Have)

6. **Refine Endpoint Tags**: Better organization of endpoints
   - Estimated effort: 1 hour

7. **Add Operation IDs**: Explicit operation IDs for better client generation
   - Estimated effort: 30 minutes

---

## Implementation Plan

### Phase 1: Response Models (W1-E2-01)

**Files to modify**:
- `src/sark/api/routers/servers.py` - Add ServerDetailResponse
- `src/sark/api/routers/auth.py` - Verify all responses have models
- `src/sark/api/routers/policy.py` - Check response models
- `src/sark/api/routers/tools.py` - Check response models

**Deliverable**: All endpoints return typed Pydantic models.

### Phase 2: Enhanced OpenAPI Config (W3-E2-01)

**Files to modify**:
- `src/sark/api/main.py` - Enhance FastAPI app configuration
  - Add security schemes
  - Add contact info
  - Add license info
  - Add servers configuration
  - Add tags metadata

**Deliverable**: Richer OpenAPI spec metadata.

### Phase 3: Examples (W3-E2-01)

**Files to modify**:
- All Pydantic models in `src/sark/api/routers/`
- Add Config.schema_extra with realistic examples

**Deliverable**: OpenAPI spec with comprehensive examples.

### Phase 4: Error Standardization (W4-E2-01)

**Files to create**:
- `src/sark/api/models/errors.py` - Standard error response models

**Files to modify**:
- All routers to use structured error responses
- Add custom exception handlers

**Deliverable**: Consistent error response format.

---

## Testing Plan

1. **Generate OpenAPI Spec**:
   ```bash
   curl http://localhost:8000/openapi.json > openapi.json
   ```

2. **Validate Spec**:
   ```bash
   npx @redocly/cli lint openapi.json
   ```

3. **Generate API Client**:
   ```bash
   npx @openapitools/openapi-generator-cli generate \
     -i openapi.json \
     -g typescript-fetch \
     -o ./generated-client
   ```

4. **Review Generated Client**: Ensure types are correct and complete.

5. **Test Swagger UI**: Visit `/docs` and test "Try it out" functionality.

---

## Success Metrics

- [ ] All endpoints have typed response models (no `dict[str, Any]`)
- [ ] All models have realistic examples in OpenAPI spec
- [ ] Error responses are standardized and documented
- [ ] Security schemes properly defined in OpenAPI spec
- [ ] API client generation produces clean, typed code
- [ ] Swagger UI shows helpful examples and allows testing
- [ ] OpenAPI spec passes validation with no warnings
- [ ] API versioning is consistent across all endpoints

---

## Appendix: Endpoint Inventory

### Health Endpoints (/health)
- ✅ GET / - Basic health check
- ✅ GET /live - Liveness probe
- ✅ GET /ready - Readiness probe
- ✅ GET /startup - Startup probe
- ✅ GET /detailed - Detailed health check

### Authentication Endpoints (/api/v1/auth)
- ⚠️ GET /providers - List auth providers
- ⚠️ POST /login - Credential-based login
- ⚠️ GET /oidc/login - OIDC initiation
- ⚠️ GET /oidc/callback - OIDC callback
- ⚠️ GET /saml/metadata - SAML metadata
- ⚠️ POST /saml/acs - SAML assertion consumer
- ⚠️ POST /refresh - Refresh token
- ⚠️ POST /revoke - Revoke token
- ⚠️ GET /me - Current user info

### Server Management (/api/v1/servers)
- ✅ POST / - Register server
- ⚠️ GET /{server_id} - Get server details (needs response model)
- ✅ GET / - List servers (paginated)

### Policy (/api/v1/policy)
- ⚠️ POST /evaluate - Evaluate policy

### Tools (/api/v1/tools)
- ⚠️ GET /{tool_id}/sensitivity - Get tool sensitivity
- ⚠️ POST /{tool_id}/sensitivity - Update tool sensitivity
- ⚠️ POST /detect-sensitivity - Detect sensitivity level

### Bulk Operations (/api/v1/bulk)
- ✅ POST /servers/register - Bulk register servers
- ⚠️ POST /servers/status - Bulk update server status

**Legend**:
- ✅ = Has response model and documentation
- ⚠️ = Needs review or improvement
- ❌ = Missing or incomplete

---

## Next Steps

1. Complete this review (W1-E2-01) ✅
2. Create enhancement tasks for Week 3 (W3-E2-01)
3. Implement API client auto-generation pipeline (W3-E2-02)
4. Test generated clients (W3-E2-03)

---

**Review Status**: ✅ Complete
**Next Action**: Proceed to W1-E2-02 (Add MCP FAQs to FAQ.md)
