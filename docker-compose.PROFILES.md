# Docker Compose Profiles Guide

This document explains the different Docker Compose profiles available for SARK deployment.

## Available Profiles

### 1. Minimal Profile (Quick Start - 5 Minutes)

**Use case:** Quick local development and testing

**Services included:**
- SARK Application
- PostgreSQL (database)
- Redis (cache)
- Open Policy Agent (OPA)

**Start command:**
```bash
docker compose --profile minimal up
```

**What you get:**
- ✅ Full SARK functionality
- ✅ Authentication and authorization working
- ✅ Policy evaluation via OPA
- ✅ Database and caching
- ❌ No Kong Gateway (not needed for basic testing)

**Best for:**
- New developers getting started
- Quick testing and prototyping
- Tutorial walkthroughs
- CI/CD pipelines

---

### 2. Managed Profile (Full Local Stack)

**Use case:** Complete local development environment

**Services included:**
- All services from minimal profile
- Kong API Gateway
- Kong Database (PostgreSQL)
- Kong Migrations

**Start command:**
```bash
docker compose --profile managed up
```

**What you get:**
- ✅ Everything from minimal profile
- ✅ Kong Gateway for edge security
- ✅ Production-like setup
- ✅ MCP protocol validation
- ✅ Rate limiting and routing

**Best for:**
- Testing Kong integration
- Production-like local testing
- API gateway feature development
- Load testing

---

### 3. Full Profile (Alias)

Same as `managed` profile - provided for compatibility.

```bash
docker compose --profile full up
```

---

### 4. Kong Profile (Kong Only)

**Use case:** Use Kong services with external database/redis

**Services included:**
- Kong API Gateway
- Kong Database
- Kong Migrations

**Start command:**
```bash
docker compose --profile kong up
```

**Best for:**
- Testing Kong configuration changes
- Kong plugin development
- Using external PostgreSQL/Redis

---

## Profile Comparison

| Feature | Minimal | Managed | Full | Kong Only |
|---------|---------|---------|------|-----------|
| **SARK App** | ✅ | ✅ | ✅ | ❌ |
| **PostgreSQL** | ✅ | ✅ | ✅ | ❌ |
| **Redis** | ✅ | ✅ | ✅ | ❌ |
| **OPA** | ✅ | ✅ | ✅ | ❌ |
| **Kong Gateway** | ❌ | ✅ | ✅ | ✅ |
| **Kong DB** | ❌ | ✅ | ✅ | ✅ |
| **Startup Time** | ~30 sec | ~60 sec | ~60 sec | ~45 sec |
| **Memory Usage** | ~1 GB | ~2 GB | ~2 GB | ~500 MB |
| **Containers** | 4 | 8 | 8 | 3 |

---

## Quick Start Examples

### First Time Setup (Minimal)

```bash
# 1. Clone repository
git clone <repository-url>
cd sark

# 2. Create environment file
cp .env.example .env

# 3. Start minimal stack
docker compose --profile minimal up -d

# 4. Verify services are running
docker compose ps

# 5. Access SARK API
curl http://localhost:8000/health
```

**Expected output:**
```
NAME                IMAGE                         STATUS
sark-app            sark-app:latest               Up
sark-db             postgres:15-alpine            Up (healthy)
sark-cache          redis:7-alpine                Up (healthy)
sark-opa            openpolicyagent/opa:0.60.0    Up (healthy)
```

---

### Testing with Full Stack

```bash
# Start with all services including Kong
docker compose --profile managed up -d

# Wait for all services to be healthy (may take 60 seconds)
docker compose ps

# Access via Kong Gateway
curl http://localhost:8000/health  # Via Kong
curl http://localhost:8001/         # Kong Admin API
```

---

## Service Ports

| Service | Port | Description |
|---------|------|-------------|
| SARK API | 8000 | Main application API |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache |
| OPA | 8181 | Policy engine |
| Kong Proxy | 8000 | API Gateway (conflicts with app port when using managed profile) |
| Kong Admin | 8001 | Kong administration |
| Kong Proxy SSL | 8443 | API Gateway (HTTPS) |
| Kong Admin SSL | 8444 | Kong admin (HTTPS) |

**Note:** When using `managed` profile, SARK app port may need to be changed to avoid conflict with Kong. Update `.env` with `API_PORT=8080`.

---

## Environment Variables

Key environment variables for profile configuration:

```bash
# PostgreSQL
POSTGRES_ENABLED=true          # Enable PostgreSQL integration
POSTGRES_MODE=managed          # Use managed (Docker) or external
POSTGRES_HOST=database         # Hostname (database for Docker, FQDN for external)
POSTGRES_PORT=5432
POSTGRES_DB=sark
POSTGRES_USER=sark
POSTGRES_PASSWORD=sark         # Change in production!

# Redis
REDIS_ENABLED=true
REDIS_MODE=managed
REDIS_HOST=cache
REDIS_PORT=6379
REDIS_PASSWORD=                # Empty for development, set in production

# OPA
OPA_ENABLED=true
OPA_URL=http://opa:8181
OPA_POLICY_PATH=/v1/data/mcp/allow

# Kong (only for managed/full profiles)
KONG_ENABLED=true
KONG_MODE=managed
KONG_ADMIN_URL=http://kong:8001
KONG_PROXY_URL=http://kong:8000
```

---

## Troubleshooting

### Port Conflicts

If you see errors about ports already in use:

```bash
# Check what's using the port
lsof -i :8000  # or :5432, :6379, :8181

# Stop conflicting service or change SARK port
echo "API_PORT=8080" >> .env
docker compose --profile minimal up
```

### Slow Startup

First startup downloads images and may take 2-3 minutes:

```bash
# Pull images beforehand
docker compose --profile minimal pull

# Then start (will be faster)
docker compose --profile minimal up -d
```

### Services Not Healthy

Check service logs:

```bash
# All services
docker compose logs

# Specific service
docker compose logs database
docker compose logs opa
docker compose logs app
```

### Reset Everything

To start fresh:

```bash
# Stop all containers
docker compose --profile minimal down

# Remove volumes (WARNING: deletes all data!)
docker compose --profile minimal down -v

# Start fresh
docker compose --profile minimal up -d
```

---

## External Services Mode

To use external (non-Docker) services:

1. **Edit `.env`:**
   ```bash
   # Disable managed services
   POSTGRES_MODE=external
   REDIS_MODE=external
   KONG_MODE=external

   # Point to external services
   POSTGRES_HOST=postgres.company.com
   POSTGRES_PORT=5432
   POSTGRES_PASSWORD=<secret>

   REDIS_HOST=redis.company.com
   REDIS_PORT=6379
   REDIS_PASSWORD=<secret>

   OPA_URL=http://opa.company.com:8181
   ```

2. **Start only the app:**
   ```bash
   # Don't use any profile - just runs app container
   docker compose up app
   ```

---

## Next Steps

- **Quick Start:** [docs/QUICK_START.md](../docs/QUICK_START.md)
- **Full Deployment:** [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md)
- **Kubernetes:** [k8s/README.md](../k8s/README.md)

---

**Profile recommendations:**

- 👨‍💻 **Developers:** Use `minimal` for daily work
- 🧪 **Testers:** Use `managed` for full feature testing
- 🚀 **DevOps:** Use external mode with Kubernetes
- 📚 **Tutorials:** Use `minimal` for simplicity
