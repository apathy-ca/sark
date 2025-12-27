# Installation Guide

This guide provides detailed installation instructions for SARK in various environments.

## Quick Install

For the fastest way to get started, see the [Quick Start Guide](QUICK_START.md).

## System Requirements

### Minimum Requirements

- **CPU:** 2 cores
- **RAM:** 4GB
- **Disk:** 20GB
- **OS:** Linux (Ubuntu 22.04+, RHEL 8+, Debian 11+)

### Recommended Requirements (Production)

- **CPU:** 8+ cores
- **RAM:** 16GB+
- **Disk:** 100GB+ SSD
- **OS:** Linux (Ubuntu 22.04 LTS or RHEL 8+)

### Software Dependencies

- Python 3.11+
- Docker 24.0+ with Docker Compose v2
- PostgreSQL 15+
- Redis 7+
- Open Policy Agent 0.60+
- Kong Gateway 3.8+ (for production)

## Installation Methods

### Method 1: Docker Compose (Recommended for Development)

Docker Compose is the easiest way to get started with SARK.

#### Step 1: Clone the Repository

```bash
git clone https://github.com/apathy-ca/sark.git
cd sark
```

#### Step 2: Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
nano .env
```

#### Step 3: Start Services

```bash
# Start with minimal profile (app only)
docker compose up -d

# Start with managed services (PostgreSQL, Redis)
docker compose --profile managed up -d

# Start with all services (includes Kong)
docker compose --profile full up -d
```

#### Step 4: Verify Installation

```bash
# Check service health
curl http://localhost:8000/health

# View logs
docker compose logs -f
```

### Method 2: Kubernetes (Production)

For production deployments, use Kubernetes with Helm or kubectl.

#### Prerequisites

- Kubernetes 1.28+
- kubectl configured
- Helm 3+ (if using Helm)

#### Option A: Using Helm

```bash
# Install SARK with Helm
helm install sark ./helm/sark \
  --namespace production \
  --create-namespace \
  --values custom-values.yaml
```

#### Option B: Using kubectl

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/base/namespace.yaml
kubectl apply -f k8s/base/configmap.yaml
kubectl apply -f k8s/base/deployment.yaml
kubectl apply -f k8s/base/service.yaml
kubectl apply -f k8s/base/ingress.yaml
```

See [Deployment Guide](DEPLOYMENT.md) for complete Kubernetes setup.

### Method 3: Local Development

For local development without Docker:

#### Step 1: Install Python Dependencies

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

#### Step 2: Set Up External Services

You'll need PostgreSQL, Redis, and OPA running. You can use Docker for these:

```bash
# Start only infrastructure services
docker compose up -d postgres redis opa timescaledb
```

#### Step 3: Run SARK

```bash
# Run with uvicorn
uvicorn sark.api.main:app --reload --host 0.0.0.0 --port 8000

# Or use make
make run
```

## Post-Installation

### Initialize Database

```bash
# Run migrations
docker compose exec app alembic upgrade head

# Or if running locally
alembic upgrade head
```

### Configure Authentication

1. **OIDC Setup**: See [OIDC Setup Guide](OIDC_SETUP.md)
2. **LDAP Setup**: See [LDAP Setup Guide](LDAP_SETUP.md)
3. **SAML Setup**: See [SAML Setup Guide](SAML_SETUP.md)
4. **API Keys**: See [API Keys Guide](API_KEYS.md)

### Load Default Policies

```bash
# Load default OPA policies
docker compose exec app python -m sark.cli policies load

# Or use the API
curl -X POST http://localhost:8000/api/v1/policies/reload
```

### Verify Installation

```bash
# Check health endpoints
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/metrics

# Test authentication (LDAP example)
curl -X POST http://localhost:8000/api/v1/auth/login/ldap \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

## Troubleshooting

### Common Issues

#### Port Conflicts

If ports 8000, 5432, or 6379 are already in use:

```bash
# Check what's using the port
lsof -i :8000

# Change ports in .env file
SARK_PORT=8001
POSTGRES_PORT=5433
VALKEY_PORT=6380
```

#### Permission Issues

```bash
# Fix file permissions
chmod +x scripts/*.sh

# Fix Docker socket permissions
sudo usermod -aG docker $USER
newgrp docker
```

#### Database Connection Failed

```bash
# Check PostgreSQL is running
docker compose ps postgres

# View PostgreSQL logs
docker compose logs postgres

# Test connection
docker compose exec postgres psql -U sark -c "SELECT 1"
```

### Getting Help

- Check [Troubleshooting Guide](TROUBLESHOOTING.md)
- Review [FAQ](FAQ.md)
- Open an [issue on GitHub](https://github.com/apathy-ca/sark/issues)

## Next Steps

After installation:

1. **Configure**: Review [Configuration Guide](PRODUCTION_CONFIG.md)
2. **Deploy**: Follow [Deployment Guide](DEPLOYMENT.md) for production
3. **Monitor**: Set up [Monitoring](MONITORING.md)
4. **Secure**: Apply [Security Hardening](SECURITY_HARDENING.md)
5. **Test**: Run through [Quick Start](QUICK_START.md) examples

## Updating SARK

### Docker Compose

```bash
# Pull latest images
docker compose pull

# Restart services
docker compose up -d

# Run migrations
docker compose exec app alembic upgrade head
```

### Kubernetes

```bash
# Update Helm release
helm upgrade sark ./helm/sark

# Or using kubectl
kubectl apply -f k8s/base/

# Monitor rollout
kubectl rollout status deployment/sark-api -n sark-system
```

### Local Development

```bash
# Pull latest code
git pull origin main

# Update dependencies
pip install -e ".[dev]"

# Run migrations
alembic upgrade head
```

## Uninstalling

### Docker Compose

```bash
# Stop and remove containers
docker compose down

# Remove volumes (WARNING: deletes all data)
docker compose down -v

# Remove images
docker compose down --rmi all
```

### Kubernetes

```bash
# Using Helm
helm uninstall sark -n production

# Using kubectl
kubectl delete -f k8s/base/
kubectl delete namespace sark-system
```

### Local Development

```bash
# Deactivate virtual environment
deactivate

# Remove virtual environment
rm -rf venv

# Remove generated files
make clean
```
