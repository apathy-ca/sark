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

# ============================================================================
# Home Deployment Commands
# ============================================================================
# Lightweight deployment profile for home routers (OPNsense, 512MB RAM)
# Uses SQLite, embedded OPA, and in-memory caching
# ============================================================================

.PHONY: home-up home-down home-logs home-shell home-status home-restart home-clean home-build home-init

HOME_COMPOSE := docker compose -f docker-compose.home.yml

home-init: ## Initialize home deployment directories and default config
	@echo "Initializing SARK home deployment..."
	@mkdir -p data/db data/policies data/certs data/config data/logs
	@if [ ! -f .env.home ]; then \
		cp .env.home.example .env.home 2>/dev/null || echo "# SARK Home Configuration" > .env.home; \
		echo "Created .env.home from template"; \
	fi
	@echo "Home deployment initialized. Run 'make home-up' to start."

home-build: ## Build SARK home Docker image
	@echo "Building SARK home image..."
	$(HOME_COMPOSE) build

home-up: ## Start SARK home deployment
	@echo "Starting SARK home deployment..."
	@mkdir -p data/db data/policies data/certs data/logs
	$(HOME_COMPOSE) up -d
	@echo ""
	@echo "SARK Home is starting..."
	@echo "  HTTPS Proxy: https://localhost:$${SARK_HOME_HTTPS_PORT:-8443}"
	@echo "  Health:      http://localhost:$${SARK_HOME_HEALTH_PORT:-9090}/health"
	@echo ""
	@echo "Run 'make home-logs' to view logs"
	@echo "Run 'make home-status' to check status"

home-up-build: ## Start SARK home deployment with rebuild
	@echo "Building and starting SARK home deployment..."
	$(HOME_COMPOSE) up -d --build

home-down: ## Stop SARK home deployment
	@echo "Stopping SARK home deployment..."
	$(HOME_COMPOSE) down

home-logs: ## View SARK home logs (follow mode)
	$(HOME_COMPOSE) logs -f

home-logs-tail: ## View last 100 lines of SARK home logs
	$(HOME_COMPOSE) logs --tail=100

home-shell: ## Open shell in SARK home container
	$(HOME_COMPOSE) exec sark-home /bin/sh

home-status: ## Check SARK home deployment status
	@echo "=== Container Status ==="
	$(HOME_COMPOSE) ps
	@echo ""
	@echo "=== Health Check ==="
	@curl -sf http://localhost:$${SARK_HOME_HEALTH_PORT:-9090}/health 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "Service not responding (may still be starting)"
	@echo ""
	@echo "=== Resource Usage ==="
	@docker stats --no-stream sark-home 2>/dev/null || echo "Container not running"

home-restart: ## Restart SARK home deployment
	@echo "Restarting SARK home deployment..."
	$(HOME_COMPOSE) restart

home-clean: ## Clean SARK home deployment (remove containers and volumes)
	@echo "Cleaning SARK home deployment..."
	$(HOME_COMPOSE) down -v
	@echo "Home deployment cleaned. Data volumes removed."

home-db-shell: ## Connect to SARK home SQLite database
	$(HOME_COMPOSE) exec sark-home sqlite3 /var/db/sark/home.db

home-audit-shell: ## Connect to SARK home audit SQLite database
	$(HOME_COMPOSE) exec sark-home sqlite3 /var/db/sark/audit.db

home-config: ## Show current SARK home configuration
	@echo "=== SARK Home Configuration ==="
	@echo "Environment file: .env.home"
	@echo ""
	@if [ -f .env.home ]; then \
		cat .env.home | grep -v "^#" | grep -v "^$$"; \
	else \
		echo "No .env.home file found. Run 'make home-init' to create one."; \
	fi

# Kubernetes commands
k8s-deploy: ## Deploy to Kubernetes using Kustomize
	kubectl apply -k k8s/base

k8s-deploy-prod: ## Deploy to production using Kustomize overlay
	kubectl apply -k k8s/overlays/production

k8s-status: ## Check Kubernetes deployment status
	kubectl get all -n sark

k8s-logs: ## View backend API logs
	kubectl logs -f deployment/sark-api -n sark

k8s-logs-frontend: ## View frontend logs
	kubectl logs -f -n sark -l app.kubernetes.io/component=frontend

k8s-delete: ## Delete Kubernetes resources
	kubectl delete -k k8s/base

k8s-shell-frontend: ## Open shell in frontend pod
	kubectl exec -it -n sark deployment/sark-frontend -- sh

k8s-shell-api: ## Open shell in API pod
	kubectl exec -it -n sark deployment/sark-api -- bash

# Helm commands
helm-install: ## Install SARK using Helm
	helm install sark ./helm/sark --namespace sark --create-namespace

helm-install-prod: ## Install SARK using Helm with production values
	helm install sark ./helm/sark \
		--namespace sark \
		--create-namespace \
		--set frontend.enabled=true \
		--set ingress.enabled=true

helm-upgrade: ## Upgrade SARK Helm release
	helm upgrade sark ./helm/sark --namespace sark

helm-uninstall: ## Uninstall SARK Helm release
	helm uninstall sark --namespace sark

helm-status: ## Check Helm release status
	helm status sark --namespace sark

helm-test: ## Test Helm chart
	helm lint ./helm/sark
	helm template sark ./helm/sark

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

# Frontend commands
frontend-build: ## Build production frontend Docker image
	cd frontend && docker build \
		--target production \
		--build-arg VITE_API_URL=${VITE_API_URL:-http://localhost:8000} \
		--build-arg VITE_APP_VERSION=$$(git describe --tags --always) \
		--build-arg VITE_APP_NAME=SARK \
		-t sark-frontend:latest \
		-t sark-frontend:$$(git describe --tags --always) \
		.

frontend-build-dev: ## Build development frontend Docker image
	cd frontend && docker build \
		-f Dockerfile.dev \
		-t sark-frontend:dev \
		.

frontend-up: ## Start frontend service (production)
	docker compose --profile standard up -d frontend

frontend-down: ## Stop frontend service
	docker compose stop frontend
	docker compose rm -f frontend

frontend-logs: ## View frontend logs
	docker compose logs -f frontend

frontend-shell: ## Open shell in frontend container
	docker compose exec frontend sh

frontend-restart: ## Restart frontend service
	docker compose restart frontend

frontend-clean: ## Clean frontend containers and images
	docker compose down frontend
	docker rmi sark-frontend:latest sark-frontend:dev 2>/dev/null || true
