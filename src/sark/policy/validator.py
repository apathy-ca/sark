"""Policy validation framework to prevent OPA policy injection attacks.

This module provides comprehensive validation for OPA Rego policies including:
- Syntax validation via OPA check
- Required rules verification (allow, deny, reason)
- Forbidden pattern detection (security vulnerabilities)
- Sample input testing
"""

from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any

import structlog

logger = structlog.get_logger()


class Severity(str, Enum):
    """Validation issue severity levels."""

    CRITICAL = "critical"  # Policy must be rejected
    HIGH = "high"  # Serious security concern
    MEDIUM = "medium"  # Potential issue
    LOW = "low"  # Best practice violation
    INFO = "info"  # Informational


@dataclass
class ValidationIssue:
    """Represents a validation issue found in a policy."""

    severity: Severity
    code: str  # Unique issue code (e.g., "FORBIDDEN_HTTP_SEND")
    message: str
    line_number: int | None = None
    column: int | None = None
    context: str | None = None  # Code snippet showing the issue
    suggestion: str | None = None  # How to fix it


@dataclass
class ValidationResult:
    """Result of policy validation."""

    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    policy_name: str | None = None
    package_name: str | None = None

    @property
    def critical_issues(self) -> list[ValidationIssue]:
        """Get critical severity issues."""
        return [i for i in self.issues if i.severity == Severity.CRITICAL]

    @property
    def high_issues(self) -> list[ValidationIssue]:
        """Get high severity issues."""
        return [i for i in self.issues if i.severity == Severity.HIGH]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "valid": self.valid,
            "policy_name": self.policy_name,
            "package_name": self.package_name,
            "issues": [
                {
                    "severity": issue.severity.value,
                    "code": issue.code,
                    "message": issue.message,
                    "line_number": issue.line_number,
                    "column": issue.column,
                    "context": issue.context,
                    "suggestion": issue.suggestion,
                }
                for issue in self.issues
            ],
        }


# Forbidden patterns that indicate security vulnerabilities
FORBIDDEN_PATTERNS = [
    {
        "pattern": r"^default\s+allow\s*:=\s*true",
        "code": "BLANKET_ALLOW",
        "severity": Severity.CRITICAL,
        "message": "Blanket 'default allow := true' detected - policies should deny by default",
        "suggestion": "Use 'default allow := false' and explicitly define allow conditions",
    },
    {
        "pattern": r"http\.send\s*\(",
        "code": "FORBIDDEN_HTTP_SEND",
        "severity": Severity.CRITICAL,
        "message": "http.send() detected - external HTTP calls can leak data and create SSRF vulnerabilities",
        "suggestion": "Remove http.send() calls. Use policy inputs instead.",
    },
    {
        "pattern": r"opa\.runtime\s*\(",
        "code": "FORBIDDEN_OPA_RUNTIME",
        "severity": Severity.CRITICAL,
        "message": "opa.runtime() detected - access to OPA runtime can leak sensitive information",
        "suggestion": "Remove opa.runtime() calls",
    },
    {
        "pattern": r"file\.(read|write|remove)",
        "code": "FORBIDDEN_FILE_ACCESS",
        "severity": Severity.CRITICAL,
        "message": "File system access detected - policies should not read/write files",
        "suggestion": "Remove file system access. Use policy inputs instead.",
    },
    {
        "pattern": r"net\.cidr_contains_matches\s*\(\s*\"0\.0\.0\.0/0\"",
        "code": "OVERLY_BROAD_CIDR",
        "severity": Severity.HIGH,
        "message": "Overly broad CIDR range 0.0.0.0/0 detected - this allows all IPs",
        "suggestion": "Use specific CIDR ranges for your network",
    },
    {
        "pattern": r"allow\s*:=\s*true\s*$",
        "code": "UNCONDITIONAL_ALLOW",
        "severity": Severity.CRITICAL,
        "message": "Unconditional 'allow := true' without conditions detected",
        "suggestion": "Add conditions to allow rules using 'if { ... }' blocks",
    },
    {
        "pattern": r"allow\s+if\s*\{\s*\}",
        "code": "EMPTY_ALLOW_CONDITION",
        "severity": Severity.CRITICAL,
        "message": "Empty allow condition detected - this allows everything",
        "suggestion": "Add actual authorization checks inside the allow rule",
    },
    {
        "pattern": r"trace\s*\(",
        "code": "DEBUG_TRACE",
        "severity": Severity.MEDIUM,
        "message": "trace() function detected - may leak sensitive data in logs",
        "suggestion": "Remove trace() calls before deploying to production",
    },
    {
        "pattern": r"print\s*\(",
        "code": "DEBUG_PRINT",
        "severity": Severity.MEDIUM,
        "message": "print() function detected - may leak sensitive data in logs",
        "suggestion": "Remove print() calls before deploying to production",
    },
    {
        "pattern": r'==\s*""[^"]',
        "code": "EMPTY_STRING_CHECK",
        "severity": Severity.LOW,
        "message": "Comparison with empty string - consider using not exists or checking length",
        "suggestion": "Use 'not input.field' or check if field exists",
    },
    {
        "pattern": r"regex\.match\s*\(\s*[\"']\.?\*",
        "code": "OVERLY_BROAD_REGEX",
        "severity": Severity.HIGH,
        "message": "Overly permissive regex pattern detected (.*)",
        "suggestion": "Use more specific regex patterns",
    },
    {
        "pattern": r"walk\s*\(\s*input\s*\)",
        "code": "WALK_FULL_INPUT",
        "severity": Severity.MEDIUM,
        "message": "Walking entire input tree may have performance implications",
        "suggestion": "Walk specific subtrees instead of entire input",
    },
    {
        "pattern": r"eval\s*\(",
        "code": "FORBIDDEN_EVAL",
        "severity": Severity.CRITICAL,
        "message": "Dynamic evaluation detected - potential code injection vulnerability",
        "suggestion": "Remove eval() calls. Write explicit policy logic instead.",
    },
    {
        "pattern": r"#\s*(TODO|FIXME|HACK)",
        "code": "TODO_COMMENT",
        "severity": Severity.INFO,
        "message": "TODO/FIXME/HACK comment found - policy may be incomplete",
        "suggestion": "Address TODO items before deploying to production",
    },
]


class PolicyValidator:
    """Validates OPA Rego policies for security and correctness."""

    def __init__(self, opa_path: str = "opa", strict: bool = True):
        """
        Initialize the policy validator.

        Args:
            opa_path: Path to OPA binary (default: "opa")
            strict: If True, treat HIGH severity issues as validation failures
        """
        self.opa_path = opa_path
        self.strict = strict

    def validate(
        self,
        policy_content: str,
        policy_name: str | None = None,
        sample_inputs: list[dict[str, Any]] | None = None,
    ) -> ValidationResult:
        """
        Validate a Rego policy comprehensively.

        Args:
            policy_content: The Rego policy content as a string
            policy_name: Optional name for the policy (for reporting)
            sample_inputs: Optional list of sample inputs to test the policy with

        Returns:
            ValidationResult with validation status and any issues found
        """
        result = ValidationResult(valid=True, policy_name=policy_name)

        # Extract package name
        package_match = re.search(r"^package\s+([\w.]+)", policy_content, re.MULTILINE)
        if package_match:
            result.package_name = package_match.group(1)
        else:
            result.issues.append(
                ValidationIssue(
                    severity=Severity.CRITICAL,
                    code="MISSING_PACKAGE",
                    message="Policy must declare a package",
                    suggestion="Add 'package <name>' at the top of the policy",
                )
            )

        # 1. Syntax validation
        syntax_issues = self._validate_syntax(policy_content)
        result.issues.extend(syntax_issues)

        # 2. Required rules validation
        required_issues = self._validate_required_rules(policy_content)
        result.issues.extend(required_issues)

        # 3. Forbidden patterns detection
        pattern_issues = self._detect_forbidden_patterns(policy_content)
        result.issues.extend(pattern_issues)

        # 4. Sample input testing (if provided)
        if sample_inputs:
            test_issues = self._test_sample_inputs(policy_content, sample_inputs)
            result.issues.extend(test_issues)

        # Determine if policy is valid
        # CRITICAL issues always fail validation
        # HIGH issues fail in strict mode
        # MEDIUM issues fail in strict mode
        has_blocking_issues = any(
            issue.severity == Severity.CRITICAL
            or (self.strict and issue.severity in [Severity.HIGH, Severity.MEDIUM])
            for issue in result.issues
        )
        result.valid = not has_blocking_issues

        if not result.valid:
            logger.warning(
                "policy_validation_failed",
                policy_name=policy_name,
                package=result.package_name,
                critical_count=len(result.critical_issues),
                high_count=len(result.high_issues),
            )
        else:
            logger.info(
                "policy_validation_passed",
                policy_name=policy_name,
                package=result.package_name,
                issue_count=len(result.issues),
            )

        return result

    def _validate_syntax(self, policy_content: str) -> list[ValidationIssue]:
        """
        Validate Rego syntax using 'opa check'.

        Args:
            policy_content: The Rego policy content

        Returns:
            List of validation issues found
        """
        issues = []

        try:
            # Write policy to temporary file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".rego", delete=False) as tmp_file:
                tmp_file.write(policy_content)
                tmp_file.flush()
                tmp_path = Path(tmp_file.name)

            try:
                # Run opa check
                result = subprocess.run(
                    [self.opa_path, "check", str(tmp_path)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode != 0:
                    # Parse OPA errors
                    error_output = result.stderr or result.stdout
                    issues.append(
                        ValidationIssue(
                            severity=Severity.CRITICAL,
                            code="SYNTAX_ERROR",
                            message=f"OPA syntax check failed: {error_output}",
                            suggestion="Fix syntax errors reported by OPA",
                        )
                    )

            finally:
                # Clean up temporary file
                tmp_path.unlink(missing_ok=True)

        except subprocess.TimeoutExpired:
            issues.append(
                ValidationIssue(
                    severity=Severity.CRITICAL,
                    code="VALIDATION_TIMEOUT",
                    message="OPA syntax check timed out (>10s)",
                    suggestion="Policy may be too complex or contain infinite loops",
                )
            )
        except FileNotFoundError:
            issues.append(
                ValidationIssue(
                    severity=Severity.CRITICAL,
                    code="OPA_NOT_FOUND",
                    message=f"OPA binary not found at: {self.opa_path}",
                    suggestion="Install OPA or specify correct path",
                )
            )
        except Exception as e:
            issues.append(
                ValidationIssue(
                    severity=Severity.CRITICAL,
                    code="VALIDATION_ERROR",
                    message=f"Unexpected error during syntax validation: {e!s}",
                )
            )

        return issues

    def _validate_required_rules(self, policy_content: str) -> list[ValidationIssue]:
        """
        Validate that required rules are present.

        A valid authorization policy should have:
        - Either 'allow' or 'deny' rules (or both)
        - A 'reason' rule for audit logging

        Args:
            policy_content: The Rego policy content

        Returns:
            List of validation issues
        """
        issues = []

        # Check for allow rule
        has_allow = bool(re.search(r"^(default\s+)?allow\s*(:=|if)", policy_content, re.MULTILINE))

        # Check for deny rule
        has_deny = bool(
            re.search(r"^(default\s+)?deny\s*(:=|if|contains)", policy_content, re.MULTILINE)
        )

        if not has_allow and not has_deny:
            issues.append(
                ValidationIssue(
                    severity=Severity.CRITICAL,
                    code="MISSING_ALLOW_DENY",
                    message="Policy must define at least one 'allow' or 'deny' rule",
                    suggestion="Add authorization rules: 'allow if { ... }' or 'deny if { ... }'",
                )
            )

        # Check for reason rule (important for audit trail)
        has_reason = bool(re.search(r"^reason\s*:=", policy_content, re.MULTILINE))

        if not has_reason:
            issues.append(
                ValidationIssue(
                    severity=Severity.HIGH,
                    code="MISSING_REASON",
                    message="Policy should define a 'reason' rule for audit logging",
                    suggestion="Add 'reason := ...' rules to explain allow/deny decisions",
                )
            )

        # Check for default deny (best practice)
        has_default_deny = bool(
            re.search(r"^default\s+allow\s*:=\s*false", policy_content, re.MULTILINE)
        )

        if has_allow and not has_default_deny:
            issues.append(
                ValidationIssue(
                    severity=Severity.HIGH,
                    code="MISSING_DEFAULT_DENY",
                    message="Policy should have 'default allow := false' for security",
                    suggestion="Add 'default allow := false' to deny by default",
                )
            )

        return issues

    def _detect_forbidden_patterns(self, policy_content: str) -> list[ValidationIssue]:
        """
        Detect forbidden patterns that indicate security vulnerabilities.

        Args:
            policy_content: The Rego policy content

        Returns:
            List of validation issues
        """
        issues = []
        lines = policy_content.split("\n")

        for pattern_def in FORBIDDEN_PATTERNS:
            pattern = pattern_def["pattern"]
            regex = re.compile(pattern, re.MULTILINE | re.DOTALL)

            # Search line by line for single-line patterns
            for line_num, line in enumerate(lines, start=1):
                # Skip comments (but still check for TODO/FIXME/HACK)
                if line.strip().startswith("#") and pattern_def["code"] != "TODO_COMMENT":
                    continue

                match = regex.search(line)
                if match:
                    issues.append(
                        ValidationIssue(
                            severity=pattern_def["severity"],
                            code=pattern_def["code"],
                            message=pattern_def["message"],
                            line_number=line_num,
                            context=line.strip(),
                            suggestion=pattern_def.get("suggestion"),
                        )
                    )

            # Also search whole content for multi-line patterns (like empty braces)
            # Use a separate search for patterns that might span lines
            if any(char in pattern for char in [r"\s*\{", r"\}"]):
                whole_matches = regex.finditer(policy_content)
                for match in whole_matches:
                    # Calculate line number
                    line_num = policy_content[: match.start()].count("\n") + 1
                    # Get context (the matched text)
                    context = match.group().replace("\n", " ").strip()

                    # Skip if we already found this on a single line
                    if not any(
                        issue.line_number == line_num and issue.code == pattern_def["code"]
                        for issue in issues
                    ):
                        issues.append(
                            ValidationIssue(
                                severity=pattern_def["severity"],
                                code=pattern_def["code"],
                                message=pattern_def["message"],
                                line_number=line_num,
                                context=context,
                                suggestion=pattern_def.get("suggestion"),
                            )
                        )

        return issues

    def _test_sample_inputs(
        self, policy_content: str, sample_inputs: list[dict[str, Any]]
    ) -> list[ValidationIssue]:
        """
        Test policy with sample inputs to ensure it evaluates correctly.

        Args:
            policy_content: The Rego policy content
            sample_inputs: List of sample input dictionaries

        Returns:
            List of validation issues
        """
        issues = []

        try:
            # Write policy to temporary file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".rego", delete=False) as policy_file:
                policy_file.write(policy_content)
                policy_file.flush()
                policy_path = Path(policy_file.name)

            try:
                for idx, sample_input in enumerate(sample_inputs):
                    # Write input to temporary file
                    with tempfile.NamedTemporaryFile(
                        mode="w", suffix=".json", delete=False
                    ) as input_file:
                        json.dump(sample_input, input_file)
                        input_file.flush()
                        input_path = Path(input_file.name)

                    try:
                        # Evaluate policy with sample input
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

                        if result.returncode != 0:
                            error_output = result.stderr or result.stdout
                            issues.append(
                                ValidationIssue(
                                    severity=Severity.HIGH,
                                    code="SAMPLE_INPUT_FAILED",
                                    message=f"Sample input {idx + 1} failed to evaluate: {error_output}",
                                    suggestion="Check policy logic and sample input structure",
                                )
                            )

                    finally:
                        input_path.unlink(missing_ok=True)

            finally:
                policy_path.unlink(missing_ok=True)

        except subprocess.TimeoutExpired:
            issues.append(
                ValidationIssue(
                    severity=Severity.HIGH,
                    code="SAMPLE_TEST_TIMEOUT",
                    message="Sample input testing timed out",
                    suggestion="Policy evaluation may be too slow or contain loops",
                )
            )
        except Exception as e:
            issues.append(
                ValidationIssue(
                    severity=Severity.MEDIUM,
                    code="SAMPLE_TEST_ERROR",
                    message=f"Error testing sample inputs: {e!s}",
                )
            )

        return issues

    def validate_file(
        self, policy_path: Path, sample_inputs: list[dict[str, Any]] | None = None
    ) -> ValidationResult:
        """
        Validate a policy file.

        Args:
            policy_path: Path to the .rego file
            sample_inputs: Optional list of sample inputs

        Returns:
            ValidationResult
        """
        try:
            policy_content = policy_path.read_text()
            return self.validate(
                policy_content,
                policy_name=policy_path.name,
                sample_inputs=sample_inputs,
            )
        except Exception as e:
            result = ValidationResult(valid=False, policy_name=policy_path.name)
            result.issues.append(
                ValidationIssue(
                    severity=Severity.CRITICAL,
                    code="FILE_READ_ERROR",
                    message=f"Failed to read policy file: {e!s}",
                )
            )
            return result
