"""Example test file to verify test setup."""

import sark


def test_version() -> None:
    """Test that version is defined."""
    assert hasattr(sark, "__version__")
    assert isinstance(sark.__version__, str)


def test_sample_fixture(sample_fixture: str) -> None:
    """Test that fixtures work correctly."""
    assert sample_fixture == "test_data"
