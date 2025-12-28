# Memory Profiling & Leak Detection

Memory profiling tests to ensure no memory leaks and stable memory usage.

## Overview

This directory contains tests for detecting memory leaks and profiling memory usage:

### Test Objectives

| Test Type | Duration | Purpose |
|-----------|----------|---------|
| Short-term leak detection | ~10 min | CI-friendly leak detection (100K operations) |
| Long-term stability | 24 hours | Production stability validation |
| Rust vs Python comparison | ~5 min | Compare memory footprint |
| Resource cleanup | ~2 min | Verify proper cleanup on close |

## Files

- **`test_memory_leaks.py`**: Memory leak detection tests
- **`profile_memory.sh`**: Automation script for memory profiling
- **`README.md`**: This file

## Running Memory Tests

### Quick Start

```bash
# Run short-term tests (CI-friendly, ~10 minutes)
./profile_memory.sh short

# Compare Rust vs Python memory usage
./profile_memory.sh comparison

# Verify resource cleanup
./profile_memory.sh cleanup

# Run all tests (except 24-hour test)
./profile_memory.sh all
```

### 24-Hour Stability Test

```bash
# Run in screen/tmux for long-running test
screen -S memory-test
./profile_memory.sh long

# Detach with Ctrl+A, D
# Reattach with: screen -r memory-test
```

## Test Scenarios

### 1. Short-term Leak Detection

```bash
pytest test_memory_leaks.py::test_opa_client_no_memory_leak_short -v -s
pytest test_memory_leaks.py::test_cache_no_memory_leak_short -v -s
```

**Purpose**: Detect obvious memory leaks quickly

**What it tests**:
- 100,000 OPA client operations
- 100,000 cache operations
- Memory growth monitoring
- Linear growth detection

**Acceptance criteria**:
- Total growth <50MB for OPA client
- Total growth <30MB for cache
- No linear memory growth pattern

**Duration**: ~5-10 minutes per test

### 2. Long-term Stability (24 hours)

```bash
pytest test_memory_leaks.py::test_no_memory_leak_24h -v -s
```

**Purpose**: Validate production stability

**What it tests**:
- Continuous operation for 24 hours
- Memory sampling every 5 minutes
- Growth rate analysis
- Memory stabilization

**Acceptance criteria**:
- Total growth <100MB over 24 hours
- Growth rate <1 MB/hour after stabilization
- No continuous linear growth

**Duration**: 24 hours

⚠️ **Important**: Run in `screen` or `tmux` for long tests!

### 3. Rust vs Python Comparison

```bash
# Set RUST_ENABLED=true if Rust implementation available
RUST_ENABLED=true pytest test_memory_leaks.py::test_rust_vs_python_memory_usage -v -s
```

**Purpose**: Compare memory footprint

**What it tests**:
- Same workload on both implementations
- Initial memory footprint
- Memory growth under load
- Memory efficiency

**Expected outcome**:
- Rust ≤ Python memory usage
- Document memory improvement percentage

**Duration**: ~5 minutes

### 4. Resource Cleanup

```bash
pytest test_memory_leaks.py::test_resource_cleanup_on_client_close -v -s
```

**Purpose**: Verify proper resource cleanup

**What it tests**:
- Memory before client creation
- Memory after client usage
- Memory after client close
- Garbage collection effectiveness

**Acceptance criteria**:
- Memory returns to within 10MB of baseline
- No resource leaks
- Connection pools properly closed

**Duration**: ~2 minutes

## Automation Script

### Usage

```bash
./profile_memory.sh <command>
```

### Commands

| Command | Description | Duration |
|---------|-------------|----------|
| `short` | Run short-term leak tests | ~10 min |
| `long` | Run 24-hour stability test | 24 hours |
| `comparison` | Rust vs Python comparison | ~5 min |
| `cleanup` | Resource cleanup test | ~2 min |
| `profiler` | Run with memory_profiler | Varies |
| `monitor` | Monitor system memory | Custom |
| `report` | Generate summary report | <1 min |
| `all` | All tests except long | ~20 min |

### Examples

```bash
# Short-term leak detection
./profile_memory.sh short

# 24-hour test (prompts for confirmation)
./profile_memory.sh long

# Monitor system memory for 10 minutes, sample every 10 seconds
./profile_memory.sh monitor 600 10

# Generate comprehensive report
./profile_memory.sh report
```

## Memory Profiler

The `memory_profiler` package can provide line-by-line memory usage:

### Installation

```bash
pip install memory-profiler
```

### Usage

```bash
# Profile with memory_profiler
./profile_memory.sh profiler

# Or manually
python -m memory_profiler test_memory_leaks.py
```

### Decorate Functions

Add `@profile` decorator to profile specific functions:

```python
from memory_profiler import profile

@profile
def my_function():
    # Function code here
    pass
```

## Interpreting Results

### Memory Growth Patterns

**✅ Good (No leak)**:
```
Initial: 100 MB
After 25K ops: 110 MB (+10 MB)
After 50K ops: 112 MB (+12 MB)
After 75K ops: 113 MB (+13 MB)
After 100K ops: 113 MB (+13 MB)
```
Memory stabilizes after initial growth (caching, buffers).

**❌ Bad (Leak)**:
```
Initial: 100 MB
After 25K ops: 110 MB (+10 MB)
After 50K ops: 120 MB (+20 MB)
After 75K ops: 130 MB (+30 MB)
After 100K ops: 140 MB (+40 MB)
```
Linear growth indicates a memory leak.

### Growth Rate Analysis

Tests calculate growth rate by comparing first and last quarters:

```
First quarter avg: 110 MB
Last quarter avg: 113 MB
Growth rate: 0.05 MB/hr
```

**Acceptable**: <1 MB/hr
**Warning**: 1-5 MB/hr
**Failure**: >5 MB/hr

## Monitoring During Tests

### System Resources

```bash
# Terminal 1: Run test
./profile_memory.sh short

# Terminal 2: Monitor memory
watch -n 5 'free -h'

# Terminal 3: Monitor process
watch -n 5 'ps aux | grep python | grep -v grep'
```

### With htop

```bash
# Install htop
sudo apt-get install htop

# Run htop in another terminal
htop -p $(pgrep -f test_memory_leaks.py)
```

## Troubleshooting

### Test Fails with "Possible memory leak"

**Causes**:
- Actual memory leak in code
- Test environment issues
- Other processes consuming memory
- OS caching

**Solutions**:
1. Run test in isolation (close other apps)
2. Check for actual leaks in code
3. Increase threshold if OS caching is culprit
4. Use memory_profiler for detailed analysis

### Out of Memory During Test

**Causes**:
- System has insufficient memory
- Large cache test on small system
- Memory leak in test itself

**Solutions**:
1. Reduce test parameters (fewer operations)
2. Run on machine with more RAM
3. Skip large cache tests
4. Check test code for leaks

### 24-hour Test Interrupted

**Causes**:
- System reboot
- SSH connection lost
- Process killed

**Prevention**:
1. Always use `screen` or `tmux`
2. Disable auto-updates during test
3. Use dedicated test machine

**Recovery**:
```bash
# Check if test is still running
ps aux | grep test_memory_leaks

# Reattach to screen
screen -r memory-test

# View partial results
cat tests/performance/memory/reports/memory_long_*.txt
```

## Acceptance Criteria

### Short-term Tests
- [ ] OPA client: <50MB growth for 100K requests
- [ ] Cache: <30MB growth for 100K operations
- [ ] No linear memory growth pattern
- [ ] All tests pass in <15 minutes

### Long-term Test
- [ ] Total growth <100MB over 24 hours
- [ ] Growth rate <1 MB/hr after stabilization
- [ ] No crashes or errors
- [ ] Memory usage stable

### Rust vs Python
- [ ] Rust memory usage ≤ Python
- [ ] Comparison documented
- [ ] No regressions

### Resource Cleanup
- [ ] Memory returns to baseline (within 10MB)
- [ ] No resource leaks
- [ ] All connections closed

## CI Integration

Short-term tests are suitable for CI:

```yaml
# .github/workflows/memory-tests.yml
- name: Run memory leak detection
  run: |
    cd tests/performance/memory
    ./profile_memory.sh short
```

Long-term tests should run on schedule:

```yaml
# Weekly 24-hour test
- cron: '0 0 * * 0'
```

## Best Practices

### Before Running Tests

1. **Close other applications**: Free up memory
2. **Check available memory**: Ensure sufficient RAM
3. **Use dedicated environment**: Avoid interference
4. **Disable auto-updates**: Prevent interruptions

### During Tests

1. **Monitor resources**: Watch memory, CPU, disk
2. **Check logs**: Look for errors or warnings
3. **Don't interrupt**: Let tests complete naturally
4. **Use screen/tmux**: For long-running tests

### After Tests

1. **Review reports**: Check all metrics
2. **Analyze trends**: Look for patterns
3. **Document findings**: Note any issues
4. **Archive results**: Keep for comparison

## See Also

- [Microbenchmarks](../benchmarks/README.md)
- [Load Testing](../load/README.md)
- [Stress Testing](../stress/README.md)
- [Worker Instructions](../../../.czarina/workers/performance-testing.md)
