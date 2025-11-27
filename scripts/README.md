# SARK Deployment Scripts

This directory contains automation scripts for deploying, testing, and managing SARK.

---

## Available Scripts

### Deployment

#### `deploy.sh`
**Purpose:** Automated deployment for different environments

**Usage:**
```bash
./scripts/deploy.sh [environment] [profile]
```

**Arguments:**
- `environment` - Target environment: development, staging, production
- `profile` - Docker Compose profile: minimal, standard, full

**Examples:**
```bash
# Development deployment with standard profile
./scripts/deploy.sh development standard

# Staging deployment with full stack
./scripts/deploy.sh staging full

# Production deployment (minimal profile, external services)
./scripts/deploy.sh production minimal
```

**Features:**
- Prerequisites validation
- Docker image building
- Service startup
- Health check monitoring
- Automated testing
- Production config validation

**Environment Variables:**
- `RUN_TESTS=true|false` - Enable/disable automated tests (default: true)
- `RUN_VALIDATION=true|false` - Enable/disable validation (default: true)
- `DEBUG=1` - Enable verbose output

---

### Testing

#### `test-minimal-deployment.sh`
**Purpose:** Test minimal deployment scenarios

**Usage:**
```bash
./scripts/test-minimal-deployment.sh
```

**Tests:**
1. Prerequisites check (Docker, Compose)
2. App-only deployment
3. Managed profile deployment
4. Full profile deployment
5. Quickstart deployment
6. Environment configuration
7. Resource usage check
8. Network setup validation

**Exit Codes:**
- `0` - All tests passed
- `1` - One or more tests failed

**Example:**
```bash
# Run all deployment tests
./scripts/test-minimal-deployment.sh

# View detailed output
DEBUG=1 ./scripts/test-minimal-deployment.sh
```

---

#### `test-health-checks.sh`
**Purpose:** Test all health check endpoints

**Usage:**
```bash
./scripts/test-health-checks.sh [profile]
```

**Arguments:**
- `profile` - Docker Compose profile to test (default: standard)

**Tests:**
- Basic health endpoint (`/health`)
- Readiness endpoint (`/ready`)
- Liveness endpoint (`/live`)
- Startup endpoint (`/startup`)
- Metrics endpoint (`/metrics`)
- API documentation endpoints
- Service-specific health checks (PostgreSQL, Redis, Kong)
- Response time performance

**Example:**
```bash
# Test standard profile
./scripts/test-health-checks.sh standard

# Test full profile
./scripts/test-health-checks.sh full

# Test minimal profile
./scripts/test-health-checks.sh minimal
```

---

### Validation

#### `validate-production-config.sh`
**Purpose:** Validate production configuration

**Usage:**
```bash
./scripts/validate-production-config.sh [env-file]
```

**Arguments:**
- `env-file` - Path to .env file (default: .env)

**Checks:**
- Environment configuration
- Database settings (external mode required)
- Cache settings (external mode required)
- Security configuration (passwords, secrets)
- SSL/TLS configuration
- Monitoring setup
- SIEM integration
- Authentication methods
- Resource limits

**Example:**
```bash
# Validate default .env
./scripts/validate-production-config.sh

# Validate specific environment file
./scripts/validate-production-config.sh .env.production

# Validate staging config
./scripts/validate-production-config.sh .env.staging
```

---

## Script Organization

```
scripts/
├── README.md                         # This file
├── deploy.sh                         # Main deployment automation
├── test-minimal-deployment.sh        # Deployment testing
├── test-health-checks.sh             # Health check testing
├── validate-production-config.sh     # Production validation
└── db/                               # Database scripts
    └── init/                         # Database initialization scripts
```

---

## Common Workflows

### Development Setup

```bash
# 1. Deploy development environment
./scripts/deploy.sh development standard

# 2. View logs
docker compose logs -f

# 3. Run health checks
./scripts/test-health-checks.sh standard
```

### Staging Deployment

```bash
# 1. Validate configuration
./scripts/validate-production-config.sh .env.staging

# 2. Deploy with full stack
./scripts/deploy.sh staging full

# 3. Run all tests
./scripts/test-minimal-deployment.sh
./scripts/test-health-checks.sh full
```

### Production Deployment

```bash
# 1. Validate production config
./scripts/validate-production-config.sh .env.production

# 2. Deploy (with external services)
./scripts/deploy.sh production minimal

# 3. Verify health
./scripts/test-health-checks.sh minimal

# 4. Monitor
docker compose logs -f app
```

### Testing All Profiles

```bash
# Test minimal profile
./scripts/test-health-checks.sh minimal

# Test standard profile
./scripts/test-health-checks.sh standard

# Test full profile
./scripts/test-health-checks.sh full

# Run comprehensive deployment tests
./scripts/test-minimal-deployment.sh
```

---

## Exit Codes

All scripts follow consistent exit code conventions:

- `0` - Success, all checks passed
- `1` - Failure, one or more checks failed
- `2` - Invalid arguments or usage

---

## Logging

All scripts use consistent logging with color-coded output:

- 🔵 **[INFO]** - Informational messages
- ✅ **[PASS]** - Successful checks
- ❌ **[FAIL]** - Failed checks
- ⚠️  **[WARN]** - Warnings (non-critical issues)

---

## Environment Variables

### Global Variables

- `DEBUG=1` - Enable verbose debug output
- `NO_COLOR=1` - Disable colored output

### Deployment Script Variables

- `RUN_TESTS=true|false` - Run automated tests (default: true)
- `RUN_VALIDATION=true|false` - Run configuration validation (default: true)

---

## Requirements

### Prerequisites

- Docker 24.0+
- Docker Compose v2
- bash 4.0+
- curl (for health checks)
- jq (for JSON parsing)

### Optional Tools

- `bc` - For performance calculations
- `netstat` - For port conflict checking

---

## Development

### Adding New Scripts

1. Create script in `scripts/` directory
2. Add shebang: `#!/usr/bin/env bash`
3. Set strict mode: `set -euo pipefail`
4. Use consistent logging functions
5. Add usage documentation in header
6. Make executable: `chmod +x scripts/your-script.sh`
7. Update this README

### Script Template

```bash
#!/usr/bin/env bash

# ============================================================================
# Script Name
# ============================================================================
# Brief description
#
# Usage:
#   ./scripts/your-script.sh [args]
#
# Exit codes:
#   0 - Success
#   1 - Failure
# ============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

# Main logic here
main() {
    log_info "Starting..."
    # Your code here
    log_success "Complete!"
}

main "$@"
```

---

## Troubleshooting

### Script Won't Execute

```bash
# Make script executable
chmod +x scripts/deploy.sh

# Check shebang
head -1 scripts/deploy.sh  # Should show #!/usr/bin/env bash
```

### Docker Commands Fail

```bash
# Ensure Docker is running
docker info

# Check Docker Compose version
docker compose version

# Verify user has Docker permissions
docker ps
```

### Health Checks Timeout

```bash
# Increase wait time in script
export MAX_WAIT_TIME=300  # 5 minutes

# Check container logs
docker compose logs app

# Manual health check
curl http://localhost:8000/health
```

---

## See Also

- [Deployment Guide](../docs/DEPLOYMENT.md) - Production deployment procedures
- [Docker Profiles](../docs/DOCKER_PROFILES.md) - Docker Compose profile documentation
- [Quick Start](../docs/QUICK_START.md) - Getting started guide
- [Troubleshooting](../docs/TROUBLESHOOTING.md) - Common issues and solutions

---

**Last Updated:** 2025-11-27
**Maintainer:** Engineer 4 (DevOps/Infrastructure)
