# SARK v1.4.0 Detailed Implementation Plan
## Rust Foundation: High-Performance Core Components

Complete technical specification for implementing Rust optimizations in SARK v1.4.0.

**Document Version:** 1.0  
**Last Updated:** December 27, 2025  
**Target Release Date:** February 2026 (6-8 weeks from start)  

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Work Stream Architecture](#work-stream-architecture)
3. [Stream 1: Rust Build System](#stream-1-rust-build-system)
4. [Stream 2: Rust OPA Engine](#stream-2-rust-opa-engine)
5. [Stream 3: Rust Cache Engine](#stream-3-rust-cache-engine)
6. [Stream 4: Integration & A/B Testing](#stream-4-integration-ab-testing)
7. [Stream 5: Performance Testing](#stream-5-performance-testing)
8. [Stream 6: Documentation](#stream-6-documentation)
9. [Release Checklist](#release-checklist)
10. [Risk Management](#risk-management)
11. [Resource Requirements](#resource-requirements)

---

## Executive Summary

### Objectives

Replace critical Python performance bottlenecks with high-performance Rust implementations:

1. **Rust OPA Engine** - Embedded Rego evaluation (no HTTP overhead)
2. **Rust In-Memory Cache** - Fast LRU+TTL cache (no Redis network I/O)

### Performance Goals

| Component | Current (Python) | Target (Rust) | Improvement |
|-----------|------------------|---------------|-------------|
| OPA Evaluation | 20-50ms p95 | <5ms p95 | 4-10x faster |
| Cache Get/Set | 1-5ms p95 | <0.5ms p95 | 10-50x faster |
| Total Request | ~100ms p95 | ~50ms p95 | 2x faster |
| Throughput | 850 req/s | 2,000+ req/s | 2.4x faster |

### Strategic Approach

- **Zero Breaking Changes** - Drop-in replacement for existing Python code
- **Feature Flags** - A/B testing to validate performance gains
- **Gradual Rollout** - 5% → 25% → 50% → 100% traffic migration
- **Fallback Support** - Keep Python implementation for emergency rollback

### Timeline

```
Week 1: Build Setup      ┐
Week 2: OPA + Cache      ├─ Core Implementation
Week 3: OPA + Cache      ┘
Week 4: Integration      ┐
Week 5: A/B + Perf Test  ├─ Validation
Week 6: Perf + Docs      ┘
Week 7-8: Buffer/Polish
```

---

## Work Stream Architecture

### Dependency Graph

```
Stream 1 (Build)
    ├─→ Stream 2 (OPA)    ─┐
    └─→ Stream 3 (Cache)  ─┤
                           ├─→ Stream 4 (Integration) ─→ Stream 5 (Testing)
                           └─────────────────────────────→ Stream 6 (Docs)
```

### Worker Assignments

| Stream | Worker | Agent | Duration | Parallel |
|--------|--------|-------|----------|----------|
| 1. Build Setup | DEVOPS-1 | Cursor | Week 1 | No |
| 2. Rust OPA | RUST-1 | Aider | Weeks 2-3 | Yes (with 3) |
| 3. Rust Cache | RUST-2 | Aider | Weeks 2-3 | Yes (with 2) |
| 4. Integration | RUST-3 | Cursor | Weeks 4-5 | No |
| 5. Performance | QA | Aider | Weeks 5-6 | Partial (with 6) |
| 6. Documentation | DOCS | Any | Week 6 | Partial (with 5) |

---

## Stream 1: Rust Build System

**Owner:** DEVOPS-1 (Cursor recommended)  
**Duration:** 1 week  
**Goal:** Set up Rust tooling and PyO3 integration  

### Tasks

#### 1.1 Initialize Rust Workspace (Day 1)

Create Rust project structure:

```
rust/
├── Cargo.toml           # Workspace manifest
├── sark-opa/            # OPA engine crate
│   ├── Cargo.toml
│   ├── src/
│   │   └── lib.rs
│   └── tests/
└── sark-cache/          # Cache engine crate
    ├── Cargo.toml
    ├── src/
    │   └── lib.rs
    └── tests/
```

**rust/Cargo.toml:**
```toml
[workspace]
members = ["sark-opa", "sark-cache"]
resolver = "2"

[workspace.dependencies]
pyo3 = { version = "0.21", features = ["extension-module"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
regorus = "0.1"         # Rust OPA implementation
dashmap = "5.5"         # Concurrent HashMap
parking_lot = "0.12"    # Fast synchronization primitives
```

#### 1.2 Configure Maturin (Day 2)

Update `pyproject.toml`:

```toml
[build-system]
requires = ["maturin>=1.4,<2.0"]
build-backend = "maturin"

[tool.maturin]
bindings = "pyo3"
python-source = "src"
module-name = "sark._rust"
```

Test with hello world function.

#### 1.3 CI/CD Integration (Days 3-4)

Create `.github/workflows/rust.yml`:

```yaml
name: Rust CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
      - run: cd rust && cargo test --all
      - run: cd rust && cargo clippy -- -D warnings
      - run: cd rust && cargo fmt --check
```

Add Rust build to main CI pipeline.

#### 1.4 Python Import Wrapper (Day 5)

**src/sark/_rust/__init__.py:**
```python
"""Rust extension modules."""
try:
    from sark._rust.sark_opa import *
    from sark._rust.sark_cache import *
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
```

### Acceptance Criteria

- [ ] `maturin build --release` succeeds
- [ ] Rust tests pass in CI
- [ ] Python can import `sark._rust`
- [ ] All clippy warnings resolved

---

## Stream 2: Rust OPA Engine

**Owner:** RUST-1 (Aider with Rust expertise)  
**Duration:** 2 weeks  
**Goal:** Embedded Rego policy evaluation engine  

### Architecture

```
Python Code
    ↓
PyO3 Bindings (sark_opa.so)
    ↓
Rust OPA Engine
    ├─ Regorus (Rego parser/evaluator)
    ├─ Policy Cache (HashMap<String, Policy>)
    └─ Evaluation Engine
```

### Implementation

#### Week 2: Core Engine

**Task 2.1: Regorus Integration** (Days 1-3)

**rust/sark-opa/src/engine.rs:**
```rust
use regorus::Engine as RegorusEngine;
use serde_json::Value;
use anyhow::Result;

pub struct OPAEngine {
    engine: RegorusEngine,
    policies: HashMap<String, String>,
}

impl OPAEngine {
    pub fn new() -> Result<Self> {
        Ok(Self {
            engine: RegorusEngine::new(),
            policies: HashMap::new(),
        })
    }

    pub fn load_policy(&mut self, name: String, rego: String) -> Result<()> {
        self.engine.add_policy(name.clone(), rego.clone())?;
        self.policies.insert(name, rego);
        Ok(())
    }

    pub fn evaluate(&mut self, query: &str, input: Value) -> Result<Value> {
        self.engine.set_input(input);
        let result = self.engine.eval_query(query.to_string(), false)?;
        Ok(result)
    }
}
```

**Task 2.2: PyO3 Bindings** (Days 4-5)

**rust/sark-opa/src/lib.rs:**
```rust
use pyo3::prelude::*;

#[pyclass]
struct RustOPAEngine {
    inner: OPAEngine,
}

#[pymethods]
impl RustOPAEngine {
    #[new]
    fn new() -> PyResult<Self> {
        let engine = OPAEngine::new()
            .map_err(|e| PyErr::new::<exceptions::PyRuntimeError, _>(
                format!("OPA init failed: {}", e)
            ))?;
        Ok(Self { inner: engine })
    }

    fn load_policy(&mut self, name: String, rego: String) -> PyResult<()> {
        self.inner.load_policy(name, rego)
            .map_err(|e| PyErr::new::<exceptions::PyRuntimeError, _>(e.to_string()))
    }

    fn evaluate(&mut self, query: String, input: &PyDict) -> PyResult<PyObject> {
        let input_json: Value = pythonize::depythonize(input)?;
        let result = self.inner.evaluate(&query, input_json)?;
        Python::with_gil(|py| pythonize::pythonize(py, &result))
    }
}

#[pymodule]
fn sark_opa(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<RustOPAEngine>()?;
    Ok(())
}
```

#### Week 3: Python Integration

**Task 3.1: Python Wrapper** (Days 1-2)

**src/sark/services/policy/rust_opa_client.py:**
```python
from sark._rust import RUST_AVAILABLE, sark_opa

class RustOPAClient:
    def __init__(self):
        if not RUST_AVAILABLE:
            raise RuntimeError("Rust not available")
        self.engine = sark_opa.RustOPAEngine()
    
    async def evaluate(self, policy: str, input_data: dict) -> dict:
        return self.engine.evaluate(policy, input_data)
```

**Task 3.2: Feature Flag** (Day 3)

Enable runtime switching between Rust and HTTP OPA.

**Task 3.3: Tests** (Days 4-5)

- Rust unit tests (Cargo test)
- Python integration tests
- Performance benchmarks

### Performance Target

- **<5ms p95 latency** for policy evaluation
- **4-10x faster** than HTTP OPA

### Acceptance Criteria

- [ ] All Rego test policies evaluate correctly
- [ ] Performance benchmarks pass
- [ ] Python integration tests pass
- [ ] Fallback to HTTP OPA works

---

## Stream 3: Rust Cache Engine

**Owner:** RUST-2 (Aider with Rust expertise)  
**Duration:** 2 weeks (parallel with Stream 2)  
**Goal:** High-performance in-memory LRU+TTL cache  

### Architecture

```
Python Code
    ↓
PyO3 Bindings (sark_cache.so)
    ↓
Rust Cache Engine
    ├─ DashMap (concurrent HashMap)
    ├─ TTL tracking (Instant-based)
    └─ LRU eviction policy
```

### Implementation

#### Week 2: Core Cache

**Task 3.1: LRU+TTL Implementation** (Days 1-3)

**rust/sark-cache/src/lru_ttl.rs:**
```rust
use dashmap::DashMap;
use std::time::{Duration, Instant};

struct CacheEntry {
    value: String,
    expires_at: Instant,
}

pub struct LRUTTLCache {
    map: DashMap<String, CacheEntry>,
    max_size: usize,
    default_ttl: Duration,
}

impl LRUTTLCache {
    pub fn new(max_size: usize, ttl_secs: u64) -> Self {
        Self {
            map: DashMap::new(),
            max_size,
            default_ttl: Duration::from_secs(ttl_secs),
        }
    }

    pub fn get(&self, key: &str) -> Option<String> {
        let entry = self.map.get(key)?;
        if entry.expires_at <= Instant::now() {
            drop(entry);
            self.map.remove(key);
            return None;
        }
        Some(entry.value.clone())
    }

    pub fn set(&self, key: String, value: String, ttl: Option<u64>) {
        if self.map.len() >= self.max_size {
            self.evict_lru();
        }
        let ttl = ttl.map(Duration::from_secs).unwrap_or(self.default_ttl);
        self.map.insert(key, CacheEntry {
            value,
            expires_at: Instant::now() + ttl,
        });
    }

    fn evict_lru(&self) {
        // Evict oldest entry (simplified - production needs better LRU)
        if let Some(entry) = self.map.iter().next() {
            let key = entry.key().clone();
            drop(entry);
            self.map.remove(&key);
        }
    }
}
```

**Task 3.2: PyO3 Bindings** (Days 4-5)

Similar to OPA bindings, expose cache operations to Python.

#### Week 3: Integration

**Task 3.3: Python Wrapper** (Days 1-2)

**src/sark/services/policy/rust_cache.py:**
```python
from sark._rust.sark_cache import RustCache

class RustPolicyCache:
    def __init__(self, max_size=10000, ttl_secs=300):
        self.cache = RustCache(max_size, ttl_secs)
    
    async def get(self, key: str) -> dict | None:
        cached = self.cache.get(key)
        return json.loads(cached) if cached else None
    
    async def set(self, key: str, value: dict, ttl: int | None = None):
        self.cache.set(key, json.dumps(value), ttl)
```

**Task 3.4: Background Cleanup** (Day 3)

Periodic task to remove expired entries.

**Task 3.5: Tests** (Days 4-5)

- TTL expiration tests
- LRU eviction tests
- Concurrent access tests
- Performance benchmarks

### Performance Target

- **<0.5ms p95 latency** for get/set operations
- **10-50x faster** than Redis cache

### Acceptance Criteria

- [ ] TTL expiration works correctly
- [ ] LRU eviction under memory pressure
- [ ] Thread-safe concurrent access
- [ ] Performance benchmarks pass

---

## Stream 4: Integration & A/B Testing

**Owner:** RUST-3 (Cursor recommended)  
**Duration:** 2 weeks  
**Goal:** Production integration with gradual rollout  

### A/B Testing Framework

**src/sark/services/feature_flags.py:**
```python
class FeatureFlagManager:
    def __init__(self):
        self.rollout_pct = {
            "rust_opa": 0,    # Start at 0%
            "rust_cache": 0,
        }
    
    def should_use_rust(self, feature: str, user_id: str) -> bool:
        hash_val = hash(user_id) % 100
        return hash_val < self.rollout_pct[feature]
```

### Dual-Path Execution

Modify gateway router to choose Python or Rust based on feature flags:

```python
async def authorize(user_id, action, resource):
    if feature_flags.should_use_rust("rust_opa", user_id):
        client = RustOPAClient()
    else:
        client = HTTPOPAClient()
    
    # ... rest of authorization logic
```

### Metrics Collection

Record latency separately for Rust and Python paths:

```python
@histogram('request_latency', labels=['implementation'])
async def authorize(...):
    impl = "rust" if using_rust else "python"
    # ... measure and record
```

### Gradual Rollout

Admin API to adjust rollout percentage:

```python
@router.post("/admin/rust-rollout")
async def set_rollout(feature: str, percentage: int):
    feature_flags.set_rollout(feature, percentage)
```

### Acceptance Criteria

- [ ] Feature flags route traffic correctly
- [ ] Metrics show Rust vs Python comparison
- [ ] Rollout percentage adjustable
- [ ] Instant rollback to 0% works

---

## Stream 5: Performance Testing

**Owner:** QA  
**Duration:** 2 weeks  
**Goal:** Validate performance improvements  

### Test Types

1. **Benchmarks** - Microbenchmarks for OPA and cache
2. **Load Tests** - Sustained throughput (Locust)
3. **Stress Tests** - Find breaking points
4. **Comparison** - Rust vs Python side-by-side

### Target Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| OPA p95 latency | <5ms | Benchmark |
| Cache p95 latency | <0.5ms | Benchmark |
| Throughput | 2,000+ req/s | Load test |
| Memory usage | ≤baseline | Profiling |

### Tools

- **pytest-benchmark** - Python benchmarks
- **Locust** - Load testing
- **Prometheus** - Metrics collection
- **Grafana** - Visualization

### Acceptance Criteria

- [ ] All performance targets met
- [ ] No memory leaks detected
- [ ] 99.9% success rate under load
- [ ] Performance report published

---

## Stream 6: Documentation

**Owner:** DOCS  
**Duration:** 1 week  
**Goal:** Complete documentation for v1.4.0  

### Documents

1. **Migration Guide** - Upgrading from v1.3.0
2. **Release Notes** - What's new in v1.4.0
3. **Architecture Docs** - Rust integration design
4. **Developer Guide** - Building Rust extensions
5. **Performance Report** - Benchmark results

### Acceptance Criteria

- [ ] All docs peer-reviewed
- [ ] Migration guide tested
- [ ] Build instructions verified

---

## Release Checklist

### Pre-Release

- [ ] All streams merged
- [ ] Tests passing (100%)
- [ ] Performance validated
- [ ] Documentation complete

### Release

- [ ] Tag v1.4.0
- [ ] Build release binaries (maturin)
- [ ] Publish to PyPI
- [ ] Update Helm charts
- [ ] Deploy to staging

### Post-Release

- [ ] Gradual rollout (5% → 100%)
- [ ] Monitor metrics
- [ ] Document learnings

---

## Risk Management

### Risks

1. **Regorus library immature** → Test early, have fallback
2. **PyO3 complexity** → Start simple, iterate
3. **Performance targets not met** → Profile and optimize

### Mitigation

- Early prototyping (Week 1)
- Continuous benchmarking
- Keep Python fallback

---

## Resource Requirements

### Team

- 3 Rust developers (2 weeks each) = 6 weeks FTE
- 1 DevOps engineer (1 week) = 1 week FTE
- 1 QA engineer (2 weeks) = 2 weeks FTE
- 1 Tech writer (1 week) = 1 week FTE

**Total:** ~10 weeks FTE over 6-8 calendar weeks

### Cost Estimate

- Engineering: $50,000 (10 weeks × $5k/week)
- Infrastructure: $1,200 (testing)
- **Total: ~$51,200**

---

## Timeline

```
January 2026:  Weeks 1-4 (Build, Core, Integration)
February 2026: Weeks 5-8 (Testing, Docs, Release)
```

**Target Release:** February 28, 2026

---

## Success Criteria

✅ 2,000+ req/s sustained throughput  
✅ <5ms OPA latency  
✅ <0.5ms cache latency  
✅ Zero breaking changes  
✅ Smooth rollout with rollback capability  

---

**End of Detailed Plan**

