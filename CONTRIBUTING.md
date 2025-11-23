# Contributing to Sark

Thank you for contributing to Sark! This document provides guidelines and standards for contributing to this project, with special consideration for multi-agent collaboration.

## Table of Contents

- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Git Workflow](#git-workflow)
- [Multi-Agent Collaboration](#multi-agent-collaboration)
- [Code Review Process](#code-review-process)
- [Testing Guidelines](#testing-guidelines)
- [Documentation Standards](#documentation-standards)

## Development Setup

### Prerequisites

- Python 3.11+
- Docker with Docker Compose v2
- Git
- Pre-commit (installed via pip)

### Initial Setup

```bash
# Clone the repository
git clone <repository-url>
cd sark

# Create and activate virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt
pip install -e .

# Install pre-commit hooks
pre-commit install
pre-commit install --hook-type commit-msg
```

### Verify Setup

```bash
# Run tests
pytest

# Run code quality checks
pre-commit run --all-files
```

## Coding Standards

### Python Style Guide

We follow **PEP 8** with the following tools and configurations:

#### Code Formatting

- **Black**: Auto-formatter with 100 character line length
  ```bash
  black src tests
  ```

#### Linting

- **Ruff**: Fast Python linter with comprehensive rules
  ```bash
  ruff check src tests
  ruff check --fix src tests  # Auto-fix issues
  ```

#### Type Checking

- **MyPy**: Strict type checking enabled
  ```bash
  mypy src
  ```

### Code Structure Standards

#### 1. Imports

Follow this import order (enforced by ruff):

```python
# Standard library imports
import os
import sys
from pathlib import Path

# Third-party imports
import numpy as np
import pandas as pd

# Local application imports
from sark.core import SomeClass
from sark.utils import helper_function
```

#### 2. Type Hints

**Required** for all functions and methods:

```python
def process_data(
    input_data: list[dict[str, Any]],
    threshold: float = 0.5,
) -> pd.DataFrame:
    """Process input data and return a DataFrame.

    Args:
        input_data: List of dictionaries containing raw data
        threshold: Filtering threshold (default: 0.5)

    Returns:
        Processed data as a pandas DataFrame

    Raises:
        ValueError: If input_data is empty
    """
    if not input_data:
        raise ValueError("input_data cannot be empty")

    # Implementation
    ...
```

#### 3. Docstrings

Use **Google-style** docstrings for all public modules, classes, and functions:

```python
class DataProcessor:
    """Processes and transforms raw data.

    This class handles data ingestion, validation, and transformation
    for the Sark application.

    Attributes:
        config: Configuration dictionary
        validator: Data validator instance

    Example:
        >>> processor = DataProcessor(config={'validate': True})
        >>> result = processor.process(data)
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the DataProcessor.

        Args:
            config: Configuration dictionary with processing options
        """
        self.config = config
```

#### 4. Error Handling

- Use specific exception types
- Always include helpful error messages
- Document exceptions in docstrings

```python
def load_config(path: Path) -> dict[str, Any]:
    """Load configuration from file.

    Args:
        path: Path to configuration file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is invalid JSON
    """
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file: {e}") from e
```

#### 5. Naming Conventions

- **Variables/Functions**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private members**: `_leading_underscore`
- **Test functions**: `test_description_of_behavior`

```python
# Good
MAX_RETRIES = 3
user_name = "alice"

class UserManager:
    def get_user_by_id(self, user_id: int) -> User:
        ...

# Bad
maxRetries = 3
UserName = "alice"

class user_manager:
    def GetUserById(self, userId: int) -> User:
        ...
```

## Git Workflow

### Branch Naming Convention

Use descriptive branch names with the following prefixes:

- `feature/` - New features
- `fix/` - Bug fixes
- `refactor/` - Code refactoring
- `docs/` - Documentation changes
- `test/` - Test additions/modifications
- `chore/` - Maintenance tasks
- `claude/` - AI agent branches (auto-generated)

Examples:
```
feature/user-authentication
fix/database-connection-timeout
refactor/api-client-structure
docs/update-installation-guide
claude/setup-python-cicd-015zYCM83v8RCWhD8JdPWMu8
```

### Commit Message Format

Follow **Conventional Commits** specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Test additions/modifications
- `build`: Build system changes
- `ci`: CI/CD changes
- `chore`: Other changes

Examples:
```
feat(auth): add JWT authentication support

Implements JSON Web Token authentication for API endpoints.
Includes token generation, validation, and refresh logic.

Closes #123

---

fix(database): resolve connection pool exhaustion

The connection pool was not properly releasing connections
after query completion, leading to exhaustion under high load.

Fixes #456

---

docs: update contributing guidelines

Add section on multi-agent collaboration and commit standards.
```

### Pull Request Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Write code following standards
   - Add/update tests
   - Update documentation

3. **Run Quality Checks**
   ```bash
   # Format code
   black src tests

   # Lint
   ruff check --fix src tests

   # Type check
   mypy src

   # Run tests
   pytest

   # Run all pre-commit checks
   pre-commit run --all-files
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

5. **Push and Create PR**
   ```bash
   git push -u origin feature/your-feature-name
   ```
   Then create PR via GitHub UI using the PR template.

6. **Address Review Comments**
   - Make requested changes
   - Push additional commits
   - Request re-review

7. **Merge**
   - Squash and merge (preferred for feature branches)
   - Rebase and merge (for clean linear history)
   - Never force push to main/master

## Multi-Agent Collaboration

### Guidelines for Multiple Agents/Contributors

When multiple AI agents or developers are working on the project simultaneously:

#### 1. Branch Coordination

- **Always** work on separate feature branches
- Never commit directly to `main`
- Use descriptive branch names that indicate the work scope
- Agent branches are prefixed with `claude/`

#### 2. Frequent Syncing

```bash
# Before starting work
git fetch origin
git pull origin main

# Rebase your feature branch on latest main
git rebase origin/main

# Resolve conflicts if any
git rebase --continue
```

#### 3. Atomic Commits

- Make small, focused commits
- Each commit should be self-contained and functional
- Easier to review and resolve conflicts

#### 4. Communication via Commits and PRs

- Use detailed commit messages
- Reference related issues and PRs
- Use PR descriptions to explain context
- Mark PRs as draft if work is incomplete

#### 5. Conflict Resolution

If you encounter merge conflicts:

```bash
# Update your branch
git fetch origin
git merge origin/main

# Resolve conflicts in files
# Edit conflicted files, keeping the correct changes

# Mark as resolved
git add .
git commit -m "fix: resolve merge conflicts with main"
```

#### 6. Interface Changes

When modifying shared interfaces or APIs:

1. Document changes in commit message
2. Update relevant documentation
3. Add deprecation warnings before removing features
4. Coordinate with other active branches

#### 7. Testing in Multi-Agent Context

- Run full test suite before pushing
- Ensure your changes don't break existing tests
- Add integration tests for cross-module interactions

## Code Review Process

### For Authors

- Ensure CI passes before requesting review
- Keep PRs focused and reasonably sized (< 500 lines preferred)
- Respond to review comments promptly
- Don't take feedback personally

### For Reviewers

Check for:
- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New tests cover new functionality
- [ ] Documentation is updated
- [ ] No security vulnerabilities
- [ ] Performance implications considered
- [ ] Breaking changes are documented

## Testing Guidelines

### Test Structure

```
tests/
├── unit/               # Unit tests
│   ├── test_core.py
│   └── test_utils.py
├── integration/        # Integration tests
│   └── test_api.py
└── conftest.py         # Shared fixtures
```

### Writing Tests

```python
import pytest
from sark.core import DataProcessor


class TestDataProcessor:
    """Tests for DataProcessor class."""

    def test_process_valid_data(self) -> None:
        """Test processing with valid data."""
        processor = DataProcessor(config={})
        data = [{"id": 1, "value": 10}]

        result = processor.process(data)

        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_process_empty_data_raises_error(self) -> None:
        """Test that empty data raises ValueError."""
        processor = DataProcessor(config={})

        with pytest.raises(ValueError, match="cannot be empty"):
            processor.process([])

    @pytest.mark.slow
    def test_process_large_dataset(self) -> None:
        """Test processing with large dataset (slow test)."""
        # Large dataset test
        ...
```

### Test Coverage

- Aim for **>80%** coverage
- Focus on critical paths
- Test edge cases and error conditions
- Use markers for slow/integration tests

```bash
# Run all tests
pytest

# Run only fast tests
pytest -m "not slow"

# Run with coverage
pytest --cov --cov-report=html

# Run specific test file
pytest tests/unit/test_core.py

# Run specific test
pytest tests/unit/test_core.py::TestDataProcessor::test_process_valid_data
```

## Documentation Standards

### Code Documentation

1. **Module docstrings** at the top of each file
2. **Class docstrings** describing purpose and usage
3. **Function/method docstrings** with Args, Returns, Raises
4. **Inline comments** for complex logic only

### Project Documentation

Update relevant docs when changing:
- Public APIs
- Configuration options
- Environment setup
- Deployment procedures

### Documentation Files

SARK maintains comprehensive operational documentation:

**Core Documentation:**
- `README.md` - Project overview and quick start
- `CONTRIBUTING.md` - This file
- `SECURITY.md` - Security policy and vulnerability reporting
- `CHANGELOG.md` - Version history and changes

**Operational Documentation** (docs/):
- `QUICK_START.md` - 15-minute getting started guide
- `API_REFERENCE.md` - Complete API documentation
- `ARCHITECTURE.md` - System architecture with diagrams
- `DEPLOYMENT.md` - Kubernetes deployment guide
- `OPERATIONS_RUNBOOK.md` - Day-to-day operational procedures
- `DISASTER_RECOVERY.md` - DR procedures and backup strategy
- `TROUBLESHOOTING.md` - Master troubleshooting guide

**Performance & Optimization:**
- `PERFORMANCE_TESTING.md` - Performance testing methodology
- `DATABASE_OPTIMIZATION.md` - Database optimization guide
- `REDIS_OPTIMIZATION.md` - Redis optimization guide

**Security:**
- `SECURITY_BEST_PRACTICES.md` - Security development practices
- `SECURITY_HARDENING.md` - Security hardening checklist
- `INCIDENT_RESPONSE.md` - Incident response playbooks

**Project Documentation:**
- `PHASE2_COMPLETION_REPORT.md` - Phase 2 summary
- `DEVELOPMENT_LOG.md` - Complete development history
- `PRODUCTION_HANDOFF.md` - Production deployment handoff
- `KNOWN_ISSUES.md` - Known issues and limitations

**Complete documentation index**: See `docs/PHASE2_COMPLETION_REPORT.md` for full documentation suite.

### Documentation Standards

When contributing documentation:
1. Follow existing templates and structure
2. Include code examples that actually work
3. Add diagrams for complex flows (use Mermaid)
4. Cross-reference related documentation
5. Test all commands and procedures
6. Update table of contents

## Additional Resources

- [PEP 8 - Style Guide](https://pep8.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)

## Questions?

If you have questions about contributing:
1. Check existing issues and PRs
2. Review this document thoroughly
3. Create an issue with your question

---

**Thank you for contributing to Sark!**
