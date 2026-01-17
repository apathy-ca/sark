# Worker: Gateway HTTP Transport - Production MVP

**Worker ID**: gateway-http
**Branch**: cz1/feat/gateway-http
**Duration**: 3-4 days
**Priority**: High
**Status**: Active

---

## Objective

Harden and validate the Gateway HTTP transport for production deployment. The HTTP client implementation exists but needs production readiness validation, performance optimization, enhanced observability, and comprehensive integration testing.

---

## Context

The Gateway HTTP transport (`src/sark/gateway/transports/http_client.py`) provides async HTTP communication with MCP Gateway servers. The implementation includes:
- ✅ Async HTTP client with connection pooling
- ✅ Pagination support for large result sets
- ✅ TTL-based response caching
- ✅ OPA authorization integration
- ✅ Retry logic with exponential backoff
- ✅ 39 unit tests (test_http_client.py)
- ✅ Basic documentation (HTTP_TRANSPORT.md)

**Production Gaps:**
- ⚠️ Edge case handling and error recovery
- ⚠️ Production observability (metrics, tracing)
- ⚠️ Load testing and performance validation
- ⚠️ Security hardening review
- ⚠️ Production deployment guide
- ⚠️ Operational runbook

---

## Tasks

### Task 1: Production Hardening & Edge Cases (Day 1)

**Objective**: Review and harden the HTTP client for production edge cases.

**Subtasks**:

1.1. **Connection Management Review**
- Review connection pool limits and cleanup
- Add connection health checks
- Implement graceful shutdown handling
- Add connection timeout circuit breakers

1.2. **Error Handling Enhancement**
- Review all exception paths
- Add specific error types for different failure modes
- Implement error context preservation
- Add retry budget tracking (prevent infinite retries)

1.3. **Edge Case Testing**
- Test network failures (connection refused, timeouts, DNS failures)
- Test malformed responses from Gateway
- Test partial failures (some servers unavailable)
- Test cache invalidation edge cases
- Test OPA unavailability scenarios

1.4. **Security Hardening**
- Review header injection vulnerabilities
- Validate URL construction (prevent SSRF)
- Review sensitive data logging (API keys, tokens)
- Add request/response size limits
- Review TLS/SSL configuration options

**Files**:
- `src/sark/gateway/transports/http_client.py` (review/enhance)
- `tests/unit/gateway/transports/test_http_client.py` (add edge case tests)
- `tests/integration/gateway/test_http_edge_cases.py` (NEW)

**Deliverable**:
```bash
git commit -m "feat(gateway): Harden HTTP transport for production edge cases

- Add connection health checks and graceful shutdown
- Enhance error handling with specific error types
- Add retry budget to prevent infinite retries
- Add edge case tests for network failures
- Review and fix security vulnerabilities (headers, URL construction)
- Add request/response size limits

Part of gateway-http production MVP

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: Observability & Monitoring (Day 2)

**Objective**: Add production-grade observability for the HTTP transport.

**Subtasks**:

2.1. **Metrics Integration**
- Add Prometheus metrics or compatible metric collection
- Track: request count, latency (p50/p95/p99), error rate, retry count
- Track: cache hit rate, connection pool utilization
- Track: OPA check latency and authorization decisions
- Add per-endpoint metrics breakdown

2.2. **Distributed Tracing**
- Add OpenTelemetry trace spans for all HTTP operations
- Propagate trace context to Gateway
- Add trace attributes for debugging (server_name, tool_name, user_id)
- Link OPA authorization checks to request traces

2.3. **Enhanced Logging**
- Review structured logging for all operations
- Add correlation IDs for request tracking
- Add latency logging for slow requests (>1s)
- Review log levels (avoid info spam in production)
- Add rate-limited error logging

2.4. **Health Checks Enhancement**
- Enhance `health_check()` with detailed diagnostics
- Add readiness vs liveness distinction
- Add dependency health checks (OPA, Gateway connectivity)
- Return detailed status for monitoring systems

**Files**:
- `src/sark/gateway/transports/http_client.py` (add metrics/tracing)
- `src/sark/observability/metrics.py` (NEW - if not exists)
- `src/sark/observability/tracing.py` (NEW - if not exists)
- `tests/unit/gateway/transports/test_http_observability.py` (NEW)
- `docs/gateway/HTTP_OBSERVABILITY.md` (NEW)

**Deliverable**:
```bash
git commit -m "feat(gateway): Add production observability to HTTP transport

- Add Prometheus metrics for requests, latency, errors, cache
- Add OpenTelemetry distributed tracing
- Add correlation IDs for request tracking
- Enhance health checks with detailed diagnostics
- Add monitoring documentation

Part of gateway-http production MVP

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: Performance Validation & Optimization (Day 3)

**Objective**: Validate and optimize HTTP transport performance for production load.

**Subtasks**:

3.1. **Load Testing**
- Create load test scenarios (100, 500, 1000 req/s)
- Test with realistic Gateway response times
- Test cache effectiveness under load
- Test connection pool saturation
- Identify bottlenecks and latency outliers

3.2. **Performance Benchmarks**
- Benchmark list_servers() with various page sizes
- Benchmark list_tools() with 1000+ tools
- Benchmark invoke_tool() with OPA authorization
- Benchmark cache hit/miss scenarios
- Document baseline performance metrics

3.3. **Optimization**
- Optimize connection pool settings based on load tests
- Review and optimize caching strategy
- Consider connection keep-alive optimization
- Review JSON parsing performance (large responses)
- Add batch operation support if needed

3.4. **Resource Profiling**
- Profile memory usage under sustained load
- Check for memory leaks (long-running scenarios)
- Profile CPU usage for hot paths
- Review asyncio task cleanup

**Files**:
- `tests/performance/load/test_gateway_http_load.py` (NEW)
- `tests/performance/benchmarks/test_http_benchmarks.py` (NEW)
- `docs/gateway/HTTP_PERFORMANCE.md` (NEW)

**Deliverable**:
```bash
git commit -m "feat(gateway): Add performance validation for HTTP transport

- Add load tests (100-1000 req/s scenarios)
- Add performance benchmarks for all operations
- Optimize connection pool settings for production
- Document baseline performance metrics
- Verify no memory leaks under sustained load

Performance targets achieved:
- p95 latency: <100ms
- Throughput: 1000+ req/s
- Cache hit rate: >80%

Part of gateway-http production MVP

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: Production Documentation & Runbook (Day 4)

**Objective**: Create comprehensive production deployment and operational documentation.

**Subtasks**:

4.1. **Production Deployment Guide**
- Document production configuration recommendations
- Document environment variables and settings
- Document connection pool sizing guidelines
- Document cache configuration for different loads
- Document monitoring and alerting setup
- Document security best practices

4.2. **Operational Runbook**
- Create troubleshooting guide for common issues
- Document error codes and resolution steps
- Document performance degradation scenarios
- Document failover and recovery procedures
- Document rollback procedures
- Add diagnostic commands and tools

4.3. **Integration Examples**
- Create production-ready example code
- Show full configuration with monitoring
- Show error handling patterns
- Show graceful shutdown implementation
- Show multi-environment configuration

4.4. **API Documentation Review**
- Review and enhance HTTP_TRANSPORT.md
- Add production configuration examples
- Document all error conditions
- Add architecture diagrams
- Add troubleshooting section

**Files**:
- `docs/gateway/HTTP_PRODUCTION_GUIDE.md` (NEW)
- `docs/gateway/HTTP_RUNBOOK.md` (NEW)
- `docs/gateway/HTTP_TRANSPORT.md` (enhance)
- `examples/gateway-integration/http_client_production.py` (NEW)
- `examples/gateway-integration/README.md` (update)

**Deliverable**:
```bash
git commit -m "docs(gateway): Add production deployment guide for HTTP transport

- Add production deployment guide with sizing recommendations
- Add operational runbook for troubleshooting
- Add production-ready example code
- Enhance API documentation
- Add monitoring and alerting guide

Part of gateway-http production MVP

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: Integration Testing & E2E Validation (Final Day)

**Objective**: Comprehensive end-to-end validation with real Gateway instances.

**Subtasks**:

5.1. **Integration Test Suite**
- Test against real Gateway instance (Docker)
- Test full auth flow (API key + user JWT + OPA)
- Test server discovery → tool listing → invocation flow
- Test pagination with large datasets
- Test cache behavior across multiple requests
- Test retry logic with simulated failures

5.2. **Multi-Scenario Testing**
- Test happy path (all systems healthy)
- Test Gateway unavailable (connection refused)
- Test OPA unavailable (authorization falls back)
- Test partial failures (some tools fail, some succeed)
- Test rate limiting scenarios
- Test timeout scenarios

5.3. **Production Readiness Checklist**
- ✅ All unit tests passing (90%+ coverage)
- ✅ All integration tests passing
- ✅ Load tests passing (performance targets met)
- ✅ Security review completed
- ✅ Documentation complete
- ✅ Monitoring/observability implemented
- ✅ Runbook created
- ✅ Example code validated

5.4. **Final Validation**
- Run full test suite
- Run coverage report
- Run load tests
- Review all documentation
- Create summary report

**Files**:
- `tests/integration/gateway/test_http_e2e_flow.py` (NEW/enhance)
- `tests/integration/gateway/test_http_multi_scenario.py` (NEW)
- `docs/gateway/PRODUCTION_READINESS.md` (NEW)

**Deliverable**:
```bash
git commit -m "test(gateway): Add comprehensive E2E tests for HTTP transport

- Add full auth flow integration tests
- Add multi-scenario testing (failures, timeouts, etc)
- Validate production readiness checklist
- All tests passing with >90% coverage
- Performance targets validated

Production readiness: ✅ READY

Part of gateway-http production MVP

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Success Criteria

### Functional Requirements
- ✅ All existing functionality preserved and enhanced
- ✅ Comprehensive error handling for all edge cases
- ✅ Graceful degradation when dependencies unavailable
- ✅ Security vulnerabilities addressed
- ✅ Production configuration validated

### Performance Requirements
- ✅ p95 latency: <100ms for all operations
- ✅ Throughput: 1000+ requests/second sustained
- ✅ Cache hit rate: >80% for read operations
- ✅ Connection pool: efficient utilization under load
- ✅ No memory leaks over 24-hour test

### Testing Requirements
- ✅ Unit test coverage: >90%
- ✅ Integration tests: all scenarios passing
- ✅ Load tests: performance targets achieved
- ✅ Edge case tests: all scenarios covered
- ✅ Security tests: vulnerabilities addressed

### Observability Requirements
- ✅ Prometheus metrics implemented
- ✅ Distributed tracing integrated
- ✅ Structured logging with correlation IDs
- ✅ Health checks with detailed diagnostics
- ✅ Monitoring dashboards documented

### Documentation Requirements
- ✅ Production deployment guide complete
- ✅ Operational runbook created
- ✅ API documentation enhanced
- ✅ Example code validated
- ✅ Troubleshooting guide complete

---

## Testing Strategy

### Unit Tests
- Existing: 39 tests in `test_http_client.py`
- Add: Edge case tests (~15 tests)
- Add: Observability tests (~10 tests)
- Target: >90% coverage

### Integration Tests
- Existing: Basic E2E tests
- Add: Full auth flow tests
- Add: Multi-scenario tests
- Add: Failure scenario tests

### Performance Tests
- NEW: Load tests (100/500/1000 req/s)
- NEW: Benchmark suite
- NEW: Memory leak tests
- NEW: Sustained load tests (1-hour duration)

---

## Files to Review/Create

### Review & Enhance
- `src/sark/gateway/transports/http_client.py`
- `tests/unit/gateway/transports/test_http_client.py`
- `docs/gateway/HTTP_TRANSPORT.md`

### Create New
- `src/sark/observability/metrics.py` (if not exists)
- `src/sark/observability/tracing.py` (if not exists)
- `tests/integration/gateway/test_http_edge_cases.py`
- `tests/integration/gateway/test_http_e2e_flow.py`
- `tests/integration/gateway/test_http_multi_scenario.py`
- `tests/performance/load/test_gateway_http_load.py`
- `tests/performance/benchmarks/test_http_benchmarks.py`
- `docs/gateway/HTTP_PRODUCTION_GUIDE.md`
- `docs/gateway/HTTP_RUNBOOK.md`
- `docs/gateway/HTTP_OBSERVABILITY.md`
- `docs/gateway/HTTP_PERFORMANCE.md`
- `docs/gateway/PRODUCTION_READINESS.md`
- `examples/gateway-integration/http_client_production.py`

---

## Dependencies

- httpx (existing)
- pytest, pytest-asyncio, pytest-httpx (existing)
- prometheus-client (for metrics)
- opentelemetry-api, opentelemetry-sdk (for tracing)
- locust or pytest-benchmark (for load testing)

---

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| p50 latency | <50ms | All operations |
| p95 latency | <100ms | All operations |
| p99 latency | <200ms | All operations |
| Throughput | 1000+ req/s | Sustained load |
| Cache hit rate | >80% | Read operations |
| Connection pool efficiency | >70% utilization | Under load |
| Memory growth | <10MB/hour | 24-hour stability test |
| Error rate | <0.1% | Under normal load |

---

## Rollout Strategy

1. **Local Testing** (Day 1-3)
   - Unit tests passing
   - Integration tests passing
   - Load tests passing

2. **Staging Deployment** (Day 4)
   - Deploy to staging environment
   - Run smoke tests
   - Monitor for 24 hours
   - Review metrics and logs

3. **Production Readiness Review** (Day 4)
   - Security review
   - Performance validation
   - Documentation review
   - Runbook validation

4. **Production Deployment** (Post-worker)
   - Gradual rollout (5% → 25% → 50% → 100%)
   - Monitor metrics and errors
   - Have rollback plan ready

---

## Notes

- Focus on production hardening, not new features
- Prioritize observability and debugging capabilities
- Ensure graceful degradation under failures
- Document all production configurations
- Create actionable runbook for on-call engineers
- Validate with realistic production scenarios

---

## Logging

Use the czarina logging functions to track progress:

```bash
# Source logging functions
source $(git rev-parse --show-toplevel)/../../czarina-core/logging.sh

# Log task progress
czarina_log_task_start "Task 1: Production Hardening"
czarina_log_checkpoint "edge_case_testing_complete"
czarina_log_task_complete "Task 1: Production Hardening"

# When all tasks done
czarina_log_worker_complete
```

**Your logs:**
- Worker log: ${CZARINA_WORKER_LOG}
- Event stream: ${CZARINA_EVENTS_LOG}

---

## Contact

For questions or blockers:
- Review existing HTTP client: `src/sark/gateway/transports/http_client.py`
- Review existing tests: `tests/unit/gateway/transports/test_http_client.py`
- Review existing docs: `docs/gateway/HTTP_TRANSPORT.md`
- Check integration examples: `examples/gateway-integration/`
