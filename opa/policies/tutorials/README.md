# Tutorial Policy Examples

This directory contains OPA policy examples used in SARK tutorials. These policies demonstrate common access control patterns and work with the sample LDAP users in `ldap/bootstrap/`.

---

## Quick Start

These policies are automatically loaded when you start SARK with any profile:

```bash
# Start SARK with minimal profile
docker compose --profile minimal up -d

# Policies are loaded from opa/policies/ directory
# Tutorial examples are in opa/policies/tutorials/
```

---

## Policy Examples Overview

| Example | Pattern | Tutorial | Sample User |
|---------|---------|----------|-------------|
| 1 | Role-Based Access Control (RBAC) | Tutorial 1 | john.doe, jane.smith |
| 2 | Team-Based Access Control | Tutorial 3 | alice.engineer |
| 3 | Time-Based Access Control | Tutorial 3 | All users |
| 4 | Parameter Filtering | Tutorial 3 | carol.analyst |
| 5 | MFA Requirement | Tutorial 3 | bob.security |
| 6 | IP-Based Access Control | Tutorial 3 | All users |
| 7 | Approval Workflow | Tutorial 3 | jane.smith |
| 8 | SQL Query Validation | Tutorial 1 | alice.engineer |
| 9 | Rate Limiting | Tutorial 3 | All users |
| 10 | Environment-Based Access | Tutorial 3 | All users |

---

## Example 1: Role-Based Access Control (RBAC)

**Use Case:** Control tool access based on user roles

**Policy:**
```rego
# Developers can invoke low and medium sensitivity tools
allow_developer_basic if {
    input.user.role == "developer"
    input.action == "tool:invoke"
    input.tool.sensitivity_level in ["low", "medium"]
}

# Team leads can also invoke high sensitivity tools
allow_team_lead if {
    "team_lead" in input.user.roles
    input.action == "tool:invoke"
    input.tool.sensitivity_level in ["low", "medium", "high"]
}
```

**Test with SARK:**
```bash
# john.doe (team_lead) can access high-sensitivity tool
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "user": {
      "id": "john.doe",
      "role": "developer",
      "roles": ["developer", "team_lead"]
    },
    "action": "tool:invoke",
    "tool": {
      "name": "execute_query",
      "sensitivity_level": "high"
    }
  }' | jq

# Expected: "decision": "allow"

# jane.smith (developer) CANNOT access high-sensitivity tool
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "user": {
      "id": "jane.smith",
      "role": "developer",
      "roles": ["developer"]
    },
    "action": "tool:invoke",
    "tool": {
      "name": "execute_query",
      "sensitivity_level": "high"
    }
  }' | jq

# Expected: "decision": "deny"
```

---

## Example 2: Team-Based Access Control

**Use Case:** Users can access tools owned by their team

**Policy:**
```rego
# Users can access tools owned by their team
allow_team_ownership if {
    input.action == "tool:invoke"
    some team in input.user.teams
    team == input.tool.team
}

# Data engineering team has special database access
allow_data_engineering_db if {
    "data-engineering" in input.user.teams
    input.action == "tool:invoke"
    input.tool.name == "execute_query"
    input.arguments.database in ["analytics", "reporting"]
}
```

**Test with SARK:**
```bash
# alice.engineer (data-engineering team) can access analytics database
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "user": {
      "id": "alice.engineer",
      "teams": ["data-engineering", "analytics"]
    },
    "action": "tool:invoke",
    "tool": {
      "name": "execute_query"
    },
    "arguments": {
      "database": "analytics"
    }
  }' | jq

# Expected: "decision": "allow"
```

---

## Example 3: Time-Based Access Control

**Use Case:** Restrict high-sensitivity operations to business hours

**Policy:**
```rego
# Check if timestamp is during business hours (9 AM - 6 PM)
is_business_hours(timestamp) if {
    hour := time.clock([timestamp])[0]
    hour >= 9
    hour < 18
}

# High sensitivity tools require business hours
require_business_hours if {
    input.tool.sensitivity_level == "high"
    not is_business_hours(input.context.timestamp)
}
```

**Test with SARK:**
```bash
# During business hours (2 PM = 14:00)
NOW=$(date -u -d "today 14:00" +%s)
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d "{
    \"user\": {\"role\": \"developer\", \"roles\": [\"developer\", \"team_lead\"]},
    \"action\": \"tool:invoke\",
    \"tool\": {\"sensitivity_level\": \"high\"},
    \"context\": {\"timestamp\": $NOW}
  }" | jq

# Expected: "decision": "allow"

# Outside business hours (11 PM = 23:00)
NOW=$(date -u -d "today 23:00" +%s)
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d "{
    \"user\": {\"role\": \"developer\", \"roles\": [\"developer\", \"team_lead\"]},
    \"action\": \"tool:invoke\",
    \"tool\": {\"sensitivity_level\": \"high\"},
    \"context\": {\"timestamp\": $NOW}
  }" | jq

# Expected: "decision": "deny", "reason": "Requires business hours"
```

---

## Example 4: Parameter Filtering and Data Masking

**Use Case:** Analysts get read-only access with automatic query filtering

**Policy:**
```rego
# Analyst gets limited database access with filtering
filtered_parameters_analyst contains param if {
    input.user.role == "analyst"
    input.tool.name == "execute_query"

    # Filter out DELETE, UPDATE, INSERT keywords
    query := input.arguments.query
    not contains(upper(query), "DELETE")
    not contains(upper(query), "UPDATE")

    # Return allowed parameters
    param := {
        "query": query,
        "database": "analytics",  # Force analytics DB only
        "limit": min([input.arguments.limit, 1000])  # Cap at 1000 rows
    }
}
```

**Test with SARK:**
```bash
# carol.analyst tries to SELECT - allowed with filtering
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "user": {"role": "analyst"},
    "tool": {"name": "execute_query"},
    "arguments": {
      "query": "SELECT * FROM users",
      "database": "production",
      "limit": 10000
    }
  }' | jq

# Expected:
# "decision": "allow"
# "filtered_parameters": {
#   "query": "SELECT * FROM users",
#   "database": "analytics",  # Changed from production
#   "limit": 1000  # Capped from 10000
# }

# carol.analyst tries to DELETE - denied
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "user": {"role": "analyst"},
    "tool": {"name": "execute_query"},
    "arguments": {
      "query": "DELETE FROM users"
    }
  }' | jq

# Expected: "decision": "deny", "reason": "Dangerous SQL query detected"
```

---

## Example 5: MFA Requirement

**Use Case:** Critical operations require multi-factor authentication

**Policy:**
```rego
# Critical tools require MFA verification
require_mfa if {
    input.tool.sensitivity_level == "critical"
    not input.context.mfa_verified
}

# MFA must be recent (within last 5 minutes)
mfa_expired if {
    input.tool.sensitivity_level == "critical"
    input.context.mfa_verified
    (now - mfa_time) > 300000000000  # 5 minutes in nanoseconds
}
```

**Test with SARK:**
```bash
# Critical tool without MFA - denied
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "user": {"role": "security_engineer"},
    "tool": {"sensitivity_level": "critical"},
    "context": {"mfa_verified": false}
  }' | jq

# Expected: "decision": "deny", "reason": "Requires MFA verification"

# Critical tool with valid MFA - allowed
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d "{
    \"user\": {\"role\": \"security_engineer\"},
    \"tool\": {\"sensitivity_level\": \"critical\"},
    \"context\": {
      \"mfa_verified\": true,
      \"mfa_timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
    }
  }" | jq

# Expected: "decision": "allow"
```

---

## Example 8: SQL Query Validation

**Use Case:** Prevent SQL injection and dangerous operations

**Policy:**
```rego
# Detect dangerous SQL keywords
dangerous_keywords := [
    "DELETE", "UPDATE", "INSERT", "DROP", "ALTER",
    "TRUNCATE", "GRANT", "REVOKE", "EXEC"
]

# Check if query contains dangerous keywords
query_is_dangerous if {
    input.tool.name == "execute_query"
    query := upper(input.arguments.query)
    some keyword in dangerous_keywords
    contains(query, keyword)
}
```

**Test with SARK:**
```bash
# Safe SELECT query - allowed
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "user": {"role": "data_engineer"},
    "tool": {"name": "execute_query"},
    "arguments": {"query": "SELECT * FROM users WHERE id = 1"}
  }' | jq

# Expected: "decision": "allow"

# Dangerous DELETE query - denied
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "user": {"role": "data_engineer"},
    "tool": {"name": "execute_query"},
    "arguments": {"query": "DELETE FROM users WHERE id = 1"}
  }' | jq

# Expected: "decision": "deny", "reason": "Dangerous SQL query detected"
```

---

## Testing Policies Locally

### 1. Test with OPA CLI

```bash
# Install OPA
brew install opa  # macOS
# or download from https://www.openpolicyagent.org/docs/latest/#running-opa

# Test a policy
opa eval -i input.json -d tutorial_examples.rego "data.mcp.tutorials.result"
```

Example `input.json`:
```json
{
  "user": {
    "id": "john.doe",
    "role": "developer",
    "roles": ["developer", "team_lead"],
    "teams": ["engineering"]
  },
  "action": "tool:invoke",
  "tool": {
    "name": "execute_query",
    "sensitivity_level": "high",
    "team": "engineering"
  },
  "arguments": {
    "query": "SELECT * FROM users",
    "database": "analytics"
  },
  "context": {
    "timestamp": 1732708800,
    "mfa_verified": false,
    "ip_address": "10.0.1.50"
  }
}
```

### 2. Test with OPA Playground

1. Go to https://play.openpolicyagent.org/
2. Paste policy from `tutorial_examples.rego`
3. Paste input JSON
4. Click "Evaluate"

### 3. Test with SARK API

```bash
# Start SARK
docker compose --profile minimal up -d

# Authenticate
export ACCESS_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ldap \
  -H "Content-Type: application/json" \
  -d '{"username": "john.doe", "password": "password"}' | jq -r '.access_token')

# Evaluate policy
curl -X POST http://localhost:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d @input.json | jq
```

---

## Policy Development Workflow

1. **Write Policy:** Create `.rego` file in `opa/policies/tutorials/`
2. **Write Tests:** Create `_test.rego` file with test cases
3. **Test Locally:** Run `opa test opa/policies/ -v`
4. **Deploy:** Restart OPA service to reload policies
5. **Validate:** Test with SARK API

Example test file (`tutorial_examples_test.rego`):

```rego
package mcp.tutorials

test_developer_can_access_low_sensitivity if {
    result.allow with input as {
        "user": {"role": "developer"},
        "action": "tool:invoke",
        "tool": {"sensitivity_level": "low"}
    }
}

test_developer_cannot_access_critical if {
    not result.allow with input as {
        "user": {"role": "developer"},
        "action": "tool:invoke",
        "tool": {"sensitivity_level": "critical"}
    }
}
```

Run tests:
```bash
docker compose exec opa opa test /policies -v
```

---

## Integrating with Tutorials

### Tutorial 1: Basic Setup
- Uses Example 1 (RBAC) and Example 8 (SQL Validation)
- Sample user: john.doe
- Demonstrates basic allow/deny decisions

### Tutorial 3: Policy Development
- Uses all 10 examples
- Sample users: All users from ldap/bootstrap/
- Teaches policy authoring, testing, deployment

---

## Related Documentation

- **[LDAP Sample Users](../../../ldap/README.md)** - User accounts and permissions
- **[Tutorial 1: Basic Setup](../../../tutorials/01-basic-setup/README.md)** - Hands-on tutorial
- **[Tutorial 3: Policies](../../../tutorials/03-policies/README.md)** - Policy development
- **[OPA Documentation](https://www.openpolicyagent.org/docs/)** - Official OPA docs

---

**Ready to write policies?** Start with [Tutorial 3: Policy Development](../../../tutorials/03-policies/README.md)
