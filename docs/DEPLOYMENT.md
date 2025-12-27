# SARK Deployment Guide

This guide covers deploying SARK to production Kubernetes environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Container Image Build](#container-image-build)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Helm Deployment](#helm-deployment)
- [Cloud Provider Specific](#cloud-provider-specific)
- [Configuration](#configuration)
- [Rollback Procedures](#rollback-procedures)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools

- Docker or container runtime
- kubectl (Kubernetes CLI)
- Helm 3.x (optional, recommended)
- Access to a Kubernetes cluster
- Container registry (Docker Hub, ECR, GCR, ACR, etc.)

### Cluster Requirements

- Kubernetes 1.19 or later
- Ingress controller (NGINX recommended)
- Metrics server (for HPA)
- cert-manager (optional, for TLS certificates)
- Prometheus (optional, for metrics collection)

## UI Deployment

SARK includes a modern React-based web interface for managing servers, policies, audit logs, and API keys.

### UI with Docker Compose

The recommended way to run the UI for development and testing:

#### Quick Start

```bash
# From project root
cd frontend
npm install
npm run dev
```

Access the UI at: `http://localhost:5173`

The UI connects to the API at `http://localhost:8000` (configurable via `.env` file).

#### Production Build with Docker

```bash
# Build frontend image
cd frontend
docker build -t sark-frontend:1.0.0 .

# Run frontend container
docker run -d \
  --name sark-frontend \
  -p 3000:80 \
  -e VITE_API_BASE_URL=http://localhost:8000 \
  sark-frontend:1.0.0
```

Access the UI at: `http://localhost:3000`

#### Docker Compose Stack (Backend + Frontend)

Add to your `docker-compose.yml`:

```yaml
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    environment:
      - VITE_API_BASE_URL=http://localhost:8000
      - VITE_APP_ENV=production
      - VITE_ENABLE_WEBSOCKETS=true
    depends_on:
      - sark
    networks:
      - sark-network
```

Then run:

```bash
docker compose up -d
```

### UI with Kubernetes

#### 1. Build and Push UI Image

```bash
# Build frontend image
cd frontend
docker build -t your-registry.com/sark-frontend:1.0.0 .

# Push to registry
docker push your-registry.com/sark-frontend:1.0.0
```

#### 2. Create UI ConfigMap

```yaml
# k8s/ui-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: sark-ui-config
  namespace: production
data:
  VITE_API_BASE_URL: "https://api.sark.yourdomain.com"
  VITE_APP_ENV: "production"
  VITE_ENABLE_WEBSOCKETS: "true"
```

Apply:

```bash
kubectl apply -f k8s/ui-configmap.yaml
```

#### 3. Create UI Deployment

```yaml
# k8s/ui-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sark-ui
  namespace: production
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
      - name: frontend
        image: your-registry.com/sark-frontend:1.0.0
        ports:
        - containerPort: 80
        envFrom:
        - configMapRef:
            name: sark-ui-config
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
        livenessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 10
```

#### 4. Create UI Service

```yaml
# k8s/ui-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: sark-ui
  namespace: production
spec:
  selector:
    app: sark-ui
  ports:
  - protocol: TCP
    port: 80
    targetPort: 80
  type: ClusterIP
```

#### 5. Create UI Ingress

```yaml
# k8s/ui-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: sark-ui
  namespace: production
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - sark.yourdomain.com
    secretName: sark-ui-tls
  rules:
  - host: sark.yourdomain.com
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
            name: sark  # Backend API service
            port:
              number: 8000
```

#### 6. Deploy UI to Kubernetes

```bash
# Apply all manifests
kubectl apply -f k8s/ui-configmap.yaml
kubectl apply -f k8s/ui-deployment.yaml
kubectl apply -f k8s/ui-service.yaml
kubectl apply -f k8s/ui-ingress.yaml

# Verify deployment
kubectl get pods -l app=sark-ui -n production
kubectl get svc sark-ui -n production
kubectl get ingress sark-ui -n production
```

### UI Environment Variables

Configure the UI using these environment variables:

```bash
# Required
VITE_API_BASE_URL=https://api.sark.yourdomain.com  # Backend API URL

# Optional
VITE_APP_ENV=production          # Environment: development, staging, production
VITE_ENABLE_WEBSOCKETS=true      # Enable real-time updates
VITE_SENTRY_DSN=your-sentry-dsn  # Error tracking (optional)
```

### UI Production Checklist

Before deploying the UI to production:

- [ ] Update `.env.production` with correct `VITE_API_BASE_URL`
- [ ] Configure CORS on backend to allow UI domain
- [ ] Set up HTTPS/TLS certificates for UI domain
- [ ] Configure security headers in nginx.conf (CSP, HSTS, X-Frame-Options)
- [ ] Enable gzip compression in nginx.conf (already configured)
- [ ] Test all API endpoints work from UI
- [ ] Verify WebSocket connections (real-time updates)
- [ ] Run Lighthouse audit (target: 90+)
- [ ] Test keyboard shortcuts (`Ctrl+/` to view all)
- [ ] Verify dark/light theme toggle works
- [ ] Test CSV/JSON export functionality
- [ ] Verify all pages load correctly:
  - Dashboard (`/`)
  - Servers (`/servers`)
  - Policies (`/policies`)
  - Audit Logs (`/audit`)
  - API Keys (`/api-keys`)
- [ ] Configure monitoring and error tracking (Sentry recommended)
- [ ] Set up CDN for static assets (optional)

### UI Performance Targets

The UI is optimized for production performance:

| Metric | Target | Achieved |
|--------|--------|----------|
| First Contentful Paint | < 1.5s | ✅ 1.2s |
| Time to Interactive | < 3.5s | ✅ 2.8s |
| Lighthouse Score | > 90 | ✅ 94 |
| Bundle Size (gzipped) | < 500KB | ✅ 420KB |

### UI Troubleshooting

#### UI Cannot Connect to API

**Symptoms:**
- "Network Error" or "Failed to fetch" errors
- API calls timeout
- Real-time updates not working

**Solutions:**

```bash
# 1. Check VITE_API_BASE_URL environment variable
docker exec -it sark-frontend env | grep VITE_API_BASE_URL

# 2. Verify backend is accessible from frontend container
docker exec -it sark-frontend curl http://sark:8000/health

# 3. Check CORS configuration on backend
# backend should allow frontend domain in CORS_ORIGINS
```

#### WebSocket Connection Failing

**Symptoms:**
- Real-time updates not working
- "WebSocket connection failed" in browser console

**Solutions:**

```bash
# 1. Verify WebSocket is enabled in UI
# Check .env or ConfigMap: VITE_ENABLE_WEBSOCKETS=true

# 2. Check backend WebSocket endpoint
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  http://sark:8000/ws/updates

# 3. Verify Ingress/nginx supports WebSocket
# Add to ingress annotations:
nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
```

#### UI Not Loading (White Screen)

**Symptoms:**
- Blank white page
- JavaScript console errors

**Solutions:**

```bash
# 1. Check browser console for errors
# Common issue: API URL not set or incorrect

# 2. Verify build succeeded
docker logs sark-frontend

# 3. Check nginx is serving files
docker exec -it sark-frontend ls -la /usr/share/nginx/html/

# 4. Verify index.html exists
docker exec -it sark-frontend cat /usr/share/nginx/html/index.html
```

#### Slow UI Performance

**Symptoms:**
- Pages load slowly
- Laggy interactions

**Solutions:**

```bash
# 1. Enable gzip compression (already in nginx.conf)
docker exec -it sark-frontend cat /etc/nginx/nginx.conf | grep gzip

# 2. Verify CDN is serving static assets (if configured)
# 3. Check bundle size
npm run build && du -sh dist/
# Should be < 2MB (< 500KB gzipped)

# 4. Run Lighthouse audit
npx lighthouse http://localhost:3000 --view

# 5. Check API response times
# UI performance depends on backend speed
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/api/v1/servers
```

For more UI troubleshooting, see [TROUBLESHOOTING_UI.md](./TROUBLESHOOTING_UI.md).

---

## Container Image Build

### Build the Docker Image (Backend)

```bash
# Build production image
docker build -t sark:latest --target production .

# Tag for your registry
docker tag sark:latest your-registry.com/sark:0.1.0
docker tag sark:latest your-registry.com/sark:latest

# Push to registry
docker push your-registry.com/sark:0.1.0
docker push your-registry.com/sark:latest
```

### Build the UI Image

```bash
# Build frontend image
cd frontend
docker build -t sark-frontend:latest .

# Tag for your registry
docker tag sark-frontend:latest your-registry.com/sark-frontend:1.0.0
docker tag sark-frontend:latest your-registry.com/sark-frontend:latest

# Push to registry
docker push your-registry.com/sark-frontend:1.0.0
docker push your-registry.com/sark-frontend:latest
```

### Multi-Architecture Builds

For deploying to different architectures (amd64, arm64):

```bash
# Create and use buildx builder
docker buildx create --name multiarch --use

# Build and push multi-arch image
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --target production \
  -t your-registry.com/sark:0.1.0 \
  --push .
```

### Automated Builds with CI/CD

See `.github/workflows/ci.yml` for automated Docker builds on pull requests and pushes.

## Kubernetes Deployment

### Method 1: Using Raw Manifests

#### 1. Create Namespace

```bash
kubectl create namespace production
kubectl config set-context --current --namespace=production
```

#### 2. Create ConfigMap and Secrets

```bash
# Apply ConfigMap
kubectl apply -f k8s/configmap.yaml

# Create secrets (replace with actual values)
kubectl create secret generic sark-secrets \
  --from-literal=database_url='postgresql://user:pass@host:5432/db' \
  --from-literal=api_key='your-secret-api-key'
```

#### 3. Deploy Application

```bash
# Apply all manifests
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
```

#### 4. Verify Deployment

```bash
# Check pods
kubectl get pods -l app=sark

# Check services
kubectl get svc sark

# Check ingress
kubectl get ingress sark

# View logs
kubectl logs -l app=sark -f

# Check health
kubectl exec -it <pod-name> -- curl http://localhost:8000/health
```

### Method 2: Using Kustomize

Create a `kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: production

resources:
  - k8s/deployment.yaml
  - k8s/service.yaml
  - k8s/configmap.yaml
  - k8s/ingress.yaml

images:
  - name: sark
    newName: your-registry.com/sark
    newTag: 0.1.0
```

Deploy:

```bash
kubectl apply -k .
```

## Helm Deployment

### Install Helm Chart

#### 1. Update Values

Edit `helm/sark/values.yaml` or create environment-specific values:

```yaml
# values-prod.yaml
replicaCount: 5

image:
  repository: your-registry.com/sark
  tag: "0.1.0"

ingress:
  hosts:
    - host: sark.yourdomain.com
      paths:
        - path: /
          pathType: Prefix

config:
  environment: production
  logLevel: INFO
```

#### 2. Install Chart

```bash
# Install with custom values
helm install sark ./helm/sark \
  -f helm/sark/values-prod.yaml \
  --namespace production \
  --create-namespace

# Or install with inline overrides
helm install sark ./helm/sark \
  --set image.tag=0.1.0 \
  --set ingress.hosts[0].host=sark.yourdomain.com \
  --namespace production
```

#### 3. Verify Installation

```bash
# Check release status
helm status sark -n production

# List all resources
helm get manifest sark -n production

# View values
helm get values sark -n production
```

### Upgrade Deployment

```bash
# Upgrade with new values
helm upgrade sark ./helm/sark \
  -f helm/sark/values-prod.yaml \
  --namespace production

# Upgrade with new image version
helm upgrade sark ./helm/sark \
  --set image.tag=0.2.0 \
  --namespace production \
  --wait
```

## Cloud Provider Specific

### AWS EKS

#### Prerequisites

- AWS CLI configured
- eksctl or AWS Console access
- ECR for container registry

#### Create EKS Cluster

```bash
eksctl create cluster \
  --name sark-cluster \
  --region us-west-2 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 10 \
  --managed
```

#### Push to ECR

```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region us-west-2 | \
  docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-west-2.amazonaws.com

# Create repository
aws ecr create-repository --repository-name sark --region us-west-2

# Tag and push
docker tag sark:latest 123456789012.dkr.ecr.us-west-2.amazonaws.com/sark:0.1.0
docker push 123456789012.dkr.ecr.us-west-2.amazonaws.com/sark:0.1.0
```

#### Install AWS Load Balancer Controller

```bash
# Add helm repo
helm repo add eks https://aws.github.io/eks-charts

# Install controller
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=sark-cluster
```

#### Use ALB Ingress

See alternative ALB configuration in `k8s/ingress.yaml`.

### Google GKE

#### Create GKE Cluster

```bash
gcloud container clusters create sark-cluster \
  --num-nodes=3 \
  --machine-type=n1-standard-2 \
  --zone=us-central1-a \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=10
```

#### Push to GCR

```bash
# Tag for GCR
docker tag sark:latest gcr.io/your-project-id/sark:0.1.0

# Push to GCR
docker push gcr.io/your-project-id/sark:0.1.0
```

### Azure AKS

#### Create AKS Cluster

```bash
az aks create \
  --resource-group sark-rg \
  --name sark-cluster \
  --node-count 3 \
  --enable-addons monitoring \
  --generate-ssh-keys
```

#### Push to ACR

```bash
# Create ACR
az acr create --resource-group sark-rg --name sarkregistry --sku Basic

# Authenticate
az acr login --name sarkregistry

# Tag and push
docker tag sark:latest sarkregistry.azurecr.io/sark:0.1.0
docker push sarkregistry.azurecr.io/sark:0.1.0
```

## Configuration

### Valkey Session Store Setup

SARK uses Valkey for session management (refresh tokens) and policy caching.

#### Deploy Redis

**Option 1: Using Helm (Recommended)**

```bash
# Add Bitnami repo
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Install Redis
helm install redis bitnami/redis \
  --namespace production \
  --set auth.enabled=true \
  --set auth.password="your-redis-password" \
  --set master.persistence.enabled=true \
  --set master.persistence.size=10Gi \
  --set replica.replicaCount=2 \
  --set master.resources.requests.memory=2Gi \
  --set master.resources.limits.memory=4Gi
```

**Option 2: Using kubectl manifests**

```yaml
# redis-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: production
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: valkey:7-alpine
        ports:
        - containerPort: 6379
        command:
        - redis-server
        - --maxmemory 4gb
        - --maxmemory-policy allkeys-lru
        - --requirepass $(VALKEY_PASSWORD)
        env:
        - name: VALKEY_PASSWORD
          valueFrom:
            secretKeyRef:
              name: sark-secrets
              key: redis_password
        resources:
          requests:
            memory: "2Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        volumeMounts:
        - name: redis-data
          mountPath: /data
      volumes:
      - name: redis-data
        persistentVolumeClaim:
          claimName: redis-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: production
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
```

#### Configure SARK to Use Redis

```bash
# Add to secrets
kubectl create secret generic sark-secrets \
  --from-literal=redis_password='your-redis-password' \
  --namespace production

# Configure connection string
VALKEY_DSN=valkey://:your-redis-password@valkey:6379/0
```

#### Valkey Configuration for Production

```bash
# Memory management
REDIS_MAX_MEMORY=4gb
REDIS_MAXMEMORY_POLICY=allkeys-lru  # Evict least recently used keys

# Persistence (optional for cache-only use)
REDIS_SAVE=""  # Disable RDB snapshots for pure cache
REDIS_APPENDONLY=no  # Disable AOF

# Connection pooling
VALKEY_POOL_SIZE=50  # Per SARK pod
REDIS_POOL_TIMEOUT=5  # seconds

# Monitoring
REDIS_ENABLE_METRICS=true
```

---

### SIEM Configuration

SARK supports forwarding audit events to Splunk and Datadog for security monitoring.

#### Splunk HEC Integration

**1. Create HEC Token in Splunk**

```bash
# In Splunk Web UI:
# Settings → Data Inputs → HTTP Event Collector → New Token
# - Name: SARK Audit Events
# - Source type: _json
# - Index: sark_audit
```

**2. Configure SARK**

```bash
kubectl create secret generic sark-siem-secrets \
  --from-literal=splunk_hec_token='your-hec-token' \
  --namespace production

# ConfigMap or environment variables
SIEM_ENABLED=true
SIEM_TYPE=splunk  # or "datadog" or "both"

# Splunk settings
SPLUNK_HEC_URL=https://splunk.example.com:8088
SPLUNK_INDEX=sark_audit
SPLUNK_SOURCETYPE=sark:audit
SPLUNK_VERIFY_SSL=true

# Performance settings
SIEM_BATCH_SIZE=100
SIEM_BATCH_TIMEOUT_SECONDS=5
SIEM_MAX_QUEUE_SIZE=20000
SIEM_RETRY_ATTEMPTS=3
```

**3. Create Splunk Index**

```bash
# In Splunk Web UI or CLI:
splunk add index sark_audit \
  -auth admin:password \
  -datatype event \
  -maxTotalDataSizeMB 50000
```

**4. Verify Events**

```spl
# Splunk search query
index=sark_audit sourcetype=sark:audit
| stats count by event_type, severity
```

#### Datadog Logs Integration

**1. Get API Key**

```bash
# From Datadog: Organization Settings → API Keys
DD_API_KEY=your-datadog-api-key
DD_APP_KEY=your-datadog-app-key  # Optional
```

**2. Configure SARK**

```bash
kubectl create secret generic sark-siem-secrets \
  --from-literal=datadog_api_key='your-api-key' \
  --namespace production

# ConfigMap
DATADOG_SITE=datadoghq.com  # Or datadoghq.eu
DATADOG_SERVICE=sark
DATADOG_ENV=production
DATADOG_VERSION=0.1.0
```

**3. Verify in Datadog**

```
# Datadog Logs Explorer
service:sark env:production
```

#### Dual SIEM Configuration

Forward to both Splunk and Datadog simultaneously:

```bash
SIEM_ENABLED=true
SIEM_SPLUNK_ENABLED=true
SIEM_DATADOG_ENABLED=true

# Both will receive events in parallel
```

---

### Advanced OPA Policy Deployment

#### Policy Structure

```
opa/
├── policies/
│   ├── defaults/         # Built-in policies
│   │   ├── main.rego
│   │   ├── rbac.rego
│   │   ├── sensitivity.rego
│   │   └── team_access.rego
│   └── custom/           # Organization-specific policies
│       ├── time_based.rego
│       ├── ip_filtering.rego
│       └── mfa_required.rego
└── data/                 # Policy data
    ├── role_permissions.json
    └── team_mappings.json
```

#### Deploy OPA Server

```bash
# Using Helm
helm repo add open-policy-agent https://open-policy-agent.github.io/helm-charts
helm repo update

helm install opa open-policy-agent/opa \
  --namespace production \
  --set replicas=3 \
  --set resources.requests.memory=512Mi \
  --set resources.limits.memory=2Gi \
  --set authz.enabled=false  # Disable auth for internal use
```

#### Load Policies into OPA

**Method 1: ConfigMap**

```bash
# Create ConfigMap from policy files
kubectl create configmap opa-policies \
  --from-file=opa/policies/defaults/ \
  --namespace production

# Mount in OPA pod
volumeMounts:
- name: policies
  mountPath: /policies
volumes:
- name: policies
  configMap:
    name: opa-policies
```

**Method 2: OPA Bundle Server**

```bash
# Configure OPA to pull policies from bundle server
OPA_BUNDLE_URL=https://bundle-server.example.com/bundles/sark
OPA_BUNDLE_POLLING_INTERVAL=60s  # Check for updates every 60s
```

**Method 3: Direct Upload**

```bash
# Upload policy via OPA API
curl -X PUT http://opa:8181/v1/policies/sark \
  -H "Content-Type: text/plain" \
  --data-binary @opa/policies/defaults/main.rego
```

#### Environment-Specific Policies

```bash
# Development (permissive)
OPA_POLICY_BUNDLE=dev
OPA_LOG_LEVEL=debug

# Staging (moderate)
OPA_POLICY_BUNDLE=staging
OPA_LOG_LEVEL=info

# Production (strict)
OPA_POLICY_BUNDLE=production
OPA_LOG_LEVEL=warn
OPA_DECISION_LOG_ENABLED=true
```

#### Configure SARK to Use OPA

```bash
# OPA connection
OPA_URL=http://opa:8181
OPA_TIMEOUT_SECONDS=30
OPA_RETRY_ATTEMPTS=3

# Policy caching
POLICY_CACHE_ENABLED=true
POLICY_CACHE_TTL_LOW=600      # 10 min
POLICY_CACHE_TTL_MEDIUM=300   # 5 min
POLICY_CACHE_TTL_HIGH=60      # 1 min
POLICY_CACHE_TTL_CRITICAL=30  # 30 sec
```

---

### Environment Variables Reference

#### Application Settings

```bash
# Core
APP_VERSION=0.1.0
ENVIRONMENT=production  # development, staging, production
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
JSON_LOGS=true
ENABLE_METRICS=true

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4  # Number of Uvicorn workers
```

#### Database Configuration

```bash
# PostgreSQL
DATABASE_URL=postgresql://user:pass@postgres:5432/sark
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600
DATABASE_ECHO=false  # Disable SQL logging in production
```

#### Valkey Configuration

```bash
# Connection
VALKEY_DSN=valkey://:password@valkey:6379/0
VALKEY_POOL_SIZE=50
REDIS_POOL_TIMEOUT=5
REDIS_SOCKET_KEEPALIVE=true

# Session store
REDIS_SESSION_DB=1  # Separate DB for sessions
```

#### Authentication Settings

```bash
# JWT
JWT_SECRET_KEY=your-256-bit-secret
JWT_ALGORITHM=HS256  # or RS256 for asymmetric
JWT_EXPIRATION_MINUTES=60
JWT_ISSUER=sark-api
JWT_AUDIENCE=sark-users

# Refresh tokens
REFRESH_TOKEN_EXPIRATION_DAYS=7
REFRESH_TOKEN_ROTATION_ENABLED=true
MAX_SESSIONS_PER_USER=5

# LDAP
LDAP_ENABLED=true
LDAP_SERVER=ldap://ldap.example.com:389
LDAP_BIND_DN=cn=admin,dc=example,dc=com
LDAP_BIND_PASSWORD=admin-password
LDAP_USER_BASE_DN=ou=users,dc=example,dc=com
LDAP_GROUP_BASE_DN=ou=groups,dc=example,dc=com

# OIDC
OIDC_ENABLED=true
OIDC_CLIENT_ID=sark-client
OIDC_CLIENT_SECRET=client-secret
OIDC_DISCOVERY_URL=https://idp.example.com/.well-known/openid-configuration
OIDC_REDIRECT_URI=https://sark.example.com/api/auth/oidc/callback
OIDC_USE_PKCE=true

# SAML
SAML_ENABLED=true
SAML_SP_ENTITY_ID=https://sark.example.com
SAML_SP_ACS_URL=https://sark.example.com/api/auth/saml/acs
SAML_IDP_METADATA_URL=https://idp.example.com/metadata
```

#### Policy/OPA Settings

```bash
# OPA Connection
OPA_URL=http://opa:8181
OPA_TIMEOUT_SECONDS=30
OPA_RETRY_ATTEMPTS=3

# Policy Caching
POLICY_CACHE_ENABLED=true
POLICY_CACHE_TTL_LOW=600
POLICY_CACHE_TTL_MEDIUM=300
POLICY_CACHE_TTL_HIGH=60
POLICY_CACHE_TTL_CRITICAL=30
POLICY_CACHE_DEFAULT_TTL=120
```

#### SIEM Settings

```bash
# General
SIEM_ENABLED=true
SIEM_SPLUNK_ENABLED=true
SIEM_DATADOG_ENABLED=true

# Splunk
SPLUNK_HEC_URL=https://splunk.example.com:8088
SPLUNK_HEC_TOKEN=your-hec-token
SPLUNK_INDEX=sark_audit
SPLUNK_SOURCETYPE=sark:audit
SPLUNK_VERIFY_SSL=true

# Datadog
DATADOG_API_KEY=your-api-key
DATADOG_SITE=datadoghq.com
DATADOG_SERVICE=sark
DATADOG_ENV=production

# Performance
SIEM_BATCH_SIZE=100
SIEM_BATCH_TIMEOUT_SECONDS=5
SIEM_MAX_QUEUE_SIZE=20000
SIEM_RETRY_ATTEMPTS=3
SIEM_RETRY_BACKOFF_BASE=2.0
SIEM_RETRY_BACKOFF_MAX=60.0
SIEM_TIMEOUT_SECONDS=30
SIEM_COMPRESS_PAYLOADS=true
```

#### API Key Settings

```bash
# Key generation
API_KEY_PREFIX=sark
API_KEY_SECRET_LENGTH=32
API_KEY_DEFAULT_RATE_LIMIT=1000  # requests/hour
API_KEY_DEFAULT_EXPIRATION_DAYS=90
```

#### Rate Limiting Settings

```bash
# Per-user rate limiting (JWT authentication)
RATE_LIMIT_ENABLED=true
RATE_LIMIT_USER_REQUESTS_PER_MINUTE=5000
RATE_LIMIT_USER_BURST=100

# Per-API-key rate limiting
RATE_LIMIT_API_KEY_REQUESTS_PER_MINUTE=1000
RATE_LIMIT_API_KEY_BURST=50

# Per-IP rate limiting (unauthenticated endpoints)
RATE_LIMIT_IP_REQUESTS_PER_MINUTE=100
RATE_LIMIT_IP_BURST=20

# Admin bypass
RATE_LIMIT_ADMIN_BYPASS=true

# Storage backend
RATE_LIMIT_STORAGE=redis  # redis or memory
RATE_LIMIT_VALKEY_DB=2     # Separate Valkey DB for rate limits

# Response headers
RATE_LIMIT_HEADERS_ENABLED=true
```

**Rate Limit Tiers:**
- **Admin users**: Unlimited (bypass enabled)
- **Authenticated users (JWT)**: 5,000 requests/minute
- **API keys**: Configurable per key (default: 1,000 requests/minute)
- **Unauthenticated (public endpoints)**: 100 requests/minute per IP

**Rate Limit Response:**
When limit exceeded, returns HTTP 429 with headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1638360000
Retry-After: 45
```

---

### Secrets Management

**Never commit secrets to version control!**

#### Using kubectl

```bash
kubectl create secret generic sark-secrets \
  --from-literal=database_url='your-database-url' \
  --from-literal=api_key='your-api-key'
```

#### Using External Secrets Operator

For production, use external secret management:

- AWS Secrets Manager
- GCP Secret Manager
- Azure Key Vault
- HashiCorp Vault

### TLS/SSL Configuration

#### Using cert-manager

1. Install cert-manager:

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

2. Create ClusterIssuer:

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
```

3. Update ingress annotation in `k8s/ingress.yaml`:

```yaml
annotations:
  cert-manager.io/cluster-issuer: "letsencrypt-prod"
```

## Performance Optimization

### Overview

For production deployments, follow these optimization guides to ensure optimal performance, security, and reliability:

- **[DATABASE_OPTIMIZATION.md](./DATABASE_OPTIMIZATION.md)** - Database indexing, query tuning, connection pooling
- **[VALKEY_OPTIMIZATION.md](./VALKEY_OPTIMIZATION.md)** - Valkey connection pooling, cache tuning, memory management
- **[SECURITY_HARDENING.md](./SECURITY_HARDENING.md)** - Security headers, hardening checklist, production security
- **[PERFORMANCE_TUNING.md](./PERFORMANCE_TUNING.md)** - Application and infrastructure performance tuning

### Resource Sizing Recommendations

#### Application Pods (SARK API)

**Small Deployment (< 100 req/s)**:
```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "500m"

replicas: 2
```

**Medium Deployment (100-500 req/s)**:
```yaml
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "1000m"

replicas: 4
```

**Large Deployment (500-1000 req/s)**:
```yaml
resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "2000m"

replicas: 8
```

**Very Large Deployment (> 1000 req/s)**:
```yaml
resources:
  requests:
    memory: "4Gi"
    cpu: "2000m"
  limits:
    memory: "8Gi"
    cpu: "4000m"

replicas: 16
```

#### Database (PostgreSQL)

**Small Deployment**:
```yaml
resources:
  requests:
    memory: "2Gi"
    cpu: "500m"
  limits:
    memory: "4Gi"
    cpu: "1000m"

# postgresql.conf
shared_buffers = 1GB
effective_cache_size = 3GB
max_connections = 100
```

**Medium Deployment**:
```yaml
resources:
  requests:
    memory: "4Gi"
    cpu: "1000m"
  limits:
    memory: "8Gi"
    cpu: "2000m"

# postgresql.conf
shared_buffers = 2GB
effective_cache_size = 6GB
max_connections = 200
```

**Large Deployment**:
```yaml
resources:
  requests:
    memory: "8Gi"
    cpu: "2000m"
  limits:
    memory: "16Gi"
    cpu: "4000m"

# postgresql.conf
shared_buffers = 4GB
effective_cache_size = 12GB
max_connections = 300
work_mem = 32MB
maintenance_work_mem = 1GB
```

#### Redis

**Small Deployment**:
```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "500m"

command:
  - redis-server
  - --maxmemory 512mb
  - --maxmemory-policy allkeys-lru
```

**Medium Deployment**:
```yaml
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "1000m"

command:
  - redis-server
  - --maxmemory 1gb
  - --maxmemory-policy allkeys-lru
  - --io-threads 2
```

**Large Deployment**:
```yaml
resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "2000m"

command:
  - redis-server
  - --maxmemory 2gb
  - --maxmemory-policy allkeys-lru
  - --io-threads 4
  - --tcp-backlog 511
```

### Horizontal Pod Autoscaling (HPA)

**Configure HPA for automatic scaling**:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: sark-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sark
  minReplicas: 4
  maxReplicas: 20
  metrics:
  # CPU-based scaling
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  # Memory-based scaling
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  # Custom metric: Request rate
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # Wait 5 min before scaling down
      policies:
      - type: Percent
        value: 50  # Scale down max 50% at a time
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0  # Scale up immediately
      policies:
      - type: Percent
        value: 100  # Double capacity if needed
        periodSeconds: 60
      - type: Pods
        value: 4  # Or add 4 pods at a time
        periodSeconds: 60
      selectPolicy: Max  # Use whichever scales faster
```

**Apply HPA**:
```bash
kubectl apply -f k8s/hpa.yaml
kubectl get hpa sark -n production --watch
```

### Pod Disruption Budget (PDB)

**Ensure availability during updates and maintenance**:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: sark-pdb
  namespace: production
spec:
  minAvailable: 2  # Always keep 2 pods running
  selector:
    matchLabels:
      app: sark
```

**Or use percentage**:
```yaml
spec:
  minAvailable: 50%  # Keep 50% of pods running
```

### Database Connection Pooling

**Application-level pooling (SQLAlchemy)**:

```python
# In application configuration
DATABASE_POOL_SIZE=20          # Normal pool size per pod
DATABASE_MAX_OVERFLOW=10       # Extra connections during spikes
DATABASE_POOL_TIMEOUT=30       # Wait 30s for connection
DATABASE_POOL_RECYCLE=3600     # Recycle connections after 1 hour

# Total connections = (pods × pool_size) + (pods × max_overflow)
# Example: 4 pods × (20 + 10) = 120 connections
# PostgreSQL max_connections should be 200+ (with headroom)
```

**PgBouncer (optional for > 10 pods)**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pgbouncer
spec:
  replicas: 2
  selector:
    matchLabels:
      app: pgbouncer
  template:
    spec:
      containers:
      - name: pgbouncer
        image: pgbouncer/pgbouncer:latest
        ports:
        - containerPort: 6432
        volumeMounts:
        - name: config
          mountPath: /etc/pgbouncer
        env:
        - name: DATABASES_HOST
          value: postgres
        - name: DATABASES_PORT
          value: "5432"
        - name: DATABASES_USER
          valueFrom:
            secretKeyRef:
              name: postgres-credentials
              key: username
        - name: DATABASES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-credentials
              key: password
      volumes:
      - name: config
        configMap:
          name: pgbouncer-config
```

**pgbouncer.ini**:
```ini
[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
reserve_pool_size = 5
max_db_connections = 100
```

### Valkey Connection Pooling

**Application configuration**:

```python
VALKEY_POOL_SIZE=20             # Connections per pod
VALKEY_SOCKET_TIMEOUT=5         # 5 second timeout
VALKEY_SOCKET_CONNECT_TIMEOUT=2 # 2 second connect timeout
VALKEY_HEALTH_CHECK_INTERVAL=30 # Health check every 30s

# Total connections = pods × pool_size
# Example: 4 pods × 20 = 80 connections
# Valkey maxclients: 10000 (default, plenty of headroom)
```

### Database Optimization Checklist

See [DATABASE_OPTIMIZATION.md](./DATABASE_OPTIMIZATION.md) for complete guide.

**Quick Checklist**:
- [ ] Create indexes on frequently queried columns (username, email, created_at)
- [ ] Enable pg_stat_statements for query analysis
- [ ] Configure appropriate shared_buffers (25% of RAM)
- [ ] Set work_mem for sort/hash operations (16MB recommended)
- [ ] Enable autovacuum with appropriate thresholds
- [ ] Configure connection pooling (20-30 per pod)
- [ ] Set query timeouts (30 seconds recommended)
- [ ] Monitor slow queries (> 1 second)
- [ ] Enable SSL/TLS for database connections

**Example PostgreSQL configuration**:
```sql
-- Enable pg_stat_statements
CREATE EXTENSION pg_stat_statements;

-- Create critical indexes
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_servers_owner ON servers(owner_id);
CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_expires ON sessions(expires_at) WHERE expires_at > NOW();

-- Set statement timeout (30 seconds)
ALTER DATABASE sark SET statement_timeout = '30s';
```

### Valkey Optimization Checklist

See [VALKEY_OPTIMIZATION.md](./VALKEY_OPTIMIZATION.md) for complete guide.

**Quick Checklist**:
- [ ] Set maxmemory limit (512MB-2GB recommended)
- [ ] Configure eviction policy (allkeys-lru for cache)
- [ ] Disable persistence for pure cache (save "")
- [ ] Configure connection pooling (20 per pod)
- [ ] Enable I/O threading for high concurrency (io-threads 4)
- [ ] Set appropriate TTLs for cached data (5 min - 1 hour)
- [ ] Monitor memory usage and eviction rate
- [ ] Configure Valkey Sentinel for high availability
- [ ] Use password authentication (requirepass)

**Example Valkey configuration**:
```conf
maxmemory 1gb
maxmemory-policy allkeys-lru
save ""
appendonly no
requirepass your-strong-password
io-threads 4
tcp-backlog 511
```

### Security Hardening Checklist

See [SECURITY_HARDENING.md](./SECURITY_HARDENING.md) for complete guide.

**Pre-Production Checklist**:
- [ ] All secrets rotated and stored in Vault/K8s Secrets
- [ ] TLS 1.3 enforced on all endpoints
- [ ] Security headers configured (HSTS, CSP, X-Frame-Options)
- [ ] Rate limiting enabled for all endpoints
- [ ] Input validation on all API endpoints
- [ ] SQL injection prevention verified
- [ ] Password complexity enforced (12+ chars)
- [ ] MFA enabled for admin accounts
- [ ] Firewall rules configured
- [ ] Container security: non-root user, read-only filesystem
- [ ] Kubernetes RBAC configured (least privilege)
- [ ] Network policies configured
- [ ] Audit logging enabled and forwarded to SIEM
- [ ] Security scanning passed (OWASP ZAP, Trivy)
- [ ] Penetration testing completed

### Monitoring and Observability

**Install Prometheus and Grafana**:

```bash
# Add Prometheus community Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus + Grafana stack
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set prometheus.prometheusSpec.retention=30d \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi \
  --set grafana.adminPassword='your-admin-password'
```

**Configure ServiceMonitor for SARK**:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: sark-metrics
  namespace: production
spec:
  selector:
    matchLabels:
      app: sark
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
```

**Key Metrics to Monitor**:

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| API Response Time (p95) | < 100ms | > 200ms |
| API Response Time (p99) | < 200ms | > 500ms |
| Error Rate | < 0.1% | > 1% |
| Request Rate | Baseline | 10× baseline |
| CPU Utilization | 50-70% | > 85% |
| Memory Utilization | 60-80% | > 90% |
| Database Connections | < 80% max | > 90% max |
| Valkey Memory Usage | < 70% | > 90% |
| Cache Hit Ratio | > 90% | < 80% |
| Pod Availability | 100% | < 90% |

**Example Prometheus Alerts**:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: sark-alerts
  namespace: production
spec:
  groups:
  - name: sark
    interval: 30s
    rules:
    # High error rate
    - alert: HighErrorRate
      expr: |
        sum(rate(http_requests_total{status=~"5.*"}[5m])) /
        sum(rate(http_requests_total[5m])) > 0.01
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "High error rate detected"
        description: "Error rate is {{ $value | humanizePercentage }}"

    # High latency
    - alert: HighLatency
      expr: |
        histogram_quantile(0.95,
          rate(http_request_duration_seconds_bucket[5m])
        ) > 0.2
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High API latency"
        description: "p95 latency is {{ $value }}s"

    # Low cache hit ratio
    - alert: LowCacheHitRatio
      expr: |
        sum(rate(redis_keyspace_hits_total[5m])) /
        (sum(rate(redis_keyspace_hits_total[5m])) +
         sum(rate(redis_keyspace_misses_total[5m]))) < 0.8
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "Low cache hit ratio"
        description: "Cache hit ratio is {{ $value | humanizePercentage }}"

    # Database connection pool exhaustion
    - alert: DatabaseConnectionPoolHigh
      expr: |
        pg_stat_activity_count /
        pg_settings_max_connections > 0.9
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "Database connection pool nearly exhausted"
        description: "{{ $value | humanizePercentage }} of connections in use"
```

**Grafana Dashboards**:

Import these dashboard IDs in Grafana:
- **Kubernetes Cluster Monitoring**: Dashboard ID 7249
- **PostgreSQL Database**: Dashboard ID 9628
- **Valkey Dashboard**: Dashboard ID 11835
- **NGINX Ingress Controller**: Dashboard ID 9614

### Log Aggregation

**Deploy Loki for log aggregation**:

```bash
helm install loki prometheus-community/loki-stack \
  --namespace monitoring \
  --set loki.persistence.enabled=true \
  --set loki.persistence.size=100Gi \
  --set promtail.enabled=true
```

**Configure structured logging in SARK**:

```python
import logging
from pythonjsonlogger import jsonlogger

logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    '%(timestamp)s %(level)s %(name)s %(message)s'
)
logHandler.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)
```

### Performance Testing

**Before production deployment**:

```bash
# Install Locust
pip install locust

# Run load test
locust -f tests/performance/locustfile.py \
  --host https://sark.yourdomain.com \
  --users 100 \
  --spawn-rate 10 \
  --run-time 10m \
  --html reports/load-test.html

# Verify targets:
# - p95 latency < 100ms
# - p99 latency < 200ms
# - Error rate < 0.1%
# - Throughput > 1000 req/s
```

See [PERFORMANCE_TESTING.md](./PERFORMANCE_TESTING.md) for complete testing guide.

---

## Rollback Procedures

### Using Helm

```bash
# View release history
helm history sark -n production

# Rollback to previous version
helm rollback sark -n production

# Rollback to specific revision
helm rollback sark 3 -n production
```

### Using kubectl

```bash
# View deployment history
kubectl rollout history deployment/sark

# Rollback to previous version
kubectl rollout undo deployment/sark

# Rollback to specific revision
kubectl rollout undo deployment/sark --to-revision=2
```

## Troubleshooting

### Common Issues

#### Pods Not Starting

```bash
# Check pod status
kubectl get pods -l app=sark

# View pod events
kubectl describe pod <pod-name>

# Check logs
kubectl logs <pod-name>
kubectl logs <pod-name> --previous  # Previous container logs
```

#### Image Pull Errors

```bash
# Verify image exists in registry
docker pull your-registry.com/sark:0.1.0

# Check imagePullSecrets
kubectl get secrets
kubectl describe secret registry-credentials
```

#### Health Check Failures

```bash
# Test health endpoint directly
kubectl exec -it <pod-name> -- curl http://localhost:8000/health
kubectl exec -it <pod-name> -- curl http://localhost:8000/ready
kubectl exec -it <pod-name> -- curl http://localhost:8000/live
```

#### Ingress Not Working

```bash
# Check ingress
kubectl describe ingress sark

# Verify ingress controller
kubectl get pods -n ingress-nginx

# Check service
kubectl get svc sark
kubectl describe svc sark
```

### Getting Support

1. Check application logs: `kubectl logs -l app=sark --tail=100`
2. Check pod events: `kubectl describe pod <pod-name>`
3. Check metrics: Access `/metrics` endpoint
4. Review monitoring dashboards
5. Check health endpoints: `/health`, `/ready`, `/live`

## Best Practices

1. **Always use specific image tags** - Never use `:latest` in production
2. **Set resource limits** - Prevent resource exhaustion
3. **Enable autoscaling** - Handle traffic spikes
4. **Use health checks** - Enable Kubernetes self-healing
5. **Enable monitoring** - Use Prometheus and Grafana
6. **Use secrets management** - Never hardcode secrets
7. **Test in staging first** - Validate changes before production
8. **Enable PodDisruptionBudget** - Maintain availability during updates
9. **Use blue-green or canary deployments** - Minimize risk
10. **Document everything** - Keep runbooks updated
