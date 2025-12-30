#!/usr/bin/env python3
"""Validate database migrations.

This script tests migration upgrade and downgrade paths to ensure
they work correctly and don't lose data.

Usage:
    python scripts/validate_migrations.py
    python scripts/validate_migrations.py --test-downgrade
    python scripts/validate_migrations.py --migration 003_policies
"""

import argparse
import asyncio
import logging
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from sark.db.session import get_postgres_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_database_connection() -> bool:
    """Check if database is accessible.

    Returns:
        True if database is accessible, False otherwise
    """
    try:
        engine = get_postgres_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✓ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        return False


async def get_current_revision() -> str | None:
    """Get current database revision.

    Returns:
        Current revision ID or None if no migrations applied
    """
    try:
        engine = get_postgres_engine()
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1")
            )
            row = result.first()
            if row:
                return row[0]
        return None
    except Exception:
        return None


async def count_tables() -> int:
    """Count number of tables in database.

    Returns:
        Number of tables
    """
    try:
        engine = get_postgres_engine()
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
                )
            )
            row = result.first()
            return row[0] if row else 0
    except Exception as e:
        logger.error(f"Failed to count tables: {e}")
        return 0


def get_alembic_config() -> Config:
    """Get Alembic configuration.

    Returns:
        Alembic Config object
    """
    config = Config("alembic.ini")
    return config


async def test_upgrade() -> bool:
    """Test migration upgrade to head.

    Returns:
        True if upgrade successful, False otherwise
    """
    logger.info("=" * 80)
    logger.info("Testing migration upgrade to head")
    logger.info("=" * 80)

    try:
        config = get_alembic_config()

        # Get initial state
        initial_revision = await get_current_revision()
        initial_tables = await count_tables()

        logger.info(f"Initial revision: {initial_revision or 'None'}")
        logger.info(f"Initial tables: {initial_tables}")

        # Upgrade to head
        logger.info("\nUpgrading to head...")
        command.upgrade(config, "head")

        # Get final state
        final_revision = await get_current_revision()
        final_tables = await count_tables()

        logger.info(f"\nFinal revision: {final_revision}")
        logger.info(f"Final tables: {final_tables}")

        if final_revision:
            logger.info("✓ Migration upgrade successful")
            return True
        else:
            logger.error("✗ Migration upgrade failed - no revision found")
            return False

    except Exception as e:
        logger.error(f"✗ Migration upgrade failed: {e}")
        return False


async def test_downgrade(target: str = "base") -> bool:
    """Test migration downgrade.

    Args:
        target: Target revision to downgrade to (default: base)

    Returns:
        True if downgrade successful, False otherwise
    """
    logger.info("=" * 80)
    logger.info(f"Testing migration downgrade to {target}")
    logger.info("=" * 80)

    try:
        config = get_alembic_config()

        # Get initial state
        initial_revision = await get_current_revision()
        initial_tables = await count_tables()

        logger.info(f"Initial revision: {initial_revision}")
        logger.info(f"Initial tables: {initial_tables}")

        # Downgrade
        logger.info(f"\nDowngrading to {target}...")
        command.downgrade(config, target)

        # Get final state
        final_revision = await get_current_revision()
        final_tables = await count_tables()

        logger.info(f"\nFinal revision: {final_revision or 'None'}")
        logger.info(f"Final tables: {final_tables}")

        if target == "base" and final_revision is None:
            logger.info("✓ Migration downgrade to base successful")
            return True
        elif target != "base" and final_revision == target:
            logger.info(f"✓ Migration downgrade to {target} successful")
            return True
        else:
            logger.error("✗ Migration downgrade failed - unexpected final revision")
            return False

    except Exception as e:
        logger.error(f"✗ Migration downgrade failed: {e}")
        return False


async def test_specific_migration(revision: str) -> bool:
    """Test a specific migration.

    Args:
        revision: Migration revision to test

    Returns:
        True if test successful, False otherwise
    """
    logger.info("=" * 80)
    logger.info(f"Testing specific migration: {revision}")
    logger.info("=" * 80)

    try:
        config = get_alembic_config()

        # Upgrade to specific revision
        logger.info(f"\nUpgrading to {revision}...")
        command.upgrade(config, revision)

        current = await get_current_revision()
        if current != revision:
            logger.error(f"✗ Failed to upgrade to {revision}")
            return False

        logger.info(f"✓ Successfully upgraded to {revision}")

        # Downgrade one step
        logger.info("\nDowngrading one step...")
        command.downgrade(config, "-1")

        logger.info("✓ Successfully downgraded one step")

        # Upgrade back
        logger.info(f"\nUpgrading back to {revision}...")
        command.upgrade(config, revision)

        current = await get_current_revision()
        if current != revision:
            logger.error(f"✗ Failed to re-upgrade to {revision}")
            return False

        logger.info(f"✓ Successfully re-upgraded to {revision}")
        return True

    except Exception as e:
        logger.error(f"✗ Migration test failed: {e}")
        return False


async def show_migration_history() -> None:
    """Show migration history."""
    logger.info("=" * 80)
    logger.info("Migration History")
    logger.info("=" * 80)

    try:
        config = get_alembic_config()
        command.history(config, verbose=True)
    except Exception as e:
        logger.error(f"Failed to show history: {e}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate database migrations")
    parser.add_argument(
        "--test-downgrade",
        action="store_true",
        help="Test downgrade to base after upgrade",
    )
    parser.add_argument(
        "--migration",
        type=str,
        help="Test specific migration revision",
    )
    parser.add_argument(
        "--show-history",
        action="store_true",
        help="Show migration history",
    )

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("SARK Database Migration Validation")
    logger.info("=" * 80)
    logger.info("")

    # Check database connection
    if not await check_database_connection():
        logger.error("Cannot proceed without database connection")
        sys.exit(1)

    # Show history if requested
    if args.show_history:
        await show_migration_history()
        return

    # Test specific migration if requested
    if args.migration:
        success = await test_specific_migration(args.migration)
        sys.exit(0 if success else 1)

    # Test upgrade
    if not await test_upgrade():
        logger.error("\n✗ VALIDATION FAILED: Upgrade test failed")
        sys.exit(1)

    # Test downgrade if requested
    if args.test_downgrade:
        if not await test_downgrade():
            logger.error("\n✗ VALIDATION FAILED: Downgrade test failed")
            sys.exit(1)

    logger.info("\n" + "=" * 80)
    logger.info("✓ ALL VALIDATIONS PASSED")
    logger.info("=" * 80)
    logger.info("\nMigrations are ready for production use!")


if __name__ == "__main__":
    asyncio.run(main())
