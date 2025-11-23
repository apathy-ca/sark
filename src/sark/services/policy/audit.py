"""Policy audit service for logging decisions and tracking changes.

This service provides comprehensive audit trail functionality including:
- Policy decision logging
- Policy change tracking with versioning
- Analytics and reporting
- Export capabilities (CSV, JSON)
"""

import csv
import hashlib
import io
import json
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sark.models.policy_audit import (
    PolicyAnalyticsSummary,
    PolicyChangeLog,
    PolicyChangeType,
    PolicyDecisionLog,
    PolicyDecisionResult,
)
from sark.services.policy.opa_client import AuthorizationInput, AuthorizationDecision

logger = structlog.get_logger(__name__)


class PolicyAuditService:
    """Service for policy audit trail and analytics."""

    def __init__(self, db_session: AsyncSession):
        """Initialize audit service.

        Args:
            db_session: Database session for audit logging
        """
        self.db = db_session
        self.logger = logger.bind(service="policy_audit")

    # ========================================================================
    # POLICY DECISION LOGGING
    # ========================================================================

    async def log_decision(
        self,
        auth_input: AuthorizationInput,
        decision: AuthorizationDecision,
        duration_ms: Optional[float] = None,
        cache_hit: bool = False,
        request_context: Optional[Dict[str, Any]] = None,
    ) -> PolicyDecisionLog:
        """Log a policy evaluation decision.

        Args:
            auth_input: Authorization input that was evaluated
            decision: Policy decision result
            duration_ms: Evaluation duration in milliseconds
            cache_hit: Whether this was a cache hit
            request_context: Additional request context (IP, request ID, etc.)

        Returns:
            Created policy decision log entry
        """
        try:
            # Determine result
            if decision.allow:
                result = PolicyDecisionResult.ALLOW
            else:
                result = PolicyDecisionResult.DENY

            # Extract user info
            user_id = auth_input.user.get("id", "unknown")
            user_role = auth_input.user.get("role")
            user_teams = auth_input.user.get("teams", [])

            # Extract tool info
            tool_info = auth_input.tool or {}
            tool_id = tool_info.get("id")
            tool_name = tool_info.get("name")
            sensitivity_level = tool_info.get("sensitivity_level")

            # Extract server info
            server_info = auth_input.server or {}
            server_id = server_info.get("id")
            server_name = server_info.get("name")

            # Extract request context
            context = request_context or {}
            client_ip = context.get("client_ip") or auth_input.context.get("client_ip")
            request_id = context.get("request_id") or auth_input.context.get("request_id")
            session_id = context.get("session_id")

            # Extract MFA context
            mfa_verified = auth_input.user.get("mfa_verified", False)
            mfa_methods = auth_input.user.get("mfa_methods", [])
            mfa_method = mfa_methods[0] if mfa_methods else None

            # Extract advanced policy results
            policy_results = getattr(decision, "policy_results", {})
            time_based_allowed = (
                policy_results.get("time_based", {}).get("allow")
                if policy_results
                else None
            )
            ip_filtering_allowed = (
                policy_results.get("ip_filtering", {}).get("allow")
                if policy_results
                else None
            )
            mfa_required_satisfied = (
                policy_results.get("mfa_required", {}).get("allow")
                if policy_results
                else None
            )

            # Determine resource type
            resource_type = None
            resource_id = None
            if "server" in auth_input.action:
                resource_type = "server"
                resource_id = server_id
            elif "tool" in auth_input.action:
                resource_type = "tool"
                resource_id = tool_id

            # Create log entry
            log_entry = PolicyDecisionLog(
                timestamp=datetime.now(UTC),
                result=result,
                allow=decision.allow,
                user_id=user_id,
                user_role=user_role,
                user_teams=user_teams,
                action=auth_input.action,
                resource_type=resource_type,
                resource_id=resource_id,
                tool_id=tool_id,
                tool_name=tool_name,
                sensitivity_level=sensitivity_level,
                server_id=server_id,
                server_name=server_name,
                policies_evaluated=getattr(decision, "policies_evaluated", []),
                policy_results=policy_results,
                violations=getattr(decision, "violations", []),
                reason=decision.reason,
                denial_reason=decision.reason if not decision.allow else None,
                evaluation_duration_ms=duration_ms,
                cache_hit=cache_hit,
                client_ip=client_ip,
                request_id=request_id,
                session_id=session_id,
                mfa_verified=mfa_verified,
                mfa_method=mfa_method,
                time_based_allowed=time_based_allowed,
                ip_filtering_allowed=ip_filtering_allowed,
                mfa_required_satisfied=mfa_required_satisfied,
            )

            self.db.add(log_entry)
            await self.db.commit()
            await self.db.refresh(log_entry)

            self.logger.info(
                "policy_decision_logged",
                log_id=str(log_entry.id),
                result=result.value,
                user_id=user_id,
                action=auth_input.action,
                duration_ms=duration_ms,
            )

            return log_entry

        except Exception as e:
            await self.db.rollback()
            self.logger.error(
                "failed_to_log_policy_decision",
                error=str(e),
                user_id=auth_input.user.get("id"),
                action=auth_input.action,
            )
            raise

    # ========================================================================
    # POLICY CHANGE TRACKING
    # ========================================================================

    async def log_policy_change(
        self,
        policy_name: str,
        change_type: PolicyChangeType,
        changed_by_user_id: str,
        policy_content: Optional[str] = None,
        previous_content: Optional[str] = None,
        change_reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PolicyChangeLog:
        """Log a policy change for versioning and compliance.

        Args:
            policy_name: Name of the policy
            change_type: Type of change (created, updated, etc.)
            changed_by_user_id: User ID who made the change
            policy_content: Full policy content (Rego code)
            previous_content: Previous version content for diff
            change_reason: Reason for the change
            metadata: Additional metadata (approver, tags, etc.)

        Returns:
            Created policy change log entry
        """
        try:
            # Get current version
            stmt = (
                select(func.max(PolicyChangeLog.policy_version))
                .where(PolicyChangeLog.policy_name == policy_name)
            )
            result = await self.db.execute(stmt)
            current_version = result.scalar() or 0
            new_version = current_version + 1

            # Calculate policy hash
            policy_hash = None
            if policy_content:
                policy_hash = hashlib.sha256(policy_content.encode()).hexdigest()

            # Calculate diff if previous content provided
            policy_diff = None
            if policy_content and previous_content:
                policy_diff = self._calculate_diff(previous_content, policy_content)

            # Extract metadata
            metadata = metadata or {}
            approver_user_id = metadata.get("approver_user_id")
            approval_id = metadata.get("approval_id")
            breaking_change = metadata.get("breaking_change", False)
            tags = metadata.get("tags", [])

            # Create change log
            change_log = PolicyChangeLog(
                timestamp=datetime.now(UTC),
                change_type=change_type,
                policy_name=policy_name,
                policy_version=new_version,
                changed_by_user_id=changed_by_user_id,
                policy_content=policy_content,
                policy_diff=policy_diff,
                policy_hash=policy_hash,
                change_reason=change_reason,
                approver_user_id=approver_user_id,
                approval_id=approval_id,
                breaking_change=breaking_change,
                tags=tags,
                details=metadata,
            )

            self.db.add(change_log)
            await self.db.commit()
            await self.db.refresh(change_log)

            self.logger.info(
                "policy_change_logged",
                policy_name=policy_name,
                version=new_version,
                change_type=change_type.value,
                changed_by=changed_by_user_id,
            )

            return change_log

        except Exception as e:
            await self.db.rollback()
            self.logger.error(
                "failed_to_log_policy_change",
                error=str(e),
                policy_name=policy_name,
                change_type=change_type.value,
            )
            raise

    def _calculate_diff(self, old_content: str, new_content: str) -> str:
        """Calculate diff between two policy versions.

        Args:
            old_content: Previous policy content
            new_content: New policy content

        Returns:
            Unified diff string
        """
        import difflib

        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile="previous",
            tofile="current",
            lineterm="",
        )

        return "".join(diff)

    # ========================================================================
    # QUERY AND RETRIEVAL
    # ========================================================================

    async def get_decision_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        result: Optional[PolicyDecisionResult] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[PolicyDecisionLog]:
        """Query policy decision logs with filters.

        Args:
            start_time: Filter by start timestamp
            end_time: Filter by end timestamp
            user_id: Filter by user ID
            action: Filter by action
            result: Filter by result (allow/deny/error)
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of matching policy decision logs
        """
        stmt = select(PolicyDecisionLog).order_by(desc(PolicyDecisionLog.timestamp))

        # Apply filters
        if start_time:
            stmt = stmt.where(PolicyDecisionLog.timestamp >= start_time)
        if end_time:
            stmt = stmt.where(PolicyDecisionLog.timestamp <= end_time)
        if user_id:
            stmt = stmt.where(PolicyDecisionLog.user_id == user_id)
        if action:
            stmt = stmt.where(PolicyDecisionLog.action == action)
        if result:
            stmt = stmt.where(PolicyDecisionLog.result == result)

        # Pagination
        stmt = stmt.limit(limit).offset(offset)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_policy_changes(
        self,
        policy_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        change_type: Optional[PolicyChangeType] = None,
        limit: int = 100,
    ) -> List[PolicyChangeLog]:
        """Query policy change logs.

        Args:
            policy_name: Filter by policy name
            start_time: Filter by start timestamp
            end_time: Filter by end timestamp
            change_type: Filter by change type
            limit: Maximum number of results

        Returns:
            List of matching policy change logs
        """
        stmt = select(PolicyChangeLog).order_by(desc(PolicyChangeLog.timestamp))

        # Apply filters
        if policy_name:
            stmt = stmt.where(PolicyChangeLog.policy_name == policy_name)
        if start_time:
            stmt = stmt.where(PolicyChangeLog.timestamp >= start_time)
        if end_time:
            stmt = stmt.where(PolicyChangeLog.timestamp <= end_time)
        if change_type:
            stmt = stmt.where(PolicyChangeLog.change_type == change_type)

        stmt = stmt.limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ========================================================================
    # EXPORT FUNCTIONALITY
    # ========================================================================

    async def export_decisions_csv(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Export policy decisions to CSV format.

        Args:
            start_time: Start timestamp filter
            end_time: End timestamp filter
            filters: Additional filters (user_id, action, etc.)

        Returns:
            CSV content as string
        """
        # Get decision logs
        filters = filters or {}
        logs = await self.get_decision_logs(
            start_time=start_time,
            end_time=end_time,
            user_id=filters.get("user_id"),
            action=filters.get("action"),
            result=filters.get("result"),
            limit=filters.get("limit", 10000),
        )

        # Create CSV
        output = io.StringIO()
        fieldnames = [
            "timestamp",
            "result",
            "user_id",
            "user_role",
            "action",
            "resource_type",
            "tool_name",
            "sensitivity_level",
            "reason",
            "duration_ms",
            "cache_hit",
            "client_ip",
            "mfa_verified",
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for log in logs:
            writer.writerow(
                {
                    "timestamp": log.timestamp.isoformat(),
                    "result": log.result.value,
                    "user_id": log.user_id,
                    "user_role": log.user_role,
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "tool_name": log.tool_name,
                    "sensitivity_level": log.sensitivity_level,
                    "reason": log.reason,
                    "duration_ms": log.evaluation_duration_ms,
                    "cache_hit": log.cache_hit,
                    "client_ip": log.client_ip,
                    "mfa_verified": log.mfa_verified,
                }
            )

        return output.getvalue()

    async def export_decisions_json(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Export policy decisions to JSON format.

        Args:
            start_time: Start timestamp filter
            end_time: End timestamp filter
            filters: Additional filters

        Returns:
            JSON content as string
        """
        filters = filters or {}
        logs = await self.get_decision_logs(
            start_time=start_time,
            end_time=end_time,
            user_id=filters.get("user_id"),
            action=filters.get("action"),
            result=filters.get("result"),
            limit=filters.get("limit", 10000),
        )

        # Convert to dict
        data = []
        for log in logs:
            data.append(
                {
                    "id": str(log.id),
                    "timestamp": log.timestamp.isoformat(),
                    "result": log.result.value,
                    "allow": log.allow,
                    "user_id": log.user_id,
                    "user_role": log.user_role,
                    "user_teams": log.user_teams,
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "tool_id": log.tool_id,
                    "tool_name": log.tool_name,
                    "sensitivity_level": log.sensitivity_level,
                    "policies_evaluated": log.policies_evaluated,
                    "policy_results": log.policy_results,
                    "violations": log.violations,
                    "reason": log.reason,
                    "evaluation_duration_ms": log.evaluation_duration_ms,
                    "cache_hit": log.cache_hit,
                    "client_ip": log.client_ip,
                    "request_id": log.request_id,
                    "mfa_verified": log.mfa_verified,
                    "mfa_method": log.mfa_method,
                    "time_based_allowed": log.time_based_allowed,
                    "ip_filtering_allowed": log.ip_filtering_allowed,
                    "mfa_required_satisfied": log.mfa_required_satisfied,
                }
            )

        return json.dumps({"decisions": data, "count": len(data)}, indent=2)

    # ========================================================================
    # ANALYTICS
    # ========================================================================

    async def get_decision_analytics(
        self,
        start_time: datetime,
        end_time: datetime,
        group_by: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get analytics for policy decisions.

        Args:
            start_time: Start of time range
            end_time: End of time range
            group_by: Fields to group by (action, sensitivity_level, user_role)

        Returns:
            Analytics data including counts, rates, and performance metrics
        """
        stmt = select(PolicyDecisionLog).where(
            and_(
                PolicyDecisionLog.timestamp >= start_time,
                PolicyDecisionLog.timestamp <= end_time,
            )
        )

        result = await self.db.execute(stmt)
        logs = list(result.scalars().all())

        # Calculate overall statistics
        total = len(logs)
        allows = sum(1 for log in logs if log.allow)
        denies = total - allows
        cache_hits = sum(1 for log in logs if log.cache_hit)

        # Calculate performance metrics
        durations = [log.evaluation_duration_ms for log in logs if log.evaluation_duration_ms]
        avg_duration = sum(durations) / len(durations) if durations else 0
        durations_sorted = sorted(durations)
        p50_duration = (
            durations_sorted[len(durations_sorted) // 2] if durations_sorted else 0
        )
        p95_duration = (
            durations_sorted[int(len(durations_sorted) * 0.95)] if durations_sorted else 0
        )
        p99_duration = (
            durations_sorted[int(len(durations_sorted) * 0.99)] if durations_sorted else 0
        )

        # Group by dimensions
        grouped_data = {}
        if group_by:
            for field in group_by:
                grouped = {}
                for log in logs:
                    key = getattr(log, field, "unknown")
                    if key not in grouped:
                        grouped[key] = {"total": 0, "allows": 0, "denies": 0}
                    grouped[key]["total"] += 1
                    if log.allow:
                        grouped[key]["allows"] += 1
                    else:
                        grouped[key]["denies"] += 1
                grouped_data[field] = grouped

        return {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
            "summary": {
                "total_evaluations": total,
                "total_allows": allows,
                "total_denies": denies,
                "allow_rate": (allows / total * 100) if total > 0 else 0,
                "deny_rate": (denies / total * 100) if total > 0 else 0,
            },
            "cache_performance": {
                "total_hits": cache_hits,
                "total_misses": total - cache_hits,
                "hit_rate": (cache_hits / total * 100) if total > 0 else 0,
            },
            "latency": {
                "avg_ms": round(avg_duration, 2),
                "p50_ms": round(p50_duration, 2),
                "p95_ms": round(p95_duration, 2),
                "p99_ms": round(p99_duration, 2),
            },
            "grouped": grouped_data,
        }

    async def get_top_denial_reasons(
        self,
        start_time: datetime,
        end_time: datetime,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get top denial reasons with counts.

        Args:
            start_time: Start of time range
            end_time: End of time range
            limit: Maximum number of reasons to return

        Returns:
            List of denial reasons with counts
        """
        stmt = (
            select(
                PolicyDecisionLog.denial_reason,
                func.count(PolicyDecisionLog.id).label("count"),
            )
            .where(
                and_(
                    PolicyDecisionLog.timestamp >= start_time,
                    PolicyDecisionLog.timestamp <= end_time,
                    PolicyDecisionLog.allow == False,  # noqa: E712
                    PolicyDecisionLog.denial_reason.isnot(None),
                )
            )
            .group_by(PolicyDecisionLog.denial_reason)
            .order_by(desc("count"))
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return [{"reason": row.denial_reason, "count": row.count} for row in rows]
