"""Home profile test fixtures.

Provides fixtures for integration testing of home deployment profile including:
- Home deployment configuration
- SQLite in-memory database
- Mock services
- Sample data fixtures
"""

from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from sark.models.gateway import (
    AgentContext,
    AgentType,
    GatewayAuthorizationRequest,
    GatewayAuthorizationResponse,
    GatewayServerInfo,
    GatewayToolInfo,
    SensitivityLevel,
    TrustLevel,
)
from sark.services.auth.user_context import UserContext


@dataclass
class HomeDeploymentConfig:
    """Configuration for home deployment testing.

    Attributes:
        mode: Deployment mode (test, observe, enforce)
        database_url: Database connection URL
        opa_mode: OPA mode (embedded, remote)
        enable_cost_tracking: Whether to track costs
        enable_rate_limiting: Whether to enable rate limiting
        daily_budget_usd: Daily budget limit in USD
        monthly_budget_usd: Monthly budget limit in USD
    """

    mode: str = "test"
    database_url: str = "sqlite:///:memory:"
    opa_mode: str = "embedded"
    enable_cost_tracking: bool = True
    enable_rate_limiting: bool = True
    daily_budget_usd: Decimal = Decimal("10.00")
    monthly_budget_usd: Decimal = Decimal("100.00")
    allowed_endpoints: list[str] = field(default_factory=lambda: [
        "api.openai.com",
        "api.anthropic.com",
        "generativelanguage.googleapis.com",
    ])


@dataclass
class HomeDeploymentContext:
    """Context for home deployment integration tests.

    Provides access to all services needed for testing the home
    deployment profile.
    """

    config: HomeDeploymentConfig
    db: Any  # Database session
    authorization: Any  # Authorization service mock
    cost_tracker: Any  # Cost tracker mock
    rate_limiter: Any  # Rate limiter mock
    audit_service: Any  # Audit service mock


@asynccontextmanager
async def home_deployment_context(
    config: HomeDeploymentConfig | None = None,
) -> AsyncGenerator[HomeDeploymentContext, None]:
    """Create a home deployment context for integration testing.

    Args:
        config: Optional deployment configuration

    Yields:
        HomeDeploymentContext with all services initialized

    Example:
        async with home_deployment_context() as ctx:
            result = await ctx.authorization.authorize(request)
            assert result.allow is True
    """
    if config is None:
        config = HomeDeploymentConfig()

    # Create mock services
    mock_db = MagicMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.execute = AsyncMock()

    mock_authorization = MagicMock()
    mock_authorization.authorize = AsyncMock(
        return_value=GatewayAuthorizationResponse(
            allow=True,
            reason="Authorized",
            cache_ttl=300,
        )
    )

    mock_cost_tracker = MagicMock()
    mock_cost_tracker.check_budget_before_invocation = AsyncMock(
        return_value=(True, None)
    )
    mock_cost_tracker.record_invocation_cost = AsyncMock()

    mock_rate_limiter = MagicMock()
    mock_rate_limiter.check_rate_limit = AsyncMock(
        return_value=MagicMock(
            allowed=True,
            limit=1000,
            remaining=999,
            reset_at=0,
        )
    )

    mock_audit_service = MagicMock()
    mock_audit_service.log_decision = AsyncMock()

    context = HomeDeploymentContext(
        config=config,
        db=mock_db,
        authorization=mock_authorization,
        cost_tracker=mock_cost_tracker,
        rate_limiter=mock_rate_limiter,
        audit_service=mock_audit_service,
    )

    try:
        yield context
    finally:
        # Cleanup if needed
        pass


# ============================================================================
# User Fixtures
# ============================================================================


@pytest.fixture
def home_admin_user() -> UserContext:
    """Create admin user for home deployment."""
    return UserContext(
        user_id=uuid4(),
        email="admin@home.local",
        role="admin",
        teams=["home-admins"],
        is_authenticated=True,
        is_admin=True,
    )


@pytest.fixture
def home_parent_user() -> UserContext:
    """Create parent user for home deployment."""
    return UserContext(
        user_id=uuid4(),
        email="parent@home.local",
        role="parent",
        teams=["parents"],
        is_authenticated=True,
        is_admin=False,
    )


@pytest.fixture
def home_child_user() -> UserContext:
    """Create child user for home deployment."""
    return UserContext(
        user_id=uuid4(),
        email="child@home.local",
        role="child",
        teams=["children"],
        is_authenticated=True,
        is_admin=False,
    )


# ============================================================================
# Device Fixtures (Allowlist)
# ============================================================================


@dataclass
class HomeDevice:
    """Represents a device on the home network."""

    device_id: str
    name: str
    ip_address: str
    mac_address: str
    device_type: str  # laptop, phone, tablet, smart_device
    owner: str
    is_allowlisted: bool = True
    daily_budget_usd: Decimal | None = None


@pytest.fixture
def home_devices() -> list[HomeDevice]:
    """Create list of home network devices."""
    return [
        HomeDevice(
            device_id="dev_001",
            name="Dad's Laptop",
            ip_address="192.168.1.100",
            mac_address="AA:BB:CC:DD:EE:01",
            device_type="laptop",
            owner="parent",
            is_allowlisted=True,
        ),
        HomeDevice(
            device_id="dev_002",
            name="Mom's Phone",
            ip_address="192.168.1.101",
            mac_address="AA:BB:CC:DD:EE:02",
            device_type="phone",
            owner="parent",
            is_allowlisted=True,
        ),
        HomeDevice(
            device_id="dev_003",
            name="Kid's Tablet",
            ip_address="192.168.1.102",
            mac_address="AA:BB:CC:DD:EE:03",
            device_type="tablet",
            owner="child",
            is_allowlisted=True,
            daily_budget_usd=Decimal("1.00"),
        ),
        HomeDevice(
            device_id="dev_004",
            name="Smart TV",
            ip_address="192.168.1.150",
            mac_address="AA:BB:CC:DD:EE:04",
            device_type="smart_device",
            owner="shared",
            is_allowlisted=False,  # Not allowed to use LLM APIs
        ),
    ]


# ============================================================================
# Time Rule Fixtures
# ============================================================================


@dataclass
class TimeRule:
    """Represents a time-based access rule."""

    rule_id: str
    name: str
    start_time: str  # HH:MM format
    end_time: str  # HH:MM format
    action: str  # allow, block, alert
    applies_to: list[str]  # Device types or owners
    days_of_week: list[str] = field(
        default_factory=lambda: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    )
    enabled: bool = True


@pytest.fixture
def home_time_rules() -> list[TimeRule]:
    """Create list of home time-based rules."""
    return [
        TimeRule(
            rule_id="rule_001",
            name="Bedtime Block",
            start_time="21:00",
            end_time="07:00",
            action="block",
            applies_to=["child"],
            days_of_week=["Mon", "Tue", "Wed", "Thu", "Sun"],
        ),
        TimeRule(
            rule_id="rule_002",
            name="Weekend Bedtime",
            start_time="22:00",
            end_time="08:00",
            action="block",
            applies_to=["child"],
            days_of_week=["Fri", "Sat"],
        ),
        TimeRule(
            rule_id="rule_003",
            name="Homework Hours Alert",
            start_time="15:00",
            end_time="18:00",
            action="alert",
            applies_to=["child"],
            days_of_week=["Mon", "Tue", "Wed", "Thu", "Fri"],
        ),
    ]


# ============================================================================
# Server and Tool Fixtures
# ============================================================================


@pytest.fixture
def home_servers() -> list[GatewayServerInfo]:
    """Create list of servers for home deployment."""
    return [
        GatewayServerInfo(
            server_id="srv_openai",
            server_name="openai-proxy",
            server_url="http://localhost:8081",
            sensitivity_level=SensitivityLevel.MEDIUM,
            authorized_teams=["parents", "children"],
            health_status="healthy",
            tools_count=3,
        ),
        GatewayServerInfo(
            server_id="srv_anthropic",
            server_name="anthropic-proxy",
            server_url="http://localhost:8082",
            sensitivity_level=SensitivityLevel.MEDIUM,
            authorized_teams=["parents", "children"],
            health_status="healthy",
            tools_count=2,
        ),
        GatewayServerInfo(
            server_id="srv_local_llm",
            server_name="ollama-local",
            server_url="http://localhost:11434",
            sensitivity_level=SensitivityLevel.LOW,
            authorized_teams=["parents", "children", "home-admins"],
            health_status="healthy",
            tools_count=5,
        ),
    ]


@pytest.fixture
def home_tools() -> list[GatewayToolInfo]:
    """Create list of tools for home deployment."""
    return [
        GatewayToolInfo(
            tool_name="chat_completion",
            server_name="openai-proxy",
            description="Send a chat message to GPT",
            sensitivity_level=SensitivityLevel.MEDIUM,
            parameters=[
                {"name": "messages", "type": "array", "required": True},
                {"name": "model", "type": "string", "required": True},
            ],
            required_capabilities=["llm:chat"],
        ),
        GatewayToolInfo(
            tool_name="generate_image",
            server_name="openai-proxy",
            description="Generate an image with DALL-E",
            sensitivity_level=SensitivityLevel.HIGH,  # Higher cost
            parameters=[
                {"name": "prompt", "type": "string", "required": True},
            ],
            required_capabilities=["llm:image"],
        ),
        GatewayToolInfo(
            tool_name="local_chat",
            server_name="ollama-local",
            description="Chat with local LLM (no cost)",
            sensitivity_level=SensitivityLevel.LOW,
            parameters=[
                {"name": "messages", "type": "array", "required": True},
            ],
            required_capabilities=["llm:local"],
        ),
    ]


# ============================================================================
# Request Fixtures
# ============================================================================


@pytest.fixture
def home_chat_request() -> GatewayAuthorizationRequest:
    """Create a typical home chat request."""
    return GatewayAuthorizationRequest(
        action="gateway:tool:invoke",
        server_name="openai-proxy",
        tool_name="chat_completion",
        parameters={
            "messages": [
                {"role": "user", "content": "Help me with my homework"}
            ],
            "model": "gpt-3.5-turbo",
        },
    )


# ============================================================================
# Sample Data for Testing
# ============================================================================


HOME_SAMPLE_PROMPTS = [
    "What is the capital of France?",
    "Help me understand photosynthesis",
    "Write a poem about my cat",
    "Explain quantum physics simply",
    "What are some healthy dinner recipes?",
]

HOME_SAMPLE_ENDPOINTS = [
    "api.openai.com",
    "api.anthropic.com",
    "generativelanguage.googleapis.com",
]


__all__ = [
    "HomeDeploymentConfig",
    "HomeDeploymentContext",
    "home_deployment_context",
    "HomeDevice",
    "TimeRule",
    "HOME_SAMPLE_PROMPTS",
    "HOME_SAMPLE_ENDPOINTS",
]
