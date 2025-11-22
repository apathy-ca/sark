"""Comprehensive tests for OPA client."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from sark.services.policy.opa_client import (
    AuthorizationDecision,
    AuthorizationInput,
    OPAClient,
)


class TestAuthorizationInput:
    """Test suite for AuthorizationInput model."""

    def test_authorization_input_creation(self):
        """Test creating authorization input with all fields."""
        user_id = str(uuid4())
        auth_input = AuthorizationInput(
            user={
                "id": user_id,
                "email": "test@example.com",
                "role": "developer",
                "teams": ["team-1", "team-2"],
            },
            action="tool:invoke",
            tool={
                "name": "test_tool",
                "sensitivity_level": "medium",
                "owner": user_id,
                "managers": ["team-1"],
            },
            server={
                "name": "test_server",
                "sensitivity_level": "low",
            },
            context={"timestamp": 1234567890, "environment": "dev"},
        )

        assert auth_input.user["id"] == user_id
        assert auth_input.user["role"] == "developer"
        assert auth_input.action == "tool:invoke"
        assert auth_input.tool["name"] == "test_tool"
        assert auth_input.server["name"] == "test_server"
        assert auth_input.context["timestamp"] == 1234567890

    def test_authorization_input_minimal(self):
        """Test creating authorization input with minimal fields."""
        auth_input = AuthorizationInput(
            user={"id": "user-123", "role": "developer"},
            action="read",
            context={},
        )

        assert auth_input.user["id"] == "user-123"
        assert auth_input.action == "read"
        assert auth_input.tool is None
        assert auth_input.server is None

    def test_authorization_input_serialization(self):
        """Test that authorization input can be serialized."""
        auth_input = AuthorizationInput(
            user={"id": "user-123", "role": "admin"},
            action="server:register",
            context={"ip": "192.168.1.1"},
        )

        serialized = auth_input.model_dump()
        assert serialized["user"]["id"] == "user-123"
        assert serialized["action"] == "server:register"


class TestAuthorizationDecision:
    """Test suite for AuthorizationDecision model."""

    def test_authorization_decision_allow(self):
        """Test creating allow decision."""
        decision = AuthorizationDecision(
            allow=True,
            reason="User has required permissions",
            filtered_parameters={"param1": "value1"},
            audit_id="audit-123",
        )

        assert decision.allow is True
        assert "permissions" in decision.reason
        assert decision.filtered_parameters == {"param1": "value1"}
        assert decision.audit_id == "audit-123"

    def test_authorization_decision_deny(self):
        """Test creating deny decision."""
        decision = AuthorizationDecision(
            allow=False,
            reason="Insufficient permissions",
        )

        assert decision.allow is False
        assert "Insufficient" in decision.reason
        assert decision.filtered_parameters is None
        assert decision.audit_id is None


class TestOPAClient:
    """Test suite for OPAClient class."""

    @pytest.fixture
    def client(self):
        """Create OPA client instance."""
        return OPAClient(opa_url="http://test-opa:8181", timeout=5.0)

    @pytest.fixture
    def sample_auth_input(self):
        """Sample authorization input."""
        return AuthorizationInput(
            user={
                "id": "user-123",
                "email": "test@example.com",
                "role": "developer",
                "teams": ["team-1"],
            },
            action="tool:invoke",
            tool={
                "name": "test_tool",
                "sensitivity_level": "medium",
            },
            context={"timestamp": 0},
        )

    @pytest.fixture
    def mock_opa_allow_response(self):
        """Mock OPA response for allow decision."""
        return {
            "result": {
                "allow": True,
                "audit_reason": "User has required role and team membership",
                "filtered_parameters": {"key": "value"},
                "audit_id": "audit-abc-123",
            }
        }

    @pytest.fixture
    def mock_opa_deny_response(self):
        """Mock OPA response for deny decision."""
        return {
            "result": {
                "allow": False,
                "audit_reason": "User lacks required permissions",
            }
        }

    # ===== Initialization Tests =====

    def test_client_initialization(self):
        """Test OPA client initialization."""
        client = OPAClient(opa_url="http://custom:8181", timeout=10.0)

        assert client.opa_url == "http://custom:8181"
        assert client.timeout == 10.0
        assert client.client is not None

    def test_client_initialization_with_defaults(self):
        """Test OPA client initialization uses settings defaults."""
        with patch("sark.services.policy.opa_client.settings") as mock_settings:
            mock_settings.opa_url = "http://default:8181"
            mock_settings.opa_timeout_seconds = 30
            mock_settings.opa_policy_path = "/v1/data/sark/allow"

            client = OPAClient()

            assert client.opa_url == "http://default:8181"
            assert client.timeout == 30

    # ===== evaluate_policy Tests =====

    @pytest.mark.asyncio
    async def test_evaluate_policy_allow(
        self, client, sample_auth_input, mock_opa_allow_response
    ):
        """Test successful policy evaluation with allow decision."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_opa_allow_response
        mock_response.raise_for_status = MagicMock()

        with patch.object(client.client, "post", new=AsyncMock(return_value=mock_response)):
            decision = await client.evaluate_policy(sample_auth_input)

            assert decision.allow is True
            assert "required role" in decision.reason
            assert decision.filtered_parameters == {"key": "value"}
            assert decision.audit_id == "audit-abc-123"

    @pytest.mark.asyncio
    async def test_evaluate_policy_deny(
        self, client, sample_auth_input, mock_opa_deny_response
    ):
        """Test policy evaluation with deny decision."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_opa_deny_response
        mock_response.raise_for_status = MagicMock()

        with patch.object(client.client, "post", new=AsyncMock(return_value=mock_response)):
            decision = await client.evaluate_policy(sample_auth_input)

            assert decision.allow is False
            assert "lacks required permissions" in decision.reason

    @pytest.mark.asyncio
    async def test_evaluate_policy_http_error(self, client, sample_auth_input):
        """Test policy evaluation fails closed on HTTP error."""
        with patch.object(
            client.client,
            "post",
            new=AsyncMock(side_effect=httpx.HTTPError("Connection failed")),
        ):
            decision = await client.evaluate_policy(sample_auth_input)

            # Should fail closed (deny)
            assert decision.allow is False
            assert "failed" in decision.reason.lower()

    @pytest.mark.asyncio
    async def test_evaluate_policy_unexpected_error(self, client, sample_auth_input):
        """Test policy evaluation fails closed on unexpected error."""
        with patch.object(
            client.client,
            "post",
            new=AsyncMock(side_effect=Exception("Unexpected error")),
        ):
            decision = await client.evaluate_policy(sample_auth_input)

            # Should fail closed (deny)
            assert decision.allow is False
            assert "Internal error" in decision.reason

    @pytest.mark.asyncio
    async def test_evaluate_policy_empty_result(self, client, sample_auth_input):
        """Test policy evaluation with empty result defaults to deny."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}  # No result field
        mock_response.raise_for_status = MagicMock()

        with patch.object(client.client, "post", new=AsyncMock(return_value=mock_response)):
            decision = await client.evaluate_policy(sample_auth_input)

            # Should default to deny when allow not in result
            assert decision.allow is False

    @pytest.mark.asyncio
    async def test_evaluate_policy_calls_correct_endpoint(
        self, client, sample_auth_input, mock_opa_allow_response
    ):
        """Test that evaluate_policy calls the correct OPA endpoint."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_opa_allow_response
        mock_response.raise_for_status = MagicMock()

        mock_post = AsyncMock(return_value=mock_response)

        with patch.object(client.client, "post", new=mock_post):
            await client.evaluate_policy(sample_auth_input)

            # Verify POST was called with correct URL
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert client.policy_path in call_args[0][0]

    # ===== check_tool_access Tests =====

    @pytest.mark.asyncio
    async def test_check_tool_access_allow(self, client, mock_opa_allow_response):
        """Test check_tool_access with allow decision."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_opa_allow_response
        mock_response.raise_for_status = MagicMock()

        with patch.object(client.client, "post", new=AsyncMock(return_value=mock_response)):
            decision = await client.check_tool_access(
                user_id="user-123",
                user_email="test@example.com",
                user_role="developer",
                tool_name="test_tool",
                tool_sensitivity="medium",
                tool_owner_id="owner-456",
                team_ids=["team-1"],
            )

            assert decision.allow is True

    @pytest.mark.asyncio
    async def test_check_tool_access_without_teams(self, client, mock_opa_deny_response):
        """Test check_tool_access without team IDs."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_opa_deny_response
        mock_response.raise_for_status = MagicMock()

        with patch.object(client.client, "post", new=AsyncMock(return_value=mock_response)):
            decision = await client.check_tool_access(
                user_id="user-123",
                user_email="test@example.com",
                user_role="user",
                tool_name="sensitive_tool",
                tool_sensitivity="critical",
            )

            assert decision.allow is False

    @pytest.mark.asyncio
    async def test_check_tool_access_builds_correct_input(self, client):
        """Test that check_tool_access builds correct authorization input."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": {"allow": True, "audit_reason": "OK"}}
        mock_response.raise_for_status = MagicMock()

        mock_post = AsyncMock(return_value=mock_response)

        with patch.object(client.client, "post", new=mock_post):
            await client.check_tool_access(
                user_id="user-123",
                user_email="test@example.com",
                user_role="admin",
                tool_name="admin_tool",
                tool_sensitivity="high",
                tool_owner_id="owner-789",
                team_ids=["team-admin"],
            )

            # Verify the input structure
            call_args = mock_post.call_args
            input_data = call_args[1]["json"]["input"]

            assert input_data["user"]["id"] == "user-123"
            assert input_data["user"]["role"] == "admin"
            assert input_data["action"] == "tool:invoke"
            assert input_data["tool"]["name"] == "admin_tool"
            assert input_data["tool"]["sensitivity_level"] == "high"

    # ===== check_server_registration Tests =====

    @pytest.mark.asyncio
    async def test_check_server_registration_allow(self, client, mock_opa_allow_response):
        """Test check_server_registration with allow decision."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_opa_allow_response
        mock_response.raise_for_status = MagicMock()

        with patch.object(client.client, "post", new=AsyncMock(return_value=mock_response)):
            decision = await client.check_server_registration(
                user_id="user-123",
                user_email="test@example.com",
                user_role="admin",
                server_name="new_server",
                server_sensitivity="low",
            )

            assert decision.allow is True

    @pytest.mark.asyncio
    async def test_check_server_registration_builds_correct_input(self, client):
        """Test that check_server_registration builds correct authorization input."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": {"allow": True, "audit_reason": "OK"}}
        mock_response.raise_for_status = MagicMock()

        mock_post = AsyncMock(return_value=mock_response)

        with patch.object(client.client, "post", new=mock_post):
            await client.check_server_registration(
                user_id="user-456",
                user_email="admin@example.com",
                user_role="admin",
                server_name="production_server",
                server_sensitivity="critical",
            )

            # Verify the input structure
            call_args = mock_post.call_args
            input_data = call_args[1]["json"]["input"]

            assert input_data["user"]["id"] == "user-456"
            assert input_data["action"] == "server:register"
            assert input_data["server"]["name"] == "production_server"
            assert input_data["server"]["sensitivity_level"] == "critical"

    # ===== authorize Tests =====

    @pytest.mark.asyncio
    async def test_authorize_true(self, client, mock_opa_allow_response):
        """Test authorize method returns True for allow decision."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_opa_allow_response
        mock_response.raise_for_status = MagicMock()

        with patch.object(client.client, "post", new=AsyncMock(return_value=mock_response)):
            result = await client.authorize(
                user_id="user-123",
                action="read",
                resource="document",
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_authorize_false(self, client, mock_opa_deny_response):
        """Test authorize method returns False for deny decision."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_opa_deny_response
        mock_response.raise_for_status = MagicMock()

        with patch.object(client.client, "post", new=AsyncMock(return_value=mock_response)):
            result = await client.authorize(
                user_id="user-123",
                action="delete",
                resource="critical_data",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_authorize_with_context(self, client, mock_opa_allow_response):
        """Test authorize method with additional context."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_opa_allow_response
        mock_response.raise_for_status = MagicMock()

        mock_post = AsyncMock(return_value=mock_response)

        with patch.object(client.client, "post", new=mock_post):
            await client.authorize(
                user_id="user-123",
                action="write",
                resource="file",
                context={"user": {"email": "test@example.com", "department": "engineering"}},
            )

            # Verify context was included
            call_args = mock_post.call_args
            input_data = call_args[1]["json"]["input"]

            assert input_data["user"]["email"] == "test@example.com"
            assert input_data["user"]["department"] == "engineering"

    # ===== health_check Tests =====

    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test health check succeeds when OPA is healthy."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(client.client, "get", new=AsyncMock(return_value=mock_response)):
            result = await client.health_check()

            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure_non_200(self, client):
        """Test health check fails when OPA returns non-200."""
        mock_response = MagicMock()
        mock_response.status_code = 503

        with patch.object(client.client, "get", new=AsyncMock(return_value=mock_response)):
            result = await client.health_check()

            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_failure_exception(self, client):
        """Test health check fails when exception occurs."""
        with patch.object(
            client.client,
            "get",
            new=AsyncMock(side_effect=httpx.ConnectError("Connection refused")),
        ):
            result = await client.health_check()

            assert result is False

    # ===== close Tests =====

    @pytest.mark.asyncio
    async def test_close(self, client):
        """Test closing the HTTP client."""
        mock_aclose = AsyncMock()
        client.client.aclose = mock_aclose

        await client.close()

        mock_aclose.assert_called_once()
