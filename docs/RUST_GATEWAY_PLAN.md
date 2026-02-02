# SARK Rust Gateway - Hot Path Binary

## Overview

Extract the hot path (high-frequency request handling) into a standalone Rust binary while keeping cold path (admin, UI, complex logic) in Python.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SARK System Architecture                   │
└─────────────────────────────────────────────────────────────┘

🔥 HOT PATH (Rust Binary - sark-gateway)
┌──────────────────────────────────────────────────────────────┐
│ POST /gateway/authorize                                       │
│  - Extract user from JWT                                      │
│  - Check cache (grid-cache - Rust)                           │
│  - Evaluate policy (grid-opa - Rust)                         │
│  - Return decision + cache                                    │
│                                                               │
│ POST /gateway/authorize-a2a                                  │
│  - Agent-to-agent authorization                              │
│                                                               │
│ Performance: <5ms p95 latency, pure Rust, no Python overhead │
└──────────────────────────────────────────────────────────────┘

❄️ COLD PATH (Python/FastAPI - existing sark service)
┌──────────────────────────────────────────────────────────────┐
│ • Web UI (React + FastAPI backend)                           │
│ • Admin APIs (users, roles, permissions)                     │
│ • Policy management (CRUD, editor)                           │
│ • Audit log viewing & search                                 │
│ • Discovery & federation                                     │
│ • SIEM integration                                           │
│ • Metrics & monitoring dashboards                            │
│ • Complex workflows                                          │
│                                                               │
│ Performance: Not critical, developer productivity focused    │
└──────────────────────────────────────────────────────────────┘
```

## Why This Matters

### Current Hot Path (Python)
```
MCP Request → FastAPI (Python)
             ↓
         authorize_gateway_request (Python)
             ↓
         evaluate_policy (Python wrapper)
             ↓
         OPA Engine (Rust via PyO3) ✅
         Cache (Rust via PyO3) ✅
             ↓
         Return via Python → JSON
```

**Overhead**: ~10-50ms of Python handling per request
**At Scale**: 10,000 req/s × 20ms overhead = 200 CPU cores wasted

### New Hot Path (Rust)
```
MCP Request → Axum (Rust)
             ↓
         authorize handler (Rust)
             ↓
         OPA Engine (Rust - direct) ✅
         Cache (Rust - direct) ✅
             ↓
         Return via Rust → JSON
```

**Overhead**: ~1-2ms total
**At Scale**: 10,000 req/s × 2ms = 20 CPU cores needed

**Savings**: 180 CPU cores (90% reduction in hot path resources)

## Implementation Plan

### Phase 1: Basic Gateway (DONE ✓)
- [x] Create `rust/sark-gateway` crate
- [x] Set up workspace in root `Cargo.toml`
- [x] Basic Axum server with `/health` endpoint
- [x] Integrate grid-opa and grid-cache

### Phase 2: Authorization Endpoint (NEXT)
- [ ] Implement JWT extraction and validation
- [ ] Implement `/gateway/authorize` endpoint
- [ ] Add OPA policy evaluation
- [ ] Add caching logic
- [ ] Unit tests

### Phase 3: Production Ready
- [ ] Add metrics (Prometheus)
- [ ] Add tracing (OpenTelemetry)
- [ ] Add graceful shutdown
- [ ] Add TLS support
- [ ] Load testing & benchmarks

### Phase 4: Deployment
- [ ] Docker image for sark-gateway
- [ ] Update docker-compose.yml
- [ ] Update Kubernetes manifests
- [ ] Migration guide (Python → Rust gateway)
- [ ] Rollback plan

## Current Status

```bash
# Build status
$ cd /home/jhenry/Source/sark
$ cargo build --release -p sark-gateway

# Output:
# ✓ Workspace configured
# ✓ Dependencies resolved
# ✗ Compilation errors (API needs implementation)
```

**Next Steps**:
1. Implement correct API using OPAEngine and LRUTTLCache
2. Add JWT validation
3. Test authorization flow
4. Deploy alongside Python service
5. Gradually migrate traffic (feature flags)

## Benefits

### Performance
- **10-50x faster** hot path (no Python overhead)
- **<5ms p95** latency vs current 42ms (HTTP OPA) or 15ms (PyO3 OPA)
- **90% resource reduction** at scale

### Architecture
- **Separation of concerns**: Hot path separate from business logic
- **Independent scaling**: Scale Rust gateway separately from Python API
- **Gradual migration**: Can run both simultaneously

### Cost
- **10x fewer servers** needed for hot path at enterprise scale
- **Lower cloud costs** (fewer CPU cores, less memory)
- **Better utilization** of existing infrastructure

## Files Created

```
rust/sark-gateway/
├── Cargo.toml          # Package definition
└── src/
    └── main.rs         # Main server (needs API implementation)

Cargo.toml              # Updated with workspace

docs/
└── RUST_GATEWAY_PLAN.md  # This file
```

## Migration Strategy

### Week 1-2: Development
- Complete authorization endpoint
- Add metrics and logging
- Integration tests

### Week 3: Testing
- Load testing (Locust)
- Compare Python vs Rust latency
- Fix bugs

### Week 4: Deployment
- Deploy sark-gateway alongside Python
- Use feature flag for gradual rollout:
  - 0% Rust (baseline)
  - 5% Rust (canary)
  - 25% Rust
  - 50% Rust
  - 100% Rust

### Rollback
- If issues: Set feature flag to 0% (instant rollback)
- Python hot path remains as fallback

## Questions?

- **Do we still need Python?** YES - for admin, UI, complex logic
- **Can we replace all of SARK with Rust?** Possible, but not worth it. Keep Python for developer productivity on cold path.
- **What about YORI?** Similar architecture - YORI already has pure Rust binary for hot path
- **Performance impact?** Expect 10-50x improvement on authorization endpoint
