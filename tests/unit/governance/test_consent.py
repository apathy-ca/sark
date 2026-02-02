"""
Unit tests for ConsentService.
"""

from datetime import UTC, datetime, timedelta

import pytest

from sark.models.governance import ConsentStatus
from sark.services.governance.consent import ConsentService
from sark.services.governance.exceptions import ConsentError


class TestConsentService:
    """Tests for ConsentService."""

    @pytest.mark.asyncio
    async def test_request_change(self, consent_service: ConsentService):
        """Test creating a consent request."""
        request = await consent_service.request_change(
            change_type="enable_blocking",
            description="Enable content blocking for kids",
            requester="parent1",
        )

        assert request.change_type == "enable_blocking"
        assert request.requester == "parent1"
        assert request.status == ConsentStatus.PENDING.value

    @pytest.mark.asyncio
    async def test_request_change_with_multiple_approvers(self, consent_service: ConsentService):
        """Test creating request requiring multiple approvers."""
        request = await consent_service.request_change(
            change_type="enable_blocking",
            description="Enable blocking",
            requester="parent1",
            required_approvers=2,
        )

        assert request.required_approvers == 2

    @pytest.mark.asyncio
    async def test_request_change_duplicate(self, consent_service: ConsentService):
        """Test duplicate pending request raises error."""
        await consent_service.request_change(
            change_type="enable_blocking",
            description="First request",
            requester="parent1",
        )

        with pytest.raises(ConsentError) as exc_info:
            await consent_service.request_change(
                change_type="enable_blocking",
                description="Second request",
                requester="parent2",
            )

        assert "already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_approve_single_approver(self, consent_service: ConsentService):
        """Test approving request with single approver."""
        request = await consent_service.request_change(
            change_type="enable_blocking",
            description="Enable blocking",
            requester="parent1",
            required_approvers=1,
        )

        approved = await consent_service.approve(request.id, "parent2")
        assert approved.status == ConsentStatus.APPROVED.value

    @pytest.mark.asyncio
    async def test_approve_multiple_approvers(self, consent_service: ConsentService):
        """Test approving request requiring multiple approvers."""
        request = await consent_service.request_change(
            change_type="enable_blocking",
            description="Enable blocking",
            requester="parent1",
            required_approvers=2,
        )

        # First approval
        partial = await consent_service.approve(request.id, "parent2")
        assert partial.status == ConsentStatus.PENDING.value

        # Second approval
        approved = await consent_service.approve(request.id, "parent3")
        assert approved.status == ConsentStatus.APPROVED.value

    @pytest.mark.asyncio
    async def test_approve_by_requester_raises_error(self, consent_service: ConsentService):
        """Test requester cannot approve their own request."""
        request = await consent_service.request_change(
            change_type="enable_blocking",
            description="Enable blocking",
            requester="parent1",
        )

        with pytest.raises(ConsentError) as exc_info:
            await consent_service.approve(request.id, "parent1")

        assert "cannot approve their own request" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_approve_already_approved(self, consent_service: ConsentService):
        """Test approving already approved request raises error."""
        request = await consent_service.request_change(
            change_type="enable_blocking",
            description="Enable blocking",
            requester="parent1",
        )
        await consent_service.approve(request.id, "parent2")

        with pytest.raises(ConsentError) as exc_info:
            await consent_service.approve(request.id, "parent3")

        assert "already approved" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_approve_duplicate_approver(self, consent_service: ConsentService):
        """Test same person cannot approve twice."""
        request = await consent_service.request_change(
            change_type="enable_blocking",
            description="Enable blocking",
            requester="parent1",
            required_approvers=2,
        )
        await consent_service.approve(request.id, "parent2")

        with pytest.raises(ConsentError) as exc_info:
            await consent_service.approve(request.id, "parent2")

        assert "already approved" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_reject(self, consent_service: ConsentService):
        """Test rejecting a consent request."""
        request = await consent_service.request_change(
            change_type="enable_blocking",
            description="Enable blocking",
            requester="parent1",
        )

        rejected = await consent_service.reject(request.id, "parent2", "Not needed")
        assert rejected.status == ConsentStatus.REJECTED.value
        assert rejected.rejection_reason == "Not needed"

    @pytest.mark.asyncio
    async def test_is_approved(self, consent_service: ConsentService):
        """Test checking if change type is approved."""
        request = await consent_service.request_change(
            change_type="enable_blocking",
            description="Enable blocking",
            requester="parent1",
        )

        # Not approved yet
        assert await consent_service.is_approved("enable_blocking") is False

        # After approval
        await consent_service.approve(request.id, "parent2")
        assert await consent_service.is_approved("enable_blocking") is True

    @pytest.mark.asyncio
    async def test_get_pending_requests(self, consent_service: ConsentService):
        """Test getting pending requests."""
        await consent_service.request_change(
            change_type="change1",
            description="First change",
            requester="parent1",
        )
        await consent_service.request_change(
            change_type="change2",
            description="Second change",
            requester="parent1",
        )

        pending = await consent_service.get_pending_requests()
        assert len(pending) == 2

    @pytest.mark.asyncio
    async def test_list_requests_by_status(self, consent_service: ConsentService):
        """Test listing requests by status."""
        request = await consent_service.request_change(
            change_type="change1",
            description="First change",
            requester="parent1",
        )
        await consent_service.approve(request.id, "parent2")

        approved = await consent_service.list_requests(status=ConsentStatus.APPROVED)
        assert len(approved) == 1

    @pytest.mark.asyncio
    async def test_cancel(self, consent_service: ConsentService):
        """Test cancelling a consent request."""
        request = await consent_service.request_change(
            change_type="enable_blocking",
            description="Enable blocking",
            requester="parent1",
        )

        result = await consent_service.cancel(request.id, "parent1")
        assert result is True

        # Check status
        updated = await consent_service.get_request(request.id)
        assert updated.status == ConsentStatus.REJECTED.value

    @pytest.mark.asyncio
    async def test_cancel_by_non_requester(self, consent_service: ConsentService):
        """Test non-requester cannot cancel."""
        request = await consent_service.request_change(
            change_type="enable_blocking",
            description="Enable blocking",
            requester="parent1",
        )

        with pytest.raises(ConsentError) as exc_info:
            await consent_service.cancel(request.id, "parent2")

        assert "Only the requester can cancel" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_statistics(self, consent_service: ConsentService):
        """Test getting consent statistics."""
        await consent_service.request_change(
            change_type="change1",
            description="First change",
            requester="parent1",
        )

        stats = await consent_service.get_statistics()
        assert "total_pending" in stats
        assert stats["currently_pending"] >= 1

    @pytest.mark.asyncio
    async def test_expired_request(self, consent_service: ConsentService):
        """Test expired request cannot be approved."""
        request = await consent_service.request_change(
            change_type="enable_blocking",
            description="Enable blocking",
            requester="parent1",
            expires_in_hours=1,
        )

        # Manually expire
        request = await consent_service.get_request(request.id)
        request.expires_at = datetime.now(UTC) - timedelta(hours=1)
        await consent_service.db.commit()

        with pytest.raises(ConsentError) as exc_info:
            await consent_service.approve(request.id, "parent2")

        assert "expired" in str(exc_info.value)
