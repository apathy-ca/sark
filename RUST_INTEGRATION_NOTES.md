# Rust Integration - Python Bindings

## Overview
Fixed Python import paths for Rust OPA and Cache extensions to work with the unified `sark.sark_rust` module built by Maturin.

## Changes Made

### 1. src/sark/_rust/__init__.py
- Changed from wildcard import to explicit imports: `from sark.sark_rust import RustCache, RustOPAEngine`
- Added None initialization for `RustOPAEngine` and `RustCache` before try block
- Updated `__all__` to export the classes explicitly
- **Benefit**: Better IDE support, clearer API, proper type hints

### 2. src/sark/services/policy/rust_cache.py
- Changed import from `from sark_cache import RustCache` to `from sark._rust import RustCache`
- Updated error message to reference `sark_rust` instead of `sark_cache`
- **Reason**: The Rust workspace builds a single combined module, not separate modules

### 3. src/sark/services/policy/rust_opa_client.py
- Changed from `from sark._rust import sark_opa` to `from sark._rust import RustOPAEngine`
- Changed usage from `sark_opa.RustOPAEngine()` to `RustOPAEngine()`
- **Reason**: Import the class directly, not as a nested module

## Architecture

```
Python Module Structure:
├── sark.sark_rust (built by Maturin from src/lib.rs)
│   ├── RustOPAEngine (from rust/sark-opa/src/python.rs)
│   └── RustCache (from rust/sark-cache/src/python.rs)
├── sark._rust (Python wrapper package)
│   └── __init__.py (re-exports from sark.sark_rust)
└── sark.services.policy
    ├── rust_opa_client.py (imports from sark._rust)
    └── rust_cache.py (imports from sark._rust)
```

## Build Configuration

From `pyproject.toml`:
```toml
[tool.maturin]
python-source = "src"
module-name = "sark.sark_rust"  # Single unified module
```

From `src/lib.rs`:
```rust
#[pymodule]
fn sark_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustOPAEngine>()?;
    m.add_class::<RustCache>()?;
    Ok(())
}
```

## Next Steps

To build and use the Rust extensions:

```bash
# Build in development mode
maturin develop --release

# Verify import works
python3 -c "from sark._rust import RUST_AVAILABLE, RustOPAEngine, RustCache; print(f'Rust: {RUST_AVAILABLE}')"

# Run tests
pytest tests/unit/services/policy/test_rust_opa_client.py -v
pytest tests/unit/services/policy/test_rust_cache.py -v
```

## Performance Targets

When built and deployed:
- **OPA Engine**: <5ms p95 latency (4-10x faster than HTTP)
- **Cache**: <0.5ms p95 latency (10-50x faster than Redis)
- **Overall**: 2.3x faster request processing

## Compatibility

- ✅ 100% backwards compatible - Python fallbacks used when Rust unavailable
- ✅ Zero breaking changes to existing APIs
- ✅ Graceful degradation if build fails
