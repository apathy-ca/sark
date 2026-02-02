# SARK Rust/PyO3 Integration Guide

**Document Version:** 2.0
**Last Updated:** 2026-02-01
**Audience:** Developers integrating with SARK's Rust components

---

## Overview

SARK includes high-performance Rust components with Python bindings via [PyO3](https://pyo3.rs/). This guide covers:

1. How the Rust/Python integration works
2. How to build and use the Rust extensions
3. How to integrate SARK's Rust components into your own projects
4. Common patterns and gotchas

> **Migration Note (v1.6.0):** SARK now uses **[GRID Core](https://github.com/apathy-ca/grid-core)** as the source for its Rust components. The crates are named `grid-opa` and `grid-cache` and are shared with [YORI](https://github.com/apathy-ca/yori).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Python Application                        │
│                         (SARK)                               │
├─────────────────────────────────────────────────────────────┤
│                   sark._rust module                          │
│          (fallback-aware import wrapper)                     │
├─────────────────────────────────────────────────────────────┤
│                   sark.sark_rust                             │
│              (compiled Python extension)                     │
├──────────────────────┬──────────────────────────────────────┤
│      grid-opa        │           grid-cache                  │
│   (Rust + PyO3)      │         (Rust + PyO3)                │
│   from GRID Core     │         from GRID Core               │
├──────────────────────┼──────────────────────────────────────┤
│      regorus         │           dashmap                     │
│    (OPA engine)      │     (concurrent hashmap)              │
└──────────────────────┴──────────────────────────────────────┘
```

### Key Components

| Component | Purpose | Performance |
|-----------|---------|-------------|
| `grid-opa` | Embedded OPA policy evaluation | 4-10x faster than HTTP OPA |
| `grid-cache` | Thread-safe LRU+TTL cache | 10-50x faster than Redis |

---

## Building the Rust Extensions

### Prerequisites

```bash
# Install Rust (1.92+)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# Install maturin (Rust/Python build tool)
pip install maturin
```

### Development Build

```bash
cd /path/to/sark

# Build in development mode (creates .so in source tree)
maturin develop

# Verify installation
python -c "from sark._rust import RUST_AVAILABLE; print(f'Rust: {RUST_AVAILABLE}')"
# Output: Rust: True
```

### Release Build

```bash
# Build optimized wheel
maturin build --release

# Install the wheel
pip install target/wheels/sark_rust-*.whl
```

---

## Using the Rust Components from Python

### Graceful Fallback Pattern

SARK uses a fallback pattern that allows operation without Rust:

```python
# src/sark/_rust/__init__.py
RUST_AVAILABLE = False
RustOPAEngine = None
RustCache = None

try:
    from sark.sark_rust import RustCache, RustOPAEngine
    RUST_AVAILABLE = True
except ImportError as e:
    import warnings
    warnings.warn(
        f"Rust extensions not available: {e}. "
        "Run 'maturin develop' to build them.",
        ImportWarning,
    )
```

### Using RustOPAEngine

```python
from sark._rust import RustOPAEngine, RUST_AVAILABLE

if RUST_AVAILABLE:
    # Create engine
    engine = RustOPAEngine()

    # Load a Rego policy
    policy = """
    package authz

    default allow := false

    allow {
        input.user == "admin"
    }

    allow {
        input.role == "developer"
        input.action == "read"
    }
    """
    engine.load_policy("authz", policy)

    # Evaluate policy
    result = engine.evaluate(
        "data.authz.allow",
        {"user": "alice", "role": "developer", "action": "read"}
    )
    print(result)  # True

    # List loaded policies
    print(engine.loaded_policies())  # ['authz']

    # Check if policy exists
    print(engine.has_policy("authz"))  # True

    # Clear all policies
    engine.clear_policies()
```

### Using RustCache

```python
from sark._rust import RustCache, RUST_AVAILABLE

if RUST_AVAILABLE:
    # Create cache with 10,000 max entries, 1 hour TTL
    cache = RustCache(max_size=10000, ttl_secs=3600)

    # Store values (string keys and values)
    cache.set("user:alice:permissions", '["read", "write"]')

    # Store with custom TTL (5 minutes)
    cache.set("session:abc123", '{"user": "alice"}', ttl=300)

    # Retrieve values
    value = cache.get("user:alice:permissions")
    if value is not None:
        permissions = json.loads(value)

    # Delete entry
    deleted = cache.delete("session:abc123")  # Returns True if existed

    # Get cache statistics
    print(f"Cache size: {cache.size()}")

    # Manual cleanup of expired entries
    removed = cache.cleanup_expired()
    print(f"Removed {removed} expired entries")

    # Clear entire cache
    cache.clear()
```

---

## PyO3 Integration Patterns

### Module Naming Convention

**Important:** PyO3 module names must match exactly between Rust and Python.

```rust
// Cargo.toml
[lib]
name = "sark_opa"  // Use underscores, not hyphens!
crate-type = ["cdylib", "rlib"]

// src/python.rs
#[pymodule]
fn sark_opa(py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Module name must match [lib].name
    m.add_class::<RustOPAEngine>()?;
    Ok(())
}
```

```python
# Python import must match the module name exactly
from sark_opa import RustOPAEngine  # Works
from sark-opa import RustOPAEngine  # FAILS - hyphens not allowed
```

### Wrapper Module Pattern

For cleaner imports, create a Python wrapper:

```python
# sark/_rust/__init__.py
"""Wrapper for Rust extensions with graceful fallback."""

RUST_AVAILABLE = False
RustOPAEngine = None

try:
    # Import from the compiled extension
    from sark.sark_rust import RustOPAEngine
    RUST_AVAILABLE = True
except ImportError:
    pass

# Now users can do:
# from sark._rust import RustOPAEngine, RUST_AVAILABLE
```

### Error Handling Pattern

Convert Rust errors to Python exceptions:

```rust
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;

// Define custom exceptions
pyo3::create_exception!(sark_opa, OPACompilationError, pyo3::exceptions::PyException);

// Convert Rust errors to Python exceptions
impl From<OPAError> for PyErr {
    fn from(err: OPAError) -> PyErr {
        match err {
            OPAError::CompilationError(msg) => OPACompilationError::new_err(msg),
            OPAError::InvalidInput(msg) => PyValueError::new_err(msg),
            OPAError::InternalError(msg) => PyRuntimeError::new_err(msg),
        }
    }
}

// Use in methods - errors automatically convert
#[pymethods]
impl RustOPAEngine {
    fn evaluate(&mut self, query: String, input: &PyDict) -> PyResult<PyObject> {
        let result = self.inner.evaluate(&query, input)?;  // ? converts to PyErr
        Ok(result)
    }
}
```

### Type Conversion Pattern

Convert between Python dicts and Rust types:

```rust
use pyo3::types::PyDict;
use pythonize::{depythonize, pythonize};

fn evaluate(&mut self, py: Python, query: String, input: &Bound<'_, PyDict>) -> PyResult<PyObject> {
    // Python dict -> serde_json::Value
    let input_json: serde_json::Value = pythonize::depythonize(input.as_any())?;

    // Do Rust processing...
    let result = self.process(input_json)?;

    // serde_json::Value -> Python object
    let result_py = pythonize::pythonize(py, &result)?;
    Ok(result_py.into())
}
```

---

## Workspace Configuration

SARK uses a Cargo workspace to manage multiple crates:

```toml
# Cargo.toml (root)
[workspace]
members = ["rust/sark-opa", "rust/sark-cache"]
resolver = "2"

[workspace.package]
version = "1.3.0"
edition = "2021"
rust-version = "1.92"

[workspace.dependencies]
pyo3 = { version = "0.22", features = ["extension-module", "abi3-py39"] }
pythonize = "0.22"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
regorus = "0.2"
dashmap = "6.1"

# Main crate re-exports all components
[package]
name = "sark-rust"

[lib]
name = "sark_rust"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.22", features = ["extension-module"] }
sark-opa = { path = "rust/sark-opa" }
sark-cache = { path = "rust/sark-cache" }
```

```rust
// src/lib.rs - Main crate re-exports components
use pyo3::prelude::*;
use sark_cache::python::RustCache;
use sark_opa::python::RustOPAEngine;

#[pymodule]
fn sark_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Re-export all Rust components through single module
    m.add_class::<RustOPAEngine>()?;
    m.add_class::<RustCache>()?;
    Ok(())
}
```

---

## Testing Rust Extensions

### Rust Unit Tests

```rust
// rust/sark-opa/src/engine.rs
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_policy_evaluation() {
        let mut engine = OPAEngine::new().unwrap();
        engine.load_policy("test", "package test\nallow = true".to_string()).unwrap();

        let input = Value::Object(Arc::new(BTreeMap::new()));
        let result = engine.evaluate("data.test.allow", input).unwrap();

        assert_eq!(result, Value::Bool(true));
    }
}
```

### Python Integration Tests

```python
# tests/unit/test_rust_extensions.py
import pytest
from sark._rust import RUST_AVAILABLE, RustOPAEngine, RustCache

@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust extensions not built")
class TestRustOPAEngine:
    def test_basic_policy(self):
        engine = RustOPAEngine()
        engine.load_policy("test", "package test\nallow = true")

        result = engine.evaluate("data.test.allow", {})
        assert result is True

    def test_policy_with_input(self):
        engine = RustOPAEngine()
        policy = """
        package authz
        allow { input.user == "admin" }
        """
        engine.load_policy("authz", policy)

        assert engine.evaluate("data.authz.allow", {"user": "admin"}) is True
        assert engine.evaluate("data.authz.allow", {"user": "guest"}) is False

@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust extensions not built")
class TestRustCache:
    def test_basic_operations(self):
        cache = RustCache(max_size=100, ttl_secs=60)

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        assert cache.delete("key1") is True
        assert cache.get("key1") is None
```

---

## Benchmarking

### Rust Benchmarks

```rust
// rust/sark-opa/benches/opa_benchmarks.rs
use criterion::{black_box, criterion_group, criterion_main, Criterion};
use sark_opa::engine::OPAEngine;

fn benchmark_evaluation(c: &mut Criterion) {
    let mut engine = OPAEngine::new().unwrap();
    engine.load_policy("bench", POLICY.to_string()).unwrap();

    c.bench_function("policy_evaluation", |b| {
        b.iter(|| {
            engine.evaluate(black_box("data.bench.allow"), black_box(input.clone()))
        })
    });
}

criterion_group!(benches, benchmark_evaluation);
criterion_main!(benches);
```

```bash
# Run Rust benchmarks
cargo bench -p sark-opa
```

### Python Benchmarks

```python
# tests/performance/test_rust_perf.py
import pytest
from sark._rust import RUST_AVAILABLE, RustOPAEngine

@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust extensions not built")
@pytest.mark.benchmark
def test_rust_opa_performance(benchmark):
    engine = RustOPAEngine()
    engine.load_policy("bench", "package bench\nallow { input.x > 5 }")

    result = benchmark(lambda: engine.evaluate("data.bench.allow", {"x": 10}))
    assert result is True
```

---

## Troubleshooting

### "Module not found" Error

```python
ImportError: cannot import name 'RustOPAEngine' from 'sark.sark_rust'
```

**Solution:** Build the Rust extensions:
```bash
maturin develop
```

### "Symbol not found" Error (macOS)

```
ImportError: dlopen(...): symbol not found
```

**Solution:** Ensure consistent Python version:
```bash
# Check Python version
python --version

# Rebuild with correct Python
maturin develop --interpreter python3.11
```

### Performance Not As Expected

**Checklist:**
1. Built in release mode? `maturin build --release`
2. Using the Rust version? Check `RUST_AVAILABLE`
3. Caching policy objects? Creating new engines is expensive

### Memory Usage Higher Than Expected

The Rust components include:
- regorus OPA engine: ~5-10MB for policy compilation
- dashmap cache: Scales with entries

**Mitigation:**
- Reuse engine instances (don't recreate per request)
- Set appropriate cache size limits
- Call `cleanup_expired()` periodically

---

## See Also

- [Embedded Deployment Guide](EMBEDDED_DEPLOYMENT.md) - Resource-constrained environments
- [Standalone Crates Guide](STANDALONE_CRATES.md) - Using sark-opa/sark-cache independently
- [Cross-Compilation Guide](CROSS_COMPILATION.md) - Building for other platforms
- [PyO3 Documentation](https://pyo3.rs/) - Official PyO3 docs
- [Maturin Documentation](https://www.maturin.rs/) - Build tool docs
