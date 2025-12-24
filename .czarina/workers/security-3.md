# Worker: SECURITY-3
## Secret Scanning

**Stream:** 4
**Duration:** Week 6 (1 week)
**Branch:** `feat/secret-scanning`
**Agent:** Aider (recommended)
**Dependencies:** None

---

## Mission

Detect and redact accidentally exposed secrets in tool responses to prevent credential leakage through MCP tool outputs.

## Goals

- Pattern-based detection for 10+ secret types
- Automatic redaction with [REDACTED] placeholder
- Alert on secret detection
- <1ms scanning overhead
- Zero secret exposure in responses

## Week 6: Implementation

### Tasks

1. **Secret Scanner** (3 days)
   - File: `src/sark/security/secret_scanner.py` (NEW)
   - Detect patterns:
     * OpenAI API keys (sk-...)
     * GitHub tokens (ghp_...)
     * AWS keys (AKIA...)
     * Private keys (-----BEGIN...)
     * JWT tokens
     * Database connection strings
     * Generic base64 secrets (high entropy + length)
   - Return `SecretFinding` list with locations

2. **Redaction** (1 day)
   - File: `src/sark/security/secret_scanner.py`
   - Replace detected secrets with [REDACTED]
   - Preserve data structure
   - Return redacted copy (don't mutate original)

3. **Gateway Integration** (1 day)
   - File: `src/sark/api/routers/gateway.py` (UPDATE)
   - Scan all tool responses before returning
   - Redact if secrets found
   - Send alert to security team
   - Feature flag: `SECRET_SCANNING_ENABLED`

4. **Tests** (1 day)
   - File: `tests/unit/security/test_secret_scanner.py` (NEW)
   - Test all secret patterns
   - Test redaction correctness
   - Test nested data structures
   - Test performance (<1ms)

## Deliverables

- ✅ `src/sark/security/secret_scanner.py` (~150 lines)
- ✅ `tests/unit/security/test_secret_scanner.py` (~200 lines)
- ✅ `docs/security/SECRET_SCANNING.md`

## Success Metrics

- [ ] All secret patterns detected
- [ ] Redaction preserves data structure
- [ ] Alerts sent on detection
- [ ] <1ms overhead (p95)
- [ ] Zero false negatives on test dataset

## References

- Implementation Plan: `docs/v1.3.0/IMPLEMENTATION_PLAN.md` (Stream 4)
- TruffleHog patterns: https://github.com/trufflesecurity/truffleHog
