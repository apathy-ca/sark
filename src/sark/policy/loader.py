"""Policy loader with integrated validation.

This module provides safe policy loading with automatic validation
to prevent policy injection attacks and ensure policy quality.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Any

import structlog

from sark.policy.validator import PolicyValidator, Severity, ValidationResult

logger = structlog.get_logger()


class PolicyLoadError(Exception):
    """Raised when policy loading fails validation."""

    def __init__(
        self,
        message: str,
        validation_result: ValidationResult | None = None,
    ):
        """Initialize the error."""
        super().__init__(message)
        self.validation_result = validation_result


class PolicyLoader:
    """Loads and validates OPA policies before deployment."""

    def __init__(
        self,
        validator: PolicyValidator | None = None,
        opa_path: str = "opa",
        strict: bool = True,
        auto_validate: bool = True,
    ):
        """
        Initialize the policy loader.

        Args:
            validator: PolicyValidator instance (creates default if None)
            opa_path: Path to OPA binary
            strict: If True, reject policies with HIGH severity issues
            auto_validate: If True, automatically validate all loaded policies
        """
        self.validator = validator or PolicyValidator(opa_path=opa_path, strict=strict)
        self.opa_path = opa_path
        self.strict = strict
        self.auto_validate = auto_validate

    def load_policy(
        self,
        policy_path: Path,
        sample_inputs: list[dict[str, Any]] | None = None,
        force: bool = False,
    ) -> tuple[str, ValidationResult | None]:
        """
        Load a policy file with validation.

        Args:
            policy_path: Path to the .rego policy file
            sample_inputs: Optional sample inputs to test the policy
            force: If True, load policy even if validation fails (DANGEROUS!)

        Returns:
            Tuple of (policy_content, validation_result)

        Raises:
            PolicyLoadError: If policy fails validation (unless force=True)
            FileNotFoundError: If policy file doesn't exist
        """
        if not policy_path.exists():
            raise FileNotFoundError(f"Policy file not found: {policy_path}")

        # Read policy content
        policy_content = policy_path.read_text()

        # Validate if auto_validate is enabled
        validation_result = None
        if self.auto_validate:
            validation_result = self.validator.validate(
                policy_content,
                policy_name=policy_path.name,
                sample_inputs=sample_inputs,
            )

            # Check validation result
            if not validation_result.valid:
                error_msg = self._format_validation_errors(
                    validation_result, policy_path
                )

                if force:
                    logger.warning(
                        "policy_validation_failed_force_load",
                        policy_path=str(policy_path),
                        critical_count=len(validation_result.critical_issues),
                        high_count=len(validation_result.high_issues),
                    )
                else:
                    logger.error(
                        "policy_validation_failed_rejected",
                        policy_path=str(policy_path),
                        critical_count=len(validation_result.critical_issues),
                        high_count=len(validation_result.high_issues),
                    )
                    raise PolicyLoadError(error_msg, validation_result)

        logger.info(
            "policy_loaded",
            policy_path=str(policy_path),
            package=validation_result.package_name if validation_result else None,
            validated=self.auto_validate,
        )

        return policy_content, validation_result

    def load_policy_directory(
        self,
        policy_dir: Path,
        pattern: str = "*.rego",
        recursive: bool = True,
        sample_inputs_dir: Path | None = None,
    ) -> dict[str, tuple[str, ValidationResult | None]]:
        """
        Load all policies from a directory.

        Args:
            policy_dir: Directory containing policy files
            pattern: Glob pattern for policy files (default: "*.rego")
            recursive: If True, search subdirectories
            sample_inputs_dir: Optional directory containing sample input JSON files

        Returns:
            Dictionary mapping policy names to (content, validation_result) tuples

        Raises:
            PolicyLoadError: If any policy fails validation
        """
        if not policy_dir.exists():
            raise FileNotFoundError(f"Policy directory not found: {policy_dir}")

        policies = {}
        errors = []

        # Find policy files
        if recursive:
            policy_files = list(policy_dir.rglob(pattern))
        else:
            policy_files = list(policy_dir.glob(pattern))

        for policy_file in sorted(policy_files):
            try:
                # Load sample inputs if available
                sample_inputs = None
                if sample_inputs_dir:
                    input_file = sample_inputs_dir / f"{policy_file.stem}.json"
                    if input_file.exists():
                        import json

                        with open(input_file) as f:
                            sample_inputs = json.load(f)
                        if not isinstance(sample_inputs, list):
                            sample_inputs = [sample_inputs]

                # Load policy
                content, validation = self.load_policy(
                    policy_file, sample_inputs=sample_inputs
                )
                policies[policy_file.name] = (content, validation)

            except PolicyLoadError as e:
                errors.append(f"{policy_file.name}: {str(e)}")
                logger.error(
                    "policy_load_failed",
                    policy_file=str(policy_file),
                    error=str(e),
                )

        # Report errors
        if errors:
            error_msg = f"Failed to load {len(errors)} policies:\n" + "\n".join(
                errors
            )
            raise PolicyLoadError(error_msg)

        logger.info(
            "policy_directory_loaded",
            policy_dir=str(policy_dir),
            policy_count=len(policies),
        )

        return policies

    def deploy_to_opa(
        self,
        policy_content: str,
        policy_name: str,
        opa_bundle_path: Path | None = None,
    ) -> bool:
        """
        Deploy a validated policy to OPA.

        Args:
            policy_content: The validated policy content
            policy_name: Name for the policy
            opa_bundle_path: Optional path to OPA bundle directory

        Returns:
            True if deployment successful

        Raises:
            RuntimeError: If OPA deployment fails
        """
        try:
            if opa_bundle_path:
                # Write to bundle directory
                policy_file = opa_bundle_path / policy_name
                policy_file.parent.mkdir(parents=True, exist_ok=True)
                policy_file.write_text(policy_content)

                logger.info(
                    "policy_deployed_to_bundle",
                    policy_name=policy_name,
                    bundle_path=str(opa_bundle_path),
                )
            else:
                # For now, just write to temp location and verify with OPA
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".rego", delete=False
                ) as tmp_file:
                    tmp_file.write(policy_content)
                    tmp_file.flush()
                    tmp_path = Path(tmp_file.name)

                try:
                    # Verify with OPA
                    result = subprocess.run(
                        [self.opa_path, "check", str(tmp_path)],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )

                    if result.returncode != 0:
                        raise RuntimeError(
                            f"OPA deployment verification failed: {result.stderr}"
                        )

                finally:
                    tmp_path.unlink(missing_ok=True)

                logger.info("policy_deployed_verified", policy_name=policy_name)

            return True

        except Exception as e:
            logger.error(
                "policy_deployment_failed", policy_name=policy_name, error=str(e)
            )
            raise RuntimeError(f"Failed to deploy policy {policy_name}: {str(e)}")

    def _format_validation_errors(
        self, validation_result: ValidationResult, policy_path: Path
    ) -> str:
        """
        Format validation errors into a readable error message.

        Args:
            validation_result: The validation result
            policy_path: Path to the policy file

        Returns:
            Formatted error message
        """
        lines = [f"Policy validation failed for {policy_path.name}:\n"]

        # Group by severity
        critical = validation_result.critical_issues
        high = validation_result.high_issues

        if critical:
            lines.append(f"\n🔴 CRITICAL ISSUES ({len(critical)}):")
            for issue in critical:
                lines.append(f"  - [{issue.code}] {issue.message}")
                if issue.line_number:
                    lines.append(f"    Line {issue.line_number}: {issue.context}")
                if issue.suggestion:
                    lines.append(f"    💡 {issue.suggestion}")

        if high:
            lines.append(f"\n🟠 HIGH SEVERITY ISSUES ({len(high)}):")
            for issue in high:
                lines.append(f"  - [{issue.code}] {issue.message}")
                if issue.line_number:
                    lines.append(f"    Line {issue.line_number}: {issue.context}")
                if issue.suggestion:
                    lines.append(f"    💡 {issue.suggestion}")

        return "\n".join(lines)


def validate_policy_file(policy_path: Path, strict: bool = True) -> ValidationResult:
    """
    Convenience function to validate a policy file.

    Args:
        policy_path: Path to the policy file
        strict: If True, treat HIGH severity issues as failures

    Returns:
        ValidationResult
    """
    validator = PolicyValidator(strict=strict)
    return validator.validate_file(policy_path)


def load_and_validate_policy(
    policy_path: Path,
    sample_inputs: list[dict[str, Any]] | None = None,
    strict: bool = True,
) -> tuple[str, ValidationResult]:
    """
    Convenience function to load and validate a policy.

    Args:
        policy_path: Path to the policy file
        sample_inputs: Optional sample inputs to test
        strict: If True, reject policies with HIGH severity issues

    Returns:
        Tuple of (policy_content, validation_result)

    Raises:
        PolicyLoadError: If validation fails
    """
    loader = PolicyLoader(strict=strict)
    return loader.load_policy(policy_path, sample_inputs=sample_inputs)
