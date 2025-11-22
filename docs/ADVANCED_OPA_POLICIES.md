# Advanced OPA Policies

## Overview

This document describes the advanced OPA policies implemented for SARK, including time-based access controls, IP filtering, and MFA requirements.

## Policy Files

### 1. Time-Based Access Control (`time_based.rego`)

Enforces time-based restrictions on tool access based on business hours, weekdays, and role-based exemptions.

**Features:**
- Business hours enforcement (default: 9 AM - 5 PM, Monday-Friday)
- Configurable business hours per weekday
- Timezone support
- Role-based exemptions (admins bypass restrictions)
- Sensitivity-based time restrictions (critical tools only during business hours)
- Action-based restrictions (destructive actions during business hours only)
- Emergency override mechanism
- Maintenance window support

**Policy Decisions:**
```rego
# Critical tools require business hours
sensitivity_time_restrictions := {
    "critical": {
        "type": "business_hours_only",
        "reason": "Critical tools require business hours access",
        "exempt_roles": ["admin"],
    },
}

# Server deletion requires business hours
action_time_restrictions := {
    "server:delete": {
        "type": "business_hours_only",
        "reason": "Server deletion requires business hours",
        "exempt_roles": ["admin"],
    },
}
```

**Use Cases:**
- Restrict critical operations to business hours
- Prevent off-hours access for certain roles
- Emergency access during maintenance windows
- Compliance requirements (e.g., no changes during weekends)

**Example Input:**
```json
{
  "user": {"id": "dev1", "role": "developer"},
  "action": "tool:invoke",
  "tool": {"name": "critical_tool", "sensitivity_level": "critical"},
  "context": {
    "timestamp": "2024-01-01T20:00:00Z"
  }
}
```

**Example Output:**
```json
{
  "allow": false,
  "reason": "Time restrictions violated: Critical tools require business hours access",
  "violations": [
    {
      "type": "time_restriction",
      "restriction": {
        "type": "business_hours_only",
        "reason": "Critical tools require business hours access"
      },
      "current_time": {
        "timestamp": 1704132000000000000,
        "weekday": 0,
        "hour": 20,
        "is_business_hours": false,
        "is_weekend": false
      }
    }
  ]
}
```

### 2. IP Filtering (`ip_filtering.rego`)

Enforces IP-based access control using allowlists, blocklists, and geographic restrictions.

**Features:**
- Global IP allowlist (only these IPs allowed)
- Global IP blocklist (these IPs explicitly denied)
- CIDR range support (e.g., `10.0.0.0/8`)
- Wildcard matching (e.g., `192.168.*`)
- Private IP detection (RFC 1918)
- Role-specific IP restrictions
- VPN requirement for critical/high sensitivity tools
- Geographic restrictions (country-based)
- X-Forwarded-For header support

**Policy Decisions:**
```rego
# Critical tools require VPN
requires_vpn if {
    input.tool.sensitivity_level == "critical"
}

# Admin role requires corporate network
role_ip_requirements := {
    "admin": {
        "require_vpn": true,
        "allowed_ranges": ["10.0.0.0/8", "192.168.0.0/16"],
    },
}
```

**Use Cases:**
- Corporate network restrictions
- VPN-only access for critical tools
- Block known malicious IPs
- Geo-fencing for compliance
- Development vs production IP separation

**Example Input:**
```json
{
  "user": {"id": "dev1", "role": "developer"},
  "action": "tool:invoke",
  "tool": {"name": "critical_tool", "sensitivity_level": "critical"},
  "context": {
    "client_ip": "1.2.3.4"
  },
  "policy_config": {
    "ip_allowlist": ["10.0.0.0/8", "192.168.0.0/16"],
    "ip_blocklist": ["1.2.3.4"]
  }
}
```

**Example Output:**
```json
{
  "allow": false,
  "reason": "IP filtering violations: IP address 1.2.3.4 is on blocklist; VPN connection required for this operation",
  "violations": [
    {
      "type": "ip_blocked",
      "reason": "IP address 1.2.3.4 is on blocklist"
    },
    {
      "type": "vpn_required",
      "reason": "VPN connection required for this operation"
    }
  ],
  "client_ip": "1.2.3.4"
}
```

### 3. MFA Requirements (`mfa_required.rego`)

Enforces Multi-Factor Authentication requirements based on sensitivity, actions, and roles.

**Features:**
- Sensitivity-based MFA (critical/high tools require MFA)
- Action-based MFA (destructive actions require MFA)
- Role-based MFA (admins require MFA for certain operations)
- Time-based MFA session validation (default: 1 hour timeout)
- Step-up authentication (additional MFA for very sensitive operations)
- Service account exemption (API key-based auth)
- Tool-specific MFA requirements (configurable)
- Context-aware MFA (off-hours, non-corporate network)
- Emergency override mechanism

**Policy Decisions:**
```rego
# Critical tools require MFA
sensitivity_requires_mfa if {
    input.tool.sensitivity_level == "critical"
}

# Destructive actions require MFA
action_requires_mfa if {
    input.action in destructive_actions
}

destructive_actions := {
    "server:delete",
    "tool:delete",
    "user:delete",
    "secrets:delete",
}

# Step-up required for critical operations >5 minutes after MFA
step_up_required if {
    input.tool.sensitivity_level == "critical"
    input.action in ["tool:invoke", "server:delete"]
    mfa_age_seconds > 300  # 5 minutes
}
```

**Use Cases:**
- Protect critical infrastructure operations
- Compliance requirements (SOC2, ISO 27001)
- Prevent unauthorized access with compromised credentials
- Step-up auth for sensitive operations
- Time-based re-verification

**Example Input:**
```json
{
  "user": {
    "id": "dev1",
    "role": "developer",
    "mfa_verified": false
  },
  "action": "tool:invoke",
  "tool": {"name": "critical_tool", "sensitivity_level": "critical"},
  "context": {}
}
```

**Example Output:**
```json
{
  "allow": false,
  "reason": "MFA requirements not met: Multi-factor authentication required but not verified",
  "violations": [
    {
      "type": "mfa_not_verified",
      "reason": "Multi-factor authentication required but not verified",
      "required_factors": ["password", "mfa"]
    }
  ],
  "mfa_status": {
    "required": true,
    "verified": false,
    "session_valid": false
  },
  "required_factors": ["password", "mfa"]
}
```

## Policy Integration

The advanced policies are integrated into the main policy bundle (`main.rego`) and evaluated alongside RBAC, team access, and sensitivity policies.

**Evaluation Order:**
1. **RBAC** - Role-based access control
2. **Team Access** - Team ownership and permissions
3. **Sensitivity** - Sensitivity level enforcement
4. **Time-based** - Business hours and time restrictions
5. **IP Filtering** - IP allowlist/blocklist and geo-restrictions
6. **MFA Required** - Multi-factor authentication requirements

**All policies must pass for access to be granted.**

## Testing

### OPA Native Tests

Each policy includes comprehensive OPA native tests (`.rego` files with `_test` suffix):

```bash
# Run OPA tests
opa test opa/policies/defaults/time_based_test.rego
opa test opa/policies/defaults/ip_filtering_test.rego
opa test opa/policies/defaults/mfa_required_test.rego

# Run all tests
opa test opa/policies/defaults/
```

### Python Integration Tests

Integration tests validate the policies through the Python OPA client:

```bash
# Run integration tests
pytest tests/test_integration/test_advanced_opa_policies.py -v

# Run specific test
pytest tests/test_integration/test_advanced_opa_policies.py::test_critical_tool_requires_mfa -v
```

### Test Coverage

**Time-based Policy:**
- ✅ Business hours enforcement
- ✅ Weekend blocking
- ✅ Admin exemption
- ✅ Emergency override
- ✅ Custom business hours
- ✅ Maintenance windows

**IP Filtering Policy:**
- ✅ Allowlist enforcement
- ✅ Blocklist enforcement
- ✅ CIDR range matching
- ✅ Wildcard matching
- ✅ Private IP detection
- ✅ VPN requirements
- ✅ Geographic restrictions
- ✅ Role-specific IP restrictions

**MFA Policy:**
- ✅ Critical tool MFA requirement
- ✅ MFA session validation
- ✅ MFA session expiration
- ✅ Step-up authentication
- ✅ Service account exemption
- ✅ Destructive action MFA
- ✅ Off-hours MFA requirement
- ✅ Non-corporate network MFA

## Configuration

### Time-based Configuration

```json
{
  "policy_config": {
    "business_hours": {
      "monday": {"start": 9, "end": 17},
      "tuesday": {"start": 9, "end": 17},
      "wednesday": {"start": 9, "end": 17},
      "thursday": {"start": 9, "end": 17},
      "friday": {"start": 9, "end": 17},
      "saturday": null,
      "sunday": null
    },
    "maintenance_windows": [
      {
        "start": 1699477200000000000,
        "end": 1699484400000000000,
        "allowed_actions": ["tool:deploy", "server:update"]
      }
    ]
  }
}
```

### IP Filtering Configuration

```json
{
  "policy_config": {
    "ip_filtering_enabled": true,
    "ip_allowlist": [
      "10.0.0.0/8",
      "192.168.0.0/16",
      "203.0.113.0/24"
    ],
    "ip_blocklist": [
      "1.2.3.4",
      "5.6.7.0/24"
    ],
    "allow_private_ips": true,
    "vpn_ip_ranges": [
      "10.100.0.0/16"
    ],
    "geo_restrictions_enabled": true,
    "allowed_countries": ["US", "CA", "GB", "DE"]
  }
}
```

### MFA Configuration

```json
{
  "policy_config": {
    "mfa_timeout_seconds": 3600,
    "mfa_methods": ["totp", "webauthn", "push"],
    "mfa_required_tools": [
      "payment_processor",
      "user_admin",
      "secrets_manager"
    ],
    "corporate_ip_ranges": [
      "10.0.0.0/8",
      "192.168.0.0/16"
    ]
  }
}
```

## Emergency Override

All advanced policies support emergency override for critical situations:

```json
{
  "context": {
    "emergency_override": true,
    "emergency_reason": "Production outage requiring immediate action",
    "emergency_approver": "cto@company.com"
  }
}
```

**Requirements:**
- Must provide detailed reason
- Must specify approver
- Admin role required (for MFA override)
- All overrides are logged for audit

## Performance Considerations

### Caching

Policy decisions involving advanced policies should consider:

- **Time-based**: Not cacheable (depends on current time)
- **IP filtering**: Cacheable per IP address (short TTL recommended)
- **MFA**: Cacheable with MFA session TTL (default 1 hour)

### Cache TTL Recommendations

| Sensitivity | Time-based | IP Filtering | MFA |
|-------------|-----------|--------------|-----|
| **Low**     | N/A       | 300s         | 3600s |
| **Medium**  | N/A       | 180s         | 1800s |
| **High**    | N/A       | 60s          | 600s |
| **Critical**| N/A       | 30s          | 300s |

## Compliance and Audit

All policy violations are logged with detailed context:

```json
{
  "audit_log": {
    "policy": "time_based",
    "user_id": "dev1",
    "action": "tool:invoke",
    "tool_name": "critical_tool",
    "violations": [
      {
        "type": "time_restriction",
        "reason": "Critical tools require business hours access",
        "current_time": {
          "timestamp": 1704132000000000000,
          "hour": 20,
          "is_business_hours": false
        }
      }
    ],
    "timestamp": 1704132000000000000
  }
}
```

## Best Practices

1. **Time-based Access:**
   - Use custom business hours for different timezones
   - Always provide emergency override for critical incidents
   - Document maintenance windows in advance
   - Exempt admins but log all override usage

2. **IP Filtering:**
   - Start with allowlist approach for critical systems
   - Regularly review and update blocklist
   - Use CIDR ranges instead of individual IPs
   - Enable geographic restrictions for compliance
   - Test VPN connectivity before enforcement

3. **MFA Requirements:**
   - Enforce MFA for all critical and high sensitivity operations
   - Use step-up authentication for destructive actions
   - Set appropriate session timeouts (1 hour default)
   - Provide clear error messages for MFA failures
   - Support multiple MFA methods for redundancy

4. **Testing:**
   - Test all policies in development environment first
   - Use OPA native tests for policy logic validation
   - Use integration tests for end-to-end validation
   - Monitor policy performance in production
   - Set up alerts for policy violations

## Troubleshooting

### Common Issues

**Time-based Policy:**
- **Issue**: Legitimate access denied during business hours
- **Solution**: Check timezone configuration and current time calculation

**IP Filtering:**
- **Issue**: VPN users blocked unexpectedly
- **Solution**: Verify VPN IP ranges are in allowlist and `allow_private_ips` is enabled

**MFA Policy:**
- **Issue**: MFA session expired too quickly
- **Solution**: Adjust `mfa_timeout_seconds` in policy configuration

### Debug Mode

Enable debug logging in OPA to troubleshoot policy decisions:

```bash
opa run --server --log-level debug opa/policies/defaults/
```

## References

- [OPA Policy Language](https://www.openpolicyagent.org/docs/latest/policy-language/)
- [SARK Default Policies](../opa/policies/defaults/README.md)
- [Policy Caching Documentation](POLICY_CACHING.md)
- [Tool Sensitivity Classification](TOOL_SENSITIVITY_CLASSIFICATION.md)
