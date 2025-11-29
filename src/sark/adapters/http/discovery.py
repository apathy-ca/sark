"""
OpenAPI discovery for HTTP adapter.

This module handles:
- OpenAPI/Swagger spec parsing (v2.0, v3.0, v3.1)
- Automatic endpoint discovery
- Schema extraction for validation
- Capability generation from API operations

Version: 2.0.0
Engineer: ENGINEER-2
"""

from typing import Any, Dict, List, Optional, Tuple
import structlog
import httpx
from urllib.parse import urljoin

from sark.models.base import ResourceSchema, CapabilitySchema
from sark.adapters.exceptions import DiscoveryError

logger = structlog.get_logger(__name__)


class OpenAPIDiscovery:
    """
    OpenAPI specification discovery and parsing.

    Supports:
    - OpenAPI 3.x (3.0, 3.1)
    - Swagger 2.0
    - Common spec locations (/openapi.json, /swagger.json, /api-docs)
    """

    # Common OpenAPI spec locations to try
    COMMON_SPEC_PATHS = [
        "/openapi.json",
        "/openapi.yaml",
        "/swagger.json",
        "/swagger.yaml",
        "/api-docs",
        "/v1/api-docs",
        "/v2/api-docs",
        "/v3/api-docs",
        "/docs/openapi.json",
        "/docs/swagger.json",
    ]

    def __init__(self, base_url: str, spec_url: Optional[str] = None):
        """
        Initialize OpenAPI discovery.

        Args:
            base_url: Base URL of the API (e.g., https://api.example.com)
            spec_url: Direct URL to OpenAPI spec (optional, will auto-discover if not provided)
        """
        self.base_url = base_url.rstrip("/")
        self.spec_url = spec_url
        self.spec: Optional[Dict[str, Any]] = None
        self.openapi_version: Optional[str] = None

    async def discover_spec(self) -> Dict[str, Any]:
        """
        Discover and fetch OpenAPI specification.

        Returns:
            Parsed OpenAPI specification

        Raises:
            DiscoveryError: If spec cannot be found or parsed
        """
        if self.spec:
            return self.spec

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try direct spec URL first
            if self.spec_url:
                spec = await self._fetch_spec(client, self.spec_url)
                if spec:
                    self.spec = spec
                    return spec

            # Auto-discover by trying common paths
            logger.info("Auto-discovering OpenAPI spec", base_url=self.base_url)

            for path in self.COMMON_SPEC_PATHS:
                try:
                    url = urljoin(self.base_url, path)
                    spec = await self._fetch_spec(client, url)
                    if spec:
                        logger.info("Found OpenAPI spec", url=url)
                        self.spec = spec
                        self.spec_url = url
                        return spec
                except Exception as e:
                    logger.debug("Spec not found at path", path=path, error=str(e))
                    continue

        raise DiscoveryError(
            "Could not find OpenAPI specification",
            details={
                "base_url": self.base_url,
                "tried_paths": self.COMMON_SPEC_PATHS,
                "spec_url": self.spec_url,
            }
        )

    async def _fetch_spec(self, client: httpx.AsyncClient, url: str) -> Optional[Dict[str, Any]]:
        """
        Fetch and parse OpenAPI spec from URL.

        Args:
            client: HTTP client
            url: URL to fetch from

        Returns:
            Parsed spec or None if failed
        """
        try:
            response = await client.get(url)
            response.raise_for_status()

            # Try JSON first
            try:
                spec = response.json()
            except Exception:
                # Try YAML
                import yaml
                spec = yaml.safe_load(response.text)

            # Validate it's an OpenAPI/Swagger spec
            if "openapi" in spec:
                self.openapi_version = spec["openapi"]
                logger.info("Found OpenAPI spec", version=self.openapi_version)
                return spec
            elif "swagger" in spec:
                self.openapi_version = spec["swagger"]
                logger.info("Found Swagger spec", version=self.openapi_version)
                return spec

            return None

        except Exception as e:
            logger.debug("Failed to fetch spec", url=url, error=str(e))
            return None

    async def discover_capabilities(
        self,
        resource: ResourceSchema,
        spec: Optional[Dict[str, Any]] = None
    ) -> List[CapabilitySchema]:
        """
        Discover capabilities from OpenAPI spec.

        Args:
            resource: Resource to discover capabilities for
            spec: OpenAPI spec (will auto-discover if not provided)

        Returns:
            List of discovered capabilities

        Raises:
            DiscoveryError: If discovery fails
        """
        if spec is None:
            spec = await self.discover_spec()

        capabilities: List[CapabilitySchema] = []

        # Parse paths and operations
        paths = spec.get("paths", {})

        for path, path_item in paths.items():
            # Path-level parameters
            path_params = path_item.get("parameters", [])

            # Iterate through HTTP methods
            for method in ["get", "post", "put", "patch", "delete", "head", "options"]:
                operation = path_item.get(method)
                if not operation:
                    continue

                capability = self._create_capability_from_operation(
                    resource=resource,
                    path=path,
                    method=method.upper(),
                    operation=operation,
                    path_params=path_params,
                    spec=spec
                )

                if capability:
                    capabilities.append(capability)

        logger.info(
            "Discovered capabilities from OpenAPI spec",
            resource_id=resource.id,
            count=len(capabilities)
        )

        return capabilities

    def _create_capability_from_operation(
        self,
        resource: ResourceSchema,
        path: str,
        method: str,
        operation: Dict[str, Any],
        path_params: List[Dict[str, Any]],
        spec: Dict[str, Any]
    ) -> Optional[CapabilitySchema]:
        """
        Create capability from OpenAPI operation.

        Args:
            resource: Parent resource
            path: API path (e.g., /users/{id})
            method: HTTP method (GET, POST, etc.)
            operation: Operation object from spec
            path_params: Path-level parameters
            spec: Full OpenAPI spec

        Returns:
            CapabilitySchema or None if operation should be skipped
        """
        # Generate capability ID
        operation_id = operation.get("operationId", f"{method.lower()}_{path.replace('/', '_')}")
        capability_id = f"{resource.id}:{operation_id}"

        # Get description
        summary = operation.get("summary", "")
        description = operation.get("description", summary)

        # Combine parameters
        all_params = list(path_params)
        all_params.extend(operation.get("parameters", []))

        # Build input schema
        input_schema = self._build_input_schema(operation, all_params, spec)

        # Build output schema
        output_schema = self._build_output_schema(operation, spec)

        # Determine sensitivity level based on operation
        sensitivity_level = self._determine_sensitivity(method, path, operation)

        # Build metadata
        metadata = {
            "http_method": method,
            "http_path": path,
            "operation_id": operation_id,
            "tags": operation.get("tags", []),
            "deprecated": operation.get("deprecated", False),
        }

        # Add security requirements if present
        if "security" in operation:
            metadata["security"] = operation["security"]

        return CapabilitySchema(
            id=capability_id,
            resource_id=resource.id,
            name=operation_id,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            sensitivity_level=sensitivity_level,
            metadata=metadata
        )

    def _build_input_schema(
        self,
        operation: Dict[str, Any],
        parameters: List[Dict[str, Any]],
        spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build JSON Schema for operation inputs.

        Combines:
        - Path parameters
        - Query parameters
        - Header parameters
        - Request body

        Args:
            operation: Operation object
            parameters: Combined parameters
            spec: Full OpenAPI spec

        Returns:
            JSON Schema for inputs
        """
        schema: Dict[str, Any] = {
            "type": "object",
            "properties": {},
            "required": [],
        }

        # Add parameters
        for param in parameters:
            # Resolve $ref if present
            if "$ref" in param:
                param = self._resolve_ref(param["$ref"], spec)

            param_name = param.get("name")
            param_in = param.get("in")  # path, query, header, cookie
            param_required = param.get("required", False)

            if not param_name:
                continue

            # Get parameter schema (OpenAPI 3.x) or type (Swagger 2.0)
            if "schema" in param:
                param_schema = param["schema"]
            else:
                # Swagger 2.0 style
                param_schema = {
                    "type": param.get("type", "string"),
                    "format": param.get("format"),
                }

            # Add to schema
            property_name = f"{param_in}_{param_name}" if param_in != "path" else param_name
            schema["properties"][property_name] = param_schema

            if param.get("description"):
                schema["properties"][property_name]["description"] = param["description"]

            if param_required:
                schema["required"].append(property_name)

        # Add request body (OpenAPI 3.x)
        if "requestBody" in operation:
            request_body = operation["requestBody"]

            # Resolve $ref if present
            if "$ref" in request_body:
                request_body = self._resolve_ref(request_body["$ref"], spec)

            content = request_body.get("content", {})

            # Prefer application/json
            if "application/json" in content:
                body_schema = content["application/json"].get("schema", {})
                if "$ref" in body_schema:
                    body_schema = self._resolve_ref(body_schema["$ref"], spec)

                schema["properties"]["body"] = body_schema

                if request_body.get("required", False):
                    schema["required"].append("body")

        return schema

    def _build_output_schema(
        self,
        operation: Dict[str, Any],
        spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build JSON Schema for operation outputs.

        Args:
            operation: Operation object
            spec: Full OpenAPI spec

        Returns:
            JSON Schema for outputs
        """
        responses = operation.get("responses", {})

        # Look for successful response (200, 201, etc.)
        success_response = None
        for code in ["200", "201", "202", "204"]:
            if code in responses:
                success_response = responses[code]
                break

        if not success_response:
            # Default to any 2xx response
            success_response = responses.get("default", {})

        if not success_response:
            return {"type": "object"}

        # Resolve $ref if present
        if "$ref" in success_response:
            success_response = self._resolve_ref(success_response["$ref"], spec)

        # Get schema from content (OpenAPI 3.x)
        if "content" in success_response:
            content = success_response["content"]

            # Prefer application/json
            if "application/json" in content:
                schema = content["application/json"].get("schema", {})
                if "$ref" in schema:
                    schema = self._resolve_ref(schema["$ref"], spec)
                return schema

        # Swagger 2.0 style
        if "schema" in success_response:
            schema = success_response["schema"]
            if "$ref" in schema:
                schema = self._resolve_ref(schema["$ref"], spec)
            return schema

        return {"type": "object"}

    def _resolve_ref(self, ref: str, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve $ref in OpenAPI spec.

        Args:
            ref: Reference string (e.g., #/components/schemas/User)
            spec: Full OpenAPI spec

        Returns:
            Resolved object
        """
        if not ref.startswith("#/"):
            logger.warning("External $ref not supported", ref=ref)
            return {}

        # Split ref path
        parts = ref[2:].split("/")

        # Navigate spec
        current = spec
        for part in parts:
            if part not in current:
                logger.warning("Could not resolve $ref", ref=ref)
                return {}
            current = current[part]

        return current

    def _determine_sensitivity(
        self,
        method: str,
        path: str,
        operation: Dict[str, Any]
    ) -> str:
        """
        Determine sensitivity level for operation.

        Args:
            method: HTTP method
            path: API path
            operation: Operation object

        Returns:
            Sensitivity level (low, medium, high, critical)
        """
        # Check for security requirements
        has_security = "security" in operation or operation.get("deprecated", False)

        # Mutating operations are higher risk
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            return "high" if has_security else "medium"

        # Read operations
        # Check path for sensitive keywords
        sensitive_keywords = ["admin", "password", "secret", "token", "key", "credential"]
        path_lower = path.lower()

        if any(keyword in path_lower for keyword in sensitive_keywords):
            return "high"

        return "medium" if has_security else "low"

    async def get_server_info(self, spec: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract server information from OpenAPI spec.

        Args:
            spec: OpenAPI spec (will auto-discover if not provided)

        Returns:
            Server information dictionary
        """
        if spec is None:
            spec = await self.discover_spec()

        info = spec.get("info", {})
        servers = spec.get("servers", [])

        return {
            "title": info.get("title", "Unknown API"),
            "version": info.get("version", "unknown"),
            "description": info.get("description", ""),
            "servers": servers,
            "openapi_version": self.openapi_version,
        }


__all__ = ["OpenAPIDiscovery"]
