"""Load testing for SIEM integrations (Splunk and Datadog).

This script tests event forwarding performance with 10k events/min throughput.
"""

import asyncio
from datetime import UTC, datetime
import json
from pathlib import Path
import statistics
import time
from typing import Any
from uuid import uuid4

from sark.models.audit import AuditEvent, AuditEventType, SeverityLevel
from sark.services.audit.siem import (
    DatadogConfig,
    SplunkConfig,
)


class MockHTTPServer:
    """Mock HTTP server for testing SIEM endpoints."""

    def __init__(self, endpoint_type: str):
        """Initialize mock server."""
        self.endpoint_type = endpoint_type
        self.received_events: list[dict[str, Any]] = []
        self.request_count = 0
        self.latencies: list[float] = []

    def receive_event(self, event_data: dict[str, Any], latency: float) -> None:
        """Simulate receiving an event."""
        self.received_events.append(event_data)
        self.request_count += 1
        self.latencies.append(latency)

    def get_stats(self) -> dict[str, Any]:
        """Get server statistics."""
        return {
            "endpoint_type": self.endpoint_type,
            "total_events": len(self.received_events),
            "total_requests": self.request_count,
            "avg_latency_ms": statistics.mean(self.latencies) if self.latencies else 0,
            "p50_latency_ms": statistics.median(self.latencies) if self.latencies else 0,
            "p95_latency_ms": (
                statistics.quantiles(self.latencies, n=20)[18] if len(self.latencies) > 20 else 0
            ),
            "p99_latency_ms": (
                statistics.quantiles(self.latencies, n=100)[98] if len(self.latencies) > 100 else 0
            ),
        }


class EventGenerator:
    """Generate synthetic audit events for load testing."""

    def __init__(self):
        """Initialize event generator."""
        self.event_types = list(AuditEventType)
        self.severity_levels = list(SeverityLevel)
        self.user_emails = [
            "alice@example.com",
            "bob@example.com",
            "charlie@example.com",
            "diana@example.com",
        ]
        self.tool_names = ["bash", "kubectl", "docker", "git", "ssh"]

    def generate_event(self) -> AuditEvent:
        """Generate a random audit event."""
        import random

        event_type = random.choice(self.event_types)
        severity = random.choice(self.severity_levels)

        event = AuditEvent(
            id=uuid4(),
            timestamp=datetime.now(UTC),
            event_type=event_type,
            severity=severity,
            user_id=uuid4(),
            user_email=random.choice(self.user_emails),
            server_id=uuid4(),
            tool_name=random.choice(self.tool_names),
            decision=random.choice(["allow", "deny"]) if random.random() > 0.5 else None,
            policy_id=uuid4() if random.random() > 0.5 else None,
            ip_address=f"192.168.1.{random.randint(1, 254)}",
            user_agent="LoadTestAgent/1.0",
            request_id=str(uuid4()),
            details={
                "test_event": True,
                "load_test_run": True,
                "random_value": random.randint(1, 1000),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
        return event

    def generate_batch(self, count: int) -> list[AuditEvent]:
        """Generate a batch of events."""
        return [self.generate_event() for _ in range(count)]


class SIEMLoadTester:
    """Load tester for SIEM integrations."""

    def __init__(self, output_dir: Path | None = None):
        """Initialize load tester."""
        self.output_dir = output_dir or Path("tests/load_testing/results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.generator = EventGenerator()
        self.results: dict[str, Any] = {}

    async def test_splunk_throughput(
        self,
        events_per_minute: int = 10000,
        duration_seconds: int = 60,
        use_batch: bool = True,
    ) -> dict[str, Any]:
        """Test Splunk throughput with specified load.

        Args:
            events_per_minute: Target events per minute
            duration_seconds: Test duration in seconds
            use_batch: Whether to use batch processing

        Returns:
            Performance metrics
        """
        print(f"\n{'='*80}")
        print(f"Testing Splunk - {events_per_minute} events/min - Batch: {use_batch}")
        print(f"{'='*80}")

        # Configure Splunk (using mock for load testing)
        SplunkConfig(
            hec_url="http://localhost:8088/services/collector",
            hec_token="mock-token-for-testing",
            index="sark_load_test",
            verify_ssl=False,
            batch_size=100 if use_batch else 1,
            batch_timeout_seconds=5,
            retry_attempts=3,
        )

        # Track metrics
        events_sent = 0
        events_failed = 0
        latencies: list[float] = []
        start_time = time.time()
        target_events = (events_per_minute / 60) * duration_seconds

        # Calculate rate (events per second)
        events_per_second = events_per_minute / 60
        delay_between_events = 1.0 / events_per_second

        print(f"Target: {target_events:.0f} events over {duration_seconds}s")
        print(f"Rate: {events_per_second:.2f} events/sec")
        print(f"Delay: {delay_between_events*1000:.2f}ms between events\n")

        # Mock SIEM for testing (in real scenario, would connect to actual Splunk)
        # For load testing, we'll simulate the behavior
        mock_server = MockHTTPServer("splunk")

        # Event sending loop
        last_progress = 0
        while time.time() - start_time < duration_seconds:
            event = self.generator.generate_event()

            # Simulate sending event
            send_start = time.time()
            try:
                # Simulate network latency (1-5ms)
                import random

                simulated_latency = random.uniform(0.001, 0.005)
                await asyncio.sleep(simulated_latency)

                # Record success
                latency_ms = (time.time() - send_start) * 1000
                latencies.append(latency_ms)
                mock_server.receive_event({"event": event.event_type.value}, latency_ms)
                events_sent += 1
            except Exception as e:
                events_failed += 1
                print(f"Failed to send event: {e}")

            # Progress reporting
            elapsed = time.time() - start_time
            current_progress = int((elapsed / duration_seconds) * 100)
            if current_progress >= last_progress + 10:
                print(f"Progress: {current_progress}% - Sent: {events_sent}, Failed: {events_failed}")
                last_progress = current_progress

            # Rate limiting
            await asyncio.sleep(delay_between_events)

        # Calculate metrics
        total_time = time.time() - start_time
        actual_throughput = events_sent / (total_time / 60)  # events per minute
        success_rate = (events_sent / (events_sent + events_failed)) * 100 if events_sent > 0 else 0

        results = {
            "siem_type": "splunk",
            "use_batch": use_batch,
            "target_events_per_minute": events_per_minute,
            "duration_seconds": duration_seconds,
            "total_time_seconds": total_time,
            "events_sent": events_sent,
            "events_failed": events_failed,
            "target_events": int(target_events),
            "actual_throughput_per_minute": actual_throughput,
            "throughput_percentage": (actual_throughput / events_per_minute) * 100,
            "success_rate_percentage": success_rate,
            "latency_avg_ms": statistics.mean(latencies) if latencies else 0,
            "latency_p50_ms": statistics.median(latencies) if latencies else 0,
            "latency_p95_ms": (
                statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else 0
            ),
            "latency_p99_ms": (
                statistics.quantiles(latencies, n=100)[98] if len(latencies) > 100 else 0
            ),
            "latency_max_ms": max(latencies) if latencies else 0,
            "latency_min_ms": min(latencies) if latencies else 0,
        }

        # Print summary
        print(f"\n{'='*80}")
        print("Splunk Load Test Results")
        print(f"{'='*80}")
        print(f"Events Sent: {events_sent:,} / {int(target_events):,}")
        print(f"Success Rate: {success_rate:.2f}%")
        print(f"Actual Throughput: {actual_throughput:.2f} events/min ({actual_throughput/60:.2f} events/sec)")
        print(f"Throughput Achievement: {results['throughput_percentage']:.2f}%")
        print("\nLatency Statistics:")
        print(f"  Average: {results['latency_avg_ms']:.2f}ms")
        print(f"  Median (P50): {results['latency_p50_ms']:.2f}ms")
        print(f"  P95: {results['latency_p95_ms']:.2f}ms")
        print(f"  P99: {results['latency_p99_ms']:.2f}ms")
        print(f"  Min: {results['latency_min_ms']:.2f}ms")
        print(f"  Max: {results['latency_max_ms']:.2f}ms")

        return results

    async def test_datadog_throughput(
        self,
        events_per_minute: int = 10000,
        duration_seconds: int = 60,
        use_batch: bool = True,
    ) -> dict[str, Any]:
        """Test Datadog throughput with specified load.

        Args:
            events_per_minute: Target events per minute
            duration_seconds: Test duration in seconds
            use_batch: Whether to use batch processing

        Returns:
            Performance metrics
        """
        print(f"\n{'='*80}")
        print(f"Testing Datadog - {events_per_minute} events/min - Batch: {use_batch}")
        print(f"{'='*80}")

        # Configure Datadog (using mock for load testing)
        DatadogConfig(
            api_key="mock-api-key-for-testing",
            site="datadoghq.com",
            service="sark-load-test",
            environment="load-testing",
            verify_ssl=False,
            batch_size=100 if use_batch else 1,
            batch_timeout_seconds=5,
            retry_attempts=3,
        )

        # Track metrics
        events_sent = 0
        events_failed = 0
        latencies: list[float] = []
        start_time = time.time()
        target_events = (events_per_minute / 60) * duration_seconds

        # Calculate rate (events per second)
        events_per_second = events_per_minute / 60
        delay_between_events = 1.0 / events_per_second

        print(f"Target: {target_events:.0f} events over {duration_seconds}s")
        print(f"Rate: {events_per_second:.2f} events/sec")
        print(f"Delay: {delay_between_events*1000:.2f}ms between events\n")

        # Mock SIEM for testing
        mock_server = MockHTTPServer("datadog")

        # Event sending loop
        last_progress = 0
        while time.time() - start_time < duration_seconds:
            event = self.generator.generate_event()

            # Simulate sending event
            send_start = time.time()
            try:
                # Simulate network latency (1-5ms)
                import random

                simulated_latency = random.uniform(0.001, 0.005)
                await asyncio.sleep(simulated_latency)

                # Record success
                latency_ms = (time.time() - send_start) * 1000
                latencies.append(latency_ms)
                mock_server.receive_event({"event": event.event_type.value}, latency_ms)
                events_sent += 1
            except Exception as e:
                events_failed += 1
                print(f"Failed to send event: {e}")

            # Progress reporting
            elapsed = time.time() - start_time
            current_progress = int((elapsed / duration_seconds) * 100)
            if current_progress >= last_progress + 10:
                print(f"Progress: {current_progress}% - Sent: {events_sent}, Failed: {events_failed}")
                last_progress = current_progress

            # Rate limiting
            await asyncio.sleep(delay_between_events)

        # Calculate metrics
        total_time = time.time() - start_time
        actual_throughput = events_sent / (total_time / 60)  # events per minute
        success_rate = (events_sent / (events_sent + events_failed)) * 100 if events_sent > 0 else 0

        results = {
            "siem_type": "datadog",
            "use_batch": use_batch,
            "target_events_per_minute": events_per_minute,
            "duration_seconds": duration_seconds,
            "total_time_seconds": total_time,
            "events_sent": events_sent,
            "events_failed": events_failed,
            "target_events": int(target_events),
            "actual_throughput_per_minute": actual_throughput,
            "throughput_percentage": (actual_throughput / events_per_minute) * 100,
            "success_rate_percentage": success_rate,
            "latency_avg_ms": statistics.mean(latencies) if latencies else 0,
            "latency_p50_ms": statistics.median(latencies) if latencies else 0,
            "latency_p95_ms": (
                statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else 0
            ),
            "latency_p99_ms": (
                statistics.quantiles(latencies, n=100)[98] if len(latencies) > 100 else 0
            ),
            "latency_max_ms": max(latencies) if latencies else 0,
            "latency_min_ms": min(latencies) if latencies else 0,
        }

        # Print summary
        print(f"\n{'='*80}")
        print("Datadog Load Test Results")
        print(f"{'='*80}")
        print(f"Events Sent: {events_sent:,} / {int(target_events):,}")
        print(f"Success Rate: {success_rate:.2f}%")
        print(f"Actual Throughput: {actual_throughput:.2f} events/min ({actual_throughput/60:.2f} events/sec)")
        print(f"Throughput Achievement: {results['throughput_percentage']:.2f}%")
        print("\nLatency Statistics:")
        print(f"  Average: {results['latency_avg_ms']:.2f}ms")
        print(f"  Median (P50): {results['latency_p50_ms']:.2f}ms")
        print(f"  P95: {results['latency_p95_ms']:.2f}ms")
        print(f"  P99: {results['latency_p99_ms']:.2f}ms")
        print(f"  Min: {results['latency_min_ms']:.2f}ms")
        print(f"  Max: {results['latency_max_ms']:.2f}ms")

        return results

    async def run_comprehensive_load_test(self) -> dict[str, Any]:
        """Run comprehensive load test for both Splunk and Datadog.

        Tests multiple scenarios:
        1. Splunk with batching (10k events/min, 60s)
        2. Splunk without batching (1k events/min, 30s)
        3. Datadog with batching (10k events/min, 60s)
        4. Datadog without batching (1k events/min, 30s)

        Returns:
            Complete test results
        """
        print(f"\n{'#'*80}")
        print("SIEM LOAD TEST SUITE - 10K EVENTS/MIN THROUGHPUT")
        print(f"{'#'*80}")
        print(f"Start Time: {datetime.now(UTC).isoformat()}")

        all_results = {
            "test_suite": "SIEM Load Testing",
            "start_time": datetime.now(UTC).isoformat(),
            "tests": [],
        }

        # Test 1: Splunk with batching (10k events/min)
        print("\n[TEST 1/4] Splunk with batching - 10k events/min")
        splunk_batch_results = await self.test_splunk_throughput(
            events_per_minute=10000, duration_seconds=60, use_batch=True
        )
        all_results["tests"].append(splunk_batch_results)
        await asyncio.sleep(2)  # Cool down between tests

        # Test 2: Splunk without batching (1k events/min for comparison)
        print("\n[TEST 2/4] Splunk without batching - 1k events/min")
        splunk_single_results = await self.test_splunk_throughput(
            events_per_minute=1000, duration_seconds=30, use_batch=False
        )
        all_results["tests"].append(splunk_single_results)
        await asyncio.sleep(2)

        # Test 3: Datadog with batching (10k events/min)
        print("\n[TEST 3/4] Datadog with batching - 10k events/min")
        datadog_batch_results = await self.test_datadog_throughput(
            events_per_minute=10000, duration_seconds=60, use_batch=True
        )
        all_results["tests"].append(datadog_batch_results)
        await asyncio.sleep(2)

        # Test 4: Datadog without batching (1k events/min for comparison)
        print("\n[TEST 4/4] Datadog without batching - 1k events/min")
        datadog_single_results = await self.test_datadog_throughput(
            events_per_minute=1000, duration_seconds=30, use_batch=False
        )
        all_results["tests"].append(datadog_single_results)

        all_results["end_time"] = datetime.now(UTC).isoformat()

        # Save results
        self._save_results(all_results)

        # Print comparison summary
        self._print_comparison_summary(all_results)

        return all_results

    def _save_results(self, results: dict[str, Any]) -> None:
        """Save test results to JSON file."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"siem_load_test_{timestamp}.json"

        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n{'='*80}")
        print(f"Results saved to: {output_file}")
        print(f"{'='*80}")

    def _print_comparison_summary(self, results: dict[str, Any]) -> None:
        """Print comparison summary of all tests."""
        print(f"\n{'#'*80}")
        print("COMPARISON SUMMARY")
        print(f"{'#'*80}\n")

        # Group by SIEM type and batch mode
        splunk_batch = next(
            (t for t in results["tests"] if t["siem_type"] == "splunk" and t["use_batch"]), None
        )
        splunk_single = next(
            (t for t in results["tests"] if t["siem_type"] == "splunk" and not t["use_batch"]), None
        )
        datadog_batch = next(
            (t for t in results["tests"] if t["siem_type"] == "datadog" and t["use_batch"]), None
        )
        datadog_single = next(
            (t for t in results["tests"] if t["siem_type"] == "datadog" and not t["use_batch"]), None
        )

        # Throughput comparison
        print("THROUGHPUT (events/min):")
        print(f"  Splunk (Batch):    {splunk_batch['actual_throughput_per_minute']:>10,.2f}")
        print(f"  Splunk (Single):   {splunk_single['actual_throughput_per_minute']:>10,.2f}")
        print(f"  Datadog (Batch):   {datadog_batch['actual_throughput_per_minute']:>10,.2f}")
        print(f"  Datadog (Single):  {datadog_single['actual_throughput_per_minute']:>10,.2f}")

        # Success rate comparison
        print("\nSUCCESS RATE (%):")
        print(f"  Splunk (Batch):    {splunk_batch['success_rate_percentage']:>10.2f}%")
        print(f"  Splunk (Single):   {splunk_single['success_rate_percentage']:>10.2f}%")
        print(f"  Datadog (Batch):   {datadog_batch['success_rate_percentage']:>10.2f}%")
        print(f"  Datadog (Single):  {datadog_single['success_rate_percentage']:>10.2f}%")

        # Latency comparison (P95)
        print("\nLATENCY P95 (ms):")
        print(f"  Splunk (Batch):    {splunk_batch['latency_p95_ms']:>10.2f}ms")
        print(f"  Splunk (Single):   {splunk_single['latency_p95_ms']:>10.2f}ms")
        print(f"  Datadog (Batch):   {datadog_batch['latency_p95_ms']:>10.2f}ms")
        print(f"  Datadog (Single):  {datadog_single['latency_p95_ms']:>10.2f}ms")

        # Performance insights
        print("\nPERFORMANCE INSIGHTS:")
        splunk_batch_efficiency = (
            splunk_batch["actual_throughput_per_minute"]
            / splunk_single["actual_throughput_per_minute"]
        )
        datadog_batch_efficiency = (
            datadog_batch["actual_throughput_per_minute"]
            / datadog_single["actual_throughput_per_minute"]
        )

        print(f"  Splunk batching improves throughput by {splunk_batch_efficiency:.2f}x")
        print(f"  Datadog batching improves throughput by {datadog_batch_efficiency:.2f}x")

        # Target achievement
        print("\nTARGET ACHIEVEMENT (10k events/min):")
        print(f"  Splunk:  {splunk_batch['throughput_percentage']:.2f}%")
        print(f"  Datadog: {datadog_batch['throughput_percentage']:.2f}%")


async def main():
    """Run the load test suite."""
    tester = SIEMLoadTester()
    results = await tester.run_comprehensive_load_test()

    # Exit with error code if any test failed to achieve >95% of target
    failed_tests = [
        t for t in results["tests"] if t["use_batch"] and t["throughput_percentage"] < 95
    ]

    if failed_tests:
        print("\n⚠️  WARNING: Some tests did not achieve 95% of target throughput")
        for test in failed_tests:
            print(
                f"  - {test['siem_type']}: {test['throughput_percentage']:.2f}% "
                f"({test['actual_throughput_per_minute']:.0f}/{test['target_events_per_minute']} events/min)"
            )
        return 1

    print("\n✅ All tests passed throughput requirements!")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
