# SARK Operational Runbook

**Version:** 1.0
**Last Updated:** 2025-11-22
**Audience:** SRE, DevOps, Operations Teams

---

## Table of Contents

1. [Overview](#overview)
2. [Session Management Operations](#session-management-operations)
3. [SIEM Troubleshooting](#siem-troubleshooting)
4. [Policy Performance Tuning](#policy-performance-tuning)
5. [Retry Handler Operations](#retry-handler-operations)
6. [Common Operational Tasks](#common-operational-tasks)
7. [Emergency Procedures](#emergency-procedures)
8. [Monitoring & Alerts](#monitoring--alerts)

---

## Overview

This runbook provides step-by-step operational procedures for managing SARK in production environments. It covers routine operations, troubleshooting, performance tuning, and emergency response.

### Quick Reference

| Component | Health Check | Metrics Endpoint |
|-----------|--------------|------------------|
| **Application** | `GET /health` | `GET /health/detailed` |
| **Database** | Included in `/health/detailed` | Connection pool stats |
| **Redis** | Included in `/health/detailed` | Cache hit rate |
| **OPA** | Policy evaluation test | Evaluation latency |
| **SIEM** | SIEM health check | Success rate, latency |

### Required Access

- **Kubernetes cluster access**: `kubectl` configured
- **Database access**: Read/write credentials
- **Redis access**: Admin commands enabled
- **SIEM access**: Splunk/Datadog dashboards
- **Monitoring**: Grafana/Prometheus access

---

## Session Management Operations

SARK uses JWT access tokens with Redis-backed refresh tokens for session management.

### Architecture Overview

```
┌──────────────┐
│  User Login  │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│  Access Token    │  JWT (short-lived, 60 min)
│  + Refresh Token │  Redis entry (long-lived, 7 days)
└──────────────────┘
```

### Session Lifecycle

#### 1. Check Active Sessions

```bash
# Get session count from Redis
kubectl exec -it <redis-pod> -- redis-cli
> KEYS "refresh_token:*" | wc -l
```

#### 2. View User Sessions

```bash
# List all refresh tokens for a user
> KEYS "refresh_token:user:<user_id>:*"

# Get token details
> GET "refresh_token:user:<user_id>:<token_id>"
> TTL "refresh_token:user:<user_id>:<token_id>"
```

#### 3. Revoke User Session

```bash
# Revoke specific refresh token
> DEL "refresh_token:user:<user_id>:<token_id>"

# Revoke all sessions for a user
> EVAL "return redis.call('del', unpack(redis.call('keys', 'refresh_token:user:<user_id>:*')))" 0
```

#### 4. Force Logout All Users

```bash
# Emergency: Clear all sessions
> EVAL "return redis.call('del', unpack(redis.call('keys', 'refresh_token:*')))" 0
```

### Session Configuration

```bash
# Environment variables
JWT_EXPIRATION_MINUTES=60           # Access token lifetime
REFRESH_TOKEN_EXPIRATION_DAYS=7     # Refresh token lifetime
REFRESH_TOKEN_ROTATION_ENABLED=true # Rotate on refresh
REDIS_DSN=redis://redis:6379/0      # Redis connection
```

### Session Monitoring

#### Metrics to Track

- **Active sessions**: Count of `refresh_token:*` keys
- **Session creation rate**: New tokens/minute
- **Token refresh rate**: Refresh operations/minute
- **Token revocation rate**: Deletions/minute

#### Alerts

```yaml
# Example Prometheus alert
- alert: HighSessionCount
  expr: redis_db_keys{db="0",key="refresh_token:*"} > 100000
  for: 5m
  annotations:
    summary: "High number of active sessions"

- alert: SessionRefreshFailures
  expr: rate(token_refresh_errors_total[5m]) > 10
  for: 2m
  annotations:
    summary: "High token refresh failure rate"
```

### Troubleshooting Sessions

#### Problem: Users Can't Log In

**Symptoms:**
- 503 errors on login endpoints
- "Authentication service temporarily unavailable"

**Diagnosis:**
```bash
# Check Redis connectivity
kubectl exec -it <sark-pod> -- curl http://localhost:8000/health/detailed

# Check Redis directly
kubectl exec -it <redis-pod> -- redis-cli PING

# Check Redis logs
kubectl logs <redis-pod> --tail=100
```

**Resolution:**
1. Verify Redis is running: `kubectl get pods -l app=redis`
2. Check Redis service: `kubectl get svc redis`
3. Restart Redis if needed: `kubectl rollout restart deployment/redis`
4. Check Redis resource limits: `kubectl describe pod <redis-pod>`

#### Problem: Token Refresh Fails

**Symptoms:**
- 401 errors on `/api/auth/refresh`
- "Invalid or expired refresh token"

**Diagnosis:**
```bash
# Check if token exists in Redis
kubectl exec -it <redis-pod> -- redis-cli
> GET "refresh_token:user:<user_id>:<token_id>"

# Check token TTL
> TTL "refresh_token:user:<user_id>:<token_id>"
```

**Resolution:**
1. If TTL is -2 (expired): Token legitimately expired, user must re-login
2. If TTL is -1 (no expiry): Configuration error, check `REFRESH_TOKEN_EXPIRATION_DAYS`
3. If token exists but refresh fails: Check token service logs

#### Problem: Session Count Growing Rapidly

**Symptoms:**
- Redis memory usage increasing
- Large number of refresh tokens

**Diagnosis:**
```bash
# Count total sessions
kubectl exec -it <redis-pod> -- redis-cli
> DBSIZE

# Check Redis memory usage
> INFO memory

# List sample tokens
> KEYS "refresh_token:*" | head -20
```

**Resolution:**
1. Check for token rotation: Ensure `REFRESH_TOKEN_ROTATION_ENABLED=true`
2. Verify TTL on tokens: `TTL refresh_token:*`
3. Clean up expired tokens manually:
```bash
> EVAL "local keys = redis.call('keys', 'refresh_token:*'); local count = 0; for i=1,#keys do if redis.call('ttl', keys[i]) < 0 then redis.call('del', keys[i]); count = count + 1 end end return count" 0
```

---

## SIEM Troubleshooting

SARK forwards audit events to external SIEM systems (Splunk, Datadog) for security monitoring.

### SIEM Architecture

```
┌─────────────────┐
│  Audit Events   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ BatchHandler    │  100 events or 5s timeout
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  RetryHandler   │  3 attempts, exponential backoff
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Splunk/Datadog │
└─────────────────┘
```

### SIEM Health Checks

#### Check SIEM Status

```bash
# Via API
curl http://localhost:8000/health/detailed | jq '.siem'

# Expected output:
{
  "splunk": {
    "healthy": true,
    "latency_ms": 45.2,
    "last_check": "2025-11-22T10:30:00Z"
  },
  "datadog": {
    "healthy": true,
    "latency_ms": 38.7,
    "last_check": "2025-11-22T10:30:00Z"
  }
}
```

#### Check SIEM Metrics

```bash
# Via application logs
kubectl logs <sark-pod> | grep "siem_metrics"

# Expected metrics:
{
  "events_sent": 150000,
  "events_failed": 23,
  "success_rate": 99.98,
  "average_latency_ms": 42.5,
  "batches_sent": 1500,
  "batches_failed": 1,
  "retry_count": 5
}
```

### Common SIEM Issues

#### Problem: SIEM Events Not Arriving

**Symptoms:**
- Events missing in Splunk/Datadog
- High failure rate in metrics

**Diagnosis:**
```bash
# Check SIEM configuration
kubectl get configmap sark-config -o yaml | grep SIEM

# Check SIEM connectivity
kubectl exec -it <sark-pod> -- curl -v https://splunk.example.com:8088/services/collector/health

# Check batch handler metrics
kubectl logs <sark-pod> | grep "batch_handler"
```

**Resolution:**
1. Verify SIEM credentials:
   ```bash
   # Splunk
   kubectl get secret sark-secrets -o jsonpath='{.data.SPLUNK_HEC_TOKEN}' | base64 -d

   # Datadog
   kubectl get secret sark-secrets -o jsonpath='{.data.DATADOG_API_KEY}' | base64 -d
   ```

2. Test connectivity manually:
   ```bash
   # Splunk HEC test
   curl -k https://splunk.example.com:8088/services/collector/event \
     -H "Authorization: Splunk <token>" \
     -d '{"event": "test"}'

   # Datadog test
   curl https://http-intake.logs.datadoghq.com/v1/input/<api_key> \
     -H "Content-Type: application/json" \
     -d '{"message": "test"}'
   ```

3. Check SSL/TLS settings:
   ```bash
   # If using self-signed certs
   SPLUNK_VERIFY_SSL=false
   ```

#### Problem: High SIEM Latency

**Symptoms:**
- `average_latency_ms` > 100ms
- Batch processing delays

**Diagnosis:**
```bash
# Check latency breakdown
kubectl logs <sark-pod> | grep "siem_latency"

# Check batch size
kubectl logs <sark-pod> | grep "batch_size"

# Check network latency
kubectl exec -it <sark-pod> -- ping splunk.example.com
```

**Resolution:**
1. Increase batch size (more events per request):
   ```bash
   SIEM_BATCH_SIZE=200  # Default: 100
   ```

2. Adjust batch timeout:
   ```bash
   SIEM_BATCH_TIMEOUT_SECONDS=10  # Default: 5
   ```

3. Enable compression for large payloads:
   ```bash
   SIEM_COMPRESS_PAYLOADS=true
   ```

4. Check SIEM system performance (Splunk indexer lag, Datadog intake)

#### Problem: SIEM Retry Exhaustion

**Symptoms:**
- High `retry_count` in metrics
- Events failing after 3 attempts

**Diagnosis:**
```bash
# Check retry configuration
kubectl get configmap sark-config -o yaml | grep RETRY

# Review retry logs
kubectl logs <sark-pod> | grep "retry_attempt_failed"
```

**Resolution:**
1. Increase retry attempts (for flaky networks):
   ```bash
   SIEM_RETRY_ATTEMPTS=5  # Default: 3
   ```

2. Adjust backoff parameters:
   ```bash
   SIEM_RETRY_BACKOFF_BASE=3.0    # Default: 2.0
   SIEM_RETRY_BACKOFF_MAX=120.0   # Default: 60.0
   ```

3. Implement circuit breaker (if pattern continues):
   - Monitor error rates
   - Temporarily disable SIEM forwarding if >50% failure rate
   - Alert operations team

#### Problem: Batch Queue Full

**Symptoms:**
- "batch_queue_full" errors in logs
- Events being dropped

**Diagnosis:**
```bash
# Check queue metrics
kubectl logs <sark-pod> | grep "events_dropped"

# Check current queue size
kubectl logs <sark-pod> | grep "queue_size"
```

**Resolution:**
1. Increase queue size:
   ```bash
   SIEM_MAX_QUEUE_SIZE=20000  # Default: 10000
   ```

2. Scale horizontally (add more SARK pods)

3. Investigate SIEM slowness causing backlog

4. Temporary mitigation - drop low-priority events:
   ```python
   # Configure event filtering (code change required)
   # Only forward HIGH and CRITICAL severity events
   ```

### SIEM Performance Tuning

#### Optimal Configuration for 10,000+ events/min

```bash
# Batch settings
SIEM_BATCH_SIZE=200
SIEM_BATCH_TIMEOUT_SECONDS=5
SIEM_MAX_QUEUE_SIZE=20000

# Retry settings
SIEM_RETRY_ATTEMPTS=3
SIEM_RETRY_BACKOFF_BASE=2.0
SIEM_RETRY_BACKOFF_MAX=60.0

# Timeout settings
SIEM_TIMEOUT_SECONDS=30

# SSL settings
SIEM_VERIFY_SSL=true
```

#### Performance Benchmarks

| Batch Size | Events/min | Avg Latency | Network Usage |
|------------|------------|-------------|---------------|
| 50 | 5,000 | 35ms | 2 MB/min |
| 100 | 10,000 | 42ms | 4 MB/min |
| 200 | 18,000 | 58ms | 7 MB/min |
| 500 | 25,000 | 95ms | 12 MB/min |

**Recommendation:** Use batch size 100-200 for optimal latency/throughput balance.

---

## Policy Performance Tuning

OPA policy evaluation performance is critical for SARK's authorization system.

### Performance Targets

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| **Cache Hit Rate** | >80% | <70% | <50% |
| **Cache Latency (p95)** | <5ms | <10ms | <20ms |
| **OPA Latency (p95)** | <50ms | <100ms | <200ms |
| **Evaluation Rate** | 1000/s | 500/s | 100/s |

### Cache Performance

#### Check Cache Hit Rate

```bash
# Via Redis
kubectl exec -it <redis-pod> -- redis-cli INFO stats | grep keyspace

# Via application metrics
kubectl logs <sark-pod> | grep "policy_cache_hit_rate"

# Expected: >80% hit rate
```

#### Improve Cache Hit Rate

**If hit rate < 80%:**

1. **Increase TTL for low-sensitivity policies:**
   ```bash
   # Edit policy cache configuration
   POLICY_CACHE_TTL_LOW=600      # 10 min (default: 300)
   POLICY_CACHE_TTL_MEDIUM=300   # 5 min (default: 180)
   ```

2. **Pre-warm cache for common operations:**
   ```python
   # Script to pre-warm cache with common policy evaluations
   # Run during deployment/startup
   ```

3. **Analyze cache misses:**
   ```bash
   # Look for patterns in cache misses
   kubectl logs <sark-pod> | grep "policy_cache_miss" | jq '.context'
   ```

#### Tune Cache Memory

```bash
# Check Redis memory usage
kubectl exec -it <redis-pod> -- redis-cli INFO memory

# Check number of cached policies
kubectl exec -it <redis-pod> -- redis-cli DBSIZE

# Set Redis max memory
kubectl exec -it <redis-pod> -- redis-cli CONFIG SET maxmemory 2gb
kubectl exec -it <redis-pod> -- redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### OPA Performance

#### Check OPA Latency

```bash
# Via application logs
kubectl logs <sark-pod> | grep "opa_evaluation_latency"

# Via OPA metrics (if enabled)
kubectl exec -it <opa-pod> -- curl http://localhost:8181/metrics
```

#### Optimize OPA Policies

**If latency > 50ms (p95):**

1. **Profile slow policies:**
   ```bash
   # Enable OPA profiling
   OPA_LOG_LEVEL=debug

   # Review profiler output
   kubectl logs <opa-pod> | grep "timer_rego"
   ```

2. **Simplify complex policies:**
   ```rego
   # Before (slow - nested loops)
   allow {
     some i
     input.user.roles[i] == role
     some j
     data.permissions[role][j].action == input.action
   }

   # After (fast - sets)
   allow {
     role := input.user.roles[_]
     permission := data.permissions[role][_]
     permission.action == input.action
   }
   ```

3. **Use policy indexing:**
   ```rego
   # Create indexes for fast lookups
   role_permissions[role] = permissions {
     permissions := {p | p := data.permissions[role][_]}
   }
   ```

4. **Reduce data bundle size:**
   ```bash
   # Minimize data sent to OPA
   # Only include necessary context in policy input
   ```

### Batch Policy Evaluation

For bulk operations, use batch evaluation to reduce overhead:

```python
# Instead of N individual evaluations
for server in servers:
    decision = await opa.evaluate(server)

# Use single batch evaluation
decisions = await opa.evaluate_batch(servers)
```

**Performance Improvement:** ~10x faster for batches of 100+ items

### Policy Monitoring

#### Key Metrics

```bash
# Prometheus metrics (example)
opa_policy_evaluation_duration_seconds_bucket
opa_policy_cache_hit_rate
opa_policy_cache_miss_total
opa_policy_evaluation_errors_total
```

#### Alerts

```yaml
# Example Prometheus alerts
- alert: LowPolicyCacheHitRate
  expr: opa_policy_cache_hit_rate < 0.7
  for: 10m
  annotations:
    summary: "Policy cache hit rate below 70%"

- alert: HighPolicyLatency
  expr: histogram_quantile(0.95, opa_policy_evaluation_duration_seconds_bucket) > 0.1
  for: 5m
  annotations:
    summary: "Policy evaluation p95 latency > 100ms"
```

---

## Retry Handler Operations

SARK uses exponential backoff retry logic for resilient operations.

### Retry Configuration

```bash
# Global retry settings
RETRY_ATTEMPTS=3
RETRY_BACKOFF_BASE=2.0
RETRY_BACKOFF_MAX=60.0
RETRY_TIMEOUT_SECONDS=30
```

### Retry Behavior

| Attempt | Backoff Delay | Total Time |
|---------|---------------|------------|
| 1 | 0s (immediate) | 0s |
| 2 | 2s | 2s |
| 3 | 4s | 6s |
| 4 | 8s | 14s |

### Monitor Retry Performance

```bash
# Check retry metrics
kubectl logs <sark-pod> | grep "retry_attempt_failed"

# Count retries by operation
kubectl logs <sark-pod> | grep "retry_attempt" | jq -r '.operation' | sort | uniq -c

# Identify operations requiring retries most often
kubectl logs <sark-pod> | grep "retry_success" | jq '{operation: .operation, attempts: .total_attempts}'
```

### Troubleshoot High Retry Rates

**If retry rate > 5% for any operation:**

1. **Identify root cause:**
   ```bash
   # Check which errors trigger retries
   kubectl logs <sark-pod> | grep "retry_attempt_failed" | jq '.error_type' | sort | uniq -c
   ```

2. **Increase timeout for slow operations:**
   ```bash
   SIEM_TIMEOUT_SECONDS=60  # If TimeoutError is common
   ```

3. **Increase retry attempts for flaky services:**
   ```bash
   SIEM_RETRY_ATTEMPTS=5  # If transient errors are frequent
   ```

4. **Investigate underlying service health:**
   - Network latency
   - Service availability
   - Resource constraints

### Disable Retries (Emergency)

```bash
# Temporarily disable retries to prevent cascading failures
RETRY_ATTEMPTS=1  # Fail fast instead of retrying

# Re-enable after issue is resolved
RETRY_ATTEMPTS=3
```

---

## Common Operational Tasks

### 1. Scale Application

```bash
# Horizontal scaling
kubectl scale deployment sark --replicas=5

# Verify
kubectl get pods -l app=sark

# Check load distribution
kubectl top pods -l app=sark
```

### 2. Rolling Update

```bash
# Update image
kubectl set image deployment/sark sark=sark:v0.2.0

# Monitor rollout
kubectl rollout status deployment/sark

# Rollback if needed
kubectl rollout undo deployment/sark
```

### 3. Database Migration

```bash
# Run migration job
kubectl apply -f k8s/jobs/db-migration.yaml

# Monitor migration
kubectl logs job/db-migration -f

# Verify migration
kubectl exec -it <sark-pod> -- alembic current
```

### 4. Clear Policy Cache

```bash
# Clear all policy decisions
kubectl exec -it <redis-pod> -- redis-cli
> EVAL "return redis.call('del', unpack(redis.call('keys', 'policy:decision:*')))" 0

# Verify cache cleared
> KEYS "policy:decision:*"
```

### 5. Export Audit Logs

```bash
# Via psql
kubectl exec -it <postgres-pod> -- psql -U sark -c "COPY (SELECT * FROM audit_events WHERE timestamp > NOW() - INTERVAL '24 hours') TO STDOUT CSV HEADER;" > audit_logs.csv

# Via SIEM (preferred)
# Logs are already in Splunk/Datadog
```

### 6. Rotate Secrets

```bash
# Update secret
kubectl create secret generic sark-secrets-new \
  --from-literal=database_url='...' \
  --from-literal=jwt_secret='...'

# Update deployment to use new secret
kubectl patch deployment sark -p '{"spec":{"template":{"spec":{"containers":[{"name":"sark","envFrom":[{"secretRef":{"name":"sark-secrets-new"}}]}]}}}}'

# Delete old secret after verification
kubectl delete secret sark-secrets
```

---

## Emergency Procedures

### Emergency Contact Tree

1. **On-call SRE** → PagerDuty alert
2. **Engineering Lead** → Slack #incidents
3. **Security Team** → If security incident
4. **Management** → If P0 outage > 30 minutes

### P0: Complete Service Outage

**Symptoms:** All requests failing, health checks down

**Immediate Actions:**
```bash
# 1. Check pod status
kubectl get pods -l app=sark

# 2. Check recent events
kubectl get events --sort-by='.lastTimestamp' | head -20

# 3. Check logs
kubectl logs -l app=sark --tail=100 --timestamps

# 4. Quick restart (if no obvious issue)
kubectl rollout restart deployment/sark
```

**If restart doesn't help:**
```bash
# Rollback to previous version
kubectl rollout undo deployment/sark

# Check database connectivity
kubectl exec -it <postgres-pod> -- psql -U sark -c "SELECT 1;"

# Check Redis connectivity
kubectl exec -it <redis-pod> -- redis-cli PING

# Check resource constraints
kubectl describe nodes | grep -A 5 "Allocated resources"
```

### P1: Authentication Failures

**Symptoms:** Users cannot log in, 503 errors

**Immediate Actions:**
```bash
# Check Redis (session store)
kubectl get pods -l app=redis
kubectl logs <redis-pod> --tail=50

# Restart Redis if down
kubectl rollout restart deployment/redis

# Verify Redis connectivity from SARK
kubectl exec -it <sark-pod> -- curl http://localhost:8000/health/detailed | jq '.redis'
```

### P1: SIEM Outage

**Symptoms:** Events not forwarding, high failure rate

**Immediate Actions:**
```bash
# Option 1: Temporarily disable SIEM forwarding
kubectl set env deployment/sark SIEM_ENABLED=false

# Option 2: Increase queue size to buffer events
kubectl set env deployment/sark SIEM_MAX_QUEUE_SIZE=50000

# Monitor queue
kubectl logs <sark-pod> | grep "queue_size"

# Re-enable after SIEM recovery
kubectl set env deployment/sark SIEM_ENABLED=true
```

### P2: High Latency

**Symptoms:** Slow response times, timeouts

**Immediate Actions:**
```bash
# Check current latency
kubectl logs <sark-pod> | grep "request_duration_ms"

# Check resource usage
kubectl top pods -l app=sark
kubectl top nodes

# Scale horizontally if CPU/Memory high
kubectl scale deployment sark --replicas=10

# Check database slow queries
kubectl exec -it <postgres-pod> -- psql -U sark -c "SELECT pid, query, state, wait_event FROM pg_stat_activity WHERE state != 'idle';"

# Check OPA latency
kubectl logs <sark-pod> | grep "opa_evaluation_latency"
```

---

## Monitoring & Alerts

### Critical Alerts (Page Immediately)

| Alert | Condition | Action |
|-------|-----------|--------|
| **ServiceDown** | Health check fails | Check pod status, restart if needed |
| **HighErrorRate** | Error rate > 5% | Check logs, rollback if recent deploy |
| **DatabaseDown** | DB connection fails | Check PostgreSQL, check credentials |
| **RedisDown** | Redis connection fails | Restart Redis, check network |

### Warning Alerts (Investigate During Business Hours)

| Alert | Condition | Action |
|-------|-----------|--------|
| **LowCacheHitRate** | Cache hit < 70% | Tune TTL, analyze patterns |
| **HighPolicyLatency** | OPA latency > 100ms | Optimize policies, check OPA resources |
| **SIEMFailures** | SIEM failure rate > 1% | Check SIEM connectivity, credentials |
| **HighMemoryUsage** | Memory > 80% | Consider scaling, check for memory leaks |

### Dashboard Widgets

**Application Health:**
- Request rate (req/s)
- Error rate (%)
- Response time (p50, p95, p99)
- Active connections

**Authentication:**
- Login attempts/min
- Login success rate
- Active sessions
- Token refresh rate

**Policy Evaluation:**
- Evaluations/s
- Cache hit rate
- Cache latency (p95)
- OPA latency (p95)

**SIEM:**
- Events sent/min
- SIEM success rate
- Batch latency
- Queue size

---

## Appendix

### Useful Commands

```bash
# Quick health check
kubectl exec -it <sark-pod> -- curl -s http://localhost:8000/health | jq .

# Tail all logs
kubectl logs -l app=sark -f --max-log-requests=10

# Get recent errors
kubectl logs -l app=sark --since=1h | grep -i error

# Check configuration
kubectl get configmap sark-config -o yaml

# Check secrets (names only)
kubectl get secret sark-secrets -o jsonpath='{.data}' | jq 'keys'

# Port forward for local debugging
kubectl port-forward svc/sark 8000:8000
```

### Configuration Reference

See [DEPLOYMENT.md](./DEPLOYMENT.md) for complete environment variable reference.

### Related Documentation

- [AUTHENTICATION.md](./AUTHENTICATION.md) - Authentication setup and troubleshooting
- [AUTHORIZATION.md](./AUTHORIZATION.md) - Policy configuration and tuning
- [SIEM Integration](./siem/SIEM_INTEGRATION.md) - SIEM setup and troubleshooting
- [MONITORING.md](./MONITORING.md) - Monitoring and alerting setup

---

**Document Maintenance:**
- Review quarterly
- Update after major incidents
- Version with application releases
