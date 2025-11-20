# Database Initialization Scripts

This directory contains SQL scripts that run automatically when initializing a new PostgreSQL database in managed mode.

## How It Works

When you use the managed PostgreSQL service (via Docker Compose), any `.sql` or `.sh` files in this directory are automatically executed during database initialization, in alphabetical order.

## Usage

1. Place your `.sql` initialization scripts here
2. Name them with a numeric prefix to control execution order:
   - `01-create-schema.sql`
   - `02-create-tables.sql`
   - `03-seed-data.sql`

## Example

```sql
-- File: 01-create-extensions.sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
```

## Note for External Databases

These scripts only run for **managed** PostgreSQL deployments. If you're connecting to an existing enterprise database (external mode), you'll need to run initialization scripts manually or through your organization's database migration process.

See `docs/deployment/INTEGRATION.md` for more details on managing external databases.
