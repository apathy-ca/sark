#!/usr/bin/env python3
"""
SARK v2.0 Migration Validation Script

Comprehensive validation tool for v1.x to v2.0 data migrations.
Performs deep validation of data integrity, foreign key relationships,
and business logic constraints.

Usage:
    python scripts/validate_migration.py --full              # Full validation suite
    python scripts/validate_migration.py --quick             # Quick validation checks
    python scripts/validate_migration.py --schema            # Schema validation only
    python scripts/validate_migration.py --data              # Data validation only
    python scripts/validate_migration.py --relationships     # FK validation only
    python scripts/validate_migration.py --output report.json  # Save to file

Exit Codes:
    0 - All validations passed
    1 - Validation failures detected
    2 - Critical errors (schema missing, etc.)
"""

import argparse
import sys
import logging
import json
from datetime import datetime, UTC
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, Session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Validation issue severity."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Validation issue."""
    severity: ValidationSeverity
    check_name: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(UTC).isoformat()


@dataclass
class ValidationReport:
    """Validation report."""
    start_time: datetime
    end_time: Optional[datetime] = None
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    issues: List[ValidationIssue] = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []

    def duration_seconds(self) -> float:
        """Get validation duration."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0

    def add_issue(self, issue: ValidationIssue):
        """Add validation issue."""
        self.issues.append(issue)
        if issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]:
            self.failed_checks += 1
        else:
            self.passed_checks += 1
        self.total_checks += 1

    def has_failures(self) -> bool:
        """Check if report has any failures."""
        return any(
            issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]
            for issue in self.issues
        )

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds(),
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "issues": [
                {
                    "severity": issue.severity.value,
                    "check_name": issue.check_name,
                    "message": issue.message,
                    "details": issue.details,
                    "timestamp": issue.timestamp,
                }
                for issue in self.issues
            ],
        }


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


# ============================================================================
# Schema Validation
# ============================================================================

def validate_schema(session: Session, report: ValidationReport):
    """Validate database schema."""
    logger.info("Validating database schema...")

    inspector = inspect(session.bind)
    tables = inspector.get_table_names()

    # Required v2.0 tables
    required_tables = {
        "resources": ["id", "name", "protocol", "endpoint", "sensitivity_level", "metadata"],
        "capabilities": ["id", "resource_id", "name", "input_schema", "output_schema"],
        "federation_nodes": ["id", "node_id", "name", "endpoint", "trust_anchor_cert"],
        "cost_tracking": ["id", "timestamp", "principal_id", "resource_id", "capability_id"],
        "principal_budgets": ["principal_id", "daily_budget", "monthly_budget"],
    }

    # Check table existence
    for table_name, required_columns in required_tables.items():
        if table_name not in tables:
            report.add_issue(
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    check_name="schema.table_exists",
                    message=f"Required table '{table_name}' does not exist",
                    details={"table": table_name},
                )
            )
            continue

        # Check column existence
        columns = [col["name"] for col in inspector.get_columns(table_name)]
        missing_columns = set(required_columns) - set(columns)

        if missing_columns:
            report.add_issue(
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    check_name="schema.columns_exist",
                    message=f"Table '{table_name}' missing required columns: {missing_columns}",
                    details={"table": table_name, "missing_columns": list(missing_columns)},
                )
            )
        else:
            report.add_issue(
                ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    check_name="schema.table_valid",
                    message=f"Table '{table_name}' schema is valid",
                    details={"table": table_name, "columns": len(columns)},
                )
            )

    # Check indexes
    critical_indexes = {
        "resources": ["ix_resources_protocol", "ix_resources_metadata_gin"],
        "capabilities": ["ix_capabilities_resource", "ix_capabilities_metadata_gin"],
        "cost_tracking": ["ix_cost_tracking_timestamp", "ix_cost_tracking_principal"],
    }

    for table_name, required_indexes in critical_indexes.items():
        if table_name not in tables:
            continue

        indexes = [idx["name"] for idx in inspector.get_indexes(table_name)]
        missing_indexes = set(required_indexes) - set(indexes)

        if missing_indexes:
            report.add_issue(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    check_name="schema.indexes_exist",
                    message=f"Table '{table_name}' missing recommended indexes: {missing_indexes}",
                    details={"table": table_name, "missing_indexes": list(missing_indexes)},
                )
            )


# ============================================================================
# Data Integrity Validation
# ============================================================================

def validate_data_counts(session: Session, report: ValidationReport):
    """Validate data counts match between v1.x and v2.0."""
    logger.info("Validating data counts...")

    # Check if v1.x tables exist
    inspector = inspect(session.bind)
    tables = inspector.get_table_names()

    if "mcp_servers" not in tables or "mcp_tools" not in tables:
        report.add_issue(
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                check_name="data.v1_tables_missing",
                message="v1.x tables not found (may be expected if fully migrated)",
            )
        )
        return

    # Count v1.x data
    v1_servers = session.execute(text("SELECT COUNT(*) FROM mcp_servers")).scalar()
    v1_tools = session.execute(text("SELECT COUNT(*) FROM mcp_tools")).scalar()

    # Count v2.0 MCP data
    v2_mcp_resources = session.execute(
        text("SELECT COUNT(*) FROM resources WHERE protocol = 'mcp'")
    ).scalar()

    v2_mcp_capabilities = session.execute(
        text("""
            SELECT COUNT(*)
            FROM capabilities c
            JOIN resources r ON r.id = c.resource_id
            WHERE r.protocol = 'mcp'
        """)
    ).scalar()

    # Validate counts
    if v1_servers != v2_mcp_resources:
        report.add_issue(
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                check_name="data.server_count_mismatch",
                message=f"Server count mismatch: {v1_servers} v1.x servers != {v2_mcp_resources} v2.0 MCP resources",
                details={"v1_count": v1_servers, "v2_count": v2_mcp_resources, "diff": v1_servers - v2_mcp_resources},
            )
        )
    else:
        report.add_issue(
            ValidationIssue(
                severity=ValidationSeverity.INFO,
                check_name="data.server_count_valid",
                message=f"Server count matches: {v1_servers} servers migrated correctly",
                details={"count": v1_servers},
            )
        )

    if v1_tools != v2_mcp_capabilities:
        report.add_issue(
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                check_name="data.tool_count_mismatch",
                message=f"Tool count mismatch: {v1_tools} v1.x tools != {v2_mcp_capabilities} v2.0 MCP capabilities",
                details={"v1_count": v1_tools, "v2_count": v2_mcp_capabilities, "diff": v1_tools - v2_mcp_capabilities},
            )
        )
    else:
        report.add_issue(
            ValidationIssue(
                severity=ValidationSeverity.INFO,
                check_name="data.tool_count_valid",
                message=f"Tool count matches: {v1_tools} tools migrated correctly",
                details={"count": v1_tools},
            )
        )


def validate_data_integrity(session: Session, report: ValidationReport):
    """Validate data integrity constraints."""
    logger.info("Validating data integrity...")

    # Check for orphaned capabilities
    orphaned_capabilities = session.execute(
        text("""
            SELECT COUNT(*)
            FROM capabilities c
            WHERE NOT EXISTS (SELECT 1 FROM resources r WHERE r.id = c.resource_id)
        """)
    ).scalar()

    if orphaned_capabilities > 0:
        report.add_issue(
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                check_name="data.orphaned_capabilities",
                message=f"Found {orphaned_capabilities} capabilities without valid resource_id",
                details={"count": orphaned_capabilities},
            )
        )
    else:
        report.add_issue(
            ValidationIssue(
                severity=ValidationSeverity.INFO,
                check_name="data.no_orphaned_capabilities",
                message="No orphaned capabilities found",
            )
        )

    # Check for null required fields in resources
    null_resources = session.execute(
        text("""
            SELECT COUNT(*)
            FROM resources
            WHERE name IS NULL OR protocol IS NULL OR endpoint IS NULL
        """)
    ).scalar()

    if null_resources > 0:
        report.add_issue(
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                check_name="data.null_resource_fields",
                message=f"Found {null_resources} resources with null required fields",
                details={"count": null_resources},
            )
        )
    else:
        report.add_issue(
            ValidationIssue(
                severity=ValidationSeverity.INFO,
                check_name="data.no_null_resources",
                message="All resources have required fields populated",
            )
        )

    # Check for null required fields in capabilities
    null_capabilities = session.execute(
        text("""
            SELECT COUNT(*)
            FROM capabilities
            WHERE name IS NULL OR resource_id IS NULL
        """)
    ).scalar()

    if null_capabilities > 0:
        report.add_issue(
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                check_name="data.null_capability_fields",
                message=f"Found {null_capabilities} capabilities with null required fields",
                details={"count": null_capabilities},
            )
        )
    else:
        report.add_issue(
            ValidationIssue(
                severity=ValidationSeverity.INFO,
                check_name="data.no_null_capabilities",
                message="All capabilities have required fields populated",
            )
        )


def validate_metadata_migration(session: Session, report: ValidationReport):
    """Validate metadata was correctly migrated to JSONB."""
    logger.info("Validating metadata migration...")

    # Sample check: Verify metadata contains expected v1.x fields
    result = session.execute(
        text("""
            SELECT COUNT(*)
            FROM resources
            WHERE protocol = 'mcp'
              AND metadata IS NOT NULL
              AND metadata != '{}'::jsonb
        """)
    ).scalar()

    total_mcp = session.execute(
        text("SELECT COUNT(*) FROM resources WHERE protocol = 'mcp'")
    ).scalar()

    if total_mcp > 0:
        metadata_percentage = (result / total_mcp) * 100

        if metadata_percentage < 50:
            report.add_issue(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    check_name="data.metadata_sparse",
                    message=f"Only {metadata_percentage:.1f}% of MCP resources have metadata populated",
                    details={"with_metadata": result, "total": total_mcp, "percentage": metadata_percentage},
                )
            )
        else:
            report.add_issue(
                ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    check_name="data.metadata_populated",
                    message=f"{metadata_percentage:.1f}% of MCP resources have metadata populated",
                    details={"with_metadata": result, "total": total_mcp, "percentage": metadata_percentage},
                )
            )


# ============================================================================
# Relationship Validation
# ============================================================================

def validate_foreign_keys(session: Session, report: ValidationReport):
    """Validate foreign key relationships."""
    logger.info("Validating foreign key relationships...")

    # Check capabilities -> resources FK
    result = session.execute(
        text("""
            SELECT c.id
            FROM capabilities c
            LEFT JOIN resources r ON r.id = c.resource_id
            WHERE r.id IS NULL
            LIMIT 10
        """)
    )
    broken_fks = result.fetchall()

    if broken_fks:
        report.add_issue(
            ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                check_name="relationships.broken_fk_capabilities_resources",
                message=f"Found {len(broken_fks)} capabilities with broken resource_id foreign keys",
                details={"sample_ids": [row[0] for row in broken_fks[:5]]},
            )
        )
    else:
        report.add_issue(
            ValidationIssue(
                severity=ValidationSeverity.INFO,
                check_name="relationships.fk_capabilities_resources_valid",
                message="All capability->resource foreign keys are valid",
            )
        )

    # Check cascade delete behavior (test metadata only)
    inspector = inspect(session.bind)
    fks = inspector.get_foreign_keys("capabilities")

    cascade_configured = any(
        fk.get("options", {}).get("ondelete") == "CASCADE"
        for fk in fks
        if "resource_id" in fk.get("constrained_columns", [])
    )

    if cascade_configured:
        report.add_issue(
            ValidationIssue(
                severity=ValidationSeverity.INFO,
                check_name="relationships.cascade_delete_configured",
                message="CASCADE DELETE is properly configured for capabilities->resources",
            )
        )
    else:
        report.add_issue(
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                check_name="relationships.cascade_delete_missing",
                message="CASCADE DELETE may not be configured for capabilities->resources",
            )
        )


# ============================================================================
# Business Logic Validation
# ============================================================================

def validate_business_logic(session: Session, report: ValidationReport):
    """Validate business logic constraints."""
    logger.info("Validating business logic...")

    # Check for valid sensitivity levels
    result = session.execute(
        text("""
            SELECT COUNT(*)
            FROM resources
            WHERE sensitivity_level NOT IN ('low', 'medium', 'high', 'critical')
        """)
    ).scalar()

    if result > 0:
        report.add_issue(
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                check_name="business.invalid_sensitivity_levels",
                message=f"Found {result} resources with invalid sensitivity levels",
                details={"count": result},
            )
        )
    else:
        report.add_issue(
            ValidationIssue(
                severity=ValidationSeverity.INFO,
                check_name="business.sensitivity_levels_valid",
                message="All resource sensitivity levels are valid",
            )
        )

    # Check for valid protocols
    result = session.execute(
        text("""
            SELECT DISTINCT protocol
            FROM resources
            WHERE protocol NOT IN ('mcp', 'http', 'grpc', 'graphql', 'websocket')
        """)
    )
    unknown_protocols = [row[0] for row in result.fetchall()]

    if unknown_protocols:
        report.add_issue(
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                check_name="business.unknown_protocols",
                message=f"Found resources with unknown protocols: {unknown_protocols}",
                details={"protocols": unknown_protocols},
            )
        )
    else:
        report.add_issue(
            ValidationIssue(
                severity=ValidationSeverity.INFO,
                check_name="business.protocols_valid",
                message="All resource protocols are recognized",
            )
        )


# ============================================================================
# Main Validation Flow
# ============================================================================

def run_validation_suite(session: Session, mode: str = "full") -> ValidationReport:
    """Run validation suite."""
    logger.info(f"Starting validation suite: {mode} mode")

    report = ValidationReport(start_time=datetime.now(UTC))

    if mode in ["full", "quick", "schema"]:
        validate_schema(session, report)

    if mode in ["full", "data"]:
        validate_data_counts(session, report)
        validate_data_integrity(session, report)
        validate_metadata_migration(session, report)

    if mode in ["full", "quick", "relationships"]:
        validate_foreign_keys(session, report)

    if mode in ["full", "quick"]:
        validate_business_logic(session, report)

    report.end_time = datetime.now(UTC)
    return report


def print_report(report: ValidationReport):
    """Print validation report."""
    print("\n" + "=" * 80)
    print("SARK v2.0 Migration Validation Report")
    print("=" * 80)
    print(f"Started:  {report.start_time.isoformat()}")
    print(f"Finished: {report.end_time.isoformat() if report.end_time else 'N/A'}")
    print(f"Duration: {report.duration_seconds():.2f} seconds")
    print(f"Total checks: {report.total_checks}")
    print(f"Passed: {report.passed_checks}")
    print(f"Failed: {report.failed_checks}")
    print()

    # Group issues by severity
    by_severity = {}
    for issue in report.issues:
        severity = issue.severity.value
        if severity not in by_severity:
            by_severity[severity] = []
        by_severity[severity].append(issue)

    # Print critical issues first
    for severity in ["critical", "error", "warning", "info"]:
        if severity not in by_severity:
            continue

        issues = by_severity[severity]
        print(f"\n{severity.upper()} ({len(issues)} issues)")
        print("-" * 80)

        for issue in issues:
            print(f"  [{issue.check_name}] {issue.message}")
            if issue.details:
                print(f"    Details: {json.dumps(issue.details, indent=6)}")

    print("\n" + "=" * 80)

    # Overall status
    if report.has_failures():
        print("STATUS: ❌ VALIDATION FAILED")
        print("Please review and fix the errors above before proceeding.")
    else:
        print("STATUS: ✅ VALIDATION PASSED")
        print("Migration appears to be successful!")

    print("=" * 80 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="SARK v2.0 migration validation")
    parser.add_argument("--full", action="store_true", help="Run full validation suite (default)")
    parser.add_argument("--quick", action="store_true", help="Run quick validation checks")
    parser.add_argument("--schema", action="store_true", help="Schema validation only")
    parser.add_argument("--data", action="store_true", help="Data validation only")
    parser.add_argument("--relationships", action="store_true", help="FK validation only")
    parser.add_argument("--output", type=str, help="Output JSON report to file")

    args = parser.parse_args()

    # Determine mode
    if args.quick:
        mode = "quick"
    elif args.schema:
        mode = "schema"
    elif args.data:
        mode = "data"
    elif args.relationships:
        mode = "relationships"
    else:
        mode = "full"

    try:
        session = create_session()
        report = run_validation_suite(session, mode=mode)

        # Print report
        print_report(report)

        # Save to file if requested
        if args.output:
            with open(args.output, "w") as f:
                json.dump(report.to_dict(), f, indent=2)
            logger.info(f"Report saved to {args.output}")

        # Exit with appropriate code
        if report.has_failures():
            return 1
        else:
            return 0

    except Exception as e:
        logger.exception(f"Validation failed with exception: {e}")
        return 2

    finally:
        if 'session' in locals():
            session.close()


if __name__ == "__main__":
    sys.exit(main())
