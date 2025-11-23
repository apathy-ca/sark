"""User context extraction and management."""

from uuid import UUID

from pydantic import BaseModel


class UserContext(BaseModel):
    """User context information extracted from authentication."""

    user_id: UUID
    email: str
    role: str
    teams: list[str]
    is_authenticated: bool = True
    is_admin: bool = False

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return self.role == role or self.is_admin

    def in_team(self, team: str) -> bool:
        """Check if user is a member of a specific team."""
        return team in self.teams

    def has_any_team(self, teams: list[str]) -> bool:
        """Check if user is a member of any of the specified teams."""
        return any(team in self.teams for team in teams)

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/serialization."""
        return {
            "user_id": str(self.user_id),
            "email": self.email,
            "role": self.role,
            "teams": self.teams,
            "is_authenticated": self.is_authenticated,
            "is_admin": self.is_admin,
        }


def extract_user_context(
    user_id: UUID,
    email: str,
    role: str,
    teams: list[str] | None = None,
) -> UserContext:
    """
    Extract user context from authentication data.

    Args:
        user_id: User ID
        email: User email
        role: User role
        teams: List of team names

    Returns:
        UserContext object
    """
    return UserContext(
        user_id=user_id,
        email=email,
        role=role,
        teams=teams or [],
        is_authenticated=True,
        is_admin=role == "admin",
    )
