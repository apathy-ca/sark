# Engineer 2 (Backend/API Specialist) Tasks

**Your Role:** Backend API Development
**Total Tasks:** 3 tasks over 8 weeks
**Estimated Effort:** ~6 days

You're making sure the API supports the new UI and documentation needs.

---

## Your Tasks

### ✅ T1.3 - MCP Code Examples
**Week:** 1
**Duration:** 1 day
**Priority:** P1 (High - needed for documentation)

**What you're building:**
Example MCP server configurations for documentation and tutorials.

**Deliverables:**
1. Create `examples/mcp-servers/` directory

2. **Minimal Server** (`minimal-server.json`):
   ```json
   {
     "name": "minimal-example",
     "transport": "http",
     "endpoint": "http://localhost:9000",
     "version": "2025-06-18",
     "capabilities": ["tools"],
     "tools": [
       {
         "name": "hello_world",
         "description": "Returns a greeting",
         "parameters": {
           "type": "object",
           "properties": {
             "name": {"type": "string"}
           }
         },
         "sensitivity_level": "low"
       }
     ],
     "sensitivity_level": "low"
   }
   ```

3. **Database Server** (`database-server.json`):
   - More realistic example
   - Database query tool
   - Medium sensitivity
   - Multiple tools

4. **API Server** (`api-server.json`):
   - REST API integration
   - High sensitivity tools
   - Resources and prompts

5. **Documentation:**
   - Add examples to `docs/MCP_INTRODUCTION.md`
   - Comment each field explaining its purpose
   - Add to quickstart guide

**Acceptance Criteria:**
- [ ] All examples are valid JSON
- [ ] Examples work with current API
- [ ] Tested via curl/API
- [ ] Well-commented
- [ ] Referenced in documentation

**Claude Code Prompt:**
```
Create example MCP server configurations for SARK documentation.

Build:
1. examples/mcp-servers/minimal-server.json - Simplest possible
2. examples/mcp-servers/database-server.json - Realistic database example
3. examples/mcp-servers/api-server.json - REST API integration example

Make them valid, test them with the API, and add clear comments.
Ensure they're referenced in the documentation.
```

---

### ✅ T3.3 - API Client & Authentication Setup
**Week:** 3
**Duration:** 2 days
**Priority:** P0 (Critical - blocks UI development)

**What you're building:**
API enhancements to support the new UI.

**Deliverables:**
1. **OpenAPI Spec Enhancements:**
   - Review `docs/openapi.yaml` (or generate from FastAPI)
   - Ensure all endpoints documented
   - Add examples for request/response
   - Update descriptions to be UI-friendly

2. **CORS Configuration:**
   - Add CORS middleware to FastAPI app
   - Allow UI origin (http://localhost:3000 for dev)
   - Configure for production origins
   - Proper headers for authentication

3. **UI-Specific Endpoints:**
   Create these new endpoints if needed:
   - `GET /api/v1/ui/dashboard/metrics` - Dashboard stats
   - `GET /api/v1/ui/health` - UI-specific health check
   - `GET /api/v1/users/me` - Current user info
   - `POST /api/v1/auth/refresh` - Token refresh

4. **Session Management:**
   - Token refresh endpoint
   - Token expiration handling
   - CSRF protection (if using cookies)

5. **API Client Generation:**
   - Set up openapi-generator or similar
   - Generate TypeScript client
   - Test generated client
   - Document how to regenerate

**Acceptance Criteria:**
- [ ] OpenAPI spec is complete and accurate
- [ ] CORS works for UI origin
- [ ] UI-specific endpoints implemented
- [ ] TypeScript client can be auto-generated
- [ ] Session management works properly

**Dependencies:**
- Current API codebase

**Claude Code Prompt:**
```
Prepare SARK API for UI integration.

Tasks:
1. Update OpenAPI spec to be complete
2. Add CORS support for UI (localhost:3000 for dev)
3. Create UI-specific endpoints (/api/v1/ui/dashboard/metrics, etc.)
4. Set up API client auto-generation for TypeScript
5. Add token refresh endpoint

Test that CORS works and API client can be generated.
```

---

### ✅ T6.3 - Advanced Features & Export
**Week:** 6
**Duration:** 2 days
**Priority:** P1 (High)

**What you're building:**
Advanced API features that the UI needs.

**Deliverables:**
1. **Export Endpoints:**
   - `GET /api/v1/audit/export?format=csv&start_date=X&end_date=Y`
   - `GET /api/v1/servers/export?format=json`
   - `GET /api/v1/policies/export`
   - Support CSV and JSON formats
   - Streaming for large exports
   - Proper Content-Disposition headers

2. **WebSocket Support for Real-Time Updates:**
   - WebSocket endpoint: `ws://localhost:8000/ws`
   - Events to push:
     - New audit events
     - Server status changes
     - Policy decision metrics updates
   - Authentication for WebSocket connections
   - Graceful disconnect handling

3. **Batch Operations:**
   - `POST /api/v1/servers/batch` - Register multiple servers
   - `POST /api/v1/policies/batch` - Deploy multiple policies
   - Progress tracking
   - Partial success handling

4. **Policy Testing API:**
   - `POST /api/v1/policies/test` - Test policy without saving
   - Input: policy code + test input
   - Output: decision + reason + execution time
   - Validation errors

**Acceptance Criteria:**
- [ ] Export endpoints work for large datasets
- [ ] WebSocket real-time updates work
- [ ] Batch operations handle errors gracefully
- [ ] Policy testing API is fast (<100ms)
- [ ] Proper error messages for all failures

**Dependencies:**
- Existing API infrastructure

**Claude Code Prompt:**
```
Add advanced API features for SARK UI.

Build:
1. Export endpoints for audit logs, servers, policies (CSV and JSON)
2. WebSocket support for real-time updates (audit events, server status)
3. Batch operation endpoints (bulk server registration, policy deployment)
4. Policy testing endpoint (test without saving)

Ensure good performance and error handling.
Use FastAPI WebSocket support for real-time features.
```

---

## Your Timeline

| Week | Task | Duration | Focus |
|------|------|----------|-------|
| **1** | T1.3 | 1 day | MCP examples |
| **3** | T3.3 | 2 days | API client & CORS |
| **6** | T6.3 | 2 days | Advanced features |

## Your Responsibilities

### API Support
- Keep API stable as UI develops
- Add endpoints as UI team requests
- Ensure good error messages
- Maintain API documentation

### Code Reviews
- Review Engineer 3's API integration code
- Review Engineer 4's Docker/K8s configs
- Ensure API best practices

### Performance
- Monitor API performance
- Optimize slow endpoints
- Add caching where appropriate

## Tips for Success

### Working with Frontend
- Provide clear error messages (UI will display them)
- Use standard HTTP status codes
- Include helpful details in errors:
  ```json
  {
    "error": "Invalid server configuration",
    "details": "Field 'endpoint' must be a valid URL",
    "field": "endpoint"
  }
  ```

### WebSocket Best Practices
- Authenticate connections
- Limit event rate (don't spam)
- Handle disconnects gracefully
- Provide reconnection logic

### Export Endpoints
- Stream large exports (don't load all in memory)
- Add pagination or limits
- Provide progress indicators
- Set appropriate timeouts

### Testing
- Test with realistic data volumes
- Test error cases
- Load test export endpoints
- Verify WebSocket stability

---

**You're the API guardian - make it solid and reliable!** 🛡️
