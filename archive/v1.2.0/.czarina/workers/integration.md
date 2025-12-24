# Gateway Integration & E2E Testing Engineer

## Role
Integrate all Gateway transports into unified client, implement comprehensive error handling, and create end-to-end test suite.

## Version Assignments
- v1.2.0-integration

## Responsibilities

### v1.2.0-integration (Integration & E2E Testing - 350K tokens)
- Update `src/sark/gateway/client.py` to unified client with automatic transport selection
- Implement `src/sark/gateway/error_handler.py` with circuit breaker and retry logic
- Create comprehensive E2E test suite (50+ tests) covering all transports
- Validate authorization flow end-to-end
- Verify performance benchmarks (<100ms p95)
- Write documentation for CLIENT_USAGE.md and ERROR_HANDLING.md

## Files
- `src/sark/gateway/client.py` (UPDATE - existing file)
- `src/sark/gateway/error_handler.py` (NEW - 100+ lines)
- `tests/integration/gateway/test_gateway_e2e.py` (NEW - 500+ lines)
- `docs/gateway/CLIENT_USAGE.md` (NEW)
- `docs/gateway/ERROR_HANDLING.md` (NEW)

## Tech Stack
- Python 3.11+
- httpx, asyncio (from transports)
- pytest + pytest-asyncio + pytest-httpx (testing)
- Mock MCP server for testing

## Token Budget
Total: 350K tokens
- v1.2.0-integration: 350K tokens

## Git Workflow
Branches by version:
- v1.2.0-integration: feat/gateway-integration

Dependencies:
- MUST wait for gateway-http-sse and gateway-stdio to complete
- Merge their branches before starting

When complete:
1. Commit changes with descriptive messages
2. Push to branch feat/gateway-integration
3. Create PR to main
4. Update token metrics in status

## Pattern Library
Review before starting:
- czarina-core/patterns/ERROR_RECOVERY_PATTERNS.md
- czarina-core/patterns/CZARINA_PATTERNS.md

## Version Completion Criteria

### v1.2.0-integration Complete When:
- [ ] Unified GatewayClient with automatic transport selection
- [ ] Error handler with timeout handling (30s default)
- [ ] Circuit breaker (5 failures → open state)
- [ ] Retry logic with exponential backoff (3 attempts)
- [ ] 50+ integration tests covering all 3 transports
- [ ] 10+ E2E scenarios validated (HTTP auth, SSE streaming, stdio subprocess)
- [ ] Authorization flow verified end-to-end with OPA
- [ ] Parameter filtering verified
- [ ] Audit logging validated
- [ ] Performance benchmarks met (<100ms p95)
- [ ] CLIENT_USAGE.md and ERROR_HANDLING.md complete
- [ ] Token budget: ≤ 385K tokens (110% of projected)