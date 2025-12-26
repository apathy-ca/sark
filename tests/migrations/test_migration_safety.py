"""
Migration safety tests for SARK v2.0.

These tests ensure that:
1. Migrations can be applied without errors
2. Data is migrated correctly from v1.x to v2.0
3. No data loss occurs during migration
4. Rollback works correctly
5. Foreign key relationships are maintained
6. Indexes are created correctly
"""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from sark.db.base import Base
from sark.models.base import Capability, CostTracking, FederationNode, PrincipalBudget, Resource
from sark.models.mcp_server import MCPServer, MCPTool, SensitivityLevel, ServerStatus, TransportType


@pytest.fixture
def test_db_url():
    """Test database URL."""
    import os

    return os.getenv("TEST_DATABASE_URL", "postgresql://sark:sark@localhost:5432/sark_test")


@pytest.fixture
def engine(test_db_url):
    """Create test database engine."""
    return create_engine(test_db_url, echo=False)


@pytest.fixture
def session(engine):
    """Create test database session."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def clean_db(engine):
    """Drop and recreate all tables."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


class TestMigration006ProtocolAdapters:
    """Test migration 006: Protocol adapter support."""

    def test_resources_table_exists(self, session):
        """Test that resources table is created."""
        inspector = inspect(session.bind)
        assert "resources" in inspector.get_table_names()

    def test_capabilities_table_exists(self, session):
        """Test that capabilities table is created."""
        inspector = inspect(session.bind)
        assert "capabilities" in inspector.get_table_names()

    def test_resources_indexes(self, session):
        """Test that resource indexes are created."""
        inspector = inspect(session.bind)
        indexes = [idx["name"] for idx in inspector.get_indexes("resources")]

        assert "ix_resources_protocol" in indexes
        assert "ix_resources_sensitivity" in indexes
        assert "ix_resources_name" in indexes
        assert "ix_resources_metadata_gin" in indexes

    def test_capabilities_indexes(self, session):
        """Test that capability indexes are created."""
        inspector = inspect(session.bind)
        indexes = [idx["name"] for idx in inspector.get_indexes("capabilities")]

        assert "ix_capabilities_resource" in indexes
        assert "ix_capabilities_name" in indexes
        assert "ix_capabilities_sensitivity" in indexes
        assert "ix_capabilities_metadata_gin" in indexes

    def test_capabilities_foreign_key(self, session):
        """Test that capabilities has foreign key to resources."""
        inspector = inspect(session.bind)
        fks = inspector.get_foreign_keys("capabilities")

        assert len(fks) > 0
        fk = fks[0]
        assert fk["referred_table"] == "resources"
        assert "resource_id" in fk["constrained_columns"]
        assert fk["options"]["ondelete"] == "CASCADE"

    def test_create_resource(self, session, clean_db):
        """Test creating a resource."""
        resource = Resource(
            id="test-mcp-1",
            name="Test MCP Server",
            protocol="mcp",
            endpoint="npx -y @mcp/server-test",
            sensitivity_level="medium",
            metadata_={"transport": "stdio"},
        )
        session.add(resource)
        session.commit()

        # Verify
        saved = session.query(Resource).filter_by(id="test-mcp-1").first()
        assert saved is not None
        assert saved.name == "Test MCP Server"
        assert saved.protocol == "mcp"
        assert saved.metadata_["transport"] == "stdio"

    def test_create_capability(self, session, clean_db):
        """Test creating a capability."""
        # Create resource first
        resource = Resource(
            id="test-res-1",
            name="Test Resource",
            protocol="http",
            endpoint="https://api.example.com",
        )
        session.add(resource)
        session.commit()

        # Create capability
        capability = Capability(
            id="test-cap-1",
            resource_id="test-res-1",
            name="list_users",
            description="List all users",
            input_schema={"type": "object"},
            sensitivity_level="low",
        )
        session.add(capability)
        session.commit()

        # Verify
        saved = session.query(Capability).filter_by(id="test-cap-1").first()
        assert saved is not None
        assert saved.name == "list_users"
        assert saved.resource_id == "test-res-1"

    def test_cascade_delete(self, session, clean_db):
        """Test that deleting resource cascades to capabilities."""
        # Create resource and capability
        resource = Resource(
            id="test-res-2",
            name="Test Resource",
            protocol="grpc",
            endpoint="grpc.example.com:50051",
        )
        session.add(resource)
        session.commit()

        capability = Capability(
            id="test-cap-2",
            resource_id="test-res-2",
            name="test_method",
        )
        session.add(capability)
        session.commit()

        # Delete resource
        session.delete(resource)
        session.commit()

        # Verify capability was deleted
        cap = session.query(Capability).filter_by(id="test-cap-2").first()
        assert cap is None


class TestMigration007Federation:
    """Test migration 007: Federation support."""

    def test_federation_nodes_table_exists(self, session):
        """Test that federation_nodes table is created."""
        inspector = inspect(session.bind)
        assert "federation_nodes" in inspector.get_table_names()

    def test_cost_tracking_table_exists(self, session):
        """Test that cost_tracking table is created."""
        inspector = inspect(session.bind)
        assert "cost_tracking" in inspector.get_table_names()

    def test_principal_budgets_table_exists(self, session):
        """Test that principal_budgets table is created."""
        inspector = inspect(session.bind)
        assert "principal_budgets" in inspector.get_table_names()

    def test_audit_events_has_federation_columns(self, session):
        """Test that audit_events table has new federation columns."""
        inspector = inspect(session.bind)
        columns = [col["name"] for col in inspector.get_columns("audit_events")]

        assert "principal_org" in columns
        assert "resource_protocol" in columns
        assert "capability_id" in columns
        assert "correlation_id" in columns
        assert "source_node" in columns
        assert "target_node" in columns
        assert "estimated_cost" in columns
        assert "actual_cost" in columns

    def test_create_federation_node(self, session, clean_db):
        """Test creating a federation node."""
        node = FederationNode(
            node_id="orgb.com",
            name="Organization B",
            endpoint="https://sark.orgb.com:8443",
            trust_anchor_cert="-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
            enabled=True,
            rate_limit_per_hour=5000,
        )
        session.add(node)
        session.commit()

        # Verify
        saved = session.query(FederationNode).filter_by(node_id="orgb.com").first()
        assert saved is not None
        assert saved.name == "Organization B"
        assert saved.enabled is True
        assert saved.rate_limit_per_hour == 5000

    def test_create_cost_tracking(self, session, clean_db):
        """Test creating cost tracking records."""
        cost = CostTracking(
            principal_id="user-123",
            resource_id="res-456",
            capability_id="cap-789",
            estimated_cost=0.05,
            actual_cost=0.047,
        )
        session.add(cost)
        session.commit()

        # Verify
        saved = session.query(CostTracking).filter_by(principal_id="user-123").first()
        assert saved is not None
        assert float(saved.estimated_cost) == 0.05
        assert float(saved.actual_cost) == 0.047

    def test_create_principal_budget(self, session, clean_db):
        """Test creating principal budget."""
        budget = PrincipalBudget(
            principal_id="user-123",
            daily_budget=10.00,
            monthly_budget=300.00,
            daily_spent=2.50,
            monthly_spent=75.00,
            currency="USD",
        )
        session.add(budget)
        session.commit()

        # Verify
        saved = session.query(PrincipalBudget).filter_by(principal_id="user-123").first()
        assert saved is not None
        assert float(saved.daily_budget) == 10.00
        assert float(saved.daily_spent) == 2.50
        assert saved.currency == "USD"

    def test_materialized_view_exists(self, session):
        """Test that materialized view for cost analysis is created."""
        result = session.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM pg_matviews WHERE matviewname = 'mv_daily_cost_summary'
                )
            """
            )
        )
        assert result.scalar() is True


class TestDataMigration:
    """Test v1.x to v2.0 data migration."""

    def test_mcp_server_to_resource_migration(self, session, clean_db):
        """Test that MCP servers are correctly migrated to resources."""
        # Create v1.x MCP server
        server_id = uuid4()
        server = MCPServer(
            id=server_id,
            name="Test MCP Server",
            transport=TransportType.STDIO,
            command="npx -y @mcp/server-test",
            sensitivity_level=SensitivityLevel.MEDIUM,
            status=ServerStatus.ACTIVE,
        )
        session.add(server)
        session.commit()

        # Run migration (simulated - in practice would be via alembic or script)
        session.execute(
            text(
                """
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
                        'status', status::text
                    ),
                    created_at,
                    updated_at
                FROM mcp_servers
                WHERE id = :server_id
                ON CONFLICT (id) DO NOTHING
            """
            ),
            {"server_id": server_id},
        )
        session.commit()

        # Verify migration
        resource = session.query(Resource).filter_by(id=str(server_id)).first()
        assert resource is not None
        assert resource.name == "Test MCP Server"
        assert resource.protocol == "mcp"
        assert resource.endpoint == "npx -y @mcp/server-test"
        assert resource.metadata_["transport"] == "stdio"
        assert resource.metadata_["status"] == "active"

    def test_mcp_tool_to_capability_migration(self, session, clean_db):
        """Test that MCP tools are correctly migrated to capabilities."""
        # Create v1.x MCP server and tool
        server_id = uuid4()
        tool_id = uuid4()

        server = MCPServer(
            id=server_id,
            name="Test Server",
            transport=TransportType.STDIO,
            command="test-cmd",
        )
        session.add(server)
        session.commit()

        tool = MCPTool(
            id=tool_id,
            server_id=server_id,
            name="test_tool",
            description="Test tool description",
            parameters={"param1": "value1"},
            sensitivity_level=SensitivityLevel.LOW,
        )
        session.add(tool)
        session.commit()

        # Migrate server first
        session.execute(
            text(
                """
                INSERT INTO resources (id, name, protocol, endpoint, sensitivity_level, metadata, created_at, updated_at)
                SELECT
                    id::text, name, 'mcp', command, sensitivity_level::text,
                    '{}'::jsonb, created_at, updated_at
                FROM mcp_servers WHERE id = :server_id
                ON CONFLICT (id) DO NOTHING
            """
            ),
            {"server_id": server_id},
        )

        # Migrate tool
        session.execute(
            text(
                """
                INSERT INTO capabilities (id, resource_id, name, description, input_schema, output_schema, sensitivity_level, metadata)
                SELECT
                    id::text,
                    server_id::text,
                    name,
                    description,
                    COALESCE(parameters, '{}'::jsonb),
                    '{}'::jsonb,
                    sensitivity_level::text,
                    '{}'::jsonb
                FROM mcp_tools
                WHERE id = :tool_id
                ON CONFLICT (id) DO NOTHING
            """
            ),
            {"tool_id": tool_id},
        )
        session.commit()

        # Verify migration
        capability = session.query(Capability).filter_by(id=str(tool_id)).first()
        assert capability is not None
        assert capability.name == "test_tool"
        assert capability.description == "Test tool description"
        assert capability.resource_id == str(server_id)
        assert capability.input_schema["param1"] == "value1"

    def test_no_data_loss_during_migration(self, session, clean_db):
        """Test that no data is lost during migration."""
        # Create multiple servers and tools
        server_count = 5
        tools_per_server = 3

        for i in range(server_count):
            server = MCPServer(
                id=uuid4(),
                name=f"Server {i}",
                transport=TransportType.STDIO,
                command=f"cmd-{i}",
            )
            session.add(server)
            session.commit()

            for j in range(tools_per_server):
                tool = MCPTool(
                    id=uuid4(),
                    server_id=server.id,
                    name=f"tool_{i}_{j}",
                )
                session.add(tool)

        session.commit()

        # Count v1.x data
        v1_server_count = session.query(MCPServer).count()
        v1_tool_count = session.query(MCPTool).count()

        # Run full migration
        session.execute(
            text(
                """
                INSERT INTO resources (id, name, protocol, endpoint, sensitivity_level, metadata, created_at, updated_at)
                SELECT
                    id::text, name, 'mcp', command, sensitivity_level::text,
                    '{}'::jsonb, created_at, updated_at
                FROM mcp_servers
                ON CONFLICT (id) DO NOTHING
            """
            )
        )

        session.execute(
            text(
                """
                INSERT INTO capabilities (id, resource_id, name, description, input_schema, output_schema, sensitivity_level, metadata)
                SELECT
                    id::text, server_id::text, name, description,
                    COALESCE(parameters, '{}'::jsonb), '{}'::jsonb,
                    sensitivity_level::text, '{}'::jsonb
                FROM mcp_tools
                ON CONFLICT (id) DO NOTHING
            """
            )
        )
        session.commit()

        # Count v2.0 data
        v2_resource_count = session.query(Resource).filter_by(protocol="mcp").count()
        v2_capability_count = session.query(Capability).count()

        # Verify no data loss
        assert v1_server_count == v2_resource_count
        assert v1_tool_count == v2_capability_count

    def test_foreign_key_integrity_after_migration(self, session, clean_db):
        """Test that foreign key relationships are maintained after migration."""
        # Create server and tool
        server = MCPServer(
            id=uuid4(),
            name="Test Server",
            transport=TransportType.STDIO,
            command="test-cmd",
        )
        session.add(server)
        session.commit()

        tool = MCPTool(
            id=uuid4(),
            server_id=server.id,
            name="test_tool",
        )
        session.add(tool)
        session.commit()

        # Migrate
        session.execute(
            text(
                """
                INSERT INTO resources (id, name, protocol, endpoint, sensitivity_level, metadata, created_at, updated_at)
                SELECT id::text, name, 'mcp', command, sensitivity_level::text, '{}'::jsonb, created_at, updated_at
                FROM mcp_servers
                ON CONFLICT (id) DO NOTHING
            """
            )
        )

        session.execute(
            text(
                """
                INSERT INTO capabilities (id, resource_id, name, description, input_schema, output_schema, sensitivity_level, metadata)
                SELECT id::text, server_id::text, name, description, COALESCE(parameters, '{}'::jsonb),
                       '{}'::jsonb, sensitivity_level::text, '{}'::jsonb
                FROM mcp_tools
                ON CONFLICT (id) DO NOTHING
            """
            )
        )
        session.commit()

        # Verify FK integrity - should be no orphaned capabilities
        orphaned = session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM capabilities c
                WHERE NOT EXISTS (SELECT 1 FROM resources r WHERE r.id = c.resource_id)
            """
            )
        ).scalar()

        assert orphaned == 0


class TestRollback:
    """Test migration rollback functionality."""

    def test_rollback_deletes_only_mcp_resources(self, session, clean_db):
        """Test that rollback only deletes MCP resources, not other protocols."""
        # Create MCP and HTTP resources
        mcp_resource = Resource(
            id="mcp-1",
            name="MCP Resource",
            protocol="mcp",
            endpoint="test-cmd",
        )
        http_resource = Resource(
            id="http-1",
            name="HTTP Resource",
            protocol="http",
            endpoint="https://api.example.com",
        )
        session.add_all([mcp_resource, http_resource])
        session.commit()

        # Rollback (delete MCP only)
        session.execute(text("DELETE FROM resources WHERE protocol = 'mcp'"))
        session.commit()

        # Verify
        assert session.query(Resource).filter_by(id="mcp-1").first() is None
        assert session.query(Resource).filter_by(id="http-1").first() is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
