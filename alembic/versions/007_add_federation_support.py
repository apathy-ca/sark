"""Add federation support - cross-org governance and cost tracking.

Revision ID: 007_federation
Revises: 006_protocol_adapters
Create Date: 2025-12-02 10:00:00.000000

Creates federation and cost tracking tables:
- federation_nodes: Trusted SARK nodes for cross-org governance
- cost_tracking: Time-series cost attribution data (TimescaleDB hypertable)
- principal_budgets: Per-principal cost limits and tracking

Also enhances audit_events table with federation columns.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "007_federation"
down_revision = "006_protocol_adapters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create federation and cost tracking tables."""

    # ========================================================================
    # Federation Nodes Table
    # ========================================================================
    op.create_table(
        "federation_nodes",
        # Primary key
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),

        # Node identification
        sa.Column("node_id", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("endpoint", sa.String(500), nullable=False),

        # Trust establishment
        sa.Column("trust_anchor_cert", sa.Text, nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "trusted_since",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),

        # Rate limiting
        sa.Column("rate_limit_per_hour", sa.Integer, nullable=True, server_default="10000"),

        # Metadata
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),

        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Indexes for federation_nodes
    op.create_index("ix_federation_nodes_node_id", "federation_nodes", ["node_id"], unique=True)
    op.create_index(
        "ix_federation_nodes_enabled",
        "federation_nodes",
        ["enabled"],
        postgresql_where=sa.text("enabled = true"),
    )

    # ========================================================================
    # Cost Tracking Table (TimescaleDB Hypertable)
    # ========================================================================
    op.create_table(
        "cost_tracking",
        # Primary key
        sa.Column("id", sa.BigInteger, primary_key=True, nullable=False, autoincrement=True),

        # Temporal (hypertable partition key)
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),

        # Principal and resource
        sa.Column("principal_id", sa.String(255), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=False),
        sa.Column("capability_id", sa.String(255), nullable=False),

        # Cost data
        sa.Column("estimated_cost", sa.Numeric(10, 4), nullable=True),
        sa.Column("actual_cost", sa.Numeric(10, 4), nullable=True),

        # Additional metadata
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
    )

    # Indexes for cost_tracking
    op.create_index(
        "ix_cost_tracking_timestamp",
        "cost_tracking",
        ["timestamp"],
        postgresql_using="btree",
    )
    op.create_index("ix_cost_tracking_principal", "cost_tracking", ["principal_id"])
    op.create_index("ix_cost_tracking_resource", "cost_tracking", ["resource_id"])
    op.create_index("ix_cost_tracking_capability", "cost_tracking", ["capability_id"])

    # Convert to TimescaleDB hypertable (if extension is available)
    op.execute(
        """
        DO $$
        BEGIN
            -- Check if TimescaleDB extension exists
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
                -- Convert table to hypertable partitioned by timestamp
                PERFORM create_hypertable('cost_tracking', 'timestamp', if_not_exists => TRUE);

                -- Optional: Set retention policy (uncomment to enable)
                -- PERFORM add_retention_policy('cost_tracking', INTERVAL '365 days', if_not_exists => TRUE);

                RAISE NOTICE 'Created TimescaleDB hypertable for cost_tracking';
            ELSE
                RAISE NOTICE 'TimescaleDB extension not found, cost_tracking created as regular table';
            END IF;
        END
        $$ LANGUAGE plpgsql;
        """
    )

    # ========================================================================
    # Principal Budgets Table
    # ========================================================================
    op.create_table(
        "principal_budgets",
        # Primary key
        sa.Column("principal_id", sa.String(255), primary_key=True, nullable=False),

        # Budget limits
        sa.Column("daily_budget", sa.Numeric(10, 2), nullable=True),
        sa.Column("monthly_budget", sa.Numeric(10, 2), nullable=True),

        # Current spending
        sa.Column("daily_spent", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("monthly_spent", sa.Numeric(10, 4), nullable=False, server_default="0"),

        # Reset timestamps
        sa.Column("last_daily_reset", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_monthly_reset", sa.DateTime(timezone=True), nullable=True),

        # Currency
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),

        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Index for principal_budgets
    op.create_index("ix_principal_budgets_principal", "principal_budgets", ["principal_id"])

    # ========================================================================
    # Enhance Audit Events for Federation
    # ========================================================================

    # Add federation-related columns to existing audit_events table
    op.add_column("audit_events", sa.Column("principal_org", sa.String(255), nullable=True))
    op.add_column("audit_events", sa.Column("resource_protocol", sa.String(50), nullable=True))
    op.add_column("audit_events", sa.Column("capability_id", sa.String(255), nullable=True))
    op.add_column("audit_events", sa.Column("correlation_id", sa.String(100), nullable=True))
    op.add_column("audit_events", sa.Column("source_node", sa.String(255), nullable=True))
    op.add_column("audit_events", sa.Column("target_node", sa.String(255), nullable=True))
    op.add_column("audit_events", sa.Column("estimated_cost", sa.Numeric(10, 4), nullable=True))
    op.add_column("audit_events", sa.Column("actual_cost", sa.Numeric(10, 4), nullable=True))

    # Create indexes for new audit_events columns
    op.create_index("ix_audit_events_correlation", "audit_events", ["correlation_id"])
    op.create_index("ix_audit_events_principal_org", "audit_events", ["principal_org"])
    op.create_index("ix_audit_events_source_node", "audit_events", ["source_node"])
    op.create_index("ix_audit_events_target_node", "audit_events", ["target_node"])
    op.create_index("ix_audit_events_capability", "audit_events", ["capability_id"])

    # ========================================================================
    # Create Materialized View for Cost Analysis (Optional)
    # ========================================================================

    op.execute(
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_cost_summary AS
        SELECT
            DATE(ct.timestamp) AS date,
            ct.principal_id,
            r.protocol,
            COUNT(*) AS invocation_count,
            SUM(ct.actual_cost) AS total_cost,
            AVG(ct.actual_cost) AS avg_cost,
            MIN(ct.actual_cost) AS min_cost,
            MAX(ct.actual_cost) AS max_cost
        FROM cost_tracking ct
        LEFT JOIN capabilities c ON c.id = ct.capability_id
        LEFT JOIN resources r ON r.id = c.resource_id
        GROUP BY DATE(ct.timestamp), ct.principal_id, r.protocol;
        """
    )

    op.create_index(
        "ix_mv_daily_cost_summary_date",
        "mv_daily_cost_summary",
        ["date"],
        postgresql_using="btree",
    )
    op.create_index(
        "ix_mv_daily_cost_summary_principal",
        "mv_daily_cost_summary",
        ["principal_id"],
    )

    # ========================================================================
    # Add New Event Types to Audit Event Enum
    # ========================================================================

    # Add new event types for federation and cost tracking
    op.execute(
        """
        ALTER TYPE auditeventtype ADD VALUE IF NOT EXISTS 'cross_org_request';
        ALTER TYPE auditeventtype ADD VALUE IF NOT EXISTS 'cross_org_authorization';
        ALTER TYPE auditeventtype ADD VALUE IF NOT EXISTS 'cost_limit_exceeded';
        ALTER TYPE auditeventtype ADD VALUE IF NOT EXISTS 'federation_node_trusted';
        ALTER TYPE auditeventtype ADD VALUE IF NOT EXISTS 'federation_node_revoked';
        """
    )


def downgrade() -> None:
    """Drop federation and cost tracking tables."""

    # Drop materialized view
    op.drop_index("ix_mv_daily_cost_summary_principal", table_name="mv_daily_cost_summary")
    op.drop_index("ix_mv_daily_cost_summary_date", table_name="mv_daily_cost_summary")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_daily_cost_summary")

    # Drop audit_events federation indexes
    op.drop_index("ix_audit_events_capability", table_name="audit_events")
    op.drop_index("ix_audit_events_target_node", table_name="audit_events")
    op.drop_index("ix_audit_events_source_node", table_name="audit_events")
    op.drop_index("ix_audit_events_principal_org", table_name="audit_events")
    op.drop_index("ix_audit_events_correlation", table_name="audit_events")

    # Drop audit_events federation columns
    op.drop_column("audit_events", "actual_cost")
    op.drop_column("audit_events", "estimated_cost")
    op.drop_column("audit_events", "target_node")
    op.drop_column("audit_events", "source_node")
    op.drop_column("audit_events", "correlation_id")
    op.drop_column("audit_events", "capability_id")
    op.drop_column("audit_events", "resource_protocol")
    op.drop_column("audit_events", "principal_org")

    # Drop principal_budgets
    op.drop_index("ix_principal_budgets_principal", table_name="principal_budgets")
    op.drop_table("principal_budgets")

    # Drop cost_tracking (TimescaleDB cleanup handled automatically)
    op.drop_index("ix_cost_tracking_capability", table_name="cost_tracking")
    op.drop_index("ix_cost_tracking_resource", table_name="cost_tracking")
    op.drop_index("ix_cost_tracking_principal", table_name="cost_tracking")
    op.drop_index("ix_cost_tracking_timestamp", table_name="cost_tracking")
    op.drop_table("cost_tracking")

    # Drop federation_nodes
    op.drop_index("ix_federation_nodes_enabled", table_name="federation_nodes")
    op.drop_index("ix_federation_nodes_node_id", table_name="federation_nodes")
    op.drop_table("federation_nodes")

    # Note: We don't remove the new enum values as PostgreSQL doesn't support that
    # They will be harmless orphaned values
