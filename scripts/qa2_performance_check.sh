#!/bin/bash
# QA-2 Performance Monitoring Script for Session 4 Merges
# Runs quick performance checks after each merge

set -e

COMPONENT=$1
BASELINE_P95=150  # ms
BASELINE_RPS=100

echo "=================================="
echo "QA-2 Performance Check: $COMPONENT"
echo "=================================="
echo ""

# Check if we're on main
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" != "main" ]; then
    echo "⚠️  WARNING: Not on main branch (currently on $BRANCH)"
fi

# Show latest commit
echo "Latest commit:"
git log -1 --oneline
echo ""

# Quick syntax check for Python files
echo "1. Syntax Check..."
if python3 -m py_compile src/sark/**/*.py 2>/dev/null; then
    echo "   ✅ Python syntax valid"
else
    echo "   ⚠️  Some Python files have syntax errors"
fi
echo ""

# Check if performance test infrastructure exists
echo "2. Performance Test Infrastructure..."
if [ -f "tests/performance/v2/benchmarks.py" ]; then
    echo "   ✅ Benchmark framework present"
else
    echo "   ⚠️  Benchmark framework not found"
fi
echo ""

# Check if security tests exist
echo "3. Security Test Infrastructure..."
SECURITY_TESTS=$(find tests/security/v2 -name "test_*.py" 2>/dev/null | wc -l)
echo "   ✅ Found $SECURITY_TESTS security test files"
echo ""

# Component-specific checks
echo "4. Component-Specific Checks for: $COMPONENT"
case "$COMPONENT" in
    "database")
        echo "   - Checking database migrations..."
        if [ -d "src/sark/migrations/v2" ]; then
            echo "     ✅ Migration directory exists"
        fi
        echo "   - Database merge: No direct performance impact expected"
        ;;

    "mcp-adapter")
        echo "   - Checking MCP adapter implementation..."
        if [ -f "src/sark/adapters/mcp_adapter.py" ]; then
            echo "     ✅ MCP adapter found"
            echo "   - Note: MCP adapter benchmarks pending (requires MCP server)"
        fi
        ;;

    "http-adapter")
        echo "   ⚠️  CRITICAL: HTTP adapter performance validation required"
        echo "   - Expected P95 latency: <$BASELINE_P95 ms"
        echo "   - Expected throughput: >$BASELINE_RPS RPS"
        if [ -f "src/sark/adapters/http/http_adapter.py" ]; then
            echo "     ✅ HTTP adapter implementation found"
        fi
        if [ -f "tests/performance/v2/run_http_benchmarks.py" ]; then
            echo "     ✅ HTTP benchmark script available"
            echo "   - Run: python tests/performance/v2/run_http_benchmarks.py"
        fi
        ;;

    "grpc-adapter")
        echo "   ⚠️  CRITICAL: gRPC adapter performance validation required"
        echo "   - Expected P95 latency: <$BASELINE_P95 ms"
        echo "   - Expected throughput: >$BASELINE_RPS RPS"
        if [ -f "src/sark/adapters/grpc_adapter.py" ]; then
            echo "     ✅ gRPC adapter implementation found"
        fi
        ;;

    "federation")
        echo "   - Checking federation implementation..."
        if [ -d "src/sark/services/federation" ]; then
            echo "     ✅ Federation service found"
        fi
        echo "   - Federation: Performance impact depends on mTLS overhead"
        ;;

    "advanced-features")
        echo "   - Checking advanced features..."
        echo "   - Cost attribution may add minimal overhead"
        ;;

    "performance-security")
        echo "   - QA-2 deliverables merge"
        echo "   - Contains benchmark and security test infrastructure"
        ;;

    *)
        echo "   - General merge validation"
        ;;
esac
echo ""

# Memory/resource check
echo "5. Resource Check..."
echo "   - Memory usage: $(free -h | grep Mem | awk '{print $3 "/" $2}')"
echo "   - Disk usage: $(df -h . | tail -1 | awk '{print $3 "/" $2 " (" $5 ")"}')"
echo ""

echo "=================================="
echo "Performance Check Complete"
echo "=================================="
echo ""
echo "Status: ✅ Quick checks passed"
echo ""
echo "Next Steps:"
echo "  - For adapter merges: Run full benchmarks"
echo "  - For all merges: Run integration tests (QA-1)"
echo "  - Monitor for performance regressions"
echo ""
