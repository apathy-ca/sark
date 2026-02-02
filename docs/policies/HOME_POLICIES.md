# SARK Home Policies

This document describes the home-specific LLM governance policies for YORI (Your Own Router Intelligence). These policies help families manage AI assistant usage at the network level.

## Overview

SARK home policies differ from enterprise policies:
- **Simpler rules** designed for home users
- **Family-focused governance** (bedtime, parental controls)
- **Cost awareness** (API usage limits)
- **Privacy protection** (prevent accidental PII sharing)
- **Three operating modes** for gradual adoption

## Operating Modes

All home policies support three operating modes:

| Mode | Behavior | Use Case |
|------|----------|----------|
| `observe` | Log all requests, never block | New installations, understanding usage patterns |
| `advisory` | Log and alert on violations, but allow | Testing policies before enforcement |
| `enforce` | Block requests that violate policies | Production policy enforcement |

## Available Policies

### 1. Default Policy (`default.rego`)

The default policy for new YORI installations. It allows all requests while logging usage patterns and suggesting which policies might benefit your household.

**Package:** `sark.home.default`

**Features:**
- Always allows requests (observation mode)
- Tracks usage patterns
- Suggests appropriate policies based on usage
- Generates soft-limit warnings

**Configuration:** None required - works out of the box.

---

### 2. Bedtime Policy (`bedtime.rego`)

Restricts LLM access during configured bedtime hours for children's devices.

**Package:** `sark.home.bedtime`

**Features:**
- Configurable bedtime window (supports overnight spans like 9pm-7am)
- Day-of-week restrictions
- Device and user group exemptions
- Parent/admin bypass

**Configuration:**

```json
{
  "rules": {
    "bedtime_start_hour": 21,
    "bedtime_end_hour": 7,
    "bedtime_days": ["sunday", "monday", "tuesday", "wednesday", "thursday"]
  }
}
```

**Data (Optional):**

```json
{
  "home": {
    "bedtime_exempt_devices": ["parents-phone", "192.168.1.50"]
  }
}
```

**Exempt User Groups:** `admin`, `parent`, `adult`

---

### 3. Parental Controls Policy (`parental.rego`)

Content filtering for minor users, blocking inappropriate keywords and categories.

**Package:** `sark.home.parental`

**Features:**
- Keyword-based content filtering
- Category restrictions
- Age-restricted endpoint blocking
- Safe mode enforcement
- Case-insensitive matching

**Configuration:**

```json
{
  "rules": {
    "enforce_safe_mode": true
  }
}
```

**Data (Optional):**

```json
{
  "home": {
    "minor_devices": ["kids-tablet", "childrens-laptop"],
    "minor_device_ips": ["192.168.1.100", "192.168.1.101"],
    "parental_blocked_keywords": ["custom", "blocked", "words"],
    "parental_blocked_categories": ["adult", "violence"],
    "age_restricted_endpoints": ["api.unrestricted-llm.com"]
  }
}
```

**Minor User Groups:** `child`, `children`, `minor`, `teen`, `teenager`, `kid`

---

### 4. Cost Limit Policy (`cost_limit.rego`)

Controls LLM API usage based on daily/monthly cost and token limits.

**Package:** `sark.home.cost_limit`

**Features:**
- Daily and monthly cost limits
- Daily and monthly token limits
- Per-request budget checking
- Per-user/device limits
- Warning thresholds (50%, 75%, 90%)

**Configuration:**

```json
{
  "rules": {
    "daily_cost_limit_usd": 5.00,
    "monthly_cost_limit_usd": 100.00,
    "daily_token_limit": 50000,
    "monthly_token_limit": 1000000
  }
}
```

**Data (Optional):**

```json
{
  "home": {
    "user_daily_limits": {
      "kids-tablet": 1.00,
      "work-laptop": 10.00
    }
  }
}
```

**Required Context:**

```json
{
  "context": {
    "cost_today_usd": 2.50,
    "cost_month_usd": 45.00,
    "tokens_today": 15000,
    "tokens_month": 450000
  }
}
```

---

### 5. Privacy Policy (`privacy.rego`)

Detects and blocks personally identifiable information (PII) in prompts.

**Package:** `sark.home.privacy`

**Features:**
- Email address detection
- Phone number detection (various formats)
- Social Security Number detection (always blocked)
- Credit card number detection (always blocked)
- Address detection
- Date of birth detection
- Full name detection (strict mode)
- Privacy levels: strict, moderate, permissive

**Configuration:**

```json
{
  "rules": {
    "privacy_level": "moderate"
  }
}
```

| Privacy Level | Behavior |
|--------------|----------|
| `strict` | Block all PII including names |
| `moderate` | Block common PII (default) |
| `permissive` | Only block sensitive PII (SSN, credit cards) |

**Data (Optional):**

```json
{
  "home": {
    "pii_exempt_devices": ["parents-phone", "work-laptop"]
  }
}
```

**Note:** SSN and credit card numbers are ALWAYS blocked, even for exempt users/devices.

---

### 6. Allowlist Policy (`allowlist.rego`)

Controls access based on device and user allowlists or blocklists.

**Package:** `sark.home.allowlist`

**Features:**
- Device IP allowlist/blocklist
- Device name allowlist/blocklist
- User group allowlist/blocklist
- MAC address allowlist/blocklist
- CIDR range matching
- Endpoint allowlist
- Admin override

**Configuration:**

```json
{
  "rules": {
    "list_mode": "allowlist",
    "device_allowlist": ["192.168.1.100", "192.168.1.101"],
    "device_name_allowlist": ["family-pc", "kids-tablet"],
    "user_group_allowlist": ["family", "trusted"],
    "allowed_cidrs": ["192.168.1.0/24"],
    "allowed_endpoints": ["api.openai.com", "api.anthropic.com"]
  }
}
```

**List Modes:**
- `allowlist` (default): Only allow explicitly listed devices
- `blocklist`: Allow all except blocked devices

**Admin groups always bypass allowlist/blocklist restrictions.**

---

## Input Schema

All home policies expect input in this structure:

```json
{
  "input": {
    "user": {
      "device_ip": "192.168.1.100",
      "device_name": "kids-laptop",
      "user_group": "child",
      "mac_address": "AA:BB:CC:DD:EE:FF",
      "is_admin": false
    },
    "request": {
      "endpoint": "api.openai.com",
      "method": "POST",
      "path": "/v1/chat/completions",
      "prompt_preview": "Help me with homework...",
      "tokens_estimated": 500,
      "estimated_cost_usd": 0.02,
      "model": "gpt-4",
      "category": "education",
      "safe_mode": true
    },
    "context": {
      "timestamp": "2024-01-15T22:30:00Z",
      "hour": 22,
      "day_of_week": "monday",
      "tokens_today": 1500,
      "tokens_month": 45000,
      "cost_today_usd": 0.45,
      "cost_month_usd": 12.50,
      "device_requests_today": 25,
      "first_request": false
    },
    "rules": {
      "mode": "enforce",
      "bedtime_start_hour": 21,
      "bedtime_end_hour": 7,
      "daily_cost_limit_usd": 5.00,
      "privacy_level": "moderate"
    }
  }
}
```

## Decision Output

All policies return a standard decision structure:

```json
{
  "allow": true,
  "reason": "Allowed: request passed all policy checks",
  "policy": "bedtime",
  "severity": "info",
  "metadata": {
    "current_hour": 14,
    "is_bedtime": false
  }
}
```

**Severity Levels:**
- `info`: Informational, request allowed
- `warning`: Request allowed but noteworthy
- `high`: Request denied, policy violation
- `critical`: Request denied, serious violation (e.g., SSN detected)

## Testing Policies

Run policy tests with OPA:

```bash
# Test all home policies
opa test opa/policies/home/ tests/opa/home/ -v

# Test specific policy
opa test opa/policies/home/bedtime.rego tests/opa/home/bedtime_test.rego -v

# Check test coverage
opa test opa/policies/home/ tests/opa/home/ --coverage
```

## Shared Library

Common functions are available in `opa/policies/home/helpers/common.rego`:

```rego
import data.sark.home.helpers.common

# Time utilities
common.is_time_in_range(hour, start, end)
common.is_weekday(day)
common.is_weekend(day)

# User utilities
common.is_admin_user(user_group)
common.is_minor_user(user_group)
common.is_adult_user(user_group)

# Cost utilities
common.estimate_cost_usd(input_tokens, output_tokens)
common.remaining_daily_budget(spent, limit)
common.usage_percentage(current, limit)

# PII detection
common.contains_any_pii(text)
common.contains_sensitive_pii(text)

# Network utilities
common.is_private_ip(ip)

# Mode utilities
common.effective_mode(requested_mode)
common.mode_description(mode)
```

## OPNsense Integration

These policies are designed to be selectable from the OPNsense UI dropdown. Each policy file corresponds to a UI option that home users can enable with a single click.

Recommended default setup for families:
1. Start with `default` policy (observe mode)
2. After 1 week, review logs and enable suggested policies
3. Test with `advisory` mode
4. Enable `enforce` mode when confident

## Related Documentation

- [Policy Cookbook](POLICY_COOKBOOK.md) - Example configurations for common scenarios
- [YORI Project Plan](../v2.0/YORI_PROJECT_PLAN.md) - Overall project context
