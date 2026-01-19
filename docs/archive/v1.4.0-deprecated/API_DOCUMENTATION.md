# API Documentation Generation Guide

This guide explains how to generate and publish API documentation for SARK v1.4.0, including both Python and Rust components.

---

## Overview

SARK v1.4.0 includes:
- **Python API:** FastAPI endpoints, service classes, utilities
- **Rust API:** OPA engine and cache bindings via PyO3

Both are documented using standard tools:
- **Python:** pdoc3 for automatic docstring-based documentation
- **Rust:** cargo doc for Rustdoc-based documentation

---

## Prerequisites

```bash
# Install Python documentation tools
pip install pdoc3

# Rust documentation tools (included with Rust)
cargo doc --version
```

---

## Generating Python API Documentation

### Quick Generation

```bash
# Generate HTML documentation
pdoc --html src/sark -o docs/v1.4.0/api/python/

# Or use pdoc3
pdoc3 --html --output-dir docs/v1.4.0/api/python/ src/sark
```

### Detailed Options

```bash
# Generate with custom template
pdoc3 --html \
      --output-dir docs/v1.4.0/api/python/ \
      --template-dir docs/templates/ \
      --force \
      src/sark

# Generate single-page documentation
pdoc3 --html \
      --output-dir docs/v1.4.0/api/python/ \
      --force \
      --config show_source_code=False \
      src/sark

# Serve documentation locally (for preview)
pdoc3 --http localhost:8080 src/sark
```

### Documented Modules

Python API documentation includes:

**Core Modules:**
- `sark.gateway` - Gateway API endpoints and middleware
- `sark.services` - Service layer (auth, policy, cache, discovery)
- `sark.models` - Database models and schemas
- `sark.config` - Configuration management

**Rust Integration:**
- `sark.policy.rust_engine` - Rust OPA client wrapper
- `sark.services.cache.rust_cache` - Rust cache client wrapper
- `sark.features` - Feature flag manager

**Security:**
- `sark.security.injection` - Prompt injection detection
- `sark.security.secrets` - Secret scanning and redaction
- `sark.security.anomaly` - Behavioral anomaly detection
- `sark.security.mfa` - Multi-factor authentication

---

## Generating Rust API Documentation

### Quick Generation

```bash
# Generate Rust documentation
cd rust
cargo doc --no-deps --open

# Generate for specific crate
cargo doc --no-deps -p sark-opa --open
cargo doc --no-deps -p sark-cache --open
```

### Detailed Options

```bash
# Generate all documentation including dependencies
cargo doc --open

# Generate with private items
cargo doc --no-deps --document-private-items

# Generate for all workspace members
cargo doc --workspace --no-deps

# Generate and save to custom directory
cargo doc --no-deps --target-dir docs/v1.4.0/api/rust/
```

### Documented Crates

Rust API documentation includes:

**sark-opa:**
- `RustOPAEngine` - Main OPA engine class
- `PolicyEngine::load_policy()` - Load and compile Rego policy
- `PolicyEngine::evaluate()` - Evaluate policy against input
- Error types and handling

**sark-cache:**
- `RustPolicyCache` - Main cache class
- `Cache::get()` - Retrieve cached value
- `Cache::set()` - Store value with TTL
- `Cache::delete()` - Remove cached value
- `Cache::clear()` - Clear all entries
- `Cache::evict_expired()` - Manual cleanup

---

## Publishing Documentation

### To GitHub Pages

```bash
# Build all documentation
./scripts/build-docs.sh

# Commit to gh-pages branch
git checkout gh-pages
cp -r docs/v1.4.0/api/* api/v1.4.0/
git add api/v1.4.0/
git commit -m "docs: Add v1.4.0 API documentation"
git push origin gh-pages

# Access at: https://yourorg.github.io/sark/api/v1.4.0/
```

### To ReadTheDocs

```bash
# Ensure docs/conf.py is configured
# Ensure docs/requirements.txt includes pdoc3
# Push to main branch - ReadTheDocs will auto-build
git push origin main

# Access at: https://sark.readthedocs.io/
```

### To Static Hosting

```bash
# Build documentation
pdoc3 --html --output-dir build/docs/python/ src/sark
cargo doc --no-deps --target-dir build/docs/rust/

# Upload to S3
aws s3 sync build/docs/ s3://sark-docs/v1.4.0/ --acl public-read

# Or to any static host
scp -r build/docs/ user@host:/var/www/sark-docs/v1.4.0/
```

---

## Documentation Structure

### Recommended Directory Layout

```
docs/v1.4.0/
├── api/                              # Generated API docs
│   ├── python/                       # Python API docs (pdoc)
│   │   ├── sark/
│   │   │   ├── gateway/
│   │   │   ├── services/
│   │   │   ├── policy/
│   │   │   │   └── rust_engine.html
│   │   │   └── index.html
│   │   └── index.html
│   └── rust/                         # Rust API docs (cargo doc)
│       ├── sark_opa/
│       │   └── index.html
│       ├── sark_cache/
│       │   └── index.html
│       └── index.html
├── MIGRATION_GUIDE.md                # Migration guide
├── RELEASE_NOTES.md                  # Release notes
├── ARCHITECTURE.md                   # Architecture docs
├── DEVELOPER_GUIDE.md                # Developer guide
└── API_DOCUMENTATION.md              # This file
```

---

## Automating Documentation Generation

### Build Script

Create `scripts/build-docs.sh`:

```bash
#!/bin/bash
set -e

echo "Building SARK v1.4.0 Documentation..."

# Clean previous builds
rm -rf docs/v1.4.0/api/

# Generate Python API docs
echo "Generating Python API documentation..."
pdoc3 --html --output-dir docs/v1.4.0/api/python/ --force src/sark

# Generate Rust API docs
echo "Generating Rust API documentation..."
cd rust
cargo doc --no-deps --target-dir ../docs/v1.4.0/api/rust/
cd ..

# Copy index page
cat > docs/v1.4.0/api/index.html <<EOF
<!DOCTYPE html>
<html>
<head>
    <title>SARK v1.4.0 API Documentation</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; }
        h1 { color: #333; }
        .api-link { display: block; margin: 20px 0; padding: 15px; background: #f5f5f5; text-decoration: none; color: #333; }
        .api-link:hover { background: #e0e0e0; }
    </style>
</head>
<body>
    <h1>SARK v1.4.0 API Documentation</h1>
    <a href="python/sark/index.html" class="api-link">
        <h2>Python API</h2>
        <p>FastAPI endpoints, services, and Python wrappers for Rust components</p>
    </a>
    <a href="rust/sark_opa/index.html" class="api-link">
        <h2>Rust OPA Engine API</h2>
        <p>Embedded OPA policy evaluation engine</p>
    </a>
    <a href="rust/sark_cache/index.html" class="api-link">
        <h2>Rust Cache API</h2>
        <p>High-performance in-memory cache</p>
    </a>
</body>
</html>
EOF

echo "✅ Documentation built successfully!"
echo "   Python API: docs/v1.4.0/api/python/sark/index.html"
echo "   Rust API:   docs/v1.4.0/api/rust/sark_opa/index.html"
echo "   Index:      docs/v1.4.0/api/index.html"
```

### Make executable

```bash
chmod +x scripts/build-docs.sh
```

### GitHub Actions Workflow

Create `.github/workflows/docs.yml`:

```yaml
name: Generate Documentation

on:
  push:
    branches: [main, v1.4.0]
  pull_request:
    branches: [main]

jobs:
  build-docs:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Set up Rust
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable

      - name: Install dependencies
        run: |
          pip install pdoc3
          pip install -e .

      - name: Build documentation
        run: ./scripts/build-docs.sh

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v2
        with:
          path: docs/v1.4.0/api/

      - name: Deploy to GitHub Pages
        if: github.ref == 'refs/heads/main'
        uses: actions/deploy-pages@v2
```

---

## Docstring Guidelines

### Python Docstrings

Follow Google style:

```python
def evaluate_policy(
    policy_name: str,
    input_data: dict,
    use_rust: bool = True
) -> dict:
    """Evaluate an OPA policy against input data.

    This function evaluates the specified policy using either the Rust
    or Python OPA engine, depending on availability and configuration.

    Args:
        policy_name: Name of the policy to evaluate
        input_data: Input data as a dictionary
        use_rust: Whether to prefer Rust engine (default: True)

    Returns:
        Dictionary containing evaluation results with 'allow' and 'reason' keys

    Raises:
        PolicyNotFoundError: If the specified policy does not exist
        EvaluationError: If policy evaluation fails

    Example:
        >>> result = evaluate_policy("authz", {"user": "admin"})
        >>> print(result["allow"])
        True
    """
    # Implementation
```

### Rust Docstrings

Follow Rustdoc conventions:

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
/// # Errors
///
/// Returns `PolicyNotFound` if policy doesn't exist
/// Returns `EvaluationError` if evaluation fails
///
/// # Example
///
/// ```
/// use sark_opa::PolicyEngine;
/// use serde_json::json;
///
/// let mut engine = PolicyEngine::new()?;
/// let result = engine.evaluate("authz", &json!({"user": "admin"}))?;
/// ```
pub fn evaluate(
    &self,
    policy_name: &str,
    input: &Value
) -> Result<Value> {
    // Implementation
}
```

---

## Viewing Documentation Locally

### Python Docs

```bash
# Option 1: Use pdoc's built-in server
pdoc3 --http localhost:8080 src/sark

# Option 2: Use Python's built-in HTTP server
cd docs/v1.4.0/api/python/
python -m http.server 8080

# Access at: http://localhost:8080/sark/
```

### Rust Docs

```bash
# Build and open in browser
cd rust
cargo doc --no-deps --open

# Or manually
cargo doc --no-deps
python -m http.server 8080 -d target/doc/

# Access at: http://localhost:8080/sark_opa/
```

---

## Updating API Documentation

### For New Features

1. **Add docstrings** to all new functions/classes
2. **Build documentation** locally to verify
3. **Review output** in browser
4. **Commit changes** to repository
5. **CI will auto-publish** to docs site

### For Breaking Changes

1. **Update docstrings** with migration notes
2. **Add deprecation warnings** if applicable
3. **Update examples** to show new usage
4. **Rebuild and verify** documentation
5. **Announce** in release notes

---

## Troubleshooting

### Issue: pdoc3 not finding modules

**Solution:**
```bash
# Ensure SARK is installed in development mode
pip install -e .

# Or set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
pdoc3 --html sark
```

### Issue: Rust docs missing

**Solution:**
```bash
# Ensure you're in rust/ directory
cd rust

# Clean and rebuild
cargo clean
cargo doc --no-deps
```

### Issue: Broken links in documentation

**Solution:**
```bash
# Use --html-no-source to avoid source links
pdoc3 --html --html-no-source src/sark

# For Rust, ensure workspace structure is correct
# Check Cargo.toml [workspace] section
```

---

## Additional Resources

### Tools

- **pdoc3:** https://pdoc3.github.io/pdoc/
- **Rustdoc:** https://doc.rust-lang.org/rustdoc/
- **Sphinx:** https://www.sphinx-doc.org/ (alternative for Python)
- **mkdocs:** https://www.mkdocs.org/ (alternative docs tool)

### Documentation Best Practices

- **Write for your audience:** Assume basic knowledge, explain advanced concepts
- **Include examples:** Code examples are worth a thousand words
- **Keep it updated:** Update docs with every API change
- **Link related docs:** Cross-reference related functionality
- **Test examples:** Ensure code examples actually work

---

## Summary

**To generate all API documentation:**

```bash
./scripts/build-docs.sh
```

**To view locally:**

```bash
# Python
pdoc3 --http localhost:8080 src/sark

# Rust
cd rust && cargo doc --no-deps --open
```

**To publish:**

```bash
git push origin main  # CI will auto-publish
```

---

**Questions?** See [Developer Guide](DEVELOPER_GUIDE.md) for more details.
