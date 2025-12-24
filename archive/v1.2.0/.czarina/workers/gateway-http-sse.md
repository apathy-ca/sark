# Gateway HTTP/SSE Transport Developer

## Role
Implement HTTP and SSE transports for SARK Gateway client, enabling communication with MCP servers via REST APIs and server-sent events streaming.

## Version Assignments
- v1.2.0-http-sse

## Responsibilities

### v1.2.0-http-sse (HTTP & SSE Transports - 450K tokens)
- Implement `src/sark/gateway/transports/http_client.py` with async HTTP client, pagination, caching, and OPA integration
- Implement `src/sark/gateway/transports/sse_client.py` with streaming support, connection pooling, and reconnection logic
- Create comprehensive unit tests (35+ tests) for both transports
- Write documentation for HTTP_TRANSPORT.md and SSE_TRANSPORT.md
- Achieve 90%+ code coverage for new code
- Ensure performance <100ms p95 latency

## Files
- `src/sark/gateway/transports/http_client.py` (NEW - 200+ lines)
- `src/sark/gateway/transports/sse_client.py` (NEW - 150+ lines)
- `tests/unit/gateway/transports/test_http_client.py` (NEW - 300+ lines)
- `tests/unit/gateway/transports/test_sse_client.py` (NEW - 200+ lines)
- `docs/gateway/HTTP_TRANSPORT.md` (NEW)
- `docs/gateway/SSE_TRANSPORT.md` (NEW)

## Tech Stack
- Python 3.11+
- httpx (async HTTP client)
- asyncio (async programming)
- cachetools (TTL caching)
- OPA client (existing in codebase)
- pytest + pytest-asyncio (testing)

## Token Budget
Total: 450K tokens
- v1.2.0-http-sse: 450K tokens

## Git Workflow
Branches by version:
- v1.2.0-http-sse: feat/gateway-http-sse-transport

When complete:
1. Commit changes with descriptive messages
2. Push to branch feat/gateway-http-sse-transport
3. Create PR to main
4. Update token metrics in status

## Pattern Library
Review before starting:
- czarina-core/patterns/ERROR_RECOVERY_PATTERNS.md
- czarina-core/patterns/CZARINA_PATTERNS.md

## Version Completion Criteria

### v1.2.0-http-sse Complete When:
- [ ] HTTP client with server discovery, tool listing, and invocation
- [ ] Pagination working for 1000+ servers
- [ ] TTL caching with 5-minute default and >80% hit rate
- [ ] OPA authorization integrated for tool invocation
- [ ] SSE client with streaming support for 100+ events
- [ ] Connection pooling (max 50 concurrent for SSE)
- [ ] Automatic reconnection with exponential backoff
- [ ] 35+ unit tests passing
- [ ] 90%+ code coverage
- [ ] Performance <100ms p95 latency
- [ ] HTTP_TRANSPORT.md and SSE_TRANSPORT.md documentation complete
- [ ] Token budget: ≤ 495K tokens (110% of projected)