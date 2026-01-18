# Security Policy

## Supported Versions

We release patches for security vulnerabilities. Currently supported versions:

| Version | Supported          | Notes |
| ------- | ------------------ | ----- |
| 1.6.x   | :white_check_mark: | Current release (96% vulnerability fix rate) |
| 1.5.x   | :white_check_mark: | Production readiness release |
| 1.4.x   | :white_check_mark: | Rust foundation release |
| 1.3.x   | :white_check_mark: | Security baseline |
| < 1.3.0 | :x:                | End of life |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via **[GitHub Security Advisories](https://github.com/apathy-ca/sark/security/advisories/new)**.

You should receive a response within 48 hours. If for some reason you do not, please follow up to ensure we received your original message.

Please include the following information:

- Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

This information will help us triage your report more quickly.

## Vulnerability Disclosure Policy

When the security team receives a security bug report, they will:

1. Confirm the problem and determine the affected versions
2. Audit code to find any similar problems
3. Prepare fixes for all supported releases
4. Release new security patch versions as soon as possible

## Security Features (Phase 2)

SARK has implemented comprehensive security features in Phase 2:

### Authentication Security

- **Multi-Protocol Authentication**:
  - OIDC (OAuth 2.0) with PKCE support
  - LDAP/Active Directory with secure connection pooling
  - SAML 2.0 SP implementation
  - API Key authentication with scoped permissions

- **Password Security**:
  - Argon2id hashing (OWASP recommended)
  - Parameters: time_cost=3, memory_cost=64MB, parallelism=4
  - Resistant to GPU/ASIC attacks
  - Salt length: 16 bytes, Hash length: 32 bytes

- **Token Security**:
  - JWT tokens with HS256/RS256 signatures
  - Short-lived access tokens (15 minutes)
  - Refresh token rotation
  - Session management with concurrent session limits

### Authorization Security

- **Policy-Based Access Control**:
  - Open Policy Agent (OPA) integration
  - Default deny (fail closed) security model
  - RBAC, team-based, and sensitivity-level policies
  - Policy caching with invalidation (95%+ hit rate)

### Network Security

- **HTTP Security Headers** (all 7 critical headers implemented):
  ```
  Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
  Content-Security-Policy: default-src 'self'; ...
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  X-XSS-Protection: 1; mode=block
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: geolocation=(), microphone=(), camera=()
  ```

- **TLS Configuration**:
  - TLS 1.3 only (no TLS 1.2, 1.1, 1.0)
  - Strong cipher suites only
  - Perfect Forward Secrecy (PFS)

### Application Security

- **Input Validation**:
  - Pydantic models for all API requests
  - Regex validation for URLs, emails, usernames
  - SSRF protection (blocked internal IPs: localhost, 127.0.0.1, 169.254.169.254)
  - SQL injection protection (parameterized queries only)

- **Rate Limiting**:
  - Per API key: configurable (default: 1,000/hour)
  - Per user (JWT): 5,000/hour
  - Admin bypass: unlimited
  - Public endpoints: 100/hour per IP

- **CORS Policy**:
  - Strict origin validation
  - Configurable allowed origins
  - Credentials support (with explicit origins)

### Container Security

- **Container Hardening**:
  - Non-root user (UID 1000)
  - Read-only root filesystem
  - Capability dropping (DROP ALL, add only NET_BIND_SERVICE)
  - No privileged containers
  - Security scanning with Trivy

### Kubernetes Security

- **Pod Security**:
  - Pod Security Standards: restricted mode
  - Security contexts enforced
  - Resource limits set (CPU, memory)
  - No host network, host PID, host IPC

- **Network Policies**:
  - Pod-to-pod traffic restricted
  - Ingress/egress rules defined
  - Default deny-all policy

- **RBAC**:
  - Least privilege service accounts
  - Role-based access control
  - No cluster-admin permissions

### Secrets Management

- **Secrets Handling**:
  - Kubernetes Secrets for sensitive data
  - HashiCorp Vault integration (optional)
  - Secrets encrypted at rest (Kubernetes)
  - No secrets in code or Git
  - Environment variable injection only

### Audit and Compliance

- **Comprehensive Audit Logging**:
  - All authentication attempts (success/failure)
  - All authorization decisions
  - All data access (read/write/delete)
  - All configuration changes
  - Immutable audit trail (TimescaleDB)

- **SIEM Integration**:
  - Real-time event forwarding to Splunk/Datadog
  - 10,000+ events/min throughput
  - Dead letter queue for reliability
  - Circuit breaker for graceful degradation

- **Compliance Support**:
  - SOC 2 Type II ready (audit logging, access controls)
  - PCI-DSS compliant (encryption, access control, audit logging)
  - HIPAA ready (PHI encryption, access controls, BAA process)

### Security Testing

- **Automated Security Scanning**:
  - Bandit (Python security linter)
  - Trivy (container vulnerability scanner)
  - Safety (dependency vulnerability scanner)
  - OWASP ZAP (web application security testing)

- **Test Coverage**:
  - 87% overall test coverage
  - Security-focused test cases
  - Negative testing (unauthorized access, invalid input)
  - Performance testing under load

### Security Documentation

Comprehensive security documentation available:

- **[docs/SECURITY_BEST_PRACTICES.md](docs/SECURITY_BEST_PRACTICES.md)** - Security development practices
- **[docs/SECURITY_HARDENING.md](docs/SECURITY_HARDENING.md)** - Security hardening checklist (60+ items)
- **[docs/INCIDENT_RESPONSE.md](docs/INCIDENT_RESPONSE.md)** - Incident response playbooks

## Security Audit Results (v1.6.0)

**Status**: ✅ **1 Low-Severity Vulnerability** (96% remediation rate - 24/25 CVEs fixed)

**Security Scan Results**:
- Bandit: No high/critical issues
- Trivy: No high/critical vulnerabilities in container images
- pip-audit: 1 low-severity vulnerability (nbconvert - Windows-only, dev dependency)
- OWASP ZAP: No high/critical findings

**v1.6.0 Security Improvements**:
- Fixed 24/25 Dependabot vulnerabilities (96% fix rate)
- Eliminated ecdsa dependency (CVE-2024-23342)
- Upgraded 12 packages for security patches
- See [v1.6.0 Security Audit](docs/v1.6.0/SECURITY_AUDIT.md) for details

**Last Security Audit**: January 2026 (v1.6.0 release)

## Security Best Practices for Users

When deploying SARK in production:

1. **Use TLS 1.3** for all connections
2. **Enable all security headers** (see docs/SECURITY_HARDENING.md)
3. **Rotate secrets quarterly** (API keys, database passwords, etc.)
4. **Monitor audit logs** for suspicious activity
5. **Keep dependencies updated** (run `pip list --outdated` regularly)
6. **Run security scans** before deployment (see docs/SECURITY_BEST_PRACTICES.md)
7. **Follow principle of least privilege** for all service accounts
8. **Enable MFA** for all administrative users
9. **Backup audit logs** to immutable storage
10. **Test disaster recovery** procedures quarterly

## Security Roadmap

Future security enhancements (Phase 3):

- WebAuthn/U2F support for stronger MFA
- Hardware Security Module (HSM) integration
- Mutual TLS (mTLS) for service-to-service authentication
- Advanced threat detection with machine learning
- Automated vulnerability remediation
- Security information dashboard

## Contact

For security concerns:
- **GitHub Security Advisories**: [Report a vulnerability](https://github.com/apathy-ca/sark/security/advisories/new) (preferred)
- **PGP Key**: Available upon request for sensitive disclosures

For general questions, see [CONTRIBUTING.md](CONTRIBUTING.md)

---

**Note**: This security policy is reviewed and updated quarterly. Last updated: January 2026 (v1.6.0).
