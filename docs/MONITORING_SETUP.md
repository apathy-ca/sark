# SARK Monitoring & Alerting - Quick Setup Guide

**Version**: 1.0 | **Date**: November 2025 | **Status**: Production Ready

---

## Overview

SARK provides production-ready monitoring through:
- **4 Grafana Dashboards**: Overview, Auth, Policies, SIEM
- **25+ Prometheus Alerts**: Organized by severity and component
- **Health Check Endpoints**: Kubernetes-compatible probes
- **50+ Metrics**: Complete system observability

---

## Quick Start (5 Minutes)

### 1. Start Monitoring Stack

```bash
# Using Docker Compose
docker-compose up -d prometheus grafana alertmanager

# Or use the provided stack
cd monitoring/
docker-compose up -d
```

### 2. Import Dashboards

```bash
# Grafana will be at http://localhost:3000 (admin/admin)
# Dashboards auto-import from grafana/dashboards/*.json

# Manual import if needed:
for dashboard in grafana/dashboards/*.json; do
  curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
    -H "Content-Type: application/json" \
    -d @$dashboard
done
```

### 3. Verify Setup

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check metrics endpoint
curl http://localhost:8000/metrics | grep sark_

# Trigger test alert
curl -X GET http://localhost:8000/health/ready
```

---

## Grafana Dashboards

### 1. SARK Overview (`sark-overview.json`)
**URL**: http://localhost:3000/d/sark-overview

**Key Panels**:
- Request rate & error rate
- P95/P99 response time
- System health & cache hit rate
- Top endpoints & slowest APIs

**Use For**: Daily health checks, incident triage, SLA monitoring

### 2. SARK Authentication & Authorization (`sark-auth.json`)
**URL**: http://localhost:3000/d/sark-auth

**Key Panels**:
- Auth attempts & success rate
- Authorization decisions (allow/deny)
- MFA verification & IP filtering
- Policy violations & failed logins

**Use For**: Security monitoring, brute force detection

### 3. SARK Policy Evaluation (`sark-policies.json`)
**URL**: http://localhost:3000/d/sark-policies

**Key Panels**:
- Policy evaluation latency (P50/P95/P99)
- Cache performance & hit rates
- Batch evaluation metrics
- OPA request duration

**Use For**: Performance optimization, cache tuning

### 4. SARK SIEM & Security (`sark-siem.json`)
**URL**: http://localhost:3000/d/sark-siem

**Key Panels**:
- SIEM events & export status
- Security events by severity
- Anomalous access patterns
- Data exfiltration alerts

**Use For**: Security operations, incident response

---

## Critical Alerts

Alerts configured in `prometheus/alerts/sark-alerts.yml`:

### Severity Levels
- **Critical** → PagerDuty (immediate response)
- **High** → Slack #incidents (15 min response)
- **Warning** → Slack #alerts (1 hour response)
- **Info** → Email (next day)

### Top 10 Alerts to Watch

| Alert | Severity | Threshold | Action |
|-------|----------|-----------|--------|
| SARKServiceDown | Critical | Service unavailable >1min | Restart service |
| HighErrorRate | Critical | >5% errors for 5min | Check logs, rollback |
| SIEMExportFailures | Critical | >5 failures in 5min | Check SIEM connectivity |
| BruteForceAttackSuspected | High | >5 failed logins/sec | Block IP, notify user |
| MFABypassAttempts | Critical | Any MFA bypass detected | Immediate investigation |
| SlowPolicyEvaluation | Warning | P95 >60ms for 10min | Check cache, OPA |
| LowPolicyCacheHitRate | Warning | <70% for 10min | Tune TTL, preload cache |
| DataExfiltrationDetected | Critical | Any exfiltration event | Incident response |
| SIEMQueueFull | Critical | Queue at capacity | Increase capacity |
| SlowResponseTime | Warning | P95 >200ms for 10min | Performance profiling |

---

## Health Check Endpoints

All endpoints return JSON and follow Kubernetes health check conventions:

### Liveness Probe
```bash
GET /health/live
# Returns 200 if process is alive
# Kubernetes: Restart if failing
```

### Readiness Probe
```bash
GET /health/ready
# Returns 200 if ready to serve traffic
# Checks: Database, Redis, OPA
# Kubernetes: Remove from load balancer if failing
```

### Startup Probe
```bash
GET /health/startup
# Returns 200 when initialized
# Kubernetes: Wait up to 5min for startup
```

### Detailed Health
```bash
GET /health/detailed
# Returns component-level health status
# Use for: Debugging, status pages
```

**Kubernetes Configuration**:
```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  failureThreshold: 3

startupProbe:
  httpGet:
    path: /health/startup
    port: 8000
  periodSeconds: 10
  failureThreshold: 30
```

---

## Key Metrics

### Performance Targets
```promql
# Request rate (target: >500/s)
rate(http_requests_total{job="sark"}[5m])

# Error rate (target: <1%)
sum(rate(http_requests_total{status=~"5.."}[5m])) /
sum(rate(http_requests_total[5m])) * 100

# P95 response time (target: <200ms)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) * 1000

# Cache hit rate (target: >80%)
(rate(sark_policy_cache_hits_total[5m]) + rate(sark_policy_cache_stale_hits_total[5m])) /
(rate(sark_policy_cache_hits_total[5m]) + rate(sark_policy_cache_stale_hits_total[5m]) + rate(sark_policy_cache_misses_total[5m])) * 100
```

### Full Metrics List

**HTTP**: `http_requests_total`, `http_request_duration_seconds`
**Auth**: `sark_auth_attempts_total`, `sark_mfa_requirement_checks_total`
**Policy**: `sark_policy_evaluations_total`, `sark_policy_evaluation_duration_seconds`
**Cache**: `sark_policy_cache_hits_total`, `sark_policy_cache_misses_total`, `sark_policy_cache_stale_hits_total`
**Batch**: `sark_batch_policy_evaluations_total`, `sark_batch_evaluation_duration_seconds`
**SIEM**: `sark_siem_events_total`, `sark_siem_exports_total`, `sark_siem_queue_depth`
**System**: `sark_db_connections_checked_out`, `sark_redis_connection_pool_size`

---

## Alert Runbooks

### HighErrorRate (Critical)

**Investigation**:
```bash
# 1. Check error rate by endpoint
curl 'http://localhost:9090/api/v1/query?query=topk(10, sum(rate(http_requests_total{status=~"5.."}[5m])) by (path))'

# 2. Check logs
kubectl logs -l app=sark --tail=100 | grep ERROR

# 3. Check recent deployments
kubectl rollout history deployment/sark
```

**Resolution**:
```bash
# If recent deployment caused it
kubectl rollout undo deployment/sark

# If database issues
kubectl scale deployment/sark --replicas=5  # Scale out

# If dependency failure
kubectl get pods  # Check all services
```

### LowPolicyCacheHitRate (Warning)

**Investigation**:
```bash
# Check hit rate by sensitivity
curl 'http://localhost:9090/api/v1/query?query=sum(rate(sark_policy_cache_hits_total[5m])) by (sensitivity_level) / (sum(rate(sark_policy_cache_hits_total[5m])) by (sensitivity_level) + sum(rate(sark_policy_cache_misses_total[5m])) by (sensitivity_level)) * 100'

# Check cache size
curl http://localhost:8000/health/metrics/summary | jq '.cache'
```

**Resolution**:
1. **Increase TTL** (if security allows):
   - Critical: 30s → 60s
   - Confidential: 60s → 120s
   
2. **Enable cache preloading**:
   ```python
   await cache.preload_cache(get_top_user_tool_combinations())
   ```

3. **Enable stale-while-revalidate**:
   ```python
   cache = PolicyCache(stale_while_revalidate=True)
   ```

### SIEMExportFailures (Critical)

**Investigation**:
```bash
# 1. Test SIEM connectivity
curl -X POST $SIEM_ENDPOINT/events \
  -H "Authorization: Bearer $SIEM_TOKEN" \
  -d '{"test": "event"}'

# 2. Check queue status
curl http://localhost:8000/health/metrics/summary

# 3. Check logs
kubectl logs -l app=sark | grep siem_export_error
```

**Resolution**:
```bash
# If auth failure
kubectl create secret generic siem-credentials \
  --from-literal=token=$NEW_TOKEN --dry-run=client -o yaml | kubectl apply -f -
kubectl rollout restart deployment/sark

# If network issues
kubectl exec -it sark-pod -- curl $SIEM_ENDPOINT

# If queue full
kubectl scale deployment/sark --replicas=5  # Add workers
```

---

## Production Checklist

### Pre-Deployment
- [ ] Prometheus scraping SARK metrics
- [ ] All 4 Grafana dashboards imported
- [ ] Alert rules loaded in Prometheus
- [ ] Alertmanager configured (Slack, PagerDuty)
- [ ] Health checks configured in K8s
- [ ] Runbooks accessible to on-call team
- [ ] Test alerts verified

### Monitoring Baseline
- [ ] Request rate: 500-1000/s
- [ ] Error rate: <1%
- [ ] P95 latency: <50ms
- [ ] Cache hit rate: >80%
- [ ] SIEM export success: >98%

### Daily Operations
- [ ] Check SARK Overview dashboard
- [ ] Verify no critical alerts firing
- [ ] Review slow queries
- [ ] Check cache hit rate trends
- [ ] Verify SIEM export status

---

## Troubleshooting

### No Metrics in Prometheus
```bash
# 1. Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="sark")'

# 2. Verify metrics endpoint
curl http://localhost:8000/metrics | head -20

# 3. Check Prometheus config
docker exec prometheus cat /etc/prometheus/prometheus.yml
```

### Dashboards Show "No Data"
```bash
# 1. Verify Prometheus data source
curl http://localhost:3000/api/datasources

# 2. Test query directly in Prometheus
curl 'http://localhost:9090/api/v1/query?query=up{job="sark"}'

# 3. Check time range in Grafana
```

### Alerts Not Firing
```bash
# 1. Check alert rules
docker exec prometheus promtool check rules /etc/prometheus/alerts/sark-alerts.yml

# 2. Check alert state
curl http://localhost:9090/api/v1/alerts

# 3. Check Alertmanager
curl http://localhost:9093/api/v1/alerts
```

---

## Configuration Files

```
sark/
├── grafana/
│   └── dashboards/
│       ├── sark-overview.json      # System overview
│       ├── sark-auth.json          # Auth & authorization
│       ├── sark-policies.json      # Policy evaluation
│       └── sark-siem.json          # Security events
├── prometheus/
│   └── alerts/
│       └── sark-alerts.yml         # 25+ alert rules
└── docs/
    ├── MONITORING.md               # Full guide (this file)
    └── RUNBOOKS.md                 # Detailed runbooks
```

---

## Support

- **Issues**: https://github.com/sark/issues
- **Docs**: https://docs.sark.dev/monitoring
- **Slack**: #sark-monitoring

---

**Next**: See `docs/RUNBOOKS.md` for detailed incident response procedures.
