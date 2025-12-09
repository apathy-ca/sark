# Sark Enhancement Implementation Plan
## Addressing the Lethal Trifecta: Production Readiness Roadmap

**Version:** 1.0
**Date:** December 8, 2025
**Based on:** LETHAL_TRIFECTA_ANALYSIS.md
**Target:** Production-ready v2.1.0
**Estimated Timeline:** 8-12 weeks

---

## Executive Summary

This plan addresses critical gaps identified in the lethal trifecta security analysis to bring Sark to production readiness. Work is organized into 4 priority levels across 5 major workstreams:

1. **Gateway Implementation** (P1) - Complete MCP client functionality
2. **Security Hardening** (P1-P2) - Add prompt injection detection and policy validation
3. **Test Coverage** (P1) - Fix failing tests and achieve 85%+ coverage
4. **Production Operations** (P2-P3) - Add monitoring, anomaly detection, network controls
5. **Advanced Features** (P3-P4) - Cost attribution, federation, MFA

**Critical Path:** Gateway → Tests → Security Audit → Production Deployment

**Success Criteria:**
- ✅ Gateway client fully functional (all MCP transports)
- ✅ 85%+ test coverage with 0 failing tests
- ✅ Prompt injection detection operational
- ✅ Policy validation framework implemented
- ✅ Security audit passed (external penetration test)
- ✅ Production deployment successful with monitoring

---

## Table of Contents

1. [Priority 1: Critical (Weeks 1-4)](#priority-1-critical-weeks-1-4)
2. [Priority 2: High (Weeks 5-8)](#priority-2-high-weeks-5-8)
3. [Priority 3: Medium (Weeks 9-10)](#priority-3-medium-weeks-9-10)
4. [Priority 4: Low (Weeks 11-12)](#priority-4-low-weeks-11-12)
5. [Technical Specifications](#technical-specifications)
6. [Testing Strategy](#testing-strategy)
7. [Security Audit Plan](#security-audit-plan)
8. [Deployment Strategy](#deployment-strategy)
9. [Risk Management](#risk-management)
10. [Success Metrics](#success-metrics)

---

## Priority 1: Critical (Weeks 1-4)

**Goal:** Eliminate production blockers - complete core functionality and fix critical bugs

### 1.1 Complete Gateway Client Implementation

**Current State:** Stubbed implementation returns empty lists/NotImplementedError
**Target State:** Fully functional MCP client supporting HTTP, SSE, and stdio transports
**Effort:** 3-4 weeks, 1 developer
**Files to Modify:** `sark/gateway.py`, `sark/mcp_adapter.py`, `tests/test_gateway.py`

#### Tasks

**Week 1: HTTP Transport**
- [ ] Implement `list_servers()` - Query MCP servers via HTTP
  - Parse MCP server discovery endpoint
  - Handle pagination (max 100 servers per page)
  - Cache results with 5-minute TTL
  ```python
  async def list_servers(self, user_id: Optional[str] = None) -> list[GatewayServerInfo]:
      # Query MCP registry or configured server list
      response = await self.http_client.get(f"{self.registry_url}/servers")
      servers = [self._parse_server_info(s) for s in response.json()["servers"]]

      # Filter by user permissions
      if user_id:
          servers = [s for s in servers if await self._user_has_access(user_id, s)]

      return servers
  ```

- [ ] Implement `get_server_info()` - Fetch server metadata
  ```python
  async def get_server_info(self, server_id: str) -> Optional[GatewayServerInfo]:
      response = await self.http_client.get(f"{self.registry_url}/servers/{server_id}")
      if response.status_code == 404:
          return None
      return self._parse_server_info(response.json())
  ```

- [ ] Implement `list_tools()` - Discover available tools
  ```python
  async def list_tools(self, server_id: str) -> list[GatewayToolInfo]:
      # MCP tools/list endpoint
      response = await self.http_client.post(
          f"{self._get_server_url(server_id)}/mcp/tools/list"
      )
      return [self._parse_tool_info(t) for t in response.json()["tools"]]
  ```

- [ ] Implement `invoke_tool()` - Execute tool with authorization
  ```python
  async def invoke_tool(
      self,
      server_id: str,
      tool_name: str,
      params: dict,
      user_context: dict
  ) -> GatewayToolResult:
      # 1. Authorize request via OPA
      auth_result = await self.authorize_gateway_request(
          user_id=user_context["user_id"],
          server_id=server_id,
          tool_name=tool_name,
          params=params
      )

      if not auth_result.allowed:
          raise GatewayAuthorizationError(auth_result.reason)

      # 2. Filter parameters based on authorization response
      filtered_params = auth_result.filtered_params

      # 3. Invoke tool via MCP
      response = await self.http_client.post(
          f"{self._get_server_url(server_id)}/mcp/tools/call",
          json={
              "name": tool_name,
              "arguments": filtered_params
          }
      )

      # 4. Audit log the invocation
      await self.log_gateway_event(
          event_type="tool_invocation",
          user_id=user_context["user_id"],
          server_id=server_id,
          tool_name=tool_name,
          decision="allow",
          metadata={"params": filtered_params, "result_status": response.status_code}
      )

      return GatewayToolResult(
          success=response.status_code == 200,
          data=response.json(),
          metadata={"execution_time_ms": response.elapsed.total_seconds() * 1000}
      )
  ```

**Week 2: SSE Transport**
- [ ] Implement SSE client for streaming responses
  ```python
  async def invoke_tool_streaming(
      self,
      server_id: str,
      tool_name: str,
      params: dict,
      user_context: dict
  ) -> AsyncIterator[GatewayToolResult]:
      # Authorize first
      auth_result = await self.authorize_gateway_request(...)

      # Stream results via SSE
      async with self.sse_client.stream(
          f"{self._get_server_url(server_id)}/mcp/tools/call",
          json={"name": tool_name, "arguments": auth_result.filtered_params}
      ) as event_source:
          async for event in event_source:
              yield GatewayToolResult(
                  success=True,
                  data=json.loads(event.data),
                  metadata={"event_id": event.id}
              )
  ```

- [ ] Handle SSE reconnection and error recovery
- [ ] Add SSE connection pooling (max 50 concurrent connections)

**Week 3: Stdio Transport**
- [ ] Implement subprocess-based MCP client
  ```python
  class StdioMCPClient:
      async def start_server(self, command: list[str], env: dict) -> str:
          """Start MCP server process and return server_id"""
          process = await asyncio.create_subprocess_exec(
              *command,
              stdin=asyncio.subprocess.PIPE,
              stdout=asyncio.subprocess.PIPE,
              stderr=asyncio.subprocess.PIPE,
              env=env
          )

          server_id = f"stdio_{uuid.uuid4()}"
          self.processes[server_id] = process

          # Start JSON-RPC message loop
          asyncio.create_task(self._message_loop(server_id, process))

          return server_id

      async def invoke_tool(self, server_id: str, tool_name: str, params: dict):
          """Send JSON-RPC request to stdio MCP server"""
          process = self.processes[server_id]

          request = {
              "jsonrpc": "2.0",
              "id": str(uuid.uuid4()),
              "method": "tools/call",
              "params": {"name": tool_name, "arguments": params}
          }

          # Write to stdin
          process.stdin.write(json.dumps(request).encode() + b"\n")
          await process.stdin.drain()

          # Read from stdout (with timeout)
          try:
              response_line = await asyncio.wait_for(
                  process.stdout.readline(),
                  timeout=30.0
              )
              return json.loads(response_line)
          except asyncio.TimeoutError:
              raise GatewayTimeoutError(f"Tool {tool_name} timed out")
  ```

- [ ] Add process lifecycle management (start, stop, restart)
- [ ] Implement process health checks (heartbeat)
- [ ] Add resource limits (memory, CPU, file descriptors)

**Week 4: Integration & Error Handling**
- [ ] Add comprehensive error handling
  ```python
  class GatewayErrorHandler:
      async def handle_error(self, error: Exception, context: dict) -> GatewayToolResult:
          if isinstance(error, httpx.TimeoutException):
              return GatewayToolResult(
                  success=False,
                  error="Tool invocation timed out",
                  retry_after=30
              )
          elif isinstance(error, GatewayAuthorizationError):
              return GatewayToolResult(
                  success=False,
                  error=f"Authorization failed: {error.reason}",
                  retry_after=None  # Don't retry auth failures
              )
          # ... handle other error types
  ```

- [ ] Add retry logic with exponential backoff
- [ ] Implement circuit breaker pattern (fail-fast after 5 consecutive errors)
- [ ] Add connection pooling and keepalive
- [ ] Write integration tests (end-to-end scenarios)

**Deliverables:**
- ✅ Gateway client fully functional for all 3 transports
- ✅ 50+ integration tests covering happy path and error cases
- ✅ Performance: <100ms p95 latency for tool invocations
- ✅ Documentation: API reference and examples

---

### 1.2 Fix Failing Tests & Improve Coverage

**Current State:** 77.8% pass rate (154 auth provider tests erroring)
**Target State:** 100% pass rate, 85%+ coverage
**Effort:** 2 weeks, 1 developer
**Files to Modify:** `tests/test_auth_providers.py`, various test files

#### Tasks

**Week 1: Fix Auth Provider Tests**
- [ ] Debug LDAP auth provider tests (52 failures)
  - Issue: Mock LDAP server not starting correctly
  - Fix: Use `pytest-docker` for real LDAP container
  ```python
  @pytest.fixture(scope="session")
  def ldap_server():
      client = docker.from_env()
      container = client.containers.run(
          "osixia/openldap:1.5.0",
          detach=True,
          ports={"389/tcp": 1389},
          environment={
              "LDAP_ORGANISATION": "Test Org",
              "LDAP_DOMAIN": "test.local"
          }
      )

      # Wait for LDAP to be ready
      time.sleep(5)

      yield container

      container.stop()
      container.remove()
  ```

- [ ] Debug SAML auth provider tests (48 failures)
  - Issue: XML signature validation failing
  - Fix: Use correct certificate format in test fixtures

- [ ] Debug OIDC auth provider tests (54 failures)
  - Issue: Token expiry validation off by 1 second
  - Fix: Use freezegun for time mocking

**Week 2: Improve Test Coverage**
- [ ] Add missing unit tests for gateway authorization
  ```python
  @pytest.mark.parametrize("sensitivity,expected_cache_ttl", [
      ("public", 3600),
      ("low", 1800),
      ("medium", 300),
      ("high", 60),
      ("critical", 0)
  ])
  async def test_sensitivity_cache_ttl(sensitivity, expected_cache_ttl):
      response = await authorize_gateway_request(
          user_id="test_user",
          server_id="test_server",
          tool_name="test_tool",
          params={},
          sensitivity=sensitivity
      )
      assert response.cache_ttl_seconds == expected_cache_ttl
  ```

- [ ] Add end-to-end scenario tests
  ```python
  async def test_e2e_sensitive_data_access():
      """Verify high-sensitivity data filtered for non-admin users"""
      # Setup: Create user without admin role
      user = await create_test_user(role="developer")

      # Execute: Invoke tool with sensitive parameters
      result = await gateway_client.invoke_tool(
          server_id="test_db",
          tool_name="query_customers",
          params={"include_ssn": True, "include_emails": True},
          user_context={"user_id": user.id}
      )

      # Verify: SSN filtered out, emails allowed
      assert "ssn" not in result.data[0]
      assert "email" in result.data[0]

      # Verify: Audit log recorded
      audit_event = await get_latest_audit_event(user.id)
      assert audit_event.decision == "allow"
      assert audit_event.metadata["filtered_params"] == ["include_ssn"]
  ```

- [ ] Add performance tests (load testing)
- [ ] Add security tests (penetration testing scenarios)

**Deliverables:**
- ✅ 100% test pass rate
- ✅ 85%+ code coverage
- ✅ 200+ total tests (unit, integration, e2e)
- ✅ CI/CD pipeline green

---

### 1.3 Policy Validation Framework

**Current State:** Policies loaded without validation
**Target State:** All policies validated before loading, safety checks enforced
**Effort:** 1.5 weeks, 1 developer
**Files to Create:** `sark/policy_validator.py`, `tests/test_policy_validator.py`

#### Tasks

**Week 1: Policy Validator Implementation**
- [ ] Create policy validation engine
  ```python
  class PolicyValidator:
      """Validates OPA policies before loading"""

      REQUIRED_RULES = [
          "allow",  # Must have explicit allow rule
          "deny",   # Must have explicit deny rule
      ]

      FORBIDDEN_PATTERNS = [
          r"allow\s*:=\s*true\s*$",  # Blanket allow
          r"import\s+data\.system",  # System data access
          r"http\.send",             # External HTTP calls
      ]

      async def validate_policy(self, policy_rego: str) -> PolicyValidationResult:
          """Validate policy syntax and safety"""

          # 1. Syntax validation via OPA CLI
          result = await asyncio.create_subprocess_exec(
              "opa", "check", "-",
              stdin=asyncio.subprocess.PIPE,
              stdout=asyncio.subprocess.PIPE,
              stderr=asyncio.subprocess.PIPE
          )
          stdout, stderr = await result.communicate(policy_rego.encode())

          if result.returncode != 0:
              return PolicyValidationResult(
                  valid=False,
                  errors=[f"Syntax error: {stderr.decode()}"]
              )

          # 2. Check required rules exist
          errors = []
          for rule in self.REQUIRED_RULES:
              if not re.search(rf"^{rule}\s*:?=", policy_rego, re.MULTILINE):
                  errors.append(f"Missing required rule: {rule}")

          # 3. Check for forbidden patterns
          for pattern in self.FORBIDDEN_PATTERNS:
              if re.search(pattern, policy_rego, re.MULTILINE):
                  errors.append(f"Forbidden pattern detected: {pattern}")

          # 4. Test with sample inputs
          test_cases = [
              {"input": {"user": {"role": "admin"}}, "expected_allow": True},
              {"input": {"user": {"role": "guest"}}, "expected_allow": False},
          ]

          for test in test_cases:
              result = await self._evaluate_policy(policy_rego, test["input"])
              if result.get("allow") != test["expected_allow"]:
                  errors.append(f"Policy failed test case: {test}")

          return PolicyValidationResult(
              valid=len(errors) == 0,
              errors=errors,
              warnings=self._check_warnings(policy_rego)
          )

      def _check_warnings(self, policy_rego: str) -> list[str]:
          """Check for non-fatal issues"""
          warnings = []

          # Warn if no default deny
          if not re.search(r"default\s+allow\s*:=\s*false", policy_rego):
              warnings.append("No 'default allow := false' found - policy may allow by default")

          # Warn if caching disabled for low-sensitivity resources
          if "cache_ttl_seconds := 0" in policy_rego:
              warnings.append("Caching disabled - may impact performance")

          return warnings
  ```

- [ ] Add policy testing framework
  ```python
  class PolicyTestRunner:
      """Run unit tests for OPA policies"""

      async def run_tests(self, policy_rego: str, test_suite: dict) -> PolicyTestResult:
          """Execute policy tests defined in YAML"""

          # Load policy into OPA
          await self.opa_client.load_policy("test_policy", policy_rego)

          results = []
          for test_case in test_suite["tests"]:
              # Evaluate policy with test input
              response = await self.opa_client.evaluate(
                  "data.test_policy.allow",
                  input_data=test_case["input"]
              )

              expected = test_case["expected"]
              actual = response.get("result", {})

              if actual != expected:
                  results.append({
                      "test": test_case["name"],
                      "status": "FAIL",
                      "expected": expected,
                      "actual": actual
                  })
              else:
                  results.append({
                      "test": test_case["name"],
                      "status": "PASS"
                  })

          return PolicyTestResult(
              total=len(results),
              passed=sum(1 for r in results if r["status"] == "PASS"),
              failed=sum(1 for r in results if r["status"] == "FAIL"),
              details=results
          )
  ```

**Week 2: Integration & Policy Migration**
- [ ] Integrate validator into policy loading pipeline
  ```python
  async def load_policy(self, name: str, policy_rego: str):
      # Validate before loading
      validation = await self.validator.validate_policy(policy_rego)

      if not validation.valid:
          raise PolicyValidationError(
              f"Policy validation failed: {validation.errors}"
          )

      # Log warnings
      for warning in validation.warnings:
          logger.warning(f"Policy warning: {warning}")

      # Load into OPA
      await self.opa_client.load_policy(name, policy_rego)

      # Audit log
      await self.audit_logger.log_event(
          event_type="policy_loaded",
          policy_name=name,
          metadata={"validation_warnings": validation.warnings}
      )
  ```

- [ ] Validate all existing policies (gateway, A2A, tool chain)
- [ ] Fix any policies that fail validation
- [ ] Create policy test suites (YAML format)
  ```yaml
  # policies/tests/gateway_authorization_test.yaml
  tests:
    - name: "Admin user can access critical resources"
      input:
        user:
          id: "user1"
          role: "admin"
        resource:
          sensitivity: "critical"
      expected:
        allow: true
        filtered_params: {}

    - name: "Developer cannot access critical resources"
      input:
        user:
          id: "user2"
          role: "developer"
        resource:
          sensitivity: "critical"
      expected:
        allow: false
        reason: "Insufficient permissions for critical resource"
  ```

**Deliverables:**
- ✅ Policy validator with syntax and safety checks
- ✅ Policy testing framework
- ✅ All existing policies validated and tested
- ✅ Documentation: Policy authoring best practices

---

### 1.4 Security Audit Preparation

**Current State:** No external security assessment
**Target State:** Third-party penetration test passed
**Effort:** 1 week preparation + 2 weeks testing
**Vendor:** TBD (recommend NCC Group, Trail of Bits, or Bishop Fox)

#### Tasks

**Week 3-4: Pre-Audit Preparation**
- [ ] Document attack surface
  - API endpoints (50+ total)
  - Authentication mechanisms (OIDC, LDAP, SAML, API keys)
  - Data flows (user → AI → Gateway → MCP → external systems)
  - Trust boundaries (client ↔ gateway ↔ OPA ↔ database)

- [ ] Create security questionnaire responses
  - OWASP Top 10 mitigations
  - Encryption (TLS 1.3, at-rest, in-transit)
  - Secret management (environment variables, K8s secrets)
  - Access controls (RBAC, sensitivity levels, time-based)
  - Audit logging (immutable, SIEM integration)

- [ ] Provide test environment
  - Staging cluster with production-like configuration
  - Test accounts (admin, developer, restricted user)
  - Sample data (synthetic PII, not production data)
  - Monitoring/logging access for auditors

- [ ] Define scope
  - **In Scope:** API, authentication, authorization, MCP gateway, OPA policies
  - **Out of Scope:** Frontend UI, infrastructure (K8s), dependencies (OPA, PostgreSQL)

**Week 5-6: Security Testing**
- Performed by external vendor
- Expected findings: 5-10 medium-severity issues
- Critical path blocker: Any high/critical severity finding

**Week 7: Remediation**
- Fix identified vulnerabilities
- Re-test fixes with vendor
- Document mitigations

**Deliverables:**
- ✅ Security audit report (external)
- ✅ Remediation plan for findings
- ✅ Penetration test certification

---

## Priority 2: High (Weeks 5-8)

**Goal:** Add advanced security features and operational capabilities

### 2.1 Prompt Injection Detection

**Current State:** No detection of injection patterns in tool parameters
**Target State:** Real-time detection with configurable response (block/alert/log)
**Effort:** 2 weeks, 1 developer
**Files to Create:** `sark/prompt_injection_detector.py`, `tests/test_injection_detector.py`

#### Tasks

**Week 5: Detection Engine**
- [ ] Implement pattern-based detector
  ```python
  class PromptInjectionDetector:
      """Detects potential prompt injection in tool parameters"""

      # Known injection patterns (regex)
      INJECTION_PATTERNS = [
          # Instruction overrides
          r"ignore\s+(previous|all|above)\s+instructions?",
          r"disregard\s+(previous|all|above)\s+(instructions?|rules?)",
          r"forget\s+(previous|all|everything)",

          # Role manipulation
          r"you\s+are\s+now\s+(a|an)\s+",
          r"act\s+as\s+(a|an)\s+",
          r"pretend\s+(you|to)\s+",

          # Data exfiltration
          r"send\s+.+\s+to\s+https?://",
          r"export\s+.+\s+to\s+https?://",
          r"post\s+.+\s+to\s+https?://",

          # System prompts
          r"system\s*:\s*",
          r"<\s*system\s*>",

          # Encoded/obfuscated
          r"base64\s*\(",
          r"eval\s*\(",
          r"exec\s*\(",
      ]

      # Entropy-based detection (high randomness = potential encoding)
      ENTROPY_THRESHOLD = 4.5

      def detect(self, params: dict) -> InjectionDetectionResult:
          """Scan parameters for injection patterns"""
          findings = []

          # Scan all string values
          for key, value in self._flatten_params(params).items():
              if not isinstance(value, str):
                  continue

              # Pattern matching
              for pattern in self.INJECTION_PATTERNS:
                  if re.search(pattern, value, re.IGNORECASE):
                      findings.append(InjectionFinding(
                          severity="high",
                          param_name=key,
                          pattern=pattern,
                          matched_text=re.search(pattern, value, re.IGNORECASE).group(),
                          recommendation="Block request - known injection pattern"
                      ))

              # Entropy check
              entropy = self._calculate_entropy(value)
              if entropy > self.ENTROPY_THRESHOLD and len(value) > 50:
                  findings.append(InjectionFinding(
                      severity="medium",
                      param_name=key,
                      pattern="high_entropy",
                      matched_text=value[:100],
                      recommendation="Potential encoded payload"
                  ))

              # URL check (unexpected external URLs)
              urls = re.findall(r"https?://[^\s]+", value)
              for url in urls:
                  if not self._is_whitelisted_domain(url):
                      findings.append(InjectionFinding(
                          severity="medium",
                          param_name=key,
                          pattern="unknown_url",
                          matched_text=url,
                          recommendation="Verify URL is expected"
                      ))

          return InjectionDetectionResult(
              detected=len(findings) > 0,
              findings=findings,
              risk_score=self._calculate_risk_score(findings)
          )

      def _calculate_entropy(self, text: str) -> float:
          """Calculate Shannon entropy"""
          if not text:
              return 0.0

          char_counts = {}
          for char in text:
              char_counts[char] = char_counts.get(char, 0) + 1

          entropy = 0.0
          text_len = len(text)
          for count in char_counts.values():
              probability = count / text_len
              entropy -= probability * math.log2(probability)

          return entropy

      def _calculate_risk_score(self, findings: list[InjectionFinding]) -> int:
          """Risk score 0-100"""
          score = 0
          for finding in findings:
              if finding.severity == "high":
                  score += 30
              elif finding.severity == "medium":
                  score += 15
              elif finding.severity == "low":
                  score += 5

          return min(score, 100)
  ```

**Week 6: Integration & Response Actions**
- [ ] Add configurable response modes
  ```python
  class InjectionResponseHandler:
      """Handle detected injections based on policy"""

      async def handle(
          self,
          detection: InjectionDetectionResult,
          request_context: dict
      ) -> InjectionResponse:
          """Process detection result"""

          # Get policy decision
          policy = await self._get_injection_policy(request_context)

          if detection.risk_score >= policy.block_threshold:
              # Block request
              await self.audit_logger.log_event(
                  event_type="injection_blocked",
                  user_id=request_context["user_id"],
                  findings=detection.findings,
                  risk_score=detection.risk_score
              )

              return InjectionResponse(
                  action="block",
                  message="Request blocked due to potential prompt injection",
                  details=detection.findings
              )

          elif detection.risk_score >= policy.alert_threshold:
              # Allow but alert
              await self.alert_manager.send_alert(
                  severity="warning",
                  title="Potential prompt injection detected",
                  details={
                      "user_id": request_context["user_id"],
                      "findings": detection.findings,
                      "risk_score": detection.risk_score
                  }
              )

              return InjectionResponse(
                  action="allow_with_alert",
                  message="Request allowed but flagged for review"
              )

          else:
              # Log only
              await self.audit_logger.log_event(
                  event_type="injection_detected_low_risk",
                  user_id=request_context["user_id"],
                  findings=detection.findings,
                  risk_score=detection.risk_score
              )

              return InjectionResponse(action="allow")
  ```

- [ ] Add to gateway authorization flow
  ```python
  async def authorize_gateway_request(...) -> GatewayAuthorizationResponse:
      # Existing authorization logic
      opa_result = await self.opa_client.evaluate(...)

      # NEW: Prompt injection detection
      injection_result = await self.injection_detector.detect(params)

      if injection_result.detected:
          response = await self.injection_handler.handle(
              injection_result,
              {"user_id": user_id, "server_id": server_id, "tool_name": tool_name}
          )

          if response.action == "block":
              return GatewayAuthorizationResponse(
                  allowed=False,
                  reason=response.message,
                  metadata={"injection_findings": injection_result.findings}
              )

      # Continue with normal flow
      return GatewayAuthorizationResponse(...)
  ```

- [ ] Create injection pattern database (YAML)
  ```yaml
  # config/injection_patterns.yaml
  patterns:
    - name: "Ignore instructions"
      regex: "ignore\\s+(previous|all|above)\\s+instructions?"
      severity: "high"
      action: "block"

    - name: "Data exfiltration"
      regex: "(send|export|post)\\s+.+\\s+to\\s+https?://"
      severity: "high"
      action: "block"

    - name: "Base64 encoding"
      regex: "base64\\s*\\("
      severity: "medium"
      action: "alert"
  ```

- [ ] Add monitoring dashboard for injection attempts
  ```python
  # Prometheus metrics
  injection_detections_total = Counter(
      "sark_injection_detections_total",
      "Total prompt injection detections",
      ["severity", "action"]
  )

  injection_risk_score = Histogram(
      "sark_injection_risk_score",
      "Distribution of injection risk scores",
      buckets=[10, 25, 50, 75, 90, 100]
  )
  ```

**Deliverables:**
- ✅ Prompt injection detector with 20+ patterns
- ✅ Configurable response (block/alert/log)
- ✅ Monitoring dashboard
- ✅ 95%+ detection rate on test dataset

---

### 2.2 Anomaly Detection System

**Current State:** No behavioral analysis or anomaly detection
**Target State:** Real-time detection of unusual access patterns
**Effort:** 2 weeks, 1 developer
**Files to Create:** `sark/anomaly_detector.py`, `sark/behavioral_analysis.py`

#### Tasks

**Week 7: Baseline & Detection**
- [ ] Implement behavioral baseline
  ```python
  class BehavioralAnalyzer:
      """Analyze user/agent behavior to detect anomalies"""

      async def build_baseline(self, user_id: str, lookback_days: int = 30):
          """Build normal behavior profile"""

          # Query historical audit logs
          events = await self.audit_db.query(
              user_id=user_id,
              start_date=datetime.now() - timedelta(days=lookback_days)
          )

          baseline = {
              "tools": {
                  # Tool usage frequency
                  "most_common": self._top_n_tools(events, n=10),
                  "avg_calls_per_day": len(events) / lookback_days,
              },
              "timing": {
                  # Access patterns
                  "typical_hours": self._extract_hour_distribution(events),
                  "typical_days": self._extract_day_distribution(events),
              },
              "data_volume": {
                  # Data access patterns
                  "avg_records_per_query": self._avg_result_size(events),
                  "max_records_per_query": max(e.result_size for e in events),
              },
              "sensitivity": {
                  # Resource sensitivity accessed
                  "max_sensitivity_level": max(e.sensitivity for e in events),
                  "typical_sensitivity": mode(e.sensitivity for e in events),
              }
          }

          # Store baseline
          await self.baseline_db.save(user_id, baseline)

          return baseline

      async def detect_anomalies(self, event: AuditEvent) -> list[Anomaly]:
          """Compare event against baseline"""

          baseline = await self.baseline_db.get(event.user_id)
          if not baseline:
              return []  # No baseline yet

          anomalies = []

          # Check tool usage
          if event.tool_name not in baseline["tools"]["most_common"]:
              anomalies.append(Anomaly(
                  type="unusual_tool",
                  severity="low",
                  message=f"User rarely uses tool '{event.tool_name}'"
              ))

          # Check timing
          event_hour = event.timestamp.hour
          if event_hour not in baseline["timing"]["typical_hours"]:
              anomalies.append(Anomaly(
                  type="unusual_time",
                  severity="medium",
                  message=f"Access at unusual hour: {event_hour}"
              ))

          # Check data volume
          if event.result_size > baseline["data_volume"]["max_records_per_query"] * 2:
              anomalies.append(Anomaly(
                  type="excessive_data_access",
                  severity="high",
                  message=f"Query returned {event.result_size} records (2x baseline max)"
              ))

          # Check sensitivity escalation
          baseline_max = baseline["sensitivity"]["max_sensitivity_level"]
          if event.sensitivity > baseline_max:
              anomalies.append(Anomaly(
                  type="sensitivity_escalation",
                  severity="high",
                  message=f"Accessing {event.sensitivity} resource (baseline max: {baseline_max})"
              ))

          return anomalies
  ```

**Week 8: Alerting & Response**
- [ ] Implement real-time alerting
  ```python
  class AnomalyAlertManager:
      """Send alerts for detected anomalies"""

      async def process_anomalies(self, anomalies: list[Anomaly], event: AuditEvent):
          """Determine alert action based on anomaly severity"""

          # Calculate aggregate risk
          high_count = sum(1 for a in anomalies if a.severity == "high")
          medium_count = sum(1 for a in anomalies if a.severity == "medium")

          if high_count >= 2:
              # Multiple high-severity anomalies = immediate alert
              await self._send_alert(
                  channel="pagerduty",
                  severity="critical",
                  title=f"Multiple anomalies detected for user {event.user_id}",
                  details={"anomalies": anomalies, "event": event}
              )

              # Auto-suspend user if configured
              if self.config.auto_suspend_on_critical:
                  await self._suspend_user(event.user_id, reason="Anomaly detection")

          elif high_count == 1 or medium_count >= 3:
              # Single high or multiple medium = warning alert
              await self._send_alert(
                  channel="slack",
                  severity="warning",
                  title=f"Anomalies detected for user {event.user_id}",
                  details={"anomalies": anomalies, "event": event}
              )

          # Always log
          await self.audit_logger.log_event(
              event_type="anomaly_detected",
              user_id=event.user_id,
              anomalies=[a.dict() for a in anomalies]
          )
  ```

- [ ] Add anomaly detection to gateway flow
  ```python
  # In gateway.py after tool invocation
  async def invoke_tool(...):
      result = await self._execute_tool(...)

      # Log to audit
      event = await self.audit_logger.log_gateway_event(...)

      # NEW: Anomaly detection
      anomalies = await self.anomaly_detector.detect_anomalies(event)
      if anomalies:
          await self.alert_manager.process_anomalies(anomalies, event)

      return result
  ```

**Deliverables:**
- ✅ Behavioral baseline for all users
- ✅ Real-time anomaly detection (5 types)
- ✅ Alerting integration (Slack, PagerDuty, email)
- ✅ 80%+ detection rate on simulated attacks

---

### 2.3 Network-Level Controls

**Current State:** Application-layer controls only
**Target State:** Defense-in-depth with network segmentation
**Effort:** 1 week, 1 developer
**Files to Create:** `k8s/network-policies/`, `terraform/modules/network/`

#### Tasks

**Week 8: Kubernetes Network Policies**
- [ ] Create network policies
  ```yaml
  # k8s/network-policies/gateway-egress.yaml
  apiVersion: networking.k8s.io/v1
  kind: NetworkPolicy
  metadata:
    name: gateway-egress-policy
    namespace: sark
  spec:
    podSelector:
      matchLabels:
        app: sark-gateway
    policyTypes:
      - Egress
    egress:
      # Allow DNS
      - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
        ports:
          - protocol: UDP
            port: 53

      # Allow PostgreSQL
      - to:
        - podSelector:
            matchLabels:
              app: postgresql
        ports:
          - protocol: TCP
            port: 5432

      # Allow Redis
      - to:
        - podSelector:
            matchLabels:
              app: redis
        ports:
          - protocol: TCP
            port: 6379

      # Allow OPA
      - to:
        - podSelector:
            matchLabels:
              app: opa
        ports:
          - protocol: TCP
            port: 8181

      # Allow whitelisted external domains only
      - to:
        - namespaceSelector: {}
        ports:
          - protocol: TCP
            port: 443
        # Note: Domain-based egress filtering requires service mesh
  ```

- [ ] Implement egress filtering (Calico or Istio)
  ```yaml
  # k8s/network-policies/egress-allow-list.yaml (Calico)
  apiVersion: projectcalico.org/v3
  kind: GlobalNetworkPolicy
  metadata:
    name: sark-egress-whitelist
  spec:
    selector: app == 'sark-gateway'
    types:
      - Egress
    egress:
      # Allow specific external domains
      - action: Allow
        destination:
          domains:
            - "*.openai.com"
            - "*.anthropic.com"
            - "internal-mcp-server.company.com"
        protocol: TCP
        ports:
          - 443

      # Deny all other egress
      - action: Deny
  ```

- [ ] Add firewall rules (cloud provider)
  ```hcl
  # terraform/modules/network/firewall.tf (AWS)
  resource "aws_security_group" "sark_gateway" {
    name        = "sark-gateway-sg"
    description = "Security group for Sark gateway"
    vpc_id      = var.vpc_id

    # Egress: Allow HTTPS to whitelisted IPs only
    egress {
      description = "Allow HTTPS to MCP servers"
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = var.mcp_server_cidrs  # ["10.0.0.0/8", "172.16.0.0/12"]
    }

    # Deny all other egress
    egress {
      from_port   = 0
      to_port     = 0
      protocol    = "-1"
      cidr_blocks = ["127.0.0.1/32"]  # Unreachable, effectively denies
    }
  }
  ```

**Deliverables:**
- ✅ Kubernetes NetworkPolicies for all components
- ✅ Egress filtering (domain whitelist)
- ✅ Cloud firewall rules (AWS, GCP, Azure)
- ✅ Documentation: Network architecture diagram

---

## Priority 3: Medium (Weeks 9-10)

**Goal:** Add operational features and polish

### 3.1 Secret Scanning

**Effort:** 1 week, 1 developer

- [ ] Implement secret scanner for tool responses
  ```python
  class SecretScanner:
      """Scan tool responses for accidentally exposed secrets"""

      SECRET_PATTERNS = [
          (r"sk-[a-zA-Z0-9]{48}", "OpenAI API Key"),
          (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token"),
          (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
          (r"-----BEGIN PRIVATE KEY-----", "Private Key"),
          (r"[a-zA-Z0-9+/=]{32,}", "Potential Base64 Secret"),
      ]

      def scan(self, data: dict) -> list[SecretFinding]:
          findings = []

          for key, value in self._flatten_dict(data).items():
              if not isinstance(value, str):
                  continue

              for pattern, secret_type in self.SECRET_PATTERNS:
                  matches = re.findall(pattern, value)
                  for match in matches:
                      findings.append(SecretFinding(
                          secret_type=secret_type,
                          location=key,
                          matched_value=match[:10] + "..." # Truncate for logging
                      ))

          return findings
  ```

- [ ] Add redaction option
  ```python
  def redact_secrets(self, data: dict, findings: list[SecretFinding]) -> dict:
      """Replace secrets with [REDACTED]"""
      redacted = copy.deepcopy(data)

      for finding in findings:
          # Navigate to location and redact
          keys = finding.location.split(".")
          current = redacted
          for key in keys[:-1]:
              current = current[key]

          current[keys[-1]] = "[REDACTED]"

      return redacted
  ```

---

### 3.2 MFA for Critical Actions

**Effort:** 1 week, 1 developer

- [ ] Implement MFA challenge for high-sensitivity resources
  ```python
  class MFAChallenge:
      async def require_mfa(self, user_id: str, action: str) -> bool:
          """Send MFA challenge and wait for approval"""

          # Generate challenge
          challenge_code = self._generate_code()

          # Send via configured channel (SMS, TOTP, push notification)
          await self._send_challenge(user_id, challenge_code)

          # Wait for response (timeout: 60 seconds)
          response = await self._wait_for_response(user_id, timeout=60)

          if response == challenge_code:
              return True

          # Log failed MFA
          await self.audit_logger.log_event(
              event_type="mfa_failed",
              user_id=user_id,
              action=action
          )

          return False
  ```

- [ ] Add to authorization flow
  ```python
  async def authorize_gateway_request(...):
      # Existing checks
      opa_result = await self.opa_client.evaluate(...)

      # NEW: MFA for critical resources
      if sensitivity == "critical" and self.config.mfa_enabled:
          mfa_passed = await self.mfa_challenge.require_mfa(user_id, tool_name)

          if not mfa_passed:
              return GatewayAuthorizationResponse(
                  allowed=False,
                  reason="MFA required for critical resource"
              )

      return GatewayAuthorizationResponse(...)
  ```

---

## Priority 4: Low (Weeks 11-12)

**Goal:** Future enhancements and nice-to-haves

### 4.1 Cost Attribution System

**Effort:** 1 week

- [ ] Implement token counting and cost tracking
- [ ] Add budget alerts
- [ ] Create cost dashboard

### 4.2 Complete Federation (GRID Protocol)

**Effort:** 1 week

- [ ] Implement remaining 15% of GRID spec
- [ ] Add cross-organization trust management
- [ ] Improve mTLS certificate rotation

---

## Technical Specifications

### Gateway Client Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GATEWAY CLIENT                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐      ┌────────────┐ │
│  │   HTTP       │      │     SSE      │      │   stdio    │ │
│  │   Client     │      │   Client     │      │   Client   │ │
│  └──────┬───────┘      └──────┬───────┘      └─────┬──────┘ │
│         │                     │                     │        │
│         └─────────────────────┼─────────────────────┘        │
│                               ▼                              │
│                    ┌──────────────────┐                      │
│                    │  MCP Adapter     │                      │
│                    │  - Normalize     │                      │
│                    │  - Retry logic   │                      │
│                    │  - Circuit break │                      │
│                    └────────┬─────────┘                      │
│                             ▼                                │
│                    ┌──────────────────┐                      │
│                    │  Authorization   │                      │
│                    │  - OPA policy    │                      │
│                    │  - Parameter     │                      │
│                    │    filtering     │                      │
│                    └────────┬─────────┘                      │
│                             ▼                                │
│                    ┌──────────────────┐                      │
│                    │ Injection Check  │                      │
│                    │ - Pattern match  │                      │
│                    │ - Entropy calc   │                      │
│                    └────────┬─────────┘                      │
│                             ▼                                │
│                    ┌──────────────────┐                      │
│                    │  Tool Invocation │                      │
│                    └────────┬─────────┘                      │
│                             ▼                                │
│                    ┌──────────────────┐                      │
│                    │  Audit Logging   │                      │
│                    │  - Event         │                      │
│                    │  - Anomaly check │                      │
│                    │  - SIEM forward  │                      │
│                    └──────────────────┘                      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Injection Detection Flow

```
Tool Parameters
      ▼
┌──────────────┐
│ Flatten Dict │ → ["query": "SELECT * FROM users", "webhook": "http://evil.com"]
└──────┬───────┘
       ▼
┌──────────────┐
│ Pattern Scan │ → Check against 20+ regex patterns
└──────┬───────┘
       ▼
┌──────────────┐
│ Entropy Calc │ → Shannon entropy > 4.5 = suspicious
└──────┬───────┘
       ▼
┌──────────────┐
│  URL Check   │ → Verify against domain whitelist
└──────┬───────┘
       ▼
┌──────────────┐
│ Risk Score   │ → High: 30pts, Medium: 15pts, Low: 5pts
└──────┬───────┘
       ▼
┌──────────────────────────────────────┐
│ Response Action                       │
│ - Score ≥ 75: BLOCK                  │
│ - Score 50-74: ALERT + ALLOW         │
│ - Score < 50: LOG                    │
└──────────────────────────────────────┘
```

---

## Testing Strategy

### Test Pyramid

```
            ┌──────┐
           │  E2E  │  20 tests  (Selenium, full scenarios)
          ┌┴───────┴┐
         │Integration│  80 tests  (API tests, multi-component)
        ┌┴───────────┴┐
       │     Unit      │  200 tests (Function-level, mocked dependencies)
      └───────────────┘
```

### Coverage Requirements

| Component | Target Coverage | Current | Gap |
|-----------|-----------------|---------|-----|
| Gateway Client | 90% | 0% (stubbed) | +90% |
| Authorization | 95% | 88% | +7% |
| Authentication | 85% | 65% (tests failing) | +20% |
| Injection Detection | 90% | 0% (not implemented) | +90% |
| Anomaly Detection | 85% | 0% (not implemented) | +85% |
| **Overall** | **85%** | **64%** | **+21%** |

### Test Types

**Unit Tests (200 total)**
- Authorization logic (50 tests)
- Parameter filtering (30 tests)
- Injection detection (40 tests)
- Anomaly detection (30 tests)
- Policy validation (20 tests)
- Helper functions (30 tests)

**Integration Tests (80 total)**
- Gateway client (30 tests)
  - HTTP transport end-to-end
  - SSE streaming
  - stdio process management
- Authentication flows (25 tests)
  - OIDC, LDAP, SAML, API key
- Authorization flows (15 tests)
  - Multi-layer policy evaluation
- Audit logging (10 tests)
  - SIEM integration

**E2E Tests (20 total)**
- Sensitive data access (5 tests)
  - Admin can access, developer cannot
- Prompt injection scenarios (5 tests)
  - Injection blocked, legitimate request allowed
- Anomaly detection scenarios (5 tests)
  - Unusual access patterns trigger alerts
- Performance tests (5 tests)
  - Load testing, latency measurement

---

## Security Audit Plan

### Scope

**In-Scope Components:**
1. API Endpoints (authentication, authorization, gateway, audit)
2. Authentication mechanisms (OIDC, LDAP, SAML, API keys)
3. Authorization engine (OPA policies, parameter filtering)
4. MCP Gateway (tool invocation, MCP client)
5. Injection detection (prompt injection, policy injection)
6. Audit logging (immutability, SIEM integration)

**Testing Methods:**
- Automated vulnerability scanning (OWASP ZAP, Burp Suite)
- Manual penetration testing
- Code review (security-focused)
- Architecture review
- Policy analysis (OPA Rego code)

### Expected Findings

**Likely Issues (based on common patterns):**
1. **Medium:** Session fixation vulnerability
2. **Medium:** CSRF token reuse possible
3. **Low:** Verbose error messages leak implementation details
4. **Low:** Missing rate limiting on some endpoints
5. **Info:** Security headers could be stricter (CSP)

### Remediation SLA

| Severity | Remediation Deadline | Re-test Required |
|----------|---------------------|------------------|
| Critical | 48 hours | Yes |
| High | 1 week | Yes |
| Medium | 2 weeks | Optional |
| Low | 4 weeks | No |

---

## Deployment Strategy

### Phased Rollout

**Phase 1: Staging (Week 9)**
- Deploy to staging environment
- Run automated tests (CI/CD)
- Manual testing by QA team
- Performance testing (load test)

**Phase 2: Canary (Week 10)**
- Deploy to 5% of production traffic
- Monitor for errors/anomalies
- Gradual increase: 5% → 25% → 50%

**Phase 3: Full Production (Week 11)**
- Deploy to 100% of production
- Enable all features
- Full monitoring

### Rollback Plan

**Triggers:**
- Error rate > 1%
- Latency p95 > 200ms (2x normal)
- Critical security issue discovered
- Database corruption

**Rollback Procedure:**
1. Trigger: Alert fires (PagerDuty)
2. Assess: On-call engineer reviews logs
3. Decision: Rollback if issue confirmed (< 5 minutes)
4. Execute: Deploy previous version via Helm
5. Verify: Check metrics return to normal
6. Post-mortem: Document root cause

---

## Risk Management

### Risk Register

| Risk | Probability | Impact | Mitigation | Owner |
|------|-------------|--------|------------|-------|
| Gateway implementation takes longer than estimated | High | High | Allocate buffer time, consider reducing scope | Tech Lead |
| Security audit finds critical vulnerability | Medium | Critical | Address immediately, delay production deployment | Security |
| Test coverage improvement blocked by tech debt | Medium | Medium | Refactor problematic code, write tests iteratively | Dev Team |
| Performance degradation from injection detection | Low | Medium | Optimize regex patterns, add caching | Performance |
| OPA policy validation breaks existing policies | Medium | High | Gradual rollout, extensive testing | Policy Team |

### Contingency Plans

**If Gateway takes > 4 weeks:**
- Option 1: Ship with HTTP-only support (defer SSE, stdio to v2.2)
- Option 2: Hire contractor with MCP experience
- Option 3: Delay v2.1 release by 2 weeks

**If security audit fails:**
- Option 1: Fix critical issues, defer medium/low to v2.1.1
- Option 2: Deploy to staging only, iterate until passed
- Option 3: Engage security consultant for remediation

---

## Success Metrics

### Functional Metrics

- ✅ Gateway client: 100% of planned features implemented
- ✅ Test coverage: 85%+ with 0 failing tests
- ✅ Injection detection: 95%+ true positive rate, <5% false positive rate
- ✅ Anomaly detection: 80%+ detection rate on simulated attacks
- ✅ Policy validation: 0 invalid policies in production

### Performance Metrics

- ✅ API latency: p95 < 100ms (no regression from current)
- ✅ Throughput: 850+ req/s sustained (10% improvement)
- ✅ Injection detection overhead: < 10ms per request
- ✅ Anomaly detection overhead: < 5ms per request

### Security Metrics

- ✅ Security audit: Passed (0 critical, 0 high vulnerabilities)
- ✅ Injection detection: 0 bypasses in testing
- ✅ Anomaly detection: 95%+ alert accuracy (low false positives)
- ✅ Policy validation: 100% of policies validated before load

### Operational Metrics

- ✅ Deployment success rate: 95%+ (no rollbacks in first month)
- ✅ MTTR (mean time to recovery): < 30 minutes
- ✅ Alert fatigue: < 5 false positive alerts per day
- ✅ Documentation: 100% of new features documented

---

## Timeline Summary

```
Week 1-2:  Gateway HTTP/SSE transport
Week 3:    Gateway stdio transport
Week 4:    Gateway integration & tests
Week 5:    Prompt injection detection
Week 6:    Injection integration & response
Week 7:    Anomaly detection baseline
Week 8:    Anomaly alerting & network policies
Week 9:    Fix failing tests, staging deployment
Week 10:   Policy validation, canary deployment
Week 11:   Secret scanning, MFA, production deployment
Week 12:   Cost attribution, polish, v2.1.0 release
```

**Critical Path:** Gateway (Weeks 1-4) → Tests (Week 9) → Security Audit (External) → Production (Week 11)

**Buffer:** 1 week built into estimates (12 weeks planned, 11 weeks critical path)

---

## Appendix: Code Examples

### Example: Complete Gateway Tool Invocation

```python
async def invoke_tool_complete_flow(
    gateway_client: GatewayClient,
    user_id: str,
    server_id: str,
    tool_name: str,
    params: dict
) -> GatewayToolResult:
    """
    Complete tool invocation flow with all security checks
    """

    # 1. Get server info
    server = await gateway_client.get_server_info(server_id)
    if not server:
        raise ValueError(f"Server {server_id} not found")

    # 2. Authorize request (OPA policy + parameter filtering)
    auth_result = await gateway_client.authorize_gateway_request(
        user_id=user_id,
        server_id=server_id,
        tool_name=tool_name,
        params=params,
        sensitivity=server.sensitivity_level
    )

    if not auth_result.allowed:
        raise GatewayAuthorizationError(auth_result.reason)

    # 3. Injection detection
    injection_result = await gateway_client.injection_detector.detect(params)
    if injection_result.risk_score >= 75:
        raise InjectionDetectedError(
            f"Potential prompt injection (risk score: {injection_result.risk_score})"
        )

    # 4. Invoke tool with filtered parameters
    result = await gateway_client.invoke_tool(
        server_id=server_id,
        tool_name=tool_name,
        params=auth_result.filtered_params,
        user_context={"user_id": user_id}
    )

    # 5. Secret scanning on response
    secret_findings = await gateway_client.secret_scanner.scan(result.data)
    if secret_findings:
        result.data = gateway_client.secret_scanner.redact_secrets(
            result.data,
            secret_findings
        )

        # Alert on secret exposure
        await gateway_client.alert_manager.send_alert(
            severity="warning",
            title="Secrets detected in tool response",
            details={"findings": secret_findings}
        )

    # 6. Anomaly detection
    audit_event = await gateway_client.audit_logger.log_gateway_event(
        event_type="tool_invocation",
        user_id=user_id,
        server_id=server_id,
        tool_name=tool_name,
        decision="allow",
        result_size=len(result.data)
    )

    anomalies = await gateway_client.anomaly_detector.detect_anomalies(audit_event)
    if anomalies:
        await gateway_client.alert_manager.process_anomalies(anomalies, audit_event)

    return result
```

### Example: Policy Test Suite

```yaml
# policies/tests/gateway_authorization_test.yaml
name: "Gateway Authorization Policy Tests"
description: "Test suite for gateway authorization OPA policy"

tests:
  - name: "Admin can access critical resources"
    input:
      user:
        id: "admin1"
        role: "admin"
        teams: ["platform"]
      resource:
        server_id: "db_prod"
        tool_name: "query_customers"
        sensitivity: "critical"
        authorized_teams: ["platform"]
      context:
        timestamp: "2025-12-08T14:30:00Z"
        ip_address: "10.0.1.50"
    expected:
      allow: true
      filtered_params: {}
      cache_ttl_seconds: 0
      reason: null

  - name: "Developer cannot access critical resources"
    input:
      user:
        id: "dev1"
        role: "developer"
        teams: ["engineering"]
      resource:
        server_id: "db_prod"
        tool_name: "query_customers"
        sensitivity: "critical"
        authorized_teams: ["platform"]
      context:
        timestamp: "2025-12-08T14:30:00Z"
        ip_address: "10.0.2.100"
    expected:
      allow: false
      reason: "Insufficient permissions for critical resource"

  - name: "Sensitive parameters filtered for non-admin"
    input:
      user:
        id: "dev2"
        role: "developer"
        teams: ["engineering"]
      resource:
        server_id: "api_prod"
        tool_name: "get_config"
        sensitivity: "medium"
        authorized_teams: ["engineering"]
      params:
        include_secrets: true
        include_api_keys: true
        include_public: true
      context:
        timestamp: "2025-12-08T14:30:00Z"
    expected:
      allow: true
      filtered_params:
        include_public: true
        # include_secrets and include_api_keys should be removed
      reason: null

  - name: "Access denied outside work hours for high-sensitivity"
    input:
      user:
        id: "admin2"
        role: "admin"
        teams: ["platform"]
      resource:
        server_id: "db_prod"
        tool_name: "export_data"
        sensitivity: "high"
        authorized_teams: ["platform"]
      context:
        timestamp: "2025-12-08T02:00:00Z"  # 2 AM
        ip_address: "10.0.1.50"
    expected:
      allow: false
      reason: "High-sensitivity resources only accessible during work hours (9 AM - 5 PM)"
```

---

**Document Prepared By:** Claude (Anthropic AI)
**Review Required:** Architecture team, Security team, Product team
**Approval Required:** CTO, CISO
**Next Steps:** Review and approve plan, assign resources, begin Week 1 tasks
