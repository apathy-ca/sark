"""
Unit tests for TimeRulesService.
"""

from datetime import UTC, datetime, time, timedelta

import pytest

from sark.models.governance import TimeRuleAction
from sark.services.governance.exceptions import TimeRuleError
from sark.services.governance.time_rules import TimeRulesService


class TestTimeRulesService:
    """Tests for TimeRulesService."""

    @pytest.mark.asyncio
    async def test_add_rule(self, time_rules_service: TimeRulesService):
        """Test adding a time rule."""
        rule = await time_rules_service.add_rule(
            name="bedtime",
            start="21:00",
            end="07:00",
            action=TimeRuleAction.BLOCK,
            description="Bedtime hours",
        )

        assert rule.name == "bedtime"
        assert rule.start_time == "21:00"
        assert rule.end_time == "07:00"
        assert rule.action == "block"
        assert rule.active is True

    @pytest.mark.asyncio
    async def test_add_rule_with_days(self, time_rules_service: TimeRulesService):
        """Test adding rule with specific days."""
        rule = await time_rules_service.add_rule(
            name="weekday-school",
            start="08:00",
            end="15:00",
            days=["mon", "tue", "wed", "thu", "fri"],
        )

        assert rule.days == "mon,tue,wed,thu,fri"

    @pytest.mark.asyncio
    async def test_add_rule_invalid_time(self, time_rules_service: TimeRulesService):
        """Test adding rule with invalid time format."""
        with pytest.raises(TimeRuleError) as exc_info:
            await time_rules_service.add_rule(
                name="invalid",
                start="25:00",
                end="07:00",
            )

        assert "Invalid time format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_add_rule_invalid_day(self, time_rules_service: TimeRulesService):
        """Test adding rule with invalid day."""
        with pytest.raises(TimeRuleError) as exc_info:
            await time_rules_service.add_rule(
                name="invalid",
                start="21:00",
                end="07:00",
                days=["invalid-day"],
            )

        assert "Invalid day" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_add_duplicate_rule(self, time_rules_service: TimeRulesService):
        """Test adding duplicate rule raises error."""
        await time_rules_service.add_rule(name="bedtime", start="21:00", end="07:00")

        with pytest.raises(TimeRuleError) as exc_info:
            await time_rules_service.add_rule(name="bedtime", start="22:00", end="06:00")

        assert "already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_check_rules_blocked(self, time_rules_service: TimeRulesService):
        """Test check_rules returns blocked for matching rule."""
        await time_rules_service.add_rule(
            name="always-block",
            start="00:00",
            end="23:59",
        )

        result = await time_rules_service.check_rules()
        assert result.blocked is True
        assert result.rule == "always-block"
        assert result.action == "block"

    @pytest.mark.asyncio
    async def test_check_rules_not_blocked(self, time_rules_service: TimeRulesService):
        """Test check_rules returns not blocked when no rule matches."""
        # Rule for the past hour that doesn't include now
        now = datetime.now(UTC)
        past_hour = (now - timedelta(hours=2)).strftime("%H:%M")
        past_hour_end = (now - timedelta(hours=1)).strftime("%H:%M")

        await time_rules_service.add_rule(
            name="past-rule",
            start=past_hour,
            end=past_hour_end,
        )

        result = await time_rules_service.check_rules()
        assert result.blocked is False
        assert result.rule is None

    @pytest.mark.asyncio
    async def test_check_rules_overnight(self, time_rules_service: TimeRulesService):
        """Test overnight rule (crosses midnight)."""
        # This rule should always match some time
        await time_rules_service.add_rule(
            name="overnight",
            start="22:00",
            end="06:00",
        )

        # Test at 23:00
        late_night = datetime.now(UTC).replace(hour=23, minute=0)
        result = await time_rules_service.check_rules(check_time=late_night)
        assert result.blocked is True

        # Test at 03:00
        early_morning = datetime.now(UTC).replace(hour=3, minute=0)
        result = await time_rules_service.check_rules(check_time=early_morning)
        assert result.blocked is True

        # Test at 12:00
        midday = datetime.now(UTC).replace(hour=12, minute=0)
        result = await time_rules_service.check_rules(check_time=midday)
        assert result.blocked is False

    @pytest.mark.asyncio
    async def test_check_rules_specific_day(self, time_rules_service: TimeRulesService):
        """Test rule that only applies on specific days."""
        await time_rules_service.add_rule(
            name="weekday-only",
            start="00:00",
            end="23:59",
            days=["mon"],  # Monday only
        )

        # Get a Monday
        now = datetime.now(UTC)
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0 and now.weekday() != 0:
            days_until_monday = 7
        monday = now + timedelta(days=days_until_monday)
        if now.weekday() == 0:
            monday = now

        result = await time_rules_service.check_rules(check_time=monday)
        assert result.blocked is True

    @pytest.mark.asyncio
    async def test_check_rules_alert_action(self, time_rules_service: TimeRulesService):
        """Test alert action doesn't block."""
        await time_rules_service.add_rule(
            name="alert-rule",
            start="00:00",
            end="23:59",
            action=TimeRuleAction.ALERT,
        )

        result = await time_rules_service.check_rules()
        assert result.blocked is False
        assert result.action == "alert"

    @pytest.mark.asyncio
    async def test_remove_rule(self, time_rules_service: TimeRulesService):
        """Test removing a rule."""
        await time_rules_service.add_rule(name="test", start="00:00", end="23:59")

        result = await time_rules_service.remove_rule("test")
        assert result is True

        # Check rule no longer applies
        rules = await time_rules_service.list_rules(active_only=True)
        assert len(rules) == 0

    @pytest.mark.asyncio
    async def test_remove_nonexistent_rule(self, time_rules_service: TimeRulesService):
        """Test removing non-existent rule returns False."""
        result = await time_rules_service.remove_rule("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_rules(self, time_rules_service: TimeRulesService):
        """Test listing rules."""
        await time_rules_service.add_rule(name="rule1", start="00:00", end="12:00")
        await time_rules_service.add_rule(name="rule2", start="12:00", end="23:59")

        rules = await time_rules_service.list_rules()
        assert len(rules) == 2

    @pytest.mark.asyncio
    async def test_update_rule(self, time_rules_service: TimeRulesService):
        """Test updating a rule."""
        rule = await time_rules_service.add_rule(name="test", start="00:00", end="12:00")

        updated = await time_rules_service.update_rule(
            rule.id,
            start_time="08:00",
            end_time="16:00",
        )

        assert updated.start_time == "08:00"
        assert updated.end_time == "16:00"

    @pytest.mark.asyncio
    async def test_rule_priority(self, time_rules_service: TimeRulesService):
        """Test higher priority rules take precedence."""
        # Higher priority (lower number) - alert
        await time_rules_service.add_rule(
            name="high-priority",
            start="00:00",
            end="23:59",
            action=TimeRuleAction.ALERT,
            priority=10,
        )

        # Lower priority - block
        await time_rules_service.add_rule(
            name="low-priority",
            start="00:00",
            end="23:59",
            action=TimeRuleAction.BLOCK,
            priority=100,
        )

        result = await time_rules_service.check_rules()
        # High priority rule should match first
        assert result.rule == "high-priority"
        assert result.action == "alert"

    @pytest.mark.asyncio
    async def test_count_rules(self, time_rules_service: TimeRulesService):
        """Test counting rules."""
        await time_rules_service.add_rule(name="rule1", start="00:00", end="12:00")
        await time_rules_service.add_rule(name="rule2", start="12:00", end="23:59")

        count = await time_rules_service.count_rules()
        assert count == 2
