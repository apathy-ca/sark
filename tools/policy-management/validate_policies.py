#!/usr/bin/env python3
"""
Policy Validator - Validates OPA policies for syntax, conflicts, and best practices

Usage:
    ./validate_policies.py
    ./validate_policies.py --policy opa/policies/gateway_authorization.rego
    ./validate_policies.py --check-conflicts
    ./validate_policies.py --lint
"""

import argparse
import json
from pathlib import Path
import subprocess
import sys


class PolicyValidator:
    """Validates OPA policies"""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []

    def validate_syntax(self, policy_file: Path) -> bool:
        """Validate Rego syntax"""
        print(f"\nValidating syntax: {policy_file}")

        cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{policy_file.parent.absolute()}:/policies",
            "openpolicyagent/opa:latest",
            "check",
            f"/policies/{policy_file.name}",
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            print("  ✅ Syntax valid")
            return True
        except subprocess.CalledProcessError as e:
            print("  ❌ Syntax errors found:")
            print(e.stderr)
            self.errors.append(f"{policy_file}: {e.stderr}")
            return False

    def run_tests(self, policy_file: Path) -> bool:
        """Run OPA tests for policy"""
        # Look for corresponding test file
        test_file = policy_file.parent / f"{policy_file.stem}_test.rego"

        if not test_file.exists():
            self.warnings.append(f"{policy_file}: No test file found ({test_file.name})")
            return True

        print(f"\nRunning tests: {test_file}")

        cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{policy_file.parent.absolute()}:/policies",
            "openpolicyagent/opa:latest",
            "test",
            f"/policies/{policy_file.name}",
            f"/policies/{test_file.name}",
            "-v",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            # Parse test output
            output = result.stdout
            if "PASS" in output:
                pass_count = output.count("PASS:")
                fail_count = output.count("FAIL:")
                print(f"  ✅ Tests passed: {pass_count} passed, {fail_count} failed")
                return fail_count == 0
            else:
                print("  ⚠️  No test results found")
                return True
        except subprocess.CalledProcessError as e:
            print("  ❌ Tests failed:")
            print(e.stdout)
            self.errors.append(f"{test_file}: Tests failed")
            return False

    def check_best_practices(self, policy_file: Path) -> bool:
        """Check for policy best practices"""
        print(f"\nChecking best practices: {policy_file}")

        with open(policy_file) as f:
            content = f.read()

        issues = []

        # Check for default deny
        if "default allow :=" not in content and "default allow=" not in content:
            issues.append("Missing 'default allow' rule (should default to false)")

        # Check for documentation
        if not content.startswith("#"):
            issues.append("Missing policy documentation comment at top of file")

        # Check for package declaration
        if "package " not in content:
            issues.append("Missing package declaration")

        # Check for future keywords
        if "import future.keywords" not in content:
            issues.append("Consider importing future.keywords for better syntax")

        # Check for audit/logging
        if "audit" not in content.lower() and "reason" not in content.lower():
            issues.append("No audit_reason or logging found - consider adding for observability")

        # Check for overly permissive rules
        if "allow if {" in content and content.count("allow if {") > 20:
            issues.append("Large number of allow rules - consider consolidating")

        if issues:
            for issue in issues:
                print(f"  ⚠️  {issue}")
                self.warnings.append(f"{policy_file}: {issue}")
        else:
            print("  ✅ Best practices followed")

        return len(issues) == 0

    def check_conflicts(self, policy_files: list[Path]) -> bool:
        """Check for policy conflicts"""
        print("\nChecking for policy conflicts...")

        # Group policies by package
        packages = {}
        for policy_file in policy_files:
            with open(policy_file) as f:
                content = f.read()

            # Extract package name
            for line in content.split('\n'):
                if line.startswith('package '):
                    package_name = line.split('package ')[1].strip()
                    if package_name not in packages:
                        packages[package_name] = []
                    packages[package_name].append(policy_file)
                    break

        # Check for duplicate package definitions
        conflicts_found = False
        for package, files in packages.items():
            if len(files) > 1:
                print(f"  ⚠️  Multiple files define package '{package}':")
                for f in files:
                    print(f"      - {f}")
                self.warnings.append(f"Package '{package}' defined in multiple files")
                conflicts_found = True

        if not conflicts_found:
            print("  ✅ No package conflicts found")

        return not conflicts_found

    def check_completeness(self, policy_file: Path) -> bool:
        """Check if policy is complete"""
        print(f"\nChecking completeness: {policy_file}")

        with open(policy_file) as f:
            content = f.read()

        issues = []

        # Check for essential components
        if "allow" not in content:
            issues.append("No 'allow' rule found - policy may not make decisions")

        if "input." not in content:
            issues.append("No 'input.' references found - policy may not use request data")

        # Check for result structure
        if "result :=" not in content and "result =" not in content:
            issues.append("No 'result' object found - policy may not return structured response")

        if issues:
            for issue in issues:
                print(f"  ⚠️  {issue}")
                self.warnings.append(f"{policy_file}: {issue}")
        else:
            print("  ✅ Policy appears complete")

        return len(issues) == 0

    def generate_report(self) -> dict:
        """Generate validation report"""
        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
            "summary": {
                "total_errors": len(self.errors),
                "total_warnings": len(self.warnings),
                "validation_passed": len(self.errors) == 0,
            }
        }

    def print_summary(self):
        """Print validation summary"""
        print("\n" + "="*60)
        print("VALIDATION SUMMARY")
        print("="*60)

        if self.errors:
            print(f"\n❌ Errors ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")

        if self.warnings:
            print(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")

        if not self.errors and not self.warnings:
            print("\n✅ All validations passed!")
        elif not self.errors:
            print("\n✅ No errors found (warnings only)")
        else:
            print("\n❌ Validation failed")

        return len(self.errors) == 0


def find_policy_files(path: Path) -> list[Path]:
    """Find all .rego files (excluding tests)"""
    if path.is_file():
        return [path]

    # Find all .rego files
    rego_files = list(path.rglob("*.rego"))

    # Exclude test files
    policy_files = [f for f in rego_files if not f.name.endswith("_test.rego")]

    return policy_files


def main():
    parser = argparse.ArgumentParser(
        description="Validate OPA policies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--policy",
        "-p",
        type=Path,
        help="Specific policy file or directory to validate",
    )

    parser.add_argument(
        "--check-conflicts",
        "-c",
        action="store_true",
        help="Check for policy conflicts",
    )

    parser.add_argument(
        "--lint",
        "-l",
        action="store_true",
        help="Run best practices linter",
    )

    parser.add_argument(
        "--test",
        "-t",
        action="store_true",
        help="Run policy tests",
    )

    parser.add_argument(
        "--output",
        "-o",
        help="Output report to JSON file",
    )

    args = parser.parse_args()

    # Default to checking opa/policies directory
    policy_path = args.policy or Path("opa/policies")

    if not policy_path.exists():
        print(f"Error: Path not found: {policy_path}", file=sys.stderr)
        sys.exit(1)

    # Find policy files
    policy_files = find_policy_files(policy_path)

    if not policy_files:
        print(f"Error: No policy files found in {policy_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(policy_files)} policy file(s)")

    # Create validator
    validator = PolicyValidator()

    # Run validations

    for policy_file in policy_files:
        # Syntax validation (always run)
        if not validator.validate_syntax(policy_file):
            continue  # Skip other checks if syntax is invalid

        # Run tests
        if args.test or not args.lint:  # Run tests by default
            if not validator.run_tests(policy_file):
                pass

        # Best practices
        if args.lint or not args.test:  # Run linter by default
            validator.check_best_practices(policy_file)
            validator.check_completeness(policy_file)

    # Check conflicts
    if args.check_conflicts or len(policy_files) > 1:
        validator.check_conflicts(policy_files)

    # Print summary
    success = validator.print_summary()

    # Output report
    if args.output:
        report = validator.generate_report()
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {args.output}")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
