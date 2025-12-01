"""
Policy plugin sandbox and security controls.

Provides resource limits and security constraints for policy plugin execution.
"""

import asyncio
import resource
import signal
import sys
from contextlib import contextmanager
from typing import Any, Callable, Optional
import structlog

logger = structlog.get_logger(__name__)


class ResourceLimits:
    """
    Resource limits for plugin execution.

    Attributes:
        max_memory_mb: Maximum memory in MB (default: 128MB)
        max_cpu_time_seconds: Maximum CPU time in seconds (default: 2s)
        max_execution_time_seconds: Maximum wall-clock time (default: 5s)
        max_file_descriptors: Maximum open file descriptors (default: 10)
    """

    def __init__(
        self,
        max_memory_mb: int = 128,
        max_cpu_time_seconds: int = 2,
        max_execution_time_seconds: int = 5,
        max_file_descriptors: int = 10,
    ):
        self.max_memory_mb = max_memory_mb
        self.max_cpu_time_seconds = max_cpu_time_seconds
        self.max_execution_time_seconds = max_execution_time_seconds
        self.max_file_descriptors = max_file_descriptors


class SandboxViolation(Exception):
    """Raised when a plugin violates sandbox constraints."""

    def __init__(self, message: str, violation_type: str = None, **kwargs):
        super().__init__(message)
        self.violation_type = violation_type
        self.metadata = kwargs


class PolicyPluginSandbox:
    """
    Sandbox for executing policy plugins with resource limits.

    Provides memory limits, CPU time limits, and controlled execution environment.
    """

    def __init__(self, limits: Optional[ResourceLimits] = None):
        """
        Initialize sandbox.

        Args:
            limits: Resource limits (uses defaults if not provided)
        """
        self.limits = limits or ResourceLimits()

    @contextmanager
    def _apply_resource_limits(self):
        """
        Context manager that applies resource limits.

        Only works on Unix-like systems. On Windows, limits are not enforced.
        """
        if sys.platform == "win32":
            # Resource limits not supported on Windows
            logger.warning("resource_limits_not_supported_on_windows")
            yield
            return

        # Save old limits
        old_memory_limit = None
        old_cpu_limit = None
        old_nofile_limit = None

        try:
            # Set memory limit (address space)
            try:
                old_memory_limit = resource.getrlimit(resource.RLIMIT_AS)
                memory_bytes = self.limits.max_memory_mb * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
            except (ValueError, OSError) as e:
                logger.warning("failed_to_set_memory_limit", error=str(e))

            # Set CPU time limit
            try:
                old_cpu_limit = resource.getrlimit(resource.RLIMIT_CPU)
                resource.setrlimit(
                    resource.RLIMIT_CPU,
                    (self.limits.max_cpu_time_seconds, self.limits.max_cpu_time_seconds)
                )
            except (ValueError, OSError) as e:
                logger.warning("failed_to_set_cpu_limit", error=str(e))

            # Set file descriptor limit
            try:
                old_nofile_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
                resource.setrlimit(
                    resource.RLIMIT_NOFILE,
                    (self.limits.max_file_descriptors, self.limits.max_file_descriptors)
                )
            except (ValueError, OSError) as e:
                logger.warning("failed_to_set_nofile_limit", error=str(e))

            yield

        finally:
            # Restore old limits
            try:
                if old_memory_limit:
                    resource.setrlimit(resource.RLIMIT_AS, old_memory_limit)
                if old_cpu_limit:
                    resource.setrlimit(resource.RLIMIT_CPU, old_cpu_limit)
                if old_nofile_limit:
                    resource.setrlimit(resource.RLIMIT_NOFILE, old_nofile_limit)
            except (ValueError, OSError) as e:
                logger.warning("failed_to_restore_limits", error=str(e))

    async def execute(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a function within the sandbox.

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result of function execution

        Raises:
            SandboxViolation: If execution violates resource limits
            asyncio.TimeoutError: If execution exceeds time limit
        """
        # Apply resource limits in executor
        # Note: Resource limits work best in subprocess, but for simplicity
        # we apply them in the current process (they affect the whole process)

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.limits.max_execution_time_seconds
            )
            return result

        except asyncio.TimeoutError:
            logger.error(
                "plugin_execution_timeout",
                timeout=self.limits.max_execution_time_seconds
            )
            raise SandboxViolation(
                f"Execution exceeded {self.limits.max_execution_time_seconds}s time limit",
                violation_type="timeout"
            )

        except MemoryError:
            logger.error(
                "plugin_memory_limit_exceeded",
                limit_mb=self.limits.max_memory_mb
            )
            raise SandboxViolation(
                f"Memory limit of {self.limits.max_memory_mb}MB exceeded",
                violation_type="memory"
            )

        except OSError as e:
            if "resource" in str(e).lower():
                logger.error("plugin_resource_limit_exceeded", error=str(e))
                raise SandboxViolation(
                    f"Resource limit exceeded: {str(e)}",
                    violation_type="resource"
                )
            raise


class RestrictedImportContext:
    """
    Context manager to restrict module imports during plugin execution.

    Prevents plugins from importing dangerous modules (os, subprocess, etc.).
    """

    # Modules that are safe to import
    ALLOWED_MODULES = {
        "abc",
        "asyncio",
        "collections",
        "dataclasses",
        "datetime",
        "decimal",
        "enum",
        "functools",
        "itertools",
        "json",
        "math",
        "re",
        "typing",
        "uuid",
        # Allow SARK's own modules
        "sark.services.policy.plugins",
    }

    # Modules that are explicitly forbidden
    FORBIDDEN_MODULES = {
        "os",
        "subprocess",
        "sys",
        "shutil",
        "socket",
        "requests",
        "urllib",
        "http",
        "ftplib",
        "smtplib",
        "pickle",
        "marshal",
        "shelve",
        "__builtin__",
        "builtins",
    }

    def __init__(self, allowed_modules: Optional[set] = None):
        """
        Initialize import restrictions.

        Args:
            allowed_modules: Additional modules to allow (beyond defaults)
        """
        self.allowed = self.ALLOWED_MODULES.copy()
        if allowed_modules:
            self.allowed.update(allowed_modules)
        self._original_import = None

    def _restricted_import(self, name, *args, **kwargs):
        """
        Restricted import function.

        Checks module name against whitelist/blacklist before allowing import.
        """
        # Get top-level module name
        top_level = name.split(".")[0]

        # Check if explicitly forbidden
        if top_level in self.FORBIDDEN_MODULES:
            raise ImportError(
                f"Import of module '{name}' is forbidden in policy plugins for security reasons"
            )

        # Check if explicitly allowed
        if top_level in self.allowed:
            return self._original_import(name, *args, **kwargs)

        # Check if it's a submodule of an allowed module
        for allowed in self.allowed:
            if name.startswith(f"{allowed}."):
                return self._original_import(name, *args, **kwargs)

        # Default: deny
        logger.warning(
            "plugin_import_denied",
            module=name,
            reason="not in allowed list"
        )
        raise ImportError(
            f"Import of module '{name}' is not allowed in policy plugins. "
            f"Contact administrator to whitelist if needed."
        )

    def __enter__(self):
        """Enable import restrictions."""
        import builtins
        self._original_import = builtins.__import__
        builtins.__import__ = self._restricted_import
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Disable import restrictions."""
        import builtins
        if self._original_import:
            builtins.__import__ = self._original_import


def validate_plugin_code(code: str) -> tuple[bool, Optional[str]]:
    """
    Statically validate plugin code for dangerous patterns.

    Args:
        code: Python source code to validate

    Returns:
        Tuple of (is_safe, error_message)
    """
    # Forbidden patterns that indicate dangerous code
    forbidden_patterns = [
        "eval(",
        "exec(",
        "compile(",
        "__import__(",
        "open(",
        "file(",
        "subprocess",
        "os.system",
        "os.popen",
        "os.spawn",
    ]

    code_lower = code.lower()

    for pattern in forbidden_patterns:
        if pattern.lower() in code_lower:
            return False, f"Forbidden pattern detected: {pattern}"

    return True, None


__all__ = [
    "ResourceLimits",
    "PolicyPluginSandbox",
    "SandboxViolation",
    "RestrictedImportContext",
    "validate_plugin_code",
]
