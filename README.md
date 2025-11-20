# Sark

A large Python application built with Python 3.11.

## Project Status

🚧 **In Development** - Project structure and CI/CD setup complete, awaiting design document.

## Features

- **🔌 Enterprise Integration**: Connect to existing Kong, PostgreSQL, and Redis deployments
- **🐳 Flexible Deployment**: Support for both managed (Docker Compose) and external services
- **⚙️ Configuration Management**: Environment-based configuration with validation
- **🔒 Security**: Built-in SSL/TLS support, connection pooling, and secrets management
- **📊 Health Checks**: Comprehensive service connectivity testing
- **🏢 Enterprise-Ready**: Support for Kong Enterprise, Redis Sentinel, and PostgreSQL HA

## Requirements

- Python 3.11+
- Docker with Docker Compose v2
- Git

### Optional (for external services)
- Access to existing Kong API Gateway
- PostgreSQL database credentials
- Redis cache credentials

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
# Build and start services (app only, using external services)
docker compose up --build

# Start with managed PostgreSQL and Redis
docker compose --profile managed up --build

# Start with all managed services (Kong included)
docker compose --profile full up --build

# Run tests in container
docker compose run --rm app pytest

# Access shell in container
docker compose run --rm app bash
```

### Enterprise Integration Setup

SARK can integrate with existing Kong, PostgreSQL, and Redis deployments. See the [Quick Start Guide](docs/deployment/QUICKSTART.md) for detailed instructions.

#### Quick Example: Connect to Existing Services

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` to configure external services:
   ```bash
   # PostgreSQL
   POSTGRES_ENABLED=true
   POSTGRES_MODE=external
   POSTGRES_HOST=postgres.example.com
   POSTGRES_PASSWORD=your_password

   # Redis
   REDIS_ENABLED=true
   REDIS_MODE=external
   REDIS_HOST=redis.example.com
   REDIS_PASSWORD=your_password

   # Kong
   KONG_ENABLED=true
   KONG_MODE=external
   KONG_ADMIN_URL=https://kong-admin.example.com
   KONG_ADMIN_API_KEY=your_api_key
   ```

3. Start the application:
   ```bash
   docker compose up app
   ```

**📚 Documentation:**
- [Quick Start Guide](docs/deployment/QUICKSTART.md) - Get started in 5 minutes
- [Integration Guide](docs/deployment/INTEGRATION.md) - Complete reference for enterprise deployments

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
│   └── sark/          # Main application code
├── tests/             # Test files
├── docker/            # Docker-related files
├── .github/           # GitHub Actions workflows
├── docs/              # Documentation
├── scripts/           # Utility scripts
├── pyproject.toml     # Project configuration
├── docker-compose.yml # Docker Compose configuration
└── README.md          # This file
```

## CI/CD

This project uses GitHub Actions for continuous integration and deployment:

- **CI Pipeline**: Runs on every push and PR
  - Code quality checks (ruff, black, mypy)
  - Tests with coverage
  - Build verification
  - Docker image builds

- **Branch Protection**: Main branch requires:
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
