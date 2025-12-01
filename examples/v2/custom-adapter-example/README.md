# Custom Adapter Example: Database Protocol

This example shows how to build a custom protocol adapter for SARK v2.0, using a database protocol as an example.

## What You'll Build

A complete **DatabaseAdapter** that:
- Discovers database schemas and tables
- Translates SQL queries into SARK capabilities
- Governs database access through SARK policies
- Audits all database queries

## Why This Example?

Database access is a common use case that demonstrates:
- **Discovery**: Introspecting database schema
- **Capabilities**: Each table operation is a capability
- **Validation**: SQL injection prevention
- **Invocation**: Executing queries safely
- **Health Checks**: Database connectivity monitoring

## Architecture

```
┌─────────────────────────────────────────────┐
│            SARK v2.0                        │
│  ┌────────────┐  ┌──────────┐  ┌────────┐  │
│  │  Policy    │  │  Audit   │  │  Auth  │  │
│  │  Engine    │  │  Logger  │  │Service │  │
│  └────────────┘  └──────────┘  └────────┘  │
└─────────────────────────────────────────────┘
                    ↓
         ProtocolAdapter Interface
                    ↓
        ┌───────────────────────┐
        │   DatabaseAdapter     │
        │                       │
        │ • discover_resources  │
        │ • get_capabilities    │
        │ • validate_request    │
        │ • invoke              │
        │ • health_check        │
        └───────────────────────┘
                    ↓
        ┌───────────────────────┐
        │   PostgreSQL          │
        │   (or any database)   │
        └───────────────────────┘
```

## Files

- `database_adapter.py` - Complete DatabaseAdapter implementation
- `test_database_adapter.py` - Comprehensive test suite
- `example_usage.py` - Example of using the adapter
- `policy.rego` - Sample database access policies

## Quick Start

### 1. Install Dependencies

```bash
pip install asyncpg  # For PostgreSQL
# Or: pip install aiomysql  # For MySQL
```

### 2. Review the Adapter Implementation

```bash
cat database_adapter.py
```

Key features:
- ✅ Discovers tables and views
- ✅ Creates capabilities for SELECT, INSERT, UPDATE, DELETE
- ✅ Validates SQL to prevent injection
- ✅ Enforces row-level security
- ✅ Logs all database operations

### 3. Run Tests

```bash
pytest test_database_adapter.py -v

# Expected output:
# test_protocol_properties PASSED
# test_discover_resources PASSED
# test_get_capabilities PASSED
# test_validate_request PASSED
# test_invoke_select PASSED
# test_invoke_insert PASSED
# test_health_check PASSED
```

### 4. Register with SARK

```bash
# Copy adapter to SARK adapters directory
cp database_adapter.py /path/to/sark/src/sark/adapters/

# Register in registry
# (See database_adapter.py for registration code)

# Restart SARK
docker-compose restart sark
```

### 5. Use the Adapter

```bash
python example_usage.py

# Output:
# 🔍 Discovering database...
# ✅ Found 5 tables: users, orders, products, reviews, analytics
#
# 🔑 Capabilities discovered:
#    • users-select
#    • users-insert
#    • users-update
#    • users-delete
#    • orders-select
#    ... (20 total)
#
# 📊 Querying users table...
# ✅ Query successful: 142 rows returned
#
# 📝 Complete audit trail available
```

## Adapter Implementation Highlights

### Discovery

```python
async def discover_resources(self, discovery_config):
    """Discover database tables and views."""
    conn = await asyncpg.connect(discovery_config["connection_string"])

    # Introspect schema
    tables = await conn.fetch("""
        SELECT table_name, table_type
        FROM information_schema.tables
        WHERE table_schema = 'public'
    """)

    # Create capabilities for each table
    capabilities = []
    for table in tables:
        for operation in ["select", "insert", "update", "delete"]:
            capabilities.append(CapabilitySchema(
                id=f"{table['table_name']}-{operation}",
                name=f"{operation.upper()} {table['table_name']}",
                # ...
            ))

    return [ResourceSchema(
        id=f"database-{db_name}",
        protocol="database",
        capabilities=capabilities
    )]
```

### Validation

```python
async def validate_request(self, request):
    """Validate SQL query for safety."""
    query = request.arguments.get("query", "")

    # Prevent SQL injection
    dangerous_patterns = [
        r";\s*DROP",
        r";\s*DELETE\s+FROM",
        r"--",
        r"/\*",
        r"xp_cmdshell"
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            raise ValidationError(f"Dangerous SQL pattern detected: {pattern}")

    # Ensure query matches capability
    operation = request.capability_id.split("-")[-1]
    if operation == "select" and not query.strip().upper().startswith("SELECT"):
        raise ValidationError("Query must be a SELECT for select capability")

    return True
```

### Invocation with Row-Level Security

```python
async def invoke(self, request):
    """Execute database query with row-level security."""
    conn = await asyncpg.connect(self._get_connection_string(request))

    # Apply row-level security filters
    query = request.arguments["query"]
    if "WHERE" in query.upper():
        query += f" AND tenant_id = '{request.principal_id}'"
    else:
        query += f" WHERE tenant_id = '{request.principal_id}'"

    # Execute query
    rows = await conn.fetch(query)

    return InvocationResult(
        success=True,
        result=[dict(row) for row in rows],
        metadata={
            "row_count": len(rows),
            "query": query
        }
    )
```

## Policy Example

Control database access with fine-grained policies:

```rego
package sark.policies.database

# Allow read access to non-sensitive tables
allow if {
    input.resource.protocol == "database"
    operation := split(input.capability.id, "-")[1]
    operation == "select"
    not is_sensitive_table(input.capability.name)
}

# Only DBAs can write to tables
allow if {
    input.resource.protocol == "database"
    operation := split(input.capability.id, "-")[1]
    operation in ["insert", "update", "delete"]
    input.principal.attributes.role == "dba"
}

# Prevent deletion in production
deny["Cannot delete in production"] if {
    input.resource.metadata.environment == "production"
    operation := split(input.capability.id, "-")[1]
    operation == "delete"
}

is_sensitive_table(table_name) if {
    sensitive := ["users", "payments", "credentials"]
    table_name in sensitive
}
```

## Testing Your Adapter

Run the comprehensive test suite:

```bash
# Unit tests
pytest test_database_adapter.py::TestDatabaseAdapter -v

# Integration tests
pytest test_database_adapter.py::TestDatabaseIntegration -v

# Contract tests (ensure adapter follows ProtocolAdapter interface)
pytest test_database_adapter.py::TestAdapterContract -v
```

## Extending the Example

Ideas for extending this adapter:

1. **Connection Pooling**: Reuse database connections
2. **Query Caching**: Cache frequent read queries
3. **Streaming Results**: For large result sets
4. **Transaction Support**: Multi-statement transactions
5. **Multiple Database Support**: MySQL, MongoDB, etc.
6. **Schema Migrations**: Track schema changes
7. **Query Analytics**: Log slow queries, query plans

## Learn More

- [Building Adapters Tutorial](../../../docs/tutorials/v2/BUILDING_ADAPTERS.md)
- [Protocol Adapter Spec](../../../docs/v2.0/PROTOCOL_ADAPTER_SPEC.md)
- [Adapter Development Guide](../../../docs/v2.0/ADAPTER_DEVELOPMENT_GUIDE.md)

## License

MIT
