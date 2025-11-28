#!/usr/bin/env python3
"""
Policy Simulator - CLI tool for testing OPA policy decisions

This tool allows you to simulate policy decisions without needing to run
the full SARK stack. It's useful for:
- Testing policy changes before deployment
- Understanding policy behavior
- Debugging authorization issues
- Creating test scenarios

Usage:
    ./simulate_policy.py --policy gateway_auth \\
        --input '{"user": {"role": "admin"}, "tool": {"sensitivity_level": "high"}}' \\
        --explain

    ./simulate_policy.py --scenario examples/admin_critical_tool.json

    ./simulate_policy.py --batch scenarios/batch_test.json
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

# Policy file mappings
POLICY_MAPPINGS = {
    "gateway_auth": "opa/policies/gateway_authorization.rego",
    "a2a_auth": "opa/policies/a2a_authorization.rego",
    "rate_limit": "opa/policies/gateway/advanced/dynamic_rate_limits.rego",
    "contextual": "opa/policies/gateway/advanced/contextual_auth.rego",
    "tool_chain": "opa/policies/gateway/advanced/tool_chain_governance.rego",
    "data_gov": "opa/policies/gateway/advanced/data_governance.rego",
    "cost_control": "opa/policies/gateway/advanced/cost_control.rego",
}

# Policy package mappings
PACKAGE_MAPPINGS = {
    "gateway_auth": "data.mcp.gateway.result",
    "a2a_auth": "data.mcp.gateway.a2a.result",
    "rate_limit": "data.mcp.gateway.ratelimit.result",
    "contextual": "data.mcp.gateway.contextual.result",
    "tool_chain": "data.mcp.gateway.toolchain.result",
    "data_gov": "data.mcp.gateway.datagovernance.result",
    "cost_control": "data.mcp.gateway.costcontrol.result",
}


class PolicySimulator:
    """Simulates OPA policy decisions"""

    def __init__(self, policy_name: str, explain: bool = False):
        self.policy_name = policy_name
        self.explain = explain
        self.policy_file = self._get_policy_file()
        self.package_path = PACKAGE_MAPPINGS.get(policy_name)

    def _get_policy_file(self) -> Path:
        """Get the policy file path"""
        if self.policy_name not in POLICY_MAPPINGS:
            raise ValueError(
                f"Unknown policy: {self.policy_name}. "
                f"Available: {', '.join(POLICY_MAPPINGS.keys())}"
            )

        policy_file = Path(POLICY_MAPPINGS[self.policy_name])
        if not policy_file.exists():
            raise FileNotFoundError(f"Policy file not found: {policy_file}")

        return policy_file

    def evaluate(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate policy with given input"""
        # Build OPA eval command
        cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{Path.cwd()}:/workspace",
            "openpolicyagent/opa:latest",
            "eval",
            "-d",
            f"/workspace/{self.policy_file}",
            "-i",
            "/dev/stdin",
            self.package_path,
        ]

        if self.explain:
            cmd.append("--explain=full")

        # Run OPA
        try:
            result = subprocess.run(
                cmd,
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                check=True,
            )

            # Parse output
            output = json.loads(result.stdout)

            if self.explain:
                return {
                    "result": output.get("result", [{}])[0].get("expressions", [{}])[0].get("value"),
                    "explanation": result.stderr,
                }
            else:
                return output.get("result", [{}])[0].get("expressions", [{}])[0].get("value", {})

        except subprocess.CalledProcessError as e:
            print(f"Error running OPA: {e.stderr}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error parsing OPA output: {e}", file=sys.stderr)
            sys.exit(1)

    def evaluate_batch(self, scenarios: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Evaluate multiple scenarios"""
        results = []
        for i, scenario in enumerate(scenarios):
            scenario_name = scenario.get("name", f"Scenario {i+1}")
            input_data = scenario.get("input")

            print(f"\n{'='*60}")
            print(f"Scenario: {scenario_name}")
            print(f"{'='*60}")

            result = self.evaluate(input_data)
            results.append({
                "scenario": scenario_name,
                "input": input_data,
                "result": result,
            })

            # Print result
            self._print_result(result, scenario.get("expected"))

        return results

    def _print_result(self, result: Dict[str, Any], expected: Dict[str, Any] = None):
        """Pretty print policy result"""
        if isinstance(result, dict):
            allow = result.get("allow", False)
            reason = result.get("reason", "No reason provided")

            status = "✅ ALLOWED" if allow else "❌ DENIED"
            print(f"\nDecision: {status}")
            print(f"Reason: {reason}")

            # Print additional metadata
            for key, value in result.items():
                if key not in ["allow", "reason"]:
                    print(f"{key.replace('_', ' ').title()}: {json.dumps(value, indent=2)}")

            # Check against expected result
            if expected:
                expected_allow = expected.get("allow")
                if expected_allow is not None and expected_allow != allow:
                    print(f"\n⚠️  WARNING: Expected {expected_allow}, got {allow}")
        else:
            print(f"\nResult: {json.dumps(result, indent=2)}")


def load_json_file(filepath: str) -> Dict[str, Any]:
    """Load JSON from file"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Simulate OPA policy decisions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--policy",
        "-p",
        required=True,
        choices=POLICY_MAPPINGS.keys(),
        help="Policy to evaluate",
    )

    parser.add_argument(
        "--input",
        "-i",
        help="Input JSON string or file path (@file.json)",
    )

    parser.add_argument(
        "--scenario",
        "-s",
        help="Load scenario from JSON file",
    )

    parser.add_argument(
        "--batch",
        "-b",
        help="Load multiple scenarios from JSON file",
    )

    parser.add_argument(
        "--explain",
        "-e",
        action="store_true",
        help="Show detailed policy evaluation explanation",
    )

    parser.add_argument(
        "--list-policies",
        "-l",
        action="store_true",
        help="List available policies",
    )

    args = parser.parse_args()

    # List policies
    if args.list_policies:
        print("Available policies:")
        for policy, file in POLICY_MAPPINGS.items():
            print(f"  {policy:15} → {file}")
        sys.exit(0)

    # Validate arguments
    if not any([args.input, args.scenario, args.batch]):
        parser.error("One of --input, --scenario, or --batch is required")

    # Create simulator
    simulator = PolicySimulator(args.policy, args.explain)

    # Batch mode
    if args.batch:
        scenarios = load_json_file(args.batch)
        simulator.evaluate_batch(scenarios)
        return

    # Single scenario
    if args.scenario:
        scenario = load_json_file(args.scenario)
        input_data = scenario.get("input")
        expected = scenario.get("expected")
    elif args.input.startswith("@"):
        # Load from file
        input_data = load_json_file(args.input[1:])
        expected = None
    else:
        # Parse JSON string
        try:
            input_data = json.loads(args.input)
            expected = None
        except json.JSONDecodeError as e:
            print(f"Error parsing input JSON: {e}", file=sys.stderr)
            sys.exit(1)

    # Evaluate
    result = simulator.evaluate(input_data)

    # Print results
    if args.explain:
        print("\n" + "="*60)
        print("POLICY DECISION")
        print("="*60)
        simulator._print_result(result.get("result"), expected)

        print("\n" + "="*60)
        print("EXPLANATION")
        print("="*60)
        print(result.get("explanation"))
    else:
        simulator._print_result(result, expected)


if __name__ == "__main__":
    main()
