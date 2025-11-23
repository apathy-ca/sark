# Known Issues and Limitations

**Document Version**: 1.0
**Last Updated**: November 22, 2025
**Status**: Phase 2 Complete

---

## Table of Contents

1. [Overview](#overview)
2. [Known Issues](#known-issues)
3. [Limitations](#limitations)
4. [Workarounds](#workarounds)
5. [Future Work Recommendations](#future-work-recommendations)
6. [Technical Debt](#technical-debt)

---

## Overview

This document tracks known issues, limitations, and areas for future improvement in SARK. It serves as a reference for operations teams and guides future development priorities.

### Issue Severity Levels

| Severity | Description | Impact | Timeline |
|----------|-------------|--------|----------|
| **Critical** | System-breaking, data loss risk | Production blocker | Immediate |
| **High** | Major functionality impaired | Significant user impact | Next sprint |
| **Medium** | Feature limitation, workaround exists | Moderate user impact | Next quarter |
| **Low** | Minor issue, cosmetic, documentation | Minimal impact | Backlog |

---

## Known Issues

### High Priority

#### 1. Redis Connection Pool Exhaustion Under Extreme Load

**Severity**: High
**Status**: Open
**Affected Component**: Redis connection pooling

**Description**:
Under extreme load (> 2,000 req/s), Redis connection pool may exhaust, causing connection timeout errors.

**Impact**:
- API requests fail with 500 errors
- Error rate can spike to 5-10% under sustained high load
- Auto-recovery after load decreases

**Root Cause**:
- Current pool size: 20 connections per pod (80 total for 4 pods)
- High concurrency workloads can temporarily exhaust pool
- Connection acquisition timeout: 5 seconds

**Workaround**:
```python
# Increase pool size in application configuration
REDIS_POOL_SIZE=30  # From 20 to 30
REDIS_SOCKET_TIMEOUT=10  # From 5 to 10 seconds
```

**Permanent Fix** (Recommended for Phase 3):
- Implement connection pool monitoring and auto-scaling
- Add circuit breaker for Redis operations
- Implement request queueing during pool exhaustion

**Tracking**: Issue #TBD

---

#### 2. TimescaleDB Compression Job Failures on Large Chunks

**Severity**: High
**Status**: Open
**Affected Component**: TimescaleDB audit database

**Description**:
Compression jobs occasionally fail on chunks larger than 10 GB, causing audit log storage to grow faster than expected.

**Impact**:
- Audit database grows ~5× faster without compression
- Disk space can be exhausted in 30 days vs 90+ days with compression
- Manual intervention required to compress failed chunks

**Root Cause**:
- TimescaleDB compression timeout (default: 30 minutes)
- Large chunks (> 10 GB) exceed timeout
- High write volume during peak hours creates large chunks

**Workaround**:
```sql
-- Manually compress failed chunks during low-traffic hours
SELECT compress_chunk('_timescaledb_internal._hyper_1_123_chunk');

-- Monitor compression status
SELECT * FROM timescaledb_information.job_stats
WHERE job_id = (SELECT job_id FROM timescaledb_information.jobs WHERE proc_name = 'policy_compression');
```

**Permanent Fix** (Recommended for Phase 3):
- Reduce chunk interval from 1 day to 12 hours for high-volume hypertables
- Increase compression job timeout to 2 hours
- Implement progressive compression (compress smaller chunks first)

**Tracking**: Issue #TBD

---

### Medium Priority

#### 3. SIEM Event Queue Backup During Network Outages

**Severity**: Medium
**Status**: Open
**Affected Component**: SIEM integration (Splunk, Datadog)

**Description**:
During network outages or SIEM downtime, event queue can grow to 50,000+ events, causing memory pressure on Redis.

**Impact**:
- Redis memory usage can spike from 40 MB to 200 MB
- If queue exceeds 100,000 events, oldest events are dropped
- Events lost during extended outages (> 2 hours)

**Root Cause**:
- Circuit breaker opens after 10 consecutive failures
- Events continue to queue while circuit breaker is open
- No persistent backup for queued events

**Workaround**:
```bash
# Monitor queue size
kubectl exec -it redis-0 -n production -- redis-cli LLEN siem:event_queue

# If queue > 50,000, manually forward events
kubectl exec -it deployment/sark -n production -- \
  python -m sark.siem.worker --flush-queue --batch-size=1000
```

**Permanent Fix** (Recommended for Phase 3):
- Implement persistent queue (Kafka, RabbitMQ, or database-backed)
- Add queue size alerting (warn at 10,000, critical at 50,000)
- Implement automatic queue draining during low-traffic hours

**Tracking**: Issue #TBD

---

#### 4. Policy Cache Invalidation Delay

**Severity**: Medium
**Status**: Open
**Affected Component**: OPA policy caching

**Description**:
Policy changes (uploads, updates) are not immediately reflected in cached decisions. Cache TTL-based expiration causes up to 1-hour delay.

**Impact**:
- Policy changes may not take effect for up to 1 hour
- Security updates delayed
- User permissions updates delayed

**Root Cause**:
- Cache TTL: 5 minutes (high sensitivity) to 1 hour (low sensitivity)
- No proactive cache invalidation on policy update
- Policy version tracking not implemented

**Workaround**:
```bash
# Manually invalidate policy cache after policy update
kubectl exec -it redis-0 -n production -- redis-cli \
  EVAL "return redis.call('del', unpack(redis.call('keys', 'policy:decision:*')))" 0

# Force policy version increment
kubectl exec -it redis-0 -n production -- redis-cli \
  INCR policy:version:policy_name
```

**Permanent Fix** (Recommended for Phase 3):
- Implement policy versioning and version-based cache keys
- Add webhook or event-based cache invalidation on policy updates
- Implement selective cache invalidation (only affected decisions)

**Tracking**: Issue #TBD

---

### Low Priority

#### 5. Rate Limit Counter Drift Across Pods

**Severity**: Low
**Status**: Open
**Affected Component**: Rate limiting

**Description**:
Rate limit counters are pod-local for the first request, then centralized in Redis. This can cause slight drift in rate limit enforcement.

**Impact**:
- Users may occasionally exceed rate limits by 1-2%
- Not a security issue, just imprecise enforcement
- More noticeable with low rate limits (< 100 req/min)

**Root Cause**:
- Race condition between pods checking and incrementing Redis counter
- No distributed locking for rate limit checks (performance trade-off)

**Workaround**:
None needed. Impact is minimal (1-2% drift).

**Permanent Fix** (Recommended for Phase 3):
- Implement Lua script for atomic rate limit check + increment (already designed, not deployed)
- Add distributed locking for high-precision rate limiting (optional)

**Tracking**: Issue #TBD

---

## Limitations

### Architectural Limitations

#### 1. Single-Region Active Deployment

**Limitation**: SARK currently supports only single-region active deployment with warm DR site.

**Impact**:
- Cannot serve traffic from multiple regions simultaneously
- Increased latency for users far from primary region
- Manual failover required for DR (30-45 minutes)

**Reason**:
- Session state in Redis not replicated across regions
- Database streaming replication is primary → replica only (not multi-master)
- DNS-based failover is manual

**Future Enhancement** (Phase 3/4):
- Implement multi-region active-active deployment
- Use global Redis cluster (Redis Enterprise) or distributed cache (Hazelcast)
- Implement multi-master database replication (PostgreSQL BDR or Citus)
- Use global load balancer (AWS Global Accelerator, Cloudflare)

---

#### 2. Maximum Throughput Per Instance

**Limitation**: Single SARK instance (API deployment) is limited to ~5,000 req/s.

**Impact**:
- Cannot handle traffic spikes > 5,000 req/s without horizontal scaling
- Requires HPA configuration for automatic scaling

**Reason**:
- Database connection pool limits (200 max connections)
- Redis connection pool limits (10,000 max clients)
- Network bandwidth limits (1 Gbps per pod)

**Current Solution**:
- Horizontal Pod Autoscaler (HPA) configured (4-20 pods)
- Supports up to 100,000 req/s (20 pods × 5,000 req/s)

**Future Enhancement** (Phase 4):
- Implement request routing and load balancing at edge (Envoy, Istio)
- Optimize per-pod throughput to 10,000 req/s (2× improvement)

---

#### 3. Session Portability Across Environments

**Limitation**: Sessions are not portable across environments (staging ↔ production).

**Impact**:
- Users must re-authenticate when switching environments
- Testing production issues requires separate login

**Reason**:
- JWT secret keys are environment-specific (security best practice)
- Session data stored in environment-specific Redis instances

**Workaround**:
Use separate user accounts for each environment (recommended).

**Future Enhancement** (Phase 4):
- Implement federated authentication (OAuth 2.0 token exchange)
- Allow cross-environment session token exchange (with security controls)

---

### Feature Limitations

#### 4. MFA Limited to TOTP

**Limitation**: MFA only supports TOTP (Time-based One-Time Password), no support for U2F, WebAuthn, or SMS.

**Impact**:
- Users must use authenticator apps (Google Authenticator, Authy)
- Cannot use hardware security keys (YubiKey, Titan)
- Cannot use SMS-based MFA

**Reason**:
- Phase 2 scope limited to TOTP implementation
- U2F/WebAuthn requires additional frontend integration

**Future Enhancement** (Phase 3):
- Implement WebAuthn support (hardware security keys)
- Implement backup codes (recovery codes)
- Consider SMS MFA (with security warnings)

---

#### 5. Policy Language Limited to Rego

**Limitation**: Authorization policies must be written in Rego (OPA policy language).

**Impact**:
- Learning curve for policy authors
- No visual policy editor
- Complex policies can be difficult to debug

**Reason**:
- OPA is the chosen policy engine (industry standard)
- Alternative: custom policy language would require significant development

**Future Enhancement** (Phase 3):
- Implement visual policy editor (drag-and-drop, flowchart)
- Add policy templates and wizards
- Improve policy debugging tools (Rego playground, trace visualization)

---

## Workarounds

### 1. Redis Connection Pool Exhaustion

**Temporary Solution**:
```bash
# Increase pool size
kubectl set env deployment/sark REDIS_POOL_SIZE=30 -n production

# Or restart pods to clear stale connections
kubectl rollout restart deployment/sark -n production
```

### 2. TimescaleDB Compression Failures

**Temporary Solution**:
```bash
# Manually compress failed chunks
kubectl exec -it timescaledb-0 -n production -- psql -U sark -d sark_audit -c "
  SELECT compress_chunk(chunk)
  FROM timescaledb_information.chunks
  WHERE NOT is_compressed
  ORDER BY range_start
  LIMIT 10;
"
```

### 3. SIEM Event Queue Backup

**Temporary Solution**:
```bash
# Drain queue manually
kubectl exec -it deployment/sark -n production -- \
  python -m sark.siem.worker --flush-queue
```

### 4. Policy Cache Invalidation

**Temporary Solution**:
```bash
# Clear all policy cache after policy update
kubectl exec -it redis-0 -n production -- redis-cli FLUSHDB
```

---

## Future Work Recommendations

### High Priority (Phase 3)

1. **Multi-Region Active-Active Deployment**
   - Estimated Effort: 6-8 weeks
   - Benefits: Improved latency, automatic failover, 99.99% SLA
   - Technologies: Redis Enterprise, PostgreSQL BDR, Global Load Balancer

2. **WebAuthn/U2F Support for MFA**
   - Estimated Effort: 3-4 weeks
   - Benefits: Improved security, hardware key support, better UX
   - Technologies: WebAuthn API, FIDO2 libraries

3. **Visual Policy Editor**
   - Estimated Effort: 8-10 weeks
   - Benefits: Easier policy authoring, reduced errors, faster onboarding
   - Technologies: React Flow, Monaco Editor, OPA Playground integration

4. **Persistent SIEM Event Queue**
   - Estimated Effort: 2-3 weeks
   - Benefits: No event loss, better queue management, scalable
   - Technologies: Kafka, RabbitMQ, or PostgreSQL-backed queue

5. **Policy Versioning and Rollback**
   - Estimated Effort: 4-5 weeks
   - Benefits: Safe policy updates, instant rollback, audit trail
   - Technologies: Git-based policy storage, policy versioning API

### Medium Priority (Phase 4)

6. **Advanced RBAC and ABAC**
   - Estimated Effort: 6-8 weeks
   - Benefits: Fine-grained permissions, context-aware access control
   - Technologies: OPA with extended policy language, attribute stores

7. **Multi-Tenancy Support**
   - Estimated Effort: 10-12 weeks
   - Benefits: SaaS offering, tenant isolation, resource quotas
   - Technologies: Tenant ID in all tables, row-level security, separate Redis DBs

8. **API Rate Limiting Enhancements**
   - Estimated Effort: 2-3 weeks
   - Benefits: More precise rate limiting, custom limits per user/API key
   - Technologies: Token bucket algorithm, Lua scripts for atomic operations

9. **Audit Log Analytics and Reporting**
   - Estimated Effort: 4-5 weeks
   - Benefits: Compliance reporting, anomaly detection, insights
   - Technologies: TimescaleDB continuous aggregates, Grafana dashboards, ML anomaly detection

10. **GraphQL API**
    - Estimated Effort: 6-8 weeks
    - Benefits: Flexible queries, reduced over-fetching, better client experience
    - Technologies: Strawberry (Python GraphQL), Apollo Client

### Low Priority (Backlog)

11. **Webhooks for Event Notifications**
    - Estimated Effort: 3-4 weeks
    - Benefits: Real-time notifications, integrations with external systems

12. **Bulk Operations API**
    - Estimated Effort: 2-3 weeks
    - Benefits: Faster bulk server registration, bulk policy updates

13. **Advanced Search and Filtering**
    - Estimated Effort: 4-5 weeks
    - Benefits: Better UX for large server inventories, complex queries
    - Technologies: Elasticsearch integration

14. **Mobile App (iOS/Android)**
    - Estimated Effort: 12-16 weeks
    - Benefits: Mobile access, push notifications, offline support

---

## Technical Debt

### Code Quality

1. **Test Coverage Gaps**
   - **Current**: ~70% code coverage (unit + integration tests)
   - **Target**: 90%+ coverage
   - **Effort**: 2-3 weeks
   - **Priority**: High

2. **API Documentation Auto-Generation**
   - **Current**: Manual API documentation
   - **Target**: Auto-generated from OpenAPI spec
   - **Effort**: 1-2 weeks
   - **Priority**: Medium

3. **Type Hints and Static Analysis**
   - **Current**: ~60% of code has type hints
   - **Target**: 100% type hints, mypy strict mode
   - **Effort**: 2-3 weeks
   - **Priority**: Medium

### Infrastructure

4. **CI/CD Pipeline Enhancements**
   - **Current**: Basic CI/CD (build, test, deploy)
   - **Target**: Automated security scanning, performance tests in CI/CD
   - **Effort**: 2-3 weeks
   - **Priority**: High

5. **Infrastructure as Code (IaC)**
   - **Current**: Manual Kubernetes deployment
   - **Target**: Terraform/Pulumi for all infrastructure
   - **Effort**: 3-4 weeks
   - **Priority**: Medium

### Operational

6. **Automated DR Testing**
   - **Current**: Manual quarterly DR tests
   - **Target**: Automated monthly DR tests with chaos engineering
   - **Effort**: 3-4 weeks
   - **Priority**: High

7. **Cost Optimization**
   - **Current**: No cost monitoring or optimization
   - **Target**: Cost tracking, right-sizing recommendations, spot instances
   - **Effort**: 2-3 weeks
   - **Priority**: Low

---

## Summary

### Issue Statistics

| Severity | Open Issues | Workarounds Available |
|----------|-------------|-----------------------|
| **High** | 2 | Yes (both) |
| **Medium** | 2 | Yes (both) |
| **Low** | 1 | N/A |
| **Total** | 5 | 4 |

### Limitation Statistics

| Category | Count | Planned Enhancements |
|----------|-------|----------------------|
| **Architectural** | 3 | Phase 3/4 |
| **Feature** | 2 | Phase 3 |
| **Total** | 5 | 5 |

### Technical Debt

| Category | Items | Priority |
|----------|-------|----------|
| **Code Quality** | 3 | High/Medium |
| **Infrastructure** | 2 | High/Medium |
| **Operational** | 2 | High/Low |
| **Total** | 7 | Mixed |

---

## Appendix

### Issue Reporting

**For Production Issues**:
1. Check this document for known issues and workarounds
2. Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common issues
3. If new issue, create incident ticket with:
   - Severity level
   - Detailed description
   - Steps to reproduce
   - Impact assessment
   - Proposed workaround (if any)

**For Feature Requests**:
1. Check this document for planned future work
2. If not listed, submit feature request with:
   - Use case description
   - Expected behavior
   - Benefits and impact
   - Estimated effort (if known)

---

**Document Maintained By**: Engineering Team
**Last Reviewed**: November 22, 2025
**Next Review**: December 22, 2025 (monthly)
