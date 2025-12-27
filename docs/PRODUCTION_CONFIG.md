# SARK Production Configuration Guide

**Version:** 0.1.0
**Last Updated:** 2025-11-22
**Audience:** DevOps Engineers, SREs, Platform Engineers

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Configuration Categories](#configuration-categories)
4. [Environment Variables Reference](#environment-variables-reference)
5. [Secrets Management](#secrets-management)
6. [Deployment Scenarios](#deployment-scenarios)
7. [Security Best Practices](#security-best-practices)
8. [Troubleshooting](#troubleshooting)
9. [Configuration Validation](#configuration-validation)

---

## Overview

SARK uses environment variables for all configuration, following the **12-Factor App** methodology. This approach provides:

- **Portability**: Same code deployed across all environments
- **Security**: Secrets separated from code
- **Flexibility**: Easy configuration changes without code changes
- **Scalability**: Environment-specific scaling parameters

### Configuration Loading

Configuration is loaded in the following order (later sources override earlier):

1. **Default values** (defined in `src/sark/config/settings.py`)
2. **.env file** (if present in working directory)
3. **Environment variables** (system or container environment)

### Configuration Files

| File | Purpose | Commit to Git? |
|------|---------|----------------|
| `.env.production.example` | Production configuration template | ✅ Yes |
| `.env` | Active configuration (development) | ❌ No |
| `.env.production` | Production configuration | ❌ No |
| `.env.staging` | Staging configuration | ❌ No |
| `docs/PRODUCTION_CONFIG.md` | This documentation | ✅ Yes |

---

## Quick Start

### 1. Create Production Configuration

```bash
# Copy the production template
cp .env.production.example .env.production

# Edit with your production values
nano .env.production
```

### 2. Generate Secure Secrets

```bash
# Generate SECRET_KEY (48+ characters recommended)
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(48))"

# Generate database passwords (32 characters)
python3 -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(32))"
python3 -c "import secrets; print('TIMESCALE_PASSWORD=' + secrets.token_urlsafe(32))"
python3 -c "import secrets; print('VALKEY_PASSWORD=' + secrets.token_urlsafe(32))"
```

### 3. Validate Configuration

```bash
# Run configuration validation script
python scripts/validate_config.py --env-file .env.production

# Check for common misconfigurations
python scripts/validate_config.py --env-file .env.production --strict
```

### 4. Deploy

See [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md) for complete deployment steps.

---

## Configuration Categories

SARK configuration is organized into the following categories:

| Category | Required | Variables | Purpose |
|----------|----------|-----------|---------|
| **Application** | ✅ Yes | 6 | Basic app settings (environment, debug, logging) |
| **API Server** | ✅ Yes | 4 | HTTP server configuration |
| **Security** | ✅ Yes | 3 | Authentication, CORS, JWT |
| **PostgreSQL** | ✅ Yes | 8 | Main application database |
| **TimescaleDB** | ✅ Yes | 5 | Audit event database |
| **Redis** | ⚠️ Recommended | 5 | Caching layer |
| **Consul** | ⚠️ Optional | 4 | Service discovery |
| **OPA** | ⚠️ Optional | 3 | Policy engine |
| **Vault** | ⚠️ Optional | 4 | Secrets management |
| **Kafka** | ⚠️ Optional | 4 | High-scale event streaming |
| **Discovery** | ⚠️ Optional | 4 | MCP server discovery |
| **Audit** | ✅ Yes | 3 | Audit configuration |
| **Splunk SIEM** | ⚠️ Optional | 10 | Splunk integration |
| **Datadog SIEM** | ⚠️ Optional | 10 | Datadog integration |
| **Observability** | ⚠️ Recommended | 4 | Metrics and tracing |

**Legend:**
- ✅ **Required**: Must be configured for production
- ⚠️ **Recommended**: Should be configured for production use
- ⚠️ **Optional**: Configure based on deployment requirements

---

## Environment Variables Reference

### Application Settings

Core application configuration that controls basic behavior.

#### `ENVIRONMENT`

**Type:** String (enum)
**Default:** `development`
**Required:** ✅ Yes
**Values:** `development`, `staging`, `production`

**Description:** Deployment environment. Controls security features:
- `production`: Enables HSTS, stricter validation, production logging
- `staging`: Pre-production testing environment
- `development`: Local development, debug mode allowed

**Examples:**
```bash
# Production deployment
ENVIRONMENT=production

# Staging environment
ENVIRONMENT=staging

# Local development
ENVIRONMENT=development
```

**Security Impact:**
- `production`: HSTS headers enabled, debug mode forbidden
- Non-production: Relaxed security for development convenience

---

#### `APP_NAME`

**Type:** String
**Default:** `SARK`
**Required:** ⚠️ Optional

**Description:** Application name for logging and identification.

**Examples:**
```bash
APP_NAME=SARK
APP_NAME=SARK-Production-US-East-1
```

---

#### `APP_VERSION`

**Type:** String
**Default:** `0.1.0`
**Required:** ⚠️ Optional

**Description:** Application version for tracking and metrics.

**Examples:**
```bash
APP_VERSION=0.1.0
APP_VERSION=1.2.3
```

---

#### `DEBUG`

**Type:** Boolean
**Default:** `false`
**Required:** ✅ Yes
**Production Value:** `false`

**Description:** Enable debug mode (detailed error messages, auto-reload).

**Security Warning:** ⚠️ **MUST be `false` in production!**
Debug mode exposes:
- Internal code paths
- Detailed stack traces
- Configuration values
- Database query details

**Examples:**
```bash
# Production (required)
DEBUG=false

# Development
DEBUG=true
```

---

#### `LOG_LEVEL`

**Type:** String (enum)
**Default:** `INFO`
**Required:** ⚠️ Recommended
**Values:** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

**Description:** Logging verbosity level.

**Recommendations:**
- **Production:** `INFO` or `WARNING`
- **Staging:** `INFO` or `DEBUG`
- **Development:** `DEBUG`

**Log Volume Impact:**
- `DEBUG`: Very high (all operations logged)
- `INFO`: Moderate (important events logged)
- `WARNING`: Low (warnings and errors only)
- `ERROR`: Very low (errors only)

**Examples:**
```bash
# Production - balanced logging
LOG_LEVEL=INFO

# Production - minimal logging
LOG_LEVEL=WARNING

# Debugging issues
LOG_LEVEL=DEBUG
```

---

### API Server Configuration

HTTP server settings for the FastAPI application.

#### `API_HOST`

**Type:** String (IP address)
**Default:** `0.0.0.0`
**Required:** ⚠️ Optional

**Description:** IP address to bind the API server.

**Values:**
- `0.0.0.0`: Bind to all network interfaces (typical for production)
- `127.0.0.1`: Localhost only (development or behind reverse proxy)
- Specific IP: Bind to specific network interface

**Security Note:** Use firewall or reverse proxy to restrict access.

**Examples:**
```bash
# Production - all interfaces (behind load balancer)
API_HOST=0.0.0.0

# Development - localhost only
API_HOST=127.0.0.1

# Specific interface
API_HOST=10.0.1.50
```

---

#### `API_PORT`

**Type:** Integer
**Default:** `8000`
**Required:** ⚠️ Optional

**Description:** TCP port for the API server.

**Recommendations:**
- Standard HTTP: `80` (requires root or capabilities)
- Standard HTTPS: `443` (requires root or capabilities)
- Unprivileged port: `8000`, `8080`, `3000`
- Behind reverse proxy: Any unprivileged port

**Examples:**
```bash
# Default
API_PORT=8000

# Behind Nginx/HAProxy
API_PORT=8080

# Custom port
API_PORT=3000
```

---

#### `API_WORKERS`

**Type:** Integer
**Default:** `4`
**Required:** ⚠️ Recommended

**Description:** Number of Uvicorn worker processes.

**Formula:** `(2 × CPU cores) + 1`

**Examples:**
```bash
# 2 CPU cores → 5 workers
API_WORKERS=5

# 4 CPU cores → 9 workers
API_WORKERS=9

# 8 CPU cores → 17 workers
API_WORKERS=17

# Memory constrained → fewer workers
API_WORKERS=4
```

**Resource Considerations:**
- Each worker consumes memory (~100-200 MB)
- More workers = better concurrency, more memory
- Monitor memory usage and adjust accordingly

---

#### `API_RELOAD`

**Type:** Boolean
**Default:** `false`
**Required:** ⚠️ Optional
**Production Value:** `false`

**Description:** Auto-reload server on code changes (development only).

**Security Warning:** ⚠️ **MUST be `false` in production!**

**Examples:**
```bash
# Production (required)
API_RELOAD=false

# Development (convenience)
API_RELOAD=true
```

---

### Security Configuration

Authentication, authorization, and CORS settings.

#### `SECRET_KEY`

**Type:** String
**Default:** `dev-secret-key-change-in-production-min-32-chars`
**Required:** ✅ Yes (CRITICAL)
**Minimum Length:** 32 characters
**Recommended Length:** 48+ characters

**Description:** Secret key for JWT signing, encryption, and CSRF tokens.

**Security Requirements:**
- ⚠️ **MUST be changed from default in production**
- Generate cryptographically random value
- Minimum 32 characters (enforced by validation)
- Treat as highly sensitive credential
- Rotate every 180 days

**Generation:**
```bash
# Recommended (48 characters)
python3 -c "import secrets; print(secrets.token_urlsafe(48))"

# Minimum (32 characters)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# OpenSSL alternative
openssl rand -base64 48
```

**Examples:**
```bash
# ❌ NEVER use default in production
SECRET_KEY=dev-secret-key-change-in-production-min-32-chars

# ✅ Properly generated (example - generate your own!)
SECRET_KEY=xI9vN2kL8mP5qR7tU0wY3zA6bC9dE2fG5hJ8kM1nP4qS7tV0xY3z
```

**Key Rotation:**
When rotating SECRET_KEY, all existing JWT tokens become invalid and users must re-authenticate.

---

#### `ACCESS_TOKEN_EXPIRE_MINUTES`

**Type:** Integer
**Default:** `15`
**Required:** ⚠️ Optional

**Description:** JWT access token expiration time in minutes.

**Security Tradeoff:**
- **Shorter (5-15 min)**: More secure, more frequent re-authentication
- **Longer (30-60 min)**: Less secure, better UX

**Recommendations:**
- **High security:** 5-15 minutes
- **Balanced:** 15-30 minutes
- **User convenience:** 30-60 minutes

**Examples:**
```bash
# High security
ACCESS_TOKEN_EXPIRE_MINUTES=5

# Recommended balance
ACCESS_TOKEN_EXPIRE_MINUTES=15

# Extended session
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

---

#### `CORS_ORIGINS`

**Type:** Comma-separated list
**Default:** `http://localhost:3000`
**Required:** ✅ Yes

**Description:** Allowed origins for Cross-Origin Resource Sharing (CORS).

**Security Requirements:**
- ⚠️ **NEVER use `*` (wildcard) in production**
- List only trusted frontend domains
- Include protocol (http:// or https://)
- Include port if non-standard

**Examples:**
```bash
# Single origin
CORS_ORIGINS=https://app.example.com

# Multiple origins
CORS_ORIGINS=https://app.example.com,https://admin.example.com

# With non-standard port
CORS_ORIGINS=https://app.example.com:8443

# Development
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# ❌ NEVER in production
CORS_ORIGINS=*
```

---

### PostgreSQL Database Configuration

Main application database for servers, policies, and operational data.

#### `POSTGRES_HOST`

**Type:** String (hostname/IP)
**Default:** `localhost`
**Required:** ✅ Yes

**Description:** PostgreSQL server hostname or IP address.

**Examples:**
```bash
# Localhost
POSTGRES_HOST=localhost

# External server
POSTGRES_HOST=postgres.example.com

# Private IP
POSTGRES_HOST=10.0.1.100

# Kubernetes service
POSTGRES_HOST=postgres-service.database.svc.cluster.local
```

---

#### `POSTGRES_PORT`

**Type:** Integer
**Default:** `5432`
**Required:** ⚠️ Optional

**Description:** PostgreSQL server TCP port.

**Examples:**
```bash
# Default PostgreSQL port
POSTGRES_PORT=5432

# Custom port
POSTGRES_PORT=5433
```

---

#### `POSTGRES_USER`

**Type:** String
**Default:** `sark`
**Required:** ✅ Yes

**Description:** PostgreSQL database user.

**Security Recommendations:**
- Use dedicated application user (not `postgres` superuser)
- Grant minimum required privileges
- Different users for different environments

**Examples:**
```bash
# Application user
POSTGRES_USER=sark

# Environment-specific user
POSTGRES_USER=sark_production
POSTGRES_USER=sark_staging
```

---

#### `POSTGRES_PASSWORD`

**Type:** String
**Default:** `sark`
**Required:** ✅ Yes (CRITICAL)

**Description:** PostgreSQL database password.

**Security Requirements:**
- ⚠️ **MUST be changed from default in production**
- Minimum 20 characters recommended
- Use cryptographically random password
- Store in secrets manager
- Rotate every 90 days

**Generation:**
```bash
# Generate secure password (32 characters)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Alternative with special characters
python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(32)))"
```

**Examples:**
```bash
# ❌ NEVER use default in production
POSTGRES_PASSWORD=sark

# ✅ Properly generated (example - generate your own!)
POSTGRES_PASSWORD=kL8mN2pQ5rS8tU1wX4yZ7aC0bE3dF6gH9jK2lM5nP8qR1sT4uV7w
```

---

#### `POSTGRES_DB`

**Type:** String
**Default:** `sark`
**Required:** ✅ Yes

**Description:** PostgreSQL database name.

**Examples:**
```bash
# Default
POSTGRES_DB=sark

# Environment-specific
POSTGRES_DB=sark_production
POSTGRES_DB=sark_staging
```

---

#### `POSTGRES_POOL_SIZE`

**Type:** Integer
**Default:** `20`
**Required:** ⚠️ Optional

**Description:** Number of database connections to maintain in the connection pool.

**Sizing Guidelines:**
- **Small deployment (1-2 workers):** 5-10
- **Medium deployment (4-8 workers):** 20-40
- **Large deployment (16+ workers):** 50-100

**Formula:** `workers × expected_concurrent_queries_per_worker`

**Examples:**
```bash
# Small deployment
POSTGRES_POOL_SIZE=10

# Medium deployment (default)
POSTGRES_POOL_SIZE=20

# Large deployment
POSTGRES_POOL_SIZE=50
```

**Database Limits:**
PostgreSQL has a `max_connections` limit (default: 100). Ensure:
```
total_connections < max_connections
where total_connections = pool_size + max_overflow (per instance)
```

---

#### `POSTGRES_MAX_OVERFLOW`

**Type:** Integer
**Default:** `10`
**Required:** ⚠️ Optional

**Description:** Additional connections allowed beyond pool_size during high load.

**Total Connections:** `pool_size + max_overflow`

**Examples:**
```bash
# Conservative
POSTGRES_MAX_OVERFLOW=5

# Default
POSTGRES_MAX_OVERFLOW=10

# High burst capacity
POSTGRES_MAX_OVERFLOW=20
```

---

### TimescaleDB Configuration

Audit event database optimized for time-series data.

#### `TIMESCALE_HOST`

**Type:** String (hostname/IP)
**Default:** `localhost`
**Required:** ✅ Yes

**Description:** TimescaleDB server hostname or IP address.

**Deployment Options:**
1. **Shared instance**: Same server as PostgreSQL, different database
2. **Dedicated instance**: Separate TimescaleDB server (recommended for high audit volume)

**Examples:**
```bash
# Shared with PostgreSQL
TIMESCALE_HOST=localhost

# Dedicated TimescaleDB server
TIMESCALE_HOST=timescale.example.com

# Kubernetes
TIMESCALE_HOST=timescale-service.database.svc.cluster.local
```

---

#### `TIMESCALE_PORT`

**Type:** Integer
**Default:** `5432`
**Required:** ⚠️ Optional

**Examples:**
```bash
TIMESCALE_PORT=5432
```

---

#### `TIMESCALE_USER`

**Type:** String
**Default:** `sark`
**Required:** ✅ Yes

**Examples:**
```bash
TIMESCALE_USER=sark
TIMESCALE_USER=sark_audit
```

---

#### `TIMESCALE_PASSWORD`

**Type:** String
**Default:** `sark`
**Required:** ✅ Yes (CRITICAL)

**Security:** Same requirements as `POSTGRES_PASSWORD`.

**Generation:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

#### `TIMESCALE_DB`

**Type:** String
**Default:** `sark_audit`
**Required:** ✅ Yes

**Description:** TimescaleDB database name for audit events.

**Examples:**
```bash
# Default
TIMESCALE_DB=sark_audit

# Environment-specific
TIMESCALE_DB=sark_audit_production
```

---

### Redis Cache Configuration

In-memory cache for performance optimization.

#### `VALKEY_HOST`

**Type:** String (hostname/IP)
**Default:** `localhost`
**Required:** ✅ Yes (if using Redis)

**Examples:**
```bash
VALKEY_HOST=localhost
VALKEY_HOST=redis.example.com
VALKEY_HOST=redis-master.cache.svc.cluster.local
```

---

#### `VALKEY_PORT`

**Type:** Integer
**Default:** `6379`
**Required:** ⚠️ Optional

**Examples:**
```bash
VALKEY_PORT=6379
```

---

#### `VALKEY_PASSWORD`

**Type:** String
**Default:** None (empty)
**Required:** ✅ Yes (production)

**Security:** Required for production deployments.

**Generation:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Examples:**
```bash
# Production (required)
VALKEY_PASSWORD=secure-random-password-here

# Development (unauthenticated)
VALKEY_PASSWORD=
```

---

#### `VALKEY_DB`

**Type:** Integer
**Default:** `0`
**Required:** ⚠️ Optional

**Description:** Redis database number (0-15).

**Examples:**
```bash
# Default database
VALKEY_DB=0

# Separate database per environment
VALKEY_DB=0  # production
VALKEY_DB=1  # staging
VALKEY_DB=2  # development
```

---

#### `VALKEY_POOL_SIZE`

**Type:** Integer
**Default:** `50`
**Required:** ⚠️ Optional

**Description:** Maximum Redis connections in the connection pool.

**Sizing:**
- **Low traffic:** 20-50
- **Medium traffic:** 50-100
- **High traffic:** 100-200

**Examples:**
```bash
VALKEY_POOL_SIZE=50
VALKEY_POOL_SIZE=100
```

---

### Splunk SIEM Configuration

Splunk HTTP Event Collector (HEC) integration for audit events.

#### `SPLUNK_ENABLED`

**Type:** Boolean
**Default:** `false`
**Required:** ✅ Yes (if using Splunk)

**Examples:**
```bash
# Enable Splunk integration
SPLUNK_ENABLED=true

# Disable Splunk integration
SPLUNK_ENABLED=false
```

---

#### `SPLUNK_HEC_URL`

**Type:** String (URL)
**Default:** `https://localhost:8088/services/collector`
**Required:** ✅ Yes (if Splunk enabled)

**Description:** Splunk HTTP Event Collector endpoint URL.

**Format:** `https://<splunk-host>:<hec-port>/services/collector`

**Examples:**
```bash
# Default HEC port
SPLUNK_HEC_URL=https://splunk.example.com:8088/services/collector

# Load balancer
SPLUNK_HEC_URL=https://splunk-hec-lb.example.com/services/collector

# Splunk Cloud
SPLUNK_HEC_URL=https://inputs.prd-p-12345.splunkcloud.com:8088/services/collector
```

---

#### `SPLUNK_HEC_TOKEN`

**Type:** String (UUID)
**Default:** Empty
**Required:** ✅ Yes (if Splunk enabled) (CRITICAL)

**Description:** Splunk HEC authentication token.

**Format:** UUID (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)

**Obtaining HEC Token:**
1. Log in to Splunk Web
2. Settings → Data Inputs → HTTP Event Collector
3. Click "New Token" or copy existing token
4. Save token securely (cannot be retrieved after creation)

**Examples:**
```bash
SPLUNK_HEC_TOKEN=12345678-1234-1234-1234-123456789012
```

**Security:** Store in secrets manager, rotate regularly.

---

#### `SPLUNK_INDEX`

**Type:** String
**Default:** `sark_audit`
**Required:** ⚠️ Optional

**Description:** Splunk index for SARK audit events.

**Requirements:**
- Index must exist in Splunk
- HEC token must have permission to write to index

**Examples:**
```bash
# Default
SPLUNK_INDEX=sark_audit

# Environment-specific
SPLUNK_INDEX=production_sark_audit
SPLUNK_INDEX=staging_sark_audit

# Shared index with source type filtering
SPLUNK_INDEX=security_audit
```

---

#### `SPLUNK_SOURCETYPE`

**Type:** String
**Default:** `sark:audit:event`
**Required:** ⚠️ Optional

**Description:** Splunk sourcetype for event parsing and field extraction.

**Examples:**
```bash
# Default (recommended)
SPLUNK_SOURCETYPE=sark:audit:event

# Custom sourcetype
SPLUNK_SOURCETYPE=custom:sark:audit
```

---

#### `SPLUNK_SOURCE`

**Type:** String
**Default:** `sark`
**Required:** ⚠️ Optional

**Description:** Splunk source field for event categorization.

**Examples:**
```bash
# Default
SPLUNK_SOURCE=sark

# Environment-specific
SPLUNK_SOURCE=sark-production
SPLUNK_SOURCE=sark-staging
```

---

#### `SPLUNK_HOST`

**Type:** String
**Default:** None (uses system hostname)
**Required:** ⚠️ Optional

**Description:** Override hostname in Splunk events.

**Examples:**
```bash
# Use system hostname (default)
SPLUNK_HOST=

# Custom hostname
SPLUNK_HOST=sark-app-01
SPLUNK_HOST=sark-production-us-east-1a
```

---

#### `SPLUNK_VERIFY_SSL`

**Type:** Boolean
**Default:** `true`
**Required:** ⚠️ Optional

**Description:** Verify SSL/TLS certificate when connecting to Splunk HEC.

**Security Recommendations:**
- **Production:** `true` (verify SSL certificates)
- **Development/Testing:** `false` (self-signed certificates)

**Examples:**
```bash
# Production (recommended)
SPLUNK_VERIFY_SSL=true

# Development with self-signed cert
SPLUNK_VERIFY_SSL=false
```

---

#### `SPLUNK_BATCH_SIZE`

**Type:** Integer
**Default:** `100`
**Required:** ⚠️ Optional

**Description:** Number of events to batch before sending to Splunk.

**Tuning:**
- **Low latency:** 50-100 (faster indexing, more requests)
- **High throughput:** 500-1000 (fewer requests, higher latency)
- **Splunk Cloud:** 100-500 (respect API limits)

**Examples:**
```bash
# Default (balanced)
SPLUNK_BATCH_SIZE=100

# High throughput
SPLUNK_BATCH_SIZE=500

# Low latency
SPLUNK_BATCH_SIZE=50
```

---

#### `SPLUNK_BATCH_TIMEOUT_SECONDS`

**Type:** Integer
**Default:** `5`
**Required:** ⚠️ Optional

**Description:** Maximum seconds to wait before flushing partial batch.

**Examples:**
```bash
# Default (5 seconds)
SPLUNK_BATCH_TIMEOUT_SECONDS=5

# Real-time indexing (1 second)
SPLUNK_BATCH_TIMEOUT_SECONDS=1

# Batch processing (30 seconds)
SPLUNK_BATCH_TIMEOUT_SECONDS=30
```

---

#### `SPLUNK_RETRY_ATTEMPTS`

**Type:** Integer
**Default:** `3`
**Required:** ⚠️ Optional

**Description:** Number of retry attempts for failed Splunk requests.

**Examples:**
```bash
# Default
SPLUNK_RETRY_ATTEMPTS=3

# High reliability
SPLUNK_RETRY_ATTEMPTS=5

# No retries (use fallback logging)
SPLUNK_RETRY_ATTEMPTS=0
```

---

### Datadog SIEM Configuration

Datadog Logs API integration for audit events.

#### `DATADOG_ENABLED`

**Type:** Boolean
**Default:** `false`
**Required:** ✅ Yes (if using Datadog)

**Examples:**
```bash
DATADOG_ENABLED=true
DATADOG_ENABLED=false
```

---

#### `DATADOG_API_KEY`

**Type:** String
**Default:** Empty
**Required:** ✅ Yes (if Datadog enabled) (CRITICAL)

**Description:** Datadog API key for authentication.

**Obtaining API Key:**
1. Log in to Datadog
2. Organization Settings → API Keys
3. Create new API key or copy existing
4. Store securely (can be regenerated if compromised)

**Examples:**
```bash
DATADOG_API_KEY=1234567890abcdef1234567890abcdef
```

**Security:** Store in secrets manager, rotate regularly.

---

#### `DATADOG_APP_KEY`

**Type:** String
**Default:** Empty
**Required:** ⚠️ Optional

**Description:** Datadog Application key for advanced features.

**Note:** Not required for sending logs, but enables additional API access.

**Examples:**
```bash
DATADOG_APP_KEY=1234567890abcdefghijklmnopqrstuvwxyz1234567890ab
```

---

#### `DATADOG_SITE`

**Type:** String
**Default:** `datadoghq.com`
**Required:** ⚠️ Optional

**Description:** Datadog site/region.

**Available Sites:**
- `datadoghq.com` - US1 (default)
- `datadoghq.eu` - EU (Europe)
- `us3.datadoghq.com` - US3
- `us5.datadoghq.com` - US5
- `ap1.datadoghq.com` - AP1 (Asia Pacific)
- `ddog-gov.com` - US1-FED (Government)

**Examples:**
```bash
# US1 (default)
DATADOG_SITE=datadoghq.com

# EU
DATADOG_SITE=datadoghq.eu

# US3
DATADOG_SITE=us3.datadoghq.com
```

---

#### `DATADOG_SERVICE`

**Type:** String
**Default:** `sark`
**Required:** ⚠️ Optional

**Description:** Service name tag for Datadog logs and APM.

**Examples:**
```bash
# Default
DATADOG_SERVICE=sark

# Environment-specific
DATADOG_SERVICE=sark-production
DATADOG_SERVICE=sark-staging
```

---

#### `DATADOG_ENVIRONMENT`

**Type:** String
**Default:** `production`
**Required:** ⚠️ Optional

**Description:** Environment tag for Datadog logs and APM.

**Examples:**
```bash
DATADOG_ENVIRONMENT=production
DATADOG_ENVIRONMENT=staging
DATADOG_ENVIRONMENT=development
```

---

#### `DATADOG_HOSTNAME`

**Type:** String
**Default:** None (uses system hostname)
**Required:** ⚠️ Optional

**Description:** Override hostname in Datadog logs.

**Examples:**
```bash
# Use system hostname (default)
DATADOG_HOSTNAME=

# Custom hostname
DATADOG_HOSTNAME=sark-app-01
```

---

#### `DATADOG_VERIFY_SSL`

**Type:** Boolean
**Default:** `true`
**Required:** ⚠️ Optional

**Description:** Verify SSL/TLS certificate when connecting to Datadog.

**Recommendation:** Always `true` in production.

**Examples:**
```bash
DATADOG_VERIFY_SSL=true
```

---

#### `DATADOG_BATCH_SIZE`

**Type:** Integer
**Default:** `100`
**Required:** ⚠️ Optional

**Description:** Number of events to batch before sending to Datadog.

**Limits:** Datadog supports up to 1000 logs per request.

**Examples:**
```bash
# Default (balanced)
DATADOG_BATCH_SIZE=100

# High throughput
DATADOG_BATCH_SIZE=500

# Maximum
DATADOG_BATCH_SIZE=1000
```

---

#### `DATADOG_BATCH_TIMEOUT_SECONDS`

**Type:** Integer
**Default:** `5`
**Required:** ⚠️ Optional

**Description:** Maximum seconds to wait before flushing partial batch.

**Examples:**
```bash
DATADOG_BATCH_TIMEOUT_SECONDS=5
DATADOG_BATCH_TIMEOUT_SECONDS=10
```

---

#### `DATADOG_RETRY_ATTEMPTS`

**Type:** Integer
**Default:** `3`
**Required:** ⚠️ Optional

**Description:** Number of retry attempts for failed Datadog requests.

**Examples:**
```bash
DATADOG_RETRY_ATTEMPTS=3
DATADOG_RETRY_ATTEMPTS=5
```

---

## Secrets Management

### Overview

**NEVER** commit real secrets to version control. Use dedicated secrets management solutions.

### Recommended Solutions

| Solution | Best For | Complexity |
|----------|----------|------------|
| **HashiCorp Vault** | Enterprise, multi-cloud | High |
| **AWS Secrets Manager** | AWS deployments | Medium |
| **Azure Key Vault** | Azure deployments | Medium |
| **GCP Secret Manager** | GCP deployments | Medium |
| **Kubernetes Secrets** | Kubernetes clusters | Low |
| **Docker Secrets** | Docker Swarm | Low |

### HashiCorp Vault Integration

SARK has built-in Vault integration:

```bash
# Vault configuration
VAULT_URL=https://vault.example.com
VAULT_TOKEN=your-vault-token
VAULT_NAMESPACE=engineering
VAULT_MOUNT_POINT=sark-secrets

# Vault will be used to fetch:
# - Database passwords
# - API tokens
# - JWT secret keys
```

### Secret Rotation Schedule

| Secret Type | Rotation Frequency | Impact |
|-------------|-------------------|--------|
| `SECRET_KEY` | 180 days | All users re-authenticate |
| Database passwords | 90 days | Brief service restart |
| API tokens (Splunk, Datadog) | 30-90 days | Configuration update |
| Redis password | 90 days | Brief service restart |

### Environment-Specific Secrets

Use separate secrets for each environment:

```
Production:  .env.production
Staging:     .env.staging
Development: .env.development
```

Never use production secrets in non-production environments.

---

## Deployment Scenarios

### Scenario 1: Small Production (Single Server)

**Specs:** 4 CPU, 16 GB RAM, 100 GB SSD

```bash
ENVIRONMENT=production
API_WORKERS=9
POSTGRES_POOL_SIZE=10
POSTGRES_MAX_OVERFLOW=5
VALKEY_POOL_SIZE=50
SPLUNK_ENABLED=true
SPLUNK_BATCH_SIZE=100
```

### Scenario 2: Medium Production (Load Balanced)

**Specs:** 3 instances × (8 CPU, 32 GB RAM)

```bash
ENVIRONMENT=production
API_WORKERS=17
POSTGRES_POOL_SIZE=20
POSTGRES_MAX_OVERFLOW=10
VALKEY_POOL_SIZE=100
SPLUNK_ENABLED=true
SPLUNK_BATCH_SIZE=500
DATADOG_ENABLED=true
DATADOG_BATCH_SIZE=500
```

### Scenario 3: Large Production (Kubernetes)

**Specs:** Auto-scaling (10-50 pods), external services

```bash
ENVIRONMENT=production
API_WORKERS=4  # per pod
POSTGRES_HOST=postgres-service.database.svc.cluster.local
VALKEY_HOST=redis-service.cache.svc.cluster.local
KAFKA_ENABLED=true
KAFKA_BOOTSTRAP_SERVERS=kafka-0.kafka:9092,kafka-1.kafka:9092,kafka-2.kafka:9092
DISCOVERY_K8S_ENABLED=true
SPLUNK_ENABLED=true
DATADOG_ENABLED=true
```

---

## Security Best Practices

### 1. Secrets Security

✅ **DO:**
- Use secrets manager (Vault, AWS Secrets Manager, etc.)
- Generate cryptographically random secrets
- Rotate secrets regularly
- Use different secrets per environment
- Restrict access with least privilege

❌ **DON'T:**
- Commit secrets to git
- Use default passwords in production
- Share secrets across environments
- Store secrets in plain text
- Use weak or predictable secrets

### 2. Network Security

✅ **DO:**
- Use TLS/SSL for all connections
- Verify SSL certificates (`VERIFY_SSL=true`)
- Use private networks for databases
- Implement firewall rules
- Use VPNs for remote access

❌ **DON'T:**
- Expose databases to public internet
- Disable SSL verification in production
- Use unencrypted connections
- Trust all network traffic

### 3. Authentication & Authorization

✅ **DO:**
- Use strong JWT secret keys
- Implement short token expiration
- Restrict CORS to trusted origins
- Use dedicated database users
- Implement role-based access control

❌ **DON'T:**
- Use wildcard CORS (`*`)
- Set long token expiration
- Use superuser database accounts
- Skip authentication in production

### 4. Audit & Compliance

✅ **DO:**
- Enable SIEM integration (Splunk/Datadog)
- Set appropriate audit retention
- Monitor security events
- Regular security audits
- Document configuration changes

❌ **DON'T:**
- Disable audit logging
- Delete audit events prematurely
- Ignore security alerts

---

## Troubleshooting

### Configuration Not Loading

**Problem:** Environment variables not being read

**Solutions:**
1. Check `.env` file location (must be in working directory)
2. Verify environment variable syntax (no spaces around `=`)
3. Check for typos in variable names
4. Verify file permissions (readable by application user)

### Database Connection Failed

**Problem:** Cannot connect to PostgreSQL/TimescaleDB

**Solutions:**
1. Verify host and port: `telnet <host> <port>`
2. Check database credentials
3. Verify database exists: `psql -h <host> -U <user> -l`
4. Check firewall rules
5. Verify SSL mode matches database configuration

### SIEM Events Not Forwarding

**Problem:** Audit events not appearing in Splunk/Datadog

**Solutions:**
1. Verify `SPLUNK_ENABLED=true` or `DATADOG_ENABLED=true`
2. Check HEC token/API key validity
3. Verify network connectivity to SIEM
4. Check SIEM index/service exists
5. Review application logs for errors
6. Verify SSL certificate if `VERIFY_SSL=true`

### High Memory Usage

**Problem:** Application consuming too much memory

**Solutions:**
1. Reduce `API_WORKERS`
2. Reduce `POSTGRES_POOL_SIZE` and `POSTGRES_MAX_OVERFLOW`
3. Reduce `VALKEY_POOL_SIZE`
4. Monitor memory per worker
5. Consider horizontal scaling instead of vertical

---

## Configuration Validation

### Validation Script

Use the provided validation script:

```bash
# Validate configuration file
python scripts/validate_config.py --env-file .env.production

# Strict mode (fails on warnings)
python scripts/validate_config.py --env-file .env.production --strict

# Check specific category
python scripts/validate_config.py --env-file .env.production --category security

# Output JSON report
python scripts/validate_config.py --env-file .env.production --format json
```

### Manual Validation Checklist

Before deploying to production:

- [ ] `ENVIRONMENT=production`
- [ ] `DEBUG=false`
- [ ] `SECRET_KEY` changed from default (48+ characters)
- [ ] All `PASSWORD` fields changed from defaults
- [ ] `CORS_ORIGINS` restricted to trusted domains
- [ ] Database connection details correct
- [ ] SIEM integration configured and tested
- [ ] SSL verification enabled (`VERIFY_SSL=true`)
- [ ] Worker and pool sizes appropriate for server resources
- [ ] Secrets stored in secrets manager (not plain text)
- [ ] Configuration validated with `validate_config.py`

---

## Additional Resources

- [Deployment Checklist](./DEPLOYMENT_CHECKLIST.md) - Step-by-step deployment guide
- [Splunk Setup Guide](./siem/SPLUNK_SETUP.md) - Splunk HEC configuration
- [Datadog Setup Guide](./siem/DATADOG_SETUP.md) - Datadog Logs API configuration
- [Event Schema Reference](./siem/EVENT_SCHEMA.md) - Audit event field documentation
- [Security Fixes Report](../reports/SECURITY_FIXES_REPORT.md) - Recent security updates

---

## Support

For configuration issues:

1. Run validation script: `python scripts/validate_config.py`
2. Review application logs: `LOG_LEVEL=DEBUG`
3. Check troubleshooting section above
4. Contact DevOps team or file GitHub issue

---

**Document Version:** 1.0
**Last Updated:** 2025-11-22
**Maintained By:** Engineer 3 (SIEM Lead)
