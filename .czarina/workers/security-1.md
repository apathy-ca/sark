# Worker: SECURITY-1
## Prompt Injection Detection

**Stream:** 1
**Duration:** Weeks 1-2 (2 weeks)
**Branch:** `feat/prompt-injection-detection`
**Agent:** Aider (recommended)
**Dependencies:** None

---

## Mission

Implement a comprehensive prompt injection detection system to identify and block malicious attempts to manipulate AI tool parameters through injection attacks.

## Goals

- Pattern-based detection for 20+ known injection techniques
- Entropy analysis for encoded/obfuscated payloads
- Risk scoring system (0-100)
- Configurable response (block/alert/log)
- <10ms detection latency
- 95%+ true positive rate, <5% false positive rate

## Week 1: Detection Engine

### Task 1.1: Pattern-Based Detector (2 days)

**File:** `src/sark/security/injection_detector.py` (NEW)

**Requirements:**
1. Create `PromptInjectionDetector` class
2. Implement 20+ regex patterns for common injections:
   - Instruction overrides ("ignore previous instructions")
   - Role manipulation ("you are now a...")
   - Data exfiltration ("send to https://...")
   - System prompts ("<system>")
   - Encoded payloads (base64, eval, exec)
3. Pattern matching across all parameter values (flatten nested dicts)
4. Return `InjectionDetectionResult` with findings list

**Acceptance Criteria:**
- [ ] All 20+ patterns implemented
- [ ] Handles nested dictionary parameters
- [ ] Case-insensitive matching
- [ ] Returns severity levels (high/medium/low)

### Task 1.2: Entropy Analysis (2 days)

**File:** `src/sark/security/injection_detector.py`

**Requirements:**
1. Implement Shannon entropy calculation
2. Flag high-entropy strings (>4.5) as potential encoded payloads
3. Minimum length threshold (50 chars) to avoid false positives
4. Add entropy findings to detection results

**Acceptance Criteria:**
- [ ] Entropy calculation accurate
- [ ] Detects base64-encoded payloads
- [ ] Threshold configurable
- [ ] Low false positive rate on normal text

### Task 1.3: Risk Scoring (1 day)

**File:** `src/sark/security/injection_detector.py`

**Requirements:**
1. Calculate risk score 0-100 based on findings
2. Weight by severity: high=30, medium=15, low=5
3. Cap at 100 maximum
4. Include score in detection result

**Acceptance Criteria:**
- [ ] Risk score calculated correctly
- [ ] Multiple findings accumulate score
- [ ] Score capped at 100

## Week 2: Integration & Response

### Task 2.1: Response Handler (2 days)

**File:** `src/sark/security/injection_response.py` (NEW)

**Requirements:**
1. Create `InjectionResponseHandler` class
2. Load policy from OPA (injection policy)
3. Implement three response actions:
   - **Block:** Risk >= block_threshold (default: 70)
   - **Alert:** Risk >= alert_threshold (default: 40)
   - **Log:** All detections logged to audit
4. Integrate with audit logging and alert manager

**Acceptance Criteria:**
- [ ] Policy-driven response
- [ ] All actions audit-logged
- [ ] Alerts sent to configured channels
- [ ] Configurable thresholds

### Task 2.2: Gateway Integration (2 days)

**File:** `src/sark/api/routers/gateway.py` (UPDATE)

**Requirements:**
1. Add injection detection to `authorize_gateway_request()`
2. Run detection AFTER OPA but BEFORE tool execution
3. Block request if response action is "block"
4. Include detection details in authorization response
5. Maintain backward compatibility (feature flag: `INJECTION_DETECTION_ENABLED`)

**Acceptance Criteria:**
- [ ] Detection runs on every gateway request
- [ ] Blocked requests return 403 with reason
- [ ] Non-blocking requests proceed normally
- [ ] Feature flag works

### Task 2.3: Pattern Database (1 day)

**File:** `config/injection_patterns.yaml` (NEW)

**Requirements:**
1. Externalize patterns to YAML config
2. Allow runtime pattern updates (reload endpoint)
3. Include metadata: name, severity, action
4. Load patterns on startup

**Acceptance Criteria:**
- [ ] YAML format validated
- [ ] Patterns loaded from config
- [ ] Runtime reload works
- [ ] Invalid patterns logged/skipped

### Task 2.4: Tests (1 day)

**File:** `tests/unit/security/test_injection_detector.py` (NEW)

**Requirements:**
1. Test all 20+ patterns individually
2. Test entropy calculation edge cases
3. Test risk scoring logic
4. Test response handling (block/alert/log)
5. Test false positive scenarios
6. Test gateway integration

**Coverage Target:** 95%+

**Acceptance Criteria:**
- [ ] All patterns tested
- [ ] Edge cases covered
- [ ] Integration tests passing
- [ ] Performance: <10ms per detection

## Deliverables

### Code Files
- ✅ `src/sark/security/injection_detector.py` (~200 lines)
- ✅ `src/sark/security/injection_response.py` (~150 lines)
- ✅ `config/injection_patterns.yaml`
- ✅ `tests/unit/security/test_injection_detector.py` (~300 lines)

### Documentation
- ✅ `docs/security/INJECTION_DETECTION.md` - User guide
- ✅ Update `README.md` with v1.3.0 security features
- ✅ API documentation for detection endpoints

### Success Metrics
- [ ] 95%+ true positive rate on test dataset
- [ ] <5% false positive rate
- [ ] <10ms detection latency (p95)
- [ ] All tests passing
- [ ] Code coverage ≥95%

## Implementation Notes

1. **Pattern Sources:**
   - OWASP LLM Top 10 (Prompt Injection)
   - Simon Willison's prompt injection research
   - Real-world attack examples

2. **Performance:**
   - Use compiled regex patterns (cache)
   - Short-circuit on first high-severity finding
   - Async processing for non-blocking

3. **Testing:**
   - Include adversarial test cases
   - Test with legitimate complex prompts (avoid false positives)
   - Load testing for performance validation

## References

- Implementation Plan: `docs/v1.3.0/IMPLEMENTATION_PLAN.md` (Stream 1)
- OWASP LLM01: https://owasp.org/www-project-top-10-for-large-language-model-applications/
- Simon Willison's research: https://simonwillison.net/tags/promptinjection/

---

**Ready to start? Review this document and begin with Task 1.1!**
