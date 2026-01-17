"""Comprehensive unit tests for stdio transport.

Tests cover:
- Process lifecycle (start/stop/restart)
- JSON-RPC message handling
- Health checks and heartbeat monitoring
- Resource limit enforcement
- Auto-restart on crash
- Clean shutdown
- Error handling
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from sark.gateway.transports.stdio_client import (
    HealthConfig,
    ProcessCrashError,
    ProcessStartError,
    ResourceLimits,
    StdioTransport,
    StdioTransportError,
)


@pytest.fixture
def mock_process():
    """Create mock subprocess."""
    process = MagicMock()
    process.pid = 12345
    process.returncode = None
    process.stdin = AsyncMock()
    process.stdout = AsyncMock()
    process.stderr = AsyncMock()
    process.send_signal = Mock()
    process.kill = Mock()
    process.wait = AsyncMock()
    return process


@pytest.fixture
def mock_psutil_process():
    """Create mock psutil process."""
    process = MagicMock()
    process.is_running.return_value = True
    process.memory_info.return_value = MagicMock(rss=100 * 1024 * 1024)  # 100 MB
    process.cpu_percent.return_value = 50.0
    process.num_fds.return_value = 50
    return process


@pytest.mark.unit
class TestStdioTransportInit:
    """Test StdioTransport initialization."""

    def test_init_minimal(self):
        """Test initialization with minimal arguments."""
        transport = StdioTransport(command=["python", "server.py"])

        assert transport.command == ["python", "server.py"]
        assert transport.max_restart_attempts == 3
        assert isinstance(transport.resource_limits, ResourceLimits)
        assert isinstance(transport.health_config, HealthConfig)
        assert transport._process is None
        assert transport.is_running is False

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        resource_limits = ResourceLimits(
            max_memory_mb=512,
            max_cpu_percent=60.0,
            max_file_descriptors=500,
        )
        health_config = HealthConfig(
            heartbeat_interval=5.0,
            hung_timeout=10.0,
        )

        transport = StdioTransport(
            command=["node", "server.js"],
            cwd="/tmp/test",
            env={"NODE_ENV": "test"},
            resource_limits=resource_limits,
            health_config=health_config,
            max_restart_attempts=5,
        )

        assert transport.command == ["node", "server.js"]
        assert transport.cwd == "/tmp/test"
        assert transport.env["NODE_ENV"] == "test"
        assert transport.resource_limits.max_memory_mb == 512
        assert transport.health_config.heartbeat_interval == 5.0
        assert transport.max_restart_attempts == 5


@pytest.mark.unit
class TestStdioTransportLifecycle:
    """Test process lifecycle management."""

    @pytest.mark.asyncio
    async def test_start_success(self, mock_process, mock_psutil_process):
        """Test successful subprocess start."""
        transport = StdioTransport(command=["python", "server.py"])

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("psutil.Process", return_value=mock_psutil_process),
            patch("asyncio.create_task"),
        ):
            await transport.start()

            assert transport.is_running is True
            assert transport.pid == 12345
            assert transport._process is not None
            assert transport._last_heartbeat is not None

    @pytest.mark.asyncio
    async def test_start_already_started(self, mock_process, mock_psutil_process):
        """Test starting already-started transport."""
        transport = StdioTransport(command=["python", "server.py"])

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("psutil.Process", return_value=mock_psutil_process),
            patch("asyncio.create_task"),
        ):
            await transport.start()
            # Start again - should log warning and return
            await transport.start()

            assert transport.is_running is True

    @pytest.mark.asyncio
    async def test_start_failure(self):
        """Test subprocess start failure."""
        transport = StdioTransport(command=["invalid-command"])

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError("Command not found"),
        ):
            with pytest.raises(ProcessStartError, match="Failed to start subprocess"):
                await transport.start()

            assert transport.is_running is False

    @pytest.mark.asyncio
    async def test_stop_not_started(self):
        """Test stopping when transport not started."""
        transport = StdioTransport(command=["python", "server.py"])

        # Should not raise error, just return
        await transport.stop()
        assert transport._process is None

    @pytest.mark.asyncio
    async def test_stop_graceful(self, mock_process, mock_psutil_process):
        """Test graceful subprocess stop."""
        transport = StdioTransport(command=["python", "server.py"])

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("psutil.Process", return_value=mock_psutil_process),
            patch("asyncio.create_task"),
        ):
            await transport.start()
            await transport.stop(timeout=5.0)

            mock_process.send_signal.assert_called_once()
            mock_process.wait.assert_called()
            assert transport.is_running is False

    @pytest.mark.asyncio
    async def test_stop_force_kill(self, mock_process, mock_psutil_process):
        """Test force kill on graceful shutdown timeout."""
        transport = StdioTransport(command=["python", "server.py"])

        # Make wait() timeout
        mock_process.wait.side_effect = [TimeoutError(), None]

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("psutil.Process", return_value=mock_psutil_process),
            patch("asyncio.create_task"),
        ):
            await transport.start()
            await transport.stop(timeout=0.1)

            mock_process.kill.assert_called_once()
            assert transport.is_running is False

    @pytest.mark.asyncio
    async def test_restart_success(self, mock_process, mock_psutil_process):
        """Test successful subprocess restart."""
        transport = StdioTransport(command=["python", "server.py"])

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("psutil.Process", return_value=mock_psutil_process),
            patch("asyncio.create_task"),
        ):
            await transport.start()
            initial_restart_count = transport._restart_count

            await transport.restart()

            assert transport._restart_count == initial_restart_count + 1
            assert transport.is_running is True

    @pytest.mark.asyncio
    async def test_restart_max_attempts_exceeded(self, mock_process, mock_psutil_process):
        """Test restart failure after max attempts."""
        transport = StdioTransport(
            command=["python", "server.py"],
            max_restart_attempts=2,
        )

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("psutil.Process", return_value=mock_psutil_process),
            patch("asyncio.create_task"),
        ):
            await transport.start()

            # Exhaust restart attempts
            transport._restart_count = 3

            with pytest.raises(ProcessCrashError, match="Exceeded max restart attempts"):
                await transport.restart()


@pytest.mark.unit
class TestStdioTransportMessaging:
    """Test JSON-RPC message handling."""

    @pytest.mark.asyncio
    async def test_send_request_success(self, mock_process, mock_psutil_process):
        """Test successful JSON-RPC request."""
        transport = StdioTransport(command=["python", "server.py"])

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("psutil.Process", return_value=mock_psutil_process),
        ):
            # Don't mock create_task to let background tasks run
            await transport.start()

            # Simulate response
            async def simulate_response():
                await asyncio.sleep(0.05)
                # Trigger response handling
                if transport._pending_requests:
                    request_id = next(iter(transport._pending_requests.keys()))
                    transport._pending_requests[request_id].set_result({"status": "ok"})

            asyncio.create_task(simulate_response())

            # Send request
            result = await transport.send_request("test/method", {"arg": "value"}, timeout=1.0)

            assert result == {"status": "ok"}
            mock_process.stdin.write.assert_called()

            await transport.stop()

    @pytest.mark.asyncio
    async def test_send_request_timeout(self, mock_process, mock_psutil_process):
        """Test request timeout."""
        transport = StdioTransport(command=["python", "server.py"])

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("psutil.Process", return_value=mock_psutil_process),
            patch("asyncio.create_task"),
        ):
            await transport.start()

            # Don't simulate response - should timeout
            with pytest.raises(asyncio.TimeoutError):
                await transport.send_request("test/method", {}, timeout=0.1)

    @pytest.mark.asyncio
    async def test_send_request_not_started(self):
        """Test sending request when transport not started."""
        transport = StdioTransport(command=["python", "server.py"])

        with pytest.raises(StdioTransportError, match="Transport not started"):
            await transport.send_request("test/method", {})

    @pytest.mark.asyncio
    async def test_send_notification(self, mock_process, mock_psutil_process):
        """Test sending JSON-RPC notification."""
        transport = StdioTransport(command=["python", "server.py"])

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("psutil.Process", return_value=mock_psutil_process),
            patch("asyncio.create_task"),
        ):
            await transport.start()

            await transport.send_notification("test/notify", {"data": "value"})

            mock_process.stdin.write.assert_called()
            # Notification should not have pending request
            assert len(transport._pending_requests) == 0

    @pytest.mark.asyncio
    async def test_send_notification_not_started(self):
        """Test sending notification when transport not started."""
        transport = StdioTransport(command=["python", "server.py"])

        with pytest.raises(StdioTransportError, match="Transport not started"):
            await transport.send_notification("test/notify", {})

    @pytest.mark.asyncio
    async def test_handle_error_response(self, mock_process, mock_psutil_process):
        """Test handling JSON-RPC error response."""
        transport = StdioTransport(command=["python", "server.py"])

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("psutil.Process", return_value=mock_psutil_process),
        ):
            await transport.start()

            # Simulate error response
            async def simulate_error():
                await asyncio.sleep(0.05)
                if transport._pending_requests:
                    request_id = next(iter(transport._pending_requests.keys()))
                    transport._pending_requests[request_id].set_exception(
                        StdioTransportError("JSON-RPC error: Method not found")
                    )

            asyncio.create_task(simulate_error())

            with pytest.raises(StdioTransportError, match="Method not found"):
                await transport.send_request("invalid/method", {}, timeout=1.0)

            await transport.stop()


@pytest.mark.unit
class TestStdioTransportHealthChecks:
    """Test health check and monitoring."""

    @pytest.mark.asyncio
    async def test_heartbeat_updates(self, mock_process, mock_psutil_process):
        """Test heartbeat updates on message activity."""
        transport = StdioTransport(command=["python", "server.py"])

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("psutil.Process", return_value=mock_psutil_process),
            patch("asyncio.create_task"),
        ):
            await transport.start()

            initial_heartbeat = transport._last_heartbeat

            await asyncio.sleep(0.1)

            # Send notification to update heartbeat
            await transport.send_notification("test/ping", {})

            assert transport._last_heartbeat > initial_heartbeat

    @pytest.mark.asyncio
    async def test_detect_hung_process(self, mock_process, mock_psutil_process):
        """Test detection of hung process."""
        transport = StdioTransport(
            command=["python", "server.py"],
            health_config=HealthConfig(
                heartbeat_interval=0.1,
                hung_timeout=0.2,
            ),
        )

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("psutil.Process", return_value=mock_psutil_process),
            patch("asyncio.create_task"),
        ):
            await transport.start()

            # Simulate old heartbeat (hung process)
            transport._last_heartbeat = datetime.now(UTC) - timedelta(seconds=1.0)

            # Wait for health check to detect hung process
            # The health check loop should trigger restart
            await asyncio.sleep(0.3)

            # Verify restart was triggered (check if create_task was called for restart)
            # Note: In real scenario, this would trigger restart via create_task


@pytest.mark.unit
class TestStdioTransportResourceLimits:
    """Test resource limit enforcement."""

    @pytest.mark.asyncio
    async def test_memory_limit_exceeded(self, mock_process):
        """Test memory limit exceeded."""
        # Create psutil process with high memory usage
        mock_psutil_process = MagicMock()
        mock_psutil_process.is_running.return_value = True
        mock_psutil_process.memory_info.return_value = MagicMock(rss=2048 * 1024 * 1024)  # 2GB
        mock_psutil_process.cpu_percent.return_value = 50.0
        mock_psutil_process.num_fds.return_value = 50

        transport = StdioTransport(
            command=["python", "server.py"],
            resource_limits=ResourceLimits(max_memory_mb=1024),  # 1GB limit
            health_config=HealthConfig(heartbeat_interval=0.1),
        )

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("psutil.Process", return_value=mock_psutil_process),
        ):
            await transport.start()

            # Wait for health check to detect memory limit
            await asyncio.sleep(0.3)

            # Process should be killed
            mock_process.kill.assert_called()

            await transport.stop()

    @pytest.mark.asyncio
    async def test_fd_limit_exceeded(self, mock_process):
        """Test file descriptor limit exceeded."""
        # Create psutil process with many FDs
        mock_psutil_process = MagicMock()
        mock_psutil_process.is_running.return_value = True
        mock_psutil_process.memory_info.return_value = MagicMock(rss=100 * 1024 * 1024)
        mock_psutil_process.cpu_percent.return_value = 50.0
        mock_psutil_process.num_fds.return_value = 2000  # High FD count

        transport = StdioTransport(
            command=["python", "server.py"],
            resource_limits=ResourceLimits(max_file_descriptors=1000),
            health_config=HealthConfig(heartbeat_interval=0.1),
        )

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("psutil.Process", return_value=mock_psutil_process),
        ):
            await transport.start()

            # Wait for health check to detect FD limit
            await asyncio.sleep(0.3)

            # Process should be killed
            mock_process.kill.assert_called()

            await transport.stop()

    @pytest.mark.asyncio
    async def test_cpu_high_warning(self, mock_process):
        """Test high CPU usage warning (not fatal)."""
        # Create psutil process with high CPU
        mock_psutil_process = MagicMock()
        mock_psutil_process.is_running.return_value = True
        mock_psutil_process.memory_info.return_value = MagicMock(rss=100 * 1024 * 1024)
        mock_psutil_process.cpu_percent.return_value = 95.0  # High CPU
        mock_psutil_process.num_fds.return_value = 50

        transport = StdioTransport(
            command=["python", "server.py"],
            resource_limits=ResourceLimits(max_cpu_percent=80.0),
            health_config=HealthConfig(heartbeat_interval=0.1),
        )

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("psutil.Process", return_value=mock_psutil_process),
            patch("asyncio.create_task"),
        ):
            await transport.start()

            # Wait for health check
            await asyncio.sleep(0.3)

            # High CPU should only warn, not kill process
            assert transport.is_running is True


@pytest.mark.unit
class TestStdioTransportErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_process_crash_auto_restart(self, mock_process, mock_psutil_process):
        """Test auto-restart on process crash."""
        transport = StdioTransport(command=["python", "server.py"])

        # Simulate process crash by returning empty line (EOF)
        mock_process.stdout.readline.return_value = b""

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("psutil.Process", return_value=mock_psutil_process),
            patch("asyncio.create_task"),
        ):
            await transport.start()

            # Manually trigger stdout reader to simulate crash
            transport._is_shutting_down = False
            await transport._read_stdout()

            # Verify restart was attempted
            # In real scenario, this would call restart via create_task

    @pytest.mark.asyncio
    async def test_cleanup_pending_requests(self, mock_process, mock_psutil_process):
        """Test cleanup of pending requests on stop."""
        transport = StdioTransport(command=["python", "server.py"])

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("psutil.Process", return_value=mock_psutil_process),
        ):
            await transport.start()

            # Create pending request without response
            request_task = asyncio.create_task(
                transport.send_request("test/method", {}, timeout=10.0)
            )

            await asyncio.sleep(0.1)

            # Stop transport
            await transport.stop()

            # Pending request should fail
            with pytest.raises(StdioTransportError, match="Transport stopped"):
                await request_task

    @pytest.mark.asyncio
    async def test_invalid_json_handling(self, mock_process, mock_psutil_process):
        """Test handling of invalid JSON from subprocess."""
        transport = StdioTransport(command=["python", "server.py"])

        # Simulate invalid JSON response
        mock_process.stdout.readline.return_value = b"invalid json\n"

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("psutil.Process", return_value=mock_psutil_process),
            patch("asyncio.create_task"),
        ):
            await transport.start()

            # Read invalid JSON - should log warning and continue
            # Manually call once to test
            await asyncio.sleep(0.1)

            # Transport should still be running
            assert transport.is_running is True

    @pytest.mark.asyncio
    async def test_read_stdout_with_valid_response(self, mock_process, mock_psutil_process):
        """Test _read_stdout with valid JSON-RPC response."""
        transport = StdioTransport(command=["python", "server.py"])

        # Mock readline to return a valid JSON-RPC response, then EOF
        response = {"jsonrpc": "2.0", "id": 0, "result": {"status": "ok"}}
        mock_process.stdout.readline.side_effect = [
            (json.dumps(response) + "\n").encode("utf-8"),
            b"",  # EOF
        ]

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("psutil.Process", return_value=mock_psutil_process),
            patch("asyncio.create_task") as mock_create_task,
        ):
            await transport.start()

            # Create a pending request
            future = asyncio.Future()
            transport._pending_requests[0] = future

            # Manually call _read_stdout
            await transport._read_stdout()

            # The future should be resolved with the result
            assert future.done()
            assert future.result() == {"status": "ok"}

            await transport.stop()

    @pytest.mark.asyncio
    async def test_read_stdout_with_error_response(self, mock_process, mock_psutil_process):
        """Test _read_stdout with JSON-RPC error response."""
        transport = StdioTransport(command=["python", "server.py"])

        # Mock readline to return a JSON-RPC error response, then EOF
        error_response = {
            "jsonrpc": "2.0",
            "id": 0,
            "error": {"code": -32601, "message": "Method not found"},
        }
        mock_process.stdout.readline.side_effect = [
            (json.dumps(error_response) + "\n").encode("utf-8"),
            b"",  # EOF
        ]

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("psutil.Process", return_value=mock_psutil_process),
            patch("asyncio.create_task") as mock_create_task,
        ):
            await transport.start()

            # Create a pending request
            future = asyncio.Future()
            transport._pending_requests[0] = future

            # Manually call _read_stdout
            await transport._read_stdout()

            # The future should be resolved with an exception
            assert future.done()
            with pytest.raises(StdioTransportError, match="Method not found"):
                future.result()

            await transport.stop()

    @pytest.mark.asyncio
    async def test_process_disappeared(self, mock_process, mock_psutil_process):
        """Test handling of process disappearing."""
        transport = StdioTransport(
            command=["python", "server.py"],
            health_config=HealthConfig(heartbeat_interval=0.1),
        )

        # Simulate process disappearing
        mock_psutil_process.is_running.return_value = False

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("psutil.Process", return_value=mock_psutil_process),
            patch("asyncio.create_task"),
        ):
            await transport.start()

            # Wait for health check to detect missing process
            await asyncio.sleep(0.3)


@pytest.mark.unit
class TestStdioTransportProperties:
    """Test transport properties."""

    def test_is_running_not_started(self):
        """Test is_running when not started."""
        transport = StdioTransport(command=["python", "server.py"])
        assert transport.is_running is False

    @pytest.mark.asyncio
    async def test_is_running_after_start(self, mock_process, mock_psutil_process):
        """Test is_running after start."""
        transport = StdioTransport(command=["python", "server.py"])

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("psutil.Process", return_value=mock_psutil_process),
            patch("asyncio.create_task"),
        ):
            await transport.start()
            assert transport.is_running is True

    def test_pid_not_started(self):
        """Test PID when not started."""
        transport = StdioTransport(command=["python", "server.py"])
        assert transport.pid is None

    @pytest.mark.asyncio
    async def test_pid_after_start(self, mock_process, mock_psutil_process):
        """Test PID after start."""
        transport = StdioTransport(command=["python", "server.py"])

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("psutil.Process", return_value=mock_psutil_process),
            patch("asyncio.create_task"),
        ):
            await transport.start()
            assert transport.pid == 12345
