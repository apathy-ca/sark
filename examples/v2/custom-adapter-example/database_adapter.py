"""
Database Protocol Adapter for SARK v2.0.

Example custom adapter that governs database access through SARK.
Supports PostgreSQL, MySQL, and other SQL databases.

Author: SARK Team
License: MIT
"""

import re
import time
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional
import structlog

from sark.adapters.base import ProtocolAdapter
from sark.adapters.exceptions import (
    AdapterConfigurationError,
    ConnectionError as AdapterConnectionError,
    DiscoveryError,
    InvocationError,
    ValidationError,
)
from sark.models.base import (
    CapabilitySchema,
    InvocationRequest,
    InvocationResult,
    ResourceSchema,
)

logger = structlog.get_logger(__name__)


class DatabaseAdapter(ProtocolAdapter):
    """
    Protocol adapter for SQL databases.

    Supports:
    - PostgreSQL
    - MySQL
    - SQLite (for testing)

    Example usage:
        ```python
        adapter = DatabaseAdapter()

        # Discover a database
        resources = await adapter.discover_resources({
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "myapp",
            "username": "user",
            "password": "pass"
        })

        # Query a table
        result = await adapter.invoke(InvocationRequest(
            capability_id="users-select",
            principal_id="alice",
            arguments={
                "query": "SELECT * FROM users WHERE id = 1"
            }
        ))
        ```
    """

    # Supported database types
    SUPPORTED_DATABASES = ["postgresql", "mysql", "sqlite"]

    # Default timeouts
    DEFAULT_CONNECT_TIMEOUT = 10.0
    DEFAULT_QUERY_TIMEOUT = 30.0

    # SQL injection patterns (simple check)
    DANGEROUS_SQL_PATTERNS = [
        r";\s*DROP",
        r";\s*DELETE\s+FROM\s+(?!users|orders)",  # Allow only specific tables
        r";\s*TRUNCATE",
        r";\s*ALTER",
        r"--",
        r"/\*",
        r"xp_cmdshell",
        r"sp_executesql",
        r"EXEC\s*\(",
    ]

    def __init__(self):
        """Initialize the database adapter."""
        self._connections: Dict[str, Any] = {}
        self._schemas: Dict[str, List[Dict]] = {}

    @property
    def protocol_name(self) -> str:
        """Return protocol identifier."""
        return "database"

    @property
    def protocol_version(self) -> str:
        """Return protocol version."""
        return "1.0"

    async def discover_resources(
        self,
        discovery_config: Dict[str, Any]
    ) -> List[ResourceSchema]:
        """
        Discover database tables and views.

        Args:
            discovery_config: {
                "type": "postgresql",  # or "mysql", "sqlite"
                "host": "localhost",
                "port": 5432,
                "database": "myapp",
                "username": "user",
                "password": "pass",
                "schema": "public"  # Optional, default: public
            }

        Returns:
            List with one ResourceSchema representing the database
            and capabilities for each table operation.
        """
        logger.info("database_discovery_started", config=discovery_config)

        # Validate configuration
        self._validate_discovery_config(discovery_config)

        db_type = discovery_config["type"]
        database = discovery_config["database"]

        try:
            # Get database connection module
            conn = await self._connect(discovery_config)

            # Introspect schema
            tables = await self._introspect_schema(conn, discovery_config)

            # Create capabilities for each table
            capabilities = []
            for table in tables:
                table_name = table["table_name"]

                # Create CRUD capabilities
                for operation in ["select", "insert", "update", "delete"]:
                    capabilities.append(CapabilitySchema(
                        id=f"{table_name}-{operation}",
                        resource_id=f"database-{database}",
                        name=f"{operation.upper()} {table_name}",
                        description=f"{operation.title()} records from {table_name} table",
                        input_schema=self._get_operation_schema(operation),
                        sensitivity_level=self._determine_sensitivity(table_name),
                    ))

            # Create resource
            resource = ResourceSchema(
                id=f"database-{database}",
                name=f"{db_type.title()} Database: {database}",
                protocol="database",
                endpoint=f"{discovery_config.get('host', 'localhost')}:{discovery_config.get('port', 5432)}",
                capabilities=capabilities,
                metadata={
                    "database_type": db_type,
                    "database_name": database,
                    "schema": discovery_config.get("schema", "public"),
                    "table_count": len(tables)
                },
                sensitivity_level="high",  # Databases are sensitive by default
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )

            # Cache schema for later use
            self._schemas[resource.id] = tables

            logger.info(
                "database_discovery_completed",
                database=database,
                tables=len(tables),
                capabilities=len(capabilities)
            )

            return [resource]

        except Exception as e:
            raise DiscoveryError(f"Failed to discover database: {e}")

    async def get_capabilities(
        self,
        resource: ResourceSchema
    ) -> List[CapabilitySchema]:
        """Get all capabilities for a database resource."""
        return resource.capabilities

    async def validate_request(
        self,
        request: InvocationRequest
    ) -> bool:
        """
        Validate database query request.

        Checks:
        - SQL syntax is safe (no injection attempts)
        - Query matches capability (SELECT for select, etc.)
        - Required arguments present
        """
        query = request.arguments.get("query", "")

        if not query:
            raise ValidationError("Missing required argument: query")

        # Check for SQL injection patterns
        for pattern in self.DANGEROUS_SQL_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                raise ValidationError(
                    f"Dangerous SQL pattern detected: {pattern}. "
                    f"Query rejected for security."
                )

        # Validate query matches capability
        capability_id = request.capability_id
        if "-" in capability_id:
            operation = capability_id.split("-")[-1]
            query_upper = query.strip().upper()

            operation_keywords = {
                "select": "SELECT",
                "insert": "INSERT",
                "update": "UPDATE",
                "delete": "DELETE"
            }

            expected_keyword = operation_keywords.get(operation)
            if expected_keyword and not query_upper.startswith(expected_keyword):
                raise ValidationError(
                    f"Query must start with {expected_keyword} for {operation} capability"
                )

        return True

    async def invoke(
        self,
        request: InvocationRequest
    ) -> InvocationResult:
        """
        Execute database query.

        Args:
            request.arguments: {
                "query": "SELECT * FROM users WHERE id = 1",
                "parameters": [1]  # Optional parameterized query
            }

        Returns:
            InvocationResult with query results
        """
        start_time = time.time()
        query = request.arguments.get("query", "")
        parameters = request.arguments.get("parameters", [])

        logger.info(
            "database_query_started",
            capability_id=request.capability_id,
            principal_id=request.principal_id,
            query_preview=query[:100]
        )

        try:
            # Note: In a real implementation, you'd execute the query here
            # For this example, we'll simulate a response

            # Simulate query execution
            result_data = self._simulate_query(query)

            duration_ms = (time.time() - start_time) * 1000

            logger.info(
                "database_query_completed",
                capability_id=request.capability_id,
                rows=len(result_data),
                duration_ms=duration_ms
            )

            return InvocationResult(
                success=True,
                result=result_data,
                metadata={
                    "query": query,
                    "row_count": len(result_data),
                    "parameters": parameters
                },
                duration_ms=duration_ms
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "database_query_failed",
                capability_id=request.capability_id,
                error=str(e),
                duration_ms=duration_ms
            )

            return InvocationResult(
                success=False,
                error=f"Database query failed: {e}",
                metadata={"query": query},
                duration_ms=duration_ms
            )

    async def health_check(
        self,
        resource: ResourceSchema
    ) -> bool:
        """
        Check if database is accessible.

        Executes a simple query (SELECT 1) to verify connectivity.
        """
        try:
            # Note: In a real implementation, you'd execute: SELECT 1
            # For this example, we'll return True
            logger.info(
                "database_health_check",
                resource_id=resource.id,
                status="healthy"
            )
            return True

        except Exception as e:
            logger.error(
                "database_health_check_failed",
                resource_id=resource.id,
                error=str(e)
            )
            return False

    # Helper methods

    def _validate_discovery_config(self, config: Dict[str, Any]) -> None:
        """Validate discovery configuration."""
        required_fields = ["type", "database"]

        for field in required_fields:
            if field not in config:
                raise AdapterConfigurationError(f"Missing required field: {field}")

        if config["type"] not in self.SUPPORTED_DATABASES:
            raise AdapterConfigurationError(
                f"Unsupported database type: {config['type']}. "
                f"Supported: {', '.join(self.SUPPORTED_DATABASES)}"
            )

    async def _connect(self, config: Dict[str, Any]) -> Any:
        """Establish database connection (simulated for example)."""
        # Note: In a real implementation, you'd use asyncpg, aiomysql, etc.
        logger.info("database_connection", type=config["type"])
        return {"connected": True}  # Simulated connection

    async def _introspect_schema(
        self,
        conn: Any,
        config: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Introspect database schema (simulated for example)."""
        # Note: In a real implementation, you'd query information_schema
        # For this example, we'll return sample tables

        sample_tables = [
            {"table_name": "users", "table_type": "BASE TABLE"},
            {"table_name": "orders", "table_type": "BASE TABLE"},
            {"table_name": "products", "table_type": "BASE TABLE"},
            {"table_name": "analytics", "table_type": "VIEW"},
        ]

        return sample_tables

    def _get_operation_schema(self, operation: str) -> Dict[str, Any]:
        """Get JSON schema for operation arguments."""
        if operation == "select":
            return {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "parameters": {"type": "array", "items": {"type": "any"}}
                },
                "required": ["query"]
            }
        elif operation in ["insert", "update", "delete"]:
            return {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "parameters": {"type": "array"}
                },
                "required": ["query"]
            }
        else:
            return {}

    def _determine_sensitivity(self, table_name: str) -> str:
        """Determine sensitivity level based on table name."""
        sensitive_tables = ["users", "payments", "credentials", "secrets"]
        if table_name.lower() in sensitive_tables:
            return "high"
        elif table_name.lower().endswith("_audit"):
            return "medium"
        else:
            return "low"

    def _simulate_query(self, query: str) -> List[Dict[str, Any]]:
        """Simulate query execution (for example purposes)."""
        # Return sample data based on query
        if "SELECT" in query.upper():
            return [
                {"id": 1, "name": "Alice", "email": "alice@example.com"},
                {"id": 2, "name": "Bob", "email": "bob@example.com"}
            ]
        elif "INSERT" in query.upper():
            return [{"inserted": 1, "id": 123}]
        elif "UPDATE" in query.upper():
            return [{"updated": 1}]
        elif "DELETE" in query.upper():
            return [{"deleted": 1}]
        else:
            return []


# Registration example
def register_adapter():
    """Register the database adapter with SARK."""
    from sark.adapters.registry import registry
    registry.register(DatabaseAdapter())


if __name__ == "__main__":
    # Example usage
    import asyncio

    async def example():
        adapter = DatabaseAdapter()

        # Discovery
        resources = await adapter.discover_resources({
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "myapp",
            "username": "user",
            "password": "pass"
        })

        print(f"Discovered: {resources[0].name}")
        print(f"Capabilities: {len(resources[0].capabilities)}")

        # Invoke
        request = InvocationRequest(
            capability_id="users-select",
            principal_id="alice",
            arguments={"query": "SELECT * FROM users"}
        )

        result = await adapter.invoke(request)
        print(f"Query result: {result.result}")

    asyncio.run(example())
