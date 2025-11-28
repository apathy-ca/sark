# Extending the Gateway: Advanced Customization

**Level:** Expert
**Time:** 3-4 hours
**Prerequisites:**
- [Tutorial 1: Quick Start Guide](./01-quickstart-guide.md)
- [Tutorial 2: Building a Gateway Server](./02-building-gateway-server.md)
- [Tutorial 3: Production Deployment](./03-production-deployment.md)
- OPA/Rego experience (intermediate)
- Python experience (advanced)

---

## Overview

In this advanced tutorial, you'll extend your Gateway with enterprise features and custom capabilities. You'll learn:

- 🎨 **Custom Tool Types**: Create new tool categories with specialized handling
- 📜 **Advanced OPA Policies**: Trust levels, delegation chains, and time-based controls
- 🔌 **Authentication Plugins**: Build custom authentication providers (OAuth2, LDAP, mTLS)
- ⚡ **Performance Tuning**: Optimize for 50,000+ requests per second
- 🔧 **Custom Middleware**: Implement rate limiting, circuit breakers, and request transformation
- 📊 **Advanced Auditing**: Custom audit events and SIEM integration

By the end, you'll have a highly customized Gateway that:
- Supports custom authentication methods
- Enforces complex multi-level policies
- Handles specialized tool types
- Performs at scale under extreme load
- Provides enterprise-grade observability

---

## Part 1: Custom Tool Types

### Overview: What are Tool Types?

Tool types categorize MCP tools by their behavior and security requirements:

- **Query Tools**: Read-only data access (SELECT, GET)
- **Mutation Tools**: Data modification (INSERT, UPDATE, DELETE)
- **Admin Tools**: System administration (CREATE TABLE, GRANT)
- **Custom Types**: Your specialized categories

### Step 1.1: Define Custom Tool Type Registry

Create `src/mcp/tool_registry.py`:

```python
"""Custom tool type registry with extensible classification."""

from enum import Enum
from typing import Any, Callable

import structlog

logger = structlog.get_logger()


class ToolSensitivityLevel(str, Enum):
    """Sensitivity levels for tools."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ToolType(str, Enum):
    """Built-in tool types."""

    QUERY = "query"
    MUTATION = "mutation"
    ADMIN = "admin"
    ANALYTICS = "analytics"
    INTEGRATION = "integration"
    CUSTOM = "custom"


class ToolClassifier:
    """Classifies tools based on their characteristics."""

    def __init__(self):
        self.classifiers: dict[str, Callable[[str, dict], ToolType]] = {
            "sql": self._classify_sql_tool,
            "api": self._classify_api_tool,
            "file": self._classify_file_tool,
            "k8s": self._classify_k8s_tool,
        }
        self.sensitivity_rules: dict[ToolType, ToolSensitivityLevel] = {
            ToolType.QUERY: ToolSensitivityLevel.LOW,
            ToolType.ANALYTICS: ToolSensitivityLevel.LOW,
            ToolType.MUTATION: ToolSensitivityLevel.MEDIUM,
            ToolType.INTEGRATION: ToolSensitivityLevel.MEDIUM,
            ToolType.ADMIN: ToolSensitivityLevel.CRITICAL,
        }

    def classify_tool(
        self, tool_name: str, parameters: dict[str, Any], server_type: str
    ) -> tuple[ToolType, ToolSensitivityLevel]:
        """
        Classify a tool and determine its sensitivity level.

        Args:
            tool_name: Name of the tool
            parameters: Tool parameters
            server_type: Type of server (sql, api, file, k8s)

        Returns:
            Tuple of (ToolType, ToolSensitivityLevel)
        """
        classifier = self.classifiers.get(server_type)
        if not classifier:
            logger.warning(
                "unknown_server_type",
                server_type=server_type,
                defaulting_to_custom=True,
            )
            return ToolType.CUSTOM, ToolSensitivityLevel.HIGH

        tool_type = classifier(tool_name, parameters)
        sensitivity = self._determine_sensitivity(tool_type, parameters)

        logger.info(
            "tool_classified",
            tool_name=tool_name,
            tool_type=tool_type,
            sensitivity=sensitivity,
        )

        return tool_type, sensitivity

    def _classify_sql_tool(
        self, tool_name: str, parameters: dict
    ) -> ToolType:
        """Classify SQL-based tools."""
        query = parameters.get("query", "").lower()

        # Admin operations
        if any(
            keyword in query
            for keyword in ["create", "drop", "alter", "grant", "revoke"]
        ):
            return ToolType.ADMIN

        # Mutation operations
        if any(
            keyword in query
            for keyword in ["insert", "update", "delete", "truncate"]
        ):
            return ToolType.MUTATION

        # Analytics operations
        if any(
            keyword in query
            for keyword in ["group by", "having", "window", "aggregate"]
        ):
            return ToolType.ANALYTICS

        # Default: query
        return ToolType.QUERY

    def _classify_api_tool(
        self, tool_name: str, parameters: dict
    ) -> ToolType:
        """Classify API-based tools."""
        method = parameters.get("method", "GET").upper()

        if method in ["POST", "PUT", "PATCH", "DELETE"]:
            return ToolType.MUTATION

        return ToolType.QUERY

    def _classify_file_tool(
        self, tool_name: str, parameters: dict
    ) -> ToolType:
        """Classify file system tools."""
        if "write" in tool_name or "delete" in tool_name:
            return ToolType.MUTATION

        if "read" in tool_name or "list" in tool_name:
            return ToolType.QUERY

        return ToolType.CUSTOM

    def _classify_k8s_tool(
        self, tool_name: str, parameters: dict
    ) -> ToolType:
        """Classify Kubernetes tools."""
        if any(
            keyword in tool_name
            for keyword in ["create", "delete", "scale", "restart"]
        ):
            return ToolType.ADMIN

        if any(keyword in tool_name for keyword in ["get", "list", "describe"]):
            return ToolType.QUERY

        return ToolType.MUTATION

    def _determine_sensitivity(
        self, tool_type: ToolType, parameters: dict
    ) -> ToolSensitivityLevel:
        """
        Determine sensitivity level based on tool type and parameters.

        Can be customized with additional rules.
        """
        base_sensitivity = self.sensitivity_rules.get(
            tool_type, ToolSensitivityLevel.MEDIUM
        )

        # Elevate sensitivity for production environments
        if parameters.get("environment") == "production":
            if base_sensitivity == ToolSensitivityLevel.MEDIUM:
                return ToolSensitivityLevel.HIGH
            elif base_sensitivity == ToolSensitivityLevel.HIGH:
                return ToolSensitivityLevel.CRITICAL

        # Elevate for operations on sensitive tables/resources
        sensitive_resources = ["users", "credentials", "secrets", "keys"]
        query = str(parameters.get("query", "")).lower()
        resource = str(parameters.get("resource", "")).lower()

        if any(res in query or res in resource for res in sensitive_resources):
            return ToolSensitivityLevel.HIGH

        return base_sensitivity

    def register_custom_classifier(
        self, server_type: str, classifier: Callable[[str, dict], ToolType]
    ):
        """Register a custom tool classifier for a server type."""
        self.classifiers[server_type] = classifier
        logger.info(
            "custom_classifier_registered", server_type=server_type
        )


# Global instance
tool_classifier = ToolClassifier()
```

### Step 1.2: Integrate with Gateway Authorization

Update `src/routers/tools.py` to use tool classification:

```python
from src.mcp.tool_registry import tool_classifier

@router.post("/invoke", response_model=ToolInvocationResponse)
async def invoke_tool(
    request: ToolInvocationRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> ToolInvocationResponse:
    """Invoke a tool with custom type classification."""
    user = validate_jwt_token(credentials)
    server = mcp_registry.get_server(request.server_name)

    # Classify tool
    tool_type, sensitivity = tool_classifier.classify_tool(
        tool_name=request.tool_name,
        parameters=request.parameters,
        server_type=server.metadata.get("server_type", "custom"),
    )

    # Request authorization with tool classification
    auth_response = await sark_client.authorize_tool_invocation(
        user=user,
        server_name=request.server_name,
        tool_name=request.tool_name,
        parameters=request.parameters,
        gateway_metadata={
            "tool_type": tool_type,
            "sensitivity_level": sensitivity,
            "gateway_version": "1.1.0",
        },
    )

    # ... rest of implementation
```

### Step 1.3: Update OPA Policy for Tool Types

Update `policies/gateway.rego`:

```rego
package mcp.gateway

import future.keywords.if
import future.keywords.in

# ============================================================================
# Tool Type Based Authorization
# ============================================================================

# Admins can use all tool types except critical in production
allow if {
    input.user.roles[_] == "admin"
    input.action == "gateway:tool:invoke"
    input.gateway_metadata.sensitivity_level != "critical"
}

# Admins can use critical tools with approval
allow if {
    input.user.roles[_] == "admin"
    input.action == "gateway:tool:invoke"
    input.gateway_metadata.sensitivity_level == "critical"
    input.gateway_metadata.approval_token != null
    verify_approval_token(input.gateway_metadata.approval_token)
}

# Developers can use query and analytics tools
allow if {
    input.user.roles[_] == "developer"
    input.action == "gateway:tool:invoke"
    input.gateway_metadata.tool_type in ["query", "analytics"]
    input.gateway_metadata.sensitivity_level in ["low", "medium"]
}

# Analysts can only use analytics tools
allow if {
    input.user.roles[_] == "analyst"
    input.action == "gateway:tool:invoke"
    input.gateway_metadata.tool_type == "analytics"
    input.gateway_metadata.sensitivity_level in ["low", "medium"]
}

# Data engineers can use mutation tools with restrictions
allow if {
    input.user.roles[_] == "data_engineer"
    input.action == "gateway:tool:invoke"
    input.gateway_metadata.tool_type in ["query", "mutation", "analytics"]
    input.gateway_metadata.sensitivity_level != "critical"
    not is_production_environment(input)
}

# Helper: verify approval token
verify_approval_token(token) if {
    # In production, integrate with approval system API
    token != ""
}

is_production_environment(input) if {
    input.parameters.environment == "production"
}
```

---

## Part 2: Advanced OPA Policies

### Step 2.1: Trust Levels and Delegation

Create `policies/trust_delegation.rego`:

```rego
package mcp.gateway.trust

import future.keywords.if
import future.keywords.in

# ============================================================================
# Trust Level Hierarchy
# ============================================================================

# Trust levels: critical > high > medium > low > untrusted
trust_hierarchy := {
    "critical": 5,
    "high": 4,
    "medium": 3,
    "low": 2,
    "untrusted": 1,
}

# User trust level based on role and tenure
user_trust_level(user) := level if {
    user.roles[_] == "admin"
    user.tenure_months >= 12
    level := "critical"
} else := level if {
    user.roles[_] == "admin"
    level := "high"
} else := level if {
    user.roles[_] in ["developer", "data_engineer"]
    user.tenure_months >= 6
    level := "high"
} else := level if {
    user.roles[_] in ["developer", "data_engineer"]
    level := "medium"
} else := level if {
    user.roles[_] == "analyst"
    level := "low"
} else := "untrusted" if {
    true  # Default
}

# ============================================================================
# Delegation Authorization
# ============================================================================

# Allow delegation if source trust >= target trust
allow_delegation if {
    input.action == "a2a:delegate"
    source_level := user_trust_level(input.source_user)
    target_level := user_trust_level(input.target_user)
    trust_hierarchy[source_level] >= trust_hierarchy[target_level]
    input.delegation_depth < max_delegation_depth(source_level)
}

# Maximum delegation depth based on trust level
max_delegation_depth(level) := depth if {
    level == "critical"
    depth := 5
} else := depth if {
    level == "high"
    depth := 3
} else := depth if {
    level == "medium"
    depth := 2
} else := 1 if {
    true  # Default
}

# ============================================================================
# Time-Based Access Control
# ============================================================================

# Work hours: 9 AM - 5 PM UTC
is_work_hours if {
    now := time.now_ns()
    hour := time.clock(now)[0]
    hour >= 9
    hour < 17
}

# Weekend check
is_weekend if {
    now := time.now_ns()
    day := time.weekday(now)
    day in ["Saturday", "Sunday"]
}

# Critical operations only during work hours
allow_critical_during_work_hours if {
    input.gateway_metadata.sensitivity_level == "critical"
    is_work_hours
    not is_weekend
}

# Deny critical operations outside work hours
deny contains msg if {
    input.gateway_metadata.sensitivity_level == "critical"
    not is_work_hours
    msg := "Critical operations only allowed during work hours (9 AM - 5 PM UTC)"
}

deny contains msg if {
    input.gateway_metadata.sensitivity_level == "critical"
    is_weekend
    msg := "Critical operations not allowed on weekends"
}
```

### Step 2.2: Context-Aware Policies

Create `policies/context_aware.rego`:

```rego
package mcp.gateway.context

import future.keywords.if
import future.keywords.in

# ============================================================================
# Geographic Restrictions
# ============================================================================

allowed_regions := {
    "us-east-1",
    "us-west-2",
    "eu-west-1",
}

# Deny access from restricted regions
deny contains msg if {
    input.gateway_metadata.source_region
    not input.gateway_metadata.source_region in allowed_regions
    msg := sprintf(
        "Access denied from region: %s. Allowed regions: %v",
        [input.gateway_metadata.source_region, allowed_regions]
    )
}

# ============================================================================
# Rate Limiting via Policy
# ============================================================================

# User request history (in production, fetch from Redis)
user_request_count(user_id, window_seconds) := count if {
    # Placeholder: integrate with Redis to get actual count
    # redis_key := sprintf("rate_limit:%s:%d", [user_id, window_seconds])
    # count := redis.get(redis_key)
    count := 0
}

# Rate limit exceeded
rate_limit_exceeded if {
    user_id := input.user.id
    request_count := user_request_count(user_id, 60)  # per minute
    max_requests := user_rate_limit(input.user)
    request_count >= max_requests
}

# Rate limit based on role
user_rate_limit(user) := limit if {
    user.roles[_] == "admin"
    limit := 1000  # 1000 req/min
} else := limit if {
    user.roles[_] in ["developer", "data_engineer"]
    limit := 500  # 500 req/min
} else := 100 if {
    true  # Default: 100 req/min
}

deny contains msg if {
    rate_limit_exceeded
    msg := sprintf(
        "Rate limit exceeded: %d requests/min allowed",
        [user_rate_limit(input.user)]
    )
}

# ============================================================================
# Data Residency and Compliance
# ============================================================================

# GDPR: Restrict EU data access to EU regions
deny contains msg if {
    input.parameters.data_region == "eu"
    input.gateway_metadata.source_region
    not startswith(input.gateway_metadata.source_region, "eu-")
    msg := "GDPR violation: EU data can only be accessed from EU regions"
}

# HIPAA: Require encryption for health data
deny contains msg if {
    input.server_name == "healthcare-mcp"
    input.gateway_metadata.encryption_enabled != true
    msg := "HIPAA violation: Encryption required for healthcare data access"
}

# ============================================================================
# Conditional Access
# ============================================================================

# Require MFA for high-sensitivity operations
deny contains msg if {
    input.gateway_metadata.sensitivity_level in ["high", "critical"]
    input.user.mfa_verified != true
    msg := "MFA required for high-sensitivity operations"
}

# Require device compliance for critical operations
deny contains msg if {
    input.gateway_metadata.sensitivity_level == "critical"
    input.gateway_metadata.device_compliant != true
    msg := "Device compliance check required for critical operations"
}
```

### Step 2.3: Testing Advanced Policies

Create `policies/test_advanced.sh`:

```bash
#!/bin/bash

# Test trust delegation
echo "Testing trust delegation..."
opa eval -d policies/ \
  -i - <<EOF | jq '.result[0].expressions[0].value'
{
  "input": {
    "action": "a2a:delegate",
    "source_user": {
      "id": "user_123",
      "roles": ["admin"],
      "tenure_months": 24
    },
    "target_user": {
      "id": "user_456",
      "roles": ["developer"],
      "tenure_months": 6
    },
    "delegation_depth": 1
  }
}
EOF

# Test time-based restrictions
echo "Testing time-based restrictions..."
opa eval -d policies/ \
  -i - <<EOF | jq '.result[0].expressions[0].value'
{
  "input": {
    "action": "gateway:tool:invoke",
    "gateway_metadata": {
      "sensitivity_level": "critical"
    }
  }
}
EOF

# Test geographic restrictions
echo "Testing geographic restrictions..."
opa eval -d policies/ \
  -i - <<EOF | jq '.result[0].expressions[0].value'
{
  "input": {
    "action": "gateway:tool:invoke",
    "gateway_metadata": {
      "source_region": "cn-north-1"
    }
  }
}
EOF
```

---

## Part 3: Custom Authentication Providers

### Step 3.1: Plugin Architecture

Create `src/auth/plugins/__init__.py`:

```python
"""Authentication plugin architecture."""

from abc import ABC, abstractmethod
from typing import Any

from src.auth.jwt_handler import UserContext


class AuthenticationProvider(ABC):
    """Base class for authentication providers."""

    @abstractmethod
    async def authenticate(self, credentials: dict[str, Any]) -> UserContext:
        """
        Authenticate user and return user context.

        Args:
            credentials: Authentication credentials (varies by provider)

        Returns:
            UserContext with user information

        Raises:
            AuthenticationError: If authentication fails
        """
        pass

    @abstractmethod
    async def validate(self, token: str) -> UserContext:
        """
        Validate an existing token/session.

        Args:
            token: Token or session identifier

        Returns:
            UserContext with user information

        Raises:
            AuthenticationError: If validation fails
        """
        pass


class AuthenticationError(Exception):
    """Authentication failed."""

    pass
```

### Step 3.2: OAuth2 Provider Plugin

Create `src/auth/plugins/oauth2_provider.py`:

```python
"""OAuth2 authentication provider."""

import httpx
import structlog

from src.auth.jwt_handler import UserContext
from src.auth.plugins import AuthenticationError, AuthenticationProvider
from src.config import get_settings

logger = structlog.get_logger()


class OAuth2Provider(AuthenticationProvider):
    """OAuth2/OIDC authentication provider."""

    def __init__(
        self,
        issuer: str,
        client_id: str,
        client_secret: str,
        scopes: list[str] | None = None,
    ):
        self.issuer = issuer
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes or ["openid", "profile", "email"]
        self.client = httpx.AsyncClient()

        # Discover OIDC endpoints
        self.discovery_url = f"{issuer}/.well-known/openid-configuration"

    async def authenticate(
        self, credentials: dict[str, str]
    ) -> UserContext:
        """
        Authenticate via OAuth2 authorization code flow.

        Args:
            credentials: {"code": "auth_code", "redirect_uri": "..."}

        Returns:
            UserContext
        """
        try:
            # Exchange authorization code for tokens
            token_endpoint = await self._get_token_endpoint()

            response = await self.client.post(
                token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": credentials["code"],
                    "redirect_uri": credentials["redirect_uri"],
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            response.raise_for_status()
            tokens = response.json()

            # Get user info
            userinfo = await self._get_userinfo(tokens["access_token"])

            logger.info(
                "oauth2_authentication_success",
                user_id=userinfo["sub"],
                email=userinfo.get("email"),
            )

            return UserContext(
                user_id=userinfo["sub"],
                email=userinfo.get("email", ""),
                roles=userinfo.get("roles", []),
                teams=userinfo.get("teams", []),
            )

        except httpx.HTTPError as e:
            logger.error("oauth2_authentication_failed", error=str(e))
            raise AuthenticationError(f"OAuth2 authentication failed: {e}")

    async def validate(self, token: str) -> UserContext:
        """
        Validate OAuth2 access token.

        Args:
            token: OAuth2 access token

        Returns:
            UserContext
        """
        try:
            # Validate token via introspection endpoint
            introspection_endpoint = await self._get_introspection_endpoint()

            response = await self.client.post(
                introspection_endpoint,
                data={
                    "token": token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            response.raise_for_status()
            result = response.json()

            if not result.get("active"):
                raise AuthenticationError("Token is not active")

            # Get user info
            userinfo = await self._get_userinfo(token)

            return UserContext(
                user_id=userinfo["sub"],
                email=userinfo.get("email", ""),
                roles=userinfo.get("roles", []),
                teams=userinfo.get("teams", []),
            )

        except httpx.HTTPError as e:
            logger.error("oauth2_validation_failed", error=str(e))
            raise AuthenticationError(f"OAuth2 validation failed: {e}")

    async def _get_token_endpoint(self) -> str:
        """Discover token endpoint from OIDC discovery."""
        response = await self.client.get(self.discovery_url)
        response.raise_for_status()
        config = response.json()
        return config["token_endpoint"]

    async def _get_introspection_endpoint(self) -> str:
        """Discover introspection endpoint."""
        response = await self.client.get(self.discovery_url)
        response.raise_for_status()
        config = response.json()
        return config["introspection_endpoint"]

    async def _get_userinfo(self, access_token: str) -> dict:
        """Get user info from userinfo endpoint."""
        response = await self.client.get(self.discovery_url)
        response.raise_for_status()
        config = response.json()

        userinfo_endpoint = config["userinfo_endpoint"]

        response = await self.client.get(
            userinfo_endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()
```

### Step 3.3: LDAP Provider Plugin

Create `src/auth/plugins/ldap_provider.py`:

```python
"""LDAP authentication provider."""

import ldap3
import structlog

from src.auth.jwt_handler import UserContext
from src.auth.plugins import AuthenticationError, AuthenticationProvider

logger = structlog.get_logger()


class LDAPProvider(AuthenticationProvider):
    """LDAP/Active Directory authentication provider."""

    def __init__(
        self,
        server_url: str,
        base_dn: str,
        user_search_filter: str = "(uid={username})",
        group_search_filter: str = "(member={user_dn})",
    ):
        self.server_url = server_url
        self.base_dn = base_dn
        self.user_search_filter = user_search_filter
        self.group_search_filter = group_search_filter
        self.server = ldap3.Server(server_url)

    async def authenticate(
        self, credentials: dict[str, str]
    ) -> UserContext:
        """
        Authenticate via LDAP bind.

        Args:
            credentials: {"username": "...", "password": "..."}

        Returns:
            UserContext
        """
        username = credentials.get("username")
        password = credentials.get("password")

        if not username or not password:
            raise AuthenticationError(
                "Username and password required"
            )

        try:
            # Search for user DN
            search_conn = ldap3.Connection(self.server, auto_bind=True)
            search_filter = self.user_search_filter.format(
                username=ldap3.utils.conv.escape_filter_chars(username)
            )

            search_conn.search(
                search_base=self.base_dn,
                search_filter=search_filter,
                attributes=["uid", "mail", "cn"],
            )

            if not search_conn.entries:
                raise AuthenticationError(f"User not found: {username}")

            user_entry = search_conn.entries[0]
            user_dn = user_entry.entry_dn

            # Attempt bind with user credentials
            auth_conn = ldap3.Connection(
                self.server, user=user_dn, password=password
            )

            if not auth_conn.bind():
                raise AuthenticationError("Invalid credentials")

            # Get user groups
            groups = self._get_user_groups(auth_conn, user_dn)

            logger.info(
                "ldap_authentication_success",
                username=username,
                groups=groups,
            )

            return UserContext(
                user_id=str(user_entry.uid),
                email=str(user_entry.mail),
                roles=groups,
                teams=[],
            )

        except ldap3.core.exceptions.LDAPException as e:
            logger.error("ldap_authentication_failed", error=str(e))
            raise AuthenticationError(f"LDAP authentication failed: {e}")

    async def validate(self, token: str) -> UserContext:
        """LDAP doesn't use tokens; not implemented."""
        raise NotImplementedError(
            "LDAP provider doesn't support token validation"
        )

    def _get_user_groups(
        self, conn: ldap3.Connection, user_dn: str
    ) -> list[str]:
        """Get groups for user."""
        search_filter = self.group_search_filter.format(user_dn=user_dn)

        conn.search(
            search_base=self.base_dn,
            search_filter=search_filter,
            attributes=["cn"],
        )

        return [str(entry.cn) for entry in conn.entries]
```

### Step 3.4: mTLS Provider Plugin

Create `src/auth/plugins/mtls_provider.py`:

```python
"""Mutual TLS authentication provider."""

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import NameOID

import structlog

from src.auth.jwt_handler import UserContext
from src.auth.plugins import AuthenticationError, AuthenticationProvider

logger = structlog.get_logger()


class MTLSProvider(AuthenticationProvider):
    """Mutual TLS (mTLS) authentication provider."""

    def __init__(
        self,
        ca_cert_path: str,
        allowed_organizations: list[str] | None = None,
    ):
        self.ca_cert_path = ca_cert_path
        self.allowed_organizations = allowed_organizations or []

        # Load CA certificate
        with open(ca_cert_path, "rb") as f:
            self.ca_cert = x509.load_pem_x509_certificate(
                f.read(), default_backend()
            )

    async def authenticate(
        self, credentials: dict[str, str]
    ) -> UserContext:
        """
        Authenticate via client certificate.

        Args:
            credentials: {"client_cert_pem": "..."}

        Returns:
            UserContext
        """
        cert_pem = credentials.get("client_cert_pem")
        if not cert_pem:
            raise AuthenticationError("Client certificate required")

        try:
            # Parse client certificate
            client_cert = x509.load_pem_x509_certificate(
                cert_pem.encode(), default_backend()
            )

            # Verify certificate is signed by our CA
            # (In production, use full chain verification)
            # client_cert.verify(self.ca_cert.public_key())

            # Extract user information from certificate
            subject = client_cert.subject

            common_name = subject.get_attributes_for_oid(
                NameOID.COMMON_NAME
            )[0].value
            email_attr = subject.get_attributes_for_oid(
                NameOID.EMAIL_ADDRESS
            )
            email = email_attr[0].value if email_attr else ""
            org_attr = subject.get_attributes_for_oid(
                NameOID.ORGANIZATION_NAME
            )
            organization = org_attr[0].value if org_attr else ""

            # Check organization whitelist
            if self.allowed_organizations and organization not in self.allowed_organizations:
                raise AuthenticationError(
                    f"Organization not allowed: {organization}"
                )

            # Extract roles from certificate extensions (custom OID)
            roles = self._extract_roles_from_cert(client_cert)

            logger.info(
                "mtls_authentication_success",
                common_name=common_name,
                email=email,
                organization=organization,
            )

            return UserContext(
                user_id=common_name,
                email=email,
                roles=roles,
                teams=[organization],
            )

        except Exception as e:
            logger.error("mtls_authentication_failed", error=str(e))
            raise AuthenticationError(f"mTLS authentication failed: {e}")

    async def validate(self, token: str) -> UserContext:
        """mTLS uses certificates, not tokens."""
        raise NotImplementedError(
            "mTLS provider doesn't support token validation"
        )

    def _extract_roles_from_cert(
        self, cert: x509.Certificate
    ) -> list[str]:
        """
        Extract roles from certificate extensions.

        In production, define a custom OID for roles.
        """
        # Placeholder: parse custom extension
        # Example: 1.2.3.4.5.6 = roles extension OID
        try:
            # ext = cert.extensions.get_extension_for_oid(
            #     x509.ObjectIdentifier("1.2.3.4.5.6")
            # )
            # roles = parse_roles_from_extension(ext.value)
            # return roles
            return ["developer"]  # Placeholder
        except x509.ExtensionNotFound:
            return []
```

### Step 3.5: Plugin Registry

Create `src/auth/plugin_registry.py`:

```python
"""Authentication plugin registry."""

import structlog

from src.auth.plugins import AuthenticationProvider
from src.auth.plugins.oauth2_provider import OAuth2Provider
from src.auth.plugins.ldap_provider import LDAPProvider
from src.auth.plugins.mtls_provider import MTLSProvider

logger = structlog.get_logger()


class AuthPluginRegistry:
    """Registry for authentication plugins."""

    def __init__(self):
        self.providers: dict[str, AuthenticationProvider] = {}

    def register(
        self, name: str, provider: AuthenticationProvider
    ):
        """Register an authentication provider."""
        self.providers[name] = provider
        logger.info("auth_provider_registered", name=name)

    def get(self, name: str) -> AuthenticationProvider | None:
        """Get authentication provider by name."""
        return self.providers.get(name)

    def list(self) -> list[str]:
        """List all registered providers."""
        return list(self.providers.keys())


# Global registry
auth_registry = AuthPluginRegistry()

# Register built-in providers
# auth_registry.register("oauth2", OAuth2Provider(...))
# auth_registry.register("ldap", LDAPProvider(...))
# auth_registry.register("mtls", MTLSProvider(...))
```

---

## Part 4: Performance Optimization

### Step 4.1: Connection Pooling

Create `src/performance/connection_pool.py`:

```python
"""Connection pool management for high performance."""

import asyncio
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


class ConnectionPoolManager:
    """Manages connection pools for external services."""

    def __init__(
        self,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        keepalive_expiry: float = 30.0,
    ):
        self.limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
        )

        self.clients: dict[str, httpx.AsyncClient] = {}

    def get_client(self, base_url: str) -> httpx.AsyncClient:
        """Get or create HTTP client for base URL."""
        if base_url not in self.clients:
            self.clients[base_url] = httpx.AsyncClient(
                base_url=base_url,
                limits=self.limits,
                timeout=httpx.Timeout(10.0),
            )
            logger.info(
                "http_client_created",
                base_url=base_url,
                max_connections=self.limits.max_connections,
            )

        return self.clients[base_url]

    async def close_all(self):
        """Close all HTTP clients."""
        for base_url, client in self.clients.items():
            await client.aclose()
            logger.info("http_client_closed", base_url=base_url)


# Global pool manager
pool_manager = ConnectionPoolManager(
    max_connections=200,
    max_keepalive_connections=50,
    keepalive_expiry=60.0,
)
```

### Step 4.2: Request Batching

Create `src/performance/request_batcher.py`:

```python
"""Request batching for improved throughput."""

import asyncio
from collections import defaultdict
from typing import Any, Callable

import structlog

logger = structlog.get_logger()


class RequestBatcher:
    """
    Batches multiple authorization requests into single OPA calls.

    Reduces OPA overhead when handling burst traffic.
    """

    def __init__(
        self,
        max_batch_size: int = 100,
        max_wait_ms: int = 10,
    ):
        self.max_batch_size = max_batch_size
        self.max_wait_ms = max_wait_ms
        self.pending: dict[str, list[dict]] = defaultdict(list)
        self.batch_locks: dict[str, asyncio.Lock] = {}

    async def batch_execute(
        self,
        batch_key: str,
        request: dict[str, Any],
        executor: Callable[[list[dict]], list[Any]],
    ) -> Any:
        """
        Execute request as part of a batch.

        Args:
            batch_key: Key to group requests (e.g., "opa_evaluation")
            request: Individual request
            executor: Function that executes batch of requests

        Returns:
            Result for this specific request
        """
        # Get or create lock for this batch key
        if batch_key not in self.batch_locks:
            self.batch_locks[batch_key] = asyncio.Lock()

        lock = self.batch_locks[batch_key]

        async with lock:
            # Add request to pending batch
            self.pending[batch_key].append(request)
            batch = self.pending[batch_key]

            # Execute batch if size reached or timeout
            if len(batch) >= self.max_batch_size:
                results = await self._execute_batch(
                    batch_key, batch, executor
                )
                return results[len(results) - 1]

            # Wait for more requests (with timeout)
            try:
                await asyncio.sleep(self.max_wait_ms / 1000)
            except asyncio.CancelledError:
                pass

            # Execute whatever we have
            batch = self.pending[batch_key]
            results = await self._execute_batch(
                batch_key, batch, executor
            )

            # Return result for this request
            request_index = batch.index(request)
            return results[request_index]

    async def _execute_batch(
        self,
        batch_key: str,
        batch: list[dict],
        executor: Callable[[list[dict]], list[Any]],
    ) -> list[Any]:
        """Execute batch and clear pending."""
        logger.info(
            "batch_execution",
            batch_key=batch_key,
            batch_size=len(batch),
        )

        results = await executor(batch)

        # Clear this batch
        self.pending[batch_key] = []

        return results
```

### Step 4.3: Caching Strategy

Create `src/performance/cache_strategy.py`:

```python
"""Advanced caching strategies for authorization decisions."""

import hashlib
import json
from typing import Any

import structlog

logger = structlog.get_logger()


class CacheKeyGenerator:
    """Generates cache keys for authorization requests."""

    @staticmethod
    def generate(
        user_id: str,
        action: str,
        server_name: str,
        tool_name: str,
        parameters: dict[str, Any],
    ) -> str:
        """
        Generate cache key for authorization decision.

        Uses hash of request components for consistent caching.
        """
        # Serialize parameters (sorted for consistency)
        params_str = json.dumps(parameters, sort_keys=True)

        # Create composite key
        composite = f"{user_id}:{action}:{server_name}:{tool_name}:{params_str}"

        # Hash for fixed-length key
        cache_key = hashlib.sha256(composite.encode()).hexdigest()

        return f"authz:{cache_key}"


class AdaptiveCacheTTL:
    """Dynamically adjust cache TTL based on request patterns."""

    def __init__(self):
        self.hit_rates: dict[str, float] = {}

    def get_ttl(
        self,
        cache_key: str,
        base_ttl: int = 60,
        sensitivity_level: str = "medium",
    ) -> int:
        """
        Calculate adaptive TTL based on hit rate and sensitivity.

        Args:
            cache_key: Cache key
            base_ttl: Base TTL in seconds
            sensitivity_level: Sensitivity level (low/medium/high/critical)

        Returns:
            Calculated TTL in seconds
        """
        # Reduce TTL for high-sensitivity operations
        sensitivity_multiplier = {
            "low": 2.0,
            "medium": 1.0,
            "high": 0.5,
            "critical": 0.1,
        }

        multiplier = sensitivity_multiplier.get(sensitivity_level, 1.0)

        # Increase TTL for frequently accessed keys
        hit_rate = self.hit_rates.get(cache_key, 0.0)
        if hit_rate > 0.9:
            multiplier *= 1.5
        elif hit_rate > 0.7:
            multiplier *= 1.2

        calculated_ttl = int(base_ttl * multiplier)

        logger.debug(
            "adaptive_ttl_calculated",
            cache_key=cache_key[:16],
            sensitivity=sensitivity_level,
            hit_rate=hit_rate,
            ttl=calculated_ttl,
        )

        return calculated_ttl

    def record_hit(self, cache_key: str):
        """Record cache hit for key."""
        current = self.hit_rates.get(cache_key, 0.0)
        # Exponential moving average
        self.hit_rates[cache_key] = current * 0.9 + 1.0 * 0.1

    def record_miss(self, cache_key: str):
        """Record cache miss for key."""
        current = self.hit_rates.get(cache_key, 0.0)
        self.hit_rates[cache_key] = current * 0.9
```

### Step 4.4: Circuit Breaker

Create `src/middleware/circuit_breaker.py`:

```python
"""Circuit breaker for external service calls."""

import asyncio
from datetime import datetime, timedelta
from enum import Enum

import structlog

logger = structlog.get_logger()


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker pattern for resilient external calls.

    Prevents cascading failures when downstream service is unhealthy.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.state = CircuitState.CLOSED

    async def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection.

        Args:
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
        """
        # Check if circuit should transition to half-open
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info("circuit_breaker_half_open")
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError(
                    "Circuit breaker is OPEN"
                )

        try:
            result = await func(*args, **kwargs)

            # Success: reset failure count
            if self.state == CircuitState.HALF_OPEN:
                logger.info("circuit_breaker_closed")
                self.state = CircuitState.CLOSED

            self.failure_count = 0
            return result

        except self.expected_exception as e:
            # Failure: increment counter
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()

            logger.warning(
                "circuit_breaker_failure",
                failure_count=self.failure_count,
                error=str(e),
            )

            # Open circuit if threshold exceeded
            if self.failure_count >= self.failure_threshold:
                logger.error("circuit_breaker_open")
                self.state = CircuitState.OPEN

            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if not self.last_failure_time:
            return True

        time_since_failure = datetime.utcnow() - self.last_failure_time
        return time_since_failure >= timedelta(
            seconds=self.recovery_timeout
        )


class CircuitBreakerOpenError(Exception):
    """Circuit breaker is open."""

    pass
```

---

## Part 5: Advanced Auditing

### Step 5.1: Custom Audit Events

Create `src/audit/custom_events.py`:

```python
"""Custom audit event types for advanced tracking."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    """Custom audit event types."""

    TOOL_INVOCATION = "tool_invocation"
    AUTHORIZATION_DECISION = "authorization_decision"
    POLICY_VIOLATION = "policy_violation"
    DELEGATION_REQUEST = "delegation_request"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    DATA_ACCESS = "data_access"
    ADMIN_ACTION = "admin_action"


class AuditEvent(BaseModel):
    """Base audit event."""

    event_id: str = Field(..., description="Unique event ID")
    event_type: AuditEventType = Field(..., description="Event type")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Event timestamp"
    )
    user_id: str | None = Field(None, description="User ID")
    source_ip: str | None = Field(None, description="Source IP address")
    user_agent: str | None = Field(None, description="User agent")
    session_id: str | None = Field(None, description="Session ID")


class ToolInvocationEvent(AuditEvent):
    """Tool invocation audit event."""

    event_type: AuditEventType = Field(
        default=AuditEventType.TOOL_INVOCATION
    )
    server_name: str = Field(..., description="MCP server name")
    tool_name: str = Field(..., description="Tool name")
    tool_type: str | None = Field(None, description="Tool type")
    sensitivity_level: str | None = Field(
        None, description="Sensitivity level"
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Tool parameters"
    )
    result: Any = Field(None, description="Tool result")
    duration_ms: int | None = Field(None, description="Duration in ms")


class PolicyViolationEvent(AuditEvent):
    """Policy violation audit event."""

    event_type: AuditEventType = Field(
        default=AuditEventType.POLICY_VIOLATION
    )
    policy_name: str = Field(..., description="Violated policy name")
    violation_reason: str = Field(
        ..., description="Reason for violation"
    )
    attempted_action: str = Field(
        ..., description="Attempted action"
    )
    resource: str = Field(..., description="Affected resource")
    severity: str = Field(..., description="Violation severity")


class SuspiciousActivityEvent(AuditEvent):
    """Suspicious activity audit event."""

    event_type: AuditEventType = Field(
        default=AuditEventType.SUSPICIOUS_ACTIVITY
    )
    activity_type: str = Field(..., description="Type of activity")
    indicators: list[str] = Field(
        default_factory=list, description="Indicators of suspicious behavior"
    )
    risk_score: float = Field(..., description="Risk score (0.0 - 1.0)")
    automated_response: str | None = Field(
        None, description="Automated response taken"
    )
```

### Step 5.2: SIEM Integration

Create `src/audit/siem_forwarder.py`:

```python
"""SIEM integration for forwarding audit events."""

import asyncio
from collections import defaultdict

import httpx
import structlog

from src.audit.custom_events import AuditEvent

logger = structlog.get_logger()


class SIEMForwarder:
    """Forwards audit events to SIEM systems."""

    def __init__(
        self,
        siem_url: str,
        api_key: str,
        batch_size: int = 100,
        flush_interval_seconds: int = 30,
    ):
        self.siem_url = siem_url
        self.api_key = api_key
        self.batch_size = batch_size
        self.flush_interval_seconds = flush_interval_seconds

        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_key}"}
        )

        self.pending_events: list[AuditEvent] = []
        self.flush_task: asyncio.Task | None = None

    async def forward(self, event: AuditEvent):
        """
        Forward audit event to SIEM.

        Events are batched for efficiency.
        """
        self.pending_events.append(event)

        # Flush if batch size reached
        if len(self.pending_events) >= self.batch_size:
            await self._flush()

        # Start periodic flush task if not running
        if not self.flush_task or self.flush_task.done():
            self.flush_task = asyncio.create_task(
                self._periodic_flush()
            )

    async def _flush(self):
        """Flush pending events to SIEM."""
        if not self.pending_events:
            return

        events_to_send = self.pending_events[:]
        self.pending_events = []

        try:
            # Convert events to SIEM format
            siem_events = [
                self._convert_to_siem_format(event)
                for event in events_to_send
            ]

            # Send to SIEM
            response = await self.client.post(
                f"{self.siem_url}/api/events",
                json={"events": siem_events},
            )
            response.raise_for_status()

            logger.info(
                "siem_events_forwarded", count=len(siem_events)
            )

        except httpx.HTTPError as e:
            logger.error(
                "siem_forward_failed",
                error=str(e),
                event_count=len(events_to_send),
            )

            # Re-add events to pending (with limit)
            self.pending_events = (
                events_to_send[:1000] + self.pending_events
            )

    async def _periodic_flush(self):
        """Periodically flush events."""
        while True:
            await asyncio.sleep(self.flush_interval_seconds)
            await self._flush()

    def _convert_to_siem_format(
        self, event: AuditEvent
    ) -> dict:
        """Convert audit event to SIEM-compatible format."""
        return {
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type,
            "user_id": event.user_id,
            "source_ip": event.source_ip,
            "data": event.model_dump(exclude={"event_id"}),
        }

    async def close(self):
        """Close SIEM forwarder."""
        # Flush remaining events
        await self._flush()

        # Cancel flush task
        if self.flush_task and not self.flush_task.done():
            self.flush_task.cancel()

        await self.client.aclose()
```

---

## What You Learned

Congratulations on completing this advanced tutorial! You've mastered:

✅ **Custom Tool Types**: Extensible classification system for specialized tools
✅ **Advanced OPA Policies**: Trust levels, delegation, time-based, and geographic controls
✅ **Authentication Plugins**: OAuth2, LDAP, mTLS providers with plugin architecture
✅ **Performance Optimization**: Connection pooling, batching, caching, circuit breakers
✅ **Advanced Auditing**: Custom events, SIEM integration, compliance tracking

You can now build:
- Highly customized Gateway implementations
- Complex multi-level authorization policies
- Pluggable authentication systems
- High-performance, scalable deployments
- Enterprise-grade audit and compliance systems

---

## Next Steps

### Apply to Real-World Scenarios
- Integrate with your existing IdP (Okta, Auth0, Azure AD)
- Define custom tool types for your domain
- Write policies for your compliance requirements
- Optimize for your specific traffic patterns

### Contribute Back
- Share custom plugins with the community
- Contribute OPA policy examples
- Document performance optimizations
- Help others in discussions

---

## Resources

- **[OPA Policy Language](https://www.openpolicyagent.org/docs/latest/policy-language/)**
- **[Performance Tuning Guide](../../PERFORMANCE_TUNING.md)**
- **[Security Best Practices](../../SECURITY_BEST_PRACTICES.md)**
- **[API Reference](../../gateway-integration/API_REFERENCE.md)**

---

*Last Updated: 2025-01-15*
*SARK Version: 1.1.0+*
*Tutorial Version: 1.0*
