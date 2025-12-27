"""Unit tests for Federation Discovery Service."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sark.models.federation import DiscoveryMethod, DiscoveryQuery, ServiceDiscoveryRecord
from sark.services.federation.discovery import (
    ConsulDiscoveryClient,
    DNSSDClient,
    DiscoveryService,
    MDNSClient,
)


class TestDNSSDClient:
    """Test DNS-SD client."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test DNS-SD client initialization."""
        client = DNSSDClient()
        assert client.nameserver is None

    @pytest.mark.asyncio
    async def test_initialization_with_nameserver(self):
        """Test DNS-SD client initialization with custom nameserver."""
        client = DNSSDClient(nameserver="8.8.8.8")
        assert client.nameserver == "8.8.8.8"

    @pytest.mark.asyncio
    async def test_discover_services_empty(self):
        """Test service discovery returns empty list."""
        client = DNSSDClient()
        records = await client.discover_services("_sark._tcp.local.")
        assert records == []

    @pytest.mark.asyncio
    async def test_discover_services_with_timeout(self):
        """Test service discovery with custom timeout."""
        client = DNSSDClient()
        records = await client.discover_services("_sark._tcp.local.", timeout_seconds=10)
        assert isinstance(records, list)

    @pytest.mark.asyncio
    async def test_discover_services_max_results(self):
        """Test service discovery respects max_results."""
        client = DNSSDClient()
        # Mock _query_dns_srv to return more than max_results
        mock_records = [
            ServiceDiscoveryRecord(
                service_name="_sark._tcp",
                instance_name=f"test-{i}",
                hostname=f"host{i}.local",
                port=8080 + i,
            )
            for i in range(20)
        ]
        client._query_dns_srv = AsyncMock(return_value=mock_records)

        records = await client.discover_services("_sark._tcp.local.", max_results=5)
        assert len(records) == 5

    @pytest.mark.asyncio
    async def test_discover_services_exception_handling(self):
        """Test service discovery handles exceptions."""
        client = DNSSDClient()
        client._query_dns_srv = AsyncMock(side_effect=Exception("Network error"))

        records = await client.discover_services("_sark._tcp.local.")
        assert records == []


class TestMDNSClient:
    """Test mDNS client."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test mDNS client initialization."""
        client = MDNSClient()
        assert client._socket is None
        assert client._discovered_services == {}

    @pytest.mark.asyncio
    async def test_mdns_constants(self):
        """Test mDNS constants are set correctly."""
        assert MDNSClient.MDNS_ADDR == "224.0.0.251"
        assert MDNSClient.MDNS_PORT == 5353
        assert MDNSClient.DNS_TYPE_PTR == 12
        assert MDNSClient.DNS_TYPE_SRV == 33
        assert MDNSClient.DNS_TYPE_TXT == 16
        assert MDNSClient.DNS_CLASS_IN == 1

    @pytest.mark.asyncio
    async def test_discover_services_exception_handling(self):
        """Test mDNS discovery handles exceptions gracefully."""
        client = MDNSClient()
        # Mock _init_socket to raise exception
        client._init_socket = MagicMock(side_effect=Exception("Socket error"))

        records = await client.discover_services("_sark._tcp.local.")
        assert records == []

    @pytest.mark.asyncio
    async def test_discover_services_closes_socket(self):
        """Test mDNS discovery closes socket even on error."""
        client = MDNSClient()
        client._init_socket = MagicMock()
        client._send_query = AsyncMock(side_effect=Exception("Send error"))
        client._close_socket = MagicMock()

        await client.discover_services("_sark._tcp.local.")
        client._close_socket.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_socket_when_none(self):
        """Test closing socket when it's None doesn't error."""
        client = MDNSClient()
        client._socket = None
        # Should not raise exception
        client._close_socket()

    @pytest.mark.asyncio
    async def test_close_socket_when_exists(self):
        """Test closing socket when it exists."""
        client = MDNSClient()
        mock_socket = MagicMock()
        client._socket = mock_socket

        client._close_socket()
        mock_socket.close.assert_called_once()
        assert client._socket is None


class TestConsulDiscoveryClient:
    """Test Consul discovery client."""

    @pytest.mark.asyncio
    async def test_initialization_default(self):
        """Test Consul client initialization with defaults."""
        client = ConsulDiscoveryClient()
        assert client.consul_url == "http://localhost:8500"

    @pytest.mark.asyncio
    async def test_initialization_custom(self):
        """Test Consul client initialization with custom values."""
        client = ConsulDiscoveryClient(consul_url="http://consul.example.com:8600")
        assert client.consul_url == "http://consul.example.com:8600"

    @pytest.mark.asyncio
    async def test_discover_services_empty(self):
        """Test Consul service discovery returns empty list."""
        client = ConsulDiscoveryClient()
        # Current implementation returns empty list
        records = await client.discover_services("sark")
        assert records == []

    @pytest.mark.asyncio
    async def test_discover_services_http_error(self):
        """Test Consul discovery handles HTTP errors."""
        client = ConsulDiscoveryClient()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = Exception("HTTP 500")
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            records = await client.discover_services("sark")
            assert records == []

    @pytest.mark.asyncio
    async def test_discover_services_network_error(self):
        """Test Consul discovery handles network errors."""
        client = ConsulDiscoveryClient()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Connection refused")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            records = await client.discover_services("sark")
            assert records == []

    @pytest.mark.asyncio
    async def test_discover_services_with_timeout(self):
        """Test Consul discovery with custom timeout."""
        client = ConsulDiscoveryClient()
        records = await client.discover_services("sark", timeout_seconds=10)
        assert isinstance(records, list)


class TestDiscoveryService:
    """Test unified discovery service."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test discovery service initialization."""
        service = DiscoveryService()
        assert service.dns_sd is not None
        assert service.mdns is not None
        assert service.consul is not None

    @pytest.mark.asyncio
    async def test_discover_mdns(self):
        """Test discovery using mDNS method."""
        service = DiscoveryService()
        query = DiscoveryQuery(
            method=DiscoveryMethod.MDNS,
            service_type="_sark._tcp.local.",
            timeout_seconds=5,
            max_results=10,
        )

        mock_records = [
            ServiceDiscoveryRecord(
                service_name="_sark._tcp",
                instance_name="test-1",
                hostname="host1.local",
                port=8080,
            )
        ]

        service.mdns.discover_services = AsyncMock(return_value=mock_records)

        response = await service.discover(query)
        assert response.method == DiscoveryMethod.MDNS
        assert len(response.records) == 1
        assert response.total_found == 1
        service.mdns.discover_services.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_discover_dns_sd(self):
        """Test discovery using DNS-SD method."""
        service = DiscoveryService()
        query = DiscoveryQuery(
            method=DiscoveryMethod.DNS_SD,
            service_type="_sark._tcp.local.",
        )

        mock_records = [
            ServiceDiscoveryRecord(
                service_name="_sark._tcp",
                instance_name="test-1",
                hostname="host1.example.com",
                port=8443,
            )
        ]

        service.dns_sd.discover_services = AsyncMock(return_value=mock_records)

        response = await service.discover(query)
        assert response.method == DiscoveryMethod.DNS_SD
        assert len(response.records) == 1

    @pytest.mark.asyncio
    async def test_discover_consul(self):
        """Test discovery using Consul method."""
        service = DiscoveryService()
        query = DiscoveryQuery(
            method=DiscoveryMethod.CONSUL,
            service_type="sark",
        )

        mock_records = [
            ServiceDiscoveryRecord(
                service_name="sark",
                instance_name="sark-1",
                hostname="10.0.1.100",
                port=8443,
            )
        ]

        service.consul.discover_services = AsyncMock(return_value=mock_records)

        response = await service.discover(query)
        assert response.method == DiscoveryMethod.CONSUL
        assert len(response.records) == 1

    @pytest.mark.asyncio
    async def test_discover_manual_returns_empty(self):
        """Test that manual discovery returns empty list."""
        service = DiscoveryService()
        query = DiscoveryQuery(method=DiscoveryMethod.MANUAL)

        response = await service.discover(query)
        assert response.method == DiscoveryMethod.MANUAL
        assert len(response.records) == 0

    @pytest.mark.asyncio
    async def test_discover_all_methods(self):
        """Test discovering services using all methods."""
        service = DiscoveryService()

        mdns_records = [
            ServiceDiscoveryRecord(
                service_name="_sark._tcp",
                instance_name="mdns-1",
                hostname="mdns.local",
                port=8080,
            )
        ]
        dns_records = [
            ServiceDiscoveryRecord(
                service_name="_sark._tcp",
                instance_name="dns-1",
                hostname="dns.example.com",
                port=8443,
            )
        ]
        consul_records = [
            ServiceDiscoveryRecord(
                service_name="sark",
                instance_name="consul-1",
                hostname="10.0.1.100",
                port=8443,
            )
        ]

        service.mdns.discover_services = AsyncMock(return_value=mdns_records)
        service.dns_sd.discover_services = AsyncMock(return_value=dns_records)
        service.consul.discover_services = AsyncMock(return_value=consul_records)

        all_records = await service.discover_all("_sark._tcp.local.")
        assert len(all_records) == 3
        # Verify contains all methods
        assert DiscoveryMethod.MDNS in all_records
        assert DiscoveryMethod.DNS_SD in all_records
        assert DiscoveryMethod.CONSUL in all_records

    @pytest.mark.asyncio
    async def test_discover_all_partial_failures(self):
        """Test discover_all continues when some methods fail."""
        service = DiscoveryService()

        success_record = ServiceDiscoveryRecord(
            service_name="_sark._tcp",
            instance_name="success",
            hostname="success.local",
            port=8080,
        )

        service.mdns.discover_services = AsyncMock(side_effect=Exception("mDNS failed"))
        service.dns_sd.discover_services = AsyncMock(return_value=[success_record])
        service.consul.discover_services = AsyncMock(side_effect=Exception("Consul failed"))

        all_records = await service.discover_all("_sark._tcp.local.")
        # Should return dict with all methods
        assert isinstance(all_records, dict)
        assert DiscoveryMethod.DNS_SD in all_records

    @pytest.mark.asyncio
    async def test_discover_response_includes_timestamp(self):
        """Test that discovery response includes timestamp."""
        service = DiscoveryService()
        query = DiscoveryQuery(method=DiscoveryMethod.DNS_SD)

        service.dns_sd.discover_services = AsyncMock(return_value=[])

        response = await service.discover(query)
        assert response.discovered_at is not None
        assert isinstance(response.discovered_at, datetime)

    @pytest.mark.asyncio
    async def test_clear_cache(self):
        """Test clearing discovery cache."""
        service = DiscoveryService()
        service._cache["test"] = []
        service._cache_ttl["test"] = datetime.utcnow()

        service.clear_cache()
        assert len(service._cache) == 0
        assert len(service._cache_ttl) == 0
