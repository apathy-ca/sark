# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Nothing yet

## [1.7.0] - 2026-02-02

### Added

**Home Deployment Profile (YORI Integration)**

A lightweight deployment profile targeting home networks and low-resource environments:

- **Foundation Configuration**
  - `HomeDeploymentConfig` dataclass for 512MB RAM, single-core systems
  - Docker Compose configuration (`docker-compose.home.yml`)
  - Makefile targets: `home-up`, `home-down`, `home-logs`
  - Environment template (`.env.home.example`)
  - Comprehensive [Home Deployment Guide](docs/deployment/HOME_DEPLOYMENT.md)

- **Rego Policy Templates for Home Governance**
  - Bedtime policies for time-based LLM access control
  - Cost limit policies for budget management
  - Parental control policies with content filtering
  - Privacy protection policies for PII detection
  - Allowlist/blocklist management
  - Common helpers for policy development
  - [Policy Cookbook](docs/policies/POLICY_COOKBOOK.md) with examples

- **Python Governance Modules**
  - Allowlist management (`src/sark/services/governance/allowlist.py`)
  - Time-based rules (`src/sark/services/governance/time_rules.py`)
  - Emergency override system (`src/sark/services/governance/emergency.py`)
  - Consent tracking (`src/sark/services/governance/consent.py`)
  - Policy enforcement framework (`src/sark/services/governance/enforcement.py`)
  - Override authorization (`src/sark/services/governance/override.py`)
  - REST API endpoints (`src/sark/api/governance/router.py`)
  - [Governance Guide](docs/governance/HOME_GOVERNANCE.md)

- **Analytics and Monitoring**
  - Token usage tracking (`src/sark/services/analytics/token_tracker.py`)
  - Cost calculation service (`src/sark/services/analytics/cost_calculator.py`)
  - Trend analysis (`src/sark/services/analytics/trend_analyzer.py`)
  - Usage reporting with CSV/JSON export (`src/sark/services/analytics/usage_reporter.py`)
  - REST API endpoints (`src/sark/api/analytics/router.py`)
  - [Analytics Guide](docs/analytics/HOME_ANALYTICS.md)

- **OPNsense Plugin**
  - Web UI dashboard with usage statistics
  - Service management (start/stop/restart)
  - Policy configuration interface
  - Log viewer with filtering
  - FreeBSD rc.d service script
  - MVC architecture following OPNsense patterns
  - [Plugin Development Guide](docs/opnsense/PLUGIN_DEVELOPMENT.md)

- **Comprehensive Test Suite**
  - Unit tests for governance modules
  - Unit tests for analytics services
  - OPA policy tests with full coverage
  - Integration tests for home deployment
  - Test fixtures for home configuration

### Changed
- Configuration system extended to support deployment profiles
- OPA policies reorganized with `home/` subdirectory
- Updated pyproject.toml version to 1.7.0

### Technical Notes
- Targets 512MB RAM, single-core systems
- Uses SQLite instead of PostgreSQL for home deployment
- Embedded OPA evaluation instead of external server
- All data stays on-premise (privacy-first design)
- Progressive control: observe → advisory → enforce modes

### Documentation
- Added `docs/deployment/HOME_DEPLOYMENT.md`
- Added `docs/policies/HOME_POLICIES.md`
- Added `docs/policies/POLICY_COOKBOOK.md`
- Added `docs/governance/HOME_GOVERNANCE.md`
- Added `docs/analytics/HOME_ANALYTICS.md`
- Added `docs/opnsense/PLUGIN_DEVELOPMENT.md`

## [1.6.0] - 2026-01-18

### Security

**Vulnerability Remediation (96% fix rate - 24/25 CVEs)**:
- aiohttp 3.13.2 → 3.13.3 (7 CVEs: CVE-2025-69223 through CVE-2025-69230)
- urllib3 1.26.20 → 2.6.3 (4 CVEs: CVE-2025-50181, CVE-2025-66418, CVE-2025-66471, CVE-2026-21441)
- authlib 1.3.2 → 1.6.6 (CVE-2025-68158)
- werkzeug 3.1.3 → 3.1.5 (CVE-2026-21860)
- filelock 3.16.1 → 3.17.0 (CVE-2025-65114)
- virtualenv 20.28.0 → 20.29.1 (CVE-2025-65111)
- bokeh 3.6.2 → 3.7.0 (CVE-2025-65108)
- fonttools 4.55.3 → 4.55.5 (CVE-2026-22220)
- pyasn1 0.6.1 → 0.6.2 (CVE-2026-23490)
- pynacl 1.6.0 → 1.6.2 (CVE-2025-69277)
- azure-core 1.32.0 → 1.38.0 (CVE-2026-21226)
- kubernetes 34.1.0 → 35.0.0 (for urllib3 2.x compatibility)

**Eliminated ecdsa dependency**:
- Migrated from python-jose to PyJWT[crypto]
- Eliminated CVE-2024-23342 (Minerva timing attack in ecdsa)
- Updated 9 files with new JWT library
- Changed exception handling: JWTError → jwt.InvalidTokenError

**Remaining**:
- nbconvert 7.16.4 (CVE-2025-22250) - Windows-only, dev dependency, awaiting upstream fix

### Fixed

**Test Infrastructure (39 tests fixed)**:
- Export router: 17/17 passing (100%)
  - Fixed SessionMiddleware dependency error
  - Corrected route path from empty string to "/"
  - Created async database mocking helper functions
  - Converted from @patch decorators to dependency_overrides pattern
- Tools router: 22/22 passing (100%)
  - Fixed keyword detection regex to handle snake_case identifiers
  - Fixed FastAPI route ordering (static paths before parameterized)
  - Applied dependency_overrides pattern to all tests
  - Created 3 helper functions for database mocking

**Keyword Detection Bug**:
- Changed regex from `\b{keyword}\b` to `(?:^|[^a-z]){keyword}(?:$|[^a-z])`
- Now correctly matches keywords in snake_case identifiers
- Handles both "credit_card" and "credit card" formats

**FastAPI Route Ordering**:
- Moved `/statistics/sensitivity` before `/{tool_id}/sensitivity`
- Added documentation comment about route ordering requirement
- Prevents FastAPI from matching static path as UUID parameter

### Documentation

**Added**:
- docs/v1.6.0/RELEASE_NOTES.md - Comprehensive release documentation
- docs/v1.6.0/SECURITY_AUDIT.md - Complete vulnerability audit
- docs/v1.6.0/TEST_FIXES.md - Test infrastructure improvements

**Updated**:
- README.md - v1.6.0 as current release
- ROADMAP.md - Added v1.6.0 completion
- CHANGELOG.md - This file

## [1.5.0] - 2026-01-17

### Added

**Gateway Transport Implementations**:
- HTTP transport with full request/response support
- SSE (Server-Sent Events) transport for streaming
- stdio transport for local MCP servers
- Transport auto-detection and fallback

**Frontend Authentication UI**:
- Login page with session management
- MFA setup and verification flows
- API key management interface
- User profile and settings

**E2E Integration Tests**:
- Complete user authentication flow tests
- MCP server registration and discovery tests
- Policy evaluation integration tests
- Frontend-backend integration tests

**Performance Benchmark Infrastructure**:
- Locust load testing setup
- pytest-benchmark for micro-benchmarks
- Automated performance regression detection
- Grafana dashboards for metrics visualization

### Fixed

**Security**:
- LDAP injection vulnerability in authentication
- CSRF token validation in API endpoints
- Credential exposure in logs and responses
- Session fixation attacks

## [1.4.0] - 2026-02-28

### Added

**Rust OPA Engine**:
- Embedded Rust OPA policy evaluation using Regorus library
- PyO3 bindings for seamless Python integration
- Compiled policy caching for improved performance
- Automatic fallback to HTTP OPA on errors
- Feature flag system for gradual rollout
- 4-10x faster policy evaluation (<5ms p95, down from 42ms)
- Zero HTTP overhead with in-process evaluation

**Rust In-Memory Cache**:
- High-performance in-memory cache using DashMap
- LRU (Least Recently Used) + TTL eviction strategy
- Thread-safe lock-free concurrent access
- Background cleanup task for expired entries
- 10-50x faster than Redis (<0.5ms p95, down from 3.8ms)
- Configurable max size and TTL

**Feature Flag System**:
- Percentage-based rollout (0% → 5% → 25% → 50% → 100%)
- Stable hash-based user assignment
- Instant rollback capability (<1s to shift all traffic)
- Admin API for runtime rollout control
- Cross-instance state storage in Redis
- Prometheus metrics for implementation tracking

**A/B Testing Framework**:
- Dual-path execution (Rust vs Python/Redis)
- Metrics collection by implementation
- Performance comparison dashboards
- Error rate tracking and alerting
- Automatic fallback on Rust errors

**Build System**:
- Maturin integration for Rust extension building
- Cargo workspace for multi-crate management
- Pre-built wheels for Linux, macOS, Windows
- CI/CD pipeline for cross-platform builds
- Clippy linting and formatting in CI

**Documentation**:
- Migration guide (v1.3.0 → v1.4.0)
- Release notes with performance benchmarks
- Architecture documentation for Rust integration
- Developer guide for building and contributing
- Performance testing and profiling guides

### Performance

**Overall Improvements**:
- Total request latency: 42ms p95 (down from 98ms) - **2.3x faster**
- Throughput: 2,100 req/s (up from 850 req/s) - **2.47x higher**
- CPU usage: 15% reduction
- Memory usage: +8% (acceptable overhead)

**OPA Evaluation**:
- p95 latency: 4.3ms (down from 42ms) - **9.8x faster**
- p50 latency: 2.1ms (down from 28ms) - **13.3x faster**
- Simple policies (<100 lines): 15-20x faster
- Complex policies (>500 lines): 4-6x faster

**Cache Operations**:
- Get p95 latency: 0.24ms (down from 3.8ms) - **15.8x faster**
- Set p95 latency: 0.28ms (down from 4.2ms) - **15.0x faster**
- Throughput: 5M get ops/sec, 3M set ops/sec

### Changed
- OPA client now supports both Rust and HTTP implementations
- Cache client supports both Rust and Redis backends
- Default to Rust implementation when available
- Automatic Python fallback if Rust unavailable

### Infrastructure
- Rust workspace at `rust/` with `sark-opa` and `sark-cache` crates
- PyO3 0.20+ for Python-Rust bindings
- Regorus 0.1+ for OPA policy evaluation
- DashMap 5.5+ for concurrent HashMap
- Maturin 1.0+ for building Python extensions

### Compatibility
- **100% backwards compatible** with v1.3.0
- Zero breaking changes to APIs or configuration
- All existing OPA policies work without modification
- Python fallback ensures compatibility if Rust unavailable
- Gradual rollout allows safe deployment

### Security
- Rust memory safety eliminates entire classes of vulnerabilities
- Embedded OPA reduces attack surface (no external HTTP dependency)
- Cargo audit for Rust dependency security scanning
- Zero critical vulnerabilities in Rust dependencies
- Feature flags enable quick rollback if issues detected

### Testing
- Comprehensive Rust unit tests (cargo test)
- Python integration tests for Rust components
- Performance benchmarks comparing Rust vs Python
- Memory leak detection (valgrind, miri)
- Load testing at 2,000+ req/s

## [1.3.0] - TBD

### Added

**Prompt Injection Detection (Stream 1)**:
- Pattern-based injection detector with 20+ attack patterns
- Shannon entropy analysis for encoded payload detection
- Risk scoring system (0-100 scale) with configurable thresholds
- Injection response handler with block/alert/log actions
- Configurable patterns via `config/injection_patterns.yaml`
- < 3ms detection latency (p95)
- 95%+ true positive rate, < 5% false positive rate

**Behavioral Anomaly Detection (Stream 2)**:
- Behavioral baseline builder (30-day lookback)
- Multi-dimensional anomaly detection (tool usage, timing, data volume, sensitivity)
- Anomaly alert manager with Slack/PagerDuty/email integration
- Auto-suspend capability for critical anomalies
- 7 anomaly types: unusual tool, unusual time/day, excessive data, sensitivity escalation, rapid requests, geographic anomaly
- < 5ms analysis latency (async)
- 80%+ detection rate on simulated attacks

**Network-Level Controls (Stream 3)**:
- Kubernetes NetworkPolicy for gateway egress control
- Kubernetes NetworkPolicy for gateway ingress lockdown
- Calico GlobalNetworkPolicy for domain-based egress filtering
- Default deny egress (whitelist-only)
- Comprehensive network policies documentation
- Support for cloud provider firewall rules (AWS, GCP, Azure)

**Secret Scanning & Redaction (Stream 4)**:
- Secret scanner with 25+ pattern types
- Automatic redaction with `[REDACTED]` marker
- High-confidence detection (95%+ accuracy)
- Support for: OpenAI keys, GitHub tokens, AWS keys, private keys, JWTs, database connections, Stripe keys, Anthropic keys, and more
- False positive reduction for test/example values
- < 1ms scanning latency (p95)
- 100% detection on test dataset

**Multi-Factor Authentication (Stream 5)**:
- MFA challenge system with TOTP, SMS, Push, Email methods
- TOTP code generation and verification (RFC 6238)
- Configurable timeout (default: 120s) and max attempts (default: 3)
- Challenge storage with automatic expiration
- QR code generation support for TOTP enrollment
- Tool sensitivity-based MFA policies
- Comprehensive audit logging for MFA events

**Integration & Testing (Stream 6)**:
- End-to-end integration tests for all 6 security scenarios
- Performance testing suite with latency and throughput benchmarks
- Unit tests for all security components (injection, anomaly, secrets, MFA)
- Load testing at 1000 req/s sustained
- Consolidated security documentation
- v1.3.0 release notes and implementation guide

**Documentation**:
- Comprehensive security overview (`docs/security/README.md`)
- Individual feature guides for each security component
- Network policies deployment guide
- Performance benchmarks and optimization guide
- Production deployment checklist
- Troubleshooting guide

### Performance
- Combined security overhead < 10ms (p95) with all features enabled
- Injection detection: 2.8ms (p95)
- Secret scanning: 0.7ms (p95)
- Anomaly detection: 4.2ms (p95, async)
- Sustained 1000 req/s with all security features enabled
- Linear scaling with parameter/response size
- Zero memory leaks after 100K requests

### Security
- Addresses Lethal Trifecta Analysis findings:
  - LT-1: Prompt injection vulnerabilities → Mitigated with injection detector
  - LT-2: Insider threat risks → Mitigated with anomaly detection
  - LT-3: Data exfiltration vectors → Blocked with network policies + secret scanning
- Defense-in-depth architecture with 5 security layers
- No critical CVEs introduced

### Infrastructure
- Kubernetes NetworkPolicy manifests (`k8s/network-policies/`)
- Calico GlobalNetworkPolicy support
- Injection pattern configuration system
- MFA challenge storage (Redis-based)
- Security metrics and monitoring framework

## [1.2.0] - 2024-12-23

### Added

**Gateway Client Implementation**:
- HTTP transport for MCP Gateway communication (PR #44)
- SSE (Server-Sent Events) transport for streaming (PR #44)
- stdio transport for local process communication (PR #45)
- Unified Gateway client with automatic transport selection (PR #47)
- End-to-end Gateway integration tests
- Real MCP server communication support (replacing stubbed implementation)

**Policy Validation Framework**:
- Comprehensive OPA Rego policy validation
- Syntax validation via OPA check
- Forbidden pattern detection (security vulnerabilities)
- Required rules verification (allow, deny, reason)
- Sample input testing framework
- Policy injection attack prevention

**Test Infrastructure Improvements**:
- Docker Compose V2 migration (all scripts updated to use `docker compose`)
- pytest-docker 3.x compatibility fixes
- LDAP integration test suite (28 tests)
- All auth provider tests passing (80/80 tests)
- Removed obsolete `version` attributes from docker-compose files
- Fixed port conflicts between test services

### Changed
- Updated all shell scripts to use Docker Compose V2 syntax
- Updated pytest-docker fixtures to use `localhost` instead of deprecated `docker_ip`
- Test fixtures now use proper session scope for container management

### Fixed
- LDAP integration test fixture parameter issues
- Case-insensitive username test (corrected LDAP behavior expectations)
- SAML service port conflict (moved from 8080 to 8082)
- Docker Compose version warnings

### Testing
- Test coverage: 85%+ for Gateway client
- 100% auth provider test pass rate (52 unit + 28 integration)
- E2E Gateway integration tests
- Policy validation test suite

### Performance
- Gateway client HTTP transport: <50ms p95 latency
- SSE transport: real-time streaming support
- stdio transport: direct process communication

### Migration
- No breaking changes
- Gateway features remain opt-in (GATEWAY_ENABLED flag)
- Existing v1.1.0 deployments compatible
- Test infrastructure updates transparent to users

## [1.1.0] - 2025-XX-XX

### Added

**MCP Gateway Integration (Opt-in Feature)**:
- Gateway client for connecting to MCP Gateway Registry
- Gateway authorization endpoints (`/api/v1/gateway/*`)
- Agent-to-Agent (A2A) authorization support
- OPA policies for Gateway and A2A authorization
- Gateway audit logging and SIEM integration
- Prometheus metrics for Gateway operations
- Grafana dashboard for Gateway monitoring

**New API Endpoints**:
- `POST /api/v1/gateway/authorize` - Authorize Gateway requests
- `POST /api/v1/gateway/authorize-a2a` - Authorize A2A communication
- `GET /api/v1/gateway/servers` - List authorized servers
- `GET /api/v1/gateway/tools` - List authorized tools
- `POST /api/v1/gateway/audit` - Log Gateway events
- `GET /api/v1/version` - Get version and feature status

**Configuration**:
- `GATEWAY_ENABLED` - Enable Gateway integration (default: `false`)
- `GATEWAY_URL` - Gateway API endpoint
- `GATEWAY_API_KEY` - Gateway authentication
- `A2A_ENABLED` - Enable A2A authorization (default: `false`)
- `GATEWAY_TIMEOUT_SECONDS` - Request timeout (default: `30`)
- `GATEWAY_RETRY_ATTEMPTS` - Retry attempts (default: `3`)

**Database**:
- New table: `gateway_audit_events` (additive, optional)
- New table: `gateway_api_keys` (additive, optional)
- Reversible migrations for safe rollback

**Documentation**:
- Complete Gateway integration guide (docs/gateway-integration/)
- API reference for Gateway endpoints
- Authentication guide (JWT, API keys, Agent tokens)
- Deployment guides (Quick Start, Kubernetes, Production)
- Configuration guides (Gateway, Policies, A2A)
- Operational runbooks (Troubleshooting, Incident Response, Maintenance)
- Architecture documentation (Integration, Security)
- Migration guide (v1.0.0 → v1.1.0)
- Feature flags documentation
- Release notes
- Docker Compose example with full stack
- OPA policy examples (gateway.rego, a2a.rego)
- Kubernetes manifest examples

**Examples**:
- Complete docker-compose setup with Gateway integration
- OPA policy examples for Gateway and A2A authorization
- Helper scripts for setup and testing

### Changed
- None (fully backwards compatible)

### Deprecated
- None

### Removed
- None

### Fixed
- None (new feature release)

### Security
- Gateway integration includes parameter filtering to prevent injection attacks
- A2A authorization enforces trust levels and capabilities
- All Gateway operations audited
- JWT token validation for Gateway API keys
- Rate limiting per token type

### Performance
- Zero performance impact when Gateway integration disabled
- Gateway authorization: P95 <50ms (when enabled)
- Throughput: 5000+ req/s (when enabled)
- Minimal memory overhead (<15% when enabled)

### Testing
- Test coverage: 91% (up from 87% in v1.0.0)
- Backwards compatibility tests (v1.0.0 behavior verified)
- Migration tests (upgrade/downgrade)
- Feature flag tests
- Gateway integration tests
- A2A authorization tests

### Migration
- Upgrade: `docker pull sark:1.1.0 && alembic upgrade head`
- Downgrade: `alembic downgrade -1 && docker pull sark:1.0.0`
- Zero-downtime upgrade supported
- Rollback supported
- See docs/gateway-integration/MIGRATION_GUIDE.md for detailed instructions

### Compatibility
- 100% backwards compatible with v1.0.0
- Gateway features disabled by default
- No breaking changes to existing APIs
- Safe to upgrade without enabling Gateway features

## [0.2.0] - 2025-11-23

### Added

**Authentication**:
- OIDC authentication provider (Google OAuth, Azure AD, Okta)
- LDAP/Active Directory integration with connection pooling
- SAML 2.0 SP implementation (Azure AD, Okta)
- API Key management with scoped permissions and rotation
- Session management with Valkey backend
- Multi-factor authentication (MFA) support with TOTP
- Rate limiting per API key and per user

**Authorization**:
- Open Policy Agent (OPA) integration
- Default RBAC, team-based, and sensitivity-level policies
- Policy caching with Valkey (95%+ hit rate)
- Environment-based policy templates (dev/staging/prod)
- Policy versioning and rollback mechanism
- Time-based access controls
- IP allowlist/blocklist policies

**SIEM Integration**:
- Splunk HEC integration with custom indexes
- Datadog Logs API integration with tagging
- Kafka background worker for async event forwarding
- SIEM adapter framework for extensibility
- Dead letter queue for failed events
- Circuit breaker pattern for graceful degradation
- 10,000+ events/min throughput capacity

**API Enhancements**:
- Cursor-based pagination for all list endpoints
- Search and filtering (status, team, sensitivity, tags)
- Full-text search on server name/description
- Bulk operations (register, update, delete)
- Comprehensive OpenAPI documentation

**Database Optimizations**:
- TimescaleDB for audit logging (90%+ compression)
- 50+ strategic indexes (B-Tree, GIN, partial)
- Connection pooling with PgBouncer (200 max connections)
- Query optimization with EXPLAIN ANALYZE
- Continuous aggregates for dashboards

**Valkey Optimizations**:
- Connection pooling (20 connections per instance)
- Tiered TTL caching strategy (5min-1hour)
- I/O threading for high concurrency (4 threads)
- Valkey Sentinel HA (3 nodes)
- 95%+ cache hit rate

**Security**:
- All 7 critical HTTP security headers implemented
- Argon2id password hashing (OWASP recommended)
- TLS 1.3 only (no older protocols)
- Input validation with Pydantic models
- SSRF protection (blocked internal IPs)
- Container security hardening (non-root, read-only filesystem)
- Kubernetes Pod Security Standards (restricted mode)
- Network policies for pod-to-pod traffic restriction

**Documentation** (17 guides, 32,000+ lines):
- QUICK_START.md - 15-minute getting started guide
- API_REFERENCE.md - Complete API documentation
- ARCHITECTURE.md - Enhanced with 7 Mermaid diagrams
- TROUBLESHOOTING.md - Master troubleshooting guide
- PERFORMANCE_TESTING.md - Performance testing methodology
- SECURITY_BEST_PRACTICES.md - Security development practices
- INCIDENT_RESPONSE.md - 6 incident response playbooks
- DATABASE_OPTIMIZATION.md - Complete database optimization guide
- REDIS_OPTIMIZATION.md - Complete Valkey optimization guide
- SECURITY_HARDENING.md - Security hardening checklist (60+ items)
- PRODUCTION_DEPLOYMENT.md - Production deployment procedures
- DISASTER_RECOVERY.md - Complete DR plan (RTO < 4h, RPO < 15min)
- OPERATIONS_RUNBOOK.md - Day-to-day operational procedures
- KNOWN_ISSUES.md - Known issues and limitations
- PRODUCTION_HANDOFF.md - Production deployment handoff (75-item checklist)
- PHASE2_COMPLETION_REPORT.md - Phase 2 summary
- DEVELOPMENT_LOG.md - Complete development history

**Testing**:
- 87% test coverage (target: 85%+)
- Comprehensive integration tests for large-scale operations
- SIEM load testing (10,000+ events/min validated)
- Performance benchmarks for all critical paths
- Negative testing for unauthorized access and invalid input

### Changed
- Updated README.md with Phase 2 completion status
- Enhanced CONTRIBUTING.md with documentation guidelines
- Improved error handling across all modules

### Fixed
- N/A (initial Phase 2 release)

### Performance
- API response time (p95): 85ms (target: <100ms) ✅
- API response time (p99): 150ms (target: <200ms) ✅
- Policy evaluation (p95): <50ms ✅
- Database query (p95): 40ms ✅
- Valkey GET latency (p95): 0.8ms ✅
- Throughput: 1,200 req/s (target: >1,000) ✅

### Security
- 0 P0/P1 security vulnerabilities
- All OWASP Top 10 protections implemented
- Security scan results: Clean (Bandit, Trivy, Safety, OWASP ZAP)

## [0.1.0] - 2025-11-22

### Added
- Initial project structure setup
- CI/CD pipeline with GitHub Actions
- Python 3.11 development environment
- Docker and Docker Compose configuration
- Code quality tools (Black, Ruff, MyPy)
- Pre-commit hooks
- Comprehensive testing framework (pytest)
- Contributing guidelines and coding standards
- Development tooling (Makefile, setup scripts)

[Unreleased]: https://github.com/username/sark/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/username/sark/compare/v0.2.0...v1.1.0
[0.2.0]: https://github.com/username/sark/releases/tag/v0.2.0
[0.1.0]: https://github.com/username/sark/releases/tag/v0.1.0
