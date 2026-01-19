# Developer Guide: Rust Components

This guide explains how to build, test, and contribute to SARK's Rust components introduced in v1.4.0.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Project Structure](#project-structure)
3. [Development Workflow](#development-workflow)
4. [Building from Source](#building-from-source)
5. [Testing](#testing)
6. [Debugging](#debugging)
7. [Performance Profiling](#performance-profiling)
8. [Contributing](#contributing)
9. [Common Issues](#common-issues)

---

## Getting Started

### Prerequisites

**Required:**
- **Rust:** 1.70 or later
- **Python:** 3.11 or later
- **Maturin:** 1.0 or later (for building Python extensions)
- **Git:** For version control

**Optional:**
- **rust-analyzer:** For IDE support
- **cargo-flamegraph:** For performance profiling
- **valgrind:** For memory leak detection

### Installing Rust

**Linux/macOS:**
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# Verify installation
rustc --version  # Should be 1.70+
cargo --version
```

**Windows:**
1. Download from https://rustup.rs/
2. Run installer
3. Follow prompts
4. Verify in Command Prompt:
   ```cmd
   rustc --version
   cargo --version
   ```

### Installing Maturin

```bash
# Using pip
pip install maturin

# Or using cargo
cargo install maturin

# Verify
maturin --version
```

### Cloning the Repository

```bash
git clone https://github.com/anthropics/sark.git
cd sark
git checkout v1.4.0
```

---

## Project Structure

### Repository Layout

```
sark/
├── rust/                      # Rust workspace root
│   ├── Cargo.toml            # Workspace manifest
│   ├── sark-opa/             # OPA engine crate
│   │   ├── Cargo.toml        # Crate manifest
│   │   ├── src/
│   │   │   ├── lib.rs        # PyO3 module entry
│   │   │   ├── engine.rs     # OPA engine implementation
│   │   │   ├── policy.rs     # Policy management
│   │   │   └── error.rs      # Error types
│   │   └── tests/
│   │       ├── engine_tests.rs
│   │       └── integration_tests.rs
│   └── sark-cache/           # Cache engine crate
│       ├── Cargo.toml
│       ├── src/
│       │   ├── lib.rs        # PyO3 module entry
│       │   ├── cache.rs      # Cache implementation
│       │   ├── lru.rs        # LRU eviction
│       │   ├── ttl.rs        # TTL expiration
│       │   └── error.rs      # Error types
│       └── tests/
│           ├── cache_tests.rs
│           └── benchmark.rs
├── src/                       # Python source code
│   └── sark/
│       ├── policy/
│       │   └── rust_engine.py  # Python wrapper for Rust OPA
│       └── services/
│           └── cache/
│               └── rust_cache.py  # Python wrapper for Rust cache
├── tests/                     # Python tests
│   ├── unit/
│   │   └── policy/
│   │       └── test_rust_opa.py
│   ├── integration/
│   │   └── cache/
│   │       └── test_rust_cache.py
│   └── performance/
│       ├── bench_opa.py
│       └── bench_cache.py
└── pyproject.toml             # Python project + maturin config
```

### Rust Workspace Structure

The `rust/` directory is a Cargo workspace containing multiple crates:

**rust/Cargo.toml (workspace):**
```toml
[workspace]
members = [
    "sark-opa",
    "sark-cache",
]

[workspace.dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
anyhow = "1.0"

[profile.release]
opt-level = 3          # Maximum optimization
lto = true             # Link-time optimization
codegen-units = 1      # Better optimization, slower build
strip = true           # Remove debug symbols
```

**rust/sark-opa/Cargo.toml:**
```toml
[package]
name = "sark-opa"
version = "0.1.0"
edition = "2021"

[lib]
name = "sark_opa"
crate-type = ["cdylib"]  # Dynamic library for Python

[dependencies]
pyo3 = { workspace = true }
regorus = "0.1"
serde = { workspace = true }
serde_json = { workspace = true }
anyhow = { workspace = true }

[dev-dependencies]
tokio-test = "0.4"
```

**rust/sark-cache/Cargo.toml:**
```toml
[package]
name = "sark-cache"
version = "0.1.0"
edition = "2021"

[lib]
name = "sark_cache"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { workspace = true }
dashmap = "5.5"
parking_lot = "0.12"
tokio = { version = "1.35", features = ["rt", "time"] }
serde = { workspace = true }
anyhow = { workspace = true }
```

---

## Development Workflow

### 1. Make Changes

#### Editing Rust Code

```bash
# Edit Rust source files
vim rust/sark-opa/src/engine.rs

# Check syntax and types
cd rust
cargo check

# Run clippy for lints
cargo clippy -- -D warnings

# Format code
cargo fmt
```

#### Code Style

Follow Rust standard style:
- Use `cargo fmt` for formatting
- Pass `cargo clippy` with no warnings
- Use descriptive names
- Add doc comments for public APIs

**Example:**
```rust
/// Evaluates an OPA policy against input data
///
/// # Arguments
///
/// * `policy_name` - Name of the policy to evaluate
/// * `input` - Input data as JSON value
///
/// # Returns
///
/// Result containing evaluation output or error
///
/// # Example
///
/// ```
/// let result = engine.evaluate("authz", input)?;
/// ```
pub fn evaluate(
    &self,
    policy_name: &str,
    input: &Value
) -> Result<Value> {
    // Implementation
}
```

### 2. Build and Test

#### Building Rust

```bash
# Development build (fast, unoptimized)
cd rust
cargo build

# Release build (slow, optimized)
cargo build --release

# Build specific crate
cargo build -p sark-opa
cargo build -p sark-cache
```

#### Running Rust Tests

```bash
# Run all tests
cargo test

# Run specific crate tests
cargo test -p sark-opa

# Run specific test
cargo test test_policy_evaluation

# Run with output
cargo test -- --nocapture

# Run benchmarks
cargo bench
```

### 3. Build Python Extension

```bash
# Build and install in development mode
maturin develop

# Build release version
maturin develop --release

# Build wheel
maturin build --release
```

### 4. Test Python Integration

```bash
# Run Python tests
pytest tests/unit/policy/
pytest tests/integration/cache/

# Run performance tests
pytest tests/performance/bench_opa.py -v
pytest tests/performance/bench_cache.py -v

# Run specific test
pytest tests/unit/policy/test_rust_opa.py::test_policy_evaluation -v
```

### 5. Complete Development Cycle

```bash
# Full development cycle script
#!/bin/bash

# 1. Format and lint Rust
cd rust
cargo fmt
cargo clippy -- -D warnings

# 2. Run Rust tests
cargo test

# 3. Build release extension
cd ..
maturin develop --release

# 4. Run Python tests
pytest tests/ -v

# 5. Run performance benchmarks
pytest tests/performance/ --benchmark-only

echo "✅ All checks passed!"
```

---

## Building from Source

### Quick Build

```bash
# Clone repository
git clone https://github.com/anthropics/sark.git
cd sark
git checkout v1.4.0

# Install Rust dependencies and build
cd rust && cargo build --release && cd ..

# Build Python extension
maturin develop --release

# Install Python package
pip install -e .

# Verify
python -c "from sark._rust import RUST_AVAILABLE; print(f'Rust: {RUST_AVAILABLE}')"
```

### Detailed Build Steps

#### 1. Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y build-essential pkg-config libssl-dev
```

**macOS:**
```bash
# Install Xcode Command Line Tools
xcode-select --install

# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Windows:**
```cmd
# Install Visual Studio Build Tools
# Download from: https://visualstudio.microsoft.com/downloads/
# Select "Desktop development with C++"
```

#### 2. Setup Python Environment

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install maturin
pip install maturin
```

#### 3. Build Rust Components

```bash
cd rust

# Build all crates
cargo build --release

# Run tests
cargo test --release

# Check for issues
cargo clippy --release -- -D warnings

cd ..
```

#### 4. Build Python Extension

```bash
# Development build (faster, for iteration)
maturin develop

# Release build (optimized, for production)
maturin develop --release

# Build wheel for distribution
maturin build --release --out dist/
```

#### 5. Install SARK

```bash
# Development installation (editable)
pip install -e ".[dev]"

# Or install wheel
pip install dist/sark-1.4.0-*.whl
```

#### 6. Verify Installation

```bash
# Check Rust availability
python -c "
from sark._rust import RUST_AVAILABLE
print(f'Rust available: {RUST_AVAILABLE}')
"

# Run health check
sark health-check --rust

# Expected output:
# ✅ Rust OPA: Available
# ✅ Rust Cache: Available
```

---

## Testing

### Rust Unit Tests

```bash
cd rust

# Run all tests
cargo test

# Run with output
cargo test -- --show-output

# Run specific test
cargo test test_cache_expiration

# Run tests in specific file
cargo test --test engine_tests
```

**Example test:**
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_policy_evaluation() {
        let mut engine = OPAEngine::new().unwrap();

        let rego = r#"
            package test
            allow = true
        "#;

        engine.load_policy("test", rego).unwrap();

        let input = json!({});
        let result = engine.evaluate("test", &input).unwrap();

        assert_eq!(result["allow"], json!(true));
    }

    #[test]
    fn test_cache_expiration() {
        let cache = Cache::new(1000, Duration::from_secs(1));

        cache.set("key", "value", None);
        assert_eq!(cache.get("key"), Some("value".to_string()));

        // Wait for expiration
        std::thread::sleep(Duration::from_secs(2));
        assert_eq!(cache.get("key"), None);
    }
}
```

### Python Integration Tests

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run specific test file
pytest tests/integration/policy/test_rust_opa.py -v

# Run with coverage
pytest tests/integration/ --cov=sark --cov-report=html
```

**Example integration test:**
```python
import pytest
from sark.policy import OPAClient
from sark._rust import RUST_AVAILABLE

@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust not available")
def test_rust_opa_evaluation():
    """Test Rust OPA engine evaluates policies correctly"""
    client = OPAClient(use_rust=True)

    policy = """
    package test
    allow {
        input.user == "admin"
    }
    """

    # Load policy
    client.load_policy("test", policy)

    # Test admin user
    result = client.evaluate("test", {"user": "admin"})
    assert result["allow"] == True

    # Test non-admin user
    result = client.evaluate("test", {"user": "guest"})
    assert result["allow"] == False

def test_fallback_on_rust_error():
    """Test automatic fallback to Python when Rust fails"""
    client = OPAClient(use_rust=True)

    # Trigger Rust error (invalid policy)
    with pytest.raises(PolicyError):
        client.load_policy("bad", "invalid rego {{{")

    # Should fall back and succeed with valid policy
    client.load_policy("good", "package test\nallow = true")
    result = client.evaluate("good", {})
    assert result["allow"] == True
```

### Performance Tests

```bash
# Run benchmarks
pytest tests/performance/ --benchmark-only

# Compare implementations
pytest tests/performance/bench_opa.py --benchmark-compare
```

**Example benchmark:**
```python
import pytest
from sark.policy import OPAClient

@pytest.fixture
def policy():
    return """
    package test
    allow {
        input.roles[_] == "admin"
    }
    """

@pytest.fixture
def input_data():
    return {"roles": ["user", "developer", "admin"]}

def test_rust_opa_performance(benchmark, policy, input_data):
    """Benchmark Rust OPA evaluation"""
    client = OPAClient(use_rust=True)
    client.load_policy("test", policy)

    result = benchmark(client.evaluate, "test", input_data)
    assert result["allow"] == True

def test_python_opa_performance(benchmark, policy, input_data):
    """Benchmark Python OPA evaluation"""
    client = OPAClient(use_rust=False)
    client.load_policy("test", policy)

    result = benchmark(client.evaluate, "test", input_data)
    assert result["allow"] == True
```

---

## Debugging

### Rust Debugging

#### Print Debugging

```rust
// Use eprintln! for debug output (goes to stderr)
eprintln!("Debug: value = {:?}", value);

// Use dbg! macro
dbg!(&my_variable);

// Conditional debug output
#[cfg(debug_assertions)]
eprintln!("Debug mode: {}", info);
```

#### Using GDB/LLDB

```bash
# Build with debug symbols
cargo build

# Debug with rust-gdb
rust-gdb target/debug/sark-opa

# Or rust-lldb on macOS
rust-lldb target/debug/sark-opa

# Common GDB commands:
# b main           - Set breakpoint at main
# r                - Run program
# n                - Next line
# s                - Step into
# p variable       - Print variable
# bt               - Backtrace
# c                - Continue
```

#### Logging

```rust
// Add env_logger for better logging
use log::{debug, info, warn, error};

fn evaluate(&self, policy: &str, input: &Value) -> Result<Value> {
    info!("Evaluating policy: {}", policy);
    debug!("Input: {:?}", input);

    let result = self.engine.eval(policy, input);

    match &result {
        Ok(output) => debug!("Output: {:?}", output),
        Err(e) => error!("Evaluation failed: {}", e),
    }

    result
}
```

### Python-Rust Boundary Debugging

#### Check Exceptions

```python
import traceback
from sark._rust import RustOPAEngine

try:
    engine = RustOPAEngine()
    result = engine.evaluate("test", input_data)
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()

    # Check error type
    print(f"Type: {type(e)}")

    # Check if it's a Rust error
    if hasattr(e, '__cause__'):
        print(f"Cause: {e.__cause__}")
```

#### Memory Leak Detection

**Using Valgrind (Linux):**
```bash
# Build with debug symbols
cargo build

# Run under valgrind
valgrind --leak-check=full \
         --show-leak-kinds=all \
         python -c "from sark._rust import RustOPAEngine; e = RustOPAEngine()"

# Look for "definitely lost" or "possibly lost" blocks
```

**Using Miri (Rust):**
```bash
# Install miri
rustup +nightly component add miri

# Run tests under miri
cd rust
cargo +nightly miri test
```

### Common Debugging Scenarios

**Scenario: Rust function not visible in Python**

```python
# Check if module imported
from sark import _rust
print(dir(_rust))  # Should show your functions

# Check if Rust is available
from sark._rust import RUST_AVAILABLE
print(f"Rust available: {RUST_AVAILABLE}")

# Try importing directly
try:
    from sark._rust import RustOPAEngine
    print("✅ RustOPAEngine imported")
except ImportError as e:
    print(f"❌ Import failed: {e}")
```

**Scenario: Performance worse than expected**

```rust
// Add timing
use std::time::Instant;

let start = Instant::now();
let result = heavy_operation();
let duration = start.elapsed();

eprintln!("Operation took: {:?}", duration);
```

---

## Performance Profiling

### Rust Profiling

#### Using cargo-flamegraph

```bash
# Install
cargo install flamegraph

# Profile your code
cd rust
cargo flamegraph --bin your_benchmark

# Opens flamegraph.svg in browser
```

#### Using perf (Linux)

```bash
# Record
perf record -g ./target/release/your_binary

# Report
perf report

# Generate flamegraph
perf script | stackcollapse-perf.pl | flamegraph.pl > flamegraph.svg
```

#### Using Instruments (macOS)

```bash
# Build with symbols
cargo build --release

# Profile with Instruments
instruments -t "Time Profiler" ./target/release/your_binary
```

### Python Profiling

```bash
# Install py-spy
pip install py-spy

# Profile running process
py-spy record -o profile.svg -- python your_script.py

# Top view
py-spy top -- python your_script.py
```

### Benchmarking

```bash
# Rust benchmarks
cd rust
cargo bench

# Python benchmarks
pytest tests/performance/ --benchmark-only --benchmark-save=baseline

# Compare with baseline
pytest tests/performance/ --benchmark-only --benchmark-compare=baseline
```

---

## Contributing

### Code Style

**Rust:**
- Follow Rust standard style (`cargo fmt`)
- Pass all clippy lints (`cargo clippy`)
- Write doc comments for public APIs
- Add tests for new functionality
- Use meaningful variable names

**Python:**
- Follow PEP 8
- Use type hints
- Write docstrings
- Add tests for new features
- Keep functions focused and small

### Pull Request Process

1. **Fork the repository**
   ```bash
   # On GitHub, click "Fork"
   git clone https://github.com/YOUR_USERNAME/sark.git
   cd sark
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feat/my-awesome-feature
   ```

3. **Make your changes**
   - Write code
   - Add tests
   - Update documentation

4. **Run tests**
   ```bash
   # Rust tests
   cd rust && cargo test && cd ..

   # Python tests
   pytest tests/ -v

   # Linting
   cargo clippy -- -D warnings
   flake8 src/
   ```

5. **Commit changes**
   ```bash
   git add .
   git commit -m "feat: Add awesome feature

   - Implement feature X
   - Add tests for X
   - Update documentation"
   ```

6. **Push and create PR**
   ```bash
   git push origin feat/my-awesome-feature
   # On GitHub, create Pull Request
   ```

7. **Address review feedback**
   - Make requested changes
   - Push new commits
   - Re-request review

### Commit Message Format

```
type: Short description (50 chars max)

Longer description explaining what and why (72 chars per line)

- Bullet points for details
- Reference issues: #123
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `refactor`: Code refactoring
- `test`: Adding tests
- `perf`: Performance improvement
- `chore`: Maintenance tasks

---

## Common Issues

### Issue: Rust not compiling

**Symptoms:**
```
error: failed to compile sark-opa
```

**Solutions:**

1. **Update Rust:**
   ```bash
   rustup update
   rustc --version  # Should be 1.70+
   ```

2. **Clean and rebuild:**
   ```bash
   cd rust
   cargo clean
   cargo build
   ```

3. **Check dependencies:**
   ```bash
   cargo update
   ```

### Issue: PyO3 errors

**Symptoms:**
```
ImportError: cannot import name 'RustOPAEngine'
```

**Solutions:**

1. **Rebuild extension:**
   ```bash
   maturin develop --release
   ```

2. **Check Python version:**
   ```bash
   python --version  # Should be 3.11+
   ```

3. **Verify maturin config:**
   ```bash
   cat pyproject.toml | grep maturin
   ```

### Issue: Slow compile times

**Solutions:**

1. **Use incremental compilation:**
   ```toml
   # Cargo.toml
   [profile.dev]
   incremental = true
   ```

2. **Use sccache:**
   ```bash
   cargo install sccache
   export RUSTC_WRAPPER=sccache
   ```

3. **Reduce optimization in dev:**
   ```bash
   cargo build  # Don't use --release for development
   ```

4. **Use `cargo check` for quick checks:**
   ```bash
   cargo check  # Faster than cargo build
   ```

### Issue: Tests failing

**Symptoms:**
```
test result: FAILED. 5 passed; 3 failed
```

**Solutions:**

1. **Run specific test:**
   ```bash
   cargo test failing_test_name -- --nocapture
   ```

2. **Check test output:**
   ```bash
   cargo test -- --show-output
   ```

3. **Update test expectations:**
   ```bash
   # Review test and update assertions if behavior changed
   ```

---

## Resources

### Documentation

- **Rust Book:** https://doc.rust-lang.org/book/
- **PyO3 Guide:** https://pyo3.rs/
- **Cargo Book:** https://doc.rust-lang.org/cargo/
- **Regorus:** https://github.com/microsoft/regorus

### Tools

- **rust-analyzer:** VS Code extension for Rust
- **cargo-watch:** Auto-rebuild on file changes
- **cargo-edit:** Manage dependencies from CLI
- **cargo-outdated:** Check for outdated dependencies

### Community

- **GitHub:** https://github.com/anthropics/sark
- **Issues:** https://github.com/anthropics/sark/issues
- **Discord:** https://discord.gg/sark

---

## Next Steps

1. **Build from source** - Follow the build instructions
2. **Run tests** - Ensure everything works
3. **Make a small change** - Try adding a simple feature
4. **Submit a PR** - Contribute your improvements!

**Questions?** Open an issue or ask in Discord!

**Found a bug?** Please report it: https://github.com/anthropics/sark/issues/new

---

**Happy coding! 🦀🐍**
