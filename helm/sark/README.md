# SARK Helm Chart

This Helm chart deploys the SARK application to Kubernetes.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- Ingress controller (NGINX recommended)
- cert-manager (optional, for TLS certificates)

## Installation

### Install with default values

```bash
helm install sark ./helm/sark
```

### Install with custom values

```bash
helm install sark ./helm/sark -f values-prod.yaml
```

### Install in a specific namespace

```bash
helm install sark ./helm/sark --namespace production --create-namespace
```

## Upgrading

```bash
helm upgrade sark ./helm/sark
```

## Uninstalling

```bash
helm uninstall sark
```

## Configuration

The following table lists the configurable parameters and their default values.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `3` |
| `image.repository` | Container image repository | `sark` |
| `image.tag` | Container image tag | `latest` |
| `image.pullPolicy` | Image pull policy | `Always` |
| `service.type` | Kubernetes service type | `ClusterIP` |
| `service.port` | Service port | `80` |
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.className` | Ingress class name | `nginx` |
| `ingress.hosts[0].host` | Hostname | `sark.example.com` |
| `resources.limits.cpu` | CPU limit | `500m` |
| `resources.limits.memory` | Memory limit | `512Mi` |
| `resources.requests.cpu` | CPU request | `250m` |
| `resources.requests.memory` | Memory request | `256Mi` |
| `autoscaling.enabled` | Enable HPA | `true` |
| `autoscaling.minReplicas` | Minimum replicas | `3` |
| `autoscaling.maxReplicas` | Maximum replicas | `10` |
| `config.environment` | Application environment | `production` |
| `config.logLevel` | Log level | `INFO` |

## Environment-Specific Deployments

### Development

```bash
helm install sark ./helm/sark -f values-dev.yaml
```

### Staging

```bash
helm install sark ./helm/sark -f values-staging.yaml
```

### Production

```bash
helm install sark ./helm/sark -f values-prod.yaml
```

## Health Checks

The application exposes the following health check endpoints:

- `/health` - Basic health check
- `/ready` - Readiness probe
- `/live` - Liveness probe
- `/startup` - Startup probe

## Metrics

Prometheus metrics are exposed at `/metrics` and automatically scraped when Prometheus service discovery is configured.

## TLS/SSL

To enable TLS:

1. Install cert-manager
2. Uncomment the cert-manager annotation in `values.yaml`
3. Create a ClusterIssuer for Let's Encrypt

Example ClusterIssuer:

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
