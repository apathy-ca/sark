"""
Admin API endpoints for rollout control.

Provides administrative endpoints for controlling Rust/Python rollout percentages,
monitoring metrics, and performing emergency rollbacks.
"""

from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
import structlog

from sark.services.feature_flags import get_feature_flag_manager
from sark.api.dependencies import require_role
from sark.api.metrics.rollout_metrics import record_rollout_percentage

logger = structlog.get_logger()

router = APIRouter(prefix="/admin", tags=["admin"])


# Request/Response models
class RolloutStatusResponse(BaseModel):
    """Response model for rollout status."""

    rust_opa: int = Field(..., description="OPA rollout percentage (0-100)")
    rust_cache: int = Field(..., description="Cache rollout percentage (0-100)")


class SetRolloutRequest(BaseModel):
    """Request model for setting rollout percentage."""

    feature: str = Field(..., description="Feature name (rust_opa or rust_cache)")
    percentage: int = Field(..., ge=0, le=100, description="Rollout percentage (0-100)")


class SetRolloutResponse(BaseModel):
    """Response model for setting rollout."""

    feature: str
    percentage: int
    message: str


class RollbackResponse(BaseModel):
    """Response model for rollback."""

    feature: str
    previous_percentage: int
    new_percentage: int = 0
    rolled_back: bool = True
    message: str


class MetricsComparisonResponse(BaseModel):
    """Response model for metrics comparison."""

    rust_opa: Dict[str, Any]
    python_opa: Dict[str, Any]
    rust_cache: Dict[str, Any]
    python_cache: Dict[str, Any]
    recommendation: str


# Endpoints
@router.get("/rollout/status", response_model=RolloutStatusResponse)
async def get_rollout_status(
    _admin: Any = Depends(require_role("admin")),
) -> RolloutStatusResponse:
    """
    Get current rollout percentages for all features.

    Requires admin role.

    Returns:
        Current rollout percentages for rust_opa and rust_cache
    """
    try:
        feature_flags = get_feature_flag_manager()
        rollouts = feature_flags.get_all_rollouts()

        logger.info(
            "rollout_status_requested",
            rust_opa=rollouts.get("rust_opa", 0),
            rust_cache=rollouts.get("rust_cache", 0),
        )

        return RolloutStatusResponse(
            rust_opa=rollouts.get("rust_opa", 0),
            rust_cache=rollouts.get("rust_cache", 0),
        )

    except Exception as e:
        logger.error("Failed to get rollout status", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get rollout status: {e}")


@router.post("/rollout/set", response_model=SetRolloutResponse)
async def set_rollout(
    request: SetRolloutRequest,
    _admin: Any = Depends(require_role("admin")),
) -> SetRolloutResponse:
    """
    Set rollout percentage for a feature.

    Requires admin role.

    Args:
        request: Feature name and rollout percentage

    Returns:
        Confirmation of rollout percentage set

    Raises:
        HTTPException: If feature is invalid or percentage out of range
    """
    # Validate feature name
    valid_features = ["rust_opa", "rust_cache"]
    if request.feature not in valid_features:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid feature '{request.feature}'. Valid features: {valid_features}",
        )

    try:
        feature_flags = get_feature_flag_manager()

        # Get current percentage for logging
        current_pct = feature_flags.get_rollout_pct(request.feature)

        # Set new percentage
        feature_flags.set_rollout_pct(request.feature, request.percentage)

        # Record metric
        record_rollout_percentage(request.feature, request.percentage)

        logger.info(
            "rollout_percentage_changed",
            feature=request.feature,
            previous_percentage=current_pct,
            new_percentage=request.percentage,
        )

        return SetRolloutResponse(
            feature=request.feature,
            percentage=request.percentage,
            message=f"Rollout for {request.feature} set to {request.percentage}%",
        )

    except ValueError as e:
        logger.error("Invalid rollout percentage", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to set rollout", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to set rollout: {e}")


@router.post("/rollout/rollback", response_model=RollbackResponse)
async def rollback_feature(
    feature: str,
    _admin: Any = Depends(require_role("admin")),
) -> RollbackResponse:
    """
    Emergency rollback: set feature to 0% immediately.

    Requires admin role.

    This endpoint sets the rollout percentage to 0% instantly,
    routing all traffic back to the Python implementation.
    Propagation should be <1 second.

    Args:
        feature: Feature name to rollback

    Returns:
        Confirmation of rollback

    Raises:
        HTTPException: If feature is invalid
    """
    # Validate feature name
    valid_features = ["rust_opa", "rust_cache"]
    if feature not in valid_features:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid feature '{feature}'. Valid features: {valid_features}",
        )

    try:
        feature_flags = get_feature_flag_manager()

        # Get current percentage
        current_pct = feature_flags.get_rollout_pct(feature)

        # Rollback to 0%
        feature_flags.rollback(feature)

        # Record metric
        record_rollout_percentage(feature, 0)

        logger.warning(
            "ROLLBACK_EXECUTED",
            feature=feature,
            previous_percentage=current_pct,
            new_percentage=0,
        )

        return RollbackResponse(
            feature=feature,
            previous_percentage=current_pct,
            new_percentage=0,
            rolled_back=True,
            message=f"Emergency rollback completed for {feature}. "
            f"Traffic shifted from {current_pct}% to 0% Rust.",
        )

    except Exception as e:
        logger.error("Failed to rollback feature", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to rollback: {e}")


@router.get("/metrics/comparison", response_model=MetricsComparisonResponse)
async def get_metrics_comparison(
    _admin: Any = Depends(require_role("admin")),
) -> MetricsComparisonResponse:
    """
    Get performance comparison between Rust and Python implementations.

    Requires admin role.

    This endpoint queries Prometheus metrics to provide a comparison
    of performance between Rust and Python implementations.

    Returns:
        Performance metrics comparison and recommendation
    """
    try:
        # In a real implementation, this would query Prometheus
        # For now, return a placeholder structure
        logger.info("metrics_comparison_requested")

        # Placeholder response - in real implementation would query Prometheus
        # and calculate actual percentile latencies, error rates, etc.
        response = MetricsComparisonResponse(
            rust_opa={
                "avg_latency_ms": 0.0,  # Would calculate from metrics
                "p50_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "p99_latency_ms": 0.0,
                "error_rate": 0.0,
                "throughput_rps": 0.0,
            },
            python_opa={
                "avg_latency_ms": 0.0,
                "p50_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "p99_latency_ms": 0.0,
                "error_rate": 0.0,
                "throughput_rps": 0.0,
            },
            rust_cache={
                "avg_latency_ms": 0.0,
                "p50_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "hit_rate": 0.0,
                "error_rate": 0.0,
            },
            python_cache={
                "avg_latency_ms": 0.0,
                "p50_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "hit_rate": 0.0,
                "error_rate": 0.0,
            },
            recommendation="Metrics collection in progress. "
            "Deploy to production and enable rollout to gather comparison data.",
        )

        return response

    except Exception as e:
        logger.error("Failed to get metrics comparison", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get metrics comparison: {e}"
        )


@router.post("/rollout/rollback-all")
async def rollback_all_features(
    _admin: Any = Depends(require_role("admin")),
) -> Dict[str, Any]:
    """
    Emergency rollback ALL features to 0% immediately.

    Requires admin role.

    Use this endpoint in case of critical issues affecting multiple features.
    Sets all rollout percentages to 0% instantly.

    Returns:
        Confirmation of all rollbacks
    """
    try:
        feature_flags = get_feature_flag_manager()

        # Get current percentages
        current_rollouts = feature_flags.get_all_rollouts()

        # Rollback all
        feature_flags.rollback_all()

        # Record metrics
        for feature in current_rollouts.keys():
            record_rollout_percentage(feature, 0)

        logger.critical(
            "ALL_FEATURES_ROLLED_BACK",
            previous_rollouts=current_rollouts,
        )

        return {
            "rolled_back": True,
            "previous_rollouts": current_rollouts,
            "new_rollouts": {k: 0 for k in current_rollouts.keys()},
            "message": "Emergency rollback completed for ALL features. "
            "All traffic shifted to Python implementations.",
        }

    except Exception as e:
        logger.error("Failed to rollback all features", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to rollback all features: {e}"
        )
