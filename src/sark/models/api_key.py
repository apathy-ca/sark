"""API Key model for authentication."""

from datetime import datetime
import uuid

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID

from sark.db.base import Base


class APIKey(Base):
    """API Key model for programmatic authentication.

    API keys provide an alternative to session-based authentication for
    machine-to-machine communication and automation.
    """

    __tablename__ = "api_keys"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Ownership
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    team_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Key metadata
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Key credentials
    key_prefix = Column(String(16), nullable=False, index=True, unique=True)
    key_hash = Column(String(255), nullable=False)  # bcrypt hash of full key

    # Permissions
    scopes = Column(
        ARRAY(String),
        nullable=False,
        default=list,
        comment="List of permission scopes (e.g., 'server:read', 'server:write')",
    )

    # Rate limiting
    rate_limit = Column(
        Integer,
        nullable=False,
        default=1000,
        comment="Maximum requests per minute",
    )

    # Status and lifecycle
    is_active = Column(Boolean, default=True, nullable=False, index=True, server_default="true")
    expires_at = Column(DateTime, nullable=True, index=True)

    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    last_used_ip = Column(String(45), nullable=True)  # IPv4/IPv6
    usage_count = Column(Integer, default=0, nullable=False, server_default="0")

    # Audit timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    revoked_at = Column(DateTime, nullable=True)
    revoked_by = Column(UUID(as_uuid=True), nullable=True)

    def __repr__(self) -> str:
        """String representation."""
        return f"<APIKey(id={self.id}, name={self.name}, prefix={self.key_prefix})>"

    @property
    def is_expired(self) -> bool:
        """Check if the API key has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the API key is valid (active and not expired)."""
        return self.is_active and not self.is_expired and self.revoked_at is None

    def revoke(self, revoked_by: uuid.UUID | None = None) -> None:
        """Revoke the API key.

        Args:
            revoked_by: UUID of the user who revoked the key
        """
        self.is_active = False
        self.revoked_at = datetime.utcnow()
        self.revoked_by = revoked_by

    def record_usage(self, ip_address: str | None = None) -> None:
        """Record API key usage.

        Args:
            ip_address: IP address of the request
        """
        self.last_used_at = datetime.utcnow()
        self.usage_count += 1
        if ip_address:
            self.last_used_ip = ip_address
