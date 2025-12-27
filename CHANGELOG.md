# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Nothing yet

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
