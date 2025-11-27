.PHONY: help install install-dev test lint format type-check clean docker-build docker-up docker-down pre-commit run

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

run: ## Run SARK API server locally
	uvicorn sark.api.main:app --reload --host 0.0.0.0 --port 8000

docker-build: ## Build Docker images
	docker compose build

docker-up: ## Start Docker services (minimal profile - app only)
	docker compose up -d

docker-up-standard: ## Start Docker services (standard profile - app + PostgreSQL + Redis)
	docker compose --profile standard up -d

docker-up-full: ## Start Docker services (full profile - complete stack)
	docker compose --profile full up -d

docker-down: ## Stop Docker services
	docker compose down

# Development environment commands
dev-up: ## Start development environment (frontend + backend + database)
	docker compose -f docker-compose.dev.yml up -d

dev-up-build: ## Start development environment with rebuild
	docker compose -f docker-compose.dev.yml up -d --build

dev-down: ## Stop development environment
	docker compose -f docker-compose.dev.yml down

dev-logs: ## View development environment logs
	docker compose -f docker-compose.dev.yml logs -f

dev-logs-frontend: ## View frontend dev logs only
	docker compose -f docker-compose.dev.yml logs -f frontend-dev

dev-logs-api: ## View API dev logs only
	docker compose -f docker-compose.dev.yml logs -f app

dev-shell-frontend: ## Open shell in frontend dev container
	docker compose -f docker-compose.dev.yml exec frontend-dev sh

dev-shell-api: ## Open shell in API dev container
	docker compose -f docker-compose.dev.yml exec app bash

dev-restart: ## Restart development environment
	docker compose -f docker-compose.dev.yml restart

dev-clean: ## Clean development environment (remove volumes)
	docker compose -f docker-compose.dev.yml down -v

docker-test: ## Run tests in Docker
	docker compose run --rm app pytest

docker-shell: ## Open shell in Docker container
	docker compose run --rm app bash

docker-logs: ## View Docker logs
	docker compose logs -f

docker-ps: ## Show running containers
	docker compose ps

docker-clean: ## Clean Docker containers and volumes
	docker compose down -v
	docker system prune -f

security: ## Run security scans (bandit, safety)
	@echo "Running security scans..."
	bandit -r src -f json -o bandit-report.json || true
	@echo "Bandit report saved to bandit-report.json"
	safety check --json || true

docker-build-test: ## Test Docker builds (dev and prod)
	@echo "Testing development Docker build..."
	docker compose build
	@echo "Testing production Docker build..."
	docker build --target production -t sark:prod-test .

# Database commands
db-shell: ## Connect to PostgreSQL database
	docker compose exec postgres psql -U sark sark

audit-db-shell: ## Connect to TimescaleDB audit database
	docker compose exec timescaledb psql -U sark sark_audit

# OPA commands
opa-test: ## Test OPA policies
	docker compose exec opa opa test /policies -v

opa-check: ## Check OPA policy syntax
	docker compose exec opa opa check /policies

# Kubernetes commands
k8s-deploy: ## Deploy to Kubernetes
	kubectl apply -f k8s/base/namespace.yaml
	kubectl apply -f k8s/base/opa-deployment.yaml
	kubectl apply -f k8s/base/deployment.yaml

k8s-status: ## Check Kubernetes deployment status
	kubectl get all -n sark-system

k8s-logs: ## View Kubernetes logs
	kubectl logs -f deployment/sark-api -n sark-system

k8s-delete: ## Delete Kubernetes resources
	kubectl delete -f k8s/base/deployment.yaml
	kubectl delete -f k8s/base/opa-deployment.yaml
	kubectl delete -f k8s/base/namespace.yaml

ci-local: quality test ## Run basic CI checks locally (quality + tests)

ci-all: quality test security docker-build-test ## Run all CI checks locally (quality, tests, security, docker)
	@echo ""
	@echo "========================================="
	@echo "All CI checks completed!"
	@echo "========================================="
	@echo "✓ Code quality (lint, format, type-check)"
	@echo "✓ Tests with coverage"
	@echo "✓ Security scans"
	@echo "✓ Docker builds"
	@echo ""

setup-dev: install-dev ## Complete development setup
	@echo "Development environment setup complete!"
	@echo "Run 'make test' to verify everything works"

dev: docker-up run ## Start dependencies and run API locally

# Documentation commands
docs-build: ## Build documentation site
	mkdocs build --strict

docs-serve: ## Serve documentation locally
	mkdocs serve

docs-deploy: ## Deploy documentation to GitHub Pages
	mkdocs gh-deploy --force

docs-clean: ## Clean documentation build artifacts
	rm -rf site/

docs-check: ## Check documentation for broken links
	mkdocs build --strict
	@echo "Documentation build successful - no broken links found"
