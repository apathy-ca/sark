"""MCP Server discovery and registration service."""

from typing import Any
from uuid import UUID

import consul
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from sark.api.pagination import CursorPaginator, PaginationParams
from sark.config import get_settings
from sark.models.mcp_server import MCPServer, MCPTool, ServerStatus, TransportType

logger = structlog.get_logger()
settings = get_settings()


class DiscoveryService:
    """Service for discovering and managing MCP servers."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize discovery service."""
        self.db = db
        self.consul_client = consul.Consul(
            host=settings.consul_host,
            port=settings.consul_port,
            scheme=settings.consul_scheme,
            token=settings.consul_token,
        )

    async def register_server(
        self,
        name: str,
        transport: TransportType,
        mcp_version: str,
        capabilities: list[str],
        tools: list[dict[str, Any]],
        owner_id: UUID | None = None,
        team_id: UUID | None = None,
        endpoint: str | None = None,
        command: str | None = None,
        description: str | None = None,
        sensitivity_level: str = "medium",
        signature: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MCPServer:
        """
        Register a new MCP server.

        Args:
            name: Server name
            transport: Transport type (http, stdio, sse)
            mcp_version: MCP protocol version
            capabilities: List of capabilities
            tools: List of tool definitions
            owner_id: Owner user ID
            team_id: Managing team ID
            endpoint: HTTP/SSE endpoint
            command: stdio command
            description: Server description
            sensitivity_level: Sensitivity level
            signature: Cryptographic signature
            tags: Server tags
            metadata: Additional metadata

        Returns:
            Registered MCP server
        """
        # Create server record
        server = MCPServer(
            name=name,
            description=description,
            transport=transport,
            endpoint=endpoint,
            command=command,
            mcp_version=mcp_version,
            capabilities=capabilities,
            sensitivity_level=sensitivity_level,
            signature=signature,
            status=ServerStatus.REGISTERED,
            owner_id=owner_id,
            team_id=team_id,
            tags=tags or [],
            extra_metadata=metadata or {},
        )

        self.db.add(server)
        await self.db.flush()

        # Create tool records with auto-detection if not specified
        from sark.services.discovery.tool_registry import ToolRegistry

        tool_registry = ToolRegistry(self.db)

        for tool_def in tools:
            # Auto-detect sensitivity if not provided
            tool_sensitivity = tool_def.get("sensitivity_level")
            if not tool_sensitivity:
                # Import here to avoid circular dependency
                detected = await tool_registry.detect_sensitivity(
                    tool_name=tool_def["name"],
                    tool_description=tool_def.get("description"),
                    parameters=tool_def.get("parameters", {}),
                )
                tool_sensitivity = detected.value
            elif isinstance(tool_sensitivity, str):
                # Convert string to enum if needed
                tool_sensitivity = tool_sensitivity

            tool = MCPTool(
                server_id=server.id,
                name=tool_def["name"],
                description=tool_def.get("description"),
                parameters=tool_def.get("parameters", {}),
                sensitivity_level=tool_sensitivity,
                signature=tool_def.get("signature"),
                requires_approval=tool_def.get("requires_approval", False),
                extra_metadata=tool_def.get("metadata", {}),
            )
            self.db.add(tool)

        await self.db.commit()
        await self.db.refresh(server)

        # Register with Consul for service discovery
        await self._register_consul(server)

        logger.info(
            "server_registered",
            server_id=str(server.id),
            name=name,
            transport=transport,
            tool_count=len(tools),
        )

        return server

    async def update_server_status(
        self,
        server_id: UUID,
        status: ServerStatus,
    ) -> MCPServer:
        """
        Update server status.

        Args:
            server_id: Server ID
            status: New status

        Returns:
            Updated server
        """
        server = await self.db.get(MCPServer, server_id)
        if not server:
            raise ValueError(f"Server {server_id} not found")

        server.status = status
        await self.db.commit()
        await self.db.refresh(server)

        logger.info(
            "server_status_updated",
            server_id=str(server_id),
            status=status,
        )

        return server

    async def get_server(self, server_id: UUID) -> MCPServer | None:
        """Get server by ID."""
        return await self.db.get(MCPServer, server_id)

    async def get_server_by_name(self, name: str) -> MCPServer | None:
        """Get server by name."""
        result = await self.db.execute(select(MCPServer).where(MCPServer.name == name))
        return result.scalar_one_or_none()

    async def list_servers(
        self,
        status: ServerStatus | None = None,
        owner_id: UUID | None = None,
        team_id: UUID | None = None,
    ) -> list[MCPServer]:
        """
        List servers with optional filters.

        Args:
            status: Filter by status
            owner_id: Filter by owner
            team_id: Filter by team

        Returns:
            List of MCP servers
        """
        query = select(MCPServer)

        if status:
            query = query.where(MCPServer.status == status)
        if owner_id:
            query = query.where(MCPServer.owner_id == owner_id)
        if team_id:
            query = query.where(MCPServer.team_id == team_id)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_servers_paginated(
        self,
        pagination: PaginationParams,
        status: ServerStatus | None = None,
        owner_id: UUID | None = None,
        team_id: UUID | None = None,
        count_total: bool = False,
    ) -> tuple[list[MCPServer], str | None, bool, int | None]:
        """
        List servers with pagination and optional filters.

        Args:
            pagination: Pagination parameters
            status: Filter by status
            owner_id: Filter by owner
            team_id: Filter by team
            count_total: Whether to count total items (expensive)

        Returns:
            Tuple of (servers, next_cursor, has_more, total)
        """
        query = select(MCPServer)

        if status:
            query = query.where(MCPServer.status == status)
        if owner_id:
            query = query.where(MCPServer.owner_id == owner_id)
        if team_id:
            query = query.where(MCPServer.team_id == team_id)

        return await CursorPaginator.paginate(
            db=self.db,
            query=query,
            cursor_column=MCPServer.created_at,
            params=pagination,
            count_total=count_total,
        )

    async def get_server_tools(self, server_id: UUID) -> list[MCPTool]:
        """
        Get all tools for a server.

        Args:
            server_id: Server ID

        Returns:
            List of tools
        """
        result = await self.db.execute(select(MCPTool).where(MCPTool.server_id == server_id))
        return list(result.scalars().all())

    async def _register_consul(self, server: MCPServer) -> None:
        """
        Register server with Consul for service discovery.

        Args:
            server: MCP server to register
        """
        try:
            consul_id = f"mcp-{server.name}-{server.id}"

            service_config = {
                "id": consul_id,
                "name": f"mcp-{server.name}",
                "tags": ["mcp-server", *server.tags],
                "meta": {
                    "server_id": str(server.id),
                    "transport": server.transport.value,
                    "sensitivity": server.sensitivity_level.value,
                },
            }

            # Add health check for HTTP servers
            if server.transport == TransportType.HTTP and server.health_endpoint:
                service_config["check"] = {
                    "http": server.health_endpoint,
                    "interval": "10s",
                    "timeout": "2s",
                }

            self.consul_client.agent.service.register(**service_config)

            # Update server with consul ID
            server.consul_id = consul_id
            await self.db.commit()

            logger.info(
                "consul_registration_success",
                server_id=str(server.id),
                consul_id=consul_id,
            )

        except Exception as e:
            logger.error(
                "consul_registration_failed",
                server_id=str(server.id),
                error=str(e),
            )

    async def deregister_server(self, server_id: UUID) -> None:
        """
        Deregister server from SARK and Consul.

        Args:
            server_id: Server ID to deregister
        """
        server = await self.db.get(MCPServer, server_id)
        if not server:
            raise ValueError(f"Server {server_id} not found")

        # Deregister from Consul
        if server.consul_id:
            try:
                self.consul_client.agent.service.deregister(server.consul_id)
            except Exception as e:
                logger.warning(
                    "consul_deregistration_failed",
                    server_id=str(server_id),
                    error=str(e),
                )

        # Update status
        server.status = ServerStatus.DECOMMISSIONED
        await self.db.commit()

        logger.info("server_deregistered", server_id=str(server_id))
