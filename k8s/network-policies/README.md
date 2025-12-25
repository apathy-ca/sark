# SARK Network Policies (v1.3.0)

Network security policies for SARK Gateway to enforce defense-in-depth at the network layer.

## Overview

These NetworkPolicy manifests implement the network security controls specified in v1.3.0:

1. **gateway-egress.yaml** - Controls outbound traffic from gateway pods
2. **egress-allowlist.yaml** - Domain-based external egress filtering (requires Calico)
3. **ingress-lockdown.yaml** - Controls inbound traffic to gateway pods

## Prerequisites

### Standard Kubernetes NetworkPolicy

The `gateway-egress.yaml` and `ingress-lockdown.yaml` policies use standard Kubernetes NetworkPolicy resources and work with any CNI that supports NetworkPolicy:

- Calico
- Cilium
- Weave Net
- Kube-router

### Calico Global NetworkPolicy

The `egress-allowlist.yaml` policy uses Calico's `GlobalNetworkPolicy` CRD for domain-based filtering. This requires:

- **Calico CNI** installed in your cluster
- Calico version 3.x or higher

## Deployment

### 1. Apply Standard NetworkPolicies

```bash
# Apply egress policy
kubectl apply -f k8s/network-policies/gateway-egress.yaml

# Apply ingress policy
kubectl apply -f k8s/network-policies/ingress-lockdown.yaml
```

### 2. Apply Calico GlobalNetworkPolicy (Optional)

If you have Calico installed:

```bash
# Customize domains in egress-allowlist.yaml first
kubectl apply -f k8s/network-policies/egress-allowlist.yaml
```

If you don't have Calico, skip this step or implement equivalent firewall rules at the cloud provider level.

## Configuration

### Customizing Allowed Domains

Edit `egress-allowlist.yaml` to add your organization's MCP server domains:

```yaml
destination:
  domains:
    - "*.your-company.com"
    - "mcp-prod.example.com"
    - "mcp-staging.example.com"
```

### Customizing Service Access

Edit `gateway-egress.yaml` to modify allowed internal services:

```yaml
egress:
  - to:
    - podSelector:
        matchLabels:
          app: your-service
    ports:
      - protocol: TCP
        port: 8080
```

## Testing

### Test Allowed Egress

```bash
# From gateway pod, test allowed domain
kubectl exec -n sark deployment/sark-gateway -- curl https://api.openai.com

# Should succeed
```

### Test Blocked Egress

```bash
# From gateway pod, test blocked domain
kubectl exec -n sark deployment/sark-gateway -- curl https://evil.com

# Should fail with connection timeout or error
```

### Verify Policies Applied

```bash
# List network policies
kubectl get networkpolicies -n sark

# Describe specific policy
kubectl describe networkpolicy sark-gateway-egress-policy -n sark

# For Calico policies
kubectl get globalnetworkpolicies
```

## Troubleshooting

### Legitimate Traffic Blocked

If legitimate traffic is blocked:

1. Check pod labels match policy selectors
2. Verify ports are correct
3. Add domain/service to allowlist
4. Check Calico logs: `kubectl logs -n kube-system -l k8s-app=calico-node`

### Policy Not Enforced

If policies aren't enforcing:

1. Verify CNI supports NetworkPolicy
2. Check policy is applied: `kubectl get netpol -n sark`
3. Verify pod labels match selector
4. Check for conflicting policies (lower order/priority)

### DNS Resolution Issues

If DNS doesn't work after applying policies:

1. Ensure DNS egress rule is present
2. Verify kube-system namespace has correct label
3. Check CoreDNS/kube-dns pod labels

## Security Notes

- **Default Deny**: These policies implement default deny - only explicitly allowed traffic is permitted
- **Defense in Depth**: Network policies complement (not replace) other security controls
- **Monitoring**: Monitor blocked connections via CNI logs to detect misconfigurations
- **Updates**: Review and update allowed domains regularly

## Production Recommendations

1. **Test in Staging First**: Apply to staging environment and monitor for blocked legitimate traffic
2. **Gradual Rollout**: Start with logging mode (Calico) before enforcing
3. **Monitor Metrics**: Track blocked connection attempts
4. **Document Exceptions**: Keep list of allowed domains/services updated
5. **Periodic Review**: Audit policies quarterly

## Alternative Implementations

If not using Calico, implement domain-based egress filtering using:

- **AWS**: Security Groups + VPC endpoints
- **GCP**: Firewall rules + Private Google Access
- **Azure**: NSG rules + Service Endpoints
- **Firewall Appliance**: F5, Palo Alto, etc.

## References

- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Calico GlobalNetworkPolicy](https://docs.tigera.io/calico/latest/reference/resources/globalnetworkpolicy)
- [SARK v1.3.0 Security Documentation](../../docs/security/NETWORK_SECURITY.md)
