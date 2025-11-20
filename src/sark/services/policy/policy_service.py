"""Policy management service."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from sark.models.policy import Policy, PolicyStatus, PolicyType, PolicyVersion

logger = structlog.get_logger()


class PolicyService:
    """Service for managing policies."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize policy service."""
        self.db = db

    async def create_policy(
        self,
        name: str,
        description: str,
        policy_type: PolicyType,
        initial_content: str,
        created_by: UUID,
    ) -> Policy:
        """
        Create a new policy with initial version.

        Args:
            name: Policy name
            description: Policy description
            policy_type: Type of policy
            initial_content: Initial Rego policy content
            created_by: User ID creating the policy

        Returns:
            Created policy
        """
        # Create policy
        policy = Policy(
            name=name,
            description=description,
            policy_type=policy_type,
            status=PolicyStatus.DRAFT,
        )
        self.db.add(policy)
        await self.db.flush()

        # Create initial version
        version = PolicyVersion(
            policy_id=policy.id,
            version=1,
            content=initial_content,
            is_active=False,
            tested=False,
            created_by=created_by,
        )
        self.db.add(version)
        await self.db.flush()

        policy.current_version_id = version.id
        await self.db.commit()
        await self.db.refresh(policy)

        logger.info(
            "policy_created",
            policy_id=str(policy.id),
            name=name,
            created_by=str(created_by),
        )

        return policy

    async def create_version(
        self,
        policy_id: UUID,
        content: str,
        created_by: UUID,
        notes: str | None = None,
    ) -> PolicyVersion:
        """
        Create a new version of an existing policy.

        Args:
            policy_id: Policy ID
            content: New Rego policy content
            created_by: User ID creating the version
            notes: Optional release notes

        Returns:
            Created policy version
        """
        # Get current max version
        result = await self.db.execute(
            select(PolicyVersion.version)
            .where(PolicyVersion.policy_id == policy_id)
            .order_by(PolicyVersion.version.desc())
            .limit(1)
        )
        max_version = result.scalar_one_or_none() or 0

        # Create new version
        version = PolicyVersion(
            policy_id=policy_id,
            version=max_version + 1,
            content=content,
            is_active=False,
            tested=False,
            created_by=created_by,
            notes=notes,
        )
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)

        logger.info(
            "policy_version_created",
            policy_id=str(policy_id),
            version=version.version,
            created_by=str(created_by),
        )

        return version

    async def activate_version(self, policy_id: UUID, version_id: UUID) -> Policy:
        """
        Activate a specific policy version.

        Args:
            policy_id: Policy ID
            version_id: Version ID to activate

        Returns:
            Updated policy
        """
        # Deactivate all versions
        await self.db.execute(
            select(PolicyVersion)
            .where(PolicyVersion.policy_id == policy_id)
            .where(PolicyVersion.is_active.is_(True))
        )

        # Activate target version
        version = await self.db.get(PolicyVersion, version_id)
        if not version:
            raise ValueError(f"Version {version_id} not found")

        version.is_active = True

        # Update policy
        policy = await self.db.get(Policy, policy_id)
        if not policy:
            raise ValueError(f"Policy {policy_id} not found")

        policy.current_version_id = version_id
        policy.status = PolicyStatus.ACTIVE

        await self.db.commit()
        await self.db.refresh(policy)

        logger.info(
            "policy_version_activated",
            policy_id=str(policy_id),
            version_id=str(version_id),
            version=version.version,
        )

        return policy

    async def get_policy(self, policy_id: UUID) -> Policy | None:
        """Get policy by ID."""
        return await self.db.get(Policy, policy_id)

    async def get_policy_by_name(self, name: str) -> Policy | None:
        """Get policy by name."""
        result = await self.db.execute(select(Policy).where(Policy.name == name))
        return result.scalar_one_or_none()

    async def list_policies(
        self,
        policy_type: PolicyType | None = None,
        status: PolicyStatus | None = None,
    ) -> list[Policy]:
        """
        List policies with optional filters.

        Args:
            policy_type: Filter by policy type
            status: Filter by status

        Returns:
            List of policies
        """
        query = select(Policy)

        if policy_type:
            query = query.where(Policy.policy_type == policy_type)
        if status:
            query = query.where(Policy.status == status)

        result = await self.db.execute(query)
        return list(result.scalars().all())
