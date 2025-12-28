#!/usr/bin/env bash
#
# Memory Profiling Automation Script
#
# Runs memory profiling tests and generates reports:
# - Short-term leak detection (CI-friendly)
# - Long-term stability tests (24 hour)
# - Rust vs Python comparison
# - Resource cleanup verification
#
# Usage:
#   ./profile_memory.sh short       # Quick leak detection
#   ./profile_memory.sh long        # 24-hour stability test
#   ./profile_memory.sh comparison  # Rust vs Python
#   ./profile_memory.sh all         # All memory tests
#

set -euo pipefail

# ==============================================================================
# Configuration
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

REPORTS_DIR="${SCRIPT_DIR}/reports"
mkdir -p "$REPORTS_DIR"

# ==============================================================================
# Color output
# ==============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# ==============================================================================
# Short-term Memory Tests (CI-friendly)
# ==============================================================================

run_short_tests() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local report_file="${REPORTS_DIR}/memory_short_${timestamp}.txt"

    log_info "Running short-term memory leak tests..."
    log_info "  Duration: ~5-10 minutes"
    log_info "  Tests: OPA client, Cache operations"
    log_info "  Report: ${report_file}"

    pytest test_memory_leaks.py \
        -v -s \
        -m memory \
        --tb=short \
        -k "short" \
        | tee "$report_file"

    log_success "Short-term tests complete"
    log_info "Report saved to: ${report_file}"
}

# ==============================================================================
# Long-term Stability Test (24 hours)
# ==============================================================================

run_long_test() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local report_file="${REPORTS_DIR}/memory_long_${timestamp}.txt"

    log_warning "Starting 24-hour memory stability test"
    log_info "  Duration: 24 hours"
    log_info "  Samples: Every 5 minutes"
    log_info "  Report: ${report_file}"
    log_warning "  This will run for 24 hours. Use screen/tmux!"

    # Prompt for confirmation
    read -p "Continue? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        log_info "Cancelled"
        return
    fi

    # Run the 24-hour test
    pytest test_memory_leaks.py::test_no_memory_leak_24h \
        -v -s \
        --tb=short \
        | tee "$report_file"

    log_success "24-hour test complete"
    log_info "Report saved to: ${report_file}"
}

# ==============================================================================
# Rust vs Python Comparison
# ==============================================================================

run_comparison() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local report_file="${REPORTS_DIR}/memory_comparison_${timestamp}.txt"

    log_info "Running Rust vs Python memory comparison..."

    # Check if Rust is enabled
    rust_enabled="${RUST_ENABLED:-false}"
    if [ "$rust_enabled" != "true" ]; then
        log_warning "RUST_ENABLED is not set to 'true'"
        log_info "Will run Python baseline only"
    fi

    log_info "  Report: ${report_file}"

    pytest test_memory_leaks.py::test_rust_vs_python_memory_usage \
        -v -s \
        --tb=short \
        | tee "$report_file"

    log_success "Comparison complete"
    log_info "Report saved to: ${report_file}"
}

# ==============================================================================
# Resource Cleanup Test
# ==============================================================================

run_cleanup_test() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local report_file="${REPORTS_DIR}/memory_cleanup_${timestamp}.txt"

    log_info "Running resource cleanup verification..."
    log_info "  Report: ${report_file}"

    pytest test_memory_leaks.py::test_resource_cleanup_on_client_close \
        -v -s \
        --tb=short \
        | tee "$report_file"

    log_success "Cleanup test complete"
    log_info "Report saved to: ${report_file}"
}

# ==============================================================================
# Memory Profiling with memory_profiler
# ==============================================================================

run_profiler() {
    log_info "Running memory profiler..."

    # Check if memory_profiler is installed
    if ! python -c "import memory_profiler" 2>/dev/null; then
        log_error "memory_profiler not installed"
        log_info "Install with: pip install memory_profiler"
        return 1
    fi

    local timestamp=$(date +%Y%m%d_%H%M%S)
    local report_file="${REPORTS_DIR}/memory_profile_${timestamp}.txt"

    log_info "  Report: ${report_file}"

    # Run with memory profiler
    python -m memory_profiler test_memory_leaks.py \
        > "$report_file" 2>&1

    log_success "Profiling complete"
    log_info "Report saved to: ${report_file}"
}

# ==============================================================================
# System Memory Monitor
# ==============================================================================

monitor_system_memory() {
    local duration_seconds="${1:-300}"  # Default 5 minutes
    local interval_seconds="${2:-5}"    # Sample every 5 seconds

    log_info "Monitoring system memory..."
    log_info "  Duration: ${duration_seconds}s"
    log_info "  Interval: ${interval_seconds}s"

    local timestamp=$(date +%Y%m%d_%H%M%S)
    local report_file="${REPORTS_DIR}/system_memory_${timestamp}.csv"

    echo "timestamp,total_mb,available_mb,used_mb,percent,swap_total_mb,swap_used_mb" > "$report_file"

    local elapsed=0
    while [ $elapsed -lt $duration_seconds ]; do
        # Get memory stats
        local mem_stats=$(free -m | awk 'NR==2 {print $2","$7","$3","$3/$2*100}')
        local swap_stats=$(free -m | awk 'NR==3 {print $2","$3}')
        local timestamp=$(date +%Y-%m-%d\ %H:%M:%S)

        echo "${timestamp},${mem_stats},${swap_stats}" >> "$report_file"

        sleep $interval_seconds
        elapsed=$((elapsed + interval_seconds))

        # Progress indicator
        if [ $((elapsed % 30)) -eq 0 ]; then
            log_info "  Monitoring... ${elapsed}/${duration_seconds}s"
        fi
    done

    log_success "Monitoring complete"
    log_info "Report saved to: ${report_file}"
    log_info "View with: column -t -s, ${report_file}"
}

# ==============================================================================
# Generate Memory Report
# ==============================================================================

generate_report() {
    log_info "Generating comprehensive memory report..."

    local timestamp=$(date +%Y%m%d_%H%M%S)
    local report_file="${REPORTS_DIR}/memory_report_${timestamp}.md"

    cat > "$report_file" <<EOF
# Memory Profiling Report

**Date**: $(date)
**System**: $(uname -a)
**Python Version**: $(python --version)
**Total System Memory**: $(free -h | awk 'NR==2 {print $2}')

---

## Test Summary

EOF

    # List all recent test reports
    log_info "Recent test reports:"
    ls -lt "$REPORTS_DIR" | head -10 | tee -a "$report_file"

    log_success "Report generated: ${report_file}"
}

# ==============================================================================
# Main
# ==============================================================================

main() {
    local command="${1:-help}"

    echo ""
    echo "=========================================="
    echo "SARK Memory Profiling"
    echo "=========================================="
    echo ""

    # Check dependencies
    if ! command -v pytest &> /dev/null; then
        log_error "pytest is not installed"
        exit 1
    fi

    case "$command" in
        short)
            run_short_tests
            ;;
        long)
            run_long_test
            ;;
        comparison)
            run_comparison
            ;;
        cleanup)
            run_cleanup_test
            ;;
        profiler)
            run_profiler
            ;;
        monitor)
            local duration="${2:-300}"
            local interval="${3:-5}"
            monitor_system_memory "$duration" "$interval"
            ;;
        report)
            generate_report
            ;;
        all)
            log_info "Running all memory tests (except 24-hour test)..."
            run_short_tests
            echo ""
            run_comparison
            echo ""
            run_cleanup_test
            echo ""
            generate_report
            log_success "All tests complete"
            ;;
        help|*)
            cat <<EOF
Usage: $0 <command> [options]

Commands:
  short       - Run short-term leak detection tests (~10 min)
  long        - Run 24-hour stability test (requires confirmation)
  comparison  - Compare Rust vs Python memory usage
  cleanup     - Test resource cleanup on client close
  profiler    - Run with memory_profiler
  monitor     - Monitor system memory (args: duration interval)
  report      - Generate comprehensive memory report
  all         - Run all tests except long

Examples:
  $0 short
  $0 long
  $0 comparison
  $0 monitor 600 10     # Monitor for 10 min, sample every 10s
  $0 all

Environment Variables:
  RUST_ENABLED=true     Enable Rust implementation testing

Reports saved to: $REPORTS_DIR
EOF
            exit 0
            ;;
    esac

    echo ""
    echo "=========================================="
    echo "Reports saved to: $REPORTS_DIR"
    echo "=========================================="
    echo ""
}

main "$@"
