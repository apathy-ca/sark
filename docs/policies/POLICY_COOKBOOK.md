# SARK Home Policy Cookbook

Practical examples and configurations for common home LLM governance scenarios.

## Quick Start Recipes

### Recipe 1: Family-Friendly Setup

A balanced configuration for a household with children.

**Policies to enable:** `bedtime`, `parental`, `cost_limit`, `privacy`

**Configuration:**

```json
{
  "rules": {
    "mode": "enforce",
    "bedtime_start_hour": 21,
    "bedtime_end_hour": 7,
    "bedtime_days": ["sunday", "monday", "tuesday", "wednesday", "thursday"],
    "daily_cost_limit_usd": 5.00,
    "privacy_level": "moderate"
  }
}
```

**Data:**

```json
{
  "home": {
    "bedtime_exempt_devices": ["parents-phone", "master-bedroom-pc"],
    "minor_devices": ["kids-tablet", "homework-laptop"]
  }
}
```

---

### Recipe 2: Work From Home Setup

Separate limits for work and personal devices.

**Policies to enable:** `cost_limit`, `allowlist`

**Configuration:**

```json
{
  "rules": {
    "mode": "enforce",
    "list_mode": "allowlist",
    "daily_cost_limit_usd": 25.00,
    "monthly_cost_limit_usd": 500.00
  }
}
```

**Data:**

```json
{
  "home": {
    "device_allowlist": ["192.168.1.50", "192.168.1.51"],
    "device_name_allowlist": ["work-laptop", "home-office-pc"],
    "user_daily_limits": {
      "work-laptop": 20.00,
      "personal-phone": 2.00,
      "kids-tablet": 1.00
    }
  }
}
```

---

### Recipe 3: Privacy-First Home

Maximum privacy protection for all family members.

**Policies to enable:** `privacy`, `parental`

**Configuration:**

```json
{
  "rules": {
    "mode": "enforce",
    "privacy_level": "strict"
  }
}
```

This configuration will:
- Block any detected email addresses
- Block phone numbers
- Block physical addresses
- Block full names (in strict mode)
- Always block SSN and credit card numbers

---

### Recipe 4: Budget-Conscious Family

Strict cost controls with warning alerts.

**Policies to enable:** `cost_limit`

**Configuration:**

```json
{
  "rules": {
    "mode": "enforce",
    "daily_cost_limit_usd": 2.00,
    "monthly_cost_limit_usd": 30.00,
    "daily_token_limit": 20000
  }
}
```

**Monitoring:** The `cost_limit` policy provides warning levels:
- **50%**: `medium` - Monitor usage
- **75%**: `high` - Approaching limit
- **90%**: `critical` - Near limit

---

### Recipe 5: Observation Mode (New Users)

Start with full visibility before enforcing rules.

**Policies to enable:** `default`

**Configuration:**

```json
{
  "rules": {
    "mode": "observe"
  }
}
```

After 1-2 weeks, check:
1. `suggested_policies` in decision metadata
2. `soft_limit_warnings` for usage patterns
3. `usage_analytics` for peak hours

---

## Scenario-Based Examples

### Scenario: School Night Bedtime

**Problem:** Kids using AI for homework should be cut off at bedtime on school nights, but weekends are more relaxed.

**Solution:**

```json
{
  "rules": {
    "mode": "enforce",
    "bedtime_start_hour": 21,
    "bedtime_end_hour": 7,
    "bedtime_days": ["sunday", "monday", "tuesday", "wednesday", "thursday"]
  }
}
```

Friday and Saturday nights are unrestricted.

---

### Scenario: Teen vs. Young Child

**Problem:** Teenager needs less filtering than younger siblings.

**Solution:** Use user groups:

```json
{
  "home": {
    "minor_devices": ["elementary-tablet"],
    "minor_device_ips": ["192.168.1.100"]
  }
}
```

Assign younger children to devices in the `minor_devices` list. Teen devices not in the list will bypass parental content filters.

**Alternative:** Use different user groups:
- Assign young children to `child` group
- Assign teenagers to `teen` group (still filtered but less restrictively)
- Assign adults to `adult` group (no filtering)

---

### Scenario: Guest WiFi

**Problem:** Guest devices shouldn't access LLM services.

**Solution:** Use CIDR blocklist:

```json
{
  "rules": {
    "list_mode": "blocklist"
  }
}
```

```json
{
  "home": {
    "blocked_cidrs": ["192.168.2.0/24"]
  }
}
```

Assuming guest network is on `192.168.2.x` subnet.

---

### Scenario: Specific LLM Providers Only

**Problem:** Only allow OpenAI and Anthropic APIs.

**Solution:** Use endpoint allowlist:

```json
{
  "home": {
    "allowed_endpoints": [
      "api.openai.com",
      "api.anthropic.com"
    ]
  }
}
```

---

### Scenario: Prevent Kids Sharing School Info

**Problem:** Children might share their school name, teacher name, or home address with AI.

**Solution:** Enable strict privacy:

```json
{
  "rules": {
    "privacy_level": "strict"
  }
}
```

This will catch:
- Full addresses
- Phone numbers
- Phrases like "my name is..."

---

### Scenario: Per-Device Budget Allocation

**Problem:** Different family members have different LLM budgets.

**Solution:** Configure per-user limits:

```json
{
  "home": {
    "user_daily_limits": {
      "dad-laptop": 10.00,
      "mom-phone": 10.00,
      "teen-computer": 2.00,
      "kids-tablet": 0.50
    }
  }
}
```

---

## Combining Policies

### Safe Family Setup

Combine multiple policies for comprehensive protection:

1. **bedtime.rego**: Enforce 9pm-7am for children
2. **parental.rego**: Filter inappropriate content
3. **cost_limit.rego**: $5/day family limit
4. **privacy.rego**: Block PII sharing
5. **allowlist.rego**: Only family devices

### Performance-Focused Setup

Minimal policies for low overhead:

1. **allowlist.rego**: Only allow known devices
2. **cost_limit.rego**: Set budget limits

### Monitoring-First Setup

Understand usage before restricting:

1. **default.rego**: Observe mode for 2 weeks
2. Review `suggested_policies` in logs
3. Gradually enable recommended policies

---

## Testing Your Configuration

### Test with OPA CLI

```bash
# Test a single request
echo '{
  "input": {
    "user": {"device_ip": "192.168.1.100", "device_name": "kids-laptop", "user_group": "child"},
    "request": {"prompt_preview": "help with homework", "endpoint": "api.openai.com"},
    "context": {"hour": 22},
    "rules": {"bedtime_start_hour": 21, "bedtime_end_hour": 7}
  }
}' | opa eval -d opa/policies/home/bedtime.rego -i - "data.sark.home.bedtime.decision"
```

### Test All Policies

```bash
# Run policy test suite
opa test opa/policies/home/ tests/opa/home/ -v

# Check coverage
opa test opa/policies/home/ tests/opa/home/ --coverage --format=json
```

---

## Common Mistakes

### Mistake 1: Overnight Bedtime Window

**Wrong:**
```json
{
  "bedtime_start_hour": 7,
  "bedtime_end_hour": 21
}
```
This blocks 7am-9pm (daytime) instead of 9pm-7am (nighttime).

**Right:**
```json
{
  "bedtime_start_hour": 21,
  "bedtime_end_hour": 7
}
```

### Mistake 2: Forgetting Admin Bypass

Admin users bypass most restrictions. If testing as admin, you won't see blocks. Test with a non-admin user group.

### Mistake 3: Not Setting Mode

Without `"mode": "enforce"`, policies default to `observe` (log only) or may not block.

### Mistake 4: Overlapping Blocklist/Allowlist

If a device is in both the allowlist and blocklist, blocklist wins. Review your lists for conflicts.

---

## Recommended Rollout Plan

1. **Week 1**: Enable `default` policy in observe mode
2. **Week 2**: Review suggested policies and usage patterns
3. **Week 3**: Enable recommended policies in `advisory` mode
4. **Week 4**: Switch to `enforce` mode after confirming no false positives

---

## Getting Help

- Policy documentation: `docs/policies/HOME_POLICIES.md`
- YORI project plan: `docs/v2.0/YORI_PROJECT_PLAN.md`
- OPA documentation: https://www.openpolicyagent.org/docs/latest/
