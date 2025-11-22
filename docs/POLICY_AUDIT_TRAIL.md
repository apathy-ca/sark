# Policy Audit Trail

## Overview

The SARK policy audit trail provides comprehensive logging and analytics for all policy evaluation decisions and policy changes. This system ensures complete compliance visibility, troubleshooting capabilities, and decision pattern analysis.

## Features

### 1. Policy Decision Logging
- **Complete Audit Trail**: Every policy evaluation is logged with full context
- **Performance Metrics**: Evaluation duration and cache hit tracking
- **Advanced Policy Context**: Time-based, IP filtering, and MFA checks logged
- **Compliance Tagging**: Flexible tagging for compliance categorization
- **SIEM Integration**: Ready for SIEM export

### 2. Policy Change Tracking
- **Version Control**: Automatic versioning for all policy changes
- **Diff Generation**: Unified diff between policy versions
- **Change Approval**: Track approvers and approval IDs
- **Breaking Change Flags**: Mark potentially disruptive changes
- **Deployment Tracking**: Log deployment status and timestamps

### 3. Analytics & Reporting
- **Decision Patterns**: Analyze allow/deny rates and trends
- **Performance Metrics**: Track P50/P95/P99 latency
- **Cache Analytics**: Monitor cache hit rates
- **Denial Analysis**: Identify top denial reasons
- **Time-Series Trends**: Visualize metrics over time

### 4. Export Capabilities
- **CSV Export**: Excel-compatible CSV format
- **JSON Export**: Complete data export with all details
- **Filtered Exports**: Export specific time ranges and criteria
- **Compliance Reports**: Ready-to-use compliance documentation

## Database Models

### PolicyDecisionLog

Tracks every policy evaluation decision with complete context.

**Key Fields:**
```python
- timestamp: When the decision was made (TimescaleDB partitioned)
- result: allow/deny/error
- user_id, user_role, user_teams: User context
- action: What action was requested
- tool_id, tool_name, sensitivity_level: Tool context
- policies_evaluated: List of policies checked
- policy_results: Detailed results from each policy
- violations: List of policy violations
- reason: Human-readable explanation
- evaluation_duration_ms: Performance metric
- cache_hit: Whether cached decision was used
- client_ip, geo_country: Network context
- mfa_verified, mfa_method: MFA context
- time_based_allowed, ip_filtering_allowed, mfa_required_satisfied: Advanced policy results
```

**Indexes:**
- timestamp (TimescaleDB hypertable)
- user_id
- action
- tool_id
- sensitivity_level
- result
- cache_hit

### PolicyChangeLog

Tracks all changes to OPA policies with versioning.

**Key Fields:**
```python
- timestamp: When the change occurred
- change_type: created/updated/activated/deactivated/deleted
- policy_name: Name of the policy
- policy_version: Auto-incrementing version number
- changed_by_user_id: Who made the change
- policy_content: Full policy content (Rego)
- policy_diff: Unified diff from previous version
- policy_hash: SHA-256 hash of content
- change_reason: Why the change was made
- approver_user_id: Who approved the change
- breaking_change: Flag for disruptive changes
- deployed_at: When deployed to production
```

### PolicyAnalyticsSummary

Pre-computed hourly analytics for fast dashboard queries.

**Key Fields:**
```python
- time_bucket: Hour bucket for aggregation
- action, sensitivity_level, user_role: Grouping dimensions
- total_evaluations, total_allows, total_denies, total_errors: Counts
- cache_hits, cache_misses, cache_hit_rate: Cache metrics
- avg_duration_ms, p50/p95/p99_duration_ms: Performance metrics
- top_denial_reasons: Most common denial reasons
- rbac_violations, team_access_violations, etc.: Violation counts by policy
```

## API Endpoints

### Decision Logs

#### GET /api/v1/policy/audit/decisions
Query policy decision logs with filters.

**Parameters:**
- `start_time`: Start of time range (ISO 8601)
- `end_time`: End of time range (ISO 8601)
- `user_id`: Filter by user ID
- `action`: Filter by action
- `result`: Filter by result (allow/deny/error)
- `limit`: Maximum results (1-1000, default: 100)
- `offset`: Pagination offset

**Example:**
```bash
GET /api/v1/policy/audit/decisions?user_id=user123&result=deny&limit=50
```

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2024-01-15T10:30:00Z",
    "result": "deny",
    "allow": false,
    "user_id": "user123",
    "user_role": "developer",
    "action": "tool:invoke",
    "tool_name": "sensitive_tool",
    "sensitivity_level": "critical",
    "reason": "MFA requirements not met",
    "evaluation_duration_ms": 42.5,
    "cache_hit": false,
    "client_ip": "10.0.0.100",
    "mfa_verified": false
  }
]
```

#### GET /api/v1/policy/audit/decisions/{decision_id}
Get detailed information about a specific decision.

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-15T10:30:00Z",
  "result": "deny",
  "allow": false,
  "user": {
    "id": "user123",
    "role": "developer",
    "teams": ["team-1", "team-2"]
  },
  "action": "tool:invoke",
  "policies_evaluated": ["rbac", "team_access", "mfa_required"],
  "policy_results": {
    "rbac": {"allow": true, "reason": "Role authorized"},
    "team_access": {"allow": true, "reason": "Team member"},
    "mfa_required": {"allow": false, "reason": "MFA not verified"}
  },
  "violations": [
    {
      "type": "mfa_not_verified",
      "reason": "Multi-factor authentication required but not verified"
    }
  ],
  "advanced_policy_checks": {
    "time_based_allowed": true,
    "ip_filtering_allowed": true,
    "mfa_required_satisfied": false
  }
}
```

### Policy Changes

#### GET /api/v1/policy/audit/policy-changes
Query policy change history.

**Parameters:**
- `policy_name`: Filter by policy name
- `start_time`: Start of time range
- `end_time`: End of time range
- `change_type`: Filter by change type
- `limit`: Maximum results (1-1000, default: 100)

**Example:**
```bash
GET /api/v1/policy/audit/policy-changes?policy_name=rbac&limit=20
```

**Response:**
```json
[
  {
    "id": "660f9500-f39c-52e5-b827-557766551111",
    "timestamp": "2024-01-15T09:00:00Z",
    "change_type": "updated",
    "policy_name": "rbac",
    "policy_version": 5,
    "changed_by_user_id": "admin123",
    "change_reason": "Add new admin role permissions",
    "breaking_change": false,
    "deployed_at": "2024-01-15T09:15:00Z"
  }
]
```

#### GET /api/v1/policy/audit/policy-changes/{change_id}
Get detailed information about a policy change.

**Parameters:**
- `include_diff`: Include policy diff (boolean)

**Response:**
```json
{
  "id": "660f9500-f39c-52e5-b827-557766551111",
  "timestamp": "2024-01-15T09:00:00Z",
  "change_type": "updated",
  "policy_name": "rbac",
  "policy_version": 5,
  "changed_by_user_id": "admin123",
  "change_reason": "Add new admin role permissions",
  "policy_hash": "a3b5c7d9e1f2...",
  "approver_user_id": "manager456",
  "deployed_at": "2024-01-15T09:15:00Z",
  "policy_diff": "--- previous\n+++ current\n@@ -10,0 +11 @@\n+allow if { input.user.role == \"super_admin\" }"
}
```

### Export

#### POST /api/v1/policy/audit/export/csv
Export policy decisions to CSV format.

**Request:**
```json
{
  "start_time": "2024-01-01T00:00:00Z",
  "end_time": "2024-01-31T23:59:59Z",
  "filters": {
    "user_id": "user123",
    "result": "deny"
  }
}
```

**Response:**
Downloads CSV file: `policy_decisions_20240101_20240131.csv`

**CSV Format:**
```csv
timestamp,result,user_id,user_role,action,resource_type,tool_name,sensitivity_level,reason,duration_ms,cache_hit,client_ip,mfa_verified
2024-01-15T10:30:00Z,deny,user123,developer,tool:invoke,tool,sensitive_tool,critical,MFA requirements not met,42.5,false,10.0.0.100,false
```

#### POST /api/v1/policy/audit/export/json
Export policy decisions to JSON format.

**Request:**
```json
{
  "start_time": "2024-01-01T00:00:00Z",
  "end_time": "2024-01-31T23:59:59Z"
}
```

**Response:**
Downloads JSON file: `policy_decisions_20240101_20240131.json`

### Analytics

#### GET /api/v1/policy/audit/analytics
Get aggregated policy evaluation analytics.

**Parameters:**
- `start_time`: Start of time range
- `end_time`: End of time range
- `group_by`: Dimensions to group by (action, sensitivity_level, user_role)

**Example:**
```bash
GET /api/v1/policy/audit/analytics?group_by=action&group_by=sensitivity_level
```

**Response:**
```json
{
  "period": {
    "start": "2024-01-15T00:00:00Z",
    "end": "2024-01-16T00:00:00Z"
  },
  "summary": {
    "total_evaluations": 10543,
    "total_allows": 9821,
    "total_denies": 722,
    "allow_rate": 93.15,
    "deny_rate": 6.85
  },
  "cache_performance": {
    "total_hits": 8434,
    "total_misses": 2109,
    "hit_rate": 80.0
  },
  "latency": {
    "avg_ms": 12.5,
    "p50_ms": 8.2,
    "p95_ms": 42.1,
    "p99_ms": 68.4
  },
  "grouped": {
    "action": {
      "tool:invoke": {"total": 8500, "allows": 8100, "denies": 400},
      "server:register": {"total": 2043, "allows": 1721, "denies": 322}
    },
    "sensitivity_level": {
      "low": {"total": 3200, "allows": 3180, "denies": 20},
      "medium": {"total": 4500, "allows": 4350, "denies": 150},
      "high": {"total": 2343, "allows": 2091, "denies": 252},
      "critical": {"total": 500, "allows": 200, "denies": 300}
    }
  }
}
```

#### GET /api/v1/policy/audit/analytics/denial-reasons
Get top denial reasons with counts.

**Parameters:**
- `start_time`: Start of time range
- `end_time`: End of time range
- `limit`: Number of top reasons (1-50, default: 10)

**Example:**
```bash
GET /api/v1/policy/audit/analytics/denial-reasons?limit=20
```

**Response:**
```json
[
  {
    "reason": "MFA requirements not met: Multi-factor authentication required but not verified",
    "count": 245
  },
  {
    "reason": "Time restrictions violated: Critical tools require business hours access",
    "count": 189
  },
  {
    "reason": "Access denied by RBAC: Insufficient permissions",
    "count": 156
  }
]
```

#### GET /api/v1/policy/audit/analytics/trends
Get trends for metrics over time.

**Parameters:**
- `metric`: Metric to analyze (allow_rate, deny_rate, cache_hit_rate, avg_latency)
- `interval`: Time interval (1h, 6h, 1d)
- `start_time`: Start of time range
- `end_time`: End of time range

**Example:**
```bash
GET /api/v1/policy/audit/analytics/trends?metric=cache_hit_rate&interval=1h
```

**Response:**
```json
{
  "metric": "cache_hit_rate",
  "interval": "1h",
  "data": [
    {
      "timestamp": "2024-01-15T00:00:00Z",
      "value": 78.5,
      "total_evaluations": 1543
    },
    {
      "timestamp": "2024-01-15T01:00:00Z",
      "value": 81.2,
      "total_evaluations": 1621
    }
  ]
}
```

## Usage Examples

### Python Client

```python
import httpx
from datetime import datetime, timedelta

async def get_user_denials(user_id: str):
    """Get all denials for a specific user in the last 24 hours."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/v1/policy/audit/decisions",
            params={
                "user_id": user_id,
                "result": "deny",
                "start_time": (datetime.utcnow() - timedelta(days=1)).isoformat(),
                "limit": 100,
            },
        )
        return response.json()

async def export_compliance_report():
    """Export last month's decisions for compliance."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/policy/audit/export/csv",
            json={
                "start_time": (datetime.utcnow() - timedelta(days=30)).isoformat(),
                "end_time": datetime.utcnow().isoformat(),
            },
        )
        with open("compliance_report.csv", "wb") as f:
            f.write(response.content)

async def get_performance_analytics():
    """Get performance analytics for the last 7 days."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/v1/policy/audit/analytics",
            params={
                "start_time": (datetime.utcnow() - timedelta(days=7)).isoformat(),
                "group_by": ["action", "sensitivity_level"],
            },
        )
        return response.json()
```

### cURL Examples

```bash
# Get denied decisions for a user
curl -X GET "http://localhost:8000/api/v1/policy/audit/decisions?user_id=user123&result=deny" \
  -H "accept: application/json"

# Get policy change history
curl -X GET "http://localhost:8000/api/v1/policy/audit/policy-changes?policy_name=rbac" \
  -H "accept: application/json"

# Export to CSV
curl -X POST "http://localhost:8000/api/v1/policy/audit/export/csv" \
  -H "Content-Type: application/json" \
  -d '{"start_time": "2024-01-01T00:00:00Z", "end_time": "2024-01-31T23:59:59Z"}' \
  -o policy_decisions.csv

# Get analytics
curl -X GET "http://localhost:8000/api/v1/policy/audit/analytics?group_by=action" \
  -H "accept: application/json"

# Get denial reasons
curl -X GET "http://localhost:8000/api/v1/policy/audit/analytics/denial-reasons?limit=10" \
  -H "accept: application/json"

# Get trends
curl -X GET "http://localhost:8000/api/v1/policy/audit/analytics/trends?metric=cache_hit_rate&interval=1h" \
  -H "accept: application/json"
```

## Integration with Policy Evaluation

The audit service is automatically integrated with policy evaluation:

```python
from sark.services.policy.opa_client import OPAClient
from sark.services.policy.audit import PolicyAuditService

# Evaluate policy and log decision
decision = await opa_client.evaluate_policy(auth_input)

# Log the decision
await audit_service.log_decision(
    auth_input=auth_input,
    decision=decision,
    duration_ms=evaluation_duration,
    cache_hit=was_cache_hit,
)
```

## TimescaleDB Integration

Policy decision logs use TimescaleDB hypertables for efficient time-series storage:

```sql
-- Create hypertable (automatic in migrations)
SELECT create_hypertable('policy_decision_logs', 'timestamp');

-- Create compression policy (retain raw data for 90 days)
SELECT add_compression_policy('policy_decision_logs', INTERVAL '90 days');

-- Create retention policy (keep data for 1 year)
SELECT add_retention_policy('policy_decision_logs', INTERVAL '1 year');

-- Create continuous aggregates for analytics
CREATE MATERIALIZED VIEW policy_hourly_stats
WITH (timescaledb.continuous) AS
SELECT
  time_bucket('1 hour', timestamp) AS bucket,
  action,
  sensitivity_level,
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE allow = true) AS allows,
  COUNT(*) FILTER (WHERE allow = false) AS denies,
  AVG(evaluation_duration_ms) AS avg_duration,
  percentile_cont(0.95) WITHIN GROUP (ORDER BY evaluation_duration_ms) AS p95_duration
FROM policy_decision_logs
GROUP BY bucket, action, sensitivity_level;
```

## Best Practices

### 1. Regular Exports
Export audit logs regularly for compliance and backup:
```bash
# Daily export job
0 2 * * * curl -X POST http://localhost:8000/api/v1/policy/audit/export/json \
  -d '{"start_time": "$(date -d "yesterday" +%Y-%m-%d)T00:00:00Z"}' \
  -o /backup/audit/$(date +%Y%m%d).json
```

### 2. Monitor Denial Patterns
Set up alerts for unusual denial patterns:
```python
# Alert if denial rate exceeds 20%
analytics = await audit_service.get_decision_analytics(
    start_time=datetime.utcnow() - timedelta(hours=1),
    end_time=datetime.utcnow(),
)
if analytics["summary"]["deny_rate"] > 20:
    send_alert("High denial rate detected")
```

### 3. Performance Monitoring
Track policy evaluation performance:
```python
# Alert if P95 latency exceeds 100ms
if analytics["latency"]["p95_ms"] > 100:
    send_alert("Policy evaluation latency degraded")
```

### 4. Compliance Reporting
Generate monthly compliance reports:
```python
# Monthly compliance report
start = datetime.utcnow().replace(day=1)
end = start + timedelta(days=31)
await export_decisions_csv(start_time=start, end_time=end)
```

## Performance Considerations

- **Indexing**: All frequently-queried fields are indexed
- **Partitioning**: TimescaleDB automatically partitions by time
- **Compression**: Old data is automatically compressed
- **Retention**: Configurable retention policies (default: 1 year)
- **Aggregation**: Pre-computed hourly statistics for fast dashboard queries

## Security & Compliance

- **Immutable Logs**: Audit logs cannot be modified once created
- **Complete Context**: All decision context is captured
- **SIEM Ready**: Export format compatible with SIEM systems
- **Privacy**: Sensitive data (passwords, tokens) never logged
- **Encryption**: Supports database-level encryption at rest
- **Access Control**: API endpoints require authentication

## Troubleshooting

### High Denial Rate
```bash
# Get top denial reasons
curl http://localhost:8000/api/v1/policy/audit/analytics/denial-reasons?limit=20

# Check denials for specific user
curl "http://localhost:8000/api/v1/policy/audit/decisions?user_id=user123&result=deny"
```

### Performance Issues
```bash
# Check latency trends
curl "http://localhost:8000/api/v1/policy/audit/analytics/trends?metric=avg_latency&interval=1h"

# Get detailed analytics
curl http://localhost:8000/api/v1/policy/audit/analytics?group_by=cache_hit
```

### Policy Change Investigation
```bash
# Get recent policy changes
curl "http://localhost:8000/api/v1/policy/audit/policy-changes?limit=50"

# Get specific policy version
curl "http://localhost:8000/api/v1/policy/audit/policy-changes/{change_id}?include_diff=true"
```

## References

- [Policy Performance Report](POLICY_PERFORMANCE_REPORT.md)
- [Advanced OPA Policies](ADVANCED_OPA_POLICIES.md)
- [TimescaleDB Documentation](https://docs.timescale.com/)
- [SIEM Integration Guide](SIEM_INTEGRATION.md)
