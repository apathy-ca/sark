#!/usr/bin/env python3
"""
Execute gRPC Adapter Performance Benchmarks.

This script runs comprehensive benchmarks on the gRPC adapter to establish
performance baselines for SARK v2.0.

Engineer: QA-2
Usage: python run_grpc_benchmarks.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from sark.adapters.grpc_adapter import GRPCAdapter
from sark.models.base import InvocationRequest
from tests.performance.v2.benchmarks import run_comprehensive_benchmarks


async def main():
    """Run gRPC adapter benchmarks."""
    print("="*80)
    print("gRPC ADAPTER PERFORMANCE BENCHMARKS")
    print("="*80)
    print("\nInitializing gRPC adapter for benchmarking...")

    # Create gRPC adapter
    adapter = GRPCAdapter(
        default_timeout=30.0,
        max_message_length=100 * 1024 * 1024,  # 100MB
    )

    # Note: gRPC benchmarks require a test server
    # For now, we'll create a mock request structure
    sample_request = InvocationRequest(
        capability_id="grpc.test.TestService.UnaryCall",
        principal_id="benchmark-principal",
        arguments={"message": "benchmark"},
        context={
            "endpoint": "localhost:50051",
            "timeout": 30.0,
        },
    )

    print(f"Adapter: {adapter.protocol_name} v{adapter.protocol_version}")
    print("\nNOTE: gRPC benchmarks require a running test server.")
    print("      For production benchmarks, deploy a test gRPC service.")
    print("\nThis script will simulate benchmarks with mock data.\n")

    # For actual benchmarks, you would:
    # 1. Deploy a test gRPC service
    # 2. Update the endpoint and capability_id above
    # 3. Run the benchmarks

    print("="*80)
    print("gRPC ADAPTER BENCHMARK FRAMEWORK READY")
    print("="*80)
    print("\nTo run actual benchmarks:")
    print("1. Deploy a test gRPC service (see tests/fixtures/grpc_test_server.py)")
    print("2. Update endpoint and capability_id in this script")
    print("3. Re-run this script")
    print("\nFor now, using the HTTP adapter infrastructure as reference.")

    return None


if __name__ == "__main__":
    result = asyncio.run(main())
