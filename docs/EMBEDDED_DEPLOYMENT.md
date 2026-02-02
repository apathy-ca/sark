# SARK Embedded/Lightweight Deployment Guide

**Document Version:** 1.0
**Last Updated:** 2026-02-01
**Audience:** Developers deploying SARK components on resource-constrained systems

---

## Overview

While SARK is designed for enterprise-scale deployments (50K+ users, Kubernetes), its Rust components can be used in resource-constrained environments like:

- Home routers (OPNsense, pfSense)
- Edge devices
- IoT gateways
- Single-board computers (Raspberry Pi)
- Containers with strict resource limits

This guide covers how to use SARK's components efficiently in these scenarios.

---

## Resource Requirements Comparison

| Environment | CPU | RAM | Storage | Example |
|-------------|-----|-----|---------|---------|
| **Enterprise SARK** | 4+ cores | 8GB+ | 20GB+ | Kubernetes cluster |
| **Lightweight SARK** | 2 cores | 2GB | 5GB | Small VM/container |
| **Embedded** | 1 core | 512MB | 1GB | Home router |
| **Minimal** | 1 core | 256MB | 500MB | Edge device |

---

## What You Can Use

### Rust Components (Standalone)

These work independently without the full SARK stack:

| Component | Binary Size | Memory | Dependencies |
|-----------|-------------|--------|--------------|
| `sark-opa` | ~300KB | 5-20MB | None (statically linked) |
| `sark-cache` | ~150KB | Scales with entries | None |
| Combined | ~1.8MB | 10-50MB | None |

### What You Don't Need

For embedded deployments, you can skip:

- PostgreSQL (use SQLite)
- Valkey/Redis (use sark-cache)
- Kafka (use SQLite audit log)
- Kong (direct HTTP)
- Kubernetes infrastructure
- Full Python SARK application

---

## Architecture for Embedded Systems

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Application                          │
│              (Python, Rust, or other language)               │
├─────────────────────────────────────────────────────────────┤
│                    Rust Components                           │
│  ┌─────────────────────┐  ┌─────────────────────────────┐   │
│  │      sark-opa       │  │        sark-cache           │   │
│  │  Policy Evaluation  │  │     In-Memory Cache         │   │
│  │   (regorus-based)   │  │    (dashmap-based)          │   │
│  └─────────────────────┘  └─────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                     SQLite                                   │
│            (audit logs, configuration)                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Options

### Option 1: Pure Rust Binary

Best for maximum performance and minimal footprint.

```rust
// Cargo.toml
[package]
name = "my-gateway"
version = "0.1.0"

[dependencies]
sark-opa = { git = "https://github.com/your-org/sark", branch = "main" }
sark-cache = { git = "https://github.com/your-org/sark", branch = "main" }
tokio = { version = "1", features = ["rt-multi-thread", "macros"] }
hyper = { version = "1", features = ["server", "http1"] }

# Optimize for size
[profile.release]
opt-level = "z"      # Optimize for size
lto = true           # Link-time optimization
codegen-units = 1    # Single codegen unit
strip = true         # Strip symbols
panic = "abort"      # Smaller panic handling
```

```rust
// src/main.rs
use sark_opa::engine::OPAEngine;
use sark_cache::lru_ttl::LRUTTLCache;

#[tokio::main]
async fn main() {
    // Initialize OPA engine (5-10MB memory)
    let mut opa = OPAEngine::new().expect("Failed to create OPA engine");

    // Load policies from files
    let policy = std::fs::read_to_string("/etc/my-gateway/policies/main.rego")
        .expect("Failed to read policy");
    opa.load_policy("main".to_string(), policy).expect("Failed to load policy");

    // Initialize cache (memory scales with entries)
    // 1000 entries * ~1KB each = ~1MB
    let cache = LRUTTLCache::new(1000, 3600);

    // Start your HTTP server...
}
```

**Binary size:** ~1.5-2MB (stripped, release build)
**Memory usage:** 10-30MB typical

### Option 2: Python with Rust Extensions

Good balance of flexibility and performance.

```python
# requirements.txt
# Only install what you need
pydantic>=2.0
pyyaml>=6.0

# Build sark-opa and sark-cache locally
# pip install maturin && maturin develop
```

```python
# gateway.py
import json
from pathlib import Path

# Import Rust components
try:
    from sark._rust import RustOPAEngine, RustCache, RUST_AVAILABLE
except ImportError:
    # Build with: cd /path/to/sark && maturin develop
    raise RuntimeError("Rust extensions required. Run 'maturin develop' in SARK directory.")

class LightweightGateway:
    def __init__(self, policy_dir: Path, cache_size: int = 1000, cache_ttl: int = 3600):
        # Initialize OPA engine
        self.opa = RustOPAEngine()

        # Load policies
        for policy_file in policy_dir.glob("*.rego"):
            policy_name = policy_file.stem
            policy_content = policy_file.read_text()
            self.opa.load_policy(policy_name, policy_content)

        # Initialize cache
        self.cache = RustCache(max_size=cache_size, ttl_secs=cache_ttl)

    def evaluate(self, request: dict) -> dict:
        # Check cache first
        cache_key = self._make_cache_key(request)
        cached = self.cache.get(cache_key)
        if cached:
            return json.loads(cached)

        # Evaluate policy
        result = self.opa.evaluate("data.gateway.decision", request)

        # Cache result
        self.cache.set(cache_key, json.dumps(result))

        return result

    def _make_cache_key(self, request: dict) -> str:
        # Create deterministic cache key
        return f"{request.get('user', '')}:{request.get('action', '')}:{request.get('resource', '')}"
```

**Memory usage:** 30-50MB (Python overhead + Rust components)

### Option 3: Rust Library in Other Languages

Use sark-opa/sark-cache from any language via C FFI.

```rust
// Create C-compatible API
// rust/sark-opa-ffi/src/lib.rs
use std::ffi::{CStr, CString};
use std::os::raw::c_char;
use sark_opa::engine::OPAEngine;

static mut ENGINE: Option<OPAEngine> = None;

#[no_mangle]
pub extern "C" fn sark_opa_init() -> i32 {
    unsafe {
        match OPAEngine::new() {
            Ok(engine) => {
                ENGINE = Some(engine);
                0
            }
            Err(_) => -1,
        }
    }
}

#[no_mangle]
pub extern "C" fn sark_opa_load_policy(name: *const c_char, rego: *const c_char) -> i32 {
    unsafe {
        let name = CStr::from_ptr(name).to_string_lossy().into_owned();
        let rego = CStr::from_ptr(rego).to_string_lossy().into_owned();

        if let Some(ref mut engine) = ENGINE {
            match engine.load_policy(name, rego) {
                Ok(_) => 0,
                Err(_) => -1,
            }
        } else {
            -2
        }
    }
}

#[no_mangle]
pub extern "C" fn sark_opa_evaluate(query: *const c_char, input_json: *const c_char) -> *mut c_char {
    // ... implementation
}
```

---

## Memory Optimization

### Policy Engine Memory

```rust
// Policies consume memory when compiled
// Typical sizes:
// - Simple policy (10 rules): ~100KB
// - Medium policy (50 rules): ~500KB
// - Complex policy (200 rules): ~2MB

// Strategies to reduce memory:
// 1. Combine related policies into one file
// 2. Use simpler rule structures
// 3. Avoid large data structures in policies
```

### Cache Memory

```rust
// Cache memory = entries * average_entry_size
//
// Example calculations:
// - 1,000 entries * 500 bytes = 500KB
// - 10,000 entries * 500 bytes = 5MB
// - 100,000 entries * 500 bytes = 50MB

// For 512MB systems, recommend:
let cache = LRUTTLCache::new(
    5000,    // max_entries - keep small
    1800,    // ttl_seconds - 30 minutes to allow reuse
);
```

### String Interning

```rust
// For repeated strings (usernames, roles), consider interning
use std::collections::HashSet;
use std::sync::Arc;

struct InternedStrings {
    strings: HashSet<Arc<str>>,
}

impl InternedStrings {
    fn intern(&mut self, s: &str) -> Arc<str> {
        if let Some(existing) = self.strings.get(s) {
            existing.clone()
        } else {
            let arc: Arc<str> = s.into();
            self.strings.insert(arc.clone());
            arc
        }
    }
}
```

---

## Binary Size Optimization

### Cargo.toml Settings

```toml
[profile.release]
opt-level = "z"          # Optimize for size (vs "3" for speed)
lto = true               # Link-time optimization
codegen-units = 1        # Single codegen unit (slower build, smaller binary)
strip = true             # Strip debug symbols
panic = "abort"          # Smaller panic handling (no unwinding)

[profile.release.package."*"]
opt-level = "z"
```

### Feature Flags

```toml
# Disable unused features
[dependencies]
serde = { version = "1.0", default-features = false, features = ["derive"] }
tokio = { version = "1", default-features = false, features = ["rt", "macros"] }
```

### Expected Sizes

| Configuration | Binary Size |
|---------------|-------------|
| Debug build | ~15MB |
| Release (default) | ~5MB |
| Release (size optimized) | ~1.8MB |
| Release + UPX compressed | ~700KB |

```bash
# Compress with UPX (if available)
upx --best target/release/my-gateway
```

---

## SQLite for Persistence

Replace PostgreSQL with SQLite for embedded systems:

```python
# audit.py
import sqlite3
from datetime import datetime
from pathlib import Path

class SQLiteAuditLog:
    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._init_schema()

    def _init_schema(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_id TEXT,
                action TEXT NOT NULL,
                resource TEXT,
                decision TEXT NOT NULL,
                reason TEXT,
                metadata TEXT
            )
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp
            ON audit_log(timestamp)
        """)
        self.conn.commit()

    def log(self, user_id: str, action: str, resource: str,
            decision: str, reason: str = None, metadata: dict = None):
        self.conn.execute("""
            INSERT INTO audit_log (timestamp, user_id, action, resource, decision, reason, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            user_id,
            action,
            resource,
            decision,
            reason,
            json.dumps(metadata) if metadata else None,
        ))
        self.conn.commit()
```

---

## Example: Home Router Gateway

Based on the YORI project pattern:

```
/usr/local/
├── bin/
│   └── yori-proxy          # Rust binary (~1.8MB)
├── etc/yori/
│   ├── yori.conf           # YAML configuration
│   └── policies/
│       ├── default.rego    # Default policy
│       └── custom.rego     # User policies
├── var/yori/
│   └── yori.db             # SQLite database
└── share/yori/
    └── block.html          # Block page template
```

```yaml
# /usr/local/etc/yori/yori.conf
mode: advisory  # observe | advisory | enforce

proxy:
  listen: "0.0.0.0:8443"
  upstream_timeout: 30

cache:
  max_entries: 5000
  ttl_seconds: 1800

database:
  path: /usr/local/var/yori/yori.db

policies:
  directory: /usr/local/etc/yori/policies
```

---

## Performance Tuning for Constrained Systems

### Reduce Policy Evaluation Frequency

```python
# Cache aggressively
CACHE_TTL = 1800  # 30 minutes for stable decisions

# Batch similar requests
def batch_evaluate(requests: list[dict]) -> list[dict]:
    # Group by user+action pattern
    groups = group_by_pattern(requests)
    results = []
    for pattern, group in groups.items():
        # Evaluate once per pattern
        result = opa.evaluate("data.gateway.decision", group[0])
        results.extend([result] * len(group))
    return results
```

### Lazy Policy Loading

```python
class LazyOPAEngine:
    def __init__(self, policy_dir: Path):
        self.policy_dir = policy_dir
        self._engine = None
        self._loaded_policies = set()

    @property
    def engine(self):
        if self._engine is None:
            self._engine = RustOPAEngine()
        return self._engine

    def ensure_policy(self, name: str):
        if name not in self._loaded_policies:
            policy_file = self.policy_dir / f"{name}.rego"
            if policy_file.exists():
                self.engine.load_policy(name, policy_file.read_text())
                self._loaded_policies.add(name)
```

### Memory-Mapped Policy Files

```rust
// For very large policy sets, memory-map instead of loading
use memmap2::Mmap;

fn load_policy_mmap(path: &Path) -> Result<String, std::io::Error> {
    let file = std::fs::File::open(path)?;
    let mmap = unsafe { Mmap::map(&file)? };
    Ok(String::from_utf8_lossy(&mmap).into_owned())
}
```

---

## Monitoring on Constrained Systems

### Lightweight Metrics

```python
# Simple in-memory metrics (no Prometheus overhead)
from dataclasses import dataclass, field
from time import time

@dataclass
class SimpleMetrics:
    requests_total: int = 0
    requests_allowed: int = 0
    requests_denied: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    last_evaluation_ms: float = 0
    _start_time: float = field(default_factory=time)

    def record_request(self, allowed: bool, cached: bool, duration_ms: float):
        self.requests_total += 1
        if allowed:
            self.requests_allowed += 1
        else:
            self.requests_denied += 1
        if cached:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        self.last_evaluation_ms = duration_ms

    def to_dict(self) -> dict:
        uptime = time() - self._start_time
        return {
            "uptime_seconds": uptime,
            "requests_total": self.requests_total,
            "requests_per_second": self.requests_total / uptime if uptime > 0 else 0,
            "allow_rate": self.requests_allowed / self.requests_total if self.requests_total > 0 else 0,
            "cache_hit_rate": self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0,
            "last_evaluation_ms": self.last_evaluation_ms,
        }
```

### Health Check Endpoint

```rust
// Simple health check for monitoring
async fn health_check(metrics: Arc<Metrics>) -> impl warp::Reply {
    let stats = metrics.to_json();
    warp::reply::json(&serde_json::json!({
        "status": "healthy",
        "version": env!("CARGO_PKG_VERSION"),
        "metrics": stats,
    }))
}
```

---

## See Also

- [Rust PyO3 Integration Guide](RUST_PYO3_INTEGRATION.md) - Building Rust extensions
- [Standalone Crates Guide](STANDALONE_CRATES.md) - Using components independently
- [Cross-Compilation Guide](CROSS_COMPILATION.md) - Building for other platforms
- [YORI Project](https://github.com/apathy-ca/yori) - Reference home gateway implementation
