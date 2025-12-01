# SARK Gateway Monitoring Guide

**Version:** 1.0
**Last Updated:** November 28, 2024
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [Metrics Collection](#metrics-collection)
5. [Log Aggregation](#log-aggregation)
6. [Distributed Tracing](#distributed-tracing)
7. [Dashboards](#dashboards)
8. [Alerting](#alerting)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The SARK Gateway monitoring infrastructure provides comprehensive observability through:

- **Metrics**: Prometheus for time-series metrics collection
- **Logs**: Loki + Promtail for log aggregation
- **Traces**: Jaeger for distributed tracing
- **Visualization**: Grafana for unified dashboards
- **Alerting**: Prometheus Alertmanager for alert routing

### Key Features

✅ **15+ Core Metrics** - Authorization, latency, cache, errors
✅ **50+ Extended Metrics** - Tools, policies, connections, resources
✅ **4 Grafana Dashboards** - Overview, Performance, Security, Operations
✅ **40+ Alert Rules** - Gateway, security, infrastructure, business
✅ **Structured Logging** - JSON logs with correlation IDs
✅ **Distributed Tracing** - OpenTelemetry integration
✅ **Audit Logging** - PostgreSQL + SIEM forwarding

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      SARK Gateway                           │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Metrics  │  │   Logs   │  │  Traces  │  │  Audit   │  │
│  │ Endpoint │  │  Output  │  │  Export  │  │  Events  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
└───────┼─────────────┼─────────────┼─────────────┼─────────┘
        │             │             │             │
        ▼             ▼             ▼             ▼
  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │Prometheus│  │Promtail/ │  │  Jaeger  │  │PostgreSQL│
  │          │  │   Loki   │  │          │  │  + SIEM  │
  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────┘
       │             │             │
       └─────────────┴─────────────┘
                     │
                     ▼
              ┌──────────────┐
              │   Grafana    │
              │  Dashboards  │
              └──────────────┘
                     │
                     ▼
              ┌──────────────┐
              │ Alertmanager │
              │   + Routing  │
              └──────────────┘
```

---

## Quick Start

### 1. Deploy Monitoring Stack

```bash
# Start all monitoring services
cd /path/to/sark
docker compose -f docker-compose.monitoring.yml up -d

# Verify services are running
docker compose -f docker-compose.monitoring.yml ps

# Check service health
curl http://localhost:9090/-/healthy  # Prometheus
curl http://localhost:3000/api/health # Grafana
curl http://localhost:3100/ready       # Loki
curl http://localhost:16686            # Jaeger UI
```

### 2. Access Dashboards

- **Grafana**: http://localhost:3000 (admin/changeme)
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093
- **Jaeger**: http://localhost:16686

### 3. Configure Environment Variables

Create `.env` file:

```bash
# Grafana
GRAFANA_ADMIN_PASSWORD=your-secure-password

# Database
POSTGRES_HOST=postgres
POSTGRES_DB=sark
POSTGRES_USER=sark
POSTGRES_PASSWORD=your-db-password

# Redis
REDIS_HOST=redis
REDIS_PASSWORD=your-redis-password

# Alerting
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
PAGERDUTY_ROUTING_KEY=your-pagerduty-key
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_FROM=alerts@example.com
SMTP_USERNAME=your-smtp-user
SMTP_PASSWORD=your-smtp-password
SECURITY_EMAIL=security@example.com
BUSINESS_EMAIL=business@example.com
COMPLIANCE_EMAIL=compliance@example.com
```

---

## Metrics Collection

### Core Metrics (15+)

#### Authorization Metrics
```promql
# Total authorization requests by decision
sark_gateway_authz_requests_total{decision="allow"}
sark_gateway_authz_requests_total{decision="deny"}

# Authorization latency histogram
sark_gateway_authz_latency_seconds_bucket

# Rate of authorizations
rate(sark_gateway_authz_requests_total[5m])
```

#### Cache Metrics
```promql
# Cache hit/miss counters
sark_policy_cache_hits_total
sark_policy_cache_misses_total

# Cache hit rate percentage
100 * rate(sark_policy_cache_hits_total[5m]) /
  (rate(sark_policy_cache_hits_total[5m]) + rate(sark_policy_cache_misses_total[5m]))
```

#### Error Metrics
```promql
# Client errors by type
sark_gateway_client_errors_total{error_type="validation"}
sark_gateway_client_errors_total{error_type="timeout"}

# Error rate
rate(sark_gateway_client_errors_total[5m])
```

### Extended Metrics (50+)

#### Request Metrics
```promql
# Requests in flight (gauge)
sark_gateway_requests_in_flight

# Request duration percentiles
histogram_quantile(0.95, rate(sark_gateway_request_duration_seconds_bucket[5m]))
histogram_quantile(0.99, rate(sark_gateway_request_duration_seconds_bucket[5m]))
```

#### Tool Invocation Metrics
```promql
# Tool invocations by tool and server
sark_gateway_tool_invocations_total{tool="postgres-mcp", server="db-prod"}

# Tool execution time
sark_gateway_tool_execution_duration_seconds
```

#### Audit Metrics
```promql
# Audit events logged
sark_gateway_audit_events_total{event_type="tool_invoke", decision="allow"}

# Audit write performance
sark_audit_write_duration_seconds

# SIEM forwarding
sark_siem_forwards_total{siem_platform="splunk", status="success"}
```

### Custom Metrics

To add custom metrics to your application:

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metric
my_custom_metric = Counter(
    'sark_custom_operation_total',
    'Custom operation counter',
    ['operation_type', 'status']
)

# Record metric
my_custom_metric.labels(
    operation_type='user_action',
    status='success'
).inc()
```

---

## Log Aggregation

### Log Structure

All SARK logs follow a structured JSON format:

```json
{
  "timestamp": "2024-11-28T01:23:45.123456Z",
  "level": "INFO",
  "logger": "sark.gateway",
  "message": "Authorization request processed",
  "request_id": "req_abc123",
  "user_id": "user_789",
  "duration": 0.025,
  "status_code": 200,
  "metadata": {
    "action": "gateway:tool:invoke",
    "server": "postgres-mcp",
    "decision": "allow"
  }
}
```

### Querying Logs with LogQL

```logql
# All gateway logs
{job="sark-gateway"}

# Error logs only
{job="sark-gateway"} |= "ERROR"

# Logs for specific user
{job="sark-gateway"} | json | user_id="user_789"

# Slow requests (>1s)
{job="sark-gateway"} | json | duration > 1.0

# Denied authorizations
{job="audit"} | json | decision="deny"

# Rate of errors
rate({job="sark-gateway"} |= "ERROR" [5m])
```

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages for potentially harmful situations
- **ERROR**: Error events that might still allow the application to continue
- **CRITICAL**: Critical errors that may cause the application to abort

---

## Distributed Tracing

### Trace Context Propagation

SARK Gateway uses OpenTelemetry for distributed tracing:

```python
from opentelemetry import trace
from opentelemetry.trace import SpanKind

tracer = trace.get_tracer(__name__)

# Create span
with tracer.start_as_current_span(
    "process_authorization",
    kind=SpanKind.SERVER
) as span:
    span.set_attribute("user.id", user_id)
    span.set_attribute("action", action)
    span.set_attribute("decision", decision)

    # Your code here
    result = await authorize_request()

    span.set_attribute("latency_ms", latency * 1000)
```

### Viewing Traces

1. **Jaeger UI**: http://localhost:16686
2. **Search by Service**: Select "sark-gateway"
3. **Filter by Tags**: user_id, action, decision
4. **Trace Timeline**: View full request flow
5. **Logs Integration**: Click trace ID to see related logs

### Common Trace Queries

- **Slow requests**: Duration > 1s
- **Failed requests**: tag error=true
- **Specific user**: tag user_id=user_789
- **Tool invocations**: tag operation=tool_invoke

---

## Dashboards

### 1. Gateway Integration Dashboard

**URL**: http://localhost:3000/d/gateway-integration

**Panels**:
- Authorization Requests (rate by decision)
- Authorization Latency (P50, P95, P99)
- Allow/Deny Ratio (pie chart)
- Cache Hit Rate (gauge)
- A2A Authorization Requests
- Error Rate by Operation
- Top Denied Users
- Top Invoked Tools
- Active Gateway Connections
- Audit Events Logged Total
- Authorization Requests by Server

**Use Cases**:
- Monitor overall gateway health
- Track authorization patterns
- Identify performance issues
- Review user activity

### 2. Performance Dashboard

**URL**: http://localhost:3000/d/gateway-performance

**Panels**:
- Request Latency Heatmap
- Tool Execution Time Breakdown (P50, P95)
- Policy Evaluation Overhead
- Cache Performance (hits vs misses)
- Cache Hit Rate %
- Resource Usage - Memory (RSS, Virtual)
- Resource Usage - CPU %
- Slow Requests (>1s)
- Request Duration Percentiles
- Requests In Flight
- Average Request Duration

**Use Cases**:
- Performance optimization
- Capacity planning
- Latency troubleshooting
- Resource monitoring

### 3. Security Dashboard

**URL**: http://localhost:3000/d/gateway-security

**Panels**:
- Authentication Failures (by reason)
- Authorization Denials by Policy
- Rate Limit Violations
- Suspicious Activity Patterns
- Failed Requests by User
- Security Alerts Timeline
- Authorization Deny Rate %
- A2A Authorization Denials
- Critical Errors
- Unique Users with Failures
- Security Events Breakdown
- Denied Tool Invocations
- Client Errors by Type

**Use Cases**:
- Security monitoring
- Threat detection
- Access control review
- Compliance auditing

### 4. Operations Dashboard

**URL**: http://localhost:3000/d/gateway-operations

**Panels**:
- System Health Status
- Database Health
- OPA Health
- SIEM Connection Status
- Error Rate by Component
- Error Severity Distribution
- SIEM Forward Success Rate
- SIEM Backpressure
- Audit Queue Depth
- Active Alerts
- Component Latency
- Audit Write Performance
- Audit Events Written/s
- Storage Utilization
- Uptime

**Use Cases**:
- Operational monitoring
- Dependency health
- Error tracking
- Capacity management

---

## Alerting

### Alert Severity Levels

- **Critical**: Immediate action required, page on-call
- **Warning**: Issue needs attention, notify team
- **Info**: Informational, log only

### Alert Categories

#### 1. Gateway Alerts (10 rules)
- High/Critical Authorization Latency
- Gateway Client Errors
- High Deny Rate
- Low/Zero Cache Hit Rate
- High Request Volume
- No Gateway Requests
- Audit Event Logging Failed
- High A2A Deny Rate

#### 2. Security Alerts (20 rules)
- High/Critical Auth Failure Rate
- High Authorization Deny Rate
- Privilege Escalation Attempts
- Rate Limit Violations
- Suspicious User Activity
- Abnormal Tool Usage Patterns
- Security Event Spikes
- Account Compromise Indicators
- Audit Logging Degraded
- SIEM Forwarding Failed

#### 3. Infrastructure Alerts (20 rules)
- Gateway Service Down/Flapping
- High Request Error Rate
- High/Critical CPU Usage
- High/Critical Memory Usage
- Memory Leak Suspected
- High Connection Count
- Database/OPA/Redis Unhealthy
- High Dependency Latency
- High/Critical Disk Usage
- Network Errors
- Requests Backing Up

#### 4. Business Alerts (15 rules)
- SLA Latency/Availability Violation
- Error Budget Exhausted
- Low Active User Count
- User Approaching Quota
- High Infrastructure Cost
- Low Feature Adoption
- Cache Hit Rate Declining
- Audit Coverage Insufficient
- High Support Ticket Volume

### Alert Routing

```yaml
# Critical → PagerDuty (immediate)
severity: critical
  → pagerduty-critical
  → repeat every 5m

# Security → Security Team (Slack + Email)
category: security
  → security-team (#security-alerts)
  → repeat every 4h

# Business → Business Team (Email + Slack)
component: business
  → business-team (#business-alerts)
  → repeat every 24h

# Infrastructure → Infrastructure Team (Slack)
component: infrastructure
  → infrastructure-team (#infrastructure-alerts)
  → repeat every 8h
```

### Silencing Alerts

```bash
# Silence via Alertmanager UI
http://localhost:9093/#/silences

# Create silence via API
curl -X POST http://localhost:9093/api/v2/silences \
  -H 'Content-Type: application/json' \
  -d '{
    "matchers": [
      {"name": "alertname", "value": "HighCPUUsage", "isRegex": false}
    ],
    "startsAt": "2024-11-28T00:00:00Z",
    "endsAt": "2024-11-28T04:00:00Z",
    "createdBy": "ops-team",
    "comment": "Planned maintenance window"
  }'
```

---

## Best Practices

### 1. Metric Naming

✅ **DO**:
- Use consistent prefixes: `sark_gateway_*`
- Include units in name: `_seconds`, `_bytes`, `_total`
- Use snake_case: `authorization_requests_total`

❌ **DON'T**:
- Mix naming styles: `sarkGatewayMetric`
- Omit units: `request_duration`
- Use excessive labels (>10)

### 2. Dashboard Design

✅ **DO**:
- Group related panels together
- Use appropriate visualizations (heatmaps for latency, gauges for thresholds)
- Add panel descriptions
- Use template variables for filtering
- Set appropriate refresh intervals (10-30s)

❌ **DON'T**:
- Overcrowd dashboards (max 15 panels)
- Use default panel titles
- Query excessively large time ranges
- Mix unrelated metrics

### 3. Alert Configuration

✅ **DO**:
- Set appropriate thresholds based on baselines
- Include actionable information in annotations
- Use `for:` duration to avoid flapping
- Group related alerts
- Test alerts before deploying

❌ **DON'T**:
- Alert on everything (alert fatigue)
- Use overly aggressive thresholds
- Skip runbook links
- Ignore alert resolution

### 4. Log Management

✅ **DO**:
- Use structured logging (JSON)
- Include correlation IDs (request_id, trace_id)
- Log at appropriate levels
- Implement log rotation
- Set retention policies

❌ **DON'T**:
- Log sensitive data (passwords, tokens)
- Use DEBUG in production
- Log at excessive rates
- Ignore disk space

---

## Troubleshooting

### Issue: High Memory Usage

**Symptoms**:
- `HighMemoryUsage` alert firing
- Application slowness
- OOM kills

**Investigation**:
```promql
# Check current memory
process_resident_memory_bytes{job="sark-gateway"}

# Check memory growth rate
rate(process_resident_memory_bytes{job="sark-gateway"}[1h])

# Review large objects
sark_gateway_cache_size_bytes
```

**Resolution**:
1. Check for memory leaks (increasing trend)
2. Review cache size and eviction policies
3. Analyze heap dumps
4. Scale horizontally if needed

### Issue: High Latency

**Symptoms**:
- `HighGatewayAuthorizationLatency` alert
- Slow dashboard response
- User complaints

**Investigation**:
```promql
# Check P95 latency
histogram_quantile(0.95, rate(sark_gateway_request_duration_seconds_bucket[5m]))

# Identify slow components
sark_gateway_tool_execution_duration_seconds
sark_policy_evaluation_duration_seconds
```

**Resolution**:
1. Check database query performance
2. Review policy complexity
3. Verify cache hit rate
4. Check dependency latency

### Issue: Authentication Failures

**Symptoms**:
- `HighAuthenticationFailureRate` alert
- Users unable to login
- Failed requests

**Investigation**:
```logql
# Review auth failures
{job="sark-gateway"} | json | level="ERROR" |= "authentication"

# Check failure reasons
rate(sark_gateway_auth_failures_total[5m])
```

**Resolution**:
1. Verify credentials configuration
2. Check auth service availability
3. Review firewall rules
4. Investigate potential attacks

### Issue: SIEM Forwarding Failures

**Symptoms**:
- `SIEMForwardingFailed` alert
- Events not in SIEM
- Backpressure building

**Investigation**:
```promql
# Check SIEM status
sark_siem_connection_status

# Review error rate
rate(sark_siem_forwards_total{status="error"}[5m])

# Check backpressure
sark_siem_backpressure_events
```

**Resolution**:
1. Verify SIEM connectivity
2. Check API credentials
3. Review network configuration
4. Increase batch size if needed

---

## Support

For additional assistance:

- **Documentation**: `/docs/monitoring/`
- **Runbooks**: `/docs/runbooks/`
- **Slack**: #sark-monitoring
- **On-call**: PagerDuty escalation

---

**Document Version**: 1.0
**Maintained By**: Infrastructure Team
**Last Review**: November 28, 2024
