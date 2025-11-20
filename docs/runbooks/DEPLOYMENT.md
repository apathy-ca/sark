# SARK Deployment Runbook

## Quick Start - Local Development

### Prerequisites

- Docker and Docker Compose v2
- Python 3.11+
- Git

### Steps

1. **Clone repository and set up environment:**

```bash
git clone <repository-url>
cd sark
cp .env.example .env
# Edit .env with your configuration
```

2. **Start all services:**

```bash
docker compose up -d
```

3. **Verify services are running:**

```bash
docker compose ps
```

All services should show as "Up" or "healthy".

4. **Access services:**

- SARK API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Consul UI: http://localhost:8500
- OPA: http://localhost:8181
- Prometheus: http://localhost:9091
- Grafana: http://localhost:3000 (admin/admin)
- Vault: http://localhost:8200

5. **Run tests:**

```bash
docker compose run --rm api pytest
```

## Production Deployment - Kubernetes

### Prerequisites

- Kubernetes cluster 1.28+
- kubectl configured
- Helm 3+ (optional)
- Container registry access

### Build and Push Images

```bash
# Build API image
docker build -t your-registry/sark-api:v0.1.0 .

# Push to registry
docker push your-registry/sark-api:v0.1.0
```

### Deploy to Kubernetes

1. **Create namespace:**

```bash
kubectl apply -f k8s/base/namespace.yaml
```

2. **Create secrets:**

```bash
kubectl create secret generic sark-secrets \
  --from-literal=secret-key=<your-secret-key> \
  -n sark-system

kubectl create secret generic postgres-credentials \
  --from-literal=username=sark \
  --from-literal=password=<postgres-password> \
  -n sark-system

kubectl create secret generic timescale-credentials \
  --from-literal=username=sark \
  --from-literal=password=<timescale-password> \
  -n sark-system
```

3. **Deploy OPA:**

```bash
kubectl apply -f k8s/base/opa-deployment.yaml
```

4. **Deploy SARK API:**

```bash
kubectl apply -f k8s/base/deployment.yaml
```

5. **Verify deployment:**

```bash
kubectl get pods -n sark-system
kubectl logs -f deployment/sark-api -n sark-system
```

### Health Checks

```bash
# Check API health
kubectl exec -it deployment/sark-api -n sark-system -- \
  curl http://localhost:8000/health

# Check OPA
kubectl exec -it deployment/opa -n sark-system -- \
  curl http://localhost:8181/health
```

## Scaling

### Horizontal Scaling

```bash
# Scale API
kubectl scale deployment/sark-api --replicas=10 -n sark-system

# Scale OPA
kubectl scale deployment/opa --replicas=7 -n sark-system
```

### Database Scaling

For production, use managed database services:

- **PostgreSQL**: AWS RDS, GCP Cloud SQL, or Azure Database
- **TimescaleDB**: Timescale Cloud or self-hosted with replication
- **Redis**: AWS ElastiCache, GCP Memorystore, or Azure Cache

Update connection strings in secrets accordingly.

## Monitoring

### Prometheus Queries

```promql
# API request rate
rate(http_requests_total[5m])

# Policy evaluation latency
histogram_quantile(0.99, rate(policy_evaluation_duration_seconds_bucket[5m]))

# Error rate
rate(http_requests_total{status=~"5.."}[5m])
```

### Grafana Dashboards

Import dashboards from `config/grafana-dashboards/` directory.

## Troubleshooting

### API Not Starting

```bash
# Check logs
docker compose logs api

# Or in Kubernetes
kubectl logs deployment/sark-api -n sark-system

# Common issues:
# 1. Database connection - verify credentials and connectivity
# 2. Missing environment variables - check .env or secrets
# 3. Port conflicts - ensure ports are available
```

### OPA Policy Errors

```bash
# Test policy locally
docker run --rm -v $(pwd)/opa/policies:/policies openpolicyagent/opa \
  test /policies -v

# Check OPA logs
kubectl logs deployment/opa -n sark-system
```

### Database Migration Issues

```bash
# Run migrations manually
docker compose exec api alembic upgrade head

# Or in Kubernetes
kubectl exec -it deployment/sark-api -n sark-system -- alembic upgrade head
```

## Rollback Procedures

### Kubernetes Rollback

```bash
# View deployment history
kubectl rollout history deployment/sark-api -n sark-system

# Rollback to previous version
kubectl rollout undo deployment/sark-api -n sark-system

# Rollback to specific revision
kubectl rollout undo deployment/sark-api --to-revision=2 -n sark-system
```

### Policy Rollback

OPA policies are versioned in the database. Use the policy management API to activate previous versions.

## Backup and Recovery

### Database Backup

```bash
# PostgreSQL backup
docker compose exec postgres pg_dump -U sark sark > backup.sql

# TimescaleDB backup
docker compose exec timescaledb pg_dump -U sark sark_audit > audit_backup.sql
```

### Restore

```bash
# PostgreSQL restore
cat backup.sql | docker compose exec -T postgres psql -U sark sark

# TimescaleDB restore
cat audit_backup.sql | docker compose exec -T timescaledb psql -U sark sark_audit
```

## Performance Tuning

### Database Connection Pooling

Adjust in `.env` or environment variables:

```
POSTGRES_POOL_SIZE=50
POSTGRES_MAX_OVERFLOW=20
```

### OPA Caching

OPA automatically caches policy decisions. Monitor cache hit rate:

```promql
opa_decision_cache_hit_rate
```

### Redis Configuration

For high-throughput scenarios, tune Redis:

```bash
# Increase max connections
docker compose exec redis redis-cli CONFIG SET maxclients 10000
```

---

**For additional support, refer to:**

- [Architecture Documentation](../ARCHITECTURE.md)
- [API Documentation](http://localhost:8000/docs)
- [GitHub Issues](https://github.com/your-org/sark/issues)
