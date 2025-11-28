"""Mock OPA server for testing."""

from fastapi import FastAPI

app = FastAPI()


@app.post("/v1/data/mcp/gateway/allow")
async def evaluate_gateway_policy(request: dict):
    """Mock policy evaluation."""
    user_role = request["input"]["user"]["role"]
    action = request["input"]["action"]

    # Simple mock logic
    allow = user_role in ["admin", "developer"]

    return {
        "result": {
            "allow": allow,
            "reason": f"{action} allowed for {user_role}" if allow else "Denied",
            "filtered_parameters": request["input"].get("parameters", {}),
        }
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
