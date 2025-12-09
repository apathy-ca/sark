# Sark Enhancement Quick Reference

**Status:** 🚧 Production Readiness Roadmap
**Goal:** Address Lethal Trifecta vulnerabilities and achieve production-ready status
**Timeline:** 8-12 weeks
**Target Release:** v2.1.0

---

## 📊 Current State vs. Target

| Aspect | Current | Target | Priority |
|--------|---------|--------|----------|
| **Gateway Client** | Stubbed | Fully functional (HTTP/SSE/stdio) | P1 |
| **Test Coverage** | 64%, 154 failing | 85%+, 0 failing | P1 |
| **Prompt Injection Detection** | None | Real-time detection | P2 |
| **Policy Validation** | None | Syntax + safety checks | P1 |
| **Anomaly Detection** | None | Behavioral analysis | P2 |
| **Security Audit** | None | External pen test passed | P1 |
| **Network Controls** | App-layer only | Defense-in-depth | P2 |
| **Overall Security Score** | 6.7/10 | 8.5/10 | - |

---

## 🎯 Critical Path (Must Complete)

```
Week 1-4: Gateway Client → Week 5-6: Fix Tests → Week 7: Security Audit → Week 8-9: Remediation → Week 10-11: Production Deploy
```

**Blockers:**
- ❌ Cannot deploy without Gateway implementation
- ❌ Cannot pass audit with failing tests
- ❌ Cannot go live without external security validation

---

## 📁 Key Documents

| Document | Purpose | Audience |
|----------|---------|----------|
| **[LETHAL_TRIFECTA_ANALYSIS.md](LETHAL_TRIFECTA_ANALYSIS.md)** | Security analysis based on Simon Willison's framework | Security team, leadership |
| **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)** | Comprehensive 12-week roadmap | All teams |
| **[docs/implementation/PRIORITY_1_TASKS.md](docs/implementation/PRIORITY_1_TASKS.md)** | Detailed P1 tasks with code templates | Developers |

---

## 🚀 Quick Start for Developers

### 1. Gateway Client Implementation (Weeks 1-4)

**File:** `src/sark/services/gateway/client.py`

**What to do:**
1. Replace stubbed methods with HTTP client (httpx)
2. Add SSE streaming support
3. Add stdio subprocess support
4. Write integration tests

**Code template:** See `docs/implementation/PRIORITY_1_TASKS.md`

**Dependencies:**
```bash
pip install httpx tenacity circuitbreaker httpx-sse
```

**Acceptance criteria:**
- ✅ All 3 transports working
- ✅ 50+ integration tests passing
- ✅ <100ms p95 latency

---

### 2. Fix Failing Tests (Weeks 5-6)

**Files:** `tests/test_auth_providers.py`

**Issues:**
- LDAP: Mock server not starting → use pytest-docker
- SAML: XML signature invalid → fix certificate format
- OIDC: Timing issue → use freezegun

**What to do:**
1. Fix LDAP tests with real container
2. Fix SAML certificate in fixtures
3. Mock time in OIDC tests
4. Add missing coverage

**Acceptance criteria:**
- ✅ 100% test pass rate
- ✅ 85%+ code coverage

---

### 3. Policy Validation (Week 7)

**File:** `src/sark/policy_validator.py` (new)

**What to do:**
1. Create validator that checks OPA policies before loading
2. Add syntax validation (OPA CLI)
3. Add safety checks (forbidden patterns)
4. Add policy test framework (YAML)

**Acceptance criteria:**
- ✅ All policies validated on load
- ✅ Cannot load invalid/unsafe policies
- ✅ Policy test suite exists

---

## 🔒 Security Priorities

### Priority 1: Critical (Weeks 1-4)

1. **Complete Gateway** - Eliminate SSRF, injection at tool layer
2. **Fix Tests** - Ensure auth mechanisms working correctly
3. **Policy Validation** - Prevent malicious policies
4. **Security Audit** - External validation

### Priority 2: High (Weeks 5-8)

1. **Prompt Injection Detection** - Block injection attempts
2. **Anomaly Detection** - Detect unusual access patterns
3. **Network Controls** - Defense-in-depth

### Priority 3-4: Nice-to-Have (Weeks 9-12)

- Secret scanning
- MFA for critical actions
- Cost attribution
- Federation improvements

---

## 📈 Success Metrics

### Functional

- ✅ Gateway: 100% features implemented
- ✅ Tests: 85%+ coverage, 0 failing
- ✅ Injection detection: 95%+ accuracy

### Performance

- ✅ API latency: p95 < 100ms
- ✅ Throughput: 850+ req/s
- ✅ Overhead: <10ms for injection detection

### Security

- ✅ External audit: 0 critical/high findings
- ✅ Injection detection: 0 bypasses in testing
- ✅ Anomaly detection: 95%+ alert accuracy

---

## 🏗️ Architecture Changes

### Before (Current)

```
AI Agent → SARK API → [STUBBED] → MCP Server
                ↓
            OPA (policy)
            Audit Log
```

**Problem:** Gateway client stubbed, can't actually invoke tools

---

### After (Target)

```
AI Agent → SARK API → Gateway Client → MCP Server (HTTP/SSE/stdio)
                ↓                ↓
            OPA Policy      Injection Detection
            Audit Log       Anomaly Detection
                ↓
         SIEM (Splunk/Datadog)
```

**Benefits:**
- ✅ End-to-end tool invocation
- ✅ Multi-transport support
- ✅ Real-time threat detection
- ✅ Complete audit trail

---

## 🎓 Training Resources

### Understanding the Lethal Trifecta

**What is it?**
AI agents become vulnerable when they combine:
1. Access to private data
2. Exposure to untrusted content (prompt injection)
3. External communication (exfiltration)

**How Sark mitigates:**
- **Private data:** Sensitivity filtering, role-based access
- **Untrusted content:** Input validation, injection detection
- **External comms:** Trust levels, rate limiting, network policies

**Learn more:** `LETHAL_TRIFECTA_ANALYSIS.md`

### MCP Protocol Basics

**What is MCP?**
Model Context Protocol - standard for AI tools to access resources

**Transports:**
- **HTTP:** RESTful API (cloud deployments)
- **SSE:** Server-Sent Events (streaming)
- **stdio:** Standard input/output (local processes)

**Sark's role:** Governance layer between AI and MCP servers

---

## 🐛 Troubleshooting

### Gateway client returns empty list

**Cause:** Stubbed implementation
**Fix:** Complete Task 1.1 (Gateway Client)
**Workaround:** None - core feature not implemented

### Tests failing (LDAP/SAML/OIDC)

**Cause:** Mock servers not starting, timing issues
**Fix:** See Task 1.2 in `PRIORITY_1_TASKS.md`
**Workaround:** Skip auth provider tests temporarily

### Policy not loading

**Cause:** Syntax error or safety check failed
**Fix:** Validate policy with `opa check` command
**Workaround:** Temporarily disable validation (not recommended)

---

## 📞 Getting Help

### Questions?

- **Architecture:** See `docs/ARCHITECTURE.md`
- **Security:** See `LETHAL_TRIFECTA_ANALYSIS.md`
- **Implementation:** See `docs/implementation/PRIORITY_1_TASKS.md`
- **Testing:** See `tests/README.md` (if exists)

### Need Review?

- **Code review:** Create PR, tag `@security-team`
- **Policy review:** Tag `@policy-team`
- **Architecture review:** Tag `@arch-team`

---

## 📅 Timeline at a Glance

| Week | Focus | Deliverable | Owner |
|------|-------|-------------|-------|
| 1-2 | Gateway HTTP/SSE | HTTP client working | Backend Eng |
| 3 | Gateway stdio | stdio client working | Backend Eng |
| 4 | Gateway tests | 50+ tests passing | Backend Eng |
| 5 | Injection detection | Pattern-based detector | Security Eng |
| 6 | Injection integration | Block/alert/log actions | Security Eng |
| 7 | Fix failing tests | 100% pass rate | QA Eng |
| 7-8 | Security audit | External pen test | Security Vendor |
| 9 | Anomaly detection | Behavioral baseline | Backend Eng |
| 10 | Network policies | K8s NetworkPolicies | DevOps Eng |
| 11 | Staging deploy | Canary rollout | DevOps Eng |
| 12 | Production deploy | v2.1.0 release | All teams |

---

## ✅ Definition of Done

### For Each Task

- [ ] Code complete and reviewed
- [ ] Tests written and passing
- [ ] Documentation updated
- [ ] Security review passed
- [ ] Performance benchmarks met

### For Production Release

- [ ] All P1 tasks complete
- [ ] Security audit passed (0 critical/high)
- [ ] 85%+ test coverage
- [ ] Performance targets met (<100ms p95)
- [ ] Documentation complete
- [ ] Runbook updated
- [ ] Monitoring configured
- [ ] Rollback plan tested

---

## 🔄 Weekly Checkin

**Every Friday:**
1. Review progress vs. plan
2. Identify blockers
3. Adjust timeline if needed
4. Update stakeholders

**Metrics to track:**
- Tasks completed vs. planned
- Test coverage trend
- Security findings (if audit started)
- Performance benchmarks

---

**Last Updated:** December 8, 2025
**Next Review:** December 15, 2025
**Version:** 1.0
