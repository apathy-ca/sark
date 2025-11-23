"""Add policy management tables.

Revision ID: 003_policies
Revises: 002_api_keys
Create Date: 2024-11-22 13:00:00.000000

Creates tables for OPA policy management:
- policies: Policy definitions
- policy_versions: Versioned policy content for rollback
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "003_policies"
down_revision = "002_api_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create policy management tables."""

    # Create enum types first
    op.execute("CREATE TYPE policytype AS ENUM ('authorization', 'validation', 'transformation', 'audit')")
    op.execute("CREATE TYPE policystatus AS ENUM ('draft', 'active', 'inactive', 'deprecated')")

    # ========================================================================
    # Policies Table
    # ========================================================================
    op.create_table(
        "policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("policy_type", sa.Enum("authorization", "validation", "transformation", "audit", name="policytype"), nullable=False, server_default="authorization"),
        sa.Column("status", sa.Enum("draft", "active", "inactive", "deprecated", name="policystatus"), nullable=False, server_default="draft"),
        sa.Column("current_version_id", postgresql.UUID(as_uuid=True), nullable=True),  # FK added after policy_versions
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_policies_name", "policies", ["name"], unique=True)

    # ========================================================================
    # Policy Versions Table
    # ========================================================================
    op.create_table(
        "policy_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("policies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("tested", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index("ix_policy_versions_policy_id", "policy_versions", ["policy_id"])
    op.create_index("ix_policy_versions_version", "policy_versions", ["policy_id", "version"], unique=True)

    # Add foreign key constraint for current_version_id after policy_versions table exists
    op.create_foreign_key("fk_policies_current_version", "policies", "policy_versions", ["current_version_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    """Drop policy management tables."""

    # Drop foreign key first
    op.drop_constraint("fk_policies_current_version", "policies", type_="foreignkey")

    op.drop_index("ix_policy_versions_version", table_name="policy_versions")
    op.drop_index("ix_policy_versions_policy_id", table_name="policy_versions")
    op.drop_table("policy_versions")

    op.drop_index("ix_policies_name", table_name="policies")
    op.drop_table("policies")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS policystatus")
    op.execute("DROP TYPE IF EXISTS policytype")
