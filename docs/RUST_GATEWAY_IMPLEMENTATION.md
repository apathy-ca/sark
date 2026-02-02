# SARK Rust Gateway - Implementation Guide

**Target Developer**: External developer picking up this work
**Status**: Foundation laid, needs implementation
**Estimated Effort**: 2-3 weeks for production-ready version

---

## Quick Start

```bash
cd /home/jhenry/Source/sark

# Build (will fail with current skeleton - that's expected)
cargo build --release -p sark-gateway

# Run tests
cargo test -p sark-gateway

# Run locally
./target/release/sark-gateway --listen 127.0.0.1:8080
```

---

## Phase 1: Fix API Implementation (Week 1, Days 1-2)

### Current Issues

The skeleton code in `rust/sark-gateway/src/main.rs` has compilation errors because it uses incorrect APIs. Here's what needs fixing:

### 1.1 Fix OPA Engine Usage

**Current (broken)**:
```rust
let opa_engine = Arc::new(PolicyEngine::new()?);
match state.opa_engine.evaluate("data.mcp.gateway.allow", &opa_input) {
```

**Should be** (based on grid-opa API):
```rust
use grid_opa::{OPAEngine, Value};
use std::collections::BTreeMap;

// Initialize
let mut opa_engine = OPAEngine::new()?;

// Load policy from file
let policy_content = std::fs::read_to_string("/etc/sark/policies/gateway.rego")?;
opa_engine.load_policy("gateway".to_string(), policy_content)?;

// Convert serde_json::Value to regorus::Value
fn json_to_regorus(val: &serde_json::Value) -> Value {
    match val {
        serde_json::Value::Null => Value::Null,
        serde_json::Value::Bool(b) => Value::Bool(*b),
        serde_json::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Value::Number(regorus::Number::from(i))
            } else if let Some(f) = n.as_f64() {
                Value::Number(regorus::Number::from(f))
            } else {
                Value::Null
            }
        }
        serde_json::Value::String(s) => Value::String(s.clone().into()),
        serde_json::Value::Array(arr) => {
            Value::Array(Arc::new(arr.iter().map(json_to_regorus).collect()))
        }
        serde_json::Value::Object(obj) => {
            let mut map = BTreeMap::new();
            for (k, v) in obj {
                map.insert(Value::String(k.clone().into()), json_to_regorus(v));
            }
            Value::Object(Arc::new(map))
        }
    }
}

// Evaluate
let input_value = json_to_regorus(&opa_input);
let result_value = opa_engine.evaluate("data.mcp.gateway.allow", input_value)?;

// Extract decision
let allow = match result_value {
    Value::Bool(b) => b,
    _ => false,
};
```

### 1.2 Fix Cache Usage

**Current (broken)**:
```rust
let cache = Arc::new(Cache::new(10000));
if let Some(cached) = state.cache.get(&cache_key) {
```

**Should be** (based on grid-cache API):
```rust
use grid_cache::LRUTTLCache;

// Initialize (max_size, default_ttl_seconds)
let cache = Arc::new(LRUTTLCache::new(10_000, 300));

// Get
if let Some(cached_str) = cache.get(&cache_key) {
    // cached_str is String
    if let Ok(response) = serde_json::from_str::<GatewayAuthResponse>(&cached_str) {
        return Ok(Json(response));
    }
}

// Set (key, value, optional ttl override)
let cached_value = serde_json::to_string(&response)?;
cache.set(cache_key, cached_value, None)?; // Uses default TTL (300s)
```

### 1.3 Add JWT Validation

**Create new file**: `rust/sark-gateway/src/auth.rs`

```rust
use anyhow::{Context, Result};
use jsonwebtoken::{decode, Algorithm, DecodingKey, Validation};
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct JWTClaims {
    pub sub: String,  // user_id
    pub email: String,
    pub roles: Vec<String>,
    pub permissions: Vec<String>,
    pub exp: usize,
    pub iat: usize,
}

pub struct JWTValidator {
    decoding_key: DecodingKey,
    validation: Validation,
}

impl JWTValidator {
    pub fn new(secret: &str) -> Self {
        let mut validation = Validation::new(Algorithm::HS256);
        validation.validate_exp = true;

        Self {
            decoding_key: DecodingKey::from_secret(secret.as_bytes()),
            validation,
        }
    }

    pub fn validate(&self, token: &str) -> Result<JWTClaims> {
        let token_data = decode::<JWTClaims>(
            token,
            &self.decoding_key,
            &self.validation,
        )
        .context("Failed to decode JWT")?;

        Ok(token_data.claims)
    }
}
```

**Update main.rs**:
```rust
use axum::{
    extract::{State, TypedHeader},
    headers::{authorization::Bearer, Authorization},
};

// Add to AppState
struct AppState {
    opa_engine: Arc<Mutex<OPAEngine>>,
    cache: Arc<LRUTTLCache>,
    jwt_validator: Arc<JWTValidator>,
}

// Update authorize handler
async fn authorize(
    State(state): State<AppState>,
    TypedHeader(auth): TypedHeader<Authorization<Bearer>>,
    Json(request): Json<GatewayAuthRequest>,
) -> Result<Json<GatewayAuthResponse>, (StatusCode, String)> {
    // Validate JWT
    let claims = state.jwt_validator
        .validate(auth.token())
        .map_err(|e| (StatusCode::UNAUTHORIZED, format!("Invalid token: {}", e)))?;

    // Build user context
    let user = UserContext {
        user_id: claims.sub,
        email: claims.email,
        roles: claims.roles,
        permissions: claims.permissions,
    };

    // ... rest of authorization logic
}
```

---

## Phase 2: Configuration & Policies (Week 1, Days 3-4)

### 2.1 Configuration File

**Create**: `/etc/sark/gateway.toml`

```toml
[server]
listen = "0.0.0.0:8080"
log_level = "info"

[auth]
jwt_secret = "your-secret-key-here"  # TODO: Load from env or secret manager

[opa]
policy_dir = "/etc/sark/policies"
# Policies to load on startup
policies = [
    "gateway.rego",
    "common.rego",
]

[cache]
max_entries = 10000
default_ttl = 300  # 5 minutes

[metrics]
enabled = true
prometheus_port = 9090
```

**Update main.rs to load config**:
```rust
use config::{Config, File};
use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct ServerConfig {
    listen: String,
    log_level: String,
}

#[derive(Debug, Deserialize)]
struct AuthConfig {
    jwt_secret: String,
}

#[derive(Debug, Deserialize)]
struct OPAConfig {
    policy_dir: String,
    policies: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct CacheConfig {
    max_entries: usize,
    default_ttl: u64,
}

#[derive(Debug, Deserialize)]
struct AppConfig {
    server: ServerConfig,
    auth: AuthConfig,
    opa: OPAConfig,
    cache: CacheConfig,
}

// In main()
let config = Config::builder()
    .add_source(File::with_name(&args.config.to_string_lossy()))
    .build()?
    .try_deserialize::<AppConfig>()?;
```

### 2.2 Policy Loading

```rust
// In main(), after creating OPAEngine
let mut opa_engine = OPAEngine::new()?;

for policy_name in &config.opa.policies {
    let policy_path = format!("{}/{}", config.opa.policy_dir, policy_name);
    let policy_content = std::fs::read_to_string(&policy_path)
        .with_context(|| format!("Failed to load policy: {}", policy_path))?;

    let policy_id = policy_name.trim_end_matches(".rego");
    opa_engine.load_policy(policy_id.to_string(), policy_content)?;
    info!("Loaded policy: {}", policy_id);
}
```

---

## Phase 3: Metrics & Observability (Week 1, Day 5)

### 3.1 Add Prometheus Metrics

**Add to Cargo.toml**:
```toml
[dependencies]
prometheus = "0.13"
lazy_static = "1.4"
```

**Create**: `rust/sark-gateway/src/metrics.rs`

```rust
use lazy_static::lazy_static;
use prometheus::{
    register_histogram_vec, register_int_counter_vec, HistogramVec, IntCounterVec,
};

lazy_static! {
    pub static ref AUTHORIZATION_DURATION: HistogramVec = register_histogram_vec!(
        "sark_gateway_authorization_duration_seconds",
        "Authorization request duration",
        &["endpoint"]
    )
    .unwrap();

    pub static ref AUTHORIZATION_REQUESTS: IntCounterVec = register_int_counter_vec!(
        "sark_gateway_authorization_requests_total",
        "Total authorization requests",
        &["endpoint", "result"]
    )
    .unwrap();

    pub static ref CACHE_OPERATIONS: IntCounterVec = register_int_counter_vec!(
        "sark_gateway_cache_operations_total",
        "Cache operations",
        &["operation", "result"]
    )
    .unwrap();

    pub static ref OPA_EVALUATIONS: HistogramVec = register_histogram_vec!(
        "sark_gateway_opa_evaluation_duration_seconds",
        "OPA policy evaluation duration",
        &["policy"]
    )
    .unwrap();
}

pub fn metrics_handler() -> String {
    use prometheus::Encoder;
    let encoder = prometheus::TextEncoder::new();
    let metric_families = prometheus::gather();
    let mut buffer = Vec::new();
    encoder.encode(&metric_families, &mut buffer).unwrap();
    String::from_utf8(buffer).unwrap()
}
```

**Add metrics endpoint to main.rs**:
```rust
use crate::metrics::*;

async fn metrics() -> impl IntoResponse {
    metrics_handler()
}

// In router
let app = Router::new()
    .route("/health", get(health))
    .route("/metrics", get(metrics))
    .route("/gateway/authorize", post(authorize))
    .with_state(state);
```

**Instrument authorization handler**:
```rust
async fn authorize(...) -> ... {
    let timer = AUTHORIZATION_DURATION
        .with_label_values(&["authorize"])
        .start_timer();

    // ... authorization logic

    timer.observe_duration();
    AUTHORIZATION_REQUESTS
        .with_label_values(&["authorize", if allow { "allow" } else { "deny" }])
        .inc();

    // ... return
}
```

---

## Phase 4: Testing (Week 2, Days 1-3)

### 4.1 Unit Tests

**Create**: `rust/sark-gateway/src/lib.rs`

```rust
// Move shared code here for testing
pub mod auth;
pub mod metrics;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_jwt_validation() {
        let validator = auth::JWTValidator::new("test-secret");
        // TODO: Create test JWT and validate
    }

    #[test]
    fn test_opa_evaluation() {
        // TODO: Test OPA policy evaluation
    }

    #[test]
    fn test_cache_operations() {
        // TODO: Test cache get/set
    }
}
```

### 4.2 Integration Tests

**Create**: `rust/sark-gateway/tests/integration_test.rs`

```rust
use axum::http::StatusCode;
use sark_gateway::*;

#[tokio::test]
async fn test_health_endpoint() {
    // TODO: Start server, call /health, assert OK
}

#[tokio::test]
async fn test_authorization_flow() {
    // TODO:
    // 1. Start server
    // 2. POST /gateway/authorize with valid JWT
    // 3. Assert response
}
```

### 4.3 Load Testing

**Create**: `scripts/load_test.py` (using Locust)

```python
from locust import HttpUser, task, between

class SARKGatewayUser(HttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self):
        # Get JWT token
        self.token = "Bearer <test-jwt>"

    @task
    def authorize_request(self):
        self.client.post(
            "/gateway/authorize",
            headers={"Authorization": self.token},
            json={
                "action": "mcp:invoke",
                "server_name": "test-server",
                "tool_name": "test-tool",
            }
        )
```

**Run load test**:
```bash
locust -f scripts/load_test.py --host http://localhost:8080
# Open http://localhost:8089 and configure users
```

---

## Phase 5: Docker & Deployment (Week 2, Days 4-5)

### 5.1 Dockerfile

**Create**: `rust/sark-gateway/Dockerfile`

```dockerfile
# Build stage
FROM rust:1.75 as builder
WORKDIR /app

# Copy workspace
COPY Cargo.toml .
COPY rust/ rust/

# Build
RUN cargo build --release -p sark-gateway

# Runtime stage
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/target/release/sark-gateway /usr/local/bin/
COPY config/gateway.toml /etc/sark/

EXPOSE 8080 9090
CMD ["sark-gateway", "--config", "/etc/sark/gateway.toml"]
```

### 5.2 Docker Compose Integration

**Update**: `docker-compose.yml`

```yaml
services:
  # Existing SARK Python service
  sark-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GATEWAY_URL=http://sark-gateway:8080
    depends_on:
      - sark-gateway

  # NEW: Rust gateway for hot path
  sark-gateway:
    build:
      context: .
      dockerfile: rust/sark-gateway/Dockerfile
    ports:
      - "8080:8080"  # Authorization endpoints
      - "9090:9090"  # Prometheus metrics
    volumes:
      - ./config/gateway.toml:/etc/sark/gateway.toml:ro
      - ./opa/policies:/etc/sark/policies:ro
    environment:
      - RUST_LOG=info
      - JWT_SECRET=${JWT_SECRET}
```

### 5.3 Kubernetes Deployment

**Create**: `k8s/sark-gateway-deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sark-gateway
  labels:
    app: sark-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sark-gateway
  template:
    metadata:
      labels:
        app: sark-gateway
    spec:
      containers:
      - name: sark-gateway
        image: sark-gateway:1.6.0
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 9090
          name: metrics
        env:
        - name: RUST_LOG
          value: info
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: sark-secrets
              key: jwt-secret
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 1000m
            memory: 512Mi
---
apiVersion: v1
kind: Service
metadata:
  name: sark-gateway
spec:
  selector:
    app: sark-gateway
  ports:
  - name: http
    port: 8080
    targetPort: 8080
  - name: metrics
    port: 9090
    targetPort: 9090
```

---

## Phase 6: Migration & Rollout (Week 3)

### 6.1 Feature Flag in Python

**Update**: `src/sark/services/feature_flags.py`

```python
# Add new feature flag
RUST_GATEWAY_ENABLED = "rust_gateway_enabled"

# In evaluate_feature_flag()
if flag_name == RUST_GATEWAY_ENABLED:
    # Start at 0%, gradually increase
    return get_rollout_percentage(flag_name, user_id) < 5  # 5% initial rollout
```

### 6.2 Python Gateway Client

**Update**: `src/sark/services/gateway/client.py`

```python
import httpx
from sark.services.feature_flags import evaluate_feature_flag, RUST_GATEWAY_ENABLED

class GatewayClient:
    def __init__(self):
        self.rust_url = os.getenv("RUST_GATEWAY_URL", "http://sark-gateway:8080")
        self.python_url = "http://localhost:8000"  # Current Python endpoint

    async def authorize(self, request: GatewayAuthorizationRequest, user_id: str):
        # Feature flag routing
        use_rust = evaluate_feature_flag(RUST_GATEWAY_ENABLED, user_id)

        if use_rust:
            # Route to Rust gateway
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{self.rust_url}/gateway/authorize",
                        json=request.dict(),
                        headers={"Authorization": f"Bearer {get_jwt_token()}"},
                    )
                    resp.raise_for_status()
                    return GatewayAuthorizationResponse(**resp.json())
            except Exception as e:
                logger.error(f"Rust gateway failed, falling back to Python: {e}")
                # Fall through to Python

        # Python implementation (existing)
        return await authorize_gateway_request(user=user, request=request)
```

### 6.3 Gradual Rollout Plan

```bash
# Week 3, Day 1: Deploy alongside Python
kubectl apply -f k8s/sark-gateway-deployment.yaml

# Week 3, Day 2: 5% traffic
# Set feature flag: rust_gateway_enabled = 5%

# Week 3, Day 3: Monitor, fix issues
# Check metrics, logs, error rates

# Week 3, Day 4: 25% traffic
# Set feature flag: rust_gateway_enabled = 25%

# Week 3, Day 5: 50% traffic
# Set feature flag: rust_gateway_enabled = 50%

# Week 4: 100% traffic
# Set feature flag: rust_gateway_enabled = 100%
```

---

## API Reference

### Endpoints

#### `POST /gateway/authorize`

**Request**:
```json
{
  "action": "mcp:invoke",
  "server_name": "github-server",
  "tool_name": "create_issue",
  "parameters": {
    "title": "Bug report",
    "body": "Description"
  },
  "context": {},
  "sensitivity_level": "medium"
}
```

**Headers**:
```
Authorization: Bearer <JWT-token>
```

**Response** (200 OK):
```json
{
  "allow": true,
  "reason": "User has mcp:invoke permission",
  "filtered_parameters": null,
  "cache_ttl": 300
}
```

**Response** (403 Forbidden):
```json
{
  "allow": false,
  "reason": "User lacks required role: github-admin",
  "filtered_parameters": null,
  "cache_ttl": 300
}
```

---

## Performance Targets

| Metric | Target | Current (Python) |
|--------|--------|------------------|
| p50 latency | <2ms | ~10ms |
| p95 latency | <5ms | ~42ms |
| p99 latency | <10ms | ~100ms |
| Throughput | 10K req/s | 1K req/s |
| Memory | <512MB | ~2GB |
| CPU (10K req/s) | 1 core | 10 cores |

---

## Troubleshooting

### Build Issues

```bash
# Clear cache
cargo clean

# Update dependencies
cargo update

# Check for missing files
ls -la ../grid-core/crates/
```

### Runtime Issues

```bash
# Check logs
docker logs sark-gateway

# Test manually
curl -X POST http://localhost:8080/gateway/authorize \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"action":"test","server_name":"test","tool_name":"test"}'

# Check metrics
curl http://localhost:9090/metrics
```

---

## Checklist for External Developer

- [ ] Phase 1: Fix API implementation (OPA, Cache, JWT)
- [ ] Phase 2: Add configuration loading and policy management
- [ ] Phase 3: Add metrics and observability
- [ ] Phase 4: Write unit tests, integration tests, load tests
- [ ] Phase 5: Create Dockerfile and K8s manifests
- [ ] Phase 6: Implement migration strategy
- [ ] Documentation: Update README with Rust gateway info
- [ ] Handoff: Demo to team, knowledge transfer

---

## Questions / Support

**Architecture Questions**: See `/docs/RUST_GATEWAY_PLAN.md`
**Grid Core API**: See `../grid-core/README.md`
**YORI Reference**: See `../yori/` for similar pure Rust implementation

**Contact**: [Your contact info here]
