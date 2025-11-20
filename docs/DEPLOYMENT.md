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

## Container Image Build

### Build the Docker Image

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

### Environment Variables

Configure via ConfigMap (`k8s/configmap.yaml`) or Helm values:

- `APP_VERSION`: Application version
- `ENVIRONMENT`: Environment (development, staging, production)
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `JSON_LOGS`: Enable JSON logging (true for cloud)
- `ENABLE_METRICS`: Enable Prometheus metrics

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
