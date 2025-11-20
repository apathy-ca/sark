.PHONY: help install install-dev test lint format type-check clean docker-build docker-up docker-down pre-commit

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install --upgrade pip
	pip install -r requirements.txt
	pip install -e .

install-dev: ## Install development dependencies
	pip install --upgrade pip
	pip install -r requirements-dev.txt
	pip install -e .
	pre-commit install
	pre-commit install --hook-type commit-msg

test: ## Run tests with coverage
	pytest --cov --cov-report=term-missing --cov-report=html

test-fast: ## Run tests without slow tests
	pytest -m "not slow" --cov

test-verbose: ## Run tests with verbose output
	pytest -vv --cov

lint: ## Run linting checks
	ruff check src tests

lint-fix: ## Run linting checks and fix issues
	ruff check --fix src tests

format: ## Format code with black
	black src tests

format-check: ## Check code formatting without changes
	black --check src tests

type-check: ## Run type checking with mypy
	mypy src

quality: lint format-check type-check ## Run all code quality checks

pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

clean: ## Clean up generated files
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete

docker-build: ## Build Docker images
	docker compose build

docker-up: ## Start Docker services
	docker compose up -d

docker-down: ## Stop Docker services
	docker compose down

docker-test: ## Run tests in Docker
	docker compose run --rm app pytest

docker-shell: ## Open shell in Docker container
	docker compose run --rm app bash

docker-clean: ## Clean Docker containers and volumes
	docker compose down -v
	docker system prune -f

ci-local: quality test ## Run CI checks locally

setup-dev: install-dev ## Complete development setup
	@echo "Development environment setup complete!"
	@echo "Run 'make test' to verify everything works"
