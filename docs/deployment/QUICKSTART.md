# Quick Start Guide: Integrating with Existing Services

This guide helps you quickly integrate SARK with your existing enterprise deployments of Kong, PostgreSQL, and Redis.

## 5-Minute Setup

### Step 1: Copy Environment Template

```bash
cp .env.example .env
```

### Step 2: Choose Your Scenario

Pick the scenario that matches your environment:

#### Scenario A: All Existing Services (Most Common)

You have Kong, PostgreSQL, and Redis already deployed.

```bash
# Edit .env
POSTGRES_ENABLED=true
POSTGRES_MODE=external
POSTGRES_HOST=your-postgres-host.example.com
POSTGRES_PORT=5432
POSTGRES_DB=your_database
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_SSL_MODE=require

REDIS_ENABLED=true
REDIS_MODE=external
REDIS_HOST=your-redis-host.example.com
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password
REDIS_SSL=true

KONG_ENABLED=true
KONG_MODE=external
KONG_ADMIN_URL=https://your-kong-admin.example.com
KONG_PROXY_URL=https://your-kong-proxy.example.com
KONG_ADMIN_API_KEY=your_kong_api_key
KONG_WORKSPACE=your_workspace
```

Start the app (no Docker services needed):

```bash
docker-compose up app
```

#### Scenario B: Mixed (Some Existing, Some New)

You have existing Kong, but want to deploy PostgreSQL and Redis locally for testing.

```bash
# Edit .env
POSTGRES_ENABLED=true
POSTGRES_MODE=managed

REDIS_ENABLED=true
REDIS_MODE=managed

KONG_ENABLED=true
KONG_MODE=external
KONG_ADMIN_URL=https://your-kong-admin.example.com
KONG_PROXY_URL=https://your-kong-proxy.example.com
KONG_ADMIN_API_KEY=your_kong_api_key
```

Start managed services and the app:

```bash
docker-compose --profile managed up -d
```

#### Scenario C: All Managed (Development)

You want to deploy everything locally for development.

```bash
# Edit .env
POSTGRES_ENABLED=true
POSTGRES_MODE=managed

REDIS_ENABLED=true
REDIS_MODE=managed

KONG_ENABLED=true
KONG_MODE=managed
```

Start all services:

```bash
docker-compose --profile full up -d
```

### Step 3: Verify Connections

Create a test script `test_connections.py`:

```python
#!/usr/bin/env python3
"""Test connections to all configured services."""

from sark.config import get_config
from sark.database import create_database_manager
from sark.cache import create_cache_manager
from sark.kong_client import create_kong_client


def main():
    config = get_config()
    print(f"Environment: {config.environment}\n")

    # Test PostgreSQL
    if config.postgres.enabled:
        print(f"Testing PostgreSQL ({config.postgres.mode} mode)...")
        db = create_database_manager(config.postgres)
        result = db.test_connection()
        if result["connected"]:
            print(f"  ✓ Connected to PostgreSQL {result['version']}")
        else:
            print(f"  ✗ Failed: {result['error']}")
        db.close()
        print()

    # Test Redis
    if config.redis.enabled:
        print(f"Testing Redis ({config.redis.mode} mode)...")
        cache = create_cache_manager(config.redis)
        result = cache.test_connection()
        if result["connected"]:
            print(f"  ✓ Connected to Redis {result['version']}")
        else:
            print(f"  ✗ Failed: {result['error']}")
        cache.close()
        print()

    # Test Kong
    if config.kong.enabled:
        print(f"Testing Kong ({config.kong.mode} mode)...")
        kong = create_kong_client(config.kong)
        result = kong.test_connection()
        if result["healthy"]:
            print(f"  ✓ Connected to Kong {result['version']}")
        else:
            print(f"  ✗ Failed: {result['error']}")
        kong.close()
        print()


if __name__ == "__main__":
    main()
```

Run the test:

```bash
python test_connections.py
```

## Common Connection Strings

### PostgreSQL

```bash
# Development (managed)
POSTGRES_HOST=database
POSTGRES_PORT=5432

# External with SSL
POSTGRES_HOST=postgres.prod.example.com
POSTGRES_PORT=5432
POSTGRES_SSL_MODE=require

# AWS RDS
POSTGRES_HOST=mydb.abc123.us-east-1.rds.amazonaws.com
POSTGRES_PORT=5432
POSTGRES_SSL_MODE=require

# Google Cloud SQL
POSTGRES_HOST=/cloudsql/project:region:instance
POSTGRES_SSL_MODE=disable
```

### Redis

```bash
# Development (managed)
REDIS_HOST=cache
REDIS_PORT=6379

# External with password
REDIS_HOST=redis.prod.example.com
REDIS_PORT=6379
REDIS_PASSWORD=your_password
REDIS_SSL=true

# AWS ElastiCache
REDIS_HOST=myredis.abc123.use1.cache.amazonaws.com
REDIS_PORT=6379
REDIS_SSL=true

# Redis Sentinel (HA)
REDIS_SENTINEL_ENABLED=true
REDIS_SENTINEL_SERVICE_NAME=mymaster
REDIS_SENTINEL_HOSTS=sentinel1:26379,sentinel2:26379,sentinel3:26379
```

### Kong

```bash
# Development (managed)
KONG_ADMIN_URL=http://kong:8001
KONG_PROXY_URL=http://kong:8000

# External Kong OSS
KONG_ADMIN_URL=https://kong-admin.example.com
KONG_PROXY_URL=https://api.example.com

# Kong Enterprise with RBAC
KONG_ADMIN_URL=https://kong-admin.example.com/workspace-name
KONG_PROXY_URL=https://api.example.com
KONG_ADMIN_API_KEY=your_rbac_token
KONG_WORKSPACE=workspace-name
```

## Troubleshooting

### Can't connect to PostgreSQL

```bash
# Test connection manually
docker run --rm postgres:15 psql \
  "postgresql://user:pass@host:5432/dbname?sslmode=require"

# Check if port is accessible
telnet your-postgres-host.example.com 5432
```

### Can't connect to Redis

```bash
# Test connection manually
docker run --rm redis:7 redis-cli \
  -h your-redis-host.example.com \
  -p 6379 \
  -a your_password \
  --tls \
  ping

# Check if port is accessible
telnet your-redis-host.example.com 6379
```

### Can't connect to Kong

```bash
# Test Admin API
curl https://your-kong-admin.example.com/status

# Test with API key
curl -H "Kong-Admin-Token: your_key" \
  https://your-kong-admin.example.com/services
```

### SSL Certificate Issues

```bash
# Temporary: Disable SSL verification (NOT for production!)
POSTGRES_SSL_MODE=require  # Instead of verify-full
REDIS_SSL=false
KONG_VERIFY_SSL=false

# Permanent: Add CA certificate to system trust store
# or configure application to use custom CA bundle
```

## Next Steps

1. **Read the full documentation**: See [INTEGRATION.md](INTEGRATION.md) for detailed explanations
2. **Configure security**: Update passwords, enable SSL, configure firewalls
3. **Set up monitoring**: Add health checks, logging, and alerting
4. **Deploy to production**: Use proper secrets management, HA configuration

## Docker Compose Profiles Reference

```bash
# No profile - just the app
docker-compose up app

# managed - PostgreSQL + Redis
docker-compose --profile managed up -d

# kong - Kong API Gateway + its database
docker-compose --profile kong up -d

# full - Everything
docker-compose --profile full up -d

# Multiple profiles
docker-compose --profile managed --profile kong up -d
```

## Environment-Specific Configurations

### Development

```bash
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
POSTGRES_MODE=managed
REDIS_MODE=managed
KONG_MODE=managed
```

### Staging

```bash
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO
POSTGRES_MODE=external
POSTGRES_HOST=postgres.staging.example.com
REDIS_MODE=external
REDIS_HOST=redis.staging.example.com
KONG_MODE=external
KONG_ADMIN_URL=https://kong.staging.example.com
```

### Production

```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
POSTGRES_MODE=external
POSTGRES_HOST=postgres.prod.example.com
POSTGRES_SSL_MODE=verify-full
POSTGRES_POOL_SIZE=50
REDIS_MODE=external
REDIS_SENTINEL_ENABLED=true
REDIS_SSL=true
KONG_MODE=external
KONG_ADMIN_URL=https://kong.prod.example.com
KONG_VERIFY_SSL=true
```

## Support

- Full documentation: [INTEGRATION.md](INTEGRATION.md)
- Report issues: Contact your DevOps team
- Debug mode: Set `DEBUG=true` and `LOG_LEVEL=DEBUG`

---

**Quick Reference Card**

| What you have | What to set |
|---------------|-------------|
| Existing Kong, PostgreSQL, Redis | All `*_MODE=external` |
| Only existing Kong | `KONG_MODE=external`, others `managed` |
| Nothing deployed | All `*_MODE=managed`, use `--profile full` |
| Want to test locally | All `*_MODE=managed`, use `--profile full` |

---

**Last Updated:** 2025-11-20
