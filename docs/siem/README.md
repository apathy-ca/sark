# SIEM Integration Documentation

Complete documentation for SARK's Security Information and Event Management (SIEM) integration.

## 📚 Documentation Index

### Quick Start Guides

| Guide | Description | Audience |
|-------|-------------|----------|
| **[Integration Guide](INTEGRATION_GUIDE.md)** | Step-by-step setup for Splunk and Datadog | All users |
| **[Splunk Setup](SPLUNK_SETUP.md)** | Detailed Splunk Cloud configuration | Splunk users |
| **[Datadog Setup](DATADOG_SETUP.md)** | Detailed Datadog Logs API configuration | Datadog users |

### Reference Documentation

| Guide | Description | Audience |
|-------|-------------|----------|
| **[Event Schema](EVENT_SCHEMA.md)** | Complete audit event field reference | Developers, analysts |
| **[SIEM Framework](SIEM_FRAMEWORK.md)** | Architecture and design overview | Architects, developers |

### Production Guides

| Guide | Description | Audience |
|-------|-------------|----------|
| **[Production Configuration](PRODUCTION_CONFIG.md)** | Production deployment and operations | DevOps, SRE |
| **[Performance Optimizations](PERFORMANCE_OPTIMIZATIONS.md)** | Circuit breaker, compression, batching | DevOps, SRE |
| **[Error Handling](ERROR_HANDLING.md)** | Error recovery, fallback, alerting | DevOps, SRE |

### Testing and Validation

| Guide | Description | Audience |
|-------|-------------|----------|
| **[Load Test Report](LOAD_TEST_REPORT.md)** | 10k events/min validation results | DevOps, QA |

### Future Planning

| Guide | Description | Audience |
|-------|-------------|----------|
| **[Kafka Configuration](KAFKA_CONFIGURATION.md)** | High-scale event streaming (planned) | Architects, DevOps |

## 🚀 Getting Started

### For New Users

1. **Start here:** [Integration Guide](INTEGRATION_GUIDE.md)
   - Choose your SIEM platform (Splunk or Datadog)
   - Follow step-by-step setup instructions
   - Test connectivity and send first event

2. **Platform-specific setup:**
   - Splunk users: [Splunk Setup](SPLUNK_SETUP.md)
   - Datadog users: [Datadog Setup](DATADOG_SETUP.md)

3. **Production deployment:**
   - Review [Production Configuration](PRODUCTION_CONFIG.md)
   - Configure monitoring and alerts
   - Enable performance optimizations

### For Developers

1. **Understand the architecture:** [SIEM Framework](SIEM_FRAMEWORK.md)
2. **Learn the event schema:** [Event Schema](EVENT_SCHEMA.md)
3. **Review test coverage:** Integration tests in `tests/integration/`

### For Operations

1. **Production checklist:** [Production Configuration](PRODUCTION_CONFIG.md)
2. **Enable optimizations:** [Performance Optimizations](PERFORMANCE_OPTIMIZATIONS.md)
3. **Configure error handling:** [Error Handling](ERROR_HANDLING.md)
4. **Monitor metrics:** Prometheus/Grafana integration

## 📖 Documentation Guide

### By Use Case

#### "I want to set up Splunk integration"
1. [Splunk Setup](SPLUNK_SETUP.md) - Complete Splunk configuration
2. [Integration Guide](INTEGRATION_GUIDE.md) - Splunk section
3. [Production Configuration](PRODUCTION_CONFIG.md) - Production settings

#### "I want to set up Datadog integration"
1. [Datadog Setup](DATADOG_SETUP.md) - Complete Datadog configuration
2. [Integration Guide](INTEGRATION_GUIDE.md) - Datadog section
3. [Production Configuration](PRODUCTION_CONFIG.md) - Production settings

#### "I need to deploy to production"
1. [Production Configuration](PRODUCTION_CONFIG.md) - Deployment checklist
2. [Performance Optimizations](PERFORMANCE_OPTIMIZATIONS.md) - Enable features
3. [Error Handling](ERROR_HANDLING.md) - Configure fallback and alerts
4. [Integration Guide](INTEGRATION_GUIDE.md) - Production deployment section

#### "I'm experiencing issues"
1. [Integration Guide](INTEGRATION_GUIDE.md) - Troubleshooting section
2. [Production Configuration](PRODUCTION_CONFIG.md) - Common issues
3. [Error Handling](ERROR_HANDLING.md) - Error patterns and recovery

#### "I need to understand the event structure"
1. [Event Schema](EVENT_SCHEMA.md) - Complete field reference
2. [SIEM Framework](SIEM_FRAMEWORK.md) - Event lifecycle

#### "I need high-scale event streaming"
1. [Kafka Configuration](KAFKA_CONFIGURATION.md) - Future Kafka integration
2. [Performance Optimizations](PERFORMANCE_OPTIMIZATIONS.md) - Current optimizations

### By Role

#### Security Analyst
- 📊 [Integration Guide](INTEGRATION_GUIDE.md) - Search queries and dashboards
- 📋 [Event Schema](EVENT_SCHEMA.md) - Event types and fields
- 🔍 [Splunk Setup](SPLUNK_SETUP.md) - Splunk search examples
- 🔍 [Datadog Setup](DATADOG_SETUP.md) - Datadog query examples

#### DevOps Engineer
- 🚀 [Production Configuration](PRODUCTION_CONFIG.md) - Deployment guide
- ⚡ [Performance Optimizations](PERFORMANCE_OPTIMIZATIONS.md) - Optimization guide
- 🛡️ [Error Handling](ERROR_HANDLING.md) - Reliability features
- 📈 [Load Test Report](LOAD_TEST_REPORT.md) - Performance validation

#### Software Engineer
- 🏗️ [SIEM Framework](SIEM_FRAMEWORK.md) - Architecture overview
- 📝 [Event Schema](EVENT_SCHEMA.md) - Event structure and types
- 🧪 Integration tests: `tests/integration/test_*_integration.py`
- 🔧 Source code: `src/sark/services/audit/siem/`

#### Solutions Architect
- 🏗️ [SIEM Framework](SIEM_FRAMEWORK.md) - System design
- 📊 [Kafka Configuration](KAFKA_CONFIGURATION.md) - Scaling strategy
- ⚡ [Performance Optimizations](PERFORMANCE_OPTIMIZATIONS.md) - Performance patterns
- 📈 [Load Test Report](LOAD_TEST_REPORT.md) - Capacity planning

## 🎯 Common Tasks

### Initial Setup

```bash
# 1. Install SARK with SIEM support
pip install sark[siem]

# 2. Configure environment
export SPLUNK_HEC_URL="https://your-instance.splunkcloud.com:8088/services/collector"
export SPLUNK_HEC_TOKEN="your-token"
export SPLUNK_INDEX="sark_production"

# 3. Test connection
python -c "
from sark.services.audit.siem import SplunkConfig, SplunkSIEM
import asyncio
import os

config = SplunkConfig(
    hec_url=os.getenv('SPLUNK_HEC_URL'),
    hec_token=os.getenv('SPLUNK_HEC_TOKEN'),
    index=os.getenv('SPLUNK_INDEX')
)
siem = SplunkSIEM(config)
health = asyncio.run(siem.health_check())
print(f'Healthy: {health.healthy}, Latency: {health.latency_ms}ms')
"
```

### Production Deployment

```python
from sark.services.audit.siem import (
    SplunkConfig,
    SplunkSIEM,
    SIEMOptimizer,
    SIEMErrorHandler,
    BatchHandler,
    CompressionConfig,
    HealthMonitorConfig,
    CircuitBreakerConfig,
    BatchConfig,
)

# Full production setup with all optimizations
# See: docs/siem/INTEGRATION_GUIDE.md#production-deployment
```

### Running Tests

```bash
# Test Splunk integration
export SPLUNK_HEC_URL="..."
export SPLUNK_HEC_TOKEN="..."
pytest tests/integration/test_splunk_integration.py -v -s

# Test Datadog integration
export DATADOG_API_KEY="..."
pytest tests/integration/test_datadog_integration.py -v -s

# Run load tests (10k events/min validation)
pytest tests/integration/test_siem_load.py -v -s

# Test event formatting (no credentials needed)
pytest tests/test_audit/test_siem_event_formatting.py -v
```

### Monitoring

```promql
# Prometheus metrics

# Event throughput
rate(siem_events_sent_total[5m])

# Error rate
rate(siem_events_failed_total[5m])

# Latency (p95)
histogram_quantile(0.95, siem_send_duration_seconds)

# Circuit breaker state (0=closed, 1=open, 2=half_open)
siem_circuit_breaker_state

# Consumer lag (if using Kafka)
kafka_consumer_lag_messages
```

## 📊 Feature Matrix

| Feature | Splunk | Datadog | Status |
|---------|--------|---------|--------|
| **Event forwarding** | ✅ | ✅ | Production |
| **Batch sending** | ✅ | ✅ | Production |
| **Gzip compression** | ✅ | ✅ | Production |
| **Circuit breaker** | ✅ | ✅ | Production |
| **Health monitoring** | ✅ | ✅ | Production |
| **Error handling** | ✅ | ✅ | Production |
| **Fallback logging** | ✅ | ✅ | Production |
| **Alert integration** | ✅ | ✅ | Production |
| **Metrics (Prometheus)** | ✅ | ✅ | Production |
| **10k events/min** | ✅ | ✅ | Validated |
| **Kafka integration** | 📋 | 📋 | Planned |

## 📈 Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| **Max throughput** | 10,000+ events/min | Validated in load tests |
| **Avg latency** | ~150ms | Including network |
| **P95 latency** | ~300ms | Including network |
| **Success rate** | 99.9%+ | With retries enabled |
| **Compression ratio** | 60-70% | For typical events |
| **Batch size** | 100 events | Configurable |
| **Circuit breaker** | 5 failures → 60s recovery | Configurable |

See [Load Test Report](LOAD_TEST_REPORT.md) for detailed performance analysis.

## 🔧 Configuration Reference

### Environment Variables

#### Splunk

```bash
SPLUNK_HEC_URL=https://your-instance.splunkcloud.com:8088/services/collector
SPLUNK_HEC_TOKEN=your-hec-token
SPLUNK_INDEX=sark_production
SPLUNK_SOURCETYPE=sark:audit:event
SPLUNK_SOURCE=sark
SPLUNK_VERIFY_SSL=true
SPLUNK_TIMEOUT_SECONDS=30
```

#### Datadog

```bash
DATADOG_API_KEY=your-api-key
DATADOG_APP_KEY=your-app-key  # Optional
DATADOG_SITE=datadoghq.com
DATADOG_SERVICE=sark
DATADOG_ENVIRONMENT=production
DATADOG_HOSTNAME=sark-prod-01  # Optional
DATADOG_VERIFY_SSL=true
DATADOG_TIMEOUT_SECONDS=30
```

#### Optimizations

```bash
# Batching
SIEM_BATCH_SIZE=100
SIEM_BATCH_TIMEOUT_SECONDS=5

# Compression
SIEM_COMPRESSION_ENABLED=true
SIEM_COMPRESSION_MIN_BYTES=1024
SIEM_COMPRESSION_LEVEL=6

# Circuit breaker
SIEM_CIRCUIT_BREAKER_ENABLED=true
SIEM_CIRCUIT_FAILURE_THRESHOLD=5
SIEM_CIRCUIT_RECOVERY_TIMEOUT=60

# Health monitoring
SIEM_HEALTH_CHECK_ENABLED=true
SIEM_HEALTH_CHECK_INTERVAL=30

# Error handling
SIEM_FALLBACK_ENABLED=true
SIEM_FALLBACK_DIR=/var/log/sark/siem_fallback
```

See [Production Configuration](PRODUCTION_CONFIG.md) for complete reference.

## 🛡️ Security Best Practices

1. **Credentials**
   - Store in secret management system (Vault, AWS Secrets Manager)
   - Rotate regularly (quarterly minimum)
   - Never commit to version control
   - Use least-privilege tokens

2. **Network**
   - Always enable SSL/TLS in production
   - Use private networks when possible
   - Whitelist source IPs
   - Monitor for unauthorized access

3. **Data**
   - Never log passwords or API keys
   - Redact PII when possible
   - Comply with GDPR/CCPA
   - Set appropriate retention policies

See [Production Configuration](PRODUCTION_CONFIG.md#security-best-practices) for detailed guidance.

## 🆘 Troubleshooting

### Quick Diagnostics

```bash
# Test Splunk connectivity
curl -k https://your-instance.splunkcloud.com:8088/services/collector/health

# Test Datadog connectivity
curl -X POST https://http-intake.logs.datadoghq.com/api/v2/logs \
  -H "DD-API-KEY: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"ddsource":"test","message":"test"}'

# Check SARK health
python -c "from sark.services.audit.siem import SplunkSIEM; import asyncio; print(asyncio.run(SplunkSIEM(config).health_check()))"

# View fallback logs
ls -lh /var/log/sark/siem_fallback/
```

### Common Issues

| Issue | Solution | Reference |
|-------|----------|-----------|
| Events not appearing | Check credentials, index, time range | [Integration Guide](INTEGRATION_GUIDE.md#troubleshooting) |
| High latency | Enable compression, batching | [Performance Optimizations](PERFORMANCE_OPTIMIZATIONS.md) |
| Circuit breaker open | Fix SIEM connectivity, wait for recovery | [Error Handling](ERROR_HANDLING.md) |
| Fallback files growing | Check SIEM health, replay files | [Error Handling](ERROR_HANDLING.md) |
| SSL errors | Verify certificates, check SSL settings | [Production Configuration](PRODUCTION_CONFIG.md) |

## 📞 Support

### Documentation

- Start with [Integration Guide](INTEGRATION_GUIDE.md)
- Check troubleshooting sections in each guide
- Review test examples in `tests/integration/`

### External Resources

- **Splunk**: https://docs.splunk.com/Documentation/Splunk/latest/Data/UsetheHTTPEventCollector
- **Datadog**: https://docs.datadoghq.com/api/latest/logs/
- **SARK Issues**: https://github.com/apathy-ca/sark/issues

### Escalation

1. Check documentation
2. Review application logs
3. Test connectivity
4. Check SIEM platform status
5. Contact support team

## 🗺️ Roadmap

### Current (v1.0)

- ✅ Splunk Cloud integration
- ✅ Datadog Logs API integration
- ✅ Event batching and compression
- ✅ Circuit breaker pattern
- ✅ Health monitoring
- ✅ Error handling and fallback
- ✅ 10,000 events/min validated

### Planned (v1.1+)

- 📋 Kafka integration for high-scale deployments
- 📋 Additional SIEM platforms (Azure Sentinel, Elastic)
- 📋 Event sampling for high-volume low-value events
- 📋 Advanced analytics and anomaly detection
- 📋 Event enrichment pipeline

See [Kafka Configuration](KAFKA_CONFIGURATION.md) for scaling roadmap.

## 📝 Contributing

When updating SIEM documentation:

1. Follow existing structure and format
2. Include code examples
3. Add troubleshooting sections
4. Update this README index
5. Test all code examples
6. Update version and date

## 📄 License

Copyright © 2025 SARK Engineering Team

---

**Last Updated:** 2025-11-22
**Documentation Version:** 1.0
**SIEM Integration Version:** 1.0
**Maintained By:** SARK Engineering Team
