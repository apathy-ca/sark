# SARK Documentation

**Enterprise-Grade MCP Governance System**

> *"He's not any kind of user, SARK, he's a program."*
> —MCP, probably

Welcome to the SARK (Security Audit and Resource Kontroler) documentation. SARK provides enterprise-grade security and governance for Model Context Protocol (MCP) deployments at massive scale.

## What is SARK?

SARK addresses discovery, authorization, audit, runtime enforcement, and API Gateway integration—enabling safe MCP adoption across large organizations.

**Target Scale:** 50,000+ employees, 10,000+ MCP servers

## Quick Links

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } __Quick Start__

    ---

    Get started with SARK in 15 minutes

    [:octicons-arrow-right-24: Quick Start Guide](QUICK_START.md)

-   :material-api:{ .lg .middle } __API Reference__

    ---

    Complete API documentation and examples

    [:octicons-arrow-right-24: API Reference](API_REFERENCE.md)

-   :material-docker:{ .lg .middle } __Deployment__

    ---

    Production deployment guides and best practices

    [:octicons-arrow-right-24: Deployment Guide](DEPLOYMENT.md)

-   :material-shield-lock:{ .lg .middle } __Security__

    ---

    Security architecture and hardening guides

    [:octicons-arrow-right-24: Security Guide](SECURITY.md)

</div>

## Key Features

### 🔐 Zero-Trust Architecture
Multi-layer enforcement with comprehensive authentication and authorization

### 🔍 Automated Discovery
Agentless scanning and lightweight monitoring for MCP servers

### 🛡️ Policy-Based Authorization
Hybrid ReBAC+ABAC authorization via Open Policy Agent

### 📊 Immutable Audit Trails
Complete audit logging with TimescaleDB for compliance

### 🔑 Dynamic Secrets Management
Integration with HashiCorp Vault for secure credential handling

### 🌐 API Gateway Integration
Kong Gateway integration for edge security

## Project Status

✅ **Phase 2 - Operational Excellence** - COMPLETE (November 2025)

🎉 **Production Ready** - Comprehensive authentication, authorization, SIEM integration, and operational documentation complete.

**Phase 2 Achievements:**
- ✅ Multi-protocol authentication (OIDC, LDAP, SAML, API Keys)
- ✅ Policy-based authorization with OPA
- ✅ SIEM integrations (Splunk, Datadog)
- ✅ Comprehensive documentation (17+ guides, 32,000+ lines)
- ✅ Production deployment procedures
- ✅ 87% test coverage

**Next Steps:**
- **Phase 3 (Q1 2026):** Production deployment, monitoring, user feedback, enhancements

## Getting Started

### Prerequisites

- Python 3.11+
- Docker with Docker Compose v2
- PostgreSQL 15+
- Redis 7+
- Open Policy Agent 0.60+

### Quick Installation

```bash
# 1. Clone and setup
git clone <repository-url>
cd sark && python3.11 -m venv venv && source venv/bin/activate
pip install -e ".[dev]"

# 2. Start services
docker compose --profile full up -d

# 3. Test authentication
curl -X POST http://localhost:8000/api/v1/auth/login/ldap \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

For complete setup instructions, see the [Quick Start Guide](QUICK_START.md).

## Documentation Structure

### For New Users
Start with the [Quick Start Guide](QUICK_START.md) to get SARK running in 15 minutes.

### For Deployers
Review [Architecture](ARCHITECTURE.md), [Deployment Guide](DEPLOYMENT.md), and [Production Readiness](PRODUCTION_READINESS.md).

### For Developers
Check out [Development Guide](DEVELOPMENT.md), [API Reference](API_REFERENCE.md), and [Testing Strategy](TESTING_STRATEGY.md).

### For Operators
See [Operational Runbook](OPERATIONAL_RUNBOOK.md), [Monitoring](MONITORING.md), and [Incident Response](INCIDENT_RESPONSE.md).

## Performance

SARK is designed for enterprise scale with high performance:

- **API Response Time:** p95 < 100ms
- **Throughput:** 1,200+ req/s
- **Policy Cache Hit Rate:** >95%
- **Cache Hit Latency:** <5ms
- **SIEM Throughput:** 10,000+ events/min

See [Performance Report](PERFORMANCE_REPORT.md) for detailed benchmarks.

## Support

- **Documentation:** You're reading it!
- **Issues:** [GitHub Issues](https://github.com/apathy-ca/sark/issues)
- **Discussions:** [GitHub Discussions](https://github.com/apathy-ca/sark/discussions)

## License

MIT License - see [LICENSE](https://github.com/apathy-ca/sark/blob/main/LICENSE) file for details.

## Copyright

Copyright 2025 James Henry. All rights reserved.
