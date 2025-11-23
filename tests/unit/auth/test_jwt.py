"""Comprehensive tests for JWT token handling and validation."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import UUID, uuid4

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
import pytest

from sark.services.auth.jwt import JWTHandler, get_current_user
from sark.services.auth.user_context import UserContext


class TestJWTHandler:
    """Test suite for JWTHandler class."""

    @pytest.fixture
    def handler(self):
        """Create a JWT handler instance for testing."""
        return JWTHandler(
            secret_key="test_secret_key_12345",
            algorithm="HS256",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7,
        )

    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing."""
        return {
            "user_id": uuid4(),
            "email": "test@example.com",
            "role": "user",
            "teams": ["team-alpha", "team-beta"],
        }

    # ===== Access Token Creation Tests =====

    def test_create_access_token_basic(self, handler, sample_user_data):
        """Test creating a basic access token."""
        token = handler.create_access_token(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role=sample_user_data["role"],
        )

        assert isinstance(token, str)
        assert len(token) > 0

        # Decode to verify structure
        payload = jwt.decode(token, handler.secret_key, algorithms=[handler.algorithm])
        assert payload["sub"] == str(sample_user_data["user_id"])
        assert payload["email"] == sample_user_data["email"]
        assert payload["role"] == sample_user_data["role"]
        assert payload["type"] == "access"
        assert "iat" in payload
        assert "exp" in payload

    def test_create_access_token_with_teams(self, handler, sample_user_data):
        """Test creating access token with teams."""
        token = handler.create_access_token(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role=sample_user_data["role"],
            teams=sample_user_data["teams"],
        )

        payload = jwt.decode(token, handler.secret_key, algorithms=[handler.algorithm])
        assert payload["teams"] == sample_user_data["teams"]

    def test_create_access_token_without_teams(self, handler, sample_user_data):
        """Test creating access token without teams defaults to empty list."""
        token = handler.create_access_token(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role=sample_user_data["role"],
        )

        payload = jwt.decode(token, handler.secret_key, algorithms=[handler.algorithm])
        assert payload["teams"] == []

    def test_create_access_token_with_extra_claims(self, handler, sample_user_data):
        """Test creating access token with extra claims."""
        extra_claims = {
            "custom_field": "custom_value",
            "department": "engineering",
        }

        token = handler.create_access_token(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role=sample_user_data["role"],
            extra_claims=extra_claims,
        )

        payload = jwt.decode(token, handler.secret_key, algorithms=[handler.algorithm])
        assert payload["custom_field"] == "custom_value"
        assert payload["department"] == "engineering"

    def test_access_token_expiration(self, handler, sample_user_data):
        """Test access token has correct expiration time."""
        before_create = datetime.now(UTC)
        token = handler.create_access_token(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role=sample_user_data["role"],
        )
        datetime.now(UTC)

        payload = jwt.decode(token, handler.secret_key, algorithms=[handler.algorithm])
        exp_time = datetime.fromtimestamp(payload["exp"], UTC)

        # Should expire in 30 minutes (with small tolerance)
        expected_exp = before_create + timedelta(minutes=handler.access_token_expire_minutes)
        assert abs((exp_time - expected_exp).total_seconds()) < 5

    # ===== Refresh Token Creation Tests =====

    def test_create_refresh_token_basic(self, handler, sample_user_data):
        """Test creating a basic refresh token."""
        token = handler.create_refresh_token(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
        )

        assert isinstance(token, str)
        assert len(token) > 0

        # Decode to verify structure
        payload = jwt.decode(token, handler.secret_key, algorithms=[handler.algorithm])
        assert payload["sub"] == str(sample_user_data["user_id"])
        assert payload["email"] == sample_user_data["email"]
        assert payload["type"] == "refresh"
        assert "iat" in payload
        assert "exp" in payload
        # Refresh tokens should not have role or teams
        assert "role" not in payload
        assert "teams" not in payload

    def test_refresh_token_expiration(self, handler, sample_user_data):
        """Test refresh token has correct expiration time."""
        before_create = datetime.now(UTC)
        token = handler.create_refresh_token(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
        )
        datetime.now(UTC)

        payload = jwt.decode(token, handler.secret_key, algorithms=[handler.algorithm])
        exp_time = datetime.fromtimestamp(payload["exp"], UTC)

        # Should expire in 7 days (with small tolerance)
        expected_exp = before_create + timedelta(days=handler.refresh_token_expire_days)
        assert abs((exp_time - expected_exp).total_seconds()) < 5

    # ===== Token Decoding Tests =====

    def test_decode_valid_access_token(self, handler, sample_user_data):
        """Test decoding a valid access token."""
        token = handler.create_access_token(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role=sample_user_data["role"],
            teams=sample_user_data["teams"],
        )

        payload = handler.decode_token(token)
        assert payload["sub"] == str(sample_user_data["user_id"])
        assert payload["email"] == sample_user_data["email"]
        assert payload["role"] == sample_user_data["role"]
        assert payload["teams"] == sample_user_data["teams"]
        assert payload["type"] == "access"

    def test_decode_expired_token(self, handler, sample_user_data):
        """Test decoding an expired token raises HTTPException."""
        # Create a token that's already expired
        now = datetime.now(UTC)
        past = now - timedelta(hours=1)

        claims = {
            "sub": str(sample_user_data["user_id"]),
            "email": sample_user_data["email"],
            "role": sample_user_data["role"],
            "teams": [],
            "iat": past,
            "exp": past,  # Already expired
            "type": "access",
        }
        token = jwt.encode(claims, handler.secret_key, algorithm=handler.algorithm)

        with pytest.raises(HTTPException) as exc_info:
            handler.decode_token(token)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail

    def test_decode_invalid_signature(self, handler, sample_user_data):
        """Test decoding a token with invalid signature raises HTTPException."""
        # Create token with one key
        token = handler.create_access_token(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role=sample_user_data["role"],
        )

        # Try to decode with different key
        wrong_handler = JWTHandler(secret_key="wrong_secret_key")
        with pytest.raises(HTTPException) as exc_info:
            wrong_handler.decode_token(token)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail

    def test_decode_malformed_token(self, handler):
        """Test decoding a malformed token raises HTTPException."""
        malformed_token = "this.is.not.a.valid.jwt"

        with pytest.raises(HTTPException) as exc_info:
            handler.decode_token(malformed_token)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail

    def test_decode_refresh_token_as_access_fails(self, handler, sample_user_data):
        """Test decoding a refresh token as access token fails."""
        refresh_token = handler.create_refresh_token(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
        )

        with pytest.raises(HTTPException) as exc_info:
            handler.decode_token(refresh_token)

        assert exc_info.value.status_code == 401
        assert "Invalid token type" in exc_info.value.detail

    def test_decode_token_missing_type_field(self, handler, sample_user_data):
        """Test decoding a token without type field fails."""
        # Manually create a token without 'type' field
        claims = {
            "sub": str(sample_user_data["user_id"]),
            "email": sample_user_data["email"],
            "exp": datetime.now(UTC) + timedelta(minutes=30),
        }
        token = jwt.encode(claims, handler.secret_key, algorithm=handler.algorithm)

        with pytest.raises(HTTPException) as exc_info:
            handler.decode_token(token)

        assert exc_info.value.status_code == 401
        assert "Invalid token type" in exc_info.value.detail

    # ===== Refresh Token Decoding Tests =====

    def test_decode_valid_refresh_token(self, handler, sample_user_data):
        """Test decoding a valid refresh token."""
        token = handler.create_refresh_token(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
        )

        payload = handler.decode_refresh_token(token)
        assert payload["sub"] == str(sample_user_data["user_id"])
        assert payload["email"] == sample_user_data["email"]
        assert payload["type"] == "refresh"

    def test_decode_expired_refresh_token(self, handler, sample_user_data):
        """Test decoding an expired refresh token raises HTTPException."""
        # Create a refresh token that's already expired
        now = datetime.now(UTC)
        past = now - timedelta(days=1)

        claims = {
            "sub": str(sample_user_data["user_id"]),
            "email": sample_user_data["email"],
            "iat": past,
            "exp": past,  # Already expired
            "type": "refresh",
        }
        token = jwt.encode(claims, handler.secret_key, algorithm=handler.algorithm)

        with pytest.raises(HTTPException) as exc_info:
            handler.decode_refresh_token(token)

        assert exc_info.value.status_code == 401
        assert "Could not validate refresh token" in exc_info.value.detail

    def test_decode_access_token_as_refresh_fails(self, handler, sample_user_data):
        """Test decoding an access token as refresh token fails."""
        access_token = handler.create_access_token(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role=sample_user_data["role"],
        )

        with pytest.raises(HTTPException) as exc_info:
            handler.decode_refresh_token(access_token)

        assert exc_info.value.status_code == 401
        assert "Invalid token type" in exc_info.value.detail

    # ===== Configuration Tests =====

    def test_handler_initialization_with_defaults(self):
        """Test JWT handler initialization uses settings defaults."""
        with patch("sark.services.auth.jwt.settings") as mock_settings:
            mock_settings.secret_key = "default_secret"

            handler = JWTHandler()

            assert handler.secret_key == "default_secret"
            assert handler.algorithm == "HS256"
            assert handler.access_token_expire_minutes == 30
            assert handler.refresh_token_expire_days == 7

    def test_handler_initialization_with_custom_values(self):
        """Test JWT handler initialization with custom values."""
        handler = JWTHandler(
            secret_key="custom_secret",
            algorithm="HS512",
            access_token_expire_minutes=60,
            refresh_token_expire_days=14,
        )

        assert handler.secret_key == "custom_secret"
        assert handler.algorithm == "HS512"
        assert handler.access_token_expire_minutes == 60
        assert handler.refresh_token_expire_days == 14

    # ===== Edge Cases =====

    def test_token_with_uuid_user_id(self, handler):
        """Test token creation and decoding with UUID user_id."""
        user_id = uuid4()
        token = handler.create_access_token(
            user_id=user_id,
            email="uuid@test.com",
            role="admin",
        )

        payload = handler.decode_token(token)
        assert payload["sub"] == str(user_id)
        # Verify UUID can be reconstructed
        assert UUID(payload["sub"]) == user_id

    def test_token_with_empty_teams_list(self, handler, sample_user_data):
        """Test token with explicitly empty teams list."""
        token = handler.create_access_token(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role=sample_user_data["role"],
            teams=[],
        )

        payload = handler.decode_token(token)
        assert payload["teams"] == []

    def test_token_with_special_characters_in_email(self, handler, sample_user_data):
        """Test token with special characters in email."""
        special_email = "test+tag@sub.example.com"
        token = handler.create_access_token(
            user_id=sample_user_data["user_id"],
            email=special_email,
            role=sample_user_data["role"],
        )

        payload = handler.decode_token(token)
        assert payload["email"] == special_email

    def test_token_with_many_teams(self, handler, sample_user_data):
        """Test token with many teams."""
        many_teams = [f"team-{i}" for i in range(100)]
        token = handler.create_access_token(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role=sample_user_data["role"],
            teams=many_teams,
        )

        payload = handler.decode_token(token)
        assert payload["teams"] == many_teams
        assert len(payload["teams"]) == 100


class TestGetCurrentUser:
    """Test suite for get_current_user dependency function."""

    @pytest.fixture
    def handler(self):
        """Create a JWT handler for testing."""
        return JWTHandler(secret_key="test_secret_key_12345")

    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing."""
        return {
            "user_id": uuid4(),
            "email": "test@example.com",
            "role": "user",
            "teams": ["team-alpha"],
        }

    def test_get_current_user_valid_token(self, handler, sample_user_data):
        """Test get_current_user with valid token returns UserContext."""
        token = handler.create_access_token(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role=sample_user_data["role"],
            teams=sample_user_data["teams"],
        )

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token,
        )

        # Mock the JWT handler in get_current_user to use our test handler
        with patch("sark.services.auth.jwt.JWTHandler") as mock_handler_class:
            mock_handler_class.return_value = handler
            user_context = get_current_user(credentials)

            assert isinstance(user_context, UserContext)
            assert user_context.user_id == sample_user_data["user_id"]
            assert user_context.email == sample_user_data["email"]
            assert user_context.role == sample_user_data["role"]
            assert user_context.teams == sample_user_data["teams"]
            assert user_context.is_authenticated is True

    def test_get_current_user_invalid_token(self):
        """Test get_current_user with invalid token raises HTTPException."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid.token.here",
        )

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials)

        assert exc_info.value.status_code == 401

    def test_get_current_user_expired_token(self, handler, sample_user_data):
        """Test get_current_user with expired token raises HTTPException."""
        # Create an already expired token
        now = datetime.now(UTC)
        past = now - timedelta(hours=1)

        claims = {
            "sub": str(sample_user_data["user_id"]),
            "email": sample_user_data["email"],
            "role": sample_user_data["role"],
            "teams": [],
            "iat": past,
            "exp": past,
            "type": "access",
        }
        token = jwt.encode(claims, handler.secret_key, algorithm=handler.algorithm)

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token,
        )

        with patch("sark.services.auth.jwt.JWTHandler") as mock_handler_class:
            mock_handler_class.return_value = handler

            with pytest.raises(HTTPException) as exc_info:
                get_current_user(credentials)

            assert exc_info.value.status_code == 401

    def test_get_current_user_missing_required_claims(self, handler):
        """Test get_current_user with missing required claims raises HTTPException."""
        # Create token missing required fields
        claims = {
            "sub": str(uuid4()),
            "type": "access",
            "exp": datetime.now(UTC) + timedelta(minutes=30),
            # Missing 'email' and 'role'
        }
        token = jwt.encode(claims, handler.secret_key, algorithm=handler.algorithm)

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token,
        )

        with patch("sark.services.auth.jwt.JWTHandler") as mock_handler_class:
            mock_handler_class.return_value = handler

            with pytest.raises(HTTPException) as exc_info:
                get_current_user(credentials)

            assert exc_info.value.status_code == 401
            # Could be either error message depending on which check fails first
            assert exc_info.value.detail in ["Invalid token claims", "Could not validate credentials"]

    def test_get_current_user_invalid_uuid(self, handler):
        """Test get_current_user with invalid UUID raises HTTPException."""
        claims = {
            "sub": "not-a-valid-uuid",
            "email": "test@example.com",
            "role": "user",
            "type": "access",
            "exp": datetime.now(UTC) + timedelta(minutes=30),
        }
        token = jwt.encode(claims, handler.secret_key, algorithm=handler.algorithm)

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token,
        )

        with patch("sark.services.auth.jwt.JWTHandler") as mock_handler_class:
            mock_handler_class.return_value = handler

            with pytest.raises(HTTPException) as exc_info:
                get_current_user(credentials)

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail in ["Invalid token claims", "Could not validate credentials"]

    def test_get_current_user_refresh_token_fails(self, handler, sample_user_data):
        """Test get_current_user with refresh token raises HTTPException."""
        # Create a refresh token instead of access token
        token = handler.create_refresh_token(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
        )

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token,
        )

        with patch("sark.services.auth.jwt.JWTHandler") as mock_handler_class:
            mock_handler_class.return_value = handler

            with pytest.raises(HTTPException) as exc_info:
                get_current_user(credentials)

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail in ["Invalid token type", "Could not validate credentials"]

    def test_get_current_user_without_teams(self, handler, sample_user_data):
        """Test get_current_user with token without teams."""
        token = handler.create_access_token(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            role=sample_user_data["role"],
        )

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token,
        )

        with patch("sark.services.auth.jwt.JWTHandler") as mock_handler_class:
            mock_handler_class.return_value = handler
            user_context = get_current_user(credentials)

            assert user_context.teams == []
