# Worker: SECURITY-4
## MFA for Critical Actions

**Stream:** 5
**Duration:** Week 7 (1 week)
**Branch:** `feat/mfa-critical-actions`
**Agent:** Cursor (recommended)
**Dependencies:** Twilio account (SMS), push notification service

---

## Mission

Implement multi-factor authentication for access to critical/high-sensitivity resources, requiring real-time approval before tool execution.

## Goals

- TOTP (Time-based One-Time Password) support
- SMS challenge via Twilio
- Push notification support
- 60-second timeout for challenges
- MFA required for sensitivity=critical resources
- 95%+ success rate

## Week 7: Implementation

### Tasks

1. **MFA Challenge System** (3 days)
   - File: `src/sark/security/mfa.py` (NEW)
   - Three challenge methods:
     * TOTP: Generate and verify 6-digit codes
     * SMS: Send via Twilio, verify response
     * Push: Send notification, wait for approval
   - Challenge timeout: 60 seconds
   - Store pending challenges in Redis
   - Audit all MFA events

2. **Gateway Integration** (2 days)
   - File: `src/sark/api/routers/gateway.py` (UPDATE)
   - Trigger MFA for sensitivity=critical resources
   - Send challenge, wait for response
   - Block request if MFA fails
   - Timeout returns 403
   - Feature flag: `MFA_ENABLED`

3. **Tests** (1 day)
   - File: `tests/unit/security/test_mfa.py` (NEW)
   - Test all three challenge methods
   - Test timeout enforcement
   - Test failure handling
   - Test audit logging

4. **API Endpoints** (1 day)
   - POST /api/v1/security/mfa/enroll - User enrollment
   - POST /api/v1/security/mfa/verify - Verify challenge
   - GET /api/v1/security/mfa/status - User MFA status

## Deliverables

- ✅ `src/sark/security/mfa.py` (~200 lines)
- ✅ `tests/unit/security/test_mfa.py` (~150 lines)
- ✅ `docs/security/MFA_SETUP.md`
- ✅ Update `config.example.yaml` with MFA settings

## Success Metrics

- [ ] TOTP working (test with Google Authenticator)
- [ ] SMS working (test with Twilio sandbox)
- [ ] Push notification working
- [ ] 60s timeout enforced
- [ ] All MFA events audited
- [ ] 95%+ success rate in testing

## Configuration

Required environment variables:
```yaml
MFA_ENABLED: true
MFA_METHODS: ["totp", "sms", "push"]
MFA_TIMEOUT_SECONDS: 60
TWILIO_ACCOUNT_SID: "..."
TWILIO_AUTH_TOKEN: "..."
TWILIO_FROM_NUMBER: "+1..."
```

## References

- Implementation Plan: `docs/v1.3.0/IMPLEMENTATION_PLAN.md` (Stream 5)
- PyOTP: https://github.com/pyauth/pyotp
- Twilio Docs: https://www.twilio.com/docs/sms
