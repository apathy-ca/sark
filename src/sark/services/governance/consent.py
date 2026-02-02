"""
Consent tracking service for home LLM governance.

Tracks approval workflows for sensitive policy modifications,
supporting multi-approver consent (e.g., two-parent consent).
"""

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sark.models.governance import ConsentRequest, ConsentStatus
from sark.services.governance.exceptions import ConsentError

logger = structlog.get_logger()


class ConsentService:
    """
    Service for consent tracking and approval workflows.

    Manages consent requests for sensitive policy changes that require
    approval from one or more parties (e.g., two-parent consent).
    """

    # Default expiration for consent requests
    DEFAULT_EXPIRATION_HOURS = 24

    def __init__(self, db: AsyncSession) -> None:
        """Initialize with database session."""
        self.db = db

    async def request_change(
        self,
        change_type: str,
        description: str,
        requester: str,
        *,
        required_approvers: int = 1,
        expires_in_hours: int | None = None,
    ) -> ConsentRequest:
        """
        Create a consent request for a policy change.

        Args:
            change_type: Type of change (e.g., "enable_blocking")
            description: Detailed description of the change
            requester: Who is requesting the change
            required_approvers: Number of approvers needed (default 1)
            expires_in_hours: Hours until request expires (None = 24 hours)

        Returns:
            Created consent request

        Raises:
            ConsentError: If validation fails
        """
        # Validate inputs
        if not change_type or not change_type.strip():
            raise ConsentError("Change type is required")
        if not description or not description.strip():
            raise ConsentError("Description is required")
        if not requester or not requester.strip():
            raise ConsentError("Requester is required")
        if required_approvers < 1 or required_approvers > 10:
            raise ConsentError("Required approvers must be between 1 and 10")

        # Check for existing pending request of same type
        existing = await self._get_pending_by_type(change_type)
        if existing:
            raise ConsentError(
                f"Pending consent request already exists for '{change_type}'",
                details={"request_id": existing.id},
            )

        # Calculate expiration
        expires_at = None
        if expires_in_hours:
            expires_at = datetime.now(UTC) + timedelta(hours=expires_in_hours)
        else:
            expires_at = datetime.now(UTC) + timedelta(hours=self.DEFAULT_EXPIRATION_HOURS)

        # Create consent request
        consent = ConsentRequest(
            change_type=change_type.strip(),
            change_description=description.strip(),
            requester=requester.strip(),
            status=ConsentStatus.PENDING.value,
            required_approvers=required_approvers,
            current_approvers=None,
            expires_at=expires_at,
        )
        self.db.add(consent)
        await self.db.commit()
        await self.db.refresh(consent)

        logger.info(
            "consent_request_created",
            request_id=consent.id,
            change_type=change_type,
            requester=requester,
            required_approvers=required_approvers,
        )
        return consent

    async def approve(
        self,
        request_id: int,
        approver: str,
    ) -> ConsentRequest:
        """
        Approve a consent request.

        Args:
            request_id: Consent request ID
            approver: Who is approving

        Returns:
            Updated consent request

        Raises:
            ConsentError: If request not found, already processed, or approver is requester
        """
        consent = await self.get_request(request_id)
        if not consent:
            raise ConsentError(f"Consent request {request_id} not found")

        if consent.status != ConsentStatus.PENDING.value:
            raise ConsentError(
                f"Consent request is already {consent.status}",
                details={"request_id": request_id, "status": consent.status},
            )

        # Check expiration
        if consent.expires_at and consent.expires_at < datetime.now(UTC):
            consent.status = ConsentStatus.EXPIRED.value
            await self.db.commit()
            raise ConsentError("Consent request has expired")

        # Requester cannot approve their own request
        if consent.requester == approver:
            raise ConsentError("Requester cannot approve their own request")

        # Check if this approver has already approved
        current_approvers = self._parse_approvers(consent.current_approvers)
        if approver in current_approvers:
            raise ConsentError(f"'{approver}' has already approved this request")

        # Add approver
        current_approvers.append(approver)
        consent.current_approvers = ",".join(current_approvers)

        # Check if we have enough approvers
        if len(current_approvers) >= consent.required_approvers:
            consent.status = ConsentStatus.APPROVED.value
            consent.approved_at = datetime.now(UTC)
            logger.info(
                "consent_request_approved",
                request_id=request_id,
                approvers=current_approvers,
            )
        else:
            logger.info(
                "consent_request_partial_approval",
                request_id=request_id,
                approver=approver,
                current_count=len(current_approvers),
                required_count=consent.required_approvers,
            )

        await self.db.commit()
        await self.db.refresh(consent)
        return consent

    async def reject(
        self,
        request_id: int,
        rejector: str,
        reason: str | None = None,
    ) -> ConsentRequest:
        """
        Reject a consent request.

        Args:
            request_id: Consent request ID
            rejector: Who is rejecting
            reason: Reason for rejection

        Returns:
            Updated consent request

        Raises:
            ConsentError: If request not found or already processed
        """
        consent = await self.get_request(request_id)
        if not consent:
            raise ConsentError(f"Consent request {request_id} not found")

        if consent.status != ConsentStatus.PENDING.value:
            raise ConsentError(
                f"Consent request is already {consent.status}",
                details={"request_id": request_id, "status": consent.status},
            )

        consent.status = ConsentStatus.REJECTED.value
        consent.rejected_at = datetime.now(UTC)
        consent.rejection_reason = reason

        # Track who rejected in approvers field
        current_approvers = self._parse_approvers(consent.current_approvers)
        current_approvers.append(f"REJECTED:{rejector}")
        consent.current_approvers = ",".join(current_approvers)

        await self.db.commit()
        await self.db.refresh(consent)

        logger.info(
            "consent_request_rejected",
            request_id=request_id,
            rejector=rejector,
            reason=reason,
        )
        return consent

    async def is_approved(self, change_type: str) -> bool:
        """
        Check if a change type has been approved.

        Args:
            change_type: Type of change to check

        Returns:
            True if approved, False otherwise
        """
        result = await self.db.execute(
            select(ConsentRequest).where(
                ConsentRequest.change_type == change_type,
                ConsentRequest.status == ConsentStatus.APPROVED.value,
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_request(self, request_id: int) -> ConsentRequest | None:
        """Get consent request by ID."""
        result = await self.db.execute(
            select(ConsentRequest).where(ConsentRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def get_pending_requests(self) -> list[ConsentRequest]:
        """Get all pending consent requests."""
        # First expire any overdue requests
        await self._expire_overdue_requests()

        result = await self.db.execute(
            select(ConsentRequest)
            .where(ConsentRequest.status == ConsentStatus.PENDING.value)
            .order_by(ConsentRequest.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_requests(
        self,
        *,
        status: ConsentStatus | None = None,
        requester: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ConsentRequest]:
        """
        List consent requests with optional filters.

        Args:
            status: Filter by status
            requester: Filter by requester
            limit: Maximum number to return
            offset: Number to skip

        Returns:
            List of consent requests
        """
        query = select(ConsentRequest)

        if status:
            query = query.where(ConsentRequest.status == status.value)
        if requester:
            query = query.where(ConsentRequest.requester == requester)

        query = query.order_by(ConsentRequest.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def cancel(self, request_id: int, cancelled_by: str) -> bool:
        """
        Cancel a pending consent request.

        Only the requester can cancel their own request.

        Args:
            request_id: Consent request ID
            cancelled_by: Who is cancelling

        Returns:
            True if cancelled, False if not found or not allowed

        Raises:
            ConsentError: If not authorized to cancel
        """
        consent = await self.get_request(request_id)
        if not consent:
            return False

        if consent.status != ConsentStatus.PENDING.value:
            raise ConsentError(f"Cannot cancel request with status '{consent.status}'")

        if consent.requester != cancelled_by:
            raise ConsentError("Only the requester can cancel their own request")

        consent.status = ConsentStatus.REJECTED.value
        consent.rejected_at = datetime.now(UTC)
        consent.rejection_reason = "Cancelled by requester"

        await self.db.commit()

        logger.info("consent_request_cancelled", request_id=request_id, cancelled_by=cancelled_by)
        return True

    async def get_statistics(self) -> dict:
        """
        Get consent request statistics.

        Returns:
            Dictionary with statistics
        """
        from sqlalchemy import func

        # Total by status
        stats = {}
        for status in ConsentStatus:
            result = await self.db.execute(
                select(func.count(ConsentRequest.id)).where(
                    ConsentRequest.status == status.value
                )
            )
            stats[f"total_{status.value}"] = result.scalar() or 0

        # Pending count
        pending = await self.get_pending_requests()
        stats["currently_pending"] = len(pending)

        return stats

    # =========================================================================
    # Private helpers
    # =========================================================================

    def _parse_approvers(self, approvers_str: str | None) -> list[str]:
        """Parse comma-separated approvers string to list."""
        if not approvers_str:
            return []
        return [a.strip() for a in approvers_str.split(",") if a.strip()]

    async def _get_pending_by_type(self, change_type: str) -> ConsentRequest | None:
        """Get pending request by change type."""
        result = await self.db.execute(
            select(ConsentRequest).where(
                ConsentRequest.change_type == change_type,
                ConsentRequest.status == ConsentStatus.PENDING.value,
            )
        )
        return result.scalar_one_or_none()

    async def _expire_overdue_requests(self) -> int:
        """Mark overdue requests as expired."""
        from sqlalchemy import update

        now = datetime.now(UTC)
        result = await self.db.execute(
            update(ConsentRequest)
            .where(
                ConsentRequest.status == ConsentStatus.PENDING.value,
                ConsentRequest.expires_at < now,
            )
            .values(status=ConsentStatus.EXPIRED.value)
        )
        await self.db.commit()
        return result.rowcount


# =============================================================================
# Factory function
# =============================================================================


def get_consent_service(db: AsyncSession) -> ConsentService:
    """Get consent service instance."""
    return ConsentService(db)
