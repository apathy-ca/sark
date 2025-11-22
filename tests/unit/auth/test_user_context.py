"""Comprehensive tests for UserContext and related functionality."""

from uuid import uuid4

import pytest

from sark.services.auth.user_context import UserContext, extract_user_context


class TestUserContext:
    """Test suite for UserContext class."""

    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing."""
        return {
            "user_id": uuid4(),
            "email": "test@example.com",
            "role": "user",
            "teams": ["team-alpha", "team-beta"],
        }

    def test_user_context_initialization(self, sample_user_data):
        """Test UserContext initialization with all fields."""
        context = UserContext(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role=sample_user_data["role"],
            teams=sample_user_data["teams"],
            is_authenticated=True,
            is_admin=False,
        )

        assert context.user_id == sample_user_data["user_id"]
        assert context.email == sample_user_data["email"]
        assert context.role == sample_user_data["role"]
        assert context.teams == sample_user_data["teams"]
        assert context.is_authenticated is True
        assert context.is_admin is False

    def test_user_context_defaults(self, sample_user_data):
        """Test UserContext defaults for optional fields."""
        context = UserContext(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role=sample_user_data["role"],
            teams=sample_user_data["teams"],
        )

        assert context.is_authenticated is True  # Default value
        assert context.is_admin is False  # Default value

    # ===== has_role() Tests =====

    def test_has_role_matching(self, sample_user_data):
        """Test has_role returns True when role matches."""
        context = UserContext(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role="user",
            teams=sample_user_data["teams"],
        )

        assert context.has_role("user") is True

    def test_has_role_not_matching(self, sample_user_data):
        """Test has_role returns False when role doesn't match."""
        context = UserContext(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role="user",
            teams=sample_user_data["teams"],
        )

        assert context.has_role("admin") is False

    def test_has_role_admin_override(self, sample_user_data):
        """Test has_role returns True for any role when is_admin is True."""
        context = UserContext(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role="admin",
            teams=sample_user_data["teams"],
            is_admin=True,
        )

        # Admin should have all roles
        assert context.has_role("user") is True
        assert context.has_role("admin") is True
        assert context.has_role("moderator") is True
        assert context.has_role("any_role") is True

    def test_has_role_case_sensitive(self, sample_user_data):
        """Test has_role is case-sensitive."""
        context = UserContext(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role="User",
            teams=sample_user_data["teams"],
        )

        assert context.has_role("User") is True
        assert context.has_role("user") is False

    # ===== in_team() Tests =====

    def test_in_team_member(self, sample_user_data):
        """Test in_team returns True when user is in team."""
        context = UserContext(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role=sample_user_data["role"],
            teams=["team-alpha", "team-beta"],
        )

        assert context.in_team("team-alpha") is True
        assert context.in_team("team-beta") is True

    def test_in_team_not_member(self, sample_user_data):
        """Test in_team returns False when user is not in team."""
        context = UserContext(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role=sample_user_data["role"],
            teams=["team-alpha"],
        )

        assert context.in_team("team-gamma") is False

    def test_in_team_empty_teams(self, sample_user_data):
        """Test in_team returns False when user has no teams."""
        context = UserContext(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role=sample_user_data["role"],
            teams=[],
        )

        assert context.in_team("team-alpha") is False

    def test_in_team_case_sensitive(self, sample_user_data):
        """Test in_team is case-sensitive."""
        context = UserContext(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role=sample_user_data["role"],
            teams=["Team-Alpha"],
        )

        assert context.in_team("Team-Alpha") is True
        assert context.in_team("team-alpha") is False

    # ===== has_any_team() Tests =====

    def test_has_any_team_single_match(self, sample_user_data):
        """Test has_any_team returns True when user is in one of the teams."""
        context = UserContext(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role=sample_user_data["role"],
            teams=["team-alpha", "team-beta"],
        )

        assert context.has_any_team(["team-alpha", "team-gamma"]) is True

    def test_has_any_team_multiple_matches(self, sample_user_data):
        """Test has_any_team returns True when user is in multiple teams."""
        context = UserContext(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role=sample_user_data["role"],
            teams=["team-alpha", "team-beta"],
        )

        assert context.has_any_team(["team-alpha", "team-beta"]) is True

    def test_has_any_team_no_match(self, sample_user_data):
        """Test has_any_team returns False when user is not in any team."""
        context = UserContext(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role=sample_user_data["role"],
            teams=["team-alpha"],
        )

        assert context.has_any_team(["team-gamma", "team-delta"]) is False

    def test_has_any_team_empty_user_teams(self, sample_user_data):
        """Test has_any_team returns False when user has no teams."""
        context = UserContext(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role=sample_user_data["role"],
            teams=[],
        )

        assert context.has_any_team(["team-alpha", "team-beta"]) is False

    def test_has_any_team_empty_check_list(self, sample_user_data):
        """Test has_any_team returns False when check list is empty."""
        context = UserContext(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role=sample_user_data["role"],
            teams=["team-alpha"],
        )

        assert context.has_any_team([]) is False

    # ===== to_dict() Tests =====

    def test_to_dict_complete(self, sample_user_data):
        """Test to_dict returns complete dictionary representation."""
        context = UserContext(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role=sample_user_data["role"],
            teams=sample_user_data["teams"],
            is_authenticated=True,
            is_admin=False,
        )

        result = context.to_dict()

        assert result["user_id"] == str(sample_user_data["user_id"])
        assert result["email"] == sample_user_data["email"]
        assert result["role"] == sample_user_data["role"]
        assert result["teams"] == sample_user_data["teams"]
        assert result["is_authenticated"] is True
        assert result["is_admin"] is False

    def test_to_dict_uuid_conversion(self, sample_user_data):
        """Test to_dict converts UUID to string."""
        user_id = uuid4()
        context = UserContext(
            user_id=user_id,
            email=sample_user_data["email"],
            role=sample_user_data["role"],
            teams=sample_user_data["teams"],
        )

        result = context.to_dict()

        assert result["user_id"] == str(user_id)
        assert isinstance(result["user_id"], str)

    def test_to_dict_with_admin(self, sample_user_data):
        """Test to_dict includes is_admin flag."""
        context = UserContext(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role="admin",
            teams=sample_user_data["teams"],
            is_admin=True,
        )

        result = context.to_dict()

        assert result["is_admin"] is True


class TestExtractUserContext:
    """Test suite for extract_user_context function."""

    def test_extract_user_context_basic(self):
        """Test extracting user context with basic data."""
        user_id = uuid4()
        email = "test@example.com"
        role = "user"
        teams = ["team-alpha"]

        context = extract_user_context(
            user_id=user_id,
            email=email,
            role=role,
            teams=teams,
        )

        assert isinstance(context, UserContext)
        assert context.user_id == user_id
        assert context.email == email
        assert context.role == role
        assert context.teams == teams
        assert context.is_authenticated is True

    def test_extract_user_context_without_teams(self):
        """Test extracting user context without teams defaults to empty list."""
        user_id = uuid4()
        email = "test@example.com"
        role = "user"

        context = extract_user_context(
            user_id=user_id,
            email=email,
            role=role,
        )

        assert context.teams == []

    def test_extract_user_context_none_teams(self):
        """Test extracting user context with None teams defaults to empty list."""
        user_id = uuid4()
        email = "test@example.com"
        role = "user"

        context = extract_user_context(
            user_id=user_id,
            email=email,
            role=role,
            teams=None,
        )

        assert context.teams == []

    def test_extract_user_context_admin_role(self):
        """Test extracting user context with admin role sets is_admin flag."""
        user_id = uuid4()
        email = "admin@example.com"
        role = "admin"

        context = extract_user_context(
            user_id=user_id,
            email=email,
            role=role,
        )

        assert context.role == "admin"
        assert context.is_admin is True

    def test_extract_user_context_non_admin_role(self):
        """Test extracting user context with non-admin role sets is_admin to False."""
        user_id = uuid4()
        email = "user@example.com"
        role = "user"

        context = extract_user_context(
            user_id=user_id,
            email=email,
            role=role,
        )

        assert context.role == "user"
        assert context.is_admin is False

    def test_extract_user_context_multiple_teams(self):
        """Test extracting user context with multiple teams."""
        user_id = uuid4()
        email = "test@example.com"
        role = "user"
        teams = ["team-alpha", "team-beta", "team-gamma"]

        context = extract_user_context(
            user_id=user_id,
            email=email,
            role=role,
            teams=teams,
        )

        assert context.teams == teams
        assert len(context.teams) == 3

    def test_extract_user_context_always_authenticated(self):
        """Test extracted user context is always authenticated."""
        user_id = uuid4()
        email = "test@example.com"
        role = "user"

        context = extract_user_context(
            user_id=user_id,
            email=email,
            role=role,
        )

        assert context.is_authenticated is True

    def test_extract_user_context_special_email(self):
        """Test extracting user context with special characters in email."""
        user_id = uuid4()
        email = "test+tag@sub.example.com"
        role = "user"

        context = extract_user_context(
            user_id=user_id,
            email=email,
            role=role,
        )

        assert context.email == email
