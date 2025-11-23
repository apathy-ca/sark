# Disaster Recovery Guide

**Document Version**: 1.0
**Last Updated**: November 22, 2025
**Audience**: SRE Teams, Database Administrators, Infrastructure Teams

---

## Table of Contents

1. [Overview](#overview)
2. [Recovery Objectives](#recovery-objectives)
3. [Backup Strategy](#backup-strategy)
4. [Recovery Procedures](#recovery-procedures)
5. [Disaster Scenarios](#disaster-scenarios)
6. [Business Continuity](#business-continuity)
7. [Testing and Validation](#testing-and-validation)
8. [Emergency Contacts](#emergency-contacts)

---

## Overview

This guide defines disaster recovery (DR) procedures for SARK to ensure business continuity in the event of catastrophic failures.

### Disaster Recovery vs High Availability

| Aspect | High Availability (HA) | Disaster Recovery (DR) |
|--------|----------------------|----------------------|
| **Goal** | Prevent downtime | Recover from disaster |
| **Scope** | Component failures | Complete site/region loss |
| **RTO** | Seconds to minutes | Hours to days |
| **Cost** | Moderate (redundancy) | Higher (separate site) |
| **Examples** | Database replicas, multi-AZ | Cross-region backups, DR site |

### Disaster Types

1. **Infrastructure Failures**
   - Data center outage
   - Cloud region failure
   - Network partition
   - Power failure

2. **Data Failures**
   - Database corruption
   - Accidental data deletion
   - Ransomware attack
   - Storage system failure

3. **Application Failures**
   - Critical bug in production
   - Incompatible deployment
   - Configuration error
   - Dependency failure

4. **Natural Disasters**
   - Earthquake, flood, fire
   - Severe weather
   - Regional power grid failure

---

## Recovery Objectives

### Recovery Time Objective (RTO)

**RTO**: Maximum acceptable downtime

| Component | RTO Target | Maximum Acceptable |
|-----------|------------|-------------------|
| **API Service** | 1 hour | 4 hours |
| **Authentication** | 30 minutes | 2 hours |
| **Database (PostgreSQL)** | 2 hours | 6 hours |
| **Audit Database (TimescaleDB)** | 4 hours | 24 hours |
| **Redis Cache** | 30 minutes | 1 hour |
| **SIEM Integration** | 1 hour | 4 hours |

### Recovery Point Objective (RPO)

**RPO**: Maximum acceptable data loss

| Data Type | RPO Target | Backup Frequency |
|-----------|-----------|------------------|
| **User Data** | 15 minutes | Continuous (streaming replication) |
| **Server Registry** | 15 minutes | Continuous (streaming replication) |
| **Sessions** | Acceptable loss | N/A (ephemeral, stored in Redis) |
| **Policy Cache** | Acceptable loss | N/A (rebuilt from OPA) |
| **Audit Logs** | 5 minutes | Continuous + hourly snapshots |
| **Configuration** | 1 hour | Hourly snapshots |

### Service Level Objectives (SLO)

| Metric | Target | Disaster Recovery Impact |
|--------|--------|-------------------------|
| **Availability** | 99.9% (43 minutes downtime/month) | Allows 4-hour outage annually |
| **Data Durability** | 99.999999999% (11 nines) | Multi-region replication |
| **Mean Time to Recovery (MTTR)** | < 2 hours | Automated recovery where possible |

---

## Backup Strategy

### Backup Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Backup Strategy Overview                     │
└─────────────────────────────────────────────────────────────────┘

Production Site (Primary)                   DR Site (Secondary)
┌──────────────────────────┐               ┌─────────────────────┐
│  PostgreSQL Primary      │──Streaming───▶│  PostgreSQL Replica │
│  - Continuous WAL        │   Replication │  - Read-only        │
│  - Daily full backup     │               │  - Can be promoted  │
└──────────────────────────┘               └─────────────────────┘
           │                                         │
           │ Backup                                  │ Backup
           ▼                                         ▼
┌──────────────────────────┐               ┌─────────────────────┐
│  S3 / GCS / Azure Blob   │──Replicate───▶│  Secondary Region   │
│  - Full backups (daily)  │               │  - Geo-redundant    │
│  - WAL archives (cont.)  │               │  - Encrypted        │
│  - Retention: 30 days    │               │  - Retention: 90d   │
└──────────────────────────┘               └─────────────────────┘
           │
           │ Snapshot (weekly)
           ▼
┌──────────────────────────┐
│  Glacier / Archive       │
│  - Long-term retention   │
│  - Retention: 7 years    │
│  - Compliance            │
└──────────────────────────┘
```

### PostgreSQL Backups

#### Continuous Archiving (WAL Archiving)

**Enable WAL archiving** for point-in-time recovery (PITR):

```conf
# postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'aws s3 cp %p s3://sark-backups/wal/%f --region us-west-2'
# Or for GCP:
# archive_command = 'gsutil cp %p gs://sark-backups/wal/%f'
# Or for Azure:
# archive_command = 'az storage blob upload --account-name sarkbackups --container-name wal --file %p --name %f'

# Archive timeout (force WAL switch every 5 minutes)
archive_timeout = 300
```

**Verify WAL archiving**:
```bash
# Check archive status
kubectl exec -it postgres-0 -n production -- psql -U sark -c "
  SELECT
    archived_count,
    last_archived_wal,
    last_archived_time,
    failed_count,
    last_failed_wal
  FROM pg_stat_archiver;
"
```

#### Full Backups (Daily)

**Automated daily backups** using `pg_basebackup`:

```bash
#!/bin/bash
# backup-postgres.sh

BACKUP_DIR="/backups"
BACKUP_NAME="sark-$(date +%Y%m%d-%H%M)"
S3_BUCKET="s3://sark-backups/postgres"

# Create base backup
kubectl exec -it postgres-0 -n production -- \
  pg_basebackup -U replication -D ${BACKUP_DIR}/${BACKUP_NAME} -Ft -z -Xs -P

# Upload to S3
kubectl exec -it postgres-0 -n production -- \
  aws s3 cp ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz ${S3_BUCKET}/${BACKUP_NAME}.tar.gz

# Cleanup local backup (retain last 7 days locally)
kubectl exec -it postgres-0 -n production -- \
  find ${BACKUP_DIR} -name "sark-*.tar.gz" -mtime +7 -delete

# Verify backup
aws s3 ls ${S3_BUCKET}/${BACKUP_NAME}.tar.gz
```

**Schedule with CronJob** (Kubernetes):

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: production
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  successfulJobsHistoryLimit: 7
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: backup-sa
          containers:
          - name: backup
            image: postgres:14-alpine
            command:
            - /bin/sh
            - -c
            - |
              pg_basebackup -h postgres -U replication -D /backup/$(date +%Y%m%d) -Ft -z -Xs -P
              aws s3 sync /backup/ s3://sark-backups/postgres/
            env:
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-replication
                  key: password
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          restartPolicy: OnFailure
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
```

#### Logical Backups (pg_dump)

**Full database dump** (for point-in-time exports):

```bash
# Daily pg_dump
kubectl exec -it postgres-0 -n production -- \
  pg_dump -U sark -Fc sark > sark-$(date +%Y%m%d).dump

# Upload to S3
aws s3 cp sark-$(date +%Y%m%d).dump s3://sark-backups/dumps/

# Retention: 30 days
aws s3 ls s3://sark-backups/dumps/ | \
  awk '{if ($1 < "'$(date -d '30 days ago' +%Y-%m-%d)'") print $4}' | \
  xargs -I {} aws s3 rm s3://sark-backups/dumps/{}
```

#### Streaming Replication (HA + DR)

**Configure read replica** for high availability and disaster recovery:

**Primary (Master)**:
```conf
# postgresql.conf
wal_level = replica
max_wal_senders = 10
wal_keep_size = 1GB  # Keep 1GB of WAL for replicas
```

**Replica (Standby)**:
```conf
# postgresql.conf
hot_standby = on

# recovery.conf (PostgreSQL 12+: use standby.signal)
primary_conninfo = 'host=postgres-primary port=5432 user=replication password=xxx'
restore_command = 'aws s3 cp s3://sark-backups/wal/%f %p'
```

**Verify replication**:
```bash
# On primary
kubectl exec -it postgres-primary -n production -- psql -U sark -c "
  SELECT
    client_addr,
    state,
    sync_state,
    replay_lag
  FROM pg_stat_replication;
"

# On replica
kubectl exec -it postgres-replica -n production -- psql -U sark -c "
  SELECT pg_is_in_recovery();  -- Should return 't' (true)
"
```

### TimescaleDB Backups

**Same as PostgreSQL**, plus:

```bash
# Backup hypertable metadata
kubectl exec -it timescaledb-0 -n production -- psql -U sark -d sark_audit -c "
  SELECT timescaledb_pre_restore();
"

# Full backup
kubectl exec -it timescaledb-0 -n production -- \
  pg_dump -U sark -Fc sark_audit > sark-audit-$(date +%Y%m%d).dump

# Restore
kubectl exec -it timescaledb-0 -n production -- \
  pg_restore -U sark -d sark_audit -c sark-audit-20251122.dump

# Restore hypertable metadata
kubectl exec -it timescaledb-0 -n production -- psql -U sark -d sark_audit -c "
  SELECT timescaledb_post_restore();
"
```

### Redis Backups

**Redis persistence options**:

1. **RDB Snapshots** (point-in-time snapshots):
```conf
# redis.conf
save 900 1       # Save if >= 1 key changed in 900s
save 300 10      # Save if >= 10 keys changed in 300s
save 60 10000    # Save if >= 10000 keys changed in 60s

dbfilename dump.rdb
dir /data
```

2. **AOF** (Append-Only File - more durable):
```conf
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec  # Fsync every second
```

**Backup RDB/AOF**:
```bash
# Trigger manual snapshot
kubectl exec -it redis-0 -n production -- redis-cli BGSAVE

# Copy snapshot to S3
kubectl exec -it redis-0 -n production -- \
  aws s3 cp /data/dump.rdb s3://sark-backups/redis/dump-$(date +%Y%m%d).rdb
```

**Note**: For SARK, Redis is used as cache only (sessions, policy decisions). **No persistence recommended** for optimal performance. Sessions can be rebuilt on restart.

### Configuration Backups

**Backup Kubernetes manifests and Helm values**:

```bash
#!/bin/bash
# backup-config.sh

BACKUP_DIR="/backups/config"
DATE=$(date +%Y%m%d-%H%M)

# Create backup directory
mkdir -p ${BACKUP_DIR}/${DATE}

# Backup Helm values
helm get values sark -n production > ${BACKUP_DIR}/${DATE}/helm-values.yaml

# Backup Kubernetes resources
kubectl get all -n production -o yaml > ${BACKUP_DIR}/${DATE}/k8s-resources.yaml
kubectl get configmap -n production -o yaml > ${BACKUP_DIR}/${DATE}/configmaps.yaml
kubectl get secret -n production -o yaml > ${BACKUP_DIR}/${DATE}/secrets.yaml
kubectl get pvc -n production -o yaml > ${BACKUP_DIR}/${DATE}/pvcs.yaml
kubectl get ingress -n production -o yaml > ${BACKUP_DIR}/${DATE}/ingress.yaml

# Upload to S3
tar -czf ${BACKUP_DIR}/${DATE}.tar.gz -C ${BACKUP_DIR} ${DATE}
aws s3 cp ${BACKUP_DIR}/${DATE}.tar.gz s3://sark-backups/config/

# Cleanup
rm -rf ${BACKUP_DIR}/${DATE}
```

**Schedule hourly**:
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: config-backup
spec:
  schedule: "0 * * * *"  # Hourly
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: bitnami/kubectl:latest
            command: ["/bin/bash", "/scripts/backup-config.sh"]
```

### Backup Retention

| Backup Type | Frequency | Local Retention | Cloud Retention | Archive Retention |
|-------------|-----------|-----------------|-----------------|-------------------|
| **WAL Archives** | Continuous | 7 days | 30 days | N/A |
| **Full Backups** | Daily | 7 days | 30 days | 7 years (monthly) |
| **Logical Dumps** | Daily | 3 days | 30 days | 1 year (weekly) |
| **Config Backups** | Hourly | 1 day | 90 days | 1 year (monthly) |
| **Redis Snapshots** | N/A (disabled) | N/A | N/A | N/A |

### Backup Monitoring

**Monitor backup success**:

```bash
# Check last successful backup
aws s3 ls s3://sark-backups/postgres/ --recursive | sort | tail -n 1

# Verify backup age (should be < 24 hours)
LAST_BACKUP=$(aws s3 ls s3://sark-backups/postgres/ --recursive | sort | tail -n 1 | awk '{print $1" "$2}')
BACKUP_AGE_HOURS=$(( ($(date +%s) - $(date -d "${LAST_BACKUP}" +%s)) / 3600 ))

if [ ${BACKUP_AGE_HOURS} -gt 24 ]; then
  echo "ALERT: Last backup is ${BACKUP_AGE_HOURS} hours old!"
  # Send alert to PagerDuty
fi
```

**Prometheus metrics**:
```yaml
# Alert: Backup age > 25 hours
- alert: BackupTooOld
  expr: time() - backup_last_success_timestamp_seconds > 90000
  for: 1h
  labels:
    severity: critical
  annotations:
    summary: "Database backup too old"
    description: "Last successful backup was {{ $value | humanizeDuration }} ago"
```

---

## Recovery Procedures

### Database Recovery (PostgreSQL)

#### Scenario 1: Point-in-Time Recovery (PITR)

**Recover to specific timestamp** (e.g., before accidental data deletion):

```bash
# 1. Stop database
kubectl scale statefulset postgres --replicas=0 -n production

# 2. Download base backup
aws s3 cp s3://sark-backups/postgres/sark-20251122.tar.gz /restore/
tar -xzf /restore/sark-20251122.tar.gz -C /var/lib/postgresql/data

# 3. Download WAL archives
aws s3 sync s3://sark-backups/wal/ /var/lib/postgresql/wal_archive/

# 4. Create recovery configuration
cat > /var/lib/postgresql/data/recovery.signal << EOF
EOF

cat > /var/lib/postgresql/data/postgresql.auto.conf << EOF
restore_command = 'cp /var/lib/postgresql/wal_archive/%f %p'
recovery_target_time = '2025-11-22 10:00:00'  # Timestamp before incident
recovery_target_action = 'promote'
EOF

# 5. Start database
kubectl scale statefulset postgres --replicas=1 -n production

# 6. Monitor recovery
kubectl logs postgres-0 -n production --follow

# Database will:
# 1. Apply base backup
# 2. Replay WAL archives up to target time
# 3. Promote to primary
# 4. Accept connections

# 7. Verify recovery
kubectl exec -it postgres-0 -n production -- psql -U sark -c "
  SELECT NOW(), pg_is_in_recovery();
"
```

**Recovery Time**: 1-4 hours (depends on WAL size)

#### Scenario 2: Full Database Restore

**Restore from full backup** (e.g., complete database loss):

```bash
# 1. Stop database
kubectl scale statefulset postgres --replicas=0 -n production

# 2. Delete old data
kubectl exec -it postgres-0 -n production -- rm -rf /var/lib/postgresql/data/*

# 3. Restore from backup
# Option A: Restore from pg_basebackup
aws s3 cp s3://sark-backups/postgres/sark-20251122.tar.gz /tmp/
kubectl cp /tmp/sark-20251122.tar.gz postgres-0:/tmp/ -n production
kubectl exec -it postgres-0 -n production -- \
  tar -xzf /tmp/sark-20251122.tar.gz -C /var/lib/postgresql/data

# Option B: Restore from pg_dump
aws s3 cp s3://sark-backups/dumps/sark-20251122.dump /tmp/
kubectl cp /tmp/sark-20251122.dump postgres-0:/tmp/ -n production

# Start database
kubectl scale statefulset postgres --replicas=1 -n production

# Wait for database to start
kubectl wait --for=condition=ready pod/postgres-0 -n production --timeout=5m

# Restore dump
kubectl exec -it postgres-0 -n production -- \
  pg_restore -U sark -d sark -c /tmp/sark-20251122.dump

# 4. Verify restore
kubectl exec -it postgres-0 -n production -- psql -U sark -c "
  SELECT schemaname, tablename, n_live_tup
  FROM pg_stat_user_tables
  ORDER BY n_live_tup DESC;
"
```

**Recovery Time**: 2-6 hours (depends on database size)

#### Scenario 3: Promote Read Replica

**Fastest recovery** (replica already has data):

```bash
# 1. Stop traffic to primary
kubectl scale deployment sark --replicas=0 -n production

# 2. Promote replica to primary
kubectl exec -it postgres-replica -n production -- \
  pg_ctl promote -D /var/lib/postgresql/data

# 3. Verify promotion
kubectl exec -it postgres-replica -n production -- psql -U sark -c "
  SELECT pg_is_in_recovery();  -- Should return 'f' (false)
"

# 4. Update application to point to new primary
kubectl set env deployment/sark \
  DATABASE_URL=postgresql://sark:password@postgres-replica:5432/sark \
  -n production

# 5. Start application
kubectl scale deployment sark --replicas=4 -n production

# 6. Verify recovery
kubectl logs deployment/sark -n production --tail=50
curl https://api.example.com/health
```

**Recovery Time**: 5-15 minutes

### Application Recovery

#### Scenario 1: Rollback Deployment

**See [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md#rollback-procedures)**

```bash
# Fastest: Helm rollback
helm rollback sark -n production

# Or kubectl rollback
kubectl rollout undo deployment/sark -n production
```

**Recovery Time**: 1-3 minutes

#### Scenario 2: Rebuild from Scratch

**Complete cluster failure** (rebuild everything):

```bash
# 1. Create new Kubernetes cluster
eksctl create cluster --name sark-dr --region us-east-1

# 2. Restore configuration
aws s3 cp s3://sark-backups/config/config-20251122.tar.gz /tmp/
tar -xzf /tmp/config-20251122.tar.gz

# 3. Restore secrets
kubectl apply -f config/secrets.yaml -n production

# 4. Restore database (see Database Recovery above)

# 5. Deploy application
helm install sark ./helm/sark \
  -f config/helm-values.yaml \
  --namespace production \
  --create-namespace

# 6. Update DNS (point to new cluster)
# AWS Route 53:
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch file://dns-change.json

# 7. Verify recovery
curl https://api.example.com/health
```

**Recovery Time**: 4-8 hours

### Redis Recovery

**Redis is ephemeral cache** - no recovery needed. Cache rebuilds automatically:

- **Sessions**: Users re-authenticate
- **Policy decisions**: Rebuilt on first policy evaluation
- **Rate limits**: Reset to 0 (acceptable)

**If persistence was enabled**:
```bash
# Restore RDB snapshot
aws s3 cp s3://sark-backups/redis/dump-20251122.rdb /tmp/
kubectl cp /tmp/dump-20251122.rdb redis-0:/data/dump.rdb -n production

# Restart Redis
kubectl delete pod redis-0 -n production
```

---

## Disaster Scenarios

### Scenario 1: Complete Data Center Outage

**Incident**: Primary data center loses power, complete outage

**Impact**:
- API unavailable
- Database unavailable
- All services down

**Recovery Steps**:

**Option A: Wait for Data Center Recovery** (if expected < 4 hours)
1. Monitor data center status
2. Services auto-recover when power restored
3. **ETA**: 1-4 hours

**Option B: Failover to DR Site** (if outage > 4 hours)
1. **Promote DR database replica to primary** (15 minutes)
   ```bash
   pg_ctl promote -D /var/lib/postgresql/data
   ```

2. **Update DNS to point to DR site** (15 minutes)
   ```bash
   aws route53 change-resource-record-sets --hosted-zone-id Z123 \
     --change-batch '{
       "Changes": [{
         "Action": "UPSERT",
         "ResourceRecordSet": {
           "Name": "api.example.com",
           "Type": "A",
           "AliasTarget": {
             "HostedZoneId": "Z456",
             "DNSName": "dr-lb.us-east-1.elb.amazonaws.com",
             "EvaluateTargetHealth": true
           }
         }
       }]
     }'
   ```

3. **Scale up DR application pods** (5 minutes)
   ```bash
   kubectl scale deployment sark --replicas=4 -n production
   ```

4. **Verify service restored** (5 minutes)
   ```bash
   curl https://api.example.com/health
   ```

**Total Recovery Time**: 30-45 minutes
**Data Loss**: < 1 minute (replication lag)

### Scenario 2: Ransomware Attack

**Incident**: Database encrypted by ransomware, data inaccessible

**Impact**:
- Data encrypted
- Possible data exfiltration
- Service outage

**Recovery Steps**:

1. **Isolate infected systems** (immediate)
   ```bash
   # Block all traffic
   kubectl scale deployment sark --replicas=0 -n production

   # Network isolation
   kubectl apply -f network-policy-deny-all.yaml
   ```

2. **Assess damage** (30 minutes)
   - Identify encrypted data
   - Determine last clean backup
   - Check for data exfiltration

3. **Restore from clean backup** (2-4 hours)
   ```bash
   # Restore from backup before encryption
   # Use PITR to timestamp before attack
   recovery_target_time = '2025-11-22 09:00:00'  # Before attack
   ```

4. **Security hardening** (1 hour)
   - Rotate all secrets
   - Patch vulnerabilities
   - Enable additional monitoring

5. **Gradual service restoration** (30 minutes)
   - Deploy to DR environment first
   - Full security scan
   - Gradual user rollout

**Total Recovery Time**: 4-6 hours
**Data Loss**: Minutes to hours (depends on backup)

### Scenario 3: Accidental Data Deletion

**Incident**: Administrator accidentally deletes production database table

**Impact**:
- Data loss (user data, server registry, etc.)
- Service degradation (missing data)

**Recovery Steps**:

1. **Immediate action** (< 5 minutes)
   ```bash
   # Stop application to prevent further writes
   kubectl scale deployment sark --replicas=0 -n production
   ```

2. **Identify deletion time** (5 minutes)
   ```sql
   -- Check audit logs
   SELECT * FROM audit_events
   WHERE event_type = 'table_truncate' OR event_type = 'table_drop'
   ORDER BY time DESC
   LIMIT 10;
   ```

3. **Point-in-time recovery** (1-3 hours)
   ```bash
   # Restore to 5 minutes before deletion
   recovery_target_time = '2025-11-22 14:55:00'
   ```

4. **Verify data restored** (15 minutes)
   ```sql
   SELECT COUNT(*) FROM users;
   SELECT COUNT(*) FROM servers;
   ```

5. **Resume service** (5 minutes)
   ```bash
   kubectl scale deployment sark --replicas=4 -n production
   ```

**Total Recovery Time**: 1.5-3.5 hours
**Data Loss**: 0-5 minutes (PITR accuracy)

---

## Business Continuity

### Multi-Region Architecture

**For maximum availability**, deploy to multiple regions:

```
Primary Region (us-west-2)          DR Region (us-east-1)
┌─────────────────────────┐        ┌──────────────────────┐
│  EKS Cluster            │        │  EKS Cluster (cold)  │
│  ├── API (4 pods)       │        │  ├── API (0 pods)    │
│  ├── PostgreSQL Primary │◀──────▶│  ├── PostgreSQL Read │
│  ├── Redis Master       │ Repl.  │  ├── Redis Replica   │
│  └── OPA                │        │  └── OPA             │
└─────────────────────────┘        └──────────────────────┘
           │                                  ▲
           │ DNS (Route 53)                  │
           ▼                                  │
      ┌────────────────┐                     │
      │  api.example   │─────────────────────┘
      │  .com          │  Failover (manual or auto)
      └────────────────┘
```

**Benefits**:
- Regional failure tolerance
- Near-zero RPO (streaming replication)
- Fast failover (< 1 hour RTO)

**Cost**: 2× infrastructure cost

### Cold vs Warm vs Hot DR

| Type | Description | RTO | Cost | Use Case |
|------|-------------|-----|------|----------|
| **Cold** | Backups only, no infrastructure | 4-8 hours | Low (storage only) | Cost-sensitive, high RTO acceptable |
| **Warm** | Infrastructure ready, scaled to 0 | 1-2 hours | Medium (infra, no compute) | Balanced cost/RTO |
| **Hot** | Fully running DR site | 5-30 min | High (2× cost) | Mission-critical, low RTO |

**Recommendation for SARK**: **Warm DR**
- Keep DR infrastructure running (Kubernetes cluster, databases)
- Scale application to 0 replicas (no compute cost)
- Database replica continuously replicating (near-zero RPO)
- Fast failover: Just scale up application (15 minutes)

### Maintenance Windows

**Scheduled maintenance** for low-impact operations:

| Day | Window | Operations |
|-----|--------|------------|
| **Sunday** | 2 AM - 4 AM | Database maintenance (VACUUM, REINDEX) |
| **Tuesday** | 2 AM - 4 AM | Application deployments |
| **Thursday** | 2 AM - 4 AM | Security patches |
| **Saturday** | 2 AM - 4 AM | DR testing |

**Communication**:
- Notify users 48 hours in advance
- Update status page (status.example.com)
- Send email to stakeholders

---

## Testing and Validation

### DR Test Schedule

| Test Type | Frequency | Duration | Scope |
|-----------|-----------|----------|-------|
| **Backup Restore Test** | Monthly | 2 hours | Restore backup to non-prod |
| **Failover Test** | Quarterly | 4 hours | Failover to DR site |
| **Full DR Drill** | Annually | 8 hours | Complete disaster simulation |
| **Chaos Engineering** | Monthly | 1 hour | Random component failures |

### Backup Restore Test

**Monthly validation** that backups are restorable:

```bash
#!/bin/bash
# dr-test-monthly.sh

# 1. Download latest backup
aws s3 cp s3://sark-backups/postgres/latest.tar.gz /tmp/

# 2. Create test database
kubectl run postgres-test --image=postgres:14 -n test

# 3. Restore backup
kubectl cp /tmp/latest.tar.gz postgres-test:/tmp/ -n test
kubectl exec -it postgres-test -n test -- \
  tar -xzf /tmp/latest.tar.gz -C /var/lib/postgresql/data

# 4. Start database
kubectl exec -it postgres-test -n test -- \
  pg_ctl start -D /var/lib/postgresql/data

# 5. Verify data
kubectl exec -it postgres-test -n test -- psql -U sark -c "
  SELECT COUNT(*) FROM users;
  SELECT COUNT(*) FROM servers;
"

# 6. Cleanup
kubectl delete pod postgres-test -n test

# 7. Report results
echo "Backup restore test: PASSED" | mail -s "DR Test Results" ops@example.com
```

### Failover Test

**Quarterly test** of complete failover to DR site:

```bash
#!/bin/bash
# dr-test-quarterly.sh

echo "=== DR Failover Test ===" | tee -a dr-test.log

# 1. Simulate primary site failure
echo "1. Simulating primary site failure..." | tee -a dr-test.log
kubectl scale deployment sark --replicas=0 -n production --context=us-west-2

# 2. Promote DR database
echo "2. Promoting DR database..." | tee -a dr-test.log
kubectl exec -it postgres-replica -n production --context=us-east-1 -- \
  pg_ctl promote -D /var/lib/postgresql/data

# 3. Scale up DR application
echo "3. Scaling up DR application..." | tee -a dr-test.log
kubectl scale deployment sark --replicas=4 -n production --context=us-east-1

# 4. Update DNS (test subdomain)
echo "4. Updating DNS..." | tee -a dr-test.log
aws route53 change-resource-record-sets --hosted-zone-id Z123 \
  --change-batch file://dns-change-dr-test.json

# 5. Verify service
echo "5. Verifying service..." | tee -a dr-test.log
sleep 60  # Wait for DNS propagation
curl https://dr-test.example.com/health | tee -a dr-test.log

# 6. Run smoke tests
echo "6. Running smoke tests..." | tee -a dr-test.log
./scripts/smoke-test.sh https://dr-test.example.com

# 7. Rollback (restore primary)
echo "7. Rolling back to primary..." | tee -a dr-test.log
kubectl scale deployment sark --replicas=4 -n production --context=us-west-2
kubectl scale deployment sark --replicas=0 -n production --context=us-east-1

# 8. Report results
echo "=== DR Test Complete ===" | tee -a dr-test.log
cat dr-test.log | mail -s "DR Failover Test Results" ops@example.com
```

### Chaos Engineering

**Monthly chaos tests** using Chaos Mesh or Gremlin:

```yaml
# chaos-pod-kill.yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: pod-kill-test
  namespace: production
spec:
  action: pod-kill
  mode: one
  selector:
    namespaces:
      - production
    labelSelectors:
      app: sark
  scheduler:
    cron: "@every 1h"  # Kill random pod every hour
```

**Verify**:
- Application auto-recovers
- No user impact
- Alerts fired correctly
- On-call notified

---

## Emergency Contacts

### Escalation Matrix

| Level | Role | Contact | Response Time |
|-------|------|---------|---------------|
| **L1** | On-Call Engineer | PagerDuty | 15 minutes |
| **L2** | Engineering Lead | phone, Slack | 30 minutes |
| **L3** | CTO | phone | 1 hour |
| **DB** | Database Admin | dba@example.com | 30 minutes |
| **Sec** | Security Team | security@example.com | 15 minutes (security incidents) |
| **Vendor** | Cloud Provider Support | AWS/GCP/Azure Support | 1 hour (Premium Support) |

### Communication Channels

- **PagerDuty**: Automated on-call alerting
- **Slack**: #incidents channel
- **Email**: incidents@example.com
- **Status Page**: https://status.example.com
- **Conference Bridge**: +1-555-123-4567 (PIN: 1234#)

### Vendor Support

**Cloud Providers**:
- **AWS**: Premium Support - 15 minute response for P1 issues
- **GCP**: Enterprise Support - 15 minute response for P1 issues
- **Azure**: Premier Support - 15 minute response for Severity A issues

**Database Vendors**:
- **PostgreSQL**: Community support (forums, mailing lists)
- **TimescaleDB**: Cloud support (if using Timescale Cloud)
- **Redis**: Redis Enterprise support (if using Redis Enterprise)

---

## Summary

This guide provides comprehensive disaster recovery procedures:

- **Recovery Objectives**: RTO 1-4 hours, RPO 5-15 minutes
- **Backup Strategy**: Continuous WAL archiving, daily full backups, multi-region replication
- **Recovery Procedures**: PITR, full restore, replica promotion, complete rebuild
- **Disaster Scenarios**: Data center outage, ransomware, accidental deletion
- **Business Continuity**: Multi-region architecture, warm DR site
- **Testing**: Monthly backup tests, quarterly failover tests, annual DR drills

Following these procedures ensures SARK can recover from any disaster with minimal data loss and downtime.
