# SARK v1.2.0 Implementation Plan
## Gateway Implementation + Policy Validation + Test Fixes

**Version:** 1.0
**Date:** December 9, 2025
**Target Release:** v1.2.0
**Duration:** 8 weeks
**Orchestration:** Czarina multi-agent system
**Repository:** https://github.com/apathy-ca/sark

---

## Executive Summary

This document provides a detailed implementation plan for SARK v1.2.0, designed for parallel execution using the Czarina orchestration system. Work is divided into **4 independent streams** that can run concurrently, with clear dependencies and integration points.

**What v1.2.0 Delivers:**
- ✅ Fully functional Gateway client (HTTP, SSE, stdio transports)
- ✅ Policy validation framework (prevents policy injection)
- ✅ 100% test pass rate (fix 154 failing auth tests)
- ✅ 85%+ code coverage
- ✅ End-to-end integration verified

**Success Criteria:**
- Gateway client can communicate with real MCP servers
- All policies validated before loading into OPA
- All tests passing in CI/CD
- Performance: <100ms p95 latency for Gateway operations
- Code coverage ≥85%

---

## Work Stream Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CZARINA ORCHESTRATION                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Stream 1: Gateway HTTP/SSE    Stream 2: Gateway stdio          │
│  ┌──────────────────┐          ┌──────────────────┐            │
│  │ Worker: GATEWAY-1│          │ Worker: GATEWAY-2│            │
│  │ Weeks 1-2        │          │ Week 3           │            │
│  │ +HTTP transport  │          │ +stdio transport │            │
│  │ +SSE transport   │          │ +Process mgmt    │            │
│  └──────────────────┘          └──────────────────┘            │
│           │                              │                       │
│           └──────────┬───────────────────┘                       │
│                      ▼                                           │
│          Stream 3: Integration & Tests                          │
│          ┌──────────────────────┐                               │
│          │ Worker: INTEGRATION  │                               │
│          │ Week 4               │                               │
│          │ +Unified client      │                               │
│          │ +E2E tests           │                               │
│          └──────────────────────┘                               │
│                                                                   │
│  Stream 4: Policy Validation   Stream 5: Test Fixes            │
│  ┌──────────────────┐          ┌──────────────────┐            │
│  │ Worker: POLICY   │          │ Worker: QA       │            │
│  │ Weeks 5-6        │          │ Weeks 7-8        │            │
│  │ +Validator       │          │ +Fix auth tests  │            │
│  │ +Test framework  │          │ +Coverage boost  │            │
│  └──────────────────┘          └──────────────────┘            │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

**Parallelization Strategy:**
- **Weeks 1-3:** Streams 1 & 2 run in parallel (independent)
- **Week 4:** Stream 3 integrates Streams 1 & 2
- **Weeks 5-6:** Stream 4 runs independently
- **Weeks 7-8:** Stream 5 runs independently

**Total Worker-Weeks:** 8 calendar weeks, ~10 worker-weeks of effort

---

## Stream 1: Gateway HTTP & SSE Transport (GATEWAY-1)

**Worker Assignment:** `GATEWAY-1` (Aider or Windsurf recommended for high autonomy)
**Duration:** Weeks 1-2 (2 weeks)
**Branch:** `feat/gateway-http-sse-transport`
**Dependencies:** None (can start immediately)
**Estimated Effort:** 2 weeks, 1 worker

### Week 1: HTTP Transport Implementation

**Goal:** Complete HTTP transport for MCP server communication

#### Tasks

**Task 1.1: HTTP Client Foundation** (1 day)
- **File:** `src/sark/gateway/transports/http_client.py` (NEW)
- **Implementation:**
  ```python
  class HTTPTransport:
      """HTTP transport for MCP protocol"""

      def __init__(self, base_url: str, timeout: int = 30):
          self.base_url = base_url
          self.timeout = timeout
          self.http_client = httpx.AsyncClient(timeout=timeout)
          self.cache = TTLCache(maxsize=1000, ttl=300)  # 5-minute TTL

      async def list_servers(self, user_id: Optional[str] = None) -> list[GatewayServerInfo]:
          """Query MCP servers via HTTP with pagination"""
          # Implementation here

      async def get_server_info(self, server_id: str) -> Optional[GatewayServerInfo]:
          """Fetch server metadata"""
          # Implementation here
  ```

- **Acceptance Criteria:**
  - [ ] AsyncHTTP client with timeout configured
  - [ ] Connection pooling enabled (max 100 connections)
  - [ ] TTL cache implementation (5-minute default)
  - [ ] Error handling for connection failures

**Task 1.2: Server Discovery** (1 day)
- **File:** `src/sark/gateway/transports/http_client.py`
- **Implementation:**
  - `list_servers()` - Query MCP registry endpoint
  - Handle pagination (max 100 servers per page)
  - Filter by user permissions (integrate with OPA)
  - Cache results with 5-minute TTL

- **Acceptance Criteria:**
  - [ ] Pagination works for 1000+ servers
  - [ ] User permission filtering functional
  - [ ] Cache hit rate >80% in tests
  - [ ] Response time <50ms for cached queries

**Task 1.3: Tool Discovery** (1 day)
- **File:** `src/sark/gateway/transports/http_client.py`
- **Implementation:**
  - `list_tools(server_id)` - MCP `tools/list` endpoint
  - Parse tool schemas and metadata
  - Cache tool lists per server
  - Handle tool schema validation

- **Acceptance Criteria:**
  - [ ] Correctly parses MCP tool schemas
  - [ ] Validates tool parameter types
  - [ ] Caches tool lists per server
  - [ ] Response time <100ms

**Task 1.4: Tool Invocation** (2 days)
- **File:** `src/sark/gateway/transports/http_client.py`
- **Implementation:**
  - `invoke_tool()` - Execute tool with full authorization flow
  - Integrate with OPA for authorization
  - Apply parameter filtering from OPA response
  - Audit log all invocations
  - Handle errors and retries

- **Acceptance Criteria:**
  - [ ] Authorization flow integrated with OPA
  - [ ] Parameter filtering applied correctly
  - [ ] All invocations logged to audit system
  - [ ] Retry logic with exponential backoff
  - [ ] Circuit breaker after 5 consecutive failures

**Task 1.5: Unit Tests** (1 day)
- **File:** `tests/unit/gateway/transports/test_http_client.py` (NEW)
- **Coverage:**
  - Server discovery with pagination
  - Tool listing and caching
  - Tool invocation with authorization
  - Error handling scenarios
  - Cache behavior

- **Acceptance Criteria:**
  - [ ] 20+ unit tests
  - [ ] 90%+ code coverage for HTTP transport
  - [ ] All edge cases covered
  - [ ] Mock OPA and MCP server responses

### Week 2: SSE (Server-Sent Events) Transport

**Goal:** Implement streaming support via SSE

**Task 2.1: SSE Client Infrastructure** (2 days)
- **File:** `src/sark/gateway/transports/sse_client.py` (NEW)
- **Implementation:**
  ```python
  class SSETransport:
      """Server-Sent Events transport for streaming MCP responses"""

      def __init__(self, base_url: str, max_connections: int = 50):
          self.base_url = base_url
          self.connection_pool = ConnectionPool(max_connections)
          self.reconnect_delay = 1.0  # exponential backoff

      async def invoke_tool_streaming(
          self,
          server_id: str,
          tool_name: str,
          params: dict,
          user_context: dict
      ) -> AsyncIterator[GatewayToolResult]:
          """Stream tool results via SSE"""
          # Implementation here
  ```

- **Acceptance Criteria:**
  - [ ] Async SSE client implementation
  - [ ] Connection pooling (max 50 concurrent)
  - [ ] Automatic reconnection with exponential backoff
  - [ ] Event parsing and deserialization

**Task 2.2: Streaming Tool Invocation** (2 days)
- **File:** `src/sark/gateway/transports/sse_client.py`
- **Implementation:**
  - `invoke_tool_streaming()` - Real-time streaming
  - Async iteration over SSE events
  - Partial result handling
  - Stream cancellation on timeout/error
  - Authorization check before streaming

- **Acceptance Criteria:**
  - [ ] Can stream 100+ events per invocation
  - [ ] Handles stream cancellation gracefully
  - [ ] Timeout triggers cleanup (30s default)
  - [ ] Authorization integrated

**Task 2.3: Connection Management** (1 day)
- **File:** `src/sark/gateway/transports/sse_client.py`
- **Implementation:**
  - Connection pooling logic
  - Heartbeat/keepalive handling
  - Resource cleanup on disconnect
  - Connection health monitoring

- **Acceptance Criteria:**
  - [ ] Connection pool prevents resource exhaustion
  - [ ] Heartbeat detects dead connections (<30s)
  - [ ] All connections cleaned up properly
  - [ ] No memory leaks under load

**Task 2.4: Unit Tests** (1 day)
- **File:** `tests/unit/gateway/transports/test_sse_client.py` (NEW)
- **Coverage:**
  - SSE event parsing
  - Streaming invocation
  - Reconnection logic
  - Connection pooling
  - Error scenarios

- **Acceptance Criteria:**
  - [ ] 15+ unit tests
  - [ ] 90%+ code coverage for SSE transport
  - [ ] Mock SSE server for tests
  - [ ] Reconnection scenarios tested

### Deliverables

**Code:**
- ✅ `src/sark/gateway/transports/http_client.py` - HTTP transport (200+ lines)
- ✅ `src/sark/gateway/transports/sse_client.py` - SSE transport (150+ lines)
- ✅ `tests/unit/gateway/transports/test_http_client.py` - HTTP tests (300+ lines)
- ✅ `tests/unit/gateway/transports/test_sse_client.py` - SSE tests (200+ lines)

**Documentation:**
- ✅ `docs/gateway/HTTP_TRANSPORT.md` - Usage guide
- ✅ `docs/gateway/SSE_TRANSPORT.md` - Streaming guide

**Acceptance:**
- [ ] All unit tests passing
- [ ] Code coverage ≥90% for new code
- [ ] Peer review completed
- [ ] Documentation reviewed

---

## Stream 2: Gateway stdio Transport (GATEWAY-2)

**Worker Assignment:** `GATEWAY-2` (Aider or Windsurf recommended)
**Duration:** Week 3 (1 week)
**Branch:** `feat/gateway-stdio-transport`
**Dependencies:** None (can run parallel to Stream 1)
**Estimated Effort:** 1 week, 1 worker

### Week 3: stdio Transport Implementation

**Goal:** Implement subprocess-based MCP communication

**Task 3.1: Stdio Client Foundation** (2 days)
- **File:** `src/sark/gateway/transports/stdio_client.py` (NEW)
- **Implementation:**
  ```python
  class StdioTransport:
      """Subprocess-based MCP transport via stdin/stdout"""

      def __init__(self):
          self.processes: dict[str, asyncio.subprocess.Process] = {}
          self.message_queues: dict[str, asyncio.Queue] = {}

      async def start_server(self, command: list[str], env: dict) -> str:
          """Start MCP server process"""
          # Implementation here

      async def invoke_tool(self, server_id: str, tool_name: str, params: dict):
          """Send JSON-RPC request via stdio"""
          # Implementation here
  ```

- **Acceptance Criteria:**
  - [ ] Subprocess creation and management
  - [ ] JSON-RPC message handling over stdin/stdout
  - [ ] Process lifecycle (start, stop, restart)
  - [ ] Error handling for crashed processes

**Task 3.2: Process Health & Resource Management** (2 days)
- **File:** `src/sark/gateway/transports/stdio_client.py`
- **Implementation:**
  - Process health checks (heartbeat every 10s)
  - Resource limits (memory: 1GB, CPU: 80%, file descriptors: 1000)
  - Graceful shutdown handling
  - Zombie process prevention
  - Process restart on crash

- **Acceptance Criteria:**
  - [ ] Health checks detect hung processes (<15s)
  - [ ] Resource limits enforced via cgroups
  - [ ] No zombie processes created
  - [ ] Clean shutdown on SIGTERM
  - [ ] Auto-restart on crash (max 3 attempts)

**Task 3.3: Unit Tests** (1 day)
- **File:** `tests/unit/gateway/transports/test_stdio_client.py` (NEW)
- **Coverage:**
  - Process lifecycle
  - JSON-RPC communication
  - Health checks
  - Resource limits
  - Error scenarios

- **Acceptance Criteria:**
  - [ ] 15+ unit tests
  - [ ] 90%+ code coverage
  - [ ] Process cleanup verified
  - [ ] No leaked file descriptors

### Deliverables

**Code:**
- ✅ `src/sark/gateway/transports/stdio_client.py` - stdio transport (180+ lines)
- ✅ `tests/unit/gateway/transports/test_stdio_client.py` - stdio tests (200+ lines)

**Documentation:**
- ✅ `docs/gateway/STDIO_TRANSPORT.md` - Usage guide

**Acceptance:**
- [ ] All unit tests passing
- [ ] Code coverage ≥90%
- [ ] No process leaks in tests
- [ ] Documentation complete

---

## Stream 3: Gateway Integration & E2E Testing (INTEGRATION)

**Worker Assignment:** `INTEGRATION` (Claude Code or Cursor recommended for complex integration)
**Duration:** Week 4 (1 week)
**Branch:** `feat/gateway-integration`
**Dependencies:** Streams 1 & 2 must be complete
**Estimated Effort:** 1 week, 1 worker

### Week 4: Unified Client & End-to-End Testing

**Goal:** Integrate all transports and verify end-to-end functionality

**Task 4.1: Unified Gateway Client** (2 days)
- **File:** `src/sark/gateway/client.py` (UPDATE)
- **Implementation:**
  ```python
  class GatewayClient:
      """Unified Gateway client supporting all transports"""

      def __init__(self, config: GatewayConfig):
          self.http_transport = HTTPTransport(config.http_url)
          self.sse_transport = SSETransport(config.sse_url)
          self.stdio_transport = StdioTransport()
          self.error_handler = GatewayErrorHandler()

      async def invoke_tool(self, server_id: str, tool_name: str, params: dict):
          """Route to appropriate transport based on server config"""
          transport = self._select_transport(server_id)
          return await transport.invoke_tool(server_id, tool_name, params)
  ```

- **Acceptance Criteria:**
  - [ ] Automatic transport selection
  - [ ] Unified error handling across transports
  - [ ] Circuit breaker pattern (5 failures → open)
  - [ ] Retry logic with exponential backoff

**Task 4.2: Comprehensive Error Handling** (1 day)
- **File:** `src/sark/gateway/error_handler.py` (NEW)
- **Implementation:**
  - Timeout handling (30s default)
  - Network error retry (3 attempts, exponential backoff)
  - Authorization failure handling (no retry)
  - Circuit breaker implementation
  - Error categorization and logging

- **Acceptance Criteria:**
  - [ ] All error types handled
  - [ ] Circuit breaker opens after 5 failures
  - [ ] Retries only on retryable errors
  - [ ] Errors logged with full context

**Task 4.3: End-to-End Integration Tests** (3 days)
- **File:** `tests/integration/gateway/test_gateway_e2e.py` (NEW)
- **Implementation:**
  - Real MCP server testing (use mock MCP server)
  - Full authorization flow validation
  - Parameter filtering verification
  - Audit logging confirmation
  - Performance benchmarks (<100ms p95)

- **Test Scenarios:**
  1. HTTP: Successful tool invocation with authorization
  2. HTTP: Denied invocation (insufficient permissions)
  3. HTTP: Parameter filtering for non-admin user
  4. SSE: Streaming tool invocation
  5. stdio: Local MCP server invocation
  6. Circuit breaker: Multiple failures trigger open state
  7. Retry: Network errors retry with backoff
  8. Cache: Repeated queries hit cache
  9. Audit: All invocations logged correctly
  10. Performance: p95 latency <100ms

- **Acceptance Criteria:**
  - [ ] 50+ integration tests
  - [ ] All transports tested end-to-end
  - [ ] Authorization flow verified
  - [ ] Performance targets met
  - [ ] Audit logs validated

### Deliverables

**Code:**
- ✅ `src/sark/gateway/client.py` - Updated unified client
- ✅ `src/sark/gateway/error_handler.py` - Error handling
- ✅ `tests/integration/gateway/test_gateway_e2e.py` - E2E tests (500+ lines)

**Documentation:**
- ✅ `docs/gateway/CLIENT_USAGE.md` - Usage examples
- ✅ `docs/gateway/ERROR_HANDLING.md` - Error scenarios

**Acceptance:**
- [ ] All integration tests passing
- [ ] Performance benchmarks met
- [ ] Authorization verified end-to-end
- [ ] Documentation complete

---

## Stream 4: Policy Validation Framework (POLICY)

**Worker Assignment:** `POLICY` (Aider or Continue.dev recommended)
**Duration:** Weeks 5-6 (2 weeks)
**Branch:** `feat/policy-validation`
**Dependencies:** None (runs independently)
**Estimated Effort:** 2 weeks, 1 worker

### Week 5: Policy Validator Implementation

**Goal:** Build policy validation engine to prevent policy injection

**Task 5.1: Policy Validation Engine** (3 days)
- **File:** `src/sark/policy/validator.py` (NEW)
- **Implementation:**
  ```python
  class PolicyValidator:
      """Validates OPA policies before loading"""

      REQUIRED_RULES = ["allow", "deny"]
      FORBIDDEN_PATTERNS = [
          r"allow\s*:=\s*true\s*$",  # Blanket allow
          r"import\s+data\.system",   # System data access
          r"http\.send",               # External HTTP calls
      ]

      async def validate_policy(self, policy_rego: str) -> PolicyValidationResult:
          """Validate policy syntax and safety"""
          # 1. Syntax validation via OPA CLI
          # 2. Required rules check
          # 3. Forbidden patterns detection
          # 4. Test with sample inputs
          # Implementation here
  ```

- **Acceptance Criteria:**
  - [ ] Syntax validation via `opa check`
  - [ ] Required rules verification (allow, deny)
  - [ ] 10+ forbidden patterns detected
  - [ ] Sample input testing framework

**Task 5.2: Policy Testing Framework** (2 days)
- **File:** `src/sark/policy/test_runner.py` (NEW)
- **Implementation:**
  ```python
  class PolicyTestRunner:
      """Run unit tests for OPA policies"""

      async def run_tests(self, policy_rego: str, test_suite: dict) -> PolicyTestResult:
          """Execute policy tests defined in YAML"""
          # Load policy into OPA
          # Run test cases
          # Compare expected vs actual
          # Implementation here
  ```

- **Acceptance Criteria:**
  - [ ] YAML test suite format defined
  - [ ] Test execution via OPA evaluate
  - [ ] Expected/actual comparison
  - [ ] Test report generation

**Task 5.3: Unit Tests** (1 day)
- **File:** `tests/unit/policy/test_validator.py` (NEW)
- **Coverage:**
  - Valid policy accepted
  - Invalid syntax rejected
  - Forbidden patterns detected
  - Required rules enforced
  - Test runner functionality

- **Acceptance Criteria:**
  - [ ] 20+ unit tests
  - [ ] 90%+ code coverage
  - [ ] Malicious policy examples rejected
  - [ ] Safe policies accepted

### Week 6: Integration & Policy Migration

**Goal:** Integrate validator and validate all existing policies

**Task 6.1: Integrate Validator into Loading Pipeline** (2 days)
- **File:** `src/sark/policy/loader.py` (UPDATE)
- **Implementation:**
  ```python
  async def load_policy(self, name: str, policy_rego: str):
      # 1. Validate before loading
      validation = await self.validator.validate_policy(policy_rego)

      if not validation.valid:
          raise PolicyValidationError(f"Validation failed: {validation.errors}")

      # 2. Log warnings
      for warning in validation.warnings:
          logger.warning(f"Policy warning: {warning}")

      # 3. Load into OPA
      await self.opa_client.load_policy(name, policy_rego)

      # 4. Audit log
      await self.audit_logger.log_event(...)
  ```

- **Acceptance Criteria:**
  - [ ] Validator integrated into policy loading
  - [ ] Invalid policies rejected with errors
  - [ ] Warnings logged
  - [ ] Audit log captures policy loads

**Task 6.2: Validate Existing Policies** (2 days)
- **Files:** `opa_policies/*.rego`
- **Tasks:**
  - Run validator against all current policies
  - Fix policies that fail validation
  - Create test suites for all policies
  - Document policy changes

- **Acceptance Criteria:**
  - [ ] 100% of policies pass validation
  - [ ] Test suites created for all policies
  - [ ] Changes documented
  - [ ] No security regressions

**Task 6.3: Documentation** (1 day)
- **File:** `docs/POLICY_AUTHORING_GUIDE.md` (NEW)
- **Content:**
  - Policy safety requirements
  - Common mistakes to avoid
  - Example safe policies
  - Forbidden patterns reference
  - Testing best practices

- **Acceptance Criteria:**
  - [ ] Guide covers all validation rules
  - [ ] Examples for common scenarios
  - [ ] Troubleshooting section
  - [ ] Reviewed by security team

### Deliverables

**Code:**
- ✅ `src/sark/policy/validator.py` - Policy validator (200+ lines)
- ✅ `src/sark/policy/test_runner.py` - Test runner (150+ lines)
- ✅ `src/sark/policy/loader.py` - Updated loader
- ✅ `tests/unit/policy/test_validator.py` - Tests (250+ lines)
- ✅ `opa_policies/tests/*.yaml` - Policy test suites

**Documentation:**
- ✅ `docs/POLICY_AUTHORING_GUIDE.md` - Authoring guide
- ✅ `docs/POLICY_VALIDATION.md` - Validation reference

**Acceptance:**
- [ ] All unit tests passing
- [ ] All existing policies validated
- [ ] Documentation complete
- [ ] Security team approval

---

## Stream 5: Test Fixes & Coverage Improvement (QA)

**Worker Assignment:** `QA` (Aider recommended for test automation)
**Duration:** Weeks 7-8 (2 weeks)
**Branch:** `fix/auth-tests-and-coverage`
**Dependencies:** None (runs independently)
**Estimated Effort:** 2 weeks, 1 worker

### Week 7: Fix Auth Provider Tests

**Goal:** Fix 154 failing auth provider tests (100% pass rate)

**Task 7.1: Fix LDAP Auth Provider Tests** (2 days)
- **File:** `tests/test_auth_providers.py`
- **Issue:** Mock LDAP server not starting correctly
- **Solution:**
  - Replace mock with `pytest-docker` for real LDAP container
  - Use `osixia/openldap:1.5.0` Docker image
  - Configure test LDAP data
  - Fix 52 LDAP test failures

- **Acceptance Criteria:**
  - [ ] Docker-based LDAP test infrastructure
  - [ ] All 52 LDAP tests passing
  - [ ] Test data fixtures created
  - [ ] Docker cleanup on test completion

**Task 7.2: Fix SAML Auth Provider Tests** (2 days)
- **File:** `tests/test_auth_providers.py`
- **Issue:** XML signature validation failing
- **Solution:**
  - Correct certificate format in test fixtures
  - Update SAML assertion templates
  - Fix XML canonicalization
  - Fix 48 SAML test failures

- **Acceptance Criteria:**
  - [ ] All 48 SAML tests passing
  - [ ] Certificate fixtures correct
  - [ ] SAML assertions valid
  - [ ] Signature validation working

**Task 7.3: Fix OIDC Auth Provider Tests** (1 day)
- **File:** `tests/test_auth_providers.py`
- **Issue:** Token expiry validation off by 1 second
- **Solution:**
  - Use `freezegun` for time mocking
  - Fix timing-sensitive assertions
  - Fix 54 OIDC test failures

- **Acceptance Criteria:**
  - [ ] All 54 OIDC tests passing
  - [ ] Time mocking consistent
  - [ ] No timing race conditions
  - [ ] Tests deterministic

### Week 8: Improve Test Coverage

**Goal:** Achieve 85%+ code coverage with comprehensive tests

**Task 8.1: Add Missing Unit Tests** (2 days)
- **Files:** `tests/unit/test_*.py`
- **Coverage Areas:**
  - Gateway authorization logic
  - Parameter filtering edge cases
  - Cache TTL calculations
  - Rate limiting enforcement
  - Error handling paths

- **Acceptance Criteria:**
  - [ ] 50+ new unit tests
  - [ ] Coverage increase of 10-15%
  - [ ] All edge cases covered
  - [ ] Mock dependencies properly

**Task 8.2: Add End-to-End Scenario Tests** (3 days)
- **File:** `tests/e2e/test_scenarios.py` (NEW)
- **Scenarios:**
  1. **Sensitive Data Access:**
     - Admin can access critical resources
     - Developer cannot access critical resources
     - Sensitive parameters filtered for non-admin

  2. **Prompt Injection Blocking:**
     - Malicious parameters detected (future)
     - Legitimate requests allowed

  3. **Multi-Layer Authorization:**
     - User authentication → API key check → OPA policy → Tool invocation
     - Each layer verified independently

  4. **Audit Log Verification:**
     - All events logged correctly
     - SIEM forwarding working
     - Log immutability verified

  5. **Performance Under Load:**
     - 100 concurrent requests handled
     - p95 latency <100ms
     - No resource leaks

- **Acceptance Criteria:**
  - [ ] 20+ E2E scenario tests
  - [ ] All critical workflows covered
  - [ ] Performance benchmarks met
  - [ ] Tests run in CI/CD

### Deliverables

**Code:**
- ✅ `tests/test_auth_providers.py` - Fixed auth tests
- ✅ `tests/unit/test_*.py` - Additional unit tests
- ✅ `tests/e2e/test_scenarios.py` - E2E scenarios (400+ lines)
- ✅ `tests/fixtures/ldap_docker.py` - LDAP test infrastructure

**Documentation:**
- ✅ `tests/README.md` - Test documentation
- ✅ `docs/testing/E2E_SCENARIOS.md` - Scenario guide

**Acceptance:**
- [ ] 100% test pass rate
- [ ] 85%+ code coverage
- [ ] All scenarios documented
- [ ] CI/CD green

---

## Integration Points & Dependencies

### Dependency Graph

```
Stream 1 (HTTP/SSE) ────┐
                         ├──► Stream 3 (Integration) ──► v1.2.0 Release
Stream 2 (stdio) ────────┘

Stream 4 (Policy) ──────────────────────────────────────► v1.2.0 Release

Stream 5 (Tests) ───────────────────────────────────────► v1.2.0 Release
```

### Integration Schedule

**Week 4 End:**
- Merge Stream 1 → `main`
- Merge Stream 2 → `main`
- Merge Stream 3 → `main`
- **Milestone:** Gateway fully functional

**Week 6 End:**
- Merge Stream 4 → `main`
- **Milestone:** Policy validation complete

**Week 8 End:**
- Merge Stream 5 → `main`
- **Milestone:** All tests passing, coverage ≥85%
- **Release:** v1.2.0 🎉

### Cross-Stream Communication

**Daily Sync (Automated via Czarina):**
- Status updates from each worker
- Blocker identification
- Dependency coordination

**Integration Points:**
- Week 3 end: Stream 1 & 2 code review
- Week 4 start: Integration worker merges branches
- Week 4 end: E2E tests validate integration
- Week 8 end: Final integration and release prep

---

## Czarina Configuration

### `.czarina/config.json`

```json
{
  "project": "sark",
  "version": "1.2.0",
  "workers": {
    "gateway-1": {
      "branch": "feat/gateway-http-sse-transport",
      "agent": "aider",
      "autonomy": "high",
      "budget": {
        "tokens": 5000000,
        "weeks": 2
      }
    },
    "gateway-2": {
      "branch": "feat/gateway-stdio-transport",
      "agent": "aider",
      "autonomy": "high",
      "budget": {
        "tokens": 2500000,
        "weeks": 1
      }
    },
    "integration": {
      "branch": "feat/gateway-integration",
      "agent": "cursor",
      "autonomy": "medium",
      "budget": {
        "tokens": 3000000,
        "weeks": 1
      },
      "dependencies": ["gateway-1", "gateway-2"]
    },
    "policy": {
      "branch": "feat/policy-validation",
      "agent": "aider",
      "autonomy": "high",
      "budget": {
        "tokens": 3500000,
        "weeks": 2
      }
    },
    "qa": {
      "branch": "fix/auth-tests-and-coverage",
      "agent": "aider",
      "autonomy": "high",
      "budget": {
        "tokens": 3000000,
        "weeks": 2
      }
    }
  },
  "daemon": {
    "auto_approve": true,
    "patterns": ["test", "docs", "implementation"]
  }
}
```

### Worker Prompts

**`.czarina/workers/gateway-1.md`**
```markdown
# Gateway HTTP/SSE Transport Worker

You are GATEWAY-1, responsible for implementing HTTP and SSE transports for SARK Gateway.

## Your Mission (Weeks 1-2)

Implement fully functional HTTP and SSE transports that enable SARK to communicate with real MCP servers.

## Week 1: HTTP Transport
- Implement `src/sark/gateway/transports/http_client.py`
- Server discovery with pagination
- Tool listing and invocation
- Full OPA authorization integration
- Write 20+ unit tests

## Week 2: SSE Transport
- Implement `src/sark/gateway/transports/sse_client.py`
- Streaming tool invocation
- Connection pooling and management
- Write 15+ unit tests

## Success Criteria
- All unit tests passing
- 90%+ code coverage
- Performance: <100ms p95 latency
- Documentation complete

## Reference
- See `docs/v1.2.0/IMPLEMENTATION_PLAN.md` Section "Stream 1"
- Architecture: `docs/ARCHITECTURE.md`
- Gateway spec: `docs/gateway/SPECIFICATION.md`
```

**`.czarina/workers/gateway-2.md`** (similar structure)
**`.czarina/workers/integration.md`** (similar structure)
**`.czarina/workers/policy.md`** (similar structure)
**`.czarina/workers/qa.md`** (similar structure)

---

## Testing Strategy

### Unit Tests (200+ total)
- **Gateway HTTP:** 20 tests
- **Gateway SSE:** 15 tests
- **Gateway stdio:** 15 tests
- **Policy Validator:** 20 tests
- **Auth Providers:** 154 tests (fixed)
- **Additional Coverage:** 50 tests

**Target:** 90%+ coverage for new code

### Integration Tests (50+ total)
- **Gateway E2E:** 10 scenarios × 3 transports = 30 tests
- **Policy Validation:** 10 tests
- **Performance:** 10 benchmarks

**Target:** All critical paths covered

### E2E Scenario Tests (20+ total)
- Sensitive data access workflows
- Multi-layer authorization
- Audit logging verification
- Performance under load

**Target:** Real-world usage validated

---

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Gateway Tool Invocation (p95)** | <100ms | Load testing |
| **Policy Validation** | <50ms | Unit tests |
| **Cache Hit Rate** | >80% | Integration tests |
| **Concurrent Requests** | 100+ | Load testing |
| **Test Pass Rate** | 100% | CI/CD |
| **Code Coverage** | ≥85% | pytest-cov |

---

## Risk Management

### Critical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Gateway implementation complexity** | High | Start with HTTP (simplest), add transports incrementally |
| **MCP protocol changes** | Medium | Pin to specific MCP version, monitor spec updates |
| **Test infrastructure issues** | Medium | Use Docker for consistency, document setup |
| **Integration delays** | High | Clear interfaces between streams, integration worker buffers time |
| **Policy validation breaks policies** | High | Extensive testing, gradual rollout, rollback plan |

### Contingency Plans

**If Gateway takes >4 weeks:**
- Ship HTTP-only transport for v1.2.0
- Defer SSE/stdio to v1.2.1

**If test failures block progress:**
- Isolate failing tests (skip temporarily)
- Focus on critical path tests first
- Address non-critical tests in v1.2.1

**If integration issues arise:**
- Integration worker extends by 1 week
- Delay release by 1 week if needed

---

## Success Metrics

### v1.2.0 Release Criteria

**Functionality:**
- [ ] Gateway client fully functional (HTTP, SSE, stdio)
- [ ] Policy validation framework operational
- [ ] All tests passing (100% pass rate)

**Quality:**
- [ ] Code coverage ≥85%
- [ ] Performance targets met (<100ms p95)
- [ ] Documentation complete

**Security:**
- [ ] Policy injection risk mitigated
- [ ] Authorization verified end-to-end
- [ ] Audit logging working

**Process:**
- [ ] All worker streams complete
- [ ] Integration successful
- [ ] Peer reviews done
- [ ] CI/CD green

---

## Timeline Summary

```
Week 1:  Stream 1 (HTTP)      | Stream 2 starts
Week 2:  Stream 1 (SSE)       | Stream 2 (stdio)
Week 3:  Stream 2 complete    | Stream 1 complete
Week 4:  Stream 3 (Integration) ← Depends on 1 & 2
Week 5:  Stream 4 (Policy)    | Independent
Week 6:  Stream 4 complete    |
Week 7:  Stream 5 (QA)        | Independent
Week 8:  Stream 5 complete    | v1.2.0 RELEASE 🎉
```

**Parallel Efficiency:**
- Calendar weeks: 8
- Worker-weeks: ~10
- Speedup: ~25% via parallelization

---

## Post-Release

### v1.2.0 → v1.3.0 Planning
After v1.2.0 release, begin planning for advanced Lethal Trifecta mitigations (v1.3.0):
- Prompt injection detection
- Anomaly detection
- Network-level controls
- Secret scanning
- MFA for critical actions

**Timeline:** Q2 2026 (7-8 weeks)

### v1.2.0 → v2.0.0 Path
With v1.2.0 complete, proceed to security audit preparation:
- Internal security review
- External penetration testing
- Remediation and re-test
- Production deployment

**Timeline:** Weeks 9-15 of overall roadmap

---

## Appendix A: File Inventory

### New Files (v1.2.0)

**Source Code:**
```
src/sark/gateway/transports/
├── __init__.py
├── http_client.py       (200 lines, Stream 1)
├── sse_client.py        (150 lines, Stream 1)
└── stdio_client.py      (180 lines, Stream 2)

src/sark/gateway/
├── client.py            (UPDATE, Stream 3)
└── error_handler.py     (100 lines, Stream 3)

src/sark/policy/
├── validator.py         (200 lines, Stream 4)
├── test_runner.py       (150 lines, Stream 4)
└── loader.py            (UPDATE, Stream 4)
```

**Tests:**
```
tests/unit/gateway/transports/
├── test_http_client.py      (300 lines, Stream 1)
├── test_sse_client.py       (200 lines, Stream 1)
└── test_stdio_client.py     (200 lines, Stream 2)

tests/integration/gateway/
└── test_gateway_e2e.py      (500 lines, Stream 3)

tests/unit/policy/
└── test_validator.py        (250 lines, Stream 4)

tests/e2e/
└── test_scenarios.py        (400 lines, Stream 5)

tests/fixtures/
└── ldap_docker.py           (100 lines, Stream 5)
```

**Documentation:**
```
docs/gateway/
├── HTTP_TRANSPORT.md        (Stream 1)
├── SSE_TRANSPORT.md         (Stream 1)
├── STDIO_TRANSPORT.md       (Stream 2)
├── CLIENT_USAGE.md          (Stream 3)
└── ERROR_HANDLING.md        (Stream 3)

docs/
├── POLICY_AUTHORING_GUIDE.md  (Stream 4)
├── POLICY_VALIDATION.md       (Stream 4)

docs/testing/
└── E2E_SCENARIOS.md           (Stream 5)

tests/
└── README.md                  (Stream 5)
```

**Total New Code:** ~3,500 lines
**Total New Tests:** ~2,000 lines
**Total New Docs:** ~5,000 words

---

## Appendix B: Czarina Launch Commands

### Initial Setup
```bash
cd ~/Source/sark

# Initialize Czarina in SARK repo
czarina init

# Copy configuration from this plan
cp docs/v1.2.0/czarina-config.json .czarina/config.json

# Create worker prompts
mkdir -p .czarina/workers
# (Copy worker prompts from this document)
```

### Launch Workers
```bash
# Week 1-2: Launch Gateway workers in parallel
czarina launch gateway-1 gateway-2

# Start daemon for auto-approvals
czarina daemon start

# Monitor progress
czarina status
czarina logs gateway-1
czarina logs gateway-2
```

### Week 4: Integration
```bash
# Launch integration worker (depends on gateway-1 & gateway-2)
czarina launch integration

# Monitor integration tests
czarina logs integration
```

### Weeks 5-8: Policy & QA
```bash
# Launch remaining workers
czarina launch policy
czarina launch qa

# Final status check
czarina status --verbose
```

### Release
```bash
# All workers complete
czarina stop --all

# Review and merge PRs
gh pr list
gh pr merge <pr-number>

# Tag v1.2.0
git tag -a v1.2.0 -m "Release v1.2.0: Gateway + Policy + Tests"
git push origin v1.2.0
```

---

## Document Control

**Version:** 1.0
**Date:** December 9, 2025
**Author:** SARK Team
**Approval Required:**
- [ ] Engineering Lead
- [ ] Security Team
- [ ] Product Manager

**Related Documents:**
- `docs/ROADMAP.md` - Overall roadmap
- `IMPLEMENTATION_PLAN.md` - Original plan (root)
- `LETHAL_TRIFECTA_ANALYSIS.md` - Security analysis
- `docs/ARCHITECTURE.md` - System architecture

**Next Steps:**
1. Review and approve this plan
2. Set up Czarina configuration
3. Create worker prompts
4. Launch Stream 1 & 2 workers (Week 1)
5. Monitor progress and adjust as needed
