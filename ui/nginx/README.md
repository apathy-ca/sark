# SARK UI - Nginx Configuration

This directory contains Nginx configuration files for serving the SARK UI React application.

---

## Configuration Files

### `nginx.conf`
**Purpose:** Main Nginx configuration file

**Key Features:**
- Worker process optimization
- Gzip compression
- Rate limiting zones
- Logging configuration (standard and JSON formats)
- Performance tuning
- Buffer and timeout settings

**Usage:** Replaces `/etc/nginx/nginx.conf` in the container

---

### `default.conf`
**Purpose:** Site-specific configuration for the SARK UI

**Key Features:**
- **SPA Routing:** `try_files` directive for client-side routing
- **API Reverse Proxy:** Proxies `/api/*` requests to backend at `app:8000`
- **Static Asset Caching:** Aggressive caching for JS, CSS, images (1 year)
- **Health Endpoints:** `/health` and `/ready` for load balancer checks
- **Rate Limiting:** Protects API endpoints from abuse
- **WebSocket Support:** For real-time features
- **Custom Error Pages:** 404 and 50x error handling

**Usage:** Placed in `/etc/nginx/conf.d/` in the container

---

### `security-headers.conf`
**Purpose:** Security headers to protect against common vulnerabilities

**Headers Included:**
- **X-Frame-Options:** Prevent clickjacking
- **X-Content-Type-Options:** Prevent MIME sniffing
- **X-XSS-Protection:** XSS filter for older browsers
- **Referrer-Policy:** Control referrer information
- **Content-Security-Policy:** Prevent XSS and injection attacks
- **Permissions-Policy:** Control browser features
- **HSTS:** Force HTTPS (commented out by default)

**Security Testing:**
- Test at: https://securityheaders.com
- CSP Evaluator: https://csp-evaluator.withgoogle.com

---

### `ssl.conf`
**Purpose:** SSL/TLS configuration for production HTTPS

**Key Features:**
- TLS 1.2 and 1.3 only
- Modern cipher suites
- OCSP stapling
- SSL session caching
- Certificate configuration templates
- Compatible with Let's Encrypt and custom certificates

**SSL Testing:**
- SSL Labs: https://www.ssllabs.com/ssltest/
- Expected Grade: A or A+

---

## Docker Integration

### Development Mode

```dockerfile
# In Dockerfile (development stage)
FROM nginx:alpine AS development

# Copy nginx configuration
COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY nginx/security-headers.conf /etc/nginx/security-headers.conf

# Copy SPA files (from build)
COPY dist/ /usr/share/nginx/html/

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Production Mode

```dockerfile
# In Dockerfile (production stage)
FROM nginx:alpine AS production

# Copy nginx configuration
COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY nginx/security-headers.conf /etc/nginx/security-headers.conf
COPY nginx/ssl.conf /etc/nginx/ssl.conf

# Copy SSL certificates (if available)
# COPY certs/ /etc/nginx/ssl/

# Copy optimized SPA build
COPY dist/ /usr/share/nginx/html/

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/health || exit 1

EXPOSE 80 443
CMD ["nginx", "-g", "daemon off;"]
```

---

## Configuration Options

### Environment-Specific Settings

**Development:**
- HTTP only (no SSL)
- Detailed error messages
- Access logs enabled
- CORS permissive

**Staging:**
- HTTP and HTTPS
- Source maps included
- Detailed logging
- Security headers enforced

**Production:**
- HTTPS only (HTTP redirects to HTTPS)
- No source maps
- JSON structured logging
- Strict security headers
- Rate limiting enforced

---

## API Proxy Configuration

### Default Backend

```nginx
upstream sark_api {
    server app:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}
```

### Custom Backend (External API)

Update `default.conf`:

```nginx
upstream sark_api {
    server api.example.com:443 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

location /api/ {
    proxy_pass https://sark_api;  # Use HTTPS
    proxy_ssl_verify on;
    proxy_ssl_trusted_certificate /etc/ssl/certs/ca-bundle.crt;
    # ... rest of proxy settings
}
```

---

## Static Asset Optimization

### Caching Strategy

| Asset Type | Cache Duration | Immutable |
|------------|----------------|-----------|
| index.html | No cache | No |
| JS/CSS (hashed) | 1 year | Yes |
| Images | 1 year | Yes |
| Fonts | 1 year | Yes |
| manifest.json | 1 hour | No |
| robots.txt | 1 day | No |

### Compression

**Gzip:** Enabled by default
- Compression level: 6
- Min size: 1024 bytes
- Types: text/*, application/javascript, application/json

**Brotli:** Optional (requires nginx-mod-brotli)
```nginx
brotli on;
brotli_comp_level 6;
brotli_types text/plain text/css application/json application/javascript;
```

---

## Rate Limiting

### Configured Zones

```nginx
# API requests: 10 req/s per IP
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

# General requests: 100 req/s per IP
limit_req_zone $binary_remote_addr zone=general_limit:10m rate=100r/s;

# Concurrent connections: 10 per IP
limit_conn_zone $binary_remote_addr zone=conn_limit:10m;
```

### Applying Limits

```nginx
location /api/ {
    limit_req zone=api_limit burst=20 nodelay;
    limit_conn conn_limit 10;
    # ...
}
```

### Customizing Limits

Edit `nginx.conf` to adjust:
- `rate`: Requests per second
- `burst`: Burst capacity
- `nodelay`: Process burst immediately

---

## Health Checks

### Endpoints

**Basic Health:**
```bash
curl http://localhost/health
# Response: healthy (HTTP 200)
```

**Readiness Check:**
```bash
curl http://localhost/ready
# Response: ready (HTTP 200)
```

### Load Balancer Configuration

**AWS Application Load Balancer:**
- Health check path: `/health`
- Healthy threshold: 2
- Unhealthy threshold: 3
- Interval: 30 seconds
- Timeout: 5 seconds

**Google Cloud Load Balancer:**
- Request path: `/health`
- Check interval: 10 seconds
- Timeout: 5 seconds
- Healthy threshold: 2
- Unhealthy threshold: 3

---

## SSL/TLS Setup

### Let's Encrypt (Recommended)

1. **Install Certbot:**
```bash
# In the host machine (not container)
apt-get install certbot python3-certbot-nginx
```

2. **Obtain Certificate:**
```bash
certbot certonly --webroot \
    -w /usr/share/nginx/html \
    -d sark.example.com
```

3. **Update Nginx Config:**
Uncomment HTTPS server block in `default.conf`

4. **Auto-Renewal:**
```bash
# Add to crontab
0 0 1 * * certbot renew --quiet
```

### Custom Certificates

1. **Generate DH Parameters:**
```bash
openssl dhparam -out dhparam.pem 2048
```

2. **Mount Certificates:**
```yaml
# In docker-compose.yml
volumes:
  - ./certs/cert.pem:/etc/nginx/ssl/cert.pem:ro
  - ./certs/key.pem:/etc/nginx/ssl/key.pem:ro
  - ./certs/chain.pem:/etc/nginx/ssl/chain.pem:ro
  - ./certs/dhparam.pem:/etc/nginx/ssl/dhparam.pem:ro
```

3. **Enable HTTPS:**
Uncomment HTTPS server block in `default.conf`

---

## Troubleshooting

### Configuration Test

```bash
# Test nginx configuration syntax
docker compose exec ui nginx -t

# Reload configuration without downtime
docker compose exec ui nginx -s reload
```

### Common Issues

**1. 502 Bad Gateway**
- Check backend is running: `docker compose ps app`
- Check backend health: `curl http://localhost:8000/health`
- Check nginx error logs: `docker compose logs ui`

**2. 404 Not Found (SPA routes)**
- Verify `try_files` directive in `default.conf`
- Check if index.html exists: `docker compose exec ui ls /usr/share/nginx/html/`

**3. CORS Errors**
- Check `Access-Control-Allow-Origin` headers
- Verify API proxy configuration
- Check browser console for specific CORS error

**4. Slow Performance**
- Enable gzip: Check `Content-Encoding: gzip` in response headers
- Verify static asset caching: Check `Cache-Control` headers
- Monitor nginx access logs for slow requests

**5. SSL/TLS Issues**
- Verify certificate paths: `docker compose exec ui ls /etc/nginx/ssl/`
- Check certificate validity: `openssl x509 -in cert.pem -text -noout`
- Test SSL config: `openssl s_client -connect localhost:443`

### Debugging

**Enable Debug Logging:**
```nginx
# In nginx.conf
error_log /var/log/nginx/error.log debug;
```

**View Real-Time Logs:**
```bash
# Access logs
docker compose logs -f ui | grep access

# Error logs
docker compose logs -f ui | grep error

# All logs
docker compose logs -f ui
```

---

## Performance Tuning

### Worker Processes

```nginx
# Auto-detect CPU cores
worker_processes auto;

# Or set explicitly
worker_processes 4;
```

### Worker Connections

```nginx
# Default: 1024
# Increase for high traffic
events {
    worker_connections 4096;
}
```

### Keepalive

```nginx
# Client keepalive
keepalive_timeout 65;
keepalive_requests 100;

# Upstream keepalive
upstream sark_api {
    server app:8000;
    keepalive 32;  # Keep 32 connections open
}
```

### Buffer Sizes

```nginx
# Adjust based on your needs
client_body_buffer_size 16k;    # Default: 16k
client_max_body_size 8m;        # Default: 1m (increase for file uploads)
large_client_header_buffers 4 8k;
```

---

## Monitoring

### Metrics to Track

1. **Request Rate:** Requests per second
2. **Response Time:** p50, p95, p99 latency
3. **Error Rate:** 4xx and 5xx responses
4. **Bandwidth:** Bytes sent/received
5. **Active Connections:** Current connections

### Nginx Stub Status (Optional)

Add to `default.conf`:
```nginx
location /nginx_status {
    stub_status on;
    access_log off;
    allow 127.0.0.1;
    deny all;
}
```

View stats:
```bash
curl http://localhost/nginx_status
```

### Prometheus Integration

Use nginx-prometheus-exporter:
```yaml
# In docker-compose.yml
nginx-exporter:
  image: nginx/nginx-prometheus-exporter:latest
  command:
    - '-nginx.scrape-uri=http://ui:80/nginx_status'
  ports:
    - "9113:9113"
```

---

## Security Best Practices

1. **Keep Nginx Updated:** Use latest stable nginx:alpine image
2. **Hide Server Version:** `server_tokens off;` (already configured)
3. **Rate Limiting:** Protect against DDoS (already configured)
4. **Security Headers:** Use all recommended headers (already configured)
5. **HTTPS Only:** Redirect HTTP to HTTPS in production
6. **Regular Audits:** Test with securityheaders.com and SSL Labs
7. **Least Privilege:** Run nginx as non-root user (nginx:alpine default)
8. **Log Monitoring:** Monitor logs for suspicious activity

---

## References

- [Nginx Official Docs](https://nginx.org/en/docs/)
- [Mozilla SSL Config Generator](https://ssl-config.mozilla.org/)
- [OWASP Secure Headers](https://owasp.org/www-project-secure-headers/)
- [Security Headers Scanner](https://securityheaders.com/)
- [SSL Labs SSL Test](https://www.ssllabs.com/ssltest/)

---

**Last Updated:** 2025-11-27
**Maintained By:** Engineer 4 (DevOps/Infrastructure)
**Version:** 1.0
