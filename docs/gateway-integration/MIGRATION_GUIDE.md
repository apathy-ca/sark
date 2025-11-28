# Migration Guide: v1.0.0 → v1.1.0

**From:** SARK v1.0.0
**To:** SARK v1.1.0 (Gateway Integration)
**Migration Type:** Non-breaking upgrade
**Rollback Support:** Yes

---

## Overview

This guide covers upgrading SARK from v1.0.0 to v1.1.0, which adds **opt-in** Gateway integration support. This is a **non-breaking upgrade** - your existing v1.0.0 deployment will continue to work identically after upgrading.

**Key Points:**
- ✅ **100% Backwards Compatible** - Zero breaking changes
- ✅ **Gateway Disabled by Default** - Behaves like v1.0.0 until you enable it
- ✅ **Zero-Downtime Upgrade** - Rolling restart supported
- ✅ **Reversible** - Can rollback to v1.0.0 if needed
- ✅ **Gradual Enablement** - Enable Gateway features at your own pace

---

## Table of Contents

- [Pre-Migration Checklist](#pre-migration-checklist)
- [Migration Path](#migration-path)
  - [Docker Compose](#docker-compose-migration)
  - [Kubernetes](#kubernetes-migration)
- [Post-Migration Validation](#post-migration-validation)
- [Enabling Gateway Integration](#enabling-gateway-integration)
- [Rollback Procedure](#rollback-procedure)
- [Troubleshooting](#troubleshooting)

---

## Pre-Migration Checklist

Complete these steps **before** starting the migration:

### 1. Verify Current Version

```bash
# Check current SARK version
curl http://localhost:8000/api/v1/version

# Expected output:
{
  "version": "1.0.0",
  ...
}
```

### 2. Backup Database

```bash
# Docker Compose
docker compose exec postgres pg_dump -U sark sark > backup-v1.0.0-$(date +%Y%m%d).sql

# Kubernetes
kubectl exec -it postgres-0 -n sark -- \
  pg_dump -U sark sark > backup-v1.0.0-$(date +%Y%m%d).sql
```

**Store the backup securely** - you'll need it for rollback if issues occur.

### 3. Backup Configuration

```bash
# Docker Compose
cp .env .env.backup-v1.0.0
cp docker-compose.yml docker-compose.yml.backup-v1.0.0

# Kubernetes
kubectl get configmap sark-config -n sark -o yaml > sark-config-v1.0.0.yaml
kubectl get secret sark-secrets -n sark -o yaml > sark-secrets-v1.0.0.yaml
```

### 4. Review Release Notes

Read the [RELEASE_NOTES.md](./RELEASE_NOTES.md) for v1.1.0 to understand:
- New features added
- Configuration changes
- API changes (none - backwards compatible)
- Known issues

### 5. Schedule Maintenance Window

While this is a zero-downtime upgrade, schedule a **30-minute maintenance window** for:
- Database migration execution
- Validation testing
- Potential rollback (if needed)

---

## Migration Path

### Docker Compose Migration

#### Step 1: Pull v1.1.0 Image

```bash
# Pull the latest v1.1.0 image
docker pull sark:1.1.0

# Verify image
docker images | grep sark
# Should show: sark    1.1.0    ...
```

#### Step 2: Run Database Migrations

```bash
# Stop SARK (to avoid concurrent access during migration)
docker compose stop sark

# Run database migrations
docker run --rm \
  --network sark_default \
  -e DATABASE_URL="postgresql://sark:password@postgres:5432/sark" \
  sark:1.1.0 \
  alembic upgrade head

# Expected output:
# INFO  [alembic.runtime.migration] Running upgrade 1.0.0 -> 1.1.0
# INFO  [alembic.runtime.migration] Adding gateway_audit_events table
# INFO  [alembic.runtime.migration] Adding gateway_api_keys table
# INFO  [alembic.runtime.migration] Migration complete
```

#### Step 3: Update docker-compose.yml

```bash
# Update SARK image version
sed -i 's/sark:1.0.0/sark:1.1.0/' docker-compose.yml

# Or manually edit docker-compose.yml:
# services:
#   sark:
#     image: sark:1.1.0  # Changed from 1.0.0
```

#### Step 4: Ensure Gateway is Disabled (Default)

```bash
# Verify .env does NOT have GATEWAY_ENABLED=true
grep GATEWAY_ENABLED .env

# If not present, explicitly set to false (optional - this is the default)
echo "GATEWAY_ENABLED=false" >> .env
```

#### Step 5: Start SARK v1.1.0

```bash
# Start SARK with new version
docker compose up -d sark

# Watch logs
docker compose logs -f sark
```

**Expected log output:**
```
INFO: Starting SARK v1.1.0
INFO: Database connection established
INFO: Gateway integration: DISABLED (feature flag not set)
INFO: Application startup complete
```

#### Step 6: Validate Migration

```bash
# Check version
curl http://localhost:8000/api/v1/version

# Expected output:
{
  "version": "1.1.0",
  "features": {
    "gateway_integration": false,  # ✅ Disabled (v1.0.0 behavior)
    "a2a_authorization": false
  }
}

# Test existing endpoints (should work identically to v1.0.0)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "admin_password"
  }'

# Should return: {"access_token": "...", ...}
```

---

### Kubernetes Migration

#### Step 1: Update Container Image

```bash
# Update deployment to use v1.1.0 image
kubectl set image deployment/sark \
  sark=sark:1.1.0 \
  -n sark

# Watch rollout
kubectl rollout status deployment/sark -n sark
```

#### Step 2: Run Database Migrations (Job)

Create a Kubernetes Job to run migrations:

```yaml
# migration-job-v1.1.0.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: sark-migration-v1-1-0
  namespace: sark
spec:
  template:
    spec:
      containers:
      - name: migration
        image: sark:1.1.0
        command: ["alembic", "upgrade", "head"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: sark-secrets
              key: database-url
      restartPolicy: OnFailure
  backoffLimit: 3
```

Run the migration job:

```bash
# Apply migration job
kubectl apply -f migration-job-v1.1.0.yaml

# Watch job status
kubectl get jobs -n sark -w

# Check logs
kubectl logs job/sark-migration-v1-1-0 -n sark
```

#### Step 3: Verify Gateway is Disabled

```bash
# Check ConfigMap
kubectl get configmap sark-config -n sark -o yaml | grep GATEWAY_ENABLED

# If not present, add it explicitly (optional - disabled by default)
kubectl patch configmap sark-config -n sark \
  --type merge \
  -p '{"data":{"GATEWAY_ENABLED":"false"}}'

# Restart pods to pick up config
kubectl rollout restart deployment/sark -n sark
```

#### Step 4: Validate Migration

```bash
# Port-forward to SARK pod
kubectl port-forward deployment/sark 8000:8000 -n sark

# Check version (in another terminal)
curl http://localhost:8000/api/v1/version

# Expected output:
{
  "version": "1.1.0",
  "features": {
    "gateway_integration": false,  # ✅ Disabled
    "a2a_authorization": false
  }
}
```

---

## Post-Migration Validation

### 1. Verify All Existing Endpoints Work

```bash
# Authentication
curl -X POST http://localhost:8000/api/v1/auth/login -d '{...}'

# Policy evaluation
curl -X POST http://localhost:8000/api/v1/policies/evaluate -d '{...}'

# MCP server management
curl -X GET http://localhost:8000/api/v1/mcp-servers

# All should work identically to v1.0.0
```

### 2. Run Integration Tests

```bash
# Docker Compose
docker compose exec sark pytest tests/integration/

# Kubernetes
kubectl exec -it deployment/sark -n sark -- pytest tests/integration/
```

### 3. Check Performance Metrics

```bash
# Verify no performance degradation
curl http://localhost:9090/api/v1/query \
  -d 'query=rate(http_request_duration_seconds_sum[5m])'

# P95 latency should be identical to v1.0.0
```

### 4. Monitor for 24-48 Hours

Monitor key metrics:
- **Error Rate** - Should be ≤ v1.0.0
- **Latency (P50, P95, P99)** - Should be ≤ v1.0.0
- **Resource Usage** - Should be ≤ v1.0.0 + 2%
- **Database Queries** - Should be identical to v1.0.0

---

## Enabling Gateway Integration

After successfully migrating to v1.1.0 and validating backwards compatibility, you can **optionally** enable Gateway integration:

### Step 1: Deploy MCP Gateway (If Needed)

```bash
# Example: Deploy Gateway via Docker Compose
docker compose -f docker-compose.gateway.yml up -d
```

### Step 2: Generate SARK Gateway API Key

```bash
docker exec -it sark python -m sark.cli.generate_api_key \
  --name "MCP Gateway Production" \
  --type gateway \
  --permissions "gateway:*"

# Save the output API key
```

### Step 3: Enable Gateway Feature Flag

```bash
# Docker Compose
cat >> .env << EOF
GATEWAY_ENABLED=true
GATEWAY_URL=http://mcp-gateway:8080
GATEWAY_API_KEY=sark_gw_1234567890abcdef
EOF

docker compose restart sark

# Kubernetes
kubectl patch configmap sark-config -n sark \
  --type merge \
  -p '{
    "data": {
      "GATEWAY_ENABLED": "true",
      "GATEWAY_URL": "http://mcp-gateway.mcp-gateway.svc.cluster.local:8080"
    }
  }'

kubectl create secret generic sark-gateway-secret \
  --from-literal=gateway-api-key='sark_gw_1234567890abcdef' \
  -n sark

kubectl rollout restart deployment/sark -n sark
```

### Step 4: Verify Gateway Integration

```bash
curl http://localhost:8000/api/v1/version

# Expected output:
{
  "version": "1.1.0",
  "features": {
    "gateway_integration": true,  # ✅ Now enabled
    "a2a_authorization": false
  }
}

# Test Gateway authorization endpoint
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer $TOKEN" \
  -d '{...}'
```

See [deployment/QUICKSTART.md](./deployment/QUICKSTART.md) for detailed Gateway setup instructions.

---

## Rollback Procedure

If issues occur, rollback to v1.0.0:

### Docker Compose Rollback

```bash
# Step 1: Stop SARK
docker compose stop sark

# Step 2: Rollback database migration
docker run --rm \
  --network sark_default \
  -e DATABASE_URL="postgresql://sark:password@postgres:5432/sark" \
  sark:1.1.0 \
  alembic downgrade -1

# Step 3: Restore v1.0.0 image
docker pull sark:1.0.0
sed -i 's/sark:1.1.0/sark:1.0.0/' docker-compose.yml

# Step 4: Restore configuration
cp .env.backup-v1.0.0 .env
cp docker-compose.yml.backup-v1.0.0 docker-compose.yml

# Step 5: Start SARK v1.0.0
docker compose up -d sark

# Step 6: Verify rollback
curl http://localhost:8000/api/v1/version
# Should show: "version": "1.0.0"
```

### Kubernetes Rollback

```bash
# Step 1: Rollback deployment
kubectl rollout undo deployment/sark -n sark

# Or explicitly set v1.0.0 image
kubectl set image deployment/sark sark=sark:1.0.0 -n sark

# Step 2: Rollback database migration (Job)
kubectl apply -f migration-rollback-job.yaml

# Step 3: Restore configuration
kubectl apply -f sark-config-v1.0.0.yaml

# Step 4: Verify rollback
kubectl get pods -n sark
curl http://localhost:8000/api/v1/version
```

### Database Rollback Job

```yaml
# migration-rollback-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: sark-migration-rollback-v1-1-0
  namespace: sark
spec:
  template:
    spec:
      containers:
      - name: migration-rollback
        image: sark:1.1.0
        command: ["alembic", "downgrade", "-1"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: sark-secrets
              key: database-url
      restartPolicy: OnFailure
```

---

## Troubleshooting

### Issue: Migration Fails with "relation already exists"

**Symptoms:**
```
ERROR: relation "gateway_audit_events" already exists
```

**Cause:** Migration already ran or partial migration occurred.

**Resolution:**
```bash
# Check migration status
docker exec -it sark alembic current

# If at v1.1.0, no action needed
# If at v1.0.0, manually mark as upgraded:
docker exec -it sark alembic stamp head
```

### Issue: "Gateway endpoints not found" (404)

**Symptoms:**
```bash
curl http://localhost:8000/api/v1/gateway/authorize
# Returns: 404 Not Found
```

**Cause:** SARK not fully restarted or image not updated.

**Resolution:**
```bash
# Verify version
curl http://localhost:8000/api/v1/version

# If showing v1.0.0, image didn't update
docker compose down
docker compose up -d
```

### Issue: Performance Degradation After Migration

**Symptoms:** Latency increased, CPU usage higher.

**Diagnosis:**
```bash
# Check if Gateway is accidentally enabled
docker exec -it sark env | grep GATEWAY_ENABLED

# Check metrics
curl http://localhost:9090/metrics | grep gateway
```

**Resolution:**
```bash
# Ensure Gateway is disabled
echo "GATEWAY_ENABLED=false" > .env
docker compose restart sark

# Performance should return to v1.0.0 levels
```

### Issue: Database Connection Errors After Migration

**Symptoms:**
```
ERROR: could not connect to database
```

**Cause:** Migration changed database connection pool settings.

**Resolution:**
```bash
# Check database URL
docker compose exec sark env | grep DATABASE_URL

# Reset connection pool (if needed)
docker compose restart postgres
docker compose restart sark
```

---

## Migration Checklist

Use this checklist to track your migration:

### Pre-Migration
- [ ] Verified current version is v1.0.0
- [ ] Backed up database
- [ ] Backed up configuration files
- [ ] Read release notes
- [ ] Scheduled maintenance window

### Migration
- [ ] Pulled v1.1.0 image
- [ ] Ran database migrations successfully
- [ ] Updated docker-compose.yml / Kubernetes manifests
- [ ] Verified `GATEWAY_ENABLED=false` (or not set)
- [ ] Restarted SARK

### Post-Migration
- [ ] Verified version is v1.1.0
- [ ] Verified `gateway_integration: false` in `/version` endpoint
- [ ] Tested all existing endpoints (auth, policies, servers)
- [ ] Ran integration tests successfully
- [ ] Monitored metrics for 24-48 hours
- [ ] No increase in error rate
- [ ] No increase in latency
- [ ] No increase in resource usage

### Optional: Enable Gateway
- [ ] Deployed MCP Gateway (if needed)
- [ ] Generated SARK Gateway API key
- [ ] Set `GATEWAY_ENABLED=true`
- [ ] Configured `GATEWAY_URL` and `GATEWAY_API_KEY`
- [ ] Restarted SARK
- [ ] Verified `gateway_integration: true`
- [ ] Tested Gateway endpoints
- [ ] Monitored Gateway metrics

---

## Summary

**Migration Difficulty:** ⭐ Easy (non-breaking upgrade)

**Expected Downtime:** 0 minutes (zero-downtime rolling restart)

**Rollback Time:** < 5 minutes

**Risk Level:** Low (100% backwards compatible)

**Recommended Approach:**
1. Migrate to v1.1.0 with Gateway **disabled** (default)
2. Validate for 24-48 hours
3. **Optionally** enable Gateway integration when ready

---

## Next Steps

- **Gateway Quick Start:** See [deployment/QUICKSTART.md](./deployment/QUICKSTART.md)
- **Feature Flags:** See [FEATURE_FLAGS.md](./FEATURE_FLAGS.md)
- **Release Notes:** See [RELEASE_NOTES.md](./RELEASE_NOTES.md)

---

**Migration Guide Version:** 1.1.0
**Last Updated:** 2025
