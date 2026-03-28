# SARK Gateway - Rust Hot Path Binary

High-performance authorization service for SARK enterprise AI governance platform.

## Status

**🚧 In Development** - Foundation laid, needs implementation

- ✅ Project structure created
- ✅ Workspace configured
- ✅ Dependencies resolved
- ❌ API implementation (has compilation errors - needs fixing)
- ❌ Tests
- ❌ Deployment configs

## What This Does

Handles the **hot path** (high-frequency requests) for SARK:
- `/gateway/authorize` - Policy-based authorization for MCP tool invocations
- `/gateway/authorize-a2a` - Agent-to-agent communication authorization

**Performance Goal**: <5ms p95 latency (vs. current 15-50ms in Python)

## Why Rust?

The authorization endpoint is called on **every MCP request**. At enterprise scale (10K+ req/s), the Python overhead adds significant cost:

- **Current**: Python → PyO3 → Rust OPA → PyO3 → Python (~20ms overhead)
- **Target**: Rust → Rust OPA (direct) (~2ms total)
- **Savings**: 90% reduction in CPU resources for hot path

## Architecture

```
┌─────────────────────────────────────────────┐
│  MCP Request → SARK Gateway (Rust - this)   │
│                      ↓                       │
│           JWT Validation (Rust)              │
│                      ↓                       │
│            Cache Check (Rust)                │
│                      ↓                       │
│         OPA Evaluation (Rust - grid-opa)     │
│                      ↓                       │
│           Cache Store (Rust - grid-cache)    │
│                      ↓                       │
│              Return Decision                 │
└─────────────────────────────────────────────┘

Cold path (admin, UI) stays in Python/FastAPI
```

## Quick Start (For External Developer)

### Prerequisites
- Rust 1.75+
- Access to `grid-core/` repository

### Build
```bash
cd <repo-root>
cargo build --release -p sark-gateway
```

**Expected**: Compilation errors (current code is skeleton only)

### Implementation Guide

**📖 READ THIS FIRST**: [Implementation Guide](../../docs/RUST_GATEWAY_IMPLEMENTATION.md)

The guide contains:
- Detailed API fixes with code examples
- Phase-by-phase implementation plan (2-3 weeks)
- Configuration, testing, deployment instructions
- Migration and rollout strategy

### Quick Reference

**Fix API calls**:
- `PolicyEngine` → `OPAEngine` (from grid-opa)
- `Cache` → `LRUTTLCache` (from grid-cache)
- Add JWT validation
- Add proper type conversions (serde_json → regorus::Value)

**See**: [docs/RUST_GATEWAY_IMPLEMENTATION.md](../../docs/RUST_GATEWAY_IMPLEMENTATION.md#phase-1-fix-api-implementation-week-1-days-1-2)

## Documentation

- **[Implementation Guide](../../docs/RUST_GATEWAY_IMPLEMENTATION.md)** - Detailed development guide
- **[Architecture Plan](../../docs/RUST_GATEWAY_PLAN.md)** - High-level overview and benefits
- **[Grid Core API](grid-core/README.md)** - OPA and Cache API reference

## Dependencies

Uses shared components from `grid-core`:
- **grid-opa**: Embedded OPA policy engine (Regorus)
- **grid-cache**: High-performance LRU+TTL cache (DashMap)

## Project Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| Foundation | Complete | ✅ |
| API Implementation | 2 days | 📝 Next |
| Configuration & Policies | 2 days | ⏳ Planned |
| Metrics & Observability | 1 day | ⏳ Planned |
| Testing | 3 days | ⏳ Planned |
| Deployment | 2 days | ⏳ Planned |
| Migration & Rollout | 1 week | ⏳ Planned |

**Total**: 2-3 weeks to production

## Performance Targets

| Metric | Target | Current (Python) |
|--------|--------|------------------|
| p95 latency | <5ms | ~42ms |
| Throughput | 10K req/s | 1K req/s |
| Memory | <512MB | ~2GB |
| CPU @ 10K req/s | 1 core | 10 cores |

## Contact

Development will be done by external team.

**Questions?** See implementation guide or contact [owner]
