# SARK Learning Path

**Structured journey from beginner to expert in MCP governance**

---

## Choose Your Path

Select the learning track that matches your role and goals:

- **[Developer Track](#developer-track)** - Build MCP servers and integrate with SARK
- **[Operations Track](#operations-track)** - Deploy and manage SARK in production
- **[Security Track](#security-track)** - Configure policies and security controls
- **[User Track](#user-track)** - Use AI tools governed by SARK

---

## Developer Track

**Goal:** Build, register, and manage MCP servers with SARK governance

### Level 1: Fundamentals (2-3 hours)

#### Module 1.1: Understanding MCP (30 min)
**Learn:**
- What is Model Context Protocol
- Why MCP needs governance
- SARK's role in MCP ecosystem

**Resources:**
- [MCP Introduction](MCP_INTRODUCTION.md)
- [Official MCP Spec](https://modelcontextprotocol.io)

**Hands-On:**
- Read through example MCP server implementations
- Understand tool, resource, and prompt concepts

**Quiz:** Can you explain MCP to a colleague?

---

#### Module 1.2: SARK Basics (30 min)
**Learn:**
- SARK architecture overview
- Core components (API, OPA, audit)
- Authentication and authorization flow

**Resources:**
- [Architecture Guide](ARCHITECTURE.md)
- [Quick Start](QUICK_START.md)

**Hands-On:**
- Install SARK locally (see [5-Minute Guide](GETTING_STARTED_5MIN.md))
- Explore API documentation at `/docs`

**Quiz:** Can you describe SARK's main components?

---

#### Module 1.3: Your First MCP Server (1-2 hours)
**Learn:**
- MCP server structure
- Tool definition with JSON Schema
- Transport options (HTTP, stdio, SSE)

**Resources:**
- [Example Servers](../examples/)
- MCP SDK documentation

**Hands-On:**
- Build a simple "hello world" MCP server
- Define 2-3 basic tools
- Test locally with stdio transport

**Lab:**
```python
# Create: my_first_server.py
# Implement: greet(), add(), get_time() tools
# Run and test
```

**Checkpoint:** Working MCP server running locally

---

### Level 2: Integration (3-4 hours)

#### Module 2.1: Registering with SARK (30 min)
**Learn:**
- Server registration API
- Metadata requirements
- Health checks and heartbeats

**Resources:**
- [API Reference](API_REFERENCE.md) - Server endpoints

**Hands-On:**
- Register your server with local SARK
- Set sensitivity level and tags
- Test tool invocation through SARK

**Lab:**
```bash
# Register server via API
# Update server metadata
# Test tool call through SARK gateway
```

**Checkpoint:** Server registered and callable through SARK

---

#### Module 2.2: Authentication (1 hour)
**Learn:**
- API key authentication
- Token-based auth
- SARK session management

**Resources:**
- [Authentication Guide](AUTHENTICATION.md)
- [API Keys Guide](API_KEYS.md)

**Hands-On:**
- Generate API key in SARK
- Implement API key validation in your server
- Test authenticated tool calls

**Checkpoint:** Authenticated tool invocations working

---

#### Module 2.3: Tool Design Best Practices (1-2 hours)
**Learn:**
- Input validation with JSON Schema
- Error handling patterns
- Response formatting
- Security considerations

**Resources:**
- [Security Best Practices](SECURITY_BEST_PRACTICES.md)

**Hands-On:**
- Add input validation to your tools
- Implement proper error responses
- Add comprehensive tool descriptions

**Lab:**
- Refactor tools with validation
- Test error cases
- Document tool usage

**Checkpoint:** Production-quality tool implementations

---

#### Module 2.4: Advanced Tools (1 hour)
**Learn:**
- Database integration tools
- API integration tools
- File system tools
- Long-running operations

**Hands-On:**
- Build a database query tool
- Implement an external API call tool
- Handle async operations

**Checkpoint:** Real-world tools integrated

---

### Level 3: Production (2-3 hours)

#### Module 3.1: Tool Sensitivity (45 min)
**Learn:**
- Sensitivity levels (LOW, MEDIUM, HIGH, CRITICAL)
- Automatic classification
- Manual override

**Resources:**
- [Tool Sensitivity Classification](TOOL_SENSITIVITY_CLASSIFICATION.md)

**Hands-On:**
- Classify your tools by sensitivity
- Test SARK's automatic classification
- Override classifications as needed

**Checkpoint:** All tools properly classified

---

#### Module 3.2: Testing with SARK Policies (1 hour)
**Learn:**
- How OPA policies affect your tools
- Testing with different user roles
- Policy simulation

**Resources:**
- [OPA Policy Guide](OPA_POLICY_GUIDE.md)
- [Authorization Guide](AUTHORIZATION.md)

**Hands-On:**
- Test tools with developer role
- Test tools with analyst role
- Understand policy denials

**Checkpoint:** Tools tested against policies

---

#### Module 3.3: Monitoring & Debugging (1 hour)
**Learn:**
- Audit log analysis
- Tool usage metrics
- Debugging policy issues

**Resources:**
- [Monitoring Guide](MONITORING.md)

**Hands-On:**
- View audit logs for your tools
- Analyze tool usage patterns
- Debug a policy denial

**Checkpoint:** Can monitor and debug tool issues

---

### Level 4: Mastery (Ongoing)

#### Advanced Topics
- Custom transport implementations
- Streaming responses (SSE)
- Tool composition and chaining
- Performance optimization
- Load testing

**Resources:**
- [Performance Guide](PERFORMANCE.md)
- [Advanced Topics](#) (TBD)

---

## Operations Track

**Goal:** Deploy, configure, and operate SARK in production

### Level 1: Fundamentals (2 hours)

#### Module 1.1: SARK Architecture (45 min)
<!-- Content TBD -->

#### Module 1.2: Deployment Options (45 min)
<!-- Content TBD -->

#### Module 1.3: Local Setup (30 min)
<!-- Content TBD -->

---

### Level 2: Deployment (4-6 hours)

#### Module 2.1: Kubernetes Deployment (2 hours)
<!-- Content TBD -->

#### Module 2.2: Database Setup (1 hour)
<!-- Content TBD -->

#### Module 2.3: Authentication Configuration (1-2 hours)
<!-- Content TBD -->

#### Module 2.4: SIEM Integration (1 hour)
<!-- Content TBD -->

---

### Level 3: Operations (3-4 hours)

#### Module 3.1: Monitoring Setup (1 hour)
<!-- Content TBD -->

#### Module 3.2: Backup & Recovery (1 hour)
<!-- Content TBD -->

#### Module 3.3: Scaling & Performance (1-2 hours)
<!-- Content TBD -->

---

### Level 4: Mastery (Ongoing)

#### Advanced Topics
- Multi-region deployment
- Disaster recovery
- Cost optimization
- Capacity planning

---

## Security Track

**Goal:** Configure and maintain SARK security policies

### Level 1: Fundamentals (2 hours)

#### Module 1.1: OPA Basics (1 hour)
<!-- Content TBD -->

#### Module 1.2: SARK Policy Architecture (1 hour)
<!-- Content TBD -->

---

### Level 2: Policy Configuration (4-6 hours)

#### Module 2.1: Default Policies (1 hour)
<!-- Content TBD -->

#### Module 2.2: Writing Custom Policies (2-3 hours)
<!-- Content TBD -->

#### Module 2.3: Testing Policies (1 hour)
<!-- Content TBD -->

#### Module 2.4: Tool Sensitivity (1 hour)
<!-- Content TBD -->

---

### Level 3: Security Operations (3-4 hours)

#### Module 3.1: Audit Analysis (1 hour)
<!-- Content TBD -->

#### Module 3.2: Threat Detection (1-2 hours)
<!-- Content TBD -->

#### Module 3.3: Incident Response (1 hour)
<!-- Content TBD -->

---

### Level 4: Mastery (Ongoing)

#### Advanced Topics
- Advanced Rego patterns
- Policy optimization
- Compliance automation
- Security analytics

---

## User Track

**Goal:** Effectively use AI tools governed by SARK

### Level 1: Getting Started (1 hour)

#### Module 1.1: What is MCP? (15 min)
<!-- Content TBD -->

#### Module 1.2: Using AI with SARK (15 min)
<!-- Content TBD -->

#### Module 1.3: Available Tools (30 min)
<!-- Content TBD -->

---

### Level 2: Effective Usage (2 hours)

#### Module 2.1: Tool Discovery (30 min)
<!-- Content TBD -->

#### Module 2.2: Best Practices (1 hour)
<!-- Content TBD -->

#### Module 2.3: Troubleshooting (30 min)
<!-- Content TBD -->

---

## Learning Resources

### Documentation
- [MCP Introduction](MCP_INTRODUCTION.md)
- [API Reference](API_REFERENCE.md)
- [Architecture Guide](ARCHITECTURE.md)
- [Quick Start](QUICK_START.md)

### Code Examples
- [JWT Authentication](../examples/jwt_auth.py)
- [LDAP Integration](../examples/ldap_integration.py)
- [API Key Usage](../examples/api_key_usage.py)
- [Bulk Operations](../examples/bulk_operations.py)
- [Policy Evaluation](../examples/policy_evaluation.py)

### External Resources
- [Official MCP Specification](https://modelcontextprotocol.io)
- [OPA Documentation](https://www.openpolicyagent.org/docs)
- [Rego Playground](https://play.openpolicyagent.org)

---

## Certification Path (Future)

**SARK Certified Developer**
- Complete Developer Track Levels 1-3
- Build and deploy 3 production MCP servers
- Pass certification exam

**SARK Certified Operator**
- Complete Operations Track Levels 1-3
- Deploy SARK in production
- Pass certification exam

**SARK Certified Security Engineer**
- Complete Security Track Levels 1-3
- Implement custom policies
- Pass certification exam

---

## Getting Help

- **[FAQ](FAQ.md)** - Common questions
- **[Troubleshooting](TROUBLESHOOTING.md)** - Problem solving
- **GitHub Discussions** - Community support
- **Office Hours** - Weekly Q&A sessions (schedule TBD)

---

**Last Updated:** 2025-11-27
**Status:** Developer Track Level 1-3 content complete, other tracks in progress
