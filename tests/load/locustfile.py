"""Locust load testing for SARK policy evaluation.

This script simulates realistic load patterns for policy evaluation
including cache hits, cache misses, and various sensitivity levels.

Usage:
    locust -f tests/load/locustfile.py --host=http://localhost:8000

    # Run headless with specific load
    locust -f tests/load/locustfile.py --host=http://localhost:8000 \\
           --users 100 --spawn-rate 10 --run-time 5m --headless

    # Generate HTML report
    locust -f tests/load/locustfile.py --host=http://localhost:8000 \\
           --users 100 --spawn-rate 10 --run-time 5m --headless \\
           --html locust_report.html
"""

import random
import time

from locust import HttpUser, between, events, task


class PolicyEvaluationUser(HttpUser):
    """Simulates a user making policy evaluation requests."""

    wait_time = between(0.1, 0.5)  # 100-500ms between requests

    def on_start(self):
        """Initialize user context."""
        self.user_id = f"user-{random.randint(1, 1000)}"
        self.role = random.choice(["developer", "developer", "developer", "admin", "viewer"])
        self.team_id = f"team-{random.randint(1, 20)}"
        self.request_count = 0

    @task(50)  # 50% of requests - cache hit scenario
    def evaluate_cached_policy(self):
        """Evaluate a frequently-accessed policy (cache hit)."""
        payload = {
            "user": {
                "id": self.user_id,
                "role": self.role,
                "teams": [self.team_id],
            },
            "action": "tool:invoke",
            "tool": {
                "id": f"tool-{random.randint(1, 10)}",  # Limited set for cache hits
                "name": f"common_tool_{random.randint(1, 10)}",
                "sensitivity_level": random.choice(["low", "medium"]),
            },
            "context": {
                "client_ip": "10.0.0.100",
                "timestamp": int(time.time()),
            },
        }

        with self.client.post(
            "/api/v1/policy/evaluate",
            json=payload,
            catch_response=True,
            name="evaluate_policy_cached",
        ) as response:
            if response.status_code == 200:
                result = response.json()
                if result.get("allow") is not None:
                    response.success()
                else:
                    response.failure("Invalid response format")
            else:
                response.failure(f"Status code: {response.status_code}")

        self.request_count += 1

    @task(30)  # 30% of requests - cache miss scenario
    def evaluate_unique_policy(self):
        """Evaluate a unique policy (cache miss)."""
        payload = {
            "user": {
                "id": self.user_id,
                "role": self.role,
                "teams": [self.team_id],
            },
            "action": "tool:invoke",
            "tool": {
                "id": f"tool-{random.randint(1, 10000)}",  # Large set for cache misses
                "name": f"unique_tool_{random.randint(1, 10000)}",
                "sensitivity_level": random.choice(["low", "medium", "high"]),
            },
            "context": {
                "client_ip": "10.0.0.100",
                "timestamp": int(time.time()),
                "request_id": f"req-{self.request_count}",
            },
        }

        with self.client.post(
            "/api/v1/policy/evaluate",
            json=payload,
            catch_response=True,
            name="evaluate_policy_unique",
        ) as response:
            if response.status_code == 200:
                result = response.json()
                if result.get("allow") is not None:
                    response.success()
                else:
                    response.failure("Invalid response format")
            else:
                response.failure(f"Status code: {response.status_code}")

        self.request_count += 1

    @task(15)  # 15% of requests - critical tool evaluation
    def evaluate_critical_tool(self):
        """Evaluate critical tool policy (requires MFA, business hours, VPN)."""
        payload = {
            "user": {
                "id": self.user_id,
                "role": self.role,
                "teams": [self.team_id],
                "mfa_verified": True,
                "mfa_timestamp": int(time.time() * 1_000_000_000) - (5 * 60 * 1_000_000_000),
                "mfa_methods": ["totp"],
            },
            "action": "tool:invoke",
            "tool": {
                "id": f"critical-tool-{random.randint(1, 5)}",
                "name": f"critical_tool_{random.randint(1, 5)}",
                "sensitivity_level": "critical",
            },
            "context": {
                "client_ip": "10.0.0.100",
                "timestamp": int(time.time()),
            },
        }

        with self.client.post(
            "/api/v1/policy/evaluate",
            json=payload,
            catch_response=True,
            name="evaluate_policy_critical",
        ) as response:
            if response.status_code == 200:
                result = response.json()
                if result.get("allow") is not None:
                    response.success()
                else:
                    response.failure("Invalid response format")
            else:
                response.failure(f"Status code: {response.status_code}")

        self.request_count += 1

    @task(5)  # 5% of requests - server registration
    def register_server(self):
        """Register a new server (less frequent operation)."""
        payload = {
            "user": {
                "id": self.user_id,
                "role": self.role,
                "teams": [self.team_id],
            },
            "action": "server:register",
            "server": {
                "name": f"server-{self.user_id}-{self.request_count}",
                "teams": [self.team_id],
            },
            "context": {
                "client_ip": "10.0.0.100",
                "timestamp": int(time.time()),
            },
        }

        with self.client.post(
            "/api/v1/policy/evaluate",
            json=payload,
            catch_response=True,
            name="evaluate_policy_server_register",
        ) as response:
            if response.status_code == 200:
                result = response.json()
                if result.get("allow") is not None:
                    response.success()
                else:
                    response.failure("Invalid response format")
            else:
                response.failure(f"Status code: {response.status_code}")

        self.request_count += 1


class BurstUser(HttpUser):
    """Simulates burst traffic patterns."""

    wait_time = between(0.01, 0.1)  # Very short wait for burst

    def on_start(self):
        """Initialize user context."""
        self.user_id = f"burst-user-{random.randint(1, 100)}"

    @task
    def burst_requests(self):
        """Send rapid-fire requests."""
        payload = {
            "user": {
                "id": self.user_id,
                "role": "developer",
                "teams": ["team-1"],
            },
            "action": "tool:invoke",
            "tool": {
                "id": "burst-tool-1",
                "name": "burst_test_tool",
                "sensitivity_level": "low",
            },
            "context": {
                "client_ip": "10.0.0.100",
            },
        }

        with self.client.post(
            "/api/v1/policy/evaluate",
            json=payload,
            catch_response=True,
            name="evaluate_policy_burst",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")


# ============================================================================
# CUSTOM EVENTS FOR METRICS
# ============================================================================


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Log test start."""
    print("=" * 60)
    print("SARK POLICY EVALUATION LOAD TEST")
    print("=" * 60)
    print(f"Target: {environment.host}")
    print(f"Users: {environment.runner.target_user_count if hasattr(environment.runner, 'target_user_count') else 'N/A'}")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Log test completion and summary."""
    print("\n" + "=" * 60)
    print("LOAD TEST SUMMARY")
    print("=" * 60)

    stats = environment.stats
    total_rps = stats.total.current_rps
    total_failures = stats.total.num_failures
    total_requests = stats.total.num_requests

    print(f"Total Requests: {total_requests}")
    print(f"Total Failures: {total_failures}")
    print(f"Failure Rate: {(total_failures/total_requests*100):.2f}%" if total_requests > 0 else "0%")
    print(f"Current RPS: {total_rps:.2f}")

    print("\nResponse Time Percentiles:")
    print(f"  P50: {stats.total.get_response_time_percentile(0.50):.2f}ms")
    print(f"  P95: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"  P99: {stats.total.get_response_time_percentile(0.99):.2f}ms")
    print(f"  Max: {stats.total.max_response_time:.2f}ms")

    # Check if we met the targets
    p95 = stats.total.get_response_time_percentile(0.95)
    if p95 < 50:
        print(f"\n✅ P95 latency target MET: {p95:.2f}ms < 50ms")
    else:
        print(f"\n❌ P95 latency target MISSED: {p95:.2f}ms >= 50ms")

    print("=" * 60)


# ============================================================================
# LOAD TEST SHAPES
# ============================================================================


from locust import LoadTestShape


class StepLoadShape(LoadTestShape):
    """
    A step load shape that gradually increases load.

    Steps:
    - 10 users for 1 minute
    - 50 users for 2 minutes
    - 100 users for 2 minutes
    - 200 users for 2 minutes
    """

    step_time = 60  # 1 minute per step
    step_load = 10
    spawn_rate = 10
    time_limit = 420  # 7 minutes total

    def tick(self):
        run_time = self.get_run_time()

        if run_time < self.time_limit:
            current_step = run_time // self.step_time
            if current_step == 0:
                user_count = 10
            elif current_step == 1:
                user_count = 50
            elif current_step == 2:
                user_count = 100
            else:
                user_count = 200

            return (user_count, self.spawn_rate)

        return None


class SpikeLoadShape(LoadTestShape):
    """
    A spike load shape that simulates traffic spikes.

    Pattern:
    - Baseline: 20 users
    - Spike 1: 200 users (1 minute)
    - Baseline: 20 users
    - Spike 2: 500 users (1 minute)
    - Baseline: 20 users
    """

    def tick(self):
        run_time = self.get_run_time()

        if run_time < 60:
            return (20, 10)  # Baseline
        elif run_time < 120:
            return (200, 50)  # Spike 1
        elif run_time < 240:
            return (20, 10)  # Baseline
        elif run_time < 300:
            return (500, 100)  # Spike 2
        elif run_time < 420:
            return (20, 10)  # Baseline
        else:
            return None
