# SARK Gateway Integration - Troubleshooting Resources

**Complete troubleshooting documentation for SARK Gateway Integration**

---

## 📚 Available Resources

### 1. **[TROUBLESHOOTING_GUIDE.md](./TROUBLESHOOTING_GUIDE.md)** (1,828 lines)
**Your go-to resource for diagnosing and fixing issues**

- ✅ Symptom-based troubleshooting decision tree
- ✅ 30+ common error messages with detailed solutions
- ✅ Debug mode and logging instructions
- ✅ Common misconfigurations (auth, network, policies)
- ✅ Diagnostic commands with expected outputs
- ✅ When to file a bug report

**Use this when:**
- Something isn't working and you need to diagnose the issue
- You see an error message and need to understand what it means
- You need step-by-step resolution procedures

**Quick start:**
```bash
# Health check
curl http://localhost:8000/health/detailed | jq

# Test authorization
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"action": "gateway:tool:invoke", "server_name": "test", "tool_name": "test"}'
```

---

### 2. **[FAQ.md](./FAQ.md)** (1,748 lines)
**56+ frequently asked questions organized by category**

**Categories:**
- 🔧 **Setup & Installation** (11 questions) - Getting started
- 💻 **Usage & Operations** (10 questions) - Day-to-day operations
- 🔐 **Policies & Authorization** (10 questions) - Policy management
- ⚡ **Performance & Scaling** (9 questions) - Optimization
- 🔒 **Security & Authentication** (10 questions) - Security best practices
- 🔗 **Integration & Compatibility** (3 questions) - Integration scenarios
- 🐛 **Troubleshooting & Debugging** (3 questions) - Debug techniques

**Use this when:**
- You have a "How do I..." question
- You want to understand how something works
- You're looking for best practices
- You need code examples

**Popular questions:**
- Q1: How do I enable Gateway integration?
- Q12: How do I authorize a Gateway request?
- Q22: How do I write a custom authorization policy?
- Q32: What is the expected latency?
- Q41: How are API keys secured?

---

### 3. **[ERROR_REFERENCE.md](./ERROR_REFERENCE.md)** (1,644 lines)
**Complete error code catalog with resolution procedures**

**Error Categories:**
- 🌐 **HTTP Status Codes** (400, 401, 403, 404, 408, 429, 500, 502, 503, 504)
- 🔌 **Gateway Integration Errors** (GW-001 to GW-405)
- 🔐 **Authorization Errors** (AZ-001 to AZ-011)
- 📋 **OPA Policy Errors** (OPA-001 to OPA-004)
- 🔗 **Connection Errors** (CN-001, CN-002, CN-408)
- ⚙️ **Configuration Errors** (CF-001)
- 🔑 **Authentication Errors** (AU-001 to AU-003)
- ⏱️ **Rate Limiting Errors** (RL-001)
- 💾 **Database Errors** (DB-001)
- 📦 **Cache Errors** (CA-001)

**Error format:**
```json
{
  "error": {
    "code": "GW-001",
    "message": "Gateway integration is not enabled",
    "detail": "The GATEWAY_ENABLED configuration flag is set to false",
    "suggestions": ["Set GATEWAY_ENABLED=true", "Restart SARK", "Verify with /api/v1/version"]
  }
}
```

**Use this when:**
- You receive an error code and need to understand it
- You need step-by-step resolution for a specific error
- You want to understand the root cause of an error
- You need prevention tips

---

### 4. **[PERFORMANCE_TUNING.md](./PERFORMANCE_TUNING.md)** (1,295 lines)
**Comprehensive performance optimization guide**

**Topics covered:**
- 📊 **Bottleneck Identification** - Find what's slowing you down
- ⚙️ **Configuration Tuning** - Connection pools, timeouts, workers
- 🚀 **Caching Strategies** - Redis optimization, multi-layer caching
- 💾 **Database Optimization** - Indexing, partitioning, connection pooling
- 📋 **OPA Performance** - Policy optimization, profiling
- 💻 **Resource Sizing** - CPU, memory, storage recommendations
- 🌐 **Network Optimization** - Keep-alive, compression, pooling
- 🧪 **Load Testing** - k6 scripts, stress testing, benchmarks

**Performance targets:**

| Metric | Target | Acceptable | Poor |
|--------|--------|------------|------|
| P95 Latency | <50ms | <100ms | >100ms |
| Throughput | >500 RPS | >200 RPS | <200 RPS |
| Cache Hit Rate | >90% | >75% | <75% |
| Error Rate | <0.1% | <1% | >1% |

**Use this when:**
- Performance is slower than expected
- You need to scale for higher traffic
- You want to optimize resource usage
- You're preparing for production deployment

**Quick wins:**
1. Enable async audit logging → 44% latency reduction
2. Configure PgBouncer → 40% DB CPU reduction
3. Tune Redis cache TTL → 95% cache hit rate
4. Optimize OPA policies → 3x faster evaluation

---

## 🎯 Quick Navigation

### By Problem Type

| Problem | Resource | Section |
|---------|----------|---------|
| **Can't enable Gateway integration** | TROUBLESHOOTING_GUIDE.md | Common Error Messages → GW-001 |
| **Authorization requests denied** | FAQ.md | Q18: How do I debug denied requests? |
| **Slow performance** | PERFORMANCE_TUNING.md | Bottleneck Identification |
| **Error code received** | ERROR_REFERENCE.md | Find your error code |
| **Policy not working** | FAQ.md | Q22: How do I write custom policies? |
| **Connection issues** | TROUBLESHOOTING_GUIDE.md | Symptom-Based Troubleshooting |
| **High latency** | PERFORMANCE_TUNING.md | Configuration Tuning |
| **Setup questions** | FAQ.md | Setup & Installation |

---

### By User Role

**👨‍💻 Developers:**
1. Start with **FAQ.md** for common development questions
2. Use **TROUBLESHOOTING_GUIDE.md** when something breaks
3. Reference **ERROR_REFERENCE.md** for error details

**🔧 Operations Engineers:**
1. Start with **PERFORMANCE_TUNING.md** for optimization
2. Use **TROUBLESHOOTING_GUIDE.md** for operational issues
3. Keep **ERROR_REFERENCE.md** handy for incident response

**👔 System Administrators:**
1. Read **FAQ.md** Setup & Installation section first
2. Follow **TROUBLESHOOTING_GUIDE.md** for deployment issues
3. Use **PERFORMANCE_TUNING.md** for capacity planning

**🎯 Support Engineers:**
1. Use **ERROR_REFERENCE.md** for error code lookup
2. Reference **TROUBLESHOOTING_GUIDE.md** for resolution steps
3. Check **FAQ.md** for common user questions

---

## 🚀 Getting Started Checklist

### First-Time Setup

- [ ] Read **FAQ.md** → Q1: How do I enable Gateway integration?
- [ ] Follow setup instructions in FAQ
- [ ] Verify with health check from TROUBLESHOOTING_GUIDE.md
- [ ] Test authorization endpoint
- [ ] Review **PERFORMANCE_TUNING.md** → Resource Sizing for your environment

### Before Production

- [ ] Complete **PERFORMANCE_TUNING.md** → Tuning Checklist
- [ ] Run load tests (scripts in PERFORMANCE_TUNING.md)
- [ ] Set up monitoring (TROUBLESHOOTING_GUIDE.md → Monitoring section)
- [ ] Document your configuration
- [ ] Train team on **ERROR_REFERENCE.md** error codes
- [ ] Establish on-call runbook using these resources

### Regular Maintenance

- [ ] Monitor metrics (PERFORMANCE_TUNING.md → Dashboard)
- [ ] Review audit logs weekly
- [ ] Check for common errors (ERROR_REFERENCE.md)
- [ ] Optimize policies quarterly (FAQ.md → Q29: Test policies)
- [ ] Update documentation as you learn

---

## 📊 Resource Statistics

| Document | Lines | Words | Topics Covered |
|----------|-------|-------|----------------|
| **TROUBLESHOOTING_GUIDE.md** | 1,828 | ~15,000 | Troubleshooting, errors, diagnostics |
| **FAQ.md** | 1,748 | ~14,000 | 56 questions across 7 categories |
| **ERROR_REFERENCE.md** | 1,644 | ~12,000 | 40+ error codes with solutions |
| **PERFORMANCE_TUNING.md** | 1,295 | ~10,000 | Performance optimization, benchmarks |
| **TOTAL** | **6,515** | **~51,000** | Comprehensive coverage |

---

## 🔍 Search Tips

### Finding Information Quickly

**1. Use your editor's search (Ctrl+F / Cmd+F):**
```
# Search for error codes
GW-001, AZ-001, OPA-001

# Search for symptoms
"connection failed", "timeout", "denied"

# Search for topics
"cache", "performance", "policy", "authorization"
```

**2. Use grep on command line:**
```bash
# Find all mentions of caching
grep -r "cache" docs/troubleshooting/gateway/

# Find specific error code
grep -n "GW-001" docs/troubleshooting/gateway/ERROR_REFERENCE.md

# Find performance benchmarks
grep -A 5 "benchmark" docs/troubleshooting/gateway/PERFORMANCE_TUNING.md
```

**3. Use table of contents:**
Each document has a detailed table of contents at the top for quick navigation.

---

## 🆘 Getting Help

### When Documentation Isn't Enough

**1. Check these resources first:**
- ✅ TROUBLESHOOTING_GUIDE.md for your specific issue
- ✅ ERROR_REFERENCE.md for error code details
- ✅ FAQ.md for common questions

**2. Enable debug mode:**
```bash
export LOG_LEVEL=DEBUG
docker compose -f docker-compose.gateway.yml restart sark
```

**3. Collect diagnostic information:**
- Error messages with request IDs
- Logs from last 100 lines
- Health check output
- Configuration (sanitized)

**4. Contact support:**
- GitHub Issues: https://github.com/your-org/sark/issues
- Email: support@example.com
- Slack: #sark-support

**Bug report template:** See TROUBLESHOOTING_GUIDE.md → When to File a Bug Report

---

## 📚 Related Documentation

**Integration & Architecture:**
- [MCP_GATEWAY_INTEGRATION_PLAN.md](../../MCP_GATEWAY_INTEGRATION_PLAN.md) - Integration architecture
- [ARCHITECTURE.md](../../ARCHITECTURE.md) - Overall SARK architecture

**Operations:**
- [OPERATIONS_RUNBOOK.md](../../OPERATIONS_RUNBOOK.md) - Operational procedures
- [MONITORING.md](../../MONITORING.md) - Monitoring and observability
- [INCIDENT_RESPONSE.md](../../INCIDENT_RESPONSE.md) - Incident handling

**Security:**
- [SECURITY_BEST_PRACTICES.md](../../SECURITY_BEST_PRACTICES.md) - Security guidelines
- [SECURITY_HARDENING.md](../../SECURITY_HARDENING.md) - Hardening guide
- [POLICY_AUDIT_TRAIL.md](../../POLICY_AUDIT_TRAIL.md) - Audit logging

**Development:**
- [ADVANCED_OPA_POLICIES.md](../../ADVANCED_OPA_POLICIES.md) - Policy development
- [API_REFERENCE.md](../../API_REFERENCE.md) - API documentation
- [TESTING_STRATEGY.md](../../TESTING_STRATEGY.md) - Testing approaches

---

## 📝 Document Maintenance

**Last Updated:** November 2025  
**Version:** 1.1.0  
**Next Review:** December 2025

**Contributing:**
- Found an error? Open an issue
- Have a suggestion? Submit a PR
- New FAQ? Add to FAQ.md
- Performance tip? Add to PERFORMANCE_TUNING.md

**Feedback:** documentation@example.com

---

## ⭐ Quick Reference Card

### Common Commands

```bash
# Health check
curl http://localhost:8000/health/detailed | jq

# Test authorization
curl -X POST http://localhost:8000/api/v1/gateway/authorize \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"action": "gateway:tool:invoke", "server_name": "test", "tool_name": "test"}'

# Check logs
docker logs sark --tail=100 --follow

# Enable debug mode
export LOG_LEVEL=DEBUG
docker compose restart sark

# Test Gateway connectivity
curl http://gateway:8080/health

# Clear cache
curl -X POST http://localhost:8000/api/v1/cache/invalidate
```

### Common Error Codes

- **GW-001**: Gateway integration not enabled → Enable in .env
- **AZ-001**: Authorization denied → Check user permissions
- **CN-001**: Connection failed → Check Gateway health
- **AU-001**: Missing auth token → Add Authorization header
- **OPA-001**: OPA unavailable → Check OPA service

### Performance Targets

- **P95 Latency**: <50ms (target), <100ms (acceptable)
- **Throughput**: >500 RPS per instance
- **Cache Hit Rate**: >90%
- **Error Rate**: <0.1%

---

**💡 Pro Tip:** Bookmark this README for quick access to all troubleshooting resources!
