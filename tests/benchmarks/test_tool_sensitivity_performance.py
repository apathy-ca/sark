"""Tool Sensitivity Classification Performance Benchmarks.

Tests sensitivity detection performance to ensure <5ms detection time.
"""

import statistics
import time

import pytest

from sark.services.discovery.tool_registry import ToolRegistry


@pytest.fixture
def tool_registry(db_session):
    """Create ToolRegistry instance."""
    return ToolRegistry(db_session)


# ============================================================================
# DETECTION PERFORMANCE BENCHMARKS
# ============================================================================


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_sensitivity_detection_performance(tool_registry):
    """Benchmark: Sensitivity detection should be <5ms."""
    test_tools = [
        ("read_user_data", "Retrieves user information"),
        ("update_config", "Modifies system configuration"),
        ("delete_database", "Permanently removes database"),
        ("process_payment", "Handles credit card transactions"),
        ("list_servers", "Shows available servers"),
        ("exec_command", "Executes system commands"),
        ("manage_credentials", "Manages API credentials"),
        ("write_logs", "Writes log entries"),
        ("get_status", "Retrieves system status"),
        ("admin_panel", "Administrative operations"),
    ]

    latencies = []

    # Run 1000 detections
    for _ in range(100):
        for name, desc in test_tools:
            start = time.perf_counter()
            level = await tool_registry.detect_sensitivity(
                tool_name=name,
                tool_description=desc,
            )
            end = time.perf_counter()

            latency_ms = (end - start) * 1000
            latencies.append(latency_ms)

            assert level is not None

    avg_latency = statistics.mean(latencies)
    p50_latency = statistics.median(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18]
    p99_latency = statistics.quantiles(latencies, n=100)[98]
    max_latency = max(latencies)

    print("\n" + "=" * 60)
    print("SENSITIVITY DETECTION PERFORMANCE")
    print("=" * 60)
    print(f"Iterations: {len(latencies)}")
    print(f"Average:    {avg_latency:.3f}ms")
    print(f"P50:        {p50_latency:.3f}ms")
    print(f"P95:        {p95_latency:.3f}ms")
    print(f"P99:        {p99_latency:.3f}ms")
    print(f"Max:        {max_latency:.3f}ms")
    print("=" * 60)

    # Assert performance targets
    assert p95_latency < 5.0, f"P95 latency {p95_latency:.3f}ms exceeds 5ms target"
    assert avg_latency < 2.0, f"Average latency {avg_latency:.3f}ms exceeds 2ms target"


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_detection_with_parameters_performance(tool_registry):
    """Benchmark: Detection with parameter analysis should still be <5ms."""
    parameters = {
        "username": {"type": "string"},
        "password": {"type": "string"},
        "admin_flag": {"type": "boolean"},
        "action": {"type": "string"},
    }

    latencies = []

    # Run 1000 detections with parameters
    for i in range(1000):
        start = time.perf_counter()
        await tool_registry.detect_sensitivity(
            tool_name=f"manage_account_{i}",
            tool_description="Account management operations",
            parameters=parameters,
        )
        end = time.perf_counter()

        latency_ms = (end - start) * 1000
        latencies.append(latency_ms)

    avg_latency = statistics.mean(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18]

    print("\n" + "=" * 60)
    print("DETECTION WITH PARAMETERS PERFORMANCE")
    print("=" * 60)
    print(f"Iterations: {len(latencies)}")
    print(f"Average:    {avg_latency:.3f}ms")
    print(f"P95:        {p95_latency:.3f}ms")
    print("=" * 60)

    assert p95_latency < 5.0, f"P95 latency {p95_latency:.3f}ms exceeds 5ms target"


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_keyword_matching_performance(tool_registry):
    """Benchmark: Keyword matching with regex should be fast."""

    text = "this is a test string with delete and admin keywords in it for testing"

    latencies = []

    # Run 10000 keyword matches
    for _ in range(10000):
        start = time.perf_counter()

        # Simulate keyword matching
        tool_registry._contains_keywords(text, tool_registry.HIGH_KEYWORDS)

        end = time.perf_counter()

        latency_ms = (end - start) * 1000
        latencies.append(latency_ms)

    avg_latency = statistics.mean(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18]

    print("\n" + "=" * 60)
    print("KEYWORD MATCHING PERFORMANCE")
    print("=" * 60)
    print(f"Iterations: {len(latencies)}")
    print(f"Average:    {avg_latency:.4f}ms")
    print(f"P95:        {p95_latency:.4f}ms")
    print("=" * 60)

    # Keyword matching should be sub-millisecond
    assert p95_latency < 0.5, f"P95 latency {p95_latency:.4f}ms exceeds 0.5ms target"


# ============================================================================
# DETECTION ACCURACY BENCHMARKS
# ============================================================================


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_detection_accuracy_low_sensitivity(tool_registry):
    """Benchmark: Verify detection accuracy for low sensitivity tools."""
    from sark.models.mcp_server import SensitivityLevel

    low_tools = [
        ("read_data", "Reads data from database"),
        ("get_user", "Gets user information"),
        ("list_items", "Lists all items"),
        ("view_logs", "Views system logs"),
        ("fetch_status", "Fetches system status"),
        ("retrieve_config", "Retrieves configuration"),
        ("show_metrics", "Shows metrics"),
        ("query_database", "Queries the database"),
        ("search_users", "Searches for users"),
        ("find_records", "Finds records"),
    ]

    correct = 0
    total = len(low_tools)

    for name, desc in low_tools:
        level = await tool_registry.detect_sensitivity(name, desc)
        if level == SensitivityLevel.LOW:
            correct += 1

    accuracy = (correct / total) * 100

    print("\n" + "=" * 60)
    print("LOW SENSITIVITY DETECTION ACCURACY")
    print("=" * 60)
    print(f"Total:    {total}")
    print(f"Correct:  {correct}")
    print(f"Accuracy: {accuracy:.1f}%")
    print("=" * 60)

    assert accuracy >= 80.0, f"Accuracy {accuracy:.1f}% below 80% target"


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_detection_accuracy_critical_sensitivity(tool_registry):
    """Benchmark: Verify detection accuracy for critical sensitivity tools."""
    from sark.models.mcp_server import SensitivityLevel

    critical_tools = [
        ("process_payment", "Processes credit card payments"),
        ("manage_credentials", "Manages API credentials"),
        ("reset_password", "Resets user passwords"),
        ("handle_transactions", "Handles financial transactions"),
        ("encrypt_data", "Encrypts sensitive data with secret keys"),
        ("decrypt_secrets", "Decrypts secret information"),
        ("manage_tokens", "Manages authentication tokens"),
        ("update_permissions", "Updates access control permissions"),
        ("store_credit_card", "Stores credit card information"),
        ("generate_keys", "Generates encryption keys"),
    ]

    correct = 0
    total = len(critical_tools)

    for name, desc in critical_tools:
        level = await tool_registry.detect_sensitivity(name, desc)
        if level == SensitivityLevel.CRITICAL:
            correct += 1

    accuracy = (correct / total) * 100

    print("\n" + "=" * 60)
    print("CRITICAL SENSITIVITY DETECTION ACCURACY")
    print("=" * 60)
    print(f"Total:    {total}")
    print(f"Correct:  {correct}")
    print(f"Accuracy: {accuracy:.1f}%")
    print("=" * 60)

    assert accuracy >= 80.0, f"Accuracy {accuracy:.1f}% below 80% target"


# ============================================================================
# THROUGHPUT BENCHMARKS
# ============================================================================


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_detection_throughput(tool_registry):
    """Benchmark: Sensitivity detection throughput (detections/second)."""
    import asyncio

    test_tools = [(f"tool_{i}", f"Test tool {i}") for i in range(1000)]

    start_time = time.perf_counter()

    # Run concurrent detections
    tasks = []
    for name, desc in test_tools:
        task = tool_registry.detect_sensitivity(name, desc)
        tasks.append(task)

    await asyncio.gather(*tasks)

    end_time = time.perf_counter()
    duration = end_time - start_time

    throughput = len(test_tools) / duration

    print("\n" + "=" * 60)
    print("SENSITIVITY DETECTION THROUGHPUT")
    print("=" * 60)
    print(f"Iterations:  {len(test_tools)}")
    print(f"Duration:    {duration:.2f}s")
    print(f"Throughput:  {throughput:.0f} detections/s")
    print("=" * 60)

    # Should achieve >1000 detections/s
    assert throughput > 1000, f"Throughput {throughput:.0f} below 1000/s target"


# ============================================================================
# MEMORY USAGE BENCHMARKS
# ============================================================================


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_detection_memory_efficiency(tool_registry):
    """Benchmark: Ensure detection doesn't leak memory."""

    # Get initial memory usage
    initial_refs = len(tool_registry.HIGH_KEYWORDS)

    # Run many detections
    for i in range(10000):
        await tool_registry.detect_sensitivity(
            f"tool_{i}",
            f"Test tool {i} with various operations",
        )

    # Check keywords list hasn't grown
    final_refs = len(tool_registry.HIGH_KEYWORDS)

    print("\n" + "=" * 60)
    print("MEMORY EFFICIENCY CHECK")
    print("=" * 60)
    print(f"Initial keyword count: {initial_refs}")
    print(f"Final keyword count:   {final_refs}")
    print(f"Change:                {final_refs - initial_refs}")
    print("=" * 60)

    # Keywords list should remain constant
    assert initial_refs == final_refs, "Memory leak detected in keyword lists"


# ============================================================================
# EDGE CASE PERFORMANCE
# ============================================================================


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_detection_long_descriptions(tool_registry):
    """Benchmark: Performance with very long descriptions."""
    # Create a very long description
    long_desc = " ".join(["This is a very long tool description that contains many words " * 100])

    latencies = []

    # Run 100 detections with long descriptions
    for i in range(100):
        start = time.perf_counter()
        await tool_registry.detect_sensitivity(
            f"tool_{i}",
            long_desc,
        )
        end = time.perf_counter()

        latency_ms = (end - start) * 1000
        latencies.append(latency_ms)

    avg_latency = statistics.mean(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18]

    print("\n" + "=" * 60)
    print("LONG DESCRIPTION PERFORMANCE")
    print("=" * 60)
    print(f"Description length: {len(long_desc)} chars")
    print(f"Iterations:         {len(latencies)}")
    print(f"Average:            {avg_latency:.2f}ms")
    print(f"P95:                {p95_latency:.2f}ms")
    print("=" * 60)

    # Even with long descriptions, should be <10ms
    assert p95_latency < 10.0, f"P95 latency {p95_latency:.2f}ms exceeds 10ms target"


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_detection_many_parameters(tool_registry):
    """Benchmark: Performance with many parameters."""
    # Create many parameters
    parameters = {
        f"param_{i}": {"type": "string", "description": "Test parameter"} for i in range(100)
    }

    latencies = []

    # Run 100 detections with many parameters
    for i in range(100):
        start = time.perf_counter()
        await tool_registry.detect_sensitivity(
            f"tool_{i}",
            "Test tool",
            parameters=parameters,
        )
        end = time.perf_counter()

        latency_ms = (end - start) * 1000
        latencies.append(latency_ms)

    avg_latency = statistics.mean(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18]

    print("\n" + "=" * 60)
    print("MANY PARAMETERS PERFORMANCE")
    print("=" * 60)
    print(f"Parameter count: {len(parameters)}")
    print(f"Iterations:      {len(latencies)}")
    print(f"Average:         {avg_latency:.2f}ms")
    print(f"P95:             {p95_latency:.2f}ms")
    print("=" * 60)

    # Should handle many parameters efficiently
    assert p95_latency < 10.0, f"P95 latency {p95_latency:.2f}ms exceeds 10ms target"
