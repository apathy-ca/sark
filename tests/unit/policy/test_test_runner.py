"""Unit tests for policy test runner."""

from pathlib import Path

import pytest
import yaml

from sark.policy.test_runner import (
    PolicyTestRunner,
    TestCase,
    TestStatus,
)


class TestPolicyTestRunner:
    """Test PolicyTestRunner class."""

    @pytest.fixture
    def runner(self):
        """Create a PolicyTestRunner instance."""
        return PolicyTestRunner()

    @pytest.fixture
    def sample_test_suite(self, tmp_path):
        """Create a sample test suite file."""
        policy = """
package test.simple

import future.keywords.if

default allow := false

allow if {
    input.user.role == "admin"
}

deny contains "not admin" if {
    not input.user.role == "admin"
}

reason := "Admin access granted" if { allow }
reason := "Access denied - not admin" if { not allow }
"""
        policy_file = tmp_path / "simple.rego"
        policy_file.write_text(policy)

        test_suite = {
            "suite_name": "Simple Policy Tests",
            "description": "Basic authorization tests",
            "policy": "simple.rego",
            "tests": [
                {
                    "name": "Admin user allowed",
                    "description": "Admin users should be allowed",
                    "input": {"user": {"role": "admin"}},
                    "expected": {"allow": True},
                },
                {
                    "name": "Regular user denied",
                    "description": "Regular users should be denied",
                    "input": {"user": {"role": "user"}},
                    "expected": {"allow": False},
                },
                {
                    "name": "Skipped test",
                    "input": {"user": {"role": "guest"}},
                    "expected": {"allow": False},
                    "skip": True,
                    "skip_reason": "Test not ready",
                },
            ],
        }

        test_file = tmp_path / "simple.yaml"
        with open(test_file, "w") as f:
            yaml.dump(test_suite, f)

        return test_file, policy_file

    def test_runner_initialization(self):
        """Test runner can be initialized."""
        runner = PolicyTestRunner()
        assert runner.opa_path == "opa"

        runner2 = PolicyTestRunner(opa_path="/usr/bin/opa")
        assert runner2.opa_path == "/usr/bin/opa"

    def test_load_test_suite(self, runner, sample_test_suite):
        """Test loading a YAML test suite."""
        test_file, _ = sample_test_suite

        test_cases = runner.load_test_suite(test_file)

        assert len(test_cases) == 3
        assert isinstance(test_cases[0], TestCase)
        assert test_cases[0].name == "Admin user allowed"
        assert test_cases[0].description == "Admin users should be allowed"
        assert test_cases[0].input == {"user": {"role": "admin"}}
        assert test_cases[0].expected == {"allow": True}
        assert test_cases[0].skip is False

        assert test_cases[2].skip is True
        assert test_cases[2].skip_reason == "Test not ready"

    def test_load_invalid_test_suite(self, runner, tmp_path):
        """Test loading an invalid test suite."""
        # Create invalid YAML
        test_file = tmp_path / "invalid.yaml"
        test_file.write_text("{ invalid yaml")

        with pytest.raises(ValueError, match="Invalid YAML"):
            runner.load_test_suite(test_file)

    def test_load_test_suite_missing_tests(self, runner, tmp_path):
        """Test loading a test suite without tests array."""
        test_file = tmp_path / "no_tests.yaml"
        with open(test_file, "w") as f:
            yaml.dump({"suite_name": "Test"}, f)

        # Should return empty list if no tests
        test_cases = runner.load_test_suite(test_file)
        assert test_cases == []

    def test_load_test_suite_missing_required_fields(self, runner, tmp_path):
        """Test loading a test suite with missing required fields."""
        test_file = tmp_path / "missing_fields.yaml"
        test_suite = {
            "tests": [
                {
                    # Missing 'name' field
                    "input": {"user": {"role": "admin"}},
                    "expected": {"allow": True},
                }
            ]
        }
        with open(test_file, "w") as f:
            yaml.dump(test_suite, f)

        with pytest.raises(ValueError, match="missing 'name' field"):
            runner.load_test_suite(test_file)

    def test_load_test_suite_file_not_found(self, runner):
        """Test loading a non-existent test suite."""
        with pytest.raises(ValueError, match="Test suite file not found"):
            runner.load_test_suite(Path("/nonexistent/test.yaml"))

    def test_run_test_suite(self, runner, sample_test_suite):
        """Test running a complete test suite."""
        test_file, policy_file = sample_test_suite

        result = runner.run_test_suite(test_file, policy_file)

        assert result.suite_name == "Simple Policy Tests"
        assert result.policy_path == policy_file
        assert result.total == 3
        assert result.passed == 2
        assert result.failed == 0
        assert result.errors == 0
        assert result.skipped == 1
        assert result.success is True
        assert result.duration_ms > 0

    def test_run_test_suite_with_failures(self, runner, tmp_path):
        """Test running a test suite with failures."""
        policy = """
package test.fail

import future.keywords.if

default allow := false

allow if {
    input.user.role == "admin"
}

reason := "test" if { true }
"""
        policy_file = tmp_path / "fail.rego"
        policy_file.write_text(policy)

        test_suite = {
            "suite_name": "Failing Tests",
            "policy": "fail.rego",
            "tests": [
                {
                    "name": "Expected to pass but fails",
                    "input": {"user": {"role": "user"}},
                    "expected": {"allow": True},  # Wrong expectation
                },
            ],
        }

        test_file = tmp_path / "fail.yaml"
        with open(test_file, "w") as f:
            yaml.dump(test_suite, f)

        result = runner.run_test_suite(test_file, policy_file)

        assert result.total == 1
        assert result.passed == 0
        assert result.failed == 1
        assert result.errors == 0
        assert result.success is False

        failed_test = result.results[0]
        assert failed_test.status == TestStatus.FAILED
        assert failed_test.expected == {"allow": True}
        assert failed_test.actual["allow"] is False

    def test_run_test_suite_with_errors(self, runner, tmp_path):
        """Test running a test suite with errors."""
        # Create policy with syntax error
        policy = """
package test.error

default allow := false

# Syntax error - missing closing brace
allow if {
    input.user.role == "admin"
"""
        policy_file = tmp_path / "error.rego"
        policy_file.write_text(policy)

        test_suite = {
            "suite_name": "Error Tests",
            "policy": "error.rego",
            "tests": [
                {
                    "name": "Test with syntax error",
                    "input": {"user": {"role": "admin"}},
                    "expected": {"allow": True},
                },
            ],
        }

        test_file = tmp_path / "error.yaml"
        with open(test_file, "w") as f:
            yaml.dump(test_suite, f)

        result = runner.run_test_suite(test_file, policy_file)

        assert result.total == 1
        assert result.passed == 0
        assert result.errors == 1
        assert result.success is False

        error_test = result.results[0]
        assert error_test.status == TestStatus.ERROR
        assert "OPA evaluation failed" in error_test.error_message

    def test_run_test_suite_policy_not_found(self, runner, tmp_path):
        """Test running a test suite with missing policy."""
        test_suite = {
            "suite_name": "Missing Policy Test",
            "policy": "nonexistent.rego",
            "tests": [
                {
                    "name": "Test",
                    "input": {},
                    "expected": {},
                },
            ],
        }

        test_file = tmp_path / "test.yaml"
        with open(test_file, "w") as f:
            yaml.dump(test_suite, f)

        with pytest.raises(ValueError, match="Policy file not found"):
            runner.run_test_suite(test_file)

    def test_compare_results_exact_match(self, runner):
        """Test comparing results with exact match."""
        expected = {"allow": True, "reason": "admin access"}
        actual = {"allow": True, "reason": "admin access"}

        assert runner._compare_results(expected, actual) is True

    def test_compare_results_partial_match(self, runner):
        """Test comparing results with partial match."""
        expected = {"allow": True}
        actual = {"allow": True, "reason": "admin access", "extra": "field"}

        # Partial matching - expected fields must match
        assert runner._compare_results(expected, actual) is True

    def test_compare_results_value_mismatch(self, runner):
        """Test comparing results with value mismatch."""
        expected = {"allow": True}
        actual = {"allow": False}

        assert runner._compare_results(expected, actual) is False

    def test_compare_results_missing_key(self, runner):
        """Test comparing results with missing key."""
        expected = {"allow": True, "reason": "test"}
        actual = {"allow": True}

        assert runner._compare_results(expected, actual) is False

    def test_compare_results_nested_dict(self, runner):
        """Test comparing results with nested dictionaries."""
        expected = {"allow": True, "user": {"role": "admin"}}
        actual = {"allow": True, "user": {"role": "admin", "id": 123}}

        assert runner._compare_results(expected, actual) is True

        # Nested value mismatch
        expected2 = {"allow": True, "user": {"role": "admin"}}
        actual2 = {"allow": True, "user": {"role": "user"}}

        assert runner._compare_results(expected2, actual2) is False

    def test_compare_results_lists(self, runner):
        """Test comparing results with lists."""
        expected = {"roles": ["admin", "user"]}
        actual = {"roles": ["admin", "user"]}

        assert runner._compare_results(expected, actual) is True

        # Different list
        expected2 = {"roles": ["admin"]}
        actual2 = {"roles": ["admin", "user"]}

        assert runner._compare_results(expected2, actual2) is False

    def test_extract_package_from_policy(self, runner, tmp_path):
        """Test extracting package name from policy."""
        policy = """
package my.custom.package

default allow := false
"""
        policy_file = tmp_path / "policy.rego"
        policy_file.write_text(policy)

        package_parts = runner._extract_package_from_policy(policy_file)

        assert package_parts == ["my", "custom", "package"]

    def test_result_to_dict(self, runner, sample_test_suite):
        """Test converting test result to dictionary."""
        test_file, policy_file = sample_test_suite

        result = runner.run_test_suite(test_file, policy_file)
        result_dict = result.to_dict()

        assert result_dict["suite_name"] == "Simple Policy Tests"
        assert result_dict["total"] == 3
        assert result_dict["passed"] == 2
        assert result_dict["failed"] == 0
        assert result_dict["errors"] == 0
        assert result_dict["skipped"] == 1
        assert result_dict["success"] is True
        assert "results" in result_dict
        assert len(result_dict["results"]) == 3

    def test_run_multiple_suites(self, runner, tmp_path):
        """Test running multiple test suites from a directory."""
        # Create first policy and test
        policy1 = """
package test.one

import future.keywords.if

default allow := false

allow if { input.user.role == "admin" }

reason := "test" if { true }
"""
        (tmp_path / "one.rego").write_text(policy1)

        test1 = {
            "suite_name": "Test One",
            "policy": "one.rego",
            "tests": [
                {
                    "name": "Test 1",
                    "input": {"user": {"role": "admin"}},
                    "expected": {"allow": True},
                }
            ],
        }
        with open(tmp_path / "one.yaml", "w") as f:
            yaml.dump(test1, f)

        # Create second policy and test
        policy2 = """
package test.two

import future.keywords.if

default allow := false

allow if { input.user.role == "user" }

reason := "test" if { true }
"""
        (tmp_path / "two.rego").write_text(policy2)

        test2 = {
            "suite_name": "Test Two",
            "policy": "two.rego",
            "tests": [
                {
                    "name": "Test 2",
                    "input": {"user": {"role": "user"}},
                    "expected": {"allow": True},
                }
            ],
        }
        with open(tmp_path / "two.yaml", "w") as f:
            yaml.dump(test2, f)

        results = runner.run_multiple_suites(tmp_path, tmp_path)

        assert len(results) == 2
        assert all(r.success for r in results)
        assert results[0].suite_name == "Test One"
        assert results[1].suite_name == "Test Two"

    def test_run_multiple_suites_with_errors(self, runner, tmp_path):
        """Test running multiple suites where some have errors."""
        # Valid suite
        policy = """
package test.valid

import future.keywords.if

default allow := false
allow if { true }
reason := "test" if { true }
"""
        (tmp_path / "valid.rego").write_text(policy)

        test_valid = {
            "suite_name": "Valid",
            "policy": "valid.rego",
            "tests": [{"name": "Test", "input": {}, "expected": {"allow": True}}],
        }
        with open(tmp_path / "valid.yaml", "w") as f:
            yaml.dump(test_valid, f)

        # Invalid suite (missing policy file)
        test_invalid = {
            "suite_name": "Invalid",
            "policy": "nonexistent.rego",
            "tests": [{"name": "Test", "input": {}, "expected": {}}],
        }
        with open(tmp_path / "invalid.yaml", "w") as f:
            yaml.dump(test_invalid, f)

        results = runner.run_multiple_suites(tmp_path)

        assert len(results) == 2

        # One should succeed, one should have error
        success_count = sum(1 for r in results if r.success)
        error_count = sum(1 for r in results if not r.success)

        assert success_count == 1
        assert error_count == 1
