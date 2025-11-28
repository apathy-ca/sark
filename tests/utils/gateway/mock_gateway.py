"""Mock MCP Gateway API for testing."""

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

app = FastAPI()

# Mock server data
MOCK_SERVERS = [
    {
        "server_id": "srv_1",
        "server_name": "test-server-1",
        "server_url": "http://test1:8080",
        "sensitivity_level": "medium",
        "health_status": "healthy",
        "tools_count": 5
    },
    {
        "server_id": "srv_2",
        "server_name": "test-server-2",
        "server_url": "http://test2:8080",
        "sensitivity_level": "high",
        "health_status": "healthy",
        "tools_count": 10
    }
]


@app.get("/api/servers")
async def list_servers():
    return MOCK_SERVERS


@app.get("/api/servers/{server_name}")
async def get_server(server_name: str):
    server = next((s for s in MOCK_SERVERS if s["server_name"] == server_name), None)
    if not server:
        raise HTTPException(404, "Server not found")
    return server


@app.get("/health")
async def health():
    return {"status": "ok"}


# Test client
mock_gateway_client = TestClient(app)
