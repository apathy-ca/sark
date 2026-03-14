"""Pytest configuration for policy tests."""

import shutil

import pytest

# Check if OPA binary is available
OPA_AVAILABLE = shutil.which("opa") is not None

# Mark that can be used to skip tests requiring OPA
requires_opa = pytest.mark.skipif(
    not OPA_AVAILABLE, reason="OPA binary not found - install OPA to run these tests"
)
