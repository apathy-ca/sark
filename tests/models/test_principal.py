"""Tests for Principal model and principal type system."""

from datetime import UTC, datetime

import pytest

from sark.models.principal import Principal, PrincipalType


class TestPrincipalType:
    """Tests for PrincipalType enum."""

    def test_principal_type_values(self) -> None:
        """Test PrincipalType enum has all required values."""
        assert PrincipalType.HUMAN.value == "human"
        assert PrincipalType.AGENT.value == "agent"
        assert PrincipalType.SERVICE.value == "service"
        assert PrincipalType.DEVICE.value == "device"

    def test_principal_type_count(self) -> None:
        """Test PrincipalType has exactly 4 types."""
        assert len(PrincipalType) == 4


class TestPrincipalModel:
    """Tests for Principal model."""

    def test_principal_creation_human(self) -> None:
        """Test creating a human principal."""
        principal = Principal(
            email="human@example.com",
            full_name="Human User",
            hashed_password="hashed_pw",
            is_active=True,
            is_admin=False,
            role="developer",
            principal_type=PrincipalType.HUMAN,
            identity_token_type="jwt",
        )

        assert principal.email == "human@example.com"
        assert principal.principal_type == PrincipalType.HUMAN
        assert principal.identity_token_type == "jwt"
        assert principal.revoked_at is None
        assert principal.role == "developer"
        assert principal.is_active is True
        assert principal.is_admin is False

    def test_principal_creation_agent(self) -> None:
        """Test creating an AI agent principal."""
        principal = Principal(
            email="agent@example.com",
            full_name="AI Agent",
            hashed_password="hashed_pw",
            is_active=True,
            is_admin=False,
            role="agent",
            principal_type=PrincipalType.AGENT,
            identity_token_type="api_key",
        )

        assert principal.email == "agent@example.com"
        assert principal.principal_type == PrincipalType.AGENT
        assert principal.identity_token_type == "api_key"

    def test_principal_creation_service(self) -> None:
        """Test creating a service principal."""
        principal = Principal(
            email="service@example.com",
            full_name="Background Service",
            hashed_password="hashed_pw",
            is_active=True,
            is_admin=False,
            role="service",
            principal_type=PrincipalType.SERVICE,
            identity_token_type="certificate",
        )

        assert principal.email == "service@example.com"
        assert principal.principal_type == PrincipalType.SERVICE
        assert principal.identity_token_type == "certificate"

    def test_principal_creation_device(self) -> None:
        """Test creating a device principal."""
        principal = Principal(
            email="device@example.com",
            full_name="IoT Device",
            hashed_password="hashed_pw",
            is_active=True,
            is_admin=False,
            role="device",
            principal_type=PrincipalType.DEVICE,
            identity_token_type="certificate",
        )

        assert principal.email == "device@example.com"
        assert principal.principal_type == PrincipalType.DEVICE
        assert principal.identity_token_type == "certificate"

    def test_principal_default_type(self) -> None:
        """Test principal defaults to HUMAN type when specified."""
        # Note: SQLAlchemy defaults are only applied when inserting to DB, not in Python
        # So we specify the default explicitly for in-memory objects
        principal = Principal(
            email="test@example.com",
            full_name="Test User",
            hashed_password="hashed_pw",
            principal_type=PrincipalType.HUMAN,
            identity_token_type="jwt",
        )

        assert principal.principal_type == PrincipalType.HUMAN
        assert principal.identity_token_type == "jwt"

    def test_principal_revoked_at(self) -> None:
        """Test principal revoked_at timestamp."""
        now = datetime.now(UTC)
        principal = Principal(
            email="revoked@example.com",
            full_name="Revoked User",
            hashed_password="hashed_pw",
            principal_type=PrincipalType.HUMAN,
            identity_token_type="jwt",
            revoked_at=now,
        )

        assert principal.revoked_at == now

    def test_principal_repr(self) -> None:
        """Test principal string representation includes type."""
        principal = Principal(
            email="test@example.com",
            full_name="Test User",
            hashed_password="hashed_pw",
            role="developer",
            principal_type=PrincipalType.AGENT,
            identity_token_type="api_key",
        )

        repr_str = repr(principal)
        assert "Principal" in repr_str
        assert "test@example.com" in repr_str
        assert "agent" in repr_str
        assert "developer" in repr_str


class TestPrincipalToPolicyInput:
    """Tests for Principal.to_policy_input() method."""

    def test_to_policy_input_basic(self) -> None:
        """Test to_policy_input() returns correct structure."""
        from uuid import uuid4

        principal_id = uuid4()
        principal = Principal(
            id=principal_id,
            email="test@example.com",
            full_name="Test User",
            hashed_password="hashed_pw",
            role="developer",
            principal_type=PrincipalType.HUMAN,
            identity_token_type="jwt",
            extra_metadata={"department": "engineering"},
        )

        policy_input = principal.to_policy_input()

        assert policy_input["id"] == str(principal_id)
        assert policy_input["type"] == "human"
        assert policy_input["attributes"]["role"] == "developer"
        assert policy_input["attributes"]["teams"] == []
        assert policy_input["attributes"]["department"] == "engineering"

    def test_to_policy_input_agent(self) -> None:
        """Test to_policy_input() for agent principal."""
        from uuid import uuid4

        principal_id = uuid4()
        principal = Principal(
            id=principal_id,
            email="agent@example.com",
            full_name="AI Agent",
            hashed_password="hashed_pw",
            role="agent",
            principal_type=PrincipalType.AGENT,
            identity_token_type="api_key",
        )

        policy_input = principal.to_policy_input()

        assert policy_input["type"] == "agent"
        assert policy_input["attributes"]["role"] == "agent"

    def test_to_policy_input_service(self) -> None:
        """Test to_policy_input() for service principal."""
        from uuid import uuid4

        principal_id = uuid4()
        principal = Principal(
            id=principal_id,
            email="service@example.com",
            full_name="Background Service",
            hashed_password="hashed_pw",
            role="service",
            principal_type=PrincipalType.SERVICE,
            identity_token_type="certificate",
        )

        policy_input = principal.to_policy_input()

        assert policy_input["type"] == "service"
        assert policy_input["attributes"]["role"] == "service"

    def test_to_policy_input_device(self) -> None:
        """Test to_policy_input() for device principal."""
        from uuid import uuid4

        principal_id = uuid4()
        principal = Principal(
            id=principal_id,
            email="device@example.com",
            full_name="IoT Device",
            hashed_password="hashed_pw",
            role="device",
            principal_type=PrincipalType.DEVICE,
            identity_token_type="certificate",
        )

        policy_input = principal.to_policy_input()

        assert policy_input["type"] == "device"
        assert policy_input["attributes"]["role"] == "device"

    def test_to_policy_input_with_teams(self) -> None:
        """Test to_policy_input() includes team names."""
        from uuid import uuid4
        from sark.models.principal import Team

        principal_id = uuid4()
        principal = Principal(
            id=principal_id,
            email="test@example.com",
            full_name="Test User",
            hashed_password="hashed_pw",
            role="developer",
            principal_type=PrincipalType.HUMAN,
            identity_token_type="jwt",
        )

        # Create mock teams
        team1 = Team(name="engineering", description="Engineering team")
        team2 = Team(name="security", description="Security team")
        principal.teams = [team1, team2]

        policy_input = principal.to_policy_input()

        assert "engineering" in policy_input["attributes"]["teams"]
        assert "security" in policy_input["attributes"]["teams"]
        assert len(policy_input["attributes"]["teams"]) == 2

    def test_to_policy_input_with_extra_metadata(self) -> None:
        """Test to_policy_input() merges extra_metadata into attributes."""
        from uuid import uuid4

        principal_id = uuid4()
        principal = Principal(
            id=principal_id,
            email="test@example.com",
            full_name="Test User",
            hashed_password="hashed_pw",
            role="developer",
            principal_type=PrincipalType.HUMAN,
            identity_token_type="jwt",
            extra_metadata={
                "department": "engineering",
                "location": "remote",
                "clearance_level": "confidential",
            },
        )

        policy_input = principal.to_policy_input()

        assert policy_input["attributes"]["department"] == "engineering"
        assert policy_input["attributes"]["location"] == "remote"
        assert policy_input["attributes"]["clearance_level"] == "confidential"

    def test_to_policy_input_empty_extra_metadata(self) -> None:
        """Test to_policy_input() handles None extra_metadata."""
        from uuid import uuid4

        principal_id = uuid4()
        principal = Principal(
            id=principal_id,
            email="test@example.com",
            full_name="Test User",
            hashed_password="hashed_pw",
            role="developer",
            principal_type=PrincipalType.HUMAN,
            identity_token_type="jwt",
            extra_metadata=None,
        )

        policy_input = principal.to_policy_input()

        # Should not raise error, just have role and teams
        assert "role" in policy_input["attributes"]
        assert "teams" in policy_input["attributes"]
