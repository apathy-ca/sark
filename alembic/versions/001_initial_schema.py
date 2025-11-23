"""Initial schema with core tables.

Revision ID: 001_initial
Revises:
Create Date: 2024-11-22 12:00:00.000000

Creates the foundational tables for SARK:
- users: User accounts and authentication
- teams: Team-based access control
- user_teams: Many-to-many relationship between users and teams
- mcp_servers: MCP server registry
- mcp_tools: Tool definitions for MCP servers
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial schema tables."""

    # ========================================================================
    # Users Table
    # ========================================================================
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_admin", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("role", sa.String(50), nullable=False, server_default="developer"),
        sa.Column("extra_metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ========================================================================
    # Teams Table
    # ========================================================================
    op.create_table(
        "teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("extra_metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_teams_name", "teams", ["name"], unique=True)

    # ========================================================================
    # User-Team Association Table
    # ========================================================================
    op.create_table(
        "user_teams",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "team_id"),
    )
    op.create_index("ix_user_teams_user_id", "user_teams", ["user_id"])
    op.create_index("ix_user_teams_team_id", "user_teams", ["team_id"])

    # ========================================================================
    # MCP Servers Table
    # ========================================================================
    op.create_table(
        "mcp_servers",
        # Primary key
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),

        # Basic information
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),

        # Transport configuration
        sa.Column("transport", sa.Enum("http", "stdio", "sse", name="transporttype"), nullable=False),
        sa.Column("endpoint", sa.String(500), nullable=True),
        sa.Column("command", sa.String(500), nullable=True),

        # MCP protocol
        sa.Column("mcp_version", sa.String(20), nullable=False, server_default="2025-06-18"),
        sa.Column("capabilities", postgresql.JSONB, nullable=False, server_default="[]"),

        # Security and classification
        sa.Column(
            "sensitivity_level",
            sa.Enum("low", "medium", "high", "critical", name="sensitivitylevel"),
            nullable=False,
            server_default="medium",
        ),
        sa.Column("signature", sa.String(1000), nullable=True),

        # Status and health
        sa.Column(
            "status",
            sa.Enum("registered", "active", "inactive", "unhealthy", "decommissioned", name="serverstatus"),
            nullable=False,
            server_default="registered",
        ),
        sa.Column("health_endpoint", sa.String(500), nullable=True),
        sa.Column("last_health_check", sa.DateTime(timezone=True), nullable=True),

        # Ownership and access
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teams.id", ondelete="SET NULL"), nullable=True),

        # Service discovery
        sa.Column("consul_id", sa.String(255), unique=True, nullable=True),
        sa.Column("tags", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("extra_metadata", postgresql.JSONB, nullable=False, server_default="{}"),

        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # Indexes for mcp_servers
    op.create_index("ix_mcp_servers_name", "mcp_servers", ["name"])
    op.create_index("ix_mcp_servers_owner_id", "mcp_servers", ["owner_id"])
    op.create_index("ix_mcp_servers_team_id", "mcp_servers", ["team_id"])
    op.create_index("ix_mcp_servers_consul_id", "mcp_servers", ["consul_id"], unique=True)

    # ========================================================================
    # MCP Tools Table
    # ========================================================================
    op.create_table(
        "mcp_tools",
        # Primary key
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),

        # Relationship to server
        sa.Column("server_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False),

        # Tool definition
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("parameters_schema", postgresql.JSONB, nullable=False, server_default="{}"),

        # Security
        sa.Column(
            "sensitivity_level",
            sa.Enum("low", "medium", "high", "critical", name="sensitivitylevel"),
            nullable=False,
            server_default="medium",
        ),
        sa.Column("requires_approval", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("signature", sa.String(1000), nullable=True),

        # Metadata
        sa.Column("extra_metadata", postgresql.JSONB, nullable=False, server_default="{}"),

        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # Indexes for mcp_tools
    op.create_index("ix_mcp_tools_server_id", "mcp_tools", ["server_id"])
    op.create_index("ix_mcp_tools_name", "mcp_tools", ["name"])


def downgrade() -> None:
    """Drop all initial schema tables."""

    # Drop in reverse order due to foreign key constraints
    op.drop_index("ix_mcp_tools_name", table_name="mcp_tools")
    op.drop_index("ix_mcp_tools_server_id", table_name="mcp_tools")
    op.drop_table("mcp_tools")

    op.drop_index("ix_mcp_servers_consul_id", table_name="mcp_servers")
    op.drop_index("ix_mcp_servers_team_id", table_name="mcp_servers")
    op.drop_index("ix_mcp_servers_owner_id", table_name="mcp_servers")
    op.drop_index("ix_mcp_servers_name", table_name="mcp_servers")
    op.drop_table("mcp_servers")

    op.drop_index("ix_user_teams_team_id", table_name="user_teams")
    op.drop_index("ix_user_teams_user_id", table_name="user_teams")
    op.drop_table("user_teams")

    op.drop_index("ix_teams_name", table_name="teams")
    op.drop_table("teams")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    # Drop custom enum types
    op.execute("DROP TYPE IF EXISTS serverstatus")
    op.execute("DROP TYPE IF EXISTS sensitivitylevel")
    op.execute("DROP TYPE IF EXISTS transporttype")
