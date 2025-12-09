"""Unit tests for policy loader."""

from pathlib import Path

import pytest

from sark.policy.loader import (
    PolicyLoadError,
    PolicyLoader,
    load_and_validate_policy,
    validate_policy_file,
)
from sark.policy.validator import PolicyValidator, Severity


class TestPolicyLoader:
    """Test PolicyLoader class."""

    @pytest.fixture
    def loader(self):
        """Create a PolicyLoader instance."""
        return PolicyLoader(strict=True, auto_validate=True)

    @pytest.fixture
    def lenient_loader(self):
        """Create a lenient PolicyLoader instance."""
        return PolicyLoader(strict=False, auto_validate=True)

    @pytest.fixture
    def no_validate_loader(self):
        """Create a loader without auto-validation."""
        return PolicyLoader(auto_validate=False)

    @pytest.fixture
    def valid_policy(self, tmp_path):
        """Create a valid policy file."""
        policy = """
package test.valid

import future.keywords.if

default allow := false

allow if {
    input.user.role == "admin"
}

reason := "Admin access" if { allow }
reason := "Access denied" if { not allow }
"""
        policy_file = tmp_path / "valid.rego"
        policy_file.write_text(policy)
        return policy_file

    @pytest.fixture
    def invalid_policy(self, tmp_path):
        """Create an invalid policy file with forbidden patterns."""
        policy = """
package test.invalid

default allow := true

# This should fail validation
"""
        policy_file = tmp_path / "invalid.rego"
        policy_file.write_text(policy)
        return policy_file

    def test_loader_initialization(self):
        """Test loader can be initialized."""
        loader = PolicyLoader()
        assert loader.strict is True
        assert loader.auto_validate is True
        assert isinstance(loader.validator, PolicyValidator)

        loader2 = PolicyLoader(strict=False, auto_validate=False)
        assert loader2.strict is False
        assert loader2.auto_validate is False

    def test_load_valid_policy(self, loader, valid_policy):
        """Test loading a valid policy."""
        content, validation = loader.load_policy(valid_policy)

        assert isinstance(content, str)
        assert "package test.valid" in content
        assert validation is not None
        assert validation.valid is True
        assert validation.package_name == "test.valid"

    def test_load_invalid_policy_strict(self, loader, invalid_policy):
        """Test loading an invalid policy in strict mode."""
        with pytest.raises(PolicyLoadError) as exc_info:
            loader.load_policy(invalid_policy)

        error = exc_info.value
        assert error.validation_result is not None
        assert not error.validation_result.valid

    def test_load_invalid_policy_force(self, loader, invalid_policy):
        """Test force-loading an invalid policy."""
        content, validation = loader.load_policy(invalid_policy, force=True)

        assert isinstance(content, str)
        assert validation is not None
        assert validation.valid is False

    def test_load_policy_no_validation(self, no_validate_loader, valid_policy):
        """Test loading policy without validation."""
        content, validation = no_validate_loader.load_policy(valid_policy)

        assert isinstance(content, str)
        assert validation is None  # No validation performed

    def test_load_policy_file_not_found(self, loader):
        """Test loading a non-existent policy file."""
        with pytest.raises(FileNotFoundError):
            loader.load_policy(Path("/nonexistent/policy.rego"))

    def test_load_policy_with_sample_inputs(self, loader, tmp_path):
        """Test loading policy with sample inputs."""
        policy = """
package test.sample

import future.keywords.if

default allow := false

allow if {
    input.user.role == "admin"
}

reason := "test" if { true }
"""
        policy_file = tmp_path / "sample.rego"
        policy_file.write_text(policy)

        sample_inputs = [
            {"user": {"role": "admin"}},
            {"user": {"role": "user"}},
        ]

        content, validation = loader.load_policy(
            policy_file, sample_inputs=sample_inputs
        )

        assert validation is not None
        assert validation.valid is True

    def test_load_policy_directory(self, loader, tmp_path):
        """Test loading all policies from a directory."""
        # Create multiple policy files
        policy1 = """
package test.one

import future.keywords.if

default allow := false
allow if { input.valid }
reason := "test" if { true }
"""
        (tmp_path / "one.rego").write_text(policy1)

        policy2 = """
package test.two

import future.keywords.if

default allow := false
allow if { input.valid }
reason := "test" if { true }
"""
        (tmp_path / "two.rego").write_text(policy2)

        policies = loader.load_policy_directory(tmp_path)

        assert len(policies) == 2
        assert "one.rego" in policies
        assert "two.rego" in policies

        # Check each policy was loaded
        for name, (content, validation) in policies.items():
            assert isinstance(content, str)
            assert validation is not None
            assert validation.valid is True

    def test_load_policy_directory_recursive(self, loader, tmp_path):
        """Test loading policies recursively from subdirectories."""
        # Create nested structure
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        policy1 = """
package test.main

import future.keywords.if

default allow := false
allow if { true }
reason := "test" if { true }
"""
        (tmp_path / "main.rego").write_text(policy1)

        policy2 = """
package test.sub

import future.keywords.if

default allow := false
allow if { true }
reason := "test" if { true }
"""
        (subdir / "sub.rego").write_text(policy2)

        policies = loader.load_policy_directory(tmp_path, recursive=True)

        assert len(policies) == 2
        assert "main.rego" in policies
        assert "sub.rego" in policies

    def test_load_policy_directory_non_recursive(self, loader, tmp_path):
        """Test loading policies without recursion."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        policy1 = """
package test.main

import future.keywords.if

default allow := false
allow if { true }
reason := "test" if { true }
"""
        (tmp_path / "main.rego").write_text(policy1)

        policy2 = """
package test.sub

import future.keywords.if

default allow := false
allow if { true }
reason := "test" if { true }
"""
        (subdir / "sub.rego").write_text(policy2)

        policies = loader.load_policy_directory(tmp_path, recursive=False)

        # Only load from top level
        assert len(policies) == 1
        assert "main.rego" in policies

    def test_load_policy_directory_with_failures(self, loader, tmp_path):
        """Test loading directory with some invalid policies."""
        # Valid policy
        policy1 = """
package test.valid

import future.keywords.if

default allow := false
allow if { true }
reason := "test" if { true }
"""
        (tmp_path / "valid.rego").write_text(policy1)

        # Invalid policy (blanket allow)
        policy2 = """
package test.invalid

default allow := true
"""
        (tmp_path / "invalid.rego").write_text(policy2)

        with pytest.raises(PolicyLoadError) as exc_info:
            loader.load_policy_directory(tmp_path)

        # Error message should mention failures
        assert "Failed to load" in str(exc_info.value)

    def test_load_policy_directory_not_found(self, loader):
        """Test loading from non-existent directory."""
        with pytest.raises(FileNotFoundError):
            loader.load_policy_directory(Path("/nonexistent"))

    def test_deploy_to_opa_bundle(self, loader, tmp_path):
        """Test deploying policy to OPA bundle."""
        policy_content = """
package test.deploy

import future.keywords.if

default allow := false
allow if { true }
reason := "test" if { true }
"""
        bundle_path = tmp_path / "bundle"
        bundle_path.mkdir()

        result = loader.deploy_to_opa(
            policy_content,
            policy_name="deploy.rego",
            opa_bundle_path=bundle_path,
        )

        assert result is True
        assert (bundle_path / "deploy.rego").exists()
        assert (bundle_path / "deploy.rego").read_text() == policy_content

    def test_deploy_to_opa_verification(self, loader):
        """Test deploying policy with OPA verification."""
        policy_content = """
package test.verify

import future.keywords.if

default allow := false
allow if { true }
reason := "test" if { true }
"""
        # Deploy without bundle path (just verify)
        result = loader.deploy_to_opa(
            policy_content,
            policy_name="verify.rego",
        )

        assert result is True

    def test_deploy_to_opa_invalid_policy(self, loader):
        """Test deploying invalid policy fails."""
        policy_content = """
package test.invalid

# Syntax error - missing closing brace
allow if {
    true
"""
        with pytest.raises(RuntimeError, match="deployment verification failed"):
            loader.deploy_to_opa(policy_content, policy_name="invalid.rego")

    def test_format_validation_errors(self, loader, invalid_policy):
        """Test error message formatting."""
        try:
            loader.load_policy(invalid_policy)
        except PolicyLoadError as e:
            error_msg = str(e)

            # Error message should be formatted nicely
            assert "Policy validation failed" in error_msg
            assert "CRITICAL" in error_msg or "HIGH" in error_msg

    def test_lenient_mode_allows_medium_severity(self, lenient_loader, tmp_path):
        """Test lenient mode allows MEDIUM severity issues."""
        policy = """
package test.lenient

import future.keywords.if

default allow := false

allow if {
    trace("Debug message")  # MEDIUM severity
    true
}

reason := "test" if { true }
"""
        policy_file = tmp_path / "lenient.rego"
        policy_file.write_text(policy)

        # Should not raise in lenient mode
        content, validation = lenient_loader.load_policy(policy_file)

        assert validation is not None
        assert validation.valid is True  # No CRITICAL/HIGH issues

    def test_strict_mode_rejects_medium_severity(self, loader, tmp_path):
        """Test strict mode rejects MEDIUM severity issues."""
        policy = """
package test.strict

import future.keywords.if

default allow := false

allow if {
    trace("Debug message")  # MEDIUM severity
    true
}

reason := "test" if { true }
"""
        policy_file = tmp_path / "strict.rego"
        policy_file.write_text(policy)

        # Should raise in strict mode
        with pytest.raises(PolicyLoadError):
            loader.load_policy(policy_file)


class TestConvenienceFunctions:
    """Test convenience functions."""

    @pytest.fixture
    def valid_policy(self, tmp_path):
        """Create a valid policy file."""
        policy = """
package test.convenience

import future.keywords.if

default allow := false
allow if { input.valid }
reason := "test" if { true }
"""
        policy_file = tmp_path / "convenience.rego"
        policy_file.write_text(policy)
        return policy_file

    def test_validate_policy_file(self, valid_policy):
        """Test validate_policy_file convenience function."""
        result = validate_policy_file(valid_policy, strict=True)

        assert result.valid is True
        assert result.policy_name == "convenience.rego"

    def test_load_and_validate_policy(self, valid_policy):
        """Test load_and_validate_policy convenience function."""
        content, validation = load_and_validate_policy(valid_policy, strict=True)

        assert isinstance(content, str)
        assert validation is not None
        assert validation.valid is True

    def test_load_and_validate_policy_with_samples(self, valid_policy):
        """Test load_and_validate_policy with sample inputs."""
        sample_inputs = [{"valid": True}, {"valid": False}]

        content, validation = load_and_validate_policy(
            valid_policy, sample_inputs=sample_inputs, strict=True
        )

        assert validation is not None
        assert validation.valid is True
