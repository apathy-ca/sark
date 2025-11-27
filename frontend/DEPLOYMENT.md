# SARK Frontend Deployment Guide

## Docker Deployment

### Build Image

```bash
docker build -t sark-frontend:latest .
```

### Run Container

```bash
docker run -d \
  --name sark-frontend \
  -p 80:80 \
  --env-file .env.production \
  sark-frontend:latest
```

### With Docker Compose

```yaml
version: '3.8'
services:
  frontend:
    build: ./frontend
    ports:
      - "80:80"
    environment:
      - VITE_API_BASE_URL=http://backend:8000
    depends_on:
      - backend
```

## Production Checklist

- [ ] Update `.env.production` with correct API URL
- [ ] Configure CORS on backend
- [ ] Set up HTTPS/TLS certificates
- [ ] Configure security headers
- [ ] Enable gzip compression
- [ ] Set up CDN for static assets (optional)
- [ ] Configure monitoring and logging
- [ ] Test all API endpoints
- [ ] Verify WebSocket connections
- [ ] Run Lighthouse audit (target: 90+)

## Environment Variables

```env
VITE_API_BASE_URL=https://api.sark.yourdomain.com
VITE_APP_ENV=production
VITE_ENABLE_WEBSOCKETS=true
```

## Performance Targets

- First Contentful Paint: < 1.5s
- Time to Interactive: < 3.5s
- Lighthouse Score: > 90
- Bundle Size: < 500KB (gzipped)

## Monitoring

Add error tracking (e.g., Sentry):

```typescript
// src/main.tsx
import * as Sentry from '@sentry/react';

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  environment: import.meta.env.VITE_APP_ENV,
});
```
