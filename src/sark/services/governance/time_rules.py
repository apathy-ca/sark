"""
Time-based access rules service for home LLM governance.

Manages time-based rules that control when LLM access is allowed,
such as bedtime restrictions, school hours, etc.
"""

from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sark.models.governance import (
    TimeCheckResult,
    TimeRule,
    TimeRuleAction,
    TimeRuleCreate,
)
from sark.services.governance.exceptions import TimeRuleError

logger = structlog.get_logger()

# Day name mapping
DAYS_MAP = {
    "mon": 0, "monday": 0,
    "tue": 1, "tuesday": 1,
    "wed": 2, "wednesday": 2,
    "thu": 3, "thursday": 3,
    "fri": 4, "friday": 4,
    "sat": 5, "saturday": 5,
    "sun": 6, "sunday": 6,
}


class TimeRulesService:
    """
    Service for managing time-based access rules.

    Rules define time windows when specific actions apply:
    - block: Block all LLM requests
    - alert: Allow but generate alert
    - log: Allow and log only
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize with database session."""
        self.db = db
        self._rules_cache: list[TimeRule] | None = None
        self._cache_updated: datetime | None = None
        self._cache_ttl = 300  # 5 minutes

    async def add_rule(
        self,
        name: str,
        start: str,
        end: str,
        *,
        action: TimeRuleAction = TimeRuleAction.BLOCK,
        days: list[str] | None = None,
        description: str | None = None,
        timezone: str = "UTC",
        priority: int = 100,
        created_by: str | None = None,
    ) -> TimeRule:
        """
        Add time-based rule.

        Args:
            name: Unique rule name (e.g., "bedtime")
            start: Start time in HH:MM format (e.g., "21:00")
            end: End time in HH:MM format (e.g., "07:00")
            action: Action to take when rule matches (block, alert, log)
            days: Days of week (None = all days, or ["mon", "tue", ...])
            description: Human-readable description
            timezone: Timezone for rule evaluation
            priority: Rule priority (lower = higher priority)
            created_by: Who created this rule

        Returns:
            Created time rule

        Raises:
            TimeRuleError: If validation fails or rule already exists
        """
        # Validate times
        start_time = self._parse_time(start)
        end_time = self._parse_time(end)

        # Validate timezone
        try:
            ZoneInfo(timezone)
        except Exception as e:
            raise TimeRuleError(f"Invalid timezone: {timezone}") from e

        # Validate days
        days_str = None
        if days:
            validated_days = []
            for day in days:
                day_lower = day.lower().strip()
                if day_lower not in DAYS_MAP:
                    raise TimeRuleError(f"Invalid day: {day}")
                validated_days.append(day_lower[:3])  # Normalize to 3-letter
            days_str = ",".join(validated_days)

        # Check for existing rule with same name
        existing = await self._get_rule_by_name(name)
        if existing:
            raise TimeRuleError(
                f"Rule with name '{name}' already exists",
                details={"name": name, "rule_id": existing.id},
            )

        # Create rule
        rule = TimeRule(
            name=name,
            description=description,
            start_time=start,
            end_time=end,
            action=action.value,
            days=days_str,
            timezone=timezone,
            priority=priority,
            created_by=created_by,
        )
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)

        self._invalidate_cache()
        logger.info(
            "time_rule_added",
            name=name,
            start=start,
            end=end,
            action=action.value,
        )
        return rule

    async def remove_rule(self, name: str) -> bool:
        """
        Remove time rule (soft delete).

        Args:
            name: Rule name to remove

        Returns:
            True if rule was removed, False if not found
        """
        rule = await self._get_rule_by_name(name)
        if not rule:
            return False

        rule.active = False
        rule.updated_at = datetime.now(UTC)
        await self.db.commit()

        self._invalidate_cache()
        logger.info("time_rule_removed", name=name)
        return True

    async def check_rules(
        self,
        check_time: datetime | None = None,
        *,
        device_ip: str | None = None,
    ) -> TimeCheckResult:
        """
        Check if any time rules apply at the given time.

        This is the hot-path method for policy evaluation.

        Args:
            check_time: Time to check (defaults to now)
            device_ip: Optional device IP for logging

        Returns:
            TimeCheckResult with blocked status and matching rule info
        """
        check_time = check_time or datetime.now(UTC)

        # Get active rules (from cache if available)
        rules = await self._get_active_rules()

        # Sort by priority (lower = higher priority)
        rules_sorted = sorted(rules, key=lambda r: r.priority)

        for rule in rules_sorted:
            if self._rule_matches(rule, check_time):
                action = TimeRuleAction(rule.action)
                is_blocked = action == TimeRuleAction.BLOCK

                logger.info(
                    "time_rule_matched",
                    rule_name=rule.name,
                    action=rule.action,
                    check_time=check_time.isoformat(),
                    device_ip=device_ip,
                )

                return TimeCheckResult(
                    blocked=is_blocked,
                    rule=rule.name,
                    action=rule.action,
                    reason=f"Time rule '{rule.name}' is active ({rule.start_time} - {rule.end_time})",
                )

        return TimeCheckResult(
            blocked=False,
            rule=None,
            action=None,
            reason="No time rules apply",
        )

    async def list_rules(
        self,
        *,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TimeRule]:
        """
        List time rules.

        Args:
            active_only: Only return active rules
            limit: Maximum number of rules to return
            offset: Number of rules to skip

        Returns:
            List of time rules
        """
        query = select(TimeRule)

        if active_only:
            query = query.where(TimeRule.active == True)  # noqa: E712

        query = query.order_by(TimeRule.priority, TimeRule.name).offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_rule(self, rule_id: int) -> TimeRule | None:
        """Get time rule by ID."""
        result = await self.db.execute(
            select(TimeRule).where(TimeRule.id == rule_id)
        )
        return result.scalar_one_or_none()

    async def update_rule(
        self,
        rule_id: int,
        *,
        start_time: str | None = None,
        end_time: str | None = None,
        action: TimeRuleAction | None = None,
        days: list[str] | None = None,
        description: str | None = None,
        priority: int | None = None,
        active: bool | None = None,
    ) -> TimeRule | None:
        """
        Update time rule.

        Args:
            rule_id: Rule ID to update
            start_time: New start time (None to keep existing)
            end_time: New end time (None to keep existing)
            action: New action (None to keep existing)
            days: New days list (None to keep existing)
            description: New description (None to keep existing)
            priority: New priority (None to keep existing)
            active: New active status (None to keep existing)

        Returns:
            Updated rule or None if not found
        """
        rule = await self.get_rule(rule_id)
        if not rule:
            return None

        if start_time is not None:
            self._parse_time(start_time)  # Validate
            rule.start_time = start_time
        if end_time is not None:
            self._parse_time(end_time)  # Validate
            rule.end_time = end_time
        if action is not None:
            rule.action = action.value
        if days is not None:
            rule.days = ",".join(d.lower()[:3] for d in days) if days else None
        if description is not None:
            rule.description = description
        if priority is not None:
            rule.priority = priority
        if active is not None:
            rule.active = active

        rule.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(rule)

        self._invalidate_cache()
        logger.info("time_rule_updated", rule_id=rule_id)
        return rule

    async def count_rules(self, *, active_only: bool = True) -> int:
        """Count total time rules."""
        from sqlalchemy import func

        query = select(func.count(TimeRule.id))
        if active_only:
            query = query.where(TimeRule.active == True)  # noqa: E712

        result = await self.db.execute(query)
        return result.scalar() or 0

    # =========================================================================
    # Private helpers
    # =========================================================================

    def _parse_time(self, time_str: str) -> time:
        """Parse HH:MM string to time object."""
        try:
            parts = time_str.split(":")
            if len(parts) != 2:
                raise ValueError("Invalid format")
            hour, minute = int(parts[0]), int(parts[1])
            return time(hour=hour, minute=minute)
        except (ValueError, IndexError) as e:
            raise TimeRuleError(f"Invalid time format '{time_str}'. Use HH:MM format.") from e

    def _rule_matches(self, rule: TimeRule, check_time: datetime) -> bool:
        """Check if rule matches the given time."""
        # Convert check_time to rule's timezone
        try:
            tz = ZoneInfo(rule.timezone)
            local_time = check_time.astimezone(tz)
        except Exception:
            local_time = check_time  # Fallback to UTC

        current_time = local_time.time()
        current_weekday = local_time.weekday()

        # Check day of week
        if rule.days:
            rule_days = [DAYS_MAP.get(d.strip(), -1) for d in rule.days.split(",")]
            if current_weekday not in rule_days:
                return False

        # Parse rule times
        start = self._parse_time(rule.start_time)
        end = self._parse_time(rule.end_time)

        # Handle overnight rules (e.g., 21:00 to 07:00)
        if start > end:
            # Rule spans midnight
            return current_time >= start or current_time <= end
        else:
            # Same-day rule
            return start <= current_time <= end

    async def _get_rule_by_name(self, name: str) -> TimeRule | None:
        """Get rule by name."""
        result = await self.db.execute(
            select(TimeRule).where(TimeRule.name == name)
        )
        return result.scalar_one_or_none()

    async def _get_active_rules(self) -> list[TimeRule]:
        """Get active rules (with caching)."""
        if self._is_cache_valid() and self._rules_cache is not None:
            return self._rules_cache

        result = await self.db.execute(
            select(TimeRule).where(TimeRule.active == True)  # noqa: E712
        )
        self._rules_cache = list(result.scalars().all())
        self._cache_updated = datetime.now(UTC)
        return self._rules_cache

    def _invalidate_cache(self) -> None:
        """Invalidate the rules cache."""
        self._rules_cache = None
        self._cache_updated = None

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if self._cache_updated is None:
            return False
        age = (datetime.now(UTC) - self._cache_updated).total_seconds()
        return age < self._cache_ttl


# =============================================================================
# Factory function
# =============================================================================


def get_time_rules_service(db: AsyncSession) -> TimeRulesService:
    """Get time rules service instance."""
    return TimeRulesService(db)
