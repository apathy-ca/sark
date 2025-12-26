"""Policy validation framework for OPA Rego policies.

This package provides comprehensive validation for OPA policies to prevent
injection attacks and ensure policy quality.
"""

from sark.policy.loader import (
    PolicyLoader,
    PolicyLoadError,
    load_and_validate_policy,
    validate_policy_file,
)
from sark.policy.test_runner import (
    PolicyTestRunner,
    TestCase,
    TestResult,
    TestStatus,
    TestSuiteResult,
)
from sark.policy.validator import (
    PolicyValidator,
    Severity,
    ValidationIssue,
    ValidationResult,
)

__all__ = [
    # Validator
    "PolicyValidator",
    "ValidationResult",
    "ValidationIssue",
    "Severity",
    # Loader
    "PolicyLoader",
    "PolicyLoadError",
    "validate_policy_file",
    "load_and_validate_policy",
    # Test Runner
    "PolicyTestRunner",
    "TestCase",
    "TestResult",
    "TestStatus",
    "TestSuiteResult",
]
