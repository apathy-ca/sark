"""Comprehensive tests for Policy Service."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sark.models.policy import Policy, PolicyStatus, PolicyType, PolicyVersion
from sark.services.policy.policy_service import PolicyService


class TestPolicyService:
    """Test suite for PolicyService class."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock(spec=AsyncSession)
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.execute = AsyncMock()
        db.get = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        """Create PolicyService instance with mock database."""
        return PolicyService(db=mock_db)

    @pytest.fixture
    def sample_policy_data(self):
        """Sample policy data for testing."""
        return {
            "name": "test_policy",
            "description": "Test policy for unit tests",
            "policy_type": PolicyType.AUTHORIZATION,
            "initial_content": "package sark\n\ndefault allow = false",
            "created_by": uuid4(),
        }

    # ===== create_policy Tests =====

    @pytest.mark.asyncio
    async def test_create_policy_basic(self, service, mock_db, sample_policy_data):
        """Test creating a basic policy."""
        # Setup mock
        policy_id = uuid4()
        version_id = uuid4()

        Policy(
            id=policy_id,
            name=sample_policy_data["name"],
            description=sample_policy_data["description"],
            policy_type=sample_policy_data["policy_type"],
            status=PolicyStatus.DRAFT,
            current_version_id=version_id,
        )

        mock_db.refresh.side_effect = lambda obj: None

        # Mock the policy object to have an id after add
        def add_side_effect(obj):
            if isinstance(obj, Policy):
                obj.id = policy_id
            elif isinstance(obj, PolicyVersion):
                obj.id = version_id

        mock_db.add.side_effect = add_side_effect

        # Create policy
        with patch.object(service, "db", mock_db):
            # Manually set the attributes since we're mocking
            await service.create_policy(**sample_policy_data)

            # Verify database calls
            assert mock_db.add.call_count == 2  # Policy + PolicyVersion
            assert mock_db.flush.call_count == 2
            assert mock_db.commit.call_count == 1

    @pytest.mark.asyncio
    async def test_create_policy_sets_status_to_draft(self, service, mock_db, sample_policy_data):
        """Test that new policies start in DRAFT status."""
        policy_id = uuid4()
        version_id = uuid4()

        def add_side_effect(obj):
            if isinstance(obj, Policy):
                obj.id = policy_id
                # Verify status is DRAFT
                assert obj.status == PolicyStatus.DRAFT
            elif isinstance(obj, PolicyVersion):
                obj.id = version_id
                # Verify version is not active initially
                assert obj.is_active is False
                assert obj.tested is False

        mock_db.add.side_effect = add_side_effect
        mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", policy_id)

        await service.create_policy(**sample_policy_data)

    @pytest.mark.asyncio
    async def test_create_policy_creates_initial_version(
        self, service, mock_db, sample_policy_data
    ):
        """Test that creating policy also creates initial version."""
        version_calls = []

        def add_side_effect(obj):
            if isinstance(obj, Policy):
                obj.id = uuid4()
            elif isinstance(obj, PolicyVersion):
                obj.id = uuid4()
                version_calls.append(obj)
                # Verify version attributes
                assert obj.version == 1
                assert obj.content == sample_policy_data["initial_content"]
                assert obj.created_by == sample_policy_data["created_by"]

        mock_db.add.side_effect = add_side_effect
        mock_db.refresh.side_effect = lambda obj: None

        await service.create_policy(**sample_policy_data)

        assert len(version_calls) == 1

    # ===== create_version Tests =====

    @pytest.mark.asyncio
    async def test_create_version_increments_version_number(self, service, mock_db):
        """Test that create_version increments version number."""
        policy_id = uuid4()
        created_by = uuid4()

        # Mock database query result for max version
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 3  # Current max version is 3
        mock_db.execute.return_value = mock_result

        version_id = uuid4()

        def add_side_effect(obj):
            if isinstance(obj, PolicyVersion):
                obj.id = version_id
                # Verify new version is 4 (max + 1)
                assert obj.version == 4
                assert obj.policy_id == policy_id

        mock_db.add.side_effect = add_side_effect
        mock_db.refresh.side_effect = lambda obj: None

        await service.create_version(
            policy_id=policy_id,
            content="package sark\nallow = true",
            created_by=created_by,
        )

    @pytest.mark.asyncio
    async def test_create_version_first_version(self, service, mock_db):
        """Test creating first version when no versions exist."""
        policy_id = uuid4()
        created_by = uuid4()

        # Mock database query result for max version (None = no versions)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        def add_side_effect(obj):
            if isinstance(obj, PolicyVersion):
                obj.id = uuid4()
                # Verify first version is 1
                assert obj.version == 1

        mock_db.add.side_effect = add_side_effect
        mock_db.refresh.side_effect = lambda obj: None

        await service.create_version(
            policy_id=policy_id,
            content="package sark\ndefault allow = false",
            created_by=created_by,
        )

    @pytest.mark.asyncio
    async def test_create_version_with_notes(self, service, mock_db):
        """Test creating version with release notes."""
        policy_id = uuid4()
        created_by = uuid4()
        notes = "Fixed authorization bug for admin users"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 1
        mock_db.execute.return_value = mock_result

        def add_side_effect(obj):
            if isinstance(obj, PolicyVersion):
                obj.id = uuid4()
                assert obj.notes == notes

        mock_db.add.side_effect = add_side_effect
        mock_db.refresh.side_effect = lambda obj: None

        await service.create_version(
            policy_id=policy_id,
            content="package sark\nallow = true",
            created_by=created_by,
            notes=notes,
        )

    @pytest.mark.asyncio
    async def test_create_version_not_active_by_default(self, service, mock_db):
        """Test that new versions are not active by default."""
        policy_id = uuid4()
        created_by = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 2
        mock_db.execute.return_value = mock_result

        def add_side_effect(obj):
            if isinstance(obj, PolicyVersion):
                obj.id = uuid4()
                assert obj.is_active is False
                assert obj.tested is False

        mock_db.add.side_effect = add_side_effect
        mock_db.refresh.side_effect = lambda obj: None

        await service.create_version(
            policy_id=policy_id,
            content="package sark\nallow = true",
            created_by=created_by,
        )

    # ===== activate_version Tests =====

    @pytest.mark.asyncio
    async def test_activate_version_success(self, service, mock_db):
        """Test activating a policy version."""
        policy_id = uuid4()
        version_id = uuid4()

        # Mock version and policy retrieval
        mock_version = PolicyVersion(
            id=version_id,
            policy_id=policy_id,
            version=2,
            content="package sark\nallow = true",
            is_active=False,
            tested=True,
            created_by=uuid4(),
        )

        mock_policy = Policy(
            id=policy_id,
            name="test_policy",
            description="Test",
            policy_type=PolicyType.AUTHORIZATION,
            status=PolicyStatus.DRAFT,
        )

        # Setup get mock to return version and policy
        async def get_side_effect(model_class, id):
            if model_class == PolicyVersion:
                return mock_version
            elif model_class == Policy:
                return mock_policy
            return None

        mock_db.get = AsyncMock(side_effect=get_side_effect)
        mock_db.refresh.side_effect = lambda obj: None

        await service.activate_version(policy_id, version_id)

        # Verify version was activated
        assert mock_version.is_active is True

        # Verify policy was updated
        assert mock_policy.current_version_id == version_id
        assert mock_policy.status == PolicyStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_activate_version_not_found(self, service, mock_db):
        """Test activating a non-existent version raises error."""
        policy_id = uuid4()
        version_id = uuid4()

        # Mock get to return None (not found)
        mock_db.get = AsyncMock(return_value=None)

        with pytest.raises(ValueError) as exc_info:
            await service.activate_version(policy_id, version_id)

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_activate_version_policy_not_found(self, service, mock_db):
        """Test activating version when policy doesn't exist raises error."""
        policy_id = uuid4()
        version_id = uuid4()

        mock_version = PolicyVersion(
            id=version_id,
            policy_id=policy_id,
            version=1,
            content="package sark",
            is_active=False,
            tested=True,
            created_by=uuid4(),
        )

        # Return version but not policy
        async def get_side_effect(model_class, id):
            if model_class == PolicyVersion:
                return mock_version
            return None

        mock_db.get = AsyncMock(side_effect=get_side_effect)

        with pytest.raises(ValueError) as exc_info:
            await service.activate_version(policy_id, version_id)

        assert "Policy" in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()

    # ===== get_policy Tests =====

    @pytest.mark.asyncio
    async def test_get_policy_found(self, service, mock_db):
        """Test getting an existing policy."""
        policy_id = uuid4()
        mock_policy = Policy(
            id=policy_id,
            name="test_policy",
            description="Test",
            policy_type=PolicyType.AUTHORIZATION,
            status=PolicyStatus.ACTIVE,
        )

        mock_db.get = AsyncMock(return_value=mock_policy)

        policy = await service.get_policy(policy_id)

        assert policy is not None
        assert policy.id == policy_id
        assert policy.name == "test_policy"

    @pytest.mark.asyncio
    async def test_get_policy_not_found(self, service, mock_db):
        """Test getting a non-existent policy returns None."""
        policy_id = uuid4()
        mock_db.get = AsyncMock(return_value=None)

        policy = await service.get_policy(policy_id)

        assert policy is None

    # ===== get_policy_by_name Tests =====

    @pytest.mark.asyncio
    async def test_get_policy_by_name_found(self, service, mock_db):
        """Test getting policy by name."""
        mock_policy = Policy(
            id=uuid4(),
            name="authorization_policy",
            description="Main authorization policy",
            policy_type=PolicyType.AUTHORIZATION,
            status=PolicyStatus.ACTIVE,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_policy
        mock_db.execute.return_value = mock_result

        policy = await service.get_policy_by_name("authorization_policy")

        assert policy is not None
        assert policy.name == "authorization_policy"

    @pytest.mark.asyncio
    async def test_get_policy_by_name_not_found(self, service, mock_db):
        """Test getting non-existent policy by name returns None."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        policy = await service.get_policy_by_name("nonexistent")

        assert policy is None

    # ===== list_policies Tests =====

    @pytest.mark.asyncio
    async def test_list_policies_all(self, service, mock_db):
        """Test listing all policies without filters."""
        mock_policies = [
            Policy(
                id=uuid4(),
                name="policy1",
                description="First policy",
                policy_type=PolicyType.AUTHORIZATION,
                status=PolicyStatus.ACTIVE,
            ),
            Policy(
                id=uuid4(),
                name="policy2",
                description="Second policy",
                policy_type=PolicyType.VALIDATION,
                status=PolicyStatus.DRAFT,
            ),
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_policies
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        policies = await service.list_policies()

        assert len(policies) == 2
        assert policies[0].name == "policy1"
        assert policies[1].name == "policy2"

    @pytest.mark.asyncio
    async def test_list_policies_filter_by_type(self, service, mock_db):
        """Test listing policies filtered by type."""
        mock_policies = [
            Policy(
                id=uuid4(),
                name="auth_policy",
                description="Auth policy",
                policy_type=PolicyType.AUTHORIZATION,
                status=PolicyStatus.ACTIVE,
            ),
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_policies
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        policies = await service.list_policies(policy_type=PolicyType.AUTHORIZATION)

        assert len(policies) == 1
        assert policies[0].policy_type == PolicyType.AUTHORIZATION

    @pytest.mark.asyncio
    async def test_list_policies_filter_by_status(self, service, mock_db):
        """Test listing policies filtered by status."""
        mock_policies = [
            Policy(
                id=uuid4(),
                name="active_policy",
                description="Active policy",
                policy_type=PolicyType.AUTHORIZATION,
                status=PolicyStatus.ACTIVE,
            ),
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_policies
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        policies = await service.list_policies(status=PolicyStatus.ACTIVE)

        assert len(policies) == 1
        assert policies[0].status == PolicyStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_list_policies_filter_by_type_and_status(self, service, mock_db):
        """Test listing policies with multiple filters."""
        mock_policies = [
            Policy(
                id=uuid4(),
                name="active_auth_policy",
                description="Active auth policy",
                policy_type=PolicyType.AUTHORIZATION,
                status=PolicyStatus.ACTIVE,
            ),
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_policies
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        policies = await service.list_policies(
            policy_type=PolicyType.AUTHORIZATION,
            status=PolicyStatus.ACTIVE,
        )

        assert len(policies) == 1
        assert policies[0].policy_type == PolicyType.AUTHORIZATION
        assert policies[0].status == PolicyStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_list_policies_empty(self, service, mock_db):
        """Test listing policies when none exist."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        policies = await service.list_policies()

        assert len(policies) == 0
