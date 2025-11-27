# SARK Docker Compose Profiles

This document explains the different Docker Compose deployment profiles available for SARK.

---

## Overview

SARK provides three main deployment profiles for different use cases:

| Profile | Services | Use Case | Resource Usage |
|---------|----------|----------|----------------|
| **Minimal** | App only | External services, CI/CD | ~200MB RAM |
| **Standard** | App + PostgreSQL + Redis | Development, testing | ~300MB RAM |
| **Full** | Complete stack with Kong | Staging, demos | ~1.5GB RAM |

---

## Profile Details

### 1. Minimal (Default)

**Description:** Deploys only the SARK application without any managed services.

**Command:**
```bash
docker compose up -d
# or explicitly
docker compose --profile minimal up -d
```

**Services Included:**
- `sark-app` - SARK API application

**When to Use:**
- Connecting to existing external PostgreSQL/Redis/Kong
- CI/CD pipelines with test databases
- Lightweight development
- Resource-constrained environments

**Configuration Required:**
Configure external services in `.env`:
```env
# PostgreSQL
POSTGRES_ENABLED=true
POSTGRES_MODE=external
POSTGRES_HOST=your-postgres-host
POSTGRES_PORT=5432
POSTGRES_DB=sark
POSTGRES_USER=sark_user
POSTGRES_PASSWORD=secure_password

# Redis
REDIS_ENABLED=true
REDIS_MODE=external
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_PASSWORD=redis_password
```

**Pros:**
- ✅ Minimal resource usage (~200MB RAM)
- ✅ Fast startup (~5 seconds)
- ✅ No port conflicts
- ✅ Integrates with existing infrastructure

**Cons:**
- ❌ Requires external services to be available
- ❌ More complex configuration
- ❌ Not self-contained

---

### 2. Standard

**Description:** Deploys SARK with managed PostgreSQL and Redis. Good balance for development.

**Command:**
```bash
docker compose --profile standard up -d

# Backward compatibility alias
docker compose --profile managed up -d
```

**Services Included:**
- `sark-app` - SARK API application
- `sark-db` - PostgreSQL 15 database
- `sark-cache` - Redis 7 cache

**When to Use:**
- Local development
- Integration testing
- Team development environments
- Learning SARK

**Ports Exposed:**
- `8000` - SARK API
- `5432` - PostgreSQL
- `6379` - Redis

**Volumes Created:**
- `sark-postgres-data` - PostgreSQL data (persistent)
- `sark-redis-data` - Redis data (persistent)

**Pros:**
- ✅ Self-contained development environment
- ✅ No external services needed
- ✅ Persistent data volumes
- ✅ Easy to reset (docker compose down -v)
- ✅ Moderate resource usage (~300MB RAM)

**Cons:**
- ❌ Not suitable for production
- ❌ No API Gateway (Kong)
- ❌ No monitoring included

**Health Checks:**
- PostgreSQL: `pg_isready` check every 10 seconds
- Redis: `PING` check every 10 seconds
- Services become healthy in ~30 seconds

---

### 3. Full

**Description:** Complete SARK stack with all services including Kong API Gateway.

**Command:**
```bash
docker compose --profile full up -d
```

**Services Included:**
- `sark-app` - SARK API application
- `sark-db` - PostgreSQL 15 database
- `sark-cache` - Redis 7 cache
- `kong-database` - PostgreSQL for Kong
- `kong-migrations` - Kong database migrations
- `kong` - Kong API Gateway 3.5

**When to Use:**
- Staging environments
- Demo/evaluation
- Full integration testing
- API Gateway development
- Testing production-like setup

**Ports Exposed:**
- `8000` - Kong Proxy
- `8001` - Kong Admin API
- `8443` - Kong Proxy (SSL)
- `8444` - Kong Admin API (SSL)
- `5432` - PostgreSQL (SARK)
- `6379` - Redis

**Volumes Created:**
- `sark-postgres-data` - PostgreSQL data
- `sark-redis-data` - Redis data
- `sark-kong-data` - Kong PostgreSQL data

**Pros:**
- ✅ Production-like environment
- ✅ API Gateway for testing
- ✅ Complete feature set
- ✅ Good for demos

**Cons:**
- ❌ High resource usage (~1.5GB RAM)
- ❌ Slower startup (~90 seconds)
- ❌ Complex service dependencies
- ❌ More ports to manage

**Health Checks:**
- All services have health checks
- Kong waits for database migrations
- Full stack becomes healthy in ~90 seconds

---

## Additional Profiles

### Kong (Explicit)

Deploy only Kong services (useful for testing Kong separately):

```bash
docker compose --profile kong up -d
```

**Services:**
- `kong-database`
- `kong-migrations`
- `kong`

---

## Common Commands

### Starting Services

```bash
# Minimal (app only)
docker compose up -d

# Standard (development)
docker compose --profile standard up -d

# Full stack
docker compose --profile full up -d

# With rebuild
docker compose --profile standard up -d --build
```

### Stopping Services

```bash
# Stop services
docker compose down

# Stop and remove volumes (clean state)
docker compose down -v

# Stop specific profile
docker compose --profile full down
```

### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f app
docker compose logs -f database

# Last 100 lines
docker compose logs --tail=100 app
```

### Checking Status

```bash
# List running services
docker compose ps

# Check health
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

# Check resource usage
docker stats
```

### Database Access

```bash
# PostgreSQL (standard/full profile)
docker compose exec database psql -U sark -d sark

# Redis (standard/full profile)
docker compose exec cache redis-cli
```

---

## Profile Comparison

### Resource Requirements

| Metric | Minimal | Standard | Full |
|--------|---------|----------|------|
| RAM (idle) | ~200MB | ~300MB | ~1.5GB |
| RAM (peak) | ~400MB | ~600MB | ~2.5GB |
| CPU (idle) | <5% | <10% | <15% |
| Disk | ~100MB | ~500MB | ~2GB |
| Startup Time | ~5s | ~30s | ~90s |
| Services | 1 | 3 | 6 |

### Feature Matrix

| Feature | Minimal | Standard | Full |
|---------|---------|----------|------|
| SARK API | ✅ | ✅ | ✅ |
| PostgreSQL | ❌ External | ✅ Managed | ✅ Managed |
| Redis | ❌ External | ✅ Managed | ✅ Managed |
| Kong Gateway | ❌ External | ❌ | ✅ Managed |
| OPA | ❌ External | ❌ External | ✅ Managed |
| Monitoring | ❌ | ❌ | ✅ Optional |
| Self-contained | ❌ | ✅ | ✅ |
| Production-ready | ❌ | ❌ | ⚠️ Staging |

---

## Environment Configuration

### Standard Profile Example

Create `.env` file:

```env
# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO

# PostgreSQL (managed)
POSTGRES_ENABLED=true
POSTGRES_MODE=managed
POSTGRES_DB=sark
POSTGRES_USER=sark
POSTGRES_PASSWORD=change_me_in_production

# Redis (managed)
REDIS_ENABLED=true
REDIS_MODE=managed
REDIS_PASSWORD=  # Empty for development
```

### Minimal Profile with External Services

```env
# Environment
ENVIRONMENT=production
LOG_LEVEL=WARNING

# PostgreSQL (external)
POSTGRES_ENABLED=true
POSTGRES_MODE=external
POSTGRES_HOST=postgres.example.com
POSTGRES_PORT=5432
POSTGRES_DB=sark_production
POSTGRES_USER=sark_prod
POSTGRES_PASSWORD=super_secure_password_from_vault

# Redis (external)
REDIS_ENABLED=true
REDIS_MODE=external
REDIS_HOST=redis.example.com
REDIS_PORT=6379
REDIS_PASSWORD=redis_secure_password

# Kong (external)
KONG_ENABLED=true
KONG_MODE=external
KONG_ADMIN_URL=https://kong-admin.example.com
KONG_PROXY_URL=https://kong.example.com
KONG_ADMIN_API_KEY=kong_api_key_from_vault
```

---

## Troubleshooting

### Port Conflicts

If ports are already in use:

```env
# Change ports in .env
SARK_PORT=8001
POSTGRES_PORT=5433
REDIS_PORT=6380
```

### Services Not Starting

```bash
# Check logs
docker compose logs

# Check specific service
docker compose logs database

# Restart specific service
docker compose restart database

# Full reset
docker compose down -v
docker compose --profile standard up -d
```

### Database Connection Issues

```bash
# Verify PostgreSQL is healthy
docker compose ps database

# Check PostgreSQL logs
docker compose logs database

# Test connection
docker compose exec database pg_isready -U sark

# Connect to database
docker compose exec database psql -U sark -d sark
```

### Out of Memory

If services are killed due to OOM:

1. Increase Docker memory limit (Docker Desktop)
2. Use a lighter profile (standard instead of full)
3. Disable unnecessary services
4. Use external managed services instead

---

## Best Practices

### Development

1. **Use Standard Profile** for most development work
2. **Enable hot-reload** by mounting code volumes
3. **Use named volumes** for data persistence
4. **Clean up regularly** with `docker compose down -v`

### Testing

1. **Use Fresh Databases** for each test run
2. **Seed test data** in database init scripts
3. **Use Standard Profile** for integration tests
4. **Use Minimal Profile** for unit tests (mock services)

### Staging

1. **Use Full Profile** for staging environment
2. **Configure proper secrets** (not defaults)
3. **Enable monitoring** (Prometheus + Grafana)
4. **Test backup/restore** procedures

### Production

1. **Use Minimal Profile** with external managed services
2. **Deploy via Kubernetes** (see `helm/sark/`)
3. **Use Secrets Manager** (Vault, AWS Secrets Manager)
4. **Enable audit logging** to SIEM
5. **Configure auto-scaling** (HPA in Kubernetes)

---

## Migration Guide

### From Old Profiles to New

**Before (old profile names):**
```bash
docker compose --profile managed up -d
```

**After (new profile names):**
```bash
# 'managed' still works (alias for 'standard')
docker compose --profile standard up -d

# Or use the clearer name
docker compose --profile standard up -d
```

**No changes required** - `managed` is still supported as an alias for `standard`.

---

## Advanced Usage

### Combining Profiles

You can combine multiple profiles:

```bash
# Standard + Kong
docker compose --profile standard --profile kong up -d
```

### Selective Service Override

Start specific services:

```bash
# Start only database and cache
docker compose up -d database cache

# Start app with external services
docker compose up -d app
```

### Custom Compose Files

Override with custom compose file:

```bash
# Create docker-compose.override.yml for custom config
docker compose up -d

# Use specific override file
docker compose -f docker-compose.yml -f docker-compose.custom.yml up -d
```

---

## See Also

- [Quick Start Guide](QUICK_START.md) - Getting started with SARK
- [Deployment Guide](DEPLOYMENT.md) - Production deployment
- [Docker Deployment](DOCKER_DEPLOYMENT.md) - Docker-specific details
- [Integration Guide](deployment/INTEGRATION.md) - External services integration
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions

---

**Last Updated:** 2025-11-27
**Version:** 1.0
