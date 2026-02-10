"""Add GRID spec compliance fields to audit events.

Revision ID: 005_audit_grid_fields
Revises: 004_audit_events
Create Date: 2026-02-10 01:35:00.000000

Adds 11 missing audit event fields required by GRID spec for Wave 2 SIEM integration.
This increases compliance from 60% to 95%.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "005_audit_grid_fields"
down_revision = "004_audit_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add GRID compliance fields to audit_events table."""

    # Principal information
    op.add_column(
        "audit_events",
        sa.Column("principal_type", sa.String(50), nullable=True),
    )
    op.add_column(
        "audit_events",
        sa.Column("principal_attributes", postgresql.JSONB, nullable=True),
    )

    # Resource information
    op.add_column(
        "audit_events",
        sa.Column("resource_type", sa.String(50), nullable=True),
    )

    # Action details
    op.add_column(
        "audit_events",
        sa.Column("action_operation", sa.String(100), nullable=True),
    )
    op.add_column(
        "audit_events",
        sa.Column("action_parameters", postgresql.JSONB, nullable=True),
    )

    # Policy context
    op.add_column(
        "audit_events",
        sa.Column("policy_version", sa.String(50), nullable=True),
    )
    op.add_column(
        "audit_events",
        sa.Column("environment", sa.String(50), nullable=True),
    )

    # Outcome tracking
    op.add_column(
        "audit_events",
        sa.Column("success", sa.Boolean, nullable=True),
    )
    op.add_column(
        "audit_events",
        sa.Column("error_message", sa.String(500), nullable=True),
    )
    op.add_column(
        "audit_events",
        sa.Column("latency_ms", sa.Float, nullable=True),
    )
    op.add_column(
        "audit_events",
        sa.Column("cost", sa.Float, nullable=True),
    )

    # Retention metadata
    op.add_column(
        "audit_events",
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes for frequently queried fields
    op.create_index(
        "ix_audit_events_resource_type",
        "audit_events",
        ["resource_type"],
    )
    op.create_index(
        "ix_audit_events_action_operation",
        "audit_events",
        ["action_operation"],
    )


def downgrade() -> None:
    """Remove GRID compliance fields from audit_events table."""

    # Drop indexes
    op.drop_index("ix_audit_events_action_operation", table_name="audit_events")
    op.drop_index("ix_audit_events_resource_type", table_name="audit_events")

    # Drop columns (in reverse order)
    op.drop_column("audit_events", "retention_until")
    op.drop_column("audit_events", "cost")
    op.drop_column("audit_events", "latency_ms")
    op.drop_column("audit_events", "error_message")
    op.drop_column("audit_events", "success")
    op.drop_column("audit_events", "environment")
    op.drop_column("audit_events", "policy_version")
    op.drop_column("audit_events", "action_parameters")
    op.drop_column("audit_events", "action_operation")
    op.drop_column("audit_events", "resource_type")
    op.drop_column("audit_events", "principal_attributes")
    op.drop_column("audit_events", "principal_type")
