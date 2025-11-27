# SARK Tutorials

Hands-on tutorials to help you master SARK, from basic setup to advanced policy development.

## Learning Path

```
┌─────────────────────────────────────────────────────────────┐
│                      START HERE                              │
│  Tutorial 1: Basic Setup and First Tool Invocation          │
│  Duration: 15 minutes | Difficulty: Beginner                 │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────┐
│  Tutorial 2: Authentication Deep Dive (Coming Soon)         │
│  LDAP, OIDC, SAML, API Keys                                │
│  Duration: 20 minutes | Difficulty: Beginner                │
└────────────────┬───────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────┐
│  Tutorial 3: Policy Development (Coming Soon)               │
│  Write Rego policies, test, deploy                         │
│  Duration: 30 minutes | Difficulty: Intermediate            │
└────────────────┬───────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────┐
│  Tutorial 4: Production Deployment (Coming Soon)            │
│  Kubernetes, monitoring, operations                        │
│  Duration: 45 minutes | Difficulty: Advanced                │
└────────────────────────────────────────────────────────────┘
```

---

## Tutorial 1: Basic Setup and First Tool Invocation

**[Start Tutorial →](01-basic-setup/README.md)**

**What you'll learn:**
- Start SARK with minimal profile (5-minute setup)
- Authenticate with LDAP
- Register your first MCP server
- Invoke tools through SARK's governance layer
- View audit logs

**Prerequisites:**
- Docker 20.10+ and Docker Compose v2
- curl or HTTPie for API testing
- 15 minutes of time

**Perfect for:**
- New SARK users
- Developers evaluating SARK
- Quick proof-of-concept demos
- CI/CD pipeline testing

---

## Tutorial 2: Authentication Deep Dive

**Status:** Coming Soon

**What you'll learn:**
- LDAP authentication and user management
- OIDC authentication with Google/Okta/Auth0
- SAML 2.0 SSO integration
- API key creation and rotation
- Session management and token refresh
- Multi-factor authentication (MFA) requirements

**Prerequisites:**
- Completion of Tutorial 1
- OIDC provider account (optional)
- SAML IdP access (optional)

**Duration:** 20 minutes

---

## Tutorial 3: Policy Development

**Status:** Coming Soon

**What you'll learn:**
- Rego policy language basics
- Write custom OPA policies for SARK
- Time-based access control (business hours only)
- IP-based restrictions (corporate network only)
- MFA requirements for critical tools
- Parameter filtering and data masking
- Policy testing and validation
- Deploy policies to production

**Prerequisites:**
- Completion of Tutorials 1-2
- Text editor with Rego support (VS Code recommended)

**Duration:** 30 minutes

---

## Tutorial 4: Production Deployment

**Status:** Coming Soon

**What you'll learn:**
- Deploy SARK to Kubernetes with Helm
- Configure external PostgreSQL and Redis
- Set up Kong API Gateway
- Enable SIEM integration (Splunk, Datadog)
- Configure monitoring with Prometheus and Grafana
- Implement backup and disaster recovery
- Production security hardening
- Operational runbook procedures

**Prerequisites:**
- Completion of Tutorials 1-3
- Kubernetes cluster access
- Production environment (staging acceptable)

**Duration:** 45 minutes

---

## Quick Reference

### Tutorial Comparison

| Tutorial | Duration | Difficulty | Services Used | What You Learn |
|----------|----------|------------|---------------|----------------|
| **1. Basic Setup** | 15 min | Beginner | 4 (minimal) | Core SARK workflow |
| **2. Authentication** | 20 min | Beginner | 6 (w/ LDAP/OIDC) | All auth methods |
| **3. Policies** | 30 min | Intermediate | 4 (minimal) | Write Rego policies |
| **4. Production** | 45 min | Advanced | 12+ (full stack) | Deploy to K8s |

### Prerequisites by Tutorial

**All Tutorials Require:**
- Docker 20.10+ and Docker Compose v2
- Basic command line skills
- Text editor
- 8GB+ RAM available

**Additional Requirements:**

| Tutorial | Additional Prerequisites |
|----------|--------------------------|
| 1 | None |
| 2 | OIDC provider account (optional), SAML IdP (optional) |
| 3 | VS Code with OPA extension (recommended) |
| 4 | Kubernetes cluster, Helm 3+, kubectl |

---

## Getting Help

### Troubleshooting

Each tutorial includes a troubleshooting section. Common issues:

1. **Services won't start**
   ```bash
   docker compose ps
   docker compose logs
   docker compose --profile minimal down
   docker compose --profile minimal up -d
   ```

2. **Authentication fails**
   ```bash
   docker compose logs api
   docker compose logs openldap
   ```

3. **Policy denials**
   ```bash
   curl http://localhost:8181/health
   docker compose logs opa
   ```

### Additional Resources

- **[Quick Start Guide](../docs/QUICK_START.md)** - Comprehensive reference
- **[FAQ](../docs/FAQ.md)** - Common questions
- **[API Reference](../docs/API_REFERENCE.md)** - Complete API docs
- **[Architecture](../docs/ARCHITECTURE.md)** - System design
- **[Troubleshooting](../docs/TROUBLESHOOTING.md)** - Common issues

### Community Support

- **GitHub Issues:** https://github.com/apathy-ca/sark/issues
- **Documentation:** https://docs.sark.dev (coming soon)
- **Examples:** See `examples/` directory for runnable code

---

## Contributing Tutorials

Want to contribute a tutorial? We'd love your help!

**Tutorial Guidelines:**
- Hands-on and practical (no theory-only tutorials)
- 15-45 minutes in length
- Clear prerequisites and learning objectives
- Comprehensive troubleshooting section
- Tested on clean Docker environment
- Includes expected outputs for every command

**Suggested Topics:**
- Rate limiting and quota management
- SIEM integration (Splunk, Datadog, Elastic)
- Custom MCP server development
- Multi-tenancy and team isolation
- Approval workflows for critical operations
- Advanced Rego policy patterns

See [CONTRIBUTING.md](../CONTRIBUTING.md) for submission guidelines.

---

## Tutorial Completion Checklist

Track your progress through the SARK tutorials:

- [ ] **Tutorial 1:** Basic Setup ✅
  - [ ] Started SARK with minimal profile
  - [ ] Authenticated with LDAP
  - [ ] Registered MCP server
  - [ ] Invoked tools through SARK
  - [ ] Viewed audit logs

- [ ] **Tutorial 2:** Authentication (Coming Soon)
  - [ ] LDAP authentication
  - [ ] OIDC authentication
  - [ ] SAML SSO
  - [ ] API key management
  - [ ] Token refresh

- [ ] **Tutorial 3:** Policies (Coming Soon)
  - [ ] Written custom Rego policy
  - [ ] Tested policy locally
  - [ ] Deployed to SARK
  - [ ] Validated with real requests

- [ ] **Tutorial 4:** Production (Coming Soon)
  - [ ] Deployed to Kubernetes
  - [ ] Configured monitoring
  - [ ] Set up SIEM integration
  - [ ] Tested disaster recovery

**After completing all tutorials, you'll be ready to deploy and operate SARK in production!**

---

## Example Use Cases

Looking for real-world examples? Check out:

- **[examples/use_cases/](../examples/use_cases/)** - Complete MCP server specifications
  - Database query tool with governance
  - Ticketing system (Jira/ServiceNow)
  - Document search with RAG
  - Data analysis workflows

- **[examples/](../examples/)** - Runnable Python scripts
  - Basic tool invocation
  - Multi-tool workflows
  - Approval workflows
  - Error handling patterns

---

**Ready to start?** Begin with [Tutorial 1: Basic Setup →](01-basic-setup/README.md)
