"""
Policy enforcement coordinator for home LLM governance.

Coordinates all governance services to make authorization decisions,
following the evaluation order: emergency -> allowlist -> override -> time_rules -> OPA.
"""

import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from sark.models.governance import EnforcementDecision, EnforcementDecisionLog
from sark.services.governance.allowlist import AllowlistService
from sark.services.governance.emergency import EmergencyService
from sark.services.governance.exceptions import EnforcementError
from sark.services.governance.override import OverrideService
from sark.services.governance.time_rules import TimeRulesService

logger = structlog.get_logger()


class EnforcementService:
    """
    Coordinates policy enforcement decisions.

    Evaluation order (first match wins):
    1. Emergency override - if active, allow all
    2. Allowlist - if device/user is allowlisted, allow
    3. Per-request override - if valid override with PIN, allow
    4. Time rules - if time rule blocks, deny
    5. OPA policies - evaluate fine-grained policies

    All decisions are logged for audit purposes.
    """

    def __init__(
        self,
        db: AsyncSession,
        allowlist: AllowlistService,
        time_rules: TimeRulesService,
        emergency: EmergencyService,
        override: OverrideService,
        opa_client: Any | None = None,  # Optional OPA client
    ) -> None:
        """
        Initialize enforcement service.

        Args:
            db: Async database session
            allowlist: Allowlist service instance
            time_rules: Time rules service instance
            emergency: Emergency service instance
            override: Override service instance
            opa_client: Optional OPA client for policy evaluation
        """
        self.db = db
        self.allowlist = allowlist
        self.time_rules = time_rules
        self.emergency = emergency
        self.override = override
        self.opa_client = opa_client

    async def evaluate(
        self,
        request: dict[str, Any],
        *,
        log_decision: bool = True,
    ) -> EnforcementDecision:
        """
        Evaluate request against all policies.

        This is the main entry point for policy evaluation.

        Args:
            request: Request context containing:
                - request_id: Unique request identifier
                - device_ip: Client IP address
                - user_id: Optional user identifier
                - override_pin: Optional PIN for per-request override
                - action: Action being performed
                - resource: Resource being accessed
            log_decision: Whether to log the decision (default True)

        Returns:
            EnforcementDecision with allow/deny and reason

        Raises:
            EnforcementError: If evaluation fails critically
        """
        start_time = time.monotonic()
        request_id = request.get("request_id") or str(uuid4())
        device_ip = request.get("device_ip")
        user_id = request.get("user_id")
        override_pin = request.get("override_pin")

        try:
            # 1. Check emergency override
            decision = await self._check_emergency()
            if decision:
                return await self._finalize_decision(
                    decision, request_id, device_ip, start_time, log_decision
                )

            # 2. Check allowlist (device IP)
            if device_ip:
                decision = await self._check_allowlist(device_ip)
                if decision:
                    return await self._finalize_decision(
                        decision, request_id, device_ip, start_time, log_decision
                    )

            # 3. Check allowlist (user ID)
            if user_id:
                decision = await self._check_allowlist(user_id)
                if decision:
                    return await self._finalize_decision(
                        decision, request_id, device_ip, start_time, log_decision
                    )

            # 4. Check per-request override
            if override_pin:
                decision = await self._check_override(request_id, override_pin)
                if decision:
                    return await self._finalize_decision(
                        decision, request_id, device_ip, start_time, log_decision
                    )

            # 5. Check time rules
            decision = await self._check_time_rules(device_ip)
            if decision and not decision.allowed:
                return await self._finalize_decision(
                    decision, request_id, device_ip, start_time, log_decision
                )

            # 6. Evaluate OPA policies
            decision = await self._check_opa_policies(request)
            return await self._finalize_decision(
                decision, request_id, device_ip, start_time, log_decision
            )

        except Exception as e:
            logger.error(
                "enforcement_evaluation_failed",
                request_id=request_id,
                error=str(e),
            )
            # Fail closed - deny on error
            decision = EnforcementDecision(
                allowed=False,
                reason=f"Policy evaluation error: {e!s}",
                decision_source="error",
            )
            return await self._finalize_decision(
                decision, request_id, device_ip, start_time, log_decision
            )

    async def evaluate_simple(
        self,
        device_ip: str,
        *,
        user_id: str | None = None,
    ) -> bool:
        """
        Simple evaluation returning just allow/deny.

        Convenience method for quick checks.

        Args:
            device_ip: Client IP address
            user_id: Optional user identifier

        Returns:
            True if allowed, False if denied
        """
        decision = await self.evaluate(
            {"device_ip": device_ip, "user_id": user_id},
            log_decision=False,
        )
        return decision.allowed

    async def get_decision_log(
        self,
        *,
        request_id: str | None = None,
        device_ip: str | None = None,
        allowed: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EnforcementDecisionLog]:
        """
        Get enforcement decision log.

        Args:
            request_id: Filter by request ID
            device_ip: Filter by device IP
            allowed: Filter by decision
            limit: Maximum number to return
            offset: Number to skip

        Returns:
            List of decision log entries
        """
        from sqlalchemy import select

        query = select(EnforcementDecisionLog)

        if request_id:
            query = query.where(EnforcementDecisionLog.request_id == request_id)
        if device_ip:
            query = query.where(EnforcementDecisionLog.client_ip == device_ip)
        if allowed is not None:
            query = query.where(EnforcementDecisionLog.allowed == allowed)

        query = query.order_by(EnforcementDecisionLog.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_statistics(
        self,
        *,
        since: datetime | None = None,
    ) -> dict:
        """
        Get enforcement statistics.

        Args:
            since: Start time for statistics (default: last 24 hours)

        Returns:
            Dictionary with statistics
        """
        from datetime import timedelta

        from sqlalchemy import func, select

        if since is None:
            since = datetime.now(UTC) - timedelta(days=1)

        # Total decisions
        total_result = await self.db.execute(
            select(func.count(EnforcementDecisionLog.id)).where(
                EnforcementDecisionLog.created_at >= since
            )
        )
        total = total_result.scalar() or 0

        # Allowed vs denied
        allowed_result = await self.db.execute(
            select(func.count(EnforcementDecisionLog.id)).where(
                EnforcementDecisionLog.created_at >= since,
                EnforcementDecisionLog.allowed == True,  # noqa: E712
            )
        )
        allowed = allowed_result.scalar() or 0

        denied_result = await self.db.execute(
            select(func.count(EnforcementDecisionLog.id)).where(
                EnforcementDecisionLog.created_at >= since,
                EnforcementDecisionLog.allowed == False,  # noqa: E712
            )
        )
        denied = denied_result.scalar() or 0

        # By decision source
        source_stats = {}
        sources = ["emergency", "allowlist", "override", "time_rule", "opa", "error"]
        for source in sources:
            result = await self.db.execute(
                select(func.count(EnforcementDecisionLog.id)).where(
                    EnforcementDecisionLog.created_at >= since,
                    EnforcementDecisionLog.decision_source == source,
                )
            )
            source_stats[source] = result.scalar() or 0

        # Average decision time
        avg_result = await self.db.execute(
            select(func.avg(EnforcementDecisionLog.duration_ms)).where(
                EnforcementDecisionLog.created_at >= since,
                EnforcementDecisionLog.duration_ms.isnot(None),
            )
        )
        avg_duration = avg_result.scalar() or 0

        return {
            "period_start": since.isoformat(),
            "total_decisions": total,
            "allowed": allowed,
            "denied": denied,
            "allow_rate": round(allowed / total * 100, 2) if total > 0 else 0,
            "by_source": source_stats,
            "avg_duration_ms": round(avg_duration, 2),
        }

    # =========================================================================
    # Private evaluation methods
    # =========================================================================

    async def _check_emergency(self) -> EnforcementDecision | None:
        """Check if emergency override is active."""
        if await self.emergency.is_active():
            return EnforcementDecision(
                allowed=True,
                reason="Emergency override active",
                decision_source="emergency",
            )
        return None

    async def _check_allowlist(self, identifier: str) -> EnforcementDecision | None:
        """Check if identifier is in allowlist."""
        if await self.allowlist.is_allowed(identifier):
            return EnforcementDecision(
                allowed=True,
                reason=f"Identifier '{identifier}' is allowlisted",
                decision_source="allowlist",
            )
        return None

    async def _check_override(
        self, request_id: str, pin: str
    ) -> EnforcementDecision | None:
        """Check if valid override exists."""
        if await self.override.validate_override(request_id, pin):
            return EnforcementDecision(
                allowed=True,
                reason="Valid override PIN provided",
                decision_source="override",
            )
        return None

    async def _check_time_rules(
        self, device_ip: str | None
    ) -> EnforcementDecision | None:
        """Check time rules."""
        result = await self.time_rules.check_rules(device_ip=device_ip)

        if result.blocked:
            return EnforcementDecision(
                allowed=False,
                reason=result.reason or "Blocked by time rule",
                decision_source="time_rule",
                rule=result.rule,
            )
        elif result.action == "alert":
            # Alert action - allow but note the rule
            logger.info(
                "time_rule_alert",
                rule=result.rule,
                device_ip=device_ip,
            )

        return None

    async def _check_opa_policies(
        self, request: dict[str, Any]
    ) -> EnforcementDecision:
        """Evaluate OPA policies."""
        if self.opa_client is None:
            # No OPA client - default allow
            return EnforcementDecision(
                allowed=True,
                reason="No policy engine configured",
                decision_source="opa",
            )

        try:
            # Build OPA input
            opa_input = {
                "user": {
                    "id": request.get("user_id"),
                    "ip": request.get("device_ip"),
                },
                "action": request.get("action"),
                "resource": request.get("resource"),
                "context": {
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            }

            # Evaluate policy
            result = await self.opa_client.evaluate_policy(opa_input)

            return EnforcementDecision(
                allowed=result.allow,
                reason=result.reason or "Policy evaluation complete",
                decision_source="opa",
                policy=result.policy if hasattr(result, "policy") else None,
            )

        except Exception as e:
            logger.error("opa_evaluation_failed", error=str(e))
            # Fail closed on OPA errors
            return EnforcementDecision(
                allowed=False,
                reason=f"Policy evaluation error: {e!s}",
                decision_source="opa",
            )

    async def _finalize_decision(
        self,
        decision: EnforcementDecision,
        request_id: str,
        device_ip: str | None,
        start_time: float,
        log_decision: bool,
    ) -> EnforcementDecision:
        """Finalize and optionally log the decision."""
        duration_ms = int((time.monotonic() - start_time) * 1000)

        if log_decision:
            await self._log_decision(
                request_id=request_id,
                client_ip=device_ip,
                decision=decision,
                duration_ms=duration_ms,
            )

        logger.info(
            "enforcement_decision",
            request_id=request_id,
            allowed=decision.allowed,
            reason=decision.reason,
            source=decision.decision_source,
            duration_ms=duration_ms,
        )

        return decision

    async def _log_decision(
        self,
        request_id: str,
        client_ip: str | None,
        decision: EnforcementDecision,
        duration_ms: int,
    ) -> None:
        """Log decision to database."""
        import json

        log_entry = EnforcementDecisionLog(
            request_id=request_id,
            client_ip=client_ip,
            allowed=decision.allowed,
            reason=decision.reason,
            decision_source=decision.decision_source,
            rule_name=decision.rule,
            policy_name=decision.policy,
            duration_ms=duration_ms,
            metadata=json.dumps({}),
        )
        self.db.add(log_entry)
        await self.db.commit()


# =============================================================================
# Factory function
# =============================================================================


def get_enforcement_service(
    db: AsyncSession,
    allowlist: AllowlistService | None = None,
    time_rules: TimeRulesService | None = None,
    emergency: EmergencyService | None = None,
    override: OverrideService | None = None,
    opa_client: Any | None = None,
) -> EnforcementService:
    """
    Get enforcement service instance.

    Creates sub-services if not provided.
    """
    from sark.services.governance.allowlist import AllowlistService
    from sark.services.governance.emergency import EmergencyService
    from sark.services.governance.override import OverrideService
    from sark.services.governance.time_rules import TimeRulesService

    return EnforcementService(
        db=db,
        allowlist=allowlist or AllowlistService(db),
        time_rules=time_rules or TimeRulesService(db),
        emergency=emergency or EmergencyService(db),
        override=override or OverrideService(db),
        opa_client=opa_client,
    )
