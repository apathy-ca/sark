#!/bin/bash
# Development environment setup script

set -e

echo "🚀 Setting up Sark development environment..."

# Check Python version
if ! command -v python3.11 &> /dev/null; then
    echo "❌ Python 3.11 is required but not found"
    exit 1
fi

echo "✓ Python 3.11 found"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3.11 -m venv venv
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements-dev.txt
pip install -e .

# Install pre-commit hooks
echo "🪝 Installing pre-commit hooks..."
pre-commit install
pre-commit install --hook-type commit-msg

# Run initial checks
echo "🔍 Running initial quality checks..."
pre-commit run --all-files || true

echo ""
echo "✅ Development environment setup complete!"
echo ""
echo "Next steps:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run tests: make test"
echo "  3. Start coding!"
echo ""
echo "Useful commands:"
echo "  make help          - Show all available commands"
echo "  make test          - Run tests"
echo "  make quality       - Run code quality checks"
echo "  make docker-up     - Start Docker services"
