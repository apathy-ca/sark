# How to Monitor SARK Gateway

This guide shows you how to set up comprehensive monitoring for the SARK Gateway using Prometheus, Grafana, and logging tools to ensure reliability and performance.

## Before You Begin

**Prerequisites:**
- SARK Gateway deployed and running
- Prometheus server (or managed service like Grafana Cloud)
- Grafana instance for visualization
- kubectl access to Kubernetes cluster (if using K8s)
- Basic understanding of metrics and monitoring concepts

**What You'll Learn:**
- Configure Prometheus to scrape gateway metrics
- Set up Grafana dashboards from templates
- Create critical alerts for gateway health
- Aggregate and search logs effectively
- Monitor gateway health checks
- Interpret performance metrics

**Time Required:** 45-60 minutes

## Understanding Gateway Metrics

The SARK Gateway exposes metrics in Prometheus format at `/metrics` endpoint:

```bash
curl http://localhost:9090/metrics
```

**Key Metric Categories:**
- **Request Metrics**: Rate, latency, errors
- **Tool Metrics**: Invocations per tool, success/failure rates
- **Policy Metrics**: Evaluation time, decisions (allow/deny)
- **Resource Metrics**: CPU, memory, goroutines
- **Health Metrics**: Server health status, connectivity

## Step 1: Set Up Prometheus Metrics Scraping

### Option A: Kubernetes ServiceMonitor

Create `prometheus/gateway-servicemonitor.yaml`:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: sark-gateway
  namespace: sark-system
  labels:
    app: sark-gateway
    monitoring: prometheus
spec:
  selector:
    matchLabels:
      app: sark-gateway
  endpoints:
    - port: metrics
      interval: 15s
      path: /metrics
      scheme: http
      scrapeTimeout: 10s
      honorLabels: true
      metricRelabelings:
        # Drop high-cardinality labels
        - sourceLabels: [__name__]
          regex: 'go_.*'
          action: drop
        # Add environment label
        - sourceLabels: [__address__]
          targetLabel: environment
          replacement: production
  namespaceSelector:
    matchNames:
      - sark-system
```

Apply the configuration:

```bash
kubectl apply -f prometheus/gateway-servicemonitor.yaml
```

**Expected Output:**
```
servicemonitor.monitoring.coreos.com/sark-gateway created
```

Verify scraping is working:

```bash
kubectl get servicemonitor -n sark-system
```

**Expected Output:**
```
NAME           AGE
sark-gateway   30s
```

### Option B: Prometheus Configuration File

Edit `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'production'
    environment: 'prod'

scrape_configs:
  - job_name: 'sark-gateway'
    static_configs:
      - targets:
          - 'gateway-01.example.com:9090'
          - 'gateway-02.example.com:9090'
          - 'gateway-03.example.com:9090'
        labels:
          service: 'sark-gateway'
          environment: 'production'

    # Scrape configuration
    scheme: http
    metrics_path: /metrics
    scrape_interval: 15s
    scrape_timeout: 10s

    # Metric relabeling
    metric_relabel_configs:
      # Add instance label from target
      - source_labels: [__address__]
        target_label: instance

      # Drop unnecessary Go runtime metrics
      - source_labels: [__name__]
        regex: 'go_gc_.*'
        action: drop

      # Rename metrics for consistency
      - source_labels: [__name__]
        regex: 'sark_gateway_(.*)'
        target_label: __name__
        replacement: 'gateway_${1}'

  # Scrape registered MCP servers
  - job_name: 'mcp-servers'
    static_configs:
      - targets:
          - 'mcp-server-01.example.com:8080'
          - 'mcp-server-02.example.com:8080'
        labels:
          service: 'mcp-server'
          environment: 'production'

    metrics_path: /metrics
    scrape_interval: 30s
```

Reload Prometheus configuration:

```bash
# If using systemd
sudo systemctl reload prometheus

# If using Docker
docker exec prometheus kill -HUP 1

# If using Kubernetes
kubectl rollout restart deployment/prometheus -n monitoring
```

**Verify Targets:**

Open Prometheus UI at `http://prometheus:9090/targets` and confirm:
- All gateway instances show as "UP"
- Last scrape shows recent timestamp
- No scrape errors

### Step 2: Verify Metrics Are Being Collected

Query Prometheus to confirm metrics are available:

```bash
# Using promtool
promtool query instant http://localhost:9090 \
  'up{job="sark-gateway"}'
```

**Expected Output:**
```
up{instance="gateway-01.example.com:9090", job="sark-gateway"} => 1 @[1705324800]
up{instance="gateway-02.example.com:9090", job="sark-gateway"} => 1 @[1705324800]
up{instance="gateway-03.example.com:9090", job="sark-gateway"} => 1 @[1705324800]
```

**What This Means:** All three gateway instances are being scraped successfully.

Check gateway-specific metrics:

```bash
# Request rate
promtool query instant http://localhost:9090 \
  'rate(gateway_requests_total[5m])'

# Tool invocations
promtool query instant http://localhost:9090 \
  'gateway_tool_invocations_total'
```

## Step 2: Create Grafana Dashboards from Templates

### Import Pre-Built Dashboard

Create `grafana/dashboards/gateway-overview.json`:

```json
{
  "dashboard": {
    "title": "SARK Gateway Overview",
    "tags": ["sark", "gateway", "overview"],
    "timezone": "browser",
    "refresh": "30s",
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "panels": [
      {
        "id": 1,
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(gateway_requests_total[5m])) by (instance)",
            "legendFormat": "{{instance}}"
          }
        ],
        "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
        "yaxes": [
          {"format": "reqps", "label": "Requests/sec"}
        ]
      },
      {
        "id": 2,
        "title": "Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(rate(gateway_requests_total{status=\"success\"}[5m])) / sum(rate(gateway_requests_total[5m])) * 100",
            "legendFormat": "Success Rate %"
          }
        ],
        "gridPos": {"x": 12, "y": 0, "w": 6, "h": 4},
        "options": {
          "graphMode": "area",
          "colorMode": "value",
          "unit": "percent"
        },
        "thresholds": {
          "mode": "absolute",
          "steps": [
            {"value": 0, "color": "red"},
            {"value": 95, "color": "yellow"},
            {"value": 99, "color": "green"}
          ]
        }
      },
      {
        "id": 3,
        "title": "P95 Latency",
        "type": "stat",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(gateway_request_duration_seconds_bucket[5m])) by (le))",
            "legendFormat": "P95 Latency"
          }
        ],
        "gridPos": {"x": 18, "y": 0, "w": 6, "h": 4},
        "options": {
          "unit": "s",
          "colorMode": "value"
        },
        "thresholds": {
          "mode": "absolute",
          "steps": [
            {"value": 0, "color": "green"},
            {"value": 1, "color": "yellow"},
            {"value": 5, "color": "red"}
          ]
        }
      },
      {
        "id": 4,
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(gateway_requests_total{status=\"error\"}[5m])) by (error_type)",
            "legendFormat": "{{error_type}}"
          }
        ],
        "gridPos": {"x": 0, "y": 8, "w": 12, "h": 8},
        "yaxes": [
          {"format": "reqps", "label": "Errors/sec"}
        ],
        "alert": {
          "name": "High Error Rate",
          "conditions": [
            {
              "evaluator": {"type": "gt", "params": [10]},
              "query": {"params": ["A", "5m", "now"]}
            }
          ]
        }
      },
      {
        "id": 5,
        "title": "Tool Invocations",
        "type": "table",
        "targets": [
          {
            "expr": "topk(10, sum(rate(gateway_tool_invocations_total[5m])) by (tool_name, server_id))",
            "format": "table",
            "instant": true
          }
        ],
        "gridPos": {"x": 12, "y": 8, "w": 12, "h": 8},
        "transformations": [
          {
            "id": "organize",
            "options": {
              "excludeByName": {"Time": true},
              "indexByName": {
                "tool_name": 0,
                "server_id": 1,
                "Value": 2
              },
              "renameByName": {
                "tool_name": "Tool",
                "server_id": "Server",
                "Value": "Req/sec"
              }
            }
          }
        ]
      },
      {
        "id": 6,
        "title": "Policy Decisions",
        "type": "piechart",
        "targets": [
          {
            "expr": "sum(gateway_policy_decisions_total) by (decision)",
            "legendFormat": "{{decision}}"
          }
        ],
        "gridPos": {"x": 0, "y": 16, "w": 8, "h": 8},
        "options": {
          "legend": {"displayMode": "list", "placement": "right"}
        }
      },
      {
        "id": 7,
        "title": "Policy Evaluation Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(gateway_policy_evaluation_duration_seconds_bucket[5m])) by (le))",
            "legendFormat": "P95"
          },
          {
            "expr": "histogram_quantile(0.99, sum(rate(gateway_policy_evaluation_duration_seconds_bucket[5m])) by (le))",
            "legendFormat": "P99"
          }
        ],
        "gridPos": {"x": 8, "y": 16, "w": 8, "h": 8},
        "yaxes": [
          {"format": "s", "label": "Duration"}
        ]
      },
      {
        "id": 8,
        "title": "Server Health Status",
        "type": "table",
        "targets": [
          {
            "expr": "gateway_server_health_status",
            "format": "table",
            "instant": true
          }
        ],
        "gridPos": {"x": 16, "y": 16, "w": 8, "h": 8},
        "transformations": [
          {
            "id": "organize",
            "options": {
              "renameByName": {
                "server_id": "Server",
                "Value": "Status",
                "__name__": null
              }
            }
          }
        ],
        "options": {
          "cellHeight": "sm",
          "showHeader": true
        }
      }
    ]
  }
}
```

### Import Dashboard via Grafana API

```bash
curl -X POST http://grafana:3000/api/dashboards/db \
  -H "Authorization: Bearer ${GRAFANA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d @grafana/dashboards/gateway-overview.json
```

**Expected Response:**
```json
{
  "id": 1,
  "slug": "sark-gateway-overview",
  "status": "success",
  "uid": "sark-gateway-001",
  "url": "/d/sark-gateway-001/sark-gateway-overview",
  "version": 1
}
```

### Import via Grafana UI

1. Open Grafana at `http://grafana:3000`
2. Navigate to **Dashboards** → **Import**
3. Click **Upload JSON file**
4. Select `gateway-overview.json`
5. Select Prometheus data source
6. Click **Import**

**Expected Result:** Dashboard appears in Grafana with real-time data.

### Create Custom Panels

Add performance breakdown panel:

```json
{
  "id": 9,
  "title": "Request Duration Breakdown",
  "type": "graph",
  "targets": [
    {
      "expr": "sum(rate(gateway_request_stage_duration_seconds_sum[5m])) by (stage) / sum(rate(gateway_request_stage_duration_seconds_count[5m])) by (stage)",
      "legendFormat": "{{stage}}"
    }
  ],
  "gridPos": {"x": 0, "y": 24, "w": 24, "h": 8},
  "fieldConfig": {
    "defaults": {
      "unit": "s",
      "custom": {
        "drawStyle": "bars",
        "stacking": {"mode": "normal"}
      }
    }
  }
}
```

## Step 3: Configure Critical Alerts

### Create Alerting Rules

Create `prometheus/alerts/gateway-alerts.yml`:

```yaml
groups:
  - name: sark_gateway_alerts
    interval: 30s
    rules:
      # High error rate alert
      - alert: HighErrorRate
        expr: |
          (
            sum(rate(gateway_requests_total{status="error"}[5m]))
            /
            sum(rate(gateway_requests_total[5m]))
          ) > 0.05
        for: 5m
        labels:
          severity: critical
          component: gateway
        annotations:
          summary: "Gateway error rate above 5%"
          description: "Gateway {{ $labels.instance }} has error rate of {{ $value | humanizePercentage }} (threshold: 5%)"
          runbook_url: "https://docs.example.com/runbooks/gateway-high-error-rate"

      # High latency alert
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95,
            sum(rate(gateway_request_duration_seconds_bucket[5m])) by (le, instance)
          ) > 5
        for: 10m
        labels:
          severity: warning
          component: gateway
        annotations:
          summary: "Gateway P95 latency above 5s"
          description: "Gateway {{ $labels.instance }} P95 latency is {{ $value }}s"
          dashboard_url: "https://grafana.example.com/d/sark-gateway-001"

      # Gateway instance down
      - alert: GatewayDown
        expr: up{job="sark-gateway"} == 0
        for: 1m
        labels:
          severity: critical
          component: gateway
        annotations:
          summary: "Gateway instance is down"
          description: "Gateway instance {{ $labels.instance }} has been down for more than 1 minute"
          action: "Check gateway logs and restart if necessary"

      # MCP server unhealthy
      - alert: MCPServerUnhealthy
        expr: gateway_server_health_status == 0
        for: 5m
        labels:
          severity: warning
          component: mcp-server
        annotations:
          summary: "MCP server {{ $labels.server_id }} is unhealthy"
          description: "Server {{ $labels.server_id }} has failed health checks"
          action: "Check server logs and connectivity"

      # Policy evaluation slow
      - alert: SlowPolicyEvaluation
        expr: |
          histogram_quantile(0.95,
            sum(rate(gateway_policy_evaluation_duration_seconds_bucket[5m])) by (le)
          ) > 0.1
        for: 10m
        labels:
          severity: warning
          component: policy
        annotations:
          summary: "Policy evaluation is slow"
          description: "P95 policy evaluation time is {{ $value }}s (threshold: 100ms)"

      # High denial rate (potential attack)
      - alert: HighPolicyDenialRate
        expr: |
          (
            sum(rate(gateway_policy_decisions_total{decision="deny"}[5m]))
            /
            sum(rate(gateway_policy_decisions_total[5m]))
          ) > 0.5
        for: 5m
        labels:
          severity: warning
          component: security
        annotations:
          summary: "High policy denial rate detected"
          description: "{{ $value | humanizePercentage }} of requests are being denied"
          action: "Investigate for potential unauthorized access attempts"

      # Memory usage high
      - alert: HighMemoryUsage
        expr: |
          (
            process_resident_memory_bytes{job="sark-gateway"}
            /
            node_memory_MemTotal_bytes
          ) > 0.8
        for: 10m
        labels:
          severity: warning
          component: infrastructure
        annotations:
          summary: "Gateway memory usage above 80%"
          description: "Gateway {{ $labels.instance }} using {{ $value | humanizePercentage }} of available memory"

      # Too many goroutines (potential leak)
      - alert: GoroutineLeak
        expr: |
          go_goroutines{job="sark-gateway"} > 10000
        for: 15m
        labels:
          severity: warning
          component: gateway
        annotations:
          summary: "High goroutine count detected"
          description: "Gateway {{ $labels.instance }} has {{ $value }} goroutines"
          action: "Check for goroutine leaks in application code"

      # Request queue backing up
      - alert: RequestQueueBackup
        expr: |
          gateway_request_queue_depth > 1000
        for: 5m
        labels:
          severity: critical
          component: gateway
        annotations:
          summary: "Request queue is backing up"
          description: "{{ $value }} requests queued on {{ $labels.instance }}"
          action: "Scale gateway horizontally or investigate slow upstream services"
```

Load alerts into Prometheus:

```bash
# Add to prometheus.yml
rule_files:
  - /etc/prometheus/alerts/gateway-alerts.yml

# Reload configuration
curl -X POST http://localhost:9090/-/reload
```

**Verify alerts are loaded:**

```bash
curl http://localhost:9090/api/v1/rules | jq '.data.groups[].name'
```

**Expected Output:**
```json
"sark_gateway_alerts"
```

### Configure Alertmanager

Create `alertmanager/config.yml`:

```yaml
global:
  resolve_timeout: 5m
  slack_api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'

  routes:
    # Critical alerts to PagerDuty
    - match:
        severity: critical
      receiver: pagerduty
      continue: true

    # Warning alerts to Slack
    - match:
        severity: warning
      receiver: slack
      continue: true

    # Security alerts to security team
    - match:
        component: security
      receiver: security-team

receivers:
  - name: 'default'
    slack_configs:
      - channel: '#sark-alerts'
        title: 'SARK Gateway Alert'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
        description: '{{ .GroupLabels.alertname }}'

  - name: 'slack'
    slack_configs:
      - channel: '#sark-warnings'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
        color: 'warning'

  - name: 'security-team'
    email_configs:
      - to: 'security@example.com'
        from: 'alerts@example.com'
        smarthost: 'smtp.example.com:587'
        auth_username: 'alerts@example.com'
        auth_password: 'YOUR_PASSWORD'
        headers:
          Subject: '[SECURITY] SARK Gateway Alert'

inhibit_rules:
  # Don't alert on high latency if gateway is down
  - source_match:
      alertname: GatewayDown
    target_match:
      alertname: HighLatency
    equal: ['instance']
```

Apply configuration:

```bash
kubectl create configmap alertmanager-config \
  --from-file=alertmanager.yml=alertmanager/config.yml \
  -n monitoring

kubectl rollout restart deployment/alertmanager -n monitoring
```

**Test alerts:**

```bash
# Trigger test alert
curl -X POST http://alertmanager:9093/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '[{
    "labels": {
      "alertname": "TestAlert",
      "severity": "warning"
    },
    "annotations": {
      "summary": "Test alert from SARK Gateway"
    }
  }]'
```

**Expected Result:** Alert appears in Slack channel within 30 seconds.

## Step 4: Log Aggregation Setup

### Option A: ELK Stack (Elasticsearch, Logstash, Kibana)

Configure Filebeat to ship logs:

Create `filebeat/filebeat.yml`:

```yaml
filebeat.inputs:
  - type: container
    paths:
      - '/var/lib/docker/containers/*/*.log'
    processors:
      - add_kubernetes_metadata:
          host: ${NODE_NAME}
          matchers:
            - logs_path:
                logs_path: "/var/lib/docker/containers/"

  - type: log
    enabled: true
    paths:
      - /var/log/sark-gateway/*.log
    fields:
      service: sark-gateway
      environment: production
    json.keys_under_root: true
    json.add_error_key: true

processors:
  - drop_event:
      when:
        not:
          or:
            - contains:
                kubernetes.labels.app: "sark-gateway"
            - equals:
                fields.service: "sark-gateway"

  - add_cloud_metadata: ~
  - add_host_metadata: ~
  - add_docker_metadata: ~

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "sark-gateway-logs-%{+yyyy.MM.dd}"
  username: "elastic"
  password: "${ELASTICSEARCH_PASSWORD}"

setup.kibana:
  host: "kibana:5601"

setup.ilm.enabled: true
setup.ilm.rollover_alias: "sark-gateway-logs"
setup.ilm.pattern: "{now/d}-000001"

logging.level: info
logging.to_files: true
logging.files:
  path: /var/log/filebeat
  name: filebeat
  keepfiles: 7
```

Deploy Filebeat:

```bash
kubectl apply -f filebeat/filebeat.yml
```

Create Kibana index pattern:

```bash
curl -X POST "http://kibana:5601/api/saved_objects/index-pattern/sark-gateway-logs" \
  -H "kbn-xsrf: true" \
  -H "Content-Type: application/json" \
  -d '{
    "attributes": {
      "title": "sark-gateway-logs-*",
      "timeFieldName": "@timestamp"
    }
  }'
```

### Option B: Loki Stack (Grafana Loki)

Configure Promtail:

Create `promtail/config.yml`:

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: sark-gateway
    static_configs:
      - targets:
          - localhost
        labels:
          job: sark-gateway
          environment: production
          __path__: /var/log/sark-gateway/*.log

    pipeline_stages:
      # Parse JSON logs
      - json:
          expressions:
            level: level
            timestamp: timestamp
            message: message
            request_id: request_id
            user_id: user_id
            tool_name: tool_name
            duration_ms: duration_ms

      # Extract labels
      - labels:
          level:
          request_id:
          user_id:
          tool_name:

      # Parse timestamp
      - timestamp:
          source: timestamp
          format: RFC3339

      # Add metrics
      - metrics:
          request_duration:
            type: Histogram
            description: "Request duration in milliseconds"
            source: duration_ms
            config:
              buckets: [10, 50, 100, 500, 1000, 5000]

  - job_name: kubernetes
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
            - sark-system

    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        target_label: app
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: pod
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace
```

Deploy Promtail:

```bash
kubectl apply -f promtail/config.yml
```

Query logs in Grafana:

```logql
{app="sark-gateway", environment="production"}
  | json
  | level="error"
  | line_format "{{.timestamp}} [{{.level}}] {{.message}}"
```

### Create Log Queries and Dashboards

Common log queries:

```logql
# All errors in last hour
{app="sark-gateway"} | json | level="error"

# Tool invocation errors
{app="sark-gateway"} | json | message=~"tool invocation failed" | line_format "Tool: {{.tool_name}}, Error: {{.error}}"

# Policy denials
{app="sark-gateway"} | json | message=~"policy denied" | line_format "User: {{.user_id}}, Tool: {{.tool_name}}, Reason: {{.denial_reason}}"

# Slow requests (>1s)
{app="sark-gateway"} | json | duration_ms > 1000 | line_format "{{.request_id}}: {{.duration_ms}}ms"

# Rate of errors by tool
rate({app="sark-gateway"} | json | level="error" [5m]) by (tool_name)

# Count of 5xx errors
sum(count_over_time({app="sark-gateway"} | json | status_code>=500 [1h]))
```

## Step 5: Health Check Monitoring

### Configure Health Check Endpoint

The gateway exposes `/health` and `/ready` endpoints:

```bash
# Liveness check
curl http://localhost:8080/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T14:30:00Z",
  "version": "1.5.0",
  "uptime_seconds": 86400,
  "checks": {
    "database": "healthy",
    "opa": "healthy",
    "mcp_servers": "healthy"
  }
}
```

```bash
# Readiness check
curl http://localhost:8080/ready
```

**Expected Response:**
```json
{
  "ready": true,
  "checks": {
    "accepting_traffic": true,
    "policies_loaded": true,
    "servers_registered": 5
  }
}
```

### Create Health Check Monitor

Create synthetic monitor using Blackbox Exporter:

```yaml
# blackbox/config.yml
modules:
  http_2xx:
    prober: http
    timeout: 5s
    http:
      valid_http_versions: ["HTTP/1.1", "HTTP/2.0"]
      valid_status_codes: [200]
      method: GET
      preferred_ip_protocol: "ip4"

  http_json:
    prober: http
    timeout: 5s
    http:
      valid_status_codes: [200]
      method: GET
      fail_if_body_not_matches_regexp:
        - '"status":\s*"healthy"'
```

Add to Prometheus config:

```yaml
scrape_configs:
  - job_name: 'blackbox'
    metrics_path: /probe
    params:
      module: [http_json]
    static_configs:
      - targets:
          - http://gateway-01.example.com:8080/health
          - http://gateway-02.example.com:8080/health
          - http://gateway-03.example.com:8080/health
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: blackbox-exporter:9115
```

Create health check alert:

```yaml
- alert: HealthCheckFailing
  expr: probe_success{job="blackbox"} == 0
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "Health check failing for {{ $labels.instance }}"
    description: "Gateway health endpoint is not responding"
```

## Step 6: Interpret Performance Metrics

### Key Metrics to Monitor

**Request Throughput:**
```promql
# Requests per second
rate(gateway_requests_total[5m])

# By status
sum(rate(gateway_requests_total[5m])) by (status)

# By endpoint
sum(rate(gateway_requests_total[5m])) by (endpoint)
```

**Latency Percentiles:**
```promql
# P50 latency
histogram_quantile(0.50, sum(rate(gateway_request_duration_seconds_bucket[5m])) by (le))

# P95 latency
histogram_quantile(0.95, sum(rate(gateway_request_duration_seconds_bucket[5m])) by (le))

# P99 latency
histogram_quantile(0.99, sum(rate(gateway_request_duration_seconds_bucket[5m])) by (le))

# By tool
histogram_quantile(0.95, sum(rate(gateway_request_duration_seconds_bucket[5m])) by (le, tool_name))
```

**Error Rates:**
```promql
# Overall error rate
sum(rate(gateway_requests_total{status="error"}[5m])) / sum(rate(gateway_requests_total[5m]))

# By error type
sum(rate(gateway_requests_total[5m])) by (error_type)

# 4xx vs 5xx
sum(rate(gateway_requests_total{status_code=~"4.."}[5m])) by (status_code)
sum(rate(gateway_requests_total{status_code=~"5.."}[5m])) by (status_code)
```

**Resource Utilization:**
```promql
# CPU usage
rate(process_cpu_seconds_total{job="sark-gateway"}[5m])

# Memory usage
process_resident_memory_bytes{job="sark-gateway"}

# Goroutines
go_goroutines{job="sark-gateway"}

# GC time
rate(go_gc_duration_seconds_sum[5m]) / rate(go_gc_duration_seconds_count[5m])
```

### Performance Baselines

Establish baseline metrics:

```markdown
## SARK Gateway Performance Baselines (Production)

### Request Metrics
- Throughput: 500-1000 req/s average
- P95 Latency: < 500ms
- P99 Latency: < 2s
- Success Rate: > 99.5%

### Policy Evaluation
- P95 Duration: < 10ms
- P99 Duration: < 50ms
- Denial Rate: < 5%

### Resource Usage
- CPU: 20-40% average per instance
- Memory: 500MB-2GB per instance
- Goroutines: 100-500 normal

### Health Checks
- Server Health: > 95% healthy
- Check Frequency: Every 30s
- Timeout: 5s
```

## Related Resources

- [Prometheus Query Examples](https://prometheus.io/docs/prometheus/latest/querying/examples/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/best-practices/)
- [Log Query Language (LogQL)](https://grafana.com/docs/loki/latest/logql/)
- [Gateway Metrics Reference](../reference/metrics.md)
- [Troubleshooting Guide](./how-to-troubleshoot-tools.md)
- [Alert Runbooks](../runbooks/gateway-alerts.md)

## Next Steps

1. **Set up alerting** for critical issues
   - See: [Alerting Best Practices](../explanation/alerting-strategy.md)

2. **Create runbooks** for common alerts
   - See: [Runbook Template](../templates/runbook-template.md)

3. **Troubleshoot issues** using logs and metrics
   - See: [How to Troubleshoot Tools](./how-to-troubleshoot-tools.md)

4. **Optimize performance** based on metrics
   - See: [Performance Tuning Guide](../tutorials/performance-tuning.md)
