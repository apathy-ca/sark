# SARK (Security Audit and Resource Kontroler)

**Enterprise-Grade Multi-Protocol AI Governance Platform**

> *"He's not any kind of user, SARK, he's a program."* —MCP, probably

SARK provides zero-trust governance for AI deployments at scale. Built for Model Context Protocol (MCP), with support for **MCP, HTTP/REST, gRPC, and custom protocols** through a universal adapter interface.

**Target Scale:** 50,000+ employees, 10,000+ AI resources

📖 **[Quick Start](docs/QUICK_START.md)** | **[Changelog](CHANGELOG.md)** | **[Full Documentation](docs/)**

---

## What is This?

**The Problem:** AI assistants accessing enterprise systems (databases, APIs, cloud infrastructure) without governance creates security chaos—no visibility, no control, no audit trail.

**The Solution:** SARK sits between AI and your systems, providing:
- 🔐 **Authentication** - OIDC, LDAP, SAML, API Keys
- 🛡️ **Authorization** - Policy-based access control (OPA)
- 📊 **Audit** - Complete trail of every AI action
- ⚡ **Performance** - <100ms p95 latency, 847 req/s sustained

**Example:** Developer asks AI "Show P0 bugs for my team" → AI uses MCP → SARK validates auth & policy → If approved, executes → Logs everything.

📖 **[What is MCP?](docs/MCP_INTRODUCTION.md)** | **[Architecture](docs/ARCHITECTURE.md)** | **[Use Cases](docs/USE_CASES.md)**

---

## Quick Start

**Prerequisites:**
- Python 3.11+
- Rust 1.92+ ([install Rust](https://rustup.rs/)) - Required for building native extensions

```bash
# 1. Clone and setup
git clone <repository-url>
cd sark
python3.11 -m venv venv && source venv/bin/activate
pip install -e ".[dev]"

# 2. Build Rust extensions
maturin develop

# 3. Start services
docker compose --profile full up -d

# 4. Access UI and API
# UI: http://localhost:5173 (admin/password)
# API: http://localhost:8000/docs
```

**Next Steps:**
- 📖 **[15-Minute Quick Start](docs/QUICK_START.md)** - Complete getting started guide
- 🔨 **[Rust Development Setup](docs/v1.4.0/RUST_SETUP.md)** - Building and working with Rust extensions
- 🎓 **[Tutorials](tutorials/)** - Step-by-step examples
- 📚 **[API Reference](docs/API_REFERENCE.md)** - Complete API documentation

---

## Features

### Multi-Protocol Support
- **MCP** - SSE and HTTP transports functional (stdio in development)
- **HTTP/REST** - OpenAPI discovery, 5 auth strategies
- **gRPC** - Reflection-based, mTLS support
- **Custom** - Plugin system for any protocol

### Enterprise Security (v1.3.0 Enhanced)
- **Authentication** - OIDC, LDAP, SAML, API Keys
- **Authorization** - OPA policy engine, ReBAC+ABAC
- **Audit** - Immutable logs, SIEM integration (Splunk, Datadog)
- **Federation** - Cross-organization governance with mTLS
- **🆕 Prompt Injection Detection** - 20+ patterns, entropy analysis, 30x faster
- **🆕 Anomaly Detection** - Behavioral baselines, real-time alerts
- **🆕 Secret Scanning** - 25+ patterns, automatic redaction, 50x faster
- **🆕 MFA** - TOTP/SMS/Push/Email for critical actions
- **🆕 Network Controls** - Kubernetes policies, egress filtering

### Production Ready
- ✅ 64% test coverage (improving to 85%), 0 known P0/P1 vulnerabilities
- ✅ <100ms p95 latency, 847 req/s sustained throughput
- ✅ Kubernetes-native, Helm charts, Terraform modules
- ✅ 100+ pages of documentation

📖 **[Features Overview](docs/FEATURES.md)** | **[Security](docs/SECURITY.md)** | **[Performance](docs/PERFORMANCE.md)**

---

## Web UI

Modern React UI for managing AI governance:

- 📊 Dashboard with metrics
- 🖥️ Server/resource management
- 📝 Policy editor (Rego syntax)
- 📜 Audit log viewer
- 🔑 API key management

```bash
cd frontend && npm install && npm run dev
# Access: http://localhost:5173
```

📖 **[UI User Guide](docs/UI_USER_GUIDE.md)** | **[UI Deployment](docs/DEPLOYMENT.md#ui-deployment)**

---

## Deployment

### Development
```bash
docker compose --profile full up -d
```

### Production
```bash
# Kubernetes with Helm
helm install sark ./helm/sark -n production --create-namespace

# Or with kubectl
kubectl apply -f k8s/
```

### Cloud Platforms
- AWS EKS, GCP GKE, Azure AKS
- Terraform modules included for all platforms

📖 **[Deployment Guide](docs/DEPLOYMENT.md)** | **[Terraform Guide](terraform/README.md)** | **[Production Readiness](docs/PRODUCTION_READINESS.md)**

---

## Documentation

### Getting Started
- **[Quick Start](docs/QUICK_START.md)** - 15-minute setup
- **[MCP Introduction](docs/MCP_INTRODUCTION.md)** - What is MCP?
- **[Architecture](docs/ARCHITECTURE.md)** - System design
- **[Use Cases](docs/USE_CASES.md)** - Real-world examples

### Deployment & Operations
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Production deployment
- **[Monitoring](docs/MONITORING.md)** - Observability setup
- **[Operations Runbook](docs/OPERATIONS_RUNBOOK.md)** - Day-2 operations

### Development
- **[Development Guide](docs/DEVELOPMENT.md)** - Setup and workflow
- **[API Reference](docs/API_REFERENCE.md)** - Complete API docs
- **[Contributing](CONTRIBUTING.md)** - Contribution guidelines

### Security & Compliance
- **[Security Guide](docs/SECURITY.md)** - Security best practices
- **[OPA Policy Guide](docs/OPA_POLICY_GUIDE.md)** - Policy authoring
- **[Audit & Compliance](docs/AUDIT_COMPLIANCE.md)** - Compliance features

📚 **[Full Documentation Index](docs/README.md)**

---

## Project Status

🚀 **v1.3.0 - Current Release** (Released Dec 26, 2025)

**Completed (v1.3.0):**
- ✅ Enterprise authentication (OIDC, LDAP, SAML, API Keys)
- ✅ Policy-based authorization (OPA)
- ✅ MCP Gateway integration (opt-in)
- ✅ SIEM integration (Splunk, Datadog)
- ✅ **Prompt injection detection** (20+ patterns, 30x faster than target)
- ✅ **Behavioral anomaly detection** (30-day baseline, real-time alerts)
- ✅ **Secret scanning & redaction** (25+ patterns, 50x faster than target)
- ✅ **MFA for critical actions** (TOTP, SMS, Push, Email)
- ✅ **Network security controls** (NetworkPolicies, egress filtering)
- ✅ Comprehensive testing (350+ unit, 530+ integration, 2200+ performance)
- ✅ Complete documentation (100+ pages)
- ✅ Production deployment guides

**Future Roadmap:**
- **v1.4.0** - Rust core optimization (5-10x performance)
- **v1.5.0** - Rust detection (10-100x performance)
- **v2.0.0** - Production-ready after security audit

📖 **[Roadmap](docs/ROADMAP.md)** | **[Changelog](CHANGELOG.md)**

---

## Requirements

- Python 3.11+
- Docker with Docker Compose v2
- PostgreSQL 15+, Valkey 7+ (Redis-compatible)
- Open Policy Agent 0.60+
- Kong Gateway 3.8+ (production)
- Kubernetes 1.28+ (production)

📖 **[Requirements](docs/REQUIREMENTS.md)**

---

## GRID Protocol

SARK is the **reference implementation of GRID Protocol Specification v0.1**.

**GRID** (Governed Resource Interaction Definition) is a universal governance protocol for machine-to-machine interactions—protocol-agnostic, federated, zero-trust, policy-first.

**SARK v1.1.0 Compliance:** 85% of GRID v0.1 specification

📖 **[Gap Analysis](docs/specifications/GRID_GAP_ANALYSIS_AND_IMPLEMENTATION_NOTES.md)** - Detailed compliance matrix

📖 **[GRID Specification](docs/specifications/GRID_PROTOCOL_SPECIFICATION_v0.1.md)** | **[Gap Analysis](docs/specifications/GRID_GAP_ANALYSIS_AND_IMPLEMENTATION_NOTES.md)**

---

## Contributing

We welcome contributions! See **[CONTRIBUTING.md](CONTRIBUTING.md)** for:
- Code style and standards
- Development workflow
- PR process
- Multi-agent collaboration guidelines

---

## License

MIT License - see **[LICENSE](LICENSE)** file for details.

**Copyright** © 2025 James Henry. All rights reserved.

---

**Built with ❤️ for enterprise AI governance at scale.**
