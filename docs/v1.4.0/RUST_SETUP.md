# Rust Development Setup for SARK v1.4.0

This guide explains how to build and work with SARK's Rust extensions.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Building Rust Extensions](#building-rust-extensions)
3. [Development Workflow](#development-workflow)
4. [Testing](#testing)
5. [Troubleshooting](#troubleshooting)
6. [Architecture](#architecture)

---

## Prerequisites

### Required Tools

- **Python 3.9+** - The main application runtime
- **Rust 1.70+** - For building native extension modules
- **Maturin 1.4+** - Python/Rust build tool

### Installing Rust

#### Linux / macOS

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
```

#### Windows

Download and run [rustup-init.exe](https://rustup.rs/).

### Verifying Installation

```bash
# Check Rust version
rustc --version  # Should be 1.70.0 or higher
cargo --version

# Check Python version
python3 --version  # Should be 3.9.0 or higher
```

The project includes a `rust-toolchain.toml` file that will automatically install
the correct Rust version when you run cargo commands.

---

## Building Rust Extensions

### Quick Start

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install development dependencies (includes maturin)
pip install -e ".[dev]"

# 3. Build and install Rust extensions
maturin develop

# 4. Verify installation
python -c "from sark._rust import RUST_AVAILABLE; print(f'Rust available: {RUST_AVAILABLE}')"
```

### Build Modes

#### Development Build (Fast, Unoptimized)

```bash
maturin develop
```

- Compiles in debug mode (faster compilation)
- Includes debug symbols
- No optimizations
- Best for rapid iteration

#### Release Build (Slow, Optimized)

```bash
maturin develop --release
```

- Compiles with full optimizations
- Strips debug symbols
- Much better runtime performance
- Use for benchmarking

#### Production Wheel

```bash
maturin build --release
```

Creates an optimized wheel in `target/wheels/`

---

## Development Workflow

### Making Changes to Rust Code

1. **Edit Rust source files** in `rust/sark-opa/src/` or `rust/sark-cache/src/`

2. **Rebuild the extension:**
   ```bash
   maturin develop
   ```

3. **Test your changes:**
   ```bash
   python -c "from sark._rust.sark_opa import hello_opa; print(hello_opa())"
   ```

4. **Run tests:**
   ```bash
   cd rust
   cargo test
   ```

### Making Changes to Python Code

Python changes are immediately visible - no rebuild needed.

### Project Structure

```
sark/
├── rust/                      # Rust workspace root
│   ├── Cargo.toml            # Workspace manifest
│   ├── sark-opa/             # OPA engine crate
│   │   ├── Cargo.toml        # Crate manifest
│   │   ├── src/
│   │   │   └── lib.rs        # OPA module implementation
│   │   └── tests/            # Rust tests
│   └── sark-cache/           # Cache engine crate
│       ├── Cargo.toml        # Crate manifest
│       ├── src/
│       │   └── lib.rs        # Cache module implementation
│       └── tests/            # Rust tests
├── src/sark/_rust/           # Python wrapper package
│   ├── __init__.py           # Import wrapper with fallback
│   └── py.typed              # Type hints marker
├── pyproject.toml            # Maturin configuration
└── rust-toolchain.toml       # Rust version pinning
```

### Code Organization

- **rust/sark-opa/** - OPA policy engine using [regorus](https://github.com/microsoft/regorus)
- **rust/sark-cache/** - High-performance caching using [DashMap](https://github.com/xacrimon/dashmap)
- **src/sark/_rust/** - Python import wrapper that gracefully handles missing Rust extensions

---

## Testing

### Running Rust Tests

```bash
# Test all crates
cd rust
cargo test --all

# Test specific crate
cargo test -p sark-opa
cargo test -p sark-cache

# Run tests with output
cargo test -- --nocapture
```

### Running Python Integration Tests

```bash
# Ensure Rust extensions are built
maturin develop

# Run pytest
pytest tests/
```

### Linting and Formatting

```bash
cd rust

# Check code formatting
cargo fmt --all -- --check

# Auto-format code
cargo fmt --all

# Run clippy (Rust linter)
cargo clippy --all-targets --all-features -- -D warnings
```

### Pre-commit Checks

The CI pipeline runs:
1. `cargo test --all`
2. `cargo clippy -- -D warnings`
3. `cargo fmt --check`
4. `maturin build`
5. Python import tests

Run these locally before pushing:

```bash
cd rust
cargo test --all
cargo clippy --all-targets --all-features -- -D warnings
cargo fmt --all -- --check
cd ..
maturin build --release
```

---

## Troubleshooting

### Common Issues

#### "Rust not found" or "rustc: command not found"

**Solution:**
```bash
# Ensure Rust is in PATH
source $HOME/.cargo/env

# Or reinstall Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

#### "maturin: command not found"

**Solution:**
```bash
pip install maturin
# Or
pip install -e ".[dev]"
```

#### "error: failed to compile sark"

**Possible causes:**

1. **Wrong Rust version:**
   ```bash
   rustc --version  # Must be 1.70+
   rustup update
   ```

2. **Outdated dependencies:**
   ```bash
   cd rust
   cargo clean
   cargo update
   ```

3. **Corrupted build cache:**
   ```bash
   cd rust
   cargo clean
   cd ..
   rm -rf target/
   maturin develop
   ```

#### "ModuleNotFoundError: No module named 'sark._rust'"

**Possible causes:**

1. **Rust extensions not built:**
   ```bash
   maturin develop
   ```

2. **Wrong virtual environment:**
   ```bash
   which python  # Verify you're in the correct venv
   ```

3. **Build failed silently:**
   ```bash
   maturin develop --verbose
   ```

#### Import works but functions fail with "undefined symbol"

**Solution:**
Rebuild with matching Python version:
```bash
maturin develop --interpreter python3.11
```

#### Performance is slower than expected

**Solution:**
Ensure you're using a release build:
```bash
maturin develop --release
```

### Getting Help

1. Check `maturin develop --verbose` output for detailed errors
2. Review the CI logs in `.github/workflows/rust.yml`
3. Consult [PyO3 docs](https://pyo3.rs/) for binding issues
4. Consult [Maturin docs](https://www.maturin.rs/) for build issues

---

## Architecture

### Build System

SARK uses a **hybrid Python/Rust architecture**:

- **Maturin** - Build backend that bridges Cargo and Python packaging
- **PyO3** - Rust ↔ Python interop library
- **Cargo Workspace** - Manages multiple Rust crates

### Module Loading

```python
# src/sark/_rust/__init__.py
try:
    from sark._rust.sark_opa import *
    from sark._rust.sark_cache import *
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    # Graceful degradation to pure Python
```

This allows SARK to run without Rust extensions (useful for development or
platforms where Rust toolchain is unavailable).

### Performance Targets

The Rust extensions provide significant performance improvements:

- **OPA Policy Evaluation**: ~100x faster than Python OPA implementations
- **Cache Operations**: Lock-free concurrent access using DashMap
- **Serialization**: Zero-copy where possible using PyO3

### Dependencies

#### Core Dependencies

- **pyo3** (0.21) - Python bindings
- **serde** (1.0) - Serialization framework
- **serde_json** (1.0) - JSON support

#### OPA Module (`sark-opa`)

- **regorus** (0.1) - Rust implementation of OPA/Rego
- **parking_lot** (0.12) - High-performance locks

#### Cache Module (`sark-cache`)

- **dashmap** (5.5) - Concurrent hash map
- **parking_lot** (0.12) - High-performance locks

### Extension Points

To add new Rust functionality:

1. **Create a new crate** (or extend existing):
   ```bash
   cd rust
   cargo new --lib my-feature
   ```

2. **Add to workspace** in `rust/Cargo.toml`:
   ```toml
   members = ["sark-opa", "sark-cache", "my-feature"]
   ```

3. **Add PyO3 bindings** in `lib.rs`:
   ```rust
   use pyo3::prelude::*;

   #[pyfunction]
   fn my_function() -> PyResult<String> {
       Ok("Hello!".to_string())
   }

   #[pymodule]
   fn my_feature(m: &Bound<'_, PyModule>) -> PyResult<()> {
       m.add_function(wrap_pyfunction!(my_function, m)?)?;
       Ok(())
   }
   ```

4. **Rebuild and test**:
   ```bash
   maturin develop
   python -c "from sark._rust.my_feature import my_function; print(my_function())"
   ```

---

## CI/CD Integration

The GitHub Actions workflow (`.github/workflows/rust.yml`) runs:

1. **Rust Tests** - `cargo test --all`
2. **Clippy Lints** - `cargo clippy -- -D warnings`
3. **Format Check** - `cargo fmt --check`
4. **Maturin Build** - Cross-platform wheel building
5. **Python Import Tests** - Verify extensions load correctly

Wheels are built for:
- Python 3.9, 3.10, 3.11, 3.12
- Linux, macOS, Windows

---

## Performance Benchmarking

```python
import time
from sark._rust import RUST_AVAILABLE

if RUST_AVAILABLE:
    from sark._rust.sark_cache import hello_cache

    iterations = 1_000_000
    start = time.perf_counter()
    for _ in range(iterations):
        hello_cache()
    duration = time.perf_counter() - start

    print(f"{iterations:,} calls in {duration:.3f}s")
    print(f"Average: {duration/iterations*1_000_000:.2f} µs/call")
```

---

## References

- [PyO3 User Guide](https://pyo3.rs/)
- [Maturin Documentation](https://www.maturin.rs/)
- [Rust Book](https://doc.rust-lang.org/book/)
- [Cargo Workspaces](https://doc.rust-lang.org/book/ch14-03-cargo-workspaces.html)
- [Regorus (OPA in Rust)](https://github.com/microsoft/regorus)
- [DashMap Documentation](https://docs.rs/dashmap/)

---

## Next Steps

1. ✅ Verify Rust extensions build successfully
2. ✅ Run the test suite
3. 🚀 Start implementing performance-critical features in Rust
4. 📊 Benchmark improvements
5. 📚 Expand Rust module documentation

---

**Questions?** Check the [troubleshooting section](#troubleshooting) or open an issue.
