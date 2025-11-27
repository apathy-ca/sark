# SARK Interactive MCP Examples

This directory contains interactive Python examples demonstrating how to use SARK to govern and interact with MCP (Model Context Protocol) servers.

## Examples Overview

| Example | Description | Difficulty | Prerequisites |
|---------|-------------|------------|---------------|
| [01_basic_tool_invocation.py](01_basic_tool_invocation.py) | Simple tool invocation through SARK | ⭐ Easy | Running SARK + 1 MCP server |
| [02_multi_tool_workflow.py](02_multi_tool_workflow.py) | Chain multiple tools in a workflow | ⭐⭐ Medium | Multiple MCP servers with tools |
| [03_approval_workflow.py](03_approval_workflow.py) | Break-glass approval for sensitive tools | ⭐⭐⭐ Advanced | Admin + user accounts |
| [04_error_handling.py](04_error_handling.py) | Comprehensive error handling patterns | ⭐⭐ Medium | Running SARK |

## Prerequisites

### 1. SARK Running

Ensure SARK is running and accessible:

```bash
# Start SARK with Docker Compose
docker compose --profile full up -d

# Verify SARK is running
curl http://localhost:8000/health
```

### 2. Python Dependencies

Install required Python packages:

```bash
# Create virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install requests
```

### 3. Environment Variables

Set up environment variables (optional - examples use defaults):

```bash
export SARK_URL="http://localhost:8000"
export SARK_USERNAME="admin"
export SARK_PASSWORD="password"

# For approval workflow example
export SARK_USER_USERNAME="analyst"
export SARK_USER_PASSWORD="password"
export SARK_ADMIN_USERNAME="admin"
export SARK_ADMIN_PASSWORD="password"
```

Or create a `.env` file:

```bash
SARK_URL=http://localhost:8000
SARK_USERNAME=admin
SARK_PASSWORD=password
```

### 4. MCP Servers (for examples 1-2)

Register at least one MCP server with tools. You can use the sample MCP server:

```bash
# Start a sample MCP server (if available)
python scripts/sample_mcp_server.py

# Or manually register a server
python scripts/register_sample_server.py
```

## Running the Examples

### Example 1: Basic Tool Invocation

The simplest example - authenticate and invoke a single tool:

```bash
python examples/01_basic_tool_invocation.py
```

**What it does:**
1. Authenticates with SARK using LDAP
2. Lists available MCP servers and tools
3. Selects a low-sensitivity tool
4. Invokes the tool through SARK
5. Displays the result

**Expected output:**
```
================================================================================
SARK MCP Example 1: Basic Tool Invocation
================================================================================

📡 Authenticating as admin...
✅ Authenticated successfully!
   User: admin@company.com
   Roles: admin, user

📋 Fetching available MCP servers...
✅ Found 3 MCP servers:
   - finance-mcp (active) - 5 tools
   - hr-mcp (active) - 3 tools
   - data-mcp (active) - 7 tools

🔧 Fetching available MCP tools...
✅ Found 15 tools:
   - query_database (medium)
   - send_email (low)
   ...

🚀 Invoking tool...
✅ Tool invocation successful!

✅ Example completed successfully!
```

### Example 2: Multi-Tool Workflow

Demonstrates chaining multiple tool invocations:

```bash
python examples/02_multi_tool_workflow.py
```

**What it does:**
1. Creates a workflow with 4 steps:
   - Query database for user data
   - Analyze data
   - Generate report
   - Send notification
2. Executes steps in order, respecting dependencies
3. Passes results from one step to the next

**Use case:** Data analysis pipeline that spans multiple MCP servers

### Example 3: Approval Workflow

Shows the break-glass approval mechanism for high-sensitivity tools:

```bash
# As a regular user - request approval
python examples/03_approval_workflow.py --role user

# As an admin - approve the request
python examples/03_approval_workflow.py --role admin

# User can now invoke the tool (within approval window)
```

**What it does:**
1. User attempts to access a CRITICAL sensitivity tool
2. Access denied (requires approval)
3. User requests approval with justification
4. Admin reviews and approves/denies
5. If approved, user can invoke tool within time window

**Use case:** Emergency database operations requiring admin approval

### Example 4: Error Handling

Demonstrates robust error handling patterns:

```bash
python examples/04_error_handling.py
```

**What it does:**
1. Demonstrates various error scenarios:
   - Tool not found
   - Invalid parameters
   - MCP server offline
   - Rate limiting
   - Authorization denied
   - Network errors
2. Shows proper error handling for each case
3. Implements retry logic with exponential backoff
4. Uses circuit breaker pattern

**Use case:** Production-ready client implementation

## Configuration Options

All examples support the following environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SARK_URL` | `http://localhost:8000` | SARK API base URL |
| `SARK_USERNAME` | `admin` | Username for authentication |
| `SARK_PASSWORD` | `password` | Password for authentication |
| `SARK_USER_USERNAME` | `analyst` | Regular user (for approval example) |
| `SARK_USER_PASSWORD` | `password` | Regular user password |
| `SARK_ADMIN_USERNAME` | `admin` | Admin user (for approval example) |
| `SARK_ADMIN_PASSWORD` | `password` | Admin password |

## Troubleshooting

### Connection Refused

```
❌ Connection error: Connection refused
```

**Solution:** Ensure SARK is running:
```bash
docker compose ps
curl http://localhost:8000/health
```

### Authentication Failed

```
❌ Authentication failed: 401
```

**Solution:** Check credentials:
```bash
# Test credentials
curl -X POST http://localhost:8000/api/v1/auth/login/ldap \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

### No MCP Servers Found

```
⚠️  No MCP servers registered
```

**Solution:** Register a sample MCP server:
```bash
# See scripts/register_sample_server.py
python scripts/register_sample_server.py
```

### Tool Not Found

```
❌ Tool not found
```

**Solution:** List available tools:
```bash
# Using curl
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/tools

# Or use the example
python examples/01_basic_tool_invocation.py
```

## Code Structure

Each example follows this pattern:

```python
#!/usr/bin/env python3
"""
Example X: [Title]

Description of what this example demonstrates.
"""

import requests

class SARKClient:
    """Client for interacting with SARK API."""
    # ... implementation ...

def main():
    """Main example logic."""
    # 1. Setup
    # 2. Authenticate
    # 3. Perform example actions
    # 4. Display results

if __name__ == "__main__":
    exit(main())
```

## Extending the Examples

### Add Custom Logic

Modify the examples to suit your needs:

```python
# Customize arguments
arguments = {
    "query": "SELECT * FROM custom_table",
    "limit": 1000
}

# Add custom error handling
try:
    result = client.invoke_tool(tool_id, arguments)
except Exception as e:
    logging.error(f"Custom error handler: {e}")
    # Your error handling logic
```

### Create Your Own Example

Use the examples as templates:

```python
#!/usr/bin/env python3
"""
Custom Example: Your Use Case

Description of your custom example.
"""

from examples.01_basic_tool_invocation import SARKClient

def main():
    client = SARKClient()
    client.login("username", "password")

    # Your custom logic here
    # ...

if __name__ == "__main__":
    main()
```

## Best Practices

### 1. Error Handling

Always handle errors gracefully:

```python
try:
    result = client.invoke_tool(tool_id, arguments)
except Exception as e:
    print(f"Error: {e}")
    # Fallback logic
```

### 2. Token Management

Store tokens securely:

```python
# Don't hardcode tokens
access_token = os.getenv("SARK_TOKEN")  # From environment

# Use token refresh
if response.status_code == 401:
    # Refresh token logic
```

### 3. Timeouts

Always set timeouts:

```python
response = requests.post(
    url,
    json=data,
    timeout=30  # 30 second timeout
)
```

### 4. Retries

Implement retry logic for transient errors:

```python
for attempt in range(3):
    try:
        response = client.invoke_tool(...)
        break
    except requests.exceptions.Timeout:
        if attempt < 2:
            time.sleep(2 ** attempt)  # Exponential backoff
```

## Related Documentation

- [API Reference](../docs/API_REFERENCE.md) - Complete API documentation
- [Authentication Guide](../docs/AUTHENTICATION.md) - Auth setup
- [MCP Introduction](../docs/MCP_INTRODUCTION.md) - MCP concepts
- [Tool Invocation Flow](../docs/diagrams/02_tool_invocation_flow.md) - Detailed flow diagram

## Support

If you encounter issues:

1. Check [Troubleshooting](#troubleshooting) above
2. Review [FAQ](../docs/FAQ.md)
3. Check SARK logs: `docker compose logs app`
4. File an issue on GitHub (if applicable)

## Contributing

Want to add more examples? See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## License

These examples are part of the SARK project. See [LICENSE](../LICENSE) for details.
