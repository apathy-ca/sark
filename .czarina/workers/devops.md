# Worker: DEVOPS
## Network-Level Controls

**Stream:** 3
**Duration:** Week 5 (1 week)
**Branch:** `feat/network-controls`
**Agent:** Cursor or Continue.dev (recommended)
**Dependencies:** Local K8s cluster (kind)

---

## Mission

Implement defense-in-depth network security using Kubernetes Network Policies, Calico egress filtering, and cloud firewall rules.

## Goals

- K8s NetworkPolicies for pod-to-pod communication
- Calico GlobalNetworkPolicy for egress domain whitelist
- Terraform modules for cloud firewall rules (AWS/GCP)
- All policies tested in local kind cluster
- Documentation for production deployment

## Week 5: Implementation

### Tasks

1. **Kubernetes Network Policies** (2 days)
   - Files: `k8s/network-policies/*.yaml` (NEW)
   - Create policies for:
     * gateway-egress.yaml - SARK gateway egress rules
     * gateway-ingress.yaml - API ingress rules
     * database-access.yaml - PostgreSQL access restrictions
     * redis-access.yaml - Redis access restrictions
     * opa-access.yaml - OPA access restrictions

2. **Egress Filtering (Calico)** (2 days)
   - File: `k8s/network-policies/egress-allow-list.yaml` (NEW)
   - Domain whitelist for external MCP servers
   - Allow: *.openai.com, *.anthropic.com, internal servers
   - Deny all other egress
   - Test in local kind cluster

3. **Cloud Firewall Rules** (1 day)
   - File: `terraform/modules/network/firewall.tf` (NEW)
   - AWS Security Groups example
   - GCP Firewall Rules example
   - Azure Network Security Groups example

4. **Documentation** (1 day)
   - File: `docs/deployment/NETWORK_SECURITY.md` (NEW)
   - Network architecture diagram
   - Policy configuration guide
   - Troubleshooting guide for blocked connections
   - How to add new allowed domains

## Deliverables

- ✅ `k8s/network-policies/` directory with 5+ policies
- ✅ `k8s/network-policies/egress-allow-list.yaml`
- ✅ `terraform/modules/network/firewall.tf`
- ✅ `docs/deployment/NETWORK_SECURITY.md`
- ✅ `k8s/kind-config.yaml` - Local cluster config with Calico

## Success Metrics

- [ ] Network policies apply successfully in kind cluster
- [ ] Egress filtering blocks unauthorized domains
- [ ] Allowed domains still accessible
- [ ] Documentation verified and complete

## References

- Implementation Plan: `docs/v1.3.0/IMPLEMENTATION_PLAN.md` (Stream 3)
- Calico Docs: https://docs.tigera.io/calico/latest/network-policy/
- K8s NetworkPolicy: https://kubernetes.io/docs/concepts/services-networking/network-policies/
