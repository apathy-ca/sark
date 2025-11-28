#!/bin/bash
# OPA Policy Bundle Build Script
# This script builds an OPA policy bundle from the policies directory

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
POLICIES_DIR="$PROJECT_ROOT/opa/policies"
BUNDLE_DIR="$PROJECT_ROOT/opa/bundle"
OUTPUT_FILE="$BUNDLE_DIR/bundle.tar.gz"

echo "======================================"
echo "Building OPA Policy Bundle"
echo "======================================"
echo ""
echo "Policies directory: $POLICIES_DIR"
echo "Bundle directory: $BUNDLE_DIR"
echo "Output file: $OUTPUT_FILE"
echo ""

# Check if OPA is installed
if ! command -v opa &> /dev/null; then
    echo "Error: OPA is not installed. Please install OPA first."
    echo "Visit: https://www.openpolicyagent.org/docs/latest/#running-opa"
    exit 1
fi

echo "OPA version:"
opa version
echo ""

# Run OPA tests first
echo "Running OPA tests..."
if opa test "$POLICIES_DIR"/*.rego -v; then
    echo "✅ All tests passed!"
else
    echo "❌ Tests failed. Fix errors before building bundle."
    exit 1
fi
echo ""

# Build the bundle
echo "Building bundle..."
if opa build -b "$POLICIES_DIR" -o "$OUTPUT_FILE"; then
    echo "✅ Bundle built successfully!"
else
    echo "❌ Bundle build failed."
    exit 1
fi
echo ""

# Display bundle info
echo "Bundle information:"
ls -lh "$OUTPUT_FILE"
echo ""

# Verify bundle contents
echo "Bundle contents:"
tar -tzf "$OUTPUT_FILE" | head -20
echo ""

echo "======================================"
echo "Bundle build complete!"
echo "======================================"
echo ""
echo "To use this bundle:"
echo "  1. Copy to OPA server: scp $OUTPUT_FILE opa-server:/bundles/"
echo "  2. Configure OPA to load from bundle"
echo "  3. Or use locally: opa run --server --bundle $OUTPUT_FILE"
echo ""
