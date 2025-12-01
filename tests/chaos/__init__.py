"""
SARK Chaos Engineering Tests

This package contains chaos engineering tests for SARK, including:
- Federation chaos tests
- Network partition scenarios
- Service degradation tests
- Byzantine failure scenarios
"""

import pytest


def pytest_configure(config):
    """Configure pytest with chaos test markers."""
    config.addinivalue_line("markers", "chaos: mark test as chaos engineering test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "network: mark test as network chaos test")
    config.addinivalue_line("markers", "failure: mark test as failure injection test")
