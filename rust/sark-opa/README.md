# SARK OPA - High-Performance Embedded Policy Engine

A high-performance embedded OPA (Open Policy Agent) policy evaluation engine built with Rust using the Regorus library, with Python bindings via PyO3.

## Features

- **🚀 High Performance**: 4-10x faster than HTTP-based OPA
- **⚡ Low Latency**: <5ms p95 latency for policy evaluation
- **📦 Embedded**: No network overhead, policies run in-process
- **🔒 Thread-Safe**: Concurrent evaluations supported
- **🐍 Python Integration**: Easy-to-use Python bindings via PyO3

## Architecture

```
┌─────────────────────────────────────┐
│      Python Application (SARK)      │
├─────────────────────────────────────┤
│      RustOPAClient (Python)         │
│  - Async interface                  │
│  - Policy caching                   │
│  - Cache integration                │
├─────────────────────────────────────┤
│   RustOPAEngine (PyO3 Bindings)     │
│  - Python ↔ Rust bridge             │
│  - JSON serialization               │
│  - Exception mapping                │
├─────────────────────────────────────┤
│      OPAEngine (Rust Core)          │
│  - Policy compilation               │
│  - Policy evaluation                │
│  - Policy caching                   │
├─────────────────────────────────────┤
│       Regorus Library               │
│  - Rego parser                      │
│  - Rego interpreter                 │
└─────────────────────────────────────┘
```

## Performance Comparison

| Operation | HTTP OPA | Rust OPA | Improvement |
|-----------|----------|----------|-------------|
| Simple policy (RBAC) | ~30ms p95 | <5ms p95 | **6x faster** |
| Complex policy | ~50ms p95 | <10ms p95 | **5x faster** |
| Throughput | 500 req/s | 2000+ req/s | **4x higher** |

## Building

### Prerequisites

- Rust 1.75+ (with cargo)
- Python 3.11+
- maturin (Python package)

### Build Instructions

```bash
# Install maturin
pip install maturin

# Development build (creates a debug build and installs it in the current virtualenv)
maturin develop

# Production build (optimized)
maturin develop --release

# Build wheel for distribution
maturin build --release
```

## Usage

### Python API

```python
from sark.services.policy import RustOPAClient, AuthorizationInput

# Initialize the client
client = RustOPAClient(
    policy_dir="opa/policies",
    cache_enabled=True
)

# Create authorization request
auth_input = AuthorizationInput(
    user={"id": "user1", "role": "admin"},
    action="gateway:tool:invoke",
    tool={"name": "db-query", "sensitivity_level": "medium"},
    context={}
)

# Evaluate policy
decision = await client.evaluate_policy(auth_input)

print(f"Allow: {decision.allow}")
print(f"Reason: {decision.reason}")
```

### Direct Rust API (from Python)

```python
from sark._rust import sark_opa

# Create engine
engine = sark_opa.RustOPAEngine()

# Load policy
policy = """
package authz
allow {
    input.user.role == "admin"
}
"""
engine.load_policy("authz", policy)

# Evaluate
result = engine.evaluate(
    "data.authz.allow",
    {"user": {"role": "admin"}}
)

print(result)  # True
```

## Testing

### Rust Tests

```bash
# Run Rust unit tests
cd rust/sark-opa
cargo test

# Run with verbose output
cargo test -- --nocapture

# Run specific test
cargo test test_load_valid_policy
```

### Python Tests

```bash
# Run Python tests (requires maturin develop first)
pytest tests/unit/services/policy/test_rust_opa_client.py -v

# Run with coverage
pytest tests/unit/services/policy/test_rust_opa_client.py --cov=src/sark/services/policy
```

## Module Structure

```
rust/sark-opa/
├── src/
│   ├── lib.rs          # Library entry point
│   ├── engine.rs       # Core OPA engine implementation
│   ├── error.rs        # Error types
│   └── python.rs       # PyO3 bindings
├── tests/
│   └── engine_tests.rs # Rust unit tests
├── Cargo.toml          # Rust dependencies
└── README.md           # This file

src/sark/services/policy/
├── rust_opa_client.py  # Python wrapper
└── __init__.py         # Module exports

tests/unit/services/policy/
└── test_rust_opa_client.py  # Python tests
```

## Dependencies

### Rust Dependencies

- **regorus** (0.2): Rust implementation of OPA Rego
- **pyo3** (0.22): Python bindings
- **pythonize** (0.22): Python ↔ JSON conversion
- **serde/serde_json** (1.0): JSON serialization
- **anyhow** (1.0): Error handling

### Python Dependencies

- **structlog**: Structured logging
- **pydantic**: Data validation

## Error Handling

The engine provides comprehensive error handling:

```python
from sark._rust.sark_opa import OPACompilationError, OPAEvaluationError

try:
    engine.load_policy("bad_policy", "invalid rego")
except OPACompilationError as e:
    print(f"Policy compilation failed: {e}")

try:
    result = engine.evaluate("data.missing.policy", {})
except OPAEvaluationError as e:
    print(f"Evaluation failed: {e}")
```

## Performance Tips

1. **Preload policies**: Load policies at startup, not on every request
2. **Enable caching**: Use the built-in policy cache for repeated evaluations
3. **Batch operations**: Evaluate multiple policies in parallel when possible
4. **Reuse engine instances**: Creating engines is expensive, reuse them

## Limitations

1. **Regorus compatibility**: Some advanced OPA features may not be supported by Regorus
2. **Policy validation**: Complex policies should be tested against both HTTP OPA and Rust OPA
3. **Built-in functions**: Regorus implements a subset of OPA's built-in functions

## Troubleshooting

### ImportError: No module named 'sark._rust.sark_opa'

Run `maturin develop` to build and install the Rust extension.

### OPACompilationError on valid policy

Check Regorus compatibility - some OPA features are not yet supported. Test with the OPA playground.

### Performance not as expected

Ensure you:
- Built with `--release` flag
- Preloaded policies
- Enabled result caching
- Profiled your specific use case

## Contributing

When contributing:

1. Run Rust tests: `cargo test`
2. Run Python tests: `pytest tests/unit/services/policy/test_rust_opa_client.py`
3. Format Rust code: `cargo fmt`
4. Lint Rust code: `cargo clippy`
5. Format Python code: `black src/ tests/`

## License

MIT License - See COPYRIGHT file for details.

## References

- [Regorus GitHub](https://github.com/microsoft/regorus)
- [OPA Documentation](https://www.openpolicyagent.org/docs/latest/)
- [PyO3 Documentation](https://pyo3.rs/)
- [SARK OPA Integration Plan](../../docs/v1.4.0/DETAILED_PLAN.md)
