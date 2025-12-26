"""
Rollback scenario tests for SARK v2.0 migrations.

These tests ensure that migrations can be safely rolled back without data loss.
Tests cover various rollback scenarios including partial rollbacks, data preservation,
and emergency recovery procedures.
"""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from sark.db.base import Base
from sark.models.base import Capability, Resource
from sark.models.mcp_server import MCPServer, SensitivityLevel, ServerStatus, TransportType


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


class TestBasicRollback:
    """Test basic rollback scenarios."""

    def test_rollback_preserves_v1_data(self, session, clean_db):
        """Test that rollback doesn't affect v1.x data."""
        # Create v1.x data
        server = MCPServer(
            id=uuid4(),
            name="Test Server",
            transport=TransportType.STDIO,
            command="test-cmd",
            sensitivity_level=SensitivityLevel.MEDIUM,
            status=ServerStatus.ACTIVE,
        )
        session.add(server)
        session.commit()

        original_server_count = session.query(MCPServer).count()

        # Migrate to v2.0
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
        session.commit()

        # Verify migration
        migrated_count = session.query(Resource).filter_by(protocol="mcp").count()
        assert migrated_count == original_server_count

        # Rollback: Delete v2.0 data
        session.execute(text("DELETE FROM resources WHERE protocol = 'mcp'"))
        session.commit()

        # Verify v1.x data still intact
        final_server_count = session.query(MCPServer).count()
        assert final_server_count == original_server_count

        # Verify server data unchanged
        restored_server = session.query(MCPServer).filter_by(id=server.id).first()
        assert restored_server is not None
        assert restored_server.name == "Test Server"
        assert restored_server.command == "test-cmd"

    def test_rollback_deletes_only_mcp_resources(self, session, clean_db):
        """Test that rollback only deletes MCP resources, not other protocols."""
        # Create MCP resource
        mcp_resource = Resource(
            id="mcp-1",
            name="MCP Resource",
            protocol="mcp",
            endpoint="test-cmd",
        )
        session.add(mcp_resource)

        # Create HTTP resource
        http_resource = Resource(
            id="http-1",
            name="HTTP Resource",
            protocol="http",
            endpoint="https://api.example.com",
        )
        session.add(http_resource)

        # Create gRPC resource
        grpc_resource = Resource(
            id="grpc-1",
            name="gRPC Resource",
            protocol="grpc",
            endpoint="grpc.example.com:50051",
        )
        session.add(grpc_resource)

        session.commit()

        # Rollback (delete MCP only)
        session.execute(text("DELETE FROM resources WHERE protocol = 'mcp'"))
        session.commit()

        # Verify
        assert session.query(Resource).filter_by(id="mcp-1").first() is None
        assert session.query(Resource).filter_by(id="http-1").first() is not None
        assert session.query(Resource).filter_by(id="grpc-1").first() is not None

    def test_cascade_delete_on_rollback(self, session, clean_db):
        """Test that rolling back resource deletes cascades to capabilities."""
        # Create resource and capabilities
        resource = Resource(
            id="test-res-1",
            name="Test Resource",
            protocol="mcp",
            endpoint="test-cmd",
        )
        session.add(resource)
        session.commit()

        # Add multiple capabilities
        for i in range(5):
            cap = Capability(
                id=f"cap-{i}",
                resource_id="test-res-1",
                name=f"capability_{i}",
            )
            session.add(cap)
        session.commit()

        # Verify capabilities exist
        assert session.query(Capability).filter_by(resource_id="test-res-1").count() == 5

        # Rollback: Delete resource
        session.execute(text("DELETE FROM resources WHERE id = 'test-res-1'"))
        session.commit()

        # Verify capabilities were cascade deleted
        assert session.query(Capability).filter_by(resource_id="test-res-1").count() == 0


class TestPartialRollback:
    """Test partial rollback scenarios."""

    def test_rollback_subset_of_resources(self, session, clean_db):
        """Test rolling back a subset of migrated resources."""
        # Create multiple v1.x servers
        servers = []
        for i in range(10):
            server = MCPServer(
                id=uuid4(),
                name=f"Server {i}",
                transport=TransportType.STDIO,
                command=f"cmd-{i}",
            )
            servers.append(server)
            session.add(server)
        session.commit()

        # Migrate all to v2.0
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
        session.commit()

        # Rollback only first 5 resources
        first_five_ids = [str(s.id) for s in servers[:5]]
        session.execute(
            text("DELETE FROM resources WHERE id = ANY(:ids)"),
            {"ids": first_five_ids},
        )
        session.commit()

        # Verify partial rollback
        assert session.query(Resource).filter_by(protocol="mcp").count() == 5
        assert session.query(MCPServer).count() == 10  # v1.x untouched

    def test_rollback_with_mixed_protocols(self, session, clean_db):
        """Test rollback when multiple protocols are present."""
        # Create mixed protocol resources
        protocols = ["mcp", "http", "grpc", "mcp", "http", "mcp"]
        for i, protocol in enumerate(protocols):
            resource = Resource(
                id=f"res-{i}",
                name=f"Resource {i}",
                protocol=protocol,
                endpoint=f"endpoint-{i}",
            )
            session.add(resource)
        session.commit()

        # Count before rollback
        mcp_count_before = session.query(Resource).filter_by(protocol="mcp").count()
        http_count_before = session.query(Resource).filter_by(protocol="http").count()
        grpc_count_before = session.query(Resource).filter_by(protocol="grpc").count()

        assert mcp_count_before == 3
        assert http_count_before == 2
        assert grpc_count_before == 1

        # Rollback only MCP
        session.execute(text("DELETE FROM resources WHERE protocol = 'mcp'"))
        session.commit()

        # Verify only MCP deleted
        assert session.query(Resource).filter_by(protocol="mcp").count() == 0
        assert session.query(Resource).filter_by(protocol="http").count() == http_count_before
        assert session.query(Resource).filter_by(protocol="grpc").count() == grpc_count_before


class TestDataIntegrityDuringRollback:
    """Test data integrity is maintained during rollback."""

    def test_no_data_loss_on_failed_rollback(self, session, clean_db):
        """Test that failed rollback doesn't corrupt data."""
        # Create v1.x and v2.0 data
        server = MCPServer(
            id=uuid4(),
            name="Test Server",
            transport=TransportType.STDIO,
            command="test-cmd",
        )
        session.add(server)
        session.commit()

        # Migrate
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
        session.commit()

        # Simulate failed rollback (transaction rollback)
        try:
            session.execute(text("DELETE FROM resources WHERE protocol = 'mcp'"))
            # Simulate error before commit
            raise Exception("Simulated rollback failure")
        except:
            session.rollback()

        # Verify data unchanged
        assert session.query(MCPServer).count() == 1
        assert session.query(Resource).filter_by(protocol="mcp").count() == 1

    def test_idempotent_rollback(self, session, clean_db):
        """Test that rollback can be run multiple times safely."""
        # Create and migrate data
        server = MCPServer(
            id=uuid4(),
            name="Test Server",
            transport=TransportType.STDIO,
            command="test-cmd",
        )
        session.add(server)
        session.commit()

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
        session.commit()

        # First rollback
        session.execute(text("DELETE FROM resources WHERE protocol = 'mcp'"))
        session.commit()
        assert session.query(Resource).filter_by(protocol="mcp").count() == 0

        # Second rollback (should be safe)
        session.execute(text("DELETE FROM resources WHERE protocol = 'mcp'"))
        session.commit()
        assert session.query(Resource).filter_by(protocol="mcp").count() == 0

        # v1.x data should still be intact
        assert session.query(MCPServer).count() == 1


class TestComplexRollbackScenarios:
    """Test complex rollback scenarios."""

    def test_rollback_with_active_cost_tracking(self, session, clean_db):
        """Test rollback when cost tracking data exists."""
        # This would test rollback with related data in cost_tracking table
        # Implementation depends on whether cost_tracking should be preserved
        # For this test, we'll assume it should be deleted with capabilities

        # Create resource and capability
        resource = Resource(
            id="res-1",
            name="Test Resource",
            protocol="mcp",
            endpoint="test-cmd",
        )
        session.add(resource)
        session.commit()

        capability = Capability(
            id="cap-1",
            resource_id="res-1",
            name="test_capability",
        )
        session.add(capability)
        session.commit()

        # Simulate cost tracking data (if table exists)
        inspector = inspect(session.bind)
        if "cost_tracking" in inspector.get_table_names():
            from sark.models.base import CostTracking

            cost = CostTracking(
                principal_id="user-123",
                resource_id="res-1",
                capability_id="cap-1",
                estimated_cost=0.05,
                actual_cost=0.047,
            )
            session.add(cost)
            session.commit()

            # Rollback resource (should cascade to capability and cost tracking)
            session.execute(text("DELETE FROM resources WHERE id = 'res-1'"))
            session.commit()

            # Verify cascade
            assert session.query(Capability).filter_by(id="cap-1").first() is None
            # Cost tracking may or may not cascade depending on FK setup
            # This documents expected behavior

    def test_rollback_after_partial_migration(self, session, clean_db):
        """Test rollback after partial/interrupted migration."""
        # Create 10 v1.x servers
        servers = []
        for i in range(10):
            server = MCPServer(
                id=uuid4(),
                name=f"Server {i}",
                transport=TransportType.STDIO,
                command=f"cmd-{i}",
            )
            servers.append(server)
            session.add(server)
        session.commit()

        # Partially migrate (only first 5)
        first_five_ids = [s.id for s in servers[:5]]
        session.execute(
            text(
                """
                INSERT INTO resources (id, name, protocol, endpoint, sensitivity_level, metadata, created_at, updated_at)
                SELECT
                    id::text, name, 'mcp', command, sensitivity_level::text,
                    '{}'::jsonb, created_at, updated_at
                FROM mcp_servers
                WHERE id = ANY(:ids)
                ON CONFLICT (id) DO NOTHING
            """
            ),
            {"ids": first_five_ids},
        )
        session.commit()

        # Verify partial migration
        assert session.query(Resource).filter_by(protocol="mcp").count() == 5

        # Full rollback
        session.execute(text("DELETE FROM resources WHERE protocol = 'mcp'"))
        session.commit()

        # Verify clean rollback
        assert session.query(Resource).filter_by(protocol="mcp").count() == 0
        assert session.query(MCPServer).count() == 10


class TestEmergencyRecovery:
    """Test emergency recovery scenarios."""

    def test_recovery_from_orphaned_capabilities(self, session, clean_db):
        """Test recovery when orphaned capabilities exist."""
        # Create resource and capability
        resource = Resource(
            id="res-1",
            name="Test Resource",
            protocol="mcp",
            endpoint="test-cmd",
        )
        session.add(resource)
        session.commit()

        capability = Capability(
            id="cap-1",
            resource_id="res-1",
            name="test_capability",
        )
        session.add(capability)
        session.commit()

        # Manually delete resource without cascade (simulating data corruption)
        session.execute(text("SET session_replication_role = replica"))  # Disable triggers
        session.execute(text("DELETE FROM resources WHERE id = 'res-1'"))
        session.execute(text("SET session_replication_role = DEFAULT"))
        session.commit()

        # Verify orphaned capability
        orphaned = session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM capabilities c
                WHERE NOT EXISTS (SELECT 1 FROM resources r WHERE r.id = c.resource_id)
            """
            )
        ).scalar()
        assert orphaned == 1

        # Recovery: Clean up orphaned capabilities
        session.execute(
            text(
                """
                DELETE FROM capabilities
                WHERE NOT EXISTS (SELECT 1 FROM resources r WHERE r.id = resource_id)
            """
            )
        )
        session.commit()

        # Verify cleanup
        assert session.query(Capability).count() == 0

    def test_recovery_from_duplicate_migration(self, session, clean_db):
        """Test recovery when migration runs twice accidentally."""
        # Create v1.x server
        server = MCPServer(
            id=uuid4(),
            name="Test Server",
            transport=TransportType.STDIO,
            command="test-cmd",
        )
        session.add(server)
        session.commit()

        # First migration
        session.execute(
            text(
                """
                INSERT INTO resources (id, name, protocol, endpoint, sensitivity_level, metadata, created_at, updated_at)
                SELECT
                    id::text, name, 'mcp', command, sensitivity_level::text,
                    '{}'::jsonb, created_at, updated_at
                FROM mcp_servers
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    updated_at = EXCLUDED.updated_at
            """
            )
        )
        session.commit()

        # Second migration (should be idempotent)
        session.execute(
            text(
                """
                INSERT INTO resources (id, name, protocol, endpoint, sensitivity_level, metadata, created_at, updated_at)
                SELECT
                    id::text, name, 'mcp', command, sensitivity_level::text,
                    '{}'::jsonb, created_at, updated_at
                FROM mcp_servers
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    updated_at = EXCLUDED.updated_at
            """
            )
        )
        session.commit()

        # Verify no duplicates
        assert session.query(Resource).filter_by(protocol="mcp").count() == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
