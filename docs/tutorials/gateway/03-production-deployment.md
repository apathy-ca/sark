# Production Deployment for Gateway Integration

**Level:** Advanced
**Time:** 2-3 hours
**Prerequisites:**
- [Tutorial 1: Quick Start Guide](./01-quickstart-guide.md)
- [Tutorial 2: Building a Gateway Server](./02-building-gateway-server.md)
- Kubernetes experience (basic)
- Production infrastructure access

---

## Overview

In this tutorial, you'll deploy a **production-ready Gateway + SARK** stack with enterprise-grade reliability, security, and observability. You'll learn:

- 🏗️ **Architecture**: Design a highly available, fault-tolerant deployment
- ⚖️ **Load Balancing**: Configure NGINX/HAProxy for Gateway and SARK
- ☸️ **Kubernetes**: Deploy to Kubernetes with auto-scaling
- 📊 **Monitoring**: Set up Prometheus metrics and Grafana dashboards
- 🔔 **Alerting**: Configure critical alerts for production issues
- 🔒 **Security**: Harden the deployment with TLS, secrets management, and network policies
- 🚀 **Zero-Downtime**: Perform rolling updates without service interruption

By the end, you'll have a production deployment that:
- Handles 10,000+ requests per second
- Auto-scales based on load
- Provides 99.9% uptime
- Monitors all critical metrics
- Alerts on-call engineers for issues
- Passes security audits

---

## Architecture Overview

### High-Level Production Architecture

```
                                    ┌─────────────────────┐
                                    │   External Users    │
                                    │   AI Agents         │
                                    └──────────┬──────────┘
                                               │
                                               ▼
                                    ┌─────────────────────┐
                                    │   Load Balancer     │
                                    │   (AWS ALB/NLB)     │
                                    │   TLS Termination   │
                                    └──────────┬──────────┘
                                               │
                       ┌───────────────────────┼───────────────────────┐
                       │                       │                       │
                       ▼                       ▼                       ▼
            ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
            │  Gateway Pod 1   │   │  Gateway Pod 2   │   │  Gateway Pod N   │
            │  (Auto-scaling)  │   │  (Auto-scaling)  │   │  (Auto-scaling)  │
            └────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘
                     │                      │                      │
                     │                      ▼                      │
                     │           ┌──────────────────┐             │
                     └──────────►│  SARK Service    │◄────────────┘
                                 │  (Internal LB)   │
                                 └────────┬─────────┘
                                          │
                     ┌────────────────────┼────────────────────┐
                     │                    │                    │
                     ▼                    ▼                    ▼
          ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
          │  SARK Pod 1      │ │  SARK Pod 2      │ │  SARK Pod N      │
          │  (Stateless)     │ │  (Stateless)     │ │  (Stateless)     │
          └────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
                   │                    │                    │
                   └────────────────────┼────────────────────┘
                                        │
                        ┌───────────────┼───────────────┐
                        │               │               │
                        ▼               ▼               ▼
             ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
             │  OPA Pod 1   │ │  Redis       │ │  PostgreSQL  │
             │  (Sidecar)   │ │  Cluster     │ │  (RDS/HA)    │
             └──────────────┘ └──────────────┘ └──────────────┘
                                        │               │
                                        ▼               ▼
                             ┌──────────────┐ ┌──────────────┐
                             │  Prometheus  │ │  TimescaleDB │
                             │  (Metrics)   │ │  (Archive)   │
                             └──────────────┘ └──────────────┘
```

### Key Components

| Component | Purpose | Replicas | Scaling |
|-----------|---------|----------|---------|
| **Gateway Pods** | Route MCP requests, enforce authorization | 3+ | Horizontal (HPA) |
| **SARK Pods** | Authorization API, policy evaluation | 3+ | Horizontal (HPA) |
| **OPA** | Policy engine (sidecar) | 1 per SARK pod | Scales with SARK |
| **PostgreSQL** | Audit logs, metadata | Primary + 2 replicas | Vertical + read replicas |
| **Redis Cluster** | Policy cache, session store | 6 nodes (3 primary + 3 replica) | Horizontal |
| **Prometheus** | Metrics collection | 1 (HA pair for prod) | Vertical |
| **Grafana** | Metrics visualization | 1+ | Horizontal |

---

## Part 1: Infrastructure Preparation

### Step 1.1: Create Kubernetes Namespace

```bash
# Create production namespace
kubectl create namespace mcp-production

# Label namespace for monitoring
kubectl label namespace mcp-production \
  monitoring=enabled \
  team=platform

# Set context to new namespace
kubectl config set-context --current --namespace=mcp-production
```

### Step 1.2: Create Secrets

```bash
# Generate strong secrets
export JWT_SECRET=$(openssl rand -base64 32)
export POSTGRES_PASSWORD=$(openssl rand -base64 32)
export VALKEY_PASSWORD=$(openssl rand -base64 32)
export GATEWAY_API_KEY=$(openssl rand -hex 32)

# Create Kubernetes secrets
kubectl create secret generic sark-secrets \
  --from-literal=jwt-secret-key="$JWT_SECRET" \
  --from-literal=postgres-password="$POSTGRES_PASSWORD" \
  --from-literal=redis-password="$VALKEY_PASSWORD" \
  --from-literal=gateway-api-key="$GATEWAY_API_KEY" \
  -n mcp-production

# Create TLS certificate secret (use cert-manager or AWS ACM in production)
kubectl create secret tls gateway-tls \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key \
  -n mcp-production
```

### Step 1.3: Create ConfigMaps

Create `k8s/production/configmap.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: sark-config
  namespace: mcp-production
data:
  # SARK Configuration
  SARK_ENV: "production"
  LOG_LEVEL: "INFO"
  LOG_FORMAT: "json"

  # Gateway Integration
  GATEWAY_ENABLED: "true"
  GATEWAY_TIMEOUT_SECONDS: "10.0"

  # Database
  POSTGRES_HOST: "postgres-primary.mcp-production.svc.cluster.local"
  POSTGRES_PORT: "5432"
  POSTGRES_DB: "sark_production"
  POSTGRES_USER: "sark"
  POSTGRES_MAX_CONNECTIONS: "100"
  POSTGRES_POOL_SIZE: "20"

  # Redis
  VALKEY_HOST: "redis-cluster.mcp-production.svc.cluster.local"
  VALKEY_PORT: "6379"
  VALKEY_MAX_CONNECTIONS: "50"
  REDIS_CLUSTER_MODE: "true"

  # OPA
  OPA_URL: "http://localhost:8181"
  OPA_TIMEOUT_SECONDS: "5.0"

  # Monitoring
  METRICS_ENABLED: "true"
  PROMETHEUS_PORT: "9090"

  # Feature Flags
  A2A_ENABLED: "false"  # Enable after testing

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: gateway-config
  namespace: mcp-production
data:
  GATEWAY_ENV: "production"
  LOG_LEVEL: "INFO"
  SARK_URL: "http://sark-service.mcp-production.svc.cluster.local:8000"
```

Apply configurations:

```bash
kubectl apply -f k8s/production/configmap.yaml
```

---

## Part 2: Database Deployment

### Step 2.1: PostgreSQL with High Availability

Create `k8s/production/postgres-statefulset.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres-primary
  namespace: mcp-production
spec:
  selector:
    app: postgres
    role: primary
  ports:
  - port: 5432
    targetPort: 5432
  clusterIP: None  # Headless service

---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: mcp-production
spec:
  serviceName: postgres-primary
  replicas: 3  # 1 primary + 2 replicas
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        ports:
        - containerPort: 5432
          name: postgres
        env:
        - name: POSTGRES_DB
          valueFrom:
            configMapKeyRef:
              name: sark-config
              key: POSTGRES_DB
        - name: POSTGRES_USER
          valueFrom:
            configMapKeyRef:
              name: sark-config
              key: POSTGRES_USER
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: sark-secrets
              key: postgres-password
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata
        volumeMounts:
        - name: postgres-data
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            cpu: 1000m
            memory: 2Gi
          limits:
            cpu: 2000m
            memory: 4Gi
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - sark
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - sark
          initialDelaySeconds: 10
          periodSeconds: 5
  volumeClaimTemplates:
  - metadata:
      name: postgres-data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: fast-ssd  # Use appropriate storage class
      resources:
        requests:
          storage: 100Gi
```

**Production Alternative:** Use managed databases (AWS RDS, Google Cloud SQL, Azure Database)

```yaml
# For managed PostgreSQL, just update ConfigMap
data:
  POSTGRES_HOST: "sark-prod.abc123.us-east-1.rds.amazonaws.com"
  POSTGRES_PORT: "5432"
  POSTGRES_SSL_MODE: "require"
```

### Step 2.2: Redis Cluster

Create `k8s/production/redis-cluster.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: redis-cluster
  namespace: mcp-production
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
  clusterIP: None

---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
  namespace: mcp-production
spec:
  serviceName: redis-cluster
  replicas: 6  # 3 primary + 3 replicas
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
        image: redis:7-alpine
        ports:
        - containerPort: 6379
          name: client
        - containerPort: 16379
          name: gossip
        command:
        - redis-server
        args:
        - --cluster-enabled
        - "yes"
        - --cluster-config-file
        - /data/nodes.conf
        - --cluster-node-timeout
        - "5000"
        - --appendonly
        - "yes"
        - --requirepass
        - $(VALKEY_PASSWORD)
        env:
        - name: VALKEY_PASSWORD
          valueFrom:
            secretKeyRef:
              name: sark-secrets
              key: redis-password
        volumeMounts:
        - name: redis-data
          mountPath: /data
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 1000m
            memory: 2Gi
  volumeClaimTemplates:
  - metadata:
      name: redis-data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: fast-ssd
      resources:
        requests:
          storage: 10Gi
```

**Production Alternative:** Use managed Redis (AWS ElastiCache, Google Memorystore)

```yaml
data:
  VALKEY_HOST: "sark-redis.abc123.cache.amazonaws.com"
  VALKEY_PORT: "6379"
  REDIS_CLUSTER_MODE: "false"
  REDIS_TLS: "true"
```

Deploy databases:

```bash
kubectl apply -f k8s/production/postgres-statefulset.yaml
kubectl apply -f k8s/production/redis-cluster.yaml

# Wait for databases to be ready
kubectl wait --for=condition=ready pod -l app=postgres --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis --timeout=300s
```

---

## Part 3: SARK Deployment

### Step 3.1: SARK with OPA Sidecar

Create `k8s/production/sark-deployment.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: sark-service
  namespace: mcp-production
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "9090"
spec:
  selector:
    app: sark
  ports:
  - name: http
    port: 8000
    targetPort: 8000
  - name: metrics
    port: 9090
    targetPort: 9090
  type: ClusterIP

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sark
  namespace: mcp-production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sark
  template:
    metadata:
      labels:
        app: sark
        version: v1.1.0
    spec:
      # Init container to run migrations
      initContainers:
      - name: migration
        image: sark:1.1.0
        command: ["python", "-m", "alembic", "upgrade", "head"]
        envFrom:
        - configMapRef:
            name: sark-config
        env:
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: sark-secrets
              key: postgres-password
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: sark-secrets
              key: jwt-secret-key

      containers:
      # SARK application
      - name: sark
        image: sark:1.1.0
        ports:
        - containerPort: 8000
          name: http
        - containerPort: 9090
          name: metrics
        envFrom:
        - configMapRef:
            name: sark-config
        env:
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: sark-secrets
              key: postgres-password
        - name: VALKEY_PASSWORD
          valueFrom:
            secretKeyRef:
              name: sark-secrets
              key: redis-password
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: sark-secrets
              key: jwt-secret-key
        - name: GATEWAY_API_KEY
          valueFrom:
            secretKeyRef:
              name: sark-secrets
              key: gateway-api-key
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 2000m
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3

      # OPA sidecar
      - name: opa
        image: openpolicyagent/opa:0.60.0
        ports:
        - containerPort: 8181
          name: http
        args:
        - "run"
        - "--server"
        - "--addr=0.0.0.0:8181"
        - "--log-level=info"
        - "--log-format=json"
        - "/policies"
        volumeMounts:
        - name: opa-policies
          mountPath: /policies
          readOnly: true
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
        livenessProbe:
          httpGet:
            path: /health
            port: 8181
          initialDelaySeconds: 10
          periodSeconds: 10

      volumes:
      - name: opa-policies
        configMap:
          name: opa-policies

      # Affinity: spread across nodes
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - sark
              topologyKey: kubernetes.io/hostname
```

### Step 3.2: OPA Policies ConfigMap

Create `k8s/production/opa-policies.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: opa-policies
  namespace: mcp-production
data:
  gateway.rego: |
    package mcp.gateway

    import future.keywords.if
    import future.keywords.in

    default allow := false

    # Admin access
    allow if {
        input.user.roles[_] == "admin"
        input.action == "gateway:tool:invoke"
    }

    # Developer access to databases
    allow if {
        input.user.roles[_] == "developer"
        input.action == "gateway:tool:invoke"
        input.server_name == "postgres-mcp"
        input.tool_name in ["execute_query", "list_tables"]
        not is_destructive_query(input.parameters.query)
    }

    # Analyst read-only access
    allow if {
        input.user.roles[_] == "analyst"
        input.action == "gateway:tool:invoke"
        input.server_name == "postgres-mcp"
        input.tool_name == "execute_query"
        is_select_query(input.parameters.query)
    }

    is_destructive_query(query) if {
        lower_query := lower(query)
        destructive_keywords := ["drop", "delete", "truncate", "alter"]
        some keyword in destructive_keywords
        contains(lower_query, keyword)
    }

    is_select_query(query) if {
        lower_query := lower(query)
        startswith(lower_query, "select")
    }

    reason := sprintf("Allowed: %s", [input.user.roles[0]]) if allow
    reason := "Denied: insufficient permissions" if not allow

    cache_ttl := 60 if allow
    cache_ttl := 0 if not allow
```

Deploy SARK:

```bash
kubectl apply -f k8s/production/opa-policies.yaml
kubectl apply -f k8s/production/sark-deployment.yaml

# Wait for SARK to be ready
kubectl wait --for=condition=available deployment/sark --timeout=300s

# Check pods
kubectl get pods -l app=sark
```

---

## Part 4: Gateway Deployment

### Step 4.1: Gateway Deployment

Create `k8s/production/gateway-deployment.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: gateway-service
  namespace: mcp-production
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "9091"
spec:
  selector:
    app: gateway
  ports:
  - name: http
    port: 8080
    targetPort: 8080
  - name: metrics
    port: 9091
    targetPort: 9091
  type: ClusterIP

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gateway
  namespace: mcp-production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: gateway
  template:
    metadata:
      labels:
        app: gateway
        version: v1.0.0
    spec:
      containers:
      - name: gateway
        image: gateway:1.0.0  # Your gateway image from Tutorial 2
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 9091
          name: metrics
        envFrom:
        - configMapRef:
            name: gateway-config
        env:
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: sark-secrets
              key: jwt-secret-key
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 20
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5

      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - gateway
              topologyKey: kubernetes.io/hostname
```

Deploy Gateway:

```bash
kubectl apply -f k8s/production/gateway-deployment.yaml

kubectl wait --for=condition=available deployment/gateway --timeout=300s
```

---

## Part 5: Auto-Scaling

### Step 5.1: Horizontal Pod Autoscaler (HPA)

Create `k8s/production/hpa.yaml`:

```yaml
apiVersion autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: sark-hpa
  namespace: mcp-production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sark
  minReplicas: 3
  maxReplicas: 20
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
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      - type: Pods
        value: 4
        periodSeconds: 15
      selectPolicy: Max

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: gateway-hpa
  namespace: mcp-production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: gateway
  minReplicas: 3
  maxReplicas: 15
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
    scaleUp:
      stabilizationWindowSeconds: 0
```

Apply HPA:

```bash
# Ensure metrics-server is installed
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Apply HPA
kubectl apply -f k8s/production/hpa.yaml

# Verify HPA
kubectl get hpa
```

---

## Part 6: Ingress and Load Balancing

### Step 6.1: NGINX Ingress Controller

Create `k8s/production/ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: gateway-ingress
  namespace: mcp-production
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    nginx.ingress.kubernetes.io/proxy-connect-timeout: "30"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "30"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "30"
spec:
  tls:
  - hosts:
    - gateway.example.com
    secretName: gateway-tls
  rules:
  - host: gateway.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: gateway-service
            port:
              number: 8080

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: sark-ingress
  namespace: mcp-production
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/whitelist-source-range: "10.0.0.0/8"  # Internal only
spec:
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
            name: sark-service
            port:
              number: 8000
```

Apply Ingress:

```bash
kubectl apply -f k8s/production/ingress.yaml

# Get external IP
kubectl get ingress -n mcp-production
```

---

## Part 7: Monitoring Setup

### Step 7.1: Prometheus Deployment

Create `k8s/production/prometheus.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: mcp-production
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s

    scrape_configs:
    - job_name: 'sark'
      kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
          - mcp-production
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: sark
      - source_labels: [__meta_kubernetes_pod_container_port_name]
        action: keep
        regex: metrics

    - job_name: 'gateway'
      kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
          - mcp-production
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: gateway

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
  namespace: mcp-production
spec:
  replicas: 1
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      labels:
        app: prometheus
    spec:
      containers:
      - name: prometheus
        image: prom/prometheus:v2.48.0
        ports:
        - containerPort: 9090
          name: http
        volumeMounts:
        - name: config
          mountPath: /etc/prometheus
        - name: data
          mountPath: /prometheus
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 4Gi
      volumes:
      - name: config
        configMap:
          name: prometheus-config
      - name: data
        emptyDir: {}

---
apiVersion: v1
kind: Service
metadata:
  name: prometheus
  namespace: mcp-production
spec:
  selector:
    app: prometheus
  ports:
  - port: 9090
    targetPort: 9090
```

### Step 7.2: Grafana Deployment

Create `k8s/production/grafana.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
  namespace: mcp-production
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      containers:
      - name: grafana
        image: grafana/grafana:10.2.0
        ports:
        - containerPort: 3000
          name: http
        env:
        - name: GF_SECURITY_ADMIN_PASSWORD
          valueFrom:
            secretKeyRef:
              name: sark-secrets
              key: grafana-password
        volumeMounts:
        - name: datasources
          mountPath: /etc/grafana/provisioning/datasources
        - name: dashboards-config
          mountPath: /etc/grafana/provisioning/dashboards
        - name: dashboards
          mountPath: /var/lib/grafana/dashboards
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 1Gi
      volumes:
      - name: datasources
        configMap:
          name: grafana-datasources
      - name: dashboards-config
        configMap:
          name: grafana-dashboards-config
      - name: dashboards
        configMap:
          name: grafana-dashboards

---
apiVersion: v1
kind: Service
metadata:
  name: grafana
  namespace: mcp-production
spec:
  selector:
    app: grafana
  ports:
  - port: 3000
    targetPort: 3000

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: mcp-production
data:
  prometheus.yaml: |
    apiVersion: 1
    datasources:
    - name: Prometheus
      type: prometheus
      access: proxy
      url: http://prometheus:9090
      isDefault: true
```

Deploy monitoring:

```bash
kubectl apply -f k8s/production/prometheus.yaml
kubectl apply -f k8s/production/grafana.yaml

# Access Grafana
kubectl port-forward svc/grafana 3000:3000 -n mcp-production
# Open http://localhost:3000 (admin / password from secret)
```

---

## Part 8: Alerting

### Step 8.1: Prometheus AlertManager

Create `k8s/production/alertmanager.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
  namespace: mcp-production
data:
  alertmanager.yml: |
    global:
      resolve_timeout: 5m
      slack_api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'

    route:
      group_by: ['alertname', 'cluster', 'service']
      group_wait: 10s
      group_interval: 10s
      repeat_interval: 12h
      receiver: 'slack-critical'
      routes:
      - match:
          severity: critical
        receiver: 'pagerduty-critical'
      - match:
          severity: warning
        receiver: 'slack-warnings'

    receivers:
    - name: 'slack-critical'
      slack_configs:
      - channel: '#alerts-critical'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

    - name: 'slack-warnings'
      slack_configs:
      - channel: '#alerts-warnings'
        title: '{{ .GroupLabels.alertname }}'

    - name: 'pagerduty-critical'
      pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-rules
  namespace: mcp-production
data:
  alerts.yml: |
    groups:
    - name: gateway_alerts
      rules:
      # High authorization latency
      - alert: HighAuthorizationLatency
        expr: histogram_quantile(0.95, sark_gateway_authz_latency_seconds) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High Gateway authorization latency"
          description: "P95 latency > 100ms for 5 minutes"

      # Gateway authorization errors
      - alert: GatewayAuthorizationErrors
        expr: rate(sark_gateway_authz_errors_total[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Gateway authorization errors detected"
          description: "Error rate > 0.1/s for 2 minutes"

      # SARK pods down
      - alert: SARKPodsDown
        expr: kube_deployment_status_replicas_available{deployment="sark"} < 2
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "SARK pods unavailable"
          description: "Less than 2 SARK pods available"

      # Database connection errors
      - alert: DatabaseConnectionErrors
        expr: rate(sark_database_errors_total[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Database connection errors"
          description: "Database error rate elevated"

      # Redis cache miss rate
      - alert: LowCacheHitRate
        expr: rate(sark_gateway_cache_hits_total[10m]) / rate(sark_gateway_authz_requests_total[10m]) < 0.7
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low policy cache hit rate"
          description: "Cache hit rate < 70% for 10 minutes"
```

Deploy AlertManager:

```bash
kubectl apply -f k8s/production/alertmanager.yaml
```

---

## Part 9: Security Hardening

### Step 9.1: Network Policies

Create `k8s/production/network-policies.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sark-network-policy
  namespace: mcp-production
spec:
  podSelector:
    matchLabels:
      app: sark
  policyTypes:
  - Ingress
  - Egress
  ingress:
  # Allow from Gateway
  - from:
    - podSelector:
        matchLabels:
          app: gateway
    ports:
    - protocol: TCP
      port: 8000
  # Allow from Prometheus
  - from:
    - podSelector:
        matchLabels:
          app: prometheus
    ports:
    - protocol: TCP
      port: 9090
  egress:
  # Allow to PostgreSQL
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  # Allow to Redis
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  # Allow DNS
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: UDP
      port: 53

---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: gateway-network-policy
  namespace: mcp-production
spec:
  podSelector:
    matchLabels:
      app: gateway
  policyTypes:
  - Ingress
  - Egress
  ingress:
  # Allow from Ingress
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8080
  egress:
  # Allow to SARK
  - to:
    - podSelector:
        matchLabels:
          app: sark
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

Apply network policies:

```bash
kubectl apply -f k8s/production/network-policies.yaml
```

### Step 9.2: Pod Security Standards

Create `k8s/production/pod-security.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: mcp-production
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

---

## Part 10: Zero-Downtime Deployment

### Step 10.1: Rolling Update Strategy

Update `sark-deployment.yaml` with rolling update strategy:

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0  # Never allow all pods to be unavailable
  minReadySeconds: 10
  progressDeadlineSeconds: 600
```

### Step 10.2: Perform Rolling Update

```bash
# Update image tag
kubectl set image deployment/sark sark=sark:1.1.1 -n mcp-production

# Watch rollout
kubectl rollout status deployment/sark -n mcp-production

# If issues, rollback
kubectl rollout undo deployment/sark -n mcp-production
```

---

## Part 11: Production Checklist

### Pre-Deployment Checklist

- [ ] ✅ All secrets rotated from defaults
- [ ] ✅ TLS certificates configured
- [ ] ✅ Database backups enabled (automated)
- [ ] ✅ Monitoring dashboards configured
- [ ] ✅ Alerts configured and tested
- [ ] ✅ Network policies applied
- [ ] ✅ Resource limits set on all pods
- [ ] ✅ HPA configured and tested
- [ ] ✅ Logging forwarding to centralized system
- [ ] ✅ Disaster recovery plan documented
- [ ] ✅ On-call rotation established
- [ ] ✅ Runbook created for common issues

### Security Checklist

- [ ] ✅ No default passwords in use
- [ ] ✅ Secrets stored in Vault/Secrets Manager
- [ ] ✅ RBAC configured (least privilege)
- [ ] ✅ Pod Security Standards enforced
- [ ] ✅ Network policies restrict traffic
- [ ] ✅ Image scanning enabled (Trivy, Snyk)
- [ ] ✅ Audit logs forwarded to SIEM
- [ ] ✅ Penetration testing completed
- [ ] ✅ Compliance requirements met (SOC 2, GDPR, etc.)

---

## What You Learned

Congratulations on completing the production deployment! You now know:

✅ **High Availability**: Multi-replica deployments with pod anti-affinity
✅ **Auto-Scaling**: HPA configuration for handling load spikes
✅ **Load Balancing**: Ingress configuration with TLS termination
✅ **Monitoring**: Prometheus metrics and Grafana dashboards
✅ **Alerting**: Critical alerts for on-call engineers
✅ **Security**: Network policies, secrets management, TLS
✅ **Zero-Downtime**: Rolling updates without service interruption
✅ **Production Ops**: Runbooks, checklists, disaster recovery

Your deployment can now:
- Handle 10,000+ req/s
- Auto-scale from 3 to 20+ pods
- Provide 99.9%+ uptime
- Alert on critical issues within minutes
- Recover from failures automatically

---

## Next Steps

### Tutorial 4: Extending Gateway
Learn advanced topics:
- Custom tool type creation
- Advanced OPA policy authoring
- Plugin development for custom auth
- Performance tuning and optimization

👉 **[Continue to Tutorial 4 →](./04-extending-gateway.md)**

### Further Learning
- **[Disaster Recovery Guide](../../DISASTER_RECOVERY.md)**
- **[Incident Response Runbook](../../INCIDENT_RESPONSE.md)**
- **[Performance Tuning](../../PERFORMANCE_TUNING.md)**

---

*Last Updated: 2025-01-15*
*SARK Version: 1.1.0+*
*Tutorial Version: 1.0*
