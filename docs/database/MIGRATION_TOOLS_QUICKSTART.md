# SARK v2.0 Migration Tools - Quick Start Guide

**For:** Database Engineers, DevOps, Operations Team
**Purpose:** Quick reference for using SARK v2.0 migration testing and optimization tools

---

## 🚀 Quick Start

### Before Migration

```bash
# 1. Validate current database state
python scripts/validate_migration.py --schema

# 2. Run optimization analysis
python scripts/optimize_polymorphic_queries.py --analyze

# 3. Create database backup
pg_dump -h localhost -U sark -d sark -F c -f backup_$(date +%Y%m%d).dump
```

### During Migration

```bash
# 1. Run Alembic migrations
alembic upgrade head

# 2. Execute data migration (dry-run first!)
python scripts/migrate_v1_to_v2.py --dry-run
python scripts/migrate_v1_to_v2.py --execute

# 3. Validate migration
python scripts/validate_migration.py --full --output validation_report.json

# 4. Check validation results
cat validation_report.json | jq '.failed_checks'
```

### After Migration

```bash
# 1. Apply query optimizations
python scripts/optimize_polymorphic_queries.py --optimize

# 2. Run benchmarks
python scripts/optimize_polymorphic_queries.py --benchmark

# 3. Generate performance report
python scripts/optimize_polymorphic_queries.py --report --output perf_report.txt
```

---

## 📖 Tool Reference

### 1. validate_migration.py

**Purpose:** Comprehensive validation of v1.x → v2.0 migration

#### Usage Modes

```bash
# Quick validation (2 min) - essential checks only
python scripts/validate_migration.py --quick

# Full validation (5-10 min) - all checks
python scripts/validate_migration.py --full

# Schema only - check tables/columns/indexes
python scripts/validate_migration.py --schema

# Data only - check counts and integrity
python scripts/validate_migration.py --data

# Relationships only - check foreign keys
python scripts/validate_migration.py --relationships

# Save report to JSON
python scripts/validate_migration.py --full --output report.json
```

#### Exit Codes

- `0` = All validations passed ✅
- `1` = Validation failures detected ⚠️
- `2` = Critical errors ❌

#### Example Output

```
════════════════════════════════════════════════════════════════════════
SARK v2.0 Migration Validation Report
════════════════════════════════════════════════════════════════════════
Total checks: 25
Passed: 23
Failed: 2

CRITICAL (0 issues)
────────────────────────────────────────────────────────────────────────

ERROR (2 issues)
────────────────────────────────────────────────────────────────────────
  [data.server_count_mismatch] Server count mismatch: 1234 v1.x != 1200 v2.0
    Details: {"v1_count": 1234, "v2_count": 1200, "diff": 34}

  [data.orphaned_capabilities] Found 5 capabilities without valid resource_id
    Details: {"count": 5}

STATUS: ❌ VALIDATION FAILED
════════════════════════════════════════════════════════════════════════
```

---

### 2. optimize_polymorphic_queries.py

**Purpose:** Analyze and optimize polymorphic query performance

#### Usage Modes

```bash
# Analyze existing indexes
python scripts/optimize_polymorphic_queries.py --analyze

# Run query benchmarks
python scripts/optimize_polymorphic_queries.py --benchmark

# Generate performance report
python scripts/optimize_polymorphic_queries.py --report

# Apply optimizations (creates indexes)
python scripts/optimize_polymorphic_queries.py --optimize

# Dry-run optimizations
python scripts/optimize_polymorphic_queries.py --optimize --dry-run

# Save report to file
python scripts/optimize_polymorphic_queries.py --report --output perf.txt
```

#### Example Report

```
════════════════════════════════════════════════════════════════════════
SARK v2.0 Polymorphic Query Performance Report
════════════════════════════════════════════════════════════════════════
Generated: 2024-12-02T10:30:00Z

Index Summary
────────────────────────────────────────────────────────────────────────
resources: 4 indexes
  - ix_resources_protocol
  - ix_resources_metadata_gin
  - ix_resources_name
  - ix_resources_sensitivity

Query Benchmark Results
────────────────────────────────────────────────────────────────────────
Query Name                               Time (ms)    Rows    Index Used
────────────────────────────────────────────────────────────────────────
list_resources_by_protocol                   45.23     100    ✓
search_resources_by_metadata                 87.45      50    ✓
list_capabilities_with_resources             62.18     150    ✓
high_sensitivity_capabilities                54.32      25    ✓
cross_protocol_capabilities                 142.67     200    ✓

Performance Statistics
────────────────────────────────────────────────────────────────────────
Average query time: 78.37ms
Min query time: 45.23ms
Max query time: 142.67ms
Queries using indexes: 5/5

Optimization Recommendations
────────────────────────────────────────────────────────────────────────
No optimization recommendations - queries are performing well!
════════════════════════════════════════════════════════════════════════
```

---

### 3. migrate_v1_to_v2.py

**Purpose:** Execute v1.x → v2.0 data migration

#### Usage Modes

```bash
# Preview migration (no changes)
python scripts/migrate_v1_to_v2.py --dry-run

# Execute migration
python scripts/migrate_v1_to_v2.py --execute

# Validate existing migration
python scripts/migrate_v1_to_v2.py --validate

# Rollback migration (delete v2.0 MCP data)
python scripts/migrate_v1_to_v2.py --rollback
```

#### Example Output

```
2024-12-02 10:30:00 INFO - Checking prerequisites...
2024-12-02 10:30:00 INFO - ✓ Prerequisites validated
2024-12-02 10:30:00 INFO - Current state:
2024-12-02 10:30:00 INFO -   v1.x: 1234 servers, 5678 tools
2024-12-02 10:30:00 INFO -   v2.0: 0 resources, 0 capabilities
2024-12-02 10:30:00 INFO - === EXECUTING MIGRATION ===
2024-12-02 10:30:10 INFO - ✓ Migrated 1234 MCP servers to resources
2024-12-02 10:30:20 INFO - ✓ Migrated 5678 MCP tools to capabilities
2024-12-02 10:30:25 INFO - ✓ All v1.x servers have v2.0 resources
2024-12-02 10:30:25 INFO - ✓ All v1.x tools have v2.0 capabilities
2024-12-02 10:30:25 INFO - ✓ Foreign key integrity validated

Migration Summary
═════════════════════════════════════════════════════════════════
Duration: 25.34 seconds

v1.x Data:
  - MCP Servers: 1234
  - MCP Tools: 5678

v2.0 Data Created:
  - Resources: 1234
  - Capabilities: 5678

Status:
  - Errors: 0
  - Warnings: 0

2024-12-02 10:30:25 INFO - ✓ Migration completed successfully
```

---

## 🔍 Common Workflows

### Workflow 1: Pre-Migration Validation

```bash
# Check database is ready for migration
python scripts/validate_migration.py --schema

# Analyze current query performance baseline
python scripts/optimize_polymorphic_queries.py --benchmark > pre_migration_perf.txt

# Verify data counts
psql -h localhost -U sark -d sark -c "
  SELECT
    (SELECT COUNT(*) FROM mcp_servers) as servers,
    (SELECT COUNT(*) FROM mcp_tools) as tools;
"
```

### Workflow 2: Migration Execution

```bash
# 1. Dry-run migration
python scripts/migrate_v1_to_v2.py --dry-run

# 2. Review dry-run output, then execute
python scripts/migrate_v1_to_v2.py --execute

# 3. Immediate validation
python scripts/validate_migration.py --quick

# 4. Full validation if quick passes
python scripts/validate_migration.py --full --output validation.json

# 5. Check for any failures
if [ $? -ne 0 ]; then
  echo "Validation failed! Check validation.json"
  cat validation.json | jq '.issues[] | select(.severity == "error")'
fi
```

### Workflow 3: Post-Migration Optimization

```bash
# 1. Apply performance optimizations
python scripts/optimize_polymorphic_queries.py --optimize

# 2. Wait for indexes to build (5-20 minutes for large DBs)
psql -h localhost -U sark -d sark -c "
  SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as size
  FROM pg_indexes
  WHERE schemaname = 'public'
  ORDER BY pg_relation_size(indexname::regclass) DESC;
"

# 3. Run benchmarks
python scripts/optimize_polymorphic_queries.py --benchmark

# 4. Generate report
python scripts/optimize_polymorphic_queries.py --report --output post_migration_perf.txt

# 5. Compare before/after
diff pre_migration_perf.txt post_migration_perf.txt
```

### Workflow 4: Rollback

```bash
# 1. Dry-run rollback to see what would be deleted
python scripts/migrate_v1_to_v2.py --rollback --dry-run

# 2. Execute rollback
python scripts/migrate_v1_to_v2.py --rollback

# 3. Verify v1.x data intact
python scripts/validate_migration.py --data

# 4. Optional: Rollback Alembic migrations
alembic downgrade 005
```

---

## 🚨 Troubleshooting

### Issue: Validation shows count mismatch

```bash
# Find missing records
psql -h localhost -U sark -d sark -c "
  SELECT s.id, s.name
  FROM mcp_servers s
  WHERE NOT EXISTS (
    SELECT 1 FROM resources r WHERE r.id = s.id::text
  )
  LIMIT 10;
"

# Re-run migration (idempotent)
python scripts/migrate_v1_to_v2.py --execute
```

### Issue: Orphaned capabilities detected

```bash
# Identify orphaned capabilities
psql -h localhost -U sark -d sark -c "
  SELECT c.id, c.name, c.resource_id
  FROM capabilities c
  WHERE NOT EXISTS (
    SELECT 1 FROM resources r WHERE r.id = c.resource_id
  );
"

# Clean up orphans
psql -h localhost -U sark -d sark -c "
  DELETE FROM capabilities
  WHERE NOT EXISTS (
    SELECT 1 FROM resources r WHERE r.id = resource_id
  );
"
```

### Issue: Slow query performance

```bash
# Update table statistics
psql -h localhost -U sark -d sark -c "
  ANALYZE resources;
  ANALYZE capabilities;
"

# Apply optimizations
python scripts/optimize_polymorphic_queries.py --optimize

# Re-run benchmarks
python scripts/optimize_polymorphic_queries.py --benchmark
```

---

## 📊 CI/CD Integration

### GitHub Actions Example

```yaml
name: Migration Validation

on:
  pull_request:
    branches: [main]

jobs:
  validate-migration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Setup database
        run: docker-compose up -d postgres

      - name: Run migrations
        run: alembic upgrade head

      - name: Execute data migration
        run: python scripts/migrate_v1_to_v2.py --execute

      - name: Validate migration
        run: |
          python scripts/validate_migration.py --full --output validation.json
          if [ $? -ne 0 ]; then
            echo "Validation failed!"
            cat validation.json | jq '.issues[] | select(.severity == "error")'
            exit 1
          fi

      - name: Upload validation report
        uses: actions/upload-artifact@v2
        with:
          name: validation-report
          path: validation.json
```

---

## 📞 Support

- **Documentation:** `/docs/database/MIGRATION_RUNBOOK.md`
- **Issues:** Report to #sark-database-team
- **On-Call:** PagerDuty escalation for production issues

---

**Last Updated:** 2024-12-02
**Version:** 2.0.0
