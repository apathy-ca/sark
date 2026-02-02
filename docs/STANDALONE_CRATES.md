# Using grid-opa and grid-cache as Standalone Crates

**Document Version:** 2.0
**Last Updated:** 2026-02-01
**Audience:** Developers wanting to use SARK's Rust components independently

---

## Overview

> **Migration Note (v1.6.0):** The Rust components have been migrated to **[GRID Core](https://github.com/apathy-ca/grid-core)**, a shared library used by both SARK and [YORI](https://github.com/apathy-ca/yori). The crates are now named `grid-opa` and `grid-cache` instead of `grid-opa` and `grid-cache`.

SARK's performance-critical components are available as standalone Rust crates from GRID Core:

| Crate | Purpose | Key Dependency |
|-------|---------|----------------|
| `grid-opa` | Embedded OPA policy evaluation | [regorus](https://crates.io/crates/regorus) |
| `grid-cache` | Thread-safe LRU+TTL cache | [dashmap](https://crates.io/crates/dashmap) |

These can be used:
- In your own Rust applications
- Via PyO3 bindings in Python applications
- Via C FFI in other languages

---

## Adding as Dependencies

### From Git (Recommended)

```toml
# Cargo.toml
[dependencies]
grid-opa = { git = "https://github.com/apathy-ca/grid-core" }
grid-cache = { git = "https://github.com/apathy-ca/grid-core" }
```

### From Local Path

```toml
# Cargo.toml (if you have grid-core cloned locally)
[dependencies]
grid-opa = { path = "../grid-core/crates/grid-opa" }
grid-cache = { path = "../grid-core/crates/grid-cache" }
```

### Feature Flags

```toml
# grid-opa with Python bindings enabled
grid-opa = { git = "...", features = ["python"] }

# grid-cache with Python bindings enabled
grid-cache = { git = "...", features = ["python"] }

# Pure Rust (no Python bindings)
grid-opa = { git = "..." }
grid-cache = { git = "..." }
```

---

## grid-opa: OPA Policy Engine

### Features

- **Embedded OPA**: No external OPA server required
- **High Performance**: 4-10x faster than HTTP-based OPA
- **Low Latency**: <5ms p95 for policy evaluation
- **Thread-Safe**: Safe for concurrent use
- **Full Rego Support**: Via the regorus engine

### Basic Usage (Rust)

```rust
use grid_opa::engine::OPAEngine;
use grid_opa::error::Result;
use regorus::Value;
use std::collections::BTreeMap;
use std::sync::Arc;

fn main() -> Result<()> {
    // Create engine
    let mut engine = OPAEngine::new()?;

    // Load a Rego policy
    let policy = r#"
        package authorization

        default allow := false

        # Allow admins to do anything
        allow {
            input.user.role == "admin"
        }

        # Allow users to read their own data
        allow {
            input.action == "read"
            input.resource.owner == input.user.id
        }

        # Deny access to sensitive resources without MFA
        deny {
            input.resource.sensitivity == "high"
            not input.user.mfa_verified
        }

        # Final decision
        decision := {
            "allow": allow,
            "deny": deny,
            "reason": reason,
        }

        reason := "admin access" { input.user.role == "admin" }
        reason := "owner access" { input.resource.owner == input.user.id }
        reason := "mfa required" { deny }
        reason := "denied" { not allow }
    "#;

    engine.load_policy("authz".to_string(), policy.to_string())?;

    // Create input data
    let mut user = BTreeMap::new();
    user.insert(Value::String("id".into()), Value::String("user123".into()));
    user.insert(Value::String("role".into()), Value::String("developer".into()));
    user.insert(Value::String("mfa_verified".into()), Value::Bool(true));

    let mut resource = BTreeMap::new();
    resource.insert(Value::String("id".into()), Value::String("doc456".into()));
    resource.insert(Value::String("owner".into()), Value::String("user123".into()));
    resource.insert(Value::String("sensitivity".into()), Value::String("low".into()));

    let mut input_map = BTreeMap::new();
    input_map.insert(Value::String("user".into()), Value::Object(Arc::new(user)));
    input_map.insert(Value::String("resource".into()), Value::Object(Arc::new(resource)));
    input_map.insert(Value::String("action".into()), Value::String("read".into()));

    let input = Value::Object(Arc::new(input_map));

    // Evaluate policy
    let result = engine.evaluate("data.authorization.decision", input)?;
    println!("Decision: {}", result);

    // Check loaded policies
    println!("Loaded policies: {:?}", engine.loaded_policies());
    println!("Has 'authz' policy: {}", engine.has_policy("authz"));

    Ok(())
}
```

### Loading Policies from Files

```rust
use std::path::Path;
use std::fs;

fn load_policies_from_directory(engine: &mut OPAEngine, dir: &Path) -> Result<()> {
    for entry in fs::read_dir(dir)? {
        let entry = entry?;
        let path = entry.path();

        if path.extension().map_or(false, |ext| ext == "rego") {
            let name = path.file_stem()
                .unwrap()
                .to_string_lossy()
                .into_owned();
            let content = fs::read_to_string(&path)?;

            engine.load_policy(name, content)?;
            println!("Loaded policy: {}", path.display());
        }
    }
    Ok(())
}
```

### Error Handling

```rust
use grid_opa::error::{OPAError, Result};

fn handle_evaluation(engine: &mut OPAEngine, query: &str, input: Value) {
    match engine.evaluate(query, input) {
        Ok(result) => {
            println!("Result: {}", result);
        }
        Err(OPAError::CompilationError(msg)) => {
            eprintln!("Policy compilation failed: {}", msg);
        }
        Err(OPAError::EvaluationError(msg)) => {
            eprintln!("Policy evaluation failed: {}", msg);
        }
        Err(OPAError::PolicyNotFound(name)) => {
            eprintln!("Policy not found: {}", name);
        }
        Err(OPAError::InvalidInput(msg)) => {
            eprintln!("Invalid input: {}", msg);
        }
        Err(e) => {
            eprintln!("Unexpected error: {}", e);
        }
    }
}
```

### Thread-Safe Usage

```rust
use std::sync::Arc;
use tokio::sync::RwLock;

struct PolicyService {
    engine: Arc<RwLock<OPAEngine>>,
}

impl PolicyService {
    fn new() -> Result<Self> {
        Ok(Self {
            engine: Arc::new(RwLock::new(OPAEngine::new()?)),
        })
    }

    async fn evaluate(&self, query: &str, input: Value) -> Result<Value> {
        let mut engine = self.engine.write().await;
        engine.evaluate(query, input)
    }

    async fn load_policy(&self, name: String, rego: String) -> Result<()> {
        let mut engine = self.engine.write().await;
        engine.load_policy(name, rego)
    }
}
```

---

## grid-cache: LRU+TTL Cache

### Features

- **Lock-Free**: Uses DashMap for concurrent access
- **LRU Eviction**: Least-recently-used entries removed when full
- **TTL Support**: Automatic expiration of entries
- **High Performance**: 10-50x faster than Redis for local caching
- **Thread-Safe**: Safe for concurrent reads and writes

### Basic Usage (Rust)

```rust
use grid_cache::lru_ttl::LRUTTLCache;

fn main() {
    // Create cache: 10,000 max entries, 1 hour default TTL
    let cache = LRUTTLCache::new(10_000, 3600);

    // Store values
    cache.set("user:alice".to_string(), "admin".to_string(), None).unwrap();

    // Store with custom TTL (5 minutes)
    cache.set("session:abc123".to_string(), "data".to_string(), Some(300)).unwrap();

    // Retrieve values
    if let Some(role) = cache.get("user:alice") {
        println!("Alice's role: {}", role);
    }

    // Check existence without retrieving
    if cache.get("user:bob").is_none() {
        println!("Bob not in cache");
    }

    // Delete entry
    let deleted = cache.delete("session:abc123");
    println!("Deleted: {}", deleted);

    // Get cache statistics
    println!("Cache size: {}", cache.size());

    // Manual cleanup of expired entries
    let removed = cache.cleanup_expired();
    println!("Removed {} expired entries", removed);

    // Clear entire cache
    cache.clear();
}
```

### Caching Policy Evaluation Results

```rust
use grid_opa::engine::OPAEngine;
use grid_cache::lru_ttl::LRUTTLCache;
use serde_json;

struct CachedPolicyEngine {
    opa: OPAEngine,
    cache: LRUTTLCache,
}

impl CachedPolicyEngine {
    fn new(cache_size: usize, cache_ttl: u64) -> Result<Self, Box<dyn std::error::Error>> {
        Ok(Self {
            opa: OPAEngine::new()?,
            cache: LRUTTLCache::new(cache_size, cache_ttl),
        })
    }

    fn evaluate(&mut self, query: &str, input: &serde_json::Value) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
        // Create cache key from query and input
        let cache_key = format!("{}:{}", query, input);

        // Check cache first
        if let Some(cached) = self.cache.get(&cache_key) {
            return Ok(serde_json::from_str(&cached)?);
        }

        // Convert input to regorus Value
        let input_str = input.to_string();
        let input_value: regorus::Value = serde_json::from_str(&input_str)?;

        // Evaluate policy
        let result = self.opa.evaluate(query, input_value)?;

        // Convert result to JSON
        let result_json: serde_json::Value = serde_json::from_str(&result.to_string())?;

        // Cache the result
        self.cache.set(cache_key, result_json.to_string(), None)?;

        Ok(result_json)
    }
}
```

### Custom Cache Key Generation

```rust
use std::hash::{Hash, Hasher};
use std::collections::hash_map::DefaultHasher;

fn make_cache_key(user_id: &str, action: &str, resource: &str) -> String {
    // Simple concatenation for small key space
    format!("{}:{}:{}", user_id, action, resource)
}

fn make_cache_key_hashed(data: &impl Hash) -> String {
    // Hash for large/complex inputs
    let mut hasher = DefaultHasher::new();
    data.hash(&mut hasher);
    format!("{:x}", hasher.finish())
}
```

### Periodic Cleanup

```rust
use std::time::Duration;
use tokio::time::interval;

async fn cache_cleanup_task(cache: Arc<LRUTTLCache>) {
    let mut interval = interval(Duration::from_secs(60)); // Every minute

    loop {
        interval.tick().await;
        let removed = cache.cleanup_expired();
        if removed > 0 {
            log::debug!("Cache cleanup removed {} entries", removed);
        }
    }
}
```

---

## Python Usage

Both crates include PyO3 bindings for use from Python.

### Building for Python

```bash
# In SARK directory
pip install maturin
maturin develop  # Development mode
# or
maturin build --release  # Build wheel
```

### Python Examples

```python
# After building with maturin
from sark.sark_rust import RustOPAEngine, RustCache

# OPA Engine
engine = RustOPAEngine()
engine.load_policy("test", """
    package test
    allow { input.user == "admin" }
""")

result = engine.evaluate("data.test.allow", {"user": "admin"})
print(f"Allow: {result}")  # Allow: True

# Cache
cache = RustCache(max_size=10000, ttl_secs=3600)
cache.set("key1", "value1")
print(cache.get("key1"))  # value1

cache.set("key2", "value2", ttl=60)  # Custom TTL
```

---

## Integration Patterns

### With Axum (Web Framework)

```rust
use axum::{Router, Json, Extension, routing::post};
use grid_opa::engine::OPAEngine;
use std::sync::Arc;
use tokio::sync::RwLock;

type SharedEngine = Arc<RwLock<OPAEngine>>;

#[derive(Deserialize)]
struct AuthzRequest {
    user: String,
    action: String,
    resource: String,
}

#[derive(Serialize)]
struct AuthzResponse {
    allow: bool,
    reason: Option<String>,
}

async fn authorize(
    Extension(engine): Extension<SharedEngine>,
    Json(req): Json<AuthzRequest>,
) -> Json<AuthzResponse> {
    let input = serde_json::json!({
        "user": req.user,
        "action": req.action,
        "resource": req.resource,
    });

    let input_value: regorus::Value = serde_json::from_value(input).unwrap();

    let mut engine = engine.write().await;
    let result = engine.evaluate("data.authz.allow", input_value).unwrap();

    Json(AuthzResponse {
        allow: result == regorus::Value::Bool(true),
        reason: None,
    })
}

#[tokio::main]
async fn main() {
    let engine = Arc::new(RwLock::new(OPAEngine::new().unwrap()));

    let app = Router::new()
        .route("/authorize", post(authorize))
        .layer(Extension(engine));

    axum::Server::bind(&"0.0.0.0:3000".parse().unwrap())
        .serve(app.into_make_service())
        .await
        .unwrap();
}
```

### With Actix-web

```rust
use actix_web::{web, App, HttpServer, HttpResponse};
use grid_opa::engine::OPAEngine;
use std::sync::Mutex;

struct AppState {
    engine: Mutex<OPAEngine>,
}

async fn authorize(
    data: web::Data<AppState>,
    req: web::Json<AuthzRequest>,
) -> HttpResponse {
    let mut engine = data.engine.lock().unwrap();
    // ... evaluation logic
    HttpResponse::Ok().json(response)
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let state = web::Data::new(AppState {
        engine: Mutex::new(OPAEngine::new().unwrap()),
    });

    HttpServer::new(move || {
        App::new()
            .app_data(state.clone())
            .route("/authorize", web::post().to(authorize))
    })
    .bind("0.0.0.0:8080")?
    .run()
    .await
}
```

---

## Performance Considerations

### OPA Engine

```rust
// DO: Reuse engine instances
let engine = OPAEngine::new()?;  // Create once
for request in requests {
    engine.evaluate(query, input)?;  // Reuse many times
}

// DON'T: Create new engine per request
for request in requests {
    let engine = OPAEngine::new()?;  // Expensive!
    engine.load_policy(...)?;         // Very expensive!
    engine.evaluate(query, input)?;
}
```

### Cache

```rust
// DO: Use appropriate cache size
// Rule of thumb: entries * avg_size < available_memory / 4
let cache = LRUTTLCache::new(10_000, 3600);

// DO: Use meaningful TTLs
// - Auth decisions: 5-30 minutes (balance security vs performance)
// - Static data: 1-24 hours
// - Session data: match session timeout

// DON'T: Cache everything forever
let cache = LRUTTLCache::new(1_000_000, 86400 * 365);  // Bad!
```

### Benchmarking

```rust
use criterion::{black_box, criterion_group, criterion_main, Criterion};

fn bench_opa_evaluation(c: &mut Criterion) {
    let mut engine = OPAEngine::new().unwrap();
    engine.load_policy("bench", POLICY.to_string()).unwrap();

    let input = create_test_input();

    c.bench_function("opa_evaluate", |b| {
        b.iter(|| {
            engine.evaluate(black_box("data.bench.allow"), black_box(input.clone()))
        })
    });
}

fn bench_cache_operations(c: &mut Criterion) {
    let cache = LRUTTLCache::new(10_000, 3600);

    c.bench_function("cache_set", |b| {
        let mut i = 0;
        b.iter(|| {
            cache.set(format!("key{}", i), "value".to_string(), None).unwrap();
            i += 1;
        })
    });

    c.bench_function("cache_get", |b| {
        b.iter(|| {
            cache.get(black_box("key0"))
        })
    });
}

criterion_group!(benches, bench_opa_evaluation, bench_cache_operations);
criterion_main!(benches);
```

---

## API Reference

### grid-opa

```rust
pub struct OPAEngine { /* ... */ }

impl OPAEngine {
    /// Create a new OPA engine instance
    pub fn new() -> Result<Self>;

    /// Load and compile a Rego policy
    pub fn load_policy(&mut self, name: String, rego: String) -> Result<()>;

    /// Evaluate a query against loaded policies
    pub fn evaluate(&mut self, query: &str, input: Value) -> Result<Value>;

    /// Clear all loaded policies
    pub fn clear_policies(&mut self);

    /// Get list of loaded policy names
    pub fn loaded_policies(&self) -> Vec<String>;

    /// Check if a policy is loaded
    pub fn has_policy(&self, name: &str) -> bool;
}
```

### grid-cache

```rust
pub struct LRUTTLCache { /* ... */ }

impl LRUTTLCache {
    /// Create a new cache with max size and default TTL
    pub fn new(max_size: usize, default_ttl_secs: u64) -> Self;

    /// Get a value from the cache
    pub fn get(&self, key: &str) -> Option<String>;

    /// Set a value in the cache with optional custom TTL
    pub fn set(&self, key: String, value: String, ttl: Option<u64>) -> Result<()>;

    /// Delete a key from the cache
    pub fn delete(&self, key: &str) -> bool;

    /// Clear all entries
    pub fn clear(&self);

    /// Get current number of entries
    pub fn size(&self) -> usize;

    /// Remove expired entries, returns count removed
    pub fn cleanup_expired(&self) -> usize;
}
```

---

## See Also

- [Rust PyO3 Integration Guide](RUST_PYO3_INTEGRATION.md) - Building Python extensions
- [Embedded Deployment Guide](EMBEDDED_DEPLOYMENT.md) - Resource-constrained systems
- [Cross-Compilation Guide](CROSS_COMPILATION.md) - Building for other platforms
- [regorus documentation](https://docs.rs/regorus) - OPA engine internals
- [dashmap documentation](https://docs.rs/dashmap) - Concurrent hashmap
