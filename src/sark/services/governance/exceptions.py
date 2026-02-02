"""Governance module exceptions."""

from typing import Any


class GovernanceError(Exception):
    """Base exception for governance errors."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - {self.details}"
        return self.message


class AllowlistError(GovernanceError):
    """Allowlist-specific errors."""

    pass


class TimeRuleError(GovernanceError):
    """Time rule-specific errors."""

    pass


class EmergencyOverrideError(GovernanceError):
    """Emergency override errors."""

    pass


class ConsentError(GovernanceError):
    """Consent tracking errors."""

    pass


class OverrideError(GovernanceError):
    """Per-request override errors."""

    pass


class EnforcementError(GovernanceError):
    """Policy enforcement errors."""

    pass
