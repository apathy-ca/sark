## Policy Decision Caching

SARK implements Redis-based caching for OPA policy decisions to improve performance and reduce load on the OPA server.

### Overview

Policy evaluations can be expensive operations, especially under high load. The caching layer:

- **Reduces latency**: Cache hits return decisions in <5ms vs 50ms+ for OPA queries
- **Reduces load**: Prevents unnecessary OPA evaluations for identical requests
- **Improves scalability**: Handles higher request volumes without scaling OPA
- **Maintains security**: Intelligent TTL based on sensitivity levels

### Architecture

```
┌─────────────┐
│   Request   │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│   OPA Client    │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐     Cache Hit (< 5ms)
│  Policy Cache   │───────────────────────▶ Return Decision
│     (Redis)     │
└──────┬──────────┘
       │ Cache Miss
       ▼
┌─────────────────┐
│   OPA Server    │  (50ms+)
│  (Evaluation)   │
└──────┬──────────┘
       │
       ▼
   Cache Result
```

### Cache Key Format

Cache keys are generated using a consistent format:

```
policy:decision:{user_id}:{action}:{resource}:{context_hash}
```

**Example:**
```
policy:decision:user-123:tool:invoke:tool_delete_user:a3f2c1d4e5b6
```

**Context Hashing:**
- Context objects are JSON-serialized and hashed (SHA-256)
- First 16 characters of hash used for key
- Ensures identical contexts produce identical keys
- Sorted keys ensure consistent ordering

### TTL Configuration

Cache TTL varies based on sensitivity level:

| Sensitivity Level | TTL | Rationale |
|-------------------|-----|-----------|
| **LOW** | 300s (5 min) | Safe to cache longer |
| **MEDIUM** | 180s (3 min) | Moderate caching |
| **HIGH** | 60s (1 min) | Shorter TTL for sensitive ops |
| **CRITICAL** | 30s (30 sec) | Minimal caching for critical ops |
| **Default** | 120s (2 min) | Fallback for unclassified |

### Usage

#### Basic Usage

```python
from sark.services.policy import OPAClient, get_policy_cache

# Create OPA client with caching (enabled by default)
opa_client = OPAClient()

# Evaluate policy (uses cache automatically)
decision = await opa_client.evaluate_policy(auth_input)
```

#### Disable Caching

```python
# Disable caching entirely
opa_client = OPAClient(cache_enabled=False)

# Or bypass cache for specific request
decision = await opa_client.evaluate_policy(auth_input, use_cache=False)
```

#### Custom Cache Configuration

```python
from sark.services.policy import PolicyCache, OPAClient

# Create cache with custom TTL
cache = PolicyCache(ttl_seconds=600)  # 10 minutes

# Use custom cache
opa_client = OPAClient(cache=cache)
```

### Cache Invalidation

#### Invalidate All

```python
# Invalidate all cached decisions
deleted = await opa_client.invalidate_cache()
print(f"Invalidated {deleted} cache entries")
```

#### Invalidate by User

```python
# Invalidate all decisions for a specific user
deleted = await opa_client.invalidate_cache(user_id="user-123")
```

#### Invalidate by Action

```python
# Invalidate specific user + action combination
deleted = await opa_client.invalidate_cache(
    user_id="user-123",
    action="tool:invoke"
)
```

#### Invalidate by Pattern

```python
# Custom pattern invalidation
cache = get_policy_cache()
deleted = await cache.invalidate_pattern("policy:decision:user-123:*")
```

#### When to Invalidate

Invalidate cache when:
- **User permissions change**: Role updates, team assignments
- **Policy updates**: New policy versions deployed
- **Security events**: Suspicious activity detected
- **Tool/server updates**: Sensitivity level changes
- **Manual override**: Admin intervention required

### Cache Metrics

#### Get Metrics

```python
metrics = opa_client.get_cache_metrics()

print(f"Cache hits: {metrics['hits']}")
print(f"Cache misses: {metrics['misses']}")
print(f"Hit rate: {metrics['hit_rate']}%")
print(f"Avg cache latency: {metrics['avg_cache_latency_ms']}ms")
print(f"Avg OPA latency: {metrics['avg_opa_latency_ms']}ms")
```

**Sample Output:**
```json
{
  "hits": 850,
  "misses": 150,
  "total_requests": 1000,
  "hit_rate": 85.0,
  "miss_rate": 15.0,
  "avg_cache_latency_ms": 2.3,
  "avg_opa_latency_ms": 45.7
}
```

#### Prometheus Metrics

Cache metrics are exposed for Prometheus:

```
# HELP sark_policy_cache_hits_total Total cache hits
# TYPE sark_policy_cache_hits_total counter
sark_policy_cache_hits_total 850

# HELP sark_policy_cache_misses_total Total cache misses
# TYPE sark_policy_cache_misses_total counter
sark_policy_cache_misses_total 150

# HELP sark_policy_cache_hit_rate Cache hit rate percentage
# TYPE sark_policy_cache_hit_rate gauge
sark_policy_cache_hit_rate 85.0

# HELP sark_policy_cache_latency_ms Cache operation latency
# TYPE sark_policy_cache_latency_ms histogram
sark_policy_cache_latency_ms_bucket{le="5"} 1000
```

### Performance Characteristics

#### Latency

| Operation | Latency | Notes |
|-----------|---------|-------|
| Cache Hit | < 5ms | Redis GET operation |
| Cache Miss + OPA | 50-100ms | OPA evaluation + cache set |
| Cache Set | < 2ms | Redis SETEX operation |
| Invalidation | 10-50ms | Depends on key count |

#### Throughput

- **Cache hit throughput**: 10,000+ req/s
- **Cache miss throughput**: Limited by OPA (100-200 req/s)
- **Target hit rate**: 80%+

#### Memory Usage

**Per Cache Entry:**
- Key: ~100 bytes
- Value: ~200-500 bytes (decision JSON)
- Total: ~300-600 bytes per entry

**Example:**
- 10,000 cached decisions ≈ 5 MB
- 100,000 cached decisions ≈ 50 MB

### Configuration

#### Environment Variables

```bash
# Redis connection
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=secret
REDIS_DB=0
REDIS_POOL_SIZE=50

# OPA
OPA_URL=http://localhost:8181
OPA_TIMEOUT_SECONDS=1.0
```

#### Application Settings

```python
from sark.config import Settings

settings = Settings(
    redis_host="localhost",
    redis_port=6379,
    opa_url="http://opa:8181",
)
```

### Health Checks

#### Check Cache Health

```python
health = await opa_client.health_check()

print(f"OPA healthy: {health['opa']}")
print(f"Cache healthy: {health['cache']}")
print(f"Overall: {health['overall']}")
```

#### Health Endpoint

```http
GET /health/policy

Response:
{
  "opa": true,
  "cache": true,
  "overall": true,
  "metrics": {
    "hit_rate": 85.0,
    "cache_size": 1250
  }
}
```

### Best Practices

#### 1. Monitor Hit Rate

- **Target**: 80%+ hit rate
- **Action**: If <70%, investigate request patterns
- **Tools**: Prometheus metrics, cache statistics

#### 2. Appropriate TTL

```python
# DON'T: Cache critical decisions too long
cache = PolicyCache(ttl_seconds=3600)  # ❌ Too long for critical

# DO: Use sensitivity-aware TTL (automatic)
opa_client = OPAClient()  # ✅ Automatic TTL based on sensitivity
```

#### 3. Invalidate on Changes

```python
# When user role changes
await opa_client.invalidate_cache(user_id="user-123")

# When policy updates
await opa_client.invalidate_cache()  # Clear all
```

#### 4. Handle Cache Failures Gracefully

Cache failures automatically fall back to OPA:

```python
# If Redis is down, requests still work (slower)
decision = await opa_client.evaluate_policy(auth_input)
# ✅ Works even if cache unavailable
```

#### 5. Use Cache Warming

Pre-populate cache for common requests:

```python
# Warm cache for frequent users/actions
for user_id in frequent_users:
    auth_input = AuthorizationInput(...)
    await opa_client.evaluate_policy(auth_input)
```

### Security Considerations

#### 1. Cache Poisoning Prevention

- **Input validation**: All inputs validated before caching
- **Consistent hashing**: Context hashing prevents manipulation
- **TTL limits**: Maximum TTL enforced

#### 2. Sensitive Data

- **No PII in keys**: User IDs hashed, no emails/names
- **Decision data**: Only allow/deny decisions cached
- **Audit trails**: Separate from cache

#### 3. Cache Isolation

- **Namespace isolation**: "policy:decision:" prefix
- **Database separation**: Dedicated Redis DB
- **ACL controls**: Redis ACLs for access control

### Monitoring & Alerting

#### Key Metrics to Monitor

1. **Hit Rate**
   - Alert if < 70%
   - Investigate request patterns

2. **Latency**
   - Cache hit latency > 10ms: Redis performance issue
   - OPA latency > 100ms: OPA scaling needed

3. **Error Rate**
   - Cache errors > 1%: Redis connectivity issues
   - OPA errors > 0.1%: Policy or OPA issues

4. **Cache Size**
   - Alert if > 100,000 entries
   - Consider TTL reduction

#### Sample Prometheus Alerts

```yaml
- alert: LowPolicyCacheHitRate
  expr: sark_policy_cache_hit_rate < 70
  for: 5m
  annotations:
    summary: "Policy cache hit rate below 70%"

- alert: HighPolicyCacheLatency
  expr: histogram_quantile(0.95, sark_policy_cache_latency_ms) > 10
  for: 2m
  annotations:
    summary: "95th percentile cache latency > 10ms"
```

### Troubleshooting

#### Low Hit Rate

**Symptoms**: Hit rate < 70%

**Causes:**
- Request patterns too diverse
- TTL too short
- Context variations

**Solutions:**
- Review request patterns
- Increase TTL for low sensitivity
- Normalize context data

#### High Latency

**Symptoms**: Cache hit latency > 10ms

**Causes:**
- Redis performance issues
- Network latency
- Large decision objects

**Solutions:**
- Check Redis performance
- Optimize network
- Review decision size

#### Cache Misses After Invalidation

**Symptoms**: Expected hits become misses

**Expected behavior** after:
- Policy updates
- Permission changes
- Manual invalidation

**No action needed** - cache will rebuild

### Advanced Usage

#### Custom Cache Implementation

```python
from sark.services.policy.cache import PolicyCache
import redis.asyncio as redis

# Custom Redis configuration
custom_redis = redis.Redis(
    host="redis.example.com",
    port=6379,
    ssl=True,
    ssl_cert_reqs="required",
)

cache = PolicyCache(
    redis_client=custom_redis,
    ttl_seconds=600,
)

opa_client = OPAClient(cache=cache)
```

#### Cache Metrics Export

```python
# Export metrics for external monitoring
metrics = opa_client.get_cache_metrics()

# Send to monitoring system
await monitoring.send_metrics({
    "service": "policy_cache",
    **metrics
})
```

#### Batch Invalidation

```python
# Invalidate multiple patterns
patterns = [
    f"policy:decision:{user_id}:*"
    for user_id in updated_users
]

for pattern in patterns:
    await cache.invalidate_pattern(pattern)
```

---

**Related Documentation:**
- [OPA Integration](OPA_POLICY_GUIDE.md)
- [Security Guide](SECURITY.md)
- [Performance Tuning](PERFORMANCE.md)
- [Tool Sensitivity Classification](TOOL_SENSITIVITY_CLASSIFICATION.md)
