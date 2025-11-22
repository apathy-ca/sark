# Kafka Configuration Guide

Guide for SARK's Kafka integration for high-scale audit event streaming.

## Table of Contents

- [Overview](#overview)
- [Current Status](#current-status)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Future Implementation](#future-implementation)
- [Migration Path](#migration-path)
- [Best Practices](#best-practices)

## Overview

### What is Kafka?

Apache Kafka is a distributed event streaming platform that provides:
- **High throughput** - Millions of events per second
- **Durability** - Persistent event storage
- **Scalability** - Horizontal scaling with partitions
- **Reliability** - Replication and fault tolerance

### Use Case in SARK

Kafka is planned for SARK deployments requiring:
- **Massive scale** - Beyond 10,000 events/minute
- **Event streaming** - Real-time event processing
- **Multiple consumers** - Multiple SIEM platforms or processors
- **Durability** - Event replay and reprocessing
- **Decoupling** - Separate event production from consumption

### Architecture Overview

```
┌──────────────┐
│    SARK      │
│ (Producer)   │
└──────┬───────┘
       │ Produce events
       v
┌──────────────────────────────────┐
│          Kafka Cluster           │
│  ┌───────────────────────────┐  │
│  │ Topic: sark-audit-events  │  │
│  │  Partition 0 │ Partition 1│  │
│  │  Partition 2 │ Partition 3│  │
│  └───────────────────────────┘  │
└──────┬───────────┬───────────────┘
       │           │
       │           └──────────┐
       v                      v
┌──────────────┐      ┌──────────────┐
│   Consumer   │      │   Consumer   │
│  (Splunk)    │      │  (Datadog)   │
└──────────────┘      └──────────────┘
       │                      │
       v                      v
┌──────────────┐      ┌──────────────┐
│Splunk Cloud  │      │   Datadog    │
└──────────────┘      └──────────────┘
```

## Current Status

### ⚠️ Implementation Status

**Status:** **PLANNED** (Not yet implemented)

The Kafka integration is:
- ✅ **Configured** - Settings and configuration structure exists
- ✅ **Planned** - Architecture and design documented
- ⏳ **Not Implemented** - No Kafka client code yet
- 📋 **Roadmap** - Scheduled for future release

### Current Direct SIEM Integration

SARK currently sends events directly to SIEM platforms:
- **Splunk Cloud** - Via HTTP Event Collector (HEC)
- **Datadog** - Via Logs API
- **Performance** - Validated for 10,000+ events/minute
- **Reliability** - Circuit breaker, retry, fallback logging

**This works well for most deployments!**

### When You Need Kafka

Consider Kafka when:
- Event rate > 50,000 events/minute
- Multiple SIEM platforms or consumers
- Need event replay capability
- Want to decouple producers/consumers
- Require guaranteed event ordering
- Building complex event processing pipelines

## Configuration

### Settings Structure

Configuration structure exists in `src/sark/config/settings.py`:

```python
class Settings(BaseSettings):
    """SARK application settings."""

    # Kafka (optional - for audit pipeline at scale)
    kafka_enabled: bool = False
    kafka_bootstrap_servers: list[str] = ["localhost:9092"]
    kafka_audit_topic: str = "sark-audit-events"
    kafka_consumer_group: str = "sark-audit-consumers"
```

### Environment Variables

When Kafka is implemented, configure using:

```bash
# Enable Kafka integration
KAFKA_ENABLED=true

# Kafka cluster endpoints (comma-separated)
KAFKA_BOOTSTRAP_SERVERS=kafka-1.example.com:9092,kafka-2.example.com:9092,kafka-3.example.com:9092

# Topic for audit events
KAFKA_AUDIT_TOPIC=sark-audit-events

# Consumer group ID
KAFKA_CONSUMER_GROUP=sark-audit-consumers

# Optional: Additional Kafka settings
KAFKA_SECURITY_PROTOCOL=SASL_SSL  # or PLAINTEXT, SSL, SASL_PLAINTEXT
KAFKA_SASL_MECHANISM=SCRAM-SHA-512  # or PLAIN, SCRAM-SHA-256, GSSAPI
KAFKA_SASL_USERNAME=sark-producer
KAFKA_SASL_PASSWORD=your-password-here
KAFKA_SSL_CA_LOCATION=/path/to/ca-cert.pem
KAFKA_SSL_CERT_LOCATION=/path/to/client-cert.pem
KAFKA_SSL_KEY_LOCATION=/path/to/client-key.pem
```

### Python Configuration (Planned)

When implemented, configuration will look like:

```python
from sark.config import settings

# Check if Kafka is enabled
if settings.kafka_enabled:
    # Kafka configuration
    kafka_config = {
        "bootstrap.servers": ",".join(settings.kafka_bootstrap_servers),
        "client.id": "sark-producer",
        # Additional configuration
    }
```

## Future Implementation

### Planned Components

When Kafka integration is implemented, it will include:

#### 1. Kafka Producer

**Location:** `src/sark/services/audit/kafka_producer.py`

**Responsibilities:**
- Serialize audit events to Kafka messages
- Produce events to Kafka topic
- Handle producer errors and retries
- Monitor producer metrics

**Example (Planned):**
```python
from sark.services.audit.kafka import KafkaProducer, KafkaConfig

# Create producer
kafka_config = KafkaConfig(
    bootstrap_servers=["kafka-1:9092", "kafka-2:9092"],
    topic="sark-audit-events",
    compression_type="gzip",
    max_in_flight=5,
)

producer = KafkaProducer(kafka_config)

# Produce event
await producer.produce(audit_event)

# Flush and close
await producer.flush()
await producer.close()
```

#### 2. Kafka Consumer (SIEM Forwarder)

**Location:** `src/sark/services/audit/kafka_consumer.py`

**Responsibilities:**
- Consume audit events from Kafka
- Forward to SIEM platforms (Splunk, Datadog)
- Handle consumer group coordination
- Track consumer lag

**Example (Planned):**
```python
from sark.services.audit.kafka import KafkaConsumer, KafkaConfig
from sark.services.audit.siem import SplunkSIEM

# Create consumer
kafka_config = KafkaConfig(
    bootstrap_servers=["kafka-1:9092", "kafka-2:9092"],
    topic="sark-audit-events",
    consumer_group="sark-splunk-forwarder",
)

consumer = KafkaConsumer(kafka_config)

# Create SIEM client
splunk = SplunkSIEM(splunk_config)

# Consume and forward
async for event in consumer.consume():
    await splunk.send_event(event)
    await consumer.commit(event)
```

#### 3. Event Schema

**Format:** Avro or JSON

**Schema (Planned):**
```json
{
  "type": "record",
  "name": "AuditEvent",
  "namespace": "com.sark.audit",
  "fields": [
    {"name": "id", "type": "string"},
    {"name": "timestamp", "type": "long"},
    {"name": "event_type", "type": "string"},
    {"name": "severity", "type": "string"},
    {"name": "user_id", "type": ["null", "string"]},
    {"name": "user_email", "type": ["null", "string"]},
    {"name": "server_id", "type": ["null", "string"]},
    {"name": "tool_name", "type": ["null", "string"]},
    {"name": "decision", "type": ["null", "string"]},
    {"name": "policy_id", "type": ["null", "string"]},
    {"name": "ip_address", "type": ["null", "string"]},
    {"name": "user_agent", "type": ["null", "string"]},
    {"name": "request_id", "type": ["null", "string"]},
    {"name": "details", "type": "string"}
  ]
}
```

### Topic Configuration

**Topic Settings (Planned):**
```bash
# Create topic
kafka-topics --create \
  --topic sark-audit-events \
  --bootstrap-server kafka-1:9092 \
  --partitions 12 \
  --replication-factor 3 \
  --config retention.ms=604800000 \  # 7 days
  --config compression.type=gzip \
  --config min.insync.replicas=2
```

**Partition Strategy:**
- Partition by `user_id` for ordering per user
- Or partition by `server_id` for ordering per server
- Or round-robin for maximum throughput

### Monitoring

**Metrics (Planned):**
- Producer lag
- Consumer lag
- Throughput (messages/sec, bytes/sec)
- Error rate
- Latency (p50, p95, p99)

**Prometheus Metrics (Planned):**
```promql
# Producer metrics
kafka_producer_messages_sent_total
kafka_producer_bytes_sent_total
kafka_producer_errors_total

# Consumer metrics
kafka_consumer_messages_consumed_total
kafka_consumer_lag_messages
kafka_consumer_lag_seconds
```

## Migration Path

### Phase 1: Current (Direct SIEM)

```
SARK → Splunk/Datadog (Direct)
```

**Status:** ✅ Implemented and validated
**Capacity:** 10,000+ events/minute
**Use Case:** Most deployments

### Phase 2: Add Kafka (Future)

```
SARK → Kafka → Consumer → Splunk/Datadog
```

**Status:** 📋 Planned
**Capacity:** 100,000+ events/minute
**Use Case:** High-scale deployments

### Migration Steps (When Available)

1. **Deploy Kafka Cluster**
   - 3+ brokers for production
   - ZooKeeper or KRaft mode
   - Configure replication and retention

2. **Create Audit Events Topic**
   - 12-24 partitions (based on scale)
   - Replication factor: 3
   - Retention: 7 days (or per compliance)

3. **Deploy Kafka Consumer**
   - Run as separate service
   - Configure consumer groups
   - Point to existing SIEM configs

4. **Enable Kafka in SARK**
   - Set `KAFKA_ENABLED=true`
   - Configure bootstrap servers
   - Restart SARK

5. **Monitor and Validate**
   - Check producer metrics
   - Check consumer lag
   - Verify events in SIEM

6. **Cutover**
   - Gradually increase traffic to Kafka
   - Monitor consumer lag
   - Disable direct SIEM forwarding

## Best Practices

### Topic Configuration

**Partitions:**
- Start with `num_brokers * 2` to `num_brokers * 4`
- Example: 3 brokers → 6-12 partitions
- Can increase partitions later (but not decrease)

**Replication:**
- Production: `replication_factor=3`
- Development: `replication_factor=1`
- Always set `min.insync.replicas=2` for production

**Retention:**
- Set based on compliance requirements
- 7 days typical for operational data
- Longer for compliance (90 days, 1 year)
- Use size-based retention if time-based insufficient

### Producer Configuration

**Reliability:**
- `acks=all` - Wait for all in-sync replicas
- `enable.idempotence=true` - Prevent duplicates
- `max.in.flight.requests.per.connection=5` - Ordered delivery

**Performance:**
- `compression.type=gzip` or `compression.type=lz4`
- `batch.size=16384` or higher
- `linger.ms=10` - Small batching delay

**Example:**
```python
producer_config = {
    "bootstrap.servers": "kafka-1:9092,kafka-2:9092",
    "acks": "all",
    "enable.idempotence": True,
    "max.in.flight.requests.per.connection": 5,
    "compression.type": "gzip",
    "batch.size": 16384,
    "linger.ms": 10,
}
```

### Consumer Configuration

**Reliability:**
- `enable.auto.commit=false` - Manual commit control
- `max.poll.interval.ms=300000` - 5 minutes
- `session.timeout.ms=10000` - 10 seconds

**Performance:**
- `fetch.min.bytes=1024` - Minimum fetch size
- `fetch.max.wait.ms=500` - Max wait time
- `max.partition.fetch.bytes=1048576` - Max per partition

**Example:**
```python
consumer_config = {
    "bootstrap.servers": "kafka-1:9092,kafka-2:9092",
    "group.id": "sark-splunk-forwarder",
    "enable.auto.commit": False,
    "auto.offset.reset": "earliest",
    "max.poll.interval.ms": 300000,
}
```

### Security

**Authentication:**
- Use SASL/SCRAM for authentication
- Rotate credentials regularly
- Separate credentials per service

**Encryption:**
- Use SSL/TLS for data in transit
- Enable inter-broker encryption
- Validate certificates

**Authorization:**
- Use Kafka ACLs
- Least-privilege access
- Separate topics per environment

### Monitoring

**Key Metrics:**
- **Producer lag** - Should be near zero
- **Consumer lag** - Track and alert
- **Under-replicated partitions** - Should be zero
- **Offline partitions** - Should be zero
- **Request rate** - Track throughput
- **Error rate** - Should be < 0.1%

**Alerts:**
- Consumer lag > 1000 messages
- Consumer lag > 60 seconds
- Producer errors > 10/min
- Under-replicated partitions > 0
- Offline partitions > 0

## Comparison: Direct SIEM vs Kafka

| Aspect | Direct SIEM | Via Kafka |
|--------|-------------|-----------|
| **Complexity** | Low | Medium-High |
| **Latency** | Low (~100ms) | Medium (~200-500ms) |
| **Throughput** | 10k-50k events/min | 100k+ events/min |
| **Durability** | Fallback files | Kafka persistence |
| **Multiple consumers** | Hard | Easy |
| **Event replay** | Manual | Built-in |
| **Ordering** | Best effort | Guaranteed (per partition) |
| **Decoupling** | Tight | Loose |
| **Cost** | Lower | Higher (Kafka cluster) |
| **Ops overhead** | Low | Medium |
| **Best for** | Most deployments | High-scale, multi-consumer |

## When to Use Each Approach

### Use Direct SIEM When:

✅ Event rate < 50,000/minute
✅ Single SIEM platform
✅ Low latency requirements
✅ Simpler operational model
✅ Cost-sensitive
✅ Small team

### Use Kafka When:

✅ Event rate > 50,000/minute
✅ Multiple SIEM platforms or consumers
✅ Need event replay
✅ Building event streaming pipelines
✅ Want decoupled architecture
✅ Have Kafka expertise
✅ Already using Kafka for other services

## Support and Resources

### Kafka Resources

- **Apache Kafka Documentation**: https://kafka.apache.org/documentation/
- **Confluent Platform**: https://docs.confluent.io/
- **Kafka: The Definitive Guide** (Book)
- **Kafka Clients**:
  - Python: `confluent-kafka-python`, `kafka-python`
  - Java: Native Kafka client
  - Go: `confluent-kafka-go`, `sarama`

### SARK Documentation

- [SIEM Framework](SIEM_FRAMEWORK.md) - Current direct SIEM integration
- [Integration Guide](INTEGRATION_GUIDE.md) - Splunk and Datadog setup
- [Event Schema](EVENT_SCHEMA.md) - Audit event structure
- [Performance Optimizations](PERFORMANCE_OPTIMIZATIONS.md) - Direct SIEM optimization

### Future Updates

This document will be updated when:
- Kafka integration is implemented
- New features are added
- Best practices evolve

Check the SARK changelog and release notes for updates.

---

**Last Updated:** 2025-11-22
**Status:** Planning/Design Document
**Implementation Target:** Future release
**Maintained By:** SARK Engineering Team
