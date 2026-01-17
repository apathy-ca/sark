# SARK Path to Production Roadmap

**Document Version:** 2.2
**Last Updated:** 2026-01-17
**Current Release:** v1.5.0 (Production Readiness)
**Target Release:** v1.6.0 (Polish & Validation)
**Target Production:** v2.0.0 (Q2 2026 - GRID Reference Implementation)

---

## Executive Summary

**Current Situation:**
**v1.5.0 has been successfully released** (Jan 17, 2026) with production-ready gateway transports, security fixes, and testing infrastructure. The implementation includes HTTP/SSE/stdio gateway transports, LDAP/CSRF/credentials security fixes, frontend authentication UI, E2E integration tests, and performance benchmark infrastructure.

**What We Have (v1.5.0 - Completed):**
- ✅ **Gateway Transports** (HTTP, SSE, stdio implementations)
- ✅ **Security Fixes** (LDAP injection, CSRF protection, credentials hardening)
- ✅ **Frontend Authentication** (Login, MFA, API key management UI)
- ✅ **E2E Integration Tests** (Complete user flow testing)
- ✅ **Performance Infrastructure** (Locust, pytest-benchmark frameworks)
- ✅ **Rust Foundation** (v1.4.0: OPA engine, in-memory cache, 4-10x faster)
- ✅ **Advanced Security** (v1.3.0: injection detection, anomaly detection, secret scanning, MFA, network controls)
- ✅ Strong architectural foundation (multi-layer auth/authz)
- ✅ Comprehensive audit logging and SIEM integration

**What's Missing (Blocking v2.0 Production):**
- ⚠️ Test suite needs cleanup (34 failing tests across export/tools routers)
- ⚠️ Dependabot security vulnerabilities (4 remaining)
- ⚠️ Performance benchmarks need validation in proper environment
- ⚠️ Protocol abstraction for GRID v1.0 compliance (v2.0 work)
- ❌ External security audit not yet scheduled

**Revised Strategy:**
**v1.6.0** will provide production polish (test fixes, dependency updates, performance validation) as a solid foundation for **v2.0.0**, which will transform SARK into the universal GRID v1.0 reference implementation with protocol abstraction, federation, and cost attribution.

**Version Plan:**
- **v1.3.0** (✅ Complete - Dec 2025): Advanced Security (injection detection, anomaly, network, secrets, MFA)
- **v1.4.0** (✅ Complete - Jan 2026): Rust Foundation (OPA engine, in-memory cache, 4-10x performance)
- **v1.5.0** (✅ Complete - Jan 17, 2026): Production Readiness (gateway transports, security fixes, E2E tests)
- **v1.6.0** (Next - 2-3 weeks): Polish & Validation (test fixes, dependabot, performance validation)
- **v2.0.0** (Future - 16-20 weeks): GRID Reference Implementation (protocol abstraction, federation, cost attribution)

---

## Complete Version Timeline

```
v1.3.0 ──► v1.4.0 ──► v1.5.0 ──► v1.6.0 ──► v2.0.0
(DONE)   (DONE)    (DONE!)   (NEXT)    (Future)
  │         │         │          │         │
Advanced  Rust    Production  Polish    GRID
Security  Core    Readiness  Validation  Ref Impl
✅ Dec25  ✅ Jan26  ✅ Jan17   (2-3wks)  (16-20wks)
```

### v1.2.0: Gateway + Policy + Tests (8 weeks)

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│   Week 1-4  │   Week 5-6  │   Week 7-8  │             │
├─────────────┼─────────────┼─────────────┤             │
│   Gateway   │   Policy    │  Fix Tests  │   Release   │
│ HTTP/SSE/   │  Validation │  Auth Tests │   v1.2.0    │
│  stdio      │  Framework  │  Coverage   │             │
└─────────────┴─────────────┴─────────────┴─────────────┘
```

**Deliverables:**
- Real MCP communication (HTTP, SSE, stdio)
- Policy validation prevents injection
- 100% test pass rate, 85%+ coverage

**See:** `docs/v1.2.0/IMPLEMENTATION_PLAN.md`

### v1.3.0: Advanced Security ✅ COMPLETE (Dec 26, 2025)

```
┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
│  Week 1-2│  Week 3-4│  Week 5  │  Week 6  │  Week 7  │  Week 8  │          │          │
├──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤          │          │
│ Prompt   │ Anomaly  │ Network  │  Secret  │   MFA    │  E2E     │ Release  │          │
│Injection │Detection │ Controls │ Scanning │  System  │   Test   │  v1.3.0  │          │
│   ✅     │    ✅    │    ✅    │    ✅    │    ✅    │    ✅    │    ✅    │          │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
```

**Deliverables: ✅ ALL COMPLETE**
- ✅ Prompt injection detection (20+ patterns, entropy analysis, 30x faster than target)
- ✅ Anomaly detection (30-day baseline, multi-dimensional analysis)
- ✅ Network policies + egress filtering (Kubernetes NetworkPolicies, Calico GlobalNetworkPolicy)
- ✅ Secret scanning + redaction (25+ secret patterns, 50x faster than target)
- ✅ MFA for critical actions (TOTP, SMS, Push, Email support)
- ✅ Comprehensive testing (350+ unit tests, 530+ integration tests, 2200+ performance framework)
- ✅ Performance benchmarks (all 5/5 passing, 30-100x faster than targets)
- ✅ CI/CD integration (automated regression detection, dashboard publishing)
- ✅ Complete documentation (1200+ lines across 4 major documents)

**See:** `docs/v1.3.0/RELEASE_NOTES.md` for complete feature list

### v1.4.0: Rust Foundation (6-8 weeks)

```
┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
│  Week 1-3│  Week 2-3│  Week 4-5│  Week 5-6│  Week 6  │          │
├──────────┼──────────┼──────────┼──────────┼──────────┤          │
│   Rust   │   Rust   │   A/B    │ Perf     │   Docs   │ Release  │
│  OPA     │  Cache   │  Testing │ Testing  │          │  v1.4.0  │
│  Engine  │          │          │          │          │          │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
```

**Deliverables:**
- Embedded Rust OPA engine (4-10x faster)
- Rust in-memory cache (10-50x faster)
- Build system (maturin + PyO3)
- 2,000+ req/s throughput

**Performance Gains:**
- Authorization: 20-50ms → <5ms
- Cache ops: 1-5ms → <0.5ms
- Throughput: 850 → 2,000+ req/s

**See:** `docs/v1.4.0/IMPLEMENTATION_PLAN.md`

### v1.5.0: Rust Detection (4-5 weeks)

```
┌──────────┬──────────┬──────────┬──────────┬──────────┐
│  Week 1-2│  Week 2-3│  Week 3  │  Week 4-5│          │
├──────────┼──────────┼──────────┼──────────┤          │
│ Injection│ Anomaly  │   MCP    │   E2E    │ Release  │
│ Detector │ Detector │  Parser  │   Test   │  v1.5.0  │
│  (Rust)  │  (Rust)  │  (Rust)  │          │          │
└──────────┴──────────┴──────────┴──────────┴──────────┘
```

**Deliverables:**
- Rust injection detector (10-50x faster)
- Rust anomaly detector (5-10x faster)
- Rust MCP parser (5-10x faster)
- 5,000+ req/s throughput

**Performance Gains:**
- Injection detection: 10-50ms → <1ms
- Anomaly detection: 5-20ms → <1ms
- MCP parsing: 5-10ms → <1ms
- Throughput: 2,000 → 5,000+ req/s

**See:** `docs/v1.5.0/IMPLEMENTATION_PLAN.md`

### v2.0.0: Production Release (After Security Audit)

```
┌──────────┬──────────┬──────────┬──────────┬──────────┐
│  Week 1-2│  Week 3-4│  Week 5-6│  Week 7  │          │
├──────────┼──────────┼──────────┼──────────┤          │
│  Audit   │ External │Remediate │  Deploy  │ Release  │
│   Prep   │ Pen Test │  & Test  │ Staging  │  v2.0.0  │
│          │          │          │  to Prod │          │
└──────────┴──────────┴──────────┴──────────┴──────────┘
```

**Deliverables:**
- Zero critical/high vulnerabilities
- External security certification
- Production deployment successful
- 99.9% uptime target

**See:** Phases 4 (Security Audit) below

---

## Total Timeline to Production

**Path 1: Minimum Viable (v1.2.0 → v2.0.0):**
- v1.2.0: 8 weeks (Gateway + Policy + Tests)
- Security Audit: 6-7 weeks
- **Total: 14-15 weeks** to basic production

**Path 2: Enhanced Security (v1.2.0 → v1.3.0 → v2.0.0):**
- v1.2.0: 8 weeks
- v1.3.0: 8 weeks (Advanced security)
- Security Audit: 6-7 weeks
- **Total: 22-23 weeks** to production with advanced features

**Path 3: Full Performance (v1.2.0 → v1.3.0 → v1.4.0 → v1.5.0 → v2.0.0):**
- v1.2.0: 8 weeks
- v1.3.0: 8 weeks
- v1.4.0: 6-8 weeks (Rust foundation)
- v1.5.0: 4-5 weeks (Rust detection)
- Security Audit: 6-7 weeks
- **Total: 32-36 weeks** to production with maximum performance

**Recommended:** Path 2 (Enhanced Security) - Balance of security and time-to-market

---

## v1.2.0 Detailed Timeline (Next Phase)

**Critical Path:** Gateway (4 weeks) → Policy Validation (2 weeks) → Fix Tests (2 weeks)

**Shelved Until Post-Production:**
- CI/CD improvements (defer until core development complete)
- Web UI enhancements (already functional)

**Note:** Advanced Lethal Trifecta security mitigations (v1.3.0) are part of the recommended Path 2 and will proceed after v1.2.0 completion.

---

## Phase 1: Complete Gateway Client Implementation (Weeks 1-4)

**Priority:** 🔴 P1 - CRITICAL BLOCKER
**Goal:** Replace stubbed Gateway client with fully functional MCP transport implementation
**Duration:** 4 weeks
**Team:** 1 senior engineer
**Status:** Not Started

### Current State Analysis

**Problem:**
The Gateway client in `src/sark/api/routers/gateway.py` and `src/sark/models/gateway.py` returns stubbed responses:

```python
async def list_servers(self, user_id: Optional[str] = None) -> list[GatewayServerInfo]:
    return []  # STUBBED!

async def get_server_info(self, server_id: str) -> Optional[GatewayServerInfo]:
    raise NotImplementedError("Gateway client not fully implemented")
```

This means:
- No actual MCP server communication happens
- Authorization/filtering can't be tested end-to-end
- Production usage impossible

**Impact:**
- SARK cannot govern real AI agents
- Security controls unverified in practice
- All Gateway v1.1.0 work theoretical only

### Week 1: HTTP Transport Implementation

**Tasks:**

1. **Implement `list_servers()` - MCP Server Discovery** (2 days)
   - Query MCP registry or configured server list via HTTP
   - Parse MCP server discovery endpoint response
   - Handle pagination (max 100 servers per page)
   - Cache results with 5-minute TTL
   - Filter by user permissions
   - **File:** `src/sark/gateway/http_client.py`

2. **Implement `get_server_info()` - Server Metadata** (1 day)
   - Fetch detailed server information via HTTP
   - Handle 404 responses gracefully
   - Cache server metadata
   - **File:** `src/sark/gateway/http_client.py`

3. **Implement `list_tools()` - Tool Discovery** (2 days)
   - MCP `tools/list` endpoint integration
   - Parse tool schemas and metadata
   - Cache tool lists per server
   - **File:** `src/sark/gateway/http_client.py`

4. **Implement `invoke_tool()` - Core Tool Execution** (3 days)
   - Full authorization flow integration
   - Parameter filtering based on OPA decision
   - Tool invocation via MCP protocol
   - Result processing and validation
   - Audit logging of all invocations
   - **File:** `src/sark/gateway/http_client.py`

**Deliverables:**
- ✅ HTTP transport fully functional
- ✅ Integration with OPA authorization working end-to-end
- ✅ Cache implementation with configurable TTLs
- ✅ Error handling with retry logic
- ✅ 20+ unit tests for HTTP client

### Week 2: SSE (Server-Sent Events) Transport

**Tasks:**

1. **SSE Client Infrastructure** (2 days)
   - Implement async SSE client for streaming responses
   - Connection management and reconnection logic
   - Event parsing and deserialization
   - **File:** `src/sark/gateway/sse_client.py`

2. **Streaming Tool Invocation** (2 days)
   - `invoke_tool_streaming()` for real-time results
   - Async iteration over SSE events
   - Partial result handling
   - Stream cancellation on timeout/error
   - **File:** `src/sark/gateway/sse_client.py`

3. **SSE Connection Management** (2 days)
   - Connection pooling (max 50 concurrent)
   - Automatic reconnection with exponential backoff
   - Heartbeat/keepalive handling
   - Resource cleanup on connection close
   - **File:** `src/sark/gateway/sse_client.py`

**Deliverables:**
- ✅ SSE transport working for streaming responses
- ✅ Connection pooling implemented
- ✅ Reconnection logic tested under failure scenarios
- ✅ 15+ unit tests for SSE client

### Week 3: stdio Transport (Subprocess-based)

**Tasks:**

1. **Stdio MCP Client Foundation** (2 days)
   - Subprocess management for MCP servers
   - JSON-RPC message handling over stdin/stdout
   - Process lifecycle management (start, stop, restart)
   - **File:** `src/sark/gateway/stdio_client.py`

2. **Tool Invocation via stdio** (2 days)
   - JSON-RPC request/response handling
   - Timeout management (30s default)
   - Error handling for crashed processes
   - **File:** `src/sark/gateway/stdio_client.py`

3. **Process Health & Resource Management** (2 days)
   - Process health checks (heartbeat)
   - Resource limits (memory, CPU, file descriptors)
   - Graceful shutdown handling
   - Zombie process prevention
   - **File:** `src/sark/gateway/stdio_client.py`

**Deliverables:**
- ✅ stdio transport functional for local MCP servers
- ✅ Process management robust (no leaks, zombies)
- ✅ Resource limits enforced
- ✅ 15+ unit tests for stdio client

### Week 4: Integration, Error Handling & Polish

**Tasks:**

1. **Unified Gateway Client Interface** (2 days)
   - Abstract transport interface
   - Automatic transport selection based on server config
   - Transport-agnostic error handling
   - **File:** `src/sark/gateway/client.py`

2. **Comprehensive Error Handling** (2 days)
   - Timeout handling with exponential backoff
   - Network error retry logic
   - Authorization failure handling
   - Circuit breaker pattern (fail-fast after 5 consecutive errors)
   - **File:** `src/sark/gateway/error_handler.py`

3. **End-to-End Integration Tests** (3 days)
   - Real MCP server testing (mock or local)
   - Authorization flow validation
   - Parameter filtering verification
   - Audit logging confirmation
   - Performance benchmarks (<100ms p95 latency)
   - **File:** `tests/integration/test_gateway_e2e.py`

**Deliverables:**
- ✅ All 3 transports (HTTP, SSE, stdio) working
- ✅ Gateway client fully functional end-to-end
- ✅ 50+ integration tests covering happy path and failures
- ✅ Performance: <100ms p95 latency for tool invocations
- ✅ Documentation: API reference and usage examples
- ✅ **Gateway Implementation Complete - UNBLOCKED FOR PRODUCTION**

**Acceptance Criteria:**
- [ ] All Gateway methods implemented (no stubs)
- [ ] End-to-end test with real MCP server passes
- [ ] Authorization + filtering verified in practice
- [ ] Performance targets met (<100ms p95)
- [ ] 85%+ code coverage for gateway module
- [ ] Documentation complete with examples
- [ ] Security review passed (internal)

---

## Phase 2: Policy Validation Framework (Weeks 5-6)

**Priority:** 🔴 P2 - CRITICAL
**Goal:** Prevent policy injection attacks by validating OPA policies before loading
**Duration:** 2 weeks
**Team:** 1 engineer
**Status:** Not Started

### Current Risk

**Problem:**
Policies loaded from files/API without validation. Rego is Turing-complete, allowing arbitrary logic:

```rego
# MALICIOUS POLICY EXAMPLE
package gateway.authorization
default allow := true  # Approve everything!
filtered_params := input.params  # Don't filter anything!
```

**Impact:**
- Single malicious policy bypasses all security
- Policy misconfiguration undetected until breach
- No safety net for policy authors

### Week 5: Policy Validator Implementation

**Tasks:**

1. **Policy Validation Engine** (3 days)
   - Syntax validation via OPA CLI (`opa check`)
   - Required rule verification (must have `allow` and `deny`)
   - Forbidden pattern detection (blanket allows, system imports)
   - Safety checks (no external HTTP, no data exfiltration)
   - **File:** `src/sark/policy/validator.py`

2. **Policy Testing Framework** (2 days)
   - Run unit tests for policies (YAML test suites)
   - Evaluate policy with sample inputs
   - Verify expected allow/deny decisions
   - **File:** `src/sark/policy/test_runner.py`

**Deliverables:**
- ✅ Policy validator with syntax and safety checks
- ✅ Forbidden pattern detection (10+ patterns)
- ✅ 20+ unit tests for validator

### Week 6: Integration & Policy Migration

**Tasks:**

1. **Integrate Validator into Loading Pipeline** (2 days)
   - Validate all policies before loading into OPA
   - Reject invalid policies with detailed errors
   - Log validation warnings (non-fatal issues)
   - **File:** `src/sark/policy/loader.py`

2. **Validate Existing Policies** (2 days)
   - Run validator against all current policies
   - Fix policies that fail validation
   - Create test suites for all policies
   - **Files:** `opa_policies/*.rego`, `opa_policies/tests/*.yaml`

3. **Documentation & Best Practices** (1 day)
   - Policy authoring guide with safety requirements
   - Common mistakes and how to avoid them
   - Example safe policies
   - **File:** `docs/POLICY_AUTHORING_GUIDE.md`

**Deliverables:**
- ✅ All policies validated before loading
- ✅ 100% of existing policies pass validation
- ✅ Policy test suites created
- ✅ Documentation for policy authors
- ✅ **Policy Injection Risk Mitigated**

**Acceptance Criteria:**
- [ ] Validator rejects malicious policy examples
- [ ] All existing policies validated and tested
- [ ] Invalid policy upload returns clear error
- [ ] Documentation reviewed and approved
- [ ] Security team sign-off

---

## Phase 3: Fix Failing Tests & Improve Coverage (Weeks 7-8)

**Priority:** 🟠 P3 - HIGH
**Goal:** Achieve 85%+ test coverage with 100% pass rate
**Duration:** 2 weeks
**Team:** 1 engineer
**Status:** Not Started

### Current State

**Problem:**
- 77.8% test pass rate (154 auth provider tests erroring)
- Gaps in test coverage for critical paths
- No end-to-end scenario tests

### Week 7: Fix Auth Provider Tests

**Tasks:**

1. **Debug LDAP Auth Provider Tests** (2 days)
   - Issue: Mock LDAP server not starting correctly
   - Fix: Use `pytest-docker` for real LDAP container
   - Resolve 52 LDAP test failures
   - **File:** `tests/test_auth_providers.py`

2. **Debug SAML Auth Provider Tests** (2 days)
   - Issue: XML signature validation failing
   - Fix: Correct certificate format in test fixtures
   - Resolve 48 SAML test failures
   - **File:** `tests/test_auth_providers.py`

3. **Debug OIDC Auth Provider Tests** (1 day)
   - Issue: Token expiry validation off by 1 second
   - Fix: Use `freezegun` for time mocking
   - Resolve 54 OIDC test failures
   - **File:** `tests/test_auth_providers.py`

**Deliverables:**
- ✅ 100% test pass rate
- ✅ All 154 erroring tests fixed
- ✅ Docker-based test infrastructure for LDAP

### Week 8: Improve Test Coverage

**Tasks:**

1. **Add Missing Unit Tests** (2 days)
   - Gateway authorization logic
   - Parameter filtering edge cases
   - Cache TTL calculations
   - Rate limiting enforcement
   - **Files:** `tests/unit/test_*.py`

2. **Add End-to-End Scenario Tests** (3 days)
   - Sensitive data access workflows
   - Prompt injection blocking scenarios
   - Multi-layer authorization flows
   - Audit log verification
   - **File:** `tests/e2e/test_scenarios.py`

**Deliverables:**
- ✅ 85%+ code coverage
- ✅ 200+ total tests (unit + integration + e2e)
- ✅ CI/CD pipeline green
- ✅ Coverage report published
- ✅ **Test Quality Gate Met**

**Acceptance Criteria:**
- [ ] 100% test pass rate achieved
- [ ] 85%+ overall code coverage
- [ ] All critical paths have tests
- [ ] E2E scenarios cover major workflows
- [ ] Performance tests pass (<100ms p95)

---

## Phase 4: Security Audit Preparation & Execution (Weeks 9-10)

**Priority:** 🔴 P1 - CRITICAL GATE
**Goal:** External penetration test to validate security controls
**Duration:** 2 weeks preparation + 2 weeks vendor testing
**Team:** 1 engineer + external vendor
**Status:** Not Started

### Week 9: Pre-Audit Preparation

**Tasks:**

1. **Document Attack Surface** (2 days)
   - API endpoints inventory (50+ endpoints)
   - Authentication mechanisms documentation
   - Data flows and trust boundaries
   - **File:** `docs/security/ATTACK_SURFACE.md`

2. **Security Questionnaire** (2 days)
   - OWASP Top 10 mitigations
   - Encryption (TLS, at-rest, in-transit)
   - Secret management practices
   - Access controls documentation
   - **File:** `docs/security/SECURITY_CONTROLS.md`

3. **Provide Test Environment** (1 day)
   - Staging cluster with production-like config
   - Test accounts (admin, developer, restricted)
   - Synthetic test data (no production data)
   - **Infrastructure:** Staging environment

**Deliverables:**
- ✅ Attack surface documented
- ✅ Security controls documented
- ✅ Test environment ready
- ✅ Vendor selected and contracted

### Week 10: Internal Security Review

**Tasks:**

1. **Internal Security Scan** (2 days)
   - OWASP ZAP automated scanning
   - Dependency vulnerability check (Snyk/Trivy)
   - Secrets scanning (TruffleHog)
   - **Tools:** OWASP ZAP, Snyk, TruffleHog

2. **Fix Critical Issues** (3 days)
   - Address P0/P1 findings from internal scan
   - Update dependencies with CVEs
   - Remove any detected secrets
   - **Various files**

**Deliverables:**
- ✅ Internal security scan complete
- ✅ All P0/P1 issues resolved
- ✅ No secrets in codebase
- ✅ Dependencies up to date
- ✅ **Ready for External Audit**

### Weeks 11-12: External Security Testing (Vendor)

**Vendor Selection:** TBD (recommend NCC Group, Trail of Bits, or Bishop Fox)

**Testing Methods:**
- Automated vulnerability scanning
- Manual penetration testing
- Code review (security-focused)
- Policy analysis (OPA Rego)

**Expected Timeline:**
- Week 11: Vendor testing
- Week 12: Remediation + re-test

**Acceptance Criteria:**
- [ ] Zero critical vulnerabilities
- [ ] Zero high vulnerabilities
- [ ] Remediation plan for medium/low findings
- [ ] Penetration test report received
- [ ] Security team sign-off for production

**Deliverables:**
- ✅ External security audit report
- ✅ Remediation completed and verified
- ✅ Penetration test certification
- ✅ **PRODUCTION SECURITY GATE PASSED**

---

## Phase 5: Lethal Trifecta Advanced Mitigations (v1.3.0) ✅ COMPLETE

**Priority:** 🟢 COMPLETE
**Status:** ✅ Released Dec 26, 2025
**Completion Date:** Dec 26, 2025
**Release:** v1.3.0

These security enhancements from the Lethal Trifecta Analysis have been **successfully implemented and released**:

### Advanced Security Features

1. ✅ **Prompt Injection Detection** - COMPLETE
   - ✅ Pattern-based detection (20+ patterns)
   - ✅ Entropy analysis for encoded payloads
   - ✅ Configurable response (block/alert/log)
   - ✅ Risk scoring system (0-100)
   - ✅ Performance: 0.06ms p95 (30x faster than 2.0ms target)
   - **Files:** src/sark/security/injection_detector.py, injection_response.py

2. ✅ **Anomaly Detection System** - COMPLETE
   - ✅ Behavioral baseline per user (30-day window)
   - ✅ Real-time anomaly detection (multi-dimensional analysis)
   - ✅ Alert on unusual access patterns
   - ✅ Alert management system
   - **Files:** src/sark/security/behavioral_analyzer.py, anomaly_alerts.py

3. ✅ **Network-Level Controls** - COMPLETE
   - ✅ Kubernetes NetworkPolicies (egress/ingress control)
   - ✅ Egress filtering with Calico GlobalNetworkPolicy
   - ✅ Domain whitelisting
   - ✅ Defense-in-depth networking
   - **Files:** k8s/network-policies/

4. ✅ **Secret Scanning** - COMPLETE
   - ✅ Scan tool responses for secrets (25+ patterns)
   - ✅ Automatic redaction in responses
   - ✅ Location tracking and reporting
   - ✅ Performance: 0.01ms p95 (50x faster than 0.5ms target)
   - **Files:** src/sark/security/secret_scanner.py

5. ✅ **MFA for Critical Actions** - COMPLETE
   - ✅ MFA challenge for high-sensitivity resources
   - ✅ TOTP/SMS/Push/Email notification support
   - ✅ Challenge/response flow with expiration
   - ✅ Rate limiting
   - **Files:** src/sark/security/mfa.py

**Total Effort:** ✅ Successfully completed
**Release Date:** Dec 26, 2025
**Status:** All features production-ready with comprehensive testing and documentation

---

## Production Deployment Strategy

### Pre-Production Checklist

Before production deployment, ALL of the following must be complete:

**Phase 1 - Gateway Client:**
- [ ] All 3 transports (HTTP, SSE, stdio) working
- [ ] End-to-end tests passing with real MCP server
- [ ] Performance targets met (<100ms p95)
- [ ] Code coverage ≥85% for gateway module

**Phase 2 - Policy Validation:**
- [ ] Validator integrated into policy loading
- [ ] All existing policies validated and tested
- [ ] Security team approval

**Phase 3 - Test Quality:**
- [ ] 100% test pass rate
- [ ] Overall code coverage ≥85%
- [ ] E2E scenarios covering major workflows

**Phase 4 - Security Audit:**
- [ ] External penetration test passed
- [ ] Zero critical/high vulnerabilities
- [ ] Remediation complete and verified

**Infrastructure:**
- [ ] Production Kubernetes cluster provisioned
- [ ] SSL/TLS certificates configured
- [ ] DNS records configured
- [ ] Monitoring dashboards operational
- [ ] Backup systems verified
- [ ] Incident response playbook ready

**Documentation:**
- [ ] Production deployment guide tested
- [ ] Runbooks peer-reviewed
- [ ] User training materials ready
- [ ] API documentation complete

### Deployment Timeline

**Week 13: Staging Deployment**
- Deploy to staging environment
- Run full test suite in staging
- Performance testing under load
- Security review in staging

**Week 14: Canary Deployment**
- Deploy to 5% of production traffic
- Monitor for 48 hours
- Gradual increase: 5% → 25% → 50% → 100%

**Week 15: Production Go-Live**
- 100% production traffic
- 24/7 monitoring for first 72 hours
- On-call team ready
- Post-launch review

### Rollback Plan

**Triggers:**
- Error rate >1%
- Latency p95 >200ms (2x normal)
- Critical security issue discovered
- Data corruption detected

**Procedure:**
1. Alert fires (PagerDuty) - <1 min
2. On-call engineer assesses - <5 min
3. Rollback decision if confirmed - <5 min
4. Deploy previous version via Helm - <10 min
5. Verify metrics return to normal - <15 min
6. Post-mortem within 24 hours

**Total MTTR Target:** <30 minutes

---

## Success Metrics

### Phase Completion Gates

| Phase | Metric | Target | Measurement |
|-------|--------|--------|-------------|
| **Phase 1: Gateway** | Implementation complete | 100% | All methods working, no stubs |
| | End-to-end test | Pass | Real MCP server integration |
| | Performance | <100ms p95 | Load testing |
| | Coverage | ≥85% | pytest-cov |
| **Phase 2: Policy** | Validation working | 100% | All policies validated |
| | Existing policies pass | 100% | No validation failures |
| | Security review | Approved | Security team sign-off |
| **Phase 3: Tests** | Test pass rate | 100% | CI green |
| | Coverage | ≥85% | pytest-cov |
| | E2E scenarios | ≥20 | Scenario tests passing |
| **Phase 4: Security** | Pen test | Passed | External vendor |
| | Critical vulnerabilities | 0 | Security audit |
| | High vulnerabilities | 0 | Security audit |

### Production Readiness Metrics

| Category | Metric | Target | Status |
|----------|--------|--------|--------|
| **Functionality** | Gateway client functional | 100% | 🔴 Not Started |
| | Policy validation | 100% | 🔴 Not Started |
| | Test pass rate | 100% | 🟡 77.8% |
| **Security** | External audit | Passed | 🔴 Not Started |
| | Vulnerabilities (P0/P1) | 0 | 🟡 Unknown |
| **Quality** | Code coverage | ≥85% | 🟡 ~64% |
| | E2E tests | ≥20 | 🔴 0 |
| **Performance** | API latency (p95) | <100ms | ✅ Met |
| | Gateway latency (p95) | <100ms | 🔴 Untested |

**Overall Production Readiness:** 🔴 **NOT READY** (4/10 metrics met)

---

## Risk Management

### Critical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Gateway implementation takes >4 weeks** | High | Medium | Allocate buffer time, consider HTTP-only MVP |
| **Security audit finds critical vuln** | Critical | Medium | Address immediately, delay production |
| **Test failures block progress** | Medium | Low | Refactor problematic code iteratively |
| **Policy validation breaks existing policies** | High | Medium | Gradual rollout, extensive testing |
| **Performance degradation** | Medium | Low | Optimize, add caching, horizontal scaling |

### Contingency Plans

**If Gateway takes >4 weeks:**
- Option 1: Ship HTTP-only (defer SSE/stdio to v2.1)
- Option 2: Hire contractor with MCP experience
- Option 3: Extend timeline by 2 weeks

**If security audit fails:**
- Option 1: Fix critical issues, deploy to staging only
- Option 2: Engage security consultant for remediation
- Option 3: Defer production until re-test passes

**If test coverage can't reach 85%:**
- Option 1: Accept 80% for v1.2, target 85% for v2.0
- Option 2: Focus coverage on critical paths only
- Option 3: Technical debt sprint post-production

---

## Resource Requirements

### Engineering Team (10 weeks)

| Role | Weeks 1-4 | Weeks 5-6 | Weeks 7-8 | Weeks 9-10 | Total |
|------|-----------|-----------|-----------|------------|-------|
| **Senior Backend Engineer** | Full-time (Gateway) | Full-time (Policy) | Part-time (Review) | Part-time (Audit prep) | 6 weeks FTE |
| **Backend Engineer** | - | - | Full-time (Tests) | Full-time (Security) | 4 weeks FTE |
| **Security Engineer** | - | - | - | Part-time (Audit) | 1 week FTE |

**Total Engineering Effort:** ~11 weeks FTE across 10 calendar weeks

### External Vendor

**Security Audit:** $15,000 - $30,000 (2 weeks testing)

### Infrastructure Costs

| Environment | Cost/Month | Notes |
|-------------|------------|-------|
| **Development** | $200 | Small instances, non-HA |
| **Staging** | $500 | Production-like, HA enabled |
| **Production** | $2000 | Full HA, auto-scaling, backups |

**Total Project Cost:**
- Engineering: ~$55,000 (11 weeks FTE × $5000/week)
- Security Audit: ~$20,000
- Infrastructure (3 months): ~$8,100
- **Total: ~$83,000**

---

## Timeline Summary

```
Week 1-2:  Gateway HTTP transport + SSE transport
Week 3:    Gateway stdio transport
Week 4:    Gateway integration & end-to-end testing
Week 5:    Policy validation engine
Week 6:    Policy validation integration & migration
Week 7:    Fix auth provider tests
Week 8:    Improve test coverage
Week 9:    Security audit preparation
Week 10:   Internal security review
Week 11:   External security testing (vendor)
Week 12:   Remediation & re-test
Week 13:   Staging deployment
Week 14:   Canary production deployment
Week 15:   Full production go-live
```

**Critical Path:** Gateway (4 weeks) → Policy (2 weeks) → Tests (2 weeks) → Security Audit (4 weeks) → Deployment (3 weeks)

**Total Duration:** 15 weeks from start to production

---

## Shelved Items (Post-Production)

The following items are **intentionally deferred** to focus on production-critical work:

### CI/CD Improvements
- Advanced GitHub Actions workflows
- Automated deployment pipelines
- Blue-green deployment automation
- **Reason:** Current CI works; optimize after core dev complete

### Advanced Lethal Trifecta Mitigations (v1.3.0)
- Prompt injection detection
- Anomaly detection
- Network-level controls
- Secret scanning
- MFA for critical actions
- **Reason:** Important security enhancements but not blockers for v2.0.0 production
- **Target:** v1.3.0 release (Q2 2026)

### Web UI Enhancements
- Advanced policy editor features
- Real-time dashboard updates
- Mobile responsiveness improvements
- **Reason:** Current UI functional; polish post-launch

---

## Document Control

**Version History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-20 | SARK Team | Initial roadmap |
| 2.0 | 2025-12-09 | SARK Team | Complete revision based on Lethal Trifecta Analysis |

**Review Schedule:** Weekly on Mondays during active development

**Next Review:** 2025-12-16

**Approval Status:**
- [ ] Engineering Lead
- [ ] Security Team
- [ ] Product Manager

---

## Related Documentation

- **[Lethal Trifecta Analysis](../LETHAL_TRIFECTA_ANALYSIS.md)** - Security gap analysis
- **[Implementation Plan](../IMPLEMENTATION_PLAN.md)** - Detailed task breakdown
- **[Production Readiness Checklist](./PRODUCTION_READINESS.md)** - Go-live requirements
- **[Architecture Guide](./ARCHITECTURE.md)** - System architecture overview
- **[Security Guide](./SECURITY.md)** - Security requirements and controls
- **[Deployment Guide](./DEPLOYMENT.md)** - Deployment procedures

---

## Appendix: Version Strategy & Critical Findings

**Context:**
On December 8, 2025, a comprehensive security analysis using Simon Willison's "Lethal Trifecta" framework revealed critical implementation gaps:

**Key Findings:**
1. **Gateway Client Stubbed:** Returns empty lists and NotImplementedError - cannot communicate with real MCP servers
2. **Policy Injection Risk:** No validation of OPA policies before loading
3. **Test Failures:** 154 auth provider tests failing (77.8% pass rate)
4. **Untested End-to-End:** Critical security flows not verified in practice

**Decision:**
Adopt honest, incremental versioning with clear milestones:
- **v1.2.0:** Complete gateway implementation + critical fixes (Weeks 1-8)
- **v1.3.0:** Advanced Lethal Trifecta security features (Q2 2026)
- **v2.0.0:** Production release after security audit (Week 15)

**This Roadmap:**
Addresses these gaps with a focused 15-week plan using semantic versioning that reflects actual readiness.
