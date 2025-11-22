# SARK Troubleshooting Guide

**Master Reference for Diagnosing and Resolving Common Issues**

**Last Updated:** 2025-11-22
**Version:** 1.0

---

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Service Health](#service-health)
3. [Authentication Issues](#authentication-issues)
4. [Authorization & Policy Issues](#authorization--policy-issues)
5. [Session Management Issues](#session-management-issues)
6. [Database Issues](#database-issues)
7. [Redis Issues](#redis-issues)
8. [SIEM Integration Issues](#siem-integration-issues)
9. [Rate Limiting Issues](#rate-limiting-issues)
10. [Performance Issues](#performance-issues)
11. [Docker & Kubernetes Issues](#docker--kubernetes-issues)
12. [API Errors Reference](#api-errors-reference)
13. [Monitoring & Logs](#monitoring--logs)
14. [Getting Help](#getting-help)

---

## Quick Diagnostics

### One-Line Health Check

```bash
# Check all services at once
curl http://localhost:8000/health/detailed | jq

# Expected: All dependencies show "healthy": true
# If any show false, see specific service sections below
```

### Common Symptoms and Quick Fixes

| Symptom | Likely Cause | Quick Fix |
|---------|--------------|-----------|
| 503 Service Unavailable | Service not started or unhealthy | `docker compose ps` → restart unhealthy services |
| 401 Unauthorized | Token expired or invalid | Refresh access token or re-authenticate |
| 403 Forbidden | Policy denied request | Check OPA logs, verify user roles/permissions |
| 429 Too Many Requests | Rate limit exceeded | Wait for rate limit window to reset |
| 500 Internal Server Error | Database/Redis/OPA down | Check `docker compose logs` for errors |
| Slow responses (>1s) | Policy cache miss or DB slow | Check `/health/detailed` latency metrics |

---

## Service Health

### Check All Services

```bash
# Docker Compose
docker compose ps

# Expected: All services show "Up (healthy)"
# If service is "Up (unhealthy)", check logs:
docker compose logs <service-name>

# Kubernetes
kubectl get pods -n production
kubectl describe pod <pod-name>
```

### Detailed Health Endpoint

```bash
# Check individual service health and latency
curl http://localhost:8000/health/detailed | jq

# Response shows latency for each dependency:
# {
#   "dependencies": {
#     "postgresql": {"healthy": true, "latency_ms": 12.5},
#     "redis": {"healthy": true, "latency_ms": 3.2},
#     "opa": {"healthy": true, "latency_ms": 8.7}
#   }
# }
```

**Latency Benchmarks:**
- PostgreSQL: <20ms (healthy), >100ms (investigate)
- Redis: <5ms (healthy), >50ms (investigate)
- OPA: <50ms (healthy), >200ms (investigate)

### Restart Services

```bash
# Docker Compose - restart individual service
docker compose restart api
docker compose restart redis
docker compose restart opa

# Restart all services
docker compose restart

# Kubernetes
kubectl rollout restart deployment/sark -n production
```

---

## Authentication Issues

### Problem: Login Fails with 401 Unauthorized

**Symptoms:**
- `POST /api/v1/auth/login/ldap` returns 401
- Error: "Invalid username or password"

**Causes & Solutions:**

#### 1. LDAP Server Unreachable

```bash
# Test LDAP connectivity
docker compose exec api curl ldap://openldap:389

# Check LDAP service status
docker compose ps openldap

# Test LDAP bind
docker compose exec api ldapsearch -x -H ldap://openldap:389 \
  -D "cn=admin,dc=example,dc=com" \
  -w admin \
  -b "dc=example,dc=com"

# Fix: Restart LDAP
docker compose restart openldap
```

#### 2. Incorrect LDAP Configuration

```bash
# Check environment variables
docker compose exec api env | grep LDAP

# Verify configuration
# LDAP_SERVER=ldap://openldap:389
# LDAP_BIND_DN=cn=admin,dc=example,dc=com
# LDAP_USER_BASE_DN=ou=users,dc=example,dc=com

# Fix: Update .env and restart
nano .env
docker compose restart api
```

#### 3. User Not in LDAP Directory

```bash
# Search for user in LDAP
docker compose exec openldap ldapsearch -x \
  -b "ou=users,dc=example,dc=com" \
  "(uid=john.doe)"

# Fix: Add user to LDAP or use correct username
```

---

### Problem: OIDC/SAML Redirect Loop

**Symptoms:**
- Browser stuck in redirect loop
- Error: "Invalid state parameter"

**Solutions:**

#### 1. State/Session Expired

```bash
# Clear Redis session state
docker compose exec redis redis-cli
127.0.0.1:6379> AUTH redis_password
127.0.0.1:6379> KEYS "oidc:state:*"
127.0.0.1:6379> DEL oidc:state:{state_id}

# Or flush all session state (WARNING: logs out all users)
127.0.0.1:6379> FLUSHDB
```

#### 2. Callback URL Mismatch

```bash
# Check configured callback URL
echo $OIDC_REDIRECT_URI
# Should match: https://sark.example.com/api/v1/auth/oidc/callback

# Fix: Update environment variable and IdP configuration to match
```

#### 3. Clock Skew

```bash
# Check server time
date
# Should match real time

# Sync time (if needed)
sudo ntpdate -s time.nist.gov
```

---

### Problem: Token Refresh Fails

**Symptoms:**
- `POST /api/v1/auth/refresh` returns 401
- Error: "Invalid or expired refresh token"

**Diagnosis:**

```bash
# Check if refresh token exists in Redis
docker compose exec redis redis-cli -a redis_password
127.0.0.1:6379> GET "refresh_token:user:{user_id}:{token_id}"

# Check TTL (should be positive)
127.0.0.1:6379> TTL "refresh_token:user:{user_id}:{token_id}"
# Returns: seconds remaining (positive) or -2 (expired/doesn't exist)
```

**Solutions:**

#### 1. Token Expired (7 days passed)
- **Fix:** User must re-authenticate via login endpoint

#### 2. Token Revoked
- **Fix:** Check audit logs for revocation event, user must re-authenticate

#### 3. Redis Data Loss
```bash
# Check Redis uptime
docker compose exec redis redis-cli -a redis_password INFO server | grep uptime_in_seconds

# If Redis restarted recently, sessions may be lost
# Fix: Enable Redis persistence in production (AOF or RDB)
```

---

## Authorization & Policy Issues

### Problem: Policy Evaluation Returns "deny" Unexpectedly

**Symptoms:**
- `POST /api/v1/policy/evaluate` returns `{"decision": "deny"}`
- User believes they should have access

**Diagnosis:**

```bash
# Check policy decision with reason
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "...",
    "action": "tool:invoke",
    "tool": "execute_query"
  }' | jq '.reason'

# Common denial reasons:
# - "Tool sensitivity level 'critical' exceeds user's maximum allowed level 'high'"
# - "User does not have required role 'admin'"
# - "MFA verification required for critical operations"
# - "Access denied outside business hours (9 AM - 5 PM)"
# - "IP address not in corporate network whitelist"
```

**Solutions:**

#### 1. Insufficient Role/Permissions

```bash
# Check user roles
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.roles'

# Fix: Add required role in LDAP/OIDC or update policy to allow current role
```

#### 2. Time-Based Restriction

```bash
# Check current time and business hours policy
# Policy may restrict access to business hours only

# Fix: Update OPA policy to allow access 24/7 or during required hours
```

#### 3. IP-Based Restriction

```bash
# Check request IP
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Content-Type: application/json" \
  -d '{"context": {"ip_address": "YOUR_IP"}}'

# Fix: Add IP to whitelist in OPA policy or use VPN
```

---

### Problem: OPA Service Unavailable

**Symptoms:**
- Policy evaluation fails with 503
- Error: "OPA service temporarily unavailable"

**Diagnosis:**

```bash
# Check OPA health
curl http://localhost:8181/health

# Check OPA logs
docker compose logs opa

# Test OPA directly
curl -X POST http://localhost:8181/v1/data/mcp/allow \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "user": {"id": "test", "role": "developer"},
      "action": "tool:invoke",
      "tool": {"name": "test", "sensitivity_level": "low"}
    }
  }'
```

**Solutions:**

#### 1. OPA Service Down

```bash
# Restart OPA
docker compose restart opa

# Kubernetes
kubectl rollout restart deployment/opa -n production
```

#### 2. Policy Syntax Error

```bash
# Validate policies
docker compose exec opa opa test /policies -v

# Check for syntax errors in output
# Fix: Correct Rego syntax in policy files
```

#### 3. Policy Bundle Not Loaded

```bash
# Check loaded policies
curl http://localhost:8181/v1/policies

# Reload policies
docker compose restart opa

# Or manually upload
curl -X PUT http://localhost:8181/v1/policies/sark \
  -H "Content-Type: text/plain" \
  --data-binary @opa/policies/defaults/main.rego
```

---

### Problem: Policy Cache Issues

**Symptoms:**
- Policy changes not taking effect immediately
- Stale decisions being returned

**Diagnosis:**

```bash
# Check cache hit rate
curl http://localhost:8000/metrics | grep policy_cache

# policy_cache_hits_total{} 1250
# policy_cache_misses_total{} 250
# Cache hit rate: 1250/(1250+250) = 83% (good)
```

**Solutions:**

#### 1. Clear Policy Cache

```bash
# Flush policy cache in Redis
docker compose exec redis redis-cli -a redis_password
127.0.0.1:6379> KEYS "policy:decision:*"
127.0.0.1:6379> DEL policy:decision:{key}

# Or flush all policy cache keys
127.0.0.1:6379> EVAL "return redis.call('del', unpack(redis.call('keys', 'policy:decision:*')))" 0
```

#### 2. Bypass Cache for Testing

```bash
# Use X-Skip-Policy-Cache header
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "X-Skip-Policy-Cache: true" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

#### 3. Adjust Cache TTL

```bash
# Edit .env
POLICY_CACHE_TTL_HIGH=30  # Reduce from 60s to 30s
POLICY_CACHE_TTL_CRITICAL=15  # Reduce from 30s to 15s

# Restart
docker compose restart api
```

---

## Session Management Issues

### Problem: Sessions Expire Too Quickly

**Symptoms:**
- Users logged out after 60 minutes
- Frequent token refresh requests

**Solutions:**

#### 1. Adjust Access Token TTL

```bash
# Edit .env
JWT_EXPIRATION_MINUTES=120  # Increase from 60 to 120 minutes

# Restart API
docker compose restart api
```

#### 2. Adjust Refresh Token TTL

```bash
# Edit .env
REFRESH_TOKEN_EXPIRATION_DAYS=30  # Increase from 7 to 30 days

docker compose restart api
```

---

### Problem: "Too Many Active Sessions"

**Symptoms:**
- Login fails with error about session limit
- Old sessions not being cleaned up

**Diagnosis:**

```bash
# Check user's active sessions
docker compose exec redis redis-cli -a redis_password
127.0.0.1:6379> KEYS "refresh_token:user:{user_id}:*"

# Count sessions
127.0.0.1:6379> EVAL "return #redis.call('keys', 'refresh_token:user:{user_id}:*')" 0
```

**Solutions:**

#### 1. Increase Session Limit

```bash
# Edit .env
MAX_SESSIONS_PER_USER=10  # Increase from 5 to 10

docker compose restart api
```

#### 2. Manually Revoke Old Sessions

```bash
# List sessions with timestamps
127.0.0.1:6379> KEYS "refresh_token:user:{user_id}:*"

# Delete oldest session
127.0.0.1:6379> DEL "refresh_token:user:{user_id}:{token_id}"
```

#### 3. Enable Auto-Cleanup Job

```bash
# Add cron job to clean expired sessions
# In production, use Kubernetes CronJob

# Example cleanup script
*/10 * * * * docker compose exec redis redis-cli -a redis_password EVAL "$(cat cleanup-sessions.lua)" 0
```

---

## Database Issues

### Problem: Database Connection Errors

**Symptoms:**
- API returns 500 errors
- Error: "Could not connect to database"

**Diagnosis:**

```bash
# Check PostgreSQL service
docker compose ps postgres

# Test connection
docker compose exec postgres pg_isready -U sark

# Check logs
docker compose logs postgres
```

**Solutions:**

#### 1. PostgreSQL Not Running

```bash
# Start PostgreSQL
docker compose up -d postgres

# Check health
docker compose ps postgres
```

#### 2. Connection Pool Exhausted

```bash
# Check active connections
docker compose exec postgres psql -U sark -d sark
sark=# SELECT count(*) FROM pg_stat_activity;

# Check max connections
sark=# SHOW max_connections;

# Fix: Increase pool size or max connections
# Edit .env
DATABASE_POOL_SIZE=50  # Increase from 20
DATABASE_MAX_OVERFLOW=20  # Increase from 10

docker compose restart api
```

#### 3. Database Corrupted

```bash
# Backup database first!
docker compose exec postgres pg_dump -U sark sark > backup.sql

# Restart with fresh database (WARNING: DATA LOSS)
docker compose down -v
docker compose up -d

# Restore from backup
cat backup.sql | docker compose exec -T postgres psql -U sark -d sark
```

---

### Problem: Slow Database Queries

**Diagnosis:**

```bash
# Check slow queries
docker compose exec postgres psql -U sark -d sark
sark=# SELECT query, mean_exec_time
       FROM pg_stat_statements
       ORDER BY mean_exec_time DESC
       LIMIT 10;

# Check table sizes
sark=# SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
       FROM pg_tables
       WHERE schemaname = 'public'
       ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

**Solutions:**

#### 1. Missing Indexes

```sql
-- Add indexes on frequently queried columns
CREATE INDEX idx_servers_status ON servers(status);
CREATE INDEX idx_audit_events_timestamp ON audit_events(timestamp DESC);
CREATE INDEX idx_audit_events_user_id ON audit_events(user_id);
```

#### 2. Vacuum Database

```bash
# Run VACUUM to reclaim space and update statistics
docker compose exec postgres psql -U sark -d sark -c "VACUUM ANALYZE;"
```

#### 3. Enable Query Logging

```bash
# Edit postgresql.conf
log_min_duration_statement = 1000  # Log queries >1 second

# Restart PostgreSQL
docker compose restart postgres
```

---

## Redis Issues

### Problem: Redis Connection Errors

**Symptoms:**
- Session management fails
- Policy cache unavailable
- Error: "Connection refused" or "Connection timeout"

**Diagnosis:**

```bash
# Check Redis service
docker compose ps redis

# Test connection
docker compose exec redis redis-cli -a redis_password ping
# Expected: PONG

# Check logs
docker compose logs redis
```

**Solutions:**

#### 1. Redis Not Running

```bash
# Start Redis
docker compose up -d redis
```

#### 2. Wrong Password

```bash
# Check Redis password in .env
echo $REDIS_PASSWORD

# Test with correct password
docker compose exec redis redis-cli -a $REDIS_PASSWORD ping
```

#### 3. Redis Out of Memory

```bash
# Check memory usage
docker compose exec redis redis-cli -a redis_password INFO memory

# used_memory_human:1.5G
# maxmemory:2.0G

# Fix: Increase max memory or enable eviction
docker compose exec redis redis-cli -a redis_password CONFIG SET maxmemory 4gb
docker compose exec redis redis-cli -a redis_password CONFIG SET maxmemory-policy allkeys-lru
```

---

### Problem: High Redis Latency

**Diagnosis:**

```bash
# Check latency
docker compose exec redis redis-cli -a redis_password --latency

# Check slow log
docker compose exec redis redis-cli -a redis_password SLOWLOG GET 10
```

**Solutions:**

#### 1. Too Many Keys

```bash
# Count keys
docker compose exec redis redis-cli -a redis_password DBSIZE

# Fix: Enable key expiration, increase memory, or use Redis cluster
```

#### 2. Large Key Values

```bash
# Find large keys
docker compose exec redis redis-cli -a redis_password --bigkeys

# Fix: Reduce value size or split into smaller keys
```

---

## SIEM Integration Issues

### Problem: Events Not Forwarded to SIEM

**Symptoms:**
- No events appearing in Splunk/Datadog
- SIEM dashboards empty

**Diagnosis:**

```bash
# Check SIEM enabled
echo $SIEM_ENABLED  # Should be "true"

# Check metrics
curl http://localhost:8000/metrics | grep siem_events

# siem_events_forwarded_total{siem="splunk"} 0
# siem_events_failed_total{siem="splunk"} 150

# Check circuit breaker state
docker compose exec redis redis-cli -a redis_password
127.0.0.1:6379> GET circuit:splunk:state
# "open" means circuit is broken due to failures
```

**Solutions:**

#### 1. Circuit Breaker Open

```bash
# Reset circuit breaker
127.0.0.1:6379> DEL circuit:splunk:state
127.0.0.1:6379> DEL circuit:splunk:failure

# Wait for automatic recovery (30 seconds)
```

#### 2. Invalid HEC Token (Splunk)

```bash
# Test Splunk HEC manually
curl -k https://splunk.example.com:8088/services/collector/event \
  -H "Authorization: Splunk YOUR_HEC_TOKEN" \
  -d '{"event": "test", "sourcetype": "sark:audit"}'

# Expected: {"text":"Success","code":0}

# Fix: Update HEC token in .env
SPLUNK_HEC_TOKEN=new-valid-token
docker compose restart api
```

#### 3. Network Connectivity

```bash
# Test connectivity from SARK to Splunk
docker compose exec api curl -I https://splunk.example.com:8088

# Check firewall rules
# Fix: Open firewall ports or use proxy
```

---

### Problem: SIEM Forwarding Slow/Lagging

**Diagnosis:**

```bash
# Check queue size
curl http://localhost:8000/metrics | grep siem_queue_size

# siem_queue_size_total{} 15000  # Large backlog

# Check batch processing
curl http://localhost:8000/metrics | grep siem_batch

# siem_batch_size_bytes_sum / siem_batch_size_bytes_count = avg batch size
```

**Solutions:**

#### 1. Increase Batch Size

```bash
# Edit .env
SIEM_BATCH_SIZE=200  # Increase from 100
SIEM_BATCH_TIMEOUT_SECONDS=10  # Increase from 5

docker compose restart api
```

#### 2. Increase Concurrent Workers

```bash
# Edit SIEM forwarder config
SIEM_CONCURRENT_WORKERS=8  # Increase from 4

docker compose restart api
```

#### 3. Enable Compression

```bash
# Edit .env
SIEM_COMPRESS_PAYLOADS=true

docker compose restart api
```

---

## Rate Limiting Issues

### Problem: Legitimate Requests Getting Rate Limited

**Symptoms:**
- Users hitting 429 Too Many Requests unexpectedly
- API keys being throttled during normal operation

**Diagnosis:**

```bash
# Check current rate limit usage
curl -v -X GET http://localhost:8000/api/v1/servers \
  -H "Authorization: Bearer $ACCESS_TOKEN" 2>&1 | grep RateLimit

# X-RateLimit-Limit: 5000
# X-RateLimit-Remaining: 0
# X-RateLimit-Reset: 1638360045
```

**Solutions:**

#### 1. Increase User Rate Limit

```bash
# Edit .env
RATE_LIMIT_USER_REQUESTS_PER_MINUTE=10000  # Increase from 5000

docker compose restart api
```

#### 2. Increase API Key Rate Limit

```bash
# Update existing API key
curl -X PATCH "http://localhost:8000/api/auth/api-keys/$KEY_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"rate_limit": 5000}'  # Increase from 1000
```

#### 3. Add Admin Bypass

```bash
# Edit .env
RATE_LIMIT_ADMIN_BYPASS=true  # Admin users unlimited

# Or disable rate limiting entirely (NOT recommended for production)
RATE_LIMIT_ENABLED=false

docker compose restart api
```

---

## Performance Issues

### Problem: API Requests Slow (>1 second)

**Diagnosis:**

```bash
# Check detailed health latency
curl http://localhost:8000/health/detailed | jq '.dependencies'

# Check metrics
curl http://localhost:8000/metrics | grep http_request_duration_seconds

# Look for high p95/p99 latencies
```

**Common Causes & Solutions:**

#### 1. Policy Cache Miss Rate High

```bash
# Check cache hit rate
curl http://localhost:8000/metrics | grep policy_cache

# If hit rate <70%, increase cache TTL
POLICY_CACHE_TTL_HIGH=300  # Increase to 5 min
POLICY_CACHE_TTL_MEDIUM=600  # Increase to 10 min

docker compose restart api
```

#### 2. Database Slow Queries

See [Database Issues - Slow Queries](#problem-slow-database-queries)

#### 3. OPA Evaluation Slow

```bash
# Check OPA latency
curl http://localhost:8000/health/detailed | jq '.dependencies.opa.latency_ms'

# If >100ms:
# - Simplify OPA policies (avoid nested loops)
# - Add more caching
# - Scale OPA horizontally (multiple replicas)
```

#### 4. SIEM Forwarding Blocking

```bash
# Ensure SIEM forwarding is async (non-blocking)
# Check queue size isn't backing up
curl http://localhost:8000/metrics | grep siem_queue
```

---

## Docker & Kubernetes Issues

### Problem: Docker Compose Services Won't Start

**Diagnosis:**

```bash
# Check all service status
docker compose ps

# Check logs for failing service
docker compose logs <service-name>

# Check Docker resources
docker stats --no-stream
```

**Common Causes:**

#### 1. Port Conflicts

```bash
# Check what's using ports
netstat -tuln | grep -E ':(8000|5432|6379|8500|8181)'

# Kill conflicting processes or change ports in docker-compose.yml
```

#### 2. Insufficient Memory

```bash
# Check Docker memory limit
docker info | grep Memory

# Increase Docker memory (Docker Desktop: Settings → Resources → Memory)
# Minimum: 8GB recommended for all services
```

#### 3. Volume Permission Issues

```bash
# Fix volume permissions
docker compose down -v
docker volume prune
docker compose up -d
```

---

### Problem: Kubernetes Pods Crash Looping

**Diagnosis:**

```bash
# Check pod status
kubectl get pods -n production

# Check pod events
kubectl describe pod <pod-name> -n production

# Check logs
kubectl logs <pod-name> -n production --previous
```

**Solutions:**

#### 1. Health Check Failures

```bash
# Increase health check timeouts
# Edit deployment.yaml
livenessProbe:
  initialDelaySeconds: 60  # Increase from 30
  timeoutSeconds: 10  # Increase from 5
```

#### 2. Resource Limits Too Low

```bash
# Increase resource limits
resources:
  limits:
    memory: 2Gi  # Increase from 1Gi
    cpu: 2000m  # Increase from 1000m
```

#### 3. ImagePullBackOff

```bash
# Check image exists
docker pull your-registry.com/sark:0.1.0

# Fix image pull secrets
kubectl create secret docker-registry registry-credentials \
  --docker-server=your-registry.com \
  --docker-username=user \
  --docker-password=pass

# Reference in deployment
imagePullSecrets:
- name: registry-credentials
```

---

## API Errors Reference

### HTTP 400 - Bad Request

**Cause:** Invalid request parameters
**Solution:** Check request body against API documentation

```bash
# Example: Missing required field
curl -X POST http://localhost:8000/api/v1/servers \
  -H "Content-Type: application/json" \
  -d '{"name": "test"}'  # Missing required fields

# Error response shows validation errors
```

---

### HTTP 401 - Unauthorized

**Cause:** Authentication failed or token invalid/expired

**Solutions:**
1. Re-authenticate to get new access token
2. Use refresh token to renew access token
3. Check token hasn't been revoked

---

### HTTP 403 - Forbidden

**Cause:** Authorization denied by policy

**Solution:** Check policy decision reason

```bash
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{...}' | jq '.reason'
```

---

### HTTP 404 - Not Found

**Cause:** Resource doesn't exist

**Solution:** Verify resource ID exists

```bash
# List resources
curl http://localhost:8000/api/v1/servers

# Check specific resource
curl http://localhost:8000/api/v1/servers/{server_id}
```

---

### HTTP 422 - Unprocessable Entity

**Cause:** Validation error (e.g., invalid enum value, format error)

**Solution:** Check error details and fix request

---

### HTTP 429 - Too Many Requests

**Cause:** Rate limit exceeded

**Solution:** Wait for rate limit reset or increase limits

See [Rate Limiting Issues](#rate-limiting-issues)

---

### HTTP 500 - Internal Server Error

**Cause:** Server-side error (database down, unhandled exception)

**Solution:** Check server logs

```bash
docker compose logs api --tail=50

# Look for stack traces and error messages
```

---

### HTTP 503 - Service Unavailable

**Cause:** Dependency unavailable (DB, Redis, OPA)

**Solution:** Check dependency health

```bash
curl http://localhost:8000/health/detailed
```

---

## Monitoring & Logs

### Application Logs

```bash
# Docker Compose
docker compose logs api -f --tail=100

# Kubernetes
kubectl logs -f deployment/sark -n production --tail=100

# Filter for errors
docker compose logs api | grep -i error
docker compose logs api | grep -i exception
```

### Audit Logs (TimescaleDB)

```bash
# Connect to audit database
docker compose exec timescaledb psql -U sark sark_audit

# Recent events
sark_audit=# SELECT event_type, severity, user_email, timestamp
             FROM audit_events
             ORDER BY timestamp DESC
             LIMIT 20;

# Failed authentications
sark_audit=# SELECT user_email, COUNT(*) as failures
             FROM audit_events
             WHERE event_type = 'authentication_failure'
               AND timestamp > NOW() - INTERVAL '1 hour'
             GROUP BY user_email
             ORDER BY failures DESC;

# Policy denials
sark_audit=# SELECT tool_name, reason, COUNT(*) as denials
             FROM audit_events
             WHERE event_type = 'policy_decision'
               AND decision = 'deny'
               AND timestamp > NOW() - INTERVAL '1 day'
             GROUP BY tool_name, reason
             ORDER BY denials DESC;
```

### Prometheus Metrics

```bash
# Access Prometheus
open http://localhost:9090

# Key queries:
# Request rate: rate(http_requests_total[5m])
# Error rate: rate(http_requests_total{status=~"5.."}[5m])
# P95 latency: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
# Policy cache hit rate: rate(policy_cache_hits_total[5m]) / rate(policy_cache_total[5m])
```

### Grafana Dashboards

```bash
# Access Grafana
open http://localhost:3000
# Login: admin / admin

# Pre-configured dashboards:
# - SARK Overview: API metrics, requests/sec, latencies
# - Policy Evaluation: Cache hit rate, OPA latency, decision breakdown
# - SIEM Integration: Events forwarded, success rate, retry stats
```

---

## Getting Help

### Self-Service Resources

1. **Documentation:** [docs/](../) directory
   - [API Reference](API_REFERENCE.md)
   - [Deployment Guide](DEPLOYMENT.md)
   - [Operational Runbook](OPERATIONAL_RUNBOOK.md)
   - [Performance Tuning](PERFORMANCE_TUNING.md)

2. **Health Endpoints:**
   - `/health` - Basic health check
   - `/health/detailed` - Dependency health with latency
   - `/metrics` - Prometheus metrics

3. **Logs:**
   - Application logs: `docker compose logs api`
   - Audit logs: TimescaleDB `audit_events` table
   - SIEM dashboards: Splunk/Datadog

---

### Escalation Path

#### Level 1: Documentation & Logs
- Check this troubleshooting guide
- Review application logs
- Check health endpoints

#### Level 2: Community/Team Support
- Search GitHub issues
- Post in team Slack channel
- Check internal wiki/knowledge base

#### Level 3: Engineering Support
- Create detailed bug report with:
  - Symptoms and error messages
  - Steps to reproduce
  - Relevant logs and metrics
  - Environment details (dev/staging/prod)
  - Attempted solutions

---

### Bug Report Template

```markdown
## Issue Description
[Clear description of the problem]

## Environment
- SARK Version: [e.g., 0.1.0]
- Environment: [dev/staging/production]
- Deployment: [Docker Compose / Kubernetes]
- Cloud Provider: [AWS/GCP/Azure/On-prem]

## Steps to Reproduce
1. [Step 1]
2. [Step 2]
3. [Observe error]

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Error Messages
```
[Paste error messages and stack traces]
```

## Logs
```
[Paste relevant logs]
```

## Metrics/Screenshots
[Attach screenshots of Grafana dashboards, error responses, etc.]

## Attempted Solutions
- [x] Checked health endpoints
- [x] Reviewed logs
- [x] Restarted services
- [ ] [Other solutions tried]

## Additional Context
[Any other relevant information]
```

---

**For urgent production issues, follow your organization's incident response procedures.**

See [OPERATIONAL_RUNBOOK.md](OPERATIONAL_RUNBOOK.md) for emergency procedures and on-call escalation.
