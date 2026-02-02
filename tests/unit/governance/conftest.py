"""
Pytest fixtures for governance unit tests.
"""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from sark.models.governance import GovernanceBase
from sark.services.governance.allowlist import AllowlistService
from sark.services.governance.consent import ConsentService
from sark.services.governance.emergency import EmergencyService
from sark.services.governance.enforcement import EnforcementService
from sark.services.governance.override import OverrideService
from sark.services.governance.time_rules import TimeRulesService


@pytest_asyncio.fixture
async def db_engine():
    """Create async SQLite engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(GovernanceBase.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for testing."""
    async_session = sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session


@pytest_asyncio.fixture
async def allowlist_service(db_session: AsyncSession) -> AllowlistService:
    """Create allowlist service for testing."""
    return AllowlistService(db_session)


@pytest_asyncio.fixture
async def time_rules_service(db_session: AsyncSession) -> TimeRulesService:
    """Create time rules service for testing."""
    return TimeRulesService(db_session)


@pytest_asyncio.fixture
async def emergency_service(db_session: AsyncSession) -> EmergencyService:
    """Create emergency service for testing."""
    return EmergencyService(db_session)


@pytest_asyncio.fixture
async def consent_service(db_session: AsyncSession) -> ConsentService:
    """Create consent service for testing."""
    return ConsentService(db_session)


@pytest_asyncio.fixture
async def override_service(db_session: AsyncSession) -> OverrideService:
    """Create override service for testing."""
    return OverrideService(db_session)


@pytest_asyncio.fixture
async def enforcement_service(
    db_session: AsyncSession,
    allowlist_service: AllowlistService,
    time_rules_service: TimeRulesService,
    emergency_service: EmergencyService,
    override_service: OverrideService,
) -> EnforcementService:
    """Create enforcement service for testing."""
    return EnforcementService(
        db=db_session,
        allowlist=allowlist_service,
        time_rules=time_rules_service,
        emergency=emergency_service,
        override=override_service,
    )
