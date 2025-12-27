# SARK - Kubernetes Deployment Guide

## Overview

This guide covers deploying SARK (both frontend and backend) on Kubernetes using either raw manifests with Kustomize or Helm charts.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture](#architecture)
- [Deployment Methods](#deployment-methods)
  - [Using Kustomize](#using-kustomize)
  - [Using Helm](#using-helm)
- [Configuration](#configuration)
- [Scaling](#scaling)
- [Monitoring](#monitoring)
- [Security](#security)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools

- **kubectl**: Kubernetes CLI (v1.25+)
- **kustomize**: Configuration management (v4.5+) or **helm**: Package manager (v3.10+)
- **cert-manager**: SSL/TLS certificate management (optional)
- **nginx-ingress-controller**: Ingress controller

### Cluster Requirements

- **Kubernetes version**: 1.25+
- **Node resources**:
  - Minimum: 2 nodes, 4 vCPU, 8GB RAM each
  - Recommended: 3+ nodes, 8 vCPU, 16GB RAM each
- **Storage**: Persistent volumes for PostgreSQL, Redis (if using managed services)
- **LoadBalancer**: For ingress controller

### Dependencies

Install required cluster components:

```bash
# Install cert-manager (for SSL/TLS)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Install nginx-ingress-controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.0/deploy/static/provider/cloud/deploy.yaml

# Verify installations
kubectl get pods -n cert-manager
kubectl get pods -n ingress-nginx
```

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Ingress (nginx)                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ sark.example.com                                     │   │
│  │  /         → Frontend (Nginx serving React SPA)      │   │
│  │  /api/*    → Backend (FastAPI Python application)    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          ↓         ↓
          ┌───────────────┘         └───────────────┐
          │                                         │
┌─────────────────────┐                  ┌─────────────────────┐
│  Frontend Service   │                  │   Backend Service   │
│   (ClusterIP:80)    │                  │  (ClusterIP:8000)   │
└─────────────────────┘                  └─────────────────────┘
          │                                         │
    ┌─────┴─────┐                          ┌───────┴────────┐
    │           │                          │                │
┌───────┐  ┌───────┐                  ┌────────┐      ┌────────┐
│Frontend│  │Frontend│                 │ Backend│      │ Backend│
│ Pod 1  │  │ Pod 2  │                 │  Pod 1 │      │  Pod 2 │
└───────┘  └───────┘                  └────────┘      └────────┘
                                           │                │
                         ┌─────────────────┴────────────────┴─────┐
                         │                                         │
                    ┌────────────┐                          ┌──────────┐
                    │ PostgreSQL │                          │  Redis   │
                    │  Service   │                          │ Service  │
                    └────────────┘                          └──────────┘
```

### Namespaces

- **sark**: Main application namespace
- **cert-manager**: Certificate management (if using Let's Encrypt)
- **ingress-nginx**: Ingress controller

## Deployment Methods

### Using Kustomize

Kustomize provides declarative configuration management with overlays for different environments.

#### Structure

```
k8s/
├── base/                           # Base configurations
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── deployment.yaml             # Backend deployment
│   ├── service.yaml                # Backend service
│   ├── serviceaccount.yaml
│   ├── hpa.yaml
│   ├── ingress.yaml
│   ├── frontend-deployment.yaml    # Frontend deployment
│   ├── frontend-service.yaml       # Frontend service
│   ├── frontend-serviceaccount.yaml
│   ├── frontend-hpa.yaml
│   ├── frontend-ingress.yaml
│   └── kustomization.yaml
└── overlays/
    ├── development/
    ├── staging/
    └── production/
        ├── kustomization.yaml
        └── deployment-patch.yaml
```

#### Deploy with Kustomize

**1. Review and customize base configuration:**

```bash
# View the generated manifests
kubectl kustomize k8s/base

# Edit configuration as needed
vim k8s/base/configmap.yaml
vim k8s/base/frontend-deployment.yaml
```

**2. Create namespace and secrets:**

```bash
# Create namespace
kubectl create namespace sark

# Create secrets (replace with actual values)
kubectl create secret generic sark-secrets \
  --namespace=sark \
  --from-literal=POSTGRES_PASSWORD=<your-password> \
  --from-literal=VALKEY_PASSWORD=<your-password> \
  --from-literal=SECRET_KEY=<your-secret-key>
```

**3. Deploy using Kustomize:**

```bash
# Deploy to production
kubectl apply -k k8s/overlays/production

# Or deploy base configuration directly
kubectl apply -k k8s/base
```

**4. Verify deployment:**

```bash
# Check all resources
kubectl get all -n sark

# Check pods
kubectl get pods -n sark

# Check services
kubectl get svc -n sark

# Check ingress
kubectl get ingress -n sark
```

**5. View logs:**

```bash
# Frontend logs
kubectl logs -n sark -l app.kubernetes.io/component=frontend --tail=100 -f

# Backend logs
kubectl logs -n sark -l app.kubernetes.io/component=api --tail=100 -f
```

### Using Helm

Helm provides package management with templating and release management.

#### Install Helm Chart

**1. Review values:**

```bash
# View default values
cat helm/sark/values.yaml

# Create custom values file
cat > values-production.yaml <<EOF
# Backend configuration
replicaCount: 3
image:
  tag: "v1.0.0"

config:
  environment: production
  logLevel: INFO

# Frontend configuration
frontend:
  enabled: true
  replicaCount: 2
  image:
    tag: "v1.0.0"

# Ingress configuration
ingress:
  enabled: true
  hosts:
    - host: sark.example.com
      paths:
        - path: /api
          pathType: Prefix
  tls:
    - secretName: sark-tls
      hosts:
        - sark.example.com

frontend:
  ingress:
    enabled: true
    hosts:
      - host: sark.example.com
        paths:
          - path: /
            pathType: Prefix
    tls:
      - secretName: sark-frontend-tls
        hosts:
          - sark.example.com
EOF
```

**2. Install the chart:**

```bash
# Add local chart repository (if needed)
helm repo add sark ./helm/sark
helm repo update

# Install with custom values
helm install sark ./helm/sark \
  --namespace sark \
  --create-namespace \
  --values values-production.yaml

# Or install with inline values
helm install sark ./helm/sark \
  --namespace sark \
  --create-namespace \
  --set replicaCount=3 \
  --set image.tag=v1.0.0 \
  --set frontend.enabled=true
```

**3. Verify installation:**

```bash
# Check release status
helm status sark -n sark

# List releases
helm list -n sark

# View all resources
kubectl get all -n sark
```

**4. Upgrade the release:**

```bash
# Update values and upgrade
helm upgrade sark ./helm/sark \
  --namespace sark \
  --values values-production.yaml \
  --set image.tag=v1.1.0

# Rollback if needed
helm rollback sark 1 -n sark
```

**5. Uninstall:**

```bash
# Uninstall release
helm uninstall sark -n sark

# Clean up namespace
kubectl delete namespace sark
```

## Configuration

### Environment Variables

Configure via ConfigMap and Secrets:

**ConfigMap (non-sensitive):**

```yaml
# k8s/base/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: sark-config
  namespace: sark
data:
  # Backend config
  APP_NAME: "SARK"
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  API_PREFIX: "/api/v1"

  # Frontend build args (set during build)
  VITE_APP_NAME: "SARK"
  VITE_APP_VERSION: "1.0.0"
```

**Secret (sensitive):**

```bash
kubectl create secret generic sark-secrets \
  --namespace=sark \
  --from-literal=POSTGRES_PASSWORD=<password> \
  --from-literal=VALKEY_PASSWORD=<password> \
  --from-literal=SECRET_KEY=<secret-key> \
  --from-literal=JWT_SECRET_KEY=<jwt-secret>
```

### Ingress Configuration

**Single Ingress (Recommended):**

Use a single ingress with path-based routing:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: sark
  namespace: sark
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
          # Backend API
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: sark-api
                port:
                  number: 8000

          # Frontend (default)
          - path: /
            pathType: Prefix
            backend:
              service:
                name: sark-frontend
                port:
                  number: 80
```

**SSL/TLS with Let's Encrypt:**

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: sark-tls
  namespace: sark
spec:
  secretName: sark-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
    - sark.example.com
    - www.sark.example.com
```

## Scaling

### Horizontal Pod Autoscaling (HPA)

**Frontend HPA:**

```yaml
# k8s/base/frontend-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: sark-frontend
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sark-frontend
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

**Backend HPA:**

```yaml
# k8s/base/hpa.yaml (already exists)
```

**Manual Scaling:**

```bash
# Scale frontend
kubectl scale deployment sark-frontend -n sark --replicas=5

# Scale backend
kubectl scale deployment sark-api -n sark --replicas=5

# Verify
kubectl get hpa -n sark
```

### Vertical Pod Autoscaling (VPA)

Install VPA (optional):

```bash
# Install VPA
git clone https://github.com/kubernetes/autoscaler.git
cd autoscaler/vertical-pod-autoscaler
./hack/vpa-up.sh
```

Create VPA for frontend:

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: sark-frontend-vpa
  namespace: sark
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sark-frontend
  updatePolicy:
    updateMode: "Auto"
```

## Monitoring

### Health Checks

SARK provides multiple health check endpoints:

**Frontend:**
- `/health` - Basic health check
- `/ready` - Readiness probe
- `/live` - Liveness probe

**Backend:**
- `/health` - Basic health check
- `/health/ready` - Readiness probe
- `/health/live` - Liveness probe

**Test health checks:**

```bash
# Port-forward to frontend
kubectl port-forward -n sark svc/sark-frontend 8080:80

# Test endpoints
curl http://localhost:8080/health
curl http://localhost:8080/ready
curl http://localhost:8080/live
```

### Prometheus Metrics

Configure Prometheus to scrape metrics:

```yaml
# prometheus-config.yaml
scrape_configs:
  - job_name: 'sark-backend'
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
            - sark
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        target_label: __address__
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2

  - job_name: 'sark-frontend'
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
            - sark
```

### Logging

Aggregate logs using FluentBit or Fluentd:

```bash
# View frontend logs
kubectl logs -n sark -l app.kubernetes.io/component=frontend --tail=100 -f

# View backend logs
kubectl logs -n sark -l app.kubernetes.io/component=api --tail=100 -f

# View all logs
kubectl logs -n sark --all-containers=true --tail=100 -f
```

## Security

### Pod Security

**Security Context (already configured):**

```yaml
# Frontend
securityContext:
  runAsNonRoot: true
  runAsUser: 101  # nginx user
  allowPrivilegeEscalation: false
  capabilities:
    drop: ["ALL"]
    add: ["NET_BIND_SERVICE"]
  readOnlyRootFilesystem: true

# Backend
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  allowPrivilegeEscalation: false
  capabilities:
    drop: ["ALL"]
  readOnlyRootFilesystem: true
```

### Network Policies

Create network policies to restrict traffic:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sark-frontend-netpol
  namespace: sark
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/component: frontend
  policyTypes:
    - Ingress
    - Egress
  ingress:
    # Allow from ingress controller
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
  egress:
    # Allow to backend API
    - to:
        - podSelector:
            matchLabels:
              app.kubernetes.io/component: api
      ports:
        - protocol: TCP
          port: 8000
    # Allow DNS
    - to:
        - namespaceSelector: {}
      ports:
        - protocol: UDP
          port: 53
```

### Secrets Management

Use external secrets management:

```bash
# Using sealed-secrets
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# Seal a secret
kubectl create secret generic sark-secrets \
  --dry-run=client \
  --from-literal=POSTGRES_PASSWORD=secret \
  -o yaml | \
  kubeseal -o yaml > sealed-secret.yaml

# Apply sealed secret
kubectl apply -f sealed-secret.yaml
```

## Troubleshooting

### Common Issues

**1. Pods not starting:**

```bash
# Check pod status
kubectl get pods -n sark

# Describe pod
kubectl describe pod <pod-name> -n sark

# View logs
kubectl logs <pod-name> -n sark

# Check events
kubectl get events -n sark --sort-by='.lastTimestamp'
```

**2. Ingress not working:**

```bash
# Check ingress
kubectl get ingress -n sark
kubectl describe ingress sark-frontend -n sark

# Check ingress controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller

# Test from inside cluster
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- \
  curl http://sark-frontend.sark.svc.cluster.local/health
```

**3. HPA not scaling:**

```bash
# Check HPA status
kubectl get hpa -n sark
kubectl describe hpa sark-frontend -n sark

# Check metrics server
kubectl top nodes
kubectl top pods -n sark

# Install metrics server if missing
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

**4. Frontend 404 errors:**

```bash
# Check nginx config
kubectl exec -n sark <frontend-pod> -- cat /etc/nginx/conf.d/default.conf

# Test nginx config
kubectl exec -n sark <frontend-pod> -- nginx -t

# Check static files
kubectl exec -n sark <frontend-pod> -- ls -la /usr/share/nginx/html/
```

**5. API connection errors:**

```bash
# Test backend connectivity from frontend pod
kubectl exec -n sark <frontend-pod> -- curl http://sark-api:8000/health

# Check backend service
kubectl get svc sark-api -n sark
kubectl get endpoints sark-api -n sark

# Check network policies
kubectl get networkpolicies -n sark
```

### Debug Commands

```bash
# Shell into frontend pod
kubectl exec -it -n sark <frontend-pod> -- sh

# Shell into backend pod
kubectl exec -it -n sark <backend-pod> -- bash

# Port forward for local access
kubectl port-forward -n sark svc/sark-frontend 3000:80
kubectl port-forward -n sark svc/sark-api 8000:8000

# Copy files from pod
kubectl cp sark/<pod-name>:/var/log/nginx/error.log ./error.log

# Run network diagnostic
kubectl run -it --rm debug --image=nicolaka/netshoot --restart=Never -- bash
```

## Maintenance

### Updates and Rollouts

**Rolling Update (Kustomize):**

```bash
# Update image tag in kustomization.yaml
cd k8s/overlays/production
kustomize edit set image sark-frontend=sark-frontend:v1.1.0

# Apply update
kubectl apply -k .

# Watch rollout
kubectl rollout status deployment/sark-frontend -n sark
```

**Rolling Update (Helm):**

```bash
# Upgrade with new image tag
helm upgrade sark ./helm/sark \
  --namespace sark \
  --set frontend.image.tag=v1.1.0 \
  --set image.tag=v1.1.0

# Monitor rollout
kubectl rollout status deployment/sark-frontend -n sark
```

**Rollback:**

```bash
# Rollback deployment (Kustomize)
kubectl rollout undo deployment/sark-frontend -n sark

# Rollback release (Helm)
helm rollback sark -n sark
```

### Backup and Restore

**Export current configuration:**

```bash
# Export all resources
kubectl get all -n sark -o yaml > sark-backup.yaml

# Export specific resources
kubectl get deployment sark-frontend -n sark -o yaml > frontend-deployment.yaml
```

**Database Backup (if using PostgreSQL):**

```bash
# Create backup job
kubectl run postgres-backup -n sark \
  --image=postgres:15 \
  --restart=Never \
  --rm -it -- \
  pg_dump -h sark-postgres -U sark -d sark > backup.sql
```

## Best Practices

1. **Use namespaces** for isolation
2. **Set resource limits** on all pods
3. **Enable HPA** for automatic scaling
4. **Use readOnly root filesystem** where possible
5. **Run as non-root user** (already configured)
6. **Use network policies** to restrict traffic
7. **Enable monitoring** and logging
8. **Regular backups** of configuration and data
9. **Test in staging** before production
10. **Use GitOps** (ArgoCD, Flux) for continuous deployment

## Related Documentation

- [Docker Deployment](../DOCKER_PROFILES.md)
- [Frontend Production Guide](../../frontend/PRODUCTION.md)
- [Frontend Development Guide](../../frontend/DEVELOPMENT.md)
- [UI Docker Integration Plan](../UI_DOCKER_INTEGRATION_PLAN.md)

## Support

For issues or questions:

1. Check pod logs: `kubectl logs -n sark <pod-name>`
2. Check events: `kubectl get events -n sark`
3. Review this troubleshooting section
4. File an issue on GitHub
