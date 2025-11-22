"""
Integration tests for authentication and authorization flows.

Tests complete authentication workflows including:
- Login/logout flows
- Token generation and validation
- Token refresh mechanisms
- Authentication failures (invalid credentials, expired tokens)
- Authorization enforcement via OPA
- Role-based access control
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from fastapi import HTTPException, status
from jose import jwt

from sark.services.auth.jwt import JWTHandler, get_current_user
from sark.services.auth.api_key import APIKeyService
from sark.services.auth.session import SessionService
from sark.services.policy.opa_client import OPAClient, AuthorizationDecision
from sark.models.user import User


@pytest.fixture
def jwt_handler():
    """JWT handler for tests."""
    return JWTHandler(
        secret_key="test-secret-key-for-integration-tests",
        algorithm="HS256",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7
    )


@pytest.fixture
def api_key_service():
    """API key service for tests."""
    return APIKeyService(key_length=32)


@pytest.fixture
def session_service():
    """Session service for tests."""
    return SessionService(session_lifetime_hours=24)


@pytest.fixture
def test_user():
    """Test user fixture."""
    return User(
        id=uuid4(),
        email="test@example.com",
        full_name="Test User",
        hashed_password="hashed_password_here",
        role="developer",
        is_active=True,
        is_admin=False,
        extra_metadata={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )


@pytest.fixture
def admin_user():
    """Admin user fixture."""
    return User(
        id=uuid4(),
        email="admin@example.com",
        full_name="Admin User",
        hashed_password="hashed_password_here",
        role="admin",
        is_active=True,
        is_admin=True,
        extra_metadata={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )


@pytest.fixture
async def opa_client():
    """OPA client for policy tests."""
    client = OPAClient(base_url="http://localhost:8181")
    return client


# ============================================================================
# Login/Logout Flow Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.auth
async def test_complete_login_flow(jwt_handler, test_user):
    """Test complete login flow with token generation."""
    # Generate access and refresh tokens
    access_token = jwt_handler.create_access_token(user_id=test_user.id)
    refresh_token = jwt_handler.create_refresh_token(user_id=test_user.id)

    assert access_token is not None
    assert refresh_token is not None

    # Verify access token
    user_id = jwt_handler.verify_token(access_token, "access")
    assert user_id == test_user.id

    # Verify refresh token
    user_id = jwt_handler.verify_token(refresh_token, "refresh")
    assert user_id == test_user.id


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.auth
async def test_token_refresh_flow(jwt_handler, test_user):
    """Test token refresh mechanism."""
    # Create initial tokens
    old_access_token = jwt_handler.create_access_token(user_id=test_user.id)
    refresh_token = jwt_handler.create_refresh_token(user_id=test_user.id)

    # Verify refresh token
    user_id = jwt_handler.verify_token(refresh_token, "refresh")
    assert user_id == test_user.id

    # Generate new access token using refresh token
    new_access_token = jwt_handler.create_access_token(user_id=user_id)

    # Verify new access token works
    verified_user_id = jwt_handler.verify_token(new_access_token, "access")
    assert verified_user_id == test_user.id

    # Both tokens should be different
    assert old_access_token != new_access_token


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.auth
async def test_logout_invalidates_session(session_service, test_user):
    """Test that logout properly invalidates session."""
    # Create session
    session = session_service.create_session(
        user_id=test_user.id,
        user_agent="Mozilla/5.0",
        ip_address="127.0.0.1"
    )

    assert session.is_active is True

    # Invalidate session (logout)
    invalidated = session_service.invalidate_session(session.session_id)
    assert invalidated.is_active is False
    assert invalidated.expires_at < datetime.now(UTC)


# ============================================================================
# Authentication Failure Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.auth
async def test_invalid_credentials_rejected(jwt_handler):
    """Test that invalid tokens are rejected."""
    invalid_token = "invalid.token.here"

    with pytest.raises(HTTPException) as exc_info:
        jwt_handler.verify_token(invalid_token, "access")

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.auth
async def test_expired_token_rejected(jwt_handler, test_user):
    """Test that expired tokens are rejected."""
    # Create expired token
    now = datetime.now(UTC)
    past = now - timedelta(hours=1)
    claims = {
        "sub": str(test_user.id),
        "exp": past,
        "type": "access"
    }
    expired_token = jwt.encode(claims, jwt_handler.secret_key, algorithm=jwt_handler.algorithm)

    with pytest.raises(HTTPException) as exc_info:
        jwt_handler.verify_token(expired_token, "access")

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.auth
async def test_wrong_token_type_rejected(jwt_handler, test_user):
    """Test that using refresh token for access fails."""
    refresh_token = jwt_handler.create_refresh_token(user_id=test_user.id)

    # Try to verify refresh token as access token
    with pytest.raises(HTTPException) as exc_info:
        jwt_handler.verify_token(refresh_token, "access")

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.auth
async def test_malformed_token_rejected(jwt_handler):
    """Test that malformed tokens are rejected."""
    malformed_tokens = [
        "",
        "not-a-jwt",
        "header.payload",  # Missing signature
        "header.payload.signature.extra"  # Too many parts
    ]

    for token in malformed_tokens:
        with pytest.raises(HTTPException) as exc_info:
            jwt_handler.verify_token(token, "access")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# Authorization with OPA Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.requires_opa
async def test_opa_authorization_allows_valid_request(opa_client, test_user):
    """Test that OPA allows authorized requests."""
    # Mock OPA to return allow
    mock_response = MagicMock()
    mock_response.json.return_value = {"result": {"allow": True}}

    with patch.object(opa_client.client, "post", new=AsyncMock(return_value=mock_response)):
        decision = await opa_client.evaluate_policy({
            "user": {"id": str(test_user.id), "role": "user"},
            "action": "read",
            "resource": "servers"
        })

    assert decision.allow is True


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.requires_opa
async def test_opa_authorization_denies_invalid_request(opa_client, test_user):
    """Test that OPA denies unauthorized requests."""
    # Mock OPA to return deny
    mock_response = MagicMock()
    mock_response.json.return_value = {"result": {"allow": False, "reason": "Insufficient permissions"}}

    with patch.object(opa_client.client, "post", new=AsyncMock(return_value=mock_response)):
        decision = await opa_client.evaluate_policy({
            "user": {"id": str(test_user.id), "role": "user"},
            "action": "delete",
            "resource": "servers"
        })

    assert decision.allow is False
    assert decision.reason == "Insufficient permissions"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.requires_opa
async def test_opa_fail_closed_on_error(opa_client, test_user):
    """Test that OPA defaults to deny on errors (fail-closed)."""
    # Mock OPA to raise exception
    with patch.object(opa_client.client, "post", new=AsyncMock(side_effect=Exception("OPA unavailable"))):
        decision = await opa_client.evaluate_policy({
            "user": {"id": str(test_user.id), "role": "user"},
            "action": "read",
            "resource": "servers"
        })

    # Should fail closed (deny)
    assert decision.allow is False


# ============================================================================
# Role-Based Access Control Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.auth
async def test_admin_has_elevated_permissions(opa_client, admin_user):
    """Test that admin users have elevated permissions."""
    # Mock OPA to allow admin actions
    mock_response = MagicMock()
    mock_response.json.return_value = {"result": {"allow": True}}

    with patch.object(opa_client.client, "post", new=AsyncMock(return_value=mock_response)):
        decision = await opa_client.evaluate_policy({
            "user": {"id": str(admin_user.id), "role": "admin"},
            "action": "delete",
            "resource": "servers"
        })

    assert decision.allow is True


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.auth
async def test_regular_user_lacks_admin_permissions(opa_client, test_user):
    """Test that regular users lack admin permissions."""
    # Mock OPA to deny user from admin actions
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "result": {
            "allow": False,
            "reason": "Admin role required"
        }
    }

    with patch.object(opa_client.client, "post", new=AsyncMock(return_value=mock_response)):
        decision = await opa_client.evaluate_policy({
            "user": {"id": str(test_user.id), "role": "user"},
            "action": "delete",
            "resource": "all_servers"
        })

    assert decision.allow is False


# ============================================================================
# API Key Authentication Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.auth
async def test_api_key_authentication_flow(api_key_service):
    """Test API key generation and verification."""
    # Generate API key
    api_key = api_key_service.generate_key()
    assert len(api_key) > 0

    # Hash the key
    key_hash = api_key_service.hash_key(api_key)
    assert key_hash != api_key  # Should be hashed

    # Verify the key
    is_valid = api_key_service.verify_key(api_key, key_hash)
    assert is_valid is True

    # Wrong key should fail
    wrong_key = "wrong-api-key"
    is_valid = api_key_service.verify_key(wrong_key, key_hash)
    assert is_valid is False
