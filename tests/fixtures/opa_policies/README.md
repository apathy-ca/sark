# OPA Test Policies

This directory contains Open Policy Agent (OPA) policies used for integration testing.

## Contents

### Policy Files

1. **gateway_authorization.rego** - Gateway tool invocation authorization
   - Role-based access control
   - Parameter filtering for sensitive data
   - Context-based authorization (time, location, device trust)
   - Dangerous tool protection

2. **server_registration.rego** - MCP server registration policies
   - Sensitivity-level based access control
   - Team-based permissions
   - Production environment protection
   - Quota enforcement
   - Compliance requirements for PII handling

3. **tool_discovery.rego** - Tool visibility and discovery
   - Role-based tool filtering
   - Risk-level categorization
   - Server-based access control

4. **test_data.json** - Test data for policy evaluation
   - Allowlists (servers, tools)
   - Team definitions
   - User profiles
   - Sensitivity matrix

## Usage in Tests

### Loading Policies

```python
import pytest
import httpx

pytest_plugins = ["tests.fixtures.integration_docker"]

@pytest.fixture
async def load_policy(opa_client):
    """Helper to load policies into OPA."""
    async def _load(policy_name: str, policy_file: str):
        async with httpx.AsyncClient() as client:
            with open(f"tests/fixtures/opa_policies/{policy_file}", "r") as f:
                policy_content = f.read()

            response = await client.put(
                f"{opa_client.opa_url}/v1/policies/{policy_name}",
                data=policy_content,
                headers={"Content-Type": "text/plain"},
            )
            response.raise_for_status()

    return _load

@pytest.mark.integration
async def test_gateway_authorization(opa_client, load_policy):
    # Load policy
    await load_policy("gateway", "gateway_authorization.rego")

    # Test authorization
    decision = await opa_client.evaluate_policy({
        "action": "gateway:tool:invoke",
        "user": {"id": "user-001", "role": "developer"},
        "server": {"name": "test-server"},
        "tool": {"name": "query_database"},
    })

    assert decision.allow is True
```

### Loading Test Data

```python
import json

async def load_test_data(opa_client):
    """Load test data into OPA."""
    with open("tests/fixtures/opa_policies/test_data.json", "r") as f:
        data = json.load(f)

    async with httpx.AsyncClient() as client:
        await client.put(
            f"{opa_client.opa_url}/v1/data",
            json=data,
        )
```

## Policy Packages

| Package | Purpose | Rules |
|---------|---------|-------|
| `sark.gateway` | Gateway authorization | Tool invocation, parameter filtering |
| `sark.server` | Server registration | Sensitivity levels, team access |
| `sark.tools` | Tool discovery | Visibility filtering |

## Policy Evaluation Examples

### Gateway Tool Invocation

```rego
# Input
{
  "action": "gateway:tool:invoke",
  "user": {
    "id": "user-001",
    "role": "developer"
  },
  "server": {
    "name": "test-server"
  },
  "tool": {
    "name": "query_database",
    "dangerous": false
  }
}

# Result
{
  "allow": true,
  "reason": null
}
```

### Server Registration

```rego
# Input
{
  "action": "register",
  "user": {
    "id": "user-001",
    "role": "developer"
  },
  "resource": {
    "type": "server",
    "name": "new-server",
    "sensitivity": "high"
  }
}

# Result
{
  "allow": false,
  "reason": "No matching registration rule"
}
```

### Parameter Filtering

```rego
# Input
{
  "action": "gateway:tool:invoke",
  "tool": {
    "name": "query_database"
  },
  "parameters": {
    "query": "SELECT *",
    "password": "secret123",
    "limit": 10
  }
}

# Result
{
  "allow": true,
  "filtered_parameters": {
    "query": "SELECT *",
    "limit": 10
  }
}
```

## Testing Workflow

1. **Start OPA Docker container**
   ```bash
   ./scripts/run_integration_tests.sh start
   ```

2. **Run OPA integration tests**
   ```bash
   pytest tests/integration/test_opa_docker_integration.py -v
   ```

3. **View OPA policies**
   ```bash
   curl http://localhost:8181/v1/policies
   ```

4. **Test policy manually**
   ```bash
   curl -X POST http://localhost:8181/v1/data/sark/gateway \
     -H "Content-Type: application/json" \
     -d '{
       "input": {
         "action": "gateway:tool:invoke",
         "user": {"role": "admin"}
       }
     }'
   ```

## Policy Development

### Writing New Policies

1. Create `.rego` file in this directory
2. Use `package sark.<domain>` naming
3. Include `default allow = false` for security
4. Document rules with comments
5. Add corresponding tests

### Testing Policies Locally

```bash
# Install OPA CLI
brew install opa  # macOS
# or download from https://www.openpolicyagent.org/docs/latest/#running-opa

# Test policy
opa test tests/fixtures/opa_policies/*.rego

# Evaluate policy
opa eval -i input.json -d gateway_authorization.rego "data.sark.gateway.allow"
```

### Best Practices

1. **Fail Closed** - Always default to `allow = false`
2. **Explicit Rules** - Be specific about what is allowed
3. **Clear Reasons** - Provide helpful denial reasons
4. **Performance** - Keep policies efficient (avoid complex iterations)
5. **Testing** - Write comprehensive test cases
6. **Documentation** - Comment complex logic

## Integration with SARK

These policies are loaded into the OPA Docker container during integration tests and can be used to test the full authorization flow:

1. Gateway receives request
2. Extracts user context, action, resource info
3. Calls OPA with input data
4. OPA evaluates policies
5. Gateway enforces decision

## Debugging

### View Policy Compilation

```bash
curl http://localhost:8181/v1/policies/gateway
```

### Query Data

```bash
curl http://localhost:8181/v1/data/sark
```

### Enable Decision Logging

```bash
# Start OPA with decision logging
docker run -p 8181:8181 openpolicyagent/opa:latest \
  run --server --log-level=debug
```

## References

- [OPA Documentation](https://www.openpolicyagent.org/docs/latest/)
- [Rego Language Reference](https://www.openpolicyagent.org/docs/latest/policy-language/)
- [OPA REST API](https://www.openpolicyagent.org/docs/latest/rest-api/)
- [Testing Policies](https://www.openpolicyagent.org/docs/latest/policy-testing/)
