# MCP Flow Diagrams

This directory contains visual flow diagrams explaining key Model Context Protocol (MCP) operations in SARK.

## Available Diagrams

### 1. MCP Server Registration Flow
**File:** `mcp_server_registration_flow.svg`

Shows the complete flow when a developer registers a new MCP server:
- JWT token validation
- OPA authorization check
- Database persistence
- Audit logging
- Health check scheduling

**Key Components:** Developer, SARK API, Auth Service, OPA, PostgreSQL, Audit Service

---

### 2. MCP Tool Discovery & Invocation Flow
**File:** `mcp_tool_invocation_flow.svg`

Illustrates two phases:

**Phase 1 - Discovery:**
- How AI clients discover available tools
- Redis caching for performance
- Batch authorization via OPA
- Filtering by sensitivity level

**Phase 2 - Invocation:**
- Tool authorization checks
- Approval workflow (if required)
- MCP protocol communication
- Audit logging

**Key Components:** AI Client, SARK API, OPA, Redis Cache, PostgreSQL, MCP Server, Audit

---

### 3. MCP Authorization Flow with OPA
**File:** `mcp_authorization_flow.svg`

Demonstrates policy-based access control:
- OPA client integration
- Redis policy caching (95%+ hit rate)
- Rego policy evaluation
- Authorization decision factors
- Built-in policy types (RBAC, team-based, sensitivity-level)

**Includes:** Sample Rego policy code showing authorization rules

---

### 4. MCP Server Lifecycle Management
**File:** `mcp_lifecycle_management.svg`

Complete server state machine and operational flows:

**Server States:**
- REGISTERED → ACTIVE → INACTIVE → UNHEALTHY → DECOMMISSIONED

**Additional Information:**
- Health check process (every 60 seconds)
- State transition triggers
- Metrics and monitoring
- Alert conditions and auto-remediation
- Audit events

---

### 5. SARK Learning Path (Comprehensive)
**File:** `learning_path.svg`

Visual guide showing the complete learning journey from beginner to expert:

**4 Core Levels:**
- **Level 1 - Beginner** (2-3 hours): Quick start, register server, explore tools
- **Level 2 - Intermediate** (5-7 hours): Authentication, users, policies, monitoring
- **Level 3 - Advanced** (10-15 hours): Custom policies, SIEM, API integration, performance
- **Level 4 - Expert** (15-20 hours): Production deployment, security, DR, scale testing

**6 Specialization Tracks:**
- Policy Expert - Advanced Rego development
- DevOps Specialist - Infrastructure as Code, CI/CD
- Security Architect - Threat modeling, compliance
- Integration Engineer - API gateways, custom servers
- Performance Engineer - Optimization, benchmarking
- Data Analyst - Audit analysis, dashboards

**Total Time:** 32-45 hours base + 8-15 hours per specialization

---

### 6. SARK Learning Path (Simple)
**File:** `learning_path_simple.svg`

Simplified horizontal progression showing the 4-milestone learning journey:

**Milestones:**
1. **Beginner** - Get started (2-3 hours)
2. **Intermediate** - Build skills (5-7 hours)
3. **Advanced** - Master features (10-15 hours)
4. **Expert** - Production ready (15-20 hours)

Ideal for presentations and quick overviews.

---

## Using These Diagrams

These SVG diagrams can be:
- Embedded in documentation
- Viewed directly in browsers
- Included in presentations
- Referenced in training materials

All diagrams are self-contained SVG files with no external dependencies.

---

## Diagram Design Principles

1. **Clear Visual Hierarchy** - Color-coded states and components
2. **Sequential Flow** - Left-to-right or top-to-bottom reading
3. **Comprehensive Labels** - All transitions and decisions explained
4. **Context Annotations** - Notes provide additional details
5. **Legend Support** - Keys explain symbols and colors

---

## Color Coding

- **Blue (#3498db)** - Active processes and standard flows
- **Green (#2ecc71)** - Success states and health checks
- **Red (#e74c3c)** - Failure states and errors
- **Orange (#f39c12)** - Warning states (inactive, needs attention)
- **Purple (#9b59b6)** - OPA/policy evaluation
- **Gray (#95a5a6)** - Initial/registered state
- **Dark Gray (#34495e)** - Decommissioned/end state

---

## Related Documentation

- [ARCHITECTURE.md](../ARCHITECTURE.md) - Overall system architecture
- [API_REFERENCE.md](../API_REFERENCE.md) - API endpoint documentation
- [OPA_POLICY_GUIDE.md](../OPA_POLICY_GUIDE.md) - Policy development guide
- [MONITORING.md](../MONITORING.md) - Metrics and alerting
- [GLOSSARY.md](../GLOSSARY.md) - MCP terminology

---

**Created:** 2025-11
**Sessions:**
- Week 1, Session W1-E1-01: MCP flow diagrams (4 diagrams) ✅
- Week 2, Session W2-E1-01: Learning path graphics (2 diagrams) ✅
**Engineer:** Engineer 1 (Frontend Specialist)
**Status:** 6 diagrams complete ✅
