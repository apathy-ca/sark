"""Session model for authentication session management."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Session(BaseModel):
    """Authentication session model.

    Sessions are stored in Redis with TTL for automatic expiration.
    Each user can have multiple concurrent sessions up to a configured limit.
    """

    session_id: str = Field(..., description="Unique session identifier (UUID)")
    user_id: UUID = Field(..., description="User ID associated with this session")
    created_at: datetime = Field(..., description="Session creation timestamp")
    expires_at: datetime = Field(..., description="Session expiration timestamp")
    last_activity: datetime = Field(..., description="Last activity timestamp")
    ip_address: str = Field(..., description="IP address of the client")
    user_agent: str | None = Field(None, description="User agent string")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional session metadata"
    )

    model_config = ConfigDict(
        # JSON serialization handled by to_dict() method
        ser_json_timedelta="iso8601",
    )

    def is_expired(self, current_time: datetime | None = None) -> bool:
        """Check if session is expired.

        Args:
            current_time: Current time for comparison (defaults to now)

        Returns:
            True if session is expired, False otherwise
        """
        if current_time is None:
            current_time = datetime.now(UTC)
        return current_time >= self.expires_at

    def to_dict(self) -> dict[str, Any]:
        """Convert session to dictionary for Redis storage.

        Returns:
            Dictionary representation of session
        """
        return {
            "session_id": self.session_id,
            "user_id": str(self.user_id),
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent or "",
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Session":
        """Create session from dictionary (Redis retrieval).

        Args:
            data: Dictionary representation of session

        Returns:
            Session instance
        """
        return cls(
            session_id=data["session_id"],
            user_id=UUID(data["user_id"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
            ip_address=data["ip_address"],
            user_agent=data.get("user_agent") or None,
            metadata=data.get("metadata", {}),
        )


class SessionCreateRequest(BaseModel):
    """Request model for creating a new session."""

    user_id: UUID
    ip_address: str
    user_agent: str | None = None
    timeout_seconds: int | None = None


class SessionResponse(BaseModel):
    """Response model for session data."""

    session_id: str
    user_id: UUID
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    ip_address: str
    user_agent: str | None = None
    is_expired: bool = False

    model_config = ConfigDict(
        # JSON serialization uses Pydantic V2 defaults
        ser_json_timedelta="iso8601",
    )


class SessionListResponse(BaseModel):
    """Response model for listing sessions."""

    sessions: list[SessionResponse]
    total: int
    active: int
    expired: int
