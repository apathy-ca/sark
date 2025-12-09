# SARK v1.3.0 Implementation Plan
## Advanced Lethal Trifecta Security Mitigations

**Version:** 1.0
**Date:** December 9, 2025
**Target Release:** v1.3.0
**Prerequisites:** v1.2.0 complete (Gateway + Policy Validation + Tests)
**Duration:** 7-8 weeks
**Orchestration:** Czarina multi-agent system

---

## Executive Summary

v1.3.0 implements the advanced security features identified in the Lethal Trifecta Analysis but deferred from v1.2.0 as non-blocking enhancements. These features significantly improve security posture but are not required for basic production deployment (v2.0.0).

**What v1.3.0 Delivers:**
- ✅ Prompt injection detection (pattern-based + entropy analysis)
- ✅ Anomaly detection system (behavioral baselines + alerting)
- ✅ Network-level controls (K8s NetworkPolicies + egress filtering)
- ✅ Secret scanning (detect exposed credentials in responses)
- ✅ MFA for critical actions (TOTP/SMS/Push for high-sensitivity resources)

**Success Criteria:**
- Prompt injection detection: 95%+ true positive rate, <5% false positive rate
- Anomaly detection: 80%+ detection rate on simulated attacks
- Network policies enforced in production
- Secret exposure prevented
- MFA operational for critical resources

**Strategic Position:**
- v1.3.0 = Advanced security (nice-to-have)
- v2.0.0 = Production release (after security audit)
- v1.4.0 = Performance optimization (Rust)

---

## Work Stream Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CZARINA ORCHESTRATION                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Stream 1: Prompt Injection    Stream 2: Anomaly Detection      │
│  ┌──────────────────┐          ┌──────────────────┐            │
│  │ Worker: SECURITY-1│          │ Worker: SECURITY-2│           │
│  │ Weeks 1-2        │          │ Weeks 3-4        │            │
│  │ +Pattern detector│          │ +Baseline builder│            │
│  │ +Entropy analysis│          │ +Alert system    │            │
│  └──────────────────┘          └──────────────────┘            │
│                                                                   │
│  Stream 3: Network Controls    Stream 4: Secret Scanning        │
│  ┌──────────────────┐          ┌──────────────────┐            │
│  │ Worker: DEVOPS   │          │ Worker: SECURITY-3│           │
│  │ Week 5           │          │ Week 6           │            │
│  │ +K8s policies    │          │ +Pattern scanner │            │
│  │ +Egress filter   │          │ +Redaction       │            │
│  └──────────────────┘          └──────────────────┘            │
│                                                                   │
│  Stream 5: MFA System          Stream 6: Integration            │
│  ┌──────────────────┐          ┌──────────────────┐            │
│  │ Worker: SECURITY-4│          │ Worker: QA       │           │
│  │ Week 7           │          │ Week 8           │            │
│  │ +TOTP/SMS/Push   │          │ +E2E tests       │            │
│  │ +Challenge flow  │          │ +Performance     │            │
│  └──────────────────┘          └──────────────────┘            │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

**Parallelization:**
- Weeks 1-2: Stream 1 (independent)
- Weeks 3-4: Stream 2 (independent)
- Week 5: Stream 3 (independent)
- Week 6: Stream 4 (independent)
- Week 7: Stream 5 (independent)
- Week 8: Stream 6 (integrates all streams)

---

## Stream 1: Prompt Injection Detection (SECURITY-1)

**Worker Assignment:** `SECURITY-1` (Aider recommended)
**Duration:** Weeks 1-2 (2 weeks)
**Branch:** `feat/prompt-injection-detection`
**Dependencies:** None
**Estimated Effort:** 2 weeks, 1 worker

### Week 1: Detection Engine

**Task 1.1: Pattern-Based Detector** (2 days)
- **File:** `src/sark/security/injection_detector.py` (NEW)
- **Implementation:**
  ```python
  class PromptInjectionDetector:
      """Detects prompt injection patterns in tool parameters"""

      # 20+ injection patterns
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

      def detect(self, params: dict) -> InjectionDetectionResult:
          findings = []

          for key, value in self._flatten_params(params).items():
              if not isinstance(value, str):
                  continue

              # Pattern matching
              for pattern in self.INJECTION_PATTERNS:
                  if re.search(pattern, value, re.IGNORECASE):
                      findings.append(InjectionFinding(...))

          return InjectionDetectionResult(detected=len(findings) > 0, findings=findings)
  ```

**Task 1.2: Entropy Analysis** (2 days)
- **File:** `src/sark/security/injection_detector.py`
- **Implementation:**
  ```python
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

  # High entropy = potential encoded payload
  ENTROPY_THRESHOLD = 4.5

  if self._calculate_entropy(value) > self.ENTROPY_THRESHOLD and len(value) > 50:
      findings.append(InjectionFinding(
          severity="medium",
          pattern="high_entropy",
          recommendation="Potential encoded payload"
      ))
  ```

**Task 1.3: Risk Scoring** (1 day)
- **File:** `src/sark/security/injection_detector.py`
- **Implementation:**
  ```python
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

### Week 2: Integration & Response

**Task 2.1: Response Handler** (2 days)
- **File:** `src/sark/security/injection_response.py` (NEW)
- **Implementation:**
  ```python
  class InjectionResponseHandler:
      """Handle detected injections based on policy"""

      async def handle(
          self,
          detection: InjectionDetectionResult,
          request_context: dict
      ) -> InjectionResponse:
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
                  message="Request blocked due to potential prompt injection"
              )

          elif detection.risk_score >= policy.alert_threshold:
              # Allow but alert
              await self.alert_manager.send_alert(...)
              return InjectionResponse(action="allow_with_alert")

          else:
              # Log only
              await self.audit_logger.log_event(...)
              return InjectionResponse(action="allow")
  ```

**Task 2.2: Gateway Integration** (2 days)
- **File:** `src/sark/api/routers/gateway.py` (UPDATE)
- **Implementation:**
  ```python
  async def authorize_gateway_request(...):
      # Existing OPA authorization
      opa_result = await opa_client.evaluate(...)

      # NEW: Prompt injection detection
      injection_result = await injection_detector.detect(params)

      if injection_result.detected:
          response = await injection_handler.handle(
              injection_result,
              {"user_id": user_id, "server_id": server_id}
          )

          if response.action == "block":
              return GatewayAuthorizationResponse(
                  allowed=False,
                  reason=response.message
              )

      return GatewayAuthorizationResponse(...)
  ```

**Task 2.3: Pattern Database** (1 day)
- **File:** `config/injection_patterns.yaml` (NEW)
- **Content:**
  ```yaml
  patterns:
    - name: "Ignore instructions"
      regex: "ignore\\s+(previous|all|above)\\s+instructions?"
      severity: "high"
      action: "block"

    - name: "Data exfiltration"
      regex: "(send|export|post)\\s+.+\\s+to\\s+https?://"
      severity: "high"
      action: "block"
  ```

**Task 2.4: Tests** (1 day)
- **File:** `tests/unit/security/test_injection_detector.py` (NEW)
- **Coverage:**
  - All 20+ patterns tested
  - Entropy calculation edge cases
  - Risk scoring
  - Response handling (block/alert/log)
  - False positive scenarios

### Deliverables

**Code:**
- ✅ `src/sark/security/injection_detector.py` (200 lines)
- ✅ `src/sark/security/injection_response.py` (150 lines)
- ✅ `config/injection_patterns.yaml`
- ✅ `tests/unit/security/test_injection_detector.py` (300 lines)

**Documentation:**
- ✅ `docs/security/INJECTION_DETECTION.md`

**Acceptance:**
- [ ] 95%+ true positive rate on test dataset
- [ ] <5% false positive rate
- [ ] Integration tests passing
- [ ] Performance: <10ms per detection

---

## Stream 2: Anomaly Detection System (SECURITY-2)

**Worker Assignment:** `SECURITY-2` (Aider recommended)
**Duration:** Weeks 3-4 (2 weeks)
**Branch:** `feat/anomaly-detection`
**Dependencies:** None
**Estimated Effort:** 2 weeks, 1 worker

### Week 3: Behavioral Baseline

**Task 3.1: Baseline Builder** (3 days)
- **File:** `src/sark/security/behavioral_analyzer.py` (NEW)
- **Implementation:**
  ```python
  class BehavioralAnalyzer:
      async def build_baseline(self, user_id: str, lookback_days: int = 30):
          """Build normal behavior profile"""
          events = await self.audit_db.query(
              user_id=user_id,
              start_date=datetime.now() - timedelta(days=lookback_days)
          )

          baseline = {
              "tools": {
                  "most_common": self._top_n_tools(events, n=10),
                  "avg_calls_per_day": len(events) / lookback_days,
              },
              "timing": {
                  "typical_hours": self._extract_hour_distribution(events),
                  "typical_days": self._extract_day_distribution(events),
              },
              "data_volume": {
                  "avg_records_per_query": self._avg_result_size(events),
                  "max_records_per_query": max(e.result_size for e in events),
              },
              "sensitivity": {
                  "max_sensitivity_level": max(e.sensitivity for e in events),
                  "typical_sensitivity": mode(e.sensitivity for e in events),
              }
          }

          await self.baseline_db.save(user_id, baseline)
          return baseline
  ```

**Task 3.2: Anomaly Detection** (2 days)
- **File:** `src/sark/security/behavioral_analyzer.py`
- **Implementation:**
  ```python
  async def detect_anomalies(self, event: AuditEvent) -> list[Anomaly]:
      baseline = await self.baseline_db.get(event.user_id)
      if not baseline:
          return []

      anomalies = []

      # Unusual tool
      if event.tool_name not in baseline["tools"]["most_common"]:
          anomalies.append(Anomaly(type="unusual_tool", severity="low"))

      # Unusual time
      if event.timestamp.hour not in baseline["timing"]["typical_hours"]:
          anomalies.append(Anomaly(type="unusual_time", severity="medium"))

      # Excessive data access
      if event.result_size > baseline["data_volume"]["max_records"] * 2:
          anomalies.append(Anomaly(type="excessive_data", severity="high"))

      # Sensitivity escalation
      if event.sensitivity > baseline["sensitivity"]["max_sensitivity_level"]:
          anomalies.append(Anomaly(type="sensitivity_escalation", severity="high"))

      return anomalies
  ```

### Week 4: Alerting & Integration

**Task 4.1: Alert Manager** (2 days)
- **File:** `src/sark/security/anomaly_alerts.py` (NEW)
- **Implementation:**
  ```python
  class AnomalyAlertManager:
      async def process_anomalies(self, anomalies: list[Anomaly], event: AuditEvent):
          high_count = sum(1 for a in anomalies if a.severity == "high")
          medium_count = sum(1 for a in anomalies if a.severity == "medium")

          if high_count >= 2:
              # Critical alert
              await self._send_alert(
                  channel="pagerduty",
                  severity="critical",
                  title=f"Multiple anomalies: {event.user_id}"
              )

              if self.config.auto_suspend_on_critical:
                  await self._suspend_user(event.user_id, reason="Anomaly detection")

          elif high_count == 1 or medium_count >= 3:
              # Warning alert
              await self._send_alert(channel="slack", severity="warning")

          # Always log
          await self.audit_logger.log_event(
              event_type="anomaly_detected",
              anomalies=[a.dict() for a in anomalies]
          )
  ```

**Task 4.2: Gateway Integration** (2 days)
- **File:** `src/sark/api/routers/gateway.py` (UPDATE)
- **Implementation:**
  ```python
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

**Task 4.3: Baseline Management** (1 day)
- **File:** `src/sark/services/baseline_manager.py` (NEW)
- **Implementation:**
  - Background task to update baselines daily
  - API endpoint to manually rebuild baseline
  - Baseline versioning and rollback

**Task 4.4: Tests** (1 day)
- **File:** `tests/unit/security/test_anomaly_detector.py` (NEW)
- **Coverage:**
  - Baseline building logic
  - All anomaly types detected
  - Alert triggering
  - Auto-suspend functionality

### Deliverables

**Code:**
- ✅ `src/sark/security/behavioral_analyzer.py` (250 lines)
- ✅ `src/sark/security/anomaly_alerts.py` (150 lines)
- ✅ `src/sark/services/baseline_manager.py` (100 lines)
- ✅ `tests/unit/security/test_anomaly_detector.py` (300 lines)

**Documentation:**
- ✅ `docs/security/ANOMALY_DETECTION.md`

**Acceptance:**
- [ ] 80%+ detection rate on simulated attacks
- [ ] <10% false positive rate
- [ ] Baseline updates automatically
- [ ] Alerts delivered to configured channels

---

## Stream 3: Network-Level Controls (DEVOPS)

**Worker Assignment:** `DEVOPS` (Cursor or Continue.dev)
**Duration:** Week 5 (1 week)
**Branch:** `feat/network-controls`
**Dependencies:** None
**Estimated Effort:** 1 week, 1 worker

### Week 5: K8s Network Policies & Egress Filtering

**Task 5.1: Kubernetes Network Policies** (2 days)
- **Files:** `k8s/network-policies/*.yaml` (NEW)
- **Implementation:**
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
  ```

**Task 5.2: Egress Filtering (Calico)** (2 days)
- **File:** `k8s/network-policies/egress-allow-list.yaml` (NEW)
- **Implementation:**
  ```yaml
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

**Task 5.3: Cloud Firewall Rules** (1 day)
- **File:** `terraform/modules/network/firewall.tf` (NEW)
- **Implementation:**
  ```hcl
  # AWS Security Group example
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
      cidr_blocks = var.mcp_server_cidrs
    }
  }
  ```

**Task 5.4: Documentation** (1 day)
- **File:** `docs/deployment/NETWORK_SECURITY.md` (NEW)
- **Content:**
  - Network architecture diagram
  - Policy configuration guide
  - Troubleshooting egress issues

### Deliverables

**Code:**
- ✅ `k8s/network-policies/gateway-egress.yaml`
- ✅ `k8s/network-policies/egress-allow-list.yaml`
- ✅ `terraform/modules/network/firewall.tf`

**Documentation:**
- ✅ `docs/deployment/NETWORK_SECURITY.md`

**Acceptance:**
- [ ] Network policies applied in staging
- [ ] Egress filtering tested (blocked domains fail)
- [ ] Allowed domains still accessible
- [ ] Documentation verified

---

## Stream 4: Secret Scanning (SECURITY-3)

**Worker Assignment:** `SECURITY-3` (Aider recommended)
**Duration:** Week 6 (1 week)
**Branch:** `feat/secret-scanning`
**Dependencies:** None
**Estimated Effort:** 1 week, 1 worker

### Week 6: Secret Detection & Redaction

**Task 6.1: Secret Scanner** (3 days)
- **File:** `src/sark/security/secret_scanner.py` (NEW)
- **Implementation:**
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
                          matched_value=match[:10] + "..."
                      ))

          return findings
  ```

**Task 6.2: Redaction** (1 day)
- **File:** `src/sark/security/secret_scanner.py`
- **Implementation:**
  ```python
  def redact_secrets(self, data: dict, findings: list[SecretFinding]) -> dict:
      """Replace secrets with [REDACTED]"""
      redacted = copy.deepcopy(data)

      for finding in findings:
          keys = finding.location.split(".")
          current = redacted
          for key in keys[:-1]:
              current = current[key]

          current[keys[-1]] = "[REDACTED]"

      return redacted
  ```

**Task 6.3: Gateway Integration** (1 day)
- **File:** `src/sark/api/routers/gateway.py` (UPDATE)
- **Implementation:**
  ```python
  async def invoke_tool(...):
      result = await gateway_client.invoke_tool(...)

      # Secret scanning on response
      secret_findings = await secret_scanner.scan(result.data)
      if secret_findings:
          result.data = secret_scanner.redact_secrets(result.data, secret_findings)

          await alert_manager.send_alert(
              severity="warning",
              title="Secrets detected in tool response",
              details={"findings": secret_findings}
          )

      return result
  ```

**Task 6.4: Tests** (1 day)
- **File:** `tests/unit/security/test_secret_scanner.py` (NEW)

### Deliverables

**Code:**
- ✅ `src/sark/security/secret_scanner.py` (150 lines)
- ✅ `tests/unit/security/test_secret_scanner.py` (200 lines)

**Documentation:**
- ✅ `docs/security/SECRET_SCANNING.md`

**Acceptance:**
- [ ] All secret patterns detected
- [ ] Redaction working correctly
- [ ] Alerts sent on detection
- [ ] No performance impact (<1ms)

---

## Stream 5: MFA for Critical Actions (SECURITY-4)

**Worker Assignment:** `SECURITY-4` (Cursor recommended)
**Duration:** Week 7 (1 week)
**Branch:** `feat/mfa-critical-actions`
**Dependencies:** None
**Estimated Effort:** 1 week, 1 worker

### Week 7: MFA Challenge System

**Task 7.1: MFA Challenge** (3 days)
- **File:** `src/sark/security/mfa.py` (NEW)
- **Implementation:**
  ```python
  class MFAChallenge:
      async def require_mfa(self, user_id: str, action: str) -> bool:
          """Send MFA challenge and wait for approval"""
          challenge_code = self._generate_code()

          # Send via configured channel (SMS, TOTP, push)
          await self._send_challenge(user_id, challenge_code)

          # Wait for response (timeout: 60 seconds)
          response = await self._wait_for_response(user_id, timeout=60)

          if response == challenge_code:
              return True

          await self.audit_logger.log_event(
              event_type="mfa_failed",
              user_id=user_id,
              action=action
          )

          return False
  ```

**Task 7.2: Gateway Integration** (2 days)
- **File:** `src/sark/api/routers/gateway.py` (UPDATE)
- **Implementation:**
  ```python
  async def authorize_gateway_request(...):
      opa_result = await opa_client.evaluate(...)

      # NEW: MFA for critical resources
      if sensitivity == "critical" and config.mfa_enabled:
          mfa_passed = await mfa_challenge.require_mfa(user_id, tool_name)

          if not mfa_passed:
              return GatewayAuthorizationResponse(
                  allowed=False,
                  reason="MFA required for critical resource"
              )

      return GatewayAuthorizationResponse(...)
  ```

**Task 7.3: Tests** (1 day)
- **File:** `tests/unit/security/test_mfa.py` (NEW)

### Deliverables

**Code:**
- ✅ `src/sark/security/mfa.py` (200 lines)
- ✅ `tests/unit/security/test_mfa.py` (150 lines)

**Documentation:**
- ✅ `docs/security/MFA_SETUP.md`

**Acceptance:**
- [ ] TOTP working
- [ ] SMS working (with Twilio integration)
- [ ] Push notification working
- [ ] Timeout enforced (60s)

---

## Stream 6: Integration & Testing (QA)

**Worker Assignment:** `QA` (Aider recommended)
**Duration:** Week 8 (1 week)
**Branch:** `feat/v1.3.0-integration`
**Dependencies:** Streams 1-5 complete
**Estimated Effort:** 1 week, 1 worker

### Week 8: End-to-End Integration

**Task 8.1: Integration Tests** (3 days)
- **File:** `tests/integration/security/test_security_e2e.py` (NEW)
- **Scenarios:**
  1. Prompt injection blocked
  2. Anomaly triggers alert
  3. Network policy blocks unauthorized egress
  4. Secret detected and redacted
  5. MFA enforced for critical action
  6. All features working together

**Task 8.2: Performance Testing** (2 days)
- Verify no significant performance degradation
- Target: <10ms overhead for all security features combined

**Task 8.3: Documentation Update** (1 day)
- Update main README with v1.3.0 features
- Security documentation consolidated

### Deliverables

**Code:**
- ✅ `tests/integration/security/test_security_e2e.py` (400 lines)

**Documentation:**
- ✅ `docs/v1.3.0/RELEASE_NOTES.md`

**Acceptance:**
- [ ] All integration tests passing
- [ ] Performance targets met
- [ ] Documentation complete

---

## Release Checklist

### Code Complete
- [ ] All 6 streams merged to main
- [ ] No merge conflicts
- [ ] All tests passing (100%)
- [ ] Code coverage maintained (≥85%)

### Security Validation
- [ ] Prompt injection: 95%+ detection rate
- [ ] Anomaly detection: 80%+ detection rate
- [ ] Network policies tested in staging
- [ ] Secret scanning verified
- [ ] MFA working for all channels

### Documentation
- [ ] All feature docs complete
- [ ] Release notes published
- [ ] Security guide updated
- [ ] Deployment guide updated

### Performance
- [ ] <10ms total overhead from security features
- [ ] No throughput degradation
- [ ] Memory usage acceptable

**Release Date:** End of Week 8
**Version:** v1.3.0
**Next:** v1.4.0 (Rust optimization) or v2.0.0 (production after audit)

---

## Czarina Configuration

**`.czarina/config.json`:**
```json
{
  "project": "sark",
  "version": "1.3.0",
  "workers": {
    "security-1": {
      "branch": "feat/prompt-injection-detection",
      "agent": "aider",
      "budget": {"tokens": 3000000, "weeks": 2}
    },
    "security-2": {
      "branch": "feat/anomaly-detection",
      "agent": "aider",
      "budget": {"tokens": 3000000, "weeks": 2}
    },
    "devops": {
      "branch": "feat/network-controls",
      "agent": "cursor",
      "budget": {"tokens": 1500000, "weeks": 1}
    },
    "security-3": {
      "branch": "feat/secret-scanning",
      "agent": "aider",
      "budget": {"tokens": 1500000, "weeks": 1}
    },
    "security-4": {
      "branch": "feat/mfa-critical-actions",
      "agent": "cursor",
      "budget": {"tokens": 2000000, "weeks": 1}
    },
    "qa": {
      "branch": "feat/v1.3.0-integration",
      "agent": "aider",
      "budget": {"tokens": 2000000, "weeks": 1},
      "dependencies": ["security-1", "security-2", "devops", "security-3", "security-4"]
    }
  }
}
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Prompt Injection Detection Rate** | 95%+ | Test dataset |
| **Prompt Injection False Positives** | <5% | Production monitoring |
| **Anomaly Detection Rate** | 80%+ | Simulated attacks |
| **Anomaly False Positives** | <10% | Production monitoring |
| **Secret Exposure Prevented** | 100% | Test scenarios |
| **MFA Success Rate** | 95%+ | User authentication |
| **Performance Overhead** | <10ms | Load testing |
| **Test Coverage** | ≥85% | pytest-cov |

**Overall:** v1.3.0 delivers production-grade advanced security while maintaining performance.
