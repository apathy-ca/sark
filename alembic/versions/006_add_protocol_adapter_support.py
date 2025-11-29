"""Add protocol adapter support - resources and capabilities tables.

Revision ID: 006_protocol_adapters
Revises: 005_gateway_audit_events
Create Date: 2025-12-02 09:00:00.000000

Creates the v2.0 protocol-agnostic tables:
- resources: Universal resource abstraction (MCP, HTTP, gRPC, etc.)
- capabilities: Universal capability abstraction (tools, endpoints, methods, etc.)

These tables enable SARK to govern any protocol, not just MCP.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "006_protocol_adapters"
down_revision = "005_gateway_audit_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create v2.0 protocol adapter tables."""

    # ========================================================================
    # Resources Table
    # ========================================================================
    op.create_table(
        "resources",
        # Primary key
        sa.Column("id", sa.String(255), primary_key=True, nullable=False),

        # Basic information
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("protocol", sa.String(50), nullable=False),
        sa.Column("endpoint", sa.String(1000), nullable=False),

        # Security and classification
        sa.Column(
            "sensitivity_level",
            sa.String(20),
            nullable=False,
            server_default="medium",
        ),

        # Protocol-specific metadata (flexible JSONB)
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

    # Indexes for resources
    op.create_index("ix_resources_protocol", "resources", ["protocol"])
    op.create_index("ix_resources_sensitivity", "resources", ["sensitivity_level"])
    op.create_index("ix_resources_name", "resources", ["name"])
    op.create_index(
        "ix_resources_metadata_gin",
        "resources",
        ["metadata"],
        postgresql_using="gin",
    )

    # ========================================================================
    # Capabilities Table
    # ========================================================================
    op.create_table(
        "capabilities",
        # Primary key
        sa.Column("id", sa.String(255), primary_key=True, nullable=False),

        # Relationship to resource
        sa.Column(
            "resource_id",
            sa.String(255),
            sa.ForeignKey("resources.id", ondelete="CASCADE"),
            nullable=False,
        ),

        # Capability definition
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),

        # Schemas (JSON Schema or protocol-specific)
        sa.Column("input_schema", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("output_schema", postgresql.JSONB, nullable=False, server_default="{}"),

        # Security and classification
        sa.Column(
            "sensitivity_level",
            sa.String(20),
            nullable=False,
            server_default="medium",
        ),

        # Protocol-specific metadata
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
    )

    # Indexes for capabilities
    op.create_index("ix_capabilities_resource", "capabilities", ["resource_id"])
    op.create_index("ix_capabilities_name", "capabilities", ["name"])
    op.create_index("ix_capabilities_sensitivity", "capabilities", ["sensitivity_level"])
    op.create_index(
        "ix_capabilities_metadata_gin",
        "capabilities",
        ["metadata"],
        postgresql_using="gin",
    )

    # ========================================================================
    # Migrate v1.x Data to v2.0
    # ========================================================================

    # Note: This is a basic auto-migration. For production deployments,
    # use the dedicated migration script: scripts/migrate_v1_to_v2.py

    op.execute(
        """
        -- Migrate mcp_servers to resources
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
        ON CONFLICT (id) DO NOTHING;
        """
    )

    op.execute(
        """
        -- Migrate mcp_tools to capabilities
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
        ON CONFLICT (id) DO NOTHING;
        """
    )


def downgrade() -> None:
    """Drop v2.0 protocol adapter tables."""

    # Drop indexes
    op.drop_index("ix_capabilities_metadata_gin", table_name="capabilities")
    op.drop_index("ix_capabilities_sensitivity", table_name="capabilities")
    op.drop_index("ix_capabilities_name", table_name="capabilities")
    op.drop_index("ix_capabilities_resource", table_name="capabilities")

    op.drop_index("ix_resources_metadata_gin", table_name="resources")
    op.drop_index("ix_resources_name", table_name="resources")
    op.drop_index("ix_resources_sensitivity", table_name="resources")
    op.drop_index("ix_resources_protocol", table_name="resources")

    # Drop tables
    op.drop_table("capabilities")
    op.drop_table("resources")
