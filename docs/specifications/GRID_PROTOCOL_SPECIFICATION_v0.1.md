# GRID Protocol Specification v0.1
## Governed Resource Interaction Definition

**A Universal Governance Protocol for Machine-to-Machine Interactions**

**Document Version:** 0.1 (Draft)
**Release Date:** November 27, 2025
**Status:** Draft for community review

---

## 1. Introduction

### 1.1 What is GRID?

**GRID (Governed Resource Interaction Definition)** is a universal governance protocol designed to regulate interactions between computational agents when one party seeks to access resources, invoke capabilities, or perform actions provided by another.

GRID is **protocol-agnostic**—it governs the governance layer above any interaction protocol (MCP, HTTP, gRPC, REST APIs, custom RPC, etc.). It provides a unified framework for:

- **Policy-based access control** across heterogeneous systems
- **Immutable audit trails** for compliance and forensics
- **Federated trust** where each organization runs their own governance node
- **Interoperable governance** even when different organizations use different protocols

Think of GRID like **BIND for DNS**: just as BIND is the reference implementation of the DNS protocol that made it interoperable, **SARK is the reference implementation of GRID** that proves the protocol works at enterprise scale.

### 1.2 Why Machine-to-Machine Interaction Needs Governance

Modern systems increasingly rely on automated interactions where one computational entity (a "principal") requests capabilities from another (a "resource provider"):

**Examples across industry and scale:**
- 🤖 **AI Agents & LLMs**: Claude, GPT-4, Llama using tools (MCP, function calling, LangChain)
- 🔗 **AI-to-AI Collaboration**: One AI agent delegating work to specialized AI systems
- 🔄 **Microservices**: Service A calling Service B's API
- 📱 **IoT & Robotics**: Devices requesting cloud resources or actions from infrastructure
- 🏭 **Autonomous Systems**: Robots, drones, autonomous vehicles accessing centralized resources
- 🔐 **API Ecosystems**: Applications accessing each other's capabilities

**Without governance:**
- ❌ No visibility into who/what is accessing what
- ❌ No enforcement of least-privilege access
- ❌ No audit trail for compliance (SOC 2, ISO 27001, GDPR, HIPAA)
- ❌ No protection against unauthorized access, data exfiltration, or misuse
- ❌ No ability to revoke access in real-time
- ❌ No federation across organization boundaries

**GRID solves this** by providing a standardized governance layer that works across any protocol, any organization, and any implementation.

### 1.3 Core Design Principles

1. **Protocol-Agnostic** - GRID governs governance, not protocol mechanics. It works above HTTP, gRPC, stdio, custom RPC, or any interaction model.

2. **Federated by Design** - Each organization/user runs their own GRID node. No central authority. Trust is established through federation protocols, not central servers.

3. **Policy-First** - Governance decisions are made through declarative policies (profiles), with programmatic escape hatches for complex scenarios.

4. **Zero-Trust by Default** - All interactions require explicit authorization. Default is "deny" unless a policy says otherwise.

5. **Immutable Audit** - Every interaction is logged immutably and forwarded to compliance systems in real-time.

6. **Agent-Agnostic** - Works for human users, AI agents, services, devices—any computational entity that makes requests.

7. **Interoperable** - Different GRID implementations should understand each other's policies and audit logs, even when governing different protocols.

8. **Performance-First** - Governance decisions at sub-5ms latency through intelligent caching and batching.

### 1.4 What GRID Does (and Doesn't Do)

**GRID Governs (Explicit Privilege Access):**
- ✅ Which principals can invoke which capabilities
- ✅ Under what conditions (time, location, sensitivity, context)
- ✅ With what constraints (rate limits, quotas, costs)
- ✅ Audit trail of what happened
- ✅ Real-time revocation and policy updates

**GRID Does NOT Govern (Internal Autonomy):**
- ❌ Internal reasoning or decision-making logic
- ❌ Private data processing within a system
- ❌ Autonomous actions within a system's scope
- ❌ Thoughts, memories, or internal state (for AI systems)

**Philosophical Foundation:**
> Access to shared resources and capabilities is a privilege, not a right. Internal processing and autonomous thought (for systems that have it) is a right, not a privilege. GRID exists at the boundary between systems, not within them.

### 1.5 Scope: GRID Protocol vs Implementations

**GRID Protocol** (this specification):
- Defines abstractions: Principal, Resource, Action, Policy, Audit
- Specifies policy evaluation semantics
- Defines trust model and federation
- Specifies audit format and retention
- Provides extension mechanisms

**GRID Implementations** (not in this spec, but reference implementations):
- **SARK**: Enterprise reference implementation with mandatory enforcement
- **YORI**: Home implementation with advisory/transparency focus (planned)
- Future community implementations

**GRID Adapters** (plug into implementations):
- **MCP Adapter**: How to map MCP concepts to GRID abstractions
- **HTTP Adapter**: How to govern HTTP APIs, REST services
- **gRPC Adapter**: How to govern gRPC service-to-service calls
- **OpenAI Adapter**: How to govern OpenAI function calling
- **Custom Adapters**: How to build adapters for proprietary protocols

---

## 2. Core Abstractions

GRID is built on five core abstractions that work across all protocols:

### 2.1 Principal

A **Principal** is any entity that makes a request to access a resource or invoke a capability.

**Principal Types:**
- **Human Users** - People accessing systems (often via applications)
- **AI Agents** - Autonomous or semi-autonomous AI systems (Claude, GPT-4, custom models)
- **Services/Microservices** - Software services making requests to other services
- **IoT Devices** - Physical devices requesting cloud resources or actions
- **Robots/Autonomous Systems** - Autonomous physical systems accessing shared resources

**Principal Properties:**
```
Principal {
  id: string              # Unique identifier (UUID, email, service name)
  type: PrincipalType     # human, agent, service, device
  identity_token: string  # JWT, API key, certificate

  # For policy evaluation
  attributes: {
    role: string          # admin, developer, viewer, service
    teams: [string]       # Team memberships
    attributes: {         # Custom attributes for ABAC
      department: string
      clearance_level: string
      region: string
      ...
    }
  }

  # Metadata
  created_at: timestamp
  revoked_at: timestamp   # nil if active
}
```

**Examples:**
```
# Human user
Principal {
  id: "alice@company.com"
  type: "human"
  attributes: {
    role: "developer"
    teams: ["backend", "security"]
    department: "Engineering"
  }
}

# AI Agent
Principal {
  id: "agent-copilot-prod"
  type: "agent"
  attributes: {
    role: "service"
    teams: ["ai-systems"]
    model: "claude-opus"
  }
}

# Service Account
Principal {
  id: "svc-payment-processor"
  type: "service"
  attributes: {
    role: "service"
    teams: ["payments"]
  }
}

# IoT Device
Principal {
  id: "device-sensor-001"
  type: "device"
  attributes: {
    role: "sensor"
    region: "us-west-2"
    factory: "factory-a"
  }
}
```

### 2.2 Resource

A **Resource** is any capability, data, service, or functionality that a principal might want to access.

**Resource Types:**
- **Tools** - Invocable capabilities (functions, endpoints)
- **Data** - Information that can be queried or accessed
- **Services** - Computational services (microservices, APIs)
- **Infrastructure** - Physical or cloud infrastructure resources
- **Devices** - Physical devices (IoT, robots, etc.)

**Resource Properties:**
```
Resource {
  id: string                    # Unique identifier
  name: string                  # Human-readable name
  type: ResourceType            # tool, data, service, device
  provider_id: string           # Who provides this resource

  # Classification
  sensitivity_level: Level      # low, medium, high, critical
  classification: string        # Public, Internal, Confidential, Secret

  # Capability metadata
  capabilities: [string]        # What can be done with this resource
  parameters_schema: JSON       # Input validation schema

  # Access metadata
  owner: Principal              # Who owns/manages this resource
  managers: [Principal]         # Who can modify this resource

  metadata: {
    tags: [string]
    custom_attributes: {}
  }
}
```

**Examples:**
```
# MCP Tool
Resource {
  id: "mcp-jira-query"
  name: "jira.search"
  type: "tool"
  provider_id: "jira-server-1"
  sensitivity_level: "medium"
  capabilities: ["query", "read"]
  parameters_schema: {
    "type": "object",
    "properties": {
      "jql": {"type": "string", "description": "JQL query"}
    }
  }
}

# Database
Resource {
  id: "postgres-prod-db"
  name: "production_database"
  type: "data"
  sensitivity_level: "critical"
  capabilities: ["read", "write"]
  owner: "database-team"
}

# REST API Endpoint
Resource {
  id: "api-payment-gateway"
  name: "/api/payments/process"
  type: "service"
  sensitivity_level: "critical"
  capabilities: ["invoke"]
}

# IoT Device
Resource {
  id: "device-factory-arm-1"
  name: "Robotic Arm #1"
  type: "device"
  sensitivity_level: "high"
  capabilities: ["control", "monitor"]
}
```

### 2.3 Action

An **Action** is the operation a principal wants to perform on a resource.

**Action Types:**
- **Read** - Access information (query, search, retrieve)
- **Write** - Modify information (create, update, delete)
- **Execute** - Run a capability (invoke tool, trigger process)
- **Control** - Change behavior (start, stop, reconfigure)
- **Manage** - Change governance (grant access, revoke, update policy)
- **Audit** - Access audit logs or compliance data

**Action Representation:**
```
Action {
  resource_id: string          # What resource
  operation: string            # read, write, execute, control, manage, audit

  # Additional context
  parameters: object           # What parameters (for analysis/filtering)
  context: {
    timestamp: datetime        # When
    ip_address: string         # From where
    user_agent: string         # Via what
    request_id: string         # Request identifier
    environment: string        # dev, staging, prod
  }
}
```

**Examples:**
```
# Tool invocation
Action {
  resource_id: "mcp-jira-query"
  operation: "execute"
  parameters: {"jql": "project = PROJ AND status = 'In Progress'"}
}

# Database query
Action {
  resource_id: "postgres-prod-db"
  operation: "read"
  parameters: {"table": "users", "columns": ["id", "name"]}
}

# API call
Action {
  resource_id: "api-payment-gateway"
  operation: "execute"
  parameters: {"amount": 100.00, "currency": "USD"}
}

# Audit log access
Action {
  resource_id: "audit-logs"
  operation: "audit"
  parameters: {"date_range": ["2025-01-01", "2025-11-27"]}
}
```

### 2.4 Policy

A **Policy** is a set of rules that determine whether an action is permitted.

**Policy Elements:**
```
Policy {
  id: string                   # Unique identifier
  name: string                 # Human-readable name
  status: PolicyStatus         # active, draft, deprecated
  type: PolicyType             # authorization, validation, transformation

  # The rules
  rules: [Rule]                # Conditions and outcomes
  version: integer             # Version number for tracking changes

  # Metadata
  created_by: Principal        # Who created it
  created_at: timestamp
  last_updated: timestamp
}

Rule {
  # Conditions
  principals: [PrincipalMatcher]       # Who does this apply to?
  resources: [ResourceMatcher]         # What resources?
  actions: [ActionMatcher]             # What operations?
  conditions: [Condition]              # Under what circumstances?

  # Effects and constraints
  effect: Effect                       # allow or deny
  constraints: [Constraint]            # Rate limits, quotas, costs

  # Context
  priority: integer                    # Evaluation order
  metadata: {}                         # Custom metadata
}

# Matcher examples (can be exact match, pattern, or set membership)
PrincipalMatcher {
  type: string                 # exact, role, team, attribute
  value: string | [string]     # Matched value(s)
}

ResourceMatcher {
  type: string                 # exact, type, sensitivity, tag
  value: string | [string]     # Matched value(s)
}

ActionMatcher {
  type: string                 # exact, any
  value: string | [string]     # Matched value(s)
}

Condition {
  type: string                 # time, location, context, custom
  operator: string             # equals, in, range, between, custom
  value: mixed
}

Constraint {
  type: string                 # rate_limit, quota, cost, approval
  value: mixed
}
```

**Effect Semantics:**
- **Allow** - Grant access if all conditions are met
- **Deny** - Explicitly deny access (overrides allow)
- **Conditional Allow** - Grant access but apply constraints

### 2.5 Audit

An **Audit** event is an immutable record of an interaction (whether allowed or denied).

**Audit Event:**
```
AuditEvent {
  # Identification
  id: string                   # Unique event identifier
  timestamp: datetime          # When it happened (UTC)
  request_id: string           # Request identifier for correlation

  # Actor and action
  principal: Principal         # Who made the request
  action: Action               # What they tried to do
  resource: Resource           # What they accessed

  # Decision
  decision: Decision           # allow, deny, error
  reason: string               # Why (policy reason, error message)
  policy_id: string            # Which policy decided this

  # Context
  context: {
    ip_address: string
    user_agent: string
    environment: string        # dev, staging, prod
    request_metadata: {}
  }

  # Outcome
  success: boolean             # Did the action succeed?
  error: string                # null if successful

  # Extended metadata
  sensitivity_level: Level     # low, medium, high, critical
  cost: decimal                # Cost attributed (if applicable)
  metadata: {}                 # Custom metadata

  # Compliance
  forwarded_to_siem: timestamp # When sent to SIEM
  retention_until: timestamp   # Compliance-driven retention
}
```

**Audit Event Examples:**

```json
{
  "id": "event-001",
  "timestamp": "2025-11-27T19:45:00Z",
  "principal": {
    "id": "alice@company.com",
    "type": "human"
  },
  "action": {
    "resource_id": "mcp-jira-query",
    "operation": "execute",
    "parameters": {"jql": "project = PROJ"}
  },
  "decision": "allow",
  "reason": "Developer role has access to medium sensitivity tools",
  "context": {
    "ip_address": "10.1.2.3",
    "environment": "production"
  }
}
```

```json
{
  "id": "event-002",
  "timestamp": "2025-11-27T23:00:00Z",
  "principal": {
    "id": "bob@company.com",
    "type": "human"
  },
  "action": {
    "resource_id": "postgres-prod-db",
    "operation": "write",
    "parameters": {"table": "users"}
  },
  "decision": "deny",
  "reason": "Critical sensitivity database access denied outside work hours",
  "context": {
    "ip_address": "192.168.1.100",
    "environment": "production"
  },
  "sensitivity_level": "critical"
}
```

---

## 3. Architecture

### 3.1 Reference Architecture

GRID is implemented as a governance layer that sits between principals and resource providers:

```
┌────────────────────────────────────────────────────────────────┐
│ PRINCIPALS (Requesters)                                        │
│ ├── Users (via applications)                                   │
│ ├── AI Agents                                                  │
│ ├── Services/Microservices                                     │
│ └── Devices/Autonomous Systems                                 │
└────────────────────────────────────────────────────────────────┘
                            ↓ HTTP/gRPC/Custom
┌────────────────────────────────────────────────────────────────┐
│ GRID GOVERNANCE LAYER (Authorization, Audit, Policy)          │
│                                                                │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ 1. AUTHENTICATION (Validate Identity)                   │ │
│ │    - JWT validation                                     │ │
│ │    - API key validation                                 │ │
│ │    - Certificate validation                             │ │
│ └──────────────────────────────────────────────────────────┘ │
│                            ↓                                   │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ 2. POLICY EVALUATION (Is it allowed?)                   │ │
│ │    - Extract principal context                          │ │
│ │    - Check policy cache (L1: Distributed, L2: Local)   │ │
│ │    - If miss: Evaluate policy engine (OPA/Cedar/etc)   │ │
│ │    - Cache result with sensitivity-based TTL            │ │
│ └──────────────────────────────────────────────────────────┘ │
│                            ↓                                   │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ 3. AUDIT LOGGING (Record what happened)                 │ │
│ │    - Create audit event                                 │ │
│ │    - Store immutably (INSERT-ONLY database)            │ │
│ │    - Async forward to SIEM (non-blocking)               │ │
│ └──────────────────────────────────────────────────────────┘ │
│                            ↓                                   │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ 4. ENFORCEMENT (Execute or Deny)                        │ │
│ │    - If allow: Proceed to resource provider              │ │
│ │    - If deny: Return 403 with reason                     │ │
│ └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
                            ↓ Authorized
┌────────────────────────────────────────────────────────────────┐
│ RESOURCE PROVIDERS                                             │
│ ├── MCP Servers                                               │
│ ├── REST APIs                                                 │
│ ├── gRPC Services                                              │
│ ├── Databases                                                 │
│ └── Custom Services                                           │
└────────────────────────────────────────────────────────────────┘
```

### 3.2 Component Roles

**Principal Management:**
- Register and maintain principal identities
- Track principal attributes and group memberships
- Manage principal lifecycle (creation, revocation, updates)

**Resource Discovery & Registry:**
- Catalog all available resources
- Track resource capabilities and constraints
- Maintain resource sensitivity classification
- Support dynamic resource registration

**Authentication:**
- Validate principal identity and extract context
- Support multiple authentication methods
- Issue and manage tokens/sessions
- Handle token refresh and revocation

**Policy Engine:**
- Evaluate declarative and programmatic policies
- Support multiple policy languages (Rego, Cedar, etc.)
- Cache decisions for performance
- Support policy versioning and rollback

**Audit & Compliance:**
- Log all interactions immutably
- Forward to SIEM systems in real-time
- Support audit log queries and exports
- Enforce retention policies

**Enforcement:**
- Block unauthorized access
- Apply rate limits and quotas
- Implement circuit breakers for failing services
- Graceful degradation without security compromise

### 3.3 Request/Response Flow

**Happy Path (Access Allowed):**

```
1. PRINCIPAL REQUEST
   Principal → HTTP POST /invoke
   {
     "principal_id": "alice@company.com",
     "resource_id": "mcp-jira-query",
     "action": "execute",
     "parameters": {"jql": "project = PROJ"}
   }

2. AUTHENTICATION
   - Validate JWT token signature
   - Extract principal context (id, role, teams)
   - Verify token not expired/revoked
   ✓ Authenticated as: alice@company.com (developer)

3. POLICY EVALUATION (cached lookup)
   - Key: principal=alice, resource=mcp-jira-query, action=execute
   - L1 Cache Hit (Redis): Decision = ALLOW
   - <5ms latency
   ✓ Decision: ALLOW (Developer can access medium sensitivity tools)

4. AUDIT LOGGING
   - Create event: {principal, action, resource, decision=allow}
   - Store to audit table (non-blocking, <1ms)
   - Async queue to SIEM (background task)
   ✓ Logged to immutable trail

5. ENFORCEMENT
   - Return 200 OK to principal
   - Principal invokes resource provider
   ✓ Access granted

6. SIEM FORWARDING (async, non-blocking)
   - Background task dequeues event
   - Sends to Splunk/Datadog
   - Updates compliance dashboard
   ✓ Forwarded
```

**Failure Path (Access Denied):**

```
1. PRINCIPAL REQUEST
   Principal → HTTP POST /invoke
   {
     "principal_id": "bob@company.com",
     "resource_id": "postgres-prod-db",
     "action": "write",
     "parameters": {"table": "users"}
   }

2. AUTHENTICATION
   ✓ Authenticated as: bob@company.com (viewer)

3. POLICY EVALUATION (miss→engine)
   - Key: principal=bob, resource=postgres-prod-db, action=write
   - Cache miss (policy not recently checked)
   - Query policy engine: "Can viewer write to critical database?"
   - Policy engine: NO (denied by sensitivity policy)
   ✓ Decision: DENY (Viewers cannot write to critical resources)

4. AUDIT LOGGING
   - Create event: {principal, action, resource, decision=deny, reason}
   - Store to audit table
   - High severity → immediate SIEM forward
   ✓ Logged as HIGH severity

5. ENFORCEMENT
   - Return 403 Forbidden to principal
   ```json
   {
     "error": "Access denied",
     "reason": "Viewers cannot write to critical sensitivity resources",
     "audit_id": "event-123"
   }
   ```
   ✓ Access denied

6. MONITORING
   - Alert triggered for denied access to critical resource
   - Security team notified
   ✓ Monitored
```

### 3.4 Federation Model

GRID supports federated governance where different organizations run independent GRID nodes:

```
┌──────────────────────────┐
│ Organization A           │
│ ┌────────────────────┐   │
│ │ GRID Node A        │   │
│ │ - Policy Engine    │   │
│ │ - Audit Logs       │   │
│ │ - Resource Catalog │   │
│ └────────────────────┘   │
└──────────────────────────┘
         ↓ Trust Established
    (Federation Protocol)
         ↓
┌──────────────────────────┐
│ Organization B           │
│ ┌────────────────────┐   │
│ │ GRID Node B        │   │
│ │ - Policy Engine    │   │
│ │ - Audit Logs       │   │
│ │ - Resource Catalog │   │
│ └────────────────────┘   │
└──────────────────────────┘
```

**Federation Capabilities:**
- ✅ Cross-org policy evaluation (Org A's principal accessing Org B's resource)
- ✅ Trust establishment (X.509 certificates, mutual TLS)
- ✅ Policy exchange (Share policies across federated nodes)
- ✅ Audit correlation (Link audit events across organizations)
- ✅ Principal lookup (Resolve principals across boundaries)

**Federation Use Cases:**
- B2B API access (Company A's service accessing Company B's API)
- Multi-tenant SaaS (One SaaS instance in Org A, customers in Org B)
- Cross-org AI collaboration (Org A's agent requesting Org B's AI service)
- Partner integrations (Trusted partners accessing resources)

---

## 4. Profiles: Enterprise vs Home

GRID defines two profiles for different deployment contexts:

### 4.1 GRID-Enterprise Profile

**Target:** Enterprise, regulated, multi-user, high-trust environments

**Mandatory Features:**
- ✅ Authentication required (MUST validate all requests)
- ✅ Zero-trust authorization (default deny)
- ✅ Immutable audit logs (INSERT-ONLY, tamper-proof)
- ✅ SIEM forwarding (real-time compliance integration)
- ✅ Policy versioning (track all policy changes)
- ✅ Role-based access control (RBAC minimum)
- ✅ Rate limiting (quota enforcement)
- ✅ Encryption in transit (TLS 1.2+)

**Security Requirements:**
- Multi-layer authentication (MFA recommended)
- Separate read/write audit access
- Regular security audits
- Incident response procedures

**Reference Implementation:** SARK

### 4.2 GRID-Home Profile

**Target:** Home users, open-source projects, advisory governance, transparency-first

**Recommended Features:**
- ✅ Authentication supported (not mandatory)
- ✅ Advisory policies (logging, auditing, and recommendations, not enforcement)
- ⚠️ Semi-immutable audit (append-only with governance)
- ⚠️ Optional SIEM (advisory logging)
- ⚠️ Simple policies (rule-based or declarative)
- ⚠️ User-friendly configuration

**Flexibility:**
- May allow override of policies with audited approval
- Simpler authentication (bearer tokens, passwordless)
- Focus on transparency over enforcement
- Community-driven policies

**Reference Implementation:** YORI (planned)

**Comparison:**

| Feature | Enterprise | Home |
|---------|-----------|------|
| Authentication | MUST | Recommended |
| Authorization | Mandatory | Advisory |
| Audit | Immutable | Append-only |
| SIEM | Required | Optional |
| Policy Override | Forbidden | Audited approval |
| Multi-layer Security | Required | Optional |
| Use Case | Regulated orgs | Individual/OSS |

---

## 5. Policy Language & Evaluation

### 5.1 Declarative Policy Model (Recommended)

GRID recommends a declarative policy language that is:
- **Human-readable** (non-technical stakeholders can understand)
- **Versionable** (track all changes)
- **Testable** (validate policies before deployment)
- **Cache-friendly** (deterministic evaluation)

**Example: Rego (Open Policy Agent)**

SARK uses **Rego**, an open-source declarative language:

```rego
package grid.authorization

# Default deny
default allow := false

# Allow admins full access
allow if {
    input.principal.attributes.role == "admin"
}

# Allow developers to execute tools with low/medium sensitivity
allow if {
    input.principal.attributes.role == "developer"
    input.action.operation == "execute"
    input.resource.sensitivity_level in ["low", "medium"]
    is_work_hours
}

# Allow team members to access their team's resources
allow if {
    some team_id in input.principal.attributes.teams
    team_id in input.resource.managers
}

# Deny access to critical resources outside work hours
deny if {
    input.resource.sensitivity_level == "critical"
    not is_work_hours
}

# Helper function
is_work_hours if {
    hour := time.clock([input.context.timestamp])[0]
    hour >= 9
    hour < 18
    day := time.weekday(input.context.timestamp)
    day not in [0, 6]  # not Saturday or Sunday
}
```

**Policy Elements:**

```
Policy {
  # Rules (if-then statements)
  - Conditions (who, what, when, where)
  - Effect (allow, deny, constraint)

  # Matchers
  - Principal: exact, role, team, attribute match
  - Resource: exact, type, sensitivity, tag match
  - Action: exact match, wildcard

  # Constraints
  - Rate limits (N requests per time period)
  - Quotas (Maximum actions per day/month)
  - Approval requirements (Need human sign-off)
  - Cost limits (Maximum spend per day)
}
```

### 5.2 Policy Examples (Multi-Protocol)

**Example 1: RBAC (Role-Based Access Control)**

```rego
# All developers can execute non-critical tools
allow if {
    input.principal.attributes.role == "developer"
    input.action.operation == "execute"
    input.resource.sensitivity_level in ["low", "medium"]
}

# Viewers can only read
allow if {
    input.principal.attributes.role == "viewer"
    input.action.operation == "read"
}

# Admins can do anything
allow if {
    input.principal.attributes.role == "admin"
}
```

**Example 2: Team-Based Access**

```rego
# Backend team members can access backend resources
allow if {
    "backend" in input.principal.attributes.teams
    "backend" in input.resource.managers
    input.action.operation in ["execute", "read"]
}

# Only security team can modify security policies
allow if {
    "security" in input.principal.attributes.teams
    input.resource.type == "policy"
    input.action.operation == "write"
}
```

**Example 3: Sensitivity-Level Based**

```rego
# Low sensitivity: anyone can access
allow if {
    input.resource.sensitivity_level == "low"
}

# Medium sensitivity: authenticated users
allow if {
    input.principal.id != null  # Must be authenticated
    input.resource.sensitivity_level == "medium"
}

# High sensitivity: authenticated + cleared
allow if {
    input.principal.id != null
    input.principal.attributes.clearance_level in ["high", "critical"]
    input.resource.sensitivity_level == "high"
}

# Critical sensitivity: admin only, work hours only
allow if {
    input.principal.attributes.role == "admin"
    input.resource.sensitivity_level == "critical"
    is_work_hours
}
```

**Example 4: Time-Based Restrictions**

```rego
# Business hours access
allow if {
    input.resource.sensitivity_level in ["low", "medium"]
    is_business_hours(input.context.timestamp)
}

# Critical resources: admin only outside business hours
deny if {
    input.resource.sensitivity_level == "critical"
    not is_business_hours(input.context.timestamp)
    input.principal.attributes.role != "admin"
}

is_business_hours(ts) if {
    hour := time.clock([ts])[0]
    hour >= 9
    hour < 18
    day := time.weekday(ts)
    day not in [0, 6]  # Mon-Fri
}
```

**Example 5: Multi-Protocol Access (HTTP, gRPC, MCP)**

```rego
# Same policy applies regardless of protocol
allow if {
    input.principal.attributes.role == "developer"
    input.action.operation == "read"
    input.resource.sensitivity_level in ["low", "medium"]
}

# Rate limits apply per protocol
#constraint if {
#    input.context.protocol == "http"
#    rate_limit := {"requests_per_hour": 1000}
#}
```

### 5.3 Programmatic Policy (Escape Hatch)

For complex scenarios, GRID supports programmatic policies that can execute arbitrary logic:

```python
class ComplexPolicy:
    """Policy that requires custom logic."""

    def evaluate(self, input: PolicyInput) -> PolicyDecision:
        """Evaluate complex authorization logic."""

        # Example: Machine learning-based anomaly detection
        if self.is_anomalous(input):
            return PolicyDecision.DENY("Anomalous access pattern detected")

        # Example: Cost-based access control
        if self.estimate_cost(input) > self.daily_budget(input.principal):
            return PolicyDecision.DENY("Cost limit exceeded")

        # Example: Dynamic rate limiting
        current_rate = self.get_current_rate(input.principal)
        if current_rate > self.get_rate_limit(input.principal):
            return PolicyDecision.DENY("Rate limit exceeded")

        return PolicyDecision.ALLOW("Custom policy approved")

    def is_anomalous(self, input: PolicyInput) -> bool:
        """Detect anomalous patterns."""
        pass

    def estimate_cost(self, input: PolicyInput) -> float:
        """Estimate operation cost."""
        pass
```

### 5.4 Policy Evaluation Process

**Deterministic Evaluation Order:**

```
1. LOAD POLICIES
   - Fetch active policies from policy engine
   - Order by priority (explicit ordering)

2. EVALUATE EACH POLICY
   For each policy:
   a. Match principal (role, teams, attributes)
   b. Match resource (type, sensitivity, tags)
   c. Match action (operation, parameters)
   d. Evaluate conditions (time, context, custom)

   If all matchers pass:
   - Return effect (ALLOW, DENY, CONSTRAIN)
   - Return reason and constraints

3. CONFLICT RESOLUTION
   - Deny overrides Allow (fail-safe)
   - If multiple rules match: explicit order
   - If multiple policies: alphabetical/priority order

4. APPLY CONSTRAINTS
   - Rate limits
   - Quotas
   - Approval requirements
   - Cost limits

5. CACHE DECISION
   - Store decision with sensitivity-based TTL
   - Key: {principal_id}:{resource_id}:{action}:{context_hash}
   - Low sensitivity: 600s TTL
   - Critical: 30s TTL
```

**Pseudo-Code Evaluation:**

```python
def evaluate_policy(principal, action, resource, context):
    # Check cache first (L1: Distributed, L2: Local)
    cache_key = hash(principal.id, resource.id, action.operation)
    cached_decision = policy_cache.get(cache_key)
    if cached_decision and not cached_decision.expired():
        return cached_decision

    # Query policy engine (OPA, Cedar, or custom)
    decision = policy_engine.evaluate({
        "principal": principal,
        "action": action,
        "resource": resource,
        "context": context
    })

    # Determine TTL based on sensitivity
    ttl = {
        "low": 600,      # 10 minutes
        "medium": 300,   # 5 minutes
        "high": 60,      # 1 minute
        "critical": 30   # 30 seconds
    }[resource.sensitivity_level]

    # Cache the decision
    policy_cache.set(cache_key, decision, ttl=ttl)

    return decision
```

---

## 6. Trust and Security Model

### 6.1 Trust Levels

GRID defines explicit trust levels that policies can reference:

**Level 1: Advisory (Recommendations)**
- Suggested access rules
- Can be overridden (with audit trail)
- No enforcement
- Use case: Home profile, open-source projects

**Level 2: Sandbox (Restricted Execution)**
- Limited access within controlled environments
- Failed requests don't cascade
- Circuit breakers prevent damage
- Use case: Untrusted services, beta features

**Level 3: Trusted (Enforced)**
- Full enforcement of policies
- Zero-trust verification
- Real-time monitoring
- Use case: Enterprise, regulated environments

**Assignment:**
```
Trust Level := function of (
  Principal Type,      # human, agent, service, device
  Principal History,   # Behavior over time, incident history
  Resource Sensitivity # low, medium, high, critical
)

Examples:
- New service account → Sandbox (Level 2)
- Established developer → Trusted (Level 3)
- Unknown external agent → Advisory (Level 1)
- Untrusted third-party API → Sandbox (Level 2)
```

### 6.2 Resource Provider Registration & Verification

**Registration Process:**

```
1. DISCOVERY
   - Service registry scan (Consul, Kubernetes, etc.)
   - Manual registration via API
   - Auto-discovery via protocol-specific mechanisms

2. REGISTRATION REQUEST
   POST /api/v1/register-resource
   {
     "name": "analytics-server",
     "type": "service",
     "transport": "http",
     "endpoint": "https://analytics.example.com",
     "capabilities": ["query", "analyze"],
     "sensitivity_level": "medium",
     "owner": "analytics-team@company.com",
     "signature": "-----BEGIN CERTIFICATE-----..."
   }

3. VERIFICATION
   - Validate transport connectivity (health check)
   - Verify ownership/domain control
   - Check certificate validity (if provided)
   - Scan for known vulnerabilities
   - Verify capability declarations

4. APPROVAL
   - Security team reviews (if required by policy)
   - Creates approval audit event
   - Resource marked as APPROVED

5. ACTIVATION
   - Resource added to catalog
   - Registered in service discovery
   - Policies can now reference it
```

**Capability Declaration:**

```
Resource capabilities are declared at registration:

POST /api/v1/register-resource
{
  "capabilities": [
    {
      "name": "query",
      "sensitivity_level": "medium",
      "parameters": {
        "type": "object",
        "properties": {
          "table": {"type": "string"},
          "columns": {"type": "array"}
        },
        "required": ["table"]
      },
      "requires_approval": false
    },
    {
      "name": "delete",
      "sensitivity_level": "critical",
      "parameters": {
        "type": "object",
        "properties": {
          "table": {"type": "string"},
          "id": {"type": "string"}
        }
      },
      "requires_approval": true  # Needs explicit approval
    }
  ]
}
```

### 6.3 Identity and Authentication

**Authentication Methods:**

| Method | Protocol | Use Case | Token Type |
|--------|----------|----------|-----------|
| **OIDC** | OAuth 2.0 PKCE | Human users | JWT (session) |
| **LDAP** | BIND | Enterprise users | JWT (generated) |
| **SAML** | Assertion | Enterprise SSO | JWT (generated) |
| **API Key** | Custom | Services/devices | Bearer token |
| **mTLS** | X.509 | Service-to-service | Certificate |
| **JWT** | Custom | Token exchange | Pre-issued JWT |

**Authentication Flow (OIDC Example):**

```
1. PRINCIPAL → Browser: /api/authorize?client_id=...
2. Browser → OIDC Provider: Login request
3. OIDC Provider → Browser: "Please sign in"
4. User → OIDC Provider: Username + password (or MFA)
5. OIDC Provider → Browser: Authorization code
6. Browser → SARK: /callback?code=...
7. SARK Backend → OIDC Provider: Exchange code for token
8. OIDC Provider → SARK Backend: ID token + access token
9. SARK → Browser: Session cookie (contains JWT)
10. Browser → SARK: /api/invoke (with JWT in header)
11. SARK: Validate JWT signature, extract context
    ✓ Authenticated as alice@company.com
```

**JWT Payload (Example):**

```json
{
  "sub": "alice@company.com",
  "iss": "https://sso.company.com",
  "aud": "sark-gateway",
  "role": "developer",
  "teams": ["backend", "security"],
  "attributes": {
    "department": "Engineering",
    "clearance_level": "high",
    "region": "us-west-2"
  },
  "iat": 1700000000,
  "exp": 1700003600
}
```

### 6.4 Authorization & Delegation

**Authorization Boundary:**

```
Request Arrives
  ↓
Is principal authenticated? YES/NO
  ├─ NO → Return 401 Unauthorized
  └─ YES ↓
Is action on resource authorized? YES/NO/CONSTRAIN
  ├─ NO → Return 403 Forbidden
  ├─ CONSTRAIN → Apply constraints, return 200
  └─ YES ↓
Apply rate limits? OK/EXCEEDED
  ├─ EXCEEDED → Return 429 Too Many Requests
  └─ OK ↓
Forward to resource provider
```

**Delegation Patterns:**

**User → AI Agent:**
```
Policy: User can delegate to agents within scope

Example: Alice (developer) → Claude (AI agent)
- Alice authenticates as herself
- Invokes via AI agent (service account)
- AI agent makes request on Alice's behalf
- Audit logs: principal=alice, actor=claude-agent, action=X

Constraint: AI agent can only perform actions Alice can perform
- AI agent inherits Alice's permissions
- But bounded by AI agent's own policies
- Result: intersection of policies
```

**AI Agent → AI Agent (Cross-System Collaboration):**
```
Policy: Agent A can delegate to Agent B

Example: Agent A (internal) → Agent B (external/partner)
- Agent A authenticates with API key
- Invokes Agent B's service
- Agent B evaluates: Is Agent A authorized?
- If yes: Agent B performs action on behalf of Agent A

Constraint: Agent A can only delegate actions within its permissions
- Prevents privilege escalation
- Audit chain follows delegation path
```

**Service → Service (Microservices):**
```
Policy: Service A can call Service B

Example: Payment Service → Database Service
- Payment Service authenticates (mTLS certificate)
- Calls: GET /api/v1/transactions?customer_id=123
- Database Service evaluates: Is Payment Service authorized?
- Enforces: Only read access, limited to customer data
- Audit logs both call and outcome
```

---

## 7. Audit and Compliance

### 7.1 Required Audit Fields (Universal)

Every GRID-compliant implementation MUST log these fields:

```
Core Audit Event:
├── Temporal
│   ├── timestamp (UTC)        # When it happened
│   ├── request_id             # Request identifier for correlation
│   └── duration               # How long it took
├── Actors
│   ├── principal_id           # Who made the request
│   ├── principal_type         # human, agent, service, device
│   └── principal_attributes   # Role, teams, relevant attributes
├── Action & Resource
│   ├── resource_id            # What was accessed
│   ├── resource_type          # tool, data, service, device
│   ├── action_operation       # read, write, execute, control
│   └── action_parameters      # What parameters (sanitized)
├── Decision
│   ├── decision               # allow, deny, error
│   ├── decision_reason        # Why (policy name, error)
│   ├── policy_id              # Which policy decided
│   └── policy_version         # Which policy version
├── Context
│   ├── ip_address             # Source IP
│   ├── user_agent             # Client identification
│   ├── environment            # dev, staging, prod
│   ├── request_metadata       # Custom request metadata
│   └── error (if denied)      # Error details
├── Outcome
│   ├── success                # Did it work?
│   ├── error                  # null if successful
│   ├── latency_ms             # Response time
│   └── cost (optional)        # Cost if applicable
└── Compliance
    ├── sensitivity_level      # low, medium, high, critical
    ├── forwarded_to_siem      # Sent to compliance system?
    └── retention_until        # Delete after date
```

### 7.2 Audit Log Format

**Structured JSON (Recommended):**

```json
{
  "event": {
    "id": "event-550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-11-27T19:45:30.123Z",
    "request_id": "req-a1b2c3d4e5f6"
  },
  "principal": {
    "id": "alice@company.com",
    "type": "human",
    "attributes": {
      "role": "developer",
      "teams": ["backend", "security"],
      "department": "Engineering"
    }
  },
  "resource": {
    "id": "res-jira-query",
    "type": "tool",
    "name": "jira.search",
    "sensitivity": "medium"
  },
  "action": {
    "operation": "execute",
    "parameters": {
      "jql": "project = PROJ"
    }
  },
  "decision": {
    "result": "allow",
    "reason": "Developer can execute medium sensitivity tools",
    "policy_id": "pol-rbac-default",
    "policy_version": 2
  },
  "context": {
    "ip_address": "10.1.2.3",
    "user_agent": "Mozilla/5.0...",
    "environment": "production"
  },
  "outcome": {
    "success": true,
    "latency_ms": 42,
    "cost": 0.001
  },
  "compliance": {
    "forwarded_to_siem": "2025-11-27T19:45:31.456Z",
    "retention_until": "2026-11-27T00:00:00Z"
  }
}
```

### 7.3 Retention and Query

**Retention Policies (Configurable by Profile):**

| Profile | Minimum Retention | Default | Justification |
|---------|------------------|---------|--------------|
| GRID-Enterprise | 90 days | 1 year | SOC 2 Type II, ISO 27001 |
| GRID-Home | 30 days | 90 days | Privacy, storage efficiency |

**Query Capabilities (MUST support):**

```
- Time-range queries (from date/timestamp to date/timestamp)
- Principal filtering (by principal ID, role, team)
- Resource filtering (by resource ID, type, sensitivity)
- Action filtering (by operation)
- Decision filtering (allow, deny, error)
- Full-text search (on details)

Examples:
- All denied access to critical resources last 24 hours
- All actions by principal_id=alice@company.com this month
- All write operations to database in last 7 days
- All actions that took >1000ms (slow operations)
- All actions by role=admin with sensitivity=critical
```

**Export Formats:**

- ✅ JSON (structured, complete)
- ✅ CSV (spreadsheet-friendly)
- ✅ SIEM format (Splunk HEC, Datadog, etc.)

### 7.4 Immutability Guarantees

**Storage Design:**
- ✅ **INSERT-ONLY** tables (no UPDATE/DELETE capability)
- ✅ Database constraints prevent modification
- ✅ Snapshot taken in remote SIEM systems
- ✅ Cryptographic hashing (optional) for tampering detection

**Immutable Audit Example (TimescaleDB):**

```sql
-- Create hypertable (time-series table)
CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    event_type TEXT NOT NULL,
    principal_id UUID NOT NULL,
    decision TEXT NOT NULL,
    details JSONB NOT NULL
) PARTITION BY RANGE (timestamp);

-- Add constraint: no updates or deletes
ALTER TABLE audit_events DISABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events ADD CONSTRAINT immutable_log CHECK (true);

-- Only INSERT allowed (application enforces this)
-- SELECT allowed for queries/exports
-- UPDATE forbidden (application design + DB constraints)
-- DELETE forbidden (application design + DB constraints)

-- Retention policy via compression (data becomes read-only)
SELECT add_compression_policy('audit_events',
    INTERVAL '30 days');
```

---

## 8. Interoperability

### 8.1 Policy Exchange Format

**GRID Policy Format (Canonical):**

GRID implementations can export/import policies in a canonical format:

```yaml
apiVersion: grid.io/v1alpha1
kind: Policy
metadata:
  name: "rbac-default"
  version: 2
  created_at: "2025-11-27T00:00:00Z"
  tags:
    - "default"
    - "rbac"
spec:
  type: "authorization"
  status: "active"
  rules:
    - name: "admin_full_access"
      description: "Admins have unrestricted access"
      priority: 100
      match:
        principals:
          - type: role
            value: admin
      effect: allow

    - name: "developer_medium_sensitivity"
      description: "Developers can execute medium sensitivity tools"
      priority: 50
      match:
        principals:
          - type: role
            value: developer
        resources:
          - type: sensitivity
            value: ["low", "medium"]
        actions:
          - type: operation
            value: execute
      effect: allow

    - name: "deny_critical_outside_hours"
      description: "Deny critical resource access outside work hours"
      priority: 150  # Higher priority overrides
      match:
        resources:
          - type: sensitivity
            value: critical
        conditions:
          - type: time
            operator: not_business_hours
      effect: deny
```

### 8.2 Audit Log Portability

**Cross-Implementation Compatibility:**

GRID implementations must support importing audit logs from other implementations:

```python
# Import function (pseudo-code)
def import_audit_logs(logs: List[AuditEvent]) -> None:
    """Import audit events from another GRID implementation."""
    for log in logs:
        # Validate schema
        validate_audit_schema(log)

        # Map protocol-specific fields to GRID universal fields
        grid_event = map_to_grid_schema(log)

        # Store immutably
        audit_store.insert(grid_event)

        # Forward to SIEM
        siem_adapter.send_event(grid_event)
```

### 8.3 Federation Protocol

**Node Discovery:**

```
Node A (Org A) ← DNS/mDNS → Discover Node B (Org B)
Node A requests: /.well-known/grid
Response: {
  "version": "0.1",
  "endpoints": {
    "policy": "https://grid-b.org.com/api/v1/policy",
    "audit": "https://grid-b.org.com/api/v1/audit",
    "principals": "https://grid-b.org.com/api/v1/principals"
  },
  "trust": {
    "cert": "-----BEGIN CERTIFICATE-----...",
    "key_id": "key-123"
  }
}
```

**Trust Establishment:**

```
1. Certificate Exchange (mTLS)
   - Node A sends certificate
   - Node B verifies certificate chain
   - Mutual authentication established

2. Policy Sync (Optional)
   - Node A: "What policies do you have for accessing your resources?"
   - Node B: [Returns policy list]
   - Node A: Downloads policies of interest

3. Principal Resolution (Optional)
   - Node A: "Is alice@org-b.com authorized?"
   - Node B: Evaluates policies, returns decision

4. Audit Correlation
   - Event in Node A references Principal from Node B
   - Audit trail includes full path across federation
```

---

## 9. Protocol Adapters

### 9.1 Adapter Architecture

Protocol adapters map protocol-specific concepts to GRID abstractions:

```
┌─────────────────────────────────────────────────────┐
│ GRID Core (Protocol-Agnostic)                       │
│ - Policy Engine                                     │
│ - Audit Logging                                     │
│ - Authentication                                    │
└─────────────────────────────────────────────────────┘
                ↓ (Common Interface)
┌──────────────┬──────────────┬──────────────┐
│ MCP Adapter  │ HTTP Adapter │ gRPC Adapter │
└──────────────┴──────────────┴──────────────┘
                ↓ (Protocol Semantics)
┌──────────────┬──────────────┬──────────────┐
│ MCP Servers  │ REST APIs    │ gRPC Services│
└──────────────┴──────────────┴──────────────┘
```

**Adapter Interface:**

```python
class ProtocolAdapter(ABC):
    """Base class for GRID protocol adapters."""

    @abstractmethod
    def translate_request(
        self,
        protocol_request: Any
    ) -> GridRequest:
        """Translate protocol-specific request to GRID request."""
        pass

    @abstractmethod
    def translate_response(
        self,
        grid_response: GridResponse,
        error: Optional[str] = None
    ) -> Any:
        """Translate GRID response back to protocol-specific format."""
        pass

    @abstractmethod
    def get_principal(
        self,
        protocol_context: Any
    ) -> Principal:
        """Extract principal from protocol context."""
        pass

    @abstractmethod
    def register_resource(
        self,
        protocol_resource: Any
    ) -> Resource:
        """Register a protocol-specific resource in GRID."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Verify adapter and protocol connectivity."""
        pass
```

### 9.2 MCP Adapter (Reference Implementation)

Maps MCP concepts to GRID abstractions:

```python
class MCPAdapter(ProtocolAdapter):
    """GRID adapter for Model Context Protocol (MCP)."""

    def translate_request(self, mcp_request: MCPRequest) -> GridRequest:
        """
        MCP Tool Call → GRID Action

        MCP: {
          "jsonrpc": "2.0",
          "method": "tools/call",
          "params": {
            "name": "jira_search",
            "arguments": {"jql": "project = PROJ"}
          }
        }

        GRID: {
          "principal": <extracted from JWT>,
          "resource": "mcp-jira-server:jira_search",
          "action": {
            "operation": "execute",
            "parameters": {"jql": "project = PROJ"}
          }
        }
        """
        return GridRequest(
            principal=self._extract_principal(mcp_request),
            resource_id=f"mcp-{mcp_request.server}:{mcp_request.tool}",
            action=GridAction(
                operation="execute",
                parameters=mcp_request.arguments
            )
        )

    def translate_response(
        self,
        grid_response: GridResponse,
        error: Optional[str] = None
    ) -> MCPResponse:
        """
        GRID Response → MCP Response

        GRID: {
          "allowed": True,
          "reason": "...",
          "data": <tool result>
        }

        MCP: {
          "jsonrpc": "2.0",
          "result": {"type": "text", "text": "<output>"}
        }
        """
        if not grid_response.allowed:
            return MCPResponse(
                error={
                    "code": -32000,
                    "message": f"Access denied: {grid_response.reason}"
                }
            )

        return MCPResponse(
            result={"type": "text", "text": grid_response.data}
        )

    def register_resource(
        self,
        mcp_server: MCPServer
    ) -> GridResource:
        """Register MCP server and its tools in GRID."""
        return GridResource(
            id=f"mcp-{mcp_server.name}",
            type="service",
            name=mcp_server.name,
            sensitivity_level=mcp_server.sensitivity_level,
            capabilities=[t.name for t in mcp_server.tools],
            metadata={
                "mcp_version": mcp_server.mcp_version,
                "transport": mcp_server.transport,
                "tools": [
                    {
                        "name": t.name,
                        "sensitivity": t.sensitivity_level,
                        "parameters": t.parameters
                    }
                    for t in mcp_server.tools
                ]
            }
        )
```

### 9.3 Future Adapters

**HTTP/REST Adapter:**
```
HTTP Request → GRID
GET /api/v1/users?id=123
  ↓
Principal from Authorization header
Resource: /api/v1/users
Action: read
Parameters: {id: 123}
```

**gRPC Adapter:**
```
gRPC Request → GRID
service.Method(request)
  ↓
Principal from mTLS certificate + metadata
Resource: service.Method
Action: execute
Parameters: from request message
```

**OpenAI Function Calling Adapter:**
```
OpenAI Tool Use → GRID
{
  "type": "tool_use",
  "name": "query_database",
  "input": {...}
}
  ↓
Principal from API key
Resource: openai-tool-query_database
Action: execute
Parameters: from input
```

**Custom Protocol Adapter:**
```
Custom Protocol → GRID
Implement ProtocolAdapter interface:
- Translate requests to GRID format
- Translate GRID responses back
- Extract principals
- Register resources
```

---

## 10. Extension Points

### 10.1 Custom Policy Engines

Implementations can plug in different policy evaluation engines:

```python
class PolicyEngine(ABC):
    """Abstract policy evaluation engine."""

    @abstractmethod
    def evaluate(
        self,
        principal: Principal,
        resource: Resource,
        action: Action,
        context: Context
    ) -> PolicyDecision:
        """Evaluate policy and return decision."""
        pass

    @abstractmethod
    def validate_policy(self, policy: str) -> bool:
        """Validate policy syntax."""
        pass

    @abstractmethod
    def deploy_policy(
        self,
        policy: Policy
    ) -> None:
        """Deploy policy to engine."""
        pass

# Implementations
class OPAEngine(PolicyEngine): ...     # Open Policy Agent (Rego)
class CedarEngine(PolicyEngine): ...   # AWS Cedar
class CustomRulesEngine(PolicyEngine): ... # Custom logic
```

### 10.2 Authentication Providers

Pluggable authentication implementations:

```python
class AuthProvider(ABC):
    """Abstract authentication provider."""

    @abstractmethod
    async def authenticate(
        self,
        credentials: AuthCredentials
    ) -> AuthResult:
        """Authenticate and return principal context."""
        pass

    @abstractmethod
    async def validate_token(self, token: str) -> Principal:
        """Validate token and extract principal."""
        pass

    @abstractmethod
    async def get_user_info(self, principal_id: str) -> dict:
        """Get user/principal metadata."""
        pass

# Implementations
class OIDCProvider(AuthProvider): ...
class LDAPProvider(AuthProvider): ...
class SAMLProvider(AuthProvider): ...
class APIKeyProvider(AuthProvider): ...
```

### 10.3 Audit Backends

SIEM and compliance system integrations:

```python
class AuditBackend(ABC):
    """Abstract audit backend for forwarding."""

    @abstractmethod
    async def send_event(self, event: AuditEvent) -> bool:
        """Send event to backend."""
        pass

    @abstractmethod
    async def send_batch(self, events: List[AuditEvent]) -> bool:
        """Send batch of events."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check backend connectivity."""
        pass

    @abstractmethod
    def format_event(self, event: AuditEvent) -> dict:
        """Format event for backend."""
        pass

# Implementations
class SplunkBackend(AuditBackend): ...
class DatadogBackend(AuditBackend): ...
class KafkaBackend(AuditBackend): ...
```

### 10.4 Cost Attribution Systems

Optional cost tracking for resource usage:

```python
class CostAttributor(ABC):
    """Cost attribution for resource usage."""

    @abstractmethod
    def estimate_cost(
        self,
        action: Action,
        resource: Resource
    ) -> float:
        """Estimate cost of action."""
        pass

    @abstractmethod
    def get_budget(self, principal: Principal) -> float:
        """Get remaining budget for principal."""
        pass

    @abstractmethod
    def deduct_cost(
        self,
        principal: Principal,
        cost: float
    ) -> None:
        """Deduct cost from principal's budget."""
        pass

# Implementations
class SimpleTagBasedCostAttributor(CostAttributor): ...
class MLBasedCostEstimator(CostAttributor): ...
class ZeroTrustCostModel(CostAttributor): ...
```

---

## 11. Implementation Requirements

### 11.1 Minimum Compliance (GRID v0.1)

To be "GRID-compliant", an implementation MUST:

**Core Abstractions:**
- ✅ Define and manage Principals
- ✅ Define and manage Resources
- ✅ Define and manage Actions
- ✅ Implement Policies (at least RBAC)
- ✅ Log Audit events (immutable)

**Authentication:**
- ✅ Support at least one authentication method
- ✅ Extract principal identity and context
- ✅ Validate tokens/credentials

**Authorization:**
- ✅ Implement zero-trust (default deny)
- ✅ Support role-based access control minimum
- ✅ Cache policy decisions for performance

**Audit:**
- ✅ Log all authorization decisions (allow and deny)
- ✅ Use immutable storage (INSERT-ONLY)
- ✅ Include required audit fields
- ✅ Support time-range queries

**API:**
- ✅ Expose evaluation endpoint (evaluate principal→action→resource)
- ✅ Support resource registration
- ✅ Support policy management
- ✅ Support audit log queries

### 11.2 Optional Features

To enhance GRID-compliance:

- ⭐ Policy versioning and rollback
- ⭐ Multiple authentication providers
- ⭐ Attribute-based access control (ABAC)
- ⭐ Real-time SIEM forwarding
- ⭐ Rate limiting and quotas
- ⭐ Web UI for management
- ⭐ Federated governance
- ⭐ Policy templates and testing

### 11.3 Reference Implementations

**SARK (Enterprise)**
- ✅ GRID-Enterprise profile
- ✅ All mandatory + optional features
- ✅ Production-ready
- ✅ MCP-focused

**YORI (Home) - Planned**
- ✅ GRID-Home profile
- ✅ Advisory governance
- ✅ Privacy-focused
- ✅ Community-driven

---

## 12. Security Considerations

### 12.1 Threat Model

**GRID Governance Threats:**

1. **Policy Bypass**
   - Attacker circumvents GRID enforcement
   - Mitigation: Zero-trust architecture, default deny, multiple verification layers

2. **Privilege Escalation**
   - Low-privilege principal gains unauthorized access
   - Mitigation: Explicit permission grants, deny overrides allow, audit trail

3. **Audit Tampering**
   - Attacker modifies audit logs to hide actions
   - Mitigation: Immutable storage, remote SIEM mirror, cryptographic hashing

4. **Man-in-the-Middle (MITM)**
   - Attacker intercepts and modifies GRID decisions
   - Mitigation: Encryption in transit (TLS), signature verification

5. **Denial of Service (DoS)**
   - Attacker overwhelms policy evaluation or audit
   - Mitigation: Rate limiting, circuit breakers, caching, async audit

6. **Token Forgery**
   - Attacker creates fake authentication tokens
   - Mitigation: Cryptographic signing (HMAC/RSA), token validation

7. **Configuration Injection**
   - Attacker modifies policies or resource definitions
   - Mitigation: RBAC on policy changes, audit trail, version control

### 12.2 Security Best Practices

**Authentication:**
- ✅ Use cryptographically signed tokens (JWT with HMAC/RSA)
- ✅ Validate token signatures on every request
- ✅ Implement token expiration and refresh
- ✅ Support multi-factor authentication (MFA)
- ✅ Use HTTPS/TLS 1.2+ for all communication

**Authorization:**
- ✅ Default deny (least privilege)
- ✅ Explicit permission grants
- ✅ Deny overrides allow (fail-safe)
- ✅ Regular audit of access grants
- ✅ Implement approval workflows for sensitive actions

**Audit:**
- ✅ Immutable storage (INSERT-ONLY)
- ✅ Real-time SIEM forwarding (for critical events)
- ✅ Retention policies (meeting compliance requirements)
- ✅ Regular audit log reviews
- ✅ Incident response procedures

**Operations:**
- ✅ Encrypt secrets (JWT keys, API keys, credentials)
- ✅ Rotate secrets regularly
- ✅ Separate read/write audit access
- ✅ Monitor for anomalies (unusual access patterns)
- ✅ Test disaster recovery procedures

### 12.3 Known Limitations

**GRID v0.1 Limitations:**

1. **No distributed consensus** - Federation requires established trust, not Byzantine-fault-tolerant consensus
2. **No rate limiting standardization** - Implementations vary; no standard rate limit header format
3. **No cost model standardization** - Cost attribution is implementation-specific
4. **Timing attack vulnerabilities** - Policy evaluation timing can leak information
5. **Cache poisoning** - Cache misses can cascade, causing load spikes
6. **Policy version conflicts** - No standardized version negotiation in federation

**Recommended Mitigations:**
- Establish federation manually (pre-agreed trust)
- Use implementation-agnostic rate limit headers
- Document cost attribution model
- Use constant-time comparisons for sensitive operations
- Implement cache warming and load testing
- Version policies with semantic versioning

---

## 13. Use Cases

### 13.1 AI Agent Tool Access (MCP)

**Scenario:** Claude AI assistant accessing tools via MCP

```
Principal: AI Agent (claude-api-production)
Resource: jira.search (MCP tool)
Action: execute
Policy: Agents can invoke low/medium sensitivity tools during business hours

Request Flow:
1. User asks Claude: "Show me all bugs assigned to my team"
2. Claude selects tool: jira.search
3. Claude sends: /api/v1/policy/evaluate
   {principal: agent-id, resource: jira-search, action: execute}
4. GRID checks policy: "Agent during business hours? Sensitivity medium? ✓"
5. GRID responds: {allowed: true}
6. Claude invokes MCP tool
7. GRID logs: tool invocation allowed
```

### 13.2 AI-to-AI Collaboration

**Scenario:** AI Agent A delegating to AI Agent B

```
Principal: Agent A (internal AI system)
Resource: Agent B (external AI service)
Action: delegate_task
Policy: Agents can delegate to approved external systems

Request Flow:
1. Agent A: "I need help with data analysis, calling Agent B"
2. Agent A sends request to Agent B's API (with API key)
3. Agent B's GRID validates: "Is Agent A allowed to call this?"
4. Agent B checks policy: "Agent A on approved list? ✓"
5. Agent B responds: Success + audit event
6. Agent B's GRID logs: AI-to-AI delegation allowed
7. Audit trail shows delegation chain: User → Agent A → Agent B → Result
```

### 13.3 Microservice Governance

**Scenario:** Service A calling Service B's API

```
Principal: Service A (payment-processor service)
Resource: Service B (database-access-api)
Action: query
Policy: Services can access databases within team scope

Request Flow:
1. Service A needs customer data: GET /api/customers?id=123
2. Service A sends mTLS certificate (authentication)
3. Service B's GRID validates certificate chain
4. Service B checks policy: "Is Service A (payment-processor) allowed to read customers? ✓"
5. Service B grants access: returns customer data
6. GRID logs: Service-to-service call allowed
7. Compliance dashboard shows: Payment service accessed customer data
```

### 13.4 IoT Device Management

**Scenario:** IoT device requesting cloud resource

```
Principal: Device (sensor-001 in factory-a)
Resource: Cloud API (update-production-parameters)
Action: execute
Policy: Sensors can read parameters, only supervisors can write

Request Flow:
1. Sensor needs latest parameters: GET /api/parameters
2. Sensor sends API key (authentication)
3. GRID validates: "Is sensor-001 allowed to read parameters? ✓"
4. GRID responds: {allowed: true, data: parameters}
5. Sensor applies parameters
6. GRID logs: Sensor parameter fetch
7. When supervisor tries to write: "Only supervisors can write"
```

### 13.5 Autonomous System Control

**Scenario:** Autonomous robot requesting resource from shared infrastructure

```
Principal: Robot (robot-arm-factory-1)
Resource: Shared warehouse system
Action: move_item
Policy: Robots can move items within their facility zone

Request Flow:
1. Robot needs to move item to warehouse: POST /api/move
2. Robot sends certificate + request
3. GRID checks policy: "Is robot-arm-1 in factory-a? ✓"
   "Is move action within zone permissions? ✓"
   "Is warehouse system healthy? ✓ (circuit breaker)"
4. GRID responds: {allowed: true}
5. Robot executes move
6. Audit trail tracks: Robot X moved item Y at location Z
7. If warehouse offline: GRID returns 503 (circuit breaker), not 403
```

---

## 14. Versioning and Evolution

### 14.1 Specification Versioning

GRID uses semantic versioning:

```
Version Format: GRID vX.Y.Z

X = Major (Breaking changes)
Y = Minor (Backward-compatible additions)
Z = Patch (Bug fixes)

Examples:
- GRID v0.1.0 (Initial specification)
- GRID v0.2.0 (Add support for Adapters)
- GRID v1.0.0 (First stable release)
```

### 14.2 Backward Compatibility

**GRID v0.1 → v0.2 (Backward Compatible):**
- ✅ Existing GRID v0.1 implementations continue to work
- ✅ New implementations can opt-in to v0.2 features
- ✅ Federation works across versions

**GRID v0.x → v1.0 (Possible Breaking Change):**
- Example: Change audit event format
- Requires migration path: tools, documentation, test data

### 14.3 Extension Mechanism

Implementations can extend GRID without breaking spec:

```yaml
# Extension example (protocol adapter)
apiVersion: grid.io/v1alpha1
kind: CustomAdapter
metadata:
  name: custom-rpc-adapter
  version: 1.0.0
spec:
  protocol: "custom-rpc"
  baseClass: "ProtocolAdapter"
  implements:
    - translate_request
    - translate_response
    - get_principal
    - register_resource
```

### 14.4 Protocol Adapter Versioning

Adapters version independently:

```
MCP Adapter v1.0 (supports GRID v0.1+)
MCP Adapter v2.0 (supports GRID v0.2+, backward compatible with GRID v0.1)
HTTP Adapter v1.0 (supports GRID v0.1+)
```

---

## 15. Future Considerations

### 15.1 Potential GRID v1.0 Features

- **Byzantine-Fault-Tolerant Federation** - Consensus-based trust establishment
- **Cost Attribution Standards** - Standardized cost model across implementations
- **Rate Limit Headers** - Standard HTTP header format for rate limits
- **Policy Optimization** - Compile policies to bytecode for faster evaluation
- **Machine Learning Policy** - ML-based anomaly detection policies
- **Resource Quotas** - Fine-grained quota enforcement
- **Temporal Policies** - Time-based access patterns
- **Geo-Fenced Access** - Location-based policies

### 15.2 Tooling Ecosystem

- **GRID Policy Editor** - IDE with syntax highlighting, testing, versioning
- **GRID Debugger** - Step through policy evaluation
- **GRID Compliance Reporter** - Automated compliance reports (SOC 2, ISO 27001)
- **GRID Migration Tool** - Migrate from RBAC to GRID
- **GRID Federation Manager** - Manage federated nodes, trust relationships
- **GRID SDK** - Language-specific SDKs for implementing GRID

---

## Appendix A: Complete Policy Examples (Multi-Protocol)

### Example 1: Team-Based Access (Works Across All Protocols)

```rego
package grid.authorization

# Team members can invoke their team's resources
allow if {
    some team_id in input.principal.teams
    team_id in input.resource.managers
    input.action.operation == "execute"
}

# Team leads can create new resources
allow if {
    some team_id in input.principal.teams
    input.principal.is_team_lead[team_id] == true
    input.action.operation == "create"
    input.resource.type in ["tool", "service"]
}
```

### Example 2: Sensitivity + Time-Based (Multi-Protocol)

```rego
package grid.authorization

# Low sensitivity: anyone can access
allow if {
    input.resource.sensitivity == "low"
}

# Medium sensitivity: work hours only
allow if {
    input.resource.sensitivity == "medium"
    is_business_hours
}

# High sensitivity: approved users during business hours
allow if {
    input.resource.sensitivity == "high"
    input.principal.clearance == "high"
    is_business_hours
}

# Critical sensitivity: admin + CEO approval + daytime + weekday
allow if {
    input.resource.sensitivity == "critical"
    input.principal.role == "admin"
    input.principal.approval.ceo_approved == true
    is_business_hours
    is_weekday
}

is_business_hours if {
    hour := time.clock([input.context.timestamp])[0]
    hour >= 9
    hour < 18
}

is_weekday if {
    day := time.weekday(input.context.timestamp)
    day not in [0, 6]
}
```

### Example 3: Delegation (AI Agent Scenario)

```rego
package grid.authorization

# Users can invoke via trusted AI agents
allow if {
    input.principal.type == "human"
    input.action.via_agent == true
    is_trusted_agent(input.action.agent_id)
    is_action_in_scope(
        input.principal,
        input.action.original_action
    )
}

# AI agents can delegate to other trusted agents
allow if {
    input.principal.type == "agent"
    input.action.operation == "delegate"
    is_trusted_agent(input.action.target_agent_id)
    is_delegation_within_scope(input)
}

is_trusted_agent(agent_id) if {
    agent_id in [
        "claude-api-prod",
        "internal-agent-1"
    ]
}
```

---

## Appendix B: Audit Log Schemas (JSON Schema)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "GRID Audit Event Schema",
  "type": "object",
  "required": [
    "id",
    "timestamp",
    "principal",
    "resource",
    "action",
    "decision"
  ],
  "properties": {
    "id": {
      "type": "string",
      "description": "Unique event identifier (UUID)"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "When event occurred (UTC ISO 8601)"
    },
    "request_id": {
      "type": "string",
      "description": "Request identifier for correlation"
    },
    "principal": {
      "type": "object",
      "required": ["id"],
      "properties": {
        "id": {
          "type": "string",
          "description": "Principal identifier"
        },
        "type": {
          "type": "string",
          "enum": ["human", "agent", "service", "device"],
          "description": "Principal type"
        },
        "attributes": {
          "type": "object",
          "properties": {
            "role": {"type": "string"},
            "teams": {"type": "array", "items": {"type": "string"}},
            "department": {"type": "string"}
          }
        }
      }
    },
    "resource": {
      "type": "object",
      "required": ["id"],
      "properties": {
        "id": {
          "type": "string",
          "description": "Resource identifier"
        },
        "type": {
          "type": "string",
          "enum": ["tool", "data", "service", "device"],
          "description": "Resource type"
        },
        "name": {
          "type": "string"
        },
        "sensitivity": {
          "type": "string",
          "enum": ["low", "medium", "high", "critical"]
        }
      }
    },
    "action": {
      "type": "object",
      "required": ["operation"],
      "properties": {
        "operation": {
          "type": "string",
          "enum": ["read", "write", "execute", "control", "manage", "audit"]
        },
        "parameters": {
          "type": "object",
          "description": "Sanitized action parameters"
        }
      }
    },
    "decision": {
      "type": "object",
      "required": ["result"],
      "properties": {
        "result": {
          "type": "string",
          "enum": ["allow", "deny", "error"],
          "description": "Authorization decision"
        },
        "reason": {
          "type": "string",
          "description": "Decision rationale"
        },
        "policy_id": {
          "type": "string",
          "description": "Policy that decided"
        }
      }
    },
    "context": {
      "type": "object",
      "properties": {
        "ip_address": {"type": "string"},
        "user_agent": {"type": "string"},
        "environment": {
          "type": "string",
          "enum": ["dev", "staging", "prod"]
        },
        "metadata": {"type": "object"}
      }
    },
    "outcome": {
      "type": "object",
      "properties": {
        "success": {"type": "boolean"},
        "error": {"type": ["string", "null"]},
        "latency_ms": {"type": "number"},
        "cost": {"type": "number"}
      }
    }
  }
}
```

---

## Appendix C: Glossary

| Term | Definition |
|------|-----------|
| **Action** | An operation a principal wants to perform (read, write, execute) |
| **Audit Event** | Immutable record of an authorization decision |
| **Adapter** | Translator between protocol-specific and GRID abstractions |
| **Authorization** | Decision to grant or deny access |
| **Cache** | In-memory or distributed store for policy decisions |
| **Delegation** | Principal A authorizing Principal B to act on their behalf |
| **Federation** | Multiple independent GRID nodes establishing trust |
| **Policy** | Set of rules determining authorization decisions |
| **Principal** | Entity making a request (user, agent, service, device) |
| **Resource** | Capability, data, or service being accessed |
| **SIEM** | Security Information and Event Management system |
| **Zero-Trust** | Security model requiring explicit authorization for all access |

---

## Document History

| Version | Date | Status | Notes |
|---------|------|--------|-------|
| 0.1 | 2025-11-27 | Draft | Initial specification based on SARK reference implementation |

---

## Attribution & Contributors

**GRID Protocol Specification v0.1** was reverse-engineered from the **SARK (Secure Autonomous Resource Kontroller)** reference implementation.

**Original Design & Implementation:**
- **James R. A. Henry** - SARK architect and maintainer
  - Designed and built the reference implementation
  - Created the architecture that makes this specification possible

**Specification & Analysis:**
- **Claude Code** (Anthropic's Claude via Claude Code)
  - Reverse-engineered patterns from SARK codebase
  - Extracted universal governance concepts from MCP-specific implementation
  - Formalized GRID specification
  - Analyzed SARK's GRID compliance

**Reference Materials Analyzed:**
- SARK architecture and design patterns
- Policy engine integration (OPA/Rego)
- Authentication and authorization flows
- Audit logging and SIEM integration
- Protocol abstraction patterns
- Configuration and extension points

This specification would not exist without SARK's elegant, production-proven design. GRID documents what SARK demonstrates: that universal machine-to-machine governance is possible, practical, and deployable at enterprise scale.

---

**GRID Protocol v0.1 Specification**
*A Universal Governance Protocol for Machine-to-Machine Interactions*

For feedback, issues, or contributions: [github.com/apathy-ca/grid-protocol](https://github.com/apathy-ca/grid-protocol)
