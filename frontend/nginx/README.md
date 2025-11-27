# SARK Frontend - Nginx Configuration

## Overview

This directory contains production-grade Nginx configuration for serving the SARK React SPA. The configuration is modular, secure, and optimized for performance.

## Configuration Files

### 1. `nginx.conf` - Main Configuration

The main nginx configuration file that defines global settings:

**Key Features:**
- Worker processes: Auto-scaled based on CPU cores
- Event handling: epoll with multi_accept for high performance
- Gzip compression: Enabled for text-based content
- Rate limiting zones: API and general request limits
- JSON logging: Structured logs for analysis
- Performance tuning: Optimized buffers and timeouts

**Configuration Highlights:**
```nginx
worker_processes auto;
worker_connections 4096;

# Gzip compression
gzip on;
gzip_comp_level 6;
gzip_min_length 1024;

# Rate limiting
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=general_limit:10m rate=100r/s;
```

### 2. `default.conf` - Site Configuration

The main site configuration for serving the React SPA:

**Features:**
- **Health Check Endpoints**: `/health`, `/ready`, `/live` for monitoring
- **API Reverse Proxy**: Proxies `/api/*` requests to backend
- **SPA Routing**: Serves `index.html` for all routes
- **Static Asset Caching**: 1-year cache for hashed assets
- **WebSocket Support**: Upgradeable connections for real-time features
- **Error Pages**: Custom 404 and 50x error pages
- **Security**: Hidden files denied, CORS for fonts

**Location Blocks:**
```nginx
# API proxy with rate limiting
location /api/ { ... }

# Static assets with aggressive caching
location ~* \.(js|css|png|...)$ { ... }

# SPA routing fallback
location / {
    try_files $uri $uri/ /index.html;
}
```

### 3. `security-headers.conf` - Security Headers

Comprehensive security headers following OWASP best practices:

**Headers Included:**
- **X-Frame-Options**: Prevent clickjacking
- **X-Content-Type-Options**: Prevent MIME sniffing
- **X-XSS-Protection**: XSS filter for older browsers
- **Referrer-Policy**: Control referrer information
- **Content-Security-Policy**: Restrict resource loading
- **Permissions-Policy**: Control browser features
- **Strict-Transport-Security**: Force HTTPS (disabled by default)

**CSP Configuration:**
```nginx
Content-Security-Policy:
    default-src 'self';
    script-src 'self' 'unsafe-inline' 'unsafe-eval';
    style-src 'self' 'unsafe-inline';
    connect-src 'self' http://app:8000;
    # ... more directives
```

**Note**: In production, remove `'unsafe-inline'` and `'unsafe-eval'` and use nonce or hash-based CSP.

### 4. `ssl.conf` - SSL/TLS Configuration

Modern SSL/TLS configuration for HTTPS (disabled by default):

**Features:**
- TLS 1.2 and 1.3 only
- Modern cipher suites (ECDHE, ChaCha20)
- OCSP stapling enabled
- DH parameters support (2048-bit)
- Session caching optimized
- SSL buffer size tuned

**Configuration:**
```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_session_cache shared:SSL:10m;
ssl_stapling on;
ssl_stapling_verify on;
```

**Enabling SSL:**
1. Mount SSL certificates as volumes
2. Rename `ssl.conf.disabled` to `ssl.conf`
3. Update `default.conf` to include HTTPS server block
4. Uncomment HSTS header in `security-headers.conf`

## Usage

### Development

No configuration changes needed. The default configuration works for development.

```bash
# Start with docker-compose
docker compose -f docker-compose.dev.yml up -d

# Frontend available at http://localhost:5173
```

### Production

#### Standard Deployment

```bash
# Build and run with docker-compose
docker compose --profile standard up -d frontend

# Frontend available at http://localhost:3000
```

#### Custom Configuration

Mount custom configuration files:

```yaml
# docker-compose.yml
frontend:
  volumes:
    - ./custom-nginx.conf:/etc/nginx/nginx.conf:ro
    - ./custom-site.conf:/etc/nginx/conf.d/default.conf:ro
```

#### SSL/TLS Deployment

```yaml
# docker-compose.yml
frontend:
  ports:
    - "443:443"
  volumes:
    - ./ssl:/etc/nginx/ssl:ro
    - ./nginx/ssl.conf:/etc/nginx/conf.d/ssl.conf:ro
```

## Customization

### Adjusting Rate Limits

Edit `nginx/nginx.conf`:

```nginx
# Increase API rate limit
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/s;

# In default.conf, adjust burst
limit_req zone=api_limit burst=200 nodelay;
```

### Custom Security Headers

Edit `nginx/security-headers.conf`:

```nginx
# Stricter CSP (remove unsafe-inline)
Content-Security-Policy "
    default-src 'self';
    script-src 'self';
    style-src 'self';
    ...
";

# Enable HSTS for production
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
```

### Backend API URL

The backend URL is configured in `default.conf`:

```nginx
upstream sark_api {
    server app:8000;  # Change this for external API
}
```

For external APIs:
```nginx
upstream sark_api {
    server api.example.com:443;
}
```

### Custom Error Pages

Create custom error pages and mount them:

```bash
# Create error page
cat > 404.html <<EOF
<!DOCTYPE html>
<html>
<body>
  <h1>404 - Page Not Found</h1>
  <p>The page you're looking for doesn't exist.</p>
</body>
</html>
EOF

# Mount as volume
docker run -d \
  -v ./404.html:/usr/share/nginx/html/404.html:ro \
  sark-frontend:latest
```

## Testing Configuration

### Syntax Check

```bash
# Test nginx configuration
docker exec sark-frontend nginx -t

# Expected output:
# nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
# nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### Reload Configuration

```bash
# Reload without downtime
docker exec sark-frontend nginx -s reload
```

### Test Health Endpoints

```bash
# Health check
curl http://localhost:3000/health

# Readiness check
curl http://localhost:3000/ready

# Liveness check
curl http://localhost:3000/live
```

### Test Security Headers

```bash
# Check all headers
curl -I http://localhost:3000/

# Check specific header
curl -I http://localhost:3000/ | grep -i content-security-policy
```

### Test Compression

```bash
# Check gzip compression
curl -H "Accept-Encoding: gzip" -I http://localhost:3000/ | grep -i content-encoding

# Check compressed size
curl -H "Accept-Encoding: gzip" -s http://localhost:3000/ | wc -c
```

### Test Caching

```bash
# Check cache headers for static assets
curl -I http://localhost:3000/assets/main.js | grep -i cache-control

# Check no-cache for index.html
curl -I http://localhost:3000/ | grep -i cache-control
```

## Performance Tuning

### Worker Processes

Adjust based on CPU cores:

```nginx
# Auto (recommended)
worker_processes auto;

# Manual
worker_processes 4;
```

### Worker Connections

Increase for high traffic:

```nginx
events {
    worker_connections 8192;  # Default: 4096
}
```

### Buffer Sizes

Tune for your traffic patterns:

```nginx
client_body_buffer_size 32k;    # Default: 16k
client_header_buffer_size 2k;   # Default: 1k
client_max_body_size 16m;       # Default: 8m
```

### Caching

Enable proxy caching for API responses:

```nginx
# In nginx.conf
proxy_cache_path /var/cache/nginx
    levels=1:2
    keys_zone=api_cache:10m
    max_size=1g
    inactive=60m;

# In default.conf
location /api/public/ {
    proxy_cache api_cache;
    proxy_cache_valid 200 10m;
    proxy_cache_use_stale error timeout http_500;
}
```

## Security Best Practices

### 1. Remove Unsafe CSP Directives

For production, use nonce-based CSP:

```nginx
# Generate nonce in application
# Add to CSP
script-src 'self' 'nonce-{random}';
```

### 2. Enable HSTS

After verifying HTTPS works:

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
```

### 3. Hide Server Version

Already configured:

```nginx
server_tokens off;
```

### 4. Restrict Methods

Add to server block:

```nginx
if ($request_method !~ ^(GET|POST|PUT|DELETE|OPTIONS)$ ) {
    return 405;
}
```

### 5. DDoS Protection

Increase rate limiting:

```nginx
limit_req_zone $binary_remote_addr zone=ddos:10m rate=50r/s;
limit_req zone=ddos burst=100 nodelay;
limit_conn_zone $binary_remote_addr zone=conn:10m;
limit_conn conn 20;
```

## Monitoring

### Access Logs

```bash
# View access logs
docker exec sark-frontend tail -f /var/log/nginx/access.log

# Parse JSON logs (if enabled)
docker exec sark-frontend tail -f /var/log/nginx/access.log | jq .
```

### Error Logs

```bash
# View error logs
docker exec sark-frontend tail -f /var/log/nginx/error.log
```

### Metrics

Monitor these nginx metrics:

- **Request rate**: `requests/second`
- **Active connections**: Current connections
- **Response codes**: 2xx, 3xx, 4xx, 5xx distribution
- **Response time**: Request processing time
- **Bandwidth**: Bytes sent/received

## Troubleshooting

### Issue: 404 for all routes

**Cause**: SPA routing not working

**Solution**: Verify `try_files` directive:
```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

### Issue: API requests fail

**Cause**: Proxy configuration or backend unreachable

**Solution**:
```bash
# Test backend connectivity
docker exec sark-frontend curl http://app:8000/health

# Check proxy configuration
docker exec sark-frontend cat /etc/nginx/conf.d/default.conf | grep -A 10 "location /api"
```

### Issue: SSL not working

**Cause**: Certificate paths or SSL config

**Solution**:
```bash
# Verify certificate files exist
docker exec sark-frontend ls -la /etc/nginx/ssl/

# Test SSL config
docker exec sark-frontend nginx -t
```

### Issue: High memory usage

**Cause**: Large buffers or caching

**Solution**: Reduce buffer sizes or cache size:
```nginx
client_body_buffer_size 16k;
proxy_cache_path ... max_size=100m;
```

## References

- [Nginx Documentation](https://nginx.org/en/docs/)
- [Mozilla SSL Configuration](https://ssl-config.mozilla.org/)
- [OWASP Security Headers](https://owasp.org/www-project-secure-headers/)
- [CSP Evaluator](https://csp-evaluator.withgoogle.com/)
- [SSL Labs Test](https://www.ssllabs.com/ssltest/)

## Related Documentation

- [Production Deployment Guide](../PRODUCTION.md)
- [Development Guide](../DEVELOPMENT.md)
- [UI Docker Integration Plan](../../docs/UI_DOCKER_INTEGRATION_PLAN.md)
