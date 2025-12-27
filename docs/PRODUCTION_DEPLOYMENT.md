# Production Deployment Guide

**Document Version**: 1.0
**Last Updated**: November 22, 2025
**Audience**: DevOps Engineers, SRE Teams, Release Managers

---

## Table of Contents

1. [Overview](#overview)
2. [Infrastructure Requirements](#infrastructure-requirements)
3. [Pre-Deployment Checklist](#pre-deployment-checklist)
4. [Production Deployment Steps](#production-deployment-steps)
5. [Post-Deployment Validation](#post-deployment-validation)
6. [Rollback Procedures](#rollback-procedures)
7. [Zero-Downtime Deployment](#zero-downtime-deployment)
8. [Blue-Green Deployment](#blue-green-deployment)
9. [Canary Deployment](#canary-deployment)
10. [Troubleshooting](#troubleshooting)

---

## Overview

This guide covers production-specific deployment procedures for SARK. For general Kubernetes deployment instructions, see [DEPLOYMENT.md](./DEPLOYMENT.md).

### Deployment Philosophy

- **Zero-downtime deployments**: All production deployments must maintain service availability
- **Rollback readiness**: Every deployment must be immediately rollback-able
- **Progressive rollout**: Use canary or blue-green deployments for risk mitigation
- **Validation at every step**: Verify success before proceeding
- **Automated where possible**: Minimize human error

---

## Infrastructure Requirements

### Minimum Production Infrastructure

#### Kubernetes Cluster

| Component | Requirement | Recommended |
|-----------|-------------|-------------|
| **Kubernetes Version** | 1.24+ | 1.27+ |
| **Node Count** | 3+ | 5+ (HA) |
| **Node Type** | 4 vCPU, 16 GB RAM | 8 vCPU, 32 GB RAM |
| **Storage Class** | SSD-backed | NVMe SSD |
| **Load Balancer** | Cloud LB or MetalLB | Cloud LB with DDoS protection |
| **Ingress Controller** | NGINX Ingress | NGINX + cert-manager |
| **Monitoring** | Prometheus + Grafana | Full observability stack |

#### Database Infrastructure

**PostgreSQL (Primary Database)**:
- **Version**: PostgreSQL 14+
- **Instance Type**:
  - Minimum: 2 vCPU, 8 GB RAM, 100 GB SSD
  - Recommended: 4 vCPU, 16 GB RAM, 500 GB NVMe SSD
- **High Availability**: Primary + 2 read replicas (streaming replication)
- **Backup**: Automated daily backups with 30-day retention
- **Connection Pool**: PgBouncer for > 10 application pods

**TimescaleDB (Audit Database)**:
- **Version**: TimescaleDB 2.10+ (PostgreSQL 14+)
- **Instance Type**:
  - Minimum: 2 vCPU, 8 GB RAM, 200 GB SSD
  - Recommended: 4 vCPU, 16 GB RAM, 1 TB NVMe SSD
- **Retention**: 90-day automatic data retention
- **Compression**: Enable compression for data > 7 days old (90%+ space savings)

#### Redis Infrastructure

- **Version**: Redis 7+
- **Instance Type**:
  - Minimum: 1 vCPU, 2 GB RAM
  - Recommended: 2 vCPU, 4 GB RAM
- **High Availability**: Redis Sentinel (1 master + 2 replicas + 3 sentinels)
- **Persistence**: Disabled for pure cache (recommended)
- **Memory**: 512 MB - 2 GB maxmemory

#### Network Requirements

**Ingress**:
- TLS 1.3 certificate (Let's Encrypt or commercial CA)
- DDoS protection (Cloud provider or Cloudflare)
- WAF (Web Application Firewall) recommended
- Rate limiting at load balancer level

**Egress** (Outbound connections):
- LDAP/AD servers: Port 389 (LDAP), 636 (LDAPS)
- OIDC providers: Port 443 (HTTPS)
- SAML IdP: Port 443 (HTTPS)
- SIEM (Splunk): Port 8088 (HEC)
- SIEM (Datadog): Port 443 (HTTPS)

**Internal** (Pod-to-pod):
- PostgreSQL: Port 5432
- TimescaleDB: Port 5432
- Redis: Port 6379
- OPA: Port 8181
- Prometheus: Port 9090

### Cloud Provider Recommendations

#### AWS

**Managed Services**:
- **Kubernetes**: Amazon EKS (Elastic Kubernetes Service)
- **Database**: Amazon RDS for PostgreSQL (Multi-AZ)
- **Cache**: Amazon ElastiCache for Redis (Cluster mode)
- **Load Balancer**: Application Load Balancer (ALB)
- **Secrets**: AWS Secrets Manager
- **Monitoring**: Amazon CloudWatch + Prometheus

**Estimated Monthly Cost** (Medium deployment):
- EKS cluster: $73/month + worker nodes
- RDS PostgreSQL (db.r6g.xlarge, Multi-AZ): $500/month
- ElastiCache Redis (cache.r6g.large): $200/month
- ALB: $25/month + data transfer
- **Total**: ~$800-1,200/month (excluding data transfer and storage)

#### Google Cloud (GCP)

**Managed Services**:
- **Kubernetes**: Google Kubernetes Engine (GKE)
- **Database**: Cloud SQL for PostgreSQL (HA)
- **Cache**: Memorystore for Redis (HA)
- **Load Balancer**: Cloud Load Balancing
- **Secrets**: Secret Manager
- **Monitoring**: Cloud Monitoring + Prometheus

**Estimated Monthly Cost** (Medium deployment):
- GKE cluster: $75/month + worker nodes
- Cloud SQL PostgreSQL (db-custom-4-16384, HA): $450/month
- Memorystore Redis (Standard, 4 GB): $150/month
- Cloud Load Balancing: $20/month + data transfer
- **Total**: ~$700-1,000/month

#### Azure

**Managed Services**:
- **Kubernetes**: Azure Kubernetes Service (AKS)
- **Database**: Azure Database for PostgreSQL (HA)
- **Cache**: Azure Cache for Redis (Premium)
- **Load Balancer**: Azure Application Gateway
- **Secrets**: Azure Key Vault
- **Monitoring**: Azure Monitor + Prometheus

**Estimated Monthly Cost** (Medium deployment):
- AKS cluster: $75/month + worker nodes
- Azure Database for PostgreSQL (General Purpose, 4 vCPU): $400/month
- Azure Cache for Redis (Premium P1): $250/month
- Application Gateway: $150/month
- **Total**: ~$875-1,200/month

#### On-Premises

**Hardware Requirements**:
- **Kubernetes Cluster**: 5 bare-metal servers (8 vCPU, 32 GB RAM each)
- **PostgreSQL**: Dedicated server (16 vCPU, 64 GB RAM, RAID 10 SSD)
- **Redis**: Dedicated server (4 vCPU, 16 GB RAM, SSD)
- **Load Balancer**: HAProxy or NGINX on 2 servers (HA)
- **Storage**: SAN or NAS for persistent volumes (10 TB recommended)

**Networking**:
- 10 Gbps internal network
- Redundant switches and routers
- Firewall appliance (Palo Alto, Fortinet, or pfSense)

---

## Pre-Deployment Checklist

### Infrastructure Checklist

- [ ] **Kubernetes cluster provisioned** (3+ nodes, 1.24+)
- [ ] **PostgreSQL database deployed** (14+, HA configuration)
- [ ] **TimescaleDB deployed** (for audit logs)
- [ ] **Redis deployed** (7+, Sentinel for HA)
- [ ] **Ingress controller installed** (NGINX recommended)
- [ ] **cert-manager installed** (for TLS certificates)
- [ ] **Prometheus + Grafana deployed** (monitoring stack)
- [ ] **Namespaces created** (`production`, `monitoring`)
- [ ] **Network policies configured** (restrict pod-to-pod traffic)
- [ ] **Storage classes configured** (SSD-backed for databases)

### Security Checklist

See [SECURITY_HARDENING.md](./SECURITY_HARDENING.md) for complete checklist.

**Critical Items**:
- [ ] All secrets rotated and stored in Vault/Secrets Manager
- [ ] TLS 1.3 enforced on all endpoints
- [ ] Valid TLS certificate installed (Let's Encrypt or commercial)
- [ ] Security headers configured (HSTS, CSP, X-Frame-Options)
- [ ] Firewall rules configured (only necessary ports exposed)
- [ ] Rate limiting enabled for all endpoints
- [ ] Pod Security Standards enforced (restricted)
- [ ] RBAC configured (least privilege)
- [ ] Network Policies configured
- [ ] Container images scanned (no critical vulnerabilities)
- [ ] Secrets encrypted at rest (Kubernetes encryption config)

### Application Configuration Checklist

- [ ] **Environment variables configured**
  - [ ] `ENVIRONMENT=production`
  - [ ] `DEBUG=false`
  - [ ] `LOG_LEVEL=INFO` (or WARN)
  - [ ] `JWT_SECRET_KEY` rotated (32+ characters)
- [ ] **Database connection configured**
  - [ ] Connection pooling enabled (20-30 per pod)
  - [ ] SSL/TLS enabled for database connections
  - [ ] Query timeout configured (30 seconds)
- [ ] **Redis connection configured**
  - [ ] Password authentication enabled
  - [ ] Connection pooling configured (20 per pod)
  - [ ] Maxmemory and eviction policy set
- [ ] **OPA policies deployed** and tested
- [ ] **Authentication providers configured**
  - [ ] LDAP/AD connectivity tested
  - [ ] OIDC provider registered and tested
  - [ ] SAML IdP metadata uploaded
- [ ] **SIEM integration configured**
  - [ ] Splunk HEC token configured
  - [ ] Datadog API key configured
  - [ ] Event forwarding tested
- [ ] **Rate limiting configured**
  - [ ] Per-user limits: 5,000 req/min
  - [ ] Per-API-key limits: 1,000 req/min
  - [ ] Per-IP limits: 100 req/min

### Performance & Optimization Checklist

See [DATABASE_OPTIMIZATION.md](./DATABASE_OPTIMIZATION.md) and [VALKEY_OPTIMIZATION.md](./VALKEY_OPTIMIZATION.md).

**Database**:
- [ ] Indexes created on critical columns
- [ ] `pg_stat_statements` extension enabled
- [ ] `shared_buffers` configured (25% of RAM)
- [ ] Autovacuum enabled and tuned
- [ ] Statement timeout set (30 seconds)

**Redis**:
- [ ] Maxmemory limit set (512 MB - 2 GB)
- [ ] Eviction policy set (`allkeys-lru`)
- [ ] Persistence disabled for cache (performance)
- [ ] I/O threading enabled (`io-threads 4`)

**Application**:
- [ ] Resource limits configured (CPU, memory)
- [ ] Horizontal Pod Autoscaler (HPA) configured
- [ ] Pod Disruption Budget (PDB) configured
- [ ] Health checks configured (liveness, readiness)

### Testing Checklist

- [ ] **Unit tests passed** (100% critical path coverage)
- [ ] **Integration tests passed** (all endpoints tested)
- [ ] **Load tests passed** (see [PERFORMANCE_TESTING.md](./PERFORMANCE_TESTING.md))
  - [ ] p95 latency < 100ms
  - [ ] p99 latency < 200ms
  - [ ] Error rate < 0.1%
  - [ ] Throughput > target req/s
- [ ] **Security scans passed**
  - [ ] OWASP ZAP scan (no high/critical issues)
  - [ ] Container image scan (no critical vulnerabilities)
  - [ ] Dependency scan (no critical vulnerabilities)
- [ ] **Disaster recovery tested** (backup restore verified)
- [ ] **Failover tested** (database, Redis, Kubernetes nodes)

### Documentation Checklist

- [ ] **Architecture diagrams updated**
- [ ] **API documentation updated** (OpenAPI/Swagger)
- [ ] **Deployment guide reviewed** (this document)
- [ ] **Operations runbook reviewed** ([OPERATIONS_RUNBOOK.md](./OPERATIONS_RUNBOOK.md))
- [ ] **Incident response playbooks reviewed** ([INCIDENT_RESPONSE.md](./INCIDENT_RESPONSE.md))
- [ ] **Disaster recovery procedures reviewed** ([DISASTER_RECOVERY.md](./DISASTER_RECOVERY.md))
- [ ] **On-call schedule configured** (PagerDuty or similar)
- [ ] **Stakeholders notified** (deployment date/time communicated)

---

## Production Deployment Steps

### Phase 1: Pre-Deployment (T-24 hours)

**1. Code Freeze**
```bash
# Tag release in git
git tag -a v1.0.0 -m "Production release 1.0.0"
git push origin v1.0.0

# Lock main branch (require approval for merges)
# Configure in GitHub/GitLab settings
```

**2. Build Production Image**
```bash
# Build multi-arch image
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --target production \
  -t your-registry.com/sark:1.0.0 \
  -t your-registry.com/sark:latest \
  --push .

# Scan image for vulnerabilities
trivy image your-registry.com/sark:1.0.0 --severity HIGH,CRITICAL

# Sign image (optional, for supply chain security)
cosign sign --key cosign.key your-registry.com/sark:1.0.0
```

**3. Deploy to Staging**
```bash
# Deploy to staging namespace
helm upgrade --install sark ./helm/sark \
  -f helm/sark/values-staging.yaml \
  --set image.tag=1.0.0 \
  --namespace staging \
  --wait

# Verify staging deployment
kubectl get pods -n staging
kubectl logs deployment/sark -n staging --tail=50

# Run smoke tests
./scripts/smoke-test.sh https://staging.example.com
```

**4. Run Full Test Suite**
```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Load tests
locust -f tests/performance/locustfile.py \
  --host https://staging.example.com \
  --users 100 \
  --spawn-rate 10 \
  --run-time 10m \
  --headless

# Security scan
docker run -t zaproxy/zap-stable zap-baseline.py \
  -t https://staging.example.com \
  -r zap-report.html
```

**5. Final Pre-Deployment Meeting**
- Review deployment plan with team
- Confirm rollback procedures understood
- Assign roles (deployer, monitor, rollback executor)
- Confirm communication channels (Slack, PagerDuty)
- Get final approval from stakeholders

### Phase 2: Deployment Window (Production)

**Recommended Deployment Window**: Low-traffic hours (e.g., 2 AM - 4 AM local time)

**Step 1: Pre-Deployment Snapshot** (T-0:15)
```bash
# Backup database
kubectl exec -it postgres-0 -n production -- \
  pg_dump -U sark -Fc sark > /backups/sark-pre-deployment-$(date +%Y%m%d-%H%M).dump

# Snapshot persistent volumes (cloud provider)
# AWS
aws ec2 create-snapshot --volume-id vol-xxxxx --description "Pre-deployment snapshot"

# Export current configuration
helm get values sark -n production > helm-values-backup-$(date +%Y%m%d-%H%M).yaml
kubectl get deployment sark -n production -o yaml > deployment-backup-$(date +%Y%m%d-%H%M).yaml
```

**Step 2: Enable Maintenance Mode** (T-0:10)
```bash
# Option 1: Return 503 for all requests (full maintenance)
kubectl scale deployment sark --replicas=0 -n production
kubectl apply -f k8s/maintenance-page.yaml

# Option 2: Read-only mode (allow GET requests)
kubectl set env deployment/sark READ_ONLY_MODE=true -n production
```

**Step 3: Database Migrations** (T-0:05)
```bash
# Run migrations (if any)
kubectl run sark-migrate \
  --image=your-registry.com/sark:1.0.0 \
  --restart=Never \
  --namespace=production \
  --command -- alembic upgrade head

# Verify migrations
kubectl logs sark-migrate -n production

# Cleanup migration pod
kubectl delete pod sark-migrate -n production
```

**Step 4: Deploy Application** (T+0:00)
```bash
# Rolling update deployment
helm upgrade sark ./helm/sark \
  -f helm/sark/values-prod.yaml \
  --set image.tag=1.0.0 \
  --namespace production \
  --wait \
  --timeout 10m

# Watch deployment progress
kubectl rollout status deployment/sark -n production
kubectl get pods -n production -w
```

**Step 5: Verify Deployment** (T+0:05)
```bash
# Check pod status
kubectl get pods -n production -l app=sark

# Check pod logs for errors
kubectl logs deployment/sark -n production --tail=100

# Verify health endpoints
kubectl exec -it deployment/sark -n production -- \
  curl http://localhost:8000/health

# Run smoke tests
./scripts/smoke-test.sh https://api.example.com

# Test critical flows
# - Authentication (LDAP, OIDC, SAML)
# - Server registration
# - Policy evaluation
# - Rate limiting
# - SIEM event forwarding
```

**Step 6: Disable Maintenance Mode** (T+0:10)
```bash
# Remove maintenance page
kubectl delete -f k8s/maintenance-page.yaml

# Or disable read-only mode
kubectl set env deployment/sark READ_ONLY_MODE=false -n production

# Verify traffic is flowing
kubectl top pods -n production
```

**Step 7: Monitor Deployment** (T+0:15 to T+2:00)
```bash
# Monitor key metrics in Grafana
# - Request rate
# - Error rate
# - Latency (p95, p99)
# - CPU and memory utilization
# - Database connections
# - Redis memory usage

# Check Prometheus alerts
curl http://prometheus:9090/api/v1/alerts | jq '.data.alerts[] | select(.state=="firing")'

# Monitor logs for errors
kubectl logs deployment/sark -n production --tail=100 --follow

# Check SIEM events
# Verify events are being forwarded to Splunk/Datadog
```

**Step 8: Post-Deployment Communication** (T+2:00)
```bash
# Send success notification
# Slack: "#deployments" channel
# Email: stakeholders@example.com

# Update status page
# "All systems operational" - https://status.example.com
```

### Phase 3: Post-Deployment Monitoring (T+24 hours)

**Monitor for 24 hours**:
- Error rates (should be < 0.1%)
- Performance degradation (latency should be within targets)
- Resource utilization (should be within normal ranges)
- User reports (monitor support tickets)

**Daily Metrics Review**:
```bash
# Generate metrics report
./scripts/generate-metrics-report.sh \
  --start-time "2025-11-22T02:00:00Z" \
  --end-time "2025-11-23T02:00:00Z" \
  --output report.html
```

---

## Post-Deployment Validation

### Health Check Validation

```bash
# Basic health check
curl https://api.example.com/health | jq

# Expected response:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "timestamp": "2025-11-22T10:00:00Z"
# }

# Detailed health check
curl https://api.example.com/health/detailed | jq

# Expected response:
# {
#   "status": "healthy",
#   "components": {
#     "database": "healthy",
#     "redis": "healthy",
#     "opa": "healthy",
#     "siem": "healthy"
#   }
# }
```

### Functional Testing

**Test Authentication**:
```bash
# LDAP authentication
curl -X POST https://api.example.com/api/v1/auth/login/ldap \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpassword"
  }' | jq

# Verify token received
# Save access token
export ACCESS_TOKEN="..."
```

**Test API Endpoints**:
```bash
# List servers
curl https://api.example.com/api/v1/servers \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq

# Register server
curl -X POST https://api.example.com/api/v1/servers \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-server",
    "endpoint": "https://test-server.example.com"
  }' | jq

# Evaluate policy
curl -X POST https://api.example.com/api/v1/policies/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "server:read",
    "resource": "server-123"
  }' | jq
```

### Performance Validation

```bash
# Run quick load test (1 minute)
locust -f tests/performance/locustfile.py \
  --host https://api.example.com \
  --users 50 \
  --spawn-rate 10 \
  --run-time 1m \
  --headless

# Verify metrics:
# - p95 latency < 100ms
# - p99 latency < 200ms
# - Error rate < 0.1%
```

### Database Validation

```sql
-- Check database connectivity
kubectl exec -it postgres-0 -n production -- psql -U sark -c "SELECT version();"

-- Verify migrations applied
kubectl exec -it postgres-0 -n production -- psql -U sark -c "
  SELECT version_num, description
  FROM alembic_version
  ORDER BY version_num DESC
  LIMIT 5;
"

-- Check table row counts
kubectl exec -it postgres-0 -n production -- psql -U sark -c "
  SELECT
    schemaname,
    tablename,
    n_live_tup AS row_count
  FROM pg_stat_user_tables
  WHERE schemaname = 'public'
  ORDER BY n_live_tup DESC;
"
```

### SIEM Validation

```bash
# Check SIEM queue size
kubectl exec -it redis-0 -n production -- redis-cli LLEN siem:event_queue

# Verify events in Splunk
# Search: index=sark_audit earliest=-15m
# Should see recent events

# Verify events in Datadog
# Logs Explorer: service:sark env:production
# Should see recent logs
```

---

## Rollback Procedures

### When to Rollback

**Immediate Rollback Triggers**:
- Error rate > 5% for 5 minutes
- p99 latency > 2 seconds for 5 minutes
- Complete service outage
- Data loss or corruption detected
- Security vulnerability exploited

**Consideration for Rollback**:
- Error rate > 1% for 10 minutes
- p95 latency > 500ms for 10 minutes
- Significant feature regression
- Multiple user-reported issues

### Rollback Methods

#### Method 1: Helm Rollback (Recommended)

**Fastest rollback method** (< 2 minutes):

```bash
# Check current release
helm list -n production

# View release history
helm history sark -n production

# Output:
# REVISION  UPDATED                   STATUS      CHART       DESCRIPTION
# 1         Thu Nov 21 02:00:00 2025  superseded  sark-1.0.0  Install complete
# 2         Fri Nov 22 02:00:00 2025  deployed    sark-1.0.0  Upgrade complete

# Rollback to previous version
helm rollback sark -n production

# Or rollback to specific revision
helm rollback sark 1 -n production

# Wait for rollback to complete
kubectl rollout status deployment/sark -n production

# Verify rollback
kubectl get pods -n production
kubectl logs deployment/sark -n production --tail=50
```

#### Method 2: Kubectl Rollback

```bash
# View deployment history
kubectl rollout history deployment/sark -n production

# Rollback to previous version
kubectl rollout undo deployment/sark -n production

# Or rollback to specific revision
kubectl rollout undo deployment/sark --to-revision=3 -n production

# Monitor rollback progress
kubectl rollout status deployment/sark -n production
```

#### Method 3: Database Rollback (If Needed)

**If database migrations were applied**:

```bash
# Downgrade migrations
kubectl run sark-migrate-down \
  --image=your-registry.com/sark:1.0.0 \
  --restart=Never \
  --namespace=production \
  --command -- alembic downgrade -1

# Verify downgrade
kubectl logs sark-migrate-down -n production

# Or restore from backup
kubectl exec -it postgres-0 -n production -- \
  pg_restore -U sark -d sark -c /backups/sark-pre-deployment-20251122-0200.dump
```

### Post-Rollback Actions

**1. Verify Service Restoration**
```bash
# Health check
curl https://api.example.com/health

# Smoke tests
./scripts/smoke-test.sh https://api.example.com

# Check metrics
# Error rate should return to < 0.1%
# Latency should return to < 100ms p95
```

**2. Communication**
```bash
# Notify stakeholders
# Slack: "#deployments" channel
# Email: stakeholders@example.com
# Subject: "Production deployment rolled back - investigating"
```

**3. Post-Mortem**
```bash
# Schedule post-mortem meeting (within 24 hours)
# Agenda:
# - What went wrong?
# - Why did it go wrong?
# - How can we prevent it?
# - Action items
```

---

## Zero-Downtime Deployment

### Rolling Update Strategy

**Default Kubernetes strategy** (zero downtime):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sark
spec:
  replicas: 4
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # Create 1 extra pod during update
      maxUnavailable: 0  # Never have fewer than 4 pods available
  template:
    # ... pod spec
```

**Deployment process**:
1. Create 1 new pod with new version (total: 5 pods)
2. Wait for new pod to be ready
3. Terminate 1 old pod (total: 4 pods)
4. Repeat until all pods updated

**Advantages**:
- Zero downtime (always 4+ pods available)
- Gradual rollout (catch issues early)
- Built-in (no extra infrastructure)

**Disadvantages**:
- Slow (serial pod updates)
- Mixed versions during deployment

### Readiness Gates

**Ensure pods are truly ready before routing traffic**:

```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: sark
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          failureThreshold: 3
          successThreshold: 1
```

**Readiness endpoint** (`/ready`):
- Check database connectivity
- Check Redis connectivity
- Check OPA connectivity
- Warm up caches
- Return 200 only when ready to serve traffic

---

## Blue-Green Deployment

### Overview

**Blue-Green deployment** maintains two identical production environments:
- **Blue**: Currently live (serving traffic)
- **Green**: New version (idle, being validated)

**Switch traffic** from Blue → Green atomically (instant rollback possible).

### Implementation

**Step 1: Deploy Green Environment**

```yaml
# deployment-green.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sark-green
  labels:
    version: green
spec:
  replicas: 4
  selector:
    matchLabels:
      app: sark
      version: green
  template:
    metadata:
      labels:
        app: sark
        version: green
    spec:
      containers:
      - name: sark
        image: your-registry.com/sark:1.0.0  # New version
```

```bash
# Deploy green
kubectl apply -f deployment-green.yaml -n production

# Verify green is healthy
kubectl get pods -n production -l version=green
kubectl logs deployment/sark-green -n production --tail=50
```

**Step 2: Validate Green Environment**

```bash
# Port-forward to green deployment
kubectl port-forward deployment/sark-green 8001:8000 -n production

# Run tests against green
./scripts/smoke-test.sh http://localhost:8001

# Manual validation
curl http://localhost:8001/health
```

**Step 3: Switch Traffic to Green**

```yaml
# service.yaml (update selector)
apiVersion: v1
kind: Service
metadata:
  name: sark
spec:
  selector:
    app: sark
    version: green  # Changed from blue → green
  ports:
  - port: 80
    targetPort: 8000
```

```bash
# Apply service change (instant traffic switch)
kubectl apply -f service.yaml -n production

# Verify traffic switched
kubectl describe service sark -n production
```

**Step 4: Monitor Green Environment**

```bash
# Monitor for 30-60 minutes
kubectl top pods -n production -l version=green
kubectl logs deployment/sark-green -n production --follow

# Check metrics in Grafana
# - Error rate
# - Latency
# - Request rate
```

**Step 5: Decommission Blue Environment**

```bash
# After successful validation (e.g., 24 hours)
kubectl delete deployment sark-blue -n production
```

### Rollback (Blue-Green)

**Instant rollback** by switching service back to blue:

```yaml
# service.yaml (rollback)
apiVersion: v1
kind: Service
metadata:
  name: sark
spec:
  selector:
    app: sark
    version: blue  # Switch back to blue
```

```bash
kubectl apply -f service.yaml -n production
```

**Rollback time**: < 5 seconds (instant traffic switch)

---

## Canary Deployment

### Overview

**Canary deployment** gradually shifts traffic to new version:
- Deploy new version alongside old version
- Route 10% → 25% → 50% → 100% of traffic to new version
- Monitor at each stage, rollback if issues detected

### Implementation with Ingress

**Step 1: Deploy Canary**

```yaml
# deployment-canary.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sark-canary
spec:
  replicas: 1  # Start with 1 replica (10% of 10 total)
  selector:
    matchLabels:
      app: sark
      version: canary
  template:
    metadata:
      labels:
        app: sark
        version: canary
    spec:
      containers:
      - name: sark
        image: your-registry.com/sark:1.0.0  # New version
```

**Step 2: Configure Weighted Traffic Split**

Using **NGINX Ingress Controller**:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: sark-canary
  annotations:
    nginx.ingress.kubernetes.io/canary: "true"
    nginx.ingress.kubernetes.io/canary-weight: "10"  # 10% traffic to canary
spec:
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: sark-canary
            port:
              number: 80
```

**Step 3: Monitor Canary (10% traffic)**

```bash
# Monitor canary pods
kubectl logs deployment/sark-canary -n production --follow

# Check metrics (compare canary vs stable)
# - Error rate (should be similar)
# - Latency (should be similar)
# - CPU/memory usage
```

**Step 4: Increase Canary Traffic (25%)**

```yaml
annotations:
  nginx.ingress.kubernetes.io/canary-weight: "25"  # Increase to 25%
```

```bash
kubectl apply -f ingress-canary.yaml -n production

# Scale canary replicas
kubectl scale deployment sark-canary --replicas=3 -n production

# Monitor for 30 minutes
```

**Step 5: Promote Canary to Stable (100%)**

```bash
# Update stable deployment to new version
kubectl set image deployment/sark sark=your-registry.com/sark:1.0.0 -n production

# Wait for rollout
kubectl rollout status deployment/sark -n production

# Remove canary
kubectl delete deployment sark-canary -n production
kubectl delete ingress sark-canary -n production
```

### Automated Canary with Flagger

**Install Flagger**:
```bash
helm repo add flagger https://flagger.app
helm install flagger flagger/flagger \
  --namespace ingress-nginx \
  --set meshProvider=nginx
```

**Canary Resource**:
```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: sark
  namespace: production
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sark
  service:
    port: 80
  analysis:
    interval: 1m
    threshold: 5
    maxWeight: 50
    stepWeight: 10
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
      interval: 1m
    - name: request-duration
      thresholdRange:
        max: 500
      interval: 1m
```

**Automated rollout**:
1. Flagger creates canary deployment
2. Routes 10% traffic to canary
3. Measures success rate and latency
4. If metrics OK, increases to 20%, 30%, ..., 50%
5. If metrics fail, automatically rolls back

---

## Troubleshooting

### Deployment Stuck

**Symptom**: Deployment not progressing

**Diagnosis**:
```bash
kubectl describe deployment sark -n production
kubectl get pods -n production
kubectl describe pod <pod-name> -n production
```

**Common Causes**:
- Image pull error (check image exists in registry)
- Insufficient resources (check node capacity)
- Failing readiness probe (check `/ready` endpoint)
- Pod stuck in `Pending` (check PVC binding)

**Fix**:
```bash
# Fix and reapply
kubectl delete pod <stuck-pod> -n production

# Or rollback
helm rollback sark -n production
```

### High Error Rate After Deployment

**Symptom**: Error rate > 1% after deployment

**Diagnosis**:
```bash
# Check logs for errors
kubectl logs deployment/sark -n production --tail=100 | grep ERROR

# Check specific error types
curl https://api.example.com/api/v1/servers | jq
```

**Common Causes**:
- Database migration issues
- Configuration errors (environment variables)
- Breaking API changes
- Dependency failures (Redis, OPA)

**Fix**: Rollback immediately
```bash
helm rollback sark -n production
```

### Performance Degradation

**Symptom**: Latency increased after deployment

**Diagnosis**:
```bash
# Check resource usage
kubectl top pods -n production

# Check database queries
kubectl exec -it postgres-0 -n production -- psql -U sark -c "
  SELECT pid, query_start, state, query
  FROM pg_stat_activity
  WHERE state = 'active'
  ORDER BY query_start;
"

# Check Redis memory
kubectl exec -it redis-0 -n production -- redis-cli INFO memory
```

**Common Causes**:
- Inefficient queries (missing indexes)
- Memory leak
- Cache not warming properly
- Increased load

---

## Summary

This guide provides production-ready deployment procedures:

- **Infrastructure Requirements**: Complete cloud and on-prem specifications
- **Pre-Deployment Checklist**: 60+ items covering security, performance, testing
- **Deployment Steps**: Phase-by-phase deployment with validation
- **Rollback Procedures**: Multiple rollback methods (Helm, kubectl, database)
- **Zero-Downtime Deployment**: Rolling updates with readiness gates
- **Blue-Green Deployment**: Instant traffic switching, instant rollback
- **Canary Deployment**: Gradual traffic shifting with automated rollback

Following these procedures ensures reliable, safe production deployments with minimal risk.
