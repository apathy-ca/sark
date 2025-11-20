# Development Guide

## Quick Start

```bash
# Clone and setup
git clone <repository-url>
cd sark
bash scripts/setup.sh

# Activate environment
source venv/bin/activate

# Run tests
make test
```

## Development Workflow

### Daily Development

1. **Start your work**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/your-feature
   ```

2. **Make changes**
   - Write code following standards in CONTRIBUTING.md
   - Add tests as you go
   - Run `make quality` frequently

3. **Test your changes**
   ```bash
   make test           # Run all tests
   make test-fast      # Skip slow tests
   make quality        # All quality checks
   ```

4. **Commit**
   ```bash
   git add .
   git commit -m "feat: your feature description"
   ```

5. **Push and create PR**
   ```bash
   git push -u origin feature/your-feature
   # Create PR via GitHub UI
   ```

### Using Docker

```bash
# Build and start services
make docker-build
make docker-up

# Run tests in Docker
make docker-test

# Access container shell
make docker-shell

# Stop services
make docker-down
```

## Code Quality Tools

### Formatting with Black

```bash
# Format all code
black src tests

# Check formatting without changes
black --check src tests

# Or use Make
make format
make format-check
```

### Linting with Ruff

```bash
# Check for issues
ruff check src tests

# Auto-fix issues
ruff check --fix src tests

# Or use Make
make lint
make lint-fix
```

### Type Checking with MyPy

```bash
# Type check source code
mypy src

# Or use Make
make type-check
```

### All Checks at Once

```bash
# Run all quality checks
make quality

# Run pre-commit on all files
make pre-commit
```

## Testing

### Running Tests

```bash
# All tests with coverage
pytest

# Fast tests only (skip slow tests)
pytest -m "not slow"

# Specific test file
pytest tests/test_example.py

# Specific test function
pytest tests/test_example.py::test_version

# With verbose output
pytest -vv

# Or use Make
make test
make test-fast
make test-verbose
```

### Writing Tests

See examples in `tests/test_example.py`.

Key points:
- Use type hints
- Write clear test names
- Use fixtures for shared setup
- Mark slow tests with `@pytest.mark.slow`
- Aim for >80% coverage

### Test Markers

```python
@pytest.mark.slow
def test_slow_operation():
    ...

@pytest.mark.integration
def test_api_integration():
    ...

@pytest.mark.unit
def test_pure_function():
    ...
```

## Project Structure

```
sark/
├── src/sark/              # Source code
│   ├── __init__.py
│   └── ...                # Add modules here
├── tests/                 # Test files
│   ├── __init__.py
│   ├── conftest.py        # Shared fixtures
│   └── test_*.py          # Test files
├── docker/                # Docker-related files
├── .github/               # GitHub Actions workflows
├── docs/                  # Documentation
├── scripts/               # Utility scripts
├── pyproject.toml         # Project configuration
├── docker-compose.yml     # Docker Compose config
├── Makefile               # Common commands
└── README.md
```

## Common Tasks

### Adding a New Module

1. Create module in `src/sark/`
2. Add tests in `tests/`
3. Update documentation if needed
4. Run quality checks
5. Commit and push

### Adding a New Dependency

1. Add to `requirements.txt` (production) or `requirements-dev.txt` (dev)
2. Add to `pyproject.toml` if needed
3. Update Docker image if needed
4. Run `pip install -r requirements-dev.txt`
5. Update documentation

### Debugging

```bash
# Use ipdb for debugging
import ipdb; ipdb.set_trace()

# Or use pytest's pdb
pytest --pdb

# Run specific test with verbose output
pytest -vv -s tests/test_example.py::test_name
```

### Working with Docker

```bash
# Rebuild after dependency changes
docker compose build --no-cache

# View logs
docker compose logs -f app

# Execute command in running container
docker compose exec app pytest

# Clean up everything
make docker-clean
```

## Troubleshooting

### Pre-commit hooks failing

```bash
# Run hooks manually to see errors
pre-commit run --all-files

# Update hooks
pre-commit autoupdate

# Skip hooks temporarily (not recommended)
git commit --no-verify
```

### Import errors

```bash
# Ensure package is installed in editable mode
pip install -e .

# Check PYTHONPATH
echo $PYTHONPATH

# In Docker, PYTHONPATH is set in docker-compose.yml
```

### Type checking errors

```bash
# Run mypy with verbose output
mypy --show-error-codes src

# Ignore specific errors (use sparingly)
# Add to code:
x = some_call()  # type: ignore[error-code]
```

## Tips and Best Practices

1. **Run tests frequently** - Don't wait until the end
2. **Use Make commands** - They're shortcuts for common tasks
3. **Follow the style guide** - Pre-commit hooks enforce this
4. **Write tests first** - TDD helps design better code
5. **Keep PRs small** - Easier to review and merge
6. **Document as you go** - Don't leave it for later
7. **Use type hints** - They catch bugs early

## Resources

- [README.md](../README.md) - Project overview
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [Makefile](../Makefile) - Available commands
