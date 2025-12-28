"""
Load test scenarios for authorization workloads.

Defines realistic request patterns for SARK authorization testing.
"""

from dataclasses import dataclass
from typing import ClassVar


@dataclass
class LoadTestScenario:
    """Configuration for a load test scenario."""

    name: str
    description: str
    target_rps: int  # Requests per second
    duration_minutes: int
    users: int
    spawn_rate: int  # Users spawned per second


# ==============================================================================
# Load Test Profiles
# ==============================================================================

BASELINE = LoadTestScenario(
    name="baseline",
    description="Current production baseline load",
    target_rps=100,
    duration_minutes=30,
    users=50,
    spawn_rate=5,
)

TARGET = LoadTestScenario(
    name="target",
    description="v1.4.0 target performance (2,000 req/s)",
    target_rps=2000,
    duration_minutes=30,
    users=1000,
    spawn_rate=100,
)

STRESS = LoadTestScenario(
    name="stress",
    description="Stress test to find breaking point (5,000 req/s)",
    target_rps=5000,
    duration_minutes=10,
    users=2500,
    spawn_rate=250,
)

SPIKE = LoadTestScenario(
    name="spike",
    description="Spike test with sudden traffic increase",
    target_rps=3000,
    duration_minutes=5,
    users=1500,
    spawn_rate=500,  # Rapid spawn
)

SOAK = LoadTestScenario(
    name="soak",
    description="Long-running soak test for stability",
    target_rps=1000,
    duration_minutes=120,  # 2 hours
    users=500,
    spawn_rate=50,
)

# Scenario registry
SCENARIOS = {
    "baseline": BASELINE,
    "target": TARGET,
    "stress": STRESS,
    "spike": SPIKE,
    "soak": SOAK,
}


# ==============================================================================
# Request Distribution Patterns
# ==============================================================================

@dataclass
class RequestPattern:
    """Defines distribution of request types."""

    read_ratio: float  # Common read authorization (60%)
    write_ratio: float  # Write authorization (30%)
    admin_ratio: float  # Admin authorization (10%)

    def __post_init__(self):
        """Validate ratios sum to 1.0."""
        total = self.read_ratio + self.write_ratio + self.admin_ratio
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Ratios must sum to 1.0, got {total}")


STANDARD_PATTERN = RequestPattern(
    read_ratio=0.6,  # 60% reads
    write_ratio=0.3,  # 30% writes
    admin_ratio=0.1,  # 10% admin
)

READ_HEAVY_PATTERN = RequestPattern(
    read_ratio=0.9,  # 90% reads
    write_ratio=0.08,  # 8% writes
    admin_ratio=0.02,  # 2% admin
)

WRITE_HEAVY_PATTERN = RequestPattern(
    read_ratio=0.3,  # 30% reads
    write_ratio=0.6,  # 60% writes
    admin_ratio=0.1,  # 10% admin
)


# ==============================================================================
# User Profiles
# ==============================================================================

@dataclass
class UserProfile:
    """Defines characteristics of a simulated user."""

    user_id_prefix: str
    roles: list[str]
    wait_time_min: float  # Seconds
    wait_time_max: float  # Seconds
    pattern: RequestPattern


VIEWER_PROFILE = UserProfile(
    user_id_prefix="viewer",
    roles=["viewer"],
    wait_time_min=0.1,
    wait_time_max=0.5,
    pattern=READ_HEAVY_PATTERN,
)

EDITOR_PROFILE = UserProfile(
    user_id_prefix="editor",
    roles=["editor", "viewer"],
    wait_time_min=0.2,
    wait_time_max=1.0,
    pattern=WRITE_HEAVY_PATTERN,
)

ADMIN_PROFILE = UserProfile(
    user_id_prefix="admin",
    roles=["admin", "editor", "viewer"],
    wait_time_min=0.5,
    wait_time_max=2.0,
    pattern=RequestPattern(read_ratio=0.4, write_ratio=0.4, admin_ratio=0.2),
)

# Profile registry
USER_PROFILES = {
    "viewer": VIEWER_PROFILE,
    "editor": EDITOR_PROFILE,
    "admin": ADMIN_PROFILE,
}


# ==============================================================================
# Test Data
# ==============================================================================

# Resource patterns for realistic testing
RESOURCES = [
    "document-123",
    "document-456",
    "document-789",
    "project-alpha:document-001",
    "project-beta:document-002",
    "tenant-1:project-42:document-123",
    "system",
    "settings",
    "users",
    "api-keys",
]

# Action patterns
ACTIONS = {
    "read": ["read", "view", "list", "get"],
    "write": ["write", "update", "edit", "modify"],
    "admin": ["admin", "delete", "manage", "configure"],
}


# ==============================================================================
# Performance Targets
# ==============================================================================

@dataclass
class PerformanceTarget:
    """Expected performance targets for validation."""

    throughput_rps: int  # Requests per second
    latency_p50_ms: float  # Median latency
    latency_p95_ms: float  # 95th percentile latency
    latency_p99_ms: float  # 99th percentile latency
    error_rate_max: float  # Maximum acceptable error rate (0.01 = 1%)
    cpu_usage_max: float  # Maximum CPU usage (0.80 = 80%)


BASELINE_TARGETS = PerformanceTarget(
    throughput_rps=100,
    latency_p50_ms=20.0,
    latency_p95_ms=50.0,
    latency_p99_ms=100.0,
    error_rate_max=0.01,
    cpu_usage_max=0.50,
)

V140_TARGETS = PerformanceTarget(
    throughput_rps=2000,
    latency_p50_ms=2.0,  # Rust implementation target
    latency_p95_ms=5.0,  # OPA p95 target
    latency_p99_ms=10.0,
    error_rate_max=0.01,
    cpu_usage_max=0.80,
)

# Target registry
PERFORMANCE_TARGETS = {
    "baseline": BASELINE_TARGETS,
    "v1.4.0": V140_TARGETS,
}
