# SARK Audit Event Schema Reference

Complete reference for SARK audit events, including field definitions, data types, constraints, and examples.

## Table of Contents

- [Overview](#overview)
- [Event Structure](#event-structure)
- [Core Fields](#core-fields)
- [Event Types](#event-types)
- [Severity Levels](#severity-levels)
- [Field Reference](#field-reference)
- [Details Object](#details-object)
- [SIEM Format](#siem-format)
- [Examples](#examples)
- [Best Practices](#best-practices)

## Overview

### Data Model

SARK audit events follow a structured schema designed for:
- **Security monitoring** - Track authorization and access patterns
- **Compliance** - Maintain audit trails for regulatory requirements
- **Forensics** - Investigate security incidents
- **Analytics** - Analyze usage patterns and trends

### Storage

Events are stored in:
- **Primary**: TimescaleDB (time-series database)
- **SIEM**: Splunk Cloud, Datadog Logs API
- **Fallback**: Newline-delimited JSON files (during SIEM outages)

### Format

Events are represented as:
- **Internal**: SQLAlchemy ORM objects (`AuditEvent`)
- **JSON**: For SIEM forwarding and API responses
- **Database**: PostgreSQL/TimescaleDB tables

## Event Structure

### High-Level Overview

```
AuditEvent
├── Identity (id, timestamp)
├── Classification (event_type, severity)
├── Actor (user_id, user_email)
├── Subject (server_id, tool_name)
├── Decision (decision, policy_id)
├── Context (ip_address, user_agent, request_id)
├── Details (flexible JSON object)
└── Metadata (siem_forwarded)
```

### JSON Representation

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-11-22T15:30:00.123456+00:00",
  "event_type": "tool_invoked",
  "severity": "medium",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "user_email": "user@example.com",
  "server_id": "789e0123-e45b-67d8-a901-234567890abc",
  "tool_name": "kubectl",
  "decision": "allow",
  "policy_id": "456e7890-e12b-34d5-a678-901234567def",
  "ip_address": "192.168.1.100",
  "user_agent": "SARK-Client/1.0",
  "request_id": "req-abc123",
  "details": {
    "command": "get pods -n production",
    "namespace": "production",
    "resource_type": "pods"
  },
  "siem_forwarded": "2025-11-22T15:30:01.000000+00:00"
}
```

## Core Fields

### Identity Fields

Fields that uniquely identify an event:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Unique event identifier (UUIDv4) |
| `timestamp` | DateTime (UTC) | Yes | When the event occurred (ISO 8601) |

### Classification Fields

Fields that categorize the event:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_type` | Enum | Yes | Type of event (see [Event Types](#event-types)) |
| `severity` | Enum | Yes | Severity level (default: `low`) |

### Actor Fields

Fields identifying who performed the action:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | UUID | No | User's unique identifier |
| `user_email` | String(255) | No | User's email address |

### Subject Fields

Fields identifying what was acted upon:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `server_id` | UUID | No | Server's unique identifier |
| `tool_name` | String(255) | No | Tool/resource name |

### Decision Fields

Fields capturing authorization decisions:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `decision` | String(20) | No | Authorization decision: `allow` or `deny` |
| `policy_id` | UUID | No | Policy that made the decision |

### Context Fields

Fields providing additional context:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ip_address` | String(45) | No | Client IP address (IPv4 or IPv6) |
| `user_agent` | String(500) | No | Client user agent string |
| `request_id` | String(100) | No | Request correlation ID |

### Flexible Fields

Fields for extensible data:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `details` | JSON Object | Yes | Event-specific details (default: `{}`) |

### Metadata Fields

Fields for operational metadata:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `siem_forwarded` | DateTime (UTC) | No | When event was forwarded to SIEM |

## Event Types

### Enumeration: `AuditEventType`

| Value | Description | Typical Severity | Example Use Case |
|-------|-------------|------------------|------------------|
| `server_registered` | Server registered in system | Low | New server onboarding |
| `server_updated` | Server configuration updated | Low | Server metadata changes |
| `server_decommissioned` | Server removed from system | Medium | Server retirement |
| `tool_invoked` | Tool/command executed | Low-High | kubectl, ssh, database query |
| `authorization_allowed` | Access request approved | Low-Medium | Successful authorization |
| `authorization_denied` | Access request denied | Medium-Critical | Failed authorization attempt |
| `policy_created` | Security policy created | Low | New policy definition |
| `policy_updated` | Security policy modified | Medium | Policy rule changes |
| `policy_activated` | Policy enabled/deployed | Medium | Policy goes live |
| `user_login` | User authenticated | Low | Successful login |
| `user_logout` | User session ended | Low | Logout or session timeout |
| `security_violation` | Security rule violated | High-Critical | Suspicious activity detected |
| `session_started` | New session started | Low | User session initialization |
| `session_ended` | Session terminated | Low | User session cleanup |

### Event Type Patterns

**Server Lifecycle:**
```
server_registered → server_updated* → server_decommissioned
```

**Policy Lifecycle:**
```
policy_created → policy_updated* → policy_activated
```

**User Session:**
```
user_login → tool_invoked* → user_logout
```

**Authorization Flow:**
```
tool_invoked → authorization_allowed/denied → [action execution]
```

## Severity Levels

### Enumeration: `SeverityLevel`

| Level | Value | Description | Response Time | Examples |
|-------|-------|-------------|---------------|----------|
| **Low** | `low` | Informational, routine operations | None | Normal tool usage, successful logins |
| **Medium** | `medium` | Notable events requiring awareness | Monitor | Policy changes, configuration updates |
| **High** | `high` | Important events requiring attention | Hours | Authorization denials, multiple failures |
| **Critical** | `critical` | Security incidents requiring immediate action | Minutes | Security violations, breach attempts |

### Severity Guidelines

**Use `low` for:**
- Normal operations
- Successful authorizations
- Routine tool invocations
- Regular server updates

**Use `medium` for:**
- Configuration changes
- Policy modifications
- Unusual but not suspicious activity
- Expected authorization denials

**Use `high` for:**
- Multiple authorization failures
- Access to sensitive resources
- Privilege escalation attempts
- Abnormal usage patterns

**Use `critical` for:**
- Security violations detected
- Potential data breaches
- Malicious activity
- Compliance violations

## Field Reference

### `id` (UUID)

**Type:** UUIDv4
**Required:** Yes
**Database:** Primary key
**Format:** `xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`

**Description:**
Globally unique identifier for the event. Generated automatically using UUIDv4.

**Example:**
```json
"id": "550e8400-e29b-41d4-a716-446655440000"
```

**Usage:**
- Event correlation across systems
- Deduplication
- Retrieval and reference

---

### `timestamp` (DateTime)

**Type:** Datetime with timezone (UTC)
**Required:** Yes
**Database:** Indexed, hypertable partition key
**Format:** ISO 8601 with microseconds

**Description:**
When the event occurred. Automatically set to current UTC time if not provided.

**Example:**
```json
"timestamp": "2025-11-22T15:30:00.123456+00:00"
```

**Notes:**
- Always stored in UTC
- Microsecond precision
- Used for TimescaleDB partitioning
- Critical for time-series queries

---

### `event_type` (AuditEventType)

**Type:** Enum (string)
**Required:** Yes
**Database:** Indexed
**Values:** See [Event Types](#event-types)

**Description:**
Categorizes the type of event for filtering and analysis.

**Example:**
```json
"event_type": "tool_invoked"
```

**Usage:**
- Event filtering in searches
- Dashboard categorization
- Alert routing
- Compliance reporting

---

### `severity` (SeverityLevel)

**Type:** Enum (string)
**Required:** Yes (default: `low`)
**Values:** `low`, `medium`, `high`, `critical`

**Description:**
Indicates the importance and urgency of the event.

**Example:**
```json
"severity": "high"
```

**Usage:**
- Alert prioritization
- Incident response
- Compliance reporting
- Security monitoring

---

### `user_id` (UUID)

**Type:** UUID
**Required:** No
**Database:** Indexed
**Foreign Key:** References `users.id`

**Description:**
Unique identifier of the user who triggered the event.

**Example:**
```json
"user_id": "123e4567-e89b-12d3-a456-426614174000"
```

**Usage:**
- User activity tracking
- Access analysis
- Compliance auditing

**Null when:**
- System-generated events
- Anonymous operations
- User not yet identified

---

### `user_email` (String)

**Type:** String (max 255 characters)
**Required:** No
**Validation:** Email format recommended

**Description:**
Email address of the user who triggered the event.

**Example:**
```json
"user_email": "user@example.com"
```

**Usage:**
- Human-readable user identification
- Reporting
- Notifications

**Notes:**
- May change if user updates email
- Use `user_id` for stable references

---

### `server_id` (UUID)

**Type:** UUID
**Required:** No
**Database:** Indexed
**Foreign Key:** References `servers.id`

**Description:**
Unique identifier of the server involved in the event.

**Example:**
```json
"server_id": "789e0123-e45b-67d8-a901-234567890abc"
```

**Usage:**
- Server activity tracking
- Resource access monitoring
- Incident investigation

**Null when:**
- Event not related to a specific server
- Global system events

---

### `tool_name` (String)

**Type:** String (max 255 characters)
**Required:** No
**Database:** Indexed

**Description:**
Name of the tool or resource being accessed.

**Example:**
```json
"tool_name": "kubectl"
```

**Common values:**
- `kubectl` - Kubernetes CLI
- `ssh` - SSH access
- `psql` - PostgreSQL client
- `mysql` - MySQL client
- `redis-cli` - Redis client
- `mongo` - MongoDB shell

**Usage:**
- Tool usage analytics
- Access pattern analysis
- Security monitoring

---

### `decision` (String)

**Type:** String (max 20 characters)
**Required:** No
**Values:** Typically `allow` or `deny`

**Description:**
Authorization decision made by the policy engine.

**Example:**
```json
"decision": "allow"
```

**Usage:**
- Authorization auditing
- Compliance reporting
- Security analysis

**Null when:**
- Event doesn't involve authorization
- Decision not yet made

---

### `policy_id` (UUID)

**Type:** UUID
**Required:** No
**Foreign Key:** References `policies.id`

**Description:**
Identifier of the policy that made the authorization decision.

**Example:**
```json
"policy_id": "456e7890-e12b-34d5-a678-901234567def"
```

**Usage:**
- Policy effectiveness analysis
- Compliance verification
- Audit trail

---

### `ip_address` (String)

**Type:** String (max 45 characters)
**Required:** No
**Format:** IPv4 or IPv6

**Description:**
IP address of the client that triggered the event.

**Examples:**
```json
"ip_address": "192.168.1.100"          // IPv4
"ip_address": "2001:0db8:85a3::8a2e:0370:7334"  // IPv6
```

**Usage:**
- Geographic analysis
- Security monitoring
- Threat detection
- Access patterns

**Notes:**
- May be NAT'd or proxied
- Consider X-Forwarded-For headers
- GDPR considerations for retention

---

### `user_agent` (String)

**Type:** String (max 500 characters)
**Required:** No

**Description:**
User agent string from the client application.

**Example:**
```json
"user_agent": "SARK-Client/1.0.0 (Linux; kubectl/1.28.0)"
```

**Usage:**
- Client identification
- Version tracking
- Compatibility analysis

---

### `request_id` (String)

**Type:** String (max 100 characters)
**Required:** No
**Database:** Indexed

**Description:**
Correlation ID for request tracing across services.

**Example:**
```json
"request_id": "req-abc123-def456"
```

**Usage:**
- Distributed tracing
- Request correlation
- Debugging
- Log aggregation

**Format:**
- Application-specific
- Should be unique per request
- Recommended: `req-{uuid}` or similar

---

### `details` (JSON Object)

**Type:** JSON Object
**Required:** Yes (default: `{}`)
**Schema:** Flexible, event-type specific

**Description:**
Flexible storage for event-specific details. Structure varies by event type.

**Example:**
```json
"details": {
  "command": "get pods -n production",
  "namespace": "production",
  "exit_code": 0,
  "duration_ms": 145,
  "output_lines": 23
}
```

**Usage:**
- Store event-specific data
- Capture rich context
- Support forensic analysis

**See:** [Details Object](#details-object) for common patterns

---

### `siem_forwarded` (DateTime)

**Type:** Datetime with timezone (UTC)
**Required:** No
**Automatically set:** Yes

**Description:**
Timestamp when the event was successfully forwarded to SIEM platform.

**Example:**
```json
"siem_forwarded": "2025-11-22T15:30:01.234567+00:00"
```

**Usage:**
- SIEM sync verification
- Reprocessing detection
- Audit trail

**Null when:**
- Event not yet forwarded
- SIEM forwarding disabled
- Forwarding failed

## Details Object

The `details` field is a flexible JSON object that varies by event type. Here are common patterns:

### Tool Invocation

```json
{
  "command": "kubectl get pods -n production",
  "args": ["get", "pods", "-n", "production"],
  "namespace": "production",
  "resource_type": "pods",
  "exit_code": 0,
  "duration_ms": 145,
  "output_lines": 23,
  "output_bytes": 4562,
  "environment": {
    "KUBECONFIG": "/home/user/.kube/config"
  }
}
```

### Server Registration

```json
{
  "server_name": "production-db-01",
  "server_type": "postgresql",
  "hostname": "db01.prod.example.com",
  "port": 5432,
  "tags": ["production", "database", "postgres"],
  "connection_string": "postgresql://db01.prod.example.com:5432",
  "metadata": {
    "region": "us-east-1",
    "environment": "production",
    "tier": "critical"
  }
}
```

### Authorization Decision

```json
{
  "requested_action": "read",
  "resource_type": "database",
  "resource_id": "prod-db-01",
  "policy_name": "database-read-policy",
  "policy_version": "v1.2.3",
  "evaluation_time_ms": 12,
  "matched_rules": [
    "allow-prod-read",
    "require-vpn"
  ],
  "conditions_met": true,
  "justification": "User has read access to production databases"
}
```

### Security Violation

```json
{
  "violation_type": "unauthorized_access_attempt",
  "attempted_action": "write",
  "resource": "production-secrets",
  "detection_method": "policy_evaluation",
  "risk_score": 85,
  "indicators": [
    "multiple_failed_attempts",
    "privilege_escalation",
    "unusual_time"
  ],
  "remediation": "account_locked",
  "notification_sent": true
}
```

### Policy Change

```json
{
  "policy_name": "database-access-policy",
  "policy_version_old": "v1.2.3",
  "policy_version_new": "v1.2.4",
  "changes": [
    {
      "field": "rules.allow_production",
      "old_value": false,
      "new_value": true,
      "reason": "Production access approved"
    }
  ],
  "changed_by": "admin@example.com",
  "approved_by": "security-lead@example.com",
  "change_ticket": "CHG-12345"
}
```

### Session Events

```json
{
  "session_id": "sess-abc123-def456",
  "session_duration_seconds": 3600,
  "authentication_method": "oauth2",
  "mfa_verified": true,
  "client_ip": "192.168.1.100",
  "client_location": {
    "country": "US",
    "region": "California",
    "city": "San Francisco"
  },
  "activity_summary": {
    "tools_used": ["kubectl", "psql"],
    "commands_executed": 45,
    "data_accessed_mb": 23.5
  }
}
```

## SIEM Format

### Splunk HEC Format

Events sent to Splunk use the HTTP Event Collector format:

```json
{
  "time": 1700662200.123456,
  "source": "sark",
  "sourcetype": "sark:audit:event",
  "index": "sark_production",
  "host": "sark-prod-01",
  "event": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-11-22T15:30:00.123456+00:00",
    "event_type": "tool_invoked",
    "severity": "medium",
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_email": "user@example.com",
    "server_id": "789e0123-e45b-67d8-a901-234567890abc",
    "tool_name": "kubectl",
    "decision": "allow",
    "policy_id": "456e7890-e12b-34d5-a678-901234567def",
    "ip_address": "192.168.1.100",
    "user_agent": "SARK-Client/1.0",
    "request_id": "req-abc123",
    "details": {
      "command": "get pods -n production",
      "namespace": "production"
    }
  }
}
```

**Key fields:**
- `time`: Unix epoch timestamp (float with fractional seconds)
- `event`: Nested audit event object
- `source`, `sourcetype`, `index`, `host`: Splunk metadata

### Datadog Logs API Format

Events sent to Datadog use the Logs API format:

```json
{
  "ddsource": "sark",
  "ddtags": "env:production,service:sark,event_type:tool_invoked,severity:medium",
  "service": "sark",
  "hostname": "sark-prod-01",
  "message": "SARK audit event: tool_invoked",
  "timestamp": 1700662200123,
  "sark": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-11-22T15:30:00.123456+00:00",
    "event_type": "tool_invoked",
    "severity": "medium",
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_email": "user@example.com",
    "server_id": "789e0123-e45b-67d8-a901-234567890abc",
    "tool_name": "kubectl",
    "decision": "allow",
    "policy_id": "456e7890-e12b-34d5-a678-901234567def",
    "ip_address": "192.168.1.100",
    "user_agent": "SARK-Client/1.0",
    "request_id": "req-abc123",
    "details": {
      "command": "get pods -n production",
      "namespace": "production"
    }
  },
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "tool_invoked",
  "severity": "medium",
  "user_email": "user@example.com",
  "decision": "allow"
}
```

**Key fields:**
- `ddtags`: Comma-separated tags for filtering
- `timestamp`: Unix epoch in milliseconds
- `sark`: Nested audit event object
- Top-level fields for searchability

## Examples

### Example 1: Successful Tool Invocation

```json
{
  "id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "timestamp": "2025-11-22T15:30:00.000000+00:00",
  "event_type": "tool_invoked",
  "severity": "low",
  "user_id": "u1234567-89ab-cdef-0123-456789abcdef",
  "user_email": "alice@example.com",
  "server_id": "s7654321-fedc-ba98-7654-321098765432",
  "tool_name": "kubectl",
  "decision": "allow",
  "policy_id": "p9876543-210f-edcb-a987-654321fedcba",
  "ip_address": "192.168.1.50",
  "user_agent": "kubectl/1.28.0",
  "request_id": "req-20251122-153000-001",
  "details": {
    "command": "get pods -n production",
    "namespace": "production",
    "exit_code": 0,
    "duration_ms": 123
  },
  "siem_forwarded": "2025-11-22T15:30:01.000000+00:00"
}
```

### Example 2: Authorization Denied

```json
{
  "id": "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e",
  "timestamp": "2025-11-22T16:45:00.000000+00:00",
  "event_type": "authorization_denied",
  "severity": "high",
  "user_id": "u2345678-90ab-cdef-0123-456789abcdef",
  "user_email": "bob@example.com",
  "server_id": "s8765432-fedc-ba98-7654-321098765432",
  "tool_name": "psql",
  "decision": "deny",
  "policy_id": "p0987654-321f-edcb-a987-654321fedcba",
  "ip_address": "203.0.113.45",
  "user_agent": "psql/15.0",
  "request_id": "req-20251122-164500-002",
  "details": {
    "requested_action": "write",
    "resource": "production-database",
    "reason": "User lacks write permission to production",
    "policy_rule": "deny-production-write"
  },
  "siem_forwarded": "2025-11-22T16:45:01.000000+00:00"
}
```

### Example 3: Security Violation

```json
{
  "id": "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f",
  "timestamp": "2025-11-22T23:15:00.000000+00:00",
  "event_type": "security_violation",
  "severity": "critical",
  "user_id": "u3456789-01ab-cdef-0123-456789abcdef",
  "user_email": "suspicious@example.com",
  "server_id": null,
  "tool_name": null,
  "decision": "deny",
  "policy_id": null,
  "ip_address": "198.51.100.78",
  "user_agent": "curl/7.68.0",
  "request_id": "req-20251122-231500-003",
  "details": {
    "violation_type": "brute_force_attempt",
    "failed_attempts": 50,
    "time_window_seconds": 60,
    "targeted_accounts": ["admin", "root", "sysadmin"],
    "detection_method": "rate_limiting",
    "action_taken": "ip_blocked",
    "block_duration_seconds": 3600
  },
  "siem_forwarded": "2025-11-22T23:15:02.000000+00:00"
}
```

### Example 4: Server Registration

```json
{
  "id": "d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f8a",
  "timestamp": "2025-11-22T10:00:00.000000+00:00",
  "event_type": "server_registered",
  "severity": "low",
  "user_id": "u4567890-12ab-cdef-0123-456789abcdef",
  "user_email": "admin@example.com",
  "server_id": "s9876543-210f-edcb-a987-654321fedcba",
  "tool_name": null,
  "decision": null,
  "policy_id": null,
  "ip_address": "192.168.1.100",
  "user_agent": "SARK-Admin/2.0",
  "request_id": "req-20251122-100000-004",
  "details": {
    "server_name": "production-api-03",
    "server_type": "api",
    "hostname": "api03.prod.example.com",
    "port": 443,
    "tags": ["production", "api", "tier-1"],
    "region": "us-east-1",
    "environment": "production"
  },
  "siem_forwarded": "2025-11-22T10:00:01.000000+00:00"
}
```

## Best Practices

### Event Creation

**DO:**
- ✅ Always set `event_type` and `severity`
- ✅ Include `user_id` or `user_email` when known
- ✅ Set `request_id` for request correlation
- ✅ Use `details` for event-specific data
- ✅ Set appropriate severity levels
- ✅ Include context (IP, user agent) when available

**DON'T:**
- ❌ Store sensitive data (passwords, secrets) in `details`
- ❌ Use `details` for structured fields that should be top-level
- ❌ Set severity too high for routine events
- ❌ Omit timestamps (let them auto-generate)

### Field Population

**Required fields:**
- `id` (auto-generated if not provided)
- `timestamp` (auto-generated if not provided)
- `event_type`
- `severity` (defaults to `low`)
- `details` (defaults to `{}`)

**Recommended fields:**
- `user_id` or `user_email` (for user-triggered events)
- `server_id` (for server-related events)
- `tool_name` (for tool invocations)
- `decision` (for authorization events)
- `ip_address` (for security analysis)
- `request_id` (for tracing)

### Details Object

**Structure:**
- Use nested objects for related data
- Keep keys lowercase with underscores
- Include units in field names (e.g., `duration_ms`, `size_bytes`)
- Store timestamps as ISO 8601 strings
- Use arrays for lists

**Example:**
```json
"details": {
  "server": {
    "name": "prod-db-01",
    "region": "us-east-1"
  },
  "metrics": {
    "duration_ms": 145,
    "bytes_transferred": 4562
  },
  "tags": ["production", "critical"]
}
```

### SIEM Forwarding

**Automatic:**
- Events are automatically forwarded to configured SIEM platforms
- `siem_forwarded` is set when forwarding succeeds
- Failed forwards are retried with exponential backoff
- During outages, events are logged to fallback files

**Manual:**
- Don't manually set `siem_forwarded`
- Let the system handle forwarding
- Monitor forwarding metrics

### Privacy and Compliance

**PII Handling:**
- `user_email` may be considered PII
- `ip_address` may be considered PII
- Check compliance requirements (GDPR, CCPA)
- Implement retention policies
- Support data deletion requests

**Sensitive Data:**
- Never log passwords, API keys, or secrets
- Redact sensitive data in `details`
- Be careful with command-line arguments
- Sanitize output and logs

### Performance

**Indexing:**
- Key fields are indexed: `timestamp`, `event_type`, `user_id`, `server_id`, `tool_name`, `request_id`
- Use indexed fields in queries for performance
- Avoid complex JSON queries on `details`

**Storage:**
- TimescaleDB partitions by `timestamp`
- Configure retention policies
- Monitor index size
- Archive old data

---

**Last Updated:** 2025-11-22
**Schema Version:** 1.0
**Maintained By:** SARK Engineering Team
