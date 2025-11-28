# SARK Gateway Integration Tutorial Series

Welcome to the comprehensive Gateway Integration tutorial series! These tutorials will take you from beginner to expert in SARK Gateway integration.

## Tutorial Overview

### 📚 [Tutorial 1: Quick Start Guide](./01-quickstart-guide.md)
**Level:** Beginner | **Time:** 10 minutes

Get started with Gateway integration in just 10 minutes! Learn to:
- Register your first MCP Gateway server
- Configure basic authentication
- Test tool invocation authorization
- Verify the integration works

**Perfect for:** First-time users, POC/demo setups, understanding the basics

---

### 🏗️ [Tutorial 2: Building a Gateway Server](./02-building-gateway-server.md)
**Level:** Intermediate | **Time:** 60-90 minutes

Build a production-ready Gateway server from scratch. Learn to:
- Design scalable Gateway architecture
- Implement multiple tool endpoints with type safety
- Add authentication and authorization flow
- Create and test custom OPA policies
- Deploy to development environment

**Perfect for:** Developers building custom Gateway servers, teams needing specialized implementations

---

### 🚀 [Tutorial 3: Production Deployment](./03-production-deployment.md)
**Level:** Advanced | **Time:** 2-3 hours

Deploy Gateway + SARK to production with enterprise-grade reliability. Learn to:
- Design highly available architecture
- Configure Kubernetes deployment with auto-scaling
- Set up monitoring (Prometheus) and alerting
- Implement security hardening
- Perform zero-downtime updates
- Handle 10,000+ requests per second

**Perfect for:** DevOps engineers, SREs, production deployments

---

### ⚡ [Tutorial 4: Extending the Gateway](./04-extending-gateway.md)
**Level:** Expert | **Time:** 3-4 hours

Extend your Gateway with advanced customization. Learn to:
- Create custom tool types with specialized handling
- Write advanced OPA policies (trust levels, delegation, time-based controls)
- Build authentication plugins (OAuth2, LDAP, mTLS)
- Optimize for 50,000+ requests per second
- Implement custom middleware and advanced auditing

**Perfect for:** Advanced users, custom implementations, enterprise requirements

---

## Learning Path

```
┌─────────────────────────┐
│  Tutorial 1             │
│  Quick Start (10 min)   │
│  ✓ Basic setup          │
│  ✓ First authorization  │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Tutorial 2             │
│  Building Gateway       │
│  (60-90 min)            │
│  ✓ Complete server      │
│  ✓ OPA policies         │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Tutorial 3             │
│  Production Deployment  │
│  (2-3 hours)            │
│  ✓ Kubernetes           │
│  ✓ Monitoring           │
│  ✓ High availability    │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Tutorial 4             │
│  Extending Gateway      │
│  (3-4 hours)            │
│  ✓ Custom plugins       │
│  ✓ Advanced policies    │
│  ✓ Performance tuning   │
└─────────────────────────┘
```

## Prerequisites

### Tutorial 1 (Beginner)
- Docker & Docker Compose
- Basic REST API knowledge
- 10 minutes

### Tutorial 2 (Intermediate)
- Tutorial 1 completed
- Python experience (intermediate)
- FastAPI familiarity
- 60-90 minutes

### Tutorial 3 (Advanced)
- Tutorials 1 & 2 completed
- Kubernetes experience (basic)
- Production infrastructure access
- 2-3 hours

### Tutorial 4 (Expert)
- All previous tutorials completed
- OPA/Rego experience (intermediate)
- Python experience (advanced)
- 3-4 hours

---

## Quick Reference

### Common Commands

```bash
# Start SARK with Gateway integration
docker compose -f docker-compose.gateway.yml up -d

# Get JWT token
export TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123"}' \
  | jq -r '.access_token')

# Authorize a tool invocation
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "gateway:tool:invoke",
    "server_name": "postgres-mcp",
    "tool_name": "execute_query",
    "user": {"id": "user_123", "email": "test@example.com", "roles": ["admin"]}
  }'

# List authorized servers
curl -X GET http://localhost:8000/api/v1/gateway/servers \
  -H "Authorization: Bearer $TOKEN"
```

### Key Concepts

| Concept | Description | Tutorial |
|---------|-------------|----------|
| **Gateway Server** | Routes MCP requests with authorization | 1, 2 |
| **Tool Invocation** | Executing a tool on an MCP server | 1, 2 |
| **Authorization Flow** | Gateway → SARK → OPA → Decision | 1, 2, 3 |
| **OPA Policies** | Rego policies defining access rules | 2, 3, 4 |
| **Tool Types** | Categories of tools (query, mutation, admin) | 4 |
| **Sensitivity Levels** | Security classification (low, medium, high, critical) | 4 |
| **Trust Levels** | User/agent trust hierarchy | 4 |
| **HPA** | Horizontal Pod Autoscaler for scaling | 3 |
| **Circuit Breaker** | Resilience pattern for service failures | 4 |

---

## Tutorial Features

Each tutorial includes:

✅ **Working Code Examples** - Copy-paste ready code that actually works
✅ **Step-by-Step Instructions** - Clear, numbered steps with explanations
✅ **Expected Output** - Know what success looks like
✅ **Troubleshooting Section** - Common issues and solutions
✅ **"What You Learned" Summary** - Recap key takeaways
✅ **Links to Documentation** - Deep dive into related topics
✅ **Real-World Scenarios** - Practical, production-relevant examples

---

## Tutorial Statistics

| Tutorial | Lines | Words | Topics Covered | Code Blocks |
|----------|-------|-------|----------------|-------------|
| Tutorial 1 | 717 | ~4,500 | 7 major steps | 30+ |
| Tutorial 2 | 1,468 | ~9,000 | 11 parts | 60+ |
| Tutorial 3 | 1,492 | ~9,500 | 11 parts | 70+ |
| Tutorial 4 | 1,813 | ~11,500 | 5 parts | 80+ |
| **Total** | **5,490** | **~34,500** | **34 parts** | **240+** |

---

## Additional Resources

### Official Documentation
- **[Gateway API Reference](../../gateway-integration/API_REFERENCE.md)** - Complete API documentation
- **[OPA Policy Guide](../../gateway-integration/configuration/POLICY_CONFIGURATION.md)** - Policy authoring guide
- **[Authentication Guide](../../AUTHENTICATION.md)** - Advanced authentication methods
- **[Deployment Guide](../../gateway-integration/deployment/QUICKSTART.md)** - Production deployment
- **[Troubleshooting](../../gateway-integration/runbooks/TROUBLESHOOTING.md)** - Common issues

### Examples
- **[Docker Compose Setup](../../../examples/gateway-integration/README.md)** - Complete Docker setup
- **[OPA Policies](../../../examples/gateway-integration/policies/)** - Sample policies
- **[Kubernetes Manifests](../../../examples/gateway-integration/kubernetes/)** - K8s deployment files

### Community
- **GitHub Issues:** [Report bugs](https://github.com/your-org/sark/issues)
- **Discussions:** [Ask questions](https://github.com/your-org/sark/discussions)
- **Slack:** [Join community](https://sark-community.slack.com)

---

## Tutorial Development

These tutorials were designed with:

- **Hands-on approach** - Learn by doing, not just reading
- **Progressive complexity** - Each builds on previous knowledge
- **Production focus** - Real-world patterns and best practices
- **Comprehensive coverage** - Beginner to expert in one series
- **Quality assurance** - All code tested and verified

---

## Feedback

Help us improve these tutorials! If you:

- ✅ Found these tutorials helpful, star the repo
- 🐛 Encountered issues, open a GitHub issue
- 💡 Have suggestions, start a discussion
- 📝 Want to contribute, submit a PR

---

## License

These tutorials are part of the SARK project and follow the same license.

---

**Happy Learning!** 🚀

*Last Updated: 2025-01-15*
*Tutorial Series Version: 1.0*
*SARK Version: 1.1.0+*
