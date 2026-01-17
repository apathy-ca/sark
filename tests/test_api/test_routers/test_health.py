"""Comprehensive tests for health router endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from sark.main import app


# Create a test client
client = TestClient(app)


class TestBasicHealthCheck:
    """Tests for GET / (basic health check) endpoint."""

    def test_health_check_success(self):
        """Test basic health check returns 200."""
        response = client.get("/health/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "environment" in data

    def test_health_check_no_auth_required(self):
        """Test health check does not require authentication."""
        # Health check should work without any auth headers
        response = client.get("/health/")
        assert response.status_code == 200

    def test_health_check_response_structure(self):
        """Test health check response has correct structure."""
        response = client.get("/health/")

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields are present
        assert "status" in data
        assert "version" in data
        assert "environment" in data


class TestLivenessCheck:
    """Tests for GET /live (liveness probe) endpoint."""

    def test_liveness_check_success(self):
        """Test liveness check returns 200."""
        response = client.get("/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "version" in data
        assert "environment" in data

    def test_liveness_check_no_dependencies(self):
        """Test liveness check does not verify dependencies."""
        # Liveness should succeed even if dependencies are down
        response = client.get("/health/live")
        assert response.status_code == 200


class TestReadinessCheck:
    """Tests for GET /ready (readiness probe) endpoint."""

    @patch("sark.api.routers.health.check_database_health")
    @patch("sark.api.routers.health.check_redis_health")
    @patch("sark.api.routers.health.check_opa_health")
    async def test_readiness_check_all_healthy(
        self, mock_opa_health, mock_redis_health, mock_db_health
    ):
        """Test readiness check when all dependencies are healthy."""
        mock_db_health.return_value = True
        mock_redis_health.return_value = True
        mock_opa_health.return_value = True

        response = client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True
        assert data["database"] is True
        assert data["redis"] is True
        assert data["opa"] is True

    @patch("sark.api.routers.health.check_database_health")
    @patch("sark.api.routers.health.check_redis_health")
    @patch("sark.api.routers.health.check_opa_health")
    async def test_readiness_check_database_unhealthy(
        self, mock_opa_health, mock_redis_health, mock_db_health
    ):
        """Test readiness check when database is unhealthy."""
        mock_db_health.return_value = False
        mock_redis_health.return_value = True
        mock_opa_health.return_value = True

        response = client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is False
        assert data["database"] is False
        assert data["redis"] is True
        assert data["opa"] is True

    @patch("sark.api.routers.health.check_database_health")
    @patch("sark.api.routers.health.check_redis_health")
    @patch("sark.api.routers.health.check_opa_health")
    async def test_readiness_check_all_unhealthy(
        self, mock_opa_health, mock_redis_health, mock_db_health
    ):
        """Test readiness check when all dependencies are unhealthy."""
        mock_db_health.return_value = False
        mock_redis_health.return_value = False
        mock_opa_health.return_value = False

        response = client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is False
        assert data["database"] is False
        assert data["redis"] is False
        assert data["opa"] is False

    @patch("sark.api.routers.health.check_database_health")
    @patch("sark.api.routers.health.check_redis_health")
    @patch("sark.api.routers.health.check_opa_health")
    async def test_readiness_check_handles_exceptions(
        self, mock_opa_health, mock_redis_health, mock_db_health
    ):
        """Test readiness check handles exceptions gracefully."""
        mock_db_health.side_effect = Exception("Database connection failed")
        mock_redis_health.return_value = True
        mock_opa_health.return_value = True

        response = client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        # Should handle exception and mark as unhealthy
        assert data["database"] is False
        assert data["ready"] is False


class TestStartupCheck:
    """Tests for GET /startup (startup probe) endpoint."""

    def test_startup_check_success(self):
        """Test startup check returns 200."""
        response = client.get("/health/startup")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert "version" in data
        assert "environment" in data

    def test_startup_check_no_auth_required(self):
        """Test startup check does not require authentication."""
        response = client.get("/health/startup")
        assert response.status_code == 200


class TestDetailedHealthCheck:
    """Tests for GET /detailed (detailed health check) endpoint."""

    @patch("sark.api.routers.health.check_database_health")
    @patch("sark.api.routers.health.check_redis_health")
    @patch("sark.api.routers.health.check_opa_health")
    async def test_detailed_health_all_healthy(
        self, mock_opa_health, mock_redis_health, mock_db_health
    ):
        """Test detailed health check when all dependencies are healthy."""
        mock_db_health.return_value = True
        mock_redis_health.return_value = True
        mock_opa_health.return_value = True

        response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["overall_healthy"] is True
        assert "dependencies" in data
        assert "postgresql" in data["dependencies"]
        assert "redis" in data["dependencies"]
        assert "opa" in data["dependencies"]

        # Verify each dependency has correct structure
        for dep_name, dep_status in data["dependencies"].items():
            assert "healthy" in dep_status
            assert "latency_ms" in dep_status
            assert dep_status["healthy"] is True
            assert dep_status["latency_ms"] is not None

    @patch("sark.api.routers.health.check_database_health")
    @patch("sark.api.routers.health.check_redis_health")
    @patch("sark.api.routers.health.check_opa_health")
    async def test_detailed_health_some_unhealthy(
        self, mock_opa_health, mock_redis_health, mock_db_health
    ):
        """Test detailed health check when some dependencies are unhealthy."""
        mock_db_health.return_value = True
        mock_redis_health.side_effect = Exception("Redis connection failed")
        mock_opa_health.return_value = True

        response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["overall_healthy"] is False

        # Verify Redis dependency shows error
        redis_status = data["dependencies"]["redis"]
        assert redis_status["healthy"] is False
        assert "error" in redis_status
        assert "Redis connection failed" in redis_status["error"]

    @patch("sark.api.routers.health.check_database_health")
    @patch("sark.api.routers.health.check_redis_health")
    @patch("sark.api.routers.health.check_opa_health")
    async def test_detailed_health_includes_latency(
        self, mock_opa_health, mock_redis_health, mock_db_health
    ):
        """Test detailed health check includes latency measurements."""
        mock_db_health.return_value = True
        mock_redis_health.return_value = True
        mock_opa_health.return_value = True

        response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()

        # Each dependency should have latency measurement
        for dep_status in data["dependencies"].values():
            assert "latency_ms" in dep_status
            assert isinstance(dep_status["latency_ms"], (int, float))
            assert dep_status["latency_ms"] >= 0


class TestCheckDatabaseHealth:
    """Tests for check_database_health function."""

    @patch("sark.api.routers.health.create_async_engine")
    async def test_check_database_health_success(self, mock_create_engine):
        """Test database health check succeeds when connection is healthy."""
        from sark.api.routers.health import check_database_health
        from unittest.mock import MagicMock

        # Mock engine and connection
        mock_engine = AsyncMock()
        mock_conn = AsyncMock()

        # Create proper async context manager
        async def mock_connect():
            return mock_conn

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_engine.connect = MagicMock(return_value=mock_context)
        mock_engine.dispose = AsyncMock()
        mock_create_engine.return_value = mock_engine

        result = await check_database_health()

        assert result is True
        mock_engine.dispose.assert_called_once()

    @patch("sark.api.routers.health.create_async_engine")
    async def test_check_database_health_failure(self, mock_create_engine):
        """Test database health check fails when connection fails."""
        from sark.api.routers.health import check_database_health

        mock_create_engine.side_effect = Exception("Connection failed")

        result = await check_database_health()

        assert result is False


class TestCheckRedisHealth:
    """Tests for check_redis_health function."""

    @patch("sark.api.routers.health.aioredis.from_url")
    async def test_check_redis_health_success(self, mock_from_url):
        """Test Redis health check succeeds when connection is healthy."""
        from sark.api.routers.health import check_redis_health

        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.aclose = AsyncMock()
        mock_from_url.return_value = mock_redis

        result = await check_redis_health()

        assert result is True
        mock_redis.ping.assert_called_once()
        mock_redis.aclose.assert_called_once()

    @patch("sark.api.routers.health.aioredis.from_url")
    async def test_check_redis_health_failure(self, mock_from_url):
        """Test Redis health check fails when connection fails."""
        from sark.api.routers.health import check_redis_health

        mock_from_url.side_effect = Exception("Redis connection failed")

        result = await check_redis_health()

        assert result is False


class TestCheckOpaHealth:
    """Tests for check_opa_health function."""

    @patch("sark.api.routers.health.OPAClient")
    async def test_check_opa_health_success(self, mock_opa_client_class):
        """Test OPA health check succeeds when OPA is healthy."""
        from sark.api.routers.health import check_opa_health

        # Mock OPA client
        mock_opa_client = AsyncMock()
        mock_opa_client.health_check = AsyncMock(return_value=True)
        mock_opa_client.close = AsyncMock()
        mock_opa_client_class.return_value = mock_opa_client

        result = await check_opa_health()

        assert result is True
        mock_opa_client.health_check.assert_called_once()
        mock_opa_client.close.assert_called_once()

    @patch("sark.api.routers.health.OPAClient")
    async def test_check_opa_health_failure(self, mock_opa_client_class):
        """Test OPA health check fails when OPA is unhealthy."""
        from sark.api.routers.health import check_opa_health

        mock_opa_client = AsyncMock()
        mock_opa_client.health_check = AsyncMock(return_value=False)
        mock_opa_client.close = AsyncMock()
        mock_opa_client_class.return_value = mock_opa_client

        result = await check_opa_health()

        assert result is False

    @patch("sark.api.routers.health.OPAClient")
    async def test_check_opa_health_exception(self, mock_opa_client_class):
        """Test OPA health check handles exceptions."""
        from sark.api.routers.health import check_opa_health

        mock_opa_client_class.side_effect = Exception("OPA connection failed")

        result = await check_opa_health()

        assert result is False


class TestHealthResponseModels:
    """Tests for health response model validation."""

    def test_health_response_model(self):
        """Test HealthResponse model."""
        from sark.api.routers.health import HealthResponse

        response = HealthResponse(
            status="healthy",
            version="1.0.0",
            environment="test",
        )
        assert response.status == "healthy"
        assert response.version == "1.0.0"
        assert response.environment == "test"

    def test_dependency_status_model_healthy(self):
        """Test DependencyStatus model for healthy dependency."""
        from sark.api.routers.health import DependencyStatus

        status = DependencyStatus(
            healthy=True,
            latency_ms=5.2,
        )
        assert status.healthy is True
        assert status.latency_ms == 5.2
        assert status.error is None

    def test_dependency_status_model_unhealthy(self):
        """Test DependencyStatus model for unhealthy dependency."""
        from sark.api.routers.health import DependencyStatus

        status = DependencyStatus(
            healthy=False,
            latency_ms=100.5,
            error="Connection timeout",
        )
        assert status.healthy is False
        assert status.error == "Connection timeout"

    def test_ready_response_model(self):
        """Test ReadyResponse model."""
        from sark.api.routers.health import ReadyResponse

        response = ReadyResponse(
            ready=True,
            database=True,
            redis=True,
            opa=True,
        )
        assert response.ready is True
        assert response.database is True
        assert response.redis is True
        assert response.opa is True

    def test_detailed_health_response_model(self):
        """Test DetailedHealthResponse model."""
        from sark.api.routers.health import DetailedHealthResponse, DependencyStatus

        response = DetailedHealthResponse(
            status="healthy",
            version="1.0.0",
            environment="test",
            dependencies={
                "postgresql": DependencyStatus(healthy=True, latency_ms=5.0),
                "redis": DependencyStatus(healthy=True, latency_ms=2.0),
            },
            overall_healthy=True,
        )
        assert response.status == "healthy"
        assert response.overall_healthy is True
        assert len(response.dependencies) == 2


class TestHealthEndpointsIntegration:
    """Integration tests for health endpoints."""

    def test_all_health_endpoints_accessible(self):
        """Test that all health endpoints are accessible."""
        endpoints = [
            "/health/",
            "/health/live",
            "/health/ready",
            "/health/startup",
            "/health/detailed",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200, f"Endpoint {endpoint} failed"

    def test_health_endpoints_return_json(self):
        """Test that all health endpoints return JSON."""
        endpoints = [
            "/health/",
            "/health/live",
            "/health/ready",
            "/health/startup",
            "/health/detailed",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.headers["content-type"] == "application/json"
            # Should be valid JSON
            data = response.json()
            assert isinstance(data, dict)
