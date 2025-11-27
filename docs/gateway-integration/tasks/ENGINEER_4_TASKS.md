# Engineer 4: Audit & Monitoring

**Branch:** `feat/gateway-audit`
**Duration:** 5-7 days
**Focus:** Audit logging, SIEM integration, metrics, alerts
**Dependencies:** Shared models (Day 1)

---

## Setup

```bash
git checkout -b feat/gateway-audit
git pull origin feat/gateway-client
mkdir -p src/sark/services/audit
mkdir -p src/sark/services/siem
mkdir -p src/sark/api/metrics
mkdir -p src/sark/db/migrations
mkdir -p monitoring/grafana/dashboards
mkdir -p monitoring/prometheus/rules
```

---

## Tasks

### Day 1-2: Gateway Audit Service

**File:** `src/sark/services/audit/gateway_audit.py`

```python
"""Gateway audit event logging."""

import uuid
from datetime import datetime
import structlog

from sark.models.gateway import GatewayAuditEvent
from sark.db import get_db_session

logger = structlog.get_logger()


async def log_gateway_event(event: GatewayAuditEvent) -> str:
    """
    Log Gateway audit event to PostgreSQL.

    Args:
        event: Gateway audit event

    Returns:
        Audit event ID
    """
    audit_id = str(uuid.uuid4())

    async with get_db_session() as session:
        await session.execute(
            """
            INSERT INTO gateway_audit_events (
                id, event_type, user_id, agent_id, server_name, tool_name,
                decision, reason, timestamp, gateway_request_id, metadata
            ) VALUES (
                :id, :event_type, :user_id, :agent_id, :server_name, :tool_name,
                :decision, :reason, :timestamp, :gateway_request_id, :metadata
            )
            """,
            {
                "id": audit_id,
                "event_type": event.event_type,
                "user_id": event.user_id,
                "agent_id": event.agent_id,
                "server_name": event.server_name,
                "tool_name": event.tool_name,
                "decision": event.decision,
                "reason": event.reason,
                "timestamp": datetime.fromtimestamp(event.timestamp),
                "gateway_request_id": event.gateway_request_id,
                "metadata": event.metadata,
            }
        )
        await session.commit()

    logger.info(
        "gateway_audit_event_logged",
        audit_id=audit_id,
        event_type=event.event_type,
        decision=event.decision,
    )

    # Forward to SIEM asynchronously
    from sark.services.siem.gateway_forwarder import forward_gateway_event
    asyncio.create_task(forward_gateway_event(event, audit_id))

    return audit_id
```

**Checklist:**
- [ ] log_gateway_event() function
- [ ] PostgreSQL insertion
- [ ] SIEM forwarding trigger
- [ ] Structured logging
- [ ] Error handling

---

### Day 2-3: SIEM Integration

**File:** `src/sark/services/siem/gateway_forwarder.py`

```python
"""SIEM forwarding for Gateway events."""

import asyncio
import json
import gzip
from collections import deque
import httpx
import structlog

from sark.config import get_settings
from sark.models.gateway import GatewayAuditEvent

logger = structlog.get_logger()
settings = get_settings()

# Event queue for batching
gateway_event_queue = deque(maxlen=1000)


async def forward_gateway_event(event: GatewayAuditEvent, audit_id: str):
    """
    Forward Gateway event to SIEM platforms.

    Batches events for efficiency.
    """
    gateway_event_queue.append({
        "audit_id": audit_id,
        "event": event.dict(),
        "timestamp": event.timestamp,
    })

    # Trigger batch if queue is full
    if len(gateway_event_queue) >= 100:
        await flush_gateway_events()


async def flush_gateway_events():
    """Flush queued events to SIEM."""
    if not gateway_event_queue:
        return

    events = list(gateway_event_queue)
    gateway_event_queue.clear()

    # Format for Splunk
    splunk_events = [
        {
            "time": e["timestamp"],
            "sourcetype": "sark:gateway",
            "event": e["event"],
        }
        for e in events
    ]

    # Compress payload
    payload = gzip.compress(json.dumps(splunk_events).encode())

    # Send to Splunk with circuit breaker
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.splunk_hec_url,
                headers={
                    "Authorization": f"Splunk {settings.splunk_hec_token}",
                    "Content-Encoding": "gzip",
                },
                content=payload,
                timeout=10.0,
            )
            response.raise_for_status()

        logger.info("gateway_events_forwarded_to_siem", count=len(events))

    except Exception as e:
        logger.error("gateway_siem_forward_failed", error=str(e))
        # Events already in PostgreSQL, safe to continue
```

**Checklist:**
- [ ] Event batching (100 events or 5 seconds)
- [ ] Compression (gzip)
- [ ] Splunk HEC integration
- [ ] Datadog integration
- [ ] Circuit breaker pattern
- [ ] Retry logic

---

### Day 3-4: Prometheus Metrics

**File:** `src/sark/api/metrics/gateway_metrics.py`

```python
"""Prometheus metrics for Gateway integration."""

from prometheus_client import Counter, Histogram, Gauge

# Authorization requests
gateway_authorization_requests_total = Counter(
    "sark_gateway_authz_requests_total",
    "Total Gateway authorization requests",
    ["decision", "action", "server"],
)

# Authorization latency
gateway_authorization_latency_seconds = Histogram(
    "sark_gateway_authz_latency_seconds",
    "Gateway authorization latency in seconds",
    ["action"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

# Cache metrics
gateway_policy_cache_hits_total = Counter(
    "sark_gateway_cache_hits_total",
    "Gateway policy cache hits",
)

gateway_policy_cache_misses_total = Counter(
    "sark_gateway_cache_misses_total",
    "Gateway policy cache misses",
)

# A2A metrics
a2a_authorization_requests_total = Counter(
    "sark_a2a_authz_requests_total",
    "A2A authorization requests",
    ["decision", "source_type", "target_type"],
)

# Gateway client errors
gateway_client_errors_total = Counter(
    "sark_gateway_client_errors_total",
    "Gateway client errors",
    ["operation", "error_type"],
)

# Audit events
gateway_audit_events_total = Counter(
    "sark_gateway_audit_events_total",
    "Gateway audit events logged",
    ["event_type", "decision"],
)

# Active connections
gateway_active_connections = Gauge(
    "sark_gateway_active_connections",
    "Active Gateway connections",
)


def record_authorization(decision: str, action: str, server: str, latency: float):
    """Record authorization metrics."""
    gateway_authorization_requests_total.labels(
        decision=decision,
        action=action,
        server=server,
    ).inc()

    gateway_authorization_latency_seconds.labels(
        action=action,
    ).observe(latency)


def record_cache_hit():
    """Record cache hit."""
    gateway_policy_cache_hits_total.inc()


def record_cache_miss():
    """Record cache miss."""
    gateway_policy_cache_misses_total.inc()
```

**Checklist:**
- [ ] All metrics defined
- [ ] Helper functions for recording
- [ ] Labels for filtering
- [ ] Histogram buckets optimized

---

### Day 4: Database Migration

**File:** `src/sark/db/migrations/XXX_add_gateway_audit_events.py`

```python
"""Add gateway_audit_events table."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'gateway_audit_001'
down_revision = 'previous_migration'


def upgrade():
    op.create_table(
        'gateway_audit_events',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('agent_id', sa.String(), nullable=True),
        sa.Column('server_name', sa.String(), nullable=True),
        sa.Column('tool_name', sa.String(), nullable=True),
        sa.Column('decision', sa.String(10), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('gateway_request_id', sa.String(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Indexes for common queries
    op.create_index('ix_gateway_audit_user_id', 'gateway_audit_events', ['user_id'])
    op.create_index('ix_gateway_audit_timestamp', 'gateway_audit_events', ['timestamp'])
    op.create_index('ix_gateway_audit_decision', 'gateway_audit_events', ['decision'])


def downgrade():
    op.drop_table('gateway_audit_events')
```

---

### Day 5: Grafana Dashboard

**File:** `monitoring/grafana/dashboards/gateway-integration.json`

Dashboard panels:
1. Authorization Requests (rate)
2. Authorization Latency (P50, P95, P99)
3. Allow/Deny Ratio
4. Cache Hit Rate
5. A2A Requests
6. Error Rate
7. Top Denied Users
8. Top Invoked Tools

See Grafana JSON format in main integration plan.

---

### Day 5: Prometheus Alerts

**File:** `monitoring/prometheus/rules/gateway-alerts.yaml`

```yaml
groups:
- name: gateway_integration
  rules:
  - alert: HighGatewayAuthorizationLatency
    expr: histogram_quantile(0.95, sark_gateway_authz_latency_seconds) > 0.05
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High Gateway authorization latency"
      description: "P95 latency > 50ms for 5 minutes"

  - alert: GatewayClientErrors
    expr: rate(sark_gateway_client_errors_total[5m]) > 0.1
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "Gateway client errors detected"

  - alert: LowPolicyCacheHitRate
    expr: |
      rate(sark_gateway_cache_hits_total[10m]) /
      (rate(sark_gateway_cache_hits_total[10m]) + rate(sark_gateway_cache_misses_total[10m])) < 0.8
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Low policy cache hit rate"
```

---

## Testing

**File:** `tests/unit/services/audit/test_gateway_audit.py`

Test:
- Event logging to PostgreSQL
- SIEM forwarding
- Batch processing
- Error handling

---

## Delivery Checklist

- [ ] Gateway audit service complete
- [ ] SIEM integration working
- [ ] Prometheus metrics exposed
- [ ] Database migration created
- [ ] Grafana dashboard created
- [ ] Prometheus alerts configured
- [ ] Tests pass
- [ ] PR created

Ready! 🚀
