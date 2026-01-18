# SARK Architecture Vision: Multi-Modal LLM Governance

**Status:** Draft / Ideation
**Date:** 2026-01-18
**Authors:** Architecture Discussion

---

## Executive Summary

SARK's current architecture requires explicit client integration. This document captures a broader vision: **a spectrum of deployment modes** from passive observation to active enforcement, applicable from home networks to enterprise data centers.

```
OBSERVABILITY ◄─────────────────────────────────────────► ENFORCEMENT

  Optical TAP      Log Analysis      BGP FlowSpec      Inline Gateway
  (Passive)        (Post-hoc)        (Network)         (Application)
      │                │                  │                  │
   Mirror           Import             Redirect           Explicit
   Traffic          Logs               Traffic            Routing
      │                │                  │                  │
   Zero             N/A               Low                Moderate
   Latency                            Latency            Latency
      │                │                  │                  │
   Observe          Forensics         Block +            Block +
   + Alert          + Audit           Audit              Audit
```

---

## Current State: Explicit Resource Gateway

### How SARK Works Today

```
Agent/Client (must know about SARK)
    │
    ▼
┌─────────────────────────────────────┐
│ SARK API                            │
│  ├─ POST /api/v1/gateway/authorize  │
│  ├─ Authentication (JWT)            │
│  ├─ Policy Evaluation (OPA)         │
│  └─ Protocol Adapters               │
│      ├─ MCP (stdio/SSE/HTTP)        │
│      ├─ HTTP/REST                   │
│      └─ gRPC                        │
└─────────────────┬───────────────────┘
                  │
                  ▼
           Actual Resource
           (MCP Server, LLM API, etc.)
```

### Limitations

| Issue | Impact |
|-------|--------|
| Explicit integration required | Adoption friction |
| Clients must be SARK-aware | Can't govern legacy/third-party apps |
| Single point of failure | SARK down = access blocked |
| Application-layer only | Can't see network-level patterns |

---

## Vision: Multi-Modal Deployment

### Mode 1: Inline Gateway (Current)

**Use Case:** High-security environments, regulated industries

```
┌──────────┐      ┌──────────┐      ┌──────────┐
│  Client  │ ───► │   SARK   │ ───► │   LLM    │
└──────────┘      │ Gateway  │      │   API    │
                  └──────────┘      └──────────┘
                       │
                  Block/Allow
                  + Full Audit
```

**Characteristics:**
- Explicit routing required
- Synchronous policy evaluation
- Can block requests
- Full request/response inspection
- Latency impact: +10-50ms

---

### Mode 2: BGP FlowSpec (Network-Layer Redirect)

**Use Case:** Enterprise with SDN/programmable network fabric

```
┌─────────────────────────────────────────────────────────────┐
│                     SARK Controller                         │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ FlowSpec Rule Manager                                 │ │
│  │  - LLM endpoint registry (IPs for OpenAI, etc.)      │ │
│  │  - Policy-to-FlowSpec compiler                       │ │
│  │  - BGP speaker (ExaBGP / GoBGP / FRR)               │ │
│  └───────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────┘
                           │ BGP FlowSpec (RFC 5575/8955)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Edge Router / SDN Switch                                    │
│  FlowSpec Rules:                                            │
│  ├─ dst=104.18.0.0/16 (OpenAI) → redirect SARK:8443       │
│  ├─ dst=172.64.0.0/16 (Anthropic) → redirect SARK:8443    │
│  ├─ src=10.0.66.0/24 (untrusted) → rate-limit 1mbps       │
│  └─ dst=*.mistral.ai → drop (blocked provider)            │
└──────────────────────────┬──────────────────────────────────┘
                           │
              Traffic transparently redirected
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ SARK Inline Proxy                                           │
│  - TLS termination (enterprise CA)                         │
│  - Policy evaluation (OPA)                                 │
│  - Request/response logging                                │
│  - Forward to actual LLM endpoint                          │
└─────────────────────────────────────────────────────────────┘
```

**FlowSpec Rule Data Structures:**

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import ipaddress

class FlowSpecAction(Enum):
    REDIRECT = "redirect"      # Send to SARK proxy
    RATE_LIMIT = "rate-limit"  # Throttle bandwidth
    DROP = "drop"              # Block entirely
    MARK_DSCP = "mark"         # Tag for QoS
    SAMPLE = "sample"          # Copy to collector

@dataclass
class LLMEndpoint:
    """Known LLM API endpoint for FlowSpec rules."""
    name: str                           # "openai", "anthropic", etc.
    ip_prefixes: list[str]              # ["104.18.0.0/16", "172.64.0.0/16"]
    domains: list[str]                  # ["api.openai.com"]
    ports: list[int] = (443,)           # Usually just HTTPS

@dataclass
class FlowSpecRule:
    """BGP FlowSpec rule for LLM traffic governance."""
    name: str
    match: FlowSpecMatch
    action: FlowSpecAction
    action_params: dict                 # redirect_ip, rate_kbps, dscp_value
    policy_id: Optional[str] = None     # Link to OPA policy
    priority: int = 100
    enabled: bool = True

@dataclass
class FlowSpecMatch:
    """Traffic matching criteria for FlowSpec."""
    dst_prefix: Optional[str] = None    # Destination IP prefix
    src_prefix: Optional[str] = None    # Source IP prefix
    dst_port: Optional[list[int]] = None
    src_port: Optional[list[int]] = None
    protocol: Optional[int] = None      # 6=TCP, 17=UDP
    packet_length: Optional[tuple[int, int]] = None
    dscp: Optional[int] = None

# LLM Endpoint Registry
LLM_ENDPOINTS = {
    "openai": LLMEndpoint(
        name="openai",
        ip_prefixes=["104.18.0.0/15", "172.64.0.0/13"],
        domains=["api.openai.com", "chat.openai.com"],
    ),
    "anthropic": LLMEndpoint(
        name="anthropic",
        ip_prefixes=["104.18.32.0/20"],
        domains=["api.anthropic.com"],
    ),
    "google": LLMEndpoint(
        name="google",
        ip_prefixes=["142.250.0.0/15", "172.217.0.0/16"],
        domains=["generativelanguage.googleapis.com"],
    ),
    "mistral": LLMEndpoint(
        name="mistral",
        ip_prefixes=[],  # Resolve dynamically
        domains=["api.mistral.ai"],
    ),
    "groq": LLMEndpoint(
        name="groq",
        ip_prefixes=[],
        domains=["api.groq.com"],
    ),
}
```

**BGP Speaker Integration:**

```python
class FlowSpecManager:
    """Manage FlowSpec rules via BGP."""

    def __init__(self, bgp_config: BGPConfig):
        self.speaker = self._init_speaker(bgp_config)
        self.active_rules: dict[str, FlowSpecRule] = {}

    def _init_speaker(self, config: BGPConfig):
        """Initialize BGP speaker (ExaBGP, GoBGP, or FRR)."""
        if config.implementation == "exabgp":
            return ExaBGPClient(config.api_endpoint)
        elif config.implementation == "gobgp":
            return GoBGPClient(config.grpc_endpoint)
        elif config.implementation == "frr":
            return FRRClient(config.vtysh_socket)

    async def apply_policy(self, policy_decision: OPADecision) -> None:
        """Convert OPA policy decision to FlowSpec rules."""
        rules = self._compile_to_flowspec(policy_decision)
        for rule in rules:
            await self.announce_rule(rule)

    async def announce_rule(self, rule: FlowSpecRule) -> None:
        """Push FlowSpec rule to edge routers via BGP."""
        nlri = self._build_flowspec_nlri(rule)
        await self.speaker.announce(
            afi=AFI.IPv4,
            safi=SAFI.FLOWSPEC,
            nlri=nlri,
            communities=self._build_communities(rule),
        )
        self.active_rules[rule.name] = rule

    async def withdraw_rule(self, rule_name: str) -> None:
        """Remove FlowSpec rule from network."""
        if rule := self.active_rules.pop(rule_name, None):
            nlri = self._build_flowspec_nlri(rule)
            await self.speaker.withdraw(nlri)
```

**Characteristics:**
- Transparent to clients
- Network-layer enforcement
- Requires router/switch support (Juniper, Cisco, Arista, etc.)
- TLS inspection needs enterprise CA
- Latency impact: +5-20ms

---

### Mode 3: Corporate LLM Proxy Plugin

**Use Case:** Organizations with existing API gateways

```
┌──────────────────────────────────────────────────────────┐
│              Existing Infrastructure                      │
│                                                          │
│  ┌─────────┐    ┌──────────────────────┐    ┌────────┐ │
│  │ Client  │───►│  Corporate Proxy     │───►│  LLM   │ │
│  └─────────┘    │  (Kong/Envoy/APIM)   │    │  APIs  │ │
│                 │         │            │    └────────┘ │
│                 │    ┌────▼─────┐      │               │
│                 │    │  SARK    │      │               │
│                 │    │  Plugin  │      │               │
│                 │    └──────────┘      │               │
│                 └──────────────────────┘               │
└──────────────────────────────────────────────────────────┘
```

**Integration Options:**

| Platform | Integration Method | Complexity |
|----------|-------------------|------------|
| **Envoy** | ext_authz filter or WASM | Medium |
| **Kong** | Custom Lua/Go plugin | Medium |
| **Azure APIM** | Policy fragment | Low |
| **AWS API Gateway** | Lambda authorizer | Low |
| **Cloudflare AI Gateway** | Worker | Low |
| **Nginx/OpenResty** | auth_request + Lua | Medium |
| **Traefik** | ForwardAuth middleware | Low |

**Envoy ext_authz Example:**

```yaml
# envoy.yaml
http_filters:
  - name: envoy.filters.http.ext_authz
    typed_config:
      "@type": type.googleapis.com/envoy.extensions.filters.http.ext_authz.v3.ExtAuthz
      grpc_service:
        envoy_grpc:
          cluster_name: sark-authz
        timeout: 0.5s
      transport_api_version: V3
      failure_mode_allow: false  # Fail closed
      with_request_body:
        max_request_bytes: 65536
        allow_partial_message: true
        pack_as_bytes: true

clusters:
  - name: sark-authz
    connect_timeout: 0.25s
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    http2_protocol_options: {}
    load_assignment:
      cluster_name: sark-authz
      endpoints:
        - lb_endpoints:
            - endpoint:
                address:
                  socket_address:
                    address: sark-api
                    port_value: 9001  # gRPC authz port
```

**Kong Plugin Skeleton:**

```lua
-- kong/plugins/sark-governance/handler.lua
local http = require "resty.http"
local cjson = require "cjson"

local SarkHandler = {
    VERSION = "1.0.0",
    PRIORITY = 1000,
}

function SarkHandler:access(conf)
    local httpc = http.new()

    -- Build SARK authorization request
    local authz_request = {
        user = kong.client.get_credential(),
        action = "invoke",
        resource = {
            type = "llm",
            provider = self:detect_provider(kong.request.get_host()),
            model = self:extract_model(kong.request.get_body()),
        },
        parameters = kong.request.get_body(),
    }

    -- Call SARK
    local res, err = httpc:request_uri(conf.sark_url .. "/api/v1/gateway/authorize", {
        method = "POST",
        body = cjson.encode(authz_request),
        headers = {
            ["Content-Type"] = "application/json",
            ["Authorization"] = "Bearer " .. conf.sark_api_key,
        },
    })

    if not res or res.status ~= 200 then
        return kong.response.exit(503, { message = "SARK unavailable" })
    end

    local decision = cjson.decode(res.body)
    if not decision.allow then
        return kong.response.exit(403, {
            message = "Request denied by policy",
            reason = decision.reason,
        })
    end

    -- Request allowed, continue to upstream
end

return SarkHandler
```

**Characteristics:**
- Leverages existing infrastructure
- Vendor-specific implementations
- Variable latency based on platform
- No network changes required

---

### Mode 4: Optical TAP (Passive Observation)

**Use Case:** Compliance monitoring, shadow IT detection, cost visibility

```
                                        ┌─────────────────────┐
                                        │ SARK Passive Sensor │
                                        │  - Packet capture   │
                                        │  - TLS decryption   │
                                        │  - Policy eval      │
                                        │  - Alerting         │
                                        │  - Full audit log   │
                                        └──────────▲──────────┘
                                                   │
                                              Mirror/Copy
                                                   │
┌─────────────┐      ┌───────────────┐      ┌─────┴──────┐
│   Clients   │ ───► │ Switch + TAP  │──────│  Optical   │
│             │      │               │      │   TAP      │
└─────────────┘      └───────┬───────┘      └────────────┘
                             │
                             │ Production traffic
                             │ (untouched, zero latency)
                             ▼
                     ┌───────────────┐
                     │   LLM APIs    │
                     └───────────────┘
```

**TAP Processor Implementation:**

```python
import asyncio
from dataclasses import dataclass
from typing import AsyncIterator
import dpkt
import pcap

@dataclass
class LLMRequest:
    """Parsed LLM API request from captured traffic."""
    timestamp: float
    src_ip: str
    dst_ip: str
    provider: str          # openai, anthropic, etc.
    endpoint: str          # /v1/chat/completions
    model: str             # gpt-4, claude-3, etc.
    prompt_tokens: int
    user_agent: str
    request_body: dict     # Full request (if TLS decrypted)

@dataclass
class PolicyViolation:
    """Detected policy violation from passive analysis."""
    request: LLMRequest
    policy_id: str
    rule_id: str
    severity: str          # LOW, MEDIUM, HIGH, CRITICAL
    reason: str
    recommended_action: str

class TAPProcessor:
    """Process mirrored traffic from optical/network TAP."""

    def __init__(
        self,
        interface: str,
        tls_keys: Optional[TLSKeyLog] = None,  # For decryption
        bpf_filter: str = "tcp port 443",
    ):
        self.interface = interface
        self.tls_decoder = TLSDecoder(tls_keys) if tls_keys else None
        self.bpf_filter = bpf_filter
        self.flow_table: dict[tuple, TCPFlow] = {}
        self.llm_endpoints = self._load_llm_endpoints()

    async def capture_loop(self) -> AsyncIterator[LLMRequest]:
        """Main capture loop - yields parsed LLM requests."""
        pc = pcap.pcap(name=self.interface, promisc=True, immediate=True)
        pc.setfilter(self.bpf_filter)

        for timestamp, packet in pc:
            eth = dpkt.ethernet.Ethernet(packet)
            if not isinstance(eth.data, dpkt.ip.IP):
                continue

            ip = eth.data
            if not isinstance(ip.data, dpkt.tcp.TCP):
                continue

            tcp = ip.data
            flow_key = self._flow_key(ip, tcp)

            # Reassemble TCP stream
            flow = self.flow_table.setdefault(flow_key, TCPFlow())
            flow.add_packet(tcp, timestamp)

            # Check if we have a complete HTTP request
            if flow.has_complete_request():
                request_data = flow.extract_request()

                # Decrypt TLS if we have keys
                if self.tls_decoder:
                    request_data = self.tls_decoder.decrypt(flow)

                # Parse as LLM request if destined for known endpoint
                if llm_req := self._parse_llm_request(ip, request_data):
                    yield llm_req

                flow.reset()

    def _parse_llm_request(self, ip, data: bytes) -> Optional[LLMRequest]:
        """Parse HTTP request as LLM API call."""
        dst_ip = socket.inet_ntoa(ip.dst)

        # Check if destination is known LLM endpoint
        provider = self._identify_provider(dst_ip)
        if not provider:
            return None

        try:
            http_request = dpkt.http.Request(data)
            body = json.loads(http_request.body) if http_request.body else {}

            return LLMRequest(
                timestamp=time.time(),
                src_ip=socket.inet_ntoa(ip.src),
                dst_ip=dst_ip,
                provider=provider,
                endpoint=http_request.uri,
                model=body.get("model", "unknown"),
                prompt_tokens=self._estimate_tokens(body),
                user_agent=http_request.headers.get("user-agent", ""),
                request_body=body,
            )
        except Exception:
            return None

    async def analyze_and_alert(self, request: LLMRequest) -> None:
        """Evaluate request against policies and alert on violations."""
        # Build OPA input (same format as inline mode)
        opa_input = {
            "user": {"ip": request.src_ip},  # Limited info in passive mode
            "action": "invoke",
            "resource": {
                "type": "llm",
                "provider": request.provider,
                "model": request.model,
            },
            "parameters": request.request_body,
        }

        # Evaluate policy
        decision = await self.opa_client.evaluate(
            "data.sark.llm.allow",
            opa_input,
        )

        # Always log for audit
        await self.audit_log.write(request, decision)

        # Alert on violations (can't block in passive mode)
        if not decision.get("allow", True):
            violation = PolicyViolation(
                request=request,
                policy_id=decision.get("policy_id"),
                rule_id=decision.get("rule_id"),
                severity=decision.get("severity", "MEDIUM"),
                reason=decision.get("reason", "Policy violation"),
                recommended_action="Review and consider blocking",
            )
            await self.alert_manager.send(violation)
```

**Characteristics:**
- Zero production impact
- Full visibility including shadow IT
- Cannot block (observe only)
- Requires TLS inspection for content
- Great for compliance/audit

---

## YORI: Home Network LLM Governance

**"Your Own Resource Inspector"** - Pi-hole for LLM APIs

### Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                            YORI                                 │
│                                                                 │
│     Personal/Home LLM traffic visibility and governance         │
│                                                                 │
│     "Pi-hole showed you every tracker. YORI shows you every AI" │
└─────────────────────────────────────────────────────────────────┘
```

### Home Network Deployment

```
┌──────────────────────────────────────────────────────────────────┐
│ Home Network                                                     │
│                                                                  │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                         │
│  │ Laptop  │  │ Phone   │  │ Tablet  │                         │
│  └────┬────┘  └────┬────┘  └────┬────┘                         │
│       │            │            │                               │
│       └────────────┼────────────┘                               │
│                    │                                            │
│                    ▼                                            │
│            ┌───────────────┐                                    │
│            │    Router     │                                    │
│            │  DNS → YORI   │                                    │
│            └───────┬───────┘                                    │
│                    │                                            │
│       ┌────────────┼────────────┐                               │
│       │            │            │                               │
│       ▼            ▼            ▼                               │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                         │
│  │  YORI   │  │  NAS    │  │ Pi-hole │                         │
│  │ (Pi 4)  │  │         │  │         │                         │
│  └─────────┘  └─────────┘  └─────────┘                         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                    │
                    ▼ Internet
        ┌───────────────────────┐
        │  api.openai.com       │
        │  api.anthropic.com    │
        │  api.mistral.ai       │
        │  ...                  │
        └───────────────────────┘
```

### YORI Operating Modes

#### Mode A: DNS-Only (Simplest)

```
┌─────────────────────────────────────────────────────────┐
│ YORI DNS Mode                                           │
│                                                         │
│  - Point router DNS to YORI                            │
│  - Log all DNS queries for LLM domains                 │
│  - Block domains by returning NXDOMAIN                 │
│  - No TLS inspection needed                            │
│  - Cannot see request content                          │
│                                                         │
│  Capabilities:                                          │
│  [x] See which devices query LLM APIs                  │
│  [x] Block entire providers (e.g., block Gemini)       │
│  [x] Time-based rules (no AI after 9pm)               │
│  [ ] See what's being asked                            │
│  [ ] See costs                                         │
└─────────────────────────────────────────────────────────┘
```

#### Mode B: Transparent Proxy

```
┌─────────────────────────────────────────────────────────┐
│ YORI Proxy Mode                                         │
│                                                         │
│  - YORI acts as network gateway                        │
│  - TLS interception with user-installed CA             │
│  - Full request/response visibility                    │
│  - Can block, modify, log everything                   │
│                                                         │
│  Capabilities:                                          │
│  [x] See which devices query LLM APIs                  │
│  [x] Block providers/models/specific requests          │
│  [x] Time-based and content-based rules               │
│  [x] See prompts and responses                        │
│  [x] Calculate costs (tokens × pricing)               │
│  [x] Detect sensitive data exfiltration               │
└─────────────────────────────────────────────────────────┘
```

#### Mode C: Passive TAP (ARP-based)

```
┌─────────────────────────────────────────────────────────┐
│ YORI TAP Mode                                           │
│                                                         │
│  - ARP spoofing to mirror traffic (or managed switch)  │
│  - Passive observation only                            │
│  - TLS decryption if client CA installed               │
│  - Cannot block or modify                              │
│                                                         │
│  Capabilities:                                          │
│  [x] See which devices query LLM APIs                  │
│  [ ] Block (observe only)                              │
│  [x] Audit all traffic                                 │
│  [x] Alert on anomalies                               │
│  [x] Cost tracking                                     │
└─────────────────────────────────────────────────────────┘
```

### YORI Tech Stack

```yaml
# Lightweight, runs on Raspberry Pi 4 (2GB+)

Core:
  language: Rust            # Fast, low memory
  web_framework: Axum       # Async HTTP
  database: SQLite          # No external dependencies
  dns_server: trust-dns     # Rust DNS server
  packet_capture: libpcap   # Via rust-pcap

Frontend:
  framework: React or Solid # Or Leptos (Rust WASM)
  styling: Tailwind CSS
  bundler: Vite

Optional:
  tls_inspection: rustls + mitmproxy-rs
  arp_spoof: pnet library
```

### YORI Docker Deployment

```yaml
# docker-compose.yml
version: "3.8"

services:
  yori:
    image: ghcr.io/sark-project/yori:latest
    container_name: yori
    restart: unless-stopped
    network_mode: host          # Required for packet capture
    cap_add:
      - NET_ADMIN               # Network configuration
      - NET_RAW                 # Raw sockets for capture
    volumes:
      - ./data:/data            # SQLite database
      - ./config:/config        # Configuration
      - ./certs:/certs          # TLS CA (optional)
    environment:
      - YORI_MODE=dns           # dns, proxy, or tap
      - YORI_DNS_PORT=53
      - YORI_WEB_PORT=8080
      - YORI_LOG_LEVEL=info

  # Optional: Run alongside Pi-hole
  pihole:
    image: pihole/pihole:latest
    # ... Pi-hole config
    # Point Pi-hole upstream DNS to YORI
```

### YORI Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│ YORI - LLM Traffic Dashboard                            [━━━]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📊 This Week                                                   │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐    │
│  │ Requests    │ Est. Cost   │ Tokens In   │ Tokens Out  │    │
│  │   1,247     │   $3.42     │  892,441    │  124,882    │    │
│  └─────────────┴─────────────┴─────────────┴─────────────┘    │
│                                                                 │
│  📱 By Device                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Device           │ Requests │ Cost   │ Top Provider     │  │
│  ├──────────────────┼──────────┼────────┼──────────────────┤  │
│  │ macbook-pro      │ 847      │ $2.10  │ OpenAI (89%)     │  │
│  │ iphone-14        │ 312      │ $0.89  │ Anthropic (76%)  │  │
│  │ kids-ipad        │ 88       │ $0.43  │ OpenAI (100%)    │  │
│  │   └─ ⚠️ 12 blocked (after 9pm rule)                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  🤖 By Provider                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ ████████████████████████░░░░░░ OpenAI      74% (923)    │  │
│  │ ████████░░░░░░░░░░░░░░░░░░░░░░ Anthropic   24% (298)    │  │
│  │ ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░ Google       2% (26)     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  🚨 Recent Alerts                                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ ⚠️  14:32  Notion sent document to Claude (3.2KB)       │  │
│  │ ⚠️  09:15  Unknown app using OpenAI API key             │  │
│  │ ℹ️  Yesterday  Daily cost exceeded $1.00 threshold      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ⚙️ Active Rules                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ [✓] Block kids-ipad after 9pm                           │  │
│  │ [✓] Alert on daily cost > $5                            │  │
│  │ [✓] Log all Claude requests                             │  │
│  │ [ ] Block Google Gemini entirely                        │  │
│  │                                         [+ Add Rule]    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### YORI Use Cases

| Scenario | How YORI Helps |
|----------|----------------|
| "Why is my OpenAI bill $50?" | Shows which app/device made calls |
| "Is this app using AI?" | Logs all LLM API traffic |
| "Kids using ChatGPT for homework?" | Device + time tracking |
| "Block AI after bedtime" | Time-based rules per device |
| "What data is being sent?" | Full prompt logging (with TLS inspection) |
| "Audit my AI usage" | Exportable logs, cost reports |
| "Which model is cheapest?" | Compare costs across providers |

---

## Unified Architecture: SARK + YORI

```
┌─────────────────────────────────────────────────────────────────┐
│                    Unified Platform                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Shared Components                      │   │
│  │  ┌───────────────────────────────────────────────────┐  │   │
│  │  │ Policy Engine (OPA)                               │  │   │
│  │  │  - Same Rego policies work everywhere            │  │   │
│  │  │  - User/device/time/content rules                │  │   │
│  │  └───────────────────────────────────────────────────┘  │   │
│  │  ┌───────────────────────────────────────────────────┐  │   │
│  │  │ LLM Endpoint Registry                             │  │   │
│  │  │  - IP ranges, domains, API patterns              │  │   │
│  │  │  - Pricing data for cost estimation              │  │   │
│  │  └───────────────────────────────────────────────────┘  │   │
│  │  ┌───────────────────────────────────────────────────┐  │   │
│  │  │ Audit Log Format                                  │  │   │
│  │  │  - Consistent schema across all modes            │  │   │
│  │  │  - Exportable, searchable                        │  │   │
│  │  └───────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │    SARK      │  │    SARK      │  │       YORI           │  │
│  │  Enterprise  │  │   FlowSpec   │  │       Home           │  │
│  ├──────────────┤  ├──────────────┤  ├──────────────────────┤  │
│  │ Inline GW    │  │ BGP Control  │  │ DNS + Proxy + TAP    │  │
│  │ Proxy Plugin │  │ Network TAP  │  │ Raspberry Pi         │  │
│  │ Full Audit   │  │ Transparent  │  │ Simple Dashboard     │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│       │                  │                     │                │
│       └──────────────────┼─────────────────────┘                │
│                          │                                      │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Central Dashboard (Optional)                │   │
│  │  - Aggregate view across deployments                    │   │
│  │  - Policy sync                                          │   │
│  │  - Unified alerting                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Roadmap

### Phase 1: Foundation (Current)
- [x] SARK inline gateway (explicit routing)
- [x] OPA policy engine
- [x] Audit logging
- [ ] Complete MCP gateway client (BLOCKED)

### Phase 2: Network Integration
- [ ] BGP FlowSpec rule manager
- [ ] ExaBGP/GoBGP integration
- [ ] LLM endpoint IP registry (auto-updating)
- [ ] TLS inspection proxy

### Phase 3: Passive Monitoring
- [ ] TAP processor (libpcap)
- [ ] Flow reassembly
- [ ] Passive TLS decryption (with SSLKEYLOG)
- [ ] Alert-only mode

### Phase 4: Proxy Plugins
- [ ] Envoy ext_authz gRPC service
- [ ] Kong plugin
- [ ] Generic auth_request endpoint
- [ ] WASM filter for Envoy

### Phase 5: YORI (Home)
- [ ] Rust core daemon
- [ ] DNS server with LLM blocking
- [ ] Simple web dashboard
- [ ] Docker image for Pi
- [ ] Optional TLS inspection

### Phase 6: Unification
- [ ] Shared policy format
- [ ] Shared audit schema
- [ ] Central dashboard
- [ ] Policy sync across deployments

---

---

## Mode 5: Agent-to-Agent (A2A) Governance

### The Problem

MCP enables agent-to-agent communication that bypasses all network-level controls:

```
Network-Level Blind Spots:

┌─────────────────────────────────────────────────────────────────┐
│ Host Machine                                                    │
│                                                                 │
│   Agent A ←───stdio───→ Agent B ←───stdio───→ Agent C          │
│       │                     │                     │             │
│       └─────────────────────┴─────────────────────┘             │
│                         │                                       │
│              No network traffic                                 │
│              No packets to capture                              │
│              Gateway never sees it                              │
│              FlowSpec can't redirect it                         │
│              TAP captures nothing                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**A2A Transport Types:**

| Transport | Description | Network Visible? |
|-----------|-------------|------------------|
| stdio | Agent spawns another agent as subprocess | No |
| Unix socket | Local IPC | No |
| localhost HTTP | Same-host HTTP | Only with loopback capture |
| In-process | Agent loads another as library | No |
| Kubernetes pod-to-pod | Same-node optimized | Sometimes |

### Solution 1: SARK SDK (Embedded Policy Enforcement)

Embed policy enforcement directly in the MCP client SDK:

```python
# sark_sdk/mcp_client.py

class SARKMCPClient:
    """MCP client with embedded SARK policy enforcement."""

    def __init__(
        self,
        agent_id: str,
        sark_policy_cache: PolicyCache,
        sark_audit: AuditClient,
    ):
        self.agent_id = agent_id
        self.policy = sark_policy_cache      # Local OPA or cached rules
        self.audit = sark_audit              # Async audit shipping
        self._mcp_client = MCPClient()       # Underlying MCP client

    async def call_tool(
        self,
        server: str,
        tool: str,
        arguments: dict,
    ) -> ToolResult:
        """Call MCP tool with policy enforcement."""

        # Build policy input
        policy_input = {
            "caller": {
                "agent_id": self.agent_id,
                "type": "agent",
            },
            "callee": {
                "server": server,
                "tool": tool,
            },
            "action": "invoke",
            "arguments": arguments,
            "context": {
                "transport": self._mcp_client.transport_type,
                "timestamp": time.time(),
            },
        }

        # Evaluate policy LOCALLY (no network round-trip)
        decision = await self.policy.evaluate(policy_input)

        # Audit (async, non-blocking)
        asyncio.create_task(self.audit.log(policy_input, decision))

        if not decision.allow:
            raise PolicyDeniedError(
                f"A2A call denied: {decision.reason}",
                policy_id=decision.policy_id,
            )

        # Policy passed - make the actual MCP call
        return await self._mcp_client.call_tool(server, tool, arguments)


# Usage in agent code:
client = SARKMCPClient(
    agent_id="agent-orchestrator-1",
    sark_policy_cache=LocalOPACache("./policies"),
    sark_audit=AsyncAuditClient("https://sark.internal/audit"),
)

# All tool calls now governed
result = await client.call_tool("code-agent", "write_file", {"path": "/tmp/x"})
```

**Characteristics:**
- Zero network latency (local policy eval)
- Works with any transport (stdio, socket, HTTP)
- Requires SDK adoption
- Policy sync needed (pull from central SARK)

### Solution 2: eBPF Syscall Interception

Intercept at the kernel level - sees everything:

```
┌─────────────────────────────────────────────────────────────────┐
│ Linux Kernel                                                    │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ eBPF Probes                                               │ │
│  │                                                           │ │
│  │  kprobe:sys_write    →  Capture pipe/socket writes       │ │
│  │  kprobe:sys_read     →  Capture pipe/socket reads        │ │
│  │  kprobe:sys_execve   →  Track subprocess spawning        │ │
│  │  kprobe:sys_connect  →  Track outbound connections       │ │
│  │  kprobe:sys_accept   →  Track inbound connections        │ │
│  │                                                           │ │
│  │  Filter: Only processes in "agent" cgroup                │ │
│  │                                                           │ │
│  └───────────────────────────────────────────────────────────┘ │
│                           │                                     │
│                           │ perf buffer / ring buffer           │
│                           ▼                                     │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ SARK eBPF Agent (Userspace)                                     │
│                                                                 │
│  - Reassemble MCP JSON-RPC messages from syscall data          │
│  - Parse tool invocations                                       │
│  - Evaluate policy                                              │
│  - SIGSTOP/SIGCONT for blocking mode (dangerous)               │
│  - Or: audit-only mode (observe + alert)                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**eBPF Probe Skeleton:**

```c
// sark_ebpf/probe.c

#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>

struct mcp_event {
    u32 pid;
    u32 tid;
    u64 timestamp;
    u32 syscall;        // write, read, execve
    u32 fd;
    char comm[16];      // process name
    char data[256];     // first 256 bytes of payload
};

struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 256 * 1024);
} events SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 1024);
    __type(key, u32);   // PID
    __type(value, u8);  // 1 = monitored agent
} monitored_pids SEC(".maps");

SEC("kprobe/sys_write")
int probe_write(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;

    // Only monitor known agent processes
    if (!bpf_map_lookup_elem(&monitored_pids, &pid))
        return 0;

    int fd = (int)PT_REGS_PARM1(ctx);
    char *buf = (char *)PT_REGS_PARM2(ctx);
    size_t count = (size_t)PT_REGS_PARM3(ctx);

    // Check if this looks like MCP JSON-RPC
    char preview[32];
    bpf_probe_read_user(preview, sizeof(preview), buf);

    if (preview[0] != '{')  // Quick JSON check
        return 0;

    // Emit event to userspace
    struct mcp_event *evt = bpf_ringbuf_reserve(&events, sizeof(*evt), 0);
    if (!evt)
        return 0;

    evt->pid = pid;
    evt->tid = bpf_get_current_pid_tgid() & 0xFFFFFFFF;
    evt->timestamp = bpf_ktime_get_ns();
    evt->syscall = __NR_write;
    evt->fd = fd;
    bpf_get_current_comm(evt->comm, sizeof(evt->comm));
    bpf_probe_read_user(evt->data, sizeof(evt->data), buf);

    bpf_ringbuf_submit(evt, 0);
    return 0;
}
```

**Characteristics:**
- Sees ALL inter-process communication
- No agent code changes needed
- Linux-only (macOS: dtrace/esf, Windows: ETW)
- Complex to parse MCP from raw syscalls
- Blocking mode is risky (SIGSTOP can deadlock)

### Solution 3: MCP Protocol Extension

Extend MCP protocol to require authorization tokens:

```
Standard MCP:

  Client                              Server
    │                                   │
    │─── initialize ───────────────────→│
    │←── capabilities ──────────────────│
    │                                   │
    │─── tools/call ───────────────────→│
    │←── result ────────────────────────│


MCP + SARK Extension:

  Client                              Server                    SARK
    │                                   │                        │
    │─── initialize ───────────────────→│                        │
    │    {                              │                        │
    │      "sark": {                    │                        │
    │        "agent_id": "agent-a",     │                        │
    │        "capabilities_token": "eyJ"│                        │
    │      }                            │                        │
    │    }                              │                        │
    │                                   │────── verify ─────────→│
    │                                   │←───── ok ──────────────│
    │←── capabilities ──────────────────│                        │
    │    {                              │                        │
    │      "sark": {                    │                        │
    │        "policy_id": "pol-123",    │                        │
    │        "session_token": "xyz"     │                        │
    │      }                            │                        │
    │    }                              │                        │
    │                                   │                        │
    │─── tools/call ───────────────────→│                        │
    │    {                              │                        │
    │      "sark": {                    │                        │
    │        "authz_token": "abc",      │                        │
    │        "trace_id": "trace-456"    │                        │
    │      }                            │                        │
    │    }                              │                        │
    │                                   │────── authorize ──────→│
    │                                   │←───── allow ───────────│
    │                                   │                        │
    │←── result ────────────────────────│                        │
```

**Protocol Extension Schema:**

```typescript
// MCP SARK Extension

interface SARKClientCapabilities {
  sark?: {
    version: "1.0";
    agent_id: string;
    agent_type: "human" | "agent" | "service";
    capabilities_token?: string;  // JWT proving agent identity
  };
}

interface SARKServerCapabilities {
  sark?: {
    version: "1.0";
    policy_id: string;           // Which policy governs this server
    session_token: string;       // Session-bound token for subsequent calls
    required: boolean;           // If true, reject clients without SARK
  };
}

interface SARKToolCallExtension {
  sark?: {
    authz_token: string;         // Pre-authorized token (optional)
    trace_id: string;            // Distributed tracing
    context?: Record<string, unknown>;  // Additional policy context
  };
}

interface SARKToolResultExtension {
  sark?: {
    audit_id: string;            // Reference to audit log entry
    policy_decision: "allow" | "deny" | "redact";
    redacted_fields?: string[];  // Fields removed by policy
  };
}
```

**Characteristics:**
- Standards-track approach (could propose to MCP spec)
- Explicit, auditable
- Requires both client and server changes
- Can be adopted incrementally (non-SARK agents still work)

### Solution 4: Agent Sidecar (Per-Agent Proxy)

Each agent gets its own tiny SARK instance:

```
┌─────────────────────────────────────────────────────────────────┐
│ Kubernetes Pod                                                  │
│                                                                 │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐    │
│  │   Agent A   │      │    SARK     │      │   Agent B   │    │
│  │             │─────→│   Sidecar   │─────→│             │    │
│  │  MCP Client │      │             │      │  MCP Server │    │
│  └─────────────┘      │  - Policy   │      └─────────────┘    │
│                       │  - Audit    │                          │
│                       │  - 50MB RAM │                          │
│                       └──────┬──────┘                          │
│                              │                                  │
│                         Audit logs                              │
│                              │                                  │
└──────────────────────────────┼──────────────────────────────────┘
                               ▼
                    Central SARK (aggregation)
```

**Sidecar Container Spec:**

```yaml
# Kubernetes sidecar injection
apiVersion: v1
kind: Pod
metadata:
  name: agent-pod
  annotations:
    sark.io/inject: "true"
    sark.io/policy: "agent-policy-v1"
spec:
  containers:
    - name: agent
      image: my-agent:latest
      env:
        - name: MCP_PROXY
          value: "localhost:9999"  # Point to sidecar

    - name: sark-sidecar
      image: ghcr.io/sark/sidecar:latest
      resources:
        requests:
          memory: "50Mi"
          cpu: "50m"
        limits:
          memory: "100Mi"
          cpu: "100m"
      ports:
        - containerPort: 9999  # MCP proxy port
      env:
        - name: SARK_POLICY_URL
          value: "http://sark-central/policies"
        - name: SARK_AUDIT_URL
          value: "http://sark-central/audit"
```

**Characteristics:**
- Works with unmodified agents (just change endpoint)
- Resource overhead per agent
- Kubernetes-native (mutating webhook for injection)
- Can do stdio proxying (trickier)

### A2A Governance Comparison

| Approach | Sees stdio? | Blocking? | Agent Changes? | Overhead |
|----------|-------------|-----------|----------------|----------|
| SDK Embedded | ✅ | ✅ | Yes (use SDK) | Minimal |
| eBPF Interception | ✅ | ⚠️ Risky | No | Medium |
| Protocol Extension | ✅ | ✅ | Yes (both sides) | Minimal |
| Agent Sidecar | ❌ HTTP only | ✅ | Config only | Per-agent |

### Recommended Approach: Layered

```
┌─────────────────────────────────────────────────────────────────┐
│                    A2A Governance Stack                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Layer 1: SDK (Primary)                                        │
│  └─ Embedded policy for agents using SARK SDK                  │
│                                                                 │
│  Layer 2: Protocol Extension (Standards)                       │
│  └─ MCP extension for cross-org agent communication           │
│                                                                 │
│  Layer 3: eBPF (Audit)                                         │
│  └─ Passive observation for agents not using SDK              │
│  └─ Detect shadow/unauthorized A2A traffic                    │
│                                                                 │
│  Layer 4: Sidecar (Legacy)                                     │
│  └─ For agents that can't adopt SDK but use HTTP              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Open Questions

1. **TLS Inspection Legality**: Enterprise can mandate CA installation; home users opt-in. Document implications.

2. **LLM Endpoint Maintenance**: IP ranges change. Need automated discovery/update mechanism.

3. **Performance at Scale**: FlowSpec + inline proxy latency budget? Target <10ms p99.

4. **Privacy in Passive Mode**: Log prompts or just metadata? User-configurable.

5. **YORI Monetization**: Open source core, paid cloud dashboard? Or fully FOSS?

---

## References

- [RFC 5575 - BGP FlowSpec](https://datatracker.ietf.org/doc/html/rfc5575)
- [RFC 8955 - BGP FlowSpec v2](https://datatracker.ietf.org/doc/html/rfc8955)
- [ExaBGP Documentation](https://github.com/Exa-Networks/exabgp)
- [GoBGP Documentation](https://github.com/osrg/gobgp)
- [Envoy ext_authz](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/ext_authz_filter)
- [Pi-hole Architecture](https://docs.pi-hole.net/)
- [Open Policy Agent](https://www.openpolicyagent.org/)

---

**Document Status:** Living document - ideas and architecture in flux
