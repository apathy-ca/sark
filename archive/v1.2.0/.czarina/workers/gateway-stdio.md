# Gateway stdio Transport Developer

## Role
Implement stdio transport for SARK Gateway client, enabling subprocess-based MCP communication via stdin/stdout.

## Version Assignments
- v1.2.0-stdio

## Responsibilities

### v1.2.0-stdio (stdio Transport - 180K tokens)
- Implement `src/sark/gateway/transports/stdio_client.py` with process lifecycle management
- Add JSON-RPC message handling over stdin/stdout
- Implement health checks (heartbeat every 10s) and resource limits
- Create comprehensive unit tests (15+ tests)
- Write documentation for STDIO_TRANSPORT.md
- Achieve 90%+ code coverage
- Ensure no process leaks or zombie processes

## Files
- `src/sark/gateway/transports/stdio_client.py` (NEW - 180+ lines)
- `tests/unit/gateway/transports/test_stdio_client.py` (NEW - 200+ lines)
- `docs/gateway/STDIO_TRANSPORT.md` (NEW)

## Tech Stack
- Python 3.11+
- asyncio.subprocess (async process management)
- JSON-RPC 2.0 protocol
- pytest + pytest-asyncio (testing)

## Token Budget
Total: 180K tokens
- v1.2.0-stdio: 180K tokens

## Git Workflow
Branches by version:
- v1.2.0-stdio: feat/gateway-stdio-transport

When complete:
1. Commit changes with descriptive messages
2. Push to branch feat/gateway-stdio-transport
3. Create PR to main
4. Update token metrics in status

## Pattern Library
Review before starting:
- czarina-core/patterns/ERROR_RECOVERY_PATTERNS.md
- czarina-core/patterns/CZARINA_PATTERNS.md

## Version Completion Criteria

### v1.2.0-stdio Complete When:
- [ ] stdio transport with subprocess creation and management
- [ ] JSON-RPC message handling over stdin/stdout
- [ ] Process lifecycle (start, stop, restart) working
- [ ] Health checks detect hung processes (<15s)
- [ ] Resource limits enforced (memory: 1GB, CPU: 80%, FDs: 1000)
- [ ] No zombie processes created
- [ ] Clean shutdown on SIGTERM
- [ ] Auto-restart on crash (max 3 attempts)
- [ ] 15+ unit tests passing
- [ ] 90%+ code coverage
- [ ] No leaked file descriptors
- [ ] STDIO_TRANSPORT.md documentation complete
- [ ] Token budget: ≤ 198K tokens (110% of projected)