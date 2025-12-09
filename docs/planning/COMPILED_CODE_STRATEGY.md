# Compiled Code Strategy for SARK
## Performance Optimization Roadmap Post-v1.3.0

**Version:** 1.0
**Date:** December 9, 2025
**Target:** v1.4.0+ (Post v1.3.0)
**Status:** Planning / Future Work

---

## Executive Summary

After v1.3.0 delivers advanced security features, SARK will be feature-complete but may face performance bottlenecks under high load. This document identifies **critical hot paths** where compiled code (Rust, Go, C++) could provide 5-100x performance improvements while maintaining Python for business logic.

**Key Opportunities:**
1. **OPA Policy Evaluation** - Rust or Go (10-50x speedup)
2. **Prompt Injection Detection** - Rust (20-100x speedup for regex/entropy)
3. **Anomaly Detection** - Rust (5-10x speedup for statistical analysis)
4. **High-Performance Cache** - Rust (2-5x speedup over Redis)
5. **MCP Protocol Parsing** - Rust (10-20x speedup)
6. **Cryptographic Operations** - Rust (already using libsodium, could expand)

**Strategic Approach:**
- **Keep Python for:** API layer, business logic, orchestration
- **Use Compiled for:** CPU-intensive operations, hot paths, performance-critical components
- **Integration:** Python bindings via PyO3 (Rust), cgo (Go), or pybind11 (C++)

---

## Performance Analysis: Current State

### Current Python Performance (v1.3.0 Target)

| Component | Current Latency (p95) | Target (v1.4.0+) | Improvement Needed |
|-----------|----------------------|------------------|-------------------|
| **Gateway Authorization** | <100ms | <20ms | 5x |
| **OPA Policy Evaluation** | 20-50ms | <5ms | 4-10x |
| **Prompt Injection Detection** | N/A (v1.3.0) | <10ms | N/A |
| **Anomaly Detection** | N/A (v1.3.0) | <5ms | N/A |
| **Cache Operations** | 1-5ms | <0.5ms | 2-10x |
| **MCP Message Parsing** | 5-10ms | <1ms | 5-10x |
| **Concurrent Requests** | 850 req/s | 5,000+ req/s | 6x |

**Bottleneck Analysis:**
- **OPA Policy Evaluation:** Currently calls external OPA server (network overhead)
- **Python GIL:** Limits true parallelism for CPU-bound tasks
- **Redis Cache:** Network latency for cache operations
- **JSON Parsing:** Python JSON library relatively slow for large payloads
- **Regex Matching:** Python `re` module slower than compiled regex engines

---

## Priority 1: OPA Policy Evaluation (Rust or Go)

### Problem Statement

**Current Architecture:**
```
Python FastAPI → HTTP → OPA Server (external) → Rego Evaluation → HTTP Response
                  ↑                                              ↑
               Network RTT: 2-10ms                         Eval: 10-40ms
```

**Issues:**
- Network overhead for every authorization check
- External dependency (OPA server must be running)
- Latency accumulates: 20-50ms p95
- Cannot scale beyond single OPA instance without load balancer

### Solution: Embedded OPA Engine in Rust

**Proposed Architecture:**
```
Python FastAPI → PyO3 → Rust OPA Engine → In-Process Rego Evaluation
                  ↑                         ↑
            FFI call: <0.1ms             Eval: 1-5ms (compiled)
```

**Implementation:**
- **Language:** Rust (memory safety, performance, excellent OPA bindings)
- **Library:** `opa-wasm` or `regal` (Rego compiler in Rust)
- **Approach:** Compile Rego policies to WebAssembly, execute in Rust runtime
- **Integration:** PyO3 Python bindings

**Example Code:**

```rust
// src-rust/opa_engine/src/lib.rs
use pyo3::prelude::*;
use opa_wasm::{Runtime, Policy};

#[pyclass]
struct PolicyEngine {
    runtime: Runtime,
    policies: HashMap<String, Policy>,
}

#[pymethods]
impl PolicyEngine {
    #[new]
    fn new() -> PyResult<Self> {
        Ok(PolicyEngine {
            runtime: Runtime::new(),
            policies: HashMap::new(),
        })
    }

    fn load_policy(&mut self, name: &str, policy_wasm: &[u8]) -> PyResult<()> {
        let policy = Policy::from_wasm(policy_wasm)?;
        self.policies.insert(name.to_string(), policy);
        Ok(())
    }

    fn evaluate(&self, policy_name: &str, input: &str) -> PyResult<String> {
        let policy = self.policies.get(policy_name)
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Policy not found"))?;

        let result = self.runtime.evaluate(policy, input)?;
        Ok(serde_json::to_string(&result)?)
    }
}

#[pymodule]
fn opa_engine(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<PolicyEngine>()?;
    Ok(())
}
```

**Python Integration:**

```python
# src/sark/policy/rust_engine.py
from opa_engine import PolicyEngine  # Rust extension

class RustOPAClient:
    """High-performance OPA policy evaluation using Rust"""

    def __init__(self):
        self.engine = PolicyEngine()

    async def load_policy(self, name: str, policy_wasm: bytes):
        """Load compiled Rego policy (WebAssembly)"""
        self.engine.load_policy(name, policy_wasm)

    async def evaluate(self, policy_name: str, input_data: dict) -> dict:
        """Evaluate policy (in-process, <5ms)"""
        input_json = json.dumps(input_data)
        result_json = self.engine.evaluate(policy_name, input_json)
        return json.loads(result_json)
```

**Performance Gains:**
- **Latency:** 20-50ms → 1-5ms (4-10x improvement)
- **Throughput:** 850 req/s → 4,000+ req/s (5x improvement)
- **Reliability:** No external OPA dependency
- **Cost:** Reduced infrastructure (no separate OPA pods)

**Effort Estimate:** 2-3 weeks (Rust developer + Python integration)

---

## Priority 2: Prompt Injection Detection (Rust)

### Problem Statement

**v1.3.0 Implementation (Python):**
```python
class PromptInjectionDetector:
    INJECTION_PATTERNS = [
        r"ignore\s+(previous|all|above)\s+instructions?",
        r"you\s+are\s+now\s+(a|an)\s+",
        # ... 20+ regex patterns
    ]

    def detect(self, params: dict) -> InjectionDetectionResult:
        findings = []
        for key, value in flatten_params(params).items():
            for pattern in self.INJECTION_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE):  # SLOW!
                    findings.append(...)

            # Entropy calculation (also slow)
            entropy = self._calculate_entropy(value)
            if entropy > 4.5:
                findings.append(...)

        return InjectionDetectionResult(findings=findings)
```

**Performance Issues:**
- **Regex Matching:** Python `re` module is interpreted, slow for complex patterns
- **Entropy Calculation:** Pure Python loop over every character
- **String Operations:** Heavy string manipulation in interpreted language
- **Expected Latency:** 10-50ms for large inputs (v1.3.0 target: <10ms)

### Solution: Rust Regex Engine + Entropy Calculator

**Proposed Architecture:**
```
Python → PyO3 → Rust Detector → Compiled Regex (regex crate) → Result
                               → SIMD Entropy Calculation
```

**Implementation:**

```rust
// src-rust/injection_detector/src/lib.rs
use pyo3::prelude::*;
use regex::RegexSet;
use rayon::prelude::*;  // Parallel processing

#[pyclass]
struct InjectionDetector {
    patterns: RegexSet,
}

#[pymethods]
impl InjectionDetector {
    #[new]
    fn new(patterns: Vec<String>) -> PyResult<Self> {
        let patterns = RegexSet::new(&patterns)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
        Ok(InjectionDetector { patterns })
    }

    fn detect(&self, params: HashMap<String, String>) -> PyResult<Vec<Finding>> {
        let findings: Vec<Finding> = params.par_iter()  // Parallel!
            .flat_map(|(key, value)| {
                let mut findings = Vec::new();

                // Regex matching (compiled, fast)
                for idx in self.patterns.matches(value) {
                    findings.push(Finding {
                        severity: "high".to_string(),
                        param_name: key.clone(),
                        pattern_idx: idx,
                    });
                }

                // Entropy calculation (SIMD optimized)
                let entropy = calculate_entropy_simd(value.as_bytes());
                if entropy > 4.5 {
                    findings.push(Finding {
                        severity: "medium".to_string(),
                        param_name: key.clone(),
                        pattern_idx: 999,  // Special code for entropy
                    });
                }

                findings
            })
            .collect();

        Ok(findings)
    }
}

// SIMD-optimized entropy calculation
fn calculate_entropy_simd(data: &[u8]) -> f64 {
    // Use portable_simd for fast byte counting
    // Implementation omitted for brevity
    // 10-50x faster than Python
    0.0
}

#[pymodule]
fn injection_detector(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<InjectionDetector>()?;
    Ok(())
}
```

**Performance Gains:**
- **Regex Matching:** 20-100x faster (compiled vs interpreted)
- **Entropy Calculation:** 10-50x faster (SIMD vs Python loop)
- **Parallel Processing:** Leverages all CPU cores (bypasses GIL)
- **Latency:** 10-50ms → <1ms (10-50x improvement)

**Effort Estimate:** 1-2 weeks (Rust developer)

---

## Priority 3: Anomaly Detection (Rust)

### Problem Statement

**v1.3.0 Implementation (Python):**
```python
class BehavioralAnalyzer:
    async def detect_anomalies(self, event: AuditEvent) -> list[Anomaly]:
        baseline = await self.baseline_db.get(event.user_id)

        anomalies = []

        # Statistical calculations (slow in Python)
        event_hour = event.timestamp.hour
        if event_hour not in baseline["timing"]["typical_hours"]:
            anomalies.append(...)

        # Percentile calculations
        if event.result_size > baseline["data_volume"]["max_records"] * 2:
            anomalies.append(...)

        return anomalies
```

**Performance Issues:**
- **Statistical Calculations:** Standard deviation, percentiles, z-scores
- **Time Series Analysis:** Moving averages, trend detection
- **Machine Learning:** Future: online learning for anomaly detection
- **Expected Latency:** 5-20ms (v1.3.0 target: <5ms)

### Solution: Rust Statistical Engine

**Implementation:**

```rust
// src-rust/anomaly_detector/src/lib.rs
use pyo3::prelude::*;
use ndarray::{Array1, ArrayView1};
use statrs::statistics::Statistics;

#[pyclass]
struct AnomalyDetector {
    baseline_cache: HashMap<String, Baseline>,
}

#[derive(Clone)]
struct Baseline {
    typical_hours: Vec<u8>,
    max_records: f64,
    mean_records: f64,
    stddev_records: f64,
}

#[pymethods]
impl AnomalyDetector {
    #[new]
    fn new() -> Self {
        AnomalyDetector {
            baseline_cache: HashMap::new(),
        }
    }

    fn detect_anomalies(
        &self,
        user_id: &str,
        event_hour: u8,
        result_size: u64,
    ) -> PyResult<Vec<String>> {
        let baseline = self.baseline_cache.get(user_id)
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("No baseline"))?;

        let mut anomalies = Vec::new();

        // Timing anomaly (fast set lookup)
        if !baseline.typical_hours.contains(&event_hour) {
            anomalies.push("unusual_time".to_string());
        }

        // Statistical anomaly (z-score calculation)
        let result_size_f64 = result_size as f64;
        let z_score = (result_size_f64 - baseline.mean_records) / baseline.stddev_records;
        if z_score.abs() > 3.0 {  // 3 sigma
            anomalies.push(format!("excessive_data_access (z-score: {:.2})", z_score));
        }

        Ok(anomalies)
    }
}
```

**Performance Gains:**
- **Statistical Calculations:** 5-10x faster (native math vs Python)
- **Cache Access:** In-memory Rust HashMap vs async DB call
- **Latency:** 5-20ms → <1ms (5-20x improvement)

**Effort Estimate:** 1-2 weeks

---

## Priority 4: High-Performance In-Memory Cache (Rust)

### Problem Statement

**Current Architecture:**
```
Python → Redis (external) → Network RTT: 1-5ms
```

**Issues:**
- Network latency for every cache operation
- Serialization/deserialization overhead (pickle or JSON)
- External dependency (Redis must be running)
- Limited to single-process caching

### Solution: Embedded Rust Cache with TTL

**Implementation:**

```rust
// src-rust/fast_cache/src/lib.rs
use pyo3::prelude::*;
use std::collections::HashMap;
use std::time::{Duration, Instant};
use parking_lot::RwLock;  // Fast read-write lock

#[pyclass]
struct FastCache {
    cache: Arc<RwLock<HashMap<String, CacheEntry>>>,
    default_ttl: Duration,
}

struct CacheEntry {
    value: String,
    expires_at: Instant,
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

    fn get(&self, key: &str) -> PyResult<Option<String>> {
        let cache = self.cache.read();  // Fast read lock

        if let Some(entry) = cache.get(key) {
            if Instant::now() < entry.expires_at {
                return Ok(Some(entry.value.clone()));
            }
        }

        Ok(None)
    }

    fn set(&self, key: &str, value: &str, ttl_secs: Option<u64>) -> PyResult<()> {
        let ttl = ttl_secs
            .map(Duration::from_secs)
            .unwrap_or(self.default_ttl);

        let expires_at = Instant::now() + ttl;

        let mut cache = self.cache.write();  // Fast write lock
        cache.insert(
            key.to_string(),
            CacheEntry {
                value: value.to_string(),
                expires_at,
            },
        );

        Ok(())
    }

    fn evict_expired(&self) -> PyResult<usize> {
        let mut cache = self.cache.write();
        let now = Instant::now();

        let before_size = cache.len();
        cache.retain(|_, entry| now < entry.expires_at);
        let after_size = cache.len();

        Ok(before_size - after_size)
    }
}
```

**Performance Gains:**
- **Latency:** 1-5ms (Redis) → <0.1ms (in-memory Rust)
- **Throughput:** 10,000+ ops/sec → 1,000,000+ ops/sec (100x)
- **Reliability:** No external dependency
- **Cost:** Zero infrastructure for caching

**Trade-offs:**
- **Persistence:** No durability (Redis has AOF/RDB)
- **Sharing:** Process-local only (Redis can be shared)
- **Use Case:** Best for hot path caching where durability not required

**Effort Estimate:** 1 week

---

## Priority 5: MCP Protocol Parsing (Rust)

### Problem Statement

**Current Implementation (Python):**
```python
# JSON parsing for every MCP message
async def parse_mcp_message(raw_message: bytes) -> MCPMessage:
    data = json.loads(raw_message)  # Python json.loads (slow)

    # Pydantic validation (relatively slow for large schemas)
    return MCPMessage(**data)
```

**Performance Issues:**
- **JSON Parsing:** Python `json.loads` slower than native parsers
- **Validation:** Pydantic model validation has overhead
- **Large Payloads:** Tools with large parameter schemas (10KB+)
- **Throughput:** 850 req/s bottleneck partially due to parsing

### Solution: Rust JSON Parser with Zero-Copy Deserialization

**Implementation:**

```rust
// src-rust/mcp_parser/src/lib.rs
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use serde_json;

#[derive(Deserialize, Serialize, Clone)]
#[pyclass]
struct MCPMessage {
    #[pyo3(get)]
    jsonrpc: String,
    #[pyo3(get)]
    method: String,
    #[pyo3(get)]
    params: String,  // Keep as JSON string for Python side
}

#[pymethods]
impl MCPMessage {
    #[staticmethod]
    fn parse(raw_message: &[u8]) -> PyResult<Self> {
        let msg: MCPMessage = serde_json::from_slice(raw_message)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
        Ok(msg)
    }
}
```

**Performance Gains:**
- **Parsing:** 5-10x faster (serde_json vs Python json)
- **Validation:** Basic schema validation in Rust
- **Latency:** 5-10ms → <1ms (5-10x improvement)

**Effort Estimate:** 1 week

---

## Priority 6: Cryptographic Operations (Expand libsodium usage)

### Current State

Already using libsodium for some crypto operations, but could expand:

**Opportunities:**
- JWT signature verification (currently Python jose/jwt)
- SAML signature verification (currently Python xmlsec)
- API key hashing (currently Python bcrypt)
- Session token encryption

**Potential Library:** `ring` (Rust crypto library)

**Performance Gains:** 2-5x for crypto operations

**Effort Estimate:** 2 weeks

---

## Implementation Strategy

### Phase 1: v1.4.0 - Foundation (2-3 months)

**Goals:**
- Prove Rust integration works well
- Target highest-impact components
- Establish patterns for future work

**Components:**
1. **OPA Engine (Rust)** - Biggest latency win
2. **Fast Cache (Rust)** - Biggest throughput win
3. **Build System Setup** - maturin, PyO3, CI/CD integration

**Deliverables:**
- `src-rust/opa_engine/` - Rust OPA bindings
- `src-rust/fast_cache/` - In-memory cache
- `pyproject.toml` updated for Rust extensions
- Documentation for Rust development

**Success Metrics:**
- Gateway authorization: <20ms p95 (vs <100ms)
- Cache operations: <0.5ms (vs 1-5ms)
- Throughput: 2,000+ req/s (vs 850 req/s)

### Phase 2: v1.5.0 - Advanced Detection (2 months)

**Components:**
1. **Prompt Injection Detector (Rust)**
2. **Anomaly Detector (Rust)**
3. **MCP Parser (Rust)**

**Deliverables:**
- `src-rust/injection_detector/`
- `src-rust/anomaly_detector/`
- `src-rust/mcp_parser/`

**Success Metrics:**
- Prompt injection detection: <1ms
- Anomaly detection: <1ms
- MCP parsing: <1ms
- Throughput: 5,000+ req/s

### Phase 3: v1.6.0+ - Full Optimization (Ongoing)

**Components:**
- Crypto operations (Rust ring)
- Additional hot paths identified via profiling
- Potential: Gateway transport layer in Rust

---

## Technology Selection

### Rust (Recommended Primary Choice)

**Pros:**
- ✅ Excellent Python bindings (PyO3)
- ✅ Memory safety without GC overhead
- ✅ Best-in-class performance (often faster than C++)
- ✅ Great ecosystem (regex, serde, rayon, etc.)
- ✅ Modern tooling (cargo, rustfmt, clippy)
- ✅ Growing adoption in Python ecosystem (pydantic-core, ruff, etc.)

**Cons:**
- ❌ Learning curve for team
- ❌ Longer compile times than Go
- ❌ More complex than Go

**Use Cases:** OPA engine, detection algorithms, parsers, cache

### Go (Alternative for Some Components)

**Pros:**
- ✅ Simpler than Rust
- ✅ Fast compile times
- ✅ Good for concurrent I/O
- ✅ Easier to learn

**Cons:**
- ❌ GC overhead (though low-latency GC in recent versions)
- ❌ Python bindings less mature (cgo)
- ❌ Slightly slower than Rust for CPU-bound work

**Use Cases:** MCP protocol implementation, network I/O

### C++ (Not Recommended)

**Pros:**
- ✅ Maximum performance
- ✅ Mature ecosystem

**Cons:**
- ❌ Memory safety issues
- ❌ Complex Python bindings (pybind11)
- ❌ Harder to maintain
- ❌ Rust achieves similar performance with better safety

**Use Cases:** None (Rust preferred)

---

## Build System Integration

### Directory Structure

```
sark/
├── src/
│   └── sark/          # Python code
├── src-rust/          # Rust code
│   ├── opa_engine/
│   │   ├── Cargo.toml
│   │   └── src/
│   │       └── lib.rs
│   ├── fast_cache/
│   ├── injection_detector/
│   └── ...
├── pyproject.toml     # Python + Rust build config
└── Cargo.toml         # Workspace root
```

### Build Configuration

**`pyproject.toml`:**
```toml
[build-system]
requires = ["maturin>=1.0,<2.0"]
build-backend = "maturin"

[project]
name = "sark"
# ...

[tool.maturin]
python-source = "src"
module-name = "sark._rust"
bindings = "pyo3"
```

**`Cargo.toml` (workspace root):**
```toml
[workspace]
members = [
    "src-rust/opa_engine",
    "src-rust/fast_cache",
    "src-rust/injection_detector",
    "src-rust/anomaly_detector",
    "src-rust/mcp_parser",
]
```

### CI/CD Integration

**GitHub Actions:**
```yaml
name: Build with Rust Extensions

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install Rust
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable

      - name: Install Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install maturin
        run: pip install maturin

      - name: Build Rust extensions
        run: maturin develop

      - name: Run tests
        run: pytest
```

---

## Migration Strategy

### Gradual Adoption (Recommended)

**Phase 1: Opt-In Feature Flag**
```python
# src/sark/config/settings.py
class Settings(BaseSettings):
    use_rust_opa: bool = False  # Feature flag
    use_rust_cache: bool = False
    use_rust_injection_detector: bool = False
```

**Phase 2: A/B Testing**
```python
# Compare Python vs Rust performance
if settings.use_rust_opa:
    opa_client = RustOPAClient()
else:
    opa_client = PythonOPAClient()

# Measure latency difference
with metrics.timer("opa_evaluation"):
    result = await opa_client.evaluate(...)
```

**Phase 3: Default to Rust (Fallback to Python)**
```python
try:
    from sark._rust import opa_engine
    USE_RUST_OPA = True
except ImportError:
    USE_RUST_OPA = False
    logger.warning("Rust OPA engine not available, using Python fallback")

if USE_RUST_OPA:
    opa_client = RustOPAClient()
else:
    opa_client = PythonOPAClient()
```

---

## Cost-Benefit Analysis

### Development Costs

| Component | Effort (Weeks) | Developer Cost | Infrastructure Savings (Annual) |
|-----------|---------------|----------------|--------------------------------|
| **OPA Engine** | 2-3 | $15,000 | $5,000 (fewer OPA pods) |
| **Fast Cache** | 1 | $5,000 | $3,000 (no Redis) |
| **Injection Detector** | 1-2 | $7,500 | $0 |
| **Anomaly Detector** | 1-2 | $7,500 | $0 |
| **MCP Parser** | 1 | $5,000 | $0 |
| **Total** | 6-9 weeks | $40,000 | $8,000/year |

**Payback Period:** ~5 years on infrastructure savings alone

**Additional Benefits (Not Quantified):**
- Improved user experience (lower latency)
- Higher throughput (more requests per instance)
- Better resource utilization (lower CPU usage)
- Competitive advantage (faster than competitors)

### When NOT to Use Compiled Code

**Keep Python for:**
- ❌ **Business Logic:** Authorization policies (keep in Rego/Python)
- ❌ **API Layer:** FastAPI endpoints (well-optimized already)
- ❌ **Database Operations:** SQLAlchemy (I/O bound, not CPU bound)
- ❌ **Orchestration:** Czarina workflows (flexibility > performance)
- ❌ **Infrequent Operations:** One-time setup, admin tasks

**Only Use Compiled Code for:**
- ✅ **Hot Paths:** Request path operations (>1000 req/s)
- ✅ **CPU-Intensive:** Regex, math, parsing, crypto
- ✅ **Performance-Critical:** <10ms latency requirements
- ✅ **Proven Bottlenecks:** Identified via profiling

---

## Profiling & Measurement

### Identify Hot Paths (Pre-Implementation)

**Python Profiling:**
```python
import cProfile
import pstats

# Profile authorization flow
profiler = cProfile.Profile()
profiler.enable()

# Run 1000 authorization requests
for _ in range(1000):
    await authorize_gateway_request(...)

profiler.disable()

# Print top 20 time consumers
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

**Expected Output:**
```
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
     1000    2.345    0.002   15.234    0.015 policy_service.py:42(evaluate)
     1000    1.876    0.002   12.456    0.012 httpx/_client.py:123(request)
     1000    0.987    0.001    8.234    0.008 json/__init__.py:234(loads)
     ...
```

**Decision Criteria:**
- **cumtime >5 seconds** for 1000 calls → High-priority candidate
- **tottime >1 second** → CPU-bound (good for Rust)
- **I/O-bound** (network, disk) → Not suitable for Rust

### Post-Implementation Benchmarking

**Compare Python vs Rust:**
```python
import timeit

# Benchmark Python implementation
python_time = timeit.timeit(
    lambda: python_opa_client.evaluate(...),
    number=10000
)

# Benchmark Rust implementation
rust_time = timeit.timeit(
    lambda: rust_opa_client.evaluate(...),
    number=10000
)

speedup = python_time / rust_time
print(f"Rust is {speedup:.1f}x faster")
```

---

## Team Readiness

### Skills Required

**For Rust Development:**
- ✅ Rust programming (intermediate level)
- ✅ PyO3 Python bindings
- ✅ Performance optimization mindset
- ✅ Testing in both Rust and Python

**Hiring/Training Options:**
1. **Hire Rust Developer:** 1 FTE for v1.4.0 development
2. **Train Existing Team:** 1-2 month ramp-up for Python developers
3. **Consultant:** Bring in Rust expert for kickoff, train team

**Recommended:** Hire 1 Rust developer for v1.4.0, cross-train 1-2 Python developers

---

## Conclusion

**After v1.3.0, compiled code (Rust) makes sense for:**

1. **✅ OPA Policy Evaluation** - Biggest win (5-10x latency, 5x throughput)
2. **✅ Prompt Injection Detection** - v1.3.0 feature, 10-50x speedup
3. **✅ Anomaly Detection** - v1.3.0 feature, 5-10x speedup
4. **✅ High-Performance Cache** - Replace Redis for hot paths
5. **✅ MCP Protocol Parsing** - 5-10x parsing speedup

**Timeline:**
- **v1.4.0 (Q2 2026):** OPA + Cache (foundation)
- **v1.5.0 (Q3 2026):** Detection algorithms + Parser
- **v1.6.0+ (Q4 2026+):** Additional optimizations as needed

**Investment:**
- **Upfront:** ~$40,000 development (6-9 weeks)
- **Ongoing:** 1 Rust developer on team
- **Returns:** 5-10x performance improvement, $8K/year infrastructure savings, improved UX

**Recommendation:** Target v1.4.0 for initial Rust integration (OPA + Cache), measure impact, expand from there.
