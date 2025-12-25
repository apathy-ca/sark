"""Unit tests for injection detection configuration."""

import pytest
import os

from sark.security.config import (
    InjectionDetectionConfig,
    get_injection_config,
    reset_injection_config,
)


class TestInjectionDetectionConfig:
    """Test suite for InjectionDetectionConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = InjectionDetectionConfig()

        assert config.enabled is True
        assert config.block_threshold == 70
        assert config.alert_threshold == 40
        assert config.entropy_threshold == 4.5
        assert config.entropy_min_length == 50
        assert config.severity_weight_high == 30
        assert config.severity_weight_medium == 15
        assert config.severity_weight_low == 5
        assert config.max_parameter_depth == 10

    def test_valid_custom_values(self):
        """Test configuration with valid custom values."""
        config = InjectionDetectionConfig(
            enabled=False,
            block_threshold=80,
            alert_threshold=50,
            entropy_threshold=5.0,
            entropy_min_length=100,
            severity_weight_high=50,
            severity_weight_medium=25,
            severity_weight_low=10,
            max_parameter_depth=5,
        )

        assert config.enabled is False
        assert config.block_threshold == 80
        assert config.alert_threshold == 50
        assert config.entropy_threshold == 5.0
        assert config.entropy_min_length == 100
        assert config.severity_weight_high == 50
        assert config.severity_weight_medium == 25
        assert config.severity_weight_low == 10
        assert config.max_parameter_depth == 5

    def test_threshold_out_of_range_high(self):
        """Test that threshold above 100 is rejected."""
        with pytest.raises(ValueError, match="block_threshold must be between"):
            InjectionDetectionConfig(block_threshold=101)

    def test_threshold_out_of_range_low(self):
        """Test that threshold below 0 is rejected."""
        with pytest.raises(ValueError, match="block_threshold must be between"):
            InjectionDetectionConfig(block_threshold=-1)

    def test_alert_threshold_greater_than_block(self):
        """Test that alert_threshold > block_threshold is rejected."""
        with pytest.raises(ValueError, match="alert_threshold.*cannot be greater than.*block_threshold"):
            InjectionDetectionConfig(
                block_threshold=50,
                alert_threshold=60,
            )

    def test_entropy_threshold_too_high(self):
        """Test that entropy threshold above max is rejected."""
        with pytest.raises(ValueError, match="entropy_threshold must be between"):
            InjectionDetectionConfig(entropy_threshold=10.0)

    def test_entropy_threshold_negative(self):
        """Test that negative entropy threshold is rejected."""
        with pytest.raises(ValueError, match="entropy_threshold must be between"):
            InjectionDetectionConfig(entropy_threshold=-1.0)

    def test_entropy_min_length_too_short(self):
        """Test that entropy min length below minimum is rejected."""
        with pytest.raises(ValueError, match="entropy_min_length must be between"):
            InjectionDetectionConfig(entropy_min_length=5)

    def test_entropy_min_length_too_long(self):
        """Test that entropy min length above maximum is rejected."""
        with pytest.raises(ValueError, match="entropy_min_length must be between"):
            InjectionDetectionConfig(entropy_min_length=20000)

    def test_negative_severity_weight(self):
        """Test that negative severity weights are rejected."""
        with pytest.raises(ValueError, match="severity_weight_high must be non-negative"):
            InjectionDetectionConfig(severity_weight_high=-10)

    def test_severity_weight_ordering(self):
        """Test that severity weights must be ordered (high >= medium >= low)."""
        # High < Medium should fail
        with pytest.raises(ValueError, match="severity_weight_high.*should be"):
            InjectionDetectionConfig(
                severity_weight_high=10,
                severity_weight_medium=20,
                severity_weight_low=5,
            )

        # Medium < Low should fail
        with pytest.raises(ValueError, match="severity_weight_medium.*should be"):
            InjectionDetectionConfig(
                severity_weight_high=30,
                severity_weight_medium=5,
                severity_weight_low=15,
            )

    def test_max_parameter_depth_too_low(self):
        """Test that max_parameter_depth < 1 is rejected."""
        with pytest.raises(ValueError, match="max_parameter_depth must be at least 1"):
            InjectionDetectionConfig(max_parameter_depth=0)

    def test_multiple_validation_errors(self):
        """Test that multiple validation errors are reported together."""
        with pytest.raises(ValueError) as exc_info:
            InjectionDetectionConfig(
                block_threshold=150,  # Too high
                alert_threshold=-10,  # Too low
                entropy_threshold=20.0,  # Too high
            )

        error_msg = str(exc_info.value)
        assert "block_threshold must be between" in error_msg
        assert "alert_threshold must be between" in error_msg
        assert "entropy_threshold must be between" in error_msg

    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = InjectionDetectionConfig()
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert config_dict["enabled"] is True
        assert config_dict["block_threshold"] == 70
        assert config_dict["alert_threshold"] == 40
        assert config_dict["entropy_threshold"] == 4.5
        assert config_dict["entropy_min_length"] == 50

    def test_from_env_defaults(self, monkeypatch):
        """Test loading from environment with no overrides."""
        # Clear any existing env vars
        for key in [
            "INJECTION_DETECTION_ENABLED",
            "INJECTION_BLOCK_THRESHOLD",
            "INJECTION_ALERT_THRESHOLD",
            "INJECTION_ENTROPY_THRESHOLD",
            "INJECTION_ENTROPY_MIN_LENGTH",
        ]:
            monkeypatch.delenv(key, raising=False)

        config = InjectionDetectionConfig.from_env()

        assert config.enabled is True
        assert config.block_threshold == 70
        assert config.alert_threshold == 40
        assert config.entropy_threshold == 4.5
        assert config.entropy_min_length == 50

    def test_from_env_with_overrides(self, monkeypatch):
        """Test loading from environment with custom values."""
        monkeypatch.setenv("INJECTION_DETECTION_ENABLED", "false")
        monkeypatch.setenv("INJECTION_BLOCK_THRESHOLD", "80")
        monkeypatch.setenv("INJECTION_ALERT_THRESHOLD", "50")
        monkeypatch.setenv("INJECTION_ENTROPY_THRESHOLD", "5.0")
        monkeypatch.setenv("INJECTION_ENTROPY_MIN_LENGTH", "100")
        monkeypatch.setenv("INJECTION_SEVERITY_WEIGHT_HIGH", "50")
        monkeypatch.setenv("INJECTION_SEVERITY_WEIGHT_MEDIUM", "25")
        monkeypatch.setenv("INJECTION_SEVERITY_WEIGHT_LOW", "10")
        monkeypatch.setenv("INJECTION_MAX_PARAMETER_DEPTH", "5")

        config = InjectionDetectionConfig.from_env()

        assert config.enabled is False
        assert config.block_threshold == 80
        assert config.alert_threshold == 50
        assert config.entropy_threshold == 5.0
        assert config.entropy_min_length == 100
        assert config.severity_weight_high == 50
        assert config.severity_weight_medium == 25
        assert config.severity_weight_low == 10
        assert config.max_parameter_depth == 5

    def test_from_env_invalid_values(self, monkeypatch):
        """Test that invalid environment values are caught during validation."""
        monkeypatch.setenv("INJECTION_BLOCK_THRESHOLD", "150")

        with pytest.raises(ValueError, match="block_threshold must be between"):
            InjectionDetectionConfig.from_env()

    def test_singleton_get_injection_config(self, monkeypatch):
        """Test singleton behavior of get_injection_config."""
        # Reset singleton
        reset_injection_config()

        # Set environment
        monkeypatch.setenv("INJECTION_BLOCK_THRESHOLD", "80")

        # First call should load from environment
        config1 = get_injection_config()
        assert config1.block_threshold == 80

        # Change environment
        monkeypatch.setenv("INJECTION_BLOCK_THRESHOLD", "90")

        # Second call should return same instance (cached)
        config2 = get_injection_config()
        assert config2.block_threshold == 80  # Still 80, not reloaded
        assert config1 is config2  # Same instance

    def test_reset_injection_config(self, monkeypatch):
        """Test that reset_injection_config clears the singleton."""
        reset_injection_config()

        monkeypatch.setenv("INJECTION_BLOCK_THRESHOLD", "80")
        config1 = get_injection_config()
        assert config1.block_threshold == 80

        # Reset and change environment
        reset_injection_config()
        monkeypatch.setenv("INJECTION_BLOCK_THRESHOLD", "90")

        # Should reload with new value
        config2 = get_injection_config()
        assert config2.block_threshold == 90
        assert config1 is not config2  # Different instances

    def test_boundary_values(self):
        """Test configuration at boundary values."""
        # Minimum valid values
        config_min = InjectionDetectionConfig(
            block_threshold=0,
            alert_threshold=0,
            entropy_threshold=0.0,
            entropy_min_length=10,
            severity_weight_high=0,
            severity_weight_medium=0,
            severity_weight_low=0,
            max_parameter_depth=1,
        )
        assert config_min.block_threshold == 0

        # Maximum valid values
        config_max = InjectionDetectionConfig(
            block_threshold=100,
            alert_threshold=100,
            entropy_threshold=8.0,
            entropy_min_length=10000,
            severity_weight_high=1000,
            severity_weight_medium=500,
            severity_weight_low=100,
            max_parameter_depth=100,
        )
        assert config_max.block_threshold == 100
