#!/usr/bin/env python3
"""
Bulk Operations Example for SARK

This example demonstrates:
- Bulk server registration
- Bulk status updates
- Transaction handling (all-or-nothing)
- Error handling and partial success

Usage:
    python bulk_operations.py
"""

import os

import requests


class SARKBulkOperations:
    """Handle bulk operations for SARK."""

    def __init__(self, base_url: str, access_token: str):
        """Initialize bulk operations client.

        Args:
            base_url: SARK API base URL
            access_token: JWT access token
        """
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    def bulk_register_servers(self, servers: list[dict], fail_on_first_error: bool = False) -> dict:
        """Bulk register multiple servers.

        Args:
            servers: List of server configurations
            fail_on_first_error: If True, use transactional mode (all-or-nothing)
                                If False, use best-effort mode (continue on errors)

        Returns:
            Bulk operation result
        """
        mode = "transactional" if fail_on_first_error else "best-effort"
        print(f"\nBulk registering {len(servers)} servers ({mode} mode)")

        payload = {"servers": servers, "fail_on_first_error": fail_on_first_error}

        response = requests.post(f"{self.base_url}/api/v1/bulk/servers/register", headers=self.headers, json=payload)

        response.raise_for_status()
        result = response.json()

        # Display results
        print("\n✓ Bulk operation completed")
        print(f"  Total: {result['total']}")
        print(f"  Succeeded: {result['succeeded']}")
        print(f"  Failed: {result['failed']}")

        if result["succeeded_items"]:
            print("\n  Successful registrations:")
            for item in result["succeeded_items"]:
                print(f"    ✓ {item['name']} → {item['server_id']}")

        if result["failed_items"]:
            print("\n  Failed registrations:")
            for item in result["failed_items"]:
                print(f"    ✗ {item['name']}: {item.get('error', 'Unknown error')}")

        return result

    def bulk_update_server_status(self, updates: list[dict], fail_on_first_error: bool = False) -> dict:
        """Bulk update server statuses.

        Args:
            updates: List of status updates
            fail_on_first_error: If True, use transactional mode

        Returns:
            Bulk operation result
        """
        mode = "transactional" if fail_on_first_error else "best-effort"
        print(f"\nBulk updating {len(updates)} server statuses ({mode} mode)")

        payload = {"updates": updates, "fail_on_first_error": fail_on_first_error}

        response = requests.patch(f"{self.base_url}/api/v1/bulk/servers/status", headers=self.headers, json=payload)

        response.raise_for_status()
        result = response.json()

        # Display results
        print("\n✓ Bulk operation completed")
        print(f"  Total: {result['total']}")
        print(f"  Succeeded: {result['succeeded']}")
        print(f"  Failed: {result['failed']}")

        if result["succeeded_items"]:
            print("\n  Successful updates:")
            for item in result["succeeded_items"]:
                print(f"    ✓ {item['server_id']} → {item['status']}")

        if result["failed_items"]:
            print("\n  Failed updates:")
            for item in result["failed_items"]:
                print(f"    ✗ {item['server_id']}: {item.get('error', 'Unknown error')}")

        return result


def example_bulk_register_best_effort():
    """Example: Bulk register servers in best-effort mode."""
    print("\n" + "=" * 60)
    print("Example 1: Bulk Register (Best-Effort Mode)")
    print("=" * 60)

    # Configuration
    base_url = os.getenv("SARK_API_URL", "https://sark.example.com")
    access_token = os.getenv("SARK_ACCESS_TOKEN", "your-jwt-token")

    bulk_ops = SARKBulkOperations(base_url, access_token)

    # Define servers to register
    servers = [
        {
            "name": "analytics-server-1",
            "transport": "http",
            "endpoint": "http://analytics-1.example.com:8080",
            "capabilities": ["tools"],
            "tools": [],
            "sensitivity_level": "high",
        },
        {
            "name": "analytics-server-2",
            "transport": "http",
            "endpoint": "http://analytics-2.example.com:8080",
            "capabilities": ["tools"],
            "tools": [],
            "sensitivity_level": "high",
        },
        {
            "name": "ml-server-1",
            "transport": "http",
            "endpoint": "http://ml-1.example.com:8080",
            "capabilities": ["tools"],
            "tools": [],
            "sensitivity_level": "critical",
        },
        {
            "name": "dashboard-server-1",
            "transport": "http",
            "endpoint": "http://dashboard-1.example.com:8080",
            "capabilities": ["resources"],
            "tools": [],
            "sensitivity_level": "low",
        },
    ]

    try:
        # Best-effort mode: continues even if some servers fail
        result = bulk_ops.bulk_register_servers(servers, fail_on_first_error=False)

        print("\n📊 Summary:")
        print(f"  Success rate: {result['succeeded']}/{result['total']} " f"({result['succeeded']/result['total']*100:.1f}%)")

    except requests.exceptions.RequestException as e:
        print(f"\n✗ Request failed: {e}")


def example_bulk_register_transactional():
    """Example: Bulk register servers in transactional mode."""
    print("\n" + "=" * 60)
    print("Example 2: Bulk Register (Transactional Mode)")
    print("=" * 60)

    print("""
In transactional mode (fail_on_first_error=True):
- All servers are registered in a single transaction
- If ANY server fails, ALL registrations are rolled back
- Use this when consistency is critical

Example:
    servers = [
        {...},  # Server 1
        {...},  # Server 2
        {...},  # Server 3 (will fail due to policy)
    ]

    result = bulk_ops.bulk_register_servers(
        servers,
        fail_on_first_error=True  # Transactional mode
    )

    # If Server 3 fails, Servers 1 and 2 are also rolled back
    # result['succeeded'] = 0
    # result['failed'] = 3
    """)


def example_bulk_status_update():
    """Example: Bulk update server statuses."""
    print("\n" + "=" * 60)
    print("Example 3: Bulk Status Update")
    print("=" * 60)

    base_url = os.getenv("SARK_API_URL", "https://sark.example.com")
    access_token = os.getenv("SARK_ACCESS_TOKEN", "your-jwt-token")

    bulk_ops = SARKBulkOperations(base_url, access_token)

    # Define status updates
    updates = [
        {"server_id": "550e8400-e29b-41d4-a716-446655440000", "status": "active"},
        {"server_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8", "status": "inactive"},
        {"server_id": "7ca8c920-aeae-22e2-91c5-11d15fe541d9", "status": "active"},
        {"server_id": "8db9d030-bfbf-33f3-a2d6-22e26gf652ea", "status": "decommissioned"},
    ]

    try:
        result = bulk_ops.bulk_update_server_status(updates, fail_on_first_error=False)

        print("\n📊 Summary:")
        print(f"  Success rate: {result['succeeded']}/{result['total']}")

    except requests.exceptions.RequestException as e:
        print(f"\n✗ Request failed: {e}")


def example_large_scale_import():
    """Example: Large-scale server import from CSV."""
    print("\n" + "=" * 60)
    print("Example 4: Large-Scale Import from CSV")
    print("=" * 60)

    print("""
# Import servers from CSV file

import csv

def import_servers_from_csv(csv_file, batch_size=100):
    \"\"\"Import servers from CSV in batches.

    Args:
        csv_file: Path to CSV file
        batch_size: Number of servers per batch (max 100)
    \"\"\"
    base_url = os.getenv("SARK_API_URL")
    access_token = os.getenv("SARK_ACCESS_TOKEN")
    bulk_ops = SARKBulkOperations(base_url, access_token)

    # Read CSV file
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        servers = list(reader)

    print(f"Importing {len(servers)} servers in batches of {batch_size}")

    total_succeeded = 0
    total_failed = 0

    # Process in batches
    for i in range(0, len(servers), batch_size):
        batch = servers[i:i+batch_size]
        batch_num = i // batch_size + 1

        print(f"\\nProcessing batch {batch_num}...")

        # Format servers for API
        server_batch = [
            {
                "name": s["name"],
                "transport": s["transport"],
                "endpoint": s["endpoint"],
                "capabilities": s["capabilities"].split(","),
                "tools": [],
                "sensitivity_level": s.get("sensitivity_level", "medium"),
            }
            for s in batch
        ]

        # Register batch (best-effort mode)
        try:
            result = bulk_ops.bulk_register_servers(
                server_batch,
                fail_on_first_error=False
            )

            total_succeeded += result["succeeded"]
            total_failed += result["failed"]

        except Exception as e:
            print(f"Batch {batch_num} failed: {e}")
            total_failed += len(batch)

    print(f"\\n✓ Import completed")
    print(f"  Total succeeded: {total_succeeded}")
    print(f"  Total failed: {total_failed}")
    print(f"  Success rate: {total_succeeded/(total_succeeded+total_failed)*100:.1f}%")

# Example CSV format:
# name,transport,endpoint,capabilities,sensitivity_level
# server-1,http,http://server-1.example.com,tools,medium
# server-2,http,http://server-2.example.com,tools,high
# server-3,http,http://server-3.example.com,resources,low
    """)


def example_error_handling():
    """Example: Error handling strategies."""
    print("\n" + "=" * 60)
    print("Example 5: Error Handling Strategies")
    print("=" * 60)

    print("""
# Different error handling strategies

# 1. Fail-fast (transactional)
# Use when: All servers must be registered together
try:
    result = bulk_ops.bulk_register_servers(
        servers,
        fail_on_first_error=True  # All-or-nothing
    )
    if result['failed'] > 0:
        print("Rollback occurred - no servers registered")
except requests.exceptions.HTTPError as e:
    print(f"Bulk operation failed: {e}")

# 2. Best-effort with retry
# Use when: Want maximum throughput, can retry failures
result = bulk_ops.bulk_register_servers(
    servers,
    fail_on_first_error=False  # Continue on errors
)

# Retry failed servers
if result['failed'] > 0:
    failed_servers = [
        s for s in servers
        if s['name'] in [f['name'] for f in result['failed_items']]
    ]

    print(f"Retrying {len(failed_servers)} failed servers...")
    retry_result = bulk_ops.bulk_register_servers(
        failed_servers,
        fail_on_first_error=False
    )

# 3. Progressive retry with backoff
# Use when: Temporary failures expected (rate limits, network)
import time

def bulk_register_with_retry(servers, max_retries=3):
    remaining = servers
    retry_count = 0

    while remaining and retry_count < max_retries:
        result = bulk_ops.bulk_register_servers(
            remaining,
            fail_on_first_error=False
        )

        if result['failed'] == 0:
            break

        # Get failed servers for retry
        remaining = [
            s for s in remaining
            if s['name'] in [f['name'] for f in result['failed_items']]
        ]

        retry_count += 1
        if remaining:
            wait_time = 2 ** retry_count  # Exponential backoff
            print(f"Retrying {len(remaining)} servers in {wait_time}s...")
            time.sleep(wait_time)

    return result
    """)


def example_performance_considerations():
    """Example: Performance optimization tips."""
    print("\n" + "=" * 60)
    print("Example 6: Performance Considerations")
    print("=" * 60)

    print("""
# Performance optimization tips for bulk operations

# 1. Batch size
# - Maximum: 100 servers per request
# - Recommended: 50-100 for best performance
# - Smaller batches: Better error isolation
# - Larger batches: Higher throughput

# 2. Parallel processing
# - Split servers across multiple batches
# - Process batches in parallel (use threading/async)

import concurrent.futures
from itertools import islice

def batch_iter(iterable, batch_size):
    iterator = iter(iterable)
    while batch := list(islice(iterator, batch_size)):
        yield batch

def parallel_bulk_register(servers, batch_size=50, max_workers=4):
    batches = list(batch_iter(servers, batch_size))
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(bulk_ops.bulk_register_servers, batch, False)
            for batch in batches
        ]

        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"Batch failed: {e}")

    # Aggregate results
    total_succeeded = sum(r['succeeded'] for r in results)
    total_failed = sum(r['failed'] for r in results)

    return {
        'total': total_succeeded + total_failed,
        'succeeded': total_succeeded,
        'failed': total_failed
    }

# 3. Monitor progress
# - Use progress bars for large imports
from tqdm import tqdm

for batch in tqdm(batches, desc="Registering servers"):
    result = bulk_ops.bulk_register_servers(batch, False)

# 4. Rate limiting
# - Respect API rate limits
# - Add delays between batches if needed

import time

for i, batch in enumerate(batches):
    result = bulk_ops.bulk_register_servers(batch, False)

    # Small delay between batches to avoid rate limits
    if i < len(batches) - 1:
        time.sleep(0.1)
    """)


def main():
    """Run all examples."""
    print("=" * 60)
    print("SARK Bulk Operations Examples")
    print("=" * 60)

    print("\nNote: Set environment variables:")
    print("  export SARK_API_URL=https://sark.example.com")
    print("  export SARK_ACCESS_TOKEN=your-jwt-access-token")

    # Example 1: Best-effort registration
    # example_bulk_register_best_effort()

    # Example 2: Transactional registration
    example_bulk_register_transactional()

    # Example 3: Status updates
    # example_bulk_status_update()

    # Example 4: Large-scale import
    example_large_scale_import()

    # Example 5: Error handling
    example_error_handling()

    # Example 6: Performance
    example_performance_considerations()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)

    print("\nTo run live examples, uncomment the calls in main()")


if __name__ == "__main__":
    main()
