# SARK Frontend - Production Deployment Guide

## Overview

This guide covers deploying the SARK frontend in production using Docker. The frontend is built as a static React SPA and served by Nginx with comprehensive security headers, caching, and API proxying.

## Table of Contents

- [Quick Start](#quick-start)
- [Docker Build](#docker-build)
- [Configuration](#configuration)
- [Deployment Modes](#deployment-modes)
- [SSL/TLS Setup](#ssltls-setup)
- [Environment Variables](#environment-variables)
- [Health Checks](#health-checks)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Using Docker Compose (Recommended)

```bash
# From project root
cd /path/to/sark

# Start frontend with backend (standard profile)
docker compose --profile standard up -d frontend

# Check status
docker compose ps

# View logs
docker compose logs -f frontend
```

### Using Docker Directly

```bash
# Build production image
cd frontend
docker build \
  --target production \
  --build-arg VITE_API_URL=https://api.example.com \
  --build-arg VITE_APP_VERSION=$(git describe --tags) \
  -t sark-frontend:latest \
  .

# Run container
docker run -d \
  --name sark-frontend \
  -p 3000:80 \
  -p 3443:443 \
  sark-frontend:latest
```

## Docker Build

### Multi-Stage Build Architecture

The Dockerfile uses a 3-stage build process:

1. **Dependencies Stage**: Installs npm dependencies with locked versions
2. **Builder Stage**: Compiles the Vite application with optimizations
3. **Production Stage**: Creates minimal nginx image with static assets

### Build Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `NODE_VERSION` | `18` | Node.js version for building |
| `NGINX_VERSION` | `1.25-alpine` | Nginx version for production |
| `VITE_API_URL` | - | Backend API URL (required) |
| `VITE_APP_VERSION` | `dev` | Application version string |
| `VITE_APP_NAME` | `SARK` | Application name |

### Build Examples

**Development Build:**
```bash
docker build \
  --target production \
  --build-arg VITE_API_URL=http://localhost:8000 \
  -t sark-frontend:dev \
  .
```

**Staging Build:**
```bash
docker build \
  --target production \
  --build-arg VITE_API_URL=https://api.staging.example.com \
  --build-arg VITE_APP_VERSION=$(git describe --tags)-staging \
  -t sark-frontend:staging \
  .
```

**Production Build:**
```bash
docker build \
  --target production \
  --build-arg VITE_API_URL=https://api.example.com \
  --build-arg VITE_APP_VERSION=$(git describe --tags) \
  --build-arg NODE_VERSION=18 \
  --build-arg NGINX_VERSION=1.25-alpine \
  -t sark-frontend:$(git describe --tags) \
  -t sark-frontend:latest \
  .
```

## Configuration

### Nginx Configuration Structure

The production image includes modular nginx configuration:

```
/etc/nginx/
├── nginx.conf                          # Main nginx config
└── conf.d/
    ├── default.conf                    # Site configuration
    ├── security-headers.conf           # Security headers
    └── ssl.conf.disabled              # SSL config (enable via volume)
```

### Custom Configuration

Mount custom configuration files as volumes:

```bash
docker run -d \
  -v ./custom-nginx.conf:/etc/nginx/nginx.conf:ro \
  -v ./custom-site.conf:/etc/nginx/conf.d/default.conf:ro \
  sark-frontend:latest
```

### Security Headers

The frontend includes comprehensive security headers:

- **Content-Security-Policy**: Restricts resource loading
- **X-Frame-Options**: Prevents clickjacking
- **X-Content-Type-Options**: Prevents MIME sniffing
- **Strict-Transport-Security**: Enforces HTTPS (when enabled)
- **Referrer-Policy**: Controls referrer information
- **Permissions-Policy**: Controls browser features

## Deployment Modes

### 1. Standalone (Minimal)

Frontend only, connecting to external API:

```bash
docker run -d \
  --name sark-frontend \
  -p 3000:80 \
  -e VITE_API_URL=https://api.external.com \
  sark-frontend:latest
```

### 2. With Backend (Standard)

Frontend + Backend using Docker Compose:

```bash
# docker-compose.yml includes both services
docker compose --profile standard up -d
```

### 3. Full Stack

Complete deployment with Kong, database, cache:

```bash
docker compose --profile full up -d
```

## SSL/TLS Setup

### Option 1: Let's Encrypt (Recommended)

```bash
# 1. Install certbot
apt-get install certbot

# 2. Generate certificates
certbot certonly --standalone -d sark.example.com

# 3. Mount certificates as volumes
docker run -d \
  -v /etc/letsencrypt/live/sark.example.com:/etc/nginx/ssl:ro \
  -v ./nginx/ssl.conf:/etc/nginx/conf.d/ssl.conf:ro \
  -p 443:443 \
  sark-frontend:latest
```

### Option 2: Custom Certificates

```bash
# 1. Prepare certificates
mkdir -p ./ssl
cp your-cert.pem ./ssl/cert.pem
cp your-key.pem ./ssl/key.pem
cp your-chain.pem ./ssl/chain.pem

# 2. Generate DH parameters (one-time)
openssl dhparam -out ./ssl/dhparam.pem 2048

# 3. Run with SSL
docker run -d \
  -v ./ssl:/etc/nginx/ssl:ro \
  -v ./nginx/ssl.conf:/etc/nginx/conf.d/ssl.conf:ro \
  -p 443:443 \
  sark-frontend:latest
```

### Option 3: Reverse Proxy (Traefik/Nginx)

Let external reverse proxy handle SSL:

```bash
# Frontend serves HTTP only
docker run -d \
  --name sark-frontend \
  -p 3000:80 \
  sark-frontend:latest

# Reverse proxy (e.g., Traefik) terminates SSL
```

## Environment Variables

### Build-time Variables (ARG)

These are baked into the image during build:

```bash
--build-arg VITE_API_URL=https://api.example.com
--build-arg VITE_APP_VERSION=v1.0.0
--build-arg VITE_APP_NAME=SARK
```

### Runtime Variables (ENV)

These can be changed when running the container:

| Variable | Default | Description |
|----------|---------|-------------|
| `NGINX_HOST` | `localhost` | Server hostname |
| `NGINX_PORT` | `80` | HTTP port |
| `FRONTEND_PORT` | `3000` | Host port mapping |
| `FRONTEND_HTTPS_PORT` | `3443` | Host HTTPS port mapping |

## Health Checks

The frontend provides multiple health check endpoints:

### Endpoints

- `GET /health` - Basic health check (returns 200 "healthy")
- `GET /ready` - Readiness check (returns 200 "ready")
- `GET /live` - Liveness check (returns 200 "alive")

### Docker Health Check

Built-in health check runs every 30 seconds:

```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' sark-frontend

# View health check logs
docker inspect --format='{{range .State.Health.Log}}{{.Output}}{{end}}' sark-frontend
```

### Manual Health Check

```bash
# From host
curl http://localhost:3000/health

# From container
docker exec sark-frontend curl -f http://localhost/health
```

## Monitoring

### Nginx Access Logs

```bash
# View access logs
docker logs sark-frontend

# Follow access logs
docker logs -f sark-frontend

# Structured JSON logs (if enabled)
docker logs sark-frontend | jq .
```

### Metrics

Monitor these key metrics:

- **Request rate**: Requests per second
- **Response time**: P50, P95, P99 latency
- **Error rate**: 4xx and 5xx responses
- **Cache hit rate**: Static asset caching efficiency
- **Bandwidth**: Data transfer volumes

### Log Aggregation

Export logs to external systems:

```bash
# Fluentd
docker run -d \
  --log-driver=fluentd \
  --log-opt fluentd-address=localhost:24224 \
  sark-frontend:latest

# Syslog
docker run -d \
  --log-driver=syslog \
  --log-opt syslog-address=tcp://syslog.example.com:514 \
  sark-frontend:latest
```

## Troubleshooting

### Build Issues

**Problem**: Build fails with "index.html not found"

```bash
# Verify build output
docker build --target builder -t debug .
docker run --rm debug ls -la /app/dist/

# Check Vite build
cd frontend
npm run build
ls -la dist/
```

**Problem**: Dependencies fail to install

```bash
# Clear npm cache
docker build --no-cache .

# Check package-lock.json
npm ci --only=production=false
```

### Runtime Issues

**Problem**: Frontend returns 404 for all routes

```bash
# Verify nginx config
docker exec sark-frontend nginx -t

# Check static files
docker exec sark-frontend ls -la /usr/share/nginx/html/

# View nginx error log
docker exec sark-frontend cat /var/log/nginx/error.log
```

**Problem**: API requests fail (CORS errors)

```bash
# Check API proxy configuration
docker exec sark-frontend cat /etc/nginx/conf.d/default.conf | grep -A 10 "location /api"

# Verify backend connectivity
docker exec sark-frontend curl -v http://app:8000/health

# Check network
docker network inspect sark-network
```

**Problem**: Health check failing

```bash
# Test health endpoint manually
docker exec sark-frontend curl -v http://localhost/health

# Check nginx is running
docker exec sark-frontend ps aux | grep nginx

# Verify port binding
docker port sark-frontend
```

### Performance Issues

**Problem**: Slow page load times

```bash
# Check gzip compression
curl -H "Accept-Encoding: gzip" -I http://localhost:3000/

# Verify caching headers
curl -I http://localhost:3000/assets/main.js

# Check nginx worker processes
docker exec sark-frontend cat /etc/nginx/nginx.conf | grep worker
```

**Problem**: High memory usage

```bash
# Check nginx memory
docker stats sark-frontend

# Review buffer settings
docker exec sark-frontend cat /etc/nginx/nginx.conf | grep buffer
```

## Best Practices

### 1. Security

- ✅ Always use HTTPS in production
- ✅ Keep nginx and base images updated
- ✅ Run as non-root user (already configured)
- ✅ Use read-only volumes where possible
- ✅ Scan images for vulnerabilities

```bash
# Scan image
docker scan sark-frontend:latest

# Update base images
docker pull nginx:1.25-alpine
docker pull node:18-alpine
```

### 2. Performance

- ✅ Enable HTTP/2 for better performance
- ✅ Use CDN for static assets
- ✅ Configure proper cache headers
- ✅ Enable gzip/brotli compression
- ✅ Optimize images and assets

### 3. Reliability

- ✅ Configure health checks
- ✅ Set resource limits
- ✅ Use restart policies
- ✅ Monitor logs and metrics
- ✅ Test deployments in staging

```yaml
# docker-compose.yml example
frontend:
  deploy:
    resources:
      limits:
        cpus: '1'
        memory: 512M
      reservations:
        cpus: '0.5'
        memory: 256M
  restart: unless-stopped
```

### 4. Deployment

- ✅ Use immutable tags for production
- ✅ Test images before deploying
- ✅ Implement blue-green deployments
- ✅ Keep rollback images available
- ✅ Document deployment procedures

## Advanced Topics

### Custom Error Pages

Create custom error pages and mount them:

```bash
# Create error pages
echo "<!DOCTYPE html><html><body><h1>404 Not Found</h1></body></html>" > 404.html
echo "<!DOCTYPE html><html><body><h1>500 Server Error</h1></body></html>" > 50x.html

# Mount as volume
docker run -d \
  -v ./404.html:/usr/share/nginx/html/404.html:ro \
  -v ./50x.html:/usr/share/nginx/html/50x.html:ro \
  sark-frontend:latest
```

### Rate Limiting

Adjust rate limits in nginx configuration:

```nginx
# In nginx.conf
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/s;
limit_req zone=api_limit burst=200 nodelay;
```

### Load Balancing

Multiple frontend instances behind load balancer:

```bash
# Start multiple instances
docker run -d --name frontend-1 -p 3001:80 sark-frontend:latest
docker run -d --name frontend-2 -p 3002:80 sark-frontend:latest
docker run -d --name frontend-3 -p 3003:80 sark-frontend:latest

# Configure load balancer (nginx, HAProxy, etc.)
```

## Related Documentation

- [Development Guide](./DEVELOPMENT.md) - Local development setup
- [Docker Compose Profiles](../docs/DOCKER_PROFILES.md) - Deployment profiles
- [UI Docker Integration Plan](../docs/UI_DOCKER_INTEGRATION_PLAN.md) - Architecture
- [Main README](../README.md) - Project overview

## Support

For issues or questions:

1. Check [Troubleshooting](#troubleshooting) section
2. Review nginx error logs: `docker logs sark-frontend`
3. File an issue on GitHub
4. Contact the SARK team
