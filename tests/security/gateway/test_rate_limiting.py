"""Rate Limiting Security Tests."""

import pytest
import asyncio

pytestmark = pytest.mark.security


async def test_rate_limit_enforcement(app_client, mock_user_token):
    """Test basic rate limit enforcement."""

    # Make many rapid requests
    tasks = [
        app_client.post(
            "/api/v1/gateway/authorize",
            json={"action": "gateway:tool:invoke", "tool_name": f"tool-{i}"},
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )
        for i in range(200)
    ]

    responses = await asyncio.gather(*tasks)
    status_codes = [r.status_code for r in responses]

    # Should see rate limiting (429)
    rate_limited = sum(1 for code in status_codes if code == 429)
    assert rate_limited > 0, "Expected some requests to be rate limited"


async def test_rate_limit_bypass_attempts(app_client, mock_user_token):
    """Test rate limit bypass attempts."""

    # Try different bypass techniques
    bypass_attempts = [
        {"X-Forwarded-For": "different.ip.address"},
        {"X-Real-IP": "another.ip.address"},
        {"Via": "proxy"},
    ]

    for headers in bypass_attempts:
        tasks = [
            app_client.post(
                "/api/v1/gateway/authorize",
                json={"action": "gateway:tool:invoke", "tool_name": "test"},
                headers={**{"Authorization": f"Bearer {mock_user_token}"}, **headers},
            )
            for _ in range(100)
        ]

        responses = await asyncio.gather(*tasks)
        # Should still be rate limited
        assert any(r.status_code == 429 for r in responses)


async def test_distributed_rate_limiting(app_client):
    """Test rate limiting works across multiple instances."""

    # Simulate requests from multiple tokens/users
    tokens = [f"token_{i}" for i in range(5)]

    all_responses = []
    for token in tokens:
        tasks = [
            app_client.post(
                "/api/v1/gateway/authorize",
                json={"action": "gateway:tool:invoke", "tool_name": "test"},
                headers={"Authorization": f"Bearer {token}"},
            )
            for _ in range(50)
        ]
        responses = await asyncio.gather(*tasks)
        all_responses.extend(responses)

    # Each user should be rate limited independently
    assert any(r.status_code == 429 for r in all_responses)


async def test_rate_limit_recovery(app_client, mock_user_token):
    """Test rate limit recovery after cool-down period."""

    # Exceed rate limit
    tasks = [
        app_client.post(
            "/api/v1/gateway/authorize",
            json={"action": "gateway:tool:invoke", "tool_name": "test"},
            headers={"Authorization": f"Bearer {mock_user_token}"},
        )
        for _ in range(100)
    ]
    responses1 = await asyncio.gather(*tasks)
    assert any(r.status_code == 429 for r in responses1)

    # Wait for cool-down
    await asyncio.sleep(10)

    # Should be able to make requests again
    response2 = await app_client.post(
        "/api/v1/gateway/authorize",
        json={"action": "gateway:tool:invoke", "tool_name": "test"},
        headers={"Authorization": f"Bearer {mock_user_token}"},
    )
    assert response2.status_code in [200, 401, 403]
