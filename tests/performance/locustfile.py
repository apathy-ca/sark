"""Locust load testing scenarios for SARK API.

This file contains comprehensive load test scenarios for all major SARK endpoints:
- Server registration
- Policy evaluation
- Server search and listing
- API key management
- Health checks
- Bulk operations

Performance Targets:
- API response time (p95): < 100ms
- Server registration (p95): < 200ms
- Policy evaluation (p95): < 50ms
- Database queries: < 20ms

Usage:
    # Run with web UI
    locust -f locustfile.py --host=http://localhost:8000

    # Run headless with specific users/spawn rate
    locust -f locustfile.py --host=http://localhost:8000 --users 100 --spawn-rate 10 --run-time 5m

    # Run specific user class
    locust -f locustfile.py --host=http://localhost:8000 --users 50 ServerRegistrationUser

    # Generate HTML report
    locust -f locustfile.py --host=http://localhost:8000 --users 100 --spawn-rate 10 --run-time 5m --html=reports/load_test_report.html
"""

import random
import time
from typing import ClassVar
import uuid

from locust import TaskSet, between, task
from locust.contrib.fasthttp import FastHttpUser
from utils.test_data import TestDataGenerator

# Test data generator
generator = TestDataGenerator()

# Simulated user credentials (would come from setup)
# In real test, these would be created via setup script
TEST_API_KEY = "sk_test_1234567890abcdefghijklmnop"  # Mock API key
TEST_JWT_TOKEN = None  # Will be set during on_start


class ServerManagementTasks(TaskSet):
    """Task set for server management operations."""

    def on_start(self):
        """Set up authentication token."""
        self.api_key = TEST_API_KEY
        self.headers = {"X-API-Key": self.api_key}
        self.registered_servers = []

    @task(5)
    def register_server(self):
        """Register a new MCP server (weighted 5x - high priority test)."""
        server_data = generator.generate_server_registration()

        with self.client.post(
            "/api/v1/servers/",
            json=server_data,
            headers=self.headers,
            catch_response=True,
            name="/api/v1/servers/ [POST - Register]",
        ) as response:
            if response.status_code == 201:
                data = response.json()
                self.registered_servers.append(data["server_id"])
                response.success()
            elif response.status_code == 403:
                # Expected if policy denies - not a failure
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(10)
    def list_servers(self):
        """List all servers (weighted 10x - common operation)."""
        with self.client.get(
            "/api/v1/servers/",
            headers=self.headers,
            catch_response=True,
            name="/api/v1/servers/ [GET - List]",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"List servers failed: {response.status_code}")

    @task(8)
    def get_server_details(self):
        """Get details for a specific server."""
        if self.registered_servers:
            server_id = random.choice(self.registered_servers)
        else:
            # Use a random UUID if no servers registered yet
            server_id = str(uuid.uuid4())

        with self.client.get(
            f"/api/v1/servers/{server_id}",
            headers=self.headers,
            catch_response=True,
            name="/api/v1/servers/{id} [GET]",
        ) as response:
            if response.status_code in (200, 404):
                # 404 is acceptable if server doesn't exist
                response.success()
            else:
                response.failure(f"Get server failed: {response.status_code}")

    @task(3)
    def search_servers(self):
        """Search servers with query parameters."""
        query_params = generator.generate_search_query()

        # Remove empty values
        query_params = {k: v for k, v in query_params.items() if v}

        with self.client.get(
            "/api/v1/servers/",
            params=query_params,
            headers=self.headers,
            catch_response=True,
            name="/api/v1/servers/ [GET - Search]",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Search failed: {response.status_code}")


class PolicyEvaluationTasks(TaskSet):
    """Task set for policy evaluation operations."""

    def on_start(self):
        """Set up authentication."""
        self.api_key = TEST_API_KEY
        self.headers = {"X-API-Key": self.api_key}

    @task(15)
    def evaluate_tool_invocation_policy(self):
        """Evaluate policy for tool invocation (most common, weighted 15x)."""
        policy_request = generator.generate_policy_evaluation()

        with self.client.post(
            "/api/v1/policy/evaluate",
            json=policy_request,
            headers=self.headers,
            catch_response=True,
            name="/api/v1/policy/evaluate [Tool Invoke]",
        ) as response:
            if response.status_code == 200:
                data = response.json()
                # Check response contains expected fields
                if "decision" in data and data["decision"] in ("allow", "deny"):
                    response.success()
                else:
                    response.failure("Invalid policy response format")
            else:
                response.failure(f"Policy evaluation failed: {response.status_code}")

    @task(5)
    def evaluate_server_action_policy(self):
        """Evaluate policy for server actions."""
        actions = ["server:read", "server:update", "server:delete"]
        policy_request = {
            "action": random.choice(actions),
            "server_id": str(uuid.uuid4()),
            "parameters": {},
        }

        with self.client.post(
            "/api/v1/policy/evaluate",
            json=policy_request,
            headers=self.headers,
            catch_response=True,
            name="/api/v1/policy/evaluate [Server Action]",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Policy evaluation failed: {response.status_code}")


class HealthCheckTasks(TaskSet):
    """Task set for health check endpoints."""

    @task(1)
    def health_check(self):
        """Basic health check."""
        with self.client.get("/health/", catch_response=True, name="/health/ [GET]") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

    @task(1)
    def ready_check(self):
        """Readiness check."""
        with self.client.get(
            "/health/ready", catch_response=True, name="/health/ready [GET]"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Ready check failed: {response.status_code}")

    @task(1)
    def detailed_health(self):
        """Detailed health check with component status."""
        with self.client.get(
            "/health/detailed", catch_response=True, name="/health/detailed [GET]"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Detailed health failed: {response.status_code}")


class MixedWorkloadUser(FastHttpUser):
    """
    Simulates a realistic mixed workload user.

    This user performs a combination of server management and policy evaluation tasks,
    simulating real-world usage patterns.
    """

    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    tasks: ClassVar = {
        ServerManagementTasks: 3,  # 30% server management
        PolicyEvaluationTasks: 6,  # 60% policy evaluation (most common)
        HealthCheckTasks: 1,  # 10% health checks
    }


class ServerRegistrationUser(FastHttpUser):
    """
    Dedicated user for server registration load testing.

    Use this for focused server registration performance tests.
    Target: 1000 req/s server registration
    Expected p95: < 200ms
    """

    wait_time = between(0.5, 2)
    tasks: ClassVar = [ServerManagementTasks]


class PolicyEvaluationUser(FastHttpUser):
    """
    Dedicated user for policy evaluation load testing.

    Use this for focused policy evaluation performance tests.
    Expected p95: < 50ms
    """

    wait_time = between(0.1, 0.5)  # Fast policy evaluation
    tasks: ClassVar = [PolicyEvaluationTasks]


class BurstTrafficUser(FastHttpUser):
    """
    Simulates burst traffic patterns.

    This user creates bursty traffic with periods of high activity
    followed by idle periods, simulating real-world traffic spikes.
    """

    wait_time = between(0, 1)

    def on_start(self):
        """Initialize user."""
        self.api_key = TEST_API_KEY
        self.headers = {"X-API-Key": self.api_key}
        self.burst_count = 0

    @task
    def burst_requests(self):
        """Generate burst of requests."""
        # Send 5-10 rapid requests
        burst_size = random.randint(5, 10)

        for _ in range(burst_size):
            # Mix of different request types
            request_type = random.choice(["server_list", "policy_eval", "health"])

            if request_type == "server_list":
                self.client.get(
                    "/api/v1/servers/", headers=self.headers, name="/api/v1/servers/ [Burst]"
                )
            elif request_type == "policy_eval":
                policy_request = generator.generate_policy_evaluation()
                self.client.post(
                    "/api/v1/policy/evaluate",
                    json=policy_request,
                    headers=self.headers,
                    name="/api/v1/policy/evaluate [Burst]",
                )
            else:
                self.client.get("/health/", name="/health/ [Burst]")

        # Wait longer after burst
        time.sleep(random.uniform(3, 7))


class ConcurrentOperationsUser(FastHttpUser):
    """
    Tests concurrent operations and race conditions.

    This user performs rapid concurrent operations to stress test
    database transactions, locks, and concurrent session handling.
    """

    wait_time = between(0.1, 0.3)

    def on_start(self):
        """Initialize user."""
        self.api_key = TEST_API_KEY
        self.headers = {"X-API-Key": self.api_key}

    @task(10)
    def concurrent_policy_evaluations(self):
        """Rapidly evaluate multiple policies."""
        for _ in range(random.randint(3, 7)):
            policy_request = generator.generate_policy_evaluation()
            self.client.post(
                "/api/v1/policy/evaluate",
                json=policy_request,
                headers=self.headers,
                name="/api/v1/policy/evaluate [Concurrent]",
            )

    @task(5)
    def concurrent_server_reads(self):
        """Read multiple servers concurrently."""
        for _ in range(random.randint(2, 5)):
            server_id = str(uuid.uuid4())
            self.client.get(
                f"/api/v1/servers/{server_id}",
                headers=self.headers,
                name="/api/v1/servers/{id} [Concurrent]",
            )


# ============================================================================
# Scenario-specific user classes for targeted load testing
# ============================================================================


class RateLimitTestUser(FastHttpUser):
    """
    Tests rate limiting behavior.

    This user attempts to exceed rate limits to verify that
    rate limiting is working correctly and returns appropriate 429 responses.
    """

    wait_time = between(0, 0.1)  # Very fast to trigger rate limits

    def on_start(self):
        """Initialize user."""
        self.api_key = TEST_API_KEY
        self.headers = {"X-API-Key": self.api_key}

    @task
    def rapid_requests(self):
        """Send rapid requests to trigger rate limit."""
        with self.client.get(
            "/api/v1/servers/",
            headers=self.headers,
            catch_response=True,
            name="/api/v1/servers/ [Rate Limit Test]",
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                # Rate limit hit - expected behavior
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


class DatabaseStressUser(FastHttpUser):
    """
    Stresses database with complex queries.

    This user performs operations that are database-intensive
    to test database connection pooling, query performance, and transaction handling.
    Target: Database queries < 20ms
    """

    wait_time = between(0.5, 1.5)

    def on_start(self):
        """Initialize user."""
        self.api_key = TEST_API_KEY
        self.headers = {"X-API-Key": self.api_key}

    @task(5)
    def list_with_filters(self):
        """List servers with multiple filters."""
        params = {
            "status": random.choice(["active", "inactive"]),
            "sensitivity_level": random.choice(["low", "medium", "high", "critical"]),
            "limit": "50",
        }
        self.client.get(
            "/api/v1/servers/",
            params=params,
            headers=self.headers,
            name="/api/v1/servers/ [Filtered]",
        )

    @task(3)
    def server_registration_with_many_tools(self):
        """Register server with many tools to stress database writes."""
        server_data = generator.generate_server_registration()
        # Add many tools to increase database write complexity
        server_data["tools"] = [generator.generate_tool() for _ in range(20)]

        with self.client.post(
            "/api/v1/servers/",
            json=server_data,
            headers=self.headers,
            catch_response=True,
            name="/api/v1/servers/ [Complex Registration]",
        ) as response:
            if response.status_code in (201, 403):
                response.success()
            else:
                response.failure(f"Complex registration failed: {response.status_code}")
