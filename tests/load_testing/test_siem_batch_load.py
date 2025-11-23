"""Enhanced load testing with actual batch processing for SIEM integrations.

Tests real batch handler performance with 10k events/min throughput using
the actual BatchHandler implementation.
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
    BatchConfig,
    BatchHandler,
)


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
            user_agent="BatchLoadTestAgent/1.0",
            request_id=str(uuid4()),
            details={
                "test_event": True,
                "batch_load_test": True,
                "random_value": random.randint(1, 1000),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
        return event

    def generate_batch(self, count: int) -> list[AuditEvent]:
        """Generate a batch of events."""
        return [self.generate_event() for _ in range(count)]


class BatchLoadTester:
    """Enhanced load tester using actual BatchHandler implementation."""

    def __init__(self, output_dir: Path | None = None):
        """Initialize batch load tester."""
        self.output_dir = output_dir or Path("tests/load_testing/results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.generator = EventGenerator()

    async def test_splunk_with_batch_handler(
        self,
        events_per_minute: int = 10000,
        duration_seconds: int = 60,
        batch_size: int = 100,
        batch_timeout: int = 5,
    ) -> dict[str, Any]:
        """Test Splunk with actual BatchHandler.

        Args:
            events_per_minute: Target events per minute
            duration_seconds: Test duration in seconds
            batch_size: Events per batch
            batch_timeout: Batch timeout in seconds

        Returns:
            Performance metrics
        """
        print(f"\n{'='*80}")
        print(f"Testing Splunk with BatchHandler - {events_per_minute} events/min")
        print(f"Batch Size: {batch_size}, Timeout: {batch_timeout}s")
        print(f"{'='*80}")

        # Track metrics
        events_enqueued = 0
        batches_sent = 0
        batch_sizes: list[int] = []
        batch_latencies: list[float] = []
        start_time = time.time()
        target_events = int((events_per_minute / 60) * duration_seconds)

        # Calculate rate
        events_per_second = events_per_minute / 60
        delay_between_events = 1.0 / events_per_second

        print(f"Target: {target_events:,} events over {duration_seconds}s")
        print(f"Rate: {events_per_second:.2f} events/sec")
        print(f"Expected batches: ~{target_events // batch_size}\n")

        # Mock callback to track batch sends
        async def mock_send_batch(events: list[AuditEvent]) -> bool:
            """Mock batch send with simulated network latency."""
            nonlocal batches_sent, batch_sizes, batch_latencies
            import random

            # Simulate realistic batch send latency (10-50ms for network + processing)
            batch_start = time.time()
            latency = random.uniform(0.010, 0.050)
            await asyncio.sleep(latency)

            batches_sent += 1
            batch_sizes.append(len(events))
            batch_latencies.append((time.time() - batch_start) * 1000)
            return True

        # Create BatchHandler
        batch_config = BatchConfig(
            batch_size=batch_size,
            batch_timeout_seconds=batch_timeout,
            max_queue_size=10000,
        )
        batch_handler = BatchHandler(mock_send_batch, batch_config)

        # Start batch handler
        await batch_handler.start()

        try:
            # Enqueue events
            last_progress = 0
            while time.time() - start_time < duration_seconds:
                event = self.generator.generate_event()

                # Enqueue event (non-blocking)
                await batch_handler.enqueue(event)
                events_enqueued += 1

                # Progress reporting
                elapsed = time.time() - start_time
                current_progress = int((elapsed / duration_seconds) * 100)
                if current_progress >= last_progress + 10:
                    metrics = batch_handler.get_metrics()
                    print(
                        f"Progress: {current_progress}% - Enqueued: {events_enqueued:,}, "
                        f"Batches sent: {batches_sent}, Queue: {metrics['queue_size']}"
                    )
                    last_progress = current_progress

                # Rate limiting
                await asyncio.sleep(delay_between_events)

            # Flush remaining events
            print("\nFlushing remaining events...")
            await batch_handler.stop(flush=True)

            # Allow final batches to complete
            await asyncio.sleep(0.5)

        finally:
            if batch_handler._running:
                await batch_handler.stop(flush=True)

        # Calculate metrics
        total_time = time.time() - start_time
        events_sent = sum(batch_sizes)
        actual_throughput = events_sent / (total_time / 60)
        avg_batch_size = statistics.mean(batch_sizes) if batch_sizes else 0

        results = {
            "siem_type": "splunk",
            "test_mode": "batch_handler",
            "target_events_per_minute": events_per_minute,
            "duration_seconds": duration_seconds,
            "batch_size_configured": batch_size,
            "batch_timeout_seconds": batch_timeout,
            "total_time_seconds": total_time,
            "events_enqueued": events_enqueued,
            "events_sent": events_sent,
            "target_events": target_events,
            "batches_sent": batches_sent,
            "avg_batch_size": avg_batch_size,
            "actual_throughput_per_minute": actual_throughput,
            "throughput_percentage": (actual_throughput / events_per_minute) * 100,
            "success_rate_percentage": (events_sent / events_enqueued) * 100 if events_enqueued > 0 else 0,
            "batch_latency_avg_ms": statistics.mean(batch_latencies) if batch_latencies else 0,
            "batch_latency_p50_ms": statistics.median(batch_latencies) if batch_latencies else 0,
            "batch_latency_p95_ms": (
                statistics.quantiles(batch_latencies, n=20)[18] if len(batch_latencies) > 20 else 0
            ),
            "batch_latency_max_ms": max(batch_latencies) if batch_latencies else 0,
        }

        # Print summary
        print(f"\n{'='*80}")
        print("Splunk BatchHandler Load Test Results")
        print(f"{'='*80}")
        print(f"Events Enqueued: {events_enqueued:,}")
        print(f"Events Sent: {events_sent:,} / {target_events:,}")
        print(f"Batches Sent: {batches_sent}")
        print(f"Avg Batch Size: {avg_batch_size:.1f}")
        print(f"Success Rate: {results['success_rate_percentage']:.2f}%")
        print(f"Actual Throughput: {actual_throughput:,.2f} events/min ({actual_throughput/60:.2f} events/sec)")
        print(f"Throughput Achievement: {results['throughput_percentage']:.2f}%")
        print("\nBatch Latency Statistics:")
        print(f"  Average: {results['batch_latency_avg_ms']:.2f}ms")
        print(f"  Median (P50): {results['batch_latency_p50_ms']:.2f}ms")
        print(f"  P95: {results['batch_latency_p95_ms']:.2f}ms")
        print(f"  Max: {results['batch_latency_max_ms']:.2f}ms")

        return results

    async def test_datadog_with_batch_handler(
        self,
        events_per_minute: int = 10000,
        duration_seconds: int = 60,
        batch_size: int = 100,
        batch_timeout: int = 5,
    ) -> dict[str, Any]:
        """Test Datadog with actual BatchHandler.

        Args:
            events_per_minute: Target events per minute
            duration_seconds: Test duration in seconds
            batch_size: Events per batch
            batch_timeout: Batch timeout in seconds

        Returns:
            Performance metrics
        """
        print(f"\n{'='*80}")
        print(f"Testing Datadog with BatchHandler - {events_per_minute} events/min")
        print(f"Batch Size: {batch_size}, Timeout: {batch_timeout}s")
        print(f"{'='*80}")

        # Track metrics
        events_enqueued = 0
        batches_sent = 0
        batch_sizes: list[int] = []
        batch_latencies: list[float] = []
        start_time = time.time()
        target_events = int((events_per_minute / 60) * duration_seconds)

        # Calculate rate
        events_per_second = events_per_minute / 60
        delay_between_events = 1.0 / events_per_second

        print(f"Target: {target_events:,} events over {duration_seconds}s")
        print(f"Rate: {events_per_second:.2f} events/sec")
        print(f"Expected batches: ~{target_events // batch_size}\n")

        # Mock callback
        async def mock_send_batch(events: list[AuditEvent]) -> bool:
            """Mock batch send with simulated network latency."""
            nonlocal batches_sent, batch_sizes, batch_latencies
            import random

            batch_start = time.time()
            latency = random.uniform(0.010, 0.050)
            await asyncio.sleep(latency)

            batches_sent += 1
            batch_sizes.append(len(events))
            batch_latencies.append((time.time() - batch_start) * 1000)
            return True

        # Create BatchHandler
        batch_config = BatchConfig(
            batch_size=batch_size,
            batch_timeout_seconds=batch_timeout,
            max_queue_size=10000,
        )
        batch_handler = BatchHandler(mock_send_batch, batch_config)

        # Start batch handler
        await batch_handler.start()

        try:
            # Enqueue events
            last_progress = 0
            while time.time() - start_time < duration_seconds:
                event = self.generator.generate_event()

                await batch_handler.enqueue(event)
                events_enqueued += 1

                elapsed = time.time() - start_time
                current_progress = int((elapsed / duration_seconds) * 100)
                if current_progress >= last_progress + 10:
                    metrics = batch_handler.get_metrics()
                    print(
                        f"Progress: {current_progress}% - Enqueued: {events_enqueued:,}, "
                        f"Batches sent: {batches_sent}, Queue: {metrics['queue_size']}"
                    )
                    last_progress = current_progress

                await asyncio.sleep(delay_between_events)

            # Flush remaining
            print("\nFlushing remaining events...")
            await batch_handler.stop(flush=True)
            await asyncio.sleep(0.5)

        finally:
            if batch_handler._running:
                await batch_handler.stop(flush=True)

        # Calculate metrics
        total_time = time.time() - start_time
        events_sent = sum(batch_sizes)
        actual_throughput = events_sent / (total_time / 60)
        avg_batch_size = statistics.mean(batch_sizes) if batch_sizes else 0

        results = {
            "siem_type": "datadog",
            "test_mode": "batch_handler",
            "target_events_per_minute": events_per_minute,
            "duration_seconds": duration_seconds,
            "batch_size_configured": batch_size,
            "batch_timeout_seconds": batch_timeout,
            "total_time_seconds": total_time,
            "events_enqueued": events_enqueued,
            "events_sent": events_sent,
            "target_events": target_events,
            "batches_sent": batches_sent,
            "avg_batch_size": avg_batch_size,
            "actual_throughput_per_minute": actual_throughput,
            "throughput_percentage": (actual_throughput / events_per_minute) * 100,
            "success_rate_percentage": (events_sent / events_enqueued) * 100 if events_enqueued > 0 else 0,
            "batch_latency_avg_ms": statistics.mean(batch_latencies) if batch_latencies else 0,
            "batch_latency_p50_ms": statistics.median(batch_latencies) if batch_latencies else 0,
            "batch_latency_p95_ms": (
                statistics.quantiles(batch_latencies, n=20)[18] if len(batch_latencies) > 20 else 0
            ),
            "batch_latency_max_ms": max(batch_latencies) if batch_latencies else 0,
        }

        # Print summary
        print(f"\n{'='*80}")
        print("Datadog BatchHandler Load Test Results")
        print(f"{'='*80}")
        print(f"Events Enqueued: {events_enqueued:,}")
        print(f"Events Sent: {events_sent:,} / {target_events:,}")
        print(f"Batches Sent: {batches_sent}")
        print(f"Avg Batch Size: {avg_batch_size:.1f}")
        print(f"Success Rate: {results['success_rate_percentage']:.2f}%")
        print(f"Actual Throughput: {actual_throughput:,.2f} events/min ({actual_throughput/60:.2f} events/sec)")
        print(f"Throughput Achievement: {results['throughput_percentage']:.2f}%")
        print("\nBatch Latency Statistics:")
        print(f"  Average: {results['batch_latency_avg_ms']:.2f}ms")
        print(f"  Median (P50): {results['batch_latency_p50_ms']:.2f}ms")
        print(f"  P95: {results['batch_latency_p95_ms']:.2f}ms")
        print(f"  Max: {results['batch_latency_max_ms']:.2f}ms")

        return results

    async def run_comprehensive_batch_test(self) -> dict[str, Any]:
        """Run comprehensive batch load test for both SIEM integrations.

        Tests:
        1. Splunk with BatchHandler (10k events/min, 60s)
        2. Datadog with BatchHandler (10k events/min, 60s)
        3. Splunk with larger batches (10k events/min, 60s, batch_size=500)
        4. Datadog with larger batches (10k events/min, 60s, batch_size=500)

        Returns:
            Complete test results
        """
        print(f"\n{'#'*80}")
        print("SIEM BATCH HANDLER LOAD TEST - 10K EVENTS/MIN THROUGHPUT")
        print(f"{'#'*80}")
        print(f"Start Time: {datetime.now(UTC).isoformat()}")

        all_results = {
            "test_suite": "SIEM Batch Handler Load Testing",
            "start_time": datetime.now(UTC).isoformat(),
            "tests": [],
        }

        # Test 1: Splunk with standard batching (100)
        print("\n[TEST 1/4] Splunk BatchHandler - 10k events/min - Batch size: 100")
        splunk_100 = await self.test_splunk_with_batch_handler(
            events_per_minute=10000, duration_seconds=60, batch_size=100, batch_timeout=5
        )
        all_results["tests"].append(splunk_100)
        await asyncio.sleep(2)

        # Test 2: Datadog with standard batching (100)
        print("\n[TEST 2/4] Datadog BatchHandler - 10k events/min - Batch size: 100")
        datadog_100 = await self.test_datadog_with_batch_handler(
            events_per_minute=10000, duration_seconds=60, batch_size=100, batch_timeout=5
        )
        all_results["tests"].append(datadog_100)
        await asyncio.sleep(2)

        # Test 3: Splunk with larger batches (500)
        print("\n[TEST 3/4] Splunk BatchHandler - 10k events/min - Batch size: 500")
        splunk_500 = await self.test_splunk_with_batch_handler(
            events_per_minute=10000, duration_seconds=60, batch_size=500, batch_timeout=5
        )
        all_results["tests"].append(splunk_500)
        await asyncio.sleep(2)

        # Test 4: Datadog with larger batches (500)
        print("\n[TEST 4/4] Datadog BatchHandler - 10k events/min - Batch size: 500")
        datadog_500 = await self.test_datadog_with_batch_handler(
            events_per_minute=10000, duration_seconds=60, batch_size=500, batch_timeout=5
        )
        all_results["tests"].append(datadog_500)

        all_results["end_time"] = datetime.now(UTC).isoformat()

        # Save results
        self._save_results(all_results)

        # Print comparison
        self._print_comparison_summary(all_results)

        return all_results

    def _save_results(self, results: dict[str, Any]) -> None:
        """Save test results to JSON file."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"siem_batch_load_test_{timestamp}.json"

        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n{'='*80}")
        print(f"Results saved to: {output_file}")
        print(f"{'='*80}")

    def _print_comparison_summary(self, results: dict[str, Any]) -> None:
        """Print comparison summary."""
        print(f"\n{'#'*80}")
        print("BATCH HANDLER COMPARISON SUMMARY")
        print(f"{'#'*80}\n")

        tests = results["tests"]

        # Throughput comparison
        print("THROUGHPUT (events/min):")
        for test in tests:
            print(
                f"  {test['siem_type'].capitalize():8s} (batch={test['batch_size_configured']:3d}): "
                f"{test['actual_throughput_per_minute']:>10,.2f} "
                f"({test['throughput_percentage']:>5.1f}%)"
            )

        # Success rate
        print("\nSUCCESS RATE (%):")
        for test in tests:
            print(
                f"  {test['siem_type'].capitalize():8s} (batch={test['batch_size_configured']:3d}): "
                f"{test['success_rate_percentage']:>6.2f}%"
            )

        # Batch statistics
        print("\nBATCH STATISTICS:")
        for test in tests:
            print(
                f"  {test['siem_type'].capitalize():8s} (batch={test['batch_size_configured']:3d}): "
                f"{test['batches_sent']:>4d} batches, avg size: {test['avg_batch_size']:.1f}"
            )

        # Latency
        print("\nBATCH LATENCY P95 (ms):")
        for test in tests:
            print(
                f"  {test['siem_type'].capitalize():8s} (batch={test['batch_size_configured']:3d}): "
                f"{test['batch_latency_p95_ms']:>6.2f}ms"
            )

        # Overall assessment
        print("\nOVERALL ASSESSMENT:")
        passed = all(t["throughput_percentage"] >= 95 for t in tests)
        if passed:
            print("  ✅ All tests achieved >= 95% of target throughput")
        else:
            print("  ⚠️  Some tests did not achieve 95% of target throughput")

        avg_throughput = statistics.mean([t["actual_throughput_per_minute"] for t in tests])
        print(f"\n  Average throughput across all tests: {avg_throughput:,.2f} events/min")


async def main():
    """Run the batch handler load test suite."""
    tester = BatchLoadTester()
    results = await tester.run_comprehensive_batch_test()

    # Exit with appropriate code
    failed_tests = [t for t in results["tests"] if t["throughput_percentage"] < 95]

    if failed_tests:
        print("\n⚠️  Some tests did not achieve 95% of target throughput")
        return 1

    print("\n✅ All batch handler tests passed throughput requirements!")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
