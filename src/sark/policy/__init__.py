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
    "PolicyLoadError",
    # Loader
    "PolicyLoader",
    # Test Runner
    "PolicyTestRunner",
    # Validator
    "PolicyValidator",
    "Severity",
    "TestCase",
    "TestResult",
    "TestStatus",
    "TestSuiteResult",
    "ValidationIssue",
    "ValidationResult",
    "load_and_validate_policy",
    "validate_policy_file",
]
