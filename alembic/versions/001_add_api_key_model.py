"""Add API key model.

Revision ID: 001_api_keys
Revises:
Create Date: 2025-11-27 14:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001_api_keys"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create api_keys table."""
    op.create_table(
        "api_keys",
        # Primary key
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        # Ownership
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Key metadata
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        # Key credentials
        sa.Column("key_prefix", sa.String(16), nullable=False, unique=True),
        sa.Column("key_hash", sa.String(255), nullable=False),
        # Permissions
        sa.Column(
            "scopes",
            postgresql.ARRAY(sa.String),
            nullable=False,
            server_default="{}",
            comment="List of permission scopes (e.g., 'server:read', 'server:write')",
        ),
        # Rate limiting
        sa.Column(
            "rate_limit",
            sa.Integer,
            nullable=False,
            server_default="1000",
            comment="Maximum requests per minute",
        ),
        # Status and lifecycle
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("expires_at", sa.DateTime, nullable=True),
        # Usage tracking
        sa.Column("last_used_at", sa.DateTime, nullable=True),
        sa.Column("last_used_ip", sa.String(45), nullable=True),
        sa.Column("usage_count", sa.Integer, nullable=False, server_default="0"),
        # Audit timestamps
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.Column("revoked_at", sa.DateTime, nullable=True),
        sa.Column("revoked_by", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Create indexes
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
    op.create_index("ix_api_keys_team_id", "api_keys", ["team_id"])
    op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"], unique=True)
    op.create_index("ix_api_keys_is_active", "api_keys", ["is_active"])
    op.create_index("ix_api_keys_expires_at", "api_keys", ["expires_at"])


def downgrade() -> None:
    """Drop api_keys table."""
    op.drop_index("ix_api_keys_expires_at", table_name="api_keys")
    op.drop_index("ix_api_keys_is_active", table_name="api_keys")
    op.drop_index("ix_api_keys_key_prefix", table_name="api_keys")
    op.drop_index("ix_api_keys_team_id", table_name="api_keys")
    op.drop_index("ix_api_keys_user_id", table_name="api_keys")
    op.drop_table("api_keys")
