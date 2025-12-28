"""
Unit tests for OPA integration with factory routing and metrics.

Tests the integrated evaluate_policy function with Rust/Python routing,
caching, and metrics tracking.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from sark.services.policy.opa import evaluate_policy, _extract_resource_id
from sark.services.policy.opa_client import AuthorizationDecision


class TestEvaluatePolicy:
    """Test suite for evaluate_policy integration."""

    @pytest.mark.asyncio
    @patch("sark.services.policy.opa.create_opa_client")
    @patch("sark.services.policy.opa.create_policy_cache")
    @patch("sark.services.policy.opa.record_feature_flag_assignment")
    @patch("sark.services.policy.opa.record_opa_evaluation")
    @patch("sark.services.policy.opa.record_cache_operation")
    async def test_cache_miss_evaluates_policy(
        self,
        mock_record_cache,
        mock_record_opa,
        mock_record_ff,
        mock_create_cache,
        mock_create_opa,
    ):
        """Test that cache miss triggers OPA evaluation."""
        # Setup mocks
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None  # Cache miss
        mock_create_cache.return_value = mock_cache

        mock_opa = AsyncMock()
        mock_decision = AuthorizationDecision(
            allow=True,
            reason="Policy allows",
            filtered_parameters=None,
        )
        mock_opa.evaluate_policy.return_value = mock_decision
        mock_create_opa.return_value = mock_opa

        # Test input
        input_data = {
            "user": {"id": "user123"},
            "action": "invoke",
            "resource": {"tool": "slack", "server": "mcp-slack"},
            "context": {},
        }

        # Execute
        result = await evaluate_policy(
            policy_path="/v1/data/mcp/gateway/allow",
            input_data=input_data,
        )

        # Verify OPA was called
        assert mock_opa.evaluate_policy.called
        assert result["result"]["allow"] is True
        assert result["result"]["reason"] == "Policy allows"

        # Verify cache was set
        assert mock_cache.set.called

        # Verify metrics recorded
        assert mock_record_opa.called
        assert mock_record_cache.called

    @pytest.mark.asyncio
    @patch("sark.services.policy.opa.create_opa_client")
    @patch("sark.services.policy.opa.create_policy_cache")
    @patch("sark.services.policy.opa.record_cache_operation")
    async def test_cache_hit_skips_opa(
        self,
        mock_record_cache,
        mock_create_cache,
        mock_create_opa,
    ):
        """Test that cache hit skips OPA evaluation."""
        # Setup cached decision
        cached_decision = {
            "allow": True,
            "reason": "Cached decision",
            "filtered_parameters": None,
        }

        mock_cache = AsyncMock()
        mock_cache.get.return_value = cached_decision
        mock_create_cache.return_value = mock_cache

        mock_opa = AsyncMock()
        mock_create_opa.return_value = mock_opa

        # Test input
        input_data = {
            "user": {"id": "user123"},
            "action": "invoke",
            "resource": {"tool": "slack"},
            "context": {},
        }

        # Execute
        result = await evaluate_policy(
            policy_path="/v1/data/mcp/gateway/allow",
            input_data=input_data,
        )

        # Verify OPA was NOT called
        assert not mock_opa.evaluate_policy.called

        # Verify cached result returned
        assert result["result"]["allow"] is True
        assert result["result"]["reason"] == "Cached decision"

        # Verify cache hit recorded
        mock_record_cache.assert_called()
        # record_cache_operation(impl, operation, duration, result)
        call_args = mock_record_cache.call_args[0]
        assert call_args[1] == "get"  # operation
        # Duration is a float, result is at index 3
        assert call_args[3] == "hit"  # result

    @pytest.mark.asyncio
    @patch("sark.services.policy.opa.create_opa_client")
    @patch("sark.services.policy.opa.create_policy_cache")
    @patch("sark.services.policy.opa.record_opa_error")
    async def test_opa_error_records_metric(
        self,
        mock_record_error,
        mock_create_cache,
        mock_create_opa,
    ):
        """Test that OPA errors are recorded in metrics."""
        # Setup mocks
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None
        mock_create_cache.return_value = mock_cache

        mock_opa = AsyncMock()
        mock_opa.evaluate_policy.side_effect = TimeoutError("OPA timeout")
        mock_create_opa.return_value = mock_opa

        # Test input
        input_data = {
            "user": {"id": "user123"},
            "action": "invoke",
            "resource": {"tool": "slack"},
            "context": {},
        }

        # Execute and expect error
        with pytest.raises(TimeoutError):
            await evaluate_policy(
                policy_path="/v1/data/mcp/gateway/allow",
                input_data=input_data,
            )

        # Verify error metric recorded
        mock_record_error.assert_called()
        call_args = mock_record_error.call_args[0]
        assert call_args[1] == "timeout"  # error_type

    @pytest.mark.asyncio
    @patch("sark.services.policy.opa.create_opa_client")
    @patch("sark.services.policy.opa.create_policy_cache")
    async def test_cache_error_continues_to_opa(
        self,
        mock_create_cache,
        mock_create_opa,
    ):
        """Test that cache errors don't prevent OPA evaluation."""
        # Setup cache error
        mock_cache = AsyncMock()
        mock_cache.get.side_effect = RuntimeError("Cache error")
        mock_create_cache.return_value = mock_cache

        # Setup OPA success
        mock_opa = AsyncMock()
        mock_decision = AuthorizationDecision(
            allow=True,
            reason="Policy allows",
        )
        mock_opa.evaluate_policy.return_value = mock_decision
        mock_create_opa.return_value = mock_opa

        # Test input
        input_data = {
            "user": {"id": "user123"},
            "action": "invoke",
            "resource": {"tool": "slack"},
            "context": {},
        }

        # Execute - should succeed despite cache error
        result = await evaluate_policy(
            policy_path="/v1/data/mcp/gateway/allow",
            input_data=input_data,
        )

        # Verify OPA was still called
        assert mock_opa.evaluate_policy.called
        assert result["result"]["allow"] is True

    @pytest.mark.asyncio
    @patch("sark.services.policy.opa.create_opa_client")
    @patch("sark.services.policy.opa.create_policy_cache")
    @patch("sark.services.policy.opa.record_feature_flag_assignment")
    async def test_feature_flag_routing(
        self,
        mock_record_ff,
        mock_create_cache,
        mock_create_opa,
    ):
        """Test that feature flag assignments are recorded."""
        # Setup mocks
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None
        mock_create_cache.return_value = mock_cache

        mock_opa = AsyncMock()
        mock_opa.evaluate_policy.return_value = AuthorizationDecision(
            allow=True, reason="Test"
        )
        mock_create_opa.return_value = mock_opa

        # Test input
        input_data = {
            "user": {"id": "user123"},
            "action": "invoke",
            "resource": {"tool": "slack"},
            "context": {},
        }

        # Execute
        await evaluate_policy(
            policy_path="/v1/data/mcp/gateway/allow",
            input_data=input_data,
        )

        # Verify feature flag assignments recorded
        assert mock_record_ff.call_count == 2  # rust_opa and rust_cache
        calls = [call[0] for call in mock_record_ff.call_args_list]
        features = [call[0] for call in calls]
        assert "rust_opa" in features
        assert "rust_cache" in features

    @pytest.mark.asyncio
    @patch("sark.services.policy.opa.create_opa_client")
    @patch("sark.services.policy.opa.create_policy_cache")
    async def test_user_id_extraction(
        self,
        mock_create_cache,
        mock_create_opa,
    ):
        """Test that user_id is correctly extracted from input_data."""
        # Setup mocks
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None
        mock_create_cache.return_value = mock_cache

        mock_opa = AsyncMock()
        mock_opa.evaluate_policy.return_value = AuthorizationDecision(
            allow=True, reason="Test"
        )
        mock_create_opa.return_value = mock_opa

        # Test input without explicit user_id
        input_data = {
            "user": {"id": "extracted_user"},
            "action": "invoke",
            "resource": {"tool": "slack"},
            "context": {},
        }

        # Execute
        await evaluate_policy(
            policy_path="/v1/data/mcp/gateway/allow",
            input_data=input_data,
        )

        # Verify clients created with extracted user_id
        mock_create_opa.assert_called_once_with("extracted_user")
        mock_create_cache.assert_called_once_with("extracted_user")

    @pytest.mark.asyncio
    @patch("sark.services.policy.opa.create_opa_client")
    @patch("sark.services.policy.opa.create_policy_cache")
    async def test_explicit_user_id(
        self,
        mock_create_cache,
        mock_create_opa,
    ):
        """Test that explicit user_id takes precedence."""
        # Setup mocks
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None
        mock_create_cache.return_value = mock_cache

        mock_opa = AsyncMock()
        mock_opa.evaluate_policy.return_value = AuthorizationDecision(
            allow=True, reason="Test"
        )
        mock_create_opa.return_value = mock_opa

        # Test input
        input_data = {
            "user": {"id": "from_input"},
            "action": "invoke",
            "resource": {"tool": "slack"},
            "context": {},
        }

        # Execute with explicit user_id
        await evaluate_policy(
            policy_path="/v1/data/mcp/gateway/allow",
            input_data=input_data,
            user_id="explicit_user",
        )

        # Verify clients created with explicit user_id
        mock_create_opa.assert_called_once_with("explicit_user")
        mock_create_cache.assert_called_once_with("explicit_user")


class TestExtractResourceId:
    """Test suite for _extract_resource_id helper."""

    def test_extract_tool_resource(self):
        """Test extracting tool resource ID."""
        input_data = {
            "resource": {
                "tool": "slack",
                "server": "mcp-slack",
            }
        }

        resource_id = _extract_resource_id(input_data)
        assert resource_id == "tool:mcp-slack/slack"

    def test_extract_tool_resource_dict(self):
        """Test extracting tool resource ID from dict."""
        input_data = {
            "resource": {
                "tool": {"name": "slack"},
                "server": "mcp-slack",
            }
        }

        resource_id = _extract_resource_id(input_data)
        assert resource_id == "tool:mcp-slack/slack"

    def test_extract_server_resource(self):
        """Test extracting server resource ID."""
        input_data = {
            "resource": {
                "server": "mcp-slack",
            }
        }

        resource_id = _extract_resource_id(input_data)
        assert resource_id == "server:mcp-slack"

    def test_extract_type_resource(self):
        """Test extracting typed resource ID."""
        input_data = {
            "resource": {
                "type": "api",
                "server": "production",
            }
        }

        resource_id = _extract_resource_id(input_data)
        assert resource_id == "api:production"

    def test_extract_unknown_resource(self):
        """Test handling unknown resource format."""
        input_data = {
            "resource": {}
        }

        resource_id = _extract_resource_id(input_data)
        assert resource_id == "unknown"

    def test_extract_missing_resource(self):
        """Test handling missing resource."""
        input_data = {}

        resource_id = _extract_resource_id(input_data)
        assert resource_id == "unknown"


class TestImplementationDetection:
    """Test suite for implementation type detection."""

    @pytest.mark.asyncio
    @patch("sark.services.policy.opa.create_opa_client")
    @patch("sark.services.policy.opa.create_policy_cache")
    @patch("sark.services.policy.opa.record_feature_flag_assignment")
    async def test_rust_implementation_detection(
        self,
        mock_record_ff,
        mock_create_cache,
        mock_create_opa,
    ):
        """Test that Rust implementation is correctly detected."""
        # Setup Rust client mock
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None
        mock_create_cache.return_value = mock_cache

        mock_opa = AsyncMock()
        mock_opa.__class__.__name__ = "RustOPAClient"  # Simulate Rust client
        mock_opa.evaluate_policy.return_value = AuthorizationDecision(
            allow=True, reason="Test"
        )
        mock_create_opa.return_value = mock_opa

        # Test input
        input_data = {
            "user": {"id": "user123"},
            "action": "invoke",
            "resource": {"tool": "slack"},
            "context": {},
        }

        # Execute
        await evaluate_policy(
            policy_path="/v1/data/mcp/gateway/allow",
            input_data=input_data,
        )

        # Verify Rust implementation recorded
        calls = [call[0] for call in mock_record_ff.call_args_list]
        implementations = [call[1] for call in calls]
        assert all(impl == "rust" for impl in implementations)

    @pytest.mark.asyncio
    @patch("sark.services.policy.opa.create_opa_client")
    @patch("sark.services.policy.opa.create_policy_cache")
    @patch("sark.services.policy.opa.record_feature_flag_assignment")
    async def test_python_implementation_detection(
        self,
        mock_record_ff,
        mock_create_cache,
        mock_create_opa,
    ):
        """Test that Python implementation is correctly detected."""
        # Setup Python client mock
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None
        mock_create_cache.return_value = mock_cache

        mock_opa = AsyncMock()
        mock_opa.__class__.__name__ = "OPAClient"  # Simulate Python client
        mock_opa.evaluate_policy.return_value = AuthorizationDecision(
            allow=True, reason="Test"
        )
        mock_create_opa.return_value = mock_opa

        # Test input
        input_data = {
            "user": {"id": "user123"},
            "action": "invoke",
            "resource": {"tool": "slack"},
            "context": {},
        }

        # Execute
        await evaluate_policy(
            policy_path="/v1/data/mcp/gateway/allow",
            input_data=input_data,
        )

        # Verify Python implementation recorded
        calls = [call[0] for call in mock_record_ff.call_args_list]
        implementations = [call[1] for call in calls]
        assert all(impl == "python" for impl in implementations)
