#!/usr/bin/env python3
"""
Example 3: Approval Workflow for High-Sensitivity Tools

This example demonstrates SARK's break-glass approval mechanism for high-sensitivity
MCP tools that require additional authorization beyond standard policies.

Scenario:
- User wants to invoke a CRITICAL sensitivity tool (e.g., delete_database)
- OPA policy requires explicit approval from admin
- User requests approval with justification
- Admin reviews and approves/denies
- If approved, user can invoke tool within time window

This showcases:
- Sensitivity-based access control
- Approval request workflow
- Time-limited approvals
- Justification requirements
- Audit trail of approval decisions

Prerequisites:
- SARK running at http://localhost:8000
- MCP server with high/critical sensitivity tools
- Two users: regular user and admin

Usage:
    # As regular user
    python examples/03_approval_workflow.py --role user

    # As admin (to approve/deny requests)
    python examples/03_approval_workflow.py --role admin
"""

import argparse
import json
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List

import requests


class SARKClient:
    """SARK API client with approval workflow support."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.access_token: str | None = None
        self.user_info: Dict[str, Any] | None = None

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
            self.user_info = data["user"]
            self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})

            print(f"✅ Authenticated as {data['user']['email']}")
            print(f"   Roles: {', '.join(data['user']['roles'])}")

            return data
        else:
            raise Exception("Authentication failed")

    def check_tool_access(self, tool_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Check if user can access a tool (dry-run policy evaluation)."""
        print(f"\n🔍 Checking access to tool...")

        response = self.session.post(
            f"{self.base_url}/api/v1/policy/evaluate",
            json={
                "action": "tool:invoke",
                "resource_id": tool_id,
                "parameters": arguments,
                "dry_run": True
            },
        )

        if response.status_code == 200:
            decision = response.json()
            return decision
        else:
            raise Exception(f"Policy evaluation failed: {response.status_code}")

    def request_approval(
        self,
        tool_id: str,
        justification: str,
        arguments: Dict[str, Any],
        duration_hours: int = 4
    ) -> Dict[str, Any]:
        """Request approval to invoke a high-sensitivity tool."""
        print(f"\n📝 Requesting approval...")
        print(f"   Tool: {tool_id}")
        print(f"   Justification: {justification}")
        print(f"   Duration: {duration_hours} hours")

        response = self.session.post(
            f"{self.base_url}/api/v1/approvals/request",
            json={
                "tool_id": tool_id,
                "justification": justification,
                "arguments": arguments,
                "duration_hours": duration_hours
            },
        )

        if response.status_code == 201:
            approval_request = response.json()
            print(f"\n✅ Approval request created!")
            print(f"   Request ID: {approval_request['id']}")
            print(f"   Status: {approval_request['status']}")
            print(f"   Expires: {approval_request['expires_at']}")

            return approval_request
        else:
            error = response.json()
            raise Exception(f"Failed to request approval: {error.get('detail')}")

    def list_pending_approvals(self) -> List[Dict[str, Any]]:
        """List pending approval requests (admin view)."""
        print(f"\n📋 Fetching pending approval requests...")

        response = self.session.get(
            f"{self.base_url}/api/v1/approvals?status=pending"
        )

        if response.status_code == 200:
            approvals = response.json()["items"]
            print(f"✅ Found {len(approvals)} pending requests")
            return approvals
        else:
            raise Exception("Failed to fetch approvals")

    def approve_request(
        self,
        approval_id: str,
        admin_notes: str = ""
    ) -> Dict[str, Any]:
        """Approve an approval request (admin only)."""
        print(f"\n✅ Approving request {approval_id}...")

        response = self.session.post(
            f"{self.base_url}/api/v1/approvals/{approval_id}/approve",
            json={"notes": admin_notes},
        )

        if response.status_code == 200:
            approval = response.json()
            print(f"✅ Request approved!")
            print(f"   Valid until: {approval['expires_at']}")
            return approval
        else:
            error = response.json()
            raise Exception(f"Failed to approve: {error.get('detail')}")

    def deny_request(
        self,
        approval_id: str,
        admin_notes: str
    ) -> Dict[str, Any]:
        """Deny an approval request (admin only)."""
        print(f"\n🚫 Denying request {approval_id}...")

        response = self.session.post(
            f"{self.base_url}/api/v1/approvals/{approval_id}/deny",
            json={"notes": admin_notes},
        )

        if response.status_code == 200:
            approval = response.json()
            print(f"🚫 Request denied")
            print(f"   Reason: {admin_notes}")
            return approval
        else:
            error = response.json()
            raise Exception(f"Failed to deny: {error.get('detail')}")

    def invoke_tool_with_approval(
        self,
        tool_id: str,
        arguments: Dict[str, Any],
        approval_id: str
    ) -> Dict[str, Any]:
        """Invoke a tool with an approval token."""
        print(f"\n🚀 Invoking tool with approval...")

        response = self.session.post(
            f"{self.base_url}/api/v1/tools/invoke",
            json={
                "tool_id": tool_id,
                "arguments": arguments,
                "approval_id": approval_id
            },
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Tool invoked successfully!")
            return result
        elif response.status_code == 403:
            error = response.json()
            raise Exception(f"Access denied: {error.get('reason')}")
        else:
            error = response.json()
            raise Exception(f"Tool invocation failed: {error.get('detail')}")


def run_user_workflow(client: SARKClient):
    """Run the workflow from a regular user's perspective."""
    print("\n" + "=" * 80)
    print("👤 User Workflow: Request Approval for High-Sensitivity Tool")
    print("=" * 80)

    # Step 1: Find a high-sensitivity tool
    print("\n📋 Step 1: Find high-sensitivity tools")

    response = client.session.get(f"{client.base_url}/api/v1/tools?sensitivity=critical")

    if response.status_code == 200:
        critical_tools = response.json()["items"]

        if not critical_tools:
            print("⚠️  No critical sensitivity tools found")
            print("   This example requires tools marked as 'critical' sensitivity")
            return

        # Use first critical tool
        tool = critical_tools[0]
        print(f"\n✅ Found critical tool: {tool['name']}")
        print(f"   Sensitivity: {tool['sensitivity_level']}")
        print(f"   Requires Approval: {tool['requires_approval']}")

    # Step 2: Try to invoke without approval (should fail)
    print("\n🔍 Step 2: Check access (should fail without approval)")

    try:
        decision = client.check_tool_access(
            tool_id=tool['id'],
            arguments={}
        )

        if not decision.get('allow'):
            print(f"❌ Access denied (as expected)")
            print(f"   Reason: {decision.get('reason')}")
            print(f"   Approval required: {decision.get('requires_approval', False)}")
    except Exception as e:
        print(f"❌ {e}")

    # Step 3: Request approval
    print("\n📝 Step 3: Request approval from admin")

    justification = (
        "Emergency: Production database corruption detected. Need to run cleanup tool "
        "to restore service. Incident ticket: INC-12345. Approved by VP Engineering."
    )

    approval_request = client.request_approval(
        tool_id=tool['id'],
        justification=justification,
        arguments={},
        duration_hours=2
    )

    print("\n✉️  Approval request submitted!")
    print(f"\n📋 Request Details:")
    print(f"   ID: {approval_request['id']}")
    print(f"   Requester: {client.user_info['email']}")
    print(f"   Tool: {tool['name']}")
    print(f"   Status: {approval_request['status']}")
    print(f"   Created: {approval_request['created_at']}")

    print("\n⏳ Waiting for admin approval...")
    print("   In a real scenario:")
    print("   • Admin receives notification (email/Slack/PagerDuty)")
    print("   • Admin reviews justification and incident ticket")
    print("   • Admin approves or denies via UI or CLI")

    print("\n" + "=" * 80)
    print("Next step: Run this script with --role admin to approve the request")
    print("=" * 80)


def run_admin_workflow(client: SARKClient):
    """Run the workflow from an admin's perspective."""
    print("\n" + "=" * 80)
    print("👑 Admin Workflow: Review and Approve/Deny Requests")
    print("=" * 80)

    # Step 1: List pending approvals
    print("\n📋 Step 1: List pending approval requests")

    approvals = client.list_pending_approvals()

    if not approvals:
        print("\n✅ No pending approval requests")
        print("   Run this script with --role user first to create a request")
        return

    # Step 2: Review each request
    print(f"\n📝 Step 2: Review pending requests")

    for i, approval in enumerate(approvals, 1):
        print(f"\n{'='*80}")
        print(f"Request #{i}:")
        print(f"{'='*80}")
        print(f"ID: {approval['id']}")
        print(f"Requester: {approval['requester']['email']}")
        print(f"Roles: {', '.join(approval['requester']['roles'])}")
        print(f"Tool: {approval['tool']['name']} ({approval['tool']['sensitivity_level']})")
        print(f"Justification:\n   {approval['justification']}")
        print(f"Requested: {approval['created_at']}")
        print(f"Duration: {approval['duration_hours']} hours")

        # In a real scenario, admin would review:
        # - Is justification valid?
        # - Is there an incident ticket?
        # - Has this been escalated properly?
        # - Is the user authorized for this emergency access?

    # Step 3: Approve or deny
    print(f"\n🤔 Step 3: Make decision (approve/deny)")

    # For this example, auto-approve if justification mentions incident ticket
    approval = approvals[0]

    if "INC-" in approval['justification'] or "Incident" in approval['justification']:
        print("\n✅ Justification includes incident ticket - APPROVING")

        approved = client.approve_request(
            approval_id=approval['id'],
            admin_notes="Approved for emergency incident response. Incident verified: INC-12345"
        )

        print("\n" + "=" * 80)
        print("✅ Approval Granted!")
        print("=" * 80)
        print(f"Approval ID: {approved['id']}")
        print(f"Valid until: {approved['expires_at']}")
        print(f"User can now invoke the tool using this approval")

    else:
        print("\n🚫 Insufficient justification - DENYING")

        denied = client.deny_request(
            approval_id=approval['id'],
            admin_notes="Denied: No valid incident ticket provided. Please include incident number."
        )

        print("\n" + "=" * 80)
        print("🚫 Request Denied")
        print("=" * 80)

    print("\n💡 What happened:")
    print("   1. ✅ Admin reviewed pending approval requests")
    print("   2. ✅ Admin validated justification and incident ticket")
    print("   3. ✅ Admin made approve/deny decision")
    print("   4. ✅ Decision audited in TimescaleDB")
    print("   5. ✅ User notified of decision")
    print("   6. ✅ Approval token generated (if approved)")


def main():
    """Run the approval workflow example."""
    parser = argparse.ArgumentParser(description="SARK Approval Workflow Example")
    parser.add_argument(
        "--role",
        choices=["user", "admin"],
        default="user",
        help="Run as user (request approval) or admin (approve requests)"
    )
    args = parser.parse_args()

    print("=" * 80)
    print("SARK MCP Example 3: Approval Workflow")
    print("=" * 80)

    # Configuration
    SARK_URL = os.getenv("SARK_URL", "http://localhost:8000")

    if args.role == "user":
        USERNAME = os.getenv("SARK_USER_USERNAME", "analyst")
        PASSWORD = os.getenv("SARK_USER_PASSWORD", "password")
    else:
        USERNAME = os.getenv("SARK_ADMIN_USERNAME", "admin")
        PASSWORD = os.getenv("SARK_ADMIN_PASSWORD", "password")

    # Create client
    client = SARKClient(base_url=SARK_URL)

    try:
        # Authenticate
        client.login(USERNAME, PASSWORD)

        # Run appropriate workflow
        if args.role == "user":
            run_user_workflow(client)
        else:
            run_admin_workflow(client)

        print("\n🎯 Key Benefits of Approval Workflows:")
        print("   • Break-glass access for emergency situations")
        print("   • Time-limited approvals (auto-expire)")
        print("   • Justification required and audited")
        print("   • Admin review and approval process")
        print("   • Complete audit trail of sensitive operations")
        print("   • SOC 2 / ISO 27001 compliance support")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
