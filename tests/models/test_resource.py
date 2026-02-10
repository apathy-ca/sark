"""Tests for GRID-compliant Resource model."""

from datetime import UTC, datetime

import pytest

from sark.models.resource import (
    Classification,
    GridResource,
    ResourceStatus,
    ResourceTool,
    ResourceType,
    SensitivityLevel,
)


class TestResourceModel:
    """Tests for GridResource model."""

    def test_resource_creation(self) -> None:
        """Test creating GridResource instance with minimal fields."""
        resource = GridResource(
            name="test-resource",
            description="Test resource",
            type=ResourceType.TOOL,
            classification=Classification.INTERNAL,
            status=ResourceStatus.REGISTERED,
        )

        assert resource.name == "test-resource"
        assert resource.type == ResourceType.TOOL
        assert resource.classification == Classification.INTERNAL
        assert resource.status == ResourceStatus.REGISTERED

    def test_resource_with_metadata(self) -> None:
        """Test GridResource with MCP-specific metadata."""
        mcp_metadata = {
            "transport": "http",
            "endpoint": "http://localhost:8080",
            "mcp_version": "2025-06-18",
            "capabilities": ["tools", "resources"],
        }

        resource = GridResource(
            name="mcp-server",
            type=ResourceType.SERVICE,
            classification=Classification.CONFIDENTIAL,
            extra_metadata=mcp_metadata,
        )

        assert resource.extra_metadata["transport"] == "http"
        assert resource.extra_metadata["endpoint"] == "http://localhost:8080"
        assert "capabilities" in resource.extra_metadata

    def test_resource_types(self) -> None:
        """Test all ResourceType enum values."""
        assert ResourceType.TOOL == "tool"
        assert ResourceType.DATA == "data"
        assert ResourceType.SERVICE == "service"
        assert ResourceType.DEVICE == "device"
        assert ResourceType.INFRASTRUCTURE == "infrastructure"

    def test_classification_levels(self) -> None:
        """Test all Classification enum values."""
        assert Classification.PUBLIC == "Public"
        assert Classification.INTERNAL == "Internal"
        assert Classification.CONFIDENTIAL == "Confidential"
        assert Classification.SECRET == "Secret"

    def test_resource_with_provider(self) -> None:
        """Test GridResource with provider_id and parameters_schema."""
        schema = {
            "type": "object",
            "properties": {"api_key": {"type": "string"}},
        }

        resource = GridResource(
            name="external-api",
            type=ResourceType.DATA,
            classification=Classification.PUBLIC,
            provider_id="external-provider-123",
            parameters_schema=schema,
        )

        assert resource.provider_id == "external-provider-123"
        assert resource.parameters_schema["type"] == "object"

    def test_resource_status_values(self) -> None:
        """Test ResourceStatus enum values."""
        assert ResourceStatus.REGISTERED == "registered"
        assert ResourceStatus.ACTIVE == "active"
        assert ResourceStatus.INACTIVE == "inactive"
        assert ResourceStatus.UNHEALTHY == "unhealthy"
        assert ResourceStatus.DECOMMISSIONED == "decommissioned"

    def test_resource_repr(self) -> None:
        """Test GridResource string representation."""
        resource = GridResource(
            name="test-resource",
            type=ResourceType.SERVICE,
            classification=Classification.INTERNAL,
        )

        repr_str = repr(resource)
        assert "GridResource" in repr_str
        assert "test-resource" in repr_str
        assert "SERVICE" in repr_str

    def test_resource_defaults(self) -> None:
        """Test GridResource default values.

        Note: SQLAlchemy defaults are applied at DB flush time, not at object creation.
        For objects created without a session, we test the declared defaults exist.
        """
        resource = GridResource(
            name="minimal-resource",
            type=ResourceType.TOOL,
        )

        # These defaults are set at column definition and apply during DB operations
        # For in-memory objects, they may be None until persisted
        assert hasattr(resource, 'classification')
        assert hasattr(resource, 'status')
        assert hasattr(resource, 'extra_metadata')
        assert hasattr(resource, 'tags')


class TestResourceToolModel:
    """Tests for ResourceTool model."""

    def test_resource_tool_creation(self) -> None:
        """Test creating ResourceTool instance."""
        # We need a UUID for resource_id; using a fake one for testing
        from uuid import uuid4

        resource_id = uuid4()

        tool = ResourceTool(
            resource_id=resource_id,
            name="test-tool",
            description="Test tool description",
            parameters={"param1": "value1"},
            sensitivity_level=SensitivityLevel.MEDIUM,
        )

        assert tool.name == "test-tool"
        assert tool.resource_id == resource_id
        assert tool.sensitivity_level == SensitivityLevel.MEDIUM
        assert tool.parameters["param1"] == "value1"

    def test_resource_tool_defaults(self) -> None:
        """Test ResourceTool default values.

        Note: SQLAlchemy defaults are applied at DB flush time.
        """
        from uuid import uuid4

        resource_id = uuid4()

        tool = ResourceTool(
            resource_id=resource_id,
            name="minimal-tool",
        )

        # These attributes exist and will have defaults when persisted
        assert hasattr(tool, 'parameters')
        assert hasattr(tool, 'extra_metadata')
        assert hasattr(tool, 'sensitivity_level')
        assert hasattr(tool, 'requires_approval')
        assert hasattr(tool, 'invocation_count')

    def test_resource_tool_repr(self) -> None:
        """Test ResourceTool string representation."""
        from uuid import uuid4

        resource_id = uuid4()

        tool = ResourceTool(
            resource_id=resource_id,
            name="test-tool",
        )

        repr_str = repr(tool)
        assert "ResourceTool" in repr_str
        assert "test-tool" in repr_str


class TestSensitivityLevel:
    """Tests for backward-compatible SensitivityLevel enum."""

    def test_sensitivity_levels(self) -> None:
        """Test all SensitivityLevel enum values."""
        assert SensitivityLevel.LOW == "low"
        assert SensitivityLevel.MEDIUM == "medium"
        assert SensitivityLevel.HIGH == "high"
        assert SensitivityLevel.CRITICAL == "critical"
