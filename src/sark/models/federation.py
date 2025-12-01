"""
Federation models for SARK v2.0.

This module defines Pydantic schemas for federation API requests/responses
and supporting data structures for cross-organization governance.

The SQLAlchemy ORM model (FederationNode) is defined in models/base.py.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field, validator
from uuid import UUID


class TrustLevel(str, Enum):
    """Trust levels for federation nodes."""
    UNTRUSTED = "untrusted"
    PENDING = "pending"
    TRUSTED = "trusted"
    REVOKED = "revoked"


class NodeStatus(str, Enum):
    """Status of a federation node."""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class DiscoveryMethod(str, Enum):
    """Methods for discovering federation nodes."""
    DNS_SD = "dns-sd"  # DNS Service Discovery (RFC 6763)
    MDNS = "mdns"      # Multicast DNS (RFC 6762)
    MANUAL = "manual"  # Manual configuration
    CONSUL = "consul"  # Consul service discovery


# ============================================================================
# Federation Node Schemas
# ============================================================================


class FederationNodeBase(BaseModel):
    """Base schema for federation node."""
    node_id: str = Field(..., description="Unique identifier for the federation node")
    name: str = Field(..., description="Human-readable name for the node")
    endpoint: str = Field(..., description="Base URL for the node's API (e.g., https://sark.example.com)")
    trust_anchor_cert: str = Field(..., description="PEM-encoded X.509 certificate for mTLS trust")
    enabled: bool = Field(default=True, description="Whether this node is enabled for federation")
    rate_limit_per_hour: Optional[int] = Field(default=10000, description="Maximum requests per hour from this node")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata for this node")

    @validator('endpoint')
    def validate_endpoint(cls, v):
        """Validate endpoint is a proper URL."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Endpoint must be a valid HTTP/HTTPS URL')
        return v.rstrip('/')

    @validator('trust_anchor_cert')
    def validate_cert(cls, v):
        """Validate certificate is PEM format."""
        if not v.strip().startswith('-----BEGIN CERTIFICATE-----'):
            raise ValueError('Certificate must be in PEM format')
        if not v.strip().endswith('-----END CERTIFICATE-----'):
            raise ValueError('Certificate must be in PEM format')
        return v


class FederationNodeCreate(FederationNodeBase):
    """Schema for creating a federation node."""
    pass


class FederationNodeUpdate(BaseModel):
    """Schema for updating a federation node."""
    name: Optional[str] = None
    endpoint: Optional[str] = None
    trust_anchor_cert: Optional[str] = None
    enabled: Optional[bool] = None
    rate_limit_per_hour: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

    @validator('endpoint')
    def validate_endpoint(cls, v):
        """Validate endpoint is a proper URL."""
        if v is not None and not v.startswith(('http://', 'https://')):
            raise ValueError('Endpoint must be a valid HTTP/HTTPS URL')
        return v.rstrip('/') if v else v


class FederationNodeResponse(FederationNodeBase):
    """Schema for federation node response."""
    id: UUID
    trusted_since: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Service Discovery Schemas
# ============================================================================


class ServiceDiscoveryRecord(BaseModel):
    """Service discovery record for DNS-SD/mDNS."""
    service_name: str = Field(..., description="Service name (e.g., _sark._tcp)")
    instance_name: str = Field(..., description="Instance name (e.g., sark-prod-us-east)")
    hostname: str = Field(..., description="Hostname or IP address")
    port: int = Field(..., description="Port number")
    txt_records: Dict[str, str] = Field(default_factory=dict, description="TXT record key-value pairs")
    discovered_at: datetime = Field(default_factory=datetime.utcnow, description="When this record was discovered")
    ttl: int = Field(default=3600, description="Time-to-live in seconds")

    @validator('port')
    def validate_port(cls, v):
        """Validate port is in valid range."""
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v


class DiscoveryQuery(BaseModel):
    """Query parameters for service discovery."""
    method: DiscoveryMethod = Field(default=DiscoveryMethod.MDNS, description="Discovery method to use")
    service_type: str = Field(default="_sark._tcp.local.", description="Service type to discover")
    timeout_seconds: int = Field(default=5, description="Discovery timeout in seconds")
    max_results: int = Field(default=10, description="Maximum number of results to return")


class DiscoveryResponse(BaseModel):
    """Response from service discovery."""
    method: DiscoveryMethod
    records: List[ServiceDiscoveryRecord]
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    total_found: int


# ============================================================================
# mTLS Trust Schemas
# ============================================================================


class CertificateInfo(BaseModel):
    """Information about an X.509 certificate."""
    subject: str = Field(..., description="Certificate subject DN")
    issuer: str = Field(..., description="Certificate issuer DN")
    serial_number: str = Field(..., description="Certificate serial number")
    not_before: datetime = Field(..., description="Certificate validity start")
    not_after: datetime = Field(..., description="Certificate validity end")
    fingerprint_sha256: str = Field(..., description="SHA-256 fingerprint of the certificate")
    key_usage: List[str] = Field(default_factory=list, description="Key usage extensions")
    extended_key_usage: List[str] = Field(default_factory=list, description="Extended key usage extensions")


class TrustEstablishmentRequest(BaseModel):
    """Request to establish mTLS trust with a node."""
    node_id: str = Field(..., description="Node ID to establish trust with")
    client_cert: str = Field(..., description="PEM-encoded client certificate")
    challenge: Optional[str] = Field(None, description="Challenge string for mutual verification")


class TrustEstablishmentResponse(BaseModel):
    """Response from trust establishment."""
    success: bool
    node_id: str
    trust_level: TrustLevel
    certificate_info: CertificateInfo
    challenge_response: Optional[str] = None
    expires_at: datetime
    message: Optional[str] = None


class TrustVerificationRequest(BaseModel):
    """Request to verify trust with a node."""
    node_id: str
    certificate_fingerprint: str


class TrustVerificationResponse(BaseModel):
    """Response from trust verification."""
    verified: bool
    node_id: str
    trust_level: TrustLevel
    certificate_info: Optional[CertificateInfo] = None
    error: Optional[str] = None


# ============================================================================
# Federated Resource Access Schemas
# ============================================================================


class FederatedResourceRequest(BaseModel):
    """Request to access a resource on a federated node."""
    target_node_id: str = Field(..., description="Federation node hosting the resource")
    resource_id: str = Field(..., description="Resource ID to access")
    capability_id: Optional[str] = Field(None, description="Specific capability to invoke")
    principal_id: str = Field(..., description="Principal making the request")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments for capability invocation")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional request context")


class FederatedResourceResponse(BaseModel):
    """Response from federated resource access."""
    success: bool
    node_id: str
    resource_id: str
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: float
    audit_correlation_id: str = Field(..., description="Correlation ID for cross-node audit trail")


# ============================================================================
# Routing Schemas
# ============================================================================


class RouteEntry(BaseModel):
    """Routing entry for federated resources."""
    resource_id: str
    node_id: str
    endpoint: str
    last_verified: datetime
    health_status: NodeStatus
    latency_ms: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RoutingTable(BaseModel):
    """Routing table for federated resources."""
    entries: List[RouteEntry]
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(default=1)


class RouteQuery(BaseModel):
    """Query to find a route to a resource."""
    resource_id: str
    preferred_node: Optional[str] = None
    include_unhealthy: bool = Field(default=False)


class RouteResponse(BaseModel):
    """Response with routing information."""
    resource_id: str
    available_routes: List[RouteEntry]
    recommended_route: Optional[RouteEntry] = None


# ============================================================================
# Audit Correlation Schemas
# ============================================================================


class FederatedAuditEvent(BaseModel):
    """Audit event for federated operations."""
    correlation_id: str = Field(..., description="Cross-node correlation ID")
    source_node_id: str = Field(..., description="Node that initiated the request")
    target_node_id: str = Field(..., description="Node that processed the request")
    principal_id: str
    resource_id: str
    capability_id: Optional[str] = None
    action: str
    success: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration_ms: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AuditCorrelationQuery(BaseModel):
    """Query to find correlated audit events across nodes."""
    correlation_id: Optional[str] = None
    principal_id: Optional[str] = None
    resource_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    node_ids: List[str] = Field(default_factory=list)


class AuditCorrelationResponse(BaseModel):
    """Response with correlated audit events."""
    events: List[FederatedAuditEvent]
    total_events: int
    nodes_queried: List[str]
    query_duration_ms: float


# ============================================================================
# Health Check Schemas
# ============================================================================


class NodeHealthCheck(BaseModel):
    """Health check for a federation node."""
    node_id: str
    status: NodeStatus
    last_check: datetime
    response_time_ms: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FederationHealthResponse(BaseModel):
    """Overall federation health status."""
    total_nodes: int
    online_nodes: int
    offline_nodes: int
    degraded_nodes: int
    node_health: List[NodeHealthCheck]
    checked_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Enums
    "TrustLevel",
    "NodeStatus",
    "DiscoveryMethod",

    # Federation Node
    "FederationNodeBase",
    "FederationNodeCreate",
    "FederationNodeUpdate",
    "FederationNodeResponse",

    # Service Discovery
    "ServiceDiscoveryRecord",
    "DiscoveryQuery",
    "DiscoveryResponse",

    # mTLS Trust
    "CertificateInfo",
    "TrustEstablishmentRequest",
    "TrustEstablishmentResponse",
    "TrustVerificationRequest",
    "TrustVerificationResponse",

    # Federated Resource Access
    "FederatedResourceRequest",
    "FederatedResourceResponse",

    # Routing
    "RouteEntry",
    "RoutingTable",
    "RouteQuery",
    "RouteResponse",

    # Audit Correlation
    "FederatedAuditEvent",
    "AuditCorrelationQuery",
    "AuditCorrelationResponse",

    # Health
    "NodeHealthCheck",
    "FederationHealthResponse",
]
