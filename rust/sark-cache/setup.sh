#!/usr/bin/env bash
set -euo pipefail

# Setup script for SARK Rust Cache build environment

echo "=== SARK Rust Cache Build Setup ==="
echo ""

# Check if Rust is installed
if ! command -v cargo &> /dev/null; then
    echo "❌ Rust is not installed"
    echo ""
    echo "Please install Rust using one of these methods:"
    echo ""
    echo "1. Using rustup (recommended):"
    echo "   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
    echo ""
    echo "2. Using package manager:"
    echo "   - Ubuntu/Debian: sudo apt install cargo rustc"
    echo "   - macOS: brew install rust"
    echo ""
    exit 1
else
    RUST_VERSION=$(cargo --version)
    echo "✓ Rust installed: $RUST_VERSION"
fi

# Check Rust version
RUST_MIN_VERSION="1.70.0"
RUST_CURRENT=$(cargo --version | grep -oP '\d+\.\d+\.\d+')

if ! printf '%s\n' "$RUST_MIN_VERSION" "$RUST_CURRENT" | sort -V -C; then
    echo "❌ Rust version $RUST_CURRENT is too old (need >= $RUST_MIN_VERSION)"
    echo "   Run: rustup update"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
else
    PYTHON_VERSION=$(python3 --version)
    echo "✓ Python installed: $PYTHON_VERSION"
fi

# Check/install maturin
if ! command -v maturin &> /dev/null; then
    echo "⚠️  Maturin is not installed"
    echo "   Installing maturin..."
    pip install maturin
    if [ $? -eq 0 ]; then
        echo "✓ Maturin installed successfully"
    else
        echo "❌ Failed to install maturin"
        exit 1
    fi
else
    MATURIN_VERSION=$(maturin --version)
    echo "✓ Maturin installed: $MATURIN_VERSION"
fi

echo ""
echo "=== Build Environment Ready ==="
echo ""
echo "Next steps:"
echo "1. cargo test          # Run Rust tests"
echo "2. cargo build --release  # Build optimized Rust library"
echo "3. maturin develop --release  # Build Python extension"
echo ""
