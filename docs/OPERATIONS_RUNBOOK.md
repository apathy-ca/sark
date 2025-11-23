# SARK Operations Runbook

**Document Version**: 1.0
**Last Updated**: November 22, 2025
**Audience**: SRE Teams, Operations Engineers, On-Call Engineers

---

## Table of Contents

1. [Overview](#overview)
2. [Daily Operations](#daily-operations)
3. [User Management](#user-management)
4. [Server Management](#server-management)
5. [Policy Management](#policy-management)
6. [Session Management](#session-management)
7. [Rate Limiting Operations](#rate-limiting-operations)
8. [SIEM Operations](#siem-operations)
9. [Database Operations](#database-operations)
10. [Redis Operations](#redis-operations)
11. [Monitoring and Alerts](#monitoring-and-alerts)
12. [Maintenance Procedures](#maintenance-procedures)
13. [Troubleshooting Guide](#troubleshooting-guide)
14. [On-Call Guide](#on-call-guide)

---

## Overview

This runbook provides comprehensive operational procedures for day-to-day management of SARK in production.

### Quick Health Check

**One-line health check** for all components:

```bash
curl https://api.example.com/health/detailed | jq
```

**Expected output**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-11-22T10:00:00Z",
  "components": {
    "database": "healthy",
    "redis": "healthy",
    "opa": "healthy",
    "siem": "healthy"
  },
  "metrics": {
    "active_users": 1250,
    "registered_servers": 3500,
    "requests_per_minute": 5000
  }
}
```

### Required Access

- **Kubernetes**: `kubectl` access to production namespace
- **Database**: PostgreSQL read/write access
- **Redis**: Redis CLI access
- **Monitoring**: Grafana/Prometheus dashboards
- **SIEM**: Splunk/Datadog access
- **Cloud Provider**: AWS/GCP/Azure console access (as needed)

---

## Daily Operations

### Morning Checklist

**Daily review** (5-10 minutes):

```bash
#!/bin/bash
# daily-health-check.sh

echo "=== SARK Daily Health Check ==="
echo "Date: $(date)"

# 1. Check pod health
echo "\n1. Pod Health:"
kubectl get pods -n production | grep -v Running | wc -l
echo "Non-running pods: $(kubectl get pods -n production | grep -v Running | wc -l)"

# 2. Check resource usage
echo "\n2. Resource Usage:"
kubectl top pods -n production | sort -k3 -rn | head -5

# 3. Check error rate (last 24h)
echo "\n3. Error Rate (last 24h):"
# Query Prometheus
curl -s 'http://prometheus:9090/api/v1/query?query=sum(rate(http_requests_total{status=~"5.*"}[24h]))/sum(rate(http_requests_total[24h]))' | jq -r '.data.result[0].value[1]'

# 4. Check recent deployments
echo "\n4. Recent Deployments:"
kubectl rollout history deployment/sark -n production | tail -5

# 5. Check database size
echo "\n5. Database Size:"
kubectl exec -it postgres-0 -n production -- psql -U sark -c "
  SELECT pg_size_pretty(pg_database_size('sark'));
"

# 6. Check Redis memory
echo "\n6. Redis Memory:"
kubectl exec -it redis-0 -n production -- redis-cli INFO memory | grep used_memory_human

# 7. Check backup age
echo "\n7. Last Backup:"
aws s3 ls s3://sark-backups/postgres/ --recursive | sort | tail -1

# 8. Check alerts
echo "\n8. Active Alerts:"
curl -s http://prometheus:9090/api/v1/alerts | jq '.data.alerts[] | select(.state=="firing") | .labels.alertname'

echo "\n=== End Daily Health Check ==="
```

### Weekly Tasks

**Every Monday** (30 minutes):

1. **Review metrics from previous week**
   - Error rate trends
   - Performance degradation
   - Resource usage trends

2. **Check disk space**
   ```bash
   kubectl exec -it postgres-0 -n production -- df -h
   kubectl get pvc -n production
   ```

3. **Review logs for warnings**
   ```bash
   kubectl logs deployment/sark -n production --since=168h | grep -i warn | wc -l
   ```

4. **Verify backups**
   ```bash
   # Test restore from last week's backup
   ./scripts/dr-test-weekly.sh
   ```

5. **Review security alerts**
   ```bash
   # Check Datadog/Splunk for security events
   # index=sark_audit severity=high earliest=-7d
   ```

### Monthly Tasks

**First Monday of month** (2 hours):

1. **Database maintenance**
   ```bash
   kubectl exec -it postgres-0 -n production -- psql -U sark -c "VACUUM ANALYZE;"
   ```

2. **Rotate logs**
   ```bash
   kubectl exec -it postgres-0 -n production -- \
     find /var/log/postgresql -name "*.log" -mtime +30 -delete
   ```

3. **Update documentation**
   - Review runbooks for accuracy
   - Update architecture diagrams
   - Document new procedures

4. **Security review**
   - Review user permissions
   - Rotate API keys
   - Check for unused accounts

5. **Capacity planning**
   - Review resource trends
   - Forecast growth
   - Plan scaling

---

## User Management

### Create User

**Via API**:
```bash
curl -X POST https://api.example.com/api/v1/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john.doe",
    "email": "john.doe@example.com",
    "password": "SecureP@ssw0rd!",
    "roles": ["user"]
  }'
```

**Via Database** (emergency only):
```sql
-- Connect to database
kubectl exec -it postgres-0 -n production -- psql -U sark

-- Create user
INSERT INTO users (username, email, password_hash, is_active)
VALUES (
  'john.doe',
  'john.doe@example.com',
  '$argon2id$v=19$m=65536,t=3,p=4$...',  -- Pre-hashed password
  true
);
```

### List Users

```bash
# Via API
curl https://api.example.com/api/v1/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Via Database
kubectl exec -it postgres-0 -n production -- psql -U sark -c "
  SELECT id, username, email, is_active, created_at
  FROM users
  ORDER BY created_at DESC
  LIMIT 20;
"
```

### Disable User

```bash
# Via API
curl -X PATCH https://api.example.com/api/v1/users/user-123 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'

# Via Database
kubectl exec -it postgres-0 -n production -- psql -U sark -c "
  UPDATE users SET is_active = false WHERE id = 'user-123';
"

# Revoke all sessions
kubectl exec -it redis-0 -n production -- redis-cli \
  EVAL "return redis.call('del', unpack(redis.call('keys', 'session:user:user-123:*')))" 0
```

### Reset User Password

```bash
# Generate new password hash
python3 <<EOF
from argon2 import PasswordHasher
ph = PasswordHasher()
print(ph.hash("NewP@ssw0rd!"))
EOF

# Update in database
kubectl exec -it postgres-0 -n production -- psql -U sark -c "
  UPDATE users
  SET password_hash = '\$argon2id\$v=19\$m=65536,t=3,p=4\$...'
  WHERE username = 'john.doe';
"

# Revoke all sessions (force re-login)
kubectl exec -it redis-0 -n production -- redis-cli \
  EVAL "return redis.call('del', unpack(redis.call('keys', 'session:user:user-123:*')))" 0
```

### Grant Admin Role

```bash
# Via API
curl -X PATCH https://api.example.com/api/v1/users/user-123 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"roles": ["user", "admin"]}'

# Via Database
kubectl exec -it postgres-0 -n production -- psql -U sark -c "
  UPDATE users SET is_admin = true WHERE id = 'user-123';
"
```

---

## Server Management

### List Servers

```bash
# All servers
curl https://api.example.com/api/v1/servers \
  -H "Authorization: Bearer $TOKEN" | jq

# Filter by owner
curl https://api.example.com/api/v1/servers?owner_id=user-123 \
  -H "Authorization: Bearer $TOKEN" | jq

# Search by name
curl https://api.example.com/api/v1/servers?search=prod \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Register Server

```bash
curl -X POST https://api.example.com/api/v1/servers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "prod-server-01",
    "endpoint": "https://prod-server-01.example.com",
    "tags": ["production", "us-west-2"]
  }'
```

### Delete Server

```bash
# Soft delete (mark inactive)
curl -X DELETE https://api.example.com/api/v1/servers/server-123 \
  -H "Authorization: Bearer $TOKEN"

# Hard delete (remove from database)
kubectl exec -it postgres-0 -n production -- psql -U sark -c "
  DELETE FROM servers WHERE id = 'server-123';
"
```

### Bulk Operations

**Export all servers**:
```bash
curl https://api.example.com/api/v1/servers?limit=10000 \
  -H "Authorization: Bearer $TOKEN" | jq -r '.servers[] | [.id, .name, .endpoint] | @csv' > servers.csv
```

**Import servers**:
```bash
#!/bin/bash
# import-servers.sh

while IFS=',' read -r name endpoint; do
  curl -X POST https://api.example.com/api/v1/servers \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"$name\",
      \"endpoint\": \"$endpoint\"
    }"
done < servers.csv
```

---

## Policy Management

### List Policies

```bash
# Via API
curl https://api.example.com/api/v1/policies \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Via OPA
curl http://opa:8181/v1/policies
```

### Upload Policy

```bash
# Upload Rego policy to OPA
curl -X PUT http://opa:8181/v1/policies/server_access \
  -H "Content-Type: text/plain" \
  --data-binary @policies/server_access.rego
```

### Test Policy

```bash
# Evaluate policy
curl -X POST http://opa:8181/v1/data/mcp/allow \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "user": {"id": "user-123", "roles": ["admin"]},
      "action": "server:read",
      "resource": "server-456"
    }
  }' | jq
```

### Clear Policy Cache

```bash
# Clear all policy decision cache
kubectl exec -it redis-0 -n production -- redis-cli \
  EVAL "return redis.call('del', unpack(redis.call('keys', 'policy:decision:*')))" 0

# Clear specific policy cache
kubectl exec -it redis-0 -n production -- redis-cli \
  DEL policy:version:server_access
```

### View Policy Statistics

```sql
-- Policy evaluation stats (last 24 hours)
kubectl exec -it timescaledb-0 -n production -- psql -U sark -d sark_audit -c "
  SELECT
    policy_name,
    COUNT(*) AS evaluations,
    SUM(CASE WHEN decision THEN 1 ELSE 0 END) AS allowed,
    SUM(CASE WHEN NOT decision THEN 1 ELSE 0 END) AS denied,
    AVG(duration_ms) AS avg_duration_ms
  FROM policy_evaluations
  WHERE time >= NOW() - INTERVAL '24 hours'
  GROUP BY policy_name
  ORDER BY evaluations DESC;
"
```

---

## Session Management

### View Active Sessions

```bash
# Count active sessions
kubectl exec -it redis-0 -n production -- redis-cli \
  EVAL "return #redis.call('keys', 'session:user:*')" 0

# List sessions for user
kubectl exec -it redis-0 -n production -- redis-cli \
  KEYS "session:user:user-123:*"

# Get session details
kubectl exec -it redis-0 -n production -- redis-cli \
  HGETALL "session:user:user-123:session-456"
```

### Revoke Session

```bash
# Revoke specific session
kubectl exec -it redis-0 -n production -- redis-cli \
  DEL "session:user:user-123:session-456"

# Revoke all sessions for user
kubectl exec -it redis-0 -n production -- redis-cli \
  EVAL "return redis.call('del', unpack(redis.call('keys', 'session:user:user-123:*')))" 0
```

### Force Global Logout

**Emergency procedure** (revoke all sessions):

```bash
# WARNING: This logs out all users!
kubectl exec -it redis-0 -n production -- redis-cli \
  EVAL "return redis.call('del', unpack(redis.call('keys', 'session:*')))" 0

# Announce maintenance
curl -X POST https://api.example.com/api/v1/admin/announce \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"message": "Emergency maintenance - all users logged out"}'
```

### Session Metrics

```bash
# Average session duration
kubectl exec -it timescaledb-0 -n production -- psql -U sark -d sark_audit -c "
  SELECT
    AVG(EXTRACT(EPOCH FROM (logout_time - login_time))) AS avg_duration_seconds
  FROM audit_events
  WHERE event_type = 'logout'
    AND time >= NOW() - INTERVAL '24 hours';
"

# Peak concurrent sessions
kubectl exec -it redis-0 -n production -- redis-cli \
  INFO stats | grep instantaneous_ops_per_sec
```

---

## Rate Limiting Operations

### Check Rate Limit Status

```bash
# Check user's current rate limit
curl https://api.example.com/api/v1/servers \
  -H "Authorization: Bearer $TOKEN" \
  -I | grep -i ratelimit

# Output:
# X-RateLimit-Limit: 5000
# X-RateLimit-Remaining: 4850
# X-RateLimit-Reset: 1700000000
```

### View Rate Limit Keys

```bash
# List all rate limit keys
kubectl exec -it redis-0 -n production -- redis-cli \
  KEYS "ratelimit:*"

# Check specific user's rate limit
kubectl exec -it redis-0 -n production -- redis-cli \
  GET "ratelimit:user:user-123:2025-11-22-10"  # Hourly window
```

### Reset Rate Limit

```bash
# Reset rate limit for user (current window)
kubectl exec -it redis-0 -n production -- redis-cli \
  DEL "ratelimit:user:user-123:$(date +%Y-%m-%d-%H)"

# Reset all rate limits (emergency)
kubectl exec -it redis-0 -n production -- redis-cli \
  EVAL "return redis.call('del', unpack(redis.call('keys', 'ratelimit:*')))" 0
```

### Adjust Rate Limits

```bash
# Update user's rate limit (via database)
kubectl exec -it postgres-0 -n production -- psql -U sark -c "
  UPDATE users
  SET rate_limit_per_minute = 10000
  WHERE id = 'user-123';
"

# Or via environment variable (requires restart)
kubectl set env deployment/sark \
  RATE_LIMIT_USER_REQUESTS_PER_MINUTE=10000 \
  -n production
```

---

## SIEM Operations

### Check SIEM Health

```bash
# Health check
curl https://api.example.com/health/detailed | jq '.components.siem'

# Expected: "healthy"
```

### View SIEM Queue

```bash
# Check event queue size
kubectl exec -it redis-0 -n production -- redis-cli \
  LLEN siem:event_queue

# Healthy: < 1,000
# Warning: 1,000 - 10,000
# Critical: > 10,000
```

### Drain SIEM Queue

```bash
# Force immediate forwarding
kubectl exec -it deployment/sark -n production -- \
  python -m sark.siem.worker --flush-queue

# Or manually forward events
kubectl exec -it redis-0 -n production -- redis-cli \
  LPOP siem:event_queue 100  # Pop 100 events
```

### View SIEM Errors

```bash
# Check failed events
kubectl exec -it redis-0 -n production -- redis-cli \
  LLEN siem:failed_events

# View failed events
kubectl exec -it redis-0 -n production -- redis-cli \
  LRANGE siem:failed_events 0 10
```

### Reset Circuit Breaker

```bash
# SIEM circuit breaker open (too many failures)
# Reset to allow retry

kubectl exec -it redis-0 -n production -- redis-cli \
  DEL siem:circuit_breaker:state

kubectl exec -it redis-0 -n production -- redis-cli \
  DEL siem:circuit_breaker:failure_count
```

### Verify Events in SIEM

**Splunk**:
```spl
index=sark_audit sourcetype=sark:audit earliest=-15m
| stats count by event_type
```

**Datadog**:
```
service:sark env:production
| group by event_type
```

---

## Database Operations

### Database Health Check

```bash
# Check connectivity
kubectl exec -it postgres-0 -n production -- pg_isready -U sark

# Check replication lag
kubectl exec -it postgres-0 -n production -- psql -U sark -c "
  SELECT
    client_addr,
    state,
    sync_state,
    replay_lag
  FROM pg_stat_replication;
"
```

### View Active Connections

```sql
kubectl exec -it postgres-0 -n production -- psql -U sark -c "
  SELECT
    COUNT(*) AS total_connections,
    SUM(CASE WHEN state = 'active' THEN 1 ELSE 0 END) AS active,
    SUM(CASE WHEN state = 'idle' THEN 1 ELSE 0 END) AS idle
  FROM pg_stat_activity
  WHERE datname = 'sark';
"
```

### Kill Long-Running Queries

```sql
-- View long-running queries
kubectl exec -it postgres-0 -n production -- psql -U sark -c "
  SELECT
    pid,
    NOW() - query_start AS duration,
    state,
    query
  FROM pg_stat_activity
  WHERE state = 'active'
    AND NOW() - query_start > INTERVAL '30 seconds'
  ORDER BY duration DESC;
"

-- Kill specific query
kubectl exec -it postgres-0 -n production -- psql -U sark -c "
  SELECT pg_terminate_backend(12345);  -- Replace with PID
"

-- Kill all long-running queries (> 5 minutes)
kubectl exec -it postgres-0 -n production -- psql -U sark -c "
  SELECT pg_terminate_backend(pid)
  FROM pg_stat_activity
  WHERE state = 'active'
    AND NOW() - query_start > INTERVAL '5 minutes';
"
```

### Database Maintenance

```bash
# VACUUM ANALYZE (weekly)
kubectl exec -it postgres-0 -n production -- psql -U sark -c "VACUUM ANALYZE;"

# Reindex (monthly, during maintenance window)
kubectl exec -it postgres-0 -n production -- psql -U sark -c "REINDEX DATABASE sark;"

# Update statistics
kubectl exec -it postgres-0 -n production -- psql -U sark -c "ANALYZE;"
```

### Database Backups

See [DISASTER_RECOVERY.md](./DISASTER_RECOVERY.md#postgresql-backups) for complete backup procedures.

**Quick backup**:
```bash
# Full backup
kubectl exec -it postgres-0 -n production -- \
  pg_dump -U sark -Fc sark > sark-backup-$(date +%Y%m%d-%H%M).dump

# Upload to S3
aws s3 cp sark-backup-$(date +%Y%m%d-%H%M).dump \
  s3://sark-backups/manual/
```

---

## Redis Operations

### Redis Health Check

```bash
# Ping Redis
kubectl exec -it redis-0 -n production -- redis-cli PING

# Check memory usage
kubectl exec -it redis-0 -n production -- redis-cli INFO memory

# Check key count
kubectl exec -it redis-0 -n production -- redis-cli DBSIZE
```

### Cache Statistics

```bash
# Hit/miss ratio
kubectl exec -it redis-0 -n production -- redis-cli INFO stats | grep keyspace

# Output:
# keyspace_hits:1000000
# keyspace_misses:50000
# Hit ratio = 1000000 / (1000000 + 50000) = 95.2%
```

### Clear Cache

```bash
# Clear all caches
kubectl exec -it redis-0 -n production -- redis-cli FLUSHDB

# Clear specific pattern
kubectl exec -it redis-0 -n production -- redis-cli \
  EVAL "return redis.call('del', unpack(redis.call('keys', 'policy:*')))" 0
```

### Monitor Redis

```bash
# Real-time monitoring
kubectl exec -it redis-0 -n production -- redis-cli MONITOR

# Slow log
kubectl exec -it redis-0 -n production -- redis-cli SLOWLOG GET 10
```

---

## Monitoring and Alerts

### View Active Alerts

```bash
# Prometheus alerts
curl http://prometheus:9090/api/v1/alerts | \
  jq '.data.alerts[] | select(.state=="firing") | {name: .labels.alertname, severity: .labels.severity}'
```

### Acknowledge Alert

**PagerDuty**:
```bash
# Acknowledge via API
curl -X PUT https://api.pagerduty.com/incidents/INCIDENT_ID \
  -H "Authorization: Token token=YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "incident": {
      "type": "incident_reference",
      "status": "acknowledged"
    }
  }'
```

### Silence Alert

**Prometheus Alertmanager**:
```bash
# Silence for 1 hour
curl -X POST http://alertmanager:9093/api/v2/silences \
  -H "Content-Type: application/json" \
  -d '{
    "matchers": [{
      "name": "alertname",
      "value": "HighErrorRate",
      "isRegex": false
    }],
    "startsAt": "2025-11-22T10:00:00Z",
    "endsAt": "2025-11-22T11:00:00Z",
    "createdBy": "ops@example.com",
    "comment": "Investigating high error rate"
  }'
```

### Custom Metrics

**Export custom metric**:
```python
from prometheus_client import Counter, Histogram

# Counter
custom_operations = Counter('custom_operations_total', 'Total custom operations')
custom_operations.inc()

# Histogram
custom_duration = Histogram('custom_duration_seconds', 'Custom operation duration')
with custom_duration.time():
    # Operation
    pass
```

---

## Maintenance Procedures

### Planned Maintenance

**Schedule maintenance window**:

1. **Announce maintenance** (48 hours advance notice)
   ```bash
   # Update status page
   curl -X POST https://status.example.com/api/incidents \
     -d 'name=Scheduled Maintenance&status=scheduled&start=2025-11-24T02:00:00Z'

   # Email users
   # Send notification to all_users@example.com
   ```

2. **Pre-maintenance backup**
   ```bash
   # Full backup before maintenance
   ./scripts/backup-all.sh
   ```

3. **Enable maintenance mode** (read-only)
   ```bash
   kubectl set env deployment/sark READ_ONLY_MODE=true -n production
   ```

4. **Perform maintenance**
   - Database VACUUM, REINDEX
   - Apply security patches
   - Update configurations

5. **Disable maintenance mode**
   ```bash
   kubectl set env deployment/sark READ_ONLY_MODE=false -n production
   ```

6. **Post-maintenance validation**
   ```bash
   ./scripts/smoke-test.sh https://api.example.com
   ```

### Rolling Restart

**Restart application pods** (zero-downtime):

```bash
kubectl rollout restart deployment/sark -n production
kubectl rollout status deployment/sark -n production
```

### Database Restart

```bash
# Graceful restart
kubectl exec -it postgres-0 -n production -- pg_ctl restart -D /var/lib/postgresql/data

# Or delete pod (StatefulSet will recreate)
kubectl delete pod postgres-0 -n production
kubectl wait --for=condition=ready pod/postgres-0 -n production --timeout=5m
```

---

## Troubleshooting Guide

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) and [INCIDENT_RESPONSE.md](./INCIDENT_RESPONSE.md) for comprehensive troubleshooting.

### Quick Diagnostics

```bash
#!/bin/bash
# quick-diagnostics.sh

echo "=== Quick Diagnostics ==="

# 1. Health check
echo "\n1. Health Check:"
curl -s https://api.example.com/health | jq

# 2. Pod status
echo "\n2. Pod Status:"
kubectl get pods -n production | grep -v Running

# 3. Recent errors
echo "\n3. Recent Errors (last 5 min):"
kubectl logs deployment/sark -n production --since=5m | grep -i error | tail -10

# 4. Resource usage
echo "\n4. Resource Usage:"
kubectl top pods -n production --sort-by=memory | head -5

# 5. Database connections
echo "\n5. Database Connections:"
kubectl exec -it postgres-0 -n production -- psql -U sark -c "SELECT COUNT(*) FROM pg_stat_activity;"

# 6. Redis memory
echo "\n6. Redis Memory:"
kubectl exec -it redis-0 -n production -- redis-cli INFO memory | grep used_memory_human

# 7. Active alerts
echo "\n7. Active Alerts:"
curl -s http://prometheus:9090/api/v1/alerts | jq -r '.data.alerts[] | select(.state=="firing") | .labels.alertname'

echo "\n=== End Diagnostics ==="
```

---

## On-Call Guide

### On-Call Expectations

- **Response Time**: 15 minutes for P0, 1 hour for P1
- **Availability**: 24/7 during on-call shift
- **Tools Required**: Laptop, phone, VPN access, kubectl configured
- **Communication**: Slack #incidents, PagerDuty

### On-Call Handoff

**Weekly handoff** (Monday 9 AM):

```bash
# Review previous week
1. Check incident history
2. Review open action items
3. Discuss any ongoing issues

# Verify access
4. Test PagerDuty notifications
5. Verify kubectl access
6. Test VPN connection

# Knowledge transfer
7. Brief on recent changes
8. Highlight any areas of concern
```

### Common Alerts

| Alert | Severity | Action |
|-------|----------|--------|
| **APIDown** | P0 | Immediate investigation, check pods, rollback if needed |
| **HighErrorRate** | P1 | Check logs, identify error cause, escalate if needed |
| **HighLatency** | P1 | Check database queries, cache hit rate, scale if needed |
| **DatabaseConnectionHigh** | P1 | Kill idle connections, increase pool size |
| **DiskSpacelow** | P2 | Clean up logs, expand disk, plan capacity |

### Escalation Path

1. **L1** (On-Call Engineer): Initial response, basic troubleshooting
2. **L2** (Engineering Lead): Complex issues, architectural decisions
3. **L3** (CTO): Critical business impact, major outages
4. **Specialists**: DBA (database), Security (security incidents)

---

## Summary

This runbook provides comprehensive operational procedures for SARK:

- **Daily Operations**: Health checks, monitoring, weekly/monthly tasks
- **User Management**: Create, disable, reset password, grant roles
- **Server Management**: Register, list, delete, bulk operations
- **Policy Management**: Upload, test, cache management
- **Session Management**: View, revoke, force logout
- **Rate Limiting**: Check status, reset limits, adjust thresholds
- **SIEM Operations**: Health check, queue management, troubleshooting
- **Database Operations**: Health check, maintenance, backups
- **Redis Operations**: Cache management, statistics, monitoring
- **Monitoring**: View alerts, acknowledge, silence, custom metrics
- **Maintenance**: Planned maintenance, restarts, rollouts
- **Troubleshooting**: Quick diagnostics, common issues
- **On-Call**: Expectations, handoff, escalation

Keep this runbook updated with new procedures as they are developed.
