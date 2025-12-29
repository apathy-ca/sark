"""
HTTP Adapter Real-World Example - GitHub API

This example demonstrates integrating a real-world API (GitHub) with SARK.

Shows:
- Bearer token authentication
- Rate limiting (GitHub has strict rate limits)
- Real API operations (list repos, get user info)
- Error handling

Note: You'll need a GitHub personal access token to run this.
Create one at: https://github.com/settings/tokens

Version: 2.0.0
Engineer: ENGINEER-2
"""

import asyncio
from datetime import datetime
import os

from sark.adapters.http import HTTPAdapter
from sark.models.base import InvocationRequest, ResourceSchema


async def main():
    """GitHub API integration example."""

    print("=" * 60)
    print("HTTP Adapter - GitHub API Example")
    print("=" * 60)

    # Get GitHub token from environment
    github_token = os.getenv("GITHUB_TOKEN")

    if not github_token:
        print("\n⚠ No GitHub token found!")
        print("  Set GITHUB_TOKEN environment variable:")
        print("  export GITHUB_TOKEN='your_token_here'")
        print("\n  Or run with:")
        print("  GITHUB_TOKEN='your_token' python github_api_example.py")
        print("\n  Using demo mode (will fail for authenticated endpoints)...")
        github_token = "demo_token_will_fail"

    # Step 1: Create HTTP adapter for GitHub API
    print("\n1. Creating HTTP adapter for GitHub API...")
    adapter = HTTPAdapter(
        base_url="https://api.github.com",
        auth_config={
            "type": "bearer",
            "token": github_token
        },
        rate_limit=5.0,  # GitHub allows ~5000/hour = ~1.4/sec, we'll be conservative
        timeout=15.0,
    )

    print(f"   ✓ Adapter created: {adapter}")
    print("   - Rate limit: 5 requests/second")
    print("   - Authentication: Bearer token")

    # Step 2: Create resource for GitHub API
    print("\n2. Creating GitHub API resource...")

    resource = ResourceSchema(
        id="http:github_api",
        name="GitHub REST API",
        protocol="http",
        endpoint="https://api.github.com",
        sensitivity_level="medium",  # GitHub APIs can access private data
        metadata={
            "api_version": "v3",
            "description": "GitHub REST API v3",
            "documentation": "https://docs.github.com/rest",
        },
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    print(f"   ✓ Resource created: {resource.name}")
    print(f"   - Sensitivity: {resource.sensitivity_level}")

    # Step 3: Check API health
    print("\n3. Checking GitHub API health...")
    is_healthy = await adapter.health_check(resource)
    print(f"   {'✓' if is_healthy else '✗'} API is {'healthy' if is_healthy else 'unhealthy'}")

    # Step 4: Get authenticated user info
    print("\n4. Getting authenticated user information...")

    user_request = InvocationRequest(
        capability_id=f"{resource.id}:get_user",
        principal_id="example-user",
        arguments={},
        context={
            "capability_metadata": {
                "http_method": "GET",
                "http_path": "/user"
            }
        }
    )

    user_result = await adapter.invoke(user_request)

    if user_result.success:
        user_data = user_result.result
        print("   ✓ Request successful!")
        print(f"   - Duration: {user_result.duration_ms:.2f}ms")
        print(f"   - Username: {user_data.get('login', 'N/A')}")
        print(f"   - Name: {user_data.get('name', 'N/A')}")
        print(f"   - Public repos: {user_data.get('public_repos', 'N/A')}")
        print(f"   - Followers: {user_data.get('followers', 'N/A')}")
    else:
        print(f"   ✗ Request failed: {user_result.error}")
        if "401" in str(user_result.error):
            print("   Hint: Invalid or missing GitHub token")

    # Step 5: List public repositories for a user
    print("\n5. Listing repositories for 'octocat' user...")

    repos_request = InvocationRequest(
        capability_id=f"{resource.id}:list_user_repos",
        principal_id="example-user",
        arguments={
            "username": "octocat",
            "query_per_page": "5",  # Limit to 5 repos
            "query_sort": "updated",
        },
        context={
            "capability_metadata": {
                "http_method": "GET",
                "http_path": "/users/octocat/repos"
            }
        }
    )

    repos_result = await adapter.invoke(repos_request)

    if repos_result.success:
        repos = repos_result.result
        print(f"   ✓ Found {len(repos)} repositories")
        print(f"   - Duration: {repos_result.duration_ms:.2f}ms")

        for i, repo in enumerate(repos[:5], 1):
            print(f"\n   [{i}] {repo.get('name', 'N/A')}")
            print(f"       Description: {repo.get('description', 'No description')}")
            print(f"       Stars: ⭐ {repo.get('stargazers_count', 0)}")
            print(f"       Forks: 🍴 {repo.get('forks_count', 0)}")
            print(f"       Language: {repo.get('language', 'N/A')}")
            print(f"       URL: {repo.get('html_url', 'N/A')}")
    else:
        print(f"   ✗ Request failed: {repos_result.error}")

    # Step 6: Get repository information
    print("\n6. Getting information for 'octocat/Hello-World' repository...")

    repo_request = InvocationRequest(
        capability_id=f"{resource.id}:get_repo",
        principal_id="example-user",
        arguments={
            "owner": "octocat",
            "repo": "Hello-World",
        },
        context={
            "capability_metadata": {
                "http_method": "GET",
                "http_path": "/repos/octocat/Hello-World"
            }
        }
    )

    repo_result = await adapter.invoke(repo_request)

    if repo_result.success:
        repo_data = repo_result.result
        print("   ✓ Repository found!")
        print(f"   - Duration: {repo_result.duration_ms:.2f}ms")
        print(f"   - Full name: {repo_data.get('full_name', 'N/A')}")
        print(f"   - Description: {repo_data.get('description', 'N/A')}")
        print(f"   - Stars: ⭐ {repo_data.get('stargazers_count', 0)}")
        print(f"   - Open issues: {repo_data.get('open_issues_count', 0)}")
        print(f"   - Created: {repo_data.get('created_at', 'N/A')}")
        print(f"   - Last updated: {repo_data.get('updated_at', 'N/A')}")
    else:
        print(f"   ✗ Request failed: {repo_result.error}")

    # Step 7: Demonstrate rate limiting
    print("\n7. Demonstrating rate limiting...")
    print("   Making 10 rapid requests to show rate limiter in action...")

    start_time = asyncio.get_event_loop().time()

    for i in range(10):
        ping_request = InvocationRequest(
            capability_id=f"{resource.id}:get_octocat",
            principal_id="example-user",
            arguments={},
            context={
                "capability_metadata": {
                    "http_method": "GET",
                    "http_path": "/octocat"
                }
            }
        )

        result = await adapter.invoke(ping_request)
        print(f"   [{i+1}/10] {'✓' if result.success else '✗'}")

    end_time = asyncio.get_event_loop().time()
    duration = end_time - start_time

    print(f"\n   ✓ Completed 10 requests in {duration:.2f}s")
    print("   Expected: ~2s at 5 req/s")
    print(f"   Rate limiting working: {'✓' if duration >= 1.5 else '✗'}")

    # Step 8: Check rate limit status (GitHub provides this)
    print("\n8. Checking GitHub API rate limit status...")

    rate_limit_request = InvocationRequest(
        capability_id=f"{resource.id}:get_rate_limit",
        principal_id="example-user",
        arguments={},
        context={
            "capability_metadata": {
                "http_method": "GET",
                "http_path": "/rate_limit"
            }
        }
    )

    rate_limit_result = await adapter.invoke(rate_limit_request)

    if rate_limit_result.success:
        rate_data = rate_limit_result.result
        core = rate_data.get("resources", {}).get("core", {})

        print("   ✓ Rate limit info retrieved")
        print(f"   - Limit: {core.get('limit', 'N/A')} requests/hour")
        print(f"   - Remaining: {core.get('remaining', 'N/A')}")
        print(f"   - Resets at: {core.get('reset', 'N/A')}")
    else:
        print(f"   ⚠ Could not get rate limit info: {rate_limit_result.error}")

    # Step 9: Cleanup
    print("\n9. Cleaning up...")
    await adapter.on_resource_unregistered(resource)
    print("   ✓ Adapter cleaned up")

    print("\n" + "=" * 60)
    print("GitHub API integration completed!")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("1. SARK can govern real-world APIs like GitHub")
    print("2. Bearer token authentication is seamlessly handled")
    print("3. Rate limiting protects both client and server")
    print("4. All API calls are tracked and governed")
    print("5. Easy to integrate any REST API with minimal code")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
