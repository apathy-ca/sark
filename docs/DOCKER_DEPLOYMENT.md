# SARK Docker & Kubernetes Deployment Guide

This guide covers deploying SARK using Docker Compose and Kubernetes with production-ready configurations.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Docker Deployment](#docker-deployment)
  - [Development Environment](#development-environment)
  - [Production Environment](#production-environment)
  - [Docker Security](#docker-security)
- [Kubernetes Deployment](#kubernetes-deployment)
  - [Prerequisites](#k8s-prerequisites)
  - [Deployment Steps](#deployment-steps)
  - [Scaling and Updates](#scaling-and-updates)
- [Monitoring and Observability](#monitoring-and-observability)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Prerequisites

### General Requirements
- Docker Engine 20.10+ or Docker Desktop
- Docker Compose 2.0+
- At least 4GB RAM available
- 10GB disk space

### For Kubernetes
- Kubernetes cluster 1.24+
- kubectl CLI tool
- Kustomize 4.0+ (bundled with kubectl 1.14+)
- Helm 3.0+ (optional, for advanced deployments)

---

## Docker Deployment

### Development Environment

**Quick Start:**

```bash
# Clone repository
git clone https://github.com/your-org/sark.git
cd sark

# Start development environment
docker-compose --profile managed up -d

# View logs
docker-compose logs -f app

# Run tests
docker-compose exec app pytest

# Stop environment
docker-compose down
```

**Development Features:**
- Hot reload enabled
- Debug mode active
- Test databases included
- Code mounted as volume for live editing

**Available Services:**
- **app**: SARK API application (port 8000)
- **database**: PostgreSQL 15 (port 5432)
- **cache**: Redis 7 (port 6379)
- **kong**: Kong API Gateway (ports 8000, 8001)

### Production Environment

#### 1. Environment Configuration

Create `.env.production` file:

```bash
# Application
SARK_VERSION=1.0.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=info

# Database
POSTGRES_DB=sark_prod
POSTGRES_USER=sark_user
POSTGRES_PASSWORD=<STRONG_PASSWORD>

# Redis
REDIS_PASSWORD=<STRONG_PASSWORD>

# Security
SECRET_KEY=<GENERATE_WITH: python -c "import secrets; print(secrets.token_urlsafe(32))">
JWT_SECRET_KEY=<GENERATE_WITH: python -c "import secrets; print(secrets.token_urlsafe(32))">

# OIDC
OIDC_CLIENT_ID=your_client_id
OIDC_CLIENT_SECRET=your_client_secret

# Kong
KONG_DB_PASSWORD=<STRONG_PASSWORD>
KONG_ENABLED=true

# Monitoring
GRAFANA_ADMIN_PASSWORD=<STRONG_PASSWORD>

# CORS
CORS_ORIGINS=https://your-domain.com,https://api.your-domain.com
```

**⚠️ Security Note**: Never commit `.env.production` to version control!

#### 2. Build Production Images

```bash
# Build SARK API image
docker build -f Dockerfile.production --target runtime -t sark:1.0.0 .

# Build migrations image
docker build -f Dockerfile.production --target migrations -t sark-migrations:1.0.0 .

# Tag for registry (optional)
docker tag sark:1.0.0 registry.example.com/sark:1.0.0
docker push registry.example.com/sark:1.0.0
```

#### 3. Deploy Production Stack

```bash
# Deploy all services
docker-compose -f docker-compose.production.yml up -d

# Check status
docker-compose -f docker-compose.production.yml ps

# View logs
docker-compose -f docker-compose.production.yml logs -f sark-api

# Scale API instances
docker-compose -f docker-compose.production.yml up -d --scale sark-api=5
```

#### 4. Initialize Database

```bash
# Run migrations
docker-compose -f docker-compose.production.yml run --rm sark-migrations

# Verify database
docker-compose -f docker-compose.production.yml exec sark-db psql -U $POSTGRES_USER -d $POSTGRES_DB -c "\dt"
```

#### 5. Health Checks

```bash
# API health
curl http://localhost:8000/health

# Database health
docker-compose -f docker-compose.production.yml exec sark-db pg_isready

# Redis health
docker-compose -f docker-compose.production.yml exec sark-redis redis-cli -a $REDIS_PASSWORD ping

# Kong health
curl http://localhost:8001/status
```

### Docker Security

**Image Security Best Practices:**

1. **Non-Root User**: All containers run as UID 1000
2. **Read-Only Filesystem**: Root filesystem is read-only
3. **No New Privileges**: Security opt `no-new-privileges:true`
4. **Dropped Capabilities**: All Linux capabilities dropped
5. **Resource Limits**: Memory and CPU limits enforced
6. **Secret Management**: Secrets via environment or Docker secrets

**Scanning Images:**

```bash
# Scan for vulnerabilities (requires Docker Scout)
docker scout cves sark:1.0.0

# Scan with Trivy
trivy image sark:1.0.0

# Scan with Anchore Grype
grype sark:1.0.0
```

**Hardening Checklist:**

- ✅ Use official base images only
- ✅ Multi-stage builds to minimize attack surface
- ✅ Scan images before deployment
- ✅ Sign images with Docker Content Trust
- ✅ Use secrets management (not environment variables)
- ✅ Enable AppArmor/SELinux profiles
- ✅ Limit network exposure
- ✅ Regular security updates

---

## Kubernetes Deployment

### K8s Prerequisites

**Required Cluster Components:**

- **Ingress Controller**: nginx-ingress or similar
- **Cert Manager**: For TLS certificates
- **Metrics Server**: For HPA (Horizontal Pod Autoscaler)
- **Storage Class**: For persistent volumes

**Install Prerequisites:**

```bash
# Ingress NGINX
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml

# Cert Manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Metrics Server
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### Deployment Steps

#### 1. Create Namespace

```bash
kubectl create namespace sark
```

#### 2. Create Secrets

**Option A: Using kubectl**

```bash
kubectl create secret generic sark-secrets \
  --from-literal=POSTGRES_USER=sark \
  --from-literal=POSTGRES_PASSWORD=<PASSWORD> \
  --from-literal=REDIS_PASSWORD=<PASSWORD> \
  --from-literal=SECRET_KEY=<SECRET> \
  --from-literal=JWT_SECRET_KEY=<SECRET> \
  --from-literal=OIDC_CLIENT_ID=<ID> \
  --from-literal=OIDC_CLIENT_SECRET=<SECRET> \
  --from-literal=KONG_DB_PASSWORD=<PASSWORD> \
  --from-literal=GRAFANA_ADMIN_PASSWORD=<PASSWORD> \
  --namespace=sark
```

**Option B: Using Sealed Secrets (Recommended for GitOps)**

```bash
# Install Sealed Secrets controller
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# Create sealed secret
kubectl create secret generic sark-secrets \
  --from-literal=POSTGRES_PASSWORD=<PASSWORD> \
  --dry-run=client -o yaml | \
  kubeseal -o yaml > k8s/base/sealed-secret.yaml

# Apply sealed secret
kubectl apply -f k8s/base/sealed-secret.yaml
```

**Option C: Using External Secrets Operator**

```yaml
# external-secret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: sark-secrets
  namespace: sark
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: sark-secrets
  data:
    - secretKey: POSTGRES_PASSWORD
      remoteRef:
        key: sark/postgres
        property: password
```

#### 3. Deploy Using Kustomize

**Base Deployment:**

```bash
# Build and preview
kubectl kustomize k8s/base

# Deploy base configuration
kubectl apply -k k8s/base

# Verify deployment
kubectl get pods -n sark
kubectl get svc -n sark
```

**Production Deployment:**

```bash
# Deploy production overlay
kubectl apply -k k8s/overlays/production

# Watch rollout
kubectl rollout status deployment/sark-api -n sark-prod

# Check pods
kubectl get pods -n sark-prod -l app.kubernetes.io/name=sark
```

#### 4. Verify Deployment

```bash
# Check all resources
kubectl get all -n sark

# Check pod status
kubectl get pods -n sark -o wide

# Check logs
kubectl logs -f deployment/sark-api -n sark

# Check events
kubectl get events -n sark --sort-by='.lastTimestamp'

# Port forward for testing
kubectl port-forward svc/sark-api 8000:8000 -n sark

# Test API
curl http://localhost:8000/health
```

### Scaling and Updates

#### Manual Scaling

```bash
# Scale deployment
kubectl scale deployment sark-api --replicas=5 -n sark

# Verify scaling
kubectl get pods -n sark -l app.kubernetes.io/name=sark
```

#### Horizontal Pod Autoscaler (HPA)

```bash
# HPA is automatically deployed with base manifests
kubectl get hpa -n sark

# Describe HPA
kubectl describe hpa sark-api -n sark

# Watch HPA
kubectl get hpa -n sark --watch
```

#### Rolling Updates

```bash
# Update image
kubectl set image deployment/sark-api sark-api=sark:1.1.0 -n sark

# Watch rollout
kubectl rollout status deployment/sark-api -n sark

# Rollout history
kubectl rollout history deployment/sark-api -n sark

# Rollback if needed
kubectl rollout undo deployment/sark-api -n sark
```

#### Blue/Green Deployment

```bash
# Create new deployment (green)
kubectl apply -f k8s/blue-green/green-deployment.yaml

# Verify green deployment
kubectl get pods -l version=green -n sark

# Switch traffic
kubectl patch svc sark-api -p '{"spec":{"selector":{"version":"green"}}}' -n sark

# Remove old deployment (blue)
kubectl delete deployment sark-api-blue -n sark
```

---

## Monitoring and Observability

### Accessing Monitoring Tools

**Prometheus:**
```bash
# Port forward
kubectl port-forward svc/sark-prometheus 9090:9090 -n sark

# Access: http://localhost:9090
```

**Grafana:**
```bash
# Port forward
kubectl port-forward svc/sark-grafana 3000:3000 -n sark

# Access: http://localhost:3000
# Default credentials: admin / <GRAFANA_ADMIN_PASSWORD>
```

### Key Metrics to Monitor

**Application Metrics:**
- Request rate (requests/second)
- Error rate (%)
- Response time (p50, p95, p99)
- Active sessions
- Rate limit hits

**Infrastructure Metrics:**
- CPU usage
- Memory usage
- Pod restarts
- Network traffic
- Disk I/O

**Database Metrics:**
- Connection pool utilization
- Query duration
- Slow queries
- Replication lag

**Redis Metrics:**
- Memory usage
- Hit/miss ratio
- Evicted keys
- Connected clients

### Prometheus Queries

```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# Response time 95th percentile
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Pod CPU usage
rate(container_cpu_usage_seconds_total{namespace="sark",pod=~"sark-api-.*"}[5m])

# Pod memory usage
container_memory_working_set_bytes{namespace="sark",pod=~"sark-api-.*"}
```

---

## Troubleshooting

### Common Issues

#### Pods Not Starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n sark

# Check events
kubectl get events -n sark --sort-by='.lastTimestamp'

# Check logs
kubectl logs <pod-name> -n sark --previous
```

**Common Causes:**
- Image pull errors → Check image tag and registry credentials
- Resource limits → Adjust requests/limits in deployment
- Config/secret errors → Verify ConfigMap and Secret exist
- Init container failures → Check init container logs

#### Database Connection Issues

```bash
# Test database connectivity from pod
kubectl exec -it <pod-name> -n sark -- \
  sh -c 'nc -zv sark-postgres 5432'

# Check database logs
kubectl logs deployment/sark-postgres -n sark

# Verify credentials
kubectl get secret sark-secrets -n sark -o yaml
```

#### High Memory Usage

```bash
# Check resource usage
kubectl top pods -n sark

# Describe pod for OOMKilled events
kubectl describe pod <pod-name> -n sark

# Increase memory limits
kubectl patch deployment sark-api -n sark -p \
  '{"spec":{"template":{"spec":{"containers":[{"name":"sark-api","resources":{"limits":{"memory":"1Gi"}}}]}}}}'
```

#### Certificate Issues

```bash
# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager

# Check certificate status
kubectl get certificate -n sark

# Describe certificate
kubectl describe certificate sark-api-tls -n sark

# Force renewal
kubectl delete secret sark-api-tls -n sark
```

---

## Best Practices

### Production Readiness Checklist

**Security:**
- ✅ All secrets in secure storage (Sealed Secrets, Vault, etc.)
- ✅ RBAC configured with least privilege
- ✅ Network policies enforced
- ✅ Pod security policies/standards enabled
- ✅ Container images scanned and signed
- ✅ TLS enabled for all external traffic
- ✅ Regular security updates automated

**Reliability:**
- ✅ Resource requests and limits set
- ✅ Health checks configured (liveness, readiness, startup)
- ✅ HPA configured for auto-scaling
- ✅ PodDisruptionBudget set
- ✅ Multiple replicas across zones
- ✅ Graceful shutdown implemented
- ✅ Circuit breakers configured

**Observability:**
- ✅ Centralized logging (ELK, Loki, etc.)
- ✅ Metrics collection (Prometheus)
- ✅ Distributed tracing (Jaeger, Zipkin)
- ✅ Alerting rules configured
- ✅ Dashboards created (Grafana)
- ✅ SLOs defined and monitored

**Operations:**
- ✅ GitOps workflow (ArgoCD, Flux)
- ✅ CI/CD pipelines automated
- ✅ Database backups configured
- ✅ Disaster recovery plan documented
- ✅ Runbooks created for common issues
- ✅ On-call rotation established

### Resource Sizing Guide

**Development:**
```yaml
resources:
  requests:
    memory: "128Mi"
    cpu: "100m"
  limits:
    memory: "256Mi"
    cpu: "200m"
```

**Staging:**
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

**Production:**
```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

### Backup and Disaster Recovery

**PostgreSQL Backups:**

```bash
# Create backup
kubectl exec sark-postgres-0 -n sark -- \
  pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup.sql

# Restore backup
kubectl exec -i sark-postgres-0 -n sark -- \
  psql -U $POSTGRES_USER $POSTGRES_DB < backup.sql

# Automated backups with CronJob
kubectl apply -f k8s/backup/postgres-backup-cronjob.yaml
```

**Redis Backups:**

```bash
# Trigger save
kubectl exec sark-redis-0 -n sark -- redis-cli BGSAVE

# Copy RDB file
kubectl cp sark/sark-redis-0:/data/dump.rdb ./redis-backup.rdb
```

### Performance Tuning

**Database Connection Pool:**
```yaml
- name: POSTGRES_POOL_SIZE
  value: "20"
- name: POSTGRES_MAX_OVERFLOW
  value: "40"
```

**Redis Connection Pool:**
```yaml
- name: REDIS_POOL_SIZE
  value: "50"
- name: REDIS_MAX_CONNECTIONS
  value: "100"
```

**Worker Processes:**
```yaml
- name: WORKERS
  value: "4"  # 2x CPU cores
- name: WORKER_TIMEOUT
  value: "30"
```

---

## Additional Resources

- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
- [Docker Security](https://docs.docker.com/engine/security/)
- [CNCF Cloud Native Trail Map](https://github.com/cncf/trailmap)
- [12-Factor App Methodology](https://12factor.net/)

---

*Last Updated: 2024-11-23*
