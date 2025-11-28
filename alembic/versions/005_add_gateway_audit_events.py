"""Add gateway_audit_events table for Gateway integration.

Revision ID: 005_gateway_audit
Revises: 004_audit_events
Create Date: 2024-11-28 00:30:00.000000

Creates the gateway_audit_events table for Gateway-specific audit logging.
This table stores all Gateway authorization decisions, tool invocations,
and A2A communication events for compliance and security monitoring.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "005_gateway_audit"
down_revision = "004_audit_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create gateway_audit_events table."""

    # ========================================================================
    # Gateway Audit Events Table
    # ========================================================================
    op.create_table(
        "gateway_audit_events",
        # Primary key
        sa.Column("id", sa.String(), primary_key=True, nullable=False),

        # Event classification
        sa.Column("event_type", sa.String(50), nullable=False),

        # Actor information (either user or agent)
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("agent_id", sa.String(), nullable=True),

        # Target information
        sa.Column("server_name", sa.String(), nullable=True),
        sa.Column("tool_name", sa.String(), nullable=True),

        # Authorization decision
        sa.Column("decision", sa.String(10), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),

        # Temporal information
        sa.Column("timestamp", sa.DateTime(), nullable=False),

        # Request tracking
        sa.Column("gateway_request_id", sa.String(), nullable=False),

        # Flexible metadata storage
        sa.Column("metadata", postgresql.JSONB(), nullable=True, server_default="{}"),

        # Created timestamp for record keeping
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Create indexes for common queries
    op.create_index(
        "ix_gateway_audit_user_id",
        "gateway_audit_events",
        ["user_id"],
    )

    op.create_index(
        "ix_gateway_audit_timestamp",
        "gateway_audit_events",
        ["timestamp"],
        postgresql_using="btree",
    )

    op.create_index(
        "ix_gateway_audit_decision",
        "gateway_audit_events",
        ["decision"],
    )

    op.create_index(
        "ix_gateway_audit_event_type",
        "gateway_audit_events",
        ["event_type"],
    )

    op.create_index(
        "ix_gateway_audit_server_name",
        "gateway_audit_events",
        ["server_name"],
    )

    op.create_index(
        "ix_gateway_audit_tool_name",
        "gateway_audit_events",
        ["tool_name"],
    )

    op.create_index(
        "ix_gateway_audit_request_id",
        "gateway_audit_events",
        ["gateway_request_id"],
    )

    # Convert to TimescaleDB hypertable if available (for time-series optimization)
    op.execute(
        """
        DO $$
        BEGIN
            -- Check if TimescaleDB extension exists
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
                -- Convert table to hypertable partitioned by timestamp
                PERFORM create_hypertable(
                    'gateway_audit_events',
                    'timestamp',
                    if_not_exists => TRUE
                );

                RAISE NOTICE 'Created TimescaleDB hypertable for gateway_audit_events';
            ELSE
                RAISE NOTICE 'TimescaleDB extension not found, gateway_audit_events created as regular table';
            END IF;
        END
        $$ LANGUAGE plpgsql;
        """
    )


def downgrade() -> None:
    """Drop gateway_audit_events table."""

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
    op.drop_index("ix_gateway_audit_request_id", table_name="gateway_audit_events")
    op.drop_index("ix_gateway_audit_tool_name", table_name="gateway_audit_events")
    op.drop_index("ix_gateway_audit_server_name", table_name="gateway_audit_events")
    op.drop_index("ix_gateway_audit_event_type", table_name="gateway_audit_events")
    op.drop_index("ix_gateway_audit_decision", table_name="gateway_audit_events")
    op.drop_index("ix_gateway_audit_timestamp", table_name="gateway_audit_events")
    op.drop_index("ix_gateway_audit_user_id", table_name="gateway_audit_events")

    # Drop table
    op.drop_table("gateway_audit_events")
