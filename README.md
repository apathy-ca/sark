# SARK (Security Audit and Resource Kontroler)

**Enterprise-Grade Multi-Protocol AI Governance Platform**

> *"He's not any kind of user, SARK, he's a program."* —MCP, probably

SARK v2.0 provides zero-trust governance for AI deployments at scale. Originally built for Model Context Protocol (MCP), v2.0 now supports **MCP, HTTP/REST, gRPC, and custom protocols** through a universal adapter interface.

**Target Scale:** 50,000+ employees, 10,000+ AI resources

📖 **[Quick Start](docs/QUICK_START.md)** | **[What's New in v2.0](RELEASE_NOTES_v2.0.0.md)** | **[Migration Guide](docs/MIGRATION_v1_to_v2.md)** | **[Full Documentation](docs/)**

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

```bash
# 1. Clone and setup
git clone <repository-url>
cd sark
python3.11 -m venv venv && source venv/bin/activate
pip install -e ".[dev]"

# 2. Start services
docker compose --profile full up -d

# 3. Access UI and API
# UI: http://localhost:5173 (admin/password)
# API: http://localhost:8000/docs
```

**Next Steps:**
- 📖 **[15-Minute Quick Start](docs/QUICK_START.md)** - Complete getting started guide
- 🎓 **[Tutorials](tutorials/)** - Step-by-step examples
- 📚 **[API Reference](docs/API_REFERENCE.md)** - Complete API documentation

---

## Features

### Multi-Protocol Support
- **MCP** - SSE and HTTP transports functional (stdio in development)
- **HTTP/REST** - OpenAPI discovery, 5 auth strategies
- **gRPC** - Reflection-based, mTLS support
- **Custom** - Plugin system for any protocol

### Enterprise Security
- **Authentication** - OIDC, LDAP, SAML, API Keys
- **Authorization** - OPA policy engine, ReBAC+ABAC
- **Audit** - Immutable logs, SIEM integration (Splunk, Datadog)
- **Federation** - Cross-organization governance with mTLS

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

🎉 **v2.0.0-rc1 - Release Candidate** (Pre-release validation in progress)

**Completed:**
- ✅ Multi-protocol architecture (MCP, HTTP, gRPC)
- ✅ Enterprise authentication (OIDC, LDAP, SAML, API Keys)
- ✅ Policy-based authorization (OPA)
- ✅ Federation support with mTLS
- ✅ Cost attribution and budgets
- ✅ SIEM integration (Splunk, Datadog)
- ✅ Comprehensive documentation (100+ pages)
- ✅ Production deployment guides

**Roadmap:**
- **Q1 2026** - v2.1: Enhanced federation, additional protocol adapters
- **Q2 2026** - v2.2: Advanced cost models, policy marketplace

📖 **[Roadmap](docs/ROADMAP.md)** | **[Changelog](CHANGELOG.md)**

---

## Requirements

- Python 3.11+
- Docker with Docker Compose v2
- PostgreSQL 15+, Redis 7+
- Open Policy Agent 0.60+
- Kong Gateway 3.8+ (production)
- Kubernetes 1.28+ (production)

📖 **[Requirements](docs/REQUIREMENTS.md)**

---

## GRID Protocol

SARK is the **reference implementation of GRID Protocol Specification v0.1**.

**GRID** (Governed Resource Interaction Definition) is a universal governance protocol for machine-to-machine interactions—protocol-agnostic, federated, zero-trust, policy-first.

**SARK v2.0-rc1 Compliance:** 85% of GRID v0.1 specification

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

**Copyright** © 2024 James R. A. Henry. All rights reserved.

---

**Built with ❤️ for enterprise AI governance at scale.**
