# QA Engineer - Test Fixes & Coverage

## Role
Fix all failing auth provider tests, add missing unit tests, create E2E scenario tests, and achieve 85%+ code coverage.

## Version Assignments
- v1.2.0-qa

## Responsibilities

### v1.2.0-qa (Test Fixes & Coverage - 450K tokens)
- Fix 154 failing auth provider tests (LDAP: 52, SAML: 48, OIDC: 54)
- Set up Docker-based LDAP test infrastructure with pytest-docker
- Fix SAML XML signature validation and certificate fixtures
- Fix OIDC timing issues with freezegun
- Add 50+ missing unit tests for gateway authorization, parameter filtering, caching, rate limiting
- Create 20+ E2E scenario tests for sensitive data access, multi-layer authorization, audit logging, performance
- Achieve 85%+ code coverage
- Write comprehensive test documentation

## Files
- `tests/test_auth_providers.py` (UPDATE - fix 154 tests)
- `tests/unit/test_*.py` (UPDATE/NEW - 50+ new tests)
- `tests/e2e/test_scenarios.py` (NEW - 400+ lines)
- `tests/fixtures/ldap_docker.py` (NEW - 100+ lines)
- `tests/README.md` (UPDATE)
- `docs/testing/E2E_SCENARIOS.md` (NEW)

## Tech Stack
- Python 3.11+
- pytest + pytest-asyncio + pytest-cov
- pytest-docker (LDAP container)
- freezegun (time mocking)
- Docker (osixia/openldap:1.5.0)
- LDAP3, python3-saml, authlib

## Token Budget
Total: 450K tokens
- v1.2.0-qa: 450K tokens

## Git Workflow
Branches by version:
- v1.2.0-qa: fix/auth-tests-and-coverage

When complete:
1. Commit changes with descriptive messages
2. Push to branch fix/auth-tests-and-coverage
3. Create PR to main
4. Update token metrics in status

## Pattern Library
Review before starting:
- czarina-core/patterns/ERROR_RECOVERY_PATTERNS.md
- czarina-core/patterns/CZARINA_PATTERNS.md

## Version Completion Criteria

### v1.2.0-qa Complete When:
- [ ] All 52 LDAP tests passing with Docker-based infrastructure
- [ ] All 48 SAML tests passing with fixed certificates and assertions
- [ ] All 54 OIDC tests passing with freezegun time mocking
- [ ] 50+ new unit tests added for gateway, caching, rate limiting
- [ ] 20+ E2E scenario tests created covering:
  - Sensitive data access workflows
  - Multi-layer authorization
  - Audit log verification
  - Performance under load (100 concurrent requests)
- [ ] 100% test pass rate in CI/CD
- [ ] 85%+ code coverage achieved
- [ ] Docker cleanup working properly
- [ ] No timing race conditions in tests
- [ ] tests/README.md updated with setup instructions
- [ ] E2E_SCENARIOS.md complete with scenario documentation
- [ ] Token budget: ≤ 495K tokens (110% of projected)