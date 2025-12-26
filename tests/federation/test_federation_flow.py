"""
Integration tests for SARK v2.0 Federation.

Tests the complete federation flow:
1. Node discovery (DNS-SD, mDNS)
2. mTLS trust establishment
3. Federated resource routing and invocation
4. Audit correlation across nodes
5. Circuit breaking and failover
"""

import asyncio
from datetime import datetime, timedelta

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from sark.models.base import Base, FederationNode, Resource
from sark.models.federation import (
    AuditCorrelationQuery,
    DiscoveryMethod,
    DiscoveryQuery,
    FederatedResourceRequest,
    RouteQuery,
    TrustEstablishmentRequest,
    TrustLevel,
    TrustVerificationRequest,
)
from sark.services.federation import DiscoveryService, RoutingService, TrustService

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
async def db_session():
    """Create test database session."""
    # Use in-memory SQLite for tests
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def test_certificate():
    """Generate test X.509 certificate."""
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )

    # Generate certificate
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "SARK Test"),
            x509.NameAttribute(NameOID.COMMON_NAME, "test.sark.local"),
        ]
    )

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=365))
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage(
                [
                    ExtendedKeyUsageOID.SERVER_AUTH,
                    ExtendedKeyUsageOID.CLIENT_AUTH,
                ]
            ),
            critical=True,
        )
        .sign(private_key, hashes.SHA256(), default_backend())
    )

    # Convert to PEM
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")

    return {"certificate": cert, "pem": cert_pem, "private_key": private_key}


@pytest.fixture
def discovery_service():
    """Create discovery service instance."""
    return DiscoveryService()


@pytest.fixture
def trust_service():
    """Create trust service instance."""
    return TrustService()


@pytest.fixture
async def routing_service():
    """Create routing service instance."""
    service = RoutingService(local_node_id="test-node-1")
    yield service
    await service.close()


# ============================================================================
# Discovery Tests
# ============================================================================


class TestDiscoveryService:
    """Tests for node discovery service."""

    @pytest.mark.asyncio
    async def test_dns_sd_discovery(self, discovery_service):
        """Test DNS-SD service discovery."""
        query = DiscoveryQuery(
            method=DiscoveryMethod.DNS_SD, service_type="_sark._tcp.local.", timeout_seconds=2
        )

        response = await discovery_service.discover(query)

        assert response.method == DiscoveryMethod.DNS_SD
        assert isinstance(response.records, list)
        assert response.total_found == len(response.records)

    @pytest.mark.asyncio
    async def test_mdns_discovery(self, discovery_service):
        """Test mDNS service discovery."""
        query = DiscoveryQuery(
            method=DiscoveryMethod.MDNS, service_type="_sark._tcp.local.", timeout_seconds=2
        )

        response = await discovery_service.discover(query)

        assert response.method == DiscoveryMethod.MDNS
        assert isinstance(response.records, list)

    @pytest.mark.asyncio
    async def test_consul_discovery(self, discovery_service):
        """Test Consul service discovery."""
        query = DiscoveryQuery(
            method=DiscoveryMethod.CONSUL, service_type="sark", timeout_seconds=2
        )

        response = await discovery_service.discover(query)

        assert response.method == DiscoveryMethod.CONSUL
        assert isinstance(response.records, list)

    @pytest.mark.asyncio
    async def test_discover_all_methods(self, discovery_service):
        """Test discovery using all methods."""
        results = await discovery_service.discover_all(
            service_type="_sark._tcp.local.", timeout_seconds=2
        )

        assert DiscoveryMethod.DNS_SD in results
        assert DiscoveryMethod.MDNS in results
        assert DiscoveryMethod.CONSUL in results

    @pytest.mark.asyncio
    async def test_discovery_caching(self, discovery_service):
        """Test discovery result caching."""
        query = DiscoveryQuery(
            method=DiscoveryMethod.MDNS, service_type="_sark._tcp.local.", timeout_seconds=1
        )

        # First call
        response1 = await discovery_service.discover(query)

        # Second call should use cache
        response2 = await discovery_service.discover(query)

        # Clear cache and call again
        discovery_service.clear_cache()
        await discovery_service.discover(query)

        assert response1.total_found == response2.total_found


# ============================================================================
# Trust Tests
# ============================================================================


class TestTrustService:
    """Tests for mTLS trust establishment."""

    @pytest.mark.asyncio
    async def test_establish_trust_success(self, trust_service, test_certificate, db_session):
        """Test successful trust establishment."""
        request = TrustEstablishmentRequest(
            node_id="test-node-2", client_cert=test_certificate["pem"]
        )

        response = await trust_service.establish_trust(request, db_session)

        assert response.success
        assert response.node_id == "test-node-2"
        assert response.trust_level == TrustLevel.TRUSTED
        assert response.certificate_info is not None

    @pytest.mark.asyncio
    async def test_establish_trust_with_challenge(
        self, trust_service, test_certificate, db_session
    ):
        """Test trust establishment with challenge-response."""
        # Generate challenge
        challenge = trust_service.generate_challenge("test-node-2")

        request = TrustEstablishmentRequest(
            node_id="test-node-2", client_cert=test_certificate["pem"], challenge=challenge
        )

        response = await trust_service.establish_trust(request, db_session)

        assert response.success
        assert response.challenge_response is not None

    @pytest.mark.asyncio
    async def test_verify_trust_success(self, trust_service, test_certificate, db_session):
        """Test trust verification."""
        # First establish trust
        establish_req = TrustEstablishmentRequest(
            node_id="test-node-3", client_cert=test_certificate["pem"]
        )
        establish_resp = await trust_service.establish_trust(establish_req, db_session)

        # Now verify trust
        verify_req = TrustVerificationRequest(
            node_id="test-node-3",
            certificate_fingerprint=establish_resp.certificate_info.fingerprint_sha256,
        )

        verify_resp = await trust_service.verify_trust(verify_req, db_session)

        assert verify_resp.verified
        assert verify_resp.trust_level == TrustLevel.TRUSTED

    @pytest.mark.asyncio
    async def test_verify_trust_fingerprint_mismatch(
        self, trust_service, test_certificate, db_session
    ):
        """Test trust verification with wrong fingerprint."""
        # Establish trust first
        establish_req = TrustEstablishmentRequest(
            node_id="test-node-4", client_cert=test_certificate["pem"]
        )
        await trust_service.establish_trust(establish_req, db_session)

        # Verify with wrong fingerprint
        verify_req = TrustVerificationRequest(
            node_id="test-node-4", certificate_fingerprint="wrong_fingerprint"
        )

        verify_resp = await trust_service.verify_trust(verify_req, db_session)

        assert not verify_resp.verified
        assert verify_resp.error is not None

    @pytest.mark.asyncio
    async def test_revoke_trust(self, trust_service, test_certificate, db_session):
        """Test trust revocation."""
        # Establish trust
        establish_req = TrustEstablishmentRequest(
            node_id="test-node-5", client_cert=test_certificate["pem"]
        )
        await trust_service.establish_trust(establish_req, db_session)

        # Revoke trust
        result = await trust_service.revoke_trust("test-node-5", db_session)
        assert result

        # Verify trust is revoked
        verify_req = TrustVerificationRequest(
            node_id="test-node-5", certificate_fingerprint="dummy"
        )
        verify_resp = await trust_service.verify_trust(verify_req, db_session)

        assert not verify_resp.verified


# ============================================================================
# Routing Tests
# ============================================================================


class TestRoutingService:
    """Tests for federated routing service."""

    @pytest.mark.asyncio
    async def test_find_local_route(self, routing_service, db_session):
        """Test finding route to local resource."""
        # Create local resource
        resource = Resource(
            id="test-resource-1",
            name="Test Resource",
            protocol="mcp",
            endpoint="stdio",
            sensitivity_level="medium",
        )
        db_session.add(resource)
        await db_session.commit()

        # Find route
        query = RouteQuery(resource_id="test-resource-1")
        response = await routing_service.find_route(query, db_session)

        assert len(response.available_routes) >= 1
        assert response.recommended_route is not None
        assert response.recommended_route.node_id == "test-node-1"  # Local node

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens(self, routing_service):
        """Test circuit breaker opens after failures."""
        node_id = "test-node-failing"
        cb = routing_service.circuit_breaker

        # Record failures
        for _ in range(5):
            cb.record_failure(node_id)

        # Circuit should be open
        assert cb.get_state(node_id) == "open"
        assert not cb.is_available(node_id)

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open(self, routing_service):
        """Test circuit breaker transitions to half-open."""
        node_id = "test-node-recovering"
        cb = routing_service.circuit_breaker
        cb.timeout_seconds = 0  # Immediate timeout for testing

        # Open circuit
        for _ in range(5):
            cb.record_failure(node_id)

        assert cb.get_state(node_id) == "open"

        # Wait a bit
        await asyncio.sleep(0.1)

        # Should transition to half-open
        assert cb.is_available(node_id)
        assert cb.get_state(node_id) == "half-open"

    @pytest.mark.asyncio
    async def test_circuit_breaker_closes_on_success(self, routing_service):
        """Test circuit breaker closes after success in half-open."""
        node_id = "test-node-recovered"
        cb = routing_service.circuit_breaker
        cb.timeout_seconds = 0

        # Open circuit
        for _ in range(5):
            cb.record_failure(node_id)

        # Transition to half-open
        await asyncio.sleep(0.1)
        cb.is_available(node_id)

        # Record success
        cb.record_success(node_id)

        # Circuit should be closed
        assert cb.get_state(node_id) == "closed"

    @pytest.mark.asyncio
    async def test_invoke_federated_node_not_found(self, routing_service, db_session):
        """Test federated invocation with non-existent node."""
        request = FederatedResourceRequest(
            target_node_id="non-existent-node",
            resource_id="test-resource",
            principal_id="test-principal",
            arguments={},
        )

        response = await routing_service.invoke_federated(request, db_session)

        assert not response.success
        assert "not found" in response.error.lower()

    @pytest.mark.asyncio
    async def test_audit_correlation(self, routing_service, db_session):
        """Test audit event correlation."""
        query = AuditCorrelationQuery(principal_id="test-principal")

        response = await routing_service.correlate_audit_events(query, db_session)

        assert isinstance(response.events, list)
        assert response.total_events == len(response.events)
        assert "test-node-1" in response.nodes_queried

    @pytest.mark.asyncio
    async def test_routing_table_cache(self, routing_service, db_session):
        """Test routing table caching."""
        # Create resource
        resource = Resource(
            id="test-resource-2",
            name="Test Resource 2",
            protocol="mcp",
            endpoint="stdio",
            sensitivity_level="medium",
        )
        db_session.add(resource)
        await db_session.commit()

        # Find route (should cache)
        query = RouteQuery(resource_id="test-resource-2")
        await routing_service.find_route(query, db_session)

        # Get routing table
        routing_table = await routing_service.get_routing_table()
        assert len(routing_table.entries) >= 1

        # Clear cache
        routing_service.clear_routing_cache()
        routing_table = await routing_service.get_routing_table()
        assert len(routing_table.entries) == 0


# ============================================================================
# Integration Tests
# ============================================================================


class TestFederationFlow:
    """End-to-end federation flow tests."""

    @pytest.mark.asyncio
    async def test_complete_federation_flow(
        self, discovery_service, trust_service, routing_service, test_certificate, db_session
    ):
        """Test complete federation flow from discovery to invocation."""

        # Step 1: Discover nodes
        query = DiscoveryQuery(
            method=DiscoveryMethod.MDNS, service_type="_sark._tcp.local.", timeout_seconds=1
        )
        discovery_response = await discovery_service.discover(query)
        assert isinstance(discovery_response.records, list)

        # Step 2: Establish trust with a node
        trust_request = TrustEstablishmentRequest(
            node_id="test-federated-node", client_cert=test_certificate["pem"]
        )
        trust_response = await trust_service.establish_trust(trust_request, db_session)
        assert trust_response.success

        # Step 3: Create a local resource
        resource = Resource(
            id="test-resource-flow",
            name="Test Flow Resource",
            protocol="mcp",
            endpoint="stdio",
            sensitivity_level="medium",
        )
        db_session.add(resource)
        await db_session.commit()

        # Step 4: Find route to resource
        route_query = RouteQuery(resource_id="test-resource-flow")
        route_response = await routing_service.find_route(route_query, db_session)
        assert len(route_response.available_routes) >= 1

        # Step 5: Correlate audit events
        audit_query = AuditCorrelationQuery()
        audit_response = await routing_service.correlate_audit_events(audit_query, db_session)
        assert isinstance(audit_response.events, list)

    @pytest.mark.asyncio
    async def test_federation_failover(self, routing_service, test_certificate, db_session):
        """Test federation failover when primary node fails."""

        # Create multiple federation nodes
        nodes = [
            FederationNode(
                node_id=f"test-node-{i}",
                name=f"Test Node {i}",
                endpoint=f"https://node{i}.example.com",
                trust_anchor_cert=test_certificate["pem"],
                enabled=True,
            )
            for i in range(3)
        ]

        for node in nodes:
            db_session.add(node)
        await db_session.commit()

        # Simulate primary node failure
        routing_service.circuit_breaker.record_failure("test-node-0")
        routing_service.circuit_breaker.record_failure("test-node-0")
        routing_service.circuit_breaker.record_failure("test-node-0")
        routing_service.circuit_breaker.record_failure("test-node-0")
        routing_service.circuit_breaker.record_failure("test-node-0")

        # Circuit should be open for failed node
        assert routing_service.circuit_breaker.get_state("test-node-0") == "open"

        # But other nodes should be available
        assert routing_service.circuit_breaker.is_available("test-node-1")
        assert routing_service.circuit_breaker.is_available("test-node-2")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
