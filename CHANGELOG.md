# Changelog

All notable changes to SARK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased] - v1.2.0-dev

### In Progress
- Gateway HTTP transport implementation
- Gateway SSE transport implementation  
- Gateway stdio transport implementation
- Policy validation framework
- Fix 154 failing auth provider tests
- Achieve 85%+ code coverage

**Target Release:** 8 weeks from project start
**See:** `docs/v1.2.0/IMPLEMENTATION_PLAN.md`

---

## [1.1.0] - 2025-11-28

### Added
- Gateway infrastructure (models, tests, docs)
- Gateway authorization API endpoints
- Gateway client SDK (stubbed implementation)
- Complete test infrastructure
- Comprehensive documentation
- Production monitoring and observability
- Advanced OPA policies for Gateway/A2A authorization

### Known Issues
- Gateway client methods return stubbed responses
- No actual MCP server communication
- 154 auth provider tests failing (LDAP, SAML, OIDC)

**Note:** This release provides infrastructure foundation but requires v1.2.0 for functional Gateway.

---

## Version Numbering Change - 2025-12-09

**Major Change:** Adopted honest, incremental versioning strategy.

**New Plan:**
- v1.1.0 (Current): Gateway infrastructure merged but stubbed
- v1.2.0 (Next): Gateway working + policy validation + tests passing
- v1.3.0: Advanced security features
- v1.4.0: Rust optimization foundation
- v1.5.0: Rust detection algorithms
- v2.0.0: Production-ready (after external security audit)

**See:** `VERSION_RENUMBERING.md` for complete explanation.
