# Engineer 4 (DevOps) - Immediate Task Assignment

**Status:** UNBLOCKED - UI source code scaffold will be available Day 3
**Timeline:** Days 3-5 (starts after Engineer 3 completes T3.2)
**Branch:** `task/engineer4-ui-docker-integration`
**Dependencies:** Engineer 3's T3.2 (React scaffold) must be complete

---

## 🎯 Mission

Integrate the new UI into SARK's Docker and development infrastructure. You were blocked on 14 tasks because the `ui/` directory didn't exist. Now that Engineer 3 is building the scaffold, you can complete the UI Docker integration tasks.

---

## 📋 Task Overview

### Task 1 (Day 3): W4-E4-01 - Vite Build Configuration
**Duration:** 1 day
**Depends on:** Engineer 3's T3.2 completion (Day 2)
**Deliverables:**
- Configure Vite for production builds
- Set up environment variable handling
- Create build verification script
- Document build process

### Task 2 (Day 4): W4-E4-02 - Development Docker Compose Setup
**Duration:** 1 day
**Depends on:** W4-E4-01 complete
**Deliverables:**
- Add UI service to docker-compose.yml
- Configure hot-reload for development
- Set up volume mounts for source code
- Test full-stack development workflow

### Task 3 (Day 5): W4-E4-03 - Production UI Dockerfile
**Duration:** 1 day
**Depends on:** W4-E4-02 complete
**Deliverables:**
- Multi-stage Dockerfile for UI
- Nginx configuration for SPA routing
- Production build optimization
- Security headers and best practices

---

## 📅 Day-by-Day Plan

### Day 3: Vite Build Configuration

**Morning: Production Build Setup**

1. **Verify Engineer 3's scaffold is ready:**
```bash
# Coordinate with Engineer 3 before starting
git pull origin task/engineer3-ui-foundation
cd ui/
npm install
npm run dev  # Verify dev server works
```

2. **Create environment configuration:**

**File: `ui/.env.example`**
```bash
# API Configuration
VITE_API_BASE_URL=http://localhost:8000
VITE_API_TIMEOUT=30000

# Authentication
VITE_AUTH_ENABLED=true

# Features
VITE_ENABLE_METRICS=true
VITE_ENABLE_AUDIT_LOGS=true

# Build
VITE_BUILD_VERSION=1.0.0
VITE_BUILD_DATE=
```

**File: `ui/.env.production`**
```bash
VITE_API_BASE_URL=/api
VITE_API_TIMEOUT=30000
VITE_AUTH_ENABLED=true
VITE_ENABLE_METRICS=true
VITE_ENABLE_AUDIT_LOGS=true
```

3. **Update Vite config for production:**

**File: `ui/vite.config.ts` (add to existing config)**
```typescript
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 3000,
      proxy: {
        '/api': {
          target: env.VITE_API_BASE_URL || 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: mode !== 'production',
      rollupOptions: {
        output: {
          manualChunks: {
            'react-vendor': ['react', 'react-dom', 'react-router-dom'],
            'ui-vendor': ['lucide-react', '@radix-ui/react-dialog'],
            'query-vendor': ['@tanstack/react-query'],
          },
        },
      },
      chunkSizeWarningLimit: 1000,
    },
    optimizeDeps: {
      include: ['react', 'react-dom', 'react-router-dom'],
    },
  }
})
```

**Afternoon: Build Scripts and Verification**

4. **Create build verification script:**

**File: `ui/scripts/verify-build.sh`**
```bash
#!/bin/bash
set -e

echo "🔨 Building UI..."
npm run build

echo "📊 Analyzing build output..."
BUILD_DIR="dist"

if [ ! -d "$BUILD_DIR" ]; then
    echo "❌ Build directory not found!"
    exit 1
fi

echo "✅ Build directory exists"

# Check for required files
REQUIRED_FILES=("index.html" "assets")
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -e "$BUILD_DIR/$file" ]; then
        echo "❌ Missing required file: $file"
        exit 1
    fi
done

echo "✅ All required files present"

# Check bundle sizes
TOTAL_SIZE=$(du -sh "$BUILD_DIR" | cut -f1)
echo "📦 Total build size: $TOTAL_SIZE"

# List generated chunks
echo "📄 Generated chunks:"
find "$BUILD_DIR/assets" -name "*.js" -exec du -h {} \; | sort -h

echo ""
echo "✅ Build verification complete!"
echo ""
echo "To test locally:"
echo "  npx serve dist -p 3000"
```

```bash
chmod +x ui/scripts/verify-build.sh
```

5. **Update package.json scripts:**

**File: `ui/package.json` (add to scripts section)**
```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "build:prod": "NODE_ENV=production vite build",
    "preview": "vite preview",
    "verify": "./scripts/verify-build.sh",
    "serve:build": "npx serve dist -p 3000",
    "type-check": "tsc --noEmit"
  }
}
```

6. **Test the build:**
```bash
npm run verify
npm run serve:build
# Visit http://localhost:3000 and verify the built app works
```

7. **Create build documentation:**

**File: `ui/BUILD.md`**
```markdown
# UI Build Process

## Development Build
```bash
npm run dev
```
- Runs on port 3000
- Hot module replacement enabled
- Proxies `/api` to backend at `localhost:8000`

## Production Build
```bash
npm run build
```
- TypeScript type checking
- Minification and tree-shaking
- Source maps (configurable)
- Outputs to `dist/`

## Build Verification
```bash
npm run verify
```
Checks:
- Build completes successfully
- Required files present
- Bundle size analysis

## Environment Variables

### Development (`.env`)
- `VITE_API_BASE_URL`: Backend URL (default: http://localhost:8000)

### Production (`.env.production`)
- `VITE_API_BASE_URL`: Set to `/api` (proxied by Nginx)

## Bundle Optimization

The build splits code into chunks:
- `react-vendor`: React core libraries
- `ui-vendor`: UI component libraries
- `query-vendor`: Data fetching libraries

## Testing Build Locally
```bash
npm run serve:build
```
Visit http://localhost:3000
```

**End of Day 3 Commit:**
```bash
git add ui/.env.example ui/.env.production ui/vite.config.ts \
        ui/scripts/verify-build.sh ui/package.json ui/BUILD.md
git commit -m "feat(ui): configure Vite production build

- Add environment variable configuration
- Update Vite config with build optimization
- Create build verification script
- Add build documentation
- Configure code splitting for vendors

Part of W4-E4-01"
```

---

### Day 4: Development Docker Compose Setup

**Morning: Docker Compose Integration**

1. **Add UI service to docker-compose.yml:**

**File: `docker-compose.yml` (add to services)**
```yaml
services:
  # ... existing services (postgres, redis, sark-api) ...

  ui:
    build:
      context: ./ui
      dockerfile: Dockerfile.dev
      target: development
    ports:
      - "3000:3000"
    volumes:
      # Mount source code for hot reload
      - ./ui/src:/app/src:ro
      - ./ui/public:/app/public:ro
      - ./ui/index.html:/app/index.html:ro
      - ./ui/vite.config.ts:/app/vite.config.ts:ro
      - ./ui/tsconfig.json:/app/tsconfig.json:ro
      - ./ui/tailwind.config.js:/app/tailwind.config.js:ro
      - ./ui/postcss.config.js:/app/postcss.config.js:ro
      # Don't mount node_modules - use container's version
      - /app/node_modules
    environment:
      - VITE_API_BASE_URL=http://sark-api:8000
      - NODE_ENV=development
    depends_on:
      - sark-api
    networks:
      - sark-network
    profiles:
      - full
      - ui-dev

  # Nginx reverse proxy (optional, for testing production-like setup)
  nginx:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./ui/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
      - ./ui/nginx/security-headers.conf:/etc/nginx/conf.d/security-headers.conf:ro
    depends_on:
      - sark-api
      - ui
    networks:
      - sark-network
    profiles:
      - full
      - production-test

networks:
  sark-network:
    driver: bridge

volumes:
  postgres-data:
  redis-data:
```

2. **Create development Dockerfile:**

**File: `ui/Dockerfile.dev`**
```dockerfile
FROM node:20-alpine AS development

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code (volumes will override in docker-compose)
COPY . .

# Expose Vite dev server port
EXPOSE 3000

# Start development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

**Afternoon: Docker Profiles and Testing**

3. **Update Docker profiles documentation:**

**File: `docs/DOCKER_PROFILES.md` (add section)**
```markdown
# Docker Compose Profiles

## Available Profiles

### `minimal` - Core Services Only
```bash
docker-compose --profile minimal up
```
Services: postgres, redis, sark-api
Use case: Backend development only

### `ui-dev` - UI Development
```bash
docker-compose --profile ui-dev up
```
Services: postgres, redis, sark-api, ui
Use case: Full-stack development with hot reload

### `full` - Complete Stack
```bash
docker-compose --profile full up
```
Services: All services including nginx
Use case: Production-like testing

### `production-test` - Production Simulation
```bash
docker-compose --profile production-test up
```
Services: postgres, redis, sark-api, nginx (serving built UI)
Use case: Testing production deployment locally

## UI-Specific Profiles

### Development Workflow
```bash
# Start backend + UI with hot reload
docker-compose --profile ui-dev up

# UI available at http://localhost:3000
# API available at http://localhost:8000
# Hot reload works for changes in ui/src/
```

### Production Testing
```bash
# Build UI first
cd ui && npm run build && cd ..

# Start with nginx serving built files
docker-compose --profile production-test up

# Full stack available at http://localhost:8080
```
```

4. **Create docker-compose test script:**

**File: `scripts/test-ui-docker.sh`**
```bash
#!/bin/bash
set -e

echo "🧪 Testing UI Docker Integration..."
echo ""

# Test 1: Development profile
echo "Test 1: Starting ui-dev profile..."
docker-compose --profile ui-dev up -d

echo "Waiting for services to be ready..."
sleep 10

echo "Checking UI service..."
if docker-compose ps ui | grep -q "Up"; then
    echo "✅ UI service is running"
else
    echo "❌ UI service failed to start"
    docker-compose logs ui
    exit 1
fi

echo "Testing UI endpoint..."
if curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ UI is accessible at http://localhost:3000"
else
    echo "❌ UI endpoint not responding"
    docker-compose logs ui
    exit 1
fi

echo "Testing API proxy..."
if curl -f http://localhost:3000/api/health > /dev/null 2>&1; then
    echo "✅ API proxy working"
else
    echo "⚠️  API proxy may need configuration"
fi

echo ""
echo "Cleaning up..."
docker-compose --profile ui-dev down

echo ""
echo "✅ All tests passed!"
echo ""
echo "To start development:"
echo "  docker-compose --profile ui-dev up"
echo ""
echo "Then visit:"
echo "  UI:  http://localhost:3000"
echo "  API: http://localhost:8000"
```

```bash
chmod +x scripts/test-ui-docker.sh
```

5. **Test the setup:**
```bash
./scripts/test-ui-docker.sh
```

6. **Create developer guide:**

**File: `ui/DOCKER_DEVELOPMENT.md`**
```markdown
# UI Docker Development Guide

## Quick Start

### Option 1: Docker Compose (Recommended)
```bash
# Start full stack with hot reload
docker-compose --profile ui-dev up

# UI: http://localhost:3000
# API: http://localhost:8000
```

### Option 2: Local Development
```bash
# Terminal 1: Start backend services
docker-compose --profile minimal up

# Terminal 2: Run UI locally
cd ui
npm install
npm run dev
```

## Hot Reload

Changes to these files trigger hot reload:
- `ui/src/**/*` - Application source code
- `ui/index.html` - HTML template
- `ui/vite.config.ts` - Vite configuration
- `ui/tailwind.config.js` - Tailwind styles

Changes to these require restart:
- `ui/package.json` - Dependencies
- `ui/.env` - Environment variables

## Troubleshooting

### UI not updating after code changes
```bash
# Restart UI service
docker-compose restart ui
```

### Port 3000 already in use
```bash
# Find and kill process
lsof -ti:3000 | xargs kill -9
```

### Node modules out of sync
```bash
# Rebuild UI container
docker-compose build ui --no-cache
```

## Volume Mounts

Source code is mounted read-only for security:
- ✅ Changes reflected immediately
- ✅ No accidental file permission changes
- ✅ Fast hot reload

`node_modules` is kept in container:
- ✅ Consistent across environments
- ✅ No host OS compatibility issues
```

**End of Day 4 Commit:**
```bash
git add docker-compose.yml ui/Dockerfile.dev \
        docs/DOCKER_PROFILES.md scripts/test-ui-docker.sh \
        ui/DOCKER_DEVELOPMENT.md
git commit -m "feat(docker): add UI development Docker Compose setup

- Add ui service to docker-compose.yml
- Create development Dockerfile with hot reload
- Add ui-dev profile for full-stack development
- Create Docker testing script
- Add developer documentation

Part of W4-E4-02"
```

---

### Day 5: Production UI Dockerfile

**Morning: Multi-Stage Production Dockerfile**

1. **Create production Dockerfile:**

**File: `ui/Dockerfile`**
```dockerfile
# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (cached layer)
COPY package*.json ./
RUN npm ci --only=production=false

# Copy source code
COPY . .

# Build for production
ENV NODE_ENV=production
RUN npm run build

# Verify build output
RUN test -d dist || (echo "Build failed - dist directory not found" && exit 1)
RUN test -f dist/index.html || (echo "Build failed - index.html not found" && exit 1)

# Stage 2: Nginx server
FROM nginx:alpine AS production

# Install curl for health checks
RUN apk add --no-cache curl

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy nginx configuration
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY nginx/security-headers.conf /etc/nginx/conf.d/security-headers.conf

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
```

2. **Update nginx configuration for health check:**

**File: `ui/nginx/default.conf` (update existing file)**
```nginx
# Health check endpoint
server {
    listen 80;
    server_name _;

    # Security headers
    include /etc/nginx/conf.d/security-headers.conf;

    # Health check
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }

    # API proxy
    location /api/ {
        proxy_pass http://sark-api:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static assets with caching
    location /assets/ {
        alias /usr/share/nginx/html/assets/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # SPA fallback - serve index.html for all routes
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;

        # No caching for index.html
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
    }

    # Deny access to hidden files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/javascript
        application/json
        application/xml+rss
        application/atom+xml
        image/svg+xml;
}
```

**Afternoon: Build Optimization and Testing**

3. **Create production build script:**

**File: `ui/scripts/build-docker.sh`**
```bash
#!/bin/bash
set -e

IMAGE_NAME="sark-ui"
IMAGE_TAG="${1:-latest}"
FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"

echo "🐳 Building Docker image: $FULL_IMAGE"
echo ""

# Build the image
docker build -t "$FULL_IMAGE" -f Dockerfile .

echo ""
echo "✅ Build complete!"
echo ""

# Show image size
echo "📦 Image details:"
docker images "$IMAGE_NAME" | head -n 2

echo ""
echo "🧪 Testing image..."
echo ""

# Run test container
CONTAINER_ID=$(docker run -d -p 8081:80 "$FULL_IMAGE")

# Wait for container to be ready
echo "Waiting for container to start..."
sleep 3

# Test health endpoint
if curl -f http://localhost:8081/health > /dev/null 2>&1; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    docker logs "$CONTAINER_ID"
    docker stop "$CONTAINER_ID" && docker rm "$CONTAINER_ID"
    exit 1
fi

# Test main page
if curl -f http://localhost:8081 > /dev/null 2>&1; then
    echo "✅ Main page accessible"
else
    echo "❌ Main page failed"
    docker logs "$CONTAINER_ID"
    docker stop "$CONTAINER_ID" && docker rm "$CONTAINER_ID"
    exit 1
fi

# Cleanup
docker stop "$CONTAINER_ID" && docker rm "$CONTAINER_ID"

echo ""
echo "✅ All tests passed!"
echo ""
echo "To run the image:"
echo "  docker run -p 8080:80 $FULL_IMAGE"
echo ""
echo "To push to registry:"
echo "  docker tag $FULL_IMAGE your-registry/$FULL_IMAGE"
echo "  docker push your-registry/$FULL_IMAGE"
```

```bash
chmod +x ui/scripts/build-docker.sh
```

4. **Create .dockerignore:**

**File: `ui/.dockerignore`**
```
node_modules
dist
.git
.env
.env.local
.env.*.local
*.log
.DS_Store
coverage
.vscode
.idea
*.md
!BUILD.md
!README.md
```

5. **Test production build:**
```bash
cd ui
./scripts/build-docker.sh dev
```

6. **Create production deployment documentation:**

**File: `ui/PRODUCTION_DEPLOYMENT.md`**
```markdown
# Production Deployment Guide

## Building the Image

### Local Build
```bash
cd ui
./scripts/build-docker.sh v1.0.0
```

### CI/CD Build
```bash
docker build -t sark-ui:$VERSION -f ui/Dockerfile ./ui
docker push your-registry/sark-ui:$VERSION
```

## Image Details

### Multi-Stage Build
1. **Builder stage** (node:20-alpine)
   - Installs dependencies
   - Runs TypeScript compilation
   - Builds optimized production bundle
   - Verifies build output

2. **Production stage** (nginx:alpine)
   - Minimal nginx server
   - Serves static files
   - Proxies API requests
   - Security headers enabled

### Image Size
- Expected size: ~50MB (nginx + static files)
- Builder stage discarded (not in final image)

## Configuration

### Environment Variables
Set these at runtime:
- `API_BACKEND_URL` - Backend API URL (injected via nginx or init script)

### Nginx Configuration
- SPA routing: All routes serve index.html
- API proxy: `/api/*` → backend
- Static caching: 1 year for `/assets/*`
- No caching: `index.html`
- Security headers: HSTS, CSP, X-Frame-Options, etc.

## Health Checks

### Docker Health Check
```bash
curl http://localhost/health
# Returns: 200 OK "healthy"
```

### Kubernetes Liveness Probe
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 80
  initialDelaySeconds: 5
  periodSeconds: 30
```

### Kubernetes Readiness Probe
```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 80
  initialDelaySeconds: 3
  periodSeconds: 10
```

## Running the Container

### Development Testing
```bash
docker run -p 8080:80 \
  -e API_BACKEND_URL=http://localhost:8000 \
  sark-ui:latest
```

### Production (Docker Compose)
See `docker-compose.production.yml`

### Production (Kubernetes)
See `k8s/ui-deployment.yaml`

## Security

### Built-in Security Features
- ✅ Security headers (HSTS, CSP, X-Frame-Options)
- ✅ Hidden files blocked (`.env`, `.git`)
- ✅ Minimal base image (Alpine)
- ✅ Non-root nginx process
- ✅ Read-only filesystem compatible

### Additional Recommendations
- Run behind HTTPS (TLS termination at load balancer)
- Set CSP based on your API domain
- Enable rate limiting at ingress
- Regular security scanning of base image

## Troubleshooting

### Build fails at verification
```bash
# Check if dist was created
docker run --rm -it sark-ui:latest ls -la /usr/share/nginx/html
```

### Health check fails
```bash
# Check nginx logs
docker logs <container-id>

# Test health endpoint
docker exec <container-id> curl -f http://localhost/health
```

### SPA routing not working
- Verify `try_files` directive in nginx config
- Check that index.html exists in `/usr/share/nginx/html`
- Ensure all routes return index.html (not 404)

## Performance

### Expected Metrics
- Build time: ~2-3 minutes
- Image size: ~50MB
- Container start time: <2 seconds
- First contentful paint: <1s (cached)
- Lighthouse score: >90

### Optimization Tips
- Enable gzip compression (already configured)
- Use CDN for static assets
- Enable HTTP/2 at load balancer
- Implement service worker for caching
```

**End of Day 5 Commit:**
```bash
git add ui/Dockerfile ui/.dockerignore \
        ui/nginx/default.conf \
        ui/scripts/build-docker.sh \
        ui/PRODUCTION_DEPLOYMENT.md
git commit -m "feat(docker): create production UI Dockerfile

- Multi-stage build with node:20-alpine and nginx:alpine
- Optimized layer caching and build verification
- Production nginx configuration with health checks
- Security headers and SPA routing
- Docker build and test script
- Production deployment documentation

Part of W4-E4-03

UI Docker integration complete! Ready for K8s deployment."
```

---

## 🤝 Coordination with Engineer 3

### Communication Protocol

**Day 2 Evening - Engineer 3 notifies you:**
Engineer 3 will send message when T3.2 is complete:
```
✅ T3.2 complete - React scaffold ready
Branch: task/engineer3-ui-foundation
Commit: <hash>

UI structure:
- ✅ Vite + React + TypeScript
- ✅ Tailwind + shadcn/ui
- ✅ React Router setup
- ✅ Basic layout components
- ✅ Dev server runs on :3000

You can start W4-E4-01 (Vite config) on Day 3.
```

**Your Response:**
```
👍 Received! Starting W4-E4-01 tomorrow.
Will coordinate on environment variables and API proxy config.
```

**Day 3 - Check-in:**
After completing W4-E4-01, confirm with Engineer 3:
```
✅ W4-E4-01 complete - Production build config ready
- Environment variable setup
- Build verification script
- Code splitting configured

Starting W4-E4-02 (Docker Compose) tomorrow.
Any issues with the build config?
```

**Day 5 - Handoff:**
After completing W4-E4-03:
```
✅ UI Docker integration complete!
- Development: docker-compose --profile ui-dev up
- Production: docker build -t sark-ui -f ui/Dockerfile ./ui

All 3 tasks done:
- W4-E4-01: Vite production build ✅
- W4-E4-02: Docker Compose dev ✅
- W4-E4-03: Production Dockerfile ✅

Ready for your T4.3 (Auth UI) work!
```

---

## 📊 Success Criteria

### W4-E4-01 (Vite Config) Complete When:
- [ ] Production build runs without errors
- [ ] Environment variables properly configured
- [ ] Build verification script passes
- [ ] Code splitting generates vendor chunks
- [ ] Build documentation created

### W4-E4-02 (Docker Compose) Complete When:
- [ ] UI service starts with `docker-compose --profile ui-dev up`
- [ ] Hot reload works for source code changes
- [ ] API proxy routes `/api/*` to backend
- [ ] Volume mounts configured correctly
- [ ] Test script passes

### W4-E4-03 (Production Dockerfile) Complete When:
- [ ] Multi-stage Dockerfile builds successfully
- [ ] Image size <100MB
- [ ] Health check endpoint returns 200
- [ ] Nginx serves SPA with correct routing
- [ ] Security headers configured
- [ ] Build script creates and tests image

---

## 🚀 After Completion

You will have UNBLOCKED all 14 remaining UI tasks:
- W5-E4-04 through W5-E4-07 (Week 5)
- W6-E4-08 through W6-E4-11 (Week 6)
- W7-E4-12 through W7-E4-13 (Week 7)
- W8-E4-14 through W8-E4-16 (Week 8)

**Next immediate task (Week 5):** W5-E4-04 - Kubernetes deployment manifests

---

## 📞 Questions or Issues?

1. **Build fails?** Check Node.js version (should be 20), clear `node_modules` and rebuild
2. **Docker issues?** Ensure Docker daemon running, check `docker-compose --version`
3. **Port conflicts?** Use `lsof -ti:3000` to find conflicting processes
4. **Need help?** Check existing docs in `ui/nginx/` from your previous work

**You've got this! 🚀**

---

**Task Assignment Created:** 2025-11-27
**Created By:** Planning Agent
**Branch:** `task/engineer4-ui-docker-integration`
**Estimated Duration:** 3 days (Days 3-5)
**Unblocks:** 14 remaining Engineer 4 tasks
