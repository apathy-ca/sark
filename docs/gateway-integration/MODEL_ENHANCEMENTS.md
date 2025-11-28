# Gateway Model Enhancements

**Author:** Engineer 1 (Gateway Models Architect)
**Date:** 2024
**Version:** 1.0
**Status:** Recommendations based on cross-team code review

---

## Executive Summary

After reviewing implementations from Engineers 2, 3, and 4, this document proposes enhancements to the Gateway data models to address integration gaps, improve type safety, and support production requirements discovered during the review process.

**Key Finding:** All three implementations created **parallel data structures** instead of using the shared Gateway models, indicating the models need to be more complete and easier to integrate.

---

## 1. Missing Model Fields

### 1.1 GatewayServerInfo Enhancements

**Problem:** Engineer 3's OPA policies expect fields that don't exist in the model.

**Current Model:**
```python
class GatewayServerInfo(BaseModel):
    server_id: str
    server_name: str
    server_url: HttpUrl
    sensitivity_level: SensitivityLevel
    authorized_teams: list[str] = Field(default_factory=list)
    access_restrictions: dict[str, Any] | None = None
    health_status: str
    tools_count: int = Field(ge=0)
```

**Proposed Enhancements:**
```python
class GatewayServerInfo(BaseModel):
    """MCP Server metadata for Gateway registry."""

    # Existing fields
    server_id: str
    server_name: str
    server_url: HttpUrl
    sensitivity_level: SensitivityLevel

    # ENHANCEMENTS:
    owner_id: str | None = None                    # ADD: Server owner for policy checks
    managed_by_team: str | None = None             # ADD: Primary team for team-based access
    authorized_teams: list[str] = Field(default_factory=list)
    visibility: str = "internal"                   # ADD: public/internal/private
    environment: str = "production"                # ADD: dev/staging/production

    access_restrictions: dict[str, Any] | None = None
    health_status: str
    tools_count: int = Field(ge=0)

    # Additional metadata
    description: str | None = None                 # ADD: Human-readable description
    tags: list[str] = Field(default_factory=list)  # ADD: Categorization tags
    created_at: int | None = None                  # ADD: Unix timestamp
    updated_at: int | None = None                  # ADD: Unix timestamp
```

**Rationale:**
- `owner_id`, `managed_by_team`, `visibility`, `environment` required by OPA policies
- Enables team-based and ownership-based access control
- Supports multi-environment deployments

---

### 1.2 AgentContext Enhancements

**Problem:** Engineer 3's A2A policies expect fields not in the model.

**Current Model:**
```python
class AgentContext(BaseModel):
    agent_id: str
    agent_type: AgentType
    trust_level: TrustLevel
    capabilities: list[str] = Field(default_factory=list)
    environment: str
    rate_limited: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
```

**Proposed Enhancements:**
```python
class AgentContext(BaseModel):
    """Agent context for A2A authorization."""

    # Existing fields
    agent_id: str
    agent_type: AgentType
    trust_level: TrustLevel
    capabilities: list[str] = Field(default_factory=list)
    environment: str

    # ENHANCEMENTS:
    organization_id: str | None = None              # ADD: For cross-org checks
    accepts_execution: bool = True                  # ADD: Can execute tasks
    accepts_queries: bool = True                    # ADD: Can answer queries
    accepts_delegation: bool = False                # ADD: Can receive delegated work
    rate_limit_per_minute: int = 100                # ADD: Rate limiting threshold

    rate_limited: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
```

**Rationale:**
- Required by A2A authorization policies
- Enables capability-based access control
- Supports rate limiting enforcement

---

### 1.3 GatewayAuditEvent Enhancements

**Problem:** Engineer 4's audit system needs additional context fields.

**Current Model:**
```python
class GatewayAuditEvent(BaseModel):
    event_type: str
    user_id: str | None = None
    agent_id: str | None = None
    server_name: str | None = None
    tool_name: str | None = None
    decision: str
    reason: str
    timestamp: int
    gateway_request_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)
```

**Proposed Enhancements:**
```python
class GatewayAuditEvent(BaseModel):
    """Audit event for Gateway operations."""

    # Existing fields
    event_type: str
    user_id: str | None = None
    agent_id: str | None = None
    server_name: str | None = None
    tool_name: str | None = None
    decision: str
    reason: str
    timestamp: int
    gateway_request_id: str

    # ENHANCEMENTS:
    sensitivity_level: SensitivityLevel | None = None  # ADD: For alert routing
    client_ip: str | None = None                       # ADD: Source IP
    session_id: str | None = None                      # ADD: Session correlation
    mfa_verified: bool | None = None                   # ADD: Security context
    policy_id: str | None = None                       # ADD: Which policy evaluated
    evaluation_duration_ms: float | None = None        # ADD: Performance tracking

    metadata: dict[str, Any] = Field(default_factory=dict)
```

**Rationale:**
- Enables severity-based alert routing in monitoring systems
- Provides security context for compliance auditing
- Supports performance monitoring and optimization

---

## 2. Enum Value Corrections

### 2.1 TrustLevel Enum Fix

**Problem:** OPA policies use `"verified"` but model defines `"limited"`.

**Current:**
```python
class TrustLevel(str, Enum):
    TRUSTED = "trusted"
    LIMITED = "limited"      # ❌ Doesn't match policy expectations
    UNTRUSTED = "untrusted"
```

**Proposed Fix:**
```python
class TrustLevel(str, Enum):
    """Agent trust level for A2A authorization."""
    TRUSTED = "trusted"      # Fully trusted agents
    VERIFIED = "verified"    # ✅ Verified agents (renamed from LIMITED)
    UNTRUSTED = "untrusted"  # Untrusted agents
```

**Migration Path:**
- Update all references from `TrustLevel.LIMITED` → `TrustLevel.VERIFIED`
- Add deprecation warning for "limited" in v1.x
- Remove "limited" support in v2.0

---

### 2.2 AgentType Enum Expansion

**Problem:** OPA policies expect `"orchestrator"` and `"monitor"` types.

**Current:**
```python
class AgentType(str, Enum):
    SERVICE = "service"
    WORKER = "worker"
    QUERY = "query"          # ❌ Unused in policies
```

**Proposed Fix:**
```python
class AgentType(str, Enum):
    """Agent type classification."""
    SERVICE = "service"           # Service agents
    WORKER = "worker"             # Worker agents
    ORCHESTRATOR = "orchestrator" # ✅ ADD: Orchestrator agents
    MONITOR = "monitor"           # ✅ ADD: Monitoring agents
    # Remove QUERY or clarify its purpose
```

**Rationale:**
- Aligns with OPA policy agent type checks
- Supports orchestration patterns in A2A communication

---

## 3. Action String Validation Updates

### 3.1 GatewayAuthorizationRequest Action Expansion

**Problem:** OPA policies use action strings not in the validator.

**Current Validator:**
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

**Proposed Fix:**
```python
@field_validator('action')
@classmethod
def validate_action(cls, v: str) -> str:
    valid_actions = [
        # Tool operations
        'gateway:tool:invoke',
        'gateway:tool:discover',
        'gateway:tools:list',        # ✅ ADD: Plural variant

        # Server operations
        'gateway:server:list',
        'gateway:server:info',
        'gateway:server:register',   # ✅ ADD: Server registration
        'gateway:servers:list',      # ✅ ADD: Plural variant

        # Audit operations
        'gateway:audit:view',        # ✅ ADD: Audit access
    ]
    if v not in valid_actions:
        raise ValueError(f"Action must be one of {valid_actions}")
    return v
```

---

### 3.2 A2AAuthorizationRequest Action Validation

**Problem:** No action validation exists for A2A requests.

**Current Model:**
```python
class A2AAuthorizationRequest(BaseModel):
    source_agent_id: str
    target_agent_id: str
    capability: str
    message_type: str
    payload_metadata: dict[str, Any] = Field(default_factory=dict)
```

**Proposed Enhancement:**
```python
class A2AAuthorizationRequest(BaseModel):
    """Agent-to-Agent authorization request."""

    source_agent: AgentContext     # ✅ Full context instead of just ID
    target_agent: AgentContext     # ✅ Full context instead of just ID
    action: str                    # ✅ ADD: Standardized action string
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

**Rationale:**
- Aligns with OPA policy structure
- Provides full agent context for policy evaluation
- Adds action validation for safety

---

## 4. Additional Helper Methods

### 4.1 GatewayServerInfo Helper Methods

**Proposed Additions:**
```python
class GatewayServerInfo(BaseModel):
    # ... fields ...

    def is_accessible_by(self, user_teams: list[str]) -> bool:
        """Check if user's teams can access this server."""
        if self.visibility == "public":
            return True
        return bool(set(user_teams) & set(self.authorized_teams))

    def is_production(self) -> bool:
        """Check if this is a production server."""
        return self.environment == "production"

    def requires_high_security(self) -> bool:
        """Check if server requires elevated security controls."""
        return self.sensitivity_level in [
            SensitivityLevel.HIGH,
            SensitivityLevel.CRITICAL
        ]
```

---

### 4.2 GatewayToolInfo Helper Methods

**Proposed Additions:**
```python
class GatewayToolInfo(BaseModel):
    # ... fields ...

    def filter_parameters(
        self,
        params: dict[str, Any]
    ) -> dict[str, Any]:
        """Filter out sensitive parameters before logging."""
        filtered = {}
        for key, value in params.items():
            if key in self.sensitive_params:
                filtered[key] = "***REDACTED***"
            else:
                filtered[key] = value
        return filtered

    def has_required_capabilities(
        self,
        user_capabilities: list[str]
    ) -> bool:
        """Check if user has all required capabilities."""
        required = set(self.required_capabilities)
        user_caps = set(user_capabilities)
        return required.issubset(user_caps)

    def is_critical(self) -> bool:
        """Check if tool is critical sensitivity."""
        return self.sensitivity_level == SensitivityLevel.CRITICAL
```

---

### 4.3 AgentContext Helper Methods

**Proposed Additions:**
```python
class AgentContext(BaseModel):
    # ... fields ...

    def can_communicate_with(
        self,
        target: "AgentContext"
    ) -> bool:
        """Check if this agent can communicate with target."""
        # Same environment check
        if self.environment != target.environment:
            return False

        # Trust level compatibility
        if self.trust_level == TrustLevel.UNTRUSTED:
            return False

        return True

    def is_rate_limit_exceeded(
        self,
        current_count: int
    ) -> bool:
        """Check if rate limit is exceeded."""
        return current_count >= self.rate_limit_per_minute

    def has_capability(self, capability: str) -> bool:
        """Check if agent has specific capability."""
        return capability in self.capabilities
```

---

## 5. New Supporting Models

### 5.1 UserContext Model

**Problem:** Engineers 2 and 3 both create ad-hoc user context dicts.

**Proposed New Model:**
```python
class UserContext(BaseModel):
    """User context for authorization decisions."""

    id: str
    email: str | None = None
    role: str  # Consider making this an enum
    teams: list[str] = Field(default_factory=list)
    team_manager_of: list[str] = Field(default_factory=list)
    environment: str = "production"
    mfa_verified: bool = False
    capabilities: list[str] = Field(default_factory=list)

    def is_team_member(self, team_id: str) -> bool:
        """Check if user is member of team."""
        return team_id in self.teams

    def is_team_manager(self, team_id: str) -> bool:
        """Check if user manages team."""
        return team_id in self.team_manager_of
```

---

### 5.2 GatewayPolicyContext Model

**Problem:** Context dicts passed to OPA are unstructured.

**Proposed New Model:**
```python
class GatewayPolicyContext(BaseModel):
    """Context for Gateway policy evaluation."""

    timestamp: int = Field(default_factory=lambda: int(time.time()))
    environment: str = "production"
    client_ip: str | None = None
    emergency_override: bool = False
    emergency_reason: str | None = None
    emergency_approver: str | None = None
    audit_enabled: bool = True

    @field_validator('emergency_override')
    @classmethod
    def validate_emergency(cls, v: bool, info) -> bool:
        """Ensure emergency overrides have reason and approver."""
        if v:
            if not info.data.get('emergency_reason'):
                raise ValueError("Emergency override requires reason")
            if not info.data.get('emergency_approver'):
                raise ValueError("Emergency override requires approver")
        return v
```

---

### 5.3 RateLimitInfo Model

**Proposed New Model:**
```python
class RateLimitInfo(BaseModel):
    """Rate limiting information for A2A communication."""

    current_count: int = Field(ge=0)
    window_start: int  # Unix timestamp
    limit: int = Field(gt=0)
    window_duration_seconds: int = Field(default=60, gt=0)

    def is_exceeded(self) -> bool:
        """Check if rate limit is exceeded."""
        return self.current_count >= self.limit

    def remaining(self) -> int:
        """Calculate remaining requests."""
        return max(0, self.limit - self.current_count)

    def reset_in_seconds(self, current_time: int) -> int:
        """Calculate seconds until rate limit resets."""
        elapsed = current_time - self.window_start
        return max(0, self.window_duration_seconds - elapsed)
```

---

## 6. Cross-Field Validation

### 6.1 GatewayAuthorizationRequest Validation

**Proposed Enhancement:**
```python
class GatewayAuthorizationRequest(BaseModel):
    # ... fields ...

    @model_validator(mode='after')
    def validate_resource_specified(self) -> Self:
        """Ensure at least one resource is specified."""
        if not self.server_name and not self.tool_name:
            raise ValueError(
                "At least one of server_name or tool_name must be specified"
            )
        return self

    @model_validator(mode='after')
    def validate_tool_requires_server(self) -> Self:
        """Ensure tool invocations specify server."""
        if self.action == 'gateway:tool:invoke' and not self.server_name:
            raise ValueError(
                "Tool invocation requires server_name to be specified"
            )
        return self
```

---

### 6.2 AgentContext Trust Level Validation

**Proposed Enhancement:**
```python
class AgentContext(BaseModel):
    # ... fields ...

    @model_validator(mode='after')
    def validate_untrusted_restrictions(self) -> Self:
        """Enforce restrictions on untrusted agents."""
        if self.trust_level == TrustLevel.UNTRUSTED:
            if self.accepts_execution:
                raise ValueError(
                    "Untrusted agents cannot accept execution"
                )
            if self.accepts_delegation:
                raise ValueError(
                    "Untrusted agents cannot accept delegation"
                )
        return self
```

---

## 7. Performance Optimizations

### 7.1 Model Caching

**Proposed:**
```python
from functools import lru_cache

class GatewayServerInfo(BaseModel):
    # ... fields ...

    model_config = ConfigDict(
        frozen=True,  # Make immutable for caching
    )

    @lru_cache(maxsize=1)
    def get_authorized_teams_set(self) -> frozenset[str]:
        """Get authorized teams as frozen set for fast lookups."""
        return frozenset(self.authorized_teams)
```

---

### 7.2 Lazy Validation

**Proposed:**
```python
class GatewayToolInfo(BaseModel):
    # ... fields ...

    _parameter_validation_cache: dict[str, bool] | None = None

    def validate_parameters_lazy(
        self,
        params: dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """Lazy parameter validation with caching."""
        if self._parameter_validation_cache is None:
            self._parameter_validation_cache = {}

        # Validation logic...
        return (is_valid, errors)
```

---

## 8. Breaking Changes & Migration

### 8.1 Breaking Changes

The following enhancements are **breaking changes** requiring a major version bump:

1. **TrustLevel.LIMITED → TrustLevel.VERIFIED**
   - Migration: Global find/replace
   - Deprecation period: 2 releases

2. **A2AAuthorizationRequest structure change**
   - Migration: Update all A2A authorization call sites
   - Provide compatibility shim for 1 release

3. **user_id type change (UUID → str)**
   - Migration: Database migration + application code update
   - No compatibility shim possible

### 8.2 Migration Guide

```python
# OLD (v1.x):
from sark.models.gateway import TrustLevel

agent = AgentContext(
    agent_id="agent1",
    trust_level=TrustLevel.LIMITED,  # Old
    # ...
)

# NEW (v2.x):
from sark.models.gateway import TrustLevel

agent = AgentContext(
    agent_id="agent1",
    trust_level=TrustLevel.VERIFIED,  # New
    # ...
)
```

---

## 9. Implementation Priority

### High Priority (Must Have for Production)

1. ✅ Add missing fields to `GatewayServerInfo` (owner_id, managed_by_team, visibility)
2. ✅ Add missing fields to `AgentContext` (accepts_*, rate_limit_per_minute)
3. ✅ Fix `TrustLevel.LIMITED` → `TrustLevel.VERIFIED`
4. ✅ Expand `AgentType` enum (add ORCHESTRATOR, MONITOR)
5. ✅ Expand action validation in `GatewayAuthorizationRequest`

### Medium Priority (Should Have for Production)

6. ✅ Create `UserContext` model
7. ✅ Create `GatewayPolicyContext` model
8. ✅ Add helper methods to existing models
9. ✅ Add cross-field validation

### Low Priority (Nice to Have)

10. ✅ Performance optimizations (caching, lazy validation)
11. ✅ Create `RateLimitInfo` model
12. ✅ Additional helper methods

---

## 10. Testing Requirements

### 10.1 Model Integration Tests

```python
def test_gateway_authorization_request_to_opa_input():
    """Test that GatewayAuthorizationRequest maps to OPA input."""
    request = GatewayAuthorizationRequest(
        action="gateway:tool:invoke",
        server_name="postgres-mcp",
        tool_name="execute_query",
        parameters={"query": "SELECT 1"},
        gateway_metadata={"timestamp": 0}
    )

    # Should not raise validation errors
    assert request.action == "gateway:tool:invoke"
    assert request.server_name == "postgres-mcp"
```

### 10.2 Enum Compatibility Tests

```python
@pytest.mark.parametrize("sensitivity", [
    SensitivityLevel.LOW,
    SensitivityLevel.MEDIUM,
    SensitivityLevel.HIGH,
    SensitivityLevel.CRITICAL,
])
def test_all_sensitivity_levels_supported_in_policies(sensitivity):
    """Ensure OPA policies handle all SensitivityLevel enum values."""
    # Test each enum value works in policies
    pass
```

---

## 11. Documentation Updates Required

After implementing these enhancements:

1. **Update MODELS_GUIDE.md** with new fields and methods
2. **Update API documentation** (OpenAPI spec) with new models
3. **Create migration guide** for breaking changes
4. **Update integration examples** to show new patterns
5. **Document model-policy alignment** in contracts document

---

## Conclusion

These enhancements address the integration gaps discovered during cross-team code review. The recommendations prioritize:

1. **Completeness**: Add missing fields required by OPA policies and audit systems
2. **Type Safety**: Fix enum mismatches and add validation
3. **Usability**: Add helper methods to reduce boilerplate
4. **Performance**: Optimize for production workloads

Implementing High Priority items will enable successful integration of all four engineer's work.

---

**Next Steps:**
1. Review this document with team
2. Approve breaking changes (requires v2.0)
3. Create implementation tickets
4. Update models on `feat/gateway-client` branch
5. Coordinate with Engineers 2, 3, 4 to adopt changes
