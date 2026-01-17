"""Rust extension modules for SARK.

This package provides high-performance Rust implementations of
performance-critical SARK components:

- OPA policy engine with regorus
- Thread-safe caching with DashMap

The Rust extensions are optional. If not built, SARK will fall back
to pure-Python implementations where available.
"""

# Try to import Rust extensions
RUST_AVAILABLE = False
RustOPAEngine = None
RustCache = None

try:
    from sark.sark_rust import RustCache, RustOPAEngine

    RUST_AVAILABLE = True
except ImportError as e:
    # Rust extensions not built - this is OK during development
    # or when running from source without building Rust
    import warnings

    warnings.warn(
        f"Rust extensions not available: {e}. "
        "Run 'maturin develop' to build them. "
        "SARK will use pure-Python fallbacks where available.",
        ImportWarning,
        stacklevel=2,
    )

__all__ = ["RUST_AVAILABLE", "RustOPAEngine", "RustCache"]
