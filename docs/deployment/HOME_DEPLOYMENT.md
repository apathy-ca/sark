# SARK Home Deployment Guide

This guide covers deploying SARK in a home environment, optimized for resource-constrained devices like OPNsense routers.

## Overview

SARK Home is a lightweight deployment profile designed for:

- **Home routers** (OPNsense, pfSense)
- **Low-resource devices** (512MB RAM, single core)
- **Privacy-focused users** who want to monitor LLM usage on their network
- **Families** wanting visibility into AI assistant usage

### Key Features

| Feature | Home Deployment | Enterprise Deployment |
|---------|----------------|----------------------|
| Database | SQLite | PostgreSQL/TimescaleDB |
| Caching | In-memory | Redis/Valkey |
| Policy Engine | Embedded OPA | External OPA |
| Workers | 1 (single core) | Multiple |
| Memory Target | 256MB (max 512MB) | 4GB+ |
| Audit Storage | Local SQLite | SIEM Integration |

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- 512MB available RAM
- 1GB disk space for application and logs

### 1. Clone and Configure

```bash
# Navigate to SARK directory
cd sark

# Initialize home deployment
make home-init

# Edit configuration
nano .env.home
```

### 2. Start the Service

```bash
# Start SARK home
make home-up

# Check status
make home-status

# View logs
make home-logs
```

### 3. Verify Installation

```bash
# Check health endpoint
curl http://localhost:9090/health

# Expected response:
# {"status": "healthy", "mode": "observe", "version": "2.0.0"}
```

## Configuration

### Environment Variables

All configuration is done via the `.env.home` file. Key settings:

#### Operation Mode

```bash
# observe:  Log only (recommended for initial setup)
# advisory: Log + alerts (no blocking)
# enforce:  Log + alerts + blocking
SARK_HOME_MODE=observe
```

#### Resource Limits

```bash
# Memory limit (256MB recommended, 512MB max)
SARK_HOME_MAX_MEMORY_MB=256

# Worker processes (1 for single core)
SARK_HOME_WORKERS=1

# Max concurrent connections
SARK_HOME_MAX_CONNECTIONS=50
```

#### Database Paths

```bash
# Main database
SARK_HOME_DB_PATH=/var/db/sark/home.db

# Audit database
SARK_HOME_AUDIT_DB_PATH=/var/db/sark/audit.db
```

#### Audit Settings

```bash
# Enable audit logging
SARK_HOME_AUDIT_ENABLED=true

# Retention period (days)
SARK_HOME_AUDIT_RETENTION_DAYS=365

# Store prompt preview (first N chars)
SARK_HOME_AUDIT_PROMPT_PREVIEW=true
SARK_HOME_AUDIT_PROMPT_PREVIEW_LENGTH=200
```

### TLS Certificates

For HTTPS interception, you need TLS certificates:

#### Generate Self-Signed CA

```bash
# Create certificate directory
mkdir -p data/certs
cd data/certs

# Generate CA private key
openssl genrsa -out ca.key 4096

# Generate CA certificate
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt \
    -subj "/CN=SARK Home CA/O=SARK/C=US"

# Generate server key and certificate
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr \
    -subj "/CN=sark-home/O=SARK/C=US"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \
    -CAcreateserial -out server.crt -days 365
```

#### Install CA on Devices

To intercept HTTPS traffic, install the CA certificate on client devices:

**Windows:**
1. Double-click `ca.crt`
2. Select "Install Certificate"
3. Choose "Local Machine" > "Trusted Root Certification Authorities"

**macOS:**
1. Double-click `ca.crt`
2. Add to "System" keychain
3. Trust for "SSL"

**iOS:**
1. AirDrop or email `ca.crt` to device
2. Settings > Profile Downloaded > Install
3. Settings > General > About > Certificate Trust Settings > Enable

**Android:**
1. Copy `ca.crt` to device
2. Settings > Security > Encryption & credentials > Install from storage

## Architecture

### Components

```
┌─────────────────────────────────────────┐
│           SARK Home Container           │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────────────────────┐   │
│  │     FastAPI Proxy Server        │   │
│  │     (Port 8443 HTTPS)           │   │
│  └────────────┬────────────────────┘   │
│               │                         │
│  ┌────────────▼────────────────────┐   │
│  │      Embedded OPA Engine        │   │
│  │      (Policy Evaluation)        │   │
│  └────────────┬────────────────────┘   │
│               │                         │
│  ┌────────────▼────────────────────┐   │
│  │       In-Memory Cache           │   │
│  │       (32MB default)            │   │
│  └────────────┬────────────────────┘   │
│               │                         │
│  ┌────────────▼────────────────────┐   │
│  │      SQLite Databases           │   │
│  │  - home.db (main)               │   │
│  │  - audit.db (logs)              │   │
│  └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

### Traffic Flow

```
Client Device (laptop, phone, etc.)
        │
        │ HTTPS request to api.openai.com
        │
        ▼
┌───────────────────┐
│  Network Router   │──── Redirect rule ────┐
└───────────────────┘                       │
                                            ▼
                                   ┌────────────────┐
                                   │   SARK Home    │
                                   │   :8443        │
                                   ├────────────────┤
                                   │ 1. TLS Terminate
                                   │ 2. Log request │
                                   │ 3. Evaluate    │
                                   │    policy      │
                                   │ 4. Forward     │
                                   └───────┬────────┘
                                           │
                                           ▼
                                   ┌────────────────┐
                                   │  OpenAI API    │
                                   │  (or other LLM)│
                                   └────────────────┘
```

## Policy Configuration

### Default Policies

SARK Home includes default policies for common use cases:

**Observe Mode (default):**
```rego
# home_default.rego
package sark.home

default allow = true

# Log all requests but don't block
```

**Bedtime Policy:**
```rego
# bedtime.rego
package sark.home.bedtime

import future.keywords.if

default allow = true

# Alert (advisory) or block (enforce) after 9 PM
allow = false if {
    time.now_ns() / 1e9 > hour_to_timestamp(21)
    time.now_ns() / 1e9 < hour_to_timestamp(6)
}
```

### Adding Custom Policies

1. Create a `.rego` file in `data/policies/`
2. Restart SARK Home: `make home-restart`
3. Verify policy loaded: Check logs for policy compilation

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make home-init` | Initialize directories and config |
| `make home-up` | Start SARK home deployment |
| `make home-down` | Stop SARK home deployment |
| `make home-logs` | View logs (follow mode) |
| `make home-status` | Check container status and health |
| `make home-restart` | Restart the service |
| `make home-shell` | Open shell in container |
| `make home-db-shell` | SQLite shell for main database |
| `make home-audit-shell` | SQLite shell for audit database |
| `make home-clean` | Remove containers and volumes |
| `make home-config` | Show current configuration |

## Monitoring

### Health Check

```bash
curl http://localhost:9090/health
```

Response:
```json
{
  "status": "healthy",
  "mode": "observe",
  "version": "2.0.0",
  "uptime_seconds": 3600,
  "database": "connected",
  "policy_engine": "embedded"
}
```

### Metrics

```bash
curl http://localhost:9090/metrics
```

Provides Prometheus-compatible metrics:
- `sark_requests_total` - Total requests processed
- `sark_requests_blocked` - Blocked requests (enforce mode)
- `sark_latency_seconds` - Request latency histogram
- `sark_memory_bytes` - Memory usage

### Audit Logs

Query audit logs via SQLite:

```bash
make home-audit-shell

# Recent requests
SELECT timestamp, endpoint, client_ip, policy_result
FROM audit_events
ORDER BY timestamp DESC
LIMIT 20;

# Requests by endpoint
SELECT endpoint, COUNT(*) as count
FROM audit_events
GROUP BY endpoint
ORDER BY count DESC;

# Daily usage
SELECT DATE(timestamp) as date, COUNT(*) as requests
FROM audit_events
GROUP BY DATE(timestamp)
ORDER BY date DESC;
```

## Troubleshooting

### Service Not Starting

1. Check logs: `make home-logs`
2. Verify ports available: `netstat -tlnp | grep 8443`
3. Check Docker resources: `docker stats`

### Database Errors

1. Check database permissions:
   ```bash
   ls -la data/db/
   ```
2. Verify SQLite integrity:
   ```bash
   make home-db-shell
   .tables
   PRAGMA integrity_check;
   ```

### Certificate Issues

1. Verify certificate files exist:
   ```bash
   ls -la data/certs/
   ```
2. Check certificate validity:
   ```bash
   openssl x509 -in data/certs/server.crt -text -noout
   ```

### High Memory Usage

1. Reduce cache size:
   ```bash
   SARK_HOME_CACHE_SIZE_MB=16
   ```
2. Reduce connection limit:
   ```bash
   SARK_HOME_MAX_CONNECTIONS=25
   ```
3. Disable prompt preview (reduces audit storage):
   ```bash
   SARK_HOME_AUDIT_PROMPT_PREVIEW=false
   ```

## OPNsense Integration

For OPNsense router deployment, see the OPNsense plugin documentation (coming soon).

### Firewall Rules

To redirect LLM traffic through SARK:

1. Create a port forward rule for HTTPS (443) traffic to known LLM endpoints
2. Route traffic destined for api.openai.com, api.anthropic.com, etc. to SARK
3. SARK will proxy the traffic and log/enforce policies

### Known LLM Endpoints

SARK Home monitors these endpoints by default:
- `api.openai.com` (OpenAI/ChatGPT)
- `api.anthropic.com` (Claude)
- `generativelanguage.googleapis.com` (Google AI/Gemini)
- `api.mistral.ai` (Mistral)
- `api.cohere.ai` (Cohere)

## Upgrading

### Backup Before Upgrade

```bash
# Backup databases
cp data/db/home.db data/db/home.db.backup
cp data/db/audit.db data/db/audit.db.backup

# Backup config
cp .env.home .env.home.backup
```

### Perform Upgrade

```bash
# Pull latest changes
git pull

# Rebuild and restart
make home-down
make home-build
make home-up
```

### Rollback

```bash
# Restore backups
cp data/db/home.db.backup data/db/home.db
cp data/db/audit.db.backup data/db/audit.db
cp .env.home.backup .env.home

# Restart
make home-restart
```

## Security Considerations

### Data Privacy

- All data stays local (no cloud sync)
- Prompt previews are optional and configurable
- PII detection flags sensitive content

### Network Security

- HTTPS encryption for all proxy traffic
- CA certificate required on client devices
- No external dependencies in observe mode

### Access Control

- No authentication required in home deployment (trusted network)
- For external access, use VPN or additional authentication layer

## Support

- **Documentation:** Full docs at `/docs/`
- **Issues:** Report bugs at GitHub Issues
- **Community:** OPNsense forums, r/homelab, r/selfhosted

## License

SARK is open source software. See LICENSE for details.
