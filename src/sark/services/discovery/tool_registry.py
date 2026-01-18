"""Tool Registry and Sensitivity Classification Service.

This service provides automatic sensitivity detection for MCP tools based on
keyword analysis, as well as manual override capabilities.
"""

from datetime import UTC, datetime
import re
from typing import Any, ClassVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from sark.models.audit import AuditEventType, SeverityLevel
from sark.models.mcp_server import MCPTool, SensitivityLevel
from sark.services.audit import AuditService

logger = structlog.get_logger()


class ToolRegistry:
    """Service for tool sensitivity classification and management."""

    # Keyword-based sensitivity detection rules
    HIGH_KEYWORDS: ClassVar[list[str]] = [
        "delete",
        "drop",
        "exec",
        "execute",
        "admin",
        "root",
        "sudo",
        "kill",
        "destroy",
        "remove",
        "purge",
        "truncate",
    ]

    MEDIUM_KEYWORDS: ClassVar[list[str]] = [
        "write",
        "update",
        "modify",
        "change",
        "edit",
        "create",
        "insert",
        "save",
        "upload",
        "put",
        "post",
        "patch",
    ]

    LOW_KEYWORDS: ClassVar[list[str]] = [
        "read",
        "get",
        "list",
        "fetch",
        "view",
        "show",
        "display",
        "query",
        "search",
        "find",
        "retrieve",
    ]

    # Critical keywords that always result in critical sensitivity
    CRITICAL_KEYWORDS: ClassVar[list[str]] = [
        "payment",
        "transaction",
        "credit_card",
        "password",
        "secret",
        "key",
        "token",
        "credential",
        "auth",
        "permission",
        "access_control",
        "encrypt",
        "decrypt",
    ]

    def __init__(self, db: AsyncSession, audit_db: AsyncSession | None = None) -> None:
        """
        Initialize tool registry service.

        Args:
            db: Database session for main database
            audit_db: Optional database session for audit logging
        """
        self.db = db
        self.audit_db = audit_db

    async def detect_sensitivity(
        self,
        tool_name: str,
        tool_description: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> SensitivityLevel:
        """
        Automatically detect sensitivity level based on keywords.

        Detection Algorithm:
        1. Check for CRITICAL keywords in name/description → CRITICAL
        2. Check for HIGH keywords → HIGH
        3. Check for MEDIUM keywords → MEDIUM
        4. Check for LOW keywords → LOW
        5. Default → MEDIUM

        Args:
            tool_name: Name of the tool
            tool_description: Optional description of the tool
            parameters: Optional tool parameters schema

        Returns:
            Detected sensitivity level
        """
        # Combine all text for analysis
        text_to_analyze = tool_name.lower()
        if tool_description:
            text_to_analyze += " " + tool_description.lower()

        # Include parameter names if available
        if parameters:
            param_names = " ".join(self._extract_parameter_names(parameters))
            text_to_analyze += " " + param_names.lower()

        # Check for critical keywords first
        if self._contains_keywords(text_to_analyze, self.CRITICAL_KEYWORDS):
            logger.info(
                "sensitivity_detected",
                tool_name=tool_name,
                level="critical",
                reason="critical_keywords",
            )
            return SensitivityLevel.CRITICAL

        # Check for high keywords
        if self._contains_keywords(text_to_analyze, self.HIGH_KEYWORDS):
            logger.info(
                "sensitivity_detected",
                tool_name=tool_name,
                level="high",
                reason="high_keywords",
            )
            return SensitivityLevel.HIGH

        # Check for medium keywords
        if self._contains_keywords(text_to_analyze, self.MEDIUM_KEYWORDS):
            logger.info(
                "sensitivity_detected",
                tool_name=tool_name,
                level="medium",
                reason="medium_keywords",
            )
            return SensitivityLevel.MEDIUM

        # Check for low keywords
        if self._contains_keywords(text_to_analyze, self.LOW_KEYWORDS):
            logger.info(
                "sensitivity_detected",
                tool_name=tool_name,
                level="low",
                reason="low_keywords",
            )
            return SensitivityLevel.LOW

        # Default to medium
        logger.info(
            "sensitivity_detected",
            tool_name=tool_name,
            level="medium",
            reason="default",
        )
        return SensitivityLevel.MEDIUM

    def _contains_keywords(self, text: str, keywords: list[str]) -> bool:
        """
        Check if text contains any of the specified keywords.

        Uses flexible matching to handle snake_case, spaces, and word boundaries.
        For example, "credit_card" will match "credit card", "credit_card", etc.

        Args:
            text: Text to search in (should be lowercase)
            keywords: List of keywords to search for

        Returns:
            True if any keyword is found
        """
        for keyword in keywords:
            # Replace underscores in keyword with pattern that matches underscore or space
            # This allows "credit_card" to match both "credit_card" and "credit card"
            keyword_pattern = keyword.replace("_", "[ _]")

            # Use pattern that matches at word boundaries (start/end or after non-letter)
            # Pattern: (start of string OR non-letter) + keyword + (end of string OR non-letter)
            pattern = r"(?:^|[^a-z])" + keyword_pattern + r"(?:$|[^a-z])"
            if re.search(pattern, text):
                return True
        return False

    def _extract_parameter_names(self, parameters: dict[str, Any]) -> list[str]:
        """
        Extract parameter names from tool parameters schema.

        Handles both simple and nested parameter structures.

        Args:
            parameters: Tool parameters schema

        Returns:
            List of parameter names
        """
        names = []

        # Handle JSONSchema-style parameters
        if isinstance(parameters, dict):
            if "properties" in parameters:
                names.extend(parameters["properties"].keys())
            elif "type" in parameters and parameters["type"] == "object":
                if "properties" in parameters:
                    names.extend(parameters["properties"].keys())
            else:
                # Simple dict of parameter names
                names.extend(parameters.keys())

        return names

    async def get_tool(self, tool_id: UUID) -> MCPTool | None:
        """
        Get tool by ID.

        Args:
            tool_id: Tool UUID

        Returns:
            Tool or None if not found
        """
        return await self.db.get(MCPTool, tool_id)

    async def get_tool_by_name(self, server_id: UUID, tool_name: str) -> MCPTool | None:
        """
        Get tool by server ID and name.

        Args:
            server_id: Server UUID
            tool_name: Tool name

        Returns:
            Tool or None if not found
        """
        result = await self.db.execute(
            select(MCPTool).where(
                MCPTool.server_id == server_id,
                MCPTool.name == tool_name,
            )
        )
        return result.scalar_one_or_none()

    async def update_sensitivity(
        self,
        tool_id: UUID,
        new_sensitivity: SensitivityLevel,
        user_id: UUID,
        user_email: str,
        reason: str | None = None,
    ) -> MCPTool:
        """
        Manually update tool sensitivity level (override auto-detection).

        This creates an audit trail for compliance.

        Args:
            tool_id: Tool UUID
            new_sensitivity: New sensitivity level
            user_id: User making the change
            user_email: Email of user making the change
            reason: Optional reason for the change

        Returns:
            Updated tool

        Raises:
            ValueError: If tool not found
        """
        tool = await self.db.get(MCPTool, tool_id)
        if not tool:
            raise ValueError(f"Tool {tool_id} not found")

        old_sensitivity = tool.sensitivity_level

        # Update sensitivity
        tool.sensitivity_level = new_sensitivity
        tool.extra_metadata = tool.extra_metadata or {}
        tool.extra_metadata["sensitivity_override"] = {
            "previous_level": old_sensitivity.value,
            "new_level": new_sensitivity.value,
            "updated_by": str(user_id),
            "updated_at": datetime.now(UTC).isoformat(),
            "reason": reason,
        }

        await self.db.commit()
        await self.db.refresh(tool)

        # Log audit event
        if self.audit_db:
            audit_service = AuditService(self.audit_db)
            await audit_service.log_event(
                event_type=AuditEventType.SERVER_UPDATED,  # Tool sensitivity is a server configuration change
                severity=SeverityLevel.MEDIUM,
                user_id=user_id,
                user_email=user_email,
                server_id=tool.server_id,
                tool_name=tool.name,
                details={
                    "tool_id": str(tool_id),
                    "old_sensitivity": old_sensitivity.value,
                    "new_sensitivity": new_sensitivity.value,
                    "reason": reason,
                    "change_type": "sensitivity_override",
                },
            )

        logger.info(
            "tool_sensitivity_updated",
            tool_id=str(tool_id),
            tool_name=tool.name,
            old_sensitivity=old_sensitivity.value,
            new_sensitivity=new_sensitivity.value,
            user_id=str(user_id),
            reason=reason,
        )

        return tool

    async def get_sensitivity_history(self, tool_id: UUID) -> list[dict[str, Any]]:
        """
        Get sensitivity change history for a tool.

        Args:
            tool_id: Tool UUID

        Returns:
            List of sensitivity changes
        """
        tool = await self.db.get(MCPTool, tool_id)
        if not tool:
            raise ValueError(f"Tool {tool_id} not found")

        history = []

        # Get override history from metadata
        if tool.extra_metadata and "sensitivity_override" in tool.extra_metadata:
            override = tool.extra_metadata["sensitivity_override"]
            history.append(
                {
                    "timestamp": override.get("updated_at"),
                    "previous_level": override.get("previous_level"),
                    "new_level": override.get("new_level"),
                    "updated_by": override.get("updated_by"),
                    "reason": override.get("reason"),
                    "type": "manual_override",
                }
            )

        # Current state
        history.append(
            {
                "timestamp": tool.updated_at.isoformat(),
                "level": tool.sensitivity_level.value,
                "type": "current",
            }
        )

        return history

    async def bulk_detect_sensitivity(self, server_id: UUID) -> dict[str, SensitivityLevel]:
        """
        Detect sensitivity for all tools on a server.

        Useful for re-classifying tools after updating detection rules.

        Args:
            server_id: Server UUID

        Returns:
            Dictionary mapping tool IDs to detected sensitivity levels
        """
        result = await self.db.execute(select(MCPTool).where(MCPTool.server_id == server_id))
        tools = result.scalars().all()

        detections = {}
        for tool in tools:
            detected = await self.detect_sensitivity(
                tool_name=tool.name,
                tool_description=tool.description,
                parameters=tool.parameters,
            )
            detections[str(tool.id)] = detected

        logger.info(
            "bulk_sensitivity_detection",
            server_id=str(server_id),
            tool_count=len(detections),
        )

        return detections

    async def get_tools_by_sensitivity(self, sensitivity: SensitivityLevel) -> list[MCPTool]:
        """
        Get all tools with a specific sensitivity level.

        Args:
            sensitivity: Sensitivity level to filter by

        Returns:
            List of tools
        """
        result = await self.db.execute(
            select(MCPTool).where(MCPTool.sensitivity_level == sensitivity)
        )
        return list(result.scalars().all())

    async def get_sensitivity_statistics(self) -> dict[str, Any]:
        """
        Get statistics about tool sensitivity distribution.

        Returns:
            Statistics dictionary
        """
        stats = {
            "total_tools": 0,
            "by_sensitivity": {
                "low": 0,
                "medium": 0,
                "high": 0,
                "critical": 0,
            },
            "overridden_count": 0,
        }

        # Get all tools
        result = await self.db.execute(select(MCPTool))
        tools = result.scalars().all()

        stats["total_tools"] = len(tools)

        for tool in tools:
            stats["by_sensitivity"][tool.sensitivity_level.value] += 1

            # Check if sensitivity was manually overridden
            if tool.extra_metadata and "sensitivity_override" in tool.extra_metadata:
                stats["overridden_count"] += 1

        return stats
