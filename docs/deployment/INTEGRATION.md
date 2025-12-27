# Integrating SARK with Existing Enterprise Deployments

This guide explains how to integrate SARK with existing Kong, PostgreSQL, and Redis deployments in enterprise environments.

## Table of Contents

- [Overview](#overview)
- [Deployment Modes](#deployment-modes)
- [Quick Start](#quick-start)
- [Service-Specific Integration](#service-specific-integration)
  - [Kong API Gateway](#kong-api-gateway-integration)
  - [PostgreSQL Database](#postgresql-database-integration)
  - [Redis Cache](#redis-cache-integration)
- [Configuration Reference](#configuration-reference)
- [Security Best Practices](#security-best-practices)
- [Troubleshooting](#troubleshooting)
- [Examples](#examples)

---

## Overview

SARK supports two deployment modes for each service:

1. **Managed Mode**: Services deployed via Docker Compose (default, for development)
2. **External Mode**: Connect to existing enterprise deployments

You can mix modes - for example, use managed PostgreSQL locally while connecting to an external Kong gateway.

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    SARK Application                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Database   │  │    Cache     │  │  API Gateway │  │
│  │   Manager    │  │   Manager    │  │    Client    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                 │                 │          │
└─────────┼─────────────────┼─────────────────┼──────────┘
          │                 │                 │
          ├─────────────────┼─────────────────┤
          │                 │                 │
    ┌─────▼─────┐     ┌─────▼─────┐     ┌─────▼─────┐
    │           │     │           │     │           │
    │ Managed   │     │ Managed   │     │ Managed   │
    │ PostgreSQL│ OR  │   Redis   │ OR  │   Kong    │
    │ (Docker)  │     │ (Docker)  │     │ (Docker)  │
    │           │     │           │     │           │
    └───────────┘     └───────────┘     └───────────┘
          │                 │                 │
          │                 │                 │
    ┌─────▼─────┐     ┌─────▼─────┐     ┌─────▼─────┐
    │           │     │           │     │           │
    │ External  │     │ External  │     │ External  │
    │ PostgreSQL│     │   Redis   │     │   Kong    │
    │ (Existing)│     │ (Existing)│     │ (Existing)│
    │           │     │           │     │           │
    └───────────┘     └───────────┘     └───────────┘
```

---

## Deployment Modes

### Managed Mode (Default)

Services are deployed locally using Docker Compose.

**Pros:**
- Easy local development
- No external dependencies
- Complete control over configuration
- Quick setup

**Cons:**
- Not suitable for production
- Limited scalability
- No high availability

**Use Cases:**
- Local development
- Testing
- CI/CD pipelines

### External Mode

Connect to existing enterprise deployments.

**Pros:**
- Production-ready
- Enterprise security and compliance
- High availability
- Centralized management
- Shared resources across teams

**Cons:**
- Requires network access to services
- May need credentials from IT/DevOps team
- Configuration more complex

**Use Cases:**
- Production deployments
- Staging environments
- Integration with existing infrastructure

---

## Quick Start

### 1. Choose Your Deployment Mode

Copy the example environment file:

```bash
cp .env.example .env
```

### 2. Configure Services

Edit `.env` and set the mode for each service:

```bash
# Example: Use all managed services (development)
POSTGRES_ENABLED=true
POSTGRES_MODE=managed
VALKEY_ENABLED=true
VALKEY_MODE=managed
KONG_ENABLED=true
KONG_MODE=managed
```

### 3. Start Services

For managed services:

```bash
# Start all managed services
docker-compose --profile full up -d

# Or start only specific services
docker-compose --profile managed up -d  # DB + Redis
docker-compose --profile kong up -d     # Kong only
```

For external services, no Docker services needed - just configure the connection details in `.env`.

---

## Service-Specific Integration

## Kong API Gateway Integration

Kong is an enterprise-grade API gateway for managing, securing, and scaling APIs.

### Prerequisites

Before connecting to an existing Kong deployment, gather:

- Kong Admin API URL (e.g., `https://kong-admin.example.com`)
- Kong Proxy URL (e.g., `https://api.example.com`)
- Admin API key or RBAC token (for Kong Enterprise)
- Workspace name (for Kong Enterprise)
- SSL certificate information (if using custom CA)

### Configuration

#### Managed Kong (Development)

```bash
# .env
KONG_ENABLED=true
KONG_MODE=managed
KONG_ADMIN_URL=http://kong:8001
KONG_PROXY_URL=http://kong:8000
KONG_DB_PASSWORD=your_secure_password
```

Start Kong:

```bash
docker-compose --profile kong up -d
```

Access Kong Admin API:
- Admin API: http://localhost:8001
- Proxy: http://localhost:8000

#### External Kong (Enterprise)

```bash
# .env
KONG_ENABLED=true
KONG_MODE=external

# Kong URLs
KONG_ADMIN_URL=https://kong-admin.example.com
KONG_PROXY_URL=https://api.example.com

# Authentication (required for production)
KONG_ADMIN_API_KEY=your_admin_api_key_here

# Kong Enterprise workspace
KONG_WORKSPACE=production

# SSL settings
KONG_VERIFY_SSL=true
KONG_TIMEOUT=60
KONG_RETRIES=5
```

#### External Kong Enterprise with RBAC

For Kong Enterprise with Role-Based Access Control:

```bash
# .env
KONG_ENABLED=true
KONG_MODE=external
KONG_ADMIN_URL=https://kong-admin.example.com/production
KONG_PROXY_URL=https://api.example.com
KONG_ADMIN_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
KONG_WORKSPACE=production
KONG_VERIFY_SSL=true
```

### Usage in Code

```python
from sark.config import get_config
from sark.kong_client import create_kong_client

# Get configuration
config = get_config()

# Create Kong client
with create_kong_client(config.kong) as kong:
    # Test connection
    if kong.health_check():
        print("Kong is healthy!")

    # Create a service
    service = kong.create_service(
        name="my-api",
        url="http://backend:8080"
    )

    # Create a route
    route = kong.create_route(
        service_name="my-api",
        paths=["/api/v1"],
        methods=["GET", "POST"]
    )

    # Add rate limiting plugin
    plugin = kong.add_plugin(
        plugin_name="rate-limiting",
        service_name="my-api",
        config={
            "minute": 100,
            "policy": "local"
        }
    )
```

### Verification

Test your Kong connection:

```python
from sark.kong_client import verify_kong_connectivity

if verify_kong_connectivity():
    print("✓ Successfully connected to Kong")
else:
    print("✗ Failed to connect to Kong")
```

### Common Kong Plugins

SARK supports all Kong plugins. Common enterprise plugins include:

- **Authentication**: `jwt`, `oauth2`, `ldap-auth`, `openid-connect`
- **Security**: `rate-limiting`, `acl`, `cors`, `ip-restriction`
- **Traffic Control**: `request-termination`, `proxy-cache`, `request-transformer`
- **Logging**: `file-log`, `http-log`, `tcp-log`, `datadog`, `prometheus`

---

## PostgreSQL Database Integration

### Prerequisites

For external PostgreSQL, gather:

- Hostname and port
- Database name
- Username and password
- SSL requirements (certificate, mode)
- Network access (firewall rules, VPN)

### Configuration

#### Managed PostgreSQL (Development)

```bash
# .env
POSTGRES_ENABLED=true
POSTGRES_MODE=managed
POSTGRES_HOST=database
POSTGRES_PORT=5432
POSTGRES_DB=sark
POSTGRES_USER=sark
POSTGRES_PASSWORD=your_secure_password
```

Start PostgreSQL:

```bash
docker-compose --profile managed up -d
```

#### External PostgreSQL (Enterprise)

```bash
# .env
POSTGRES_ENABLED=true
POSTGRES_MODE=external

# Connection details
POSTGRES_HOST=postgres.example.com
POSTGRES_PORT=5432
POSTGRES_DB=sark_production
POSTGRES_USER=sark_app_user
POSTGRES_PASSWORD=your_secure_password_here

# Connection pool settings (adjust for production load)
POSTGRES_POOL_SIZE=20
POSTGRES_MAX_OVERFLOW=40

# SSL settings (required for production)
POSTGRES_SSL_MODE=require
# SSL modes: disable, allow, prefer, require, verify-ca, verify-full
```

#### External PostgreSQL with SSL (Verify Full)

For maximum security with certificate verification:

```bash
# .env
POSTGRES_ENABLED=true
POSTGRES_MODE=external
POSTGRES_HOST=postgres.example.com
POSTGRES_PORT=5432
POSTGRES_DB=sark_production
POSTGRES_USER=sark_app_user
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_SSL_MODE=verify-full
```

Place your SSL certificates in a secure location and configure your application to use them.

### Usage in Code

```python
from sark.config import get_config
from sark.database import create_database_manager
from sqlalchemy import text

# Get configuration
config = get_config()

# Create database manager
db = create_database_manager(config.postgres)

# Synchronous usage
with db.get_session() as session:
    result = session.execute(text("SELECT version()"))
    print(f"PostgreSQL version: {result.scalar()}")

# Async usage
async def query_async():
    async with db.get_async_session() as session:
        result = await session.execute(text("SELECT version()"))
        print(f"PostgreSQL version: {result.scalar()}")
```

### Database Schema Management

For **managed** PostgreSQL:
- Initialization scripts in `scripts/db/init/` run automatically
- Perfect for development and testing

For **external** PostgreSQL:
- Coordinate with your DBA team for schema changes
- Use your organization's migration process
- Consider tools like Alembic or Flyway

### Verification

Test your database connection:

```python
from sark.database import verify_database_connectivity

if verify_database_connectivity():
    print("✓ Successfully connected to PostgreSQL")
else:
    print("✗ Failed to connect to PostgreSQL")
```

---

## Redis Cache Integration

### Prerequisites

For external Redis, gather:

- Hostname and port
- Password (if authentication enabled)
- SSL requirements
- For Redis Sentinel: sentinel hosts and service name
- For Redis Cluster: cluster nodes

### Configuration

#### Managed Redis (Development)

```bash
# .env
VALKEY_ENABLED=true
VALKEY_MODE=managed
VALKEY_HOST=cache
VALKEY_PORT=6379
VALKEY_PASSWORD=your_redis_password
```

Start Redis:

```bash
docker-compose --profile managed up -d
```

#### External Redis (Simple)

```bash
# .env
VALKEY_ENABLED=true
VALKEY_MODE=external

# Connection details
VALKEY_HOST=redis.example.com
VALKEY_PORT=6379
VALKEY_DB=0
VALKEY_PASSWORD=your_redis_password_here

# Advanced settings
VALKEY_MAX_CONNECTIONS=100
VALKEY_SSL=true
```

#### External Redis Sentinel (High Availability)

For production deployments with Redis Sentinel:

```bash
# .env
VALKEY_ENABLED=true
VALKEY_MODE=external

# Sentinel configuration
VALKEY_SENTINEL_ENABLED=true
VALKEY_SENTINEL_SERVICE_NAME=mymaster
VALKEY_SENTINEL_HOSTS=sentinel1.example.com:26379,sentinel2.example.com:26379,sentinel3.example.com:26379

# Authentication and SSL
VALKEY_PASSWORD=your_redis_password_here
VALKEY_SSL=true
VALKEY_DB=0
VALKEY_MAX_CONNECTIONS=100
```

### Usage in Code

```python
from sark.config import get_config
from sark.cache import create_cache_manager

# Get configuration
config = get_config()

# Create cache manager
with create_cache_manager(config.redis) as cache:
    # Set a value
    cache.set("user:123", "John Doe", expire=3600)

    # Get a value
    user = cache.get("user:123")
    print(f"User: {user}")

    # Delete a key
    cache.delete("user:123")

    # Increment a counter
    views = cache.increment("page:views")
    print(f"Page views: {views}")
```

### Verification

Test your Redis connection:

```python
from sark.cache import verify_cache_connectivity

if verify_cache_connectivity():
    print("✓ Successfully connected to Redis")
else:
    print("✗ Failed to connect to Redis")
```

---

## Configuration Reference

### Environment Variables

All configuration is done via environment variables in the `.env` file.

#### Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | Environment name |
| `DEBUG` | `false` | Enable debug mode |
| `LOG_LEVEL` | `INFO` | Logging level |

#### PostgreSQL Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_ENABLED` | `false` | Enable PostgreSQL |
| `POSTGRES_MODE` | `managed` | `managed` or `external` |
| `POSTGRES_HOST` | `database` | Database hostname |
| `POSTGRES_PORT` | `5432` | Database port |
| `POSTGRES_DB` | `sark` | Database name |
| `POSTGRES_USER` | `sark` | Database user |
| `POSTGRES_PASSWORD` | `sark` | Database password |
| `POSTGRES_POOL_SIZE` | `5` | Connection pool size |
| `POSTGRES_MAX_OVERFLOW` | `10` | Max overflow connections |
| `POSTGRES_SSL_MODE` | `disable` | SSL mode |

#### Redis Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `VALKEY_ENABLED` | `false` | Enable Redis |
| `VALKEY_MODE` | `managed` | `managed` or `external` |
| `VALKEY_HOST` | `cache` | Redis hostname |
| `VALKEY_PORT` | `6379` | Redis port |
| `VALKEY_DB` | `0` | Redis database number |
| `VALKEY_PASSWORD` | `` | Redis password |
| `VALKEY_MAX_CONNECTIONS` | `50` | Max connections |
| `VALKEY_SSL` | `false` | Enable SSL |
| `VALKEY_SENTINEL_ENABLED` | `false` | Use Redis Sentinel |
| `VALKEY_SENTINEL_SERVICE_NAME` | `` | Sentinel service name |
| `VALKEY_SENTINEL_HOSTS` | `` | Sentinel hosts |

#### Kong Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `KONG_ENABLED` | `false` | Enable Kong |
| `KONG_MODE` | `managed` | `managed` or `external` |
| `KONG_ADMIN_URL` | `http://kong:8001` | Kong Admin API URL |
| `KONG_PROXY_URL` | `http://kong:8000` | Kong Proxy URL |
| `KONG_ADMIN_API_KEY` | `` | Admin API key |
| `KONG_WORKSPACE` | `default` | Kong workspace |
| `KONG_VERIFY_SSL` | `true` | Verify SSL certificates |
| `KONG_TIMEOUT` | `30` | Request timeout (seconds) |
| `KONG_RETRIES` | `3` | Number of retries |
| `KONG_DB_PASSWORD` | `kong` | Kong DB password (managed) |

---

## Security Best Practices

### 1. Credentials Management

**DO:**
- ✓ Use strong, unique passwords
- ✓ Rotate credentials regularly
- ✓ Use environment variables or secrets management
- ✓ Enable SSL/TLS for external connections
- ✓ Use least-privilege access

**DON'T:**
- ✗ Commit `.env` files to version control
- ✗ Use default passwords in production
- ✗ Share credentials across environments
- ✗ Disable SSL verification in production

### 2. Network Security

- Use VPN or private networks for external services
- Configure firewall rules (allow only necessary IPs)
- Use SSL/TLS for all connections
- Enable authentication on all services

### 3. PostgreSQL Security

```bash
# Production PostgreSQL configuration
POSTGRES_SSL_MODE=verify-full  # Highest security
POSTGRES_PASSWORD=<strong-password-from-secrets-manager>
POSTGRES_POOL_SIZE=20  # Adjust based on load
```

### 4. Redis Security

```bash
# Production Redis configuration
VALKEY_PASSWORD=<strong-password-from-secrets-manager>
VALKEY_SSL=true
VALKEY_MAX_CONNECTIONS=100
```

### 5. Kong Security

```bash
# Production Kong configuration
KONG_ADMIN_API_KEY=<rbac-token-from-secrets-manager>
KONG_VERIFY_SSL=true
KONG_WORKSPACE=production
```

### 6. Secrets Management

Consider using:
- AWS Secrets Manager
- HashiCorp Vault
- Azure Key Vault
- Kubernetes Secrets
- Docker Secrets

---

## Troubleshooting

### Connection Issues

#### "Connection refused" error

**Problem:** Cannot connect to external service.

**Solutions:**
1. Verify service is running: `telnet <host> <port>`
2. Check firewall rules
3. Verify network connectivity (VPN connected?)
4. Confirm credentials are correct

#### "SSL certificate verify failed"

**Problem:** SSL certificate validation error.

**Solutions:**
1. Ensure `VERIFY_SSL=true` for production
2. For testing only: `VERIFY_SSL=false` (not recommended)
3. Add CA certificate to system trust store
4. Use `SSL_MODE=require` instead of `verify-full`

#### "Authentication failed"

**Problem:** Invalid credentials.

**Solutions:**
1. Verify username and password
2. Check if user has necessary permissions
3. For Kong: verify API key is valid
4. Check if credentials have expired

### PostgreSQL Issues

#### "too many connections"

**Problem:** Connection pool exhausted.

**Solutions:**
```bash
# Increase pool size
POSTGRES_POOL_SIZE=50
POSTGRES_MAX_OVERFLOW=100
```

#### "password authentication failed"

**Problem:** Invalid database credentials.

**Solutions:**
1. Verify `POSTGRES_USER` and `POSTGRES_PASSWORD`
2. Check if user exists in database
3. Verify user has access to specified database

### Redis Issues

#### "NOAUTH Authentication required"

**Problem:** Redis requires password.

**Solutions:**
```bash
VALKEY_PASSWORD=your_redis_password
```

#### "Connection timeout"

**Problem:** Cannot reach Redis.

**Solutions:**
1. Verify `VALKEY_HOST` and `VALKEY_PORT`
2. Check network connectivity
3. For Sentinel: verify `VALKEY_SENTINEL_HOSTS`

### Kong Issues

#### "workspace not found"

**Problem:** Invalid workspace name.

**Solutions:**
1. Verify workspace exists in Kong
2. Use `default` for Kong OSS
3. Check `KONG_WORKSPACE` setting

#### "Unauthorized"

**Problem:** Invalid admin API key.

**Solutions:**
1. Verify `KONG_ADMIN_API_KEY`
2. Check if key has necessary permissions (RBAC)
3. Regenerate key if expired

### Debug Mode

Enable debug logging:

```bash
DEBUG=true
LOG_LEVEL=DEBUG
```

Run connection tests:

```python
from sark.config import get_config
from sark.database import create_database_manager
from sark.cache import create_cache_manager
from sark.kong_client import create_kong_client

config = get_config()

# Test each service
if config.postgres.enabled:
    db = create_database_manager(config.postgres)
    print(db.test_connection())

if config.redis.enabled:
    cache = create_cache_manager(config.redis)
    print(cache.test_connection())

if config.kong.enabled:
    kong = create_kong_client(config.kong)
    print(kong.test_connection())
```

---

## Examples

### Example 1: All Managed Services (Development)

```bash
# .env
ENVIRONMENT=development
DEBUG=true

# Use Docker Compose for all services
POSTGRES_ENABLED=true
POSTGRES_MODE=managed
VALKEY_ENABLED=true
VALKEY_MODE=managed
KONG_ENABLED=true
KONG_MODE=managed
```

```bash
# Start all services
docker-compose --profile full up -d
```

### Example 2: All External Services (Production)

```bash
# .env
ENVIRONMENT=production
DEBUG=false

# Connect to existing enterprise services
POSTGRES_ENABLED=true
POSTGRES_MODE=external
POSTGRES_HOST=postgres.prod.example.com
POSTGRES_PORT=5432
POSTGRES_DB=sark_production
POSTGRES_USER=sark_app
POSTGRES_PASSWORD=${DB_PASSWORD}  # From secrets manager
POSTGRES_SSL_MODE=verify-full

VALKEY_ENABLED=true
VALKEY_MODE=external
VALKEY_SENTINEL_ENABLED=true
VALKEY_SENTINEL_SERVICE_NAME=mymaster
VALKEY_SENTINEL_HOSTS=sentinel1:26379,sentinel2:26379,sentinel3:26379
VALKEY_PASSWORD=${VALKEY_PASSWORD}
VALKEY_SSL=true

KONG_ENABLED=true
KONG_MODE=external
KONG_ADMIN_URL=https://kong-admin.prod.example.com
KONG_PROXY_URL=https://api.prod.example.com
KONG_ADMIN_API_KEY=${KONG_API_KEY}
KONG_WORKSPACE=production
```

```bash
# No Docker Compose needed - connect to external services
docker-compose up app
```

### Example 3: Mixed Mode (Staging)

```bash
# .env
ENVIRONMENT=staging

# Use managed PostgreSQL for testing
POSTGRES_ENABLED=true
POSTGRES_MODE=managed

# Use managed Redis for testing
VALKEY_ENABLED=true
VALKEY_MODE=managed

# Connect to shared Kong gateway
KONG_ENABLED=true
KONG_MODE=external
KONG_ADMIN_URL=https://kong-admin.staging.example.com
KONG_PROXY_URL=https://api.staging.example.com
KONG_ADMIN_API_KEY=${KONG_API_KEY}
KONG_WORKSPACE=staging
```

```bash
# Start managed services only
docker-compose --profile managed up -d
```

### Example 4: Kubernetes Deployment (External Services)

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sark-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sark
  template:
    metadata:
      labels:
        app: sark
    spec:
      containers:
      - name: sark
        image: sark:latest
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: POSTGRES_ENABLED
          value: "true"
        - name: POSTGRES_MODE
          value: "external"
        - name: POSTGRES_HOST
          valueFrom:
            secretKeyRef:
              name: sark-secrets
              key: postgres-host
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: sark-secrets
              key: postgres-password
        # ... additional env vars
```

---

## Additional Resources

- **Kong Documentation**: https://docs.konghq.com/
- **PostgreSQL Documentation**: https://www.postgresql.org/docs/
- **Redis Documentation**: https://redis.io/documentation
- **Docker Compose Profiles**: https://docs.docker.com/compose/profiles/

---

## Support

For questions or issues:

1. Check this documentation
2. Review logs with `DEBUG=true`
3. Run connection tests
4. Check [Troubleshooting](#troubleshooting) section
5. Contact your DevOps/Infrastructure team for external service access

---

**Last Updated:** 2025-11-20
