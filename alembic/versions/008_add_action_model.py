"""Add Action model - formalize action abstraction per GRID spec.

Revision ID: 008_action_model
Revises: 007_federation
Create Date: 2025-02-10 01:00:00.000000

Creates actions table to formalize the Action abstraction as a first-class model
per GRID v0.1 specification. Actions represent operations that principals perform
on resources, with standardized OperationType enum (READ, WRITE, EXECUTE, CONTROL,
MANAGE, AUDIT).

This addresses the gap identified in GRID_GAP_ANALYSIS_AND_IMPLEMENTATION_NOTES.md:
"⚠️ Action model not explicitly defined in spec"
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "008_action_model"
down_revision = "007_federation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create actions table."""

    # ========================================================================
    # OperationType Enum
    # ========================================================================
    operation_type_enum = postgresql.ENUM(
        "read",
        "write",
        "execute",
        "control",
        "manage",
        "audit",
        name="operationtype",
        create_type=True,
    )
    operation_type_enum.create(op.get_bind(), checkfirst=True)

    # ========================================================================
    # Actions Table
    # ========================================================================
    op.create_table(
        "actions",
        # Primary key
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        # Core action fields per GRID specification
        sa.Column("resource_id", sa.String(255), nullable=False),
        sa.Column(
            "operation",
            operation_type_enum,
            nullable=False,
        ),
        # Action parameters and context
        sa.Column("parameters", postgresql.JSONB, nullable=False, server_default="{}"),
        # Context fields (optimized for queries)
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("ip_address", sa.String(45), nullable=True),  # IPv6 max length
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("request_id", sa.String(100), nullable=True),
        sa.Column("environment", sa.String(50), nullable=True),
        # Additional context stored as flexible JSON
        sa.Column("context_metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        # Actor information (principal who performed the action)
        sa.Column("principal_id", sa.String(255), nullable=True),
        # Authorization decision
        sa.Column("authorized", sa.String(20), nullable=True),  # "allow" or "deny"
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Performance metadata
        sa.Column("duration_ms", sa.String(20), nullable=True),
    )

    # ========================================================================
    # Indexes for actions table
    # ========================================================================
    # Primary query patterns: by resource, operation, timestamp, principal
    op.create_index("ix_actions_resource_id", "actions", ["resource_id"])
    op.create_index("ix_actions_operation", "actions", ["operation"])
    op.create_index("ix_actions_timestamp", "actions", ["timestamp"])
    op.create_index("ix_actions_principal_id", "actions", ["principal_id"])
    op.create_index("ix_actions_request_id", "actions", ["request_id"])
    op.create_index("ix_actions_ip_address", "actions", ["ip_address"])
    op.create_index("ix_actions_environment", "actions", ["environment"])

    # Composite indexes for common query patterns
    op.create_index(
        "ix_actions_resource_operation", "actions", ["resource_id", "operation", "timestamp"]
    )
    op.create_index(
        "ix_actions_principal_operation", "actions", ["principal_id", "operation", "timestamp"]
    )

    # ========================================================================
    # TimescaleDB Hypertable (Optional)
    # ========================================================================
    # Note: If TimescaleDB is available, convert to hypertable for time-series optimization
    # This is optional and will gracefully skip if TimescaleDB extension is not available
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
            ) THEN
                PERFORM create_hypertable('actions', 'timestamp',
                    chunk_time_interval => INTERVAL '1 day',
                    if_not_exists => TRUE
                );
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    """Drop actions table and enum."""

    # Drop table
    op.drop_table("actions")

    # Drop enum type
    operation_type_enum = postgresql.ENUM(
        "read",
        "write",
        "execute",
        "control",
        "manage",
        "audit",
        name="operationtype",
    )
    operation_type_enum.drop(op.get_bind(), checkfirst=True)
