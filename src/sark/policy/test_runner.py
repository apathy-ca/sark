"""Policy test runner for YAML-based policy testing.

This module provides a test framework for OPA policies using YAML test suites.
Test suites define sample inputs and expected outputs to verify policy behavior.
"""

from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any

import structlog
import yaml

logger = structlog.get_logger()


class TestStatus(str, Enum):
    """Test result status."""

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class TestCase:
    """Represents a single test case."""

    name: str
    description: str | None
    input: dict[str, Any]
    expected: dict[str, Any]
    skip: bool = False
    skip_reason: str | None = None


@dataclass
class TestResult:
    """Result of a single test case."""

    test_name: str
    status: TestStatus
    expected: dict[str, Any] | None = None
    actual: dict[str, Any] | None = None
    error_message: str | None = None
    duration_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "test_name": self.test_name,
            "status": self.status.value,
            "expected": self.expected,
            "actual": self.actual,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
        }


@dataclass
class TestSuiteResult:
    """Result of running a test suite."""

    suite_name: str
    policy_path: Path | None
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    duration_ms: float = 0.0
    results: list[TestResult] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Whether all tests passed."""
        return self.failed == 0 and self.errors == 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "suite_name": self.suite_name,
            "policy_path": str(self.policy_path) if self.policy_path else None,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "skipped": self.skipped,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "results": [r.to_dict() for r in self.results],
        }


class PolicyTestRunner:
    """Runs YAML-based test suites for OPA policies."""

    def __init__(self, opa_path: str = "opa"):
        """
        Initialize the test runner.

        Args:
            opa_path: Path to OPA binary (default: "opa")
        """
        self.opa_path = opa_path

    def load_test_suite(self, test_suite_path: Path) -> list[TestCase]:
        """
        Load a YAML test suite file.

        Expected format:
        ```yaml
        suite_name: "Gateway Policy Tests"
        description: "Test suite for gateway authorization policy"
        policy: "path/to/policy.rego"
        tests:
          - name: "Admin can invoke any tool"
            description: "Administrators should have full access"
            input:
              user:
                roles: ["admin"]
                email: "admin@example.com"
              action: "gateway:tool:invoke"
              tool_name: "execute_query"
            expected:
              allow: true
              reason: "Allowed: admin user admin@example.com can perform any action"

          - name: "Analyst cannot execute mutations"
            input:
              user:
                roles: ["analyst"]
              action: "gateway:tool:invoke"
              tool_name: "execute_mutation"
            expected:
              allow: false
        ```

        Args:
            test_suite_path: Path to the YAML test suite file

        Returns:
            List of TestCase objects

        Raises:
            ValueError: If test suite format is invalid
        """
        try:
            with open(test_suite_path) as f:
                suite_data = yaml.safe_load(f)

            if not isinstance(suite_data, dict):
                raise ValueError("Test suite must be a YAML dictionary")

            tests = suite_data.get("tests", [])
            if not isinstance(tests, list):
                raise ValueError("'tests' must be a list")

            test_cases = []
            for idx, test_data in enumerate(tests):
                if not isinstance(test_data, dict):
                    raise ValueError(f"Test case {idx} must be a dictionary")

                # Required fields
                name = test_data.get("name")
                if not name:
                    raise ValueError(f"Test case {idx} missing 'name' field")

                input_data = test_data.get("input")
                if input_data is None:
                    raise ValueError(f"Test case '{name}' missing 'input' field")

                expected = test_data.get("expected")
                if expected is None:
                    raise ValueError(f"Test case '{name}' missing 'expected' field")

                # Optional fields
                description = test_data.get("description")
                skip = test_data.get("skip", False)
                skip_reason = test_data.get("skip_reason")

                test_cases.append(
                    TestCase(
                        name=name,
                        description=description,
                        input=input_data,
                        expected=expected,
                        skip=skip,
                        skip_reason=skip_reason,
                    )
                )

            logger.info(
                "test_suite_loaded",
                suite_path=str(test_suite_path),
                test_count=len(test_cases),
            )

            return test_cases

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in test suite: {e!s}") from e
        except FileNotFoundError as e:
            raise ValueError(f"Test suite file not found: {test_suite_path}") from e

    def run_test_suite(
        self, test_suite_path: Path, policy_path: Path | None = None
    ) -> TestSuiteResult:
        """
        Run a complete test suite against a policy.

        Args:
            test_suite_path: Path to the YAML test suite file
            policy_path: Path to the policy file. If None, reads from test suite.

        Returns:
            TestSuiteResult with all test results
        """
        import time

        start_time = time.time()

        # Load test suite metadata
        with open(test_suite_path) as f:
            suite_data = yaml.safe_load(f)

        suite_name = suite_data.get("suite_name", test_suite_path.stem)

        # Determine policy path
        if policy_path is None:
            policy_rel = suite_data.get("policy")
            if policy_rel:
                # Resolve relative to test suite directory
                policy_path = (test_suite_path.parent / policy_rel).resolve()

        if policy_path is None:
            raise ValueError("Policy path must be specified in test suite or as argument")

        if not policy_path.exists():
            raise ValueError(f"Policy file not found: {policy_path}")

        # Load test cases
        test_cases = self.load_test_suite(test_suite_path)

        # Initialize result
        result = TestSuiteResult(suite_name=suite_name, policy_path=policy_path)
        result.total = len(test_cases)

        # Run each test case
        for test_case in test_cases:
            if test_case.skip:
                test_result = TestResult(
                    test_name=test_case.name,
                    status=TestStatus.SKIPPED,
                    error_message=test_case.skip_reason,
                )
                result.skipped += 1
            else:
                test_result = self._run_test_case(test_case, policy_path)

                if test_result.status == TestStatus.PASSED:
                    result.passed += 1
                elif test_result.status == TestStatus.FAILED:
                    result.failed += 1
                elif test_result.status == TestStatus.ERROR:
                    result.errors += 1

            result.results.append(test_result)

        result.duration_ms = (time.time() - start_time) * 1000

        logger.info(
            "test_suite_completed",
            suite_name=suite_name,
            total=result.total,
            passed=result.passed,
            failed=result.failed,
            errors=result.errors,
            skipped=result.skipped,
            duration_ms=result.duration_ms,
        )

        return result

    def _run_test_case(self, test_case: TestCase, policy_path: Path) -> TestResult:
        """
        Run a single test case.

        Args:
            test_case: The test case to run
            policy_path: Path to the policy file

        Returns:
            TestResult
        """
        import time

        start_time = time.time()

        try:
            # Create temporary input file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as input_file:
                json.dump(test_case.input, input_file)
                input_file.flush()
                input_path = Path(input_file.name)

            try:
                # Run OPA eval
                result = subprocess.run(
                    [
                        self.opa_path,
                        "eval",
                        "--data",
                        str(policy_path),
                        "--input",
                        str(input_path),
                        "--format",
                        "json",
                        "data",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                duration_ms = (time.time() - start_time) * 1000

                if result.returncode != 0:
                    error_output = result.stderr or result.stdout
                    return TestResult(
                        test_name=test_case.name,
                        status=TestStatus.ERROR,
                        error_message=f"OPA evaluation failed: {error_output}",
                        duration_ms=duration_ms,
                    )

                # Parse OPA output
                opa_output = json.loads(result.stdout)

                # Extract policy result
                # OPA eval returns: {"result": [{"expressions": [{"value": {...}}]}]}
                if "result" not in opa_output or not opa_output["result"]:
                    return TestResult(
                        test_name=test_case.name,
                        status=TestStatus.ERROR,
                        error_message="OPA returned empty result",
                        duration_ms=duration_ms,
                    )

                # Get the policy package output
                actual = opa_output["result"][0]["expressions"][0]["value"]

                # Extract the specific package results we care about
                # Navigate to the package (e.g., data.mcp.gateway)
                package_parts = self._extract_package_from_policy(policy_path)
                for part in package_parts:
                    if isinstance(actual, dict) and part in actual:
                        actual = actual[part]
                    else:
                        # Package not found in expected location
                        break

                # Compare expected vs actual
                passed = self._compare_results(test_case.expected, actual)

                if passed:
                    return TestResult(
                        test_name=test_case.name,
                        status=TestStatus.PASSED,
                        expected=test_case.expected,
                        actual=actual,
                        duration_ms=duration_ms,
                    )
                else:
                    return TestResult(
                        test_name=test_case.name,
                        status=TestStatus.FAILED,
                        expected=test_case.expected,
                        actual=actual,
                        error_message=f"Expected {test_case.expected}, got {actual}",
                        duration_ms=duration_ms,
                    )

            finally:
                input_path.unlink(missing_ok=True)

        except subprocess.TimeoutExpired:
            return TestResult(
                test_name=test_case.name,
                status=TestStatus.ERROR,
                error_message="Test execution timed out (>5s)",
            )
        except Exception as e:
            return TestResult(
                test_name=test_case.name,
                status=TestStatus.ERROR,
                error_message=f"Unexpected error: {e!s}",
            )

    def _extract_package_from_policy(self, policy_path: Path) -> list[str]:
        """
        Extract package name from policy file.

        Args:
            policy_path: Path to policy file

        Returns:
            List of package parts (e.g., ["mcp", "gateway"])
        """
        try:
            content = policy_path.read_text()
            import re

            match = re.search(r"^package\s+([\w.]+)", content, re.MULTILINE)
            if match:
                package_name = match.group(1)
                return package_name.split(".")
        except Exception:
            pass

        return []

    def _compare_results(self, expected: dict[str, Any], actual: dict[str, Any]) -> bool:
        """
        Compare expected and actual results.

        Handles partial matching - expected fields must match, but actual
        can have additional fields.

        Args:
            expected: Expected result dictionary
            actual: Actual result dictionary

        Returns:
            True if results match, False otherwise
        """
        if not isinstance(actual, dict):
            return False

        # Check each expected field
        for key, expected_value in expected.items():
            if key not in actual:
                logger.debug(
                    "comparison_failed_missing_key",
                    key=key,
                    expected=expected,
                    actual=actual,
                )
                return False

            actual_value = actual[key]

            # Recursive comparison for nested dicts
            if isinstance(expected_value, dict):
                if not isinstance(actual_value, dict):
                    return False
                if not self._compare_results(expected_value, actual_value):
                    return False
            # List comparison
            elif isinstance(expected_value, list):
                if not isinstance(actual_value, list):
                    return False
                if len(expected_value) != len(actual_value):
                    return False
                # For now, simple equality check
                # Could enhance with order-independent comparison if needed
                if expected_value != actual_value:
                    return False
            # Direct value comparison
            else:
                if expected_value != actual_value:
                    logger.debug(
                        "comparison_failed_value_mismatch",
                        key=key,
                        expected_value=expected_value,
                        actual_value=actual_value,
                    )
                    return False

        return True

    def run_multiple_suites(
        self, test_suite_dir: Path, policy_dir: Path | None = None
    ) -> list[TestSuiteResult]:
        """
        Run all test suites in a directory.

        Args:
            test_suite_dir: Directory containing YAML test suite files
            policy_dir: Optional directory containing policy files

        Returns:
            List of TestSuiteResult objects
        """
        results = []

        # Find all .yaml and .yml files
        test_files = list(test_suite_dir.glob("*.yaml")) + list(test_suite_dir.glob("*.yml"))

        for test_file in sorted(test_files):
            try:
                # Determine policy path
                policy_path = None
                if policy_dir:
                    # Try to find matching policy file
                    policy_name = test_file.stem + ".rego"
                    potential_policy = policy_dir / policy_name
                    if potential_policy.exists():
                        policy_path = potential_policy

                result = self.run_test_suite(test_file, policy_path)
                results.append(result)

            except Exception as e:
                logger.error(
                    "test_suite_error",
                    test_file=str(test_file),
                    error=str(e),
                )
                # Create error result
                error_result = TestSuiteResult(suite_name=test_file.stem, policy_path=None)
                error_result.total = 1
                error_result.errors = 1
                error_result.results.append(
                    TestResult(
                        test_name="suite_load",
                        status=TestStatus.ERROR,
                        error_message=str(e),
                    )
                )
                results.append(error_result)

        return results
