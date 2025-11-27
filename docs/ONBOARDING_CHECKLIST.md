# SARK Onboarding Checklist

**Complete setup guide for new SARK deployments**

Use this checklist to ensure a successful SARK deployment from initial planning through production launch.

---

## Pre-Deployment Planning

### Phase 0: Assessment & Planning (Week 1)

- [ ] **Identify Stakeholders**
  - [ ] Security team lead assigned
  - [ ] DevOps/SRE team lead assigned
  - [ ] Development team representative assigned
  - [ ] Executive sponsor identified

- [ ] **Define Scope**
  - [ ] Inventory existing MCP servers (if any)
  - [ ] Identify teams that will use SARK
  - [ ] Estimate number of users (current and 6-month projection)
  - [ ] List sensitive data types to be governed

- [ ] **Technical Assessment**
  - [ ] Kubernetes cluster available (or provision plan)
  - [ ] PostgreSQL option selected (managed service vs self-hosted)
  - [ ] Redis option selected (managed service vs self-hosted)
  - [ ] Network architecture reviewed (VPC, subnets, firewall rules)
  - [ ] Authentication provider identified (OIDC/LDAP/SAML)

- [ ] **Resource Planning**
  - [ ] Infrastructure budget approved
  - [ ] Deployment timeline agreed upon
  - [ ] Training schedule planned
  - [ ] Support model defined

---

## Infrastructure Setup

### Phase 1: Core Infrastructure (Week 2)

- [ ] **Kubernetes Cluster**
  - [ ] Cluster provisioned (3+ nodes for HA)
  - [ ] kubectl access configured
  - [ ] Namespace created (`sark-system`)
  - [ ] Resource quotas set
  - [ ] Network policies configured

- [ ] **Database (PostgreSQL)**
  - [ ] PostgreSQL 15+ deployed
  - [ ] TimescaleDB extension installed
  - [ ] Database created (`sark`)
  - [ ] User credentials configured
  - [ ] Connection tested from cluster
  - [ ] Backup strategy configured
  - [ ] High availability configured (if required)

- [ ] **Cache (Redis)**
  - [ ] Redis 7+ deployed
  - [ ] Cluster mode configured (if using Redis Cluster)
  - [ ] Connection tested from cluster
  - [ ] Persistence configured
  - [ ] Memory limits set

- [ ] **Policy Engine (OPA)**
  - [ ] OPA 0.60+ deployed
  - [ ] Sidecar vs standalone decision made
  - [ ] Policy bundle loading configured
  - [ ] Health checks configured

- [ ] **Secrets Management**
  - [ ] Secrets backend selected (Kubernetes Secrets vs Vault)
  - [ ] Database credentials stored
  - [ ] Redis credentials stored
  - [ ] API keys stored (if using external services)
  - [ ] Encryption at rest enabled

---

## SARK Application Deployment

### Phase 2: Application Setup (Week 3)

- [ ] **Container Registry**
  - [ ] SARK Docker images pushed to registry
  - [ ] Image pull secrets configured
  - [ ] Tag/version strategy defined

- [ ] **Configuration**
  - [ ] ConfigMap created with app settings
  - [ ] Environment variables set
  - [ ] Feature flags configured
  - [ ] Log level set (INFO for production)

- [ ] **Deploy SARK API**
  - [ ] Deployment manifest applied
  - [ ] Service created (ClusterIP/LoadBalancer)
  - [ ] Health checks passing (`/health`, `/ready`)
  - [ ] Logs streaming correctly
  - [ ] Metrics endpoint accessible (`/metrics`)

- [ ] **Ingress/Load Balancer**
  - [ ] Ingress controller configured
  - [ ] TLS certificates installed
  - [ ] DNS records created
  - [ ] URL accessible externally (if required)

- [ ] **Database Migrations**
  - [ ] Migration job executed
  - [ ] Schema version verified
  - [ ] Initial data loaded (if any)

---

## Authentication & Authorization

### Phase 3: Identity & Access (Week 3-4)

- [ ] **Authentication Provider**
  - [ ] OIDC configured (if using)
    - [ ] Client ID and secret obtained
    - [ ] Redirect URLs registered
    - [ ] Scopes configured
    - [ ] Test user login successful
  - [ ] LDAP configured (if using)
    - [ ] LDAP server connection tested
    - [ ] Base DN configured
    - [ ] User search filter tested
    - [ ] Group lookup tested
    - [ ] TLS/SSL enabled
  - [ ] SAML configured (if using)
    - [ ] Service Provider metadata exported
    - [ ] Identity Provider metadata imported
    - [ ] Assertion Consumer Service (ACS) URL configured
    - [ ] Test login successful

- [ ] **User Management**
  - [ ] Admin user created
  - [ ] User roles defined (admin, developer, analyst, etc.)
  - [ ] Team structure mapped
  - [ ] Initial users imported/synced

- [ ] **API Key Management**
  - [ ] API key generation tested
  - [ ] Key scopes defined
  - [ ] Key rotation policy set
  - [ ] Test API key created

- [ ] **Session Management**
  - [ ] Session timeout configured
  - [ ] Concurrent session limits set
  - [ ] Session storage (Redis) verified

---

## Policy Configuration

### Phase 4: Authorization Policies (Week 4)

- [ ] **OPA Policy Setup**
  - [ ] Default policies loaded
    - [ ] RBAC policy active
    - [ ] Team access policy active
    - [ ] Sensitivity policy active
    - [ ] Time-based policy active (if needed)
    - [ ] IP filtering policy active (if needed)
    - [ ] MFA policy active (if needed)
  - [ ] Policy bundle versioning configured
  - [ ] Policy testing performed

- [ ] **Custom Policies** (if needed)
  - [ ] Organization-specific policies written
  - [ ] Policies tested in dev environment
  - [ ] Policies reviewed by security team
  - [ ] Policies deployed to OPA

- [ ] **Tool Sensitivity Classification**
  - [ ] Sensitivity levels defined (LOW/MEDIUM/HIGH/CRITICAL)
  - [ ] Auto-classification keywords configured
  - [ ] Test tools classified
  - [ ] Classification validation process established

---

## Monitoring & Observability

### Phase 5: Monitoring Setup (Week 4-5)

- [ ] **Metrics Collection**
  - [ ] Prometheus configured
  - [ ] SARK metrics scraped (`/metrics`)
  - [ ] PostgreSQL metrics collected
  - [ ] Redis metrics collected
  - [ ] OPA metrics collected

- [ ] **Dashboards**
  - [ ] Grafana installed
  - [ ] SARK overview dashboard imported
  - [ ] API performance dashboard created
  - [ ] Policy evaluation dashboard created
  - [ ] Audit activity dashboard created

- [ ] **Alerts**
  - [ ] API error rate alerts configured
  - [ ] Database connection alerts configured
  - [ ] Policy evaluation latency alerts configured
  - [ ] Disk space alerts configured
  - [ ] Pod restart alerts configured

- [ ] **Logging**
  - [ ] Log aggregation configured (ELK, Splunk, etc.)
  - [ ] Log retention policy set
  - [ ] Log search tested
  - [ ] Structured logging validated

- [ ] **SIEM Integration** (if required)
  - [ ] SIEM adapter configured (Splunk/Datadog/custom)
  - [ ] Audit events forwarding tested
  - [ ] Event schema validated
  - [ ] Batch size optimized
  - [ ] Retry logic tested

---

## MCP Server Integration

### Phase 6: Server Onboarding (Week 5+)

- [ ] **First MCP Server Registration**
  - [ ] Dev/staging server registered first
  - [ ] Server metadata complete (name, URL, team, tags)
  - [ ] Sensitivity level assigned
  - [ ] Health check endpoint verified
  - [ ] Tool list retrieved

- [ ] **Tool Testing**
  - [ ] Tool invocation through SARK tested
  - [ ] Policy evaluation verified
  - [ ] Audit logging confirmed
  - [ ] Error handling tested

- [ ] **Discovery Configuration**
  - [ ] Automated discovery enabled (if using)
  - [ ] Network scan ranges configured
  - [ ] Discovery schedule set
  - [ ] Alert on unregistered servers configured

- [ ] **Bulk Server Registration**
  - [ ] Bulk registration API tested
  - [ ] CSV import template created (if needed)
  - [ ] Migration plan for existing servers (if any)
  - [ ] Rollout schedule defined

---

## Testing & Validation

### Phase 7: Pre-Production Testing (Week 5-6)

- [ ] **Functional Testing**
  - [ ] User authentication flows tested
  - [ ] API endpoints tested (CRUD operations)
  - [ ] Policy evaluation tested with sample users
  - [ ] Audit logging validated
  - [ ] Tool sensitivity classification tested

- [ ] **Performance Testing**
  - [ ] Load test performed (target: 1,200+ req/s)
  - [ ] Policy evaluation latency measured (<50ms p95)
  - [ ] Database query performance validated
  - [ ] Redis cache hit rate measured (>95% target)
  - [ ] API response times measured (<100ms p95)

- [ ] **Security Testing**
  - [ ] Authentication bypass attempts tested
  - [ ] Authorization boundary testing performed
  - [ ] SQL injection testing performed
  - [ ] XSS testing performed
  - [ ] Rate limiting tested
  - [ ] Secret exposure checked (no secrets in logs/responses)

- [ ] **Disaster Recovery Testing**
  - [ ] Database backup tested
  - [ ] Database restore tested
  - [ ] Redis failover tested (if HA)
  - [ ] Pod failure recovery tested
  - [ ] Deployment rollback tested

- [ ] **Integration Testing**
  - [ ] End-to-end user workflow tested
  - [ ] SIEM event forwarding verified
  - [ ] Authentication provider integration verified
  - [ ] Monitoring alerts verified

---

## Documentation & Training

### Phase 8: Knowledge Transfer (Week 6)

- [ ] **Internal Documentation**
  - [ ] Deployment runbook created
  - [ ] Incident response procedures documented
  - [ ] Escalation contacts listed
  - [ ] Common troubleshooting guide created
  - [ ] Backup/restore procedures documented

- [ ] **User Training**
  - [ ] Developer training materials prepared
  - [ ] User training materials prepared
  - [ ] Security team training materials prepared
  - [ ] Training sessions scheduled
  - [ ] Training sessions conducted

- [ ] **Knowledge Base**
  - [ ] FAQ updated with org-specific information
  - [ ] Known issues documented
  - [ ] Best practices guide created
  - [ ] Example MCP servers documented

---

## Production Launch

### Phase 9: Go-Live (Week 7)

- [ ] **Pre-Launch Review**
  - [ ] All checklist items completed
  - [ ] Security review passed
  - [ ] Performance targets met
  - [ ] Stakeholder sign-off obtained
  - [ ] Rollback plan documented

- [ ] **Launch**
  - [ ] Production deployment executed
  - [ ] Smoke tests passed
  - [ ] Monitoring confirmed active
  - [ ] Audit logging confirmed
  - [ ] Users notified of launch

- [ ] **Post-Launch Monitoring** (First 48 hours)
  - [ ] Error rates monitored
  - [ ] Performance metrics reviewed
  - [ ] User feedback collected
  - [ ] Issues triaged and addressed
  - [ ] Success metrics tracked

---

## Post-Launch

### Phase 10: Optimization & Growth (Ongoing)

- [ ] **Week 1 Post-Launch**
  - [ ] User adoption metrics reviewed
  - [ ] Performance bottlenecks identified
  - [ ] Policy adjustments made based on feedback
  - [ ] Audit reports generated
  - [ ] Incident review (if any)

- [ ] **Week 2-4 Post-Launch**
  - [ ] Policy optimization based on patterns
  - [ ] Additional MCP servers onboarded
  - [ ] User training refined
  - [ ] Documentation updated
  - [ ] Feature requests prioritized

- [ ] **Ongoing Operations**
  - [ ] Monthly security reviews scheduled
  - [ ] Quarterly capacity planning
  - [ ] Regular policy audits
  - [ ] Continuous user feedback collection
  - [ ] Version upgrade planning

---

## Success Criteria

### Deployment Success

- [ ] All services healthy and stable for 7 days
- [ ] Zero P0/P1 incidents
- [ ] Performance targets met (API <100ms p95)
- [ ] Policy evaluation <50ms p95
- [ ] Cache hit rate >95%
- [ ] Zero security vulnerabilities (P0/P1)

### User Adoption

- [ ] 80%+ of target users onboarded
- [ ] 10+ MCP servers registered
- [ ] 1,000+ tool invocations per day
- [ ] <5% user-reported issues
- [ ] Positive feedback from stakeholders

### Security & Compliance

- [ ] 100% of tool invocations audited
- [ ] Zero policy bypass incidents
- [ ] Audit retention policy met
- [ ] Compliance requirements satisfied
- [ ] Security team satisfied with posture

---

## Templates & Resources

### Planning Templates
- [ ] Deployment timeline template
- [ ] Resource estimation spreadsheet
- [ ] Stakeholder communication plan
- [ ] Training schedule template

### Technical Templates
- [ ] Kubernetes manifest templates
- [ ] Helm values template
- [ ] OPA policy templates
- [ ] Monitoring dashboard templates
- [ ] Alert rule templates

### Documentation Templates
- [ ] Runbook template
- [ ] Incident response template
- [ ] Training materials template
- [ ] User guide template

---

## Quick Reference

**Minimum Requirements:**
- Kubernetes 1.28+
- PostgreSQL 15+ with TimescaleDB
- Redis 7+
- OPA 0.60+
- 3+ nodes for HA

**Recommended Specifications:**
- API: 3 replicas, 2 CPU, 4GB RAM each
- PostgreSQL: 4 CPU, 16GB RAM, 100GB SSD
- Redis: 2 CPU, 8GB RAM
- OPA: 1 CPU, 2GB RAM per sidecar

**Timeline:**
- Planning: Week 1
- Infrastructure: Week 2
- Deployment: Week 3
- Configuration: Week 4
- Testing: Week 5-6
- Launch: Week 7

---

**Last Updated:** 2025-11-27
**Version:** 1.0
**Maintainer:** Documentation Team
