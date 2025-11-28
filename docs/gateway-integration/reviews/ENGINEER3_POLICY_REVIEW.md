# Architectural Review: OPA Policy Implementation

**Reviewer:** Engineer 1 (Architect)
**Engineer Reviewed:** Engineer 3
**Project:** SARK Gateway Integration - OPA Policy Authorization
**Review Date:** 2024
**Branches Reviewed:**
- `feat/gateway-client` (Gateway Models - Engineer 1)
- `feat/gateway-policies` (OPA Policies - Engineer 3)

---

## Executive Summary

**Overall Grade: B-**

### Key Strengths
- **Well-structured OPA policies** with clear separation between Gateway and A2A authorization
- **Comprehensive helper functions** in Rego policies for audit trails and parameter filtering
- **Robust error handling** with fail-closed security posture in the OPA client

### Critical Issues Summary
The implementation has **significant architectural misalignment** between the Gateway models and OPA policies. The most critical issue is that Engineer 3 created policies expecting a completely different input structure than what my Gateway models provide. There are enum value mismatches (`LIMITED` vs `VERIFIED`, `QUERY` vs `MONITOR`), missing model field validations in policies, and the OPA client bypasses model validation by using raw dictionaries instead of Pydantic instances.

---

## Critical Issues (BLOCKING - Must Fix Before Merge)

### 1. **Enum Value Mismatch: TrustLevel**
**Severity:** CRITICAL
**Location:** `src/sark/models/gateway.py` vs `opa/policies/a2a_authorization.rego`

**Problem:**
The `TrustLevel` enum in my Gateway models defines three values:
```python
class TrustLevel(str, Enum):
    TRUSTED = "trusted"
    LIMITED = "limited"      # ← My model
    UNTRUSTED = "untrusted"
```

But the A2A policy expects `"verified"` instead of `"limited"`:
```rego
# Line 20: a2a_authorization.rego
input.source_agent.trust_level == "trusted"
input.target_agent.trust_level == "trusted"

# Line 30: a2a_authorization.rego
input.source_agent.trust_level in ["trusted", "verified"]  # ← "verified" doesn't exist!

# Line 38: a2a_authorization.rego
input.source_agent.trust_level == "verified"
input.target_agent.trust_level == "verified"
```

**Impact:**
- All agents with `trust_level="limited"` will fail policy evaluation
- Policies checking for `"verified"` will never match any valid agent from my models
- Silent authorization failures with confusing audit logs

**Recommended Fix:**
**Option A (Preferred):** Update `TrustLevel` enum to match policy expectations:
```python
class TrustLevel(str, Enum):
    TRUSTED = "trusted"
    VERIFIED = "verified"    # Change from LIMITED
    UNTRUSTED = "untrusted"
```

**Option B:** Update all policy references from `"verified"` to `"limited"` in `a2a_authorization.rego`

**Coordination Required:** This is a breaking change. Engineer 1 should update the model, then Engineer 3 should verify all policies still work.

---

### 2. **Enum Value Mismatch: AgentType**
**Severity:** CRITICAL
**Location:** `src/sark/models/gateway.py` vs `opa/policies/a2a_authorization.rego`

**Problem:**
The `AgentType` enum in my Gateway models defines:
```python
class AgentType(str, Enum):
    SERVICE = "service"
    WORKER = "worker"
    QUERY = "query"          # ← My model has QUERY
```

But the A2A policy expects `"orchestrator"` and `"monitor"`:
```rego
# Line 106: a2a_authorization.rego
input.source_agent.type == "orchestrator"  # ← Not in my enum!

# Line 114: a2a_authorization.rego
input.source_agent.type == "monitor"       # ← Not in my enum!
```

Additionally, I defined `ORCHESTRATOR` and `MONITOR` in my task description, but the actual code only has `SERVICE`, `WORKER`, and `QUERY`.

**Impact:**
- Orchestrator and Monitor agents cannot be authorized
- `QUERY` agent type is unused in policies
- Complete disconnect between model capabilities and policy rules

**Recommended Fix:**
Update `AgentType` enum to include all agent types used in policies:
```python
class AgentType(str, Enum):
    SERVICE = "service"
    WORKER = "worker"
    ORCHESTRATOR = "orchestrator"  # Add
    MONITOR = "monitor"             # Add
    # Remove QUERY or map it to appropriate policy
```

**Coordination Required:** Engineer 1 must update the model. Engineer 3 should verify if `QUERY` was intentional and map it to policy logic.

---

### 3. **Missing GatewayAuthorizationRequest Validation in Policies**
**Severity:** CRITICAL
**Location:** `opa/policies/gateway_authorization.rego` vs `src/sark/models/gateway.py`

**Problem:**
My `GatewayAuthorizationRequest` model enforces strict action validation:
```python
@field_validator('action')
@classmethod
def validate_action(cls, v: str) -> str:
    valid_actions = [
        'gateway:tool:invoke',
        'gateway:server:list',
        'gateway:tool:discover',
        'gateway:server:info'
    ]
    if v not in valid_actions:
        raise ValueError(f"Action must be one of {valid_actions}")
    return v
```

But the OPA Gateway policy uses completely different action strings:
```rego
# Line 19: gateway_authorization.rego
input.action == "gateway:tool:invoke"      # ✓ Matches model
input.action == "gateway:server:register"  # ✗ NOT in valid_actions!
input.action == "gateway:servers:list"     # ✗ "servers" plural vs "server" singular
input.action == "gateway:tools:list"       # ✗ NOT in valid_actions!
input.action == "gateway:audit:view"       # ✗ NOT in valid_actions!
```

**Impact:**
- Requests using `"gateway:server:register"` will be rejected by model validation before reaching OPA
- Developers will get confusing validation errors
- Policy rules for registration/audit become unreachable code

**Recommended Fix:**
**Option A (Preferred):** Update `GatewayAuthorizationRequest.validate_action()` to include all actions used in policies:
```python
valid_actions = [
    'gateway:tool:invoke',
    'gateway:server:list',      # Keep as singular
    'gateway:server:register',   # Add
    'gateway:server:info',
    'gateway:tool:discover',
    'gateway:tools:list',        # Add plural variant
    'gateway:servers:list',      # Add plural variant
    'gateway:audit:view',        # Add
]
```

**Option B:** Standardize on singular form in policies:
- Change `"gateway:servers:list"` → `"gateway:server:list"`
- Change `"gateway:tools:list"` → `"gateway:tool:list"`
- Remove unsupported actions from policies

---

### 4. **OPA Client Bypasses Model Validation**
**Severity:** CRITICAL
**Location:** `src/sark/services/policy/opa_client.py`

**Problem:**
The `OPAClient` uses a generic `AuthorizationInput` model with loose typing:
```python
class AuthorizationInput(BaseModel):
    user: dict[str, Any]              # ← Should use structured models
    action: str                       # ← No validation
    tool: dict[str, Any] | None = None
    server: dict[str, Any] | None = None
    context: dict[str, Any]
```

This completely bypasses the validation logic in my `GatewayAuthorizationRequest` model. The helper methods construct raw dicts:
```python
# Line 494-516: opa_client.py
auth_input = AuthorizationInput(
    user={
        "id": user_id,
        "email": user_email,
        "role": user_role,
        "teams": team_ids or [],
    },
    action="tool:invoke",  # ← Uses old action format, bypasses validation!
    tool={
        "name": tool_name,
        "sensitivity_level": tool_sensitivity,
        "owner": tool_owner_id,
        "managers": team_ids or [],
    },
    context={"timestamp": 0},
)
```

**Impact:**
- All Pydantic validations in `GatewayAuthorizationRequest` are unused
- Invalid sensitivity levels can pass through (`"confidential"` instead of `"high"`)
- No compile-time safety for action strings
- Type confusion between `tool_name` (string) vs my model's `GatewayToolInfo` object

**Recommended Fix:**
Refactor `OPAClient` to use my Gateway models:
```python
from sark.models.gateway import (
    GatewayAuthorizationRequest,
    GatewayAuthorizationResponse,
    SensitivityLevel,
    AgentContext,
)

async def evaluate_gateway_policy(
    self,
    request: GatewayAuthorizationRequest,  # ← Use the actual model
    user_context: dict[str, Any],
    gateway_metadata: dict[str, Any] | None = None,
) -> GatewayAuthorizationResponse:
    """Evaluate Gateway policy using validated models."""

    # Construct OPA input from validated request
    auth_input = AuthorizationInput(
        user=user_context,
        action=request.action,  # Already validated
        tool={
            "name": request.tool_name,
            "sensitivity_level": ...,  # Extract from GatewayToolInfo
        } if request.tool_name else None,
        server=...,
        context=request.gateway_metadata,
    )

    decision = await self.evaluate_policy(auth_input)

    # Return using response model
    return GatewayAuthorizationResponse(
        allow=decision.allow,
        reason=decision.reason,
        filtered_parameters=decision.filtered_parameters,
        audit_id=decision.audit_id,
    )
```

---

### 5. **Input Structure Mismatch: Tool and Server Fields**
**Severity:** CRITICAL
**Location:** `opa/policies/gateway_authorization.rego` vs models

**Problem:**
The Gateway policy expects specific field names that don't exist in my models:

**Policy Expectations:**
```rego
input.server.managed_by_team   # Line 39, 99
input.server.owner_id          # Line 46, 165, 209
input.server.visibility        # Line 160, 177
input.server.environment       # Line 176
input.tool.parameters          # Line 107 (expects dict)
```

**My GatewayServerInfo Model:**
```python
class GatewayServerInfo(BaseModel):
    server_id: str
    server_name: str
    server_url: HttpUrl
    sensitivity_level: SensitivityLevel
    authorized_teams: list[str]  # ← Not "managed_by_team"
    access_restrictions: dict[str, Any] | None
    health_status: str
    tools_count: int
    # Missing: owner_id, visibility, environment
```

**My GatewayToolInfo Model:**
```python
class GatewayToolInfo(BaseModel):
    tool_name: str
    server_name: str
    description: str
    sensitivity_level: SensitivityLevel
    parameters: list[dict[str, Any]]  # ← List, not dict!
    sensitive_params: list[str]
    required_capabilities: list[str]
```

**Impact:**
- All policy rules checking `server.managed_by_team` will fail
- Team-based access control is broken
- Parameter filtering logic expects wrong data structure
- Server ownership checks will never succeed

**Recommended Fix:**
**Option A:** Enhance `GatewayServerInfo` to include policy-required fields:
```python
class GatewayServerInfo(BaseModel):
    server_id: str
    server_name: str
    server_url: HttpUrl
    sensitivity_level: SensitivityLevel
    owner_id: str | None = None              # Add
    managed_by_team: str | None = None       # Add
    authorized_teams: list[str] = Field(default_factory=list)
    visibility: str = "internal"             # Add: public/internal/private
    environment: str = "production"          # Add: dev/staging/production
    access_restrictions: dict[str, Any] | None = None
    health_status: str
    tools_count: int
```

**Option B:** Update OPA policies to use `authorized_teams[0]` instead of `managed_by_team`.

---

## Major Concerns (Should Fix - Architectural Alignment)

### 6. **A2A Authorization Input Structure Mismatch**
**Severity:** MAJOR
**Location:** `opa/policies/a2a_authorization.rego` vs `src/sark/models/gateway.py`

**Problem:**
My `A2AAuthorizationRequest` model has this structure:
```python
class A2AAuthorizationRequest(BaseModel):
    source_agent_id: str          # Just ID
    target_agent_id: str          # Just ID
    capability: str
    message_type: str
    payload_metadata: dict[str, Any]
```

But the A2A policy expects full `AgentContext` objects:
```rego
input.source_agent.trust_level   # Expects full agent object
input.source_agent.type
input.source_agent.capabilities
input.source_agent.environment
input.target_agent.trust_level
input.target_agent.type
```

The OPA client method `evaluate_a2a_policy()` correctly expects full agent objects (line 744-750), but my model only has agent IDs.

**Impact:**
- Cannot use `A2AAuthorizationRequest` model for actual authorization
- Developers forced to bypass model and use raw dicts
- No type safety for A2A requests

**Recommended Fix:**
Update `A2AAuthorizationRequest` to embed full agent contexts:
```python
class A2AAuthorizationRequest(BaseModel):
    source_agent: AgentContext     # Full context, not just ID
    target_agent: AgentContext     # Full context, not just ID
    action: str                    # Match policy: "a2a:communicate", "a2a:execute"
    context: dict[str, Any] = Field(default_factory=dict)

    @field_validator('action')
    @classmethod
    def validate_action(cls, v: str) -> str:
        valid_actions = [
            'a2a:communicate',
            'a2a:execute',
            'a2a:query',
            'a2a:delegate',
            'a2a:invoke',
        ]
        if v not in valid_actions:
            raise ValueError(f"Action must be one of {valid_actions}")
        return v
```

---

### 7. **Sensitivity Level Terminology Inconsistency**
**Severity:** MAJOR
**Location:** Multiple files

**Problem:**
Gateway models use: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
OPA policies use: `"low"`, `"medium"`, `"high"`, `"critical"` (lowercase strings) ✓
OPA client TTL uses: `"critical"`, `"confidential"`, `"internal"`, `"public"` ✗

```python
# Line 205-211: opa_client.py
ttl_map = {
    "critical": 60,
    "confidential": 120,  # ← Not in SensitivityLevel enum!
    "internal": 180,      # ← Not in SensitivityLevel enum!
    "public": 300,        # ← Not in SensitivityLevel enum!
}
```

**Impact:**
- Cache TTL logic will default to 120s for all valid sensitivity levels
- Caching optimization is broken for non-critical tools
- Confusing for developers seeing different sensitivity vocabularies

**Recommended Fix:**
Align TTL map with `SensitivityLevel` enum:
```python
ttl_map = {
    "critical": 60,      # Short cache for critical
    "high": 120,         # Medium cache for high
    "medium": 180,       # Longer cache for medium
    "low": 300,          # Longest cache for low
}
```

---

### 8. **Missing AgentContext Field in Policies**
**Severity:** MAJOR
**Location:** `opa/policies/a2a_authorization.rego` vs `src/sark/models/gateway.py`

**Problem:**
My `AgentContext` model defines these fields:
```python
class AgentContext(BaseModel):
    agent_id: str
    agent_type: AgentType
    trust_level: TrustLevel
    capabilities: list[str]
    environment: str
    rate_limited: bool              # ← Not used in policies
    metadata: dict[str, Any]        # ← Not used in policies
```

The A2A policy expects additional fields not in my model:
```rego
# Line 51: a2a_authorization.rego
input.target_agent.accepts_execution == true    # ← Not in AgentContext

# Line 59: a2a_authorization.rego
input.target_agent.accepts_queries == true      # ← Not in AgentContext

# Line 66: a2a_authorization.rego
input.target_agent.accepts_delegation == true   # ← Not in AgentContext

# Line 132: a2a_authorization.rego
agent.rate_limit_per_minute                     # ← Not in AgentContext
```

**Impact:**
- Policy rules checking `accepts_execution`, `accepts_queries`, `accepts_delegation` will fail
- Rate limiting logic is broken
- Capability enforcement doesn't work as designed

**Recommended Fix:**
Enhance `AgentContext` model:
```python
class AgentContext(BaseModel):
    agent_id: str
    agent_type: AgentType
    trust_level: TrustLevel
    capabilities: list[str]
    environment: str
    organization_id: str | None = None        # Add for cross-org checks
    accepts_execution: bool = True            # Add
    accepts_queries: bool = True              # Add
    accepts_delegation: bool = False          # Add (more restrictive default)
    rate_limit_per_minute: int = 100          # Add
    rate_limited: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
```

---

### 9. **Action String Format Inconsistency**
**Severity:** MAJOR
**Location:** `src/sark/services/policy/opa_client.py`

**Problem:**
The helper method `check_tool_access()` uses old-style action strings:
```python
# Line 501: opa_client.py
action="tool:invoke",  # ← Old format
```

But Gateway policies expect:
```rego
input.action == "gateway:tool:invoke"  # Prefixed with "gateway:"
```

And `check_server_registration()` uses:
```python
# Line 546: opa_client.py
action="server:register",  # ← Old format, should be "gateway:server:register"
```

**Impact:**
- These helper methods will always fail authorization
- Developers using convenience methods get confused errors
- Inconsistent action naming across codebase

**Recommended Fix:**
Update helper methods to use correct action prefixes:
```python
async def check_tool_access(self, ...) -> AuthorizationDecision:
    auth_input = AuthorizationInput(
        user={...},
        action="gateway:tool:invoke",  # ← Fix prefix
        tool={...},
        context={...},
    )
    return await self.evaluate_policy(auth_input)

async def check_server_registration(self, ...) -> AuthorizationDecision:
    auth_input = AuthorizationInput(
        user={...},
        action="gateway:server:register",  # ← Fix prefix
        server={...},
        context={...},
    )
    return await self.evaluate_policy(auth_input)
```

---

## Minor Issues (Nice to Have - Code Quality)

### 10. **GatewayAuditEvent Not Used in OPA Client**
**Severity:** MINOR
**Location:** `src/sark/models/gateway.py` and `opa_client.py`

**Problem:**
I defined `GatewayAuditEvent` model for structured audit logging:
```python
class GatewayAuditEvent(BaseModel):
    event_type: str
    user_id: str | None
    agent_id: str | None
    server_name: str | None
    tool_name: str | None
    decision: str
    reason: str
    timestamp: int
    gateway_request_id: str
    metadata: dict[str, Any]
```

But the OPA client just returns `audit_id` strings without structured audit events.

**Impact:**
- Audit event model is unused
- Missing opportunity for type-safe audit logging
- Harder to integrate with audit service

**Recommended Fix:**
Enhance `GatewayAuthorizationResponse` to optionally include audit event:
```python
class GatewayAuthorizationResponse(BaseModel):
    allow: bool
    reason: str
    filtered_parameters: dict[str, Any] | None = None
    audit_id: str | None = None
    audit_event: GatewayAuditEvent | None = None  # Add
    cache_ttl: int = Field(default=60, ge=0)
```

---

### 11. **Missing Timestamp Validation in Context**
**Severity:** MINOR
**Location:** `src/sark/models/gateway.py`

**Problem:**
The policies heavily use `input.context.timestamp` for time-based access control, but my models don't enforce timestamp format/validation.

**Impact:**
- Potential for invalid timestamp formats
- Time-based policies may fail silently

**Recommended Fix:**
Add timestamp validation to authorization request models:
```python
class GatewayAuthorizationRequest(BaseModel):
    action: str
    server_name: str | None = None
    tool_name: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    gateway_metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: int | None = None  # Add: Unix timestamp

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: int | None) -> int:
        if v is None:
            return int(time.time())
        if v < 0:
            raise ValueError("Timestamp must be positive")
        return v
```

---

### 12. **Hardcoded Timestamp Logic in OPA Client**
**Severity:** MINOR
**Location:** `src/sark/services/policy/opa_client.py`

**Problem:**
The `check_tool_access()` method has a bizarre hardcoded timestamp fetch:
```python
# Line 509-513: opa_client.py
context={
    "timestamp": (
        httpx.get("https://worldtimeapi.org/api/ip").json()["unixtime"]
        if settings.environment == "production"
        else 0
    )
}
```

**Impact:**
- Synchronous HTTP call blocks async method
- External API dependency for authorization
- Will fail if API is down
- Always returns `0` in non-production (breaks time-based tests)

**Recommended Fix:**
Use local time and let caller override if needed:
```python
import time

async def check_tool_access(
    self,
    user_id: str,
    user_email: str,
    user_role: str,
    tool_name: str,
    tool_sensitivity: str,
    tool_owner_id: str | None = None,
    team_ids: list[str] | None = None,
    timestamp: int | None = None,  # Add parameter
) -> AuthorizationDecision:
    auth_input = AuthorizationInput(
        user={...},
        action="gateway:tool:invoke",
        tool={...},
        context={
            "timestamp": timestamp or int(time.time()),  # Use local time
        },
    )
    return await self.evaluate_policy(auth_input)
```

---

### 13. **Parameter Filtering Structure Mismatch**
**Severity:** MINOR
**Location:** `opa/policies/gateway_authorization.rego`

**Problem:**
The policy's parameter filtering expects `input.tool.parameters` to be a dict:
```rego
# Line 107-125: gateway_authorization.rego
filter_params(params, role, sensitivity) := filtered if {
    # Non-admin users: filter out sensitive fields
    role != "admin"
    filtered := {k: v |
        some k, v in params     # ← Expects dict iteration
        not is_sensitive_param(k, sensitivity)
    }
}
```

But my `GatewayToolInfo` model defines parameters as a list:
```python
parameters: list[dict[str, Any]] = Field(default_factory=list)
```

**Impact:**
- Parameter filtering will fail or behave unexpectedly
- Sensitive parameters may leak to unauthorized users

**Recommended Fix:**
**Option A:** Change model to use dict:
```python
parameters: dict[str, Any] = Field(default_factory=dict)
```

**Option B:** Update policy to handle list of parameter schemas:
```rego
filter_params(params, role, sensitivity) := filtered if {
    role != "admin"
    filtered := [p |
        some i
        p := params[i]
        not is_sensitive_param(p.name, sensitivity)
    ]
}
```

---

### 14. **Missing Required Capabilities Enforcement**
**Severity:** MINOR
**Location:** Models vs policies

**Problem:**
My `GatewayToolInfo` includes `required_capabilities`:
```python
required_capabilities: list[str] = Field(default_factory=list)
```

But there's no policy logic to enforce that agents have these capabilities before invoking tools.

**Impact:**
- Model field is unused
- No capability-based access control for tools

**Recommended Fix:**
Add capability checking to Gateway policy:
```rego
# Add to gateway_authorization.rego
allow if {
    input.action == "gateway:tool:invoke"
    # Check that user/agent has required capabilities
    has_required_capabilities(input.user, input.tool)
}

has_required_capabilities(user, tool) if {
    # If no capabilities required, allow
    count(tool.required_capabilities) == 0
}

has_required_capabilities(user, tool) if {
    # User must have ALL required capabilities
    required := {c | some c in tool.required_capabilities}
    user_caps := {c | some c in user.capabilities}
    required_subset := required & user_caps
    count(required_subset) == count(required)
}
```

---

### 15. **Policy Service Not Integrated with OPA Client**
**Severity:** MINOR
**Location:** `src/sark/services/policy/policy_service.py`

**Problem:**
The `PolicyService` manages policy versioning and activation but has no integration with `OPAClient`. There's no mechanism to load active policies into OPA.

**Impact:**
- Policy versioning is unused
- No way to deploy new policy versions
- OPA must be manually updated

**Recommended Fix:**
Add OPA bundle deployment to `PolicyService`:
```python
async def deploy_to_opa(self, policy_id: UUID) -> bool:
    """Deploy active policy version to OPA."""
    policy = await self.get_policy(policy_id)
    if not policy.current_version_id:
        raise ValueError("No active version")

    version = await self.db.get(PolicyVersion, policy.current_version_id)

    # Upload to OPA via bundle API
    # POST to /v1/policies/{policy.name}
    # with version.content as Rego policy

    return True
```

---

## Recommendations

### Immediate Actions (Pre-Merge)

1. **Coordinate Enum Alignment** (Critical Issues #1, #2)
   - Schedule meeting with Engineer 1 and Engineer 3
   - Decide on canonical enum values
   - Update models and policies together
   - Add integration tests to prevent future drift

2. **Expand Model Field Coverage** (Critical Issue #5, Major Issue #8)
   - Engineer 1: Update `GatewayServerInfo` with `owner_id`, `managed_by_team`, `visibility`, `environment`
   - Engineer 1: Update `AgentContext` with `accepts_*` fields and `rate_limit_per_minute`
   - Engineer 3: Verify all policy rules still function

3. **Fix Action String Validation** (Critical Issue #3)
   - Engineer 1: Expand `valid_actions` in `GatewayAuthorizationRequest`
   - Standardize on `gateway:*` prefix for all Gateway actions
   - Document action naming convention

4. **Refactor OPA Client to Use Models** (Critical Issue #4)
   - Engineer 3: Update `evaluate_gateway_policy()` to accept `GatewayAuthorizationRequest`
   - Replace `AuthorizationInput` dict fields with model types
   - Add type hints for all parameters

### Architectural Improvements

5. **Create Model-Policy Alignment Tests**
   ```python
   # tests/test_integration/test_model_policy_alignment.py

   def test_sensitivity_levels_match():
       """Ensure all policy sensitivity values exist in SensitivityLevel enum."""
       policy_sensitivities = extract_from_rego("gateway_authorization.rego")
       for sens in policy_sensitivities:
           assert sens in [e.value for e in SensitivityLevel]

   def test_agent_types_match():
       """Ensure all policy agent types exist in AgentType enum."""
       # Similar check for AgentType

   def test_trust_levels_match():
       """Ensure all policy trust levels exist in TrustLevel enum."""
       # Similar check for TrustLevel
   ```

6. **Document Input/Output Contracts**
   Create `docs/gateway-integration/OPA_POLICY_CONTRACTS.md`:
   ```markdown
   # OPA Policy Input/Output Contracts

   ## Gateway Authorization Input

   ```json
   {
     "user": {
       "id": "string (required)",
       "role": "admin|developer|team_lead|viewer",
       "teams": ["string"],
       "environment": "string"
     },
     "action": "gateway:tool:invoke|gateway:server:register|...",
     "server": {
       "id": "string",
       "owner_id": "string",
       "managed_by_team": "string",
       "sensitivity_level": "low|medium|high|critical"
     },
     "tool": {
       "name": "string",
       "sensitivity_level": "low|medium|high|critical",
       "parameters": {"key": "value"}
     },
     "context": {
       "timestamp": "integer (unix time)"
     }
   }
   ```
   ```

7. **Standardize Naming Conventions**
   - Actions: `gateway:<noun>:<verb>` (e.g., `gateway:tool:invoke`)
   - Enums: Uppercase constants, lowercase string values
   - Fields: snake_case everywhere (both models and policies)

8. **Add Policy Validation Pipeline**
   - Pre-commit hook to validate Rego syntax
   - CI job to extract enum values from policies and compare to models
   - Auto-generate TypeScript types from Pydantic models for frontend

### Model Enhancement Suggestions Based on Policy Needs

9. **Create Policy Context Models**
   ```python
   # src/sark/models/gateway.py

   class GatewayPolicyContext(BaseModel):
       """Context for Gateway policy evaluation."""
       timestamp: int = Field(default_factory=lambda: int(time.time()))
       environment: str = "production"
       client_ip: str | None = None
       emergency_override: bool = False
       emergency_reason: str | None = None
       emergency_approver: str | None = None
       audit_enabled: bool = True

   class A2APolicyContext(BaseModel):
       """Context for A2A policy evaluation."""
       rate_limit: RateLimitInfo | None = None
       encryption_required: bool = True
       monitoring_required: bool = False

   class RateLimitInfo(BaseModel):
       current_count: int
       window_start: int
       limit: int
   ```

10. **Add User Context Model**
    ```python
    class UserContext(BaseModel):
        """User context for authorization."""
        id: str
        email: str | None = None
        role: str  # Consider making this an enum
        teams: list[str] = Field(default_factory=list)
        team_manager_of: list[str] = Field(default_factory=list)
        environment: str = "production"
        mfa_verified: bool = False
        capabilities: list[str] = Field(default_factory=list)
    ```

### Integration Patterns to Standardize

11. **Request/Response Pattern for Authorization**
    ```python
    # Standardize on this pattern across all services

    from sark.models.gateway import (
        GatewayAuthorizationRequest,
        GatewayAuthorizationResponse,
    )
    from sark.services.policy.opa_client import OPAClient

    async def authorize_gateway_request(
        opa_client: OPAClient,
        request: GatewayAuthorizationRequest,
        user_context: UserContext,
    ) -> GatewayAuthorizationResponse:
        """Standard authorization flow."""

        decision = await opa_client.evaluate_gateway_policy(
            user_context=user_context.model_dump(),
            action=request.action,
            server=...,  # Construct from request
            tool=...,    # Construct from request
            context=..., # Construct from request
        )

        return GatewayAuthorizationResponse(
            allow=decision.allow,
            reason=decision.reason,
            filtered_parameters=decision.filtered_parameters,
            audit_id=decision.audit_id,
        )
    ```

12. **Cache Key Generation**
    Standardize cache key format to include model version:
    ```python
    def generate_cache_key(
        user_id: str,
        action: str,
        resource: str,
        model_version: str = "v1",
    ) -> str:
        return f"policy:{model_version}:{user_id}:{action}:{resource}"
    ```

---

## Positive Findings

### What Engineer 3 Did Well

1. **Excellent OPA Policy Structure**
   - Clean separation between Gateway and A2A policies
   - Well-organized helper functions
   - Comprehensive audit reason generation
   - Good use of Rego best practices (future keywords, default deny)

2. **Robust Error Handling**
   - Fail-closed security posture throughout
   - Graceful degradation on OPA failures
   - Comprehensive exception handling in async code

3. **Cache Implementation**
   - Smart sensitivity-based TTL strategy
   - Batch evaluation for performance
   - Stale-while-revalidate pattern
   - Good metrics tracking

4. **Security-First Design**
   - Parameter filtering to prevent leaking sensitive data
   - Time-based access controls
   - Rate limiting considerations
   - Audit logging throughout

5. **Comprehensive Policy Coverage**
   - RBAC rules
   - Team-based access
   - Sensitivity-level enforcement
   - Cross-environment restrictions for A2A
   - Trust level verification

6. **Good Code Organization**
   - Clear file structure
   - Logical separation of concerns
   - Well-documented policy rules with comments
   - Consistent naming within each subsystem

### Patterns to Replicate

- **Audit reason generation in policies**: The detailed audit reasons with context are excellent for debugging and compliance
- **Helper function organization**: The separation of policy logic from helpers is clean
- **Batch operations**: The batch evaluation pattern should be used across other services
- **Cache revalidation**: The stale-while-revalidate pattern is sophisticated and production-ready

---

## Testing Recommendations

### Add These Test Scenarios

1. **Model-Policy Integration Tests**
   ```python
   async def test_gateway_authorization_request_to_opa():
       """Test that GatewayAuthorizationRequest maps correctly to OPA input."""
       request = GatewayAuthorizationRequest(
           action="gateway:tool:invoke",
           tool_name="test-tool",
           parameters={},
           gateway_metadata={"timestamp": 0},
       )

       # Should not raise validation errors
       decision = await opa_client.evaluate_gateway_policy(
           user_context={"id": "user1", "role": "admin"},
           action=request.action,
           ...
       )

       assert isinstance(decision, GatewayAuthorizationResponse)
   ```

2. **Enum Value Coverage Tests**
   ```python
   @pytest.mark.parametrize("sensitivity", [
       SensitivityLevel.LOW,
       SensitivityLevel.MEDIUM,
       SensitivityLevel.HIGH,
       SensitivityLevel.CRITICAL,
   ])
   async def test_all_sensitivity_levels_supported(sensitivity):
       """Ensure OPA policies handle all SensitivityLevel enum values."""
       # Test each enum value works in policies
   ```

3. **A2A Complete Flow Test**
   ```python
   async def test_a2a_full_request_response_cycle():
       """Test A2A authorization using AgentContext models."""
       source = AgentContext(
           agent_id="agent1",
           agent_type=AgentType.SERVICE,
           trust_level=TrustLevel.TRUSTED,
           capabilities=["execute"],
           environment="production",
       )

       target = AgentContext(
           agent_id="agent2",
           agent_type=AgentType.WORKER,
           trust_level=TrustLevel.TRUSTED,
           capabilities=[],
           environment="production",
       )

       decision = await opa_client.evaluate_a2a_policy(
           source_agent=source.model_dump(),
           target_agent=target.model_dump(),
           action="a2a:execute",
       )

       assert decision.allow
   ```

---

## Conclusion

Engineer 3 has built a solid OPA policy framework with excellent security practices and sophisticated caching. However, there are **critical architectural misalignments** with the Gateway models that must be resolved before merge.

The primary issues stem from:
1. Independent development without continuous integration testing
2. Missing shared validation between models and policies
3. Different assumptions about enum values and data structures

### Next Steps

1. **Immediate** (This Week):
   - Fix enum mismatches (TrustLevel, AgentType)
   - Align action string validation
   - Update model fields to match policy expectations

2. **Short Term** (Next Sprint):
   - Refactor OPA client to use Pydantic models
   - Add model-policy integration tests
   - Document input/output contracts

3. **Long Term** (Future Sprints):
   - Implement policy deployment pipeline
   - Add automated model-policy alignment checks
   - Create code generation for TypeScript types

With these fixes, the OPA policy implementation will be production-ready and maintainable. The architecture is sound; it just needs better integration with the Gateway models.

---

**Reviewed by:** Engineer 1 (Gateway Models Architect)
**Signature:** `[Architectural Review Complete]`
**Date:** 2024
