# SARK Glossary

**Comprehensive terminology reference for SARK MCP Governance**

---

## 🔑 Core Concept

### MCP (Model Context Protocol)

**Model Context Protocol** is an open protocol that standardizes how applications provide context to Large Language Models (LLMs).

**What it does:**
- Enables AI applications to securely connect to data sources, tools, and services
- Provides a unified interface for LLMs to access external context
- Supports discovery of capabilities, invocation of tools, and retrieval of resources

**Why governance is needed:**
- **Unrestricted Access**: MCP servers can potentially access any connected system
- **Visibility Gap**: Organizations lack insight into deployed MCP servers
- **Missing Controls**: No standard authorization or audit mechanisms
- **Compliance Risk**: Audit trails and policy enforcement typically absent

**MCP Components:**
- **MCP Client**: AI application that connects to MCP servers (e.g., Claude Desktop, IDEs)
- **MCP Server**: Service that exposes tools, resources, and prompts to clients
- **MCP Protocol**: JSON-RPC 2.0 based communication protocol
- **MCP Gateway**: Proxy layer for authentication, authorization, and audit (SARK's role)

**Key Capabilities:**
- **Tools**: Executable functions (e.g., search database, run script, send email)
- **Resources**: Data access (e.g., read file, query API, fetch document)
- **Prompts**: Template interactions with context
- **Sampling**: Request LLM completions through the server

**SARK's MCP Governance:**
1. **Discovery**: Automated scanning and registration of MCP servers
2. **Authentication**: Multi-protocol identity verification (OIDC, LDAP, SAML)
3. **Authorization**: Policy-based access control via Open Policy Agent
4. **Audit**: Immutable logging of all MCP interactions
5. **Enforcement**: Runtime policy enforcement at the gateway layer

**Example MCP Server:**
```json
{
  "name": "database-server",
  "version": "1.0.0",
  "capabilities": ["tools", "resources"],
  "tools": ["query_customer_data", "update_records"],
  "resources": ["customer_database", "analytics_views"],
  "endpoint": "https://mcp-db.internal:8080",
  "sensitivity": "high"
}
```

**Security Considerations:**
- MCP servers inherit the permissions of their host environment
- Tools can execute arbitrary code if not properly sandboxed
- Resources may expose sensitive data without access controls
- Rate limiting needed to prevent abuse

**Standards & Specifications:**
- **Official Spec**: https://spec.modelcontextprotocol.io/
- **GitHub Repo**: https://github.com/modelcontextprotocol
- **Transport**: JSON-RPC 2.0 over HTTP/HTTPS, WebSockets, or stdio

**See also:**
- [MCP Server](#mcp-server)
- [MCP Client](#mcp-client)
- [Capabilities (MCP)](#capabilities-mcp)
- [Zero-Trust MCP](#zero-trust-mcp)

---

## A

### ABAC (Attribute-Based Access Control)
Access control model where authorization decisions are based on attributes of users, resources, and environment. Example: "Allow access if user.department == resource.department AND time == business_hours".

**See also:** [RBAC](#rbac-role-based-access-control), [ReBAC](#rebac-relationship-based-access-control)

### Access Token
Short-lived credential (typically JWT) used to authenticate API requests. SARK tokens expire after 15 minutes by default.

**Example:** `eyJhbGciOiJSUzI1NiIs...`

### API Gateway
Entry point for API requests that handles authentication, rate limiting, and routing. SARK uses Kong Gateway.

**See also:** [Kong Gateway](#kong-gateway)

### Audit Event
Immutable record of an action in the system. Stored in TimescaleDB for compliance and security analysis.

**Fields:** timestamp, user, action, resource, decision, reason, context

### Audit Trail
Complete chronological record of all system activities. SARK maintains immutable audit trails in TimescaleDB.

**Retention:** 90 days default (configurable)

---

## B

### Batch Evaluation
Evaluating multiple policy decisions in a single API request for efficiency.

**Example:** Instead of 100 individual requests, send 1 batch request with 100 evaluations.

### Break-Glass Access
Emergency access procedure that bypasses normal controls with extensive logging.

**Use case:** Critical incident response when normal approval process is too slow.

### Bundle (OPA)
Package containing compiled OPA policies. Deployed to OPA servers as a single unit.

**Format:** `.tar.gz` file with policies and data

---

## C

### Cache Hit Rate
Percentage of requests served from cache vs. database. SARK targets >95% hit rate.

**Formula:** `cache_hits / (cache_hits + cache_misses)`

### Capabilities (MCP)
Features supported by an MCP server (e.g., "tools", "resources", "prompts").

**Example:** `["tools", "resources"]`

### Circuit Breaker
Pattern that prevents cascading failures by stopping requests to failing services.

**States:** Closed (normal) → Open (failing) → Half-Open (testing recovery)

### Compliance Framework
Standard for security/privacy controls (e.g., SOC 2, ISO 27001, GDPR).

**SARK supports:** SOC 2 Type II, ISO 27001, GDPR, HIPAA, PCI-DSS

### Consul
Service discovery and configuration tool. SARK uses it for MCP server registry.

**Port:** 8500 (HTTP), 8600 (DNS)

### Context (Policy)
Environmental information used in authorization decisions (time, IP, user agent, etc.).

**Example:** `{"timestamp": 1700000000, "ip_address": "10.0.1.45"}`

---

## D

### Data Classification
Categorization of data by sensitivity (Public, Confidential, Secret, Top Secret).

**SARK levels:** Low, Medium, High, Critical

### Data Residency
Legal requirement that data must be stored in specific geographic locations.

**Example:** GDPR requires EU citizen data to stay in EU.

### Defense in Depth
Security strategy using multiple layers of protection.

**SARK layers:** Network → Gateway → Application → Service Mesh → Data

### Deny by Default
Security principle where everything is denied unless explicitly allowed.

**OPA:** `default allow := false`

### Discovery Service
SARK component that finds and registers MCP servers automatically.

**Methods:** Network scanning, Kubernetes API, cloud APIs, manual registration

### DLP (Data Loss Prevention)
System that prevents sensitive data from being sent outside organization.

**Integration:** SARK can integrate with Microsoft Purview, Google DLP, Symantec DLP

---

## E

### Endpoint
URL where an MCP server is accessible.

**Example:** `https://mcp-finance.internal:8080`

### etcd
Distributed key-value store used for coordination and configuration.

**SARK usage:** Leader election, distributed locking

---

## F

### Fail-Safe
System design where failures result in secure state (deny access).

**Opposite:** Fail-open (allow access on failure) - NOT recommended

### Federated Identity
Authentication where user identities are managed by external provider (Okta, Azure AD).

**Protocol:** OIDC (OpenID Connect)

---

## G

### Grafana
Visualization platform for metrics. SARK includes pre-built dashboards.

**Metrics source:** Prometheus

### gRPC
High-performance RPC framework. Alternative to HTTP for MCP transport.

**Not yet supported** in SARK (planned for future)

---

## H

### HashiCorp Vault
Secrets management tool for storing/generating credentials.

**SARK usage:** Dynamic database credentials, encryption keys, API tokens

### Health Check
Endpoint that reports service status.

**SARK endpoints:** `/health` (basic), `/health/ready` (with dependencies)

### HPA (Horizontal Pod Autoscaler)
Kubernetes feature that automatically scales pods based on metrics.

**SARK triggers:** CPU >70%, memory >80%, RPS >1000/pod

### HTTP/2
Next version of HTTP with multiplexing, compression, server push.

**SARK support:** Yes, enabled on all HTTPS endpoints

### Hypertable (TimescaleDB)
PostgreSQL table optimized for time-series data using chunking.

**SARK usage:** audit_events table partitioned by timestamp

---

## I

### Idempotency
Property where performing an operation multiple times has same effect as performing it once.

**API:** Include `Idempotency-Key` header for server registration

### Immutable Audit Log
Audit record that cannot be modified or deleted after creation.

**Implementation:** TimescaleDB with append-only writes

### Incident Response
Structured approach to handling security incidents.

**SARK phases:** Detection → Containment → Eradication → Recovery → Post-mortem

---

## J

### JSON Schema
Standard for describing JSON data structures. Used for MCP tool parameters.

**Example:**
```json
{
  "type": "object",
  "properties": {
    "query": {"type": "string"}
  },
  "required": ["query"]
}
```

### JWT (JSON Web Token)
Compact, URL-safe token format for authentication.

**Structure:** `header.payload.signature`

**Algorithm:** RS256 (recommended) or HS256

---

## K

### Kafka
Distributed event streaming platform. Optional for SARK audit pipeline at scale.

**When needed:** >5,000 audit events/second

### Kong Gateway
API gateway that SARK uses for edge security and routing.

**Version:** 3.8+

**Features:** Rate limiting, authentication, MCP protocol validation

### Kong Mesh
Service mesh based on Kuma. Provides mTLS between SARK services.

**Alternative:** Istio (also supported)

### Kubernetes
Container orchestration platform. SARK's primary deployment target.

**Min version:** 1.28

---

## L

### Latency
Time between request and response. SARK targets <5ms p99 for policy evaluation.

**Measured:** p50 (median), p95 (95th percentile), p99 (99th percentile), p999

### Least Privilege
Security principle of granting minimum permissions necessary.

**Example:** Developer gets "tool:invoke" for low/medium tools, not admin rights

### Load Balancer
Distributes traffic across multiple servers.

**Cloud:** AWS ALB, GCP Load Balancer, Azure Load Balancer

### LRU Cache
Caching strategy that evicts Least Recently Used items when full.

**SARK L1 cache:** 1,000 entries, LRU eviction

---

## M

### MCP (Model Context Protocol)
Open protocol for AI assistants to access tools and data.

**Specification:** https://modelcontextprotocol.io

**Version:** 2025-06-18 (latest)

**See also:** [MCP (detailed)](#mcp-model-context-protocol) in Core Concepts section

### MCP Client
AI application or agent that connects to MCP servers to access tools, resources, and prompts.

**Examples:**
- Claude Desktop (Anthropic's desktop app)
- IDEs with AI integrations (VS Code, Cursor, Zed)
- Custom AI agents and chatbots
- Enterprise AI platforms

**Client responsibilities:**
- Discover available MCP servers
- Authenticate with servers or gateway
- Request tool execution and resource access
- Handle responses and present to users

**SARK integration:** Clients connect through SARK Gateway for authentication and authorization

### MCP Gateway
Proxy layer that sits between MCP clients and servers to enforce security policies.

**What SARK provides:**
- Authentication: Verify client identities (OIDC, LDAP, SAML, API keys)
- Authorization: Policy-based access control via OPA
- Audit: Log all tool invocations and resource accesses
- Rate limiting: Prevent abuse and DoS
- Discovery: Central registry of available MCP servers

**Architecture:** Clients → SARK Gateway → MCP Servers → Resources

### MCP Server
Service that implements MCP protocol to provide tools/resources to AI assistants.

**Transports:** HTTP, stdio, SSE (Server-Sent Events)

**Security concerns:**
- Servers run with host system permissions
- Tools can execute arbitrary code
- Resources may expose sensitive data
- No built-in authentication or authorization

**SARK solution:** All access goes through gateway with policy enforcement

### MCP Tool
Function exposed by MCP server that AI can invoke.

**Examples:** `database_query`, `send_email`, `create_ticket`

**Security:** SARK can restrict which users/roles can invoke which tools

### mTLS (Mutual TLS)
TLS where both client and server authenticate each other with certificates.

**SARK usage:** Service mesh communication (Kong Mesh/Istio)

---

## N

### Namespace (Kubernetes)
Logical partition of Kubernetes cluster. SARK uses `sark-system` namespace.

### Network Policy
Kubernetes firewall rules controlling pod-to-pod traffic.

**SARK:** Restricts traffic to only necessary connections

---

## O

### OAuth 2.0
Authorization framework for delegating access.

**Flows:** Authorization Code (recommended), Client Credentials (server-to-server)

### OIDC (OpenID Connect)
Authentication layer on top of OAuth 2.0.

**Providers:** Okta, Auth0, Azure AD, Google

### OPA (Open Policy Agent)
Policy engine that SARK uses for authorization decisions.

**Language:** Rego (declarative query language)

**Latency:** <10ms p99 target

### Observability
Ability to understand system state from external outputs.

**Pillars:** Metrics (Prometheus), Logs (structured logs), Traces (OpenTelemetry)

---

## P

### P50, P95, P99
Percentile measurements. P99 means 99% of requests are faster than this value.

**SARK targets:** P95 <50ms API response, P99 <5ms policy evaluation

### PagerDuty
Incident management platform for alerts.

**SARK integration:** Alert on policy failures, high error rates

### PII (Personally Identifiable Information)
Data that can identify an individual (name, email, SSN, etc.).

**SARK:** Automatic redaction in logs

### Pod
Smallest deployable unit in Kubernetes. Contains one or more containers.

**SARK components:** sark-api, opa, postgres, redis, etc.

### Policy
Rule that determines whether an action is allowed or denied.

**Language:** Rego (OPA)

**Types:** Authorization, validation, transformation

### Policy Decision Point (PDP)
Component that evaluates policies and makes authorization decisions.

**SARK PDP:** Open Policy Agent

### PostgreSQL
Relational database used for SARK's main data storage.

**Version:** 15+

**Extensions:** uuid-ossp, pgcrypto (for encryption)

### Prometheus
Monitoring system that collects and stores metrics.

**SARK metrics:** Request rates, latency, errors, cache hit rate

### Prompt Injection
Attack where malicious input manipulates AI behavior.

**SARK mitigation:** Input segregation, validation, output filtering

---

## Q

### Query Optimization
Improving database query performance.

**Techniques:** Indexing, query rewriting, connection pooling

---

## R

### Rate Limiting
Restricting number of requests from a client in a time period.

**SARK:** 1,000 requests/minute per API key (default)

### RBAC (Role-Based Access Control)
Access control based on user roles (admin, developer, viewer).

**Simpler than:** ABAC, ReBAC

### ReBAC (Relationship-Based Access Control)
Access control based on relationships (team membership, ownership).

**Example:** "Allow if user is member of team that manages tool"

### Redis
In-memory data store used for caching.

**Version:** 7+

**SARK usage:** Policy decisions, user attributes, rate limiting

### Rego
Declarative policy language for Open Policy Agent.

**Syntax:** Similar to Datalog/Prolog

**Example:** `allow if { input.user.role == "admin" }`

### Replica
Copy of a database for read scalability and high availability.

**PostgreSQL:** 2-5 read replicas recommended for production

### RPS (Requests Per Second)
Measure of API throughput.

**SARK targets:** 100 RPS (Phase 1) → 10,000+ RPS (Phase 4)

---

## S

### SARK
**S**ecurity **A**udit and **R**esource **K**ontroler - Enterprise MCP governance system.

### Secrets Management
Secure storage and distribution of sensitive data (passwords, API keys, certificates).

**SARK:** HashiCorp Vault (production), Kubernetes Secrets (development)

### Sensitivity Level
Data classification level.

**SARK levels:** Low, Medium, High, Critical

### Service Mesh
Infrastructure layer that handles service-to-service communication.

**SARK:** Kong Mesh (Kuma-based) or Istio

### Shadow IT
Unauthorized systems/services not managed by IT.

**SARK detection:** Network scanning, anomaly detection

### SIEM (Security Information and Event Management)
Platform that aggregates and analyzes security events.

**Integrations:** Splunk, Datadog, Sumo Logic, ElasticSearch

### SOC 2 (System and Organization Controls 2)
Audit framework for service providers' security controls.

**Types:** Type I (design), Type II (operational effectiveness over time)

### SQLAlchemy
Python SQL toolkit and ORM.

**SARK version:** 2.0+ (async support)

### SSE (Server-Sent Events)
HTTP-based protocol for server-to-client event streaming.

**MCP usage:** Alternative transport to HTTP request/response

### SSO (Single Sign-On)
Authentication scheme where one login provides access to multiple systems.

**SARK:** OIDC-based SSO with enterprise identity providers

---

## T

### Team
Group of users with shared permissions.

**Hierarchy:** Teams can have parent teams (organizational structure)

### TDE (Transparent Data Encryption)
Encryption of database files at rest.

**PostgreSQL:** Available in enterprise versions

### Throughput
Number of operations completed per time unit.

**See also:** [RPS](#rps-requests-per-second)

### TimescaleDB
PostgreSQL extension for time-series data.

**SARK usage:** audit_events table (100M+ events)

**Features:** Automatic partitioning (chunks), compression, retention policies

### TLS (Transport Layer Security)
Cryptographic protocol for secure communication.

**SARK:** TLS 1.3 minimum, mutual TLS for service mesh

### Tool (MCP)
Function that MCP server exposes for invocation.

**Required fields:** name, description, parameters (JSON Schema)

### Transport (MCP)
Communication method between client and MCP server.

**Types:** HTTP (remote), stdio (local process), SSE (streaming)

---

## U

### UUID (Universally Unique Identifier)
128-bit identifier guaranteed to be unique.

**Format:** `550e8400-e29b-41d4-a716-446655440000`

**SARK usage:** Primary keys for all entities

---

## V

### Vault
See [HashiCorp Vault](#hashicorp-vault)

---

## W

### WAF (Web Application Firewall)
Firewall that filters HTTP traffic to protect web applications.

**Recommended:** Cloudflare, AWS WAF, Azure WAF in front of SARK

### Webhook
HTTP callback triggered by events.

**SARK events:** server.registered, authorization.denied, policy.updated

### Workload Identity
Identity tied to workload (pod, service) rather than static credentials.

**Kubernetes:** Service account tokens automatically injected

---

## Z

### Zero-Trust
Security model where no user or service is trusted by default.

**Principles:** Verify explicitly, least privilege, assume breach

**SARK:** Every request authenticated and authorized, regardless of source

### Zero-Trust MCP
Application of zero-trust security principles to Model Context Protocol deployments.

**Key tenets:**
1. **Never trust, always verify**: Every MCP request requires authentication
2. **Least privilege**: Grant minimum permissions needed for each tool/resource
3. **Assume breach**: Log everything, detect anomalies, limit blast radius
4. **Explicit authorization**: Every tool invocation checked against policies
5. **Continuous validation**: Re-authenticate and re-authorize for sensitive operations

**SARK implementation:**
- **Identity verification**: Multi-factor authentication via OIDC/LDAP/SAML
- **Context-aware policies**: Consider user, time, location, sensitivity, risk score
- **Microsegmentation**: Isolate MCP servers in network segments
- **Least privilege access**: Default deny, explicitly grant tool permissions
- **Continuous monitoring**: Real-time anomaly detection, SIEM integration
- **Immutable audit**: All MCP interactions logged to TimescaleDB

**Architecture layers:**
```
┌─────────────────────────────────────────┐
│ User/Application (Authenticated)        │
└──────────────┬──────────────────────────┘
               │ 1. Authenticate
               ▼
┌─────────────────────────────────────────┐
│ SARK Gateway (AuthN + AuthZ)            │
│ - Verify identity (OIDC/LDAP)           │
│ - Check OPA policies                    │
│ - Log to audit trail                    │
└──────────────┬──────────────────────────┘
               │ 2. Authorized request
               ▼
┌─────────────────────────────────────────┐
│ MCP Server (Sandboxed)                  │
│ - Execute tool/access resource          │
│ - Limited permissions                   │
└──────────────┬──────────────────────────┘
               │ 3. Access data
               ▼
┌─────────────────────────────────────────┐
│ Protected Resource (Database/API/File)  │
└─────────────────────────────────────────┘
```

**Benefits:**
- Prevent lateral movement after compromise
- Detect and respond to suspicious tool usage
- Meet compliance requirements (SOC 2, ISO 27001)
- Reduce blast radius of compromised MCP servers

**See also:** [Zero-Trust](#zero-trust), [MCP Gateway](#mcp-gateway), [Defense in Depth](#defense-in-depth)

---

## Acronyms Quick Reference

| Acronym | Full Name |
|---------|-----------|
| ABAC | Attribute-Based Access Control |
| API | Application Programming Interface |
| CA | Certificate Authority |
| CIDR | Classless Inter-Domain Routing |
| DLP | Data Loss Prevention |
| DNS | Domain Name System |
| GDPR | General Data Protection Regulation |
| gRPC | gRPC Remote Procedure Call |
| HA | High Availability |
| HIPAA | Health Insurance Portability and Accountability Act |
| HPA | Horizontal Pod Autoscaler |
| HTTP | Hypertext Transfer Protocol |
| IAM | Identity and Access Management |
| IOC | Indicators of Compromise |
| IP | Internet Protocol |
| ISO | International Organization for Standardization |
| JSON | JavaScript Object Notation |
| JWT | JSON Web Token |
| K8s | Kubernetes (K + 8 letters + s) |
| MCP | Model Context Protocol |
| MFA | Multi-Factor Authentication |
| mTLS | Mutual Transport Layer Security |
| NIST | National Institute of Standards and Technology |
| OAuth | Open Authorization |
| OIDC | OpenID Connect |
| OPA | Open Policy Agent |
| OWASP | Open Web Application Security Project |
| PCI-DSS | Payment Card Industry Data Security Standard |
| PDP | Policy Decision Point |
| PII | Personally Identifiable Information |
| PKI | Public Key Infrastructure |
| RBAC | Role-Based Access Control |
| ReBAC | Relationship-Based Access Control |
| REST | Representational State Transfer |
| ROI | Return on Investment |
| RPS | Requests Per Second |
| RPO | Recovery Point Objective |
| RTO | Recovery Time Objective |
| SAML | Security Assertion Markup Language |
| SARK | Security Audit and Resource Kontroler |
| SDK | Software Development Kit |
| SIEM | Security Information and Event Management |
| SLA | Service Level Agreement |
| SOC | System and Organization Controls |
| SQL | Structured Query Language |
| SSE | Server-Sent Events |
| SSO | Single Sign-On |
| TDE | Transparent Data Encryption |
| TLS | Transport Layer Security |
| TTL | Time To Live |
| UUID | Universally Unique Identifier |
| VPC | Virtual Private Cloud |
| WAF | Web Application Firewall |
| WAL | Write-Ahead Log |

---

## See Also

- [Architecture Documentation](ARCHITECTURE.md) - System design overview
- [API Documentation](API_INTEGRATION.md) - Complete API reference
- [Security Guide](SECURITY.md) - Security best practices
- [FAQ](FAQ.md) - Frequently asked questions

---

**Document Version:** 1.0
**Last Updated:** November 2025
**Maintained By:** SARK Documentation Team
