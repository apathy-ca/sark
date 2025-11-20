# SARK Monitoring and Observability Guide

This guide covers monitoring, logging, and observability for SARK in production environments.

## Table of Contents

- [Overview](#overview)
- [Health Endpoints](#health-endpoints)
- [Metrics Collection](#metrics-collection)
- [Logging](#logging)
- [Prometheus Setup](#prometheus-setup)
- [Grafana Dashboards](#grafana-dashboards)
- [Alerting](#alerting)
- [Distributed Tracing](#distributed-tracing)
- [Log Aggregation](#log-aggregation)

## Overview

SARK is instrumented with comprehensive observability features:

- **Health Checks**: Kubernetes-native liveness, readiness, and startup probes
- **Metrics**: Prometheus-compatible metrics for monitoring
- **Structured Logging**: JSON logs for cloud log aggregators
- **Distributed Tracing**: Ready for OpenTelemetry integration

## Health Endpoints

SARK exposes four health check endpoints:

### `/health` - General Health Check

Basic health check that returns application status and uptime.

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "uptime": 1234.56,
  "version": "0.1.0"
}
```

**Use cases:**
- Basic smoke tests
- Service verification
- Load balancer health checks

### `/ready` - Readiness Probe

Kubernetes readiness probe to determine if the pod can accept traffic.

```bash
curl http://localhost:8000/ready
```

Response (ready):
```json
{
  "status": "ready",
  "checks": {
    "application": true
  },
  "uptime": 1234.56
}
```

Response (not ready - 503):
```json
{
  "status": "not_ready",
  "checks": {
    "application": true,
    "database": false
  },
  "uptime": 1234.56
}
```

**Use cases:**
- Kubernetes readiness probe
- Load balancer backend health
- Temporary traffic removal during issues

**Customize**: Add database, cache, and external service checks in `src/sark/health.py:readiness_check()`

### `/live` - Liveness Probe

Kubernetes liveness probe to detect if the application is alive or needs restart.

```bash
curl http://localhost:8000/live
```

Response:
```json
{
  "status": "alive",
  "uptime": 1234.56
}
```

**Use cases:**
- Kubernetes liveness probe
- Deadlock detection
- Unrecoverable error detection

**Customize**: Add deadlock detection, thread pool checks in `src/sark/health.py:liveness_check()`

### `/startup` - Startup Probe

Kubernetes startup probe for applications with long initialization times.

```bash
curl http://localhost:8000/startup
```

Response:
```json
{
  "status": "started",
  "uptime": 10.5
}
```

**Use cases:**
- Kubernetes startup probe
- Long initialization processes
- Prevents premature liveness/readiness checks

## Metrics Collection

SARK exposes Prometheus-compatible metrics at `/metrics`.

### Available Metrics

#### HTTP Metrics

- `http_requests_total` - Total HTTP requests (labels: method, endpoint, status)
- `http_request_duration_seconds` - Request latency histogram (labels: method, endpoint)
- `http_requests_in_progress` - Current in-progress requests (labels: method, endpoint)

#### Application Metrics

- `app_info` - Application metadata (labels: version, environment)
- `errors_total` - Total errors (labels: error_type, endpoint)
- `active_connections` - Number of active connections

#### Business Metrics

- `business_operations_total` - Total business operations (labels: operation, status)
- `business_operation_duration_seconds` - Business operation duration (labels: operation)

### Viewing Metrics

```bash
# View all metrics
curl http://localhost:8000/metrics

# View specific metric
curl http://localhost:8000/metrics | grep http_requests_total
```

Example output:
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/health",status="200"} 1523.0
http_requests_total{method="GET",endpoint="/api/v1/users",status="200"} 8932.0

# HELP http_request_duration_seconds HTTP request latency in seconds
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{method="GET",endpoint="/api/v1/users",le="0.005"} 5432.0
http_request_duration_seconds_bucket{method="GET",endpoint="/api/v1/users",le="0.01"} 7821.0
```

### Custom Metrics

Add custom metrics in your application code:

```python
from sark.metrics import business_operations_total, business_operation_duration_seconds
import time

# Count operations
business_operations_total.labels(operation="user_signup", status="success").inc()

# Track duration
start_time = time.time()
# ... do work ...
duration = time.time() - start_time
business_operation_duration_seconds.labels(operation="user_signup").observe(duration)
```

## Logging

SARK uses structured JSON logging for cloud environments.

### Log Format

**JSON format (production):**
```json
{
  "timestamp": "2025-01-20T10:30:45",
  "level": "INFO",
  "logger": "sark.main",
  "message": "Starting sark version 0.1.0 in production environment"
}
```

**Human-readable format (development):**
```
2025-01-20 10:30:45 - sark.main - INFO - Starting sark version 0.1.0 in production environment
```

### Log Levels

Set via `LOG_LEVEL` environment variable:
- `DEBUG` - Verbose debugging information
- `INFO` - General informational messages (default)
- `WARNING` - Warning messages
- `ERROR` - Error messages
- `CRITICAL` - Critical errors

### Accessing Logs

#### Kubernetes

```bash
# View logs from all pods
kubectl logs -l app=sark -f

# View logs from specific pod
kubectl logs <pod-name> -f

# View previous container logs (after crash)
kubectl logs <pod-name> --previous

# View last 100 lines
kubectl logs -l app=sark --tail=100
```

#### Docker

```bash
# View logs
docker logs <container-id> -f

# View last 100 lines
docker logs <container-id> --tail=100
```

### Contextual Logging

Add context to log entries:

```python
import logging

logger = logging.getLogger(__name__)

# Add custom fields
logger.info(
    "User action completed",
    extra={
        "request_id": "abc-123",
        "user_id": "user-456",
        "action": "purchase",
    }
)
```

Results in:
```json
{
  "timestamp": "2025-01-20T10:30:45",
  "level": "INFO",
  "logger": "sark.api",
  "message": "User action completed",
  "request_id": "abc-123",
  "user_id": "user-456",
  "action": "purchase"
}
```

## Prometheus Setup

### Install Prometheus in Kubernetes

#### Using Helm (Recommended)

```bash
# Add Prometheus community Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false
```

#### Create ServiceMonitor for SARK

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: sark
  namespace: production
  labels:
    app: sark
spec:
  selector:
    matchLabels:
      app: sark
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

Apply:
```bash
kubectl apply -f k8s/servicemonitor.yaml
```

### Verify Prometheus Scraping

1. Port-forward Prometheus:
```bash
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090
```

2. Open http://localhost:9090 in browser

3. Query for SARK metrics:
```promql
http_requests_total{app="sark"}
```

## Grafana Dashboards

### Access Grafana

```bash
# Port-forward Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Get admin password
kubectl get secret -n monitoring prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 --decode
```

Open http://localhost:3000 and login with `admin` and the password.

### Import SARK Dashboard

Create a dashboard with these key metrics:

#### Request Rate

```promql
sum(rate(http_requests_total{app="sark"}[5m])) by (endpoint)
```

#### Error Rate

```promql
sum(rate(http_requests_total{app="sark",status=~"5.."}[5m])) by (endpoint)
```

#### Request Duration (p95)

```promql
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{app="sark"}[5m])) by (le, endpoint))
```

#### Pod Count

```promql
count(kube_pod_info{namespace="production",pod=~"sark-.*"})
```

#### CPU Usage

```promql
sum(rate(container_cpu_usage_seconds_total{namespace="production",pod=~"sark-.*"}[5m])) by (pod)
```

#### Memory Usage

```promql
sum(container_memory_working_set_bytes{namespace="production",pod=~"sark-.*"}) by (pod)
```

### Example Dashboard JSON

Create `grafana/sark-dashboard.json` for a pre-built dashboard.

## Alerting

### Prometheus AlertManager Rules

Create `k8s/prometheus-rules.yaml`:

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
        sum(rate(http_requests_total{app="sark",status=~"5.."}[5m]))
        / sum(rate(http_requests_total{app="sark"}[5m])) > 0.05
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High error rate detected"
        description: "Error rate is {{ $value | humanizePercentage }}"

    # Pod down
    - alert: PodDown
      expr: kube_deployment_status_replicas_available{deployment="sark"} < 2
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "SARK pods unavailable"
        description: "Only {{ $value }} pods available"

    # High latency
    - alert: HighLatency
      expr: |
        histogram_quantile(0.95,
          sum(rate(http_request_duration_seconds_bucket{app="sark"}[5m])) by (le)
        ) > 1.0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High request latency"
        description: "P95 latency is {{ $value }}s"

    # High memory usage
    - alert: HighMemoryUsage
      expr: |
        sum(container_memory_working_set_bytes{pod=~"sark-.*"})
        / sum(container_spec_memory_limit_bytes{pod=~"sark-.*"}) > 0.85
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High memory usage"
        description: "Memory usage is {{ $value | humanizePercentage }}"
```

## Distributed Tracing

SARK is ready for OpenTelemetry integration. To enable:

1. Add OpenTelemetry dependencies:
```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi
```

2. Configure in `src/sark/main.py`:
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Configure tracing
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Configure OTLP exporter
otlp_exporter = OTLPSpanExporter(endpoint="http://jaeger:4317")
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))

# Auto-instrument FastAPI
FastAPIInstrumentor.instrument_app(app)
```

## Log Aggregation

### ELK Stack (Elasticsearch, Logstash, Kibana)

Deploy ELK stack to collect and analyze logs:

```bash
helm repo add elastic https://helm.elastic.co
helm install elasticsearch elastic/elasticsearch -n logging --create-namespace
helm install kibana elastic/kibana -n logging
helm install filebeat elastic/filebeat -n logging
```

### Cloud Provider Log Aggregation

#### AWS CloudWatch

Configure FluentBit DaemonSet to ship logs to CloudWatch.

#### GCP Cloud Logging

Enabled by default in GKE. View logs in Cloud Console.

#### Azure Monitor

Configure Azure Monitor for containers.

## Best Practices

1. **Set appropriate log levels** - Use INFO in production, DEBUG for troubleshooting
2. **Monitor the golden signals** - Latency, traffic, errors, saturation
3. **Set up alerts for critical issues** - Pod down, high error rate, high latency
4. **Use structured logging** - Enable JSON logs in cloud environments
5. **Regularly review dashboards** - Identify trends and anomalies
6. **Set up log retention policies** - Balance storage costs with compliance needs
7. **Use distributed tracing for complex requests** - Track requests across services
8. **Monitor resource usage** - Prevent resource exhaustion
9. **Test alerts** - Ensure alerting works before incidents occur
10. **Document runbooks** - Have clear procedures for responding to alerts
