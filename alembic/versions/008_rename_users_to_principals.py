"""Rename users to principals and add principal type system.

Revision ID: 008_principals
Revises: 007_federation
Create Date: 2026-02-10 00:00:00.000000

Renames users table to principals and adds multi-principal support:
- Renames users table to principals
- Renames user_teams table to principal_teams
- Adds principal_type enum (human/agent/service/device)
- Adds identity_token_type field
- Adds revoked_at timestamp field
- Updates all foreign key references
- Sets default principal_type='human' for existing records
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "008_principals"
down_revision = "007_federation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Rename users to principals and add type system."""

    # ========================================================================
    # Create PrincipalType enum
    # ========================================================================
    principal_type_enum = postgresql.ENUM(
        "human", "agent", "service", "device",
        name="principaltype",
        create_type=True
    )
    principal_type_enum.create(op.get_bind(), checkfirst=True)

    # ========================================================================
    # Rename users table to principals
    # ========================================================================
    op.rename_table("users", "principals")

    # Rename the existing index
    op.execute("ALTER INDEX ix_users_email RENAME TO ix_principals_email")

    # ========================================================================
    # Add new columns to principals table
    # ========================================================================
    # Add principal_type with default 'human' for existing records
    op.add_column(
        "principals",
        sa.Column(
            "principal_type",
            postgresql.ENUM("human", "agent", "service", "device", name="principaltype"),
            nullable=False,
            server_default="human"
        )
    )

    # Add identity_token_type with default 'jwt' for existing records
    op.add_column(
        "principals",
        sa.Column(
            "identity_token_type",
            sa.String(50),
            nullable=False,
            server_default="jwt"
        )
    )

    # Add revoked_at (nullable)
    op.add_column(
        "principals",
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True
        )
    )

    # Create index on principal_type for efficient queries
    op.create_index("ix_principals_principal_type", "principals", ["principal_type"])

    # ========================================================================
    # Rename user_teams table to principal_teams
    # ========================================================================
    op.rename_table("user_teams", "principal_teams")

    # Rename the column in principal_teams
    op.alter_column("principal_teams", "user_id", new_column_name="principal_id")

    # Rename the existing indexes
    op.execute("ALTER INDEX ix_user_teams_user_id RENAME TO ix_principal_teams_principal_id")
    op.execute("ALTER INDEX ix_user_teams_team_id RENAME TO ix_principal_teams_team_id")

    # ========================================================================
    # Update foreign keys in other tables
    # ========================================================================
    # Note: The ForeignKey constraints are named automatically by SQLAlchemy
    # We need to drop and recreate them to point to the new table name

    # Update mcp_servers.owner_id foreign key
    op.drop_constraint("mcp_servers_owner_id_fkey", "mcp_servers", type_="foreignkey")
    op.create_foreign_key(
        "mcp_servers_owner_id_fkey",
        "mcp_servers",
        "principals",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL"
    )

    # Update policies.created_by foreign key
    op.drop_constraint("policies_created_by_fkey", "policies", type_="foreignkey")
    op.create_foreign_key(
        "policies_created_by_fkey",
        "policies",
        "principals",
        ["created_by"],
        ["id"],
        ondelete="SET NULL"
    )

    # Update principal_teams foreign key
    op.drop_constraint("user_teams_user_id_fkey", "principal_teams", type_="foreignkey")
    op.create_foreign_key(
        "principal_teams_principal_id_fkey",
        "principal_teams",
        "principals",
        ["principal_id"],
        ["id"],
        ondelete="CASCADE"
    )


def downgrade() -> None:
    """Revert principals back to users."""

    # ========================================================================
    # Revert foreign keys
    # ========================================================================
    # Revert principal_teams foreign key
    op.drop_constraint("principal_teams_principal_id_fkey", "principal_teams", type_="foreignkey")
    op.create_foreign_key(
        "user_teams_user_id_fkey",
        "principal_teams",
        "principals",
        ["principal_id"],
        ["id"],
        ondelete="CASCADE"
    )

    # Revert policies.created_by foreign key (temporarily point to principals before rename)
    op.drop_constraint("policies_created_by_fkey", "policies", type_="foreignkey")
    op.create_foreign_key(
        "policies_created_by_fkey",
        "policies",
        "principals",
        ["created_by"],
        ["id"],
        ondelete="SET NULL"
    )

    # Revert mcp_servers.owner_id foreign key
    op.drop_constraint("mcp_servers_owner_id_fkey", "mcp_servers", type_="foreignkey")
    op.create_foreign_key(
        "mcp_servers_owner_id_fkey",
        "mcp_servers",
        "principals",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL"
    )

    # ========================================================================
    # Revert principal_teams table rename
    # ========================================================================
    # Rename indexes back
    op.execute("ALTER INDEX ix_principal_teams_principal_id RENAME TO ix_user_teams_user_id")
    op.execute("ALTER INDEX ix_principal_teams_team_id RENAME TO ix_user_teams_team_id")

    # Rename column back
    op.alter_column("principal_teams", "principal_id", new_column_name="user_id")

    # Rename table back
    op.rename_table("principal_teams", "user_teams")

    # ========================================================================
    # Remove new columns from principals
    # ========================================================================
    op.drop_index("ix_principals_principal_type", "principals")
    op.drop_column("principals", "revoked_at")
    op.drop_column("principals", "identity_token_type")
    op.drop_column("principals", "principal_type")

    # ========================================================================
    # Rename principals table back to users
    # ========================================================================
    op.execute("ALTER INDEX ix_principals_email RENAME TO ix_users_email")
    op.rename_table("principals", "users")

    # Update foreign keys to point to users table
    op.drop_constraint("policies_created_by_fkey", "policies", type_="foreignkey")
    op.create_foreign_key(
        "policies_created_by_fkey",
        "policies",
        "users",
        ["created_by"],
        ["id"],
        ondelete="SET NULL"
    )

    op.drop_constraint("mcp_servers_owner_id_fkey", "mcp_servers", type_="foreignkey")
    op.create_foreign_key(
        "mcp_servers_owner_id_fkey",
        "mcp_servers",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL"
    )

    op.drop_constraint("user_teams_user_id_fkey", "user_teams", type_="foreignkey")
    op.create_foreign_key(
        "user_teams_user_id_fkey",
        "user_teams",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE"
    )

    # ========================================================================
    # Drop PrincipalType enum
    # ========================================================================
    principal_type_enum = postgresql.ENUM(
        "human", "agent", "service", "device",
        name="principaltype"
    )
    principal_type_enum.drop(op.get_bind(), checkfirst=True)
