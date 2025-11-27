# Engineer 4 (DevOps/Infrastructure) Tasks

**Your Role:** DevOps and Infrastructure
**Total Tasks:** 2 tasks over 8 weeks
**Estimated Effort:** ~5 days

You're making sure everything deploys smoothly and runs reliably.

---

## Your Tasks

### ✅ T2.4 - Docker Compose Profiles
**Week:** 2
**Duration:** 1-2 days
**Priority:** P0 (Critical - blocks quickstart guide)

**What you're building:**
Simplified Docker Compose profiles for different use cases.

**Deliverables:**
1. **Update `docker-compose.yml` with profiles:**

   ```yaml
   services:
     # Core services (in all profiles)
     api:
       profiles: ["minimal", "standard", "full"]
       # ... config

     postgres:
       profiles: ["minimal", "standard", "full"]
       # ... config

     redis:
       profiles: ["minimal", "standard", "full"]
       # ... config

     opa:
       profiles: ["minimal", "standard", "full"]
       # ... config

     # Standard profile adds monitoring
     prometheus:
       profiles: ["standard", "full"]
       # ... config

     grafana:
       profiles: ["standard", "full"]
       # ... config

     # Full profile includes everything
     ldap:
       profiles: ["standard", "full"]
       # ... config

     vault:
       profiles: ["full"]
       # ... config

     consul:
       profiles: ["full"]
       # ... config

     kong:
       profiles: ["full"]
       # ... config
   ```

2. **Profile Documentation:**
   - `minimal`: API + PostgreSQL + Redis + OPA (fastest startup)
   - `standard`: + Monitoring (Prometheus, Grafana) + Auth (LDAP)
   - `full`: Everything including Kong, Vault, Consul

3. **Update README.md:**
   ```bash
   # Minimal (quick start)
   docker compose --profile minimal up -d

   # Standard (with monitoring)
   docker compose --profile standard up -d

   # Full (all services)
   docker compose --profile full up -d
   ```

4. **Test Each Profile:**
   - Test on clean system (no existing volumes)
   - Verify startup time for each
   - Ensure health checks pass
   - Document any profile-specific configuration

5. **Create Profile Comparison Table:**
   | Service | Minimal | Standard | Full |
   |---------|---------|----------|------|
   | API | ✅ | ✅ | ✅ |
   | PostgreSQL | ✅ | ✅ | ✅ |
   | Redis | ✅ | ✅ | ✅ |
   | OPA | ✅ | ✅ | ✅ |
   | Prometheus | ❌ | ✅ | ✅ |
   | Grafana | ❌ | ✅ | ✅ |
   | LDAP | ❌ | ✅ | ✅ |
   | Vault | ❌ | ❌ | ✅ |
   | Kong | ❌ | ❌ | ✅ |

**Acceptance Criteria:**
- [ ] `minimal` profile starts in <30 seconds
- [ ] `standard` profile includes monitoring
- [ ] `full` profile includes all services
- [ ] Each profile tested on clean system
- [ ] Documentation updated with when to use each

**Dependencies:**
- Current docker-compose.yml

**Claude Code Prompt:**
```
Update SARK docker-compose.yml with three profiles: minimal, standard, full.

Profile configurations:
- minimal: API + PostgreSQL + Redis + OPA (for quick start)
- standard: + Prometheus + Grafana + LDAP (for development)
- full: + Vault + Consul + Kong (complete stack)

Test each profile and document startup times.
Update README.md with usage instructions and comparison table.
```

---

### ✅ T8.1 - Docker & Kubernetes Integration
**Week:** 8
**Duration:** 3-4 days
**Priority:** P0 (Critical - required for launch)

**What you're building:**
Production-ready deployment for UI and complete SARK stack.

**Deliverables:**
1. **UI Dockerfile** (`ui/Dockerfile`):
   ```dockerfile
   # Multi-stage build
   FROM node:20-alpine AS builder

   WORKDIR /app
   COPY package*.json ./
   RUN npm ci --only=production

   COPY . .
   RUN npm run build

   # Production image
   FROM nginx:alpine

   # Copy built assets
   COPY --from=builder /app/dist /usr/share/nginx/html

   # Nginx config for SPA routing
   COPY nginx.conf /etc/nginx/conf.d/default.conf

   EXPOSE 80
   CMD ["nginx", "-g", "daemon off;"]
   ```

2. **Nginx Configuration** (`ui/nginx.conf`):
   ```nginx
   server {
     listen 80;
     server_name _;
     root /usr/share/nginx/html;
     index index.html;

     # Gzip compression
     gzip on;
     gzip_types text/plain text/css application/json application/javascript;

     # SPA routing - all routes go to index.html
     location / {
       try_files $uri $uri/ /index.html;
     }

     # API proxy (optional, for same-origin)
     location /api {
       proxy_pass http://api:8000;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
     }

     # Health check
     location /health {
       access_log off;
       return 200 "healthy\n";
     }
   }
   ```

3. **Update docker-compose.yml:**
   ```yaml
   services:
     ui:
       build:
         context: ./ui
         dockerfile: Dockerfile
       ports:
         - "3000:80"
       environment:
         - VITE_API_URL=${API_URL:-http://localhost:8000}
       depends_on:
         - api
       profiles: ["standard", "full"]
       healthcheck:
         test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/health"]
         interval: 30s
         timeout: 10s
         retries: 3
   ```

4. **Kubernetes Manifests:**

   **UI Deployment** (`k8s/ui-deployment.yaml`):
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: sark-ui
     namespace: sark-system
   spec:
     replicas: 2
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
           image: sark/ui:latest
           ports:
           - containerPort: 80
           env:
           - name: VITE_API_URL
             value: "http://sark-api:8000"
           resources:
             requests:
               memory: "128Mi"
               cpu: "100m"
             limits:
               memory: "256Mi"
               cpu: "200m"
           livenessProbe:
             httpGet:
               path: /health
               port: 80
             initialDelaySeconds: 10
             periodSeconds: 30
           readinessProbe:
             httpGet:
               path: /health
               port: 80
             initialDelaySeconds: 5
             periodSeconds: 10
   ```

   **UI Service** (`k8s/ui-service.yaml`):
   ```yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: sark-ui
     namespace: sark-system
   spec:
     selector:
       app: sark-ui
     ports:
     - protocol: TCP
       port: 80
       targetPort: 80
     type: ClusterIP
   ```

   **UI Ingress** (`k8s/ui-ingress.yaml`):
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: sark-ui
     namespace: sark-system
     annotations:
       cert-manager.io/cluster-issuer: "letsencrypt-prod"
   spec:
     ingressClassName: nginx
     tls:
     - hosts:
       - sark.example.com
       secretName: sark-tls
     rules:
     - host: sark.example.com
       http:
         paths:
         - path: /
           pathType: Prefix
           backend:
             service:
               name: sark-ui
               port:
                 number: 80
         - path: /api
           pathType: Prefix
           backend:
             service:
               name: sark-api
               port:
                 number: 8000
   ```

5. **Update Helm Chart** (`helm/sark/values.yaml`):
   ```yaml
   ui:
     enabled: true
     replicas: 2
     image:
       repository: sark/ui
       tag: "latest"
       pullPolicy: IfNotPresent
     service:
       type: ClusterIP
       port: 80
     ingress:
       enabled: true
       className: nginx
       hosts:
         - host: sark.example.com
           paths:
             - path: /
               pathType: Prefix
     resources:
       requests:
         memory: 128Mi
         cpu: 100m
       limits:
         memory: 256Mi
         cpu: 200m
   ```

   Update `helm/sark/templates/` with UI deployment, service, ingress templates.

6. **CI/CD Pipeline** (`.github/workflows/ui-build.yml`):
   ```yaml
   name: UI Build and Publish

   on:
     push:
       branches: [main]
       paths:
         - 'ui/**'

   jobs:
     build:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4

         - name: Set up Docker Buildx
           uses: docker/setup-buildx-action@v3

         - name: Build UI
           run: |
             cd ui
             docker build -t sark/ui:${{ github.sha }} .

         - name: Run tests
           run: |
             docker run sark/ui:${{ github.sha }} npm test

         - name: Push to registry
           run: |
             docker tag sark/ui:${{ github.sha }} sark/ui:latest
             docker push sark/ui:latest
   ```

7. **Environment Configuration:**
   - `.env.production` template
   - ConfigMap for K8s
   - Secrets management

**Acceptance Criteria:**
- [ ] `docker compose up` includes UI
- [ ] UI accessible at http://localhost:3000
- [ ] Kubernetes deployment works
- [ ] Helm chart includes UI
- [ ] CI/CD pipeline builds and tests UI
- [ ] Production deployment tested
- [ ] Health checks pass

**Dependencies:**
- Week 1-7 (UI must be functional)

**Claude Code Prompt:**
```
Integrate SARK UI into Docker and Kubernetes deployments.

Tasks:
1. Create ui/Dockerfile (multi-stage build with Nginx)
2. Create ui/nginx.conf for SPA routing
3. Add UI service to docker-compose.yml
4. Create Kubernetes manifests (deployment, service, ingress)
5. Update Helm chart with UI resources
6. Create CI/CD pipeline for UI builds

Test that:
- Docker Compose works with UI
- Kubernetes deployment works
- Health checks pass
- Helm chart deploys correctly
```

---

## Your Timeline

| Week | Task | Duration | Focus |
|------|------|----------|-------|
| **2** | T2.4 | 1-2 days | Docker Compose profiles |
| **3-7** | — | — | Support, review infra changes |
| **8** | T8.1 | 3-4 days | Docker + K8s integration |

## Your Responsibilities

### Infrastructure
- Maintain Docker configurations
- Manage Kubernetes manifests
- Update Helm charts
- Monitor deployment health

### CI/CD
- Build pipelines
- Automated testing
- Docker image publishing
- Deployment automation

### Monitoring
- Prometheus configuration
- Grafana dashboards
- Alert rules
- Health checks

### Documentation
- Deployment guides
- Troubleshooting runbooks
- Infrastructure diagrams

## Tips for Success

### Docker Best Practices
- Multi-stage builds for smaller images
- Use alpine base images
- Cache npm dependencies in separate layer
- Security: non-root user, no unnecessary packages
- Health checks for all services

### Kubernetes Best Practices
- Resource limits and requests
- Liveness and readiness probes
- PodDisruptionBudgets for high availability
- Security contexts
- Network policies

### Testing Deployments
- Test on clean cluster
- Verify all pods are ready
- Check logs for errors
- Test ingress routing
- Verify persistent volumes

### Performance
- Optimize Docker layer caching
- Minimize image size
- Configure resource limits appropriately
- Use CDN for static assets (production)

---

**You make SARK deployable and reliable!** 🚀
