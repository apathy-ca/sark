# Valkey Optimization Guide

**Document Version**: 1.0
**Last Updated**: November 22, 2025
**Audience**: DevOps Engineers, Backend Developers, SRE Teams

---

## Table of Contents

1. [Overview](#overview)
2. [Valkey Architecture in SARK](#redis-architecture-in-sark)
3. [Connection Pooling](#connection-pooling)
4. [Cache Optimization](#cache-optimization)
5. [Memory Management](#memory-management)
6. [Persistence Configuration](#persistence-configuration)
7. [Performance Tuning](#performance-tuning)
8. [High Availability](#high-availability)
9. [Monitoring and Metrics](#monitoring-and-metrics)
10. [Troubleshooting](#troubleshooting)
11. [Best Practices](#best-practices)

---

## Overview

SARK uses Valkey for multiple critical functions:
- **Session Storage**: User sessions and JWT token tracking
- **Policy Decision Caching**: OPA policy evaluation results
- **Rate Limiting**: Request rate tracking and enforcement
- **SIEM Event Queue**: Buffering audit events before forwarding
- **Circuit Breaker State**: SIEM integration failure tracking

### Performance Goals

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| GET Latency (p95) | < 1ms | < 5ms |
| SET Latency (p95) | < 2ms | < 10ms |
| Memory Usage | < 70% | < 90% |
| Cache Hit Rate (Policy) | > 90% | > 80% |
| Connection Pool Utilization | 60-80% | < 95% |
| Eviction Rate | < 100/s | < 1000/s |
| Keyspace Utilization | < 80% | < 90% |

---

## Valkey Architecture in SARK

### Data Structure Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Valkey Keyspace                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Database 0 (Default)                                            │
│  ├── Sessions                                                    │
│  │   ├── session:user:{user_id}:{session_id}  (Hash)            │
│  │   │   Fields: access_token_jti, refresh_token_hash, ...      │
│  │   │   TTL: 7 days                                             │
│  │   └── session:token:{jti}                  (String)          │
│  │       Value: session_id                                       │
│  │       TTL: 15 minutes                                         │
│  │                                                                │
│  ├── Policy Cache                                                │
│  │   ├── policy:decision:{hash}               (String)          │
│  │   │   Value: {"allow": true, "reason": "..."} (JSON)         │
│  │   │   TTL: 300s (high sensitivity) to 3600s (low)            │
│  │   └── policy:version:{policy_name}         (String)          │
│  │       Value: version_number                                   │
│  │                                                                │
│  ├── Rate Limiting                                               │
│  │   ├── ratelimit:user:{user_id}:{window}    (String)          │
│  │   │   Value: request_count                                    │
│  │   │   TTL: 60s (1-minute window)                              │
│  │   ├── ratelimit:ip:{ip_addr}:{window}      (String)          │
│  │   │   Value: request_count                                    │
│  │   │   TTL: 60s                                                │
│  │   └── ratelimit:apikey:{key_id}:{window}   (String)          │
│  │       Value: request_count                                    │
│  │       TTL: 60s                                                │
│  │                                                                │
│  ├── SIEM Event Queue                                            │
│  │   ├── siem:event_queue                     (List)            │
│  │   │   Values: JSON event objects                              │
│  │   │   Max Length: 100,000                                     │
│  │   └── siem:failed_events                   (List)            │
│  │       Values: Failed event objects                            │
│  │                                                                │
│  └── Circuit Breaker                                             │
│      ├── circuit_breaker:siem:state           (String)          │
│      │   Value: "closed", "open", "half_open"                   │
│      │   TTL: None (persistent)                                  │
│      ├── circuit_breaker:siem:failure_count   (String)          │
│      │   Value: consecutive_failures                             │
│      └── circuit_breaker:siem:last_failure    (String)          │
│          Value: ISO timestamp                                    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

Total Keys (Production Estimate):
- Sessions: ~10,000 (5,000 users × 2 sessions avg)
- Policy Cache: ~50,000 (varies by policy complexity)
- Rate Limits: ~5,000 (ephemeral, 1-minute windows)
- SIEM Queue: ~1,000-10,000 (buffer during spikes)
- Total: ~66,000-75,000 keys
```

### Memory Estimation

```
Memory Per Data Type:
- Session (Hash): ~500 bytes × 10,000 = 5 MB
- Policy Decision (String): ~200 bytes × 50,000 = 10 MB
- Rate Limit (String): ~100 bytes × 5,000 = 0.5 MB
- SIEM Event (List): ~1 KB × 10,000 = 10 MB
- Total Data: ~25-30 MB

Valkey Overhead (40%): ~12 MB
Total Memory: ~40-50 MB (typical)
Recommended Memory Limit: 512 MB (10× headroom)
```

---

## Connection Pooling

### Connection Pool Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  Valkey Connection Pool Architecture              │
└─────────────────────────────────────────────────────────────────┘

         Application Servers (4 pods × 20 connections = 80)
         ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
         │   Pod 1  │  │   Pod 2  │  │   Pod 3  │  │   Pod 4  │
         │  Pool:20 │  │  Pool:20 │  │  Pool:20 │  │  Pool:20 │
         └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
              │             │             │             │
              └──────────┬──┴─────┬───────┴──────────┬──┘
                         │        │                  │
                         ▼        ▼                  ▼
                    ┌────────────────────────────────────┐
                    │         Valkey Server               │
                    │         maxclients = 10000         │
                    │         Used: ~100 (1%)            │
                    └────────────────────────────────────┘
```

### Python Valkey Connection Pool (redis-py)

**Configuration** (`src/sark/cache.py`):
```python
import redis
from redis.connection import ConnectionPool
import os

# Valkey connection URL
VALKEY_URL = os.getenv("VALKEY_URL", "valkey://valkey:6379/0")
VALKEY_PASSWORD = os.getenv("VALKEY_PASSWORD")

# Create connection pool
redis_pool = ConnectionPool(
    host="redis",
    port=6379,
    db=0,
    password=VALKEY_PASSWORD,
    max_connections=20,          # Maximum connections in pool
    socket_timeout=5,            # Socket timeout (5 seconds)
    socket_connect_timeout=2,    # Connection timeout (2 seconds)
    socket_keepalive=True,       # Enable TCP keepalive
    socket_keepalive_options={
        1: 1,    # TCP_KEEPIDLE
        2: 1,    # TCP_KEEPINTVL
        3: 3     # TCP_KEEPCNT
    },
    retry_on_timeout=True,       # Retry on timeout
    health_check_interval=30,    # Health check every 30s
    decode_responses=True        # Auto-decode bytes to strings
)

# Create Valkey client
redis_client = redis.Redis(connection_pool=redis_pool)

# Test connection
try:
    redis_client.ping()
    print("✓ Valkey connection successful")
except redis.ConnectionError as e:
    print(f"✗ Valkey connection failed: {e}")
```

**Environment Variables**:
```bash
# Valkey connection
VALKEY_URL=valkey://valkey:6379/0
VALKEY_PASSWORD=your-secure-password-here
VALKEY_POOL_SIZE=20
VALKEY_SOCKET_TIMEOUT=5
VALKEY_SOCKET_CONNECT_TIMEOUT=2
VALKEY_HEALTH_CHECK_INTERVAL=30

# Valkey Sentinel (HA setup)
VALKEY_SENTINEL_HOSTS=sentinel1:26379,sentinel2:26379,sentinel3:26379
VALKEY_SENTINEL_MASTER=mymaster
```

### Connection Pool Sizing

**Formula**:
```
Total Connections = Application Pods × Pool Size

Example:
- Application Pods: 4
- Pool Size per Pod: 20
- Total Connections: 80

Valkey maxclients: 10000 (default)
Utilization: 80 / 10000 = 0.8%
```

**Recommended Sizing by Workload**:

| Workload Type | Pool Size | Total (4 pods) | Valkey maxclients |
|---------------|-----------|----------------|------------------|
| **Low** (< 100 req/s) | 10 | 40 | 1000 |
| **Medium** (100-500 req/s) | 20 | 80 | 10000 (default) |
| **High** (500-1000 req/s) | 30 | 120 | 10000 |
| **Very High** (> 1000 req/s) | 50 | 200 | 10000 |

### Connection Pool Monitoring

```python
# Get pool stats
pool_info = redis_pool.connection_kwargs
print(f"Max connections: {redis_pool.max_connections}")
print(f"Created connections: {redis_pool._created_connections}")
print(f"Available connections: {redis_pool._available_connections.qsize()}")
print(f"In-use connections: {redis_pool._created_connections - redis_pool._available_connections.qsize()}")

# Pool utilization
utilization = (redis_pool._created_connections - redis_pool._available_connections.qsize()) / redis_pool.max_connections * 100
print(f"Pool utilization: {utilization:.2f}%")
```

**Valkey Server Connection Stats**:
```bash
# Check current connections
redis-cli INFO clients

# Output:
# connected_clients:85
# client_recent_max_input_buffer:8
# client_recent_max_output_buffer:0
# blocked_clients:0

# Check maxclients setting
redis-cli CONFIG GET maxclients

# Set maxclients (if needed)
redis-cli CONFIG SET maxclients 10000
```

---

## Cache Optimization

### Cache Strategy

SARK uses Valkey caching for OPA policy evaluation results to reduce latency from ~50ms (OPA call) to <5ms (Valkey cache hit).

```
┌─────────────────────────────────────────────────────────────────┐
│                      Policy Evaluation Flow                      │
└─────────────────────────────────────────────────────────────────┘

    Request → Check Cache → [Cache Hit] → Return Cached Decision (< 5ms)
                   │
                   └─→ [Cache Miss] → Evaluate with OPA (50ms)
                                          │
                                          └─→ Cache Result → Return Decision
```

### Cache Key Design

**Policy Decision Cache Key**:
```python
import hashlib
import json

def get_policy_cache_key(user_id: str, action: str, resource: str, context: dict = None) -> str:
    """
    Generate deterministic cache key for policy decision.

    Format: policy:decision:{hash}
    Hash: SHA256 of sorted JSON (user_id, action, resource, context)
    """
    cache_input = {
        "user_id": user_id,
        "action": action,
        "resource": resource,
        "context": context or {}
    }

    # Sort keys for deterministic hashing
    cache_json = json.dumps(cache_input, sort_keys=True)
    cache_hash = hashlib.sha256(cache_json.encode()).hexdigest()

    return f"policy:decision:{cache_hash}"

# Example usage
cache_key = get_policy_cache_key(
    user_id="user-123",
    action="server:read",
    resource="server-456",
    context={"ip": "192.168.1.1"}
)
# Result: "policy:decision:a1b2c3d4e5f6..."
```

### Cache TTL Strategy

**Tiered TTL Based on Sensitivity**:
```python
from enum import Enum

class PolicySensitivity(Enum):
    HIGH = 300      # 5 minutes (e.g., admin actions)
    MEDIUM = 900    # 15 minutes (e.g., write operations)
    LOW = 3600      # 1 hour (e.g., read operations)

def get_cache_ttl(action: str) -> int:
    """Get cache TTL based on action sensitivity."""
    if action.startswith("admin:"):
        return PolicySensitivity.HIGH.value
    elif action.endswith(":write") or action.endswith(":delete"):
        return PolicySensitivity.MEDIUM.value
    else:
        return PolicySensitivity.LOW.value

# Example usage
ttl = get_cache_ttl("server:read")    # 3600s (1 hour)
ttl = get_cache_ttl("server:write")   # 900s (15 min)
ttl = get_cache_ttl("admin:delete")   # 300s (5 min)
```

### Cache Implementation

**Set Cache**:
```python
def cache_policy_decision(cache_key: str, decision: dict, ttl: int) -> None:
    """Cache policy decision with TTL."""
    try:
        redis_client.setex(
            name=cache_key,
            time=ttl,
            value=json.dumps(decision)
        )
    except redis.RedisError as e:
        # Log error but don't fail request
        logger.error(f"Failed to cache policy decision: {e}")

# Example
decision = {"allow": True, "reason": "User has read permission"}
cache_policy_decision(cache_key, decision, ttl=3600)
```

**Get Cache**:
```python
def get_cached_policy_decision(cache_key: str) -> dict | None:
    """Get cached policy decision."""
    try:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
        return None
    except redis.RedisError as e:
        logger.error(f"Failed to get cached policy decision: {e}")
        return None

# Example
cached_decision = get_cached_policy_decision(cache_key)
if cached_decision:
    print(f"Cache hit! Decision: {cached_decision}")
else:
    print("Cache miss, evaluating with OPA...")
```

### Cache Invalidation

**Invalidation Strategies**:

1. **Time-based (TTL)**: Automatic expiration (primary strategy)
2. **Event-based**: Invalidate on policy update
3. **Pattern-based**: Invalidate all decisions for a policy

**Invalidate on Policy Update**:
```python
def invalidate_policy_cache(policy_name: str) -> int:
    """
    Invalidate all cached decisions for a policy.
    Returns number of keys deleted.
    """
    try:
        # Get all policy decision keys
        pattern = f"policy:decision:*"
        cursor = 0
        deleted = 0

        while True:
            cursor, keys = redis_client.scan(cursor, match=pattern, count=1000)

            if keys:
                # Delete in batches
                deleted += redis_client.delete(*keys)

            if cursor == 0:
                break

        # Update policy version (cache bust)
        redis_client.incr(f"policy:version:{policy_name}")

        logger.info(f"Invalidated {deleted} cached decisions for policy {policy_name}")
        return deleted

    except redis.RedisError as e:
        logger.error(f"Failed to invalidate policy cache: {e}")
        return 0

# Example: Invalidate when policy is updated
invalidate_policy_cache("server_access_policy")
```

**Selective Invalidation (User-specific)**:
```python
def invalidate_user_cache(user_id: str) -> int:
    """Invalidate all cached decisions for a user."""
    # Since we hash the entire input, we need to track user keys separately
    # Option 1: Use Valkey Sets to track keys per user
    # Option 2: Use key prefix with user_id (less efficient for lookups)

    # For simplicity, use pattern matching (less efficient)
    pattern = f"policy:decision:*"
    cursor = 0
    deleted = 0

    while True:
        cursor, keys = redis_client.scan(cursor, match=pattern, count=1000)

        for key in keys:
            # Check if decision is for this user (expensive!)
            cached = redis_client.get(key)
            if cached and user_id in cached:
                redis_client.delete(key)
                deleted += 1

        if cursor == 0:
            break

    return deleted

# Better approach: Track user keys in a Set
def cache_policy_decision_tracked(cache_key: str, user_id: str, decision: dict, ttl: int):
    """Cache policy decision and track by user."""
    pipe = redis_client.pipeline()

    # Set cache
    pipe.setex(cache_key, ttl, json.dumps(decision))

    # Track user's cached keys (with same TTL)
    user_keys_set = f"user:cache_keys:{user_id}"
    pipe.sadd(user_keys_set, cache_key)
    pipe.expire(user_keys_set, ttl)

    pipe.execute()

def invalidate_user_cache_efficient(user_id: str) -> int:
    """Efficiently invalidate all cached decisions for a user."""
    user_keys_set = f"user:cache_keys:{user_id}"

    # Get all keys for user
    keys = redis_client.smembers(user_keys_set)

    if not keys:
        return 0

    # Delete all keys + the set itself
    deleted = redis_client.delete(*keys, user_keys_set)

    return deleted
```

### Cache Warming

**Pre-warm Cache on Application Start**:
```python
async def warm_policy_cache():
    """Pre-warm cache with common policy decisions."""
    logger.info("Warming policy cache...")

    # Common patterns to pre-cache
    common_patterns = [
        ("user:read", PolicySensitivity.LOW),
        ("server:read", PolicySensitivity.LOW),
        ("server:list", PolicySensitivity.LOW),
    ]

    users = await get_active_users(limit=100)  # Top 100 active users

    for user in users:
        for action, sensitivity in common_patterns:
            # Evaluate and cache
            decision = await evaluate_policy(user.id, action, resource="*")
            cache_key = get_policy_cache_key(user.id, action, "*")
            cache_policy_decision(cache_key, decision, sensitivity.value)

    logger.info(f"Cache warmed with {len(users) * len(common_patterns)} decisions")

# Call on startup
@app.on_event("startup")
async def startup_event():
    await warm_policy_cache()
```

---

## Memory Management

### Memory Configuration

**redis.conf**:
```conf
# ===========================
# Memory Settings
# ===========================

# Maximum memory (512 MB)
maxmemory 512mb

# Eviction policy
# - allkeys-lru: Evict least recently used keys (recommended for cache)
# - volatile-lru: Evict LRU keys with TTL only
# - allkeys-lfu: Evict least frequently used keys
# - volatile-lfu: Evict LFU keys with TTL only
# - allkeys-random: Evict random keys
# - volatile-random: Evict random keys with TTL
# - volatile-ttl: Evict keys with shortest TTL
# - noeviction: Return errors when memory limit reached
maxmemory-policy allkeys-lru

# LRU/LFU algorithm precision (1-10, higher = more accurate but slower)
maxmemory-samples 5

# ===========================
# Persistence (Optional)
# ===========================

# Disable RDB snapshots for pure cache (better performance)
save ""

# Disable AOF for pure cache
appendonly no

# If persistence is needed:
# save 900 1       # Save after 900s if >= 1 key changed
# save 300 10      # Save after 300s if >= 10 keys changed
# save 60 10000    # Save after 60s if >= 10000 keys changed
# appendonly yes
# appendfsync everysec

# ===========================
# Performance
# ===========================

# TCP backlog
tcp-backlog 511

# TCP keepalive (seconds)
tcp-keepalive 300

# Max clients
maxclients 10000

# Disable slow commands (optional for security)
# rename-command FLUSHDB ""
# rename-command FLUSHALL ""
# rename-command KEYS ""
# rename-command CONFIG ""
```

### Apply Configuration

**Docker Compose**:
```yaml
services:
  valkey:
    image: valkey:7-alpine
    command: >
      redis-server
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
      --save ""
      --appendonly no
      --requirepass ${VALKEY_PASSWORD}
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3
```

**Kubernetes ConfigMap**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: redis-config
data:
  redis.conf: |
    maxmemory 512mb
    maxmemory-policy allkeys-lru
    maxmemory-samples 5
    save ""
    appendonly no
    tcp-backlog 511
    tcp-keepalive 300
    maxclients 10000
```

### Memory Optimization Techniques

#### 1. Use Appropriate Data Structures

```python
# ✗ Bad: Store session as JSON string (inefficient)
redis_client.set(
    f"session:{session_id}",
    json.dumps({
        "user_id": "123",
        "expires_at": "2025-11-22T10:00:00Z",
        "ip": "192.168.1.1"
    })
)

# ✓ Good: Store session as Hash (50% less memory)
redis_client.hset(
    f"session:{session_id}",
    mapping={
        "user_id": "123",
        "expires_at": "2025-11-22T10:00:00Z",
        "ip": "192.168.1.1"
    }
)
redis_client.expire(f"session:{session_id}", 3600)
```

#### 2. Compress Large Values

```python
import gzip
import json

def set_compressed(key: str, value: dict, ttl: int):
    """Store compressed JSON value."""
    json_str = json.dumps(value)
    compressed = gzip.compress(json_str.encode())
    redis_client.setex(key, ttl, compressed)

def get_compressed(key: str) -> dict | None:
    """Get and decompress value."""
    compressed = redis_client.get(key)
    if not compressed:
        return None
    json_str = gzip.decompress(compressed).decode()
    return json.loads(json_str)

# Use for large values (> 1 KB)
large_decision = {"allow": True, "details": "..." * 1000}
set_compressed(cache_key, large_decision, ttl=3600)
```

#### 3. Use Shorter Key Names

```python
# ✗ Bad: Long key names (wastes memory)
redis_client.set("policy:decision:user:123:action:server:read:resource:server-456", "...")

# ✓ Good: Shorter key names
# p:d = policy:decision
# u = user, a = action, r = resource
redis_client.set("p:d:u:123:a:srv:r:r:456", "...")

# Even better: Use hash as key
cache_hash = hashlib.sha256(f"123:server:read:456".encode()).hexdigest()[:16]
redis_client.set(f"pd:{cache_hash}", "...")
```

#### 4. Set Appropriate TTLs

```python
# Always set TTL to prevent memory leaks
redis_client.setex("key", time=3600, value="value")  # ✓ Good

# Never use SET without TTL for cache data
redis_client.set("key", "value")  # ✗ Bad (no TTL)
```

### Memory Monitoring

```bash
# Memory usage
redis-cli INFO memory

# Key memory breakdown
redis-cli --memkeys

# Sample output:
# Sampled 10000 keys in the keyspace!
# Total key length: 450000 bytes
# Total value length: 2500000 bytes

# Top key prefixes by memory
redis-cli --bigkeys

# Memory usage by key pattern
redis-cli --scan --pattern "policy:*" | wc -l
redis-cli --scan --pattern "session:*" | wc -l
```

**Python Script for Memory Analysis**:
```python
def analyze_memory():
    """Analyze Valkey memory usage by key pattern."""
    info = redis_client.info("memory")

    print(f"Used Memory: {info['used_memory_human']}")
    print(f"Peak Memory: {info['used_memory_peak_human']}")
    print(f"Memory Fragmentation: {info['mem_fragmentation_ratio']}")

    # Count keys by pattern
    patterns = ["session:*", "policy:*", "ratelimit:*", "siem:*"]

    for pattern in patterns:
        cursor = 0
        count = 0
        total_size = 0

        while True:
            cursor, keys = redis_client.scan(cursor, match=pattern, count=1000)
            count += len(keys)

            # Sample memory for first 100 keys
            for key in keys[:100]:
                total_size += redis_client.memory_usage(key) or 0

            if cursor == 0:
                break

        avg_size = total_size / min(count, 100) if count > 0 else 0
        estimated_total = avg_size * count

        print(f"\n{pattern}")
        print(f"  Keys: {count}")
        print(f"  Avg Size: {avg_size:.0f} bytes")
        print(f"  Estimated Total: {estimated_total / 1024 / 1024:.2f} MB")

# Run analysis
analyze_memory()
```

---

## Persistence Configuration

### Persistence Strategies

**1. No Persistence (Pure Cache)** - Recommended for SARK
```conf
# Disable RDB
save ""

# Disable AOF
appendonly no
```
**Pros**: Maximum performance, no disk I/O
**Cons**: Data lost on restart (acceptable for cache)

**2. RDB Snapshots** (Background saves)
```conf
# Save after 900s if >= 1 key changed
save 900 1

# Save after 300s if >= 10 keys changed
save 300 10

# Save after 60s if >= 10000 keys changed
save 60 10000

# Compress RDB files
rdbcompression yes

# Checksum RDB files
rdbchecksum yes

# RDB filename
dbfilename dump.rdb
```
**Pros**: Point-in-time snapshots, low overhead
**Cons**: Potential data loss (up to save interval)

**3. AOF (Append-Only File)** - Most durable
```conf
# Enable AOF
appendonly yes

# AOF filename
appendfilename "appendonly.aof"

# Fsync strategy
# - always: Fsync after every write (slowest, most durable)
# - everysec: Fsync every second (good balance)
# - no: Let OS decide when to fsync (fastest, least durable)
appendfsync everysec

# Rewrite AOF when it grows 100% and is at least 64 MB
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
```
**Pros**: Maximum durability, every write persisted
**Cons**: Higher disk I/O, larger files

### Recommended Configuration for SARK

Since SARK uses Valkey primarily for caching (sessions, policy decisions, rate limits), **no persistence** is recommended for optimal performance. Data can be rebuilt on restart:

- **Sessions**: Users re-authenticate
- **Policy Cache**: Rebuilds on first evaluation
- **Rate Limits**: Reset on restart (acceptable)
- **SIEM Queue**: Use persistent queue if durability needed

If persistence is required (e.g., for SIEM queue), use **AOF with everysec fsync**:
```conf
appendonly yes
appendfsync everysec
```

---

## Performance Tuning

### Valkey Server Configuration

```conf
# ===========================
# Network Optimization
# ===========================

# TCP backlog (increase for high connection rates)
tcp-backlog 511

# Disable TCP_NODELAY for better throughput (enable for low latency)
# tcp-nodelay no

# ===========================
# Threading (Valkey 6+)
# ===========================

# I/O threads (for handling network I/O)
# Set to number of CPU cores (max 8)
io-threads 4
io-threads-do-reads yes

# ===========================
# Memory Optimization
# ===========================

# Actively defragment memory
activedefrag yes
active-defrag-threshold-lower 10
active-defrag-threshold-upper 100

# ===========================
# Client Output Buffer Limits
# ===========================

# client-output-buffer-limit <class> <hard limit> <soft limit> <soft seconds>
client-output-buffer-limit normal 0 0 0
client-output-buffer-limit replica 256mb 64mb 60
client-output-buffer-limit pubsub 32mb 8mb 60

# ===========================
# Slow Log
# ===========================

# Log queries slower than 10ms
slowlog-log-slower-than 10000

# Keep last 128 slow queries
slowlog-max-len 128
```

### Pipeline Commands

**Use Pipelining for Bulk Operations**:
```python
# ✗ Bad: Individual commands (multiple round trips)
for i in range(1000):
    redis_client.set(f"key:{i}", f"value:{i}")

# ✓ Good: Pipeline (single round trip)
pipe = redis_client.pipeline()
for i in range(1000):
    pipe.set(f"key:{i}", f"value:{i}")
pipe.execute()

# Example: Batch invalidate cache
def invalidate_keys_batch(keys: list[str]):
    """Delete keys in batches using pipeline."""
    batch_size = 1000

    for i in range(0, len(keys), batch_size):
        batch = keys[i:i+batch_size]
        pipe = redis_client.pipeline()
        for key in batch:
            pipe.delete(key)
        pipe.execute()
```

### Use Lua Scripts

**Atomic Operations with Lua**:
```python
# Rate limiting with Lua (atomic increment + TTL)
rate_limit_script = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])

local current = redis.call('GET', key)
if current and tonumber(current) >= limit then
    return 0  -- Rate limit exceeded
end

redis.call('INCR', key)
redis.call('EXPIRE', key, window)
return 1  -- Request allowed
"""

rate_limit_sha = redis_client.script_load(rate_limit_script)

def check_rate_limit(user_id: str, limit: int = 1000, window: int = 60) -> bool:
    """Check rate limit using Lua script."""
    key = f"ratelimit:user:{user_id}"
    result = redis_client.evalsha(rate_limit_sha, 1, key, limit, window)
    return result == 1

# Usage
if check_rate_limit("user-123", limit=1000, window=60):
    # Process request
    pass
else:
    # Return 429 Too Many Requests
    raise RateLimitExceeded()
```

### Optimize Data Structures

```python
# Use Hashes for objects (more memory efficient)
# ✗ Bad: Multiple keys
redis_client.set(f"user:{user_id}:name", "John Doe")
redis_client.set(f"user:{user_id}:email", "john@example.com")
redis_client.set(f"user:{user_id}:role", "admin")

# ✓ Good: Single Hash
redis_client.hset(f"user:{user_id}", mapping={
    "name": "John Doe",
    "email": "john@example.com",
    "role": "admin"
})

# Use Sets for unique collections
redis_client.sadd(f"user:{user_id}:roles", "admin", "developer")

# Use Sorted Sets for rankings
redis_client.zadd("leaderboard", {"user-1": 100, "user-2": 200})
```

---

## High Availability

### Valkey Sentinel (Recommended for Production)

**Architecture**:
```
┌─────────────────────────────────────────────────────────────────┐
│                     Valkey Sentinel Architecture                  │
└─────────────────────────────────────────────────────────────────┘

                      ┌──────────────┐
                      │  Sentinel 1  │
                      │  (Monitor)   │
                      └──────┬───────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────▼────┐         ┌────▼────┐        ┌────▼────┐
    │Sentinel │         │Sentinel │        │Sentinel │
    │    2    │         │    3    │        │  (Quorum)
    └────┬────┘         └────┬────┘        └─────────┘
         │                   │
         └────────┬──────────┘
                  │
         ┌────────▼─────────┐
         │   Valkey Master   │
         │   (Read/Write)   │
         └────────┬─────────┘
                  │
         ┌────────┴─────────┐
         │                  │
    ┌────▼────┐        ┌────▼────┐
    │ Replica │        │ Replica │
    │   1     │        │   2     │
    │(Read-only)       │(Read-only)
    └─────────┘        └─────────┘
```

**Sentinel Configuration** (`sentinel.conf`):
```conf
# Sentinel port
port 26379

# Monitor master
sentinel monitor mymaster redis-master 6379 2

# Auth password
sentinel auth-pass mymaster your-password-here

# Down after 5 seconds
sentinel down-after-milliseconds mymaster 5000

# Failover timeout (3 minutes)
sentinel failover-timeout mymaster 180000

# Parallel syncs during failover
sentinel parallel-syncs mymaster 1
```

**Docker Compose with Sentinel**:
```yaml
services:
  redis-master:
    image: valkey:7-alpine
    command: redis-server --requirepass password --masterauth password
    ports:
      - "6379:6379"

  redis-replica-1:
    image: valkey:7-alpine
    command: redis-server --replicaof redis-master 6379 --requirepass password --masterauth password
    depends_on:
      - redis-master

  redis-replica-2:
    image: valkey:7-alpine
    command: redis-server --replicaof redis-master 6379 --requirepass password --masterauth password
    depends_on:
      - redis-master

  sentinel-1:
    image: valkey:7-alpine
    command: redis-sentinel /etc/sentinel.conf
    volumes:
      - ./sentinel.conf:/etc/sentinel.conf
    depends_on:
      - redis-master

  sentinel-2:
    image: valkey:7-alpine
    command: redis-sentinel /etc/sentinel.conf
    volumes:
      - ./sentinel.conf:/etc/sentinel.conf
    depends_on:
      - redis-master

  sentinel-3:
    image: valkey:7-alpine
    command: redis-sentinel /etc/sentinel.conf
    volumes:
      - ./sentinel.conf:/etc/sentinel.conf
    depends_on:
      - redis-master
```

**Application Configuration with Sentinel**:
```python
from redis.sentinel import Sentinel

# Sentinel hosts
sentinel_hosts = [
    ("sentinel-1", 26379),
    ("sentinel-2", 26379),
    ("sentinel-3", 26379)
]

# Create Sentinel instance
sentinel = Sentinel(
    sentinel_hosts,
    socket_timeout=2,
    password="password"
)

# Get master (for writes)
master = sentinel.master_for(
    "mymaster",
    socket_timeout=5,
    password="password"
)

# Get replica (for reads)
replica = sentinel.slave_for(
    "mymaster",
    socket_timeout=5,
    password="password"
)

# Usage
master.set("key", "value")  # Write to master
value = replica.get("key")   # Read from replica
```

---

## Monitoring and Metrics

### Key Metrics to Monitor

```bash
# General info
redis-cli INFO

# Memory stats
redis-cli INFO memory

# Clients
redis-cli INFO clients

# Stats
redis-cli INFO stats

# Replication (if using replicas)
redis-cli INFO replication
```

### Important Metrics

| Metric | Command | Target | Alert Threshold |
|--------|---------|--------|-----------------|
| **Used Memory** | `INFO memory → used_memory_human` | < 70% | > 90% |
| **Memory Fragmentation** | `INFO memory → mem_fragmentation_ratio` | 1.0-1.5 | > 2.0 or < 1.0 |
| **Connected Clients** | `INFO clients → connected_clients` | < 80% maxclients | > 90% maxclients |
| **Keyspace Hits/Misses** | `INFO stats → keyspace_hits/misses` | Hit ratio > 90% | < 80% |
| **Evicted Keys** | `INFO stats → evicted_keys` | Low | > 1000/s |
| **Expired Keys** | `INFO stats → expired_keys` | Expected | High rate unexpected |
| **Ops/sec** | `INFO stats → instantaneous_ops_per_sec` | Baseline | 10× baseline |

### Cache Hit Ratio

```bash
# Calculate cache hit ratio
redis-cli INFO stats | grep keyspace

# Output:
# keyspace_hits:1000000
# keyspace_misses:50000

# Hit ratio = hits / (hits + misses)
# 1000000 / (1000000 + 50000) = 95.2%
```

**Python Monitoring Script**:
```python
def get_cache_stats():
    """Get Valkey cache statistics."""
    info = redis_client.info("stats")

    hits = info["keyspace_hits"]
    misses = info["keyspace_misses"]
    total = hits + misses

    hit_ratio = (hits / total * 100) if total > 0 else 0

    print(f"Cache Hits: {hits:,}")
    print(f"Cache Misses: {misses:,}")
    print(f"Hit Ratio: {hit_ratio:.2f}%")

    # Evictions
    evicted = info.get("evicted_keys", 0)
    print(f"Evicted Keys: {evicted:,}")

    return {
        "hits": hits,
        "misses": misses,
        "hit_ratio": hit_ratio,
        "evicted": evicted
    }
```

### Prometheus Metrics

**Valkey Exporter** (`docker-compose.yml`):
```yaml
redis-exporter:
  image: oliver006/redis_exporter:latest
  environment:
    VALKEY_ADDR: "valkey:6379"
    VALKEY_PASSWORD: "${VALKEY_PASSWORD}"
  ports:
    - "9121:9121"
```

**Key Prometheus Queries**:
```promql
# Memory usage percent
100 * redis_memory_used_bytes / redis_memory_max_bytes

# Cache hit ratio
100 * rate(redis_keyspace_hits_total[5m]) / (rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m]))

# Connected clients
redis_connected_clients

# Commands per second
rate(redis_commands_processed_total[1m])

# Evictions per second
rate(redis_evicted_keys_total[5m])
```

**Grafana Dashboard**: Use dashboard ID 11835 (Valkey Dashboard for Prometheus Valkey Exporter)

---

## Troubleshooting

### Common Issues

#### 1. High Memory Usage

**Symptoms**: Used memory approaching maxmemory limit

**Diagnosis**:
```bash
# Check memory
redis-cli INFO memory

# Find large keys
redis-cli --bigkeys

# Sample keys
redis-cli --scan --pattern "*" | head -100
```

**Solutions**:
- Reduce TTL for cached data
- Enable eviction policy (allkeys-lru)
- Increase maxmemory limit
- Compress large values
- Remove unused keys

#### 2. Low Cache Hit Ratio

**Symptoms**: Hit ratio < 80%

**Diagnosis**:
```bash
# Check hit ratio
redis-cli INFO stats | grep keyspace
```

**Solutions**:
- Increase cache TTL
- Pre-warm cache on startup
- Review cache key design
- Increase maxmemory (prevent premature evictions)

#### 3. Connection Pool Exhaustion

**Symptoms**: Connection timeout errors

**Diagnosis**:
```python
# Check pool stats
print(f"Pool utilization: {pool_utilization}%")
print(f"In-use connections: {in_use_connections}")
```

**Solutions**:
- Increase pool size
- Check for connection leaks
- Ensure connections are returned to pool
- Use connection health checks

#### 4. Slow Commands

**Symptoms**: High latency

**Diagnosis**:
```bash
# Check slow log
redis-cli SLOWLOG GET 10

# Monitor commands in real-time
redis-cli MONITOR
```

**Solutions**:
- Avoid KEYS command (use SCAN)
- Use pipelining for bulk operations
- Optimize Lua scripts
- Enable I/O threading

---

## Best Practices

### Development Best Practices

1. **Always set TTL** on cached data
2. **Use connection pooling** (never create new connection per request)
3. **Use pipelining** for bulk operations
4. **Use Lua scripts** for atomic multi-step operations
5. **Design cache keys** for easy invalidation
6. **Handle cache failures gracefully** (fallback to source)
7. **Monitor cache hit ratio** and optimize TTL accordingly

### Production Best Practices

1. **Use Valkey Sentinel** for high availability
2. **Set maxmemory** and eviction policy
3. **Disable persistence** for pure cache (better performance)
4. **Enable I/O threading** for high concurrency
5. **Monitor memory usage** and set alerts
6. **Use read replicas** for read-heavy workloads
7. **Secure with password** and network isolation
8. **Regularly review slow log** and optimize
9. **Test failover** scenarios
10. **Document cache invalidation** strategy

---

## Summary

This guide covers comprehensive Valkey optimization for SARK:

- **Connection Pooling**: Proper pool sizing, health checks, Sentinel support
- **Cache Optimization**: Smart TTL strategy, efficient invalidation, cache warming
- **Memory Management**: Eviction policies, data structure optimization, memory monitoring
- **Performance Tuning**: Pipelining, Lua scripts, I/O threading
- **High Availability**: Valkey Sentinel for automatic failover
- **Monitoring**: Key metrics, Prometheus integration, troubleshooting

Following these practices ensures SARK's Valkey cache performs optimally with high availability and minimal latency.
