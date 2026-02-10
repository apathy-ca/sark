"""Add policy rules metadata table.

Revision ID: 008_policy_rules
Revises: 007_federation_support
Create Date: 2026-02-10 00:00:00.000000

Adds structured metadata layer for policy introspection:
- policy_rules: Structured rule metadata with matchers, conditions, constraints
- Enables programmatic policy composition alongside Rego evaluation
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "008_policy_rules"
down_revision = "007_federation_support"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create policy rules metadata table."""

    # Create Effect enum type
    op.execute("CREATE TYPE effect AS ENUM ('allow', 'deny', 'constrain')")

    # ========================================================================
    # Policy Rules Table
    # ========================================================================
    op.create_table(
        "policy_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "policy_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("policy_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "effect",
            sa.Enum("allow", "deny", "constrain", name="effect"),
            nullable=False,
        ),
        sa.Column("principal_matchers", postgresql.JSON, nullable=False, server_default="[]"),
        sa.Column("resource_matchers", postgresql.JSON, nullable=False, server_default="[]"),
        sa.Column("action_matchers", postgresql.JSON, nullable=False, server_default="[]"),
        sa.Column("conditions", postgresql.JSON, nullable=False, server_default="[]"),
        sa.Column("constraints", postgresql.JSON, nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Create indexes
    op.create_index(
        "ix_policy_rules_policy_version_id",
        "policy_rules",
        ["policy_version_id"],
    )
    op.create_index(
        "ix_policy_rules_priority",
        "policy_rules",
        ["priority"],
    )


def downgrade() -> None:
    """Drop policy rules metadata table."""

    # Drop indexes
    op.drop_index("ix_policy_rules_priority", table_name="policy_rules")
    op.drop_index("ix_policy_rules_policy_version_id", table_name="policy_rules")

    # Drop table
    op.drop_table("policy_rules")

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS effect")
