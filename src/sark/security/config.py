"""Configuration for prompt injection detection system."""

from dataclasses import dataclass
import os
from typing import ClassVar

import structlog

logger = structlog.get_logger()


@dataclass
class InjectionDetectionConfig:
    """Configuration for prompt injection detection."""

    # Detection settings
    enabled: bool = True

    # Risk thresholds (0-100 scale)
    block_threshold: int = 70
    alert_threshold: int = 40

    # Entropy analysis settings
    entropy_threshold: float = 4.5
    entropy_min_length: int = 50

    # Pattern weights for risk scoring
    severity_weight_high: int = 30
    severity_weight_medium: int = 15
    severity_weight_low: int = 5

    # Performance settings
    max_parameter_depth: int = 10  # Maximum nesting depth for parameter scanning

    # Valid ranges for validation
    MIN_THRESHOLD: ClassVar[int] = 0
    MAX_THRESHOLD: ClassVar[int] = 100
    MIN_ENTROPY: ClassVar[float] = 0.0
    MAX_ENTROPY: ClassVar[float] = 8.0
    MIN_ENTROPY_LENGTH: ClassVar[int] = 10
    MAX_ENTROPY_LENGTH: ClassVar[int] = 10000

    def __post_init__(self):
        """Validate configuration after initialization."""
        self.validate()

    def validate(self) -> None:
        """
        Validate configuration values.

        Raises:
            ValueError: If any configuration value is invalid
        """
        errors = []

        # Validate block threshold
        if not (self.MIN_THRESHOLD <= self.block_threshold <= self.MAX_THRESHOLD):
            errors.append(
                f"block_threshold must be between {self.MIN_THRESHOLD} and {self.MAX_THRESHOLD}, "
                f"got {self.block_threshold}"
            )

        # Validate alert threshold
        if not (self.MIN_THRESHOLD <= self.alert_threshold <= self.MAX_THRESHOLD):
            errors.append(
                f"alert_threshold must be between {self.MIN_THRESHOLD} and {self.MAX_THRESHOLD}, "
                f"got {self.alert_threshold}"
            )

        # Validate threshold ordering
        if self.alert_threshold > self.block_threshold:
            errors.append(
                f"alert_threshold ({self.alert_threshold}) cannot be greater than "
                f"block_threshold ({self.block_threshold})"
            )

        # Validate entropy threshold
        if not (self.MIN_ENTROPY <= self.entropy_threshold <= self.MAX_ENTROPY):
            errors.append(
                f"entropy_threshold must be between {self.MIN_ENTROPY} and {self.MAX_ENTROPY}, "
                f"got {self.entropy_threshold}"
            )

        # Validate entropy minimum length
        if not (self.MIN_ENTROPY_LENGTH <= self.entropy_min_length <= self.MAX_ENTROPY_LENGTH):
            errors.append(
                f"entropy_min_length must be between {self.MIN_ENTROPY_LENGTH} and {self.MAX_ENTROPY_LENGTH}, "
                f"got {self.entropy_min_length}"
            )

        # Validate severity weights
        if self.severity_weight_high < 0:
            errors.append(
                f"severity_weight_high must be non-negative, got {self.severity_weight_high}"
            )
        if self.severity_weight_medium < 0:
            errors.append(
                f"severity_weight_medium must be non-negative, got {self.severity_weight_medium}"
            )
        if self.severity_weight_low < 0:
            errors.append(
                f"severity_weight_low must be non-negative, got {self.severity_weight_low}"
            )

        # Validate weight ordering (high > medium > low)
        if self.severity_weight_high < self.severity_weight_medium:
            errors.append(
                f"severity_weight_high ({self.severity_weight_high}) should be >= "
                f"severity_weight_medium ({self.severity_weight_medium})"
            )
        if self.severity_weight_medium < self.severity_weight_low:
            errors.append(
                f"severity_weight_medium ({self.severity_weight_medium}) should be >= "
                f"severity_weight_low ({self.severity_weight_low})"
            )

        # Validate max parameter depth
        if self.max_parameter_depth < 1:
            errors.append(f"max_parameter_depth must be at least 1, got {self.max_parameter_depth}")

        if errors:
            error_msg = "Invalid injection detection configuration:\n" + "\n".join(
                f"  - {e}" for e in errors
            )
            logger.error("injection_config_validation_failed", errors=errors)
            raise ValueError(error_msg)

        logger.info(
            "injection_config_validated",
            block_threshold=self.block_threshold,
            alert_threshold=self.alert_threshold,
            entropy_threshold=self.entropy_threshold,
        )

    @classmethod
    def from_env(cls) -> "InjectionDetectionConfig":
        """
        Load configuration from environment variables.

        Environment variables:
        - INJECTION_DETECTION_ENABLED: Enable/disable detection (default: true)
        - INJECTION_BLOCK_THRESHOLD: Risk threshold for blocking (default: 70)
        - INJECTION_ALERT_THRESHOLD: Risk threshold for alerts (default: 40)
        - INJECTION_ENTROPY_THRESHOLD: Entropy threshold for encoded payloads (default: 4.5)
        - INJECTION_ENTROPY_MIN_LENGTH: Minimum string length for entropy check (default: 50)
        - INJECTION_SEVERITY_WEIGHT_HIGH: Points for high severity findings (default: 30)
        - INJECTION_SEVERITY_WEIGHT_MEDIUM: Points for medium severity findings (default: 15)
        - INJECTION_SEVERITY_WEIGHT_LOW: Points for low severity findings (default: 5)
        - INJECTION_MAX_PARAMETER_DEPTH: Maximum nesting depth for scanning (default: 10)

        Returns:
            InjectionDetectionConfig instance with values from environment
        """
        return cls(
            enabled=os.getenv("INJECTION_DETECTION_ENABLED", "true").lower() == "true",
            block_threshold=int(os.getenv("INJECTION_BLOCK_THRESHOLD", "70")),
            alert_threshold=int(os.getenv("INJECTION_ALERT_THRESHOLD", "40")),
            entropy_threshold=float(os.getenv("INJECTION_ENTROPY_THRESHOLD", "4.5")),
            entropy_min_length=int(os.getenv("INJECTION_ENTROPY_MIN_LENGTH", "50")),
            severity_weight_high=int(os.getenv("INJECTION_SEVERITY_WEIGHT_HIGH", "30")),
            severity_weight_medium=int(os.getenv("INJECTION_SEVERITY_WEIGHT_MEDIUM", "15")),
            severity_weight_low=int(os.getenv("INJECTION_SEVERITY_WEIGHT_LOW", "5")),
            max_parameter_depth=int(os.getenv("INJECTION_MAX_PARAMETER_DEPTH", "10")),
        )

    def to_dict(self) -> dict:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration
        """
        return {
            "enabled": self.enabled,
            "block_threshold": self.block_threshold,
            "alert_threshold": self.alert_threshold,
            "entropy_threshold": self.entropy_threshold,
            "entropy_min_length": self.entropy_min_length,
            "severity_weight_high": self.severity_weight_high,
            "severity_weight_medium": self.severity_weight_medium,
            "severity_weight_low": self.severity_weight_low,
            "max_parameter_depth": self.max_parameter_depth,
        }


# Singleton instance
_config: InjectionDetectionConfig | None = None


def get_injection_config() -> InjectionDetectionConfig:
    """
    Get singleton injection detection configuration.

    Loads from environment on first call, returns cached instance thereafter.

    Returns:
        InjectionDetectionConfig instance
    """
    global _config
    if _config is None:
        _config = InjectionDetectionConfig.from_env()
    return _config


def reset_injection_config() -> None:
    """
    Reset singleton configuration (primarily for testing).

    This will cause the next call to get_injection_config() to reload from environment.
    """
    global _config
    _config = None
