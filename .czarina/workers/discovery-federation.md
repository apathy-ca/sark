# Workstream 2: Discovery & Federation Tests

**Worker ID**: discovery-federation
**Branch**: feat/tests-discovery-federation
**Duration**: 2-3 days
**Target Coverage**: 15 modules (0% → 85%)

---

## Objective

Write comprehensive tests for service discovery, tool registry, and federation services to achieve 85% code coverage.

---

## Modules to Test (15 modules)

### Discovery Services (6 modules)
1. `src/sark/services/discovery/discovery_service.py` (92 lines, 0% coverage)
2. `src/sark/services/discovery/search.py` (121 lines, 0% coverage)
3. `src/sark/services/discovery/tool_registry.py` (108 lines, 0% coverage)
4. `src/sark/api/v1/servers.py` (218 lines, 0% coverage)
5. `src/sark/api/v1/discovery.py` (156 lines, 0% coverage)
6. `src/sark/api/v1/tools.py` (142 lines, 0% coverage)

### Federation Services (6 modules)
7. `src/sark/services/federation/discovery.py` (202 lines, 0% coverage)
8. `src/sark/services/federation/routing.py` (203 lines, 0% coverage)
9. `src/sark/services/federation/trust.py` (208 lines, 0% coverage)
10. `src/sark/api/v2/federation.py` (185 lines, 0% coverage)
11. `src/sark/models/federation.py` (124 lines, 0% coverage)
12. `src/sark/models/discovery.py` (98 lines, 0% coverage)

### Database Models (3 modules)
13. `src/sark/db/models/server.py` (89 lines, 0% coverage)
14. `src/sark/db/models/tool.py` (76 lines, 0% coverage)
15. `src/sark/db/models/federation.py` (102 lines, 0% coverage)

---

## Test Strategy

### 1. Discovery Service Tests
**File**: `tests/unit/discovery/test_discovery_service.py`

**Coverage Goals**:
- Server registration
- Server health checking
- Server deregistration
- Network scanning (K8s, Consul)
- Service metadata extraction
- Error handling

**Example Test**:
```python
@pytest.mark.asyncio
async def test_register_server(discovery_service, postgres_connection):
    """Test MCP server registration."""
    server_info = {
        "name": "test-server",
        "endpoint": "http://localhost:8080",
        "transport": "http",
        "sensitivity_level": "public"
    }

    server = await discovery_service.register_server(server_info)
    assert server.id is not None
    assert server.name == "test-server"
    assert server.is_active is True
```

### 2. Tool Registry Tests
**File**: `tests/unit/discovery/test_tool_registry.py`

**Coverage Goals**:
- Tool registration
- Tool search and filtering
- Tool sensitivity levels
- Tool metadata
- Tool versioning
- Tool deactivation

### 3. Search Tests
**File**: `tests/unit/discovery/test_search.py`

**Coverage Goals**:
- Full-text search
- Fuzzy matching
- Tag-based filtering
- Sensitivity filtering
- Result ranking
- Pagination

### 4. Federation Discovery Tests
**File**: `tests/unit/federation/test_federation_discovery.py`

**Coverage Goals**:
- Peer discovery
- Trust chain validation
- Certificate verification
- mTLS handshake
- Peer health monitoring
- Failover logic

### 5. Federation Routing Tests
**File**: `tests/unit/federation/test_federation_routing.py`

**Coverage Goals**:
- Cross-instance routing
- Load balancing
- Circuit breaker
- Request forwarding
- Response aggregation
- Error propagation

### 6. Federation Trust Tests
**File**: `tests/unit/federation/test_federation_trust.py`

**Coverage Goals**:
- Certificate issuance
- Certificate revocation
- Trust chain building
- Trust score calculation
- Byzantine fault detection
- Gossip protocol

---

## Fixtures to Use

From `tests/fixtures/integration_docker.py`:
- `postgres_connection` - For server/tool registration
- `initialized_db` - For full discovery flow
- `valkey_connection` - For caching discovered services
- `all_services` - For integration tests

---

## Success Criteria

- ✅ All 15 modules have ≥85% code coverage
- ✅ All tests pass
- ✅ Tests cover discovery lifecycle (register → discover → health check → deregister)
- ✅ Federation tests cover peer communication
- ✅ Database models have full CRUD coverage
- ✅ Search functionality is thoroughly tested
- ✅ Edge cases covered (network failures, timeouts, invalid data)

---

## Test Pattern Example

```python
import pytest
from uuid import uuid4
from sark.services.discovery import DiscoveryService
from sark.models.discovery import ServerInfo, SensitivityLevel

class TestDiscoveryService:
    """Test MCP server discovery."""

    @pytest.fixture
    async def discovery_service(self, postgres_connection):
        """Create discovery service instance."""
        return DiscoveryService(db=postgres_connection)

    @pytest.mark.asyncio
    async def test_server_lifecycle(self, discovery_service):
        """Test complete server lifecycle."""
        # Register
        server = await discovery_service.register_server({
            "name": "test-server",
            "endpoint": "http://localhost:8080",
            "transport": "http"
        })
        assert server.is_active

        # Discover
        servers = await discovery_service.discover_servers()
        assert len(servers) >= 1
        assert any(s.id == server.id for s in servers)

        # Health check
        is_healthy = await discovery_service.check_health(server.id)
        assert is_healthy

        # Deregister
        await discovery_service.deregister_server(server.id)
        servers = await discovery_service.discover_servers()
        assert not any(s.id == server.id for s in servers)
```

---

## Priority Order

1. **High Priority** (Day 1):
   - Discovery service tests
   - Tool registry tests
   - Database model tests

2. **Medium Priority** (Day 2):
   - Search tests
   - Federation discovery tests
   - API endpoint tests

3. **Low Priority** (Day 3):
   - Federation routing tests
   - Federation trust tests
   - Performance tests

---

## Deliverables

1. Test files for all 15 modules
2. Coverage report showing 85%+ coverage
3. All tests passing in CI
4. Commit message:
   ```
   test: Add discovery & federation test suite

   - Add discovery service tests (88% coverage)
   - Add tool registry tests (90% coverage)
   - Add search tests (85% coverage)
   - Add federation discovery tests (86% coverage)
   - Add federation routing tests (84% coverage)
   - Add federation trust tests (87% coverage)
   - Add database model tests (92% coverage)

   Total: 15 modules, 400+ tests, 85%+ coverage

   Part of Phase 3 Workstream 2 (v1.3.1 implementation plan)
   ```

---

## Notes

- Use existing chaos tests as reference for federation resilience
- Test federation with multiple mock instances
- Validate discovery across network boundaries
- Test Byzantine fault scenarios
