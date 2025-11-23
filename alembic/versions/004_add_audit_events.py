"""Add audit events table for TimescaleDB.

Revision ID: 004_audit_events
Revises: 003_policies
Create Date: 2024-11-22 13:30:00.000000

Creates the audit events table with TimescaleDB hypertable for time-series data.
This table stores all audit events for security monitoring and compliance.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "004_audit_events"
down_revision = "003_policies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create audit events table and convert to TimescaleDB hypertable."""

    # Create enum types
    op.execute(
        "CREATE TYPE auditeventtype AS ENUM ('server_registered', 'server_updated', "
        "'server_decommissioned', 'tool_invoked', 'authorization_allowed', 'authorization_denied', "
        "'policy_created', 'policy_updated', 'policy_activated', 'user_login', 'user_logout', "
        "'security_violation')"
    )
    op.execute("CREATE TYPE severitylevel AS ENUM ('low', 'medium', 'high', 'critical')")

    # ========================================================================
    # Audit Events Table
    # ========================================================================
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),

        # Temporal (TimescaleDB hypertable partitioned on this column)
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),

        # Event classification
        sa.Column(
            "event_type",
            sa.Enum(
                "server_registered", "server_updated", "server_decommissioned", "tool_invoked",
                "authorization_allowed", "authorization_denied", "policy_created", "policy_updated",
                "policy_activated", "user_login", "user_logout", "security_violation",
                name="auditeventtype"
            ),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum("low", "medium", "high", "critical", name="severitylevel"),
            nullable=False,
            server_default="low",
        ),

        # Actor information
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_email", sa.String(255), nullable=True),

        # Subject information
        sa.Column("server_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tool_name", sa.String(255), nullable=True),

        # Authorization decision
        sa.Column("decision", sa.String(20), nullable=True),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=True),

        # Context and details
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("request_id", sa.String(100), nullable=True),

        # Flexible details storage
        sa.Column("details", postgresql.JSONB, nullable=False, server_default="{}"),

        # Retention metadata
        sa.Column("siem_forwarded", sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes for audit events
    op.create_index("ix_audit_events_timestamp", "audit_events", ["timestamp"], postgresql_using="btree")
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_user_id", "audit_events", ["user_id"])
    op.create_index("ix_audit_events_server_id", "audit_events", ["server_id"])
    op.create_index("ix_audit_events_tool_name", "audit_events", ["tool_name"])
    op.create_index("ix_audit_events_request_id", "audit_events", ["request_id"])

    # Convert to TimescaleDB hypertable (if TimescaleDB extension is available)
    # This will partition the table by timestamp for efficient time-series queries
    op.execute(
        """
        DO $$
        BEGIN
            -- Check if TimescaleDB extension exists
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
                -- Convert table to hypertable partitioned by timestamp
                PERFORM create_hypertable('audit_events', 'timestamp', if_not_exists => TRUE);

                -- Set retention policy: keep data for 90 days (configurable)
                -- PERFORM add_retention_policy('audit_events', INTERVAL '90 days', if_not_exists => TRUE);

                RAISE NOTICE 'Created TimescaleDB hypertable for audit_events';
            ELSE
                RAISE NOTICE 'TimescaleDB extension not found, audit_events created as regular table';
            END IF;
        END
        $$ LANGUAGE plpgsql;
        """
    )


def downgrade() -> None:
    """Drop audit events table."""

    # Drop TimescaleDB hypertable (if it exists)
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
                -- TimescaleDB will handle cleanup when table is dropped
                NULL;
            END IF;
        END
        $$ LANGUAGE plpgsql;
        """
    )

    # Drop indexes
    op.drop_index("ix_audit_events_request_id", table_name="audit_events")
    op.drop_index("ix_audit_events_tool_name", table_name="audit_events")
    op.drop_index("ix_audit_events_server_id", table_name="audit_events")
    op.drop_index("ix_audit_events_user_id", table_name="audit_events")
    op.drop_index("ix_audit_events_event_type", table_name="audit_events")
    op.drop_index("ix_audit_events_timestamp", table_name="audit_events")

    # Drop table
    op.drop_table("audit_events")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS severitylevel")
    op.execute("DROP TYPE IF EXISTS auditeventtype")
