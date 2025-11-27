# Engineer 4 - Docker & Kubernetes Integration

**Status:** Ready to start (waiting for Engineer 3 to fix build)
**Estimated Time:** 3-5 days
**Branch:** Current branch or new feature branch
**Dependencies:** Engineer 3 must complete TypeScript fixes first

---

## Mission

Complete Docker, Kubernetes, and Helm integration for the UI. You have 14 tasks remaining across Weeks 4-8.

---

## Phase 1: Development Docker (Day 1 - CAN START IN PARALLEL)

**Don't wait for production build!** Use dev server while Engineer 3 fixes types.

### Task 1: Create Development Docker Setup

**File:** `frontend/Dockerfile.dev`
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

### Task 2: Add UI Service to docker-compose.yml

**File:** `docker-compose.yml` (add to services section)
```yaml
services:
  # ... existing services ...

  frontend-dev:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    volumes:
      - ./frontend/src:/app/src:ro
      - ./frontend/public:/app/public:ro
      - ./frontend/index.html:/app/index.html:ro
      - ./frontend/vite.config.ts:/app/vite.config.ts:ro
      - /app/node_modules
    environment:
      - VITE_API_BASE_URL=http://sark-api:8000
    depends_on:
      - sark-api
    networks:
      - sark-network
    profiles:
      - full
      - ui-dev

  # Production frontend (uncomment after build works)
  # frontend-prod:
  #   build:
  #     context: ./frontend
  #     dockerfile: Dockerfile
  #   ports:
  #     - "8080:80"
  #   depends_on:
  #     - sark-api
  #   profiles:
  #     - production

networks:
  sark-network:
    driver: bridge
```

### Task 3: Test Development Setup

```bash
docker-compose --profile ui-dev up

# UI: http://localhost:3000
# API: http://localhost:8000
# Hot reload should work
```

**Deliverable:** Development environment working (Day 1)

---

## Phase 2: Production Docker (After Engineer 3 Fixes - Days 2-3)

### Task 4: Verify Production Dockerfile

Engineer 3 already created `frontend/Dockerfile` - just needs to work!

**File:** `frontend/Dockerfile` (already exists)
```dockerfile
# Multi-stage build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Once Engineer 3's build succeeds:
1. Uncomment frontend-prod in docker-compose.yml
2. Test: `docker-compose --profile production up`
3. Verify UI at http://localhost:8080

**Deliverable:** Production Docker working (Day 2)

---

## Phase 3: Kubernetes Manifests (Days 3-4)

### Task 5: Create UI Deployment

**File:** `k8s/ui-deployment.yaml`
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sark-ui
  namespace: sark
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sark-ui
  template:
    metadata:
      labels:
        app: sark-ui
    spec:
      containers:
      - name: ui
        image: sark-ui:latest
        ports:
        - containerPort: 80
        livenessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 3
          periodSeconds: 10
        resources:
          requests:
            memory: "64Mi"
            cpu: "100m"
          limits:
            memory: "128Mi"
            cpu: "200m"
        env:
        - name: API_BASE_URL
          value: "http://sark-api:8000"
---
apiVersion: v1
kind: Service
metadata:
  name: sark-ui
  namespace: sark
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 80
  selector:
    app: sark-ui
```

**Deliverable:** K8s manifests created (Day 3)

---

## Phase 4: Helm Chart Updates (Days 4-5)

### Task 6: Update Helm Chart

Add UI to existing Helm chart in `helm/sark/`:

**Files to create/update:**
1. `helm/sark/templates/ui-deployment.yaml`
2. `helm/sark/templates/ui-service.yaml`
3. `helm/sark/templates/ui-ingress.yaml`
4. `helm/sark/values.yaml` (add UI configuration)

**Example values.yaml addition:**
```yaml
ui:
  enabled: true
  replicaCount: 3
  image:
    repository: sark-ui
    tag: latest
    pullPolicy: IfNotPresent
  service:
    type: LoadBalancer
    port: 80
  resources:
    requests:
      memory: "64Mi"
      cpu: "100m"
    limits:
      memory: "128Mi"
      cpu: "200m"
  ingress:
    enabled: true
    className: nginx
    hosts:
      - host: sark.example.com
        paths:
          - path: /
            pathType: Prefix
```

**Deliverable:** Helm chart with UI support (Day 5)

---

## Quick Task Checklist

### Day 1 (Can Start Now):
- [ ] Create Dockerfile.dev
- [ ] Add frontend-dev to docker-compose.yml
- [ ] Test dev environment with hot reload
- [ ] Document development workflow

### Days 2-3 (After Engineer 3 Fixes):
- [ ] Test production Dockerfile build
- [ ] Verify nginx.conf works correctly
- [ ] Enable frontend-prod in docker-compose.yml
- [ ] Test production container locally

### Days 3-4:
- [ ] Create k8s/ui-deployment.yaml
- [ ] Create k8s/ui-service.yaml
- [ ] Test K8s deployment (if cluster available)
- [ ] Document K8s deployment process

### Days 4-5:
- [ ] Update Helm chart templates
- [ ] Add UI values to values.yaml
- [ ] Test Helm installation
- [ ] Document Helm deployment
- [ ] Create deployment troubleshooting guide

---

## Files You Already Created

✅ You already did great planning work:
- `frontend/Dockerfile` (production multi-stage) - Engineer 3 created
- `frontend/nginx.conf` (SPA routing + API proxy) - Engineer 3 created
- `frontend/.dockerignore` - Engineer 3 created
- `frontend/.env.production` - Engineer 3 created
- `frontend/DEPLOYMENT.md` - Engineer 3 created
- `docs/UI_DOCKER_INTEGRATION_PLAN.md` (45 pages!) - YOU created

**Most of your planning is done - now it's execution time!**

---

## Testing Checklist

### Development Mode:
```bash
# Test 1: Dev server works
docker-compose --profile ui-dev up
curl http://localhost:3000

# Test 2: Hot reload works
# Edit frontend/src/App.tsx
# Check browser auto-refreshes

# Test 3: API proxy works
curl http://localhost:3000/api/health
```

### Production Mode:
```bash
# Test 1: Build succeeds
cd frontend
docker build -t sark-ui .

# Test 2: Container runs
docker run -p 8080:80 sark-ui
curl http://localhost:8080

# Test 3: Health check works
curl http://localhost:8080/health

# Test 4: SPA routing works
curl http://localhost:8080/servers
# Should return index.html (not 404)
```

### Kubernetes:
```bash
# Test 1: Deploy to K8s
kubectl apply -f k8s/ui-deployment.yaml

# Test 2: Check pods
kubectl get pods -n sark

# Test 3: Access service
kubectl port-forward svc/sark-ui 8080:80 -n sark
curl http://localhost:8080
```

---

## Success Criteria

**Phase 1 Complete When:**
- [ ] `docker-compose --profile ui-dev up` starts UI with hot reload
- [ ] Changes to source files trigger automatic refresh
- [ ] API proxy routes requests correctly

**Phase 2 Complete When:**
- [ ] Production Dockerfile builds without errors
- [ ] Image size < 100MB
- [ ] `docker run` starts container successfully
- [ ] Health endpoint returns 200 OK
- [ ] SPA routing works (all routes serve index.html)

**Phase 3 Complete When:**
- [ ] K8s manifests apply without errors
- [ ] Pods reach Running state
- [ ] Service is accessible
- [ ] Health checks pass

**Phase 4 Complete When:**
- [ ] `helm install` succeeds
- [ ] All UI components deployed
- [ ] Ingress routes traffic correctly
- [ ] Documentation complete

---

## Coordination with Engineer 3

**Wait for this notification:**
```
✅ Engineer 3: TypeScript errors fixed!
✅ npm run build succeeds
✅ Production Dockerfile builds
✅ Ready for your production Docker testing
```

**Until then:** Work on Phase 1 (development Docker) - doesn't need production build!

---

## Timeline Summary

```
Day 1:   Development Docker (CAN START NOW)
Day 2:   Production Docker testing (after E3 fixes)
Day 3:   Kubernetes manifests
Day 4:   Helm chart updates
Day 5:   Testing and documentation
```

**Total:** 5 days to complete all infrastructure work

---

## Need Help?

**Your own documentation:**
- `docs/UI_DOCKER_INTEGRATION_PLAN.md` - Your 45-page plan!
- `docs/DOCKER_PROFILES.md` - Docker profiles guide

**Engineer 3's work:**
- `frontend/Dockerfile` - Production build
- `frontend/nginx.conf` - Nginx config
- `frontend/DEPLOYMENT.md` - Deployment guide

**Backend API:**
- Runs at http://localhost:8000
- Swagger docs at http://localhost:8000/docs

---

**YOU'VE GOT THIS! Most of your work is done - just need to execute! 🚀**

**Created:** 2025-11-27
**Status:** Ready to start Phase 1 now, Phase 2 after E3
**Timeline:** 5 days total
