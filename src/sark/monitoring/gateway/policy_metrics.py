"""Policy evaluation metrics for Gateway."""

from prometheus_client import Counter, Gauge, Histogram

# ============================================================================
# Policy Decision Metrics
# ============================================================================

policy_decisions_total = Counter(
    "sark_policy_decisions_total",
    "Total policy decisions",
    ["policy_name", "decision", "resource_type"],
)

policy_denials_by_reason = Counter(
    "sark_policy_denials_by_reason",
    "Policy denials by reason",
    ["policy_name", "reason"],
)

# ============================================================================
# Policy Evaluation Metrics
# ============================================================================

policy_evaluation_duration_seconds = Histogram(
    "sark_policy_evaluation_duration_seconds",
    "Policy evaluation duration in seconds",
    ["policy_name"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

policy_evaluations_in_progress = Gauge(
    "sark_policy_evaluations_in_progress",
    "Policy evaluations currently in progress",
)

# ============================================================================
# Policy Cache Metrics
# ============================================================================

policy_cache_hits_total = Counter(
    "sark_policy_cache_hits_total",
    "Policy cache hits",
    ["policy_name"],
)

policy_cache_misses_total = Counter(
    "sark_policy_cache_misses_total",
    "Policy cache misses",
    ["policy_name"],
)

policy_cache_size = Gauge(
    "sark_policy_cache_size",
    "Number of cached policy results",
)

policy_cache_ttl_seconds = Gauge(
    "sark_policy_cache_ttl_seconds",
    "Policy cache TTL in seconds",
)

# ============================================================================
# Policy Management Metrics
# ============================================================================

policy_updates_total = Counter(
    "sark_policy_updates_total",
    "Total policy updates",
    ["policy_name", "update_type"],
)

policy_load_errors_total = Counter(
    "sark_policy_load_errors_total",
    "Policy load errors",
    ["policy_name", "error_type"],
)

active_policies = Gauge(
    "sark_active_policies",
    "Number of active policies",
)

policy_compilation_duration_seconds = Histogram(
    "sark_policy_compilation_duration_seconds",
    "Policy compilation duration",
    ["policy_name"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)


class PolicyMetricsCollector:
    """Metrics collector for policy operations."""

    def record_decision(
        self,
        policy_name: str,
        decision: str,
        resource_type: str,
        denial_reason: str | None = None,
    ):
        """
        Record a policy decision.

        Args:
            policy_name: Name of policy
            decision: allow or deny
            resource_type: Type of resource
            denial_reason: Reason for denial (if denied)
        """
        policy_decisions_total.labels(
            policy_name=policy_name,
            decision=decision,
            resource_type=resource_type,
        ).inc()

        if decision == "deny" and denial_reason:
            policy_denials_by_reason.labels(
                policy_name=policy_name,
                reason=denial_reason,
            ).inc()

    def record_evaluation(self, policy_name: str, duration: float):
        """
        Record policy evaluation.

        Args:
            policy_name: Name of policy
            duration: Evaluation duration in seconds
        """
        policy_evaluation_duration_seconds.labels(
            policy_name=policy_name,
        ).observe(duration)

    def record_cache_hit(self, policy_name: str):
        """
        Record policy cache hit.

        Args:
            policy_name: Name of policy
        """
        policy_cache_hits_total.labels(policy_name=policy_name).inc()

    def record_cache_miss(self, policy_name: str):
        """
        Record policy cache miss.

        Args:
            policy_name: Name of policy
        """
        policy_cache_misses_total.labels(policy_name=policy_name).inc()

    def update_cache_size(self, size: int):
        """
        Update policy cache size.

        Args:
            size: Number of cached entries
        """
        policy_cache_size.set(size)

    def update_cache_ttl(self, ttl_seconds: float):
        """
        Update policy cache TTL.

        Args:
            ttl_seconds: TTL in seconds
        """
        policy_cache_ttl_seconds.set(ttl_seconds)

    def record_policy_update(self, policy_name: str, update_type: str):
        """
        Record policy update.

        Args:
            policy_name: Name of policy
            update_type: create, update, delete
        """
        policy_updates_total.labels(
            policy_name=policy_name,
            update_type=update_type,
        ).inc()

    def record_load_error(self, policy_name: str, error_type: str):
        """
        Record policy load error.

        Args:
            policy_name: Name of policy
            error_type: Type of error
        """
        policy_load_errors_total.labels(
            policy_name=policy_name,
            error_type=error_type,
        ).inc()

    def update_active_policies(self, count: int):
        """
        Update active policy count.

        Args:
            count: Number of active policies
        """
        active_policies.set(count)

    def record_compilation(self, policy_name: str, duration: float):
        """
        Record policy compilation.

        Args:
            policy_name: Name of policy
            duration: Compilation duration in seconds
        """
        policy_compilation_duration_seconds.labels(
            policy_name=policy_name,
        ).observe(duration)


# Global instance
_collector = PolicyMetricsCollector()


# Convenience functions
def record_policy_decision(
    policy_name: str,
    decision: str,
    resource_type: str,
    denial_reason: str | None = None,
):
    """Record a policy decision."""
    _collector.record_decision(policy_name, decision, resource_type, denial_reason)


def record_policy_evaluation(policy_name: str, duration: float):
    """Record policy evaluation."""
    _collector.record_evaluation(policy_name, duration)
