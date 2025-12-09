# SARK v1.4.0 Implementation Plan
## Rust Performance Optimization - Foundation

**Version:** 1.0
**Date:** December 9, 2025
**Target Release:** v1.4.0
**Prerequisites:** v1.3.0 complete (Advanced security features)
**Duration:** 6-8 weeks
**Orchestration:** Czarina multi-agent system + Rust specialist

---

## Executive Summary

v1.4.0 introduces compiled Rust components for critical hot paths, providing 5-10x performance improvements while maintaining Python for business logic. This is the **foundation phase** establishing patterns and infrastructure for future Rust integration.

**What v1.4.0 Delivers:**
- ✅ Embedded Rust OPA engine (4-10x faster authorization)
- ✅ High-performance in-memory cache (10-50x faster than Redis)
- ✅ Rust build system integration (maturin + PyO3)
- ✅ Python fallback mechanisms (graceful degradation)
- ✅ Performance benchmarking framework

**Success Criteria:**
- Gateway authorization: <20ms p95 (from <100ms)
- Cache operations: <0.5ms (from 1-5ms)
- Throughput: 2,000+ req/s (from 850 req/s)
- 100% Python fallback compatibility
- No regressions in functionality

**Strategic Position:**
- v1.4.0 = Rust foundation (OPA + Cache)
- v1.5.0 = Rust detection algorithms (injection, anomaly, parsing)
- v1.6.0+ = Additional optimizations as needed

---

## Work Stream Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CZARINA ORCHESTRATION                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Stream 1: Rust OPA Engine     Stream 2: Rust Fast Cache        │
│  ┌──────────────────┐          ┌──────────────────┐            │
│  │ Worker: RUST-1   │          │ Worker: RUST-2   │            │
│  │ Weeks 1-3        │          │ Weeks 2-3        │            │
│  │ +OPA WASM engine │          │ +TTL cache       │            │
│  │ +PyO3 bindings   │          │ +Eviction policy │            │
│  └──────────────────┘          └──────────────────┘            │
│                                                                   │
│  Stream 3: Build System        Stream 4: Integration            │
│  ┌──────────────────┐          ┌──────────────────┐            │
│  │ Worker: DEVOPS   │          │ Worker: QA       │            │
│  │ Week 1           │          │ Weeks 4-5        │            │
│  │ +maturin setup   │          │ +A/B testing     │            │
│  │ +CI/CD integration│         │ +Benchmarks      │            │
│  └──────────────────┘          └──────────────────┘            │
│                                                                   │
│  Stream 5: Documentation       Stream 6: Performance Testing    │
│  ┌──────────────────┐          ┌──────────────────┐            │
│  │ Worker: DOCS     │          │ Worker: PERF     │            │
│  │ Week 6           │          │ Weeks 5-6        │            │
│  │ +Rust dev guide  │          │ +Load testing    │            │
│  │ +Migration guide │          │ +Profiling       │            │
│  └──────────────────┘          └──────────────────┘            │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

**Team Requirements:**
- 1x Rust specialist (senior) - Weeks 1-3
- 1x Python developer (integration) - Weeks 4-5
- 1x DevOps engineer - Week 1
- 1x QA engineer - Weeks 5-6

---

## Stream 1: Rust OPA Engine (RUST-1)

**Worker Assignment:** `RUST-1` (Rust specialist required)
**Duration:** Weeks 1-3 (3 weeks)
**Branch:** `feat/rust-opa-engine`
**Dependencies:** Stream 3 (build system setup)
**Estimated Effort:** 3 weeks, 1 Rust developer

### Week 1: OPA WASM Runtime

**Task 1.1: Project Setup** (1 day)
- **Directory:** `src-rust/opa_engine/`
- **Files:**
  ```
  src-rust/opa_engine/
  ├── Cargo.toml
  ├── src/
  │   ├── lib.rs
  │   ├── runtime.rs
  │   └── policy.rs
  └── tests/
      └── integration_test.rs
  ```

**`Cargo.toml`:**
```toml
[package]
name = "sark-opa-engine"
version = "0.1.0"
edition = "2021"

[lib]
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }
wasmtime = "15.0"  # WASM runtime
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
anyhow = "1.0"

[dev-dependencies]
tokio = { version = "1", features = ["full"] }
```

**Task 1.2: WASM Runtime Implementation** (2 days)
- **File:** `src-rust/opa_engine/src/runtime.rs`
- **Implementation:**
  ```rust
  use wasmtime::*;
  use anyhow::Result;

  pub struct OPARuntime {
      engine: Engine,
      store: Store<()>,
  }

  impl OPARuntime {
      pub fn new() -> Result<Self> {
          let engine = Engine::default();
          let store = Store::new(&engine, ());

          Ok(OPARuntime { engine, store })
      }

      pub fn evaluate(
          &mut self,
          policy_wasm: &[u8],
          input: &str,
      ) -> Result<String> {
          // Load WASM module
          let module = Module::new(&self.engine, policy_wasm)?;

          // Instantiate
          let instance = Instance::new(&mut self.store, &module, &[])?;

          // Call evaluate function
          let evaluate = instance
              .get_typed_func::<(i32, i32), i32>(&mut self.store, "evaluate")?;

          // ... implementation details
          Ok(result_json)
      }
  }
  ```

**Task 1.3: PyO3 Bindings** (2 days)
- **File:** `src-rust/opa_engine/src/lib.rs`
- **Implementation:**
  ```rust
  use pyo3::prelude::*;
  use std::collections::HashMap;

  #[pyclass]
  struct PolicyEngine {
      runtime: OPARuntime,
      policies: HashMap<String, Vec<u8>>,  // policy name -> WASM bytes
  }

  #[pymethods]
  impl PolicyEngine {
      #[new]
      fn new() -> PyResult<Self> {
          let runtime = OPARuntime::new()
              .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

          Ok(PolicyEngine {
              runtime,
              policies: HashMap::new(),
          })
      }

      fn load_policy(&mut self, name: &str, policy_wasm: &[u8]) -> PyResult<()> {
          self.policies.insert(name.to_string(), policy_wasm.to_vec());
          Ok(())
      }

      fn evaluate(&mut self, policy_name: &str, input: &str) -> PyResult<String> {
          let policy_wasm = self.policies.get(policy_name)
              .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Policy not found"))?;

          self.runtime.evaluate(policy_wasm, input)
              .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
      }
  }

  #[pymodule]
  fn sark_opa_engine(_py: Python, m: &PyModule) -> PyResult<()> {
      m.add_class::<PolicyEngine>()?;
      Ok(())
  }
  ```

### Week 2-3: Python Integration & Testing

**Task 2.1: Python Wrapper** (2 days)
- **File:** `src/sark/policy/rust_engine.py` (NEW)
- **Implementation:**
  ```python
  try:
      from sark_opa_engine import PolicyEngine as RustPolicyEngine
      RUST_AVAILABLE = True
  except ImportError:
      RUST_AVAILABLE = False
      logger.warning("Rust OPA engine not available, using Python fallback")

  class OPAClient:
      def __init__(self, use_rust: bool = True):
          if use_rust and RUST_AVAILABLE:
              self.engine = RustPolicyEngine()
              self.backend = "rust"
          else:
              self.engine = PythonOPAClient()
              self.backend = "python"

          logger.info(f"Using {self.backend} OPA engine")

      async def load_policy(self, name: str, policy_wasm: bytes):
          if self.backend == "rust":
              self.engine.load_policy(name, policy_wasm)
          else:
              await self.engine.load_policy(name, policy_wasm)

      async def evaluate(self, policy_name: str, input_data: dict) -> dict:
          input_json = json.dumps(input_data)

          if self.backend == "rust":
              result_json = self.engine.evaluate(policy_name, input_json)
          else:
              result_json = await self.engine.evaluate(policy_name, input_data)

          return json.loads(result_json)
  ```

**Task 2.2: Feature Flag** (1 day)
- **File:** `src/sark/config/settings.py` (UPDATE)
- **Implementation:**
  ```python
  class Settings(BaseSettings):
      # Rust feature flags
      use_rust_opa: bool = Field(
          default=True,
          description="Use Rust OPA engine (falls back to Python if unavailable)"
      )
  ```

**Task 2.3: Integration Tests** (2 days)
- **File:** `tests/integration/policy/test_rust_opa.py` (NEW)
- **Tests:**
  - Policy loading (Rust vs Python)
  - Policy evaluation correctness
  - Performance comparison
  - Error handling
  - Fallback mechanism

**Task 2.4: Benchmarks** (2 days)
- **File:** `tests/performance/bench_opa.py` (NEW)
- **Implementation:**
  ```python
  import timeit

  def benchmark_opa():
      # Python implementation
      python_time = timeit.timeit(
          lambda: python_opa.evaluate("test_policy", input_data),
          number=10000
      )

      # Rust implementation
      rust_time = timeit.timeit(
          lambda: rust_opa.evaluate("test_policy", input_data),
          number=10000
      )

      speedup = python_time / rust_time
      print(f"Rust OPA is {speedup:.1f}x faster")
      assert speedup >= 4.0, "Expected 4x+ speedup"
  ```

### Deliverables

**Code:**
- ✅ `src-rust/opa_engine/` - Rust OPA engine (500+ lines)
- ✅ `src/sark/policy/rust_engine.py` - Python wrapper (200 lines)
- ✅ `tests/integration/policy/test_rust_opa.py` (300 lines)
- ✅ `tests/performance/bench_opa.py` (150 lines)

**Performance:**
- [ ] 4-10x faster than Python OPA client
- [ ] <5ms p95 latency for policy evaluation
- [ ] 100% functional parity with Python

---

## Stream 2: Rust Fast Cache (RUST-2)

**Worker Assignment:** `RUST-2` (Rust specialist)
**Duration:** Weeks 2-3 (2 weeks)
**Branch:** `feat/rust-fast-cache`
**Dependencies:** Stream 3 (build system)
**Estimated Effort:** 2 weeks, 1 Rust developer

### Week 2: In-Memory Cache Implementation

**Task 2.1: TTL Cache** (2 days)
- **File:** `src-rust/fast_cache/src/lib.rs`
- **Implementation:**
  ```rust
  use pyo3::prelude::*;
  use std::collections::HashMap;
  use std::time::{Duration, Instant};
  use std::sync::Arc;
  use parking_lot::RwLock;

  struct CacheEntry {
      value: String,
      expires_at: Instant,
  }

  #[pyclass]
  struct FastCache {
      cache: Arc<RwLock<HashMap<String, CacheEntry>>>,
      default_ttl: Duration,
  }

  #[pymethods]
  impl FastCache {
      #[new]
      fn new(default_ttl_secs: u64) -> Self {
          FastCache {
              cache: Arc::new(RwLock::new(HashMap::new())),
              default_ttl: Duration::from_secs(default_ttl_secs),
          }
      }

      fn get(&self, key: &str) -> Option<String> {
          let cache = self.cache.read();

          if let Some(entry) = cache.get(key) {
              if Instant::now() < entry.expires_at {
                  return Some(entry.value.clone());
              }
          }

          None
      }

      fn set(&self, key: String, value: String, ttl_secs: Option<u64>) {
          let ttl = ttl_secs
              .map(Duration::from_secs)
              .unwrap_or(self.default_ttl);

          let expires_at = Instant::now() + ttl;

          let mut cache = self.cache.write();
          cache.insert(key, CacheEntry { value, expires_at });
      }

      fn delete(&self, key: &str) -> bool {
          let mut cache = self.cache.write();
          cache.remove(key).is_some()
      }

      fn clear(&self) {
          let mut cache = self.cache.write();
          cache.clear();
      }

      fn evict_expired(&self) -> usize {
          let mut cache = self.cache.write();
          let now = Instant::now();

          let before_size = cache.len();
          cache.retain(|_, entry| now < entry.expires_at);

          before_size - cache.len()
      }
  }

  #[pymodule]
  fn sark_fast_cache(_py: Python, m: &PyModule) -> PyResult<()> {
      m.add_class::<FastCache>()?;
      Ok(())
  }
  ```

### Week 3: Integration & Testing

**Task 3.1: Python Wrapper** (1 day)
- **File:** `src/sark/services/cache/rust_cache.py` (NEW)
- **Implementation:**
  ```python
  try:
      from sark_fast_cache import FastCache as RustFastCache
      RUST_CACHE_AVAILABLE = True
  except ImportError:
      RUST_CACHE_AVAILABLE = False

  class CacheClient:
      def __init__(self, use_rust: bool = True, ttl: int = 300):
          if use_rust and RUST_CACHE_AVAILABLE:
              self.cache = RustFastCache(ttl)
              self.backend = "rust"
          else:
              self.cache = RedisCacheClient(ttl)
              self.backend = "redis"

      async def get(self, key: str) -> Optional[str]:
          if self.backend == "rust":
              return self.cache.get(key)
          else:
              return await self.cache.get(key)

      async def set(self, key: str, value: str, ttl: Optional[int] = None):
          if self.backend == "rust":
              self.cache.set(key, value, ttl)
          else:
              await self.cache.set(key, value, ttl)
  ```

**Task 3.2: Benchmarks** (2 days)
- **File:** `tests/performance/bench_cache.py` (NEW)
- **Target:** 10-50x faster than Redis

**Task 3.3: Tests** (2 days)
- **File:** `tests/integration/cache/test_rust_cache.py` (NEW)

### Deliverables

**Code:**
- ✅ `src-rust/fast_cache/` - Rust cache (300 lines)
- ✅ `src/sark/services/cache/rust_cache.py` (150 lines)
- ✅ `tests/performance/bench_cache.py` (150 lines)

**Performance:**
- [ ] <0.5ms latency (vs 1-5ms Redis)
- [ ] 1,000,000+ ops/sec (vs 10,000 Redis)

---

## Stream 3: Build System Setup (DEVOPS)

**Worker Assignment:** `DEVOPS`
**Duration:** Week 1 (1 week)
**Branch:** `feat/rust-build-system`
**Dependencies:** None (prerequisite for Rust streams)
**Estimated Effort:** 1 week, 1 DevOps engineer

### Week 1: Maturin + CI/CD

**Task 3.1: Maturin Configuration** (1 day)
- **File:** `pyproject.toml` (UPDATE)
- **Implementation:**
  ```toml
  [build-system]
  requires = ["maturin>=1.0,<2.0"]
  build-backend = "maturin"

  [tool.maturin]
  python-source = "src"
  features = ["pyo3/extension-module"]
  ```

**Task 3.2: Workspace Configuration** (1 day)
- **File:** `Cargo.toml` (NEW, workspace root)
- **Implementation:**
  ```toml
  [workspace]
  members = [
      "src-rust/opa_engine",
      "src-rust/fast_cache",
  ]

  [profile.release]
  opt-level = 3
  lto = true
  codegen-units = 1
  ```

**Task 3.3: CI/CD Integration** (2 days)
- **File:** `.github/workflows/rust.yml` (NEW)
- **Implementation:**
  ```yaml
  name: Rust Extensions

  on: [push, pull_request]

  jobs:
    build:
      runs-on: ${{ matrix.os }}
      strategy:
        matrix:
          os: [ubuntu-latest, macos-latest, windows-latest]
          python-version: ['3.11', '3.12']

      steps:
        - uses: actions/checkout@v3

        - name: Install Rust
          uses: actions-rs/toolchain@v1
          with:
            toolchain: stable

        - name: Install Python
          uses: actions/setup-python@v4
          with:
            python-version: ${{ matrix.python-version }}

        - name: Install maturin
          run: pip install maturin

        - name: Build Rust extensions
          run: maturin develop --release

        - name: Run tests
          run: pytest tests/integration/policy/ tests/integration/cache/
  ```

**Task 3.4: Documentation** (1 day)
- **File:** `docs/development/RUST_SETUP.md` (NEW)

### Deliverables

**Code:**
- ✅ `pyproject.toml` updated for maturin
- ✅ `Cargo.toml` workspace configuration
- ✅ `.github/workflows/rust.yml` CI/CD

**Documentation:**
- ✅ `docs/development/RUST_SETUP.md`

**Acceptance:**
- [ ] `maturin develop` works locally
- [ ] CI builds Rust extensions on all platforms
- [ ] Python can import Rust modules

---

## Stream 4: Integration & A/B Testing (QA)

**Worker Assignment:** `QA`
**Duration:** Weeks 4-5 (2 weeks)
**Branch:** `feat/rust-integration`
**Dependencies:** Streams 1, 2, 3
**Estimated Effort:** 2 weeks, 1 Python developer

### Week 4-5: Integration

**Task 4.1: Feature Flags** (2 days)
- Enable/disable Rust components via config
- A/B testing framework

**Task 4.2: Gateway Integration** (3 days)
- Update Gateway to use Rust OPA + Cache
- Fallback mechanisms
- Error handling

**Task 4.3: Performance Comparison** (3 days)
- Side-by-side benchmarks
- Load testing (Python vs Rust)
- Metrics collection

**Task 4.4: Migration Guide** (1 day)
- Document rollout strategy
- Monitoring recommendations

### Deliverables

**Code:**
- ✅ Gateway using Rust components
- ✅ A/B testing framework

**Documentation:**
- ✅ `docs/deployment/RUST_MIGRATION.md`

---

## Stream 5: Documentation (DOCS)

**Worker Assignment:** `DOCS`
**Duration:** Week 6 (1 week)
**Branch:** `docs/rust-developer-guide`
**Dependencies:** Streams 1-4
**Estimated Effort:** 1 week, 1 technical writer

### Week 6: Comprehensive Documentation

**Deliverables:**
- ✅ `docs/development/RUST_DEVELOPER_GUIDE.md`
- ✅ `docs/architecture/RUST_INTEGRATION.md`
- ✅ `docs/deployment/RUST_MIGRATION.md`
- ✅ `docs/v1.4.0/RELEASE_NOTES.md`

---

## Stream 6: Performance Testing (PERF)

**Worker Assignment:** `PERF`
**Duration:** Weeks 5-6 (2 weeks)
**Branch:** `test/performance-validation`
**Dependencies:** Stream 4
**Estimated Effort:** 2 weeks, 1 QA engineer

### Weeks 5-6: Load Testing

**Task 6.1: Load Testing** (1 week)
- Simulate production load
- Compare Python vs Rust performance
- Identify bottlenecks

**Task 6.2: Profiling** (1 week)
- CPU profiling
- Memory profiling
- Latency analysis

### Deliverables

**Reports:**
- ✅ Performance test results
- ✅ Profiling analysis
- ✅ Recommendations for v1.5.0

---

## Success Metrics

| Metric | Baseline (v1.3.0) | Target (v1.4.0) | Result |
|--------|------------------|-----------------|--------|
| **OPA Evaluation Latency (p95)** | 20-50ms | <5ms | TBD |
| **Cache Latency (p95)** | 1-5ms | <0.5ms | TBD |
| **Gateway Throughput** | 850 req/s | 2,000+ req/s | TBD |
| **Memory Usage** | Baseline | <110% | TBD |
| **CPU Usage** | Baseline | <90% | TBD |
| **Test Pass Rate** | 100% | 100% | TBD |

**Gate Criteria:**
- [ ] ≥4x speedup for OPA evaluation
- [ ] ≥10x speedup for cache operations
- [ ] ≥2x throughput improvement
- [ ] No functional regressions
- [ ] 100% Python fallback compatibility

---

## Risk Management

### Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Rust learning curve** | High | Hire experienced Rust developer |
| **PyO3 compatibility issues** | Medium | Extensive testing on all platforms |
| **Performance not as expected** | High | Benchmark early, iterate on optimization |
| **Build complexity** | Medium | Comprehensive CI/CD, good documentation |

### Mitigation Strategies

**If performance gains <4x:**
- Profile Rust code for bottlenecks
- Optimize hot paths
- Consider alternative approaches (e.g., skip OPA WASM, use native Rego parser)

**If compatibility issues arise:**
- Maintain Python fallback as default initially
- Gradual rollout with feature flags
- Comprehensive platform testing

---

## Release Checklist

- [ ] All streams complete
- [ ] Performance targets met
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Migration guide ready
- [ ] Monitoring dashboards updated

**Release:** v1.4.0 - Rust Foundation
**Next:** v1.5.0 - Rust Detection Algorithms
