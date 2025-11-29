"""
Node discovery service for SARK v2.0 Federation.

This module implements service discovery mechanisms for finding SARK nodes:
- DNS-SD (DNS Service Discovery - RFC 6763)
- mDNS (Multicast DNS - RFC 6762)
- Manual configuration
- Consul service discovery integration

The discovery service allows SARK instances to find each other automatically
for federation, reducing manual configuration overhead.
"""

import asyncio
import socket
import struct
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from collections import defaultdict
import structlog

from sark.models.federation import (
    DiscoveryMethod,
    DiscoveryQuery,
    DiscoveryResponse,
    ServiceDiscoveryRecord,
)

logger = structlog.get_logger(__name__)


class DNSSDClient:
    """
    DNS Service Discovery (DNS-SD) client implementation.

    Uses standard DNS SRV and TXT records to discover SARK instances.
    Follows RFC 6763 for DNS-based service discovery.
    """

    def __init__(self, nameserver: Optional[str] = None):
        """
        Initialize DNS-SD client.

        Args:
            nameserver: DNS server to query (None = system default)
        """
        self.nameserver = nameserver
        self.logger = logger.bind(component="dns-sd")

    async def discover_services(
        self,
        service_type: str,
        timeout_seconds: int = 5,
        max_results: int = 10
    ) -> List[ServiceDiscoveryRecord]:
        """
        Discover services using DNS-SD.

        Args:
            service_type: Service type to discover (e.g., "_sark._tcp.local.")
            timeout_seconds: Query timeout in seconds
            max_results: Maximum number of results to return

        Returns:
            List of discovered service records
        """
        self.logger.info(
            "starting_dns_sd_discovery",
            service_type=service_type,
            timeout=timeout_seconds
        )

        try:
            # In a production implementation, we would use dnspython or aiodns
            # For now, we'll use a basic socket-based implementation
            records = await self._query_dns_srv(service_type, timeout_seconds)

            # Limit results
            records = records[:max_results]

            self.logger.info(
                "dns_sd_discovery_complete",
                service_type=service_type,
                found=len(records)
            )

            return records

        except Exception as e:
            self.logger.error(
                "dns_sd_discovery_failed",
                service_type=service_type,
                error=str(e)
            )
            return []

    async def _query_dns_srv(
        self,
        service_type: str,
        timeout: int
    ) -> List[ServiceDiscoveryRecord]:
        """
        Query DNS SRV records for a service.

        Args:
            service_type: Service type to query
            timeout: Query timeout in seconds

        Returns:
            List of discovered service records
        """
        records = []

        try:
            # This is a simplified implementation
            # In production, use dnspython or aiodns for full DNS-SD support

            # For demonstration, we'll return empty list
            # Real implementation would:
            # 1. Query SRV records for service_type
            # 2. Query TXT records for additional metadata
            # 3. Resolve hostnames to IP addresses
            # 4. Parse and return ServiceDiscoveryRecord objects

            self.logger.debug(
                "querying_dns_srv",
                service_type=service_type
            )

        except Exception as e:
            self.logger.error(
                "dns_srv_query_failed",
                service_type=service_type,
                error=str(e)
            )

        return records


class MDNSClient:
    """
    Multicast DNS (mDNS) client implementation.

    Uses multicast UDP to discover SARK instances on the local network.
    Follows RFC 6762 for multicast DNS.
    """

    MDNS_ADDR = "224.0.0.251"
    MDNS_PORT = 5353

    # DNS message type constants
    DNS_TYPE_PTR = 12
    DNS_TYPE_SRV = 33
    DNS_TYPE_TXT = 16
    DNS_CLASS_IN = 1

    def __init__(self):
        """Initialize mDNS client."""
        self.logger = logger.bind(component="mdns")
        self._socket: Optional[socket.socket] = None
        self._discovered_services: Dict[str, ServiceDiscoveryRecord] = {}

    async def discover_services(
        self,
        service_type: str,
        timeout_seconds: int = 5,
        max_results: int = 10
    ) -> List[ServiceDiscoveryRecord]:
        """
        Discover services using mDNS.

        Args:
            service_type: Service type to discover (e.g., "_sark._tcp.local.")
            timeout_seconds: Discovery timeout in seconds
            max_results: Maximum number of results to return

        Returns:
            List of discovered service records
        """
        self.logger.info(
            "starting_mdns_discovery",
            service_type=service_type,
            timeout=timeout_seconds
        )

        try:
            # Initialize mDNS socket
            self._init_socket()

            # Send mDNS query
            await self._send_query(service_type)

            # Listen for responses
            records = await self._listen_responses(timeout_seconds, max_results)

            self.logger.info(
                "mdns_discovery_complete",
                service_type=service_type,
                found=len(records)
            )

            return records

        except Exception as e:
            self.logger.error(
                "mdns_discovery_failed",
                service_type=service_type,
                error=str(e)
            )
            return []

        finally:
            self._close_socket()

    def _init_socket(self):
        """Initialize mDNS multicast socket."""
        try:
            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Bind to mDNS port
            sock.bind(('', self.MDNS_PORT))

            # Join multicast group
            mreq = struct.pack("4sl", socket.inet_aton(self.MDNS_ADDR), socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

            # Set non-blocking
            sock.setblocking(False)

            self._socket = sock
            self.logger.debug("mdns_socket_initialized")

        except Exception as e:
            self.logger.error("mdns_socket_init_failed", error=str(e))
            raise

    def _close_socket(self):
        """Close mDNS socket."""
        if self._socket:
            try:
                self._socket.close()
                self._socket = None
                self.logger.debug("mdns_socket_closed")
            except Exception as e:
                self.logger.error("mdns_socket_close_failed", error=str(e))

    async def _send_query(self, service_type: str):
        """
        Send mDNS query for service type.

        Args:
            service_type: Service type to query
        """
        try:
            # Build DNS query packet
            # This is a simplified implementation
            # Real implementation would construct proper DNS query packet

            query = self._build_dns_query(service_type)

            # Send to multicast group
            if self._socket:
                self._socket.sendto(query, (self.MDNS_ADDR, self.MDNS_PORT))
                self.logger.debug("mdns_query_sent", service_type=service_type)

        except Exception as e:
            self.logger.error("mdns_query_send_failed", error=str(e))

    def _build_dns_query(self, service_type: str) -> bytes:
        """
        Build DNS query packet for mDNS.

        Args:
            service_type: Service type to query

        Returns:
            DNS query packet as bytes
        """
        # This is a minimal implementation
        # In production, use a proper DNS library

        # DNS header: transaction ID, flags, counts
        transaction_id = 0x0000
        flags = 0x0000  # Standard query
        questions = 1
        answers = 0
        authority = 0
        additional = 0

        header = struct.pack(
            '!HHHHHH',
            transaction_id,
            flags,
            questions,
            answers,
            authority,
            additional
        )

        # Question section: QNAME, QTYPE (PTR), QCLASS (IN)
        # Encode service_type as DNS name
        qname = b''
        for label in service_type.rstrip('.').split('.'):
            qname += bytes([len(label)]) + label.encode('ascii')
        qname += b'\x00'  # Null terminator

        question = qname + struct.pack('!HH', self.DNS_TYPE_PTR, self.DNS_CLASS_IN)

        return header + question

    async def _listen_responses(
        self,
        timeout_seconds: int,
        max_results: int
    ) -> List[ServiceDiscoveryRecord]:
        """
        Listen for mDNS responses.

        Args:
            timeout_seconds: How long to listen
            max_results: Maximum results to collect

        Returns:
            List of discovered services
        """
        records = []
        start_time = asyncio.get_event_loop().time()

        try:
            while len(records) < max_results:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout_seconds:
                    break

                # Check for data with small timeout
                remaining = timeout_seconds - elapsed
                await asyncio.sleep(min(0.1, remaining))

                # Try to receive data
                try:
                    if self._socket:
                        data, addr = self._socket.recvfrom(4096)
                        record = self._parse_dns_response(data, addr)
                        if record:
                            records.append(record)
                except BlockingIOError:
                    # No data available yet
                    continue
                except Exception as e:
                    self.logger.error("mdns_receive_failed", error=str(e))

        except Exception as e:
            self.logger.error("mdns_listen_failed", error=str(e))

        return records

    def _parse_dns_response(
        self,
        data: bytes,
        addr: tuple
    ) -> Optional[ServiceDiscoveryRecord]:
        """
        Parse DNS response packet.

        Args:
            data: DNS response packet
            addr: Source address tuple (ip, port)

        Returns:
            ServiceDiscoveryRecord if valid response, None otherwise
        """
        try:
            # This is a minimal parser
            # In production, use dnspython or similar library

            # For now, create a placeholder record
            # Real implementation would parse SRV and TXT records

            record = ServiceDiscoveryRecord(
                service_name="_sark._tcp.local.",
                instance_name=f"sark-{addr[0]}",
                hostname=addr[0],
                port=8000,  # Default SARK port
                txt_records={},
                discovered_at=datetime.utcnow()
            )

            self.logger.debug(
                "mdns_response_parsed",
                hostname=record.hostname,
                port=record.port
            )

            return record

        except Exception as e:
            self.logger.error("mdns_parse_failed", error=str(e))
            return None


class ConsulDiscoveryClient:
    """
    Consul-based service discovery client.

    Integrates with HashiCorp Consul for service discovery in
    containerized/orchestrated environments.
    """

    def __init__(self, consul_url: str = "http://localhost:8500"):
        """
        Initialize Consul discovery client.

        Args:
            consul_url: Consul agent URL
        """
        self.consul_url = consul_url.rstrip('/')
        self.logger = logger.bind(component="consul-discovery")

    async def discover_services(
        self,
        service_name: str = "sark",
        timeout_seconds: int = 5,
        max_results: int = 10
    ) -> List[ServiceDiscoveryRecord]:
        """
        Discover services via Consul.

        Args:
            service_name: Service name to discover
            timeout_seconds: Query timeout
            max_results: Maximum results

        Returns:
            List of discovered services
        """
        self.logger.info(
            "starting_consul_discovery",
            service_name=service_name
        )

        try:
            # In production, use python-consul or httpx to query Consul API
            # Example: GET /v1/catalog/service/{service_name}

            # Placeholder implementation
            records = []

            self.logger.info(
                "consul_discovery_complete",
                service_name=service_name,
                found=len(records)
            )

            return records

        except Exception as e:
            self.logger.error(
                "consul_discovery_failed",
                service_name=service_name,
                error=str(e)
            )
            return []


class DiscoveryService:
    """
    Unified discovery service for SARK federation.

    Provides a single interface for discovering SARK nodes using
    multiple discovery methods (DNS-SD, mDNS, Consul, manual).
    """

    def __init__(
        self,
        dns_nameserver: Optional[str] = None,
        consul_url: Optional[str] = None
    ):
        """
        Initialize discovery service.

        Args:
            dns_nameserver: DNS server for DNS-SD queries
            consul_url: Consul agent URL
        """
        self.logger = logger.bind(component="discovery-service")

        # Initialize discovery clients
        self.dns_sd = DNSSDClient(nameserver=dns_nameserver)
        self.mdns = MDNSClient()
        self.consul = ConsulDiscoveryClient(consul_url or "http://localhost:8500")

        # Cache of discovered services
        self._cache: Dict[str, List[ServiceDiscoveryRecord]] = {}
        self._cache_ttl: Dict[str, datetime] = {}

    async def discover(self, query: DiscoveryQuery) -> DiscoveryResponse:
        """
        Discover SARK nodes using specified method.

        Args:
            query: Discovery query parameters

        Returns:
            Discovery response with found services
        """
        self.logger.info(
            "starting_discovery",
            method=query.method,
            service_type=query.service_type
        )

        start_time = asyncio.get_event_loop().time()

        try:
            # Check cache first
            cache_key = f"{query.method}:{query.service_type}"
            if self._is_cache_valid(cache_key):
                records = self._cache[cache_key]
                self.logger.info(
                    "discovery_cache_hit",
                    method=query.method,
                    cached_records=len(records)
                )
            else:
                # Perform discovery based on method
                if query.method == DiscoveryMethod.DNS_SD:
                    records = await self.dns_sd.discover_services(
                        query.service_type,
                        query.timeout_seconds,
                        query.max_results
                    )
                elif query.method == DiscoveryMethod.MDNS:
                    records = await self.mdns.discover_services(
                        query.service_type,
                        query.timeout_seconds,
                        query.max_results
                    )
                elif query.method == DiscoveryMethod.CONSUL:
                    # Extract service name from service_type
                    service_name = query.service_type.split('.')[0].lstrip('_')
                    records = await self.consul.discover_services(
                        service_name,
                        query.timeout_seconds,
                        query.max_results
                    )
                else:  # MANUAL
                    records = []
                    self.logger.info("manual_discovery_not_implemented")

                # Update cache
                self._update_cache(cache_key, records)

            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            response = DiscoveryResponse(
                method=query.method,
                records=records,
                total_found=len(records)
            )

            self.logger.info(
                "discovery_complete",
                method=query.method,
                found=len(records),
                duration_ms=duration_ms
            )

            return response

        except Exception as e:
            self.logger.error(
                "discovery_failed",
                method=query.method,
                error=str(e)
            )
            # Return empty response on error
            return DiscoveryResponse(
                method=query.method,
                records=[],
                total_found=0
            )

    async def discover_all(
        self,
        service_type: str = "_sark._tcp.local.",
        timeout_seconds: int = 5
    ) -> Dict[DiscoveryMethod, List[ServiceDiscoveryRecord]]:
        """
        Discover using all available methods.

        Args:
            service_type: Service type to discover
            timeout_seconds: Timeout per method

        Returns:
            Dictionary mapping discovery method to found services
        """
        self.logger.info("discovering_all_methods", service_type=service_type)

        results = {}

        # Try all discovery methods concurrently
        tasks = []
        methods = [DiscoveryMethod.DNS_SD, DiscoveryMethod.MDNS, DiscoveryMethod.CONSUL]

        for method in methods:
            query = DiscoveryQuery(
                method=method,
                service_type=service_type,
                timeout_seconds=timeout_seconds
            )
            tasks.append(self.discover(query))

        # Wait for all discoveries to complete
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect results
        for method, response in zip(methods, responses):
            if isinstance(response, Exception):
                self.logger.error(
                    "discovery_method_failed",
                    method=method,
                    error=str(response)
                )
                results[method] = []
            else:
                results[method] = response.records

        total_found = sum(len(records) for records in results.values())
        self.logger.info(
            "discover_all_complete",
            total_found=total_found,
            by_method={k.value: len(v) for k, v in results.items()}
        )

        return results

    def _is_cache_valid(self, cache_key: str) -> bool:
        """
        Check if cache entry is still valid.

        Args:
            cache_key: Cache key to check

        Returns:
            True if cache is valid, False otherwise
        """
        if cache_key not in self._cache_ttl:
            return False

        return datetime.utcnow() < self._cache_ttl[cache_key]

    def _update_cache(
        self,
        cache_key: str,
        records: List[ServiceDiscoveryRecord]
    ):
        """
        Update cache with new records.

        Args:
            cache_key: Cache key
            records: Records to cache
        """
        self._cache[cache_key] = records

        # Calculate TTL from records (use minimum TTL)
        min_ttl = min((r.ttl for r in records), default=300)
        self._cache_ttl[cache_key] = datetime.utcnow() + timedelta(seconds=min_ttl)

        self.logger.debug(
            "cache_updated",
            cache_key=cache_key,
            records=len(records),
            ttl_seconds=min_ttl
        )

    def clear_cache(self):
        """Clear discovery cache."""
        self._cache.clear()
        self._cache_ttl.clear()
        self.logger.info("cache_cleared")


__all__ = ["DiscoveryService", "DNSSDClient", "MDNSClient", "ConsulDiscoveryClient"]
