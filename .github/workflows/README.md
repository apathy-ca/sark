# Performance Testing CI/CD

Automated performance testing workflows for continuous performance validation.

## Workflows

### `performance.yml`

Comprehensive performance testing automation with multiple triggers and test suites.

#### Triggers

| Trigger | When | Test Suite |
|---------|------|------------|
| **Pull Request** | Changes to `rust/**` or `src/sark/services/policy/**` | Quick performance check |
| **Weekly Schedule** | Every Sunday at midnight | Full benchmark suite + load tests + memory tests |
| **Monthly Schedule** | First Sunday of month | Full suite + stress tests |
| **Manual Dispatch** | On-demand via GitHub UI | Configurable test suite |

#### Jobs

##### 1. Quick Performance Check (PR)

**Purpose**: Fast feedback on PRs

**Tests**:
- Subset of benchmarks (simple policies, basic cache ops)
- ~5-10 minutes duration
- Regression detection with 10% threshold

**When**: On every PR that touches performance-critical code

##### 2. Full Benchmark Suite (Weekly)

**Purpose**: Comprehensive performance validation

**Tests**:
- All microbenchmarks (OPA + cache)
- Comparison against baseline
- Statistical analysis
- ~30 minutes duration

**When**: Weekly scheduled run

##### 3. Load Tests (Weekly)

**Purpose**: Validate sustained performance

**Tests**:
- Baseline load test (100 req/s, 30 min)
- Performance target validation
- Resource monitoring

**Requirements**:
- Redis service container
- PostgreSQL service container
- SARK server running

**When**: Weekly scheduled run

##### 4. Memory Tests (Weekly)

**Purpose**: Detect memory leaks

**Tests**:
- Short-term leak detection (100K operations)
- Resource cleanup verification
- ~10-15 minutes duration

**When**: Weekly scheduled run

##### 5. Stress Tests (Monthly)

**Purpose**: Find breaking points

**Tests**:
- Extreme throughput
- Large policies/caches
- Failure recovery

**When**: First Sunday of each month

##### 6. Performance Report (Weekly)

**Purpose**: Aggregate results into report

**Actions**:
- Collect all test results
- Generate performance report
- Upload as artifact
- Comment on PR (if applicable)

**When**: After all weekly tests complete

## Regression Detection

### Script: `check_performance_regression.py`

Compares current benchmarks against baseline to detect regressions.

#### Usage

```bash
# Compare against baseline
python scripts/check_performance_regression.py \
  --current output.json \
  --baseline baseline.json \
  --threshold 0.10

# Check current only (no baseline)
python scripts/check_performance_regression.py \
  --current output.json
```

#### Thresholds

| Threshold | Meaning | Action |
|-----------|---------|--------|
| 10% slower | Performance regression | ❌ Fail CI |
| 10% faster | Performance improvement | ✅ Report |
| Within 10% | No significant change | ✅ Pass |

#### Absolute Targets

Also checks absolute performance targets:

| Target | Threshold | Component |
|--------|-----------|-----------|
| OPA p95 latency | <5ms | Rust OPA engine |
| Cache p95 latency | <0.5ms | Rust cache |

### Baseline Management

Baselines are saved using pytest-benchmark's `--benchmark-save` option:

```bash
# Save new baseline
pytest tests/performance/benchmarks/ \
  --benchmark-only \
  --benchmark-save=baseline

# Compare against baseline
pytest tests/performance/benchmarks/ \
  --benchmark-only \
  --benchmark-compare=baseline
```

Baselines are stored in `.benchmarks/` directory (git-ignored).

## Manual Workflow Triggers

### GitHub UI

1. Go to **Actions** tab
2. Select **Performance Tests** workflow
3. Click **Run workflow**
4. Choose test suite:
   - `quick`: Quick performance check
   - `full`: Full benchmark suite
   - `benchmarks`: Benchmarks only
   - `load`: Load tests only
   - `memory`: Memory tests only

### GitHub CLI

```bash
# Run quick tests
gh workflow run performance.yml -f test_suite=quick

# Run full suite
gh workflow run performance.yml -f test_suite=full

# Run specific suite
gh workflow run performance.yml -f test_suite=benchmarks
```

## Artifacts

All test results are uploaded as artifacts:

| Artifact | Contents | Retention |
|----------|----------|-----------|
| `quick-benchmark-results` | Quick PR check results | 30 days |
| `benchmark-results` | Full benchmark results + report | 90 days |
| `load-test-results` | Load test HTML/CSV reports | 90 days |
| `memory-test-results` | Memory profiling reports | 90 days |
| `stress-test-results` | Stress test results | 90 days |
| `performance-report` | Aggregated performance report | 365 days |

### Downloading Artifacts

```bash
# List artifacts
gh run list --workflow=performance.yml

# Download artifacts for specific run
gh run download <run-id>

# Download specific artifact
gh run download <run-id> -n benchmark-results
```

## Configuration

### Runner Requirements

Tests run on `ubuntu-latest-16core` for consistent performance:

- 16 CPU cores
- Sufficient memory for load testing
- Isolated environment

For self-hosted runners, ensure:
- Dedicated hardware
- No other workloads
- Consistent environment

### Service Dependencies

Load tests require:

- **Redis**: Port 6379, health checks enabled
- **PostgreSQL**: Port 5432, health checks enabled

Configured in workflow using GitHub Actions service containers.

### Environment Variables

```yaml
env:
  RUST_ENABLED: true          # Enable Rust implementations
  DATABASE_URL: postgresql://postgres:testpass@localhost:5432/sark_test
  REDIS_URL: redis://localhost:6379
```

## Monitoring CI Performance

### GitHub Actions Metrics

Monitor workflow execution:
- Duration trends
- Failure rates
- Artifact sizes

### Performance Trends

Track performance over time:
- Compare benchmark results across runs
- Monitor for gradual degradation
- Identify optimization opportunities

### Alerts

Set up alerts for:
- Workflow failures
- Performance regressions
- Long-running tests (>1 hour)

## Troubleshooting

### Workflow Fails on PR

**Common causes**:
- Performance regression >10%
- Benchmark setup issues
- Missing dependencies

**Solutions**:
1. Check workflow logs
2. Run benchmarks locally
3. Compare against baseline
4. Fix regression or update threshold

### Load Test Failures

**Common causes**:
- Services not ready
- Insufficient resources
- Timeouts

**Solutions**:
1. Check service container logs
2. Increase wait times
3. Verify port mappings
4. Check resource limits

### Memory Test Failures

**Common causes**:
- Actual memory leak
- Threshold too strict
- Environmental variance

**Solutions**:
1. Run memory tests locally
2. Use memory_profiler for analysis
3. Review recent changes
4. Adjust threshold if needed

## Best Practices

### For Contributors

1. **Run benchmarks locally** before pushing
2. **Check for regressions** in PR checks
3. **Investigate failures** before merging
4. **Update baselines** when intentionally changing performance

### For Maintainers

1. **Review weekly reports** from scheduled runs
2. **Update baselines** quarterly or after major changes
3. **Adjust thresholds** based on variance
4. **Archive historical data** for trend analysis

### For Release Management

1. **Run full suite** before releases
2. **Generate comprehensive report**
3. **Include in release notes**
4. **Update documentation** with new baselines

## Future Enhancements

### Planned Improvements

- [ ] Performance trend visualization
- [ ] Automatic baseline updates
- [ ] Slack/email notifications
- [ ] Performance dashboard
- [ ] Cross-version comparisons
- [ ] Resource usage tracking

### Integration Ideas

- **Grafana**: Real-time performance metrics
- **DataDog**: APM integration
- **PagerDuty**: Critical regression alerts
- **Slack**: Weekly performance summaries

## See Also

- [Performance Testing Documentation](../../tests/performance/)
- [Benchmark README](../../tests/performance/benchmarks/README.md)
- [Load Testing README](../../tests/performance/load/README.md)
- [Memory Profiling README](../../tests/performance/memory/README.md)
- [Performance Report Template](../../docs/v1.4.0/PERFORMANCE_REPORT.md)
