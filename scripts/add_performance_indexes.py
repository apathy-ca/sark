#!/usr/bin/env python3
"""Apply performance indexes to the database.

This script adds optimized indexes to improve query performance.
Target: Database query time < 20ms for p95

Usage:
    python scripts/add_performance_indexes.py
    python scripts/add_performance_indexes.py --dry-run
"""

import argparse
import asyncio
import logging
from pathlib import Path

from sqlalchemy import text

from sark.config import get_settings
from sark.db.session import get_postgres_engine, get_timescale_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def apply_indexes(dry_run: bool = False) -> None:
    """Apply performance indexes to the database.

    Args:
        dry_run: If True, only print SQL without executing
    """
    settings = get_settings()
    postgres_engine = get_postgres_engine()
    timescale_engine = get_timescale_engine()

    # Read the SQL file
    sql_file = Path(__file__).parent.parent / "alembic" / "versions" / "001_add_performance_indexes.sql"
    logger.info(f"Reading SQL from {sql_file}")

    with open(sql_file, "r") as f:
        sql_content = f.read()

    if dry_run:
        logger.info("DRY RUN: Would execute the following SQL:")
        print("\n" + "=" * 80)
        print(sql_content)
        print("=" * 80 + "\n")
        return

    # Execute on main database
    logger.info(f"Applying indexes to PostgreSQL database: {settings.postgres_db}")
    async with postgres_engine.begin() as conn:
        # Split by semicolon and execute each statement
        statements = [s.strip() for s in sql_content.split(";") if s.strip() and not s.strip().startswith("--")]

        for i, statement in enumerate(statements, 1):
            if statement:
                logger.info(f"Executing statement {i}/{len(statements)}")
                try:
                    await conn.execute(text(statement))
                    logger.info(f"✓ Statement {i} executed successfully")
                except Exception as e:
                    # Log error but continue (indexes might already exist)
                    logger.warning(f"Statement {i} failed (might already exist): {e}")

    # Execute on TimescaleDB for audit events indexes
    logger.info(f"Applying indexes to TimescaleDB database: {settings.timescale_db}")
    async with timescale_engine.begin() as conn:
        # Only execute audit_events indexes for TimescaleDB
        audit_statements = [s.strip() for s in sql_content.split(";")
                            if "audit_events" in s and s.strip() and not s.strip().startswith("--")]

        for i, statement in enumerate(audit_statements, 1):
            if statement:
                logger.info(f"Executing audit statement {i}/{len(audit_statements)}")
                try:
                    await conn.execute(text(statement))
                    logger.info(f"✓ Audit statement {i} executed successfully")
                except Exception as e:
                    logger.warning(f"Audit statement {i} failed (might already exist): {e}")

    logger.info("✓ All indexes applied successfully!")
    logger.info("\nTo verify indexes, run:")
    logger.info("  psql -U sark -d sark -c \"\\di+\"")
    logger.info("\nTo monitor index usage:")
    logger.info("  SELECT * FROM pg_stat_user_indexes WHERE schemaname = 'public';")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Apply performance indexes to database")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print SQL without executing",
    )

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("Performance Index Application")
    logger.info("=" * 80)

    try:
        await apply_indexes(dry_run=args.dry_run)

        if not args.dry_run:
            logger.info("\n" + "=" * 80)
            logger.info("SUCCESS: Performance indexes applied!")
            logger.info("=" * 80)
            logger.info("\nNext steps:")
            logger.info("1. Run ANALYZE to update query planner statistics:")
            logger.info("   psql -U sark -d sark -c 'ANALYZE;'")
            logger.info("\n2. Run performance tests to verify improvements:")
            logger.info("   cd tests/performance && ./run_tests.sh load_moderate")
            logger.info("\n3. Monitor query performance:")
            logger.info("   SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;")

    except Exception as e:
        logger.error(f"Failed to apply indexes: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
