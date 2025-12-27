"""Unit tests for Federation models and Pydantic schemas."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from sark.models.federation import (
    AuditCorrelationQuery,
    AuditCorrelationResponse,
    CertificateInfo,
    DiscoveryMethod,
    DiscoveryQuery,
    DiscoveryResponse,
    FederatedAuditEvent,
    FederatedResourceRequest,
    FederatedResourceResponse,
    FederationHealthResponse,
    FederationNodeBase,
    FederationNodeCreate,
    FederationNodeResponse,
    FederationNodeUpdate,
    NodeHealthCheck,
    NodeStatus,
    RouteEntry,
    RouteQuery,
    RouteResponse,
    RoutingTable,
    ServiceDiscoveryRecord,
    TrustEstablishmentRequest,
    TrustEstablishmentResponse,
    TrustLevel,
    TrustVerificationRequest,
    TrustVerificationResponse,
)


# Sample PEM certificate for testing
SAMPLE_CERT = """-----BEGIN CERTIFICATE-----
MIIDQTCCAimgAwIBAgITBmyfz5m/jAo54vB4ikPmljZbyjANBgkqhkiG9w0BAQsF
ADA5MQswCQYDVQQGEwJVUzEPMA0GA1UEChMGQW1hem9uMRkwFwYDVQQDExBBbWF6
b24gUm9vdCBDQSAxMB4XDTE1MDUyNjAwMDAwMFoXDTM4MDExNzAwMDAwMFowOTEL
-----END CERTIFICATE-----"""


class TestEnums:
    """Test federation enums."""

    def test_trust_level_values(self):
        """Test TrustLevel enum values."""
        assert TrustLevel.UNTRUSTED == "untrusted"
        assert TrustLevel.PENDING == "pending"
        assert TrustLevel.TRUSTED == "trusted"
        assert TrustLevel.REVOKED == "revoked"

    def test_node_status_values(self):
        """Test NodeStatus enum values."""
        assert NodeStatus.ONLINE == "online"
        assert NodeStatus.OFFLINE == "offline"
        assert NodeStatus.DEGRADED == "degraded"
        assert NodeStatus.UNKNOWN == "unknown"

    def test_discovery_method_values(self):
        """Test DiscoveryMethod enum values."""
        assert DiscoveryMethod.DNS_SD == "dns-sd"
        assert DiscoveryMethod.MDNS == "mdns"
        assert DiscoveryMethod.MANUAL == "manual"
        assert DiscoveryMethod.CONSUL == "consul"


class TestFederationNodeBase:
    """Test FederationNodeBase schema."""

    def test_valid_node_creation(self):
        """Test creating a valid federation node."""
        node = FederationNodeBase(
            node_id="test-node-1",
            name="Test Node",
            endpoint="https://sark.example.com",
            trust_anchor_cert=SAMPLE_CERT,
        )
        assert node.node_id == "test-node-1"
        assert node.name == "Test Node"
        assert node.endpoint == "https://sark.example.com"
        assert node.enabled is True
        assert node.rate_limit_per_hour == 10000

    def test_endpoint_validation_https(self):
        """Test endpoint validation accepts HTTPS."""
        node = FederationNodeBase(
            node_id="test",
            name="Test",
            endpoint="https://example.com/",
            trust_anchor_cert=SAMPLE_CERT,
        )
        # Should strip trailing slash
        assert node.endpoint == "https://example.com"

    def test_endpoint_validation_http(self):
        """Test endpoint validation accepts HTTP."""
        node = FederationNodeBase(
            node_id="test",
            name="Test",
            endpoint="http://localhost:8000/",
            trust_anchor_cert=SAMPLE_CERT,
        )
        assert node.endpoint == "http://localhost:8000"

    def test_endpoint_validation_invalid(self):
        """Test endpoint validation rejects invalid URLs."""
        with pytest.raises(ValidationError, match="Endpoint must be a valid HTTP/HTTPS URL"):
            FederationNodeBase(
                node_id="test",
                name="Test",
                endpoint="ftp://example.com",
                trust_anchor_cert=SAMPLE_CERT,
            )

    def test_certificate_validation_valid_pem(self):
        """Test certificate validation accepts valid PEM."""
        node = FederationNodeBase(
            node_id="test",
            name="Test",
            endpoint="https://example.com",
            trust_anchor_cert=SAMPLE_CERT,
        )
        assert "BEGIN CERTIFICATE" in node.trust_anchor_cert

    def test_certificate_validation_missing_begin(self):
        """Test certificate validation rejects cert missing BEGIN."""
        with pytest.raises(ValidationError, match="Certificate must be in PEM format"):
            FederationNodeBase(
                node_id="test",
                name="Test",
                endpoint="https://example.com",
                trust_anchor_cert="NOT A CERTIFICATE\n-----END CERTIFICATE-----",
            )

    def test_certificate_validation_missing_end(self):
        """Test certificate validation rejects cert missing END."""
        with pytest.raises(ValidationError, match="Certificate must be in PEM format"):
            FederationNodeBase(
                node_id="test",
                name="Test",
                endpoint="https://example.com",
                trust_anchor_cert="-----BEGIN CERTIFICATE-----\nNOT COMPLETE",
            )

    def test_custom_metadata(self):
        """Test custom metadata field."""
        node = FederationNodeBase(
            node_id="test",
            name="Test",
            endpoint="https://example.com",
            trust_anchor_cert=SAMPLE_CERT,
            metadata={"region": "us-east-1", "environment": "production"},
        )
        assert node.metadata["region"] == "us-east-1"
        assert node.metadata["environment"] == "production"

    def test_disabled_node(self):
        """Test creating a disabled node."""
        node = FederationNodeBase(
            node_id="test",
            name="Test",
            endpoint="https://example.com",
            trust_anchor_cert=SAMPLE_CERT,
            enabled=False,
        )
        assert node.enabled is False


class TestFederationNodeCreate:
    """Test FederationNodeCreate schema."""

    def test_inherits_from_base(self):
        """Test that FederationNodeCreate inherits from base."""
        node = FederationNodeCreate(
            node_id="test",
            name="Test",
            endpoint="https://example.com",
            trust_anchor_cert=SAMPLE_CERT,
        )
        assert isinstance(node, FederationNodeBase)


class TestFederationNodeUpdate:
    """Test FederationNodeUpdate schema."""

    def test_partial_update(self):
        """Test partial update with only some fields."""
        update = FederationNodeUpdate(name="New Name")
        assert update.name == "New Name"
        assert update.endpoint is None
        assert update.enabled is None

    def test_endpoint_validation_with_none(self):
        """Test endpoint validation allows None."""
        update = FederationNodeUpdate(endpoint=None)
        assert update.endpoint is None

    def test_endpoint_validation_with_valid_url(self):
        """Test endpoint validation with valid URL."""
        update = FederationNodeUpdate(endpoint="https://new.example.com/")
        assert update.endpoint == "https://new.example.com"

    def test_endpoint_validation_rejects_invalid(self):
        """Test endpoint validation rejects invalid URL."""
        with pytest.raises(ValidationError, match="Endpoint must be a valid HTTP/HTTPS URL"):
            FederationNodeUpdate(endpoint="not-a-url")


class TestServiceDiscoveryRecord:
    """Test ServiceDiscoveryRecord schema."""

    def test_valid_record(self):
        """Test creating a valid service discovery record."""
        record = ServiceDiscoveryRecord(
            service_name="_sark._tcp",
            instance_name="sark-prod-us-east",
            hostname="10.0.1.100",
            port=8443,
        )
        assert record.service_name == "_sark._tcp"
        assert record.instance_name == "sark-prod-us-east"
        assert record.hostname == "10.0.1.100"
        assert record.port == 8443
        assert record.ttl == 3600

    def test_port_validation_valid_range(self):
        """Test port validation accepts valid ports."""
        record = ServiceDiscoveryRecord(
            service_name="_sark._tcp",
            instance_name="test",
            hostname="localhost",
            port=8080,
        )
        assert record.port == 8080

    def test_port_validation_min_port(self):
        """Test port validation accepts port 1."""
        record = ServiceDiscoveryRecord(
            service_name="_sark._tcp",
            instance_name="test",
            hostname="localhost",
            port=1,
        )
        assert record.port == 1

    def test_port_validation_max_port(self):
        """Test port validation accepts port 65535."""
        record = ServiceDiscoveryRecord(
            service_name="_sark._tcp",
            instance_name="test",
            hostname="localhost",
            port=65535,
        )
        assert record.port == 65535

    def test_port_validation_too_low(self):
        """Test port validation rejects port 0."""
        with pytest.raises(ValidationError, match="Port must be between 1 and 65535"):
            ServiceDiscoveryRecord(
                service_name="_sark._tcp",
                instance_name="test",
                hostname="localhost",
                port=0,
            )

    def test_port_validation_too_high(self):
        """Test port validation rejects port >65535."""
        with pytest.raises(ValidationError, match="Port must be between 1 and 65535"):
            ServiceDiscoveryRecord(
                service_name="_sark._tcp",
                instance_name="test",
                hostname="localhost",
                port=65536,
            )

    def test_txt_records(self):
        """Test TXT records field."""
        record = ServiceDiscoveryRecord(
            service_name="_sark._tcp",
            instance_name="test",
            hostname="localhost",
            port=8080,
            txt_records={"version": "1.3.0", "environment": "prod"},
        )
        assert record.txt_records["version"] == "1.3.0"
        assert record.txt_records["environment"] == "prod"


class TestDiscoveryQuery:
    """Test DiscoveryQuery schema."""

    def test_default_values(self):
        """Test default query values."""
        query = DiscoveryQuery()
        assert query.method == DiscoveryMethod.MDNS
        assert query.service_type == "_sark._tcp.local."
        assert query.timeout_seconds == 5
        assert query.max_results == 10

    def test_custom_values(self):
        """Test custom query values."""
        query = DiscoveryQuery(
            method=DiscoveryMethod.DNS_SD,
            service_type="_custom._tcp.",
            timeout_seconds=10,
            max_results=50,
        )
        assert query.method == DiscoveryMethod.DNS_SD
        assert query.service_type == "_custom._tcp."
        assert query.timeout_seconds == 10
        assert query.max_results == 50


class TestDiscoveryResponse:
    """Test DiscoveryResponse schema."""

    def test_response_creation(self):
        """Test creating discovery response."""
        records = [
            ServiceDiscoveryRecord(
                service_name="_sark._tcp",
                instance_name="test",
                hostname="localhost",
                port=8080,
            )
        ]
        response = DiscoveryResponse(
            method=DiscoveryMethod.MDNS,
            records=records,
            total_found=1,
        )
        assert response.method == DiscoveryMethod.MDNS
        assert len(response.records) == 1
        assert response.total_found == 1


class TestCertificateInfo:
    """Test CertificateInfo schema."""

    def test_certificate_info_creation(self):
        """Test creating certificate info."""
        now = datetime.utcnow()
        cert_info = CertificateInfo(
            subject="CN=sark.example.com",
            issuer="CN=Example CA",
            serial_number="1234567890",
            not_before=now,
            not_after=now + timedelta(days=365),
            fingerprint_sha256="abc123",
            key_usage=["digitalSignature", "keyEncipherment"],
            extended_key_usage=["serverAuth", "clientAuth"],
        )
        assert cert_info.subject == "CN=sark.example.com"
        assert cert_info.issuer == "CN=Example CA"
        assert len(cert_info.key_usage) == 2


class TestTrustEstablishment:
    """Test trust establishment schemas."""

    def test_trust_establishment_request(self):
        """Test creating trust establishment request."""
        request = TrustEstablishmentRequest(
            node_id="remote-node",
            client_cert=SAMPLE_CERT,
            challenge="random-challenge-string",
        )
        assert request.node_id == "remote-node"
        assert request.challenge == "random-challenge-string"

    def test_trust_establishment_response(self):
        """Test creating trust establishment response."""
        now = datetime.utcnow()
        cert_info = CertificateInfo(
            subject="CN=test",
            issuer="CN=CA",
            serial_number="123",
            not_before=now,
            not_after=now + timedelta(days=365),
            fingerprint_sha256="abc",
        )
        response = TrustEstablishmentResponse(
            success=True,
            node_id="remote-node",
            trust_level=TrustLevel.TRUSTED,
            certificate_info=cert_info,
            expires_at=now + timedelta(days=365),
        )
        assert response.success is True
        assert response.trust_level == TrustLevel.TRUSTED


class TestTrustVerification:
    """Test trust verification schemas."""

    def test_trust_verification_request(self):
        """Test creating trust verification request."""
        request = TrustVerificationRequest(
            node_id="test-node",
            certificate_fingerprint="abc123",
        )
        assert request.node_id == "test-node"
        assert request.certificate_fingerprint == "abc123"

    def test_trust_verification_response_success(self):
        """Test successful trust verification response."""
        now = datetime.utcnow()
        cert_info = CertificateInfo(
            subject="CN=test",
            issuer="CN=CA",
            serial_number="123",
            not_before=now,
            not_after=now + timedelta(days=365),
            fingerprint_sha256="abc",
        )
        response = TrustVerificationResponse(
            verified=True,
            node_id="test-node",
            trust_level=TrustLevel.TRUSTED,
            certificate_info=cert_info,
        )
        assert response.verified is True
        assert response.trust_level == TrustLevel.TRUSTED
        assert response.error is None

    def test_trust_verification_response_failure(self):
        """Test failed trust verification response."""
        response = TrustVerificationResponse(
            verified=False,
            node_id="test-node",
            trust_level=TrustLevel.UNTRUSTED,
            error="Certificate expired",
        )
        assert response.verified is False
        assert response.error == "Certificate expired"


class TestFederatedResourceRequest:
    """Test FederatedResourceRequest schema."""

    def test_resource_request_creation(self):
        """Test creating federated resource request."""
        request = FederatedResourceRequest(
            target_node_id="remote-node",
            resource_id="resource-123",
            capability_id="capability-456",
            principal_id="user-789",
            arguments={"param1": "value1"},
            context={"source_ip": "10.0.1.1"},
        )
        assert request.target_node_id == "remote-node"
        assert request.resource_id == "resource-123"
        assert request.arguments["param1"] == "value1"


class TestFederatedResourceResponse:
    """Test FederatedResourceResponse schema."""

    def test_successful_response(self):
        """Test successful federated resource response."""
        response = FederatedResourceResponse(
            success=True,
            node_id="remote-node",
            resource_id="resource-123",
            result={"data": "result"},
            duration_ms=150.5,
            audit_correlation_id="correlation-123",
        )
        assert response.success is True
        assert response.duration_ms == 150.5
        assert response.error is None

    def test_failed_response(self):
        """Test failed federated resource response."""
        response = FederatedResourceResponse(
            success=False,
            node_id="remote-node",
            resource_id="resource-123",
            error="Resource not found",
            duration_ms=50.0,
            audit_correlation_id="correlation-456",
        )
        assert response.success is False
        assert response.error == "Resource not found"


class TestRouting:
    """Test routing schemas."""

    def test_route_entry_creation(self):
        """Test creating route entry."""
        now = datetime.utcnow()
        entry = RouteEntry(
            resource_id="resource-123",
            node_id="node-1",
            endpoint="https://node1.example.com",
            last_verified=now,
            health_status=NodeStatus.ONLINE,
            latency_ms=25.5,
        )
        assert entry.resource_id == "resource-123"
        assert entry.health_status == NodeStatus.ONLINE

    def test_routing_table_creation(self):
        """Test creating routing table."""
        now = datetime.utcnow()
        entries = [
            RouteEntry(
                resource_id="resource-1",
                node_id="node-1",
                endpoint="https://node1.example.com",
                last_verified=now,
                health_status=NodeStatus.ONLINE,
            )
        ]
        table = RoutingTable(entries=entries)
        assert len(table.entries) == 1
        assert table.version == 1

    def test_route_query(self):
        """Test route query."""
        query = RouteQuery(
            resource_id="resource-123",
            preferred_node="node-1",
            include_unhealthy=True,
        )
        assert query.resource_id == "resource-123"
        assert query.preferred_node == "node-1"
        assert query.include_unhealthy is True

    def test_route_response(self):
        """Test route response."""
        now = datetime.utcnow()
        routes = [
            RouteEntry(
                resource_id="resource-1",
                node_id="node-1",
                endpoint="https://node1.example.com",
                last_verified=now,
                health_status=NodeStatus.ONLINE,
            )
        ]
        response = RouteResponse(
            resource_id="resource-1",
            available_routes=routes,
            recommended_route=routes[0],
        )
        assert response.resource_id == "resource-1"
        assert len(response.available_routes) == 1


class TestAuditCorrelation:
    """Test audit correlation schemas."""

    def test_federated_audit_event(self):
        """Test creating federated audit event."""
        event = FederatedAuditEvent(
            correlation_id="corr-123",
            source_node_id="node-1",
            target_node_id="node-2",
            principal_id="user-789",
            resource_id="resource-123",
            capability_id="cap-456",
            action="invoke",
            success=True,
            duration_ms=100.5,
        )
        assert event.correlation_id == "corr-123"
        assert event.success is True

    def test_audit_correlation_query(self):
        """Test audit correlation query."""
        now = datetime.utcnow()
        query = AuditCorrelationQuery(
            correlation_id="corr-123",
            principal_id="user-789",
            start_time=now - timedelta(hours=1),
            end_time=now,
            node_ids=["node-1", "node-2"],
        )
        assert query.correlation_id == "corr-123"
        assert len(query.node_ids) == 2

    def test_audit_correlation_response(self):
        """Test audit correlation response."""
        events = [
            FederatedAuditEvent(
                correlation_id="corr-123",
                source_node_id="node-1",
                target_node_id="node-2",
                principal_id="user-789",
                resource_id="resource-123",
                action="invoke",
                success=True,
                duration_ms=100.0,
            )
        ]
        response = AuditCorrelationResponse(
            events=events,
            total_events=1,
            nodes_queried=["node-1", "node-2"],
            query_duration_ms=250.5,
        )
        assert len(response.events) == 1
        assert response.total_events == 1


class TestHealthCheck:
    """Test health check schemas."""

    def test_node_health_check(self):
        """Test node health check."""
        now = datetime.utcnow()
        health = NodeHealthCheck(
            node_id="node-1",
            status=NodeStatus.ONLINE,
            last_check=now,
            response_time_ms=50.5,
        )
        assert health.node_id == "node-1"
        assert health.status == NodeStatus.ONLINE

    def test_federation_health_response(self):
        """Test federation health response."""
        now = datetime.utcnow()
        node_health = [
            NodeHealthCheck(
                node_id="node-1",
                status=NodeStatus.ONLINE,
                last_check=now,
                response_time_ms=50.0,
            ),
            NodeHealthCheck(
                node_id="node-2",
                status=NodeStatus.OFFLINE,
                last_check=now,
                error="Connection timeout",
            ),
        ]
        response = FederationHealthResponse(
            total_nodes=2,
            online_nodes=1,
            offline_nodes=1,
            degraded_nodes=0,
            node_health=node_health,
        )
        assert response.total_nodes == 2
        assert response.online_nodes == 1
        assert response.offline_nodes == 1
        assert len(response.node_health) == 2
