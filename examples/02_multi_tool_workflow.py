#!/usr/bin/env python3
"""
Example 2: Multi-Tool Workflow

This example demonstrates chaining multiple MCP tool invocations to accomplish
a complex task. It shows how to:
- Invoke multiple tools in sequence
- Pass results from one tool to another
- Handle dependencies between tools
- Track workflow state

Use Case: Data Analysis Workflow
1. Query database for user data
2. Analyze data using analytics tool
3. Generate report using reporting tool
4. Send notification via messaging tool

Prerequisites:
- SARK running at http://localhost:8000
- Multiple MCP servers registered with different tools

Usage:
    python examples/02_multi_tool_workflow.py
"""

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List

import requests


@dataclass
class WorkflowStep:
    """Represents a step in a workflow."""
    name: str
    tool_name: str
    description: str
    depends_on: List[str] = None  # Names of steps that must complete first
    status: str = "pending"  # pending, running, completed, failed
    result: Any = None
    error: str = None
    duration_ms: int = 0

    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []


class WorkflowEngine:
    """Simple workflow engine for orchestrating multi-tool tasks."""

    def __init__(self, client):
        self.client = client
        self.steps: List[WorkflowStep] = []
        self.results: Dict[str, Any] = {}

    def add_step(
        self,
        name: str,
        tool_name: str,
        description: str,
        depends_on: List[str] = None
    ) -> WorkflowStep:
        """Add a step to the workflow."""
        step = WorkflowStep(
            name=name,
            tool_name=tool_name,
            description=description,
            depends_on=depends_on or []
        )
        self.steps.append(step)
        return step

    def can_execute(self, step: WorkflowStep) -> bool:
        """Check if a step's dependencies are satisfied."""
        for dep_name in step.depends_on:
            dep_step = next((s for s in self.steps if s.name == dep_name), None)
            if not dep_step or dep_step.status != "completed":
                return False
        return True

    def execute_workflow(self, arguments_builder=None) -> bool:
        """Execute all workflow steps in order."""
        print("\n" + "=" * 80)
        print("🔄 Starting Multi-Tool Workflow")
        print("=" * 80)

        # Display workflow plan
        print(f"\n📋 Workflow Plan ({len(self.steps)} steps):")
        for i, step in enumerate(self.steps, 1):
            deps = f" (depends on: {', '.join(step.depends_on)})" if step.depends_on else ""
            print(f"   {i}. {step.name}: {step.description}{deps}")

        # Execute steps
        completed = 0
        max_iterations = len(self.steps) * 2  # Prevent infinite loops
        iteration = 0

        while completed < len(self.steps) and iteration < max_iterations:
            iteration += 1
            made_progress = False

            for step in self.steps:
                if step.status != "pending":
                    continue

                if not self.can_execute(step):
                    continue

                # Execute this step
                print(f"\n{'='*80}")
                print(f"⚙️  Executing Step: {step.name}")
                print(f"{'='*80}")
                print(f"Tool: {step.tool_name}")
                print(f"Description: {step.description}")

                step.status = "running"
                start_time = time.time()

                try:
                    # Build arguments for this step
                    if arguments_builder:
                        arguments = arguments_builder(step.name, self.results)
                    else:
                        arguments = {}

                    print(f"Arguments: {json.dumps(arguments, indent=2)}")

                    # Find the tool
                    tools = self.client.list_tools()
                    tool = next((t for t in tools if t['name'] == step.tool_name), None)

                    if not tool:
                        raise Exception(f"Tool not found: {step.tool_name}")

                    # Invoke the tool
                    result = self.client.invoke_tool(
                        tool_id=tool['id'],
                        arguments=arguments
                    )

                    # Store result
                    step.result = result
                    step.status = "completed"
                    self.results[step.name] = result

                    elapsed_ms = int((time.time() - start_time) * 1000)
                    step.duration_ms = elapsed_ms

                    print(f"\n✅ Step completed in {elapsed_ms}ms")
                    completed += 1
                    made_progress = True

                except Exception as e:
                    step.status = "failed"
                    step.error = str(e)
                    print(f"\n❌ Step failed: {e}")

                    # Decide whether to continue or abort
                    print("\n⚠️  Workflow failed due to step failure")
                    return False

            if not made_progress:
                print("\n❌ Workflow stuck - no steps can execute (circular dependency?)")
                return False

        # Check if all steps completed
        success = all(step.status == "completed" for step in self.steps)

        print("\n" + "=" * 80)
        print("📊 Workflow Summary")
        print("=" * 80)

        total_duration = sum(step.duration_ms for step in self.steps)

        for i, step in enumerate(self.steps, 1):
            status_icon = {
                "completed": "✅",
                "failed": "❌",
                "pending": "⏳",
                "running": "⚙️"
            }.get(step.status, "❓")

            print(f"{status_icon} Step {i}: {step.name} ({step.status}) - {step.duration_ms}ms")

            if step.error:
                print(f"   Error: {step.error}")

        print(f"\n⏱️  Total execution time: {total_duration}ms")
        print(f"📈 Success rate: {completed}/{len(self.steps)} steps")

        return success


class SARKClient:
    """Simple SARK API client (same as Example 1)."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.access_token: str | None = None

    def login(self, username: str, password: str):
        """Authenticate with SARK."""
        print(f"\n📡 Authenticating as {username}...")

        response = self.session.post(
            f"{self.base_url}/api/v1/auth/login/ldap",
            json={"username": username, "password": password},
        )

        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
            print(f"✅ Authenticated as {data['user']['email']}")
            return data
        else:
            raise Exception("Authentication failed")

    def list_tools(self) -> list:
        """List available tools."""
        response = self.session.get(f"{self.base_url}/api/v1/tools")

        if response.status_code == 200:
            return response.json()["items"]
        return []

    def invoke_tool(self, tool_id: str, arguments: dict) -> dict:
        """Invoke an MCP tool."""
        response = self.session.post(
            f"{self.base_url}/api/v1/tools/invoke",
            json={"tool_id": tool_id, "arguments": arguments},
        )

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403:
            error = response.json()
            raise Exception(f"Access denied: {error.get('reason')}")
        else:
            raise Exception(f"Tool invocation failed: {response.status_code}")


def build_workflow_arguments(step_name: str, previous_results: Dict[str, Any]) -> Dict[str, Any]:
    """Build arguments for each workflow step based on previous results."""

    if step_name == "query_data":
        # First step - query database
        return {
            "query": "SELECT * FROM users WHERE status = 'active' LIMIT 100",
            "limit": 100
        }

    elif step_name == "analyze_data":
        # Second step - analyze results from query
        query_result = previous_results.get("query_data", {})
        data = query_result.get("result", {}).get("data", [])

        return {
            "data": data,
            "analysis_type": "summary_statistics",
            "include_charts": True
        }

    elif step_name == "generate_report":
        # Third step - generate report from analysis
        analysis_result = previous_results.get("analyze_data", {})
        analysis = analysis_result.get("result", {})

        return {
            "title": "User Activity Analysis Report",
            "sections": ["summary", "charts", "recommendations"],
            "data": analysis,
            "format": "pdf"
        }

    elif step_name == "send_notification":
        # Fourth step - send notification about completed report
        report_result = previous_results.get("generate_report", {})
        report_url = report_result.get("result", {}).get("url", "N/A")

        return {
            "recipients": ["data-team@company.com"],
            "subject": "User Activity Analysis Report Ready",
            "message": f"Your report is ready: {report_url}",
            "priority": "normal"
        }

    else:
        return {}


def main():
    """Run the multi-tool workflow example."""
    print("=" * 80)
    print("SARK MCP Example 2: Multi-Tool Workflow")
    print("=" * 80)

    # Configuration
    SARK_URL = os.getenv("SARK_URL", "http://localhost:8000")
    USERNAME = os.getenv("SARK_USERNAME", "admin")
    PASSWORD = os.getenv("SARK_PASSWORD", "password")

    # Create client
    client = SARKClient(base_url=SARK_URL)

    try:
        # Authenticate
        client.login(USERNAME, PASSWORD)

        # Create workflow
        workflow = WorkflowEngine(client)

        # Define workflow steps
        workflow.add_step(
            name="query_data",
            tool_name="database_query",
            description="Query user data from database"
        )

        workflow.add_step(
            name="analyze_data",
            tool_name="analyze_dataset",
            description="Analyze user data statistics",
            depends_on=["query_data"]
        )

        workflow.add_step(
            name="generate_report",
            tool_name="generate_report",
            description="Generate PDF report from analysis",
            depends_on=["analyze_data"]
        )

        workflow.add_step(
            name="send_notification",
            tool_name="send_email",
            description="Notify team that report is ready",
            depends_on=["generate_report"]
        )

        # Execute workflow
        success = workflow.execute_workflow(
            arguments_builder=build_workflow_arguments
        )

        if success:
            print("\n" + "=" * 80)
            print("✅ Multi-Tool Workflow Completed Successfully!")
            print("=" * 80)

            print("\n💡 What happened:")
            print("   1. ✅ Queried database for user data")
            print("   2. ✅ Analyzed data using analytics MCP tool")
            print("   3. ✅ Generated PDF report using reporting MCP tool")
            print("   4. ✅ Sent email notification using messaging MCP tool")
            print("   5. ✅ All steps authorized by OPA policies")
            print("   6. ✅ All steps audited in TimescaleDB")

            print("\n🎯 Benefits of Multi-Tool Workflows:")
            print("   • Orchestrate complex tasks across multiple MCP servers")
            print("   • Centralized authorization for entire workflow")
            print("   • Complete audit trail of all tool invocations")
            print("   • Policy-based access control at each step")
            print("   • Automatic dependency management")

            return 0
        else:
            print("\n❌ Workflow failed")
            return 1

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
