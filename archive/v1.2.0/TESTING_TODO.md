# Testing TODO - v1.2.0 Completion

**Date:** December 23, 2025
**Status:** Infrastructure Complete - Ready for Test Execution
**Environment Required:** Python 3.11+, Docker

---

## ⚠️ CRITICAL: Environment Requirements

**This environment (Windows, Python 3.10.11, no Docker) cannot run the tests.**
**Tests must be executed on a machine with:**

1. **Python 3.11 or higher** (currently 3.10.11)
2. **Docker Desktop** or Docker Engine (currently not available)

---

## 📋 Step-by-Step Test Execution Guide

### Phase 1: Environment Verification (5 minutes)

```bash
# 1. Check Python version
python --version
# Must be: Python 3.11.x or higher

# 2. Check Docker
docker --version
docker ps
# Docker must be running

# 3. Verify test infrastructure
./scripts/verify_test_infrastructure.sh
# Should show all green checkmarks

# If verification fails, install missing dependencies:
pip install -e ".[dev]"
pip install pytest-docker asyncpg redis psycopg2-binary
```

### Phase 2: Auth Provider Tests (30-60 minutes)

**Goal:** Fix 154 failing tests, achieve 85%+ coverage for LDAP, OIDC, SAML

```bash
# Run auth provider tests with coverage
./scripts/run_auth_tests.sh run coverage

# Or run individual providers:
./scripts/run_auth_tests.sh run ldap    # 65 tests
./scripts/run_auth_tests.sh run oidc    # 20+ tests
./scripts/run_auth_tests.sh run saml    # 25+ tests

# Check coverage report
open htmlcov/index.html  # View in browser
```

**Expected Issues:**
- Database schema not initialized → Use `initialized_db` fixture
- Service connection errors → Check Docker health with `./scripts/run_auth_tests.sh status`
- LDAP/OIDC/SAML fixture errors → Review `tests/README_AUTH_TESTS.md`

**Success Criteria:**
- [ ] LDAP coverage ≥ 85% (currently 32.02%)
- [ ] OIDC coverage ≥ 85% (currently 28.21%)
- [ ] SAML coverage ≥ 85% (currently 22.47%)
- [ ] 0 failing tests (currently 154 failures)

### Phase 3: Integration Tests (1-2 hours)

**Goal:** Increase pass rate from 27% to 90%+

```bash
# Run integration tests with coverage
./scripts/run_integration_tests.sh run coverage

# Or run by category:
./scripts/run_integration_tests.sh run api        # API tests
./scripts/run_integration_tests.sh run auth       # Auth tests
./scripts/run_integration_tests.sh run policy     # Policy tests
./scripts/run_integration_tests.sh run gateway    # Gateway tests

# Check results
cat coverage.xml  # Or view htmlcov/index.html
```

**Expected Issues:**
- Tests using mocks instead of Docker → Migrate using `docs/TEST_MIGRATION_GUIDE.md`
- Database table not found → Use `initialized_db` fixture instead of `postgres_connection`
- OPA policy not loaded → Load policies from `tests/fixtures/opa_policies/`
- Service connection refused → Check service logs: `./scripts/run_integration_tests.sh logs postgres`

**Migration Steps:**
1. Add `pytest_plugins = ["tests.fixtures.integration_docker"]` to test file
2. Replace mock fixtures with real Docker fixtures
3. Update test logic for real services (see TEST_MIGRATION_GUIDE.md)
4. Add `@pytest.mark.integration` marker
5. Test locally

**Success Criteria:**
- [ ] Pass rate ≥ 90% (currently 27% - 32/119 passing)
- [ ] All Docker services start reliably
- [ ] Tests complete in < 15 minutes

### Phase 4: OPA Integration Tests (15-30 minutes)

**Goal:** Verify all new OPA tests pass with real OPA Docker service

```bash
# Run OPA integration tests
pytest tests/integration/test_opa_docker_integration.py -v

# Run specific test categories
pytest tests/integration/test_opa_docker_integration.py -v -k "policy_upload"
pytest tests/integration/test_opa_docker_integration.py -v -k "performance"
pytest tests/integration/test_opa_docker_integration.py -v -k "gateway"

# Test with verbose output
pytest tests/integration/test_opa_docker_integration.py -v -s
```

**Expected Issues:**
- OPA service not ready → Wait 10-15 seconds after starting services
- Policy compilation errors → Check Rego syntax in `tests/fixtures/opa_policies/`
- Performance below target → Acceptable if > 100 req/s throughput

**Success Criteria:**
- [ ] All 19 test functions pass (40+ scenarios)
- [ ] Average policy evaluation < 10ms
- [ ] Throughput > 100 req/s
- [ ] Fail-closed behavior validated

### Phase 5: Full Test Suite (30-60 minutes)

```bash
# Run everything with coverage
pytest tests/ --cov=src --cov-report=term-missing --cov-report=html --cov-report=xml -v

# Or use test runners:
./scripts/run_auth_tests.sh run coverage
./scripts/run_integration_tests.sh run coverage
pytest tests/integration/test_opa_docker_integration.py -v --cov=src

# Generate combined coverage report
coverage combine
coverage html
coverage report
```

**Success Criteria:**
- [ ] Overall test pass rate > 85%
- [ ] Code coverage > 80%
- [ ] No critical failures
- [ ] CI/CD ready

---

## 🔧 Common Fixes

### Fix 1: Database Schema Not Initialized

**Symptom:** `relation "mcp_servers" does not exist`

**Fix:**
```python
# Change from:
async def test_something(postgres_connection):
    async with postgres_connection.acquire() as conn:
        await conn.execute("SELECT * FROM mcp_servers")  # Error!

# To:
async def test_something(initialized_db):
    async with initialized_db.acquire() as conn:
        await conn.execute("SELECT * FROM mcp_servers")  # Works!
```

### Fix 2: Test Using Mocks Instead of Docker

**Symptom:** Test passes but doesn't actually test integration

**Fix:**
```python
# Add to top of test file:
pytest_plugins = ["tests.fixtures.integration_docker"]

# Change from mock:
async def test_something(mock_db):
    mock_db.execute.return_value = MagicMock()

# To real Docker:
@pytest.mark.integration
@pytest.mark.asyncio
async def test_something(postgres_connection):
    async with postgres_connection.acquire() as conn:
        result = await conn.execute("...")
```

### Fix 3: OPA Service Not Ready

**Symptom:** `Connection refused to localhost:8181`

**Fix:**
```bash
# Wait for services to start
./scripts/run_integration_tests.sh start
sleep 15  # Give OPA time to fully start

# Check OPA health
curl http://localhost:8181/health

# Check OPA logs if issues
./scripts/run_integration_tests.sh logs opa
```

### Fix 4: Service Connection Timeout

**Symptom:** Tests hang or timeout waiting for services

**Fix:**
```bash
# Check Docker is running
docker ps

# Restart services
./scripts/run_integration_tests.sh stop
./scripts/run_integration_tests.sh start

# Check service health
./scripts/run_integration_tests.sh status
```

---

## 📊 Expected Test Results

### Baseline (Before Fixes)

| Category | Current | Target | Gap |
|----------|---------|--------|-----|
| **Auth Tests** |
| LDAP coverage | 32.02% | 85%+ | +53% |
| OIDC coverage | 28.21% | 85%+ | +57% |
| SAML coverage | 22.47% | 85%+ | +63% |
| Failing tests | 154 | 0 | -154 |
| **Integration Tests** |
| Pass rate | 27% (32/119) | 90%+ | +63% |
| **OPA Tests** |
| Pass rate | N/A (new) | 100% | New tests |

### Target (After Fixes)

```bash
# Auth Provider Tests
LDAP: ████████████████████████████ 85% coverage ✓
OIDC: ████████████████████████████ 85% coverage ✓
SAML: ████████████████████████████ 85% coverage ✓
Failures: 0/110 ✓

# Integration Tests
Pass rate: ██████████████████████████████████ 90% (108/120) ✓

# OPA Integration Tests
Pass rate: ████████████████████████████████████ 100% (19/19) ✓

# Overall
Total tests: 249
Passed: 227 (91%)
Failed: 22 (9%)
Coverage: 82%
```

---

## 📝 Debugging Commands

### Check Service Status

```bash
# All services
./scripts/run_integration_tests.sh status

# Individual service logs
./scripts/run_integration_tests.sh logs postgres
./scripts/run_integration_tests.sh logs redis
./scripts/run_integration_tests.sh logs opa
./scripts/run_integration_tests.sh logs timescaledb
```

### Interactive Debugging

```bash
# Open PostgreSQL shell
./scripts/run_integration_tests.sh shell postgres
# Inside: \dt (list tables), SELECT * FROM mcp_servers;

# Open Redis shell
./scripts/run_integration_tests.sh shell redis
# Inside: KEYS *, GET key_name

# Test OPA manually
curl -X POST http://localhost:8181/v1/data/sark/gateway \
  -d '{"input": {"action": "gateway:tool:invoke", "user": {"role": "admin"}}}'
```

### Run Single Test with Debug Output

```bash
# Run one test with full output
pytest tests/integration/test_api_integration.py::test_list_servers -v -s

# Run with debug logging
pytest tests/integration/test_api_integration.py -v --log-cli-level=DEBUG

# Run with pdb on failure
pytest tests/integration/test_api_integration.py -v --pdb
```

---

## 📚 Documentation Reference

| Document | Purpose | Location |
|----------|---------|----------|
| **Auth Testing** | Auth provider test guide | `tests/README_AUTH_TESTS.md` |
| **Integration Testing** | Integration test guide | `tests/README_INTEGRATION_TESTS.md` |
| **Migration Guide** | Mock → Docker migration | `docs/TEST_MIGRATION_GUIDE.md` |
| **OPA Policies** | OPA policy documentation | `tests/fixtures/opa_policies/README.md` |
| **Infrastructure Summary** | Complete overview | `TEST_INFRASTRUCTURE_COMPLETE_V1.2.0.md` |
| **Execution Status** | Environment requirements | `TEST_EXECUTION_STATUS.md` |
| **Quick Start** | Quick testing guide | `QUICK_START_TESTING.md` |
| **OPA Integration** | OPA testing complete | `OPA_INTEGRATION_COMPLETE.md` |

---

## 🎯 v1.2.0 Completion Checklist

### Infrastructure ✅ (Complete)
- [x] Auth provider Docker services (LDAP, OIDC, SAML)
- [x] Integration test Docker services (PostgreSQL, Redis, OPA, TimescaleDB, gRPC)
- [x] Test fixtures and helpers
- [x] Test runner scripts (bash + Windows batch)
- [x] OPA integration tests
- [x] OPA policy files (3 policies)
- [x] Comprehensive documentation (7 docs)

### Testing ⏳ (Pending - Requires Environment)
- [ ] Auth provider tests passing with 85%+ coverage
- [ ] Integration tests passing with 90%+ rate
- [ ] OPA integration tests passing (100%)
- [ ] Zero failing tests (from 154)

### Verification ⏳ (After Testing)
- [ ] CI/CD integration tests added to GitHub Actions
- [ ] Coverage reports generated
- [ ] Performance benchmarks validated
- [ ] Documentation reviewed and updated

### Release ⏳ (After Verification)
- [ ] All v1.2.0 goals achieved
- [ ] CHANGELOG updated
- [ ] Version bumped to 1.2.0
- [ ] Git tag created
- [ ] Release notes published

---

## 🚀 Quick Start Commands

**On a machine with Python 3.11+ and Docker:**

```bash
# 1. Clone and setup
git clone <repo-url>
cd sark

# 2. Verify environment
python --version  # Must be 3.11+
docker --version  # Must be available
./scripts/verify_test_infrastructure.sh

# 3. Install dependencies
pip install -e ".[dev]"
pip install pytest-docker asyncpg redis psycopg2-binary

# 4. Run all tests
./scripts/run_auth_tests.sh run coverage
./scripts/run_integration_tests.sh run coverage
pytest tests/integration/test_opa_docker_integration.py -v

# 5. Check results
open htmlcov/index.html  # Coverage report
cat pytest_report.txt    # Test results

# 6. Fix failures and iterate
# (Use migration guide and fix examples above)

# 7. Verify success
# - Auth coverage: 85%+ each provider ✓
# - Integration pass rate: 90%+ ✓
# - OPA tests: 100% passing ✓
# - Zero failures ✓

# 8. Celebrate! 🎉
```

---

## 💡 Tips for Success

1. **Start with verification script** - Catch environment issues early
2. **Run tests in categories** - Easier to debug specific areas
3. **Use test runners** - They handle Docker lifecycle automatically
4. **Check logs when stuck** - Services write helpful error messages
5. **Migrate tests incrementally** - Don't try to fix everything at once
6. **Follow migration guide** - It has patterns for all common scenarios
7. **Performance is OK if > targets** - Don't over-optimize
8. **Document fixes** - Help future developers
9. **Commit often** - Save progress as you fix tests
10. **Ask for help** - Review documentation or create issues

---

## 📞 Support

- **Documentation:** See files listed in "Documentation Reference" section
- **Issues:** Create GitHub issue with test output and environment details
- **Examples:** Check `tests/integration/test_docker_infrastructure_example.py`
- **Migration:** Follow `docs/TEST_MIGRATION_GUIDE.md` step-by-step

---

## ✨ Estimated Timeline

**With proper environment (Python 3.11+, Docker):**

- Environment verification: 5 minutes
- First test run: 15-30 minutes
- Fix auth provider tests: 1-2 hours
- Fix integration tests: 2-4 hours
- Fix OPA tests: 15-30 minutes
- Verification and cleanup: 30 minutes

**Total: 4-8 hours of focused work**

The infrastructure is ready. The tests are ready. Just need the environment! 🚀
