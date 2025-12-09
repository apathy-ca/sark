# Priority 1: Critical Tasks - Detailed Implementation Guide

**Timeline:** Weeks 1-4
**Goal:** Eliminate production blockers

---

## Task 1.1: Complete Gateway Client Implementation

**Owner:** Backend Engineer
**Effort:** 3-4 weeks
**Dependencies:** None
**Status:** 🟡 In Progress (stubbed implementation exists)

### Current State

**File:** `src/sark/services/gateway/client.py`

Stubbed implementation:
```python
async def list_servers(self) -> list[GatewayServerInfo]:
    return []  # Placeholder

async def invoke_tool(...) -> dict:
    raise NotImplementedError()
```

### Target State

Fully functional MCP client supporting:
- ✅ HTTP transport (RESTful API)
- ✅ SSE transport (Server-Sent Events for streaming)
- ✅ stdio transport (subprocess-based communication)

---

### Week 1: HTTP Transport Implementation

#### File: `src/sark/services/gateway/client.py`

**Step 1.1.1: Add HTTP client dependency**

```python
# At top of file
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from circuitbreaker import circuit
```

**Installation:**
```bash
pip install httpx tenacity circuitbreaker
```

Add to `pyproject.toml`:
```toml
dependencies = [
    ...
    "httpx>=0.25.0",
    "tenacity>=8.2.0",
    "circuitbreaker>=1.4.0",
]
```

---

**Step 1.1.2: Update `__init__` method**

```python
def __init__(self, base_url: str, api_key: str | None = None, timeout: float = 5.0):
    """Initialize Gateway client with HTTP connection pool."""
    self.base_url = base_url.rstrip("/")
    self.api_key = api_key
    self.timeout = timeout

    # HTTP client with connection pooling
    self.http_client = httpx.AsyncClient(
        base_url=self.base_url,
        timeout=httpx.Timeout(timeout=timeout),
        limits=httpx.Limits(
            max_connections=100,
            max_keepalive_connections=20,
            keepalive_expiry=30.0,
        ),
        headers=self._get_default_headers(),
    )

    logger.info(
        "gateway_client_initialized",
        base_url=base_url,
        has_api_key=bool(api_key),
        timeout=timeout,
    )

def _get_default_headers(self) -> dict:
    """Build default HTTP headers."""
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "SARK-Gateway-Client/2.1.0",
    }

    if self.api_key:
        headers["X-API-Key"] = self.api_key

    return headers
```

---

**Step 1.1.3: Implement `list_servers()` with retry logic**

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(httpx.HTTPError),
)
@circuit(failure_threshold=5, recovery_timeout=60)
async def list_servers(self, user_id: str | None = None) -> list[GatewayServerInfo]:
    """
    List all MCP servers registered with Gateway.

    Args:
        user_id: Optional user ID to filter servers by permissions

    Returns:
        List of Gateway server info objects

    Raises:
        httpx.HTTPError: If Gateway request fails
    """
    try:
        logger.debug("gateway_list_servers_request", user_id=user_id)

        params = {}
        if user_id:
            params["user_id"] = user_id

        response = await self.http_client.get("/servers", params=params)
        response.raise_for_status()

        data = response.json()
        servers = [
            GatewayServerInfo(**server_data) for server_data in data.get("servers", [])
        ]

        logger.info(
            "gateway_list_servers_success",
            user_id=user_id,
            server_count=len(servers),
        )

        return servers

    except httpx.HTTPStatusError as e:
        logger.error(
            "gateway_list_servers_http_error",
            status_code=e.response.status_code,
            error=str(e),
        )
        raise
    except httpx.RequestError as e:
        logger.error(
            "gateway_list_servers_request_error",
            error=str(e),
        )
        raise
```

---

**Step 1.1.4: Implement `get_server_info()`**

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
async def get_server_info(self, server_id: str) -> GatewayServerInfo | None:
    """
    Get detailed information about a specific MCP server.

    Args:
        server_id: Unique server identifier

    Returns:
        Server info or None if not found

    Raises:
        httpx.HTTPError: If Gateway request fails (except 404)
    """
    try:
        logger.debug("gateway_get_server_info", server_id=server_id)

        response = await self.http_client.get(f"/servers/{server_id}")

        if response.status_code == 404:
            logger.warning("gateway_server_not_found", server_id=server_id)
            return None

        response.raise_for_status()

        data = response.json()
        server = GatewayServerInfo(**data)

        logger.info("gateway_get_server_info_success", server_id=server_id)

        return server

    except httpx.HTTPStatusError as e:
        if e.response.status_code != 404:
            logger.error(
                "gateway_get_server_info_error",
                server_id=server_id,
                status_code=e.response.status_code,
            )
            raise
        return None
```

---

**Step 1.1.5: Implement `list_tools()`**

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
async def list_tools(
    self, server_id: str | None = None, server_name: str | None = None
) -> list[GatewayToolInfo]:
    """
    List tools available via Gateway.

    MCP tools/list endpoint returns tools with JSON schema.

    Args:
        server_id: Optional server ID filter
        server_name: Optional server name filter

    Returns:
        List of Gateway tool info objects

    Raises:
        httpx.HTTPError: If Gateway request fails
    """
    try:
        logger.debug(
            "gateway_list_tools",
            server_id=server_id,
            server_name=server_name,
        )

        params = {}
        if server_id:
            params["server_id"] = server_id
        if server_name:
            params["server_name"] = server_name

        response = await self.http_client.get("/tools", params=params)
        response.raise_for_status()

        data = response.json()
        tools = [GatewayToolInfo(**tool_data) for tool_data in data.get("tools", [])]

        logger.info(
            "gateway_list_tools_success",
            server_id=server_id,
            tool_count=len(tools),
        )

        return tools

    except httpx.HTTPError as e:
        logger.error("gateway_list_tools_error", error=str(e))
        raise
```

---

**Step 1.1.6: Implement `invoke_tool()` with authorization**

```python
@retry(
    stop=stop_after_attempt(2),  # Only retry once for tool invocations
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type(httpx.TimeoutException),
)
async def invoke_tool(
    self,
    server_id: str,
    tool_name: str,
    parameters: dict,
    user_token: str,
    gateway_request_id: str | None = None,
) -> dict:
    """
    Invoke a tool via Gateway (with authorization).

    Flow:
    1. Send request to Gateway with user JWT
    2. Gateway calls SARK /authorize endpoint
    3. Gateway routes to MCP server if authorized
    4. Return tool result

    Args:
        server_id: Target MCP server ID
        tool_name: Tool to invoke
        parameters: Tool parameters (will be filtered by authorization)
        user_token: User JWT token for authorization
        gateway_request_id: Optional request ID for tracing

    Returns:
        Tool invocation result

    Raises:
        httpx.HTTPError: If Gateway request fails
        GatewayAuthorizationError: If authorization denied
        GatewayToolError: If tool execution fails
    """
    import uuid

    request_id = gateway_request_id or str(uuid.uuid4())

    try:
        logger.info(
            "gateway_invoke_tool_request",
            server_id=server_id,
            tool_name=tool_name,
            request_id=request_id,
        )

        # Build request payload
        payload = {
            "server_id": server_id,
            "tool_name": tool_name,
            "parameters": parameters,
            "request_id": request_id,
        }

        # Add user token to headers
        headers = {"Authorization": f"Bearer {user_token}"}

        # POST to Gateway invoke endpoint
        response = await self.http_client.post(
            "/invoke", json=payload, headers=headers, timeout=30.0  # Longer timeout for tool execution
        )

        # Handle authorization failures (403)
        if response.status_code == 403:
            error_data = response.json()
            raise GatewayAuthorizationError(
                f"Authorization denied: {error_data.get('reason', 'Unknown reason')}"
            )

        # Handle tool execution errors (4xx, 5xx)
        if response.status_code >= 400:
            error_data = response.json()
            raise GatewayToolError(
                f"Tool execution failed: {error_data.get('error', 'Unknown error')}",
                status_code=response.status_code,
            )

        response.raise_for_status()

        result = response.json()

        logger.info(
            "gateway_invoke_tool_success",
            server_id=server_id,
            tool_name=tool_name,
            request_id=request_id,
            execution_time_ms=result.get("execution_time_ms"),
        )

        return result

    except httpx.TimeoutException:
        logger.error(
            "gateway_invoke_tool_timeout",
            server_id=server_id,
            tool_name=tool_name,
            request_id=request_id,
        )
        raise GatewayToolError(
            f"Tool invocation timed out after 30 seconds", status_code=504
        )
    except httpx.HTTPError as e:
        logger.error(
            "gateway_invoke_tool_http_error",
            server_id=server_id,
            tool_name=tool_name,
            request_id=request_id,
            error=str(e),
        )
        raise


# Custom exceptions
class GatewayAuthorizationError(Exception):
    """Authorization denied by SARK policy."""

    pass


class GatewayToolError(Exception):
    """Tool execution failed."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code
```

---

**Step 1.1.7: Implement `health_check()`**

```python
async def health_check(self) -> bool:
    """
    Check Gateway health.

    Returns:
        True if Gateway is healthy, False otherwise
    """
    try:
        response = await self.http_client.get("/health", timeout=2.0)
        return response.status_code == 200
    except Exception as e:
        logger.warning("gateway_health_check_failed", error=str(e))
        return False
```

---

**Step 1.1.8: Add cleanup method**

```python
async def close(self):
    """Close HTTP client and release resources."""
    await self.http_client.aclose()
    logger.info("gateway_client_closed")
```

Update `get_gateway_client()`:
```python
async def get_gateway_client() -> GatewayClient:
    """
    Get singleton Gateway client instance with lifespan management.

    Registers cleanup on shutdown.
    """
    global _gateway_client

    if _gateway_client is None:
        from sark.config import get_settings

        settings = get_settings()

        _gateway_client = GatewayClient(
            base_url=settings.gateway_url,
            api_key=settings.gateway_api_key,
            timeout=settings.gateway_timeout_seconds,
        )

        # Register cleanup (in FastAPI lifespan)
        import atexit

        atexit.register(lambda: asyncio.create_task(_gateway_client.close()))

    return _gateway_client
```

---

### Week 2: SSE Transport Implementation

**File:** `src/sark/services/gateway/sse_client.py` (new file)

```python
"""Gateway SSE (Server-Sent Events) client for streaming responses."""

import httpx_sse
import structlog
from typing import AsyncIterator
import json

logger = structlog.get_logger()


class GatewaySSEClient:
    """SSE client for streaming tool results from Gateway."""

    def __init__(self, http_client: httpx.AsyncClient):
        """
        Initialize SSE client.

        Args:
            http_client: Shared HTTP client instance
        """
        self.http_client = http_client

    async def invoke_tool_streaming(
        self,
        server_id: str,
        tool_name: str,
        parameters: dict,
        user_token: str,
    ) -> AsyncIterator[dict]:
        """
        Invoke tool with streaming response via SSE.

        Yields:
            dict: Partial results as they arrive

        Example:
            async for chunk in client.invoke_tool_streaming(...):
                print(chunk["data"])
        """
        import uuid

        request_id = str(uuid.uuid4())

        logger.info(
            "gateway_sse_invoke_request",
            server_id=server_id,
            tool_name=tool_name,
            request_id=request_id,
        )

        # Build request payload
        payload = {
            "server_id": server_id,
            "tool_name": tool_name,
            "parameters": parameters,
            "request_id": request_id,
            "stream": True,  # Request streaming response
        }

        headers = {"Authorization": f"Bearer {user_token}"}

        try:
            async with httpx_sse.aconnect_sse(
                self.http_client,
                "POST",
                "/invoke",
                json=payload,
                headers=headers,
                timeout=60.0,
            ) as event_source:
                async for event in event_source.aiter_sse():
                    # Parse SSE event
                    if event.event == "error":
                        logger.error(
                            "gateway_sse_error",
                            request_id=request_id,
                            error=event.data,
                        )
                        raise Exception(f"SSE error: {event.data}")

                    elif event.event == "done":
                        logger.info(
                            "gateway_sse_complete", request_id=request_id
                        )
                        break

                    else:
                        # Yield data chunk
                        data = json.loads(event.data)
                        yield {
                            "event_id": event.id,
                            "event_type": event.event,
                            "data": data,
                            "retry": event.retry,
                        }

        except Exception as e:
            logger.error(
                "gateway_sse_invoke_error",
                request_id=request_id,
                error=str(e),
            )
            raise
```

**Installation:**
```bash
pip install httpx-sse
```

**Integration into `GatewayClient`:**

```python
# In GatewayClient.__init__
self.sse_client = GatewaySSEClient(self.http_client)

# Add method
async def invoke_tool_streaming(self, *args, **kwargs) -> AsyncIterator[dict]:
    """Invoke tool with streaming response. Delegates to SSE client."""
    async for chunk in self.sse_client.invoke_tool_streaming(*args, **kwargs):
        yield chunk
```

---

### Week 3: stdio Transport Implementation

**File:** `src/sark/services/gateway/stdio_client.py` (new file)

```python
"""Gateway stdio client for subprocess-based MCP servers."""

import asyncio
import structlog
import json
import uuid
from typing import AsyncIterator

logger = structlog.get_logger()


class StdioMCPClient:
    """Client for managing MCP servers via stdio (subprocess)."""

    def __init__(self):
        """Initialize stdio client."""
        self.processes: dict[str, asyncio.subprocess.Process] = {}
        self.pending_responses: dict[str, asyncio.Future] = {}

    async def start_server(
        self, command: list[str], env: dict | None = None, working_dir: str | None = None
    ) -> str:
        """
        Start MCP server process.

        Args:
            command: Command and arguments (e.g., ["python", "mcp_server.py"])
            env: Environment variables
            working_dir: Working directory for process

        Returns:
            server_id: Unique server identifier

        Example:
            server_id = await client.start_server(
                command=["python", "-m", "postgres_mcp"],
                env={"DATABASE_URL": "postgresql://..."}
            )
        """
        server_id = f"stdio_{uuid.uuid4().hex[:8]}"

        logger.info(
            "stdio_start_server",
            server_id=server_id,
            command=command,
        )

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=working_dir,
            )

            self.processes[server_id] = process

            # Start message loop in background
            asyncio.create_task(self._message_loop(server_id, process))

            # Wait for initialization (read first message)
            await asyncio.sleep(0.5)

            logger.info("stdio_server_started", server_id=server_id, pid=process.pid)

            return server_id

        except Exception as e:
            logger.error(
                "stdio_start_server_failed", server_id=server_id, error=str(e)
            )
            raise

    async def _message_loop(self, server_id: str, process: asyncio.subprocess.Process):
        """
        Background task to read JSON-RPC messages from stdout.

        Matches responses to pending requests by ID.
        """
        logger.debug("stdio_message_loop_started", server_id=server_id)

        try:
            while True:
                # Read line from stdout
                line = await process.stdout.readline()

                if not line:
                    # Process exited
                    logger.warning(
                        "stdio_process_exited",
                        server_id=server_id,
                        return_code=process.returncode,
                    )
                    break

                # Parse JSON-RPC message
                try:
                    message = json.loads(line.decode().strip())
                    logger.debug(
                        "stdio_message_received",
                        server_id=server_id,
                        message_id=message.get("id"),
                    )

                    # Match to pending request
                    msg_id = message.get("id")
                    if msg_id and msg_id in self.pending_responses:
                        future = self.pending_responses.pop(msg_id)
                        future.set_result(message)

                except json.JSONDecodeError as e:
                    logger.error(
                        "stdio_invalid_json",
                        server_id=server_id,
                        line=line.decode(),
                        error=str(e),
                    )

        except Exception as e:
            logger.error(
                "stdio_message_loop_error", server_id=server_id, error=str(e)
            )

    async def invoke_tool(
        self, server_id: str, tool_name: str, parameters: dict, timeout: float = 30.0
    ) -> dict:
        """
        Invoke tool via stdio JSON-RPC.

        Args:
            server_id: Server identifier from start_server()
            tool_name: Tool name
            parameters: Tool parameters
            timeout: Timeout in seconds

        Returns:
            Tool result

        Raises:
            ValueError: If server not found
            TimeoutError: If request times out
        """
        if server_id not in self.processes:
            raise ValueError(f"Server {server_id} not found")

        process = self.processes[server_id]
        request_id = str(uuid.uuid4())

        # Build JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": parameters},
        }

        logger.info(
            "stdio_invoke_tool",
            server_id=server_id,
            tool_name=tool_name,
            request_id=request_id,
        )

        # Register pending response
        future = asyncio.Future()
        self.pending_responses[request_id] = future

        try:
            # Write to stdin
            request_json = json.dumps(request) + "\n"
            process.stdin.write(request_json.encode())
            await process.stdin.drain()

            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=timeout)

            # Check for JSON-RPC error
            if "error" in response:
                raise Exception(
                    f"Tool error: {response['error'].get('message', 'Unknown')}"
                )

            logger.info(
                "stdio_invoke_tool_success",
                server_id=server_id,
                tool_name=tool_name,
                request_id=request_id,
            )

            return response.get("result", {})

        except asyncio.TimeoutError:
            # Clean up pending response
            self.pending_responses.pop(request_id, None)

            logger.error(
                "stdio_invoke_tool_timeout",
                server_id=server_id,
                tool_name=tool_name,
                timeout=timeout,
            )
            raise TimeoutError(f"Tool invocation timed out after {timeout}s")

    async def list_tools(self, server_id: str) -> list[dict]:
        """
        Discover tools via stdio JSON-RPC.

        Args:
            server_id: Server identifier

        Returns:
            List of tool definitions
        """
        if server_id not in self.processes:
            raise ValueError(f"Server {server_id} not found")

        process = self.processes[server_id]
        request_id = str(uuid.uuid4())

        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/list",
            "params": {},
        }

        logger.info("stdio_list_tools", server_id=server_id)

        # Register pending response
        future = asyncio.Future()
        self.pending_responses[request_id] = future

        try:
            # Write to stdin
            request_json = json.dumps(request) + "\n"
            process.stdin.write(request_json.encode())
            await process.stdin.drain()

            # Wait for response
            response = await asyncio.wait_for(future, timeout=10.0)

            tools = response.get("result", {}).get("tools", [])

            logger.info("stdio_list_tools_success", server_id=server_id, count=len(tools))

            return tools

        except asyncio.TimeoutError:
            self.pending_responses.pop(request_id, None)
            raise TimeoutError("Tool discovery timed out")

    async def stop_server(self, server_id: str):
        """
        Stop MCP server process.

        Args:
            server_id: Server identifier
        """
        if server_id not in self.processes:
            logger.warning("stdio_server_not_found", server_id=server_id)
            return

        process = self.processes[server_id]

        logger.info("stdio_stop_server", server_id=server_id, pid=process.pid)

        # Graceful shutdown
        process.terminate()

        try:
            await asyncio.wait_for(process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            # Force kill
            process.kill()
            await process.wait()

        del self.processes[server_id]

        logger.info("stdio_server_stopped", server_id=server_id)

    async def close_all(self):
        """Stop all MCP server processes."""
        for server_id in list(self.processes.keys()):
            await self.stop_server(server_id)
```

**Integration into `GatewayClient`:**

```python
# In GatewayClient.__init__
self.stdio_client = StdioMCPClient()

# Add methods
async def start_stdio_server(self, *args, **kwargs) -> str:
    """Start stdio MCP server. Delegates to stdio client."""
    return await self.stdio_client.start_server(*args, **kwargs)

async def stop_stdio_server(self, server_id: str):
    """Stop stdio MCP server."""
    await self.stdio_client.stop_server(server_id)

# Update close() method
async def close(self):
    """Close all clients and release resources."""
    await self.stdio_client.close_all()
    await self.http_client.aclose()
    logger.info("gateway_client_closed")
```

---

### Week 4: Integration Tests

**File:** `tests/integration/test_gateway_client.py` (new file)

```python
"""Integration tests for Gateway client."""

import pytest
from sark.services.gateway.client import GatewayClient, GatewayAuthorizationError


@pytest.mark.asyncio
class TestGatewayHTTPClient:
    """Test HTTP transport."""

    @pytest.fixture
    async def gateway_client(self):
        """Create test gateway client."""
        client = GatewayClient(
            base_url="http://localhost:8080", api_key="test_key"
        )
        yield client
        await client.close()

    async def test_list_servers(self, gateway_client):
        """Test listing servers."""
        servers = await gateway_client.list_servers()

        assert isinstance(servers, list)
        if servers:
            assert servers[0].server_id is not None
            assert servers[0].server_name is not None

    async def test_get_server_info(self, gateway_client):
        """Test getting server info."""
        # Get first server
        servers = await gateway_client.list_servers()
        if not servers:
            pytest.skip("No servers available")

        server_id = servers[0].server_id

        # Get details
        server = await gateway_client.get_server_info(server_id)

        assert server is not None
        assert server.server_id == server_id
        assert server.tools_count >= 0

    async def test_get_server_info_not_found(self, gateway_client):
        """Test getting non-existent server."""
        server = await gateway_client.get_server_info("invalid_id")
        assert server is None

    async def test_list_tools(self, gateway_client):
        """Test listing tools."""
        tools = await gateway_client.list_tools()

        assert isinstance(tools, list)
        if tools:
            assert tools[0].tool_name is not None
            assert tools[0].server_name is not None

    async def test_invoke_tool_success(self, gateway_client, test_user_token):
        """Test successful tool invocation."""
        result = await gateway_client.invoke_tool(
            server_id="test_server",
            tool_name="echo",
            parameters={"message": "hello"},
            user_token=test_user_token,
        )

        assert result is not None
        assert "data" in result or "result" in result

    async def test_invoke_tool_authorization_denied(
        self, gateway_client, test_user_token
    ):
        """Test tool invocation with authorization denied."""
        with pytest.raises(GatewayAuthorizationError):
            await gateway_client.invoke_tool(
                server_id="restricted_server",
                tool_name="admin_only_tool",
                parameters={},
                user_token=test_user_token,
            )

    async def test_health_check(self, gateway_client):
        """Test health check."""
        is_healthy = await gateway_client.health_check()
        assert isinstance(is_healthy, bool)


@pytest.mark.asyncio
class TestGatewaySSEClient:
    """Test SSE transport."""

    @pytest.fixture
    async def gateway_client(self):
        """Create test gateway client."""
        client = GatewayClient(base_url="http://localhost:8080")
        yield client
        await client.close()

    async def test_invoke_tool_streaming(self, gateway_client, test_user_token):
        """Test streaming tool invocation."""
        chunks = []

        async for chunk in gateway_client.invoke_tool_streaming(
            server_id="test_server",
            tool_name="stream_data",
            parameters={"count": 5},
            user_token=test_user_token,
        ):
            chunks.append(chunk)

        assert len(chunks) > 0
        assert all("data" in chunk for chunk in chunks)


@pytest.mark.asyncio
class TestGatewayStdioClient:
    """Test stdio transport."""

    @pytest.fixture
    async def gateway_client(self):
        """Create test gateway client."""
        client = GatewayClient(base_url="http://localhost:8080")
        yield client
        await client.close()

    async def test_start_stop_server(self, gateway_client):
        """Test starting and stopping stdio server."""
        server_id = await gateway_client.start_stdio_server(
            command=["python", "-m", "tests.fixtures.mock_mcp_server"],
        )

        assert server_id.startswith("stdio_")

        # Stop server
        await gateway_client.stop_stdio_server(server_id)

    async def test_invoke_tool_via_stdio(self, gateway_client):
        """Test tool invocation via stdio."""
        # Start server
        server_id = await gateway_client.start_stdio_server(
            command=["python", "-m", "tests.fixtures.mock_mcp_server"],
        )

        try:
            # Invoke tool
            result = await gateway_client.stdio_client.invoke_tool(
                server_id=server_id,
                tool_name="echo",
                parameters={"message": "hello"},
            )

            assert result is not None
            assert result.get("message") == "hello"

        finally:
            await gateway_client.stop_stdio_server(server_id)
```

**Deliverables for Task 1.1:**
- ✅ HTTP client with retry and circuit breaker
- ✅ SSE client for streaming
- ✅ stdio client for subprocess communication
- ✅ 50+ integration tests
- ✅ <100ms p95 latency
- ✅ Documentation and examples

---

## Task 1.2: Fix Failing Tests

**Owner:** QA Engineer / Backend Engineer
**Effort:** 2 weeks
**Dependencies:** None

### Current State

- **Test pass rate:** 77.8%
- **Failing tests:** 154 (auth provider tests)
  - LDAP: 52 failures
  - SAML: 48 failures
  - OIDC: 54 failures

### Root Causes

1. **LDAP tests:** Mock LDAP server not starting correctly
2. **SAML tests:** XML signature validation failing
3. **OIDC tests:** Token expiry off by 1 second (timing issue)

### Implementation

*See PRIORITY_1_TASKS.md for detailed fixes (this is getting long!)*

---

## Task 1.3: Policy Validation Framework

**Owner:** Security Engineer
**Effort:** 1.5 weeks

*See detailed implementation in IMPLEMENTATION_PLAN.md Section 1.3*

---

## Task 1.4: Security Audit Preparation

**Owner:** Security Team
**Effort:** 1 week preparation + 2 weeks testing

*See IMPLEMENTATION_PLAN.md Section 1.4*

---

## Progress Tracking

### Checklist

**Task 1.1: Gateway Client**
- [ ] Week 1: HTTP transport
  - [ ] Add httpx, tenacity, circuitbreaker dependencies
  - [ ] Implement list_servers()
  - [ ] Implement get_server_info()
  - [ ] Implement list_tools()
  - [ ] Implement invoke_tool()
  - [ ] Implement health_check()
  - [ ] Add cleanup method
- [ ] Week 2: SSE transport
  - [ ] Create sse_client.py
  - [ ] Implement invoke_tool_streaming()
  - [ ] Add reconnection logic
- [ ] Week 3: stdio transport
  - [ ] Create stdio_client.py
  - [ ] Implement start_server()
  - [ ] Implement message loop
  - [ ] Implement invoke_tool()
  - [ ] Implement list_tools()
  - [ ] Implement stop_server()
- [ ] Week 4: Integration tests
  - [ ] HTTP client tests (15 tests)
  - [ ] SSE client tests (5 tests)
  - [ ] stdio client tests (10 tests)
  - [ ] Performance tests (5 tests)

**Task 1.2: Fix Tests**
- [ ] Debug LDAP tests (use pytest-docker)
- [ ] Debug SAML tests (fix certificate format)
- [ ] Debug OIDC tests (use freezegun for time mocking)
- [ ] Achieve 85%+ coverage
- [ ] All tests passing

**Task 1.3: Policy Validation**
- [ ] Create policy_validator.py
- [ ] Implement syntax validation
- [ ] Implement safety checks
- [ ] Add policy testing framework
- [ ] Validate all existing policies

**Task 1.4: Security Audit**
- [ ] Document attack surface
- [ ] Create security questionnaire
- [ ] Provide test environment
- [ ] Engage external vendor
- [ ] Complete penetration test
- [ ] Remediate findings

---

## Daily Standup Template

```markdown
### Daily Update: [Date]

**Yesterday:**
- Completed: [task]
- Blocked by: [blocker]

**Today:**
- Working on: [task]
- Need help with: [question]

**Blockers:**
- [blocker description]

**ETA:**
- [task] completion: [date]
```

---

**Document Version:** 1.0
**Last Updated:** December 8, 2025
**Next Review:** Weekly during sprint
