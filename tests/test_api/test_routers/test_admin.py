"""Comprehensive tests for admin router endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

# Import the router and models
from sark.api.routers.admin import (
    MetricsComparisonResponse,
    RollbackResponse,
    RolloutStatusResponse,
    SetRolloutRequest,
    SetRolloutResponse,
    router,
)
from sark.main import app


# Create a test client
client = TestClient(app)


class TestRolloutStatusEndpoint:
    """Tests for GET /admin/rollout/status endpoint."""

    @patch("sark.api.routers.admin.get_feature_flag_manager")
    @patch("sark.api.dependencies.require_role")
    def test_get_rollout_status_success(self, mock_require_role, mock_feature_flags):
        """Test successful retrieval of rollout status."""
        # Mock the admin role dependency
        mock_require_role.return_value = lambda: None

        # Mock feature flag manager
        mock_manager = MagicMock()
        mock_manager.get_all_rollouts.return_value = {
            "rust_opa": 50,
            "rust_cache": 75,
        }
        mock_feature_flags.return_value = mock_manager

        # Make request
        response = client.get("/admin/rollout/status")

        assert response.status_code == 200
        data = response.json()
        assert data["rust_opa"] == 50
        assert data["rust_cache"] == 75

    @patch("sark.api.routers.admin.get_feature_flag_manager")
    @patch("sark.api.dependencies.require_role")
    def test_get_rollout_status_default_values(self, mock_require_role, mock_feature_flags):
        """Test rollout status returns 0 for missing features."""
        mock_require_role.return_value = lambda: None

        # Mock feature flag manager returning empty dict
        mock_manager = MagicMock()
        mock_manager.get_all_rollouts.return_value = {}
        mock_feature_flags.return_value = mock_manager

        response = client.get("/admin/rollout/status")

        assert response.status_code == 200
        data = response.json()
        assert data["rust_opa"] == 0
        assert data["rust_cache"] == 0

    @patch("sark.api.routers.admin.get_feature_flag_manager")
    @patch("sark.api.dependencies.require_role")
    def test_get_rollout_status_error_handling(self, mock_require_role, mock_feature_flags):
        """Test error handling when feature flag manager fails."""
        mock_require_role.return_value = lambda: None

        # Mock feature flag manager to raise exception
        mock_feature_flags.side_effect = Exception("Database connection failed")

        response = client.get("/admin/rollout/status")

        assert response.status_code == 500
        assert "Failed to get rollout status" in response.json()["detail"]


class TestSetRolloutEndpoint:
    """Tests for POST /admin/rollout/set endpoint."""

    @patch("sark.api.routers.admin.get_feature_flag_manager")
    @patch("sark.api.routers.admin.record_rollout_percentage")
    @patch("sark.api.dependencies.require_role")
    def test_set_rollout_success(self, mock_require_role, mock_record, mock_feature_flags):
        """Test successfully setting rollout percentage."""
        mock_require_role.return_value = lambda: None

        mock_manager = MagicMock()
        mock_manager.get_rollout_pct.return_value = 25
        mock_feature_flags.return_value = mock_manager

        response = client.post(
            "/admin/rollout/set",
            json={"feature": "rust_opa", "percentage": 50},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["feature"] == "rust_opa"
        assert data["percentage"] == 50
        assert "Rollout for rust_opa set to 50%" in data["message"]

        # Verify manager was called
        mock_manager.set_rollout_pct.assert_called_once_with("rust_opa", 50)
        mock_record.assert_called_once_with("rust_opa", 50)

    @patch("sark.api.dependencies.require_role")
    def test_set_rollout_invalid_feature(self, mock_require_role):
        """Test setting rollout for invalid feature name."""
        mock_require_role.return_value = lambda: None

        response = client.post(
            "/admin/rollout/set",
            json={"feature": "invalid_feature", "percentage": 50},
        )

        assert response.status_code == 400
        assert "Invalid feature" in response.json()["detail"]

    @patch("sark.api.dependencies.require_role")
    def test_set_rollout_invalid_percentage_too_high(self, mock_require_role):
        """Test setting rollout percentage above 100."""
        mock_require_role.return_value = lambda: None

        response = client.post(
            "/admin/rollout/set",
            json={"feature": "rust_opa", "percentage": 150},
        )

        assert response.status_code == 422  # Validation error

    @patch("sark.api.dependencies.require_role")
    def test_set_rollout_invalid_percentage_negative(self, mock_require_role):
        """Test setting negative rollout percentage."""
        mock_require_role.return_value = lambda: None

        response = client.post(
            "/admin/rollout/set",
            json={"feature": "rust_opa", "percentage": -10},
        )

        assert response.status_code == 422  # Validation error

    @patch("sark.api.routers.admin.get_feature_flag_manager")
    @patch("sark.api.dependencies.require_role")
    def test_set_rollout_value_error(self, mock_require_role, mock_feature_flags):
        """Test handling of ValueError from feature flag manager."""
        mock_require_role.return_value = lambda: None

        mock_manager = MagicMock()
        mock_manager.get_rollout_pct.return_value = 0
        mock_manager.set_rollout_pct.side_effect = ValueError("Invalid percentage value")
        mock_feature_flags.return_value = mock_manager

        response = client.post(
            "/admin/rollout/set",
            json={"feature": "rust_opa", "percentage": 50},
        )

        assert response.status_code == 400
        assert "Invalid percentage value" in response.json()["detail"]


class TestRollbackFeatureEndpoint:
    """Tests for POST /admin/rollout/rollback endpoint."""

    @patch("sark.api.routers.admin.get_feature_flag_manager")
    @patch("sark.api.routers.admin.record_rollout_percentage")
    @patch("sark.api.dependencies.require_role")
    def test_rollback_feature_success(self, mock_require_role, mock_record, mock_feature_flags):
        """Test successful feature rollback."""
        mock_require_role.return_value = lambda: None

        mock_manager = MagicMock()
        mock_manager.get_rollout_pct.return_value = 75
        mock_feature_flags.return_value = mock_manager

        response = client.post("/admin/rollout/rollback?feature=rust_opa")

        assert response.status_code == 200
        data = response.json()
        assert data["feature"] == "rust_opa"
        assert data["previous_percentage"] == 75
        assert data["new_percentage"] == 0
        assert data["rolled_back"] is True
        assert "Emergency rollback completed" in data["message"]

        # Verify rollback was called
        mock_manager.rollback.assert_called_once_with("rust_opa")
        mock_record.assert_called_once_with("rust_opa", 0)

    @patch("sark.api.dependencies.require_role")
    def test_rollback_invalid_feature(self, mock_require_role):
        """Test rollback with invalid feature name."""
        mock_require_role.return_value = lambda: None

        response = client.post("/admin/rollout/rollback?feature=invalid_feature")

        assert response.status_code == 400
        assert "Invalid feature" in response.json()["detail"]

    @patch("sark.api.routers.admin.get_feature_flag_manager")
    @patch("sark.api.dependencies.require_role")
    def test_rollback_from_zero(self, mock_require_role, mock_feature_flags):
        """Test rolling back a feature that's already at 0%."""
        mock_require_role.return_value = lambda: None

        mock_manager = MagicMock()
        mock_manager.get_rollout_pct.return_value = 0
        mock_feature_flags.return_value = mock_manager

        response = client.post("/admin/rollout/rollback?feature=rust_cache")

        assert response.status_code == 200
        data = response.json()
        assert data["previous_percentage"] == 0
        assert data["new_percentage"] == 0


class TestMetricsComparisonEndpoint:
    """Tests for GET /admin/metrics/comparison endpoint."""

    @patch("sark.api.dependencies.require_role")
    def test_get_metrics_comparison_success(self, mock_require_role):
        """Test successful metrics comparison retrieval."""
        mock_require_role.return_value = lambda: None

        response = client.get("/admin/metrics/comparison")

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "rust_opa" in data
        assert "python_opa" in data
        assert "rust_cache" in data
        assert "python_cache" in data
        assert "recommendation" in data

        # Verify metric fields
        assert "avg_latency_ms" in data["rust_opa"]
        assert "p50_latency_ms" in data["rust_opa"]
        assert "p95_latency_ms" in data["rust_opa"]
        assert "p99_latency_ms" in data["rust_opa"]
        assert "error_rate" in data["rust_opa"]

    @patch("sark.api.dependencies.require_role")
    def test_metrics_comparison_returns_placeholder_data(self, mock_require_role):
        """Test that metrics comparison returns placeholder data for now."""
        mock_require_role.return_value = lambda: None

        response = client.get("/admin/metrics/comparison")

        assert response.status_code == 200
        data = response.json()

        # Placeholder implementation returns 0.0 for all metrics
        assert data["rust_opa"]["avg_latency_ms"] == 0.0
        assert data["python_opa"]["avg_latency_ms"] == 0.0


class TestRollbackAllFeaturesEndpoint:
    """Tests for POST /admin/rollout/rollback-all endpoint."""

    @patch("sark.api.routers.admin.get_feature_flag_manager")
    @patch("sark.api.routers.admin.record_rollout_percentage")
    @patch("sark.api.dependencies.require_role")
    def test_rollback_all_features_success(
        self, mock_require_role, mock_record, mock_feature_flags
    ):
        """Test successfully rolling back all features."""
        mock_require_role.return_value = lambda: None

        mock_manager = MagicMock()
        mock_manager.get_all_rollouts.return_value = {
            "rust_opa": 50,
            "rust_cache": 75,
        }
        mock_feature_flags.return_value = mock_manager

        response = client.post("/admin/rollout/rollback-all")

        assert response.status_code == 200
        data = response.json()
        assert data["rolled_back"] is True
        assert data["previous_rollouts"]["rust_opa"] == 50
        assert data["previous_rollouts"]["rust_cache"] == 75
        assert data["new_rollouts"]["rust_opa"] == 0
        assert data["new_rollouts"]["rust_cache"] == 0
        assert "Emergency rollback completed for ALL features" in data["message"]

        # Verify rollback_all was called
        mock_manager.rollback_all.assert_called_once()

        # Verify metrics were recorded for all features
        assert mock_record.call_count == 2

    @patch("sark.api.routers.admin.get_feature_flag_manager")
    @patch("sark.api.dependencies.require_role")
    def test_rollback_all_features_error_handling(self, mock_require_role, mock_feature_flags):
        """Test error handling when rollback_all fails."""
        mock_require_role.return_value = lambda: None

        mock_manager = MagicMock()
        mock_manager.get_all_rollouts.return_value = {"rust_opa": 50}
        mock_manager.rollback_all.side_effect = Exception("Rollback failed")
        mock_feature_flags.return_value = mock_manager

        response = client.post("/admin/rollout/rollback-all")

        assert response.status_code == 500
        assert "Failed to rollback all features" in response.json()["detail"]


class TestAdminAuthorizationRequirements:
    """Tests for authorization requirements on admin endpoints."""

    def test_admin_endpoints_require_authentication(self):
        """Test that admin endpoints require authentication."""
        # This test would require setting up proper authentication
        # For now, we verify the dependency is declared
        from sark.api.routers.admin import router

        # Check that endpoints use require_role dependency
        for route in router.routes:
            if hasattr(route, "dependencies"):
                # Admin endpoints should have dependencies
                assert len(route.dependencies) > 0 or len(route.dependant.dependencies) > 0


class TestRequestResponseModels:
    """Tests for request/response model validation."""

    def test_rollout_status_response_model(self):
        """Test RolloutStatusResponse model."""
        response = RolloutStatusResponse(rust_opa=50, rust_cache=75)
        assert response.rust_opa == 50
        assert response.rust_cache == 75

    def test_set_rollout_request_model_valid(self):
        """Test SetRolloutRequest model with valid data."""
        request = SetRolloutRequest(feature="rust_opa", percentage=50)
        assert request.feature == "rust_opa"
        assert request.percentage == 50

    def test_set_rollout_request_model_validation(self):
        """Test SetRolloutRequest model validation."""
        # Test percentage bounds
        with pytest.raises(Exception):  # Should raise validation error
            SetRolloutRequest(feature="rust_opa", percentage=150)

        with pytest.raises(Exception):  # Should raise validation error
            SetRolloutRequest(feature="rust_opa", percentage=-10)

    def test_set_rollout_response_model(self):
        """Test SetRolloutResponse model."""
        response = SetRolloutResponse(
            feature="rust_opa",
            percentage=50,
            message="Rollout set successfully",
        )
        assert response.feature == "rust_opa"
        assert response.percentage == 50
        assert response.message == "Rollout set successfully"

    def test_rollback_response_model(self):
        """Test RollbackResponse model."""
        response = RollbackResponse(
            feature="rust_opa",
            previous_percentage=75,
            new_percentage=0,
            rolled_back=True,
            message="Rollback complete",
        )
        assert response.feature == "rust_opa"
        assert response.previous_percentage == 75
        assert response.new_percentage == 0
        assert response.rolled_back is True

    def test_metrics_comparison_response_model(self):
        """Test MetricsComparisonResponse model."""
        response = MetricsComparisonResponse(
            rust_opa={"avg_latency_ms": 1.5},
            python_opa={"avg_latency_ms": 3.0},
            rust_cache={"avg_latency_ms": 0.5},
            python_cache={"avg_latency_ms": 1.0},
            recommendation="Increase Rust rollout",
        )
        assert response.rust_opa["avg_latency_ms"] == 1.5
        assert response.recommendation == "Increase Rust rollout"
