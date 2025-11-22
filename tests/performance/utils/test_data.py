"""Test data generators for performance tests."""

import random
import uuid
from typing import Any

from faker import Faker

fake = Faker()


class TestDataGenerator:
    """Generate realistic test data for load testing."""

    @staticmethod
    def generate_server_registration() -> dict[str, Any]:
        """Generate realistic server registration data."""
        transport = random.choice(["http", "stdio", "sse"])

        # Generate tools based on random count
        tool_count = random.randint(1, 10)
        tools = [TestDataGenerator.generate_tool() for _ in range(tool_count)]

        base = {
            "name": f"mcp-server-{fake.slug()}",
            "transport": transport,
            "version": "2025-06-18",
            "capabilities": random.sample(
                ["tools", "prompts", "resources", "sampling"],
                k=random.randint(1, 4)
            ),
            "tools": tools,
            "description": fake.sentence(),
            "sensitivity_level": random.choice(["low", "medium", "high", "critical"]),
            "metadata": {
                "environment": random.choice(["dev", "staging", "production"]),
                "team": fake.company(),
                "owner": fake.email(),
            }
        }

        # Add transport-specific fields
        if transport == "http":
            base["endpoint"] = f"http://{fake.ipv4()}:{random.randint(8000, 9000)}"
        elif transport == "stdio":
            base["command"] = f"/usr/local/bin/{fake.slug()}"

        return base

    @staticmethod
    def generate_tool() -> dict[str, Any]:
        """Generate a realistic tool definition."""
        return {
            "name": f"tool_{fake.word()}_{fake.word()}",
            "description": fake.sentence(),
            "parameters": {
                "type": "object",
                "properties": {
                    fake.word(): {"type": "string", "description": fake.sentence()},
                    fake.word(): {"type": "number", "description": fake.sentence()},
                    fake.word(): {"type": "boolean", "description": fake.sentence()},
                },
                "required": [fake.word()]
            },
            "sensitivity_level": random.choice(["low", "medium", "high", "critical"]),
            "requires_approval": random.choice([True, False]),
        }

    @staticmethod
    def generate_policy_evaluation(server_id: str | None = None) -> dict[str, Any]:
        """Generate policy evaluation request."""
        actions = [
            "tool:invoke",
            "tool:read",
            "server:read",
            "server:update",
            "server:delete",
            "policy:evaluate",
        ]

        return {
            "action": random.choice(actions),
            "tool": f"tool_{fake.word()}" if random.random() > 0.3 else None,
            "server_id": server_id or str(uuid.uuid4()),
            "parameters": {
                "arg1": fake.word(),
                "arg2": random.randint(1, 100),
                "arg3": fake.boolean(),
            }
        }

    @staticmethod
    def generate_api_key_request() -> dict[str, Any]:
        """Generate API key creation request."""
        scopes = [
            "server:read",
            "server:write",
            "server:delete",
            "tool:invoke",
            "policy:evaluate",
            "apikey:read",
            "apikey:write",
        ]

        return {
            "name": f"api-key-{fake.slug()}",
            "description": fake.sentence(),
            "scopes": random.sample(scopes, k=random.randint(1, len(scopes))),
            "rate_limit": random.choice([100, 500, 1000, 5000, 10000]),
            "expires_in_days": random.choice([7, 30, 90, 365, None]),
            "environment": random.choice(["live", "test", "dev"]),
        }

    @staticmethod
    def generate_bulk_servers(count: int = 10) -> list[dict[str, Any]]:
        """Generate multiple server registration requests."""
        return [TestDataGenerator.generate_server_registration() for _ in range(count)]

    @staticmethod
    def generate_search_query() -> dict[str, str]:
        """Generate realistic search query parameters."""
        return {
            "q": fake.word(),
            "status": random.choice(["active", "inactive", "pending", ""]),
            "sensitivity_level": random.choice(["low", "medium", "high", "critical", ""]),
            "limit": str(random.choice([10, 20, 50, 100])),
            "offset": str(random.randint(0, 100)),
        }
