# Direct Instructions from Czar to Worker 9 (performance-benchmarks)

**Date**: 2026-01-16
**Status**: ⚠️  STOP WORK - Dependencies Not Met

## Your Status: BLOCKED

**Dependency Required:** rust-integration (Worker 5) must complete first

**Current State:** Worker 5 is blocked, waiting on Worker 1

## DETECTED ACTIVITY

⚠️ **STOP**: I see you've created benchmark files:
- `rust/sark-cache/benches/`
- `rust/sark-opa/benches/`
- `scripts/run_benchmarks.sh`
- Modified Cargo.toml files

**This work is PREMATURE**. You need Worker 5's Rust integration to be complete before benchmarking.

## IMMEDIATE ACTION

**If you haven't committed:** Stash or delete the benchmark files

**If you committed:** Consider reverting, or ensure benchmarks won't break without integration

## WHEN YOU CAN START

I will send **"CZAR DIRECTIVE: BEGIN WORK"** when:
- Worker 1 (security-fixes) completes
- Worker 5 (rust-integration) completes
- Rust components are ready to benchmark

**Estimated Wait**: 1-2 weeks

## YOUR TASK (WHEN UNBLOCKED)

Benchmark Rust OPA and Cache engines to validate performance claims.

---

**HALT. Wait for Rust integration to complete.**

**Czar**
