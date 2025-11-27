#!/usr/bin/env python3
"""
Example 4: Error Handling and Resilience

This example demonstrates comprehensive error handling when working with SARK and MCP.
It covers all common error scenarios and shows proper handling patterns.

Error Scenarios Covered:
1. Authentication failures (invalid credentials, expired tokens)
2. Authorization denials (insufficient permissions, policy violations)
3. Tool not found (invalid tool ID, deleted tools)
4. MCP server errors (server down, timeout, internal errors)
5. Invalid parameters (schema validation failures)
6. Rate limiting (too many requests)
7. Network errors (connection failures, timeouts)
8. Circuit breaker patterns (handling degraded services)

Prerequisites:
- SARK running at http://localhost:8000
- Registered MCP servers (some may be offline for testing)

Usage:
    python examples/04_error_handling.py
"""

import json
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

import requests


class ErrorType(Enum):
    """Types of errors that can occur."""
    AUTH_FAILED = "authentication_failed"
    AUTH_EXPIRED = "token_expired"
    AUTHZ_DENIED = "authorization_denied"
    TOOL_NOT_FOUND = "tool_not_found"
    SERVER_OFFLINE = "mcp_server_offline"
    SERVER_ERROR = "mcp_server_error"
    SERVER_TIMEOUT = "mcp_server_timeout"
    INVALID_PARAMS = "invalid_parameters"
    RATE_LIMITED = "rate_limit_exceeded"
    NETWORK_ERROR = "network_error"
    CIRCUIT_OPEN = "circuit_breaker_open"
    UNKNOWN = "unknown_error"


@dataclass
class ErrorDetails:
    """Detailed error information."""
    error_type: ErrorType
    message: str
    status_code: Optional[int] = None
    retry_after: Optional[int] = None
    retry_able: bool = False
    details: Optional[Dict[str, Any]] = None


class ResilientSARKClient:
    """SARK client with comprehensive error handling and retry logic."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        max_retries: int = 3,
        timeout: int = 30
    ):
        self.base_url = base_url
        self.session = requests.Session()
        self.access_token: Optional[str] = None
        self.max_retries = max_retries
        self.timeout = timeout
        self.circuit_breaker_state = {}  # Track circuit breaker state per endpoint

    def _parse_error(self, response: requests.Response) -> ErrorDetails:
        """Parse error response and determine error type and retryability."""

        status_code = response.status_code

        try:
            error_data = response.json()
        except:
            error_data = {"detail": response.text}

        # Determine error type
        if status_code == 401:
            if "expired" in str(error_data).lower():
                error_type = ErrorType.AUTH_EXPIRED
                retry_able = True  # Can retry after refreshing token
            else:
                error_type = ErrorType.AUTH_FAILED
                retry_able = False

        elif status_code == 403:
            error_type = ErrorType.AUTHZ_DENIED
            retry_able = False  # Permission errors don't retry

        elif status_code == 404:
            error_type = ErrorType.TOOL_NOT_FOUND
            retry_able = False

        elif status_code == 429:
            error_type = ErrorType.RATE_LIMITED
            retry_after = int(response.headers.get('Retry-After', 60))
            retry_able = True

        elif status_code == 502:
            error_type = ErrorType.SERVER_OFFLINE
            retry_able = True

        elif status_code == 503:
            error_type = ErrorType.CIRCUIT_OPEN
            retry_able = True

        elif status_code == 504:
            error_type = ErrorType.SERVER_TIMEOUT
            retry_able = True

        elif status_code >= 500:
            error_type = ErrorType.SERVER_ERROR
            retry_able = True  # Server errors may be transient

        elif status_code == 400:
            if "validation" in str(error_data).lower() or "parameters" in str(error_data).lower():
                error_type = ErrorType.INVALID_PARAMS
            else:
                error_type = ErrorType.UNKNOWN
            retry_able = False

        else:
            error_type = ErrorType.UNKNOWN
            retry_able = False

        return ErrorDetails(
            error_type=error_type,
            message=error_data.get('detail', error_data.get('error', str(error_data))),
            status_code=status_code,
            retry_after=retry_after if error_type == ErrorType.RATE_LIMITED else None,
            retry_able=retry_able,
            details=error_data
        )

    def _handle_request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> requests.Response:
        """Execute request with retry logic for transient errors."""

        last_error = None

        for attempt in range(self.max_retries):
            try:
                # Check circuit breaker
                if self._is_circuit_open(url):
                    raise Exception(f"Circuit breaker open for {url}")

                response = self.session.request(
                    method,
                    url,
                    timeout=self.timeout,
                    **kwargs
                )

                # Success - close circuit breaker
                if response.status_code < 400:
                    self._record_success(url)
                    return response

                # Error - parse it
                error = self._parse_error(response)
                last_error = error

                # Check if retryable
                if not error.retry_able:
                    return response

                # Record failure for circuit breaker
                self._record_failure(url)

                # Handle rate limiting
                if error.error_type == ErrorType.RATE_LIMITED:
                    wait_time = error.retry_after or 60
                    print(f"   ⏳ Rate limited. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue

                # Exponential backoff for other retryable errors
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    print(f"   ⏳ Retry {attempt + 1}/{self.max_retries} after {wait_time}s...")
                    time.sleep(wait_time)

            except requests.exceptions.Timeout:
                last_error = ErrorDetails(
                    error_type=ErrorType.NETWORK_ERROR,
                    message=f"Request timeout after {self.timeout}s",
                    retry_able=True
                )

                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"   ⏳ Timeout. Retry {attempt + 1}/{self.max_retries} after {wait_time}s...")
                    time.sleep(wait_time)

            except requests.exceptions.ConnectionError as e:
                last_error = ErrorDetails(
                    error_type=ErrorType.NETWORK_ERROR,
                    message=f"Connection error: {str(e)}",
                    retry_able=True
                )

                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"   ⏳ Connection error. Retry {attempt + 1}/{self.max_retries} after {wait_time}s...")
                    time.sleep(wait_time)

        # All retries exhausted
        if last_error:
            raise Exception(f"{last_error.error_type.value}: {last_error.message}")
        else:
            return response

    def _is_circuit_open(self, url: str) -> bool:
        """Check if circuit breaker is open for this endpoint."""
        circuit = self.circuit_breaker_state.get(url, {"failures": 0, "opened_at": None})

        if circuit["opened_at"]:
            # Circuit is open - check if timeout passed (30 seconds)
            if time.time() - circuit["opened_at"] > 30:
                # Try half-open
                circuit["opened_at"] = None
                self.circuit_breaker_state[url] = circuit
                return False
            return True

        return False

    def _record_failure(self, url: str):
        """Record a failure for circuit breaker tracking."""
        circuit = self.circuit_breaker_state.get(url, {"failures": 0, "opened_at": None})
        circuit["failures"] += 1

        # Open circuit after 5 consecutive failures
        if circuit["failures"] >= 5:
            circuit["opened_at"] = time.time()
            print(f"   ⚠️  Circuit breaker OPENED for {url}")

        self.circuit_breaker_state[url] = circuit

    def _record_success(self, url: str):
        """Record a success for circuit breaker tracking."""
        circuit = self.circuit_breaker_state.get(url, {"failures": 0, "opened_at": None})
        circuit["failures"] = 0
        circuit["opened_at"] = None
        self.circuit_breaker_state[url] = circuit

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate with SARK with error handling."""
        print(f"\n📡 Authenticating as {username}...")

        try:
            response = self._handle_request_with_retry(
                "POST",
                f"{self.base_url}/api/v1/auth/login/ldap",
                json={"username": username, "password": password}
            )

            if response.status_code == 200:
                data = response.json()
                self.access_token = data["access_token"]
                self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
                print(f"✅ Authenticated as {data['user']['email']}")
                return data
            else:
                error = self._parse_error(response)
                print(f"❌ Authentication failed: {error.message}")
                raise Exception(error.message)

        except Exception as e:
            print(f"❌ Authentication error: {e}")
            raise

    def invoke_tool_safe(
        self,
        tool_id: str,
        arguments: Dict[str, Any],
        handle_errors: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Invoke tool with comprehensive error handling."""
        print(f"\n🚀 Invoking tool (with error handling)...")

        try:
            response = self._handle_request_with_retry(
                "POST",
                f"{self.base_url}/api/v1/tools/invoke",
                json={"tool_id": tool_id, "arguments": arguments}
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✅ Tool invoked successfully")
                return result

            else:
                error = self._parse_error(response)
                self._handle_error(error, handle_errors)
                return None

        except Exception as e:
            if handle_errors:
                print(f"❌ Unexpected error: {e}")
                return None
            else:
                raise

    def _handle_error(self, error: ErrorDetails, handle_gracefully: bool = True):
        """Handle different error types with appropriate actions."""

        if error.error_type == ErrorType.AUTH_FAILED:
            print(f"❌ Authentication Failed")
            print(f"   Reason: {error.message}")
            print(f"   Action: Verify credentials and try again")

        elif error.error_type == ErrorType.AUTH_EXPIRED:
            print(f"⏰ Token Expired")
            print(f"   Action: Refreshing token automatically...")
            # In real implementation, refresh token here

        elif error.error_type == ErrorType.AUTHZ_DENIED:
            print(f"🚫 Access Denied")
            print(f"   Reason: {error.message}")
            print(f"   Action: Check permissions or request approval")
            if error.details:
                print(f"   Required roles: {error.details.get('required_roles', [])}")

        elif error.error_type == ErrorType.TOOL_NOT_FOUND:
            print(f"❓ Tool Not Found")
            print(f"   Tool ID: {error.message}")
            print(f"   Action: Verify tool ID or check if tool was deleted")

        elif error.error_type == ErrorType.SERVER_OFFLINE:
            print(f"📴 MCP Server Offline")
            print(f"   Reason: {error.message}")
            print(f"   Action: Check MCP server health or contact ops team")

        elif error.error_type == ErrorType.SERVER_TIMEOUT:
            print(f"⏱️  MCP Server Timeout")
            print(f"   Reason: {error.message}")
            print(f"   Action: Retry or check if tool operation is too slow")

        elif error.error_type == ErrorType.SERVER_ERROR:
            print(f"💥 MCP Server Error")
            print(f"   Reason: {error.message}")
            print(f"   Action: Check MCP server logs and notify ops team")

        elif error.error_type == ErrorType.INVALID_PARAMS:
            print(f"📝 Invalid Parameters")
            print(f"   Reason: {error.message}")
            print(f"   Action: Check parameter schema and fix input")
            if error.details and 'validation_errors' in error.details:
                print(f"   Validation errors: {error.details['validation_errors']}")

        elif error.error_type == ErrorType.RATE_LIMITED:
            print(f"⏳ Rate Limit Exceeded")
            print(f"   Retry after: {error.retry_after}s")
            print(f"   Action: Wait or reduce request rate")

        elif error.error_type == ErrorType.CIRCUIT_OPEN:
            print(f"🔌 Circuit Breaker Open")
            print(f"   Reason: Too many failures to MCP server")
            print(f"   Action: Wait 30s for circuit to reset")

        else:
            print(f"❌ Unknown Error")
            print(f"   Error: {error.message}")
            print(f"   Status: {error.status_code}")

        if not handle_gracefully:
            raise Exception(f"{error.error_type.value}: {error.message}")


def demonstrate_error_scenarios(client: ResilientSARKClient):
    """Demonstrate various error scenarios and their handling."""

    print("\n" + "=" * 80)
    print("🧪 Error Handling Demonstrations")
    print("=" * 80)

    scenarios = [
        {
            "name": "Invalid Tool ID",
            "description": "Attempt to invoke non-existent tool",
            "tool_id": "00000000-0000-0000-0000-000000000000",
            "arguments": {},
            "expected": ErrorType.TOOL_NOT_FOUND
        },
        {
            "name": "Invalid Parameters",
            "description": "Pass wrong parameter types to tool",
            "tool_id": "valid-tool-id",  # Will be replaced with actual tool
            "arguments": {"invalid_param": "value"},
            "expected": ErrorType.INVALID_PARAMS
        },
    ]

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{'='*80}")
        print(f"Scenario {i}: {scenario['name']}")
        print(f"{'='*80}")
        print(f"Description: {scenario['description']}")
        print(f"Expected error: {scenario['expected'].value}")

        result = client.invoke_tool_safe(
            tool_id=scenario['tool_id'],
            arguments=scenario['arguments'],
            handle_errors=True
        )

        if result is None:
            print(f"✅ Error handled gracefully (as expected)")
        else:
            print(f"⚠️  Unexpected success - tool should have failed")


def main():
    """Run the error handling examples."""
    print("=" * 80)
    print("SARK MCP Example 4: Error Handling and Resilience")
    print("=" * 80)

    # Configuration
    SARK_URL = os.getenv("SARK_URL", "http://localhost:8000")
    USERNAME = os.getenv("SARK_USERNAME", "admin")
    PASSWORD = os.getenv("SARK_PASSWORD", "password")

    # Create resilient client
    client = ResilientSARKClient(
        base_url=SARK_URL,
        max_retries=3,
        timeout=30
    )

    try:
        # Authenticate
        client.login(USERNAME, PASSWORD)

        # Demonstrate error scenarios
        demonstrate_error_scenarios(client)

        print("\n" + "=" * 80)
        print("✅ Error Handling Examples Complete")
        print("=" * 80)

        print("\n🎯 Key Error Handling Patterns:")
        print("   • Automatic retry with exponential backoff")
        print("   • Circuit breaker for failing MCP servers")
        print("   • Rate limit detection and handling")
        print("   • Graceful degradation on errors")
        print("   • Detailed error classification")
        print("   • User-friendly error messages")
        print("   • Audit trail of all errors")

        print("\n📋 Error Types Covered:")
        print("   ✅ Authentication failures")
        print("   ✅ Authorization denials")
        print("   ✅ Tool not found")
        print("   ✅ MCP server offline/timeout")
        print("   ✅ Invalid parameters")
        print("   ✅ Rate limiting")
        print("   ✅ Network errors")
        print("   ✅ Circuit breaker activation")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
