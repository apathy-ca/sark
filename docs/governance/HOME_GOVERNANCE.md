# Home LLM Governance

YORI governance modules for home network LLM control. These services provide the core functionality for managing LLM access in a home environment.

## Overview

The governance system provides six interconnected services:

| Service | Purpose | Hot Path |
|---------|---------|----------|
| **AllowlistService** | Bypass policies for trusted devices/users | Yes |
| **TimeRulesService** | Schedule-based access control | Yes |
| **EmergencyService** | Instant policy bypass for emergencies | Yes |
| **ConsentService** | Multi-approver policy change tracking | No |
| **OverrideService** | Per-request PIN-based bypass | Yes |
| **EnforcementService** | Coordinates all services for decisions | Yes |

## Quick Start

### Basic Usage

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sark.services.governance import (
    AllowlistService,
    TimeRulesService,
    EmergencyService,
    EnforcementService,
)

# Initialize services with database session
async def setup_governance(db: AsyncSession):
    allowlist = AllowlistService(db)
    time_rules = TimeRulesService(db)
    emergency = EmergencyService(db)

    # Create enforcement coordinator
    enforcement = EnforcementService(
        db=db,
        allowlist=allowlist,
        time_rules=time_rules,
        emergency=emergency,
        override=OverrideService(db),
    )

    return enforcement
```

### Evaluate Requests

```python
# Check if request is allowed
decision = await enforcement.evaluate({
    "device_ip": "192.168.1.50",
    "user_id": "user@example.com",
})

if decision.allowed:
    print(f"Request allowed: {decision.reason}")
else:
    print(f"Request denied: {decision.reason}")
```

## Services

### AllowlistService

Manages devices and users that bypass all policy evaluation.

```python
from sark.services.governance import AllowlistService
from sark.models.governance import AllowlistEntryType

service = AllowlistService(db)

# Add device by IP address
await service.add_device(
    "192.168.1.50",
    name="dad-laptop",
    reason="Admin device",
)

# Add device by MAC address
await service.add_entry(
    "AA:BB:CC:DD:EE:FF",
    AllowlistEntryType.MAC,
    name="mom-phone",
)

# Add user
await service.add_entry(
    "admin@example.com",
    AllowlistEntryType.USER,
    name="Admin user",
)

# Check if allowed (hot path)
if await service.is_allowed("192.168.1.50"):
    print("Device is allowlisted - skip policy evaluation")

# List entries
entries = await service.list_entries(active_only=True)

# Remove entry
await service.remove_entry("192.168.1.50")
```

#### Expiring Entries

```python
from datetime import datetime, timedelta, UTC

# Add temporary allowlist entry (24 hours)
await service.add_entry(
    "192.168.1.100",
    AllowlistEntryType.DEVICE,
    name="guest-device",
    expires_at=datetime.now(UTC) + timedelta(hours=24),
)

# Cleanup expired entries (run periodically)
count = await service.cleanup_expired()
print(f"Deactivated {count} expired entries")
```

### TimeRulesService

Schedule-based access control (bedtime, school hours, etc.).

```python
from sark.services.governance import TimeRulesService
from sark.models.governance import TimeRuleAction

service = TimeRulesService(db)

# Add bedtime rule (9pm - 7am, blocks all LLM access)
await service.add_rule(
    name="bedtime",
    start="21:00",
    end="07:00",
    action=TimeRuleAction.BLOCK,
    description="No LLM access during bedtime",
)

# Add weekday school hours rule
await service.add_rule(
    name="school-hours",
    start="08:00",
    end="15:00",
    days=["mon", "tue", "wed", "thu", "fri"],
    action=TimeRuleAction.ALERT,  # Allow but alert
    description="Alert during school hours",
)

# Check current time against rules (hot path)
result = await service.check_rules()
if result.blocked:
    print(f"Blocked by rule: {result.rule}")
    print(f"Reason: {result.reason}")

# Check specific time
from datetime import datetime, UTC
check_time = datetime.now(UTC).replace(hour=22, minute=30)
result = await service.check_rules(check_time=check_time)
```

#### Rule Priority

Lower priority number = higher precedence.

```python
# High priority alert (will match first)
await service.add_rule(
    name="homework-exception",
    start="19:00",
    end="21:00",
    action=TimeRuleAction.LOG,
    priority=10,  # Higher precedence
)

# Lower priority block
await service.add_rule(
    name="evening-limit",
    start="18:00",
    end="22:00",
    action=TimeRuleAction.BLOCK,
    priority=100,  # Lower precedence
)
```

### EmergencyService

Instant bypass of all policies for emergency situations.

```python
from sark.services.governance import EmergencyService

service = EmergencyService(db)

# Activate emergency override (max 24 hours)
override = await service.activate(
    duration_minutes=60,
    reason="Homework deadline - need immediate access",
    activated_by="parent",
)

# Check if active (hot path)
if await service.is_active():
    print("Emergency override active - all policies bypassed")

# Get current override details
current = await service.get_current()
print(f"Expires at: {current.expires_at}")

# Extend override
await service.extend(
    additional_minutes=30,
    extended_by="parent",
)

# Manually deactivate
await service.deactivate(deactivated_by="admin")

# View history
history = await service.get_history(limit=10)
```

### ConsentService

Multi-approver consent tracking for sensitive policy changes.

```python
from sark.services.governance import ConsentService

service = ConsentService(db)

# Request policy change (requires 2 approvers)
request = await service.request_change(
    change_type="enable_content_blocking",
    description="Enable content filtering for kids' devices",
    requester="parent1",
    required_approvers=2,
    expires_in_hours=48,
)

# First parent approves
await service.approve(request.id, approver="parent1")
# Note: requester cannot approve their own request

# Second parent approves
await service.approve(request.id, approver="parent2")
# Request is now approved!

# Check if change is approved
if await service.is_approved("enable_content_blocking"):
    # Apply the policy change
    pass

# Reject a request
await service.reject(
    request.id,
    rejector="parent2",
    reason="Not needed at this time",
)

# List pending requests
pending = await service.get_pending_requests()
```

### OverrideService

Per-request bypass with PIN authentication.

```python
from sark.services.governance import OverrideService

service = OverrideService(db)

# Create override for specific request
await service.create_override(
    request_id="blocked-request-123",
    pin="1234",
    reason="Need to access this for homework",
    expires_in_minutes=5,
)

# Validate and use override (hot path)
if await service.validate_override("blocked-request-123", "1234"):
    print("Override valid - allow this request")
    # Note: Override is now marked as used

# Check if override exists (without using it)
exists = await service.check_override_exists("blocked-request-123")

# Set master PIN (use with caution)
service.set_master_pin("master-secret-1234")
# Master PIN works for any request
```

### EnforcementService

Coordinates all services for policy decisions.

```python
from sark.services.governance import EnforcementService

# Create with all services
enforcement = EnforcementService(
    db=db,
    allowlist=allowlist_service,
    time_rules=time_rules_service,
    emergency=emergency_service,
    override=override_service,
    opa_client=opa_client,  # Optional OPA integration
)

# Full evaluation
decision = await enforcement.evaluate({
    "request_id": "req-123",
    "device_ip": "192.168.1.50",
    "user_id": "user@example.com",
    "override_pin": "1234",  # Optional
    "action": "chat/completions",
    "resource": "openai",
})

print(f"Allowed: {decision.allowed}")
print(f"Reason: {decision.reason}")
print(f"Source: {decision.decision_source}")

# Simple evaluation (just allow/deny)
allowed = await enforcement.evaluate_simple(
    device_ip="192.168.1.50",
    user_id="user@example.com",
)

# Get decision history
logs = await enforcement.get_decision_log(
    device_ip="192.168.1.50",
    allowed=False,
    limit=50,
)

# Get statistics
stats = await enforcement.get_statistics(since=datetime.now(UTC) - timedelta(days=7))
print(f"Total decisions: {stats['total_decisions']}")
print(f"Allow rate: {stats['allow_rate']}%")
```

#### Evaluation Order

The enforcement service evaluates in this order (first match wins):

1. **Emergency Override** - If active, allow immediately
2. **Allowlist (Device)** - If device IP is allowlisted, allow
3. **Allowlist (User)** - If user ID is allowlisted, allow
4. **Per-Request Override** - If valid override with PIN, allow
5. **Time Rules** - If blocking rule matches, deny
6. **OPA Policies** - Evaluate fine-grained policies

## Database Models

### SQLite Schema

```sql
-- Allowlist entries
CREATE TABLE governance_allowlist (
    id INTEGER PRIMARY KEY,
    entry_type VARCHAR(20) NOT NULL,  -- device, user, mac
    identifier VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(100),
    reason VARCHAR(500),
    created_by VARCHAR(100),
    active BOOLEAN DEFAULT TRUE,
    expires_at DATETIME,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

-- Time rules
CREATE TABLE governance_time_rules (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(500),
    start_time VARCHAR(5) NOT NULL,  -- HH:MM
    end_time VARCHAR(5) NOT NULL,
    action VARCHAR(20) DEFAULT 'block',
    days VARCHAR(50),  -- mon,tue,wed...
    timezone VARCHAR(50) DEFAULT 'UTC',
    priority INTEGER DEFAULT 100,
    active BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(100),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

-- Emergency overrides
CREATE TABLE governance_emergency_overrides (
    id INTEGER PRIMARY KEY,
    active BOOLEAN DEFAULT TRUE,
    reason VARCHAR(500) NOT NULL,
    activated_by VARCHAR(100),
    activated_at DATETIME NOT NULL,
    expires_at DATETIME NOT NULL,
    deactivated_at DATETIME,
    deactivated_by VARCHAR(100)
);

-- Consent requests
CREATE TABLE governance_consent_requests (
    id INTEGER PRIMARY KEY,
    change_type VARCHAR(100) NOT NULL,
    change_description TEXT NOT NULL,
    requester VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    required_approvers INTEGER DEFAULT 1,
    current_approvers VARCHAR(500),
    expires_at DATETIME,
    approved_at DATETIME,
    rejected_at DATETIME,
    rejection_reason VARCHAR(500),
    created_at DATETIME NOT NULL
);

-- Override requests
CREATE TABLE governance_override_requests (
    id INTEGER PRIMARY KEY,
    request_id VARCHAR(100) UNIQUE NOT NULL,
    pin_hash VARCHAR(256) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    reason VARCHAR(500),
    requested_by VARCHAR(100),
    approved_by VARCHAR(100),
    expires_at DATETIME NOT NULL,
    used_at DATETIME,
    created_at DATETIME NOT NULL
);

-- Enforcement decision log
CREATE TABLE governance_enforcement_log (
    id INTEGER PRIMARY KEY,
    request_id VARCHAR(100) NOT NULL,
    client_ip VARCHAR(45),
    allowed BOOLEAN NOT NULL,
    reason VARCHAR(500) NOT NULL,
    decision_source VARCHAR(50) NOT NULL,
    rule_name VARCHAR(100),
    policy_name VARCHAR(100),
    duration_ms INTEGER,
    metadata TEXT,
    created_at DATETIME NOT NULL
);

-- Indexes
CREATE INDEX idx_allowlist_identifier ON governance_allowlist(identifier);
CREATE INDEX idx_allowlist_active ON governance_allowlist(active);
CREATE INDEX idx_time_rules_active ON governance_time_rules(active);
CREATE INDEX idx_emergency_active ON governance_emergency_overrides(active);
CREATE INDEX idx_enforcement_created ON governance_enforcement_log(created_at);
```

## API Endpoints

The governance module exposes REST API endpoints at `/api/governance/`:

### Allowlist

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/governance/allowlist` | Add entry |
| GET | `/governance/allowlist` | List entries |
| GET | `/governance/allowlist/check/{identifier}` | Check if allowed |
| DELETE | `/governance/allowlist/{identifier}` | Remove entry |

### Time Rules

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/governance/time-rules` | Add rule |
| GET | `/governance/time-rules` | List rules |
| GET | `/governance/time-rules/check` | Check current time |
| DELETE | `/governance/time-rules/{name}` | Remove rule |

### Emergency Override

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/governance/emergency` | Activate override |
| GET | `/governance/emergency/status` | Get status |
| DELETE | `/governance/emergency` | Deactivate |
| GET | `/governance/emergency/history` | View history |

### Consent

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/governance/consent` | Request change |
| POST | `/governance/consent/{id}/approve` | Approve request |
| POST | `/governance/consent/{id}/reject` | Reject request |
| GET | `/governance/consent/pending` | List pending |

### Per-Request Override

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/governance/override` | Create override |
| POST | `/governance/override/validate` | Validate and use |
| GET | `/governance/override/{request_id}/exists` | Check exists |

### Enforcement

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/governance/evaluate` | Full evaluation |
| GET | `/governance/evaluate/simple` | Simple check |
| GET | `/governance/statistics` | Get stats |

## Security Considerations

### PIN Storage

Override PINs are hashed using SHA-256 with a random salt:

```python
def _hash_pin(self, pin: str) -> str:
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}:{pin}".encode()).hexdigest()
    return f"{salt}:{hashed}"
```

### Fail-Closed Design

The enforcement service fails closed on errors:

```python
try:
    decision = await self._check_opa_policies(request)
except Exception as e:
    # Deny on error
    return EnforcementDecision(allowed=False, reason=f"Error: {e}")
```

### Audit Logging

All enforcement decisions are logged for audit purposes:

```python
# Decision log includes:
- request_id: Unique request identifier
- client_ip: Source IP address
- allowed: True/False
- reason: Human-readable reason
- decision_source: Which service made the decision
- duration_ms: Decision latency
```

## Best Practices

### Home Network Setup

1. **Start with observation mode** - Log decisions without blocking
2. **Add trusted devices to allowlist** - Parent devices, home servers
3. **Create time rules gradually** - Start with bedtime, add more as needed
4. **Test emergency override** - Make sure it works before you need it
5. **Set up two-parent consent** - For sensitive policy changes

### Performance

- Hot-path services use in-memory caching
- Cache TTL is configurable (default: 60 seconds for allowlist)
- Time rules are cached for 5 minutes
- Emergency checks cache for 10 seconds

### Maintenance

```python
# Run periodically (e.g., hourly cron)
async def cleanup_governance(db: AsyncSession):
    allowlist = AllowlistService(db)
    emergency = EmergencyService(db)
    override = OverrideService(db)

    await allowlist.cleanup_expired()
    await emergency.cleanup_expired()
    await override.cleanup_expired()
```

## Troubleshooting

### Request Unexpectedly Blocked

1. Check time rules: `GET /governance/time-rules/check`
2. Verify device not in allowlist: `GET /governance/allowlist/check/{ip}`
3. Check emergency status: `GET /governance/emergency/status`
4. Review decision log: `GET /governance/statistics`

### Emergency Override Not Working

1. Verify no existing active override
2. Check expiration time hasn't passed
3. Confirm activation reason was provided

### Time Rule Not Applying

1. Check rule is active: `GET /governance/time-rules`
2. Verify timezone setting
3. Check day-of-week configuration
4. Review rule priority (lower = higher)
