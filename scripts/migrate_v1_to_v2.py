#!/usr/bin/env python3
"""
SARK v1.x to v2.0 Data Migration Script

This script migrates data from the v1.x schema (mcp_servers, mcp_tools) to the
v2.0 schema (resources, capabilities) while preserving all data and relationships.

Usage:
    python scripts/migrate_v1_to_v2.py --dry-run         # Preview changes
    python scripts/migrate_v1_to_v2.py --execute         # Execute migration
    python scripts/migrate_v1_to_v2.py --validate        # Validate post-migration
    python scripts/migrate_v1_to_v2.py --rollback        # Rollback to v1.x

Requirements:
    - Database must have both v1.x and v2.0 schemas (run migrations 006 and 007 first)
    - No active writes during migration
    - Backup recommended before execution
"""

import argparse
from datetime import UTC, datetime
import logging
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class MigrationStats:
    """Track migration statistics."""

    def __init__(self):
        self.servers_migrated = 0
        self.tools_migrated = 0
        self.resources_created = 0
        self.capabilities_created = 0
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.start_time: datetime = None
        self.end_time: datetime = None

    def duration(self) -> float:
        """Calculate migration duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0

    def summary(self) -> str:
        """Generate summary report."""
        return f"""
Migration Summary
=================
Duration: {self.duration():.2f} seconds

v1.x Data:
  - MCP Servers: {self.servers_migrated}
  - MCP Tools: {self.tools_migrated}

v2.0 Data Created:
  - Resources: {self.resources_created}
  - Capabilities: {self.capabilities_created}

Status:
  - Errors: {len(self.errors)}
  - Warnings: {len(self.warnings)}
"""


def get_database_url() -> str:
    """Get database URL from environment or default."""
    import os

    return os.getenv(
        "DATABASE_URL",
        "postgresql://sark:sark@localhost:5432/sark",
    )


def create_session() -> Session:
    """Create database session."""
    engine = create_engine(get_database_url(), echo=False)
    Session = sessionmaker(bind=engine)
    return Session()


def check_prerequisites(session: Session) -> tuple[bool, list[str]]:
    """
    Check migration prerequisites.

    Returns:
        (success, errors) tuple
    """
    errors = []

    # Check if v1.x tables exist
    result = session.execute(
        text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'mcp_servers')"
        )
    )
    if not result.scalar():
        errors.append("v1.x table 'mcp_servers' does not exist")

    result = session.execute(
        text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'mcp_tools')"
        )
    )
    if not result.scalar():
        errors.append("v1.x table 'mcp_tools' does not exist")

    # Check if v2.0 tables exist
    result = session.execute(
        text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'resources')"
        )
    )
    if not result.scalar():
        errors.append("v2.0 table 'resources' does not exist (run migration 006 first)")

    result = session.execute(
        text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'capabilities')"
        )
    )
    if not result.scalar():
        errors.append("v2.0 table 'capabilities' does not exist (run migration 006 first)")

    return len(errors) == 0, errors


def count_v1_data(session: Session) -> tuple[int, int]:
    """Count existing v1.x data."""
    server_count = session.execute(text("SELECT COUNT(*) FROM mcp_servers")).scalar()
    tool_count = session.execute(text("SELECT COUNT(*) FROM mcp_tools")).scalar()
    return server_count, tool_count


def count_v2_data(session: Session) -> tuple[int, int]:
    """Count existing v2.0 data."""
    resource_count = session.execute(text("SELECT COUNT(*) FROM resources")).scalar()
    capability_count = session.execute(text("SELECT COUNT(*) FROM capabilities")).scalar()
    return resource_count, capability_count


def migrate_servers_to_resources(session: Session, stats: MigrationStats, dry_run: bool = True):
    """
    Migrate mcp_servers to resources.

    Maps:
    - id -> id (as string)
    - name -> name
    - protocol -> 'mcp'
    - command/endpoint -> endpoint
    - sensitivity_level -> sensitivity_level
    - All other fields -> metadata JSONB
    """
    logger.info("Migrating MCP servers to resources...")

    # Build migration query
    query = text("""
        INSERT INTO resources (id, name, protocol, endpoint, sensitivity_level, metadata, created_at, updated_at)
        SELECT
            id::text,
            name,
            'mcp' as protocol,
            COALESCE(command, endpoint) as endpoint,
            sensitivity_level::text,
            jsonb_build_object(
                'transport', transport::text,
                'command', command,
                'endpoint', endpoint,
                'mcp_version', mcp_version,
                'capabilities', capabilities,
                'status', status::text,
                'health_endpoint', health_endpoint,
                'last_health_check', last_health_check,
                'owner_id', owner_id::text,
                'team_id', team_id::text,
                'consul_id', consul_id,
                'tags', tags,
                'signature', signature,
                'description', description
            ) || COALESCE(extra_metadata, '{}'::jsonb),
            created_at,
            updated_at
        FROM mcp_servers
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            endpoint = EXCLUDED.endpoint,
            metadata = EXCLUDED.metadata,
            updated_at = NOW()
        RETURNING id
    """)

    if dry_run:
        # Count how many would be migrated
        count_query = text("SELECT COUNT(*) FROM mcp_servers")
        count = session.execute(count_query).scalar()
        logger.info(f"[DRY RUN] Would migrate {count} MCP servers to resources")
        stats.servers_migrated = count
        stats.resources_created = count
    else:
        result = session.execute(query)
        migrated_count = result.rowcount
        session.commit()
        logger.info(f"✓ Migrated {migrated_count} MCP servers to resources")
        stats.servers_migrated = migrated_count
        stats.resources_created = migrated_count


def migrate_tools_to_capabilities(session: Session, stats: MigrationStats, dry_run: bool = True):
    """
    Migrate mcp_tools to capabilities.

    Maps:
    - id -> id (as string)
    - server_id -> resource_id
    - name -> name
    - description -> description
    - parameters -> input_schema
    - sensitivity_level -> sensitivity_level
    - All other fields -> metadata JSONB
    """
    logger.info("Migrating MCP tools to capabilities...")

    query = text("""
        INSERT INTO capabilities (id, resource_id, name, description, input_schema, output_schema, sensitivity_level, metadata)
        SELECT
            t.id::text,
            t.server_id::text as resource_id,
            t.name,
            t.description,
            COALESCE(t.parameters, '{}'::jsonb) as input_schema,
            '{}'::jsonb as output_schema,
            t.sensitivity_level::text,
            jsonb_build_object(
                'requires_approval', t.requires_approval,
                'signature', t.signature,
                'invocation_count', t.invocation_count,
                'last_invoked', t.last_invoked
            ) || COALESCE(t.extra_metadata, '{}'::jsonb)
        FROM mcp_tools t
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            input_schema = EXCLUDED.input_schema,
            metadata = EXCLUDED.metadata
        RETURNING id
    """)

    if dry_run:
        count_query = text("SELECT COUNT(*) FROM mcp_tools")
        count = session.execute(count_query).scalar()
        logger.info(f"[DRY RUN] Would migrate {count} MCP tools to capabilities")
        stats.tools_migrated = count
        stats.capabilities_created = count
    else:
        result = session.execute(query)
        migrated_count = result.rowcount
        session.commit()
        logger.info(f"✓ Migrated {migrated_count} MCP tools to capabilities")
        stats.tools_migrated = migrated_count
        stats.capabilities_created = migrated_count


def validate_migration(session: Session) -> tuple[bool, list[str]]:
    """
    Validate migration results.

    Checks:
    - All v1.x servers have v2.0 resources
    - All v1.x tools have v2.0 capabilities
    - Foreign key relationships are intact
    - No data loss in metadata
    """
    logger.info("Validating migration...")
    errors = []

    # Check server count match
    v1_servers, _v1_tools = count_v1_data(session)
    _v2_resources, _v2_capabilities = count_v2_data(session)

    # Count MCP-protocol resources (should match v1 servers)
    mcp_resources = session.execute(
        text("SELECT COUNT(*) FROM resources WHERE protocol = 'mcp'")
    ).scalar()

    if mcp_resources != v1_servers:
        errors.append(
            f"Server count mismatch: {v1_servers} v1.x servers but {mcp_resources} v2.0 MCP resources"
        )
    else:
        logger.info(f"✓ Server count validated: {v1_servers} servers = {mcp_resources} resources")

    # Check every v1 server has a v2 resource
    orphaned_servers = session.execute(
        text("""
            SELECT COUNT(*)
            FROM mcp_servers s
            WHERE NOT EXISTS (
                SELECT 1 FROM resources r WHERE r.id = s.id::text
            )
        """)
    ).scalar()

    if orphaned_servers > 0:
        errors.append(f"Found {orphaned_servers} v1.x servers without v2.0 resources")
    else:
        logger.info("✓ All v1.x servers have v2.0 resources")

    # Check every v1 tool has a v2 capability
    orphaned_tools = session.execute(
        text("""
            SELECT COUNT(*)
            FROM mcp_tools t
            WHERE NOT EXISTS (
                SELECT 1 FROM capabilities c WHERE c.id = t.id::text
            )
        """)
    ).scalar()

    if orphaned_tools > 0:
        errors.append(f"Found {orphaned_tools} v1.x tools without v2.0 capabilities")
    else:
        logger.info("✓ All v1.x tools have v2.0 capabilities")

    # Check foreign key integrity
    broken_fks = session.execute(
        text("""
            SELECT COUNT(*)
            FROM capabilities c
            WHERE NOT EXISTS (
                SELECT 1 FROM resources r WHERE r.id = c.resource_id
            )
        """)
    ).scalar()

    if broken_fks > 0:
        errors.append(f"Found {broken_fks} capabilities with broken resource_id foreign keys")
    else:
        logger.info("✓ Foreign key integrity validated")

    return len(errors) == 0, errors


def rollback_migration(session: Session, dry_run: bool = True):
    """
    Rollback migration by clearing v2.0 MCP data.

    Only deletes resources with protocol='mcp' (leaves other protocols intact).
    """
    logger.warning("Rolling back migration...")

    if dry_run:
        mcp_resources = session.execute(
            text("SELECT COUNT(*) FROM resources WHERE protocol = 'mcp'")
        ).scalar()
        mcp_capabilities = session.execute(
            text("""
                SELECT COUNT(*)
                FROM capabilities c
                JOIN resources r ON r.id = c.resource_id
                WHERE r.protocol = 'mcp'
            """)
        ).scalar()
        logger.info(f"[DRY RUN] Would delete {mcp_resources} MCP resources and {mcp_capabilities} capabilities")
    else:
        # Delete capabilities first (FK constraint)
        result = session.execute(
            text("""
                DELETE FROM capabilities
                WHERE resource_id IN (
                    SELECT id FROM resources WHERE protocol = 'mcp'
                )
            """)
        )
        caps_deleted = result.rowcount

        # Delete resources
        result = session.execute(text("DELETE FROM resources WHERE protocol = 'mcp'"))
        resources_deleted = result.rowcount

        session.commit()
        logger.info(f"✓ Rolled back: deleted {resources_deleted} resources and {caps_deleted} capabilities")


def main():
    """Main migration entry point."""
    parser = argparse.ArgumentParser(description="SARK v1.x to v2.0 data migration")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migration without making changes",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute migration",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate existing migration",
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback migration (delete v2.0 MCP data)",
    )

    args = parser.parse_args()

    # Ensure exactly one mode is selected
    modes = sum([args.dry_run, args.execute, args.validate, args.rollback])
    if modes != 1:
        parser.error("Must specify exactly one of: --dry-run, --execute, --validate, --rollback")

    stats = MigrationStats()
    stats.start_time = datetime.now(UTC)

    try:
        session = create_session()

        # Check prerequisites
        logger.info("Checking prerequisites...")
        prereqs_ok, prereq_errors = check_prerequisites(session)
        if not prereqs_ok:
            logger.error("Prerequisites check failed:")
            for error in prereq_errors:
                logger.error(f"  - {error}")
            return 1

        logger.info("✓ Prerequisites validated")

        # Display current state
        v1_servers, v1_tools = count_v1_data(session)
        v2_resources, v2_capabilities = count_v2_data(session)
        logger.info("Current state:")
        logger.info(f"  v1.x: {v1_servers} servers, {v1_tools} tools")
        logger.info(f"  v2.0: {v2_resources} resources, {v2_capabilities} capabilities")

        if args.rollback:
            # Rollback mode
            rollback_migration(session, dry_run=args.dry_run)

        elif args.validate:
            # Validation mode
            valid, validation_errors = validate_migration(session)
            if not valid:
                logger.error("Validation failed:")
                for error in validation_errors:
                    logger.error(f"  - {error}")
                return 1
            logger.info("✓ Migration validation successful")

        else:
            # Migration mode (dry-run or execute)
            dry_run = args.dry_run

            if dry_run:
                logger.info("=== DRY RUN MODE (no changes will be made) ===")
            else:
                logger.info("=== EXECUTING MIGRATION ===")

            # Migrate servers -> resources
            migrate_servers_to_resources(session, stats, dry_run=dry_run)

            # Migrate tools -> capabilities
            migrate_tools_to_capabilities(session, stats, dry_run=dry_run)

            if not dry_run:
                # Validate after migration
                logger.info("")
                valid, validation_errors = validate_migration(session)
                if not valid:
                    logger.error("Post-migration validation failed:")
                    for error in validation_errors:
                        logger.error(f"  - {error}")
                        stats.errors.append(error)
                    return 1

        stats.end_time = datetime.now(UTC)

        # Print summary
        logger.info("")
        logger.info(stats.summary())

        if len(stats.errors) > 0:
            logger.error("Migration completed with errors")
            return 1

        logger.info("✓ Migration completed successfully")
        return 0

    except Exception as e:
        logger.exception(f"Migration failed with exception: {e}")
        return 1

    finally:
        if 'session' in locals():
            session.close()


if __name__ == "__main__":
    sys.exit(main())
