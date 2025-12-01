#!/usr/bin/env python3
"""
Execute HTTP Adapter Performance Benchmarks.

This script runs comprehensive benchmarks on the HTTP adapter to establish
performance baselines for SARK v2.0.

Engineer: QA-2
Usage: python run_http_benchmarks.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from sark.adapters.http.http_adapter import HTTPAdapter
from sark.models.base import InvocationRequest
from tests.performance.v2.benchmarks import run_comprehensive_benchmarks


async def main():
    """Run HTTP adapter benchmarks."""
    print("="*80)
    print("HTTP ADAPTER PERFORMANCE BENCHMARKS")
    print("="*80)
    print("\nInitializing HTTP adapter for benchmarking...")

    # Create HTTP adapter (using httpbin for testing)
    adapter = HTTPAdapter(
        base_url="https://httpbin.org",
        rate_limit=None,  # No rate limiting for benchmarks
        circuit_breaker_threshold=10,
        timeout=30.0,
        max_retries=1,  # Minimal retries for accurate timing
    )

    # Create sample request
    sample_request = InvocationRequest(
        capability_id="httpbin.get",
        principal_id="benchmark-principal",
        arguments={},
        context={
            "capability_metadata": {
                "http_method": "GET",
                "http_path": "/get",
            }
        },
    )

    print(f"Target: {adapter.base_url}")
    print(f"Adapter: {adapter.protocol_name} v{adapter.protocol_version}")
    print("\nStarting benchmark suite...\n")

    # Run comprehensive benchmarks
    output_dir = Path(__file__).parent / "benchmark_results"
    runner = await run_comprehensive_benchmarks(
        adapter=adapter,
        sample_request=sample_request,
        output_dir=output_dir,
    )

    print("\n" + "="*80)
    print("HTTP ADAPTER BENCHMARKS COMPLETE")
    print("="*80)
    print(f"\nResults saved to: {output_dir}")

    # Print summary
    runner.print_summary()

    # Save detailed results
    json_path = runner.save_results(filename="http_adapter_benchmarks.json")
    print(f"\nDetailed results: {json_path}")

    return runner


if __name__ == "__main__":
    runner = asyncio.run(main())
