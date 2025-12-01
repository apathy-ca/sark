# Multi-Protocol Orchestration

**Tutorial Duration:** 45-60 minutes
**Skill Level:** Intermediate to Advanced
**Prerequisites:** Completed QUICKSTART.md, understanding of async Python, workflow concepts

---

## Introduction

SARK v2.0's true power emerges when orchestrating workflows that span **multiple protocols**. This tutorial teaches you to build complex workflows that seamlessly combine MCP tools, REST APIs, and gRPC services under unified governance.

### What You'll Build

By the end of this tutorial, you'll have created a **CI/CD pipeline automation workflow** that:

1. **Fetches code** from GitHub (HTTP/REST)
2. **Analyzes code** using an MCP code analysis tool
3. **Runs tests** via a gRPC test runner service
4. **Posts results** to Slack (HTTP/REST)
5. **Stores metrics** in a database (gRPC)

All governed by a single SARK policy with complete audit trail!

---

## Table of Contents

1. [Understanding Multi-Protocol Workflows](#understanding-multi-protocol-workflows)
2. [Architecture Overview](#architecture-overview)
3. [Setup: Registering Resources](#setup-registering-resources)
4. [Building the Workflow](#building-the-workflow)
5. [Implementing Policies](#implementing-policies)
6. [Error Handling Across Protocols](#error-handling-across-protocols)
7. [Monitoring and Auditing](#monitoring-and-auditing)
8. [Advanced Patterns](#advanced-patterns)

---

## Understanding Multi-Protocol Workflows

### Why Multi-Protocol?

Real-world systems use multiple protocols:

| Protocol | Best For | Example Use Case |
|----------|----------|------------------|
| **MCP** | AI tools, local utilities | Code analysis, file operations |
| **HTTP/REST** | Web APIs, SaaS services | GitHub, Slack, Stripe |
| **gRPC** | High-performance RPC | Microservices, real-time data |
| **Custom** | Legacy systems | Proprietary APIs, databases |

SARK v2.0 lets you:
- **Govern all protocols** with one policy engine
- **Audit all calls** in one unified log
- **Orchestrate workflows** spanning multiple protocols
- **Apply consistent security** regardless of protocol

### Workflow Pattern

```
┌──────────────────────────────────────────────────┐
│            SARK Policy & Audit Layer             │
└──────────────────────────────────────────────────┘
                        ↓
    ┌───────────────────┼───────────────────┐
    │                   │                   │
┌────────┐        ┌──────────┐        ┌─────────┐
│  HTTP  │───────→│   MCP    │───────→│  gRPC   │
│GitHub  │        │ Analyzer │        │ Tests   │
└────────┘        └──────────┘        └─────────┘
    │                   │                   │
    └───────────────────┴───────────────────┘
                        ↓
                  ┌──────────┐
                  │   HTTP   │
                  │  Slack   │
                  └──────────┘
```

---

## Architecture Overview

Our CI/CD workflow involves:

```python
# Workflow steps
1. GitHub (HTTP)      → Fetch latest commit
2. Code Analyzer (MCP) → Analyze code quality
3. Test Runner (gRPC)  → Execute tests
4. Metrics DB (gRPC)   → Store results
5. Slack (HTTP)        → Notify team
```

Each step is:
- **Governed** by SARK policies
- **Logged** to the audit trail
- **Resilient** with error handling
- **Protocol-agnostic** in the orchestration layer

---

## Setup: Registering Resources

### 1. Register GitHub API (HTTP)

```bash
curl -X POST http://localhost:8000/api/v2/resources \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "http",
    "discovery_config": {
      "base_url": "https://api.github.com",
      "openapi_spec_url": "https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json",
      "auth": {
        "type": "bearer",
        "token": "ghp_YOUR_GITHUB_TOKEN"
      }
    },
    "name": "GitHub API",
    "sensitivity_level": "medium"
  }'
```

**Response:** Resource ID: `http-github-api-123`

### 2. Register Code Analyzer (MCP)

```bash
curl -X POST http://localhost:8000/api/v2/resources \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "mcp",
    "discovery_config": {
      "transport": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-code-analyzer"],
      "env": {}
    },
    "name": "Code Analyzer",
    "sensitivity_level": "low"
  }'
```

**Response:** Resource ID: `mcp-code-analyzer-456`

### 3. Register Test Runner (gRPC)

```bash
curl -X POST http://localhost:8000/api/v2/resources \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "grpc",
    "discovery_config": {
      "endpoint": "testrunner.company.com:50051",
      "reflection": true,
      "tls": true,
      "credentials": {
        "type": "mtls",
        "cert_path": "/path/to/client.crt",
        "key_path": "/path/to/client.key"
      }
    },
    "name": "Test Runner Service",
    "sensitivity_level": "medium"
  }'
```

**Response:** Resource ID: `grpc-testrunner-789`

### 4. Register Metrics Database (gRPC)

```bash
curl -X POST http://localhost:8000/api/v2/resources \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "grpc",
    "discovery_config": {
      "endpoint": "metrics.company.com:50052",
      "reflection": true,
      "tls": true
    },
    "name": "Metrics Service",
    "sensitivity_level": "high"
  }'
```

**Response:** Resource ID: `grpc-metrics-101`

### 5. Register Slack (HTTP)

```bash
curl -X POST http://localhost:8000/api/v2/resources \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "http",
    "discovery_config": {
      "base_url": "https://slack.com/api",
      "auth": {
        "type": "bearer",
        "token": "xoxb-YOUR-SLACK-BOT-TOKEN"
      }
    },
    "name": "Slack API",
    "sensitivity_level": "medium"
  }'
```

**Response:** Resource ID: `http-slack-102`

---

## Building the Workflow

### Workflow Implementation

Create `workflows/ci_cd_pipeline.py`:

```python
"""
Multi-protocol CI/CD pipeline orchestration.

Demonstrates SARK v2.0's ability to govern workflows spanning
MCP, HTTP, and gRPC protocols with unified policy enforcement.
"""

import asyncio
from typing import Any, Dict, List, Optional
import structlog
from datetime import datetime

from sark.client import SARKClient
from sark.models.base import InvocationRequest

logger = structlog.get_logger(__name__)


class CICDPipeline:
    """
    CI/CD pipeline orchestrator using SARK multi-protocol governance.

    Workflow:
    1. Fetch code from GitHub (HTTP)
    2. Analyze code quality (MCP)
    3. Run tests (gRPC)
    4. Store metrics (gRPC)
    5. Notify team on Slack (HTTP)
    """

    def __init__(self, sark_base_url: str = "http://localhost:8000"):
        """Initialize pipeline with SARK client."""
        self.sark = SARKClient(base_url=sark_base_url)
        self.pipeline_id = None

    async def run_pipeline(
        self,
        repo_owner: str,
        repo_name: str,
        principal_id: str,
        branch: str = "main"
    ) -> Dict[str, Any]:
        """
        Execute full CI/CD pipeline.

        Args:
            repo_owner: GitHub repository owner
            repo_name: Repository name
            principal_id: ID of principal running the pipeline
            branch: Git branch to test

        Returns:
            Pipeline execution results
        """
        self.pipeline_id = f"pipeline-{datetime.utcnow().timestamp()}"

        logger.info(
            "pipeline_started",
            pipeline_id=self.pipeline_id,
            repo=f"{repo_owner}/{repo_name}",
            branch=branch
        )

        results = {
            "pipeline_id": self.pipeline_id,
            "repo": f"{repo_owner}/{repo_name}",
            "branch": branch,
            "steps": []
        }

        try:
            # Step 1: Fetch latest commit from GitHub (HTTP)
            commit_info = await self._fetch_latest_commit(
                repo_owner, repo_name, branch, principal_id
            )
            results["steps"].append({
                "name": "fetch_commit",
                "protocol": "http",
                "success": True,
                "data": commit_info
            })

            # Step 2: Analyze code quality (MCP)
            analysis_results = await self._analyze_code(
                repo_owner, repo_name, commit_info["sha"], principal_id
            )
            results["steps"].append({
                "name": "code_analysis",
                "protocol": "mcp",
                "success": True,
                "data": analysis_results
            })

            # Step 3: Run tests (gRPC)
            test_results = await self._run_tests(
                repo_owner, repo_name, commit_info["sha"], principal_id
            )
            results["steps"].append({
                "name": "run_tests",
                "protocol": "grpc",
                "success": True,
                "data": test_results
            })

            # Step 4: Store metrics (gRPC)
            await self._store_metrics(
                {
                    "pipeline_id": self.pipeline_id,
                    "commit_sha": commit_info["sha"],
                    "test_results": test_results,
                    "code_quality": analysis_results
                },
                principal_id
            )
            results["steps"].append({
                "name": "store_metrics",
                "protocol": "grpc",
                "success": True
            })

            # Step 5: Notify on Slack (HTTP)
            await self._notify_slack(
                repo_owner,
                repo_name,
                commit_info,
                test_results,
                analysis_results,
                principal_id
            )
            results["steps"].append({
                "name": "slack_notification",
                "protocol": "http",
                "success": True
            })

            results["overall_success"] = True
            logger.info("pipeline_completed", pipeline_id=self.pipeline_id)

        except Exception as e:
            logger.error(
                "pipeline_failed",
                pipeline_id=self.pipeline_id,
                error=str(e),
                exc_info=True
            )
            results["overall_success"] = False
            results["error"] = str(e)

        return results

    async def _fetch_latest_commit(
        self,
        owner: str,
        repo: str,
        branch: str,
        principal_id: str
    ) -> Dict[str, Any]:
        """
        Fetch latest commit from GitHub.

        Protocol: HTTP/REST
        Capability: GET /repos/{owner}/{repo}/commits/{branch}
        """
        logger.info("fetching_commit", repo=f"{owner}/{repo}", branch=branch)

        request = InvocationRequest(
            capability_id="GET-/repos/{owner}/{repo}/commits/{branch}",
            principal_id=principal_id,
            arguments={
                "owner": owner,
                "repo": repo,
                "branch": branch
            }
        )

        result = await self.sark.authorize_and_invoke(request)

        if not result.success:
            raise Exception(f"Failed to fetch commit: {result.error}")

        commit_data = result.result
        return {
            "sha": commit_data["sha"],
            "message": commit_data["commit"]["message"],
            "author": commit_data["commit"]["author"]["name"],
            "timestamp": commit_data["commit"]["author"]["date"]
        }

    async def _analyze_code(
        self,
        owner: str,
        repo: str,
        commit_sha: str,
        principal_id: str
    ) -> Dict[str, Any]:
        """
        Analyze code quality using MCP analyzer.

        Protocol: MCP
        Capability: analyze_repository
        """
        logger.info("analyzing_code", commit=commit_sha)

        request = InvocationRequest(
            capability_id="mcp-code-analyzer-analyze_repository",
            principal_id=principal_id,
            arguments={
                "repository": f"https://github.com/{owner}/{repo}",
                "commit_sha": commit_sha,
                "checks": [
                    "complexity",
                    "security",
                    "test_coverage",
                    "documentation"
                ]
            }
        )

        result = await self.sark.authorize_and_invoke(request)

        if not result.success:
            raise Exception(f"Code analysis failed: {result.error}")

        return result.result

    async def _run_tests(
        self,
        owner: str,
        repo: str,
        commit_sha: str,
        principal_id: str
    ) -> Dict[str, Any]:
        """
        Run tests via gRPC test runner.

        Protocol: gRPC
        Service: TestRunner
        Method: RunTests
        """
        logger.info("running_tests", commit=commit_sha)

        request = InvocationRequest(
            capability_id="TestRunner.RunTests",
            principal_id=principal_id,
            arguments={
                "repository": f"{owner}/{repo}",
                "commit_sha": commit_sha,
                "test_suite": "all",
                "timeout": 600
            }
        )

        result = await self.sark.authorize_and_invoke(request)

        if not result.success:
            raise Exception(f"Test execution failed: {result.error}")

        return result.result

    async def _store_metrics(
        self,
        metrics: Dict[str, Any],
        principal_id: str
    ) -> None:
        """
        Store pipeline metrics in database.

        Protocol: gRPC
        Service: MetricsService
        Method: StoreMetrics
        """
        logger.info("storing_metrics", pipeline_id=self.pipeline_id)

        request = InvocationRequest(
            capability_id="MetricsService.StoreMetrics",
            principal_id=principal_id,
            arguments={
                "type": "ci_cd_pipeline",
                "timestamp": datetime.utcnow().isoformat(),
                "data": metrics
            }
        )

        result = await self.sark.authorize_and_invoke(request)

        if not result.success:
            # Non-fatal: Log but don't fail pipeline
            logger.warning(
                "metrics_storage_failed",
                error=result.error
            )

    async def _notify_slack(
        self,
        owner: str,
        repo: str,
        commit_info: Dict[str, Any],
        test_results: Dict[str, Any],
        analysis_results: Dict[str, Any],
        principal_id: str
    ) -> None:
        """
        Send pipeline results to Slack.

        Protocol: HTTP
        API: Slack Web API
        Endpoint: chat.postMessage
        """
        logger.info("sending_slack_notification")

        # Build notification message
        passed = test_results.get("passed", 0)
        failed = test_results.get("failed", 0)
        quality_score = analysis_results.get("overall_score", "N/A")

        message = f"""
:rocket: *CI/CD Pipeline Complete*

*Repository:* `{owner}/{repo}`
*Commit:* `{commit_info['sha'][:7]}` - {commit_info['message']}
*Author:* {commit_info['author']}

*Test Results:*
• Passed: {passed}
• Failed: {failed}
• Status: {'✅ All tests passed' if failed == 0 else '❌ Some tests failed'}

*Code Quality Score:* {quality_score}/100

*Pipeline ID:* `{self.pipeline_id}`
"""

        request = InvocationRequest(
            capability_id="http-slack-chat.postMessage",
            principal_id=principal_id,
            arguments={
                "channel": "#ci-cd",
                "text": message,
                "unfurl_links": False
            }
        )

        result = await self.sark.authorize_and_invoke(request)

        if not result.success:
            logger.warning(
                "slack_notification_failed",
                error=result.error
            )


# Helper: SARK client wrapper
class SARKClient:
    """Simple client for SARK API."""

    def __init__(self, base_url: str):
        self.base_url = base_url

    async def authorize_and_invoke(
        self,
        request: InvocationRequest
    ) -> Any:
        """
        Send request to SARK authorization endpoint.

        SARK will:
        1. Validate the request
        2. Evaluate policies
        3. Invoke the capability if authorized
        4. Log to audit trail
        """
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v2/authorize",
                json={
                    "capability_id": request.capability_id,
                    "principal_id": request.principal_id,
                    "arguments": request.arguments
                }
            )
            response.raise_for_status()
            return response.json()


# Usage example
async def main():
    """Run the CI/CD pipeline."""
    pipeline = CICDPipeline()

    results = await pipeline.run_pipeline(
        repo_owner="acme-corp",
        repo_name="api-service",
        principal_id="service-account-cicd",
        branch="main"
    )

    print(f"Pipeline {results['pipeline_id']}: ", end="")
    print("✅ SUCCESS" if results["overall_success"] else "❌ FAILED")

    for step in results["steps"]:
        status = "✅" if step["success"] else "❌"
        print(f"  {status} {step['name']} ({step['protocol']})")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Implementing Policies

Create unified policy for the entire workflow in `policies/cicd_pipeline.rego`:

```rego
package sark.policies.cicd

import future.keywords.if

# CI/CD service account principal
is_cicd_service if {
    input.principal.id == "service-account-cicd"
}

# Allow GitHub API access for CI/CD
allow if {
    is_cicd_service
    input.resource.protocol == "http"
    input.resource.name == "GitHub API"
    # Allow specific GitHub operations
    contains(input.capability.name, "repos")
}

# Allow MCP code analyzer
allow if {
    is_cicd_service
    input.resource.protocol == "mcp"
    input.resource.name == "Code Analyzer"
}

# Allow gRPC test runner
allow if {
    is_cicd_service
    input.resource.protocol == "grpc"
    input.resource.name == "Test Runner Service"
}

# Allow gRPC metrics storage
allow if {
    is_cicd_service
    input.resource.protocol == "grpc"
    input.resource.name == "Metrics Service"
}

# Allow Slack notifications
allow if {
    is_cicd_service
    input.resource.protocol == "http"
    input.resource.name == "Slack API"
    input.capability.name == "chat.postMessage"
}

# Deny everything else
allow = false

# Add constraints: Only during business hours
deny["CI/CD pipelines can only run during business hours"] if {
    is_cicd_service
    not is_business_hours
}

is_business_hours if {
    # Get current hour (0-23)
    hour := time.clock([time.now_ns(), "UTC"])[0]
    hour >= 8
    hour < 18
}

# Add rate limiting: Max 100 pipelines per hour
deny["Rate limit exceeded"] if {
    is_cicd_service
    count(recent_pipeline_runs) > 100
}

recent_pipeline_runs[run] if {
    # Query recent runs from audit log
    # (Implementation depends on SARK's audit log integration)
    run := data.audit_log[_]
    run.principal_id == "service-account-cicd"
    run.timestamp > time.now_ns() - (3600 * 1000000000)  # Last hour
}
```

Upload the policy:

```bash
curl -X POST http://localhost:8000/api/v1/policies \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"cicd-pipeline-policy\",
    \"content\": \"$(cat policies/cicd_pipeline.rego)\"
  }"
```

---

## Error Handling Across Protocols

Implement robust error handling for multi-protocol workflows:

```python
class CICDPipeline:
    """CI/CD pipeline with comprehensive error handling."""

    async def run_pipeline_with_retry(
        self,
        repo_owner: str,
        repo_name: str,
        principal_id: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """Run pipeline with retry logic."""

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    "pipeline_attempt",
                    attempt=attempt,
                    max_retries=max_retries
                )

                results = await self.run_pipeline(
                    repo_owner, repo_name, principal_id
                )

                if results["overall_success"]:
                    return results

                # Partial failure - retry
                logger.warning(
                    "pipeline_partial_failure",
                    attempt=attempt,
                    results=results
                )

            except Exception as e:
                logger.error(
                    "pipeline_attempt_failed",
                    attempt=attempt,
                    error=str(e)
                )

                if attempt == max_retries:
                    # Final attempt failed
                    raise

                # Wait before retry (exponential backoff)
                await asyncio.sleep(2 ** attempt)

        raise Exception("Pipeline failed after all retries")

    async def _invoke_with_fallback(
        self,
        primary_request: InvocationRequest,
        fallback_request: Optional[InvocationRequest] = None
    ) -> Any:
        """
        Invoke capability with optional fallback.

        Useful when you have redundant services across protocols.
        """
        try:
            result = await self.sark.authorize_and_invoke(primary_request)
            if result.success:
                return result
        except Exception as e:
            logger.warning(
                "primary_invocation_failed",
                capability=primary_request.capability_id,
                error=str(e)
            )

        if fallback_request:
            logger.info(
                "attempting_fallback",
                fallback=fallback_request.capability_id
            )
            return await self.sark.authorize_and_invoke(fallback_request)

        raise Exception("Both primary and fallback invocations failed")
```

---

## Monitoring and Auditing

### View Complete Multi-Protocol Audit Trail

```bash
# Get all events for this pipeline run
curl "http://localhost:8000/api/v1/audit-log?principal_id=service-account-cicd&limit=100"
```

**Response:**
```json
{
  "events": [
    {
      "timestamp": "2024-11-29T10:00:00Z",
      "principal": "service-account-cicd",
      "resource": "GitHub API",
      "protocol": "http",
      "capability": "GET-/repos/{owner}/{repo}/commits/{branch}",
      "decision": "allow",
      "duration_ms": 234
    },
    {
      "timestamp": "2024-11-29T10:00:01Z",
      "principal": "service-account-cicd",
      "resource": "Code Analyzer",
      "protocol": "mcp",
      "capability": "analyze_repository",
      "decision": "allow",
      "duration_ms": 5432
    },
    {
      "timestamp": "2024-11-29T10:00:07Z",
      "principal": "service-account-cicd",
      "resource": "Test Runner Service",
      "protocol": "grpc",
      "capability": "TestRunner.RunTests",
      "decision": "allow",
      "duration_ms": 45678
    },
    {
      "timestamp": "2024-11-29T10:00:53Z",
      "principal": "service-account-cicd",
      "resource": "Metrics Service",
      "protocol": "grpc",
      "capability": "MetricsService.StoreMetrics",
      "decision": "allow",
      "duration_ms": 123
    },
    {
      "timestamp": "2024-11-29T10:00:54Z",
      "principal": "service-account-cicd",
      "resource": "Slack API",
      "protocol": "http",
      "capability": "chat.postMessage",
      "decision": "allow",
      "duration_ms": 456
    }
  ]
}
```

One audit trail covering all protocols! 🎉

### Metrics Dashboard

Query aggregated metrics:

```python
import httpx

async def get_pipeline_metrics(days: int = 7):
    """Get CI/CD pipeline metrics across all protocols."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/v1/audit-log/aggregate",
            params={
                "principal_id": "service-account-cicd",
                "days": days,
                "group_by": "protocol"
            }
        )
        return response.json()

# Example output
{
    "http": {
        "total_calls": 2500,
        "avg_duration_ms": 345,
        "success_rate": 0.99
    },
    "mcp": {
        "total_calls": 1250,
        "avg_duration_ms": 5234,
        "success_rate": 0.97
    },
    "grpc": {
        "total_calls": 2500,
        "avg_duration_ms": 1234,
        "success_rate": 0.995
    }
}
```

---

## Advanced Patterns

### Pattern 1: Parallel Execution

Run multiple protocol calls in parallel:

```python
async def parallel_analysis(self, commit_sha: str, principal_id: str):
    """Run multiple analyzers in parallel across protocols."""

    tasks = [
        # MCP code analyzer
        self.sark.authorize_and_invoke(InvocationRequest(
            capability_id="mcp-code-analyzer-analyze",
            principal_id=principal_id,
            arguments={"commit": commit_sha}
        )),

        # HTTP security scanner
        self.sark.authorize_and_invoke(InvocationRequest(
            capability_id="http-security-scanner-scan",
            principal_id=principal_id,
            arguments={"commit": commit_sha}
        )),

        # gRPC dependency checker
        self.sark.authorize_and_invoke(InvocationRequest(
            capability_id="DependencyChecker.Check",
            principal_id=principal_id,
            arguments={"commit": commit_sha}
        ))
    ]

    # Wait for all to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return {
        "code_quality": results[0],
        "security": results[1],
        "dependencies": results[2]
    }
```

### Pattern 2: Protocol-Specific Optimizations

Optimize based on protocol characteristics:

```python
class ProtocolOptimizedPipeline(CICDPipeline):
    """Pipeline optimized per protocol."""

    async def _invoke_optimized(
        self,
        request: InvocationRequest,
        protocol: str
    ):
        """Apply protocol-specific optimizations."""

        if protocol == "grpc":
            # gRPC: Use connection pooling
            return await self._invoke_grpc_pooled(request)

        elif protocol == "http":
            # HTTP: Use caching
            return await self._invoke_http_cached(request)

        elif protocol == "mcp":
            # MCP: Keep process alive
            return await self._invoke_mcp_persistent(request)

        else:
            return await self.sark.authorize_and_invoke(request)
```

### Pattern 3: Cross-Protocol Transactions

Implement distributed transactions:

```python
class TransactionalPipeline(CICDPipeline):
    """Pipeline with cross-protocol transactions."""

    async def run_transactional_pipeline(self, ...):
        """Run pipeline with rollback on failure."""

        completed_steps = []

        try:
            # Execute steps
            for step in self.pipeline_steps:
                result = await step.execute()
                completed_steps.append((step, result))

        except Exception as e:
            logger.error("pipeline_failed_rolling_back", error=str(e))

            # Rollback completed steps in reverse order
            for step, result in reversed(completed_steps):
                try:
                    await step.rollback(result)
                except Exception as rollback_error:
                    logger.error(
                        "rollback_failed",
                        step=step.name,
                        error=str(rollback_error)
                    )

            raise
```

---

## Best Practices

### 1. Protocol-Agnostic Workflows

Write workflows that don't depend on protocol specifics:

```python
# Good: Protocol-agnostic
async def notify_team(self, message: str, principal_id: str):
    """Notify team (protocol-agnostic)."""
    # SARK handles the protocol details
    await self.sark.authorize_and_invoke(InvocationRequest(
        capability_id=self.config.notification_capability,
        principal_id=principal_id,
        arguments={"message": message}
    ))

# Can swap Slack (HTTP) for MS Teams (HTTP) or custom (gRPC)
# without changing workflow code!
```

### 2. Centralized Configuration

Use configuration for capability IDs:

```yaml
# config.yaml
capabilities:
  code_fetch: "GET-/repos/{owner}/{repo}/commits"
  code_analyze: "mcp-analyzer-analyze"
  test_runner: "TestRunner.RunTests"
  metrics_storage: "MetricsService.Store"
  notification: "http-slack-post"
```

### 3. Comprehensive Logging

Log at workflow and protocol levels:

```python
logger.info(
    "workflow_step_started",
    step="code_analysis",
    protocol="mcp",
    capability_id=capability_id
)
```

### 4. Handle Protocol Failures Gracefully

Different protocols have different failure modes:

```python
try:
    result = await self.sark.authorize_and_invoke(request)
except HTTPError as e:
    # HTTP-specific error
    logger.error("http_error", status_code=e.status_code)
except GRPCError as e:
    # gRPC-specific error
    logger.error("grpc_error", status_code=e.status_code)
except Exception as e:
    # Generic error
    logger.error("invocation_error", error=str(e))
```

---

## Summary

You've learned to:
- ✅ Build workflows spanning MCP, HTTP, and gRPC
- ✅ Apply unified policies across all protocols
- ✅ Track multi-protocol workflows in one audit trail
- ✅ Handle errors across protocol boundaries
- ✅ Optimize workflows per protocol

### Next Steps

- **[Federation Deployment](FEDERATION_DEPLOYMENT.md)** - Scale across organizations
- **[Troubleshooting](../troubleshooting/V2_TROUBLESHOOTING.md)** - Debug multi-protocol issues
- **[Examples](../../examples/v2/multi-protocol-example/)** - More workflow examples

---

**Happy orchestrating!** 🎼

SARK v2.0 - Orchestrate any protocol
