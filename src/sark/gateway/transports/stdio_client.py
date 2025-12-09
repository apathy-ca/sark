"""Stdio transport for MCP Gateway communication.

Provides subprocess-based MCP communication via stdin/stdout with:
- Process lifecycle management (start/stop/restart)
- JSON-RPC 2.0 message handling
- Health checks with heartbeat monitoring
- Resource limits enforcement
- Auto-restart on crash
- Clean shutdown handling
"""

import asyncio
import json
import os
import psutil
import signal
import structlog
from asyncio import StreamReader, StreamWriter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

logger = structlog.get_logger()


@dataclass
class ResourceLimits:
    """Resource limits for subprocess monitoring."""

    max_memory_mb: int = 1024  # 1GB
    max_cpu_percent: float = 80.0
    max_file_descriptors: int = 1000


@dataclass
class HealthConfig:
    """Health check configuration."""

    heartbeat_interval: float = 10.0  # seconds
    hung_timeout: float = 15.0  # seconds - time to detect hung process


class StdioTransportError(Exception):
    """Base exception for stdio transport errors."""


class ProcessStartError(StdioTransportError):
    """Failed to start subprocess."""


class ProcessCrashError(StdioTransportError):
    """Subprocess crashed unexpectedly."""


class ResourceLimitExceededError(StdioTransportError):
    """Subprocess exceeded resource limits."""


class StdioTransport:
    """
    Stdio transport for MCP communication via subprocess.

    Manages a subprocess that communicates using JSON-RPC 2.0 over stdin/stdout.
    Provides comprehensive process lifecycle management, health monitoring,
    and resource limit enforcement.

    Example:
        ```python
        transport = StdioTransport(
            command=["python", "mcp_server.py"],
            cwd="/path/to/server",
        )
        await transport.start()
        try:
            response = await transport.send_request("tools/list", {})
            print(response)
        finally:
            await transport.stop()
        ```
    """

    def __init__(
        self,
        command: list[str],
        cwd: Optional[str] = None,
        env: Optional[dict[str, str]] = None,
        resource_limits: Optional[ResourceLimits] = None,
        health_config: Optional[HealthConfig] = None,
        max_restart_attempts: int = 3,
    ):
        """
        Initialize stdio transport.

        Args:
            command: Command and arguments to execute (e.g., ["python", "server.py"])
            cwd: Working directory for subprocess (defaults to current dir)
            env: Environment variables for subprocess (inherits parent env if None)
            resource_limits: Resource limits configuration
            health_config: Health check configuration
            max_restart_attempts: Maximum auto-restart attempts on crash
        """
        self.command = command
        self.cwd = cwd or os.getcwd()
        self.env = {**os.environ, **(env or {})}
        self.resource_limits = resource_limits or ResourceLimits()
        self.health_config = health_config or HealthConfig()
        self.max_restart_attempts = max_restart_attempts

        # Process state
        self._process: Optional[asyncio.subprocess.Process] = None
        self._stdin: Optional[StreamWriter] = None
        self._stdout: Optional[StreamReader] = None
        self._stderr: Optional[StreamReader] = None
        self._psutil_process: Optional[psutil.Process] = None

        # Health monitoring
        self._last_heartbeat: Optional[datetime] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._stderr_reader_task: Optional[asyncio.Task] = None

        # Restart tracking
        self._restart_count: int = 0
        self._is_shutting_down: bool = False
        self._request_id_counter: int = 0

        # Pending requests
        self._pending_requests: dict[int, asyncio.Future] = {}

    async def start(self) -> None:
        """
        Start the subprocess and initialize communication.

        Raises:
            ProcessStartError: If subprocess fails to start
        """
        if self._process is not None:
            logger.warning("stdio_transport_already_started", command=self.command)
            return

        try:
            logger.info(
                "stdio_transport_starting",
                command=self.command,
                cwd=self.cwd,
            )

            # Create subprocess
            self._process = await asyncio.create_subprocess_exec(
                *self.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cwd,
                env=self.env,
            )

            self._stdin = self._process.stdin
            self._stdout = self._process.stdout
            self._stderr = self._process.stderr

            # Get psutil process for resource monitoring
            self._psutil_process = psutil.Process(self._process.pid)

            # Start health monitoring
            self._last_heartbeat = datetime.now(timezone.utc)
            self._health_check_task = asyncio.create_task(self._health_check_loop())

            # Start stderr reader
            self._stderr_reader_task = asyncio.create_task(self._read_stderr())

            # Start stdout reader
            asyncio.create_task(self._read_stdout())

            logger.info(
                "stdio_transport_started",
                command=self.command,
                pid=self._process.pid,
            )

        except Exception as e:
            logger.error(
                "stdio_transport_start_failed",
                command=self.command,
                error=str(e),
            )
            await self._cleanup()
            raise ProcessStartError(f"Failed to start subprocess: {e}") from e

    async def stop(self, timeout: float = 5.0) -> None:
        """
        Stop the subprocess gracefully.

        Args:
            timeout: Seconds to wait for graceful shutdown before force kill
        """
        if self._process is None:
            return

        self._is_shutting_down = True

        logger.info(
            "stdio_transport_stopping",
            pid=self._process.pid,
            timeout=timeout,
        )

        try:
            # Send SIGTERM for graceful shutdown
            if self._process.returncode is None:
                self._process.send_signal(signal.SIGTERM)

                try:
                    # Wait for graceful shutdown
                    await asyncio.wait_for(self._process.wait(), timeout=timeout)
                    logger.info(
                        "stdio_transport_stopped_gracefully",
                        pid=self._process.pid,
                    )
                except asyncio.TimeoutError:
                    # Force kill if graceful shutdown times out
                    logger.warning(
                        "stdio_transport_force_killing",
                        pid=self._process.pid,
                    )
                    self._process.kill()
                    await self._process.wait()

        finally:
            await self._cleanup()

    async def send_request(self, method: str, params: Any, timeout: float = 30.0) -> Any:
        """
        Send JSON-RPC 2.0 request and wait for response.

        Args:
            method: JSON-RPC method name
            params: Method parameters
            timeout: Request timeout in seconds

        Returns:
            Response result

        Raises:
            StdioTransportError: If transport is not started or request fails
            asyncio.TimeoutError: If request times out
        """
        if self._process is None or self._stdin is None:
            raise StdioTransportError("Transport not started")

        # Generate request ID
        request_id = self._request_id_counter
        self._request_id_counter += 1

        # Create JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        # Create future for response
        future: asyncio.Future = asyncio.Future()
        self._pending_requests[request_id] = future

        try:
            # Send request
            message = json.dumps(request) + "\n"
            self._stdin.write(message.encode("utf-8"))
            await self._stdin.drain()

            logger.debug(
                "stdio_transport_request_sent",
                method=method,
                request_id=request_id,
            )

            # Update heartbeat
            self._last_heartbeat = datetime.now(timezone.utc)

            # Wait for response
            return await asyncio.wait_for(future, timeout=timeout)

        except asyncio.TimeoutError:
            logger.error(
                "stdio_transport_request_timeout",
                method=method,
                request_id=request_id,
                timeout=timeout,
            )
            raise
        finally:
            # Clean up pending request
            self._pending_requests.pop(request_id, None)

    async def send_notification(self, method: str, params: Any) -> None:
        """
        Send JSON-RPC 2.0 notification (no response expected).

        Args:
            method: JSON-RPC method name
            params: Method parameters

        Raises:
            StdioTransportError: If transport is not started
        """
        if self._process is None or self._stdin is None:
            raise StdioTransportError("Transport not started")

        # Create JSON-RPC notification (no id field)
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }

        # Send notification
        message = json.dumps(notification) + "\n"
        self._stdin.write(message.encode("utf-8"))
        await self._stdin.drain()

        logger.debug(
            "stdio_transport_notification_sent",
            method=method,
        )

        # Update heartbeat
        self._last_heartbeat = datetime.now(timezone.utc)

    async def restart(self) -> None:
        """
        Restart the subprocess.

        Raises:
            ProcessStartError: If restart fails
        """
        logger.info("stdio_transport_restarting", restart_count=self._restart_count)

        await self.stop(timeout=3.0)
        self._restart_count += 1

        if self._restart_count > self.max_restart_attempts:
            raise ProcessCrashError(
                f"Exceeded max restart attempts ({self.max_restart_attempts})"
            )

        await self.start()

    @property
    def is_running(self) -> bool:
        """Check if subprocess is running."""
        return (
            self._process is not None
            and self._process.returncode is None
            and not self._is_shutting_down
        )

    @property
    def pid(self) -> Optional[int]:
        """Get subprocess PID."""
        return self._process.pid if self._process else None

    async def _read_stdout(self) -> None:
        """Read and process JSON-RPC messages from stdout."""
        if self._stdout is None:
            return

        try:
            while True:
                line = await self._stdout.readline()
                if not line:
                    # EOF - process exited
                    if not self._is_shutting_down:
                        logger.error(
                            "stdio_transport_unexpected_eof",
                            pid=self.pid,
                        )
                        # Auto-restart on crash
                        if self._restart_count < self.max_restart_attempts:
                            asyncio.create_task(self.restart())
                    break

                try:
                    # Parse JSON-RPC message
                    message = json.loads(line.decode("utf-8"))

                    # Handle response
                    if "id" in message and "result" in message:
                        request_id = message["id"]
                        if request_id in self._pending_requests:
                            self._pending_requests[request_id].set_result(message["result"])

                    # Handle error response
                    elif "id" in message and "error" in message:
                        request_id = message["id"]
                        if request_id in self._pending_requests:
                            error = message["error"]
                            self._pending_requests[request_id].set_exception(
                                StdioTransportError(
                                    f"JSON-RPC error: {error.get('message', 'Unknown error')}"
                                )
                            )

                    # Update heartbeat
                    self._last_heartbeat = datetime.now(timezone.utc)

                except json.JSONDecodeError as e:
                    logger.warning(
                        "stdio_transport_invalid_json",
                        line=line.decode("utf-8", errors="replace"),
                        error=str(e),
                    )

        except Exception as e:
            logger.error(
                "stdio_transport_stdout_reader_error",
                error=str(e),
            )

    async def _read_stderr(self) -> None:
        """Read and log stderr output."""
        if self._stderr is None:
            return

        try:
            while True:
                line = await self._stderr.readline()
                if not line:
                    break

                # Log stderr as warning
                logger.warning(
                    "stdio_transport_stderr",
                    pid=self.pid,
                    output=line.decode("utf-8", errors="replace").strip(),
                )

        except Exception as e:
            logger.error(
                "stdio_transport_stderr_reader_error",
                error=str(e),
            )

    async def _health_check_loop(self) -> None:
        """Periodic health check and resource monitoring."""
        while self.is_running:
            try:
                await asyncio.sleep(self.health_config.heartbeat_interval)

                # Check for hung process
                if self._last_heartbeat:
                    time_since_heartbeat = (
                        datetime.now(timezone.utc) - self._last_heartbeat
                    ).total_seconds()

                    if time_since_heartbeat > self.health_config.hung_timeout:
                        logger.error(
                            "stdio_transport_hung_process",
                            pid=self.pid,
                            time_since_heartbeat=time_since_heartbeat,
                        )
                        # Kill and restart hung process
                        if self._restart_count < self.max_restart_attempts:
                            asyncio.create_task(self.restart())
                        break

                # Check resource limits
                if self._psutil_process and self._psutil_process.is_running():
                    try:
                        # Memory check
                        memory_mb = self._psutil_process.memory_info().rss / 1024 / 1024
                        if memory_mb > self.resource_limits.max_memory_mb:
                            logger.error(
                                "stdio_transport_memory_limit_exceeded",
                                pid=self.pid,
                                memory_mb=memory_mb,
                                limit_mb=self.resource_limits.max_memory_mb,
                            )
                            raise ResourceLimitExceededError(
                                f"Memory limit exceeded: {memory_mb}MB > {self.resource_limits.max_memory_mb}MB"
                            )

                        # CPU check
                        cpu_percent = self._psutil_process.cpu_percent(interval=1.0)
                        if cpu_percent > self.resource_limits.max_cpu_percent:
                            logger.warning(
                                "stdio_transport_high_cpu",
                                pid=self.pid,
                                cpu_percent=cpu_percent,
                                limit=self.resource_limits.max_cpu_percent,
                            )

                        # File descriptor check
                        num_fds = self._psutil_process.num_fds()
                        if num_fds > self.resource_limits.max_file_descriptors:
                            logger.error(
                                "stdio_transport_fd_limit_exceeded",
                                pid=self.pid,
                                num_fds=num_fds,
                                limit=self.resource_limits.max_file_descriptors,
                            )
                            raise ResourceLimitExceededError(
                                f"FD limit exceeded: {num_fds} > {self.resource_limits.max_file_descriptors}"
                            )

                    except psutil.NoSuchProcess:
                        logger.error(
                            "stdio_transport_process_disappeared",
                            pid=self.pid,
                        )
                        break

            except ResourceLimitExceededError:
                # Kill process that exceeded limits
                if self._process and self._process.returncode is None:
                    self._process.kill()
                    await self._process.wait()
                break

            except Exception as e:
                logger.error(
                    "stdio_transport_health_check_error",
                    error=str(e),
                )

    async def _cleanup(self) -> None:
        """Clean up resources."""
        # Cancel health check task
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Cancel stderr reader task
        if self._stderr_reader_task and not self._stderr_reader_task.done():
            self._stderr_reader_task.cancel()
            try:
                await self._stderr_reader_task
            except asyncio.CancelledError:
                pass

        # Fail pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.set_exception(StdioTransportError("Transport stopped"))
        self._pending_requests.clear()

        # Close streams
        if self._stdin and not self._stdin.is_closing():
            self._stdin.close()
            try:
                await self._stdin.wait_closed()
            except Exception:
                pass

        # Reset state
        self._process = None
        self._stdin = None
        self._stdout = None
        self._stderr = None
        self._psutil_process = None
        self._health_check_task = None
        self._stderr_reader_task = None
        self._is_shutting_down = False

        logger.info("stdio_transport_cleaned_up")
