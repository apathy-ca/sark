# Database Migrations Guide

This guide covers all aspects of database migrations in SARK, including creating, testing, applying, and rolling back migrations.

## Table of Contents

- [Overview](#overview)
- [Migration System Architecture](#migration-system-architecture)
- [Quick Start](#quick-start)
- [Creating Migrations](#creating-migrations)
- [Testing Migrations](#testing-migrations)
- [Applying Migrations](#applying-migrations)
- [Rolling Back Migrations](#rolling-back-migrations)
- [Common Migration Patterns](#common-migration-patterns)
- [TimescaleDB Integration](#timescaledb-integration)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [CI/CD Integration](#cicd-integration)

## Overview

SARK uses [Alembic](https://alembic.sqlalchemy.org/) for database schema migrations. Alembic provides:

- **Version control** for database schema changes
- **Upgrade and downgrade** paths for schema evolution
- **Automatic migration generation** from SQLAlchemy models
- **Transaction support** for safe schema changes
- **Async support** for async SQLAlchemy engines

### Migration Files

Current migrations in order:

1. **001_initial_schema.py** - Users, Teams, MCP Servers, MCP Tools
2. **002_add_api_keys.py** - API Keys table
3. **003_add_policies.py** - Policies and Policy Versions
4. **004_add_audit_events.py** - Audit Events (TimescaleDB hypertable)

## Migration System Architecture

```
sark/
├── alembic/
│   ├── versions/               # Migration files
│   │   ├── 001_initial_schema.py
│   │   ├── 002_add_api_keys.py
│   │   ├── 003_add_policies.py
│   │   └── 004_add_audit_events.py
│   ├── env.py                  # Alembic environment configuration
│   └── script.py.mako          # Migration template
├── alembic.ini                 # Alembic configuration
├── scripts/
│   └── validate_migrations.py  # Migration validation script
└── src/sark/
    ├── models/                 # SQLAlchemy models
    └── db/
        ├── base.py            # Base class for models
        └── session.py         # Database session management
```

### How It Works

1. **Models**: SQLAlchemy models define the schema in Python code
2. **Alembic**: Generates migration files based on model changes
3. **Migrations**: Python scripts with `upgrade()` and `downgrade()` functions
4. **Database**: Alembic applies migrations to the database
5. **Validation**: Scripts verify migrations work correctly

## Quick Start

### Prerequisites

- PostgreSQL database running
- TimescaleDB extension (optional, for audit events)
- Python environment with dependencies installed

### Initial Setup

1. **Configure database connection**:

   ```bash
   # Set environment variables
   export POSTGRES_HOST=localhost
   export POSTGRES_PORT=5432
   export POSTGRES_DB=sark
   export POSTGRES_USER=sark
   export POSTGRES_PASSWORD=your_password
   ```

2. **Verify database connection**:

   ```bash
   psql -h localhost -U sark -d sark -c "SELECT version();"
   ```

3. **Apply all migrations**:

   ```bash
   alembic upgrade head
   ```

4. **Verify migration status**:

   ```bash
   alembic current
   ```

## Creating Migrations

### Manual Migration Creation

When you need full control over the migration:

```bash
# Create a new migration file
alembic revision -m "add_new_feature"
```

This creates a file like `alembic/versions/XXX_add_new_feature.py`:

```python
"""add new feature

Revision ID: XXX_add_new_feature
Revises: 004_audit_events
Create Date: 2024-11-23 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "005_add_new_feature"
down_revision = "004_audit_events"
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Apply migration changes."""
    # Add your upgrade logic here
    pass

def downgrade() -> None:
    """Revert migration changes."""
    # Add your downgrade logic here
    pass
```

### Auto-Generated Migrations

Alembic can detect model changes and generate migrations automatically:

```bash
# Generate migration from model changes
alembic revision --autogenerate -m "add_user_preferences"
```

**⚠️ Warning**: Always review auto-generated migrations! They may miss:
- Enum type changes
- Custom constraints
- Data migrations
- Index optimizations

### Migration Naming Convention

Use descriptive names with prefixes:

- `add_<table_name>` - Adding new tables
- `update_<table_name>_<change>` - Modifying existing tables
- `remove_<table_name>` - Dropping tables
- `add_<table>_<column>` - Adding columns
- `add_index_<purpose>` - Adding indexes

Examples:
- `001_initial_schema`
- `002_add_api_keys`
- `003_add_policies`
- `004_add_audit_events`
- `005_add_user_preferences`
- `006_add_index_performance`

## Testing Migrations

### Using the Validation Script

The `scripts/validate_migrations.py` script provides comprehensive testing:

#### Test Upgrade to Head

```bash
# Test upgrading to the latest migration
python scripts/validate_migrations.py
```

Output:
```
================================================================================
SARK Database Migration Validation
================================================================================

✓ Database connection successful

================================================================================
Testing migration upgrade to head
================================================================================
Initial revision: 003_policies
Initial tables: 8

Upgrading to head...

Final revision: 004_audit_events
Final tables: 9

✓ Migration upgrade successful

================================================================================
✓ ALL VALIDATIONS PASSED
================================================================================
```

#### Test Downgrade

```bash
# Test downgrade to base (removes all tables)
python scripts/validate_migrations.py --test-downgrade
```

#### Test Specific Migration

```bash
# Test a specific migration up/down/up cycle
python scripts/validate_migrations.py --migration 003_policies
```

Output:
```
================================================================================
Testing specific migration: 003_policies
================================================================================

Upgrading to 003_policies...
✓ Successfully upgraded to 003_policies

Downgrading one step...
✓ Successfully downgraded one step

Upgrading back to 003_policies...
✓ Successfully re-upgraded to 003_policies
```

#### Show Migration History

```bash
# Display all migrations and their status
python scripts/validate_migrations.py --show-history
```

### Manual Testing

#### Check Current Revision

```bash
alembic current
```

#### Show Migration History

```bash
alembic history --verbose
```

#### Test Upgrade Path

```bash
# Upgrade one step
alembic upgrade +1

# Upgrade to specific revision
alembic upgrade 003_policies

# Upgrade to head
alembic upgrade head
```

#### Test Downgrade Path

```bash
# Downgrade one step
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade 002_add_api_keys

# Downgrade to base (remove all)
alembic downgrade base
```

### Testing on Clean Database

```bash
# Create test database
createdb sark_test

# Export test database URL
export POSTGRES_DB=sark_test

# Run validation
python scripts/validate_migrations.py

# Cleanup
dropdb sark_test
```

### Testing with Existing Data

```bash
# Backup production database
pg_dump -h localhost -U sark sark > backup.sql

# Create test database from backup
createdb sark_test
psql -h localhost -U sark sark_test < backup.sql

# Test migrations
export POSTGRES_DB=sark_test
python scripts/validate_migrations.py

# Cleanup
dropdb sark_test
```

## Applying Migrations

### Development Environment

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade one step at a time
alembic upgrade +1
```

### Staging Environment

```bash
# Show what will be applied
alembic upgrade head --sql

# Apply migrations
alembic upgrade head
```

### Production Environment

**⚠️ Production Migration Checklist**:

1. **Backup database**:
   ```bash
   pg_dump -h $POSTGRES_HOST -U $POSTGRES_USER $POSTGRES_DB > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Test migrations on staging** with production data copy

3. **Review migration SQL**:
   ```bash
   alembic upgrade head --sql > migration.sql
   cat migration.sql  # Review carefully
   ```

4. **Plan downtime** (if required)

5. **Apply migrations**:
   ```bash
   alembic upgrade head
   ```

6. **Verify application** still works

7. **Monitor** for issues

### Zero-Downtime Migrations

For migrations that require zero downtime:

1. **Additive changes first** (new columns, tables)
2. **Deploy application** that works with both old and new schema
3. **Apply migration** to add new schema elements
4. **Deploy application** that uses new schema
5. **Apply migration** to remove old schema elements (if needed)

Example:
```python
# Migration 1: Add new column (nullable)
def upgrade():
    op.add_column('users', sa.Column('new_field', sa.String(255), nullable=True))

# Deploy app that populates new_field

# Migration 2: Make column non-nullable
def upgrade():
    op.alter_column('users', 'new_field', nullable=False)
```

## Rolling Back Migrations

### Simple Rollback

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade 003_policies

# Rollback all migrations
alembic downgrade base
```

### Production Rollback Procedure

1. **Identify issue** and target revision:
   ```bash
   alembic current
   alembic history
   ```

2. **Backup current state**:
   ```bash
   pg_dump -h $POSTGRES_HOST -U $POSTGRES_USER $POSTGRES_DB > backup_before_rollback.sql
   ```

3. **Test rollback on staging**:
   ```bash
   # On staging
   alembic downgrade <target_revision>
   ```

4. **Apply rollback on production**:
   ```bash
   alembic downgrade <target_revision>
   ```

5. **Verify application** works

### Emergency Rollback

If migrations fail mid-execution:

1. **Check Alembic version table**:
   ```sql
   SELECT * FROM alembic_version;
   ```

2. **Check transaction state**:
   ```sql
   SELECT * FROM pg_stat_activity WHERE state = 'idle in transaction';
   ```

3. **Manual intervention** may be required:
   ```sql
   -- Rollback any open transactions
   SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE state = 'idle in transaction';

   -- Manually update alembic_version if needed
   UPDATE alembic_version SET version_num = '<previous_revision>';
   ```

4. **Restore from backup** if necessary:
   ```bash
   dropdb sark
   createdb sark
   psql -h localhost -U sark sark < backup.sql
   ```

## Common Migration Patterns

### Adding a Table

```python
def upgrade() -> None:
    op.create_table(
        'new_table',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_new_table_name', 'new_table', ['name'])

def downgrade() -> None:
    op.drop_index('ix_new_table_name')
    op.drop_table('new_table')
```

### Adding a Column

```python
def upgrade() -> None:
    # Add nullable column first
    op.add_column('users', sa.Column('phone', sa.String(20), nullable=True))

    # Optionally populate with default values
    op.execute("UPDATE users SET phone = '' WHERE phone IS NULL")

    # Make non-nullable if needed
    op.alter_column('users', 'phone', nullable=False)

def downgrade() -> None:
    op.drop_column('users', 'phone')
```

### Adding an Enum Type

```python
def upgrade() -> None:
    # Create enum type
    op.execute("CREATE TYPE status_type AS ENUM ('active', 'inactive', 'suspended')")

    # Add column with enum type
    op.add_column(
        'users',
        sa.Column('status', sa.Enum('active', 'inactive', 'suspended', name='status_type'))
    )

def downgrade() -> None:
    op.drop_column('users', 'status')
    op.execute('DROP TYPE status_type')
```

### Adding Foreign Key

```python
def upgrade() -> None:
    # Add column
    op.add_column('orders', sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True))

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_orders_user_id',
        'orders', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )

    # Add index
    op.create_index('ix_orders_user_id', 'orders', ['user_id'])

def downgrade() -> None:
    op.drop_index('ix_orders_user_id')
    op.drop_constraint('fk_orders_user_id', 'orders', type_='foreignkey')
    op.drop_column('orders', 'user_id')
```

### Adding Indexes

```python
def upgrade() -> None:
    # Simple index
    op.create_index('ix_users_email', 'users', ['email'])

    # Composite index
    op.create_index('ix_users_role_status', 'users', ['role', 'status'])

    # Partial index
    op.create_index(
        'ix_users_active',
        'users',
        ['id'],
        postgresql_where=sa.text("status = 'active'")
    )

    # Unique index
    op.create_index('ix_users_email_unique', 'users', ['email'], unique=True)

def downgrade() -> None:
    op.drop_index('ix_users_email_unique')
    op.drop_index('ix_users_active')
    op.drop_index('ix_users_role_status')
    op.drop_index('ix_users_email')
```

### Data Migration

```python
def upgrade() -> None:
    # Add new column
    op.add_column('users', sa.Column('full_name', sa.String(255), nullable=True))

    # Migrate data
    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE users SET full_name = first_name || ' ' || last_name")
    )

    # Make non-nullable
    op.alter_column('users', 'full_name', nullable=False)

    # Drop old columns
    op.drop_column('users', 'first_name')
    op.drop_column('users', 'last_name')

def downgrade() -> None:
    # Add old columns back
    op.add_column('users', sa.Column('first_name', sa.String(100), nullable=True))
    op.add_column('users', sa.Column('last_name', sa.String(100), nullable=True))

    # Migrate data back (best effort)
    connection = op.get_bind()
    connection.execute(
        sa.text("""
            UPDATE users
            SET first_name = split_part(full_name, ' ', 1),
                last_name = split_part(full_name, ' ', 2)
        """)
    )

    # Drop new column
    op.drop_column('users', 'full_name')
```

### Renaming Column

```python
def upgrade() -> None:
    op.alter_column('users', 'old_name', new_column_name='new_name')

def downgrade() -> None:
    op.alter_column('users', 'new_name', new_column_name='old_name')
```

### Changing Column Type

```python
def upgrade() -> None:
    # PostgreSQL allows direct type conversion for compatible types
    op.alter_column('users', 'age', type_=sa.Integer, postgresql_using='age::integer')

def downgrade() -> None:
    op.alter_column('users', 'age', type_=sa.String, postgresql_using='age::text')
```

## TimescaleDB Integration

### Creating Hypertables

The `004_add_audit_events.py` migration shows how to create TimescaleDB hypertables:

```python
def upgrade() -> None:
    # Create regular table first
    op.create_table(
        'audit_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        # ... other columns
    )

    # Convert to TimescaleDB hypertable (if extension available)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
                PERFORM create_hypertable('audit_events', 'timestamp', if_not_exists => TRUE);
                RAISE NOTICE 'Created TimescaleDB hypertable for audit_events';
            ELSE
                RAISE NOTICE 'TimescaleDB extension not found, created as regular table';
            END IF;
        END
        $$ LANGUAGE plpgsql;
    """)
```

### Retention Policies

```python
def upgrade() -> None:
    # Add retention policy (keep data for 90 days)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
                PERFORM add_retention_policy('audit_events', INTERVAL '90 days', if_not_exists => TRUE);
                RAISE NOTICE 'Added retention policy for audit_events';
            END IF;
        END
        $$ LANGUAGE plpgsql;
    """)
```

### Compression Policies

```python
def upgrade() -> None:
    # Enable compression for older data
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
                ALTER TABLE audit_events SET (
                    timescaledb.compress,
                    timescaledb.compress_segmentby = 'event_type'
                );

                PERFORM add_compression_policy('audit_events', INTERVAL '7 days', if_not_exists => TRUE);
                RAISE NOTICE 'Added compression policy for audit_events';
            END IF;
        END
        $$ LANGUAGE plpgsql;
    """)
```

## Troubleshooting

### Migration Fails with "relation already exists"

**Problem**: Table or index already exists

**Solution**:
```python
# Check if exists before creating
def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if 'users' not in inspector.get_table_names():
        op.create_table('users', ...)
```

### Migration Fails with "column does not exist"

**Problem**: Trying to modify non-existent column

**Solution**:
```python
def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [c['name'] for c in inspector.get_columns('users')]

    if 'old_column' not in columns:
        # Skip or handle differently
        return
```

### Alembic Version Table Out of Sync

**Problem**: `alembic_version` table doesn't match actual schema

**Solution**:
```bash
# Check current database revision
psql -c "SELECT * FROM alembic_version;"

# Check what Alembic thinks
alembic current

# Manually stamp to correct revision
alembic stamp <correct_revision>
```

### Migration Stuck in Transaction

**Problem**: Migration fails and leaves transaction open

**Solution**:
```sql
-- Check for stuck transactions
SELECT * FROM pg_stat_activity WHERE state = 'idle in transaction';

-- Terminate stuck connection
SELECT pg_terminate_backend(<pid>);

-- Check alembic version
SELECT * FROM alembic_version;

-- Stamp to previous working revision
alembic stamp <previous_revision>
```

### Cannot Downgrade Data Migration

**Problem**: Data transformation is not reversible

**Solution**:
```python
def downgrade():
    # Document that downgrade loses data
    logger.warning("Downgrade will lose data from full_name field")

    # Best effort recovery or raise error
    raise NotImplementedError(
        "Downgrade not supported - data transformation is not reversible. "
        "Restore from backup if needed."
    )
```

### Circular Foreign Key Dependencies

**Problem**: Two tables reference each other

**Solution** (see `003_add_policies.py`):
```python
def upgrade():
    # Create first table without foreign key
    op.create_table('policies', ...)

    # Create second table with foreign key to first
    op.create_table('policy_versions',
        sa.ForeignKey('policies.id'),
        ...
    )

    # Add foreign key from first to second separately
    op.create_foreign_key(
        'fk_policies_active_version',
        'policies', 'policy_versions',
        ['active_version_id'], ['id']
    )
```

### Enum Type Already Exists

**Problem**: Enum type exists from previous migration

**Solution**:
```python
def upgrade():
    # Check if enum exists
    connection = op.get_bind()
    result = connection.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = 'status_type'")
    )

    if not result.fetchone():
        op.execute("CREATE TYPE status_type AS ENUM ('active', 'inactive')")
```

## Best Practices

### General Guidelines

1. **One logical change per migration** - Don't combine unrelated changes
2. **Always provide downgrade** - Every migration must be reversible
3. **Test migrations thoroughly** - Test upgrade, downgrade, and re-upgrade
4. **Use transactions** - Alembic uses transactions by default, keep it that way
5. **Review auto-generated migrations** - Never blindly trust autogenerate
6. **Document complex migrations** - Add comments explaining why and how
7. **Backup before production** - Always backup before applying migrations
8. **Plan for zero downtime** - Use additive changes when possible

### Migration Naming

- Use sequential numbers: `001_`, `002_`, `003_`
- Use descriptive names: `add_api_keys`, not `migration1`
- Use snake_case: `add_user_preferences`, not `AddUserPreferences`
- Be specific: `add_index_user_email`, not `add_indexes`

### Writing Migrations

```python
def upgrade() -> None:
    """Apply migration.

    This migration adds user preferences table to support
    customizable dashboard settings.
    """
    # Use context managers for complex operations
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('preferences', postgresql.JSONB))

    # Add comments for complex logic
    # We populate default preferences for existing users
    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE users SET preferences = '{}' WHERE preferences IS NULL")
    )
```

### Testing Strategy

1. **Unit test migrations**:
   ```bash
   python scripts/validate_migrations.py --migration <revision>
   ```

2. **Integration test**:
   ```bash
   # Test full upgrade path
   alembic downgrade base
   alembic upgrade head
   ```

3. **Test with data**:
   ```bash
   # Load sample data
   psql < tests/fixtures/sample_data.sql

   # Test migrations
   alembic upgrade head
   alembic downgrade base
   ```

4. **Performance test**:
   ```bash
   # Load large dataset
   # Measure migration time
   time alembic upgrade head
   ```

### Version Control

- **Commit migrations atomically** - One migration per commit
- **Squash before merging** - Keep migration history clean
- **Tag releases** - Tag commits with schema version
- **Document in PR** - Explain migration purpose and risks

### Production Deployment

1. **Pre-deployment**:
   - Review migration SQL
   - Test on staging with production data
   - Estimate migration time
   - Plan rollback procedure
   - Notify team of deployment window

2. **Deployment**:
   - Backup database
   - Apply migrations
   - Verify application health
   - Monitor for errors

3. **Post-deployment**:
   - Verify data integrity
   - Check application logs
   - Monitor performance
   - Keep backup for 24-48 hours

## CI/CD Integration

### GitHub Actions

```yaml
name: Database Migrations

on:
  pull_request:
    paths:
      - 'alembic/versions/**'
      - 'src/sark/models/**'

jobs:
  test-migrations:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: timescale/timescaledb:latest-pg14
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: sark_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run migration validation
        env:
          POSTGRES_HOST: localhost
          POSTGRES_PORT: 5432
          POSTGRES_DB: sark_test
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        run: |
          python scripts/validate_migrations.py
          python scripts/validate_migrations.py --test-downgrade
```

### GitLab CI

```yaml
test:migrations:
  stage: test
  services:
    - name: timescale/timescaledb:latest-pg14
      alias: postgres
  variables:
    POSTGRES_HOST: postgres
    POSTGRES_DB: sark_test
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: postgres
  script:
    - pip install -r requirements.txt
    - python scripts/validate_migrations.py
    - python scripts/validate_migrations.py --test-downgrade
  only:
    changes:
      - alembic/versions/**
      - src/sark/models/**
```

### Pre-commit Hook

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash

# Check if migration files changed
if git diff --cached --name-only | grep -q "alembic/versions/"; then
    echo "Migration files changed, running validation..."
    python scripts/validate_migrations.py
    if [ $? -ne 0 ]; then
        echo "Migration validation failed!"
        exit 1
    fi
fi
```

## Additional Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [TimescaleDB Documentation](https://docs.timescale.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## Support

For issues with migrations:

1. Check this guide's [Troubleshooting](#troubleshooting) section
2. Review migration logs: `alembic history --verbose`
3. Check database state: `psql -c "\d"` to list all tables
4. Contact the database team with specific error messages

---

*Last updated: 2024-11-23*
