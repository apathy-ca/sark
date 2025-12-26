"""
Security Performance Testing (v1.3.0)

Measures overhead from each security feature:
- Prompt injection: Target <3ms
- Anomaly detection: Target <5ms (async)
- Secret scanning: Target <1ms
- MFA: Excluded (user-facing delay)
- Combined: Target <10ms (p95)

Load test: 1000 req/s sustained
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import statistics
import time

import pytest
from src.sark.security.behavioral_analyzer import BehavioralAnalyzer, BehavioralAuditEvent
from src.sark.security.injection_detector import PromptInjectionDetector
from src.sark.security.secret_scanner import SecretScanner


@pytest.mark.performance
class TestSecurityOverhead:
    """Performance overhead tests for security features"""

    # Prompt Injection Detection Performance
    def test_injection_detection_overhead_p50(self):
        """Test p50 latency for prompt injection detection"""
        detector = PromptInjectionDetector()
        params = {"query": "normal user query", "filter": "category:analytics"}

        latencies = []

        for _ in range(1000):
            start = time.perf_counter()
            detector.detect(params)
            latencies.append((time.perf_counter() - start) * 1000)  # ms

        p50 = statistics.median(latencies)
        p95 = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        p99 = statistics.quantiles(latencies, n=100)[98]  # 99th percentile

        print("\nInjection Detection Latency:")
        print(f"  p50: {p50:.2f}ms")
        print(f"  p95: {p95:.2f}ms")
        print(f"  p99: {p99:.2f}ms")

        assert p50 < 2.0, f"p50 latency {p50:.2f}ms exceeds 2ms target"
        assert p95 < 3.0, f"p95 latency {p95:.2f}ms exceeds 3ms target"

    def test_injection_detection_worst_case(self):
        """Test worst-case (complex nested params) injection detection"""
        detector = PromptInjectionDetector()

        # Complex nested structure
        params = {
            f"level1_{i}": {
                f"level2_{j}": {f"level3_{k}": f"value_{i}_{j}_{k}" for k in range(5)}
                for j in range(5)
            }
            for i in range(5)
        }  # 125 total values

        latencies = []

        for _ in range(100):
            start = time.perf_counter()
            detector.detect(params)
            latencies.append((time.perf_counter() - start) * 1000)

        p95 = statistics.quantiles(latencies, n=20)[18]

        print(f"\nInjection Detection (Complex Params) p95: {p95:.2f}ms")

        assert p95 < 5.0, f"Complex params p95 {p95:.2f}ms exceeds 5ms threshold"

    # Secret Scanning Performance
    def test_secret_scanning_overhead_p95(self):
        """Test p95 latency for secret scanning"""
        scanner = SecretScanner()

        # Typical API response
        data = {
            "status": "success",
            "data": {
                "users": [
                    {"id": i, "name": f"User {i}", "email": f"user{i}@example.com"}
                    for i in range(10)
                ],
                "total": 10,
                "page": 1,
            },
        }

        latencies = []

        for _ in range(1000):
            start = time.perf_counter()
            scanner.scan(data)
            latencies.append((time.perf_counter() - start) * 1000)

        p50 = statistics.median(latencies)
        p95 = statistics.quantiles(latencies, n=20)[18]
        p99 = statistics.quantiles(latencies, n=100)[98]

        print("\nSecret Scanning Latency:")
        print(f"  p50: {p50:.2f}ms")
        print(f"  p95: {p95:.2f}ms")
        print(f"  p99: {p99:.2f}ms")

        assert p95 < 1.0, f"p95 latency {p95:.2f}ms exceeds 1ms target"

    def test_secret_scanning_large_response(self):
        """Test secret scanning with large response (10KB+)"""
        scanner = SecretScanner()

        # Large response with many fields
        data = {
            "records": [
                {
                    "id": i,
                    "data": "x" * 100,  # 100 chars per record
                    "metadata": {"field1": "value1", "field2": "value2"},
                }
                for i in range(100)  # 100 records
            ]
        }

        latencies = []

        for _ in range(100):
            start = time.perf_counter()
            scanner.scan(data)
            latencies.append((time.perf_counter() - start) * 1000)

        p95 = statistics.quantiles(latencies, n=20)[18]

        print(f"\nSecret Scanning (Large Response) p95: {p95:.2f}ms")

        assert p95 < 5.0, f"Large response p95 {p95:.2f}ms exceeds 5ms threshold"

    # Anomaly Detection Performance
    @pytest.mark.asyncio
    async def test_anomaly_detection_overhead(self):
        """Test anomaly detection latency"""
        analyzer = BehavioralAnalyzer()

        # Build baseline
        baseline_events = [
            BehavioralAuditEvent(
                user_id="user123",
                timestamp=datetime(2025, 1, 15 + i, 10, 0),
                tool_name="analytics",
                sensitivity="medium",
                result_size=100,
            )
            for i in range(30)
        ]

        baseline = await analyzer.build_baseline("user123", events=baseline_events)

        # Test event
        event = BehavioralAuditEvent(
            user_id="user123",
            timestamp=datetime.now(),
            tool_name="analytics",
            sensitivity="medium",
            result_size=120,
        )

        latencies = []

        for _ in range(1000):
            start = time.perf_counter()
            await analyzer.detect_anomalies(event, baseline)
            latencies.append((time.perf_counter() - start) * 1000)

        p50 = statistics.median(latencies)
        p95 = statistics.quantiles(latencies, n=20)[18]

        print("\nAnomaly Detection Latency:")
        print(f"  p50: {p50:.2f}ms")
        print(f"  p95: {p95:.2f}ms")

        # Anomaly detection runs async, so higher threshold is acceptable
        assert p95 < 5.0, f"p95 latency {p95:.2f}ms exceeds 5ms target"

    # Combined Overhead
    @pytest.mark.asyncio
    async def test_combined_security_overhead_p95(self):
        """Test combined overhead from all security features (p95 < 10ms)"""
        injection_detector = PromptInjectionDetector()
        secret_scanner = SecretScanner()

        params = {"query": "get analytics data", "timeframe": "30d"}
        response = {"status": "success", "data": {"count": 1500, "average": 75.5}}

        latencies = []

        for _ in range(1000):
            start = time.perf_counter()

            # 1. Injection detection (on request)
            injection_detector.detect(params)

            # 2. Secret scanning (on response)
            secret_scanner.scan(response)

            # Note: Anomaly detection runs async, not in critical path

            latencies.append((time.perf_counter() - start) * 1000)

        p50 = statistics.median(latencies)
        p95 = statistics.quantiles(latencies, n=20)[18]
        p99 = statistics.quantiles(latencies, n=100)[98]

        print("\nCombined Security Overhead:")
        print(f"  p50: {p50:.2f}ms")
        print(f"  p95: {p95:.2f}ms")
        print(f"  p99: {p99:.2f}ms")

        assert p95 < 10.0, f"Combined p95 overhead {p95:.2f}ms exceeds 10ms target"

    # Throughput Testing
    def test_throughput_1000_rps(self):
        """Test that system maintains 1000 req/s with security enabled"""
        injection_detector = PromptInjectionDetector()
        secret_scanner = SecretScanner()

        def process_request():
            """Simulate single request with security checks"""
            params = {"query": "user request"}
            response = {"data": "response"}

            injection_detector.detect(params)
            secret_scanner.scan(response)

        # Target: 1000 req/s for 5 seconds = 5000 total requests
        duration_seconds = 5
        target_rps = 1000
        total_requests = duration_seconds * target_rps

        start = time.time()

        # Use thread pool to simulate concurrent requests
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(process_request) for _ in range(total_requests)]

            # Wait for all to complete
            for future in futures:
                future.result()

        elapsed = time.time() - start
        actual_rps = total_requests / elapsed

        print("\nThroughput Test:")
        print(f"  Target: {target_rps} req/s")
        print(f"  Actual: {actual_rps:.0f} req/s")
        print(f"  Duration: {elapsed:.2f}s")

        assert (
            actual_rps >= target_rps * 0.9
        ), f"Throughput {actual_rps:.0f} < 90% of target {target_rps}"

    # Memory Profiling
    def test_memory_usage(self):
        """Test that security features don't cause memory leaks"""
        import tracemalloc

        injection_detector = PromptInjectionDetector()
        secret_scanner = SecretScanner()

        tracemalloc.start()

        # Measure baseline
        snapshot1 = tracemalloc.take_snapshot()

        # Process many requests
        for i in range(10000):
            params = {"query": f"request {i}"}
            response = {"data": f"response {i}"}

            injection_detector.detect(params)
            secret_scanner.scan(response)

        # Measure after load
        snapshot2 = tracemalloc.take_snapshot()

        # Calculate memory diff
        top_stats = snapshot2.compare_to(snapshot1, "lineno")

        total_diff_kb = sum(stat.size_diff for stat in top_stats) / 1024

        print("\nMemory Usage After 10K Requests:")
        print(f"  Diff: {total_diff_kb:.2f} KB")

        tracemalloc.stop()

        # Memory growth should be minimal (<5MB)
        assert total_diff_kb < 5000, f"Memory growth {total_diff_kb:.0f}KB exceeds 5MB threshold"


@pytest.mark.performance
class TestSecurityScaling:
    """Test how security features scale with load"""

    def test_injection_detection_scales_linearly(self):
        """Test that injection detection scales linearly with param count"""
        detector = PromptInjectionDetector()

        param_counts = [10, 50, 100, 500, 1000]
        latencies = []

        for count in param_counts:
            params = {f"param_{i}": f"value_{i}" for i in range(count)}

            # Measure
            times = []
            for _ in range(100):
                start = time.perf_counter()
                detector.detect(params)
                times.append((time.perf_counter() - start) * 1000)

            avg_latency = statistics.mean(times)
            latencies.append(avg_latency)

            print(f"\n{count} params: {avg_latency:.2f}ms avg")

        # Latency should grow roughly linearly
        # 1000 params shouldn't take 100x longer than 10 params
        ratio = latencies[-1] / latencies[0]

        assert ratio < 20, f"Scaling ratio {ratio:.1f}x indicates poor scaling"

    def test_secret_scanning_scales_with_response_size(self):
        """Test that secret scanning scales with response size"""
        scanner = SecretScanner()

        response_sizes = [100, 500, 1000, 5000, 10000]  # Number of fields
        latencies = []

        for size in response_sizes:
            data = {"records": [{"field": f"value_{i}"} for i in range(size)]}

            times = []
            for _ in range(50):
                start = time.perf_counter()
                scanner.scan(data)
                times.append((time.perf_counter() - start) * 1000)

            avg_latency = statistics.mean(times)
            latencies.append(avg_latency)

            print(f"\n{size} fields: {avg_latency:.2f}ms avg")

        # Should scale reasonably
        ratio = latencies[-1] / latencies[0]

        assert ratio < 30, f"Scaling ratio {ratio:.1f}x indicates poor scaling"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
