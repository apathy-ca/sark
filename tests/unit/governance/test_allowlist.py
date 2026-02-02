"""
Unit tests for AllowlistService.
"""

from datetime import UTC, datetime, timedelta

import pytest

from sark.models.governance import AllowlistEntryType
from sark.services.governance.allowlist import AllowlistService
from sark.services.governance.exceptions import AllowlistError


class TestAllowlistService:
    """Tests for AllowlistService."""

    @pytest.mark.asyncio
    async def test_add_device(self, allowlist_service: AllowlistService):
        """Test adding a device to allowlist."""
        entry = await allowlist_service.add_device(
            "192.168.1.50",
            name="dad-laptop",
            reason="Admin device",
        )

        assert entry.identifier == "192.168.1.50"
        assert entry.name == "dad-laptop"
        assert entry.reason == "Admin device"
        assert entry.active is True
        assert entry.entry_type == "device"

    @pytest.mark.asyncio
    async def test_add_entry_ipv6(self, allowlist_service: AllowlistService):
        """Test adding IPv6 address to allowlist."""
        entry = await allowlist_service.add_entry(
            "2001:db8::1",
            AllowlistEntryType.DEVICE,
            name="ipv6-device",
        )

        assert entry.identifier == "2001:db8::1"
        assert entry.entry_type == "device"

    @pytest.mark.asyncio
    async def test_add_entry_mac(self, allowlist_service: AllowlistService):
        """Test adding MAC address to allowlist."""
        entry = await allowlist_service.add_entry(
            "AA:BB:CC:DD:EE:FF",
            AllowlistEntryType.MAC,
            name="mac-device",
        )

        assert entry.identifier == "AA:BB:CC:DD:EE:FF"
        assert entry.entry_type == "mac"

    @pytest.mark.asyncio
    async def test_add_entry_user(self, allowlist_service: AllowlistService):
        """Test adding user to allowlist."""
        entry = await allowlist_service.add_entry(
            "user@example.com",
            AllowlistEntryType.USER,
            name="admin-user",
        )

        assert entry.identifier == "user@example.com"
        assert entry.entry_type == "user"

    @pytest.mark.asyncio
    async def test_add_duplicate_entry_raises_error(self, allowlist_service: AllowlistService):
        """Test adding duplicate entry raises error."""
        await allowlist_service.add_device("192.168.1.50")

        with pytest.raises(AllowlistError) as exc_info:
            await allowlist_service.add_device("192.168.1.50")

        assert "already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_add_entry_invalid_ip(self, allowlist_service: AllowlistService):
        """Test adding invalid IP address raises error."""
        with pytest.raises(AllowlistError) as exc_info:
            await allowlist_service.add_device("invalid-ip")

        assert "Invalid IP address" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_add_entry_invalid_mac(self, allowlist_service: AllowlistService):
        """Test adding invalid MAC address raises error."""
        with pytest.raises(AllowlistError) as exc_info:
            await allowlist_service.add_entry("invalid-mac", AllowlistEntryType.MAC)

        assert "Invalid MAC address" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_is_allowed_true(self, allowlist_service: AllowlistService):
        """Test is_allowed returns True for allowlisted device."""
        await allowlist_service.add_device("192.168.1.50")

        assert await allowlist_service.is_allowed("192.168.1.50") is True

    @pytest.mark.asyncio
    async def test_is_allowed_false(self, allowlist_service: AllowlistService):
        """Test is_allowed returns False for non-allowlisted device."""
        assert await allowlist_service.is_allowed("192.168.1.100") is False

    @pytest.mark.asyncio
    async def test_is_allowed_after_removal(self, allowlist_service: AllowlistService):
        """Test is_allowed returns False after removal."""
        await allowlist_service.add_device("192.168.1.50")
        await allowlist_service.remove_entry("192.168.1.50")

        assert await allowlist_service.is_allowed("192.168.1.50") is False

    @pytest.mark.asyncio
    async def test_is_allowed_expired_entry(self, allowlist_service: AllowlistService):
        """Test expired entries are not allowed."""
        past = datetime.now(UTC) - timedelta(hours=1)
        await allowlist_service.add_entry(
            "192.168.1.50",
            AllowlistEntryType.DEVICE,
            expires_at=past,
        )

        assert await allowlist_service.is_allowed("192.168.1.50") is False

    @pytest.mark.asyncio
    async def test_remove_entry(self, allowlist_service: AllowlistService):
        """Test removing entry from allowlist."""
        await allowlist_service.add_device("192.168.1.50")

        result = await allowlist_service.remove_entry("192.168.1.50")
        assert result is True

    @pytest.mark.asyncio
    async def test_remove_nonexistent_entry(self, allowlist_service: AllowlistService):
        """Test removing non-existent entry returns False."""
        result = await allowlist_service.remove_entry("192.168.1.50")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_entries(self, allowlist_service: AllowlistService):
        """Test listing allowlist entries."""
        await allowlist_service.add_device("192.168.1.50", name="device1")
        await allowlist_service.add_device("192.168.1.51", name="device2")

        entries = await allowlist_service.list_entries()
        assert len(entries) == 2

    @pytest.mark.asyncio
    async def test_list_entries_by_type(self, allowlist_service: AllowlistService):
        """Test filtering entries by type."""
        await allowlist_service.add_device("192.168.1.50")
        await allowlist_service.add_entry("user@example.com", AllowlistEntryType.USER)

        device_entries = await allowlist_service.list_entries(entry_type=AllowlistEntryType.DEVICE)
        assert len(device_entries) == 1
        assert device_entries[0].entry_type == "device"

    @pytest.mark.asyncio
    async def test_update_entry(self, allowlist_service: AllowlistService):
        """Test updating allowlist entry."""
        entry = await allowlist_service.add_device("192.168.1.50", name="old-name")

        updated = await allowlist_service.update_entry(entry.id, name="new-name")
        assert updated.name == "new-name"

    @pytest.mark.asyncio
    async def test_count_entries(self, allowlist_service: AllowlistService):
        """Test counting allowlist entries."""
        await allowlist_service.add_device("192.168.1.50")
        await allowlist_service.add_device("192.168.1.51")

        count = await allowlist_service.count_entries()
        assert count == 2

    @pytest.mark.asyncio
    async def test_reactivate_removed_entry(self, allowlist_service: AllowlistService):
        """Test reactivating a removed entry."""
        await allowlist_service.add_device("192.168.1.50", name="device1")
        await allowlist_service.remove_entry("192.168.1.50")

        # Re-add should reactivate
        entry = await allowlist_service.add_device("192.168.1.50", name="device1-new")
        assert entry.active is True
        assert await allowlist_service.is_allowed("192.168.1.50") is True

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, allowlist_service: AllowlistService):
        """Test cleanup of expired entries."""
        past = datetime.now(UTC) - timedelta(hours=1)
        await allowlist_service.add_entry(
            "192.168.1.50",
            AllowlistEntryType.DEVICE,
            expires_at=past,
        )

        count = await allowlist_service.cleanup_expired()
        assert count == 1
