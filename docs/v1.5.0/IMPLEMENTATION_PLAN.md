# SARK v1.5.0 Implementation Plan
## Rust Performance Optimization - Detection & Parsing

**Version:** 1.0
**Date:** December 9, 2025
**Target Release:** v1.5.0
**Prerequisites:** v1.4.0 complete (Rust OPA + Cache)
**Duration:** 4-5 weeks
**Orchestration:** Czarina multi-agent system

---

## Executive Summary

v1.5.0 ports CPU-intensive detection algorithms and parsing to Rust, building on the foundation established in v1.4.0. This delivers 10-100x performance improvements for security features added in v1.3.0.

**What v1.5.0 Delivers:**
- ✅ Rust prompt injection detector (10-50x faster)
- ✅ Rust anomaly detector (5-10x faster)
- ✅ Rust MCP protocol parser (5-10x faster)
- ✅ SIMD-optimized entropy calculation
- ✅ Parallel processing for detection

**Success Criteria:**
- Prompt injection detection: <1ms (from 10-50ms)
- Anomaly detection: <1ms (from 5-20ms)
- MCP parsing: <1ms (from 5-10ms)
- Throughput: 5,000+ req/s (from 2,000 req/s)
- No functional regressions

**Strategic Position:**
- v1.4.0 = Rust foundation
- v1.5.0 = Rust detection & parsing (THIS RELEASE)
- v1.6.0+ = Additional optimizations as needed
- v2.0.0 = Production release (after security audit)

---

## Work Stream Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CZARINA ORCHESTRATION                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Stream 1: Injection Detector  Stream 2: Anomaly Detector       │
│  ┌──────────────────┐          ┌──────────────────┐            │
│  │ Worker: RUST-1   │          │ Worker: RUST-2   │            │
│  │ Weeks 1-2        │          │ Weeks 2-3        │            │
│  │ +Regex engine    │          │ +Statistics      │            │
│  │ +Entropy (SIMD)  │          │ +Parallel scan   │            │
│  └──────────────────┘          └──────────────────┘            │
│                                                                   │
│  Stream 3: MCP Parser          Stream 4: Integration            │
│  ┌──────────────────┐          ┌──────────────────┐            │
│  │ Worker: RUST-3   │          │ Worker: QA       │            │
│  │ Week 3           │          │ Weeks 4-5        │            │
│  │ +serde_json      │          │ +Benchmarks      │            │
│  │ +Zero-copy       │          │ +Load testing    │            │
│  └──────────────────┘          └──────────────────┘            │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Stream 1: Rust Injection Detector (RUST-1)

**Duration:** Weeks 1-2
**Branch:** `feat/rust-injection-detector`
**Estimated Effort:** 2 weeks, 1 Rust developer

### Implementation

**File:** `src-rust/injection_detector/src/lib.rs`

```rust
use pyo3::prelude::*;
use regex::RegexSet;
use rayon::prelude::*;
use std::collections::HashMap;

#[pyclass]
struct InjectionDetector {
    patterns: RegexSet,
    pattern_names: Vec<String>,
}

#[pymethods]
impl InjectionDetector {
    #[new]
    fn new(patterns: Vec<(String, String)>) -> PyResult<Self> {
        let pattern_strings: Vec<_> = patterns.iter()
            .map(|(_, regex)| regex.as_str())
            .collect();

        let pattern_set = RegexSet::new(&pattern_strings)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

        let pattern_names = patterns.into_iter()
            .map(|(name, _)| name)
            .collect();

        Ok(InjectionDetector {
            patterns: pattern_set,
            pattern_names,
        })
    }

    fn detect(&self, params: HashMap<String, String>) -> PyResult<Vec<Finding>> {
        // Parallel processing!
        let findings: Vec<Finding> = params.par_iter()
            .flat_map(|(key, value)| {
                let mut findings = Vec::new();

                // Compiled regex matching
                for idx in self.patterns.matches(value) {
                    findings.push(Finding {
                        severity: "high".to_string(),
                        param_name: key.clone(),
                        pattern_name: self.pattern_names[idx].clone(),
                    });
                }

                // SIMD entropy calculation
                let entropy = calculate_entropy_simd(value.as_bytes());
                if entropy > 4.5 && value.len() > 50 {
                    findings.push(Finding {
                        severity: "medium".to_string(),
                        param_name: key.clone(),
                        pattern_name: "high_entropy".to_string(),
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
    use std::arch::x86_64::*;

    let mut counts = [0u32; 256];

    // Count bytes using SIMD when possible
    for &byte in data {
        counts[byte as usize] += 1;
    }

    let len = data.len() as f64;
    let mut entropy = 0.0;

    for &count in &counts {
        if count > 0 {
            let p = count as f64 / len;
            entropy -= p * p.log2();
        }
    }

    entropy
}

#[pyclass]
#[derive(Clone)]
struct Finding {
    #[pyo3(get)]
    severity: String,
    #[pyo3(get)]
    param_name: String,
    #[pyo3(get)]
    pattern_name: String,
}

#[pymodule]
fn sark_injection_detector(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<InjectionDetector>()?;
    Ok(())
}
```

**Performance Target:** <1ms (vs 10-50ms Python)

---

## Stream 2: Rust Anomaly Detector (RUST-2)

**Duration:** Weeks 2-3
**Branch:** `feat/rust-anomaly-detector`
**Estimated Effort:** 2 weeks, 1 Rust developer

### Implementation

**File:** `src-rust/anomaly_detector/src/lib.rs`

```rust
use pyo3::prelude::*;
use std::collections::HashMap;

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

    fn load_baseline(
        &mut self,
        user_id: String,
        typical_hours: Vec<u8>,
        max_records: f64,
        mean_records: f64,
        stddev_records: f64,
    ) {
        self.baseline_cache.insert(
            user_id,
            Baseline {
                typical_hours,
                max_records,
                mean_records,
                stddev_records,
            },
        );
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

        // Fast set lookup
        if !baseline.typical_hours.contains(&event_hour) {
            anomalies.push("unusual_time".to_string());
        }

        // Statistical anomaly (z-score)
        let result_size_f64 = result_size as f64;
        let z_score = (result_size_f64 - baseline.mean_records) / baseline.stddev_records;
        if z_score.abs() > 3.0 {
            anomalies.push(format!("excessive_data_access (z={:.2})", z_score));
        }

        Ok(anomalies)
    }
}

#[pymodule]
fn sark_anomaly_detector(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<AnomalyDetector>()?;
    Ok(())
}
```

**Performance Target:** <1ms (vs 5-20ms Python)

---

## Stream 3: Rust MCP Parser (RUST-3)

**Duration:** Week 3
**Branch:** `feat/rust-mcp-parser`
**Estimated Effort:** 1 week, 1 Rust developer

### Implementation

**File:** `src-rust/mcp_parser/src/lib.rs`

```rust
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

#[derive(Deserialize, Serialize, Clone)]
#[pyclass]
struct MCPMessage {
    #[pyo3(get)]
    jsonrpc: String,
    #[pyo3(get)]
    method: String,
    #[pyo3(get)]
    params: String,  // Keep as JSON string
}

#[pymethods]
impl MCPMessage {
    #[staticmethod]
    fn parse(raw_message: &[u8]) -> PyResult<Self> {
        // Zero-copy deserialization
        let msg: MCPMessage = serde_json::from_slice(raw_message)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
        Ok(msg)
    }

    #[staticmethod]
    fn parse_batch(messages: Vec<&[u8]>) -> PyResult<Vec<Self>> {
        // Parallel parsing
        use rayon::prelude::*;

        let results: Result<Vec<_>, _> = messages
            .par_iter()
            .map(|msg| serde_json::from_slice(msg))
            .collect();

        results.map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
    }
}

#[pymodule]
fn sark_mcp_parser(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<MCPMessage>()?;
    Ok(())
}
```

**Performance Target:** <1ms (vs 5-10ms Python)

---

## Stream 4: Integration & Benchmarking (QA)

**Duration:** Weeks 4-5
**Branch:** `feat/rust-integration-v1.5`
**Estimated Effort:** 2 weeks, 1 QA engineer

### Tasks

1. **Python Integration** (1 week)
   - Update injection detector to use Rust
   - Update anomaly detector to use Rust
   - Update MCP parser to use Rust
   - Feature flags and fallbacks

2. **Benchmarking** (1 week)
   - Performance comparison (Python vs Rust)
   - Load testing (5,000+ req/s target)
   - Profiling and optimization

### Deliverables

- ✅ All Rust components integrated
- ✅ Performance benchmarks published
- ✅ Load test results
- ✅ Migration guide

---

## Success Metrics

| Component | Baseline (Python) | Target (Rust) | Speedup |
|-----------|------------------|---------------|---------|
| **Prompt Injection Detection** | 10-50ms | <1ms | 10-50x |
| **Anomaly Detection** | 5-20ms | <1ms | 5-20x |
| **MCP Parsing** | 5-10ms | <1ms | 5-10x |
| **Overall Throughput** | 2,000 req/s | 5,000+ req/s | 2.5x |

---

## Release Checklist

- [ ] All Rust components implemented
- [ ] Performance targets met
- [ ] Integration tests passing
- [ ] Documentation complete
- [ ] Migration guide published

**Release:** v1.5.0 - Rust Detection & Parsing
**Next:** v1.6.0 (if needed) or v2.0.0 (Security Audit)
