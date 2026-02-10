# MCPServer → GridResource Migration Plan

## Overview

This document outlines the migration from the MCP-specific `MCPServer` model to the GRID-compliant `GridResource` model.

## Status

- ✅ GridResource model created with full GRID compliance
- ✅ Tests passing (12/12 tests)
- ⏳ Service migration (pending)
- ⏳ Full codebase migration (pending)

## Model Mapping

### Core Fields

| MCPServer Field | GridResource Field | Notes |
|----------------|-------------------|-------|
| `id` | `id` | UUID, unchanged |
| `name` | `name` | String, unchanged |
| `description` | `description` | String, unchanged |
| `status` | `status` | Enum: `ServerStatus` → `ResourceStatus` |
| `sensitivity_level` | `classification` | BREAKING: `SensitivityLevel` → `Classification` enum |
| `owner_id` | `owner_id` | UUID, unchanged |
| `team_id` | `team_id` | UUID, unchanged |
| `tags` | `tags` | JSON array, unchanged |
| `created_at` | `created_at` | Timestamp, unchanged |
| `updated_at` | `updated_at` | Timestamp, unchanged |

### MCP-Specific Fields → Metadata

These fields move to `extra_metadata` JSON column:

| MCPServer Field | GridResource Location | Migration Path |
|----------------|----------------------|----------------|
| `transport` | `extra_metadata['transport']` | Store as string |
| `endpoint` | `extra_metadata['endpoint']` | Store as string |
| `command` | `extra_metadata['command']` | Store as string |
| `mcp_version` | `extra_metadata['mcp_version']` | Store as string |
| `capabilities` | `extra_metadata['capabilities']` | Store as array |
| `health_endpoint` | `health_endpoint` | Kept at top level |
| `last_health_check` | `last_health_check` | Kept at top level |
| `consul_id` | `extra_metadata['consul_id']` | Store as string |
| `signature` | `extra_metadata['signature']` | Store as string |
| `extra_metadata` | `extra_metadata[*]` | Merge into metadata |

### New GridResource Fields

| Field | Type | Purpose |
|-------|------|---------|
| `type` | `ResourceType` enum | GRID: tool/data/service/device/infrastructure |
| `classification` | `Classification` enum | GRID: Public/Internal/Confidential/Secret |
| `provider_id` | String | GRID: External provider identifier |
| `parameters_schema` | JSON | GRID: Parameters schema for external resources |

## Table Mapping

- `mcp_servers` table → `grid_resources` table
- `mcp_tools` table → `resource_tools` table
- New: `resource_managers` association table

## Enum Migration

### SensitivityLevel → Classification

```python
# Old (MCPServer)
SensitivityLevel.LOW       # "low"
SensitivityLevel.MEDIUM    # "medium"
SensitivityLevel.HIGH      # "high"
SensitivityLevel.CRITICAL  # "critical"

# New (GridResource)
Classification.PUBLIC       # "Public"
Classification.INTERNAL     # "Internal"
Classification.CONFIDENTIAL # "Confidential"
Classification.SECRET       # "Secret"
```

**Suggested mapping:**
- `LOW` → `PUBLIC`
- `MEDIUM` → `INTERNAL`
- `HIGH` → `CONFIDENTIAL`
- `CRITICAL` → `SECRET`

### ServerStatus → ResourceStatus

```python
# Status enums are identical
ServerStatus.REGISTERED    → ResourceStatus.REGISTERED
ServerStatus.ACTIVE        → ResourceStatus.ACTIVE
ServerStatus.INACTIVE      → ResourceStatus.INACTIVE
ServerStatus.UNHEALTHY     → ResourceStatus.UNHEALTHY
ServerStatus.DECOMMISSIONED → ResourceStatus.DECOMMISSIONED
```

## Migration Approach

### Phase 1: Model Coexistence (CURRENT)
- [x] Create GridResource model
- [x] Add tests
- [x] Export from models package
- [ ] Both models coexist during transition

### Phase 2: Service Layer Migration
Files to update:
- `src/sark/services/discovery/discovery_service.py` (352 lines)
- `src/sark/services/discovery/tool_registry.py` (462 lines)
- `src/sark/services/discovery/search.py` (344 lines)
- `src/sark/services/bulk/__init__.py`

### Phase 3: API Layer Migration
Files to update:
- `src/sark/api/routers/servers.py`
- `src/sark/api/routers/tools.py`
- `src/sark/api/routers/export.py`
- `src/sark/api/routers/metrics.py`

### Phase 4: Adapter Migration
- `src/sark/adapters/mcp_adapter.py` (critical!)

### Phase 5: Test Migration
- Update all test files (29 test files reference MCPServer)
- Ensure 100% test coverage

### Phase 6: Database Migration
- Create Alembic migration script
- Migrate data from `mcp_servers` → `grid_resources`
- Transform `sensitivity_level` → `classification`
- Move MCP fields → `extra_metadata`

## Code Migration Pattern

### Example: Discovery Service

**Before:**
```python
from sark.models.mcp_server import MCPServer, ServerStatus

async def register_server(
    name: str,
    transport: TransportType,
    mcp_version: str,
    capabilities: list[str],
    ...
) -> MCPServer:
    server = MCPServer(
        name=name,
        transport=transport,
        mcp_version=mcp_version,
        capabilities=capabilities,
        status=ServerStatus.REGISTERED,
        sensitivity_level=SensitivityLevel.MEDIUM,
    )
    ...
```

**After:**
```python
from sark.models.resource import GridResource, ResourceStatus, ResourceType, Classification

async def register_server(
    name: str,
    transport: TransportType,
    mcp_version: str,
    capabilities: list[str],
    ...
) -> GridResource:
    server = GridResource(
        name=name,
        type=ResourceType.SERVICE,  # MCP servers are services
        classification=Classification.INTERNAL,  # Map from sensitivity_level
        status=ResourceStatus.REGISTERED,
        extra_metadata={
            "transport": transport,
            "mcp_version": mcp_version,
            "capabilities": capabilities,
            # ... other MCP-specific fields
        }
    )
    ...
```

## Breaking Changes

1. **Enum Values Changed**: `SensitivityLevel` values were lowercase (`"low"`), `Classification` values are title case (`"Internal"`). This affects:
   - API responses
   - Database queries filtering by classification
   - Policy rules checking sensitivity

2. **Table Names**: `mcp_servers` → `grid_resources`
   - Affects raw SQL queries
   - Affects migrations

3. **Field Locations**: MCP-specific fields now in `extra_metadata`
   - Code accessing `server.transport` must change to `server.extra_metadata['transport']`

## Backward Compatibility Strategy

### Option 1: Dual Write (Recommended for gradual migration)
- Write to both `mcp_servers` and `grid_resources` tables
- Read from `mcp_servers` initially, gradually switch to `grid_resources`
- Allows rollback

### Option 2: View/Alias
- Create database view: `mcp_servers` → `grid_resources`
- Minimal code changes
- Less flexible for schema evolution

### Option 3: Application Adapter
- Keep MCPServer model as wrapper around GridResource
- Translate between models at service boundary
- Clean separation but adds complexity

## Files Requiring Updates

Total: 62 files

### High Priority (Core Functionality)
1. Services (3 files, ~1,158 lines)
2. API Routers (4 files)
3. MCP Adapter (1 file, critical)

### Medium Priority (Tests)
4. Unit tests (29 files)
5. Integration tests
6. E2E tests

### Low Priority (Documentation)
7. Documentation files
8. Example code
9. Migration guides

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking API changes | High | Version API, provide migration guide |
| Data loss during migration | Critical | Test migration thoroughly, backup data |
| Performance degradation | Medium | Benchmark before/after, optimize queries |
| Test failures | Medium | Update tests incrementally |

## Recommendations

1. **Incremental Migration**: Start with discovery service, validate, then proceed
2. **Feature Flag**: Gate GridResource usage behind feature flag
3. **Parallel Run**: Run both systems in parallel initially
4. **Comprehensive Testing**: Update tests before migrating production code
5. **Database Migration**: Plan data migration carefully with rollback strategy

## Next Steps

1. ✅ Review and approve this migration plan
2. Migrate discovery service (proof of concept)
3. Update related tests
4. Create database migration script
5. Migrate remaining services
6. Update all tests
7. Update documentation
8. Deprecate MCPServer (future)
