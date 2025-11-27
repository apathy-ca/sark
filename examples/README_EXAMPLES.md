# SARK MCP Server Configuration Examples

This directory contains example MCP server configurations for various use cases.

## Quick Start

### Minimal Server Example

The simplest possible MCP server registration:

```bash
curl -X POST http://localhost:8000/api/v1/servers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @minimal-server.json
```

**File:** `minimal-server.json`
- Single echo tool
- HTTP transport
- Low sensitivity
- Perfect for testing

---

## Available Examples

### 1. `minimal-server.json`

**Use Case:** Getting started, testing, development

**Features:**
- Single simple tool (echo)
- HTTP transport
- Minimal configuration
- No special permissions needed

**When to use:**
- First time using SARK
- Testing the registration flow
- Development/staging environments

**Register:**
```bash
curl -X POST http://localhost:8000/api/v1/servers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @minimal-server.json
```

---

### 2. `production-server.json`

**Use Case:** Production analytics server with multiple tools

**Features:**
- 3 production-ready tools
- High sensitivity configuration
- Approval workflows for sensitive operations
- Comprehensive metadata
- Resource capabilities

**Tools:**
1. `query_metrics` - Query system metrics
2. `search_logs` - Search application logs
3. `export_report` - Export analytics reports (requires approval)

**When to use:**
- Production deployments
- Enterprise analytics platforms
- Multi-tool servers
- Servers requiring governance

**Register:**
```bash
curl -X POST http://localhost:8000/api/v1/servers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @production-server.json
```

**Note:** The `export_report` tool requires approval. Configure approval policies in OPA.

---

### 3. `stdio-server.json`

**Use Case:** Local command-line tools

**Features:**
- stdio transport (runs local binary)
- File system operations
- Low sensitivity
- Command-based execution

**Tools:**
1. `file_stats` - Get file statistics
2. `list_directory` - List directory contents

**When to use:**
- Local development tools
- CLI utilities
- On-premises tools
- Desktop applications

**Register:**
```bash
# Ensure the binary exists
which /usr/local/bin/my-mcp-tool

# Register the server
curl -X POST http://localhost:8000/api/v1/servers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @stdio-server.json
```

**Security Note:** stdio transport executes local commands. Ensure the binary is trusted and properly secured.

---

## Configuration Options Reference

### Transport Types

```json
{
  "transport": "http",      // HTTP/HTTPS endpoint
  "endpoint": "https://..."
}
```

```json
{
  "transport": "stdio",     // Local command execution
  "command": "/path/to/binary"
}
```

```json
{
  "transport": "sse",       // Server-Sent Events
  "endpoint": "https://.../stream"
}
```

### Sensitivity Levels

| Level | Use Case | Examples |
|-------|----------|----------|
| `low` | Public data, read-only operations | echo, file stats, public APIs |
| `medium` | Internal data, standard operations | metrics, logs, analytics |
| `high` | Sensitive data, write operations | user data, exports, database writes |
| `critical` | PII, financial data, system access | payment processing, admin tools |

### Capabilities

```json
{
  "capabilities": [
    "tools",      // Exposes executable tools
    "resources",  // Provides data resources
    "prompts",    // Provides prompt templates
    "sampling"    // Supports model sampling
  ]
}
```

### Tool Parameters

All tool parameters must be valid [JSON Schema](https://json-schema.org/):

```json
{
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query",
        "maxLength": 500
      },
      "limit": {
        "type": "integer",
        "minimum": 1,
        "maximum": 100,
        "default": 10
      }
    },
    "required": ["query"]
  }
}
```

**Supported types:**
- `string` - Text values (use maxLength)
- `integer` / `number` - Numeric values (use minimum/maximum)
- `boolean` - True/false
- `array` - Lists (use items schema)
- `object` - Nested structures
- `enum` - Predefined values

### Metadata

Add custom metadata for organization:

```json
{
  "metadata": {
    "owner": "team@example.com",
    "cost_center": "engineering",
    "sla_tier": "platinum",
    "version": "2.1.0",
    "custom_field": "any value"
  }
}
```

---

## Testing Your Configuration

### 1. Validate JSON Syntax

```bash
# Use jq to validate JSON
jq . < my-server.json

# If valid, jq will pretty-print it
# If invalid, you'll get an error message
```

### 2. Test Registration (Dry Run)

```bash
# Test without actually registering
curl -X POST http://localhost:8000/api/v1/servers/validate \
  -H "Content-Type: application/json" \
  -d @my-server.json
```

### 3. Register Server

```bash
# Actual registration
curl -X POST http://localhost:8000/api/v1/servers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @my-server.json
```

### 4. Verify Registration

```bash
# List all servers
curl -X GET http://localhost:8000/api/v1/servers \
  -H "Authorization: Bearer $TOKEN"

# Get specific server by ID
curl -X GET http://localhost:8000/api/v1/servers/{server_id} \
  -H "Authorization: Bearer $TOKEN"
```

---

## Common Patterns

### Pattern: Read-Only Analytics Tool

```json
{
  "name": "read_only_analytics",
  "transport": "http",
  "endpoint": "https://analytics.example.com",
  "sensitivity_level": "medium",
  "tools": [{
    "name": "get_report",
    "description": "Retrieve analytics report",
    "parameters": {
      "type": "object",
      "properties": {
        "report_id": {"type": "string"},
        "format": {"type": "string", "enum": ["json", "csv"]}
      },
      "required": ["report_id"]
    },
    "sensitivity_level": "medium"
  }]
}
```

### Pattern: Write Tool with Approval

```json
{
  "tools": [{
    "name": "delete_resource",
    "description": "Delete a resource (requires approval)",
    "parameters": {
      "type": "object",
      "properties": {
        "resource_id": {"type": "string"},
        "justification": {"type": "string", "minLength": 10}
      },
      "required": ["resource_id", "justification"]
    },
    "sensitivity_level": "high",
    "requires_approval": true
  }]
}
```

### Pattern: Time-Bounded Tool

```json
{
  "tools": [{
    "name": "get_recent_data",
    "description": "Get data from the last 24 hours only",
    "parameters": {
      "type": "object",
      "properties": {
        "hours_ago": {
          "type": "integer",
          "minimum": 1,
          "maximum": 24,
          "description": "How many hours back to query"
        }
      }
    }
  }]
}
```

### Pattern: Tool with Strict Enum

```json
{
  "tools": [{
    "name": "query_database",
    "parameters": {
      "type": "object",
      "properties": {
        "database": {
          "type": "string",
          "enum": ["analytics_readonly", "reporting_readonly"],
          "description": "Only approved read-only databases"
        },
        "query": {
          "type": "string",
          "pattern": "^SELECT.*",
          "description": "Only SELECT queries allowed"
        }
      }
    }
  }]
}
```

---

## Troubleshooting

### Error: "Invalid tool schema"

**Problem:** Tool parameters don't match JSON Schema spec.

**Solution:**
1. Validate JSON Schema: https://www.jsonschemavalidator.net/
2. Ensure all properties have `type` specified
3. Check that `required` array matches property names

### Error: "Transport validation failed"

**Problem:** Transport configuration is incomplete.

**Solution:**
- For `http`: Provide `endpoint` (must be valid URL)
- For `stdio`: Provide `command` (must be absolute path)
- For `sse`: Provide `endpoint` (must be valid URL)

### Error: "Server registration denied by policy"

**Problem:** OPA policy blocked the registration.

**Solution:**
1. Check audit logs: `/api/v1/audit/events?event_type=authorization_denied`
2. Review OPA policies in `opa/policies/`
3. Ensure you have `server:register` permission
4. Check if sensitivity level is allowed

### Error: "Tool sensitivity level mismatch"

**Problem:** Tool sensitivity level higher than server sensitivity level.

**Solution:**
Set server sensitivity_level >= max tool sensitivity_level:
```json
{
  "sensitivity_level": "high",  // Server level
  "tools": [
    {"sensitivity_level": "medium"},  // OK
    {"sensitivity_level": "high"}     // OK
  ]
}
```

---

## Best Practices

### 1. Use Descriptive Names

❌ Bad:
```json
{"name": "tool1"}
```

✅ Good:
```json
{"name": "query_customer_analytics"}
```

### 2. Provide Detailed Descriptions

❌ Bad:
```json
{"description": "Gets data"}
```

✅ Good:
```json
{"description": "Queries customer analytics data from TimescaleDB for the specified date range, with support for filtering by region and product category"}
```

### 3. Use Strict Parameter Validation

❌ Bad:
```json
{
  "parameters": {
    "type": "object",
    "properties": {
      "query": {"type": "string"}  // No limits!
    }
  }
}
```

✅ Good:
```json
{
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "maxLength": 1000,
        "pattern": "^SELECT.*"
      }
    }
  }
}
```

### 4. Set Appropriate Sensitivity Levels

**Guidelines:**
- Public, read-only data → `low`
- Internal data, standard operations → `medium`
- Sensitive data, write operations → `high`
- PII, compliance-critical → `critical`

### 5. Include Metadata

```json
{
  "metadata": {
    "owner": "team@example.com",
    "documentation_url": "https://docs.example.com",
    "support_contact": "oncall@example.com",
    "cost_center": "engineering",
    "version": "1.0.0"
  }
}
```

### 6. Version Your Servers

```json
{
  "name": "analytics-server-v2",  // Include version in name
  "metadata": {
    "version": "2.1.0",
    "changelog_url": "https://docs.example.com/changelog"
  }
}
```

---

## Next Steps

1. **Choose an example** that matches your use case
2. **Customize it** with your server details
3. **Validate** the JSON syntax
4. **Test** in a development environment
5. **Register** with SARK
6. **Verify** the registration
7. **Configure policies** in OPA (if needed)

**Additional Resources:**
- [API Reference](../docs/API_REFERENCE.md)
- [MCP FAQ](../docs/FAQ.md#mcp-protocol-questions)
- [OPA Policy Guide](../docs/OPA_POLICY_GUIDE.md)
- [Quick Start Guide](../docs/QUICKSTART.md)

---

**Questions or Issues?**
- Check [FAQ](../docs/FAQ.md)
- Review [Troubleshooting Guide](../docs/TROUBLESHOOTING.md)
- Contact support@company.com
