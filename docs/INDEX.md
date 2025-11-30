# SARK Documentation Index

**SARK (Security Audit and Resource Kontroler)** - Enterprise-grade multi-protocol governance for AI systems

**Version:** 2.0.0
**Last Updated:** November 2025
**Status:** Production Ready

---

## 🚀 Getting Started

**New to SARK?** Start here:

- **[README](../README.md)** - Project overview and introduction
- **[Installation Guide](deployment/INSTALLATION.md)** - Get SARK running
- **[Quick Start (15 minutes)](tutorials/v2/QUICKSTART.md)** - First steps with SARK v2.0
- **[What's New in v2.0](migration/V1_TO_V2_MIGRATION.md)** - New features and changes

### First-Time Setup
1. Read the [README](../README.md) to understand what SARK does
2. Follow the [Installation Guide](deployment/INSTALLATION.md)
3. Complete the [Quick Start Tutorial](tutorials/v2/QUICKSTART.md)
4. Explore [Example Projects](../examples/)

---

## 📚 User Guides

### Core Concepts
- **[Architecture Overview](architecture/V2_ARCHITECTURE.md)** - System design and components
- **[Multi-Protocol Support](api/v2/ADAPTER_INTERFACE.md)** - MCP, HTTP, gRPC governance
- **[Federation](federation/FEDERATION_GUIDE.md)** - Cross-organization governance
- **[Cost Attribution](architecture/V2_ARCHITECTURE.md#cost-attribution)** - Track and enforce budgets
- **[Policy Engine](v2.0/)** - OPA-based authorization

### Tutorials
- **[Getting Started with HTTP APIs](tutorials/v2/QUICKSTART.md)** - Govern REST APIs
- **[Getting Started with gRPC](../examples/grpc-adapter-example/)** - Govern gRPC services
- **[Setting Up Federation](federation/FEDERATION_GUIDE.md)** - Cross-org setup
- **[Cost Budgets](../examples/custom-policy-plugin/)** - Implement cost controls
- **[Custom Adapters](api/v2/ADAPTER_INTERFACE.md)** - Create protocol adapters

### How-To Guides
- [Register an HTTP API](api/v2/API_REFERENCE.md#register-resource)
- [Configure OAuth2 Authentication](api/v2/API_REFERENCE.md#http-rest)
- [Set Up mTLS for Federation](federation/FEDERATION_GUIDE.md#certificate-setup)
- [Create Custom Policies](../examples/custom-policy-plugin/)
- [Monitor Performance](monitoring/MONITORING_GUIDE.md)

---

## 🔧 Developer Guides

### Architecture
- **[System Architecture](architecture/V2_ARCHITECTURE.md)** - Complete system design
- **[Architecture Diagrams](architecture/diagrams/)** - Visual system overviews
  - [System Overview](architecture/diagrams/system-overview.mmd)
  - [Adapter Flow](architecture/diagrams/adapter-flow.mmd)
  - [Cost Attribution](architecture/diagrams/cost-attribution.mmd)
  - [Federation Flow](architecture/diagrams/federation-flow.mmd)
  - [Data Model](architecture/diagrams/data-model.mmd)
- **[Database Schema](database/V2_SCHEMA_DESIGN.md)** - Data model and migrations
- **[Performance Design](database/PERFORMANCE_OPTIMIZATION.md)** - Optimization strategies

### API Documentation
- **[API Reference](api/v2/API_REFERENCE.md)** - Complete REST API documentation
- **[Adapter Interface](api/v2/ADAPTER_INTERFACE.md)** - Protocol adapter specification
- **[SDK Usage](api/v2/API_REFERENCE.md#sdk-examples)** - Python and JavaScript SDKs

### Development
- **[Contributing Guide](../CONTRIBUTING.md)** - How to contribute
- **[Development Setup](../README.md#development)** - Local development environment
- **[Testing Guide](../tests/)** - Writing and running tests
- **[Code Style](../CONTRIBUTING.md)** - Coding standards

### Creating Adapters
- **[Adapter Interface Spec](api/v2/ADAPTER_INTERFACE.md)** - Complete specification
- **[HTTP Adapter Example](../examples/http-adapter-example/)** - Reference implementation
- **[gRPC Adapter Example](../examples/grpc-adapter-example/)** - Reference implementation
- **[Adapter Development Guide](api/v2/ADAPTER_INTERFACE.md#implementation-guide)** - Step-by-step guide

---

## 📊 Operations & Deployment

### Deployment
- **[Installation Guide](deployment/INSTALLATION.md)** - Initial setup
- **[Docker Deployment](../docker-compose.yml)** - Container orchestration
- **[Production Checklist](federation/FEDERATION_GUIDE.md#production-deployment-checklist)** - Pre-production validation
- **[High Availability](architecture/diagrams/deployment-ha.mmd)** - HA architecture
- **[Security Best Practices](security/V2_SECURITY_AUDIT.md)** - Security hardening

### Monitoring & Observability
- **[Monitoring Guide](monitoring/MONITORING_GUIDE.md)** - Metrics and alerts
- **[Performance Baselines](performance/V2_PERFORMANCE_BASELINES.md)** - Expected performance
- **[Grafana Dashboards](../monitoring/grafana/dashboards/)** - Pre-built dashboards
- **[Alert Rules](../monitoring/prometheus/rules/)** - Prometheus alerts

### Maintenance
- **[Database Migrations](database/V2_SCHEMA_DESIGN.md#migrations)** - Schema updates
- **[Backup & Recovery](database/V2_SCHEMA_DESIGN.md)** - Data protection
- **[Troubleshooting](federation/FEDERATION_GUIDE.md#troubleshooting-guide)** - Common issues
- **[Performance Tuning](database/PERFORMANCE_OPTIMIZATION.md)** - Optimization

---

## 🔄 Migration & Upgrades

### Migrating to v2.0
- **[Migration Guide](migration/V1_TO_V2_MIGRATION.md)** - Complete v1.x → v2.0 guide
- **[Breaking Changes](migration/V1_TO_V2_MIGRATION.md#breaking-changes)** - What changed
- **[Database Migration](migration/V1_TO_V2_MIGRATION.md#database-migration)** - Data migration
- **[Testing Migration](migration/V1_TO_V2_MIGRATION.md#testing-your-migration)** - Validation

### What's New in v2.0
- **Multi-Protocol Support** - HTTP, gRPC, MCP all governed uniformly
- **Federation Framework** - Cross-organization governance with mTLS
- **Cost Attribution** - Track and enforce resource usage costs
- **Policy Plugins** - Programmatic policy evaluation
- **Enhanced Security** - Comprehensive audit and security features

---

## 📖 Reference

### API Reference
- **[REST API](api/v2/API_REFERENCE.md)** - Complete endpoint reference
- **[Resources API](api/v2/API_REFERENCE.md#resources-api)** - Manage governed resources
- **[Authorization API](api/v2/API_REFERENCE.md#authorization-api)** - Policy evaluation
- **[Federation API](api/v2/API_REFERENCE.md#federation-api)** - Cross-org governance
- **[Cost API](api/v2/API_REFERENCE.md#cost-attribution-api)** - Cost tracking
- **[Audit API](api/v2/API_REFERENCE.md#audit-api)** - Audit logs

### Configuration
- **[Environment Variables](../docker-compose.yml)** - Configuration options
- **[Docker Compose](../docker-compose.yml)** - Container configuration
- **[Monitoring Stack](../docker-compose.monitoring.yml)** - Observability setup
- **[Federation Config](federation/FEDERATION_GUIDE.md#configuration)** - Federation setup

### Standards & Specifications
- **[Docker Compose Standards](standards/DOCKER_COMPOSE_STANDARDS.md)** - Container best practices
- **[GRID Protocol](../GRID_SPECIFICATION_README.md)** - Protocol specification
- **[Adapter Interface](api/v2/ADAPTER_INTERFACE.md)** - Protocol adapter spec

---

## 📁 Project History

### Development Process
- **[Session Reports](project-history/sessions/)** - Development session logs
- **[Worker Reports](project-history/workers/)** - Individual worker completions
- **[Orchestration Plan](../SARK_v2.0_ORCHESTRATED_IMPLEMENTATION_PLAN.md)** - Original plan

### Release Information
- **[Release Notes](../RELEASE_NOTES.md)** - Version history
- **[Changelog](../CHANGELOG.md)** - Detailed changes
- **[Roadmap](../docs/ROADMAP.md)** - Future plans

---

## 🔍 Finding What You Need

### By Role

**I'm a User (want to govern AI systems):**
1. Start with [README](../README.md)
2. Follow [Quick Start](tutorials/v2/QUICKSTART.md)
3. Read [API Reference](api/v2/API_REFERENCE.md)
4. Configure [Federation](federation/FEDERATION_GUIDE.md) (if needed)

**I'm a Developer (want to extend SARK):**
1. Read [Architecture](architecture/V2_ARCHITECTURE.md)
2. Study [Adapter Interface](api/v2/ADAPTER_INTERFACE.md)
3. See [Examples](../examples/)
4. Follow [Contributing Guide](../CONTRIBUTING.md)

**I'm an Operator (want to deploy SARK):**
1. Check [Installation Guide](deployment/INSTALLATION.md)
2. Review [Production Checklist](federation/FEDERATION_GUIDE.md#production-deployment-checklist)
3. Configure [Monitoring](monitoring/MONITORING_GUIDE.md)
4. Set up [High Availability](architecture/diagrams/deployment-ha.mmd)

### By Task

**Govern REST APIs:** [HTTP Adapter Guide](../examples/http-adapter-example/)
**Govern gRPC Services:** [gRPC Adapter Guide](../examples/grpc-adapter-example/)
**Set Up Cross-Org:** [Federation Guide](federation/FEDERATION_GUIDE.md)
**Track Costs:** [Cost Attribution](architecture/V2_ARCHITECTURE.md#cost-attribution)
**Write Policies:** [Policy Examples](../examples/custom-policy-plugin/)
**Monitor System:** [Monitoring Guide](monitoring/MONITORING_GUIDE.md)
**Troubleshoot Issues:** [Troubleshooting](federation/FEDERATION_GUIDE.md#troubleshooting-guide)

---

## 📞 Support & Community

### Getting Help
- **GitHub Issues**: [Report bugs or request features](https://github.com/yourusername/sark/issues)
- **Discussions**: [Ask questions and share ideas](https://github.com/yourusername/sark/discussions)
- **Documentation**: You're reading it!

### Contributing
- **[Contributing Guide](../CONTRIBUTING.md)** - How to contribute
- **[Code of Conduct](../CODE_OF_CONDUCT.md)** - Community guidelines
- **Pull Requests**: All contributions welcome!

---

## 📋 Quick Links

### Essential Documentation
- [README](../README.md) | [Quick Start](tutorials/v2/QUICKSTART.md) | [API Reference](api/v2/API_REFERENCE.md)
- [Architecture](architecture/V2_ARCHITECTURE.md) | [Migration Guide](migration/V1_TO_V2_MIGRATION.md) | [Federation](federation/FEDERATION_GUIDE.md)

### Examples
- [HTTP Examples](../examples/http-adapter-example/) | [gRPC Examples](../examples/grpc-adapter-example/) | [Policy Plugins](../examples/custom-policy-plugin/)

### Operations
- [Installation](deployment/INSTALLATION.md) | [Monitoring](monitoring/MONITORING_GUIDE.md) | [Security](security/V2_SECURITY_AUDIT.md)

---

**SARK v2.0** - Enterprise-grade multi-protocol governance for AI systems

*Documentation last updated: November 2025*
