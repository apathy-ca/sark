"""
Locust load testing for SARK authorization engine.

Tests authorization performance under sustained load with realistic request patterns.

Performance Targets (v1.4.0):
- Throughput: 2,000+ req/s
- OPA p95 latency: <5ms
- Cache p95 latency: <0.5ms
- Error rate: <1%
- No memory leaks

Usage:
    # Run baseline test (100 req/s)
    locust -f locustfile.py --host=http://localhost:8000 \\
        --users 50 --spawn-rate 5 --run-time 30m

    # Run target test (2,000 req/s)
    locust -f locustfile.py --host=http://localhost:8000 \\
        --users 1000 --spawn-rate 100 --run-time 30m

    # Run stress test (5,000 req/s)
    locust -f locustfile.py --host=http://localhost:8000 \\
        --users 2500 --spawn-rate 250 --run-time 10m

    # With HTML report
    locust -f locustfile.py --host=http://localhost:8000 \\
        --users 1000 --spawn-rate 100 --run-time 30m \\
        --html=reports/auth_load_test.html \\
        --csv=reports/auth_load_test
"""

import random

from locust import HttpUser, between, events, task

# ==============================================================================
# Authorization Load Test User
# ==============================================================================


class SARKUser(HttpUser):
    """
    Simulated user performing authorization requests.

    Generates realistic authorization traffic with weighted distribution:
    - 60% read operations (task weight 3)
    - 30% write operations (task weight 2)
    - 10% admin operations (task weight 1)
    """

    # Wait time between requests (realistic user behavior)
    wait_time = between(0.1, 0.5)  # 100-500ms between requests

    def on_start(self):
        """
        Initialize user session.

        Sets up user ID and request counter for this simulated user.
        """
        self.user_id = f"user-{self.id}"
        self.request_count = 0

    @task(3)
    def authorize_read(self):
        """
        Common read authorization (60% of traffic).

        Tests typical read operation authorization with cache hits on common resources.
        """
        self.request_count += 1

        # Use common resources for cache hit simulation
        resource = random.choice(
            [
                "document-123",
                "document-456",
                "document-789",
                "project-alpha:document-001",
                "project-beta:document-002",
            ]
        )

        with self.client.post(
            "/authorize",
            json={
                "user": self.user_id,
                "action": "read",
                "resource": resource,
                "context": {
                    "role": "viewer",
                    "tenant_id": "tenant-1",
                },
            },
            catch_response=True,
            name="POST /authorize [read]",
        ) as response:
            if response.status_code == 200:
                data = response.json()
                # Validate response structure
                if "allow" in data:
                    response.success()
                else:
                    response.failure("Missing 'allow' field in response")
            elif response.status_code in [403, 401]:
                # Authorization denied is a valid response
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(2)
    def authorize_write(self):
        """
        Write authorization (30% of traffic).

        Tests write operation authorization with varied resources.
        """
        self.request_count += 1

        resource = random.choice(
            [
                "document-123",
                "document-456",
                "project-alpha:document-001",
                f"document-{self.request_count}",  # Unique resource for cache miss
            ]
        )

        with self.client.post(
            "/authorize",
            json={
                "user": self.user_id,
                "action": "write",
                "resource": resource,
                "context": {
                    "role": "editor",
                    "tenant_id": "tenant-1",
                    "project_id": "project-alpha",
                },
            },
            catch_response=True,
            name="POST /authorize [write]",
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "allow" in data:
                    response.success()
                else:
                    response.failure("Missing 'allow' field in response")
            elif response.status_code in [403, 401]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(1)
    def authorize_admin(self):
        """
        Admin authorization (10% of traffic).

        Tests high-privilege operations with complex policies.
        """
        self.request_count += 1

        with self.client.post(
            "/authorize",
            json={
                "user": self.user_id,
                "action": "admin",
                "resource": "system",
                "context": {
                    "role": "admin",
                    "tenant_id": "tenant-1",
                    "ip_address": "192.168.1.100",
                    "mfa_verified": True,
                },
            },
            catch_response=True,
            name="POST /authorize [admin]",
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "allow" in data:
                    response.success()
                else:
                    response.failure("Missing 'allow' field in response")
            elif response.status_code in [403, 401]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


# ==============================================================================
# Read-Heavy User (Cache Hit Testing)
# ==============================================================================


class ReadHeavyUser(HttpUser):
    """
    User with mostly read operations.

    Used to test cache performance with high cache hit rate.
    """

    wait_time = between(0.05, 0.2)  # Faster requests

    def on_start(self):
        self.user_id = f"reader-{self.id}"

    @task(10)
    def authorize_read(self):
        """Read from a small set of common resources (high cache hit rate)."""
        # Only 10 resources for high cache hit rate
        resource = f"document-{random.randint(1, 10)}"

        with self.client.post(
            "/authorize",
            json={
                "user": self.user_id,
                "action": "read",
                "resource": resource,
                "context": {"role": "viewer"},
            },
            catch_response=True,
            name="POST /authorize [cache-hit]",
        ) as response:
            if response.status_code in [200, 403, 401]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


# ==============================================================================
# Cache Miss User (Cold Cache Testing)
# ==============================================================================


class CacheMissUser(HttpUser):
    """
    User generating mostly cache misses.

    Used to test OPA engine performance without cache.
    """

    wait_time = between(0.2, 0.5)

    def on_start(self):
        self.user_id = f"unique-user-{self.id}"
        self.counter = 0

    @task
    def authorize_unique(self):
        """Always use unique resources to force cache miss."""
        self.counter += 1
        resource = f"document-unique-{self.id}-{self.counter}"

        with self.client.post(
            "/authorize",
            json={
                "user": self.user_id,
                "action": "read",
                "resource": resource,
                "context": {"role": "viewer"},
            },
            catch_response=True,
            name="POST /authorize [cache-miss]",
        ) as response:
            if response.status_code in [200, 403, 401]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


# ==============================================================================
# Complex Policy User
# ==============================================================================


class ComplexPolicyUser(HttpUser):
    """
    User testing complex multi-tenant policies.

    Tests OPA performance with nested resources and multiple context attributes.
    """

    wait_time = between(0.3, 0.8)

    def on_start(self):
        self.user_id = f"complex-user-{self.id}"

    @task
    def authorize_complex(self):
        """Test with complex multi-tenant policy."""
        tenant = random.choice(["tenant-1", "tenant-2", "tenant-3"])
        project = random.choice(["project-alpha", "project-beta", "project-gamma"])
        document = random.randint(1, 1000)

        with self.client.post(
            "/authorize",
            json={
                "user": self.user_id,
                "action": "write",
                "resource": f"{tenant}:{project}:document-{document}",
                "context": {
                    "role": "admin",
                    "tenant_id": tenant,
                    "project_id": project,
                    "ip_address": f"192.168.1.{random.randint(1, 255)}",
                    "time_of_day": "business_hours",
                    "sensitivity": "confidential",
                    "department": "engineering",
                    "clearance_level": random.randint(1, 5),
                },
            },
            catch_response=True,
            name="POST /authorize [complex]",
        ) as response:
            if response.status_code in [200, 403, 401]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


# ==============================================================================
# Event Handlers for Metrics Collection
# ==============================================================================


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Log test start."""
    print("=" * 80)
    print("SARK Authorization Load Test Starting")
    print("=" * 80)
    print(f"Target host: {environment.host}")
    print(f"User classes: {[user.__name__ for user in environment.user_classes]}")
    print("=" * 80)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Log test completion and summary."""
    print("=" * 80)
    print("SARK Authorization Load Test Complete")
    print("=" * 80)

    stats = environment.stats
    total_rps = stats.total.total_rps
    total_requests = stats.total.num_requests
    total_failures = stats.total.num_failures
    error_rate = (total_failures / total_requests * 100) if total_requests > 0 else 0

    print(f"Total Requests: {total_requests:,}")
    print(f"Total Failures: {total_failures:,}")
    print(f"Error Rate: {error_rate:.2f}%")
    print(f"Requests/sec: {total_rps:.2f}")

    if stats.total.avg_response_time:
        print(f"Avg Response Time: {stats.total.avg_response_time:.2f}ms")

    # Performance validation
    print("\nPerformance Target Validation:")
    print(f"  Throughput target: 2,000 req/s -> {'✓ PASS' if total_rps >= 2000 else '✗ FAIL'}")
    print(f"  Error rate target: <1% -> {'✓ PASS' if error_rate < 1.0 else '✗ FAIL'}")

    print("=" * 80)
