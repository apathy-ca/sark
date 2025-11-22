#!/usr/bin/env python3
"""
Search and Filter Example for SARK

This example demonstrates:
- Full-text search on servers
- Multiple filter combinations
- Cursor-based pagination
- Advanced filtering techniques

Usage:
    python search_and_filter.py
"""

import os
from typing import Dict, List, Optional

import requests


class SARKSearchClient:
    """Handle search and filter operations for SARK."""

    def __init__(self, base_url: str, access_token: str):
        """Initialize search client.

        Args:
            base_url: SARK API base URL
            access_token: JWT access token
        """
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    def list_servers(
        self,
        limit: int = 50,
        cursor: Optional[str] = None,
        sort_order: str = "desc",
        status: Optional[str] = None,
        sensitivity: Optional[str] = None,
        team_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        tags: Optional[str] = None,
        match_all_tags: bool = False,
        search: Optional[str] = None,
        include_total: bool = False,
    ) -> Dict:
        """List servers with filters and pagination.

        Args:
            limit: Items per page (1-200)
            cursor: Pagination cursor
            sort_order: Sort order (asc/desc)
            status: Filter by status (comma-separated)
            sensitivity: Filter by sensitivity level (comma-separated)
            team_id: Filter by team UUID
            owner_id: Filter by owner UUID
            tags: Filter by tags (comma-separated)
            match_all_tags: Match all tags (AND) vs any tag (OR)
            search: Full-text search on name/description
            include_total: Include total count (expensive)

        Returns:
            Paginated server list
        """
        params = {"limit": limit, "sort_order": sort_order, "include_total": include_total}

        if cursor:
            params["cursor"] = cursor
        if status:
            params["status"] = status
        if sensitivity:
            params["sensitivity"] = sensitivity
        if team_id:
            params["team_id"] = team_id
        if owner_id:
            params["owner_id"] = owner_id
        if tags:
            params["tags"] = tags
            params["match_all_tags"] = match_all_tags
        if search:
            params["search"] = search

        response = requests.get(f"{self.base_url}/api/v1/servers", headers=self.headers, params=params)

        response.raise_for_status()
        return response.json()

    def search_all_pages(
        self,
        limit: int = 50,
        max_pages: Optional[int] = None,
        **filters,
    ) -> List[Dict]:
        """Search all pages and return all results.

        Args:
            limit: Items per page
            max_pages: Maximum pages to fetch (None for all)
            **filters: Filter parameters

        Returns:
            List of all servers matching criteria
        """
        all_servers = []
        cursor = None
        page = 0

        while True:
            page += 1
            if max_pages and page > max_pages:
                break

            result = self.list_servers(limit=limit, cursor=cursor, **filters)

            all_servers.extend(result["items"])

            if not result["has_more"]:
                break

            cursor = result["next_cursor"]

        return all_servers


def example_basic_search():
    """Example: Basic full-text search."""
    print("\n" + "=" * 60)
    print("Example 1: Basic Full-Text Search")
    print("=" * 60)

    base_url = os.getenv("SARK_API_URL", "https://sark.example.com")
    access_token = os.getenv("SARK_ACCESS_TOKEN", "your-jwt-token")

    client = SARKSearchClient(base_url, access_token)

    print("\nSearching for 'analytics' servers...")

    try:
        result = client.list_servers(search="analytics", limit=20)

        print(f"\n✓ Found {len(result['items'])} servers")
        print(f"  Has more: {result['has_more']}")

        for server in result["items"]:
            print(f"  - {server['name']} ({server['sensitivity_level']})")

    except requests.exceptions.RequestException as e:
        print(f"\n✗ Search failed: {e}")


def example_status_filter():
    """Example: Filter by server status."""
    print("\n" + "=" * 60)
    print("Example 2: Filter by Status")
    print("=" * 60)

    print("""
# Filter servers by status

# Single status
result = client.list_servers(status='active')

# Multiple statuses (comma-separated)
result = client.list_servers(status='active,registered')

# Valid statuses:
# - registered: Server registered but not yet active
# - active: Server is active and healthy
# - inactive: Server temporarily inactive
# - unhealthy: Server failed health checks
# - decommissioned: Server permanently decommissioned

Example output:
    ✓ Found 45 active servers
      - analytics-server-1 (active)
      - ml-server-1 (active)
      - dashboard-server-1 (active)
    """)


def example_sensitivity_filter():
    """Example: Filter by sensitivity level."""
    print("\n" + "=" * 60)
    print("Example 3: Filter by Sensitivity Level")
    print("=" * 60)

    base_url = os.getenv("SARK_API_URL", "https://sark.example.com")
    access_token = os.getenv("SARK_ACCESS_TOKEN", "your-jwt-token")

    client = SARKSearchClient(base_url, access_token)

    print("\nFinding high-risk servers (high + critical)...")

    try:
        result = client.list_servers(sensitivity="high,critical", limit=50)

        print(f"\n✓ Found {len(result['items'])} high-risk servers")

        # Group by sensitivity
        by_sensitivity = {"high": [], "critical": []}
        for server in result["items"]:
            level = server["sensitivity_level"]
            if level in by_sensitivity:
                by_sensitivity[level].append(server["name"])

        print(f"\n  High: {len(by_sensitivity['high'])} servers")
        for name in by_sensitivity["high"][:5]:
            print(f"    - {name}")

        print(f"\n  Critical: {len(by_sensitivity['critical'])} servers")
        for name in by_sensitivity["critical"][:5]:
            print(f"    - {name}")

    except requests.exceptions.RequestException as e:
        print(f"\n✗ Search failed: {e}")


def example_combined_filters():
    """Example: Combine multiple filters."""
    print("\n" + "=" * 60)
    print("Example 4: Combined Filters")
    print("=" * 60)

    print("""
# Combine multiple filters (AND logic)

# Active servers with high sensitivity
result = client.list_servers(
    status='active',
    sensitivity='high,critical'
)

# Active high-sensitivity servers for specific team
result = client.list_servers(
    status='active',
    sensitivity='high,critical',
    team_id='550e8400-e29b-41d4-a716-446655440000'
)

# Search + filters
result = client.list_servers(
    search='analytics',  # Full-text search
    status='active',     # Status filter
    sensitivity='high'   # Sensitivity filter
)

# All production servers (using tags)
result = client.list_servers(
    tags='production,critical',
    match_all_tags=False  # Match ANY tag (OR)
)

# Servers with BOTH tags
result = client.list_servers(
    tags='production,verified',
    match_all_tags=True  # Match ALL tags (AND)
)
    """)


def example_pagination():
    """Example: Cursor-based pagination."""
    print("\n" + "=" * 60)
    print("Example 5: Cursor-Based Pagination")
    print("=" * 60)

    base_url = os.getenv("SARK_API_URL", "https://sark.example.com")
    access_token = os.getenv("SARK_ACCESS_TOKEN", "your-jwt-token")

    client = SARKSearchClient(base_url, access_token)

    print("\nFetching servers with pagination...")

    try:
        cursor = None
        page = 1
        total_servers = 0

        while True:
            print(f"\nPage {page}:")

            result = client.list_servers(limit=10, cursor=cursor, sort_order="desc")

            print(f"  Items: {len(result['items'])}")
            print(f"  Has more: {result['has_more']}")

            total_servers += len(result["items"])

            # Display first few servers
            for i, server in enumerate(result["items"][:3], 1):
                print(f"    {i}. {server['name']}")

            if not result["has_more"]:
                break

            cursor = result["next_cursor"]
            page += 1

            # Limit to 3 pages for example
            if page > 3:
                print("\n  (Stopping after 3 pages for demo)")
                break

        print(f"\n✓ Total servers fetched: {total_servers}")

    except requests.exceptions.RequestException as e:
        print(f"\n✗ Pagination failed: {e}")


def example_fetch_all():
    """Example: Fetch all matching servers."""
    print("\n" + "=" * 60)
    print("Example 6: Fetch All Matching Servers")
    print("=" * 60)

    base_url = os.getenv("SARK_API_URL", "https://sark.example.com")
    access_token = os.getenv("SARK_ACCESS_TOKEN", "your-jwt-token")

    client = SARKSearchClient(base_url, access_token)

    print("\nFetching all active servers...")

    try:
        # Fetch all pages
        servers = client.search_all_pages(limit=50, status="active")

        print(f"\n✓ Found {len(servers)} active servers")

        # Analyze results
        by_sensitivity = {}
        for server in servers:
            level = server["sensitivity_level"]
            by_sensitivity[level] = by_sensitivity.get(level, 0) + 1

        print(f"\n  By sensitivity:")
        for level, count in sorted(by_sensitivity.items()):
            print(f"    {level}: {count}")

    except requests.exceptions.RequestException as e:
        print(f"\n✗ Fetch failed: {e}")


def example_advanced_queries():
    """Example: Advanced query patterns."""
    print("\n" + "=" * 60)
    print("Example 7: Advanced Query Patterns")
    print("=" * 60)

    print("""
# 1. Find all unhealthy production servers
result = client.list_servers(
    status='unhealthy',
    tags='production',
    sort_order='desc'  # Most recent first
)

# 2. Find servers owned by specific user
result = client.list_servers(
    owner_id='550e8400-e29b-41d4-a716-446655440000',
    status='active'
)

# 3. Search for ML/AI servers with high sensitivity
result = client.list_servers(
    search='ml ai machine learning',
    sensitivity='high,critical',
    status='active'
)

# 4. Find all servers for a team
result = client.list_servers(
    team_id='550e8400-e29b-41d4-a716-446655440000',
    include_total=True  # Include total count
)
print(f"Team has {result['total']} servers")

# 5. Get oldest servers (for audit)
result = client.list_servers(
    limit=20,
    sort_order='asc'  # Oldest first
)

# 6. Find servers with multiple tags (AND logic)
result = client.list_servers(
    tags='production,verified,critical',
    match_all_tags=True  # Must have ALL tags
)

# 7. Find servers with any tag (OR logic)
result = client.list_servers(
    tags='production,staging,development',
    match_all_tags=False  # Must have AT LEAST ONE tag
)
    """)


def example_performance_tips():
    """Example: Performance optimization tips."""
    print("\n" + "=" * 60)
    print("Example 8: Performance Tips")
    print("=" * 60)

    print("""
# Performance optimization tips

# 1. Use appropriate page sizes
# - Small datasets: limit=20-50
# - Large datasets: limit=100-200 (max)
result = client.list_servers(limit=100)

# 2. Avoid include_total for large datasets
# - Computing total count is expensive
# - Only use when you need the exact count
result = client.list_servers(
    include_total=False  # Default, faster
)

# 3. Use specific filters to reduce result set
# Better: Narrow filters
result = client.list_servers(
    status='active',
    sensitivity='high',
    team_id='550e8400-...'
)

# Worse: Too broad
result = client.search_all_pages()  # Fetches everything

# 4. Cache results when appropriate
import time
from functools import lru_cache

@lru_cache(maxsize=128)
def get_servers_cached(status, sensitivity):
    return tuple(client.search_all_pages(
        status=status,
        sensitivity=sensitivity
    ))

# Cache is valid for 5 minutes
servers = get_servers_cached('active', 'high')

# 5. Use cursor-based pagination efficiently
# Process results as you fetch them, don't load all in memory
def process_servers_streaming(processor_func):
    cursor = None

    while True:
        result = client.list_servers(limit=50, cursor=cursor)

        # Process this batch
        for server in result['items']:
            processor_func(server)

        if not result['has_more']:
            break

        cursor = result['next_cursor']

# Example: Export to CSV
def export_to_csv(server):
    print(f"{server['name']},{server['status']},{server['sensitivity_level']}")

process_servers_streaming(export_to_csv)
    """)


def example_error_handling():
    """Example: Error handling for search operations."""
    print("\n" + "=" * 60)
    print("Example 9: Error Handling")
    print("=" * 60)

    print("""
# Error handling for search operations

import requests

try:
    result = client.list_servers(
        search='analytics',
        status='active'
    )

except requests.exceptions.HTTPError as e:
    if e.response.status_code == 400:
        # Invalid parameters
        print(f"Invalid query parameters: {e.response.json()}")

    elif e.response.status_code == 401:
        # Authentication failed
        print("Authentication failed - check your access token")

    elif e.response.status_code == 429:
        # Rate limit exceeded
        retry_after = e.response.headers.get('Retry-After', 60)
        print(f"Rate limited - retry after {retry_after}s")
        time.sleep(int(retry_after))
        # Retry request

    elif e.response.status_code >= 500:
        # Server error
        print(f"Server error: {e}")
        # Implement retry with backoff

    else:
        print(f"HTTP error: {e}")

except requests.exceptions.ConnectionError:
    print("Connection error - check network and API URL")

except requests.exceptions.Timeout:
    print("Request timeout - server may be slow")

except Exception as e:
    print(f"Unexpected error: {e}")
    """)


def main():
    """Run all examples."""
    print("=" * 60)
    print("SARK Search and Filter Examples")
    print("=" * 60)

    print("\nNote: Set environment variables:")
    print("  export SARK_API_URL=https://sark.example.com")
    print("  export SARK_ACCESS_TOKEN=your-jwt-access-token")

    # Example 1: Basic search
    # example_basic_search()

    # Example 2: Status filter
    example_status_filter()

    # Example 3: Sensitivity filter
    # example_sensitivity_filter()

    # Example 4: Combined filters
    example_combined_filters()

    # Example 5: Pagination
    # example_pagination()

    # Example 6: Fetch all
    # example_fetch_all()

    # Example 7: Advanced queries
    example_advanced_queries()

    # Example 8: Performance tips
    example_performance_tips()

    # Example 9: Error handling
    example_error_handling()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)

    print("\nTo run live examples, uncomment the calls in main()")


if __name__ == "__main__":
    main()
