# SARK (Security Audit and Resource Kontroler)

**Enterprise-Grade MCP Governance System**

SARK provides enterprise-grade security and governance for Model Context Protocol (MCP) deployments at massive scale. This system addresses discovery, authorization, audit, runtime enforcement, and API Gateway integration—enabling safe MCP adoption across large organizations.

**Target Scale:** 50,000+ employees, 10,000+ MCP servers

## Project Status

🚀 **Phase 1 - MVP Development** - Building core control plane for 100 pilot servers

## Key Features

- **Zero-Trust MCP Architecture** with multi-layer enforcement
- **Automated Discovery** combining agentless scanning and lightweight monitoring
- **Hybrid ReBAC+ABAC Authorization** via Open Policy Agent
- **Immutable Audit Trails** with TimescaleDB
- **Dynamic Secrets Management** via HashiCorp Vault
- **Kong API Gateway Integration** for edge security
- **Comprehensive Threat Modeling** addressing MCP-specific attacks

## Requirements

- Python 3.11+
- Docker with Docker Compose v2
- Git
- PostgreSQL 15+
- Redis 7+
- Open Policy Agent 0.60+
- Kong Gateway 3.8+ (for production)
- Kubernetes 1.28+ (for production deployment)

## Development Setup

### Initial Setup

```bash
# Clone the repository
git clone <repository-url>
cd sark

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Docker Development

```bash
# Build and start services
docker compose up --build

# Run tests in container
docker compose run --rm app pytest

# Access shell in container
docker compose run --rm app bash
```

## Development Workflow

### Code Quality Standards

This project enforces strict code quality standards:

- **Formatting**: Black (line length: 100)
- **Linting**: Ruff with comprehensive rule sets
- **Type Checking**: MyPy with strict mode
- **Testing**: Pytest with coverage requirements

All checks run automatically via pre-commit hooks and CI/CD.

### Making Changes

1. Create a feature branch from main: `git checkout -b feature/your-feature-name`
2. Make your changes following the coding standards in `CONTRIBUTING.md`
3. Write tests for new functionality
4. Ensure all tests pass: `pytest`
5. Ensure code quality checks pass: `pre-commit run --all-files`
6. Commit with descriptive messages
7. Push and create a pull request

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test file
pytest tests/test_example.py

# Run tests matching pattern
pytest -k "test_pattern"

# Run only fast tests
pytest -m "not slow"
```

### Code Quality Checks

```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Format code
black src tests

# Lint code
ruff check src tests

# Type check
mypy src
```

## Project Structure

```
sark/
├── src/
│   └── sark/
│       ├── api/           # FastAPI REST API endpoints
│       ├── models/        # Database models and schemas
│       ├── services/      # Business logic services
│       │   ├── discovery/ # MCP server discovery
│       │   ├── policy/    # OPA policy integration
│       │   ├── audit/     # Audit event processing
│       │   └── vault/     # Secrets management
│       ├── config/        # Configuration management
│       └── db/            # Database connections and migrations
├── kong/                  # Kong Gateway plugins
│   └── plugins/
│       └── mcp-security/  # MCP security plugin (Lua)
├── opa/                   # Open Policy Agent policies
│   └── policies/          # Rego policy files
├── k8s/                   # Kubernetes manifests
│   ├── base/             # Base configurations
│   └── overlays/         # Environment-specific overlays
├── terraform/            # Infrastructure as Code
├── tests/                # Test files
├── docs/                 # Documentation
├── scripts/              # Utility scripts
└── docker-compose.yml    # Development environment
```

## CI/CD

### Local CI/CD Checks

Run all CI checks locally before pushing:

```bash
# Run basic CI checks (quality + tests)
make ci-local

# Run ALL CI checks (quality, tests, security, docker)
make ci-all

# Run individual check suites
make quality        # Linting, formatting, type-checking
make test          # Tests with coverage
make security      # Security scans (bandit, safety)
make docker-build-test  # Docker build verification
```

### GitHub Actions (Optional)

This project includes GitHub Actions workflows for automated CI/CD:

- **CI Pipeline**: Runs on every push and PR
  - Code quality checks (ruff, black, mypy)
  - Tests with coverage
  - Security scanning
  - Docker image builds

- **Branch Protection**: Can be configured to require:
  - All CI checks to pass
  - Code review approval
  - Up-to-date with base branch

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on:
- Code style and standards
- Commit message format
- PR process
- Multi-agent collaboration guidelines

## License

TBD
