# Migration Guide: v1.3.0 → v1.4.0

## Overview

SARK v1.4.0 introduces high-performance Rust implementations for OPA policy evaluation and caching. This is a **backwards-compatible** release with optional Rust optimizations that can be enabled gradually through feature flags.

**Key Changes:**
- Embedded Rust OPA engine (4-10x faster policy evaluation)
- Rust in-memory cache (10-50x faster than Redis)
- Feature flag system for gradual rollout
- A/B testing framework for safe deployment
- Zero breaking changes to existing APIs

## What's New

### Rust OPA Engine
- Embedded Rego evaluation using Regorus library
- Zero HTTP overhead (no external OPA server required for Rust mode)
- Sub-millisecond policy evaluation (<5ms p95)
- 100% compatible with existing OPA policies
- Automatic fallback to Python/HTTP implementation if Rust unavailable

### Rust In-Memory Cache
- LRU + TTL eviction strategy
- Thread-safe concurrent access via DashMap
- No network I/O overhead
- Automatic memory management
- 10-50x faster than Redis for cache operations

### Feature Flags & A/B Testing
- Gradual rollout capability (0% → 5% → 25% → 50% → 100%)
- Instant rollback on issues (< 1 second)
- Metrics-driven deployment
- Per-feature enable/disable controls
- Stable user assignment for consistent experience

## Breaking Changes

**None** - v1.4.0 is a drop-in replacement for v1.3.0.

All existing functionality is preserved:
- ✅ All APIs remain unchanged
- ✅ Configuration format unchanged
- ✅ OPA policies require no modifications
- ✅ Python fallback automatically used if Rust unavailable
- ✅ No database migrations required

## Upgrade Steps

### 1. Prerequisites

**System Requirements:**
- Python 3.11+
- Rust 1.70+ (only if building from source)
- PostgreSQL 15+, Valkey 7+ (unchanged)
- Open Policy Agent 0.60+ (unchanged)

**No changes required:**
- Existing OPA policies work without modification
- Configuration files remain compatible
- Database schema unchanged

### 2. Installation

**Option A: From PyPI (recommended):**
```bash
pip install --upgrade sark==1.4.0
```

Pre-built wheels are available for:
- Linux (x86_64, aarch64)
- macOS (x86_64, arm64)
- Windows (x86_64)

**Option B: From Source:**
```bash
git checkout v1.4.0

# Install Rust toolchain (if not already installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# Install maturin
pip install maturin

# Build Rust extensions
maturin develop --release

# Install SARK
pip install -e .
```

### 3. Configuration

v1.4.0 introduces new optional configuration for Rust features. If not specified, safe defaults are used.

#### Environment Variables

```bash
# Enable Rust OPA (via feature flags)
SARK_RUST_OPA_ENABLED=true
SARK_RUST_OPA_ROLLOUT_PCT=5  # Start at 5%, increase gradually

# Enable Rust cache (via feature flags)
SARK_RUST_CACHE_ENABLED=true
SARK_RUST_CACHE_ROLLOUT_PCT=5  # Start at 5%, increase gradually

# Cache configuration
SARK_RUST_CACHE_MAX_SIZE=10000
SARK_RUST_CACHE_TTL_SECONDS=300
```

#### config.yaml

Add to your existing `config.yaml`:

```yaml
features:
  rust_opa:
    enabled: true
    rollout_percentage: 5
    fallback_on_error: true

  rust_cache:
    enabled: true
    rollout_percentage: 5
    max_size: 10000
    ttl_seconds: 300
    fallback_on_error: true
```

**Important:** Start with low rollout percentages (5%) and increase gradually after monitoring.

### 4. Verification

#### Check Rust Availability

```python
from sark._rust import RUST_AVAILABLE

if RUST_AVAILABLE:
    print("✅ Rust extensions loaded successfully")
else:
    print("⚠️  Rust extensions not available, using Python fallback")
```

#### Run Health Check

```bash
# Check overall health
sark health-check

# Check Rust-specific components
sark health-check --rust
```

Expected output:
```
✅ SARK v1.4.0 Health Check
✅ Database: Connected
✅ OPA (HTTP): Available
✅ Rust OPA: Available (4.2ms avg latency)
✅ Rust Cache: Available (0.3ms avg latency)
✅ Feature Flags: Configured
```

#### Verify Feature Flags

```bash
# Check feature flag status
curl http://localhost:8000/admin/features \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

Expected response:
```json
{
  "rust_opa": {
    "enabled": true,
    "rollout_percentage": 5,
    "status": "active"
  },
  "rust_cache": {
    "enabled": true,
    "rollout_percentage": 5,
    "status": "active"
  }
}
```

### 5. Gradual Rollout

Follow this recommended rollout schedule:

#### Phase 1: Dark Launch (Day 1)
```bash
# Deploy with 0% rollout
curl -X POST http://localhost:8000/admin/rollout/update \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"feature": "rust_opa", "percentage": 0}'

curl -X POST http://localhost:8000/admin/rollout/update \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"feature": "rust_cache", "percentage": 0}'
```

**Monitor:** Deployment success, no errors in logs

#### Phase 2: Canary (Days 2-3)
```bash
# Increase to 5%
curl -X POST http://localhost:8000/admin/rollout/update \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"feature": "rust_opa", "percentage": 5}'

curl -X POST http://localhost:8000/admin/rollout/update \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"feature": "rust_cache", "percentage": 5}'
```

**Monitor:**
- `opa_evaluation_duration_seconds{implementation="rust"}` < 5ms
- `cache_operation_duration_seconds{implementation="rust"}` < 0.5ms
- Error rate < 0.01%

#### Phase 3: Gradual Increase (Days 4-10)
```bash
# Day 4-5: 25%
# Day 6-7: 50%
# Day 8-10: 100%

# Update rollout
curl -X POST http://localhost:8000/admin/rollout/update \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"feature": "rust_opa", "percentage": 25}'
```

**At each stage:**
- Monitor for 24-48 hours
- Check metrics dashboards
- Verify no performance degradation
- Ensure error rates remain low

### 6. Monitoring

#### Key Metrics to Watch

**OPA Evaluation Latency:**
```promql
# Rust vs Python comparison
opa_evaluation_duration_seconds{implementation="rust", quantile="0.95"}
opa_evaluation_duration_seconds{implementation="python", quantile="0.95"}
```

**Cache Operation Latency:**
```promql
# Rust vs Redis comparison
cache_operation_duration_seconds{implementation="rust", quantile="0.95"}
cache_operation_duration_seconds{implementation="redis", quantile="0.95"}
```

**Feature Flag Distribution:**
```promql
# Percentage of requests using Rust
feature_flag_assignments_total{feature="rust_opa", implementation="rust"}
/ feature_flag_assignments_total{feature="rust_opa"}
```

**Error Rates:**
```promql
# Should remain < 0.01%
rate(opa_evaluation_errors_total{implementation="rust"}[5m])
rate(cache_operation_errors_total{implementation="rust"}[5m])
```

#### Grafana Dashboards

Import the included dashboards:
- `monitoring/grafana/dashboards/rust-performance.json`
- `monitoring/grafana/dashboards/feature-flags.json`

## Rollback Procedure

If issues occur at any rollout stage:

### Instant Rollback (< 1 second)

```bash
# Via admin API
curl -X POST http://localhost:8000/admin/rollout/rollback \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"feature": "rust_opa"}'

curl -X POST http://localhost:8000/admin/rollout/rollback \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"feature": "rust_cache"}'
```

This immediately sets rollout to 0%, routing all traffic to Python/Redis implementations.

### Manual Rollback via Environment Variables

```bash
# Set in environment or .env file
SARK_RUST_OPA_ROLLOUT_PCT=0
SARK_RUST_CACHE_ROLLOUT_PCT=0

# Restart SARK
systemctl restart sark
```

### Complete Rollback to v1.3.0

If necessary to completely revert:

```bash
# Downgrade to v1.3.0
pip install sark==1.3.0

# Restart services
systemctl restart sark
```

**Note:** Configuration files from v1.4.0 remain compatible with v1.3.0.

## Performance Expectations

After full rollout (100%), expect these improvements:

| Metric | v1.3.0 | v1.4.0 | Improvement |
|--------|--------|--------|-------------|
| OPA Evaluation (p95) | 42ms | 4.3ms | 9.8x faster |
| Cache Get/Set (p95) | 3.8ms | 0.24ms | 15.8x faster |
| Total Request (p95) | 98ms | 42ms | 2.3x faster |
| Throughput | 850 req/s | 2,100 req/s | 2.47x higher |
| Memory Usage | Baseline | +8% | Acceptable overhead |
| CPU Usage | Baseline | -15% | More efficient |

**Performance varies based on:**
- Policy complexity (simple policies show higher speedup)
- Cache hit rates (higher hit rates show more benefit)
- Request concurrency (Rust scales better under load)

## Troubleshooting

### Issue: Rust Not Available

**Symptom:**
```
RUST_AVAILABLE = False
Warning: Rust extensions not available, using Python fallback
```

**Solutions:**

1. **If installed from PyPI:** Ensure compatible platform
   ```bash
   python -c "import sys; print(sys.platform, sys.version)"
   # Should be: linux/darwin/win32, Python 3.11+
   ```

2. **If building from source:** Check Rust installation
   ```bash
   rustc --version  # Should be 1.70+
   cargo --version
   ```

3. **Rebuild Rust extensions:**
   ```bash
   maturin develop --release
   python -c "from sark._rust import RUST_AVAILABLE; print(RUST_AVAILABLE)"
   ```

### Issue: Performance Not Improved

**Symptom:** Metrics show no improvement after enabling Rust

**Solutions:**

1. **Verify feature flag rollout:**
   ```bash
   curl http://localhost:8000/admin/features \
     -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.rust_opa.rollout_percentage'
   ```

2. **Check implementation being used:**
   ```bash
   # Look at metrics
   curl http://localhost:8000/metrics | grep 'opa_evaluation.*implementation="rust"'
   ```

3. **Verify Rust is actually running:**
   ```bash
   # Check logs for Rust usage
   tail -f /var/log/sark/sark.log | grep "Using Rust"
   ```

### Issue: Errors with Rust Enabled

**Symptom:** Increased error rate after enabling Rust

**Solutions:**

1. **Check error logs:**
   ```bash
   tail -f /var/log/sark/sark.log | grep -i "error.*rust"
   ```

2. **Verify policy compatibility:**
   ```bash
   # Test specific policy with Rust
   sark test-policy --policy-file opa/policies/example.rego --use-rust
   ```

3. **Immediate rollback:**
   ```bash
   curl -X POST http://localhost:8000/admin/rollout/rollback \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -d '{"feature": "rust_opa"}'
   ```

4. **Report issue:** https://github.com/anthropics/sark/issues

### Issue: High Memory Usage

**Symptom:** Memory usage increases significantly after enabling Rust cache

**Solutions:**

1. **Adjust cache size:**
   ```yaml
   features:
     rust_cache:
       max_size: 5000  # Reduce from default 10000
   ```

2. **Monitor memory metrics:**
   ```promql
   process_resident_memory_bytes
   rust_cache_size_entries
   ```

3. **Trigger manual cleanup:**
   ```bash
   curl -X POST http://localhost:8000/admin/cache/cleanup \
     -H "Authorization: Bearer $ADMIN_TOKEN"
   ```

### Issue: Feature Flag Not Taking Effect

**Symptom:** Changes to rollout percentage don't seem to apply

**Solutions:**

1. **Verify API call succeeded:**
   ```bash
   curl -v -X POST http://localhost:8000/admin/rollout/update \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -d '{"feature": "rust_opa", "percentage": 25}'
   ```

2. **Check feature flag storage (Redis):**
   ```bash
   redis-cli GET "feature:rust_opa:rollout_pct"
   ```

3. **Restart may be required** if using file-based config:
   ```bash
   systemctl restart sark
   ```

## Getting Help

### Documentation
- **Release Notes:** `/docs/v1.4.0/RELEASE_NOTES.md`
- **Architecture:** `/docs/v1.4.0/ARCHITECTURE.md`
- **Developer Guide:** `/docs/v1.4.0/DEVELOPER_GUIDE.md`
- **Performance Report:** `/docs/v1.4.0/PERFORMANCE_REPORT.md`

### Support Channels
- **GitHub Issues:** https://github.com/anthropics/sark/issues
- **Documentation:** https://sark.readthedocs.io/
- **Discord:** https://discord.gg/sark (community support)

### Reporting Bugs

When reporting issues with v1.4.0 Rust features, include:

```bash
# Collect diagnostic information
sark diagnostics --rust > diagnostics.txt
```

This includes:
- SARK version
- Rust availability status
- Feature flag configuration
- Recent error logs
- Performance metrics snapshot

## FAQ

**Q: Will my existing OPA policies work with Rust OPA?**
A: Yes, 100% compatibility. No policy changes required.

**Q: What happens if Rust crashes?**
A: Automatic fallback to Python/HTTP implementation. Request succeeds.

**Q: Can I use Rust OPA without Rust cache?**
A: Yes, features are independent. Enable only what you need.

**Q: How do I know if Rust is actually being used?**
A: Check metrics: `opa_evaluation_duration_seconds{implementation="rust"}`

**Q: Can I roll back to v1.3.0 after upgrading?**
A: Yes, v1.4.0 is fully compatible. Simply `pip install sark==1.3.0`.

**Q: Do I need to recompile my Rust code for updates?**
A: No if using PyPI wheels. Yes if building from source.

**Q: What's the performance impact if Rust is unavailable?**
A: Zero impact. System runs identically to v1.3.0.

**Q: Can I test Rust features in development before production?**
A: Yes! Use feature flags at 100% in dev, 0% in prod initially.

---

**Successfully migrated?** Share your experience and performance results!

**Having issues?** Open an issue: https://github.com/anthropics/sark/issues/new
