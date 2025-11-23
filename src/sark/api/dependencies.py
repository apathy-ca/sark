"""FastAPI dependency injection utilities.

Provides reusable dependencies for route handlers, including
user context extraction from authenticated requests.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
import structlog

logger = structlog.get_logger(__name__)


class UserContext:
    """User context extracted from JWT token.

    Attributes:
        user_id: Unique user identifier
        email: User email address
        name: User display name
        roles: List of user roles
        teams: List of teams/groups user belongs to
        permissions: List of permissions granted to user
    """

    def __init__(self, data: dict):
        """Initialize user context from decoded JWT payload.

        Args:
            data: Dictionary containing user context data
        """
        self.user_id: str = data.get("user_id", "")
        self.email: str | None = data.get("email")
        self.name: str | None = data.get("name")
        self.roles: list[str] = data.get("roles", [])
        self.teams: list[str] = data.get("teams", [])
        self.permissions: set[str] = set(data.get("permissions", []))
        self._raw_payload: dict = data.get("_raw_payload", {})

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role.

        Args:
            role: Role name to check

        Returns:
            True if user has the role, False otherwise
        """
        return role in self.roles

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission.

        Args:
            permission: Permission to check (e.g., "servers:write")

        Returns:
            True if user has the permission, False otherwise
        """
        return permission in self.permissions

    def is_admin(self) -> bool:
        """Check if user has admin role.

        Returns:
            True if user is an admin, False otherwise
        """
        return self.has_role("admin")

    def in_team(self, team: str) -> bool:
        """Check if user belongs to a specific team.

        Args:
            team: Team name to check

        Returns:
            True if user is in the team, False otherwise
        """
        return team in self.teams

    def to_dict(self) -> dict:
        """Convert user context to dictionary.

        Returns:
            Dictionary representation of user context
        """
        return {
            "user_id": self.user_id,
            "email": self.email,
            "name": self.name,
            "roles": self.roles,
            "teams": self.teams,
            "permissions": list(self.permissions),
        }

    def __repr__(self) -> str:
        """String representation of user context."""
        return f"UserContext(user_id={self.user_id}, email={self.email}, roles={self.roles})"


def get_current_user(request: Request) -> UserContext:
    """FastAPI dependency to extract current authenticated user.

    Args:
        request: The incoming request (injected by FastAPI)

    Returns:
        UserContext object containing user information

    Raises:
        HTTPException: If user context is not available (unauthenticated)

    Usage:
        @router.get("/protected")
        async def protected_route(
            user: Annotated[UserContext, Depends(get_current_user)]
        ):
            return {"user_id": user.user_id}
    """
    if not hasattr(request.state, "user"):
        logger.error(
            "user_context_missing",
            path=request.url.path,
            message="User context not found in request state. Is auth middleware enabled?",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    user_data = request.state.user
    return UserContext(user_data)


def require_role(required_role: str):
    """Dependency factory to require a specific role.

    Args:
        required_role: The role required to access the endpoint

    Returns:
        Dependency function that validates the role

    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(
            user: Annotated[UserContext, Depends(require_role("admin"))]
        ):
            return {"message": "Admin access granted"}
    """

    def _check_role(user: Annotated[UserContext, Depends(get_current_user)]) -> UserContext:
        if not user.has_role(required_role):
            logger.warning(
                "role_access_denied",
                user_id=user.user_id,
                required_role=required_role,
                user_roles=user.roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required for this operation",
            )
        return user

    return _check_role


def require_permission(required_permission: str):
    """Dependency factory to require a specific permission.

    Args:
        required_permission: The permission required to access the endpoint

    Returns:
        Dependency function that validates the permission

    Usage:
        @router.post("/servers/")
        async def create_server(
            user: Annotated[UserContext, Depends(require_permission("servers:write"))]
        ):
            return {"message": "Server created"}
    """

    def _check_permission(
        user: Annotated[UserContext, Depends(get_current_user)]
    ) -> UserContext:
        if not user.has_permission(required_permission):
            logger.warning(
                "permission_access_denied",
                user_id=user.user_id,
                required_permission=required_permission,
                user_permissions=list(user.permissions),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{required_permission}' required for this operation",
            )
        return user

    return _check_permission


def require_team(required_team: str):
    """Dependency factory to require membership in a specific team.

    Args:
        required_team: The team required to access the endpoint

    Returns:
        Dependency function that validates team membership

    Usage:
        @router.get("/team/security/resources")
        async def team_resources(
            user: Annotated[UserContext, Depends(require_team("security"))]
        ):
            return {"resources": []}
    """

    def _check_team(user: Annotated[UserContext, Depends(get_current_user)]) -> UserContext:
        if not user.in_team(required_team):
            logger.warning(
                "team_access_denied",
                user_id=user.user_id,
                required_team=required_team,
                user_teams=user.teams,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Team membership '{required_team}' required for this operation",
            )
        return user

    return _check_team


# Type aliases for cleaner annotations
CurrentUser = Annotated[UserContext, Depends(get_current_user)]
