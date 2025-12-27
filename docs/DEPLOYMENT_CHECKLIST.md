# SARK Production Deployment Checklist

**Version:** 0.1.0
**Last Updated:** 2025-11-22
**Purpose:** Step-by-step production deployment guide

---

## Table of Contents

1. [Pre-Deployment](#pre-deployment)
2. [Deployment](#deployment)
3. [Post-Deployment](#post-deployment)
4. [Rollback Procedures](#rollback-procedures)
5. [Emergency Contacts](#emergency-contacts)

---

## Pre-Deployment

Complete all steps in this section **before** deploying to production.

### 1. Infrastructure Preparation

#### 1.1 Server Provisioning

- [ ] **Provision server(s)** with required specifications
  - Minimum: 4 CPU, 16 GB RAM, 100 GB SSD
  - Recommended: 8 CPU, 32 GB RAM, 500 GB SSD
  - Network: Private network access to databases/services

- [ ] **Configure operating system**
  - OS: Ubuntu 22.04 LTS or RHEL 8+ (recommended)
  - Apply all security patches: `sudo apt update && sudo apt upgrade`
  - Configure timezone: `sudo timedatectl set-timezone UTC`
  - Set hostname: `sudo hostnamectl set-hostname sark-production-01`

- [ ] **Install required software**
  ```bash
  # Python 3.11+
  sudo apt install python3.11 python3.11-venv python3-pip

  # PostgreSQL client tools
  sudo apt install postgresql-client

  # Redis client tools
  sudo apt install redis-tools

  # System dependencies
  sudo apt install build-essential libssl-dev libffi-dev python3-dev
  ```

- [ ] **Configure firewall**
  ```bash
  # Allow SSH
  sudo ufw allow 22/tcp

  # Allow application port
  sudo ufw allow 8000/tcp

  # Allow metrics port (internal only)
  sudo ufw allow from <monitoring-server-ip> to any port 9090

  # Enable firewall
  sudo ufw enable
  ```

#### 1.2 Database Setup

- [ ] **Provision PostgreSQL database**
  - Version: PostgreSQL 14+ (recommended: PostgreSQL 15)
  - Create database: `sark`
  - Create user: `sark` with strong password
  - Grant permissions: `GRANT ALL PRIVILEGES ON DATABASE sark TO sark;`

- [ ] **Provision TimescaleDB database**
  - Version: TimescaleDB 2.11+ on PostgreSQL 14+
  - Create database: `sark_audit`
  - Enable TimescaleDB extension:
    ```sql
    CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
    ```
  - Create hypertable for audit events (will be created by migrations)

- [ ] **Configure database backups**
  - Set up automated daily backups
  - Verify backup restoration process
  - Document backup retention policy (recommended: 30 days)

- [ ] **Configure database connection pooling** (optional)
  - Consider PgBouncer for very high traffic deployments
  - Configure max connections based on expected load

#### 1.3 Redis Setup

- [ ] **Provision Redis instance**
  - Version: Redis 7.0+ (recommended: Redis 7.2)
  - Configure persistence: RDB + AOF (recommended)
  - Set strong password: `requirepass <strong-password>`
  - Configure maxmemory policy: `maxmemory-policy allkeys-lru`

- [ ] **Test Redis connection**
  ```bash
  redis-cli -h <redis-host> -a <redis-password> ping
  # Expected output: PONG
  ```

#### 1.4 SIEM Integration (Splunk or Datadog)

**Option A: Splunk**

- [ ] **Configure Splunk HTTP Event Collector (HEC)**
  - Log in to Splunk Web
  - Settings → Data Inputs → HTTP Event Collector
  - Click "New Token"
  - Token name: `SARK Production`
  - Source type: `sark:audit:event`
  - Index: `sark_audit` (or your security audit index)
  - Copy and securely store HEC token

- [ ] **Verify Splunk index exists**
  - Settings → Indexes
  - Ensure `sark_audit` index exists
  - Configure retention policy (recommended: 90-365 days)

- [ ] **Test Splunk connectivity**
  ```bash
  curl -k https://<splunk-host>:8088/services/collector \
    -H "Authorization: Splunk <hec-token>" \
    -d '{"event": "test", "sourcetype": "sark:audit:event"}'
  ```

**Option B: Datadog**

- [ ] **Obtain Datadog API credentials**
  - Log in to Datadog
  - Organization Settings → API Keys
  - Create new API key or copy existing
  - Securely store API key

- [ ] **Test Datadog connectivity**
  ```bash
  curl -X POST "https://http-intake.logs.datadoghq.com/api/v2/logs" \
    -H "DD-API-KEY: <api-key>" \
    -H "Content-Type: application/json" \
    -d '[{"message":"test","service":"sark"}]'
  ```

### 2. Configuration Setup

#### 2.1 Secrets Management

- [ ] **Choose secrets management solution**
  - [ ] HashiCorp Vault (recommended for enterprise)
  - [ ] AWS Secrets Manager (for AWS deployments)
  - [ ] Azure Key Vault (for Azure deployments)
  - [ ] GCP Secret Manager (for GCP deployments)
  - [ ] Kubernetes Secrets (for K8s deployments)

- [ ] **Store secrets in secrets manager**
  - [ ] `SECRET_KEY` (JWT signing key, 48+ chars)
  - [ ] `POSTGRES_PASSWORD`
  - [ ] `TIMESCALE_PASSWORD`
  - [ ] `VALKEY_PASSWORD`
  - [ ] `SPLUNK_HEC_TOKEN` or `DATADOG_API_KEY`
  - [ ] `CONSUL_TOKEN` (if using Consul ACLs)
  - [ ] `VAULT_TOKEN` (if using Vault)

- [ ] **Document secret rotation schedule**
  - SECRET_KEY: Every 180 days
  - Database passwords: Every 90 days
  - API tokens: Every 30-90 days

#### 2.2 Environment Configuration

- [ ] **Create production configuration file**
  ```bash
  cp .env.production.example .env.production
  ```

- [ ] **Set required variables** (see [PRODUCTION_CONFIG.md](./PRODUCTION_CONFIG.md))

  **Application:**
  - [ ] `ENVIRONMENT=production`
  - [ ] `DEBUG=false`
  - [ ] `LOG_LEVEL=INFO` or `WARNING`

  **Security:**
  - [ ] `SECRET_KEY=<generated-secure-key-48-chars>`
  - [ ] `ACCESS_TOKEN_EXPIRE_MINUTES=15` (or appropriate value)
  - [ ] `CORS_ORIGINS=<your-frontend-domains>`

  **PostgreSQL:**
  - [ ] `POSTGRES_HOST=<postgres-server>`
  - [ ] `POSTGRES_PORT=5432`
  - [ ] `POSTGRES_USER=sark`
  - [ ] `POSTGRES_PASSWORD=<secure-password>`
  - [ ] `POSTGRES_DB=sark`
  - [ ] `POSTGRES_POOL_SIZE=20` (adjust for your workload)

  **TimescaleDB:**
  - [ ] `TIMESCALE_HOST=<timescale-server>`
  - [ ] `TIMESCALE_PASSWORD=<secure-password>`
  - [ ] `TIMESCALE_DB=sark_audit`

  **Redis:**
  - [ ] `VALKEY_HOST=<redis-server>`
  - [ ] `VALKEY_PASSWORD=<secure-password>`

  **SIEM (Splunk or Datadog):**
  - [ ] `SPLUNK_ENABLED=true` (or `DATADOG_ENABLED=true`)
  - [ ] `SPLUNK_HEC_URL=<splunk-hec-url>`
  - [ ] `SPLUNK_HEC_TOKEN=<hec-token>`
  - [ ] `SPLUNK_INDEX=sark_audit`

- [ ] **Validate configuration**
  ```bash
  python scripts/validate_config.py --env-file .env.production --strict
  ```

  **Expected output:** ✅ All checks passed

- [ ] **Secure configuration file**
  ```bash
  chmod 600 .env.production
  chown sark:sark .env.production
  ```

### 3. Security Hardening

#### 3.1 Application Security

- [ ] **Verify all default passwords changed**
  - [ ] `SECRET_KEY` (not default)
  - [ ] `POSTGRES_PASSWORD` (not `sark`)
  - [ ] `TIMESCALE_PASSWORD` (not `sark`)
  - [ ] `VALKEY_PASSWORD` (not empty)

- [ ] **Verify security settings**
  - [ ] `DEBUG=false`
  - [ ] `ENVIRONMENT=production`
  - [ ] CORS restricted to trusted domains (not `*`)
  - [ ] SSL verification enabled (`VERIFY_SSL=true`)

- [ ] **Review security scan reports**
  ```bash
  # Check for recent security scan report
  cat reports/SECURITY_FIXES_REPORT.md

  # Verify all P0/P1 vulnerabilities fixed
  ```

#### 3.2 Network Security

- [ ] **Configure TLS/SSL**
  - [ ] Obtain SSL certificate (Let's Encrypt, commercial CA, or internal CA)
  - [ ] Configure reverse proxy (Nginx, HAProxy, or cloud load balancer)
  - [ ] Enable HTTPS redirect
  - [ ] Enable HSTS (handled by application when `ENVIRONMENT=production`)

- [ ] **Configure reverse proxy** (example: Nginx)
  ```nginx
  server {
      listen 443 ssl http2;
      server_name api.example.com;

      ssl_certificate /etc/ssl/certs/sark.crt;
      ssl_certificate_key /etc/ssl/private/sark.key;
      ssl_protocols TLSv1.2 TLSv1.3;

      location / {
          proxy_pass http://localhost:8000;
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme;
      }
  }
  ```

- [ ] **Restrict database access**
  - [ ] PostgreSQL: Configure `pg_hba.conf` to allow only application servers
  - [ ] Redis: Bind to private IP only
  - [ ] Use firewall rules to restrict access

#### 3.3 Monitoring & Alerting

- [ ] **Configure Prometheus metrics scraping**
  - Metrics endpoint: `http://<server>:9090/metrics`
  - Configure Prometheus to scrape endpoint
  - Verify metrics collection

- [ ] **Set up alerting rules**
  - [ ] High error rate (>5% of requests)
  - [ ] SIEM forwarding failures
  - [ ] Database connection pool exhaustion
  - [ ] High memory usage (>80%)
  - [ ] High CPU usage (>90%)

- [ ] **Configure log aggregation**
  - [ ] Ship application logs to centralized logging (ELK, Splunk, Datadog)
  - [ ] Set up log retention (30-90 days)

### 4. Application Deployment

#### 4.1 Code Preparation

- [ ] **Clone repository**
  ```bash
  git clone https://github.com/your-org/sark.git /opt/sark
  cd /opt/sark
  ```

- [ ] **Checkout production version**
  ```bash
  # Production release tag
  git checkout v0.1.0

  # Or production branch
  git checkout production
  ```

- [ ] **Verify code integrity**
  ```bash
  # Verify git signature (if using signed commits)
  git verify-commit HEAD

  # Or verify checksum
  sha256sum -c CHECKSUMS.txt
  ```

#### 4.2 Python Environment

- [ ] **Create virtual environment**
  ```bash
  python3.11 -m venv /opt/sark/venv
  source /opt/sark/venv/bin/activate
  ```

- [ ] **Install dependencies**
  ```bash
  pip install --upgrade pip setuptools wheel
  pip install -r requirements.txt
  ```

- [ ] **Verify installation**
  ```bash
  python -c "import sark; print(sark.__version__)"
  # Expected: 0.1.0 (or current version)
  ```

#### 4.3 Database Migrations

- [ ] **Backup existing database** (if upgrading)
  ```bash
  pg_dump -h <postgres-host> -U sark -d sark > sark_backup_$(date +%Y%m%d_%H%M%S).sql
  ```

- [ ] **Run database migrations**
  ```bash
  # PostgreSQL migrations
  alembic upgrade head

  # Verify migration status
  alembic current
  ```

- [ ] **Run TimescaleDB migrations**
  ```bash
  # Create hypertables for audit events
  psql -h <timescale-host> -U sark -d sark_audit -f migrations/timescale/001_create_hypertables.sql
  ```

- [ ] **Verify database schema**
  ```bash
  psql -h <postgres-host> -U sark -d sark -c "\dt"
  psql -h <timescale-host> -U sark -d sark_audit -c "\dt"
  ```

### 5. Pre-Deployment Testing

#### 5.1 Configuration Validation

- [ ] **Run configuration validator**
  ```bash
  python scripts/validate_config.py --env-file .env.production --strict
  ```

- [ ] **Test database connectivity**
  ```bash
  python -c "
  from sark.config.settings import get_settings
  from sark.db.session import get_db_session
  import asyncio

  async def test():
      settings = get_settings()
      async with get_db_session() as session:
          result = await session.execute('SELECT 1')
          print('✅ Database connection successful')

  asyncio.run(test())
  "
  ```

- [ ] **Test Redis connectivity**
  ```bash
  python -c "
  from sark.config.settings import get_settings
  import redis

  settings = get_settings()
  r = redis.from_url(settings.redis_dsn)
  r.ping()
  print('✅ Redis connection successful')
  "
  ```

- [ ] **Test SIEM connectivity**
  ```bash
  python scripts/test_siem_connection.py --config .env.production
  # Expected: ✅ Successfully sent test event to Splunk/Datadog
  ```

#### 5.2 Security Validation

- [ ] **Run security scanners**
  ```bash
  # Bandit (Python security)
  bandit -r src/ -f json -o reports/bandit-pre-deploy.json

  # pip-audit (dependency vulnerabilities)
  pip-audit --format json --output reports/pip-audit-pre-deploy.json
  ```

- [ ] **Review security scan results**
  - [ ] No new HIGH severity issues
  - [ ] All P0/P1 vulnerabilities addressed

- [ ] **Verify security headers**
  ```bash
  # Start application temporarily
  python -m uvicorn sark.main:app --host 127.0.0.1 --port 8000 &
  PID=$!

  # Test security headers
  curl -I http://localhost:8000/health | grep -E "(X-Content-Type|X-Frame|Strict-Transport)"

  # Stop application
  kill $PID
  ```

#### 5.3 Smoke Testing

- [ ] **Start application in test mode**
  ```bash
  python -m uvicorn sark.main:app --host 127.0.0.1 --port 8000
  ```

- [ ] **Test health endpoint**
  ```bash
  curl http://localhost:8000/health
  # Expected: {"status": "healthy", "version": "0.1.0"}
  ```

- [ ] **Test metrics endpoint**
  ```bash
  curl http://localhost:8000/metrics
  # Expected: Prometheus metrics output
  ```

- [ ] **Test API documentation**
  ```bash
  curl http://localhost:8000/docs
  # Expected: OpenAPI/Swagger UI HTML
  ```

---

## Deployment

Execute deployment steps in order.

### 1. Service Deployment

#### 1.1 Systemd Service Setup

- [ ] **Create systemd service file**
  ```bash
  sudo nano /etc/systemd/system/sark.service
  ```

  ```ini
  [Unit]
  Description=SARK - Security Audit and Resource Kontroler
  After=network.target postgresql.service redis.service
  Wants=postgresql.service redis.service

  [Service]
  Type=notify
  User=sark
  Group=sark
  WorkingDirectory=/opt/sark
  Environment="PATH=/opt/sark/venv/bin"
  EnvironmentFile=/opt/sark/.env.production
  ExecStart=/opt/sark/venv/bin/uvicorn sark.main:app \
      --host 0.0.0.0 \
      --port 8000 \
      --workers 9 \
      --log-config logging.yaml
  ExecReload=/bin/kill -s HUP $MAINPID
  Restart=always
  RestartSec=5
  KillMode=mixed
  KillSignal=SIGTERM
  TimeoutStopSec=30
  StandardOutput=journal
  StandardError=journal
  SyslogIdentifier=sark

  [Install]
  WantedBy=multi-user.target
  ```

- [ ] **Create sark system user**
  ```bash
  sudo useradd -r -s /bin/false -d /opt/sark sark
  sudo chown -R sark:sark /opt/sark
  ```

- [ ] **Enable and start service**
  ```bash
  sudo systemctl daemon-reload
  sudo systemctl enable sark.service
  sudo systemctl start sark.service
  ```

- [ ] **Verify service status**
  ```bash
  sudo systemctl status sark.service
  # Expected: active (running)
  ```

#### 1.2 Load Balancer Configuration (if applicable)

- [ ] **Add server to load balancer pool**
  - Health check path: `/health`
  - Health check interval: 10 seconds
  - Unhealthy threshold: 3 failures
  - Healthy threshold: 2 successes

- [ ] **Verify load balancer health checks**
  ```bash
  # Check load balancer logs for health check success
  ```

- [ ] **Gradual traffic cutover** (blue-green or canary deployment)
  - Start with 10% traffic
  - Monitor for 10 minutes
  - Increase to 50% traffic
  - Monitor for 10 minutes
  - Increase to 100% traffic

### 2. Verification

#### 2.1 Service Health

- [ ] **Verify application is running**
  ```bash
  curl http://localhost:8000/health
  # Expected: {"status": "healthy"}
  ```

- [ ] **Check application logs**
  ```bash
  sudo journalctl -u sark.service -f
  # Look for:
  # - "application_startup"
  # - "database_initialized"
  # - No error messages
  ```

- [ ] **Verify process is running**
  ```bash
  ps aux | grep uvicorn
  # Expected: 9 worker processes (or configured API_WORKERS value)
  ```

#### 2.2 Database Connectivity

- [ ] **Verify PostgreSQL connection**
  ```bash
  sudo journalctl -u sark.service | grep "database_initialized"
  # Expected: Found log entry
  ```

- [ ] **Verify TimescaleDB connection**
  ```bash
  psql -h <timescale-host> -U sark -d sark_audit -c "SELECT COUNT(*) FROM audit_events"
  # Expected: Query successful (count may be 0 initially)
  ```

- [ ] **Check connection pool health**
  ```bash
  curl http://localhost:9090/metrics | grep "db_pool_size"
  ```

#### 2.3 SIEM Integration

- [ ] **Verify SIEM initialization**
  ```bash
  sudo journalctl -u sark.service | grep "siem_initialized"
  # Expected: Log entry for Splunk or Datadog initialization
  ```

- [ ] **Generate test audit event**
  ```bash
  curl -X POST http://localhost:8000/api/v1/test-event \
    -H "Content-Type: application/json" \
    -d '{"test": true}'
  ```

- [ ] **Verify event in SIEM**

  **Splunk:**
  ```spl
  index=sark_audit sourcetype="sark:audit:event" test=true
  | head 1
  ```

  **Datadog:**
  - Navigate to Logs
  - Filter: `service:sark` AND `test:true`
  - Verify event appears within 30 seconds

#### 2.4 Metrics & Monitoring

- [ ] **Verify Prometheus metrics**
  ```bash
  curl http://localhost:9090/metrics | head -20
  # Expected: Prometheus metrics in text format
  ```

- [ ] **Check Prometheus scraping**
  - Navigate to Prometheus UI
  - Status → Targets
  - Verify SARK target is UP

- [ ] **Verify key metrics**
  ```bash
  curl http://localhost:9090/metrics | grep -E "(http_requests_total|siem_events_sent_total)"
  ```

---

## Post-Deployment

Complete within 24 hours of deployment.

### 1. Monitoring Setup

#### 1.1 Alerts Configuration

- [ ] **Create alert rules** (Prometheus)
  ```yaml
  groups:
    - name: sark_alerts
      rules:
        - alert: SARKHighErrorRate
          expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "High error rate detected"

        - alert: SARKSIEMForwardingFailed
          expr: rate(siem_events_failed_total[5m]) > 0
          for: 2m
          labels:
            severity: critical
          annotations:
            summary: "SIEM event forwarding failures"
  ```

- [ ] **Test alert delivery**
  - Trigger test alert
  - Verify notification received (email, Slack, PagerDuty)

#### 1.2 Dashboard Creation

- [ ] **Create Grafana dashboard** (or equivalent)
  - HTTP request rate
  - Error rate
  - Response time (p50, p95, p99)
  - SIEM forwarding rate
  - SIEM forwarding errors
  - Database connection pool usage
  - Memory usage
  - CPU usage

- [ ] **Share dashboard with team**

### 2. Documentation

- [ ] **Document deployment details**
  - Deployment date/time
  - Version deployed
  - Configuration changes
  - Any issues encountered
  - Rollback plan

- [ ] **Update runbook** (if applicable)
  - Add deployment to change log
  - Document any new procedures

- [ ] **Update monitoring documentation**
  - Alert thresholds
  - Dashboard URLs
  - On-call procedures

### 3. Team Notification

- [ ] **Notify stakeholders**
  - Deployment complete
  - Version deployed
  - Any known issues
  - Next steps

- [ ] **Update status page** (if applicable)
  - Mark deployment as complete
  - Update version information

### 4. Backup Verification

- [ ] **Verify automated backups configured**
  ```bash
  # Check database backup cron job
  sudo crontab -l | grep sark_backup
  ```

- [ ] **Test backup restoration** (in staging/test environment)
  ```bash
  # Restore from backup
  psql -h <test-db> -U sark -d sark_test < sark_backup_20251122.sql
  ```

### 5. Performance Testing

- [ ] **Run load test** (optional but recommended)
  ```bash
  # Example with Apache Bench
  ab -n 10000 -c 100 http://localhost:8000/health
  ```

- [ ] **Monitor performance under load**
  - Response times acceptable (<500ms p95)
  - No errors
  - Resource usage within limits

- [ ] **Adjust worker/pool sizes if needed**

### 6. Security Audit

- [ ] **Review access logs**
  ```bash
  sudo journalctl -u sark.service | grep -E "(authentication|authorization)" | tail -100
  ```

- [ ] **Verify HTTPS enforcement**
  ```bash
  curl -I http://api.example.com
  # Expected: 301 redirect to https://
  ```

- [ ] **Test security headers**
  ```bash
  curl -I https://api.example.com/health | grep -E "(Strict-Transport|X-Frame|X-Content-Type)"
  ```

- [ ] **Scan for open ports**
  ```bash
  nmap -sT localhost
  # Expected: Only intended ports open (8000, 9090)
  ```

---

## Rollback Procedures

### When to Rollback

Initiate rollback if:
- Critical bugs discovered in production
- Security vulnerabilities introduced
- Performance degradation >50%
- Data corruption detected
- SIEM forwarding completely broken

### Rollback Steps

#### 1. Immediate Actions

- [ ] **Stop new deployments**
  ```bash
  # Mark deployment as failed in CI/CD
  ```

- [ ] **Notify stakeholders**
  - Incident severity
  - Estimated rollback time
  - Expected impact

#### 2. Service Rollback

- [ ] **Stop current service**
  ```bash
  sudo systemctl stop sark.service
  ```

- [ ] **Checkout previous version**
  ```bash
  cd /opt/sark
  git checkout <previous-version-tag>
  # Example: git checkout v0.0.9
  ```

- [ ] **Restore previous configuration** (if changed)
  ```bash
  cp .env.production.backup .env.production
  ```

- [ ] **Reinstall dependencies** (if changed)
  ```bash
  source venv/bin/activate
  pip install -r requirements.txt
  ```

- [ ] **Start service**
  ```bash
  sudo systemctl start sark.service
  ```

- [ ] **Verify service**
  ```bash
  curl http://localhost:8000/health
  sudo systemctl status sark.service
  ```

#### 3. Database Rollback (if needed)

**⚠️ CAUTION:** Only rollback database if migrations introduced breaking changes.

- [ ] **Stop application**
  ```bash
  sudo systemctl stop sark.service
  ```

- [ ] **Backup current database**
  ```bash
  pg_dump -h <postgres-host> -U sark -d sark > sark_backup_before_rollback_$(date +%Y%m%d_%H%M%S).sql
  ```

- [ ] **Rollback migrations**
  ```bash
  alembic downgrade <previous-version>
  # Example: alembic downgrade a1b2c3d4e5f6
  ```

- [ ] **Or restore from backup**
  ```bash
  psql -h <postgres-host> -U sark -d sark < sark_backup_pre_deployment.sql
  ```

- [ ] **Restart application**
  ```bash
  sudo systemctl start sark.service
  ```

#### 4. Verification

- [ ] **Verify application health**
- [ ] **Verify SIEM forwarding**
- [ ] **Verify database connectivity**
- [ ] **Monitor error rates**

#### 5. Post-Rollback

- [ ] **Document rollback reason**
- [ ] **Create bug report**
- [ ] **Schedule postmortem**
- [ ] **Update stakeholders**

---

## Emergency Contacts

### On-Call Rotation

| Role | Primary | Secondary | Phone | Slack |
|------|---------|-----------|-------|-------|
| **DevOps Lead** | [Name] | [Name] | [Phone] | @devops-lead |
| **Backend Engineer** | [Name] | [Name] | [Phone] | @backend-eng |
| **Database Admin** | [Name] | [Name] | [Phone] | @dba |
| **Security Engineer** | [Name] | [Name] | [Phone] | @security-eng |

### Escalation Path

1. **Level 1:** On-call engineer attempts resolution (15 minutes)
2. **Level 2:** Escalate to team lead if unresolved (30 minutes)
3. **Level 3:** Escalate to director if service down >1 hour

### External Contacts

- **Cloud Provider Support:** [Phone] / [Support Portal URL]
- **Database Provider Support:** [Phone] / [Support Portal URL]
- **SIEM Provider Support:** [Phone] / [Support Portal URL]

---

## Appendix: Deployment Automation

### CI/CD Pipeline

Example GitHub Actions workflow:

```yaml
name: Deploy to Production

on:
  push:
    tags:
      - 'v*'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run pre-deployment checks
        run: |
          python scripts/validate_config.py --strict
          bandit -r src/
          pip-audit

      - name: Deploy to production
        run: |
          ansible-playbook -i inventory/production playbooks/deploy.yml

      - name: Post-deployment verification
        run: |
          ./scripts/verify_deployment.sh
```

### Ansible Playbook

Example deployment playbook:

```yaml
---
- name: Deploy SARK to Production
  hosts: sark_production
  become: yes

  tasks:
    - name: Pull latest code
      git:
        repo: https://github.com/your-org/sark.git
        dest: /opt/sark
        version: "{{ deployment_version }}"

    - name: Install dependencies
      pip:
        requirements: /opt/sark/requirements.txt
        virtualenv: /opt/sark/venv

    - name: Run migrations
      shell: |
        source /opt/sark/venv/bin/activate
        alembic upgrade head
      args:
        chdir: /opt/sark

    - name: Restart service
      systemd:
        name: sark
        state: restarted
        daemon_reload: yes

    - name: Wait for health check
      uri:
        url: http://localhost:8000/health
        status_code: 200
      register: result
      until: result.status == 200
      retries: 12
      delay: 5
```

---

**Document Version:** 1.0
**Last Updated:** 2025-11-22
**Maintained By:** Engineer 3 (SIEM Lead)
