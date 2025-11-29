# SARK v1.x to v2.0 Migration Runbook

**Version:** 2.0.0
**Last Updated:** 2024-12-02
**Owner:** Database Engineering Team (ENGINEER-6)

## Table of Contents

1. [Overview](#overview)
2. [Pre-Migration Checklist](#pre-migration-checklist)
3. [Migration Phases](#migration-phases)
4. [Rollback Procedures](#rollback-procedures)
5. [Validation & Verification](#validation--verification)
6. [Troubleshooting Guide](#troubleshooting-guide)
7. [Performance Optimization](#performance-optimization)
8. [Post-Migration Tasks](#post-migration-tasks)

---

## Overview

### What This Migration Does

The SARK v2.0 migration transforms the database schema from protocol-specific (MCP-only) to protocol-agnostic (MCP, HTTP, gRPC, GraphQL, etc.). Key changes:

- **v1.x Schema:** `mcp_servers` + `mcp_tools` (MCP-specific)
- **v2.0 Schema:** `resources` + `capabilities` (protocol-agnostic)

### Migration Strategy

- **Zero-downtime capable:** v1.x and v2.0 tables coexist during migration
- **Data preservation:** All v1.x data is migrated to v2.0 with full fidelity
- **Rollback-safe:** Migration can be rolled back without data loss
- **Performance-optimized:** Polymorphic queries use GIN indexes and partial indexes

### Estimated Timeline

| Database Size | Migration Time | Validation Time | Total Downtime |
|--------------|----------------|-----------------|----------------|
| < 1K servers | 1-2 minutes    | 1 minute        | 0 minutes*     |
| 1K-10K servers | 5-10 minutes | 2-3 minutes     | 0 minutes*     |
| 10K-100K servers | 20-30 minutes | 5-10 minutes  | 0 minutes*     |
| > 100K servers | 1-2 hours    | 10-20 minutes   | 0 minutes*     |

*Zero downtime achievable with proper application deployment strategy (see below)

---

## Pre-Migration Checklist

### 1. Backup Database

```bash
# Create full database backup
pg_dump -h localhost -U sark -d sark -F c -f "sark_backup_$(date +%Y%m%d_%H%M%S).dump"

# Verify backup
pg_restore --list sark_backup_*.dump | head -20

# Store backup in secure location
aws s3 cp sark_backup_*.dump s3://sark-backups/pre-v2-migration/
```

### 2. Verify Database Health

```bash
# Check database size
psql -h localhost -U sark -d sark -c "
  SELECT pg_size_pretty(pg_database_size('sark')) as db_size;
"

# Check table sizes
psql -h localhost -U sark -d sark -c "
  SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
  FROM pg_tables
  WHERE schemaname = 'public'
  ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
  LIMIT 10;
"

# Check for active connections
psql -h localhost -U sark -d sark -c "
  SELECT count(*) as active_connections
  FROM pg_stat_activity
  WHERE datname = 'sark' AND state = 'active';
"
```

### 3. Verify Current Data Counts

```bash
# Run pre-migration data count
python scripts/migrate_v1_to_v2.py --dry-run > pre_migration_report.txt

# Save counts for later comparison
psql -h localhost -U sark -d sark -c "
  SELECT 'mcp_servers' as table_name, COUNT(*) as row_count FROM mcp_servers
  UNION ALL
  SELECT 'mcp_tools', COUNT(*) FROM mcp_tools;
" > pre_migration_counts.txt
```

### 4. Check Application Compatibility

- [ ] SARK application is at version >= 2.0.0
- [ ] Protocol adapters are installed (HTTP, gRPC)
- [ ] Feature flags are configured: `FEATURE_PROTOCOL_ADAPTERS=true`
- [ ] API clients are compatible with v2.0 endpoints

### 5. Schedule Migration Window

- [ ] Notify stakeholders of migration window
- [ ] Schedule during low-traffic period (if possible)
- [ ] Ensure on-call engineer is available
- [ ] Prepare rollback plan

---

## Migration Phases

### Phase 1: Schema Migration (Alembic)

**Duration:** 2-5 minutes
**Downtime:** None (tables created without data)

```bash
# Navigate to SARK directory
cd /path/to/sark

# Run Alembic migrations
alembic upgrade head

# Expected output:
# INFO  [alembic.runtime.migration] Running upgrade 005 -> 006, Add protocol adapter support
# INFO  [alembic.runtime.migration] Running upgrade 006 -> 007, Add federation support

# Verify migrations applied
alembic current
# Should show: 007 (head)
```

**What This Does:**
- Creates `resources`, `capabilities`, `federation_nodes`, `cost_tracking`, `principal_budgets` tables
- Creates indexes (GIN, B-tree, partial)
- Adds federation columns to `audit_events`
- Auto-migrates existing MCP data to v2.0 tables (basic migration)

**Validation:**

```bash
# Verify tables exist
psql -h localhost -U sark -d sark -c "\dt+ resources capabilities"

# Verify indexes created
psql -h localhost -U sark -d sark -c "\di+ ix_resources_*"

# Check auto-migrated data
psql -h localhost -U sark -d sark -c "
  SELECT COUNT(*) as migrated_resources FROM resources WHERE protocol = 'mcp';
"
```

### Phase 2: Data Migration (Comprehensive)

**Duration:** 5-60 minutes (depending on data size)
**Downtime:** None (reads continue on v1.x tables)

```bash
# DRY RUN: Preview migration
python scripts/migrate_v1_to_v2.py --dry-run

# Review output carefully:
# - Check server/tool counts
# - Verify no errors in dry run
# - Confirm migration plan

# EXECUTE: Run actual migration
python scripts/migrate_v1_to_v2.py --execute

# Monitor progress in logs
# Expected output:
# INFO - ✓ Prerequisites validated
# INFO - Current state: v1.x: 1234 servers, 5678 tools
# INFO - === EXECUTING MIGRATION ===
# INFO - ✓ Migrated 1234 MCP servers to resources
# INFO - ✓ Migrated 5678 MCP tools to capabilities
# INFO - ✓ All v1.x servers have v2.0 resources
# INFO - ✓ All v1.x tools have v2.0 capabilities
# INFO - ✓ Foreign key integrity validated
# INFO - ✓ Migration completed successfully
```

**What This Does:**
- Migrates `mcp_servers` → `resources` with full metadata preservation
- Migrates `mcp_tools` → `capabilities` with schema mapping
- Uses `ON CONFLICT DO UPDATE` for idempotency (can be re-run safely)
- Validates foreign key relationships
- Preserves all v1.x data in metadata JSONB fields

**Monitoring:**

```bash
# Monitor migration progress in separate terminal
watch -n 5 'psql -h localhost -U sark -d sark -c "
  SELECT
    (SELECT COUNT(*) FROM resources WHERE protocol = '\''mcp'\'') as migrated_resources,
    (SELECT COUNT(*) FROM capabilities) as migrated_capabilities,
    (SELECT COUNT(*) FROM mcp_servers) as source_servers,
    (SELECT COUNT(*) FROM mcp_tools) as source_tools;
"'
```

### Phase 3: Validation

**Duration:** 2-10 minutes
**Downtime:** None

```bash
# Run comprehensive validation
python scripts/validate_migration.py --full --output validation_report.json

# Expected output:
# ✓ Schema validation: All tables and indexes present
# ✓ Data counts: Servers and tools match between v1.x and v2.0
# ✓ Foreign keys: No orphaned capabilities
# ✓ Metadata: All JSONB fields populated
# STATUS: ✅ VALIDATION PASSED

# If validation fails, review report
cat validation_report.json | jq '.issues[] | select(.severity == "error")'
```

**Manual Spot Checks:**

```sql
-- Check a sample resource migration
SELECT
  s.id as v1_id,
  s.name as v1_name,
  r.id as v2_id,
  r.name as v2_name,
  r.protocol,
  r.metadata
FROM mcp_servers s
LEFT JOIN resources r ON r.id = s.id::text
LIMIT 5;

-- Check capability migration
SELECT
  t.id as v1_id,
  t.name as v1_name,
  c.id as v2_id,
  c.name as v2_name,
  c.resource_id,
  c.input_schema
FROM mcp_tools t
LEFT JOIN capabilities c ON c.id = t.id::text
LIMIT 5;

-- Verify no orphaned capabilities
SELECT COUNT(*) as orphaned_count
FROM capabilities c
WHERE NOT EXISTS (SELECT 1 FROM resources r WHERE r.id = c.resource_id);
-- Should return 0
```

### Phase 4: Application Cutover

**Duration:** 5-10 minutes
**Downtime:** None (with proper deployment)

#### Option A: Blue-Green Deployment (Recommended)

```bash
# Deploy v2.0-compatible application to new environment
# Gradually shift traffic: 0% → 10% → 50% → 100%

# 1. Deploy v2.0 application
kubectl apply -f k8s/sark-v2-deployment.yaml

# 2. Route 10% traffic to v2.0
kubectl patch service sark -p '{"spec":{"selector":{"version":"v2"}}}'
# Monitor for 15 minutes

# 3. Route 50% traffic
# Monitor for 30 minutes

# 4. Route 100% traffic
# Monitor for 1 hour

# 5. Decommission v1.x pods
kubectl delete deployment sark-v1
```

#### Option B: Rolling Update

```bash
# Update application in-place
kubectl set image deployment/sark sark=sark:2.0.0

# Monitor rollout
kubectl rollout status deployment/sark

# Verify pods are healthy
kubectl get pods -l app=sark
```

### Phase 5: Performance Optimization

**Duration:** 10-20 minutes
**Downtime:** None (CONCURRENTLY indexes)

```bash
# Run query optimization analysis
python scripts/optimize_polymorphic_queries.py --report --output optimization_report.txt

# Review recommendations
cat optimization_report.txt

# Apply optimizations (creates additional indexes)
python scripts/optimize_polymorphic_queries.py --optimize

# Monitor index creation (may take 10-20 minutes for large tables)
psql -h localhost -U sark -d sark -c "
  SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
  FROM pg_indexes
  WHERE schemaname = 'public'
  ORDER BY pg_relation_size(indexname::regclass) DESC;
"
```

---

## Rollback Procedures

### Scenario 1: Pre-Application Cutover Rollback

**If migration completed but application not yet deployed:**

```bash
# Rollback is simple: just don't deploy v2.0 application
# v1.x tables are still intact and application continues using them

# Optional: Clean up v2.0 tables to free space
python scripts/migrate_v1_to_v2.py --rollback

# Rollback Alembic migrations
alembic downgrade 005
```

### Scenario 2: Post-Application Cutover Rollback

**If v2.0 application is deployed and issues arise:**

```bash
# IMMEDIATE: Rollback application deployment
kubectl rollout undo deployment/sark

# OR: Switch traffic back to v1.x (blue-green)
kubectl patch service sark -p '{"spec":{"selector":{"version":"v1"}}}'

# Verify application is using v1.x tables
curl http://sark.example.com/health | jq '.database_version'
# Should return: "1.x"

# NOTE: v2.0 data created during cutover period will be lost
# If preservation needed, contact database team for manual reconciliation
```

### Scenario 3: Data Corruption Detected

**If data integrity issues found:**

```bash
# 1. IMMEDIATE: Stop all writes
kubectl scale deployment sark --replicas=0

# 2. Restore from backup
pg_restore -h localhost -U sark -d sark -c sark_backup_<timestamp>.dump

# 3. Verify restoration
psql -h localhost -U sark -d sark -c "SELECT COUNT(*) FROM mcp_servers;"

# 4. Investigate root cause before retrying migration
# Review logs: /var/log/sark/migration.log
# Check validation report: validation_report.json

# 5. Resume operations on v1.x
kubectl scale deployment sark --replicas=3
```

---

## Validation & Verification

### Automated Validation

```bash
# Quick validation (2 minutes)
python scripts/validate_migration.py --quick

# Full validation (5-10 minutes)
python scripts/validate_migration.py --full

# Schema-only validation
python scripts/validate_migration.py --schema

# Data-only validation
python scripts/validate_migration.py --data

# Relationship validation
python scripts/validate_migration.py --relationships
```

### Manual Verification Queries

```sql
-- 1. Count verification
SELECT
  'v1.x servers' as metric, COUNT(*)::text as value FROM mcp_servers
UNION ALL
SELECT 'v1.x tools', COUNT(*)::text FROM mcp_tools
UNION ALL
SELECT 'v2.0 MCP resources', COUNT(*)::text FROM resources WHERE protocol = 'mcp'
UNION ALL
SELECT 'v2.0 MCP capabilities', COUNT(*)::text
FROM capabilities c JOIN resources r ON r.id = c.resource_id WHERE r.protocol = 'mcp';

-- 2. Sample data comparison
SELECT
  'v1.x' as version,
  id::text,
  name,
  command as endpoint,
  NULL as metadata
FROM mcp_servers
LIMIT 3

UNION ALL

SELECT
  'v2.0' as version,
  id,
  name,
  endpoint,
  metadata::text
FROM resources
WHERE protocol = 'mcp'
LIMIT 3;

-- 3. Orphaned data check
SELECT
  'Orphaned capabilities' as issue,
  COUNT(*)::text as count
FROM capabilities c
WHERE NOT EXISTS (SELECT 1 FROM resources r WHERE r.id = c.resource_id)

UNION ALL

SELECT
  'Null resource names',
  COUNT(*)::text
FROM resources
WHERE name IS NULL;

-- 4. Protocol distribution
SELECT
  protocol,
  COUNT(*) as resource_count,
  COUNT(DISTINCT c.id) as capability_count
FROM resources r
LEFT JOIN capabilities c ON c.resource_id = r.id
GROUP BY protocol
ORDER BY resource_count DESC;
```

### Health Checks

```bash
# Application health
curl http://sark.example.com/health
# Expected: {"status": "healthy", "database_version": "2.0", "database": "connected"}

# Database connectivity
psql -h localhost -U sark -d sark -c "SELECT version();"

# Query performance check
python scripts/optimize_polymorphic_queries.py --benchmark

# Audit log verification
psql -h localhost -U sark -d sark -c "
  SELECT
    event_type,
    COUNT(*) as event_count
  FROM audit_events
  WHERE timestamp >= NOW() - INTERVAL '1 hour'
  GROUP BY event_type
  ORDER BY event_count DESC;
"
```

---

## Troubleshooting Guide

### Issue: Migration Script Fails with "Table Already Exists"

**Symptom:**
```
ERROR: relation "resources" already exists
```

**Cause:** Alembic migrations already run (Phase 1 complete)

**Solution:**
```bash
# This is expected if re-running migration
# Skip to Phase 2 (data migration)
python scripts/migrate_v1_to_v2.py --execute
```

---

### Issue: Count Mismatch Between v1.x and v2.0

**Symptom:**
```
ERROR: Server count mismatch: 1234 v1.x servers != 1200 v2.0 MCP resources
```

**Cause:** Migration incomplete or data written during migration

**Solution:**
```bash
# Re-run migration (idempotent with ON CONFLICT)
python scripts/migrate_v1_to_v2.py --execute

# Investigate discrepancy
psql -h localhost -U sark -d sark -c "
  SELECT s.id, s.name
  FROM mcp_servers s
  WHERE NOT EXISTS (SELECT 1 FROM resources r WHERE r.id = s.id::text)
  LIMIT 10;
"

# Manually migrate missing records if needed
# Contact database team if issue persists
```

---

### Issue: Orphaned Capabilities Detected

**Symptom:**
```
ERROR: Found 42 capabilities with broken resource_id foreign keys
```

**Cause:** Data inconsistency or race condition during migration

**Solution:**
```sql
-- Identify orphaned capabilities
SELECT c.id, c.name, c.resource_id
FROM capabilities c
WHERE NOT EXISTS (SELECT 1 FROM resources r WHERE r.id = c.resource_id)
LIMIT 10;

-- Check if resources exist in v1.x
SELECT t.id, t.server_id, s.name
FROM mcp_tools t
LEFT JOIN mcp_servers s ON s.id = t.server_id
WHERE t.id::text IN (
  SELECT c.id FROM capabilities c
  WHERE NOT EXISTS (SELECT 1 FROM resources r WHERE r.id = c.resource_id)
)
LIMIT 10;

-- Re-run migration to fix
python scripts/migrate_v1_to_v2.py --execute
```

---

### Issue: Slow Query Performance After Migration

**Symptom:**
```
Queries taking 5-10x longer than before migration
```

**Cause:** Missing indexes or outdated statistics

**Solution:**
```bash
# Update table statistics
psql -h localhost -U sark -d sark -c "ANALYZE resources; ANALYZE capabilities;"

# Check index usage
python scripts/optimize_polymorphic_queries.py --benchmark

# Apply additional indexes
python scripts/optimize_polymorphic_queries.py --optimize

# Verify improvement
python scripts/optimize_polymorphic_queries.py --benchmark
```

---

### Issue: Application Errors After Cutover

**Symptom:**
```
HTTP 500 errors, "column 'server_id' does not exist"
```

**Cause:** Application still using v1.x table names

**Solution:**
```bash
# Verify application version
kubectl get deployment sark -o jsonpath='{.spec.template.spec.containers[0].image}'
# Should be: sark:2.0.0 or higher

# Check feature flags
kubectl exec -it deployment/sark -- env | grep FEATURE_PROTOCOL_ADAPTERS
# Should be: FEATURE_PROTOCOL_ADAPTERS=true

# If incorrect, update deployment
kubectl set env deployment/sark FEATURE_PROTOCOL_ADAPTERS=true

# Restart pods
kubectl rollout restart deployment/sark
```

---

### Issue: Rollback Required

**See:** [Rollback Procedures](#rollback-procedures) section above

---

## Performance Optimization

### Query Performance Tuning

After migration, run the optimization tool to ensure best performance:

```bash
# Analyze current performance
python scripts/optimize_polymorphic_queries.py --analyze

# Run benchmarks
python scripts/optimize_polymorphic_queries.py --benchmark

# Generate optimization report
python scripts/optimize_polymorphic_queries.py --report --output perf_report.txt

# Apply recommended optimizations
python scripts/optimize_polymorphic_queries.py --optimize
```

### Expected Performance Metrics

| Query Pattern | Target Latency | Notes |
|---------------|----------------|-------|
| List resources by protocol | < 50ms | Uses `ix_resources_protocol` |
| Search resources by metadata | < 100ms | Uses `ix_resources_metadata_gin` |
| List capabilities with resources | < 75ms | Uses JOIN indexes |
| High sensitivity capabilities | < 60ms | Uses `ix_capabilities_sensitivity` |
| Cross-protocol capabilities | < 150ms | Complex polymorphic query |
| Resource cost analysis | < 200ms | Joins 3 tables, may use materialized view |

### Index Maintenance

```sql
-- Check index bloat (run monthly)
SELECT
  schemaname,
  tablename,
  indexname,
  pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size,
  idx_scan as scans,
  idx_tup_read as tuples_read
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexname::regclass) DESC;

-- Rebuild bloated indexes (during maintenance window)
REINDEX INDEX CONCURRENTLY ix_resources_metadata_gin;
REINDEX INDEX CONCURRENTLY ix_capabilities_metadata_gin;

-- Update statistics (run weekly)
ANALYZE resources;
ANALYZE capabilities;
ANALYZE cost_tracking;
```

### Materialized View Refresh

```sql
-- Refresh cost analysis view (run daily)
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_cost_summary;

-- Check last refresh time
SELECT
  schemaname,
  matviewname,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||matviewname)) as size
FROM pg_matviews
WHERE schemaname = 'public';
```

---

## Post-Migration Tasks

### Immediate (Day 1)

- [ ] Monitor application logs for errors
- [ ] Monitor query performance metrics
- [ ] Verify audit events are being logged correctly
- [ ] Check cost tracking data is being recorded
- [ ] Update documentation with actual migration duration
- [ ] Notify stakeholders of successful migration

### Short-term (Week 1)

- [ ] Review and optimize slow queries
- [ ] Set up monitoring alerts for v2.0 schema
- [ ] Archive migration logs and reports
- [ ] Schedule v1.x table deprecation (after 30-day grace period)
- [ ] Update backup/restore procedures for v2.0 schema
- [ ] Train support team on v2.0 schema differences

### Long-term (Month 1+)

- [ ] Decommission v1.x tables (after data retention period)
  ```sql
  -- After 30-90 days, when confident v2.0 is stable:
  DROP TABLE mcp_tools CASCADE;
  DROP TABLE mcp_servers CASCADE;
  ```
- [ ] Optimize database storage (VACUUM FULL during maintenance window)
- [ ] Review and tune autovacuum settings for new tables
- [ ] Implement additional protocol adapters (HTTP, gRPC)
- [ ] Set up federation with partner organizations

---

## Appendix

### Migration Script Reference

| Script | Purpose | Duration |
|--------|---------|----------|
| `scripts/migrate_v1_to_v2.py --dry-run` | Preview migration | 1-2 min |
| `scripts/migrate_v1_to_v2.py --execute` | Execute migration | 5-60 min |
| `scripts/migrate_v1_to_v2.py --validate` | Validate migration | 2-5 min |
| `scripts/migrate_v1_to_v2.py --rollback` | Rollback migration | 2-5 min |
| `scripts/validate_migration.py --full` | Full validation | 5-10 min |
| `scripts/optimize_polymorphic_queries.py --optimize` | Apply optimizations | 10-20 min |

### Contact & Support

- **Database Team:** #sark-database-team
- **On-Call:** PagerDuty rotation
- **Documentation:** https://docs.sark.example.com/v2-migration
- **Issues:** https://github.com/example/sark/issues

### Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-12-02 | Initial runbook creation |
| 1.1.0 | TBD | Post-migration updates based on lessons learned |

---

**End of Migration Runbook**
