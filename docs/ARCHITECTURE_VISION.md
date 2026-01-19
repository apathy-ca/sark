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
│  Layer 3: EDR Integration (Enterprise)                         │
│  └─ Consume telemetry from existing EDR                       │
│  └─ Leverage EDR response capabilities                        │
│                                                                 │
│  Layer 4: eBPF (Standalone/Home)                               │
│  └─ For environments without EDR                              │
│  └─ YORI home deployment                                      │
│                                                                 │
│  Layer 5: Sidecar (Legacy)                                     │
│  └─ For agents that can't adopt SDK but use HTTP              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Mode 6: EDR Integration

### Why EDR?

Enterprise environments already have endpoint agents with deep visibility:

```
┌─────────────────────────────────────────────────────────────────┐
│                 What EDR Already Sees                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Process Tree          Network Connections      File Access     │
│  ────────────          ───────────────────      ───────────     │
│  claude-agent (1234)   1234 → api.anthropic.com  /tmp/code.py  │
│   └─ python (1235)     1235 → api.openai.com     ~/.ssh/id_rsa │
│       └─ node (1236)   1236 → localhost:8080     /etc/passwd   │
│                                                                 │
│  User Context          Command Lines            DNS Queries     │
│  ────────────          ─────────────            ───────────     │
│  alice@workstation     python agent.py          api.openai.com │
│  DOMAIN\svc-agent      node mcp-server.js       api.groq.com   │
│                                                                 │
│  Already correlated, timestamped, and queryable                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### EDR Vendor Integrations

| EDR | Integration Method | Capabilities |
|-----|-------------------|--------------|
| **CrowdStrike Falcon** | Streaming API, Falcon Fusion SOAR | Real-time events, automated response |
| **Microsoft Defender** | Microsoft Graph Security API, Sentinel | Process events, network, custom detections |
| **SentinelOne** | Deep Visibility API, Storyline | Full process tree, automated remediation |
| **Carbon Black** | Carbon Black Cloud API | Process, network, file events |
| **Elastic Security** | Elasticsearch queries, Fleet | Custom rules, osquery integration |
| **Wazuh** (OSS) | Wazuh API, Syslog | File integrity, process monitoring |
| **osquery** (OSS) | SQL queries, Fleet | Process, network, file tables |

### Architecture: SARK as EDR Consumer

```
┌─────────────────────────────────────────────────────────────────┐
│                      Enterprise Network                         │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Workstation │  │   Server    │  │  Container  │            │
│  │             │  │             │  │             │            │
│  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │            │
│  │ │EDR Agent│ │  │ │EDR Agent│ │  │ │EDR Agent│ │            │
│  │ └────┬────┘ │  │ └────┬────┘ │  │ └────┬────┘ │            │
│  └──────┼──────┘  └──────┼──────┘  └──────┼──────┘            │
│         │                │                │                    │
│         └────────────────┼────────────────┘                    │
│                          │                                      │
│                          ▼                                      │
│              ┌───────────────────────┐                         │
│              │     EDR Cloud/SIEM    │                         │
│              │  (CrowdStrike, etc.)  │                         │
│              └───────────┬───────────┘                         │
│                          │                                      │
│                          │ Streaming API / Webhook              │
│                          ▼                                      │
│              ┌───────────────────────┐                         │
│              │        SARK           │                         │
│              │                       │                         │
│              │  ┌─────────────────┐  │                         │
│              │  │ EDR Connector   │  │                         │
│              │  │  - CrowdStrike  │  │                         │
│              │  │  - Defender     │  │                         │
│              │  │  - SentinelOne  │  │                         │
│              │  └────────┬────────┘  │                         │
│              │           │           │                         │
│              │           ▼           │                         │
│              │  ┌─────────────────┐  │                         │
│              │  │ LLM/MCP Filter  │  │  Filter for AI-related │
│              │  │                 │  │  process/network activity│
│              │  └────────┬────────┘  │                         │
│              │           │           │                         │
│              │           ▼           │                         │
│              │  ┌─────────────────┐  │                         │
│              │  │ Policy Engine   │  │  Same OPA policies     │
│              │  │ (OPA)           │  │                         │
│              │  └────────┬────────┘  │                         │
│              │           │           │                         │
│              │           ▼           │                         │
│              │  ┌─────────────────┐  │                         │
│              │  │ Response        │  │  Alert, block via EDR, │
│              │  │ Orchestrator    │  │  or just audit         │
│              │  └─────────────────┘  │                         │
│              │                       │                         │
│              └───────────────────────┘                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### CrowdStrike Integration Example

```python
# sark/integrations/crowdstrike.py

from falconpy import EventStreams, RealTimeResponse
import asyncio

class CrowdStrikeConnector:
    """
    Consume CrowdStrike Falcon telemetry for LLM/MCP governance.

    Uses:
    - Event Streams API for real-time process/network events
    - Real Time Response for automated remediation
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        sark_policy_engine: PolicyEngine,
    ):
        self.streams = EventStreams(
            client_id=client_id,
            client_secret=client_secret,
        )
        self.rtr = RealTimeResponse(
            client_id=client_id,
            client_secret=client_secret,
        )
        self.policy = sark_policy_engine

        # LLM-related process and network patterns
        self.llm_indicators = LLMIndicators()

    async def stream_events(self):
        """Stream and filter events for LLM/MCP activity."""

        # Subscribe to relevant event types
        stream = self.streams.stream_events(
            app_id="sark-governance",
            event_types=[
                "ProcessRollup2",      # Process creation
                "NetworkConnectIP4",   # Network connections
                "DnsRequest",          # DNS queries
                "SyntheticProcessRollup2",  # Script execution
            ]
        )

        async for event in stream:
            if llm_event := self._filter_llm_event(event):
                await self._evaluate_and_respond(llm_event)

    def _filter_llm_event(self, event: dict) -> Optional[LLMEvent]:
        """Filter EDR events for LLM/MCP relevance."""

        event_type = event.get("event_type")

        if event_type == "NetworkConnectIP4":
            # Check if connection is to known LLM endpoint
            remote_ip = event.get("RemoteAddressIP4")
            remote_port = event.get("RemotePort")

            if provider := self.llm_indicators.identify_by_ip(remote_ip):
                return LLMEvent(
                    type="llm_api_call",
                    provider=provider,
                    process_id=event.get("TargetProcessId"),
                    process_name=event.get("FileName"),
                    user=event.get("UserName"),
                    device_id=event.get("aid"),
                    timestamp=event.get("timestamp"),
                    raw_event=event,
                )

        elif event_type == "DnsRequest":
            # Check if DNS query is for LLM domain
            domain = event.get("DomainName")

            if provider := self.llm_indicators.identify_by_domain(domain):
                return LLMEvent(
                    type="llm_dns_query",
                    provider=provider,
                    domain=domain,
                    process_id=event.get("ContextProcessId"),
                    user=event.get("UserName"),
                    device_id=event.get("aid"),
                    timestamp=event.get("timestamp"),
                    raw_event=event,
                )

        elif event_type == "ProcessRollup2":
            # Check if process is known MCP server or agent
            process_name = event.get("FileName", "").lower()
            command_line = event.get("CommandLine", "")

            if self.llm_indicators.is_mcp_process(process_name, command_line):
                return LLMEvent(
                    type="mcp_process_start",
                    process_name=process_name,
                    command_line=command_line,
                    parent_process=event.get("ParentBaseFileName"),
                    user=event.get("UserName"),
                    device_id=event.get("aid"),
                    timestamp=event.get("timestamp"),
                    raw_event=event,
                )

        return None

    async def _evaluate_and_respond(self, event: LLMEvent):
        """Evaluate policy and optionally respond via EDR."""

        # Build policy input
        policy_input = {
            "event_type": event.type,
            "user": event.user,
            "device_id": event.device_id,
            "process": {
                "name": event.process_name,
                "id": event.process_id,
                "command_line": getattr(event, "command_line", None),
            },
            "llm": {
                "provider": event.provider,
                "domain": getattr(event, "domain", None),
            },
            "context": {
                "timestamp": event.timestamp,
                "source": "crowdstrike",
            },
        }

        # Evaluate policy
        decision = await self.policy.evaluate(policy_input)

        # Always audit
        await self.audit_log.write(event, decision)

        # Respond based on policy decision
        if not decision.allow:
            if decision.action == "alert":
                await self.alert_manager.send(event, decision)

            elif decision.action == "block":
                # Use CrowdStrike RTR to kill process
                await self._kill_process_via_rtr(
                    device_id=event.device_id,
                    process_id=event.process_id,
                    reason=decision.reason,
                )

            elif decision.action == "isolate":
                # Network isolate the host via CrowdStrike
                await self._isolate_host_via_rtr(
                    device_id=event.device_id,
                    reason=decision.reason,
                )

    async def _kill_process_via_rtr(
        self,
        device_id: str,
        process_id: int,
        reason: str,
    ):
        """Kill a process using CrowdStrike Real Time Response."""

        # Initiate RTR session
        session = self.rtr.init_session(
            device_id=device_id,
            queue_offline=True,
        )

        # Execute kill command
        self.rtr.execute_command(
            session_id=session["session_id"],
            base_command="kill",
            command_string=f"kill {process_id}",
        )

        # Log the response action
        await self.audit_log.write_response(
            action="process_killed",
            device_id=device_id,
            process_id=process_id,
            reason=reason,
        )


class LLMIndicators:
    """Indicators for identifying LLM/MCP activity in EDR telemetry."""

    # Known LLM API IP ranges (simplified - real impl would auto-update)
    LLM_IP_RANGES = {
        "openai": ["104.18.0.0/15", "172.64.0.0/13"],
        "anthropic": ["104.18.32.0/20"],
        "google": ["142.250.0.0/15"],
    }

    # Known LLM API domains
    LLM_DOMAINS = {
        "api.openai.com": "openai",
        "api.anthropic.com": "anthropic",
        "generativelanguage.googleapis.com": "google",
        "api.mistral.ai": "mistral",
        "api.groq.com": "groq",
        "api.cohere.ai": "cohere",
    }

    # MCP process patterns
    MCP_PATTERNS = [
        r"mcp[-_]server",
        r"claude[-_]",
        r"openai[-_]agent",
        r"langchain",
        r"autogen",
        r"crewai",
    ]

    def identify_by_ip(self, ip: str) -> Optional[str]:
        """Identify LLM provider by IP address."""
        import ipaddress
        try:
            addr = ipaddress.ip_address(ip)
            for provider, ranges in self.LLM_IP_RANGES.items():
                for cidr in ranges:
                    if addr in ipaddress.ip_network(cidr):
                        return provider
        except ValueError:
            pass
        return None

    def identify_by_domain(self, domain: str) -> Optional[str]:
        """Identify LLM provider by domain."""
        domain = domain.lower().rstrip(".")
        return self.LLM_DOMAINS.get(domain)

    def is_mcp_process(self, name: str, cmdline: str) -> bool:
        """Check if process appears to be MCP-related."""
        import re
        text = f"{name} {cmdline}".lower()
        return any(re.search(p, text) for p in self.MCP_PATTERNS)
```

### Microsoft Defender Integration Example

```python
# sark/integrations/defender.py

from msgraph import GraphServiceClient
from azure.identity import ClientSecretCredential

class DefenderConnector:
    """
    Consume Microsoft Defender for Endpoint telemetry.

    Uses:
    - Microsoft Graph Security API
    - Advanced Hunting (KQL queries)
    - Live Response for remediation
    """

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        sark_policy_engine: PolicyEngine,
    ):
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )
        self.graph = GraphServiceClient(credential)
        self.policy = sark_policy_engine

    async def run_hunting_query(self) -> list[LLMEvent]:
        """
        Run Advanced Hunting query to find LLM/MCP activity.

        This runs periodically (e.g., every minute) to catch events.
        """

        # KQL query for LLM API connections
        query = """
        let LLMDomains = dynamic([
            "api.openai.com",
            "api.anthropic.com",
            "generativelanguage.googleapis.com",
            "api.mistral.ai"
        ]);
        DeviceNetworkEvents
        | where Timestamp > ago(5m)
        | where RemoteUrl has_any (LLMDomains)
        | project
            Timestamp,
            DeviceId,
            DeviceName,
            InitiatingProcessFileName,
            InitiatingProcessCommandLine,
            InitiatingProcessAccountName,
            RemoteUrl,
            RemoteIP,
            RemotePort
        | join kind=leftouter (
            DeviceProcessEvents
            | where Timestamp > ago(1h)
            | project ProcessId, ParentProcessName=InitiatingProcessFileName
        ) on $left.InitiatingProcessId == $right.ProcessId
        """

        result = await self.graph.security.run_hunting_query(query)

        events = []
        for row in result.results:
            events.append(LLMEvent(
                type="llm_api_call",
                provider=self._domain_to_provider(row["RemoteUrl"]),
                process_name=row["InitiatingProcessFileName"],
                command_line=row["InitiatingProcessCommandLine"],
                user=row["InitiatingProcessAccountName"],
                device_id=row["DeviceId"],
                device_name=row["DeviceName"],
                timestamp=row["Timestamp"],
                raw_event=row,
            ))

        return events

    async def create_custom_detection(self):
        """
        Create a custom detection rule in Defender for LLM policy violations.

        This makes Defender itself alert on suspicious LLM activity.
        """

        detection_rule = {
            "displayName": "SARK: Unauthorized LLM API Access",
            "isEnabled": True,
            "severity": "medium",
            "category": "DataExfiltration",
            "description": "Detects access to LLM APIs from unauthorized processes",
            "recommendedActions": "Review process and user. Check SARK audit logs.",
            "query": """
                let AuthorizedProcesses = dynamic(["python.exe", "node.exe", "java.exe"]);
                let LLMDomains = dynamic(["api.openai.com", "api.anthropic.com"]);
                DeviceNetworkEvents
                | where RemoteUrl has_any (LLMDomains)
                | where InitiatingProcessFileName !in (AuthorizedProcesses)
                | project Timestamp, DeviceName, InitiatingProcessFileName,
                         InitiatingProcessAccountName, RemoteUrl
            """,
        }

        await self.graph.security.custom_detection_rules.post(detection_rule)


### osquery Integration (Open Source)

```sql
-- osquery pack for LLM/MCP monitoring
-- Deploy via Fleet, Kolide, or standalone

{
  "platform": "linux,darwin,windows",
  "queries": {
    "llm_network_connections": {
      "query": "SELECT p.name, p.cmdline, p.uid, s.remote_address, s.remote_port FROM process_open_sockets s JOIN processes p ON s.pid = p.pid WHERE s.remote_address IN ('104.18.6.192', '104.18.7.192') OR s.remote_port = 443",
      "interval": 60,
      "description": "Connections to known LLM API endpoints"
    },
    "mcp_processes": {
      "query": "SELECT name, cmdline, uid, parent, start_time FROM processes WHERE cmdline LIKE '%mcp%' OR cmdline LIKE '%langchain%' OR cmdline LIKE '%autogen%'",
      "interval": 300,
      "description": "Running MCP-related processes"
    },
    "llm_dns_queries": {
      "query": "SELECT * FROM dns_resolvers WHERE nameserver LIKE '%openai%' OR nameserver LIKE '%anthropic%'",
      "interval": 600,
      "description": "DNS configuration pointing to LLM providers"
    },
    "env_api_keys": {
      "query": "SELECT key, value FROM process_envs WHERE key LIKE '%API_KEY%' OR key LIKE '%OPENAI%' OR key LIKE '%ANTHROPIC%'",
      "interval": 3600,
      "description": "Processes with LLM API keys in environment"
    }
  }
}
```

### SARK EDR Connector Interface

```python
# sark/integrations/base.py

from abc import ABC, abstractmethod
from typing import AsyncIterator

class EDRConnector(ABC):
    """Base class for EDR integrations."""

    @abstractmethod
    async def stream_events(self) -> AsyncIterator[LLMEvent]:
        """Stream LLM-related events from EDR."""
        pass

    @abstractmethod
    async def kill_process(self, device_id: str, process_id: int) -> bool:
        """Kill a process via EDR response capabilities."""
        pass

    @abstractmethod
    async def isolate_host(self, device_id: str) -> bool:
        """Network isolate a host via EDR."""
        pass

    @abstractmethod
    async def run_query(self, query: str) -> list[dict]:
        """Run a hunting/search query against EDR data."""
        pass


# Factory for EDR connectors
def get_edr_connector(config: EDRConfig) -> EDRConnector:
    """Get the appropriate EDR connector based on configuration."""

    connectors = {
        "crowdstrike": CrowdStrikeConnector,
        "defender": DefenderConnector,
        "sentinelone": SentinelOneConnector,
        "carbonblack": CarbonBlackConnector,
        "elastic": ElasticSecurityConnector,
        "wazuh": WazuhConnector,
        "osquery": OsqueryConnector,
    }

    connector_class = connectors.get(config.vendor)
    if not connector_class:
        raise ValueError(f"Unknown EDR vendor: {config.vendor}")

    return connector_class(**config.credentials)
```

### EDR vs Custom eBPF Comparison

| Aspect | Custom eBPF | EDR Integration |
|--------|-------------|-----------------|
| **Deployment** | New agent to deploy | Already deployed |
| **Approval** | Security team review | Already approved |
| **Maintenance** | You maintain probes | Vendor maintains |
| **Coverage** | Linux only (custom) | Cross-platform |
| **Response** | Custom implementation | Built-in RTR/Live Response |
| **Correlation** | Build yourself | EDR correlates for you |
| **Cost** | Engineering time | EDR license (existing) |
| **Latency** | Real-time | Near real-time (1-60s) |

### When to Use Each

```
┌─────────────────────────────────────────────────────────────────┐
│                    Decision Matrix                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Enterprise with EDR?                                          │
│  ├─ YES → Use EDR integration                                  │
│  │        (CrowdStrike, Defender, SentinelOne, etc.)          │
│  │                                                             │
│  └─ NO → Consider:                                             │
│          ├─ osquery (free, cross-platform)                    │
│          ├─ Wazuh (free, full SIEM)                           │
│          └─ Custom eBPF (Linux only, most control)            │
│                                                                 │
│  Home/YORI?                                                    │
│  └─ Custom eBPF or osquery                                    │
│     (No enterprise EDR, need lightweight solution)            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Mode 7: Encrypted Tunnel Detection

### The Problem

LLM traffic can hide inside encrypted tunnels, evading all previous detection methods:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Evasion Scenarios                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  What SARK Sees              What's Actually Happening          │
│  ──────────────              ────────────────────────           │
│                                                                 │
│  SSH to jumphost.corp     →  SSH tunnel to api.openai.com      │
│  WireGuard to VPN         →  Claude API calls inside VPN       │
│  HTTPS to cloudflare      →  DoH hiding DNS for api.anthropic  │
│  TCP to proxy.internal    →  SOCKS proxy to api.mistral.ai     │
│  QUIC to relay.corp       →  Cloudflare Tunnel to LLM          │
│                                                                 │
│  All our detection methods see the tunnel, not the payload     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Tunnel Types to Detect

| Tunnel Type | Protocol | Detection Difficulty |
|-------------|----------|---------------------|
| SSH Port Forward | TCP/22 | Medium - known ports, long-lived |
| SSH Dynamic (SOCKS) | TCP/22 | Medium - same as above |
| WireGuard VPN | UDP/51820 | Hard - looks like noise |
| OpenVPN | UDP/1194 or TCP/443 | Medium - signatures exist |
| IPsec | ESP/AH | Medium - protocol numbers |
| Cloudflare Tunnel | QUIC/443 | Hard - legitimate traffic |
| ngrok | HTTPS/443 | Hard - looks like normal HTTPS |
| Tailscale | WireGuard-based | Hard - peer-to-peer mesh |
| Tor | TCP/9001,9030 | Easy - known ports/nodes |
| SOCKS Proxy | TCP/1080 | Easy - known port |
| HTTP CONNECT | TCP/3128,8080 | Medium - proxy signatures |
| DNS-over-HTTPS | HTTPS/443 | Hard - looks like HTTPS |
| DNS-over-TLS | TLS/853 | Medium - known port |
| ICMP Tunnel | ICMP | Medium - unusual ICMP patterns |
| DNS Tunnel | UDP/53 | Medium - entropy analysis |

### Detection Strategies

#### Strategy 1: JA3/JA4 TLS Fingerprinting

TLS handshakes have unique fingerprints. LLM client libraries have recognizable patterns:

```python
# sark/tunnel_detection/ja4_fingerprints.py

# Known LLM client JA4 fingerprints
LLM_CLIENT_FINGERPRINTS = {
    # OpenAI Python SDK
    "t13d1516h2_8daaf6152771_b0da82dd1658": {
        "client": "openai-python",
        "confidence": 0.95,
    },
    # Anthropic Python SDK
    "t13d1517h2_8daaf6152771_e5627efa2ab1": {
        "client": "anthropic-python",
        "confidence": 0.95,
    },
    # httpx (common in LLM SDKs)
    "t13d1516h2_8daaf6152771_02713d6af862": {
        "client": "httpx",
        "confidence": 0.7,  # Lower - used for many things
    },
    # aiohttp
    "t13d1516h2_8daaf6152771_6e2c0f5a3b1d": {
        "client": "aiohttp",
        "confidence": 0.6,
    },
}

# Known tunnel software JA4 fingerprints
TUNNEL_FINGERPRINTS = {
    "t13d1516h2_5b57614c22b0_06cda9e17597": "cloudflared",
    "t13d1516h2_8daaf6152771_3c5a54f6e39d": "ngrok",
    "t13d1516h2_2bab15409345_b8cc45678def": "tailscale",
}

class JA4Analyzer:
    """Analyze JA4 fingerprints to detect LLM traffic and tunnels."""

    def __init__(self, fingerprint_db: dict):
        self.fingerprints = fingerprint_db

    def analyze_tls_handshake(self, client_hello: bytes) -> TLSAnalysis:
        """Extract and analyze JA4 fingerprint from TLS ClientHello."""

        ja4 = self._compute_ja4(client_hello)
        ja4s = self._compute_ja4s(client_hello)  # Server name hash
        ja4h = self._compute_ja4h(client_hello)  # HTTP/2 fingerprint

        result = TLSAnalysis(
            ja4=ja4,
            ja4s=ja4s,
            ja4h=ja4h,
        )

        # Check against known fingerprints
        if match := self.fingerprints.get(ja4):
            result.client = match["client"]
            result.confidence = match["confidence"]
            result.is_llm_client = match["client"] in LLM_CLIENT_FINGERPRINTS

        # Check for tunnel software
        if tunnel := TUNNEL_FINGERPRINTS.get(ja4):
            result.is_tunnel = True
            result.tunnel_type = tunnel

        return result
```

#### Strategy 2: Traffic Pattern Analysis (ML-based)

LLM API calls have distinctive traffic patterns even when encrypted:

```python
# sark/tunnel_detection/traffic_patterns.py

import numpy as np
from dataclasses import dataclass

@dataclass
class FlowFeatures:
    """Features extracted from an encrypted flow for ML classification."""

    # Packet timing
    inter_arrival_times: list[float]  # Time between packets

    # Packet sizes
    packet_sizes: list[int]           # Size of each packet
    payload_sizes: list[int]          # Payload without headers

    # Direction
    upload_bytes: int
    download_bytes: int
    upload_packets: int
    download_packets: int

    # Duration
    flow_duration: float

    # Derived features
    @property
    def avg_packet_size(self) -> float:
        return np.mean(self.packet_sizes)

    @property
    def packet_size_variance(self) -> float:
        return np.var(self.packet_sizes)

    @property
    def upload_download_ratio(self) -> float:
        if self.download_bytes == 0:
            return float('inf')
        return self.upload_bytes / self.download_bytes

    @property
    def burstiness(self) -> float:
        """Measure of traffic burstiness (LLM streaming has characteristic patterns)."""
        if len(self.inter_arrival_times) < 2:
            return 0
        return np.std(self.inter_arrival_times) / np.mean(self.inter_arrival_times)


class LLMTrafficClassifier:
    """
    ML classifier to detect LLM API traffic patterns in encrypted flows.

    LLM traffic has distinctive patterns:
    - Request: Small upload (prompt), then wait
    - Response: Streaming download (tokens), bursty
    - Timing: Characteristic token generation cadence (~50-100ms between chunks)
    """

    def __init__(self, model_path: str):
        self.model = self._load_model(model_path)

        # Characteristic LLM patterns
        self.LLM_PATTERNS = {
            "chat_completion": {
                "upload_download_ratio": (0.01, 0.3),  # Small prompt, large response
                "burstiness": (0.5, 2.0),              # Bursty streaming
                "inter_arrival_mean_ms": (30, 150),    # Token timing
            },
            "embedding": {
                "upload_download_ratio": (0.5, 5.0),   # Larger input
                "response_size": (1000, 10000),        # Fixed-size embedding
                "duration_ms": (100, 2000),            # Quick response
            },
        }

    def extract_features(self, flow: Flow) -> np.ndarray:
        """Extract ML features from encrypted flow."""

        features = FlowFeatures(
            inter_arrival_times=flow.get_inter_arrival_times(),
            packet_sizes=flow.get_packet_sizes(),
            payload_sizes=flow.get_payload_sizes(),
            upload_bytes=flow.upload_bytes,
            download_bytes=flow.download_bytes,
            upload_packets=flow.upload_packets,
            download_packets=flow.download_packets,
            flow_duration=flow.duration,
        )

        return np.array([
            features.avg_packet_size,
            features.packet_size_variance,
            features.upload_download_ratio,
            features.burstiness,
            np.mean(features.inter_arrival_times) * 1000,  # Convert to ms
            np.std(features.inter_arrival_times) * 1000,
            features.flow_duration,
            features.upload_packets,
            features.download_packets,
            # Packet size histogram (10 bins)
            *np.histogram(features.packet_sizes, bins=10, range=(0, 1500))[0],
        ])

    def classify(self, flow: Flow) -> TrafficClassification:
        """Classify encrypted flow as LLM traffic or not."""

        features = self.extract_features(flow)

        # ML prediction
        proba = self.model.predict_proba(features.reshape(1, -1))[0]

        return TrafficClassification(
            is_llm_traffic=proba[1] > 0.7,
            confidence=max(proba),
            predicted_type=self._predict_llm_type(features),
            features=features,
        )

    def _predict_llm_type(self, features: np.ndarray) -> str:
        """Predict specific LLM API type (chat, embedding, etc.)."""
        # Heuristic-based for now, could be another ML model
        ratio = features[2]  # upload_download_ratio

        if ratio < 0.3:
            return "chat_completion_streaming"
        elif ratio < 1.0:
            return "chat_completion"
        else:
            return "embedding"
```

#### Strategy 3: Tunnel Endpoint Intelligence

Maintain a database of known tunnel endpoints and flag traffic to them:

```python
# sark/tunnel_detection/endpoint_intel.py

@dataclass
class TunnelEndpoint:
    """Known tunnel/proxy endpoint."""

    ip_ranges: list[str]
    domains: list[str]
    service: str           # "cloudflare_tunnel", "ngrok", "tailscale", etc.
    risk_level: str        # "high", "medium", "low"
    can_inspect: bool      # Can we potentially inspect this?
    notes: str

TUNNEL_ENDPOINTS = {
    "cloudflare_tunnel": TunnelEndpoint(
        ip_ranges=["198.41.192.0/24", "198.41.200.0/24"],  # Cloudflare Tunnel IPs
        domains=["*.trycloudflare.com", "*.cfargotunnel.com"],
        service="cloudflare_tunnel",
        risk_level="high",
        can_inspect=False,  # End-to-end encrypted
        notes="Cloudflare Argo Tunnel - can hide any traffic",
    ),
    "ngrok": TunnelEndpoint(
        ip_ranges=["3.134.0.0/16"],  # ngrok AWS ranges
        domains=["*.ngrok.io", "*.ngrok-free.app"],
        service="ngrok",
        risk_level="high",
        can_inspect=False,
        notes="ngrok tunnels - commonly used for dev, also exfil",
    ),
    "tailscale": TunnelEndpoint(
        ip_ranges=["100.64.0.0/10"],  # CGNAT range used by Tailscale
        domains=["*.ts.net", "*.tailscale.com"],
        service="tailscale",
        risk_level="medium",
        can_inspect=False,
        notes="Tailscale mesh VPN - P2P, hard to intercept",
    ),
    "tor_exit_nodes": TunnelEndpoint(
        ip_ranges=[],  # Loaded dynamically from Tor directory
        domains=[".onion"],
        service="tor",
        risk_level="high",
        can_inspect=False,
        notes="Tor network - anonymizing proxy",
    ),
    "mullvad_vpn": TunnelEndpoint(
        ip_ranges=["45.83.220.0/22", "141.98.252.0/22"],
        domains=["*.mullvad.net"],
        service="mullvad",
        risk_level="medium",
        can_inspect=False,
        notes="Privacy VPN - no logs claimed",
    ),
}

class TunnelEndpointDetector:
    """Detect traffic to known tunnel endpoints."""

    def __init__(self):
        self.endpoints = TUNNEL_ENDPOINTS
        self._load_dynamic_lists()

    def _load_dynamic_lists(self):
        """Load dynamically updated lists (Tor exits, etc.)."""
        # Tor exit nodes
        self.endpoints["tor_exit_nodes"].ip_ranges = self._fetch_tor_exits()

        # Known VPN providers
        self._load_vpn_provider_ips()

    def check_connection(
        self,
        dst_ip: str,
        dst_port: int,
        dst_domain: str | None,
    ) -> TunnelDetection | None:
        """Check if connection is to a known tunnel endpoint."""

        import ipaddress

        for name, endpoint in self.endpoints.items():
            # Check IP ranges
            try:
                addr = ipaddress.ip_address(dst_ip)
                for cidr in endpoint.ip_ranges:
                    if addr in ipaddress.ip_network(cidr):
                        return TunnelDetection(
                            tunnel_type=name,
                            endpoint=endpoint,
                            match_type="ip",
                            confidence=0.9,
                        )
            except ValueError:
                pass

            # Check domains
            if dst_domain:
                for pattern in endpoint.domains:
                    if self._domain_matches(dst_domain, pattern):
                        return TunnelDetection(
                            tunnel_type=name,
                            endpoint=endpoint,
                            match_type="domain",
                            confidence=0.95,
                        )

        return None
```

#### Strategy 4: Behavioral Analysis

Look at what happens BEFORE and AFTER the tunnel:

```python
# sark/tunnel_detection/behavioral.py

class TunnelBehaviorAnalyzer:
    """
    Analyze process behavior around tunnel connections.

    Key insight: Even if we can't see inside the tunnel, we can see:
    - What process created the tunnel
    - What that process does before/after
    - File access patterns
    - Other network connections
    """

    def __init__(self, edr_connector: EDRConnector):
        self.edr = edr_connector

    async def analyze_tunnel_process(
        self,
        process_id: int,
        device_id: str,
    ) -> TunnelBehaviorAnalysis:
        """Analyze the process that created a tunnel connection."""

        # Get process tree from EDR
        process_tree = await self.edr.get_process_tree(device_id, process_id)

        # Get file access by this process
        file_access = await self.edr.get_file_events(
            device_id,
            process_id,
            time_window_minutes=5,
        )

        # Get other network connections by this process
        other_connections = await self.edr.get_network_events(
            device_id,
            process_id,
            time_window_minutes=5,
        )

        # Analyze patterns
        analysis = TunnelBehaviorAnalysis()

        # Check for LLM SDK files
        llm_indicators = self._check_llm_file_access(file_access)
        if llm_indicators:
            analysis.llm_likelihood = "high"
            analysis.evidence.append(f"Accessed LLM SDK files: {llm_indicators}")

        # Check for API key access
        if self._accessed_credentials(file_access):
            analysis.llm_likelihood = "high"
            analysis.evidence.append("Accessed credential files (.env, secrets)")

        # Check process command line
        if self._cmdline_has_llm_indicators(process_tree.command_line):
            analysis.llm_likelihood = "high"
            analysis.evidence.append(f"Command line indicates LLM: {process_tree.command_line}")

        # Check environment variables (from EDR)
        env_vars = await self.edr.get_process_environment(device_id, process_id)
        if self._has_llm_env_vars(env_vars):
            analysis.llm_likelihood = "high"
            analysis.evidence.append("Has OPENAI_API_KEY or similar in environment")

        return analysis

    def _check_llm_file_access(self, file_events: list) -> list[str]:
        """Check for access to LLM-related files."""

        llm_patterns = [
            r"openai",
            r"anthropic",
            r"langchain",
            r"llama",
            r"\.gguf$",        # LLM model files
            r"\.safetensors$", # Model weights
            r"transformers",
            r"huggingface",
        ]

        matches = []
        for event in file_events:
            for pattern in llm_patterns:
                if re.search(pattern, event.file_path, re.I):
                    matches.append(event.file_path)

        return matches

    def _has_llm_env_vars(self, env_vars: dict) -> bool:
        """Check for LLM API keys in environment."""

        llm_env_patterns = [
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GOOGLE_API_KEY",
            "MISTRAL_API_KEY",
            "GROQ_API_KEY",
            "HUGGINGFACE_TOKEN",
            "HF_TOKEN",
        ]

        return any(key in env_vars for key in llm_env_patterns)
```

#### Strategy 5: DNS Intelligence (Even with DoH)

Even with DNS-over-HTTPS, we can learn from DNS patterns:

```python
# sark/tunnel_detection/dns_intel.py

class DNSIntelligence:
    """
    DNS-based detection even in presence of DoH/DoT.

    Strategies:
    1. Monitor corporate DNS (before DoH)
    2. Detect DoH providers and flag
    3. Analyze SNI in TLS (not encrypted until ECH)
    4. Certificate transparency logs
    """

    def __init__(self):
        # Known DoH providers
        self.doh_providers = {
            "cloudflare": ["1.1.1.1", "1.0.0.1", "cloudflare-dns.com"],
            "google": ["8.8.8.8", "8.8.4.4", "dns.google"],
            "quad9": ["9.9.9.9", "dns.quad9.net"],
            "nextdns": ["45.90.28.0/24", "dns.nextdns.io"],
        }

        # LLM domains to watch for in SNI
        self.llm_domains = [
            "api.openai.com",
            "api.anthropic.com",
            "generativelanguage.googleapis.com",
            "api.mistral.ai",
            "api.groq.com",
            "api.cohere.ai",
            "api-inference.huggingface.co",
        ]

    def analyze_tls_sni(self, client_hello: bytes) -> SNIAnalysis:
        """
        Extract and analyze SNI from TLS ClientHello.

        Note: SNI is plaintext until ECH (Encrypted Client Hello) is deployed.
        This remains a valuable detection point for now.
        """

        sni = self._extract_sni(client_hello)

        if not sni:
            return SNIAnalysis(
                sni=None,
                is_llm_domain=False,
                is_doh_provider=False,
                notes="No SNI present (possible ECH or non-TLS)"
            )

        # Check for LLM domains
        is_llm = any(sni.endswith(domain) for domain in self.llm_domains)

        # Check for DoH providers
        is_doh = any(
            sni.endswith(provider)
            for providers in self.doh_providers.values()
            for provider in providers
            if isinstance(provider, str) and not provider[0].isdigit()
        )

        return SNIAnalysis(
            sni=sni,
            is_llm_domain=is_llm,
            is_doh_provider=is_doh,
            notes="SNI visible - not using ECH" if sni else None
        )

    def monitor_certificate_transparency(self, domain: str) -> list[CTLogEntry]:
        """
        Query Certificate Transparency logs for LLM-related certificates.

        Even if traffic is tunneled, new certificates for LLM domains
        appear in CT logs. Organizations using private LLM proxies
        might issue internal certs we can detect.
        """

        # Query CT logs via crt.sh or similar
        ct_entries = self._query_ct_logs(domain)

        llm_related = []
        for entry in ct_entries:
            # Check for LLM-related SANs
            for san in entry.subject_alt_names:
                if any(llm in san for llm in ["openai", "anthropic", "llm", "ai-proxy"]):
                    llm_related.append(entry)

        return llm_related
```

### Integrated Tunnel Detection Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                  Tunnel Detection Pipeline                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Network Traffic                                                │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────┐                                           │
│  │ 1. Endpoint     │  Check against known tunnel IPs/domains   │
│  │    Intel        │  (ngrok, Cloudflare, Tailscale, etc.)     │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │ 2. JA4          │  TLS fingerprint analysis                 │
│  │    Fingerprint  │  Detect LLM client libraries              │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │ 3. SNI/DNS      │  Domain analysis (until ECH)              │
│  │    Analysis     │  DoH provider detection                   │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │ 4. Traffic      │  ML on packet sizes/timing                │
│  │    Patterns     │  Detect LLM streaming patterns            │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │ 5. EDR          │  What is the tunnel process doing?        │
│  │    Correlation  │  File access, env vars, command line      │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │ Detection       │  Combine signals → confidence score       │
│  │ Fusion          │  Alert, block, or audit                   │
│  └─────────────────┘                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Detection Fusion Logic

```python
# sark/tunnel_detection/fusion.py

@dataclass
class TunnelDetectionResult:
    """Combined result from all detection strategies."""

    # Individual signals
    endpoint_intel: TunnelDetection | None
    ja4_analysis: TLSAnalysis | None
    sni_analysis: SNIAnalysis | None
    traffic_pattern: TrafficClassification | None
    behavioral: TunnelBehaviorAnalysis | None

    # Combined assessment
    is_tunnel: bool
    tunnel_type: str | None
    contains_llm_traffic: bool
    llm_confidence: float

    # Recommended action
    action: str  # "allow", "alert", "block", "inspect"
    reason: str

class DetectionFusion:
    """Combine signals from multiple detectors."""

    def __init__(self, policy_engine: PolicyEngine):
        self.policy = policy_engine

        # Weights for different signals
        self.weights = {
            "endpoint_intel": 0.9,      # High confidence if known tunnel
            "ja4_llm_client": 0.8,      # LLM client fingerprint
            "sni_llm_domain": 0.95,     # Direct LLM domain (very high)
            "traffic_pattern": 0.7,     # ML-based (good but not definitive)
            "behavioral_env_vars": 0.85, # API keys in env
            "behavioral_files": 0.6,    # LLM files accessed
        }

    def fuse(
        self,
        endpoint_intel: TunnelDetection | None,
        ja4_analysis: TLSAnalysis | None,
        sni_analysis: SNIAnalysis | None,
        traffic_pattern: TrafficClassification | None,
        behavioral: TunnelBehaviorAnalysis | None,
    ) -> TunnelDetectionResult:
        """Combine all signals into a single detection result."""

        signals = []

        # Collect signals with weights
        if endpoint_intel:
            signals.append(("endpoint_intel", endpoint_intel.confidence))

        if ja4_analysis and ja4_analysis.is_llm_client:
            signals.append(("ja4_llm_client", ja4_analysis.confidence))

        if sni_analysis and sni_analysis.is_llm_domain:
            signals.append(("sni_llm_domain", 0.95))

        if traffic_pattern and traffic_pattern.is_llm_traffic:
            signals.append(("traffic_pattern", traffic_pattern.confidence))

        if behavioral:
            if behavioral.has_llm_env_vars:
                signals.append(("behavioral_env_vars", 0.85))
            if behavioral.llm_file_access:
                signals.append(("behavioral_files", 0.6))

        # Calculate weighted confidence
        if not signals:
            llm_confidence = 0.0
        else:
            weighted_sum = sum(
                self.weights.get(sig, 0.5) * conf
                for sig, conf in signals
            )
            total_weight = sum(
                self.weights.get(sig, 0.5)
                for sig, _ in signals
            )
            llm_confidence = weighted_sum / total_weight

        # Determine if tunnel
        is_tunnel = endpoint_intel is not None
        tunnel_type = endpoint_intel.tunnel_type if endpoint_intel else None

        # Determine action based on policy
        action, reason = self._determine_action(
            is_tunnel=is_tunnel,
            llm_confidence=llm_confidence,
            signals=signals,
        )

        return TunnelDetectionResult(
            endpoint_intel=endpoint_intel,
            ja4_analysis=ja4_analysis,
            sni_analysis=sni_analysis,
            traffic_pattern=traffic_pattern,
            behavioral=behavioral,
            is_tunnel=is_tunnel,
            tunnel_type=tunnel_type,
            contains_llm_traffic=llm_confidence > 0.7,
            llm_confidence=llm_confidence,
            action=action,
            reason=reason,
        )

    def _determine_action(
        self,
        is_tunnel: bool,
        llm_confidence: float,
        signals: list,
    ) -> tuple[str, str]:
        """Determine action based on detection and policy."""

        # High confidence LLM in tunnel → alert or block
        if is_tunnel and llm_confidence > 0.8:
            return ("alert", f"High confidence LLM traffic in tunnel ({llm_confidence:.0%})")

        # Known high-risk tunnel → alert
        if is_tunnel:
            return ("alert", f"Traffic to known tunnel endpoint")

        # Moderate confidence LLM → audit
        if llm_confidence > 0.5:
            return ("audit", f"Possible LLM traffic ({llm_confidence:.0%})")

        return ("allow", "No significant indicators")
```

### Policy Response Options

```rego
# opa/policies/tunnel_detection.rego

package sark.tunnel

# Block known tunnel endpoints entirely
deny_tunnel {
    input.tunnel_detection.is_tunnel
    input.tunnel_detection.tunnel_type in ["ngrok", "cloudflare_tunnel", "tor"]
    not tunnel_allowed_for_user
}

# Alert on suspected LLM traffic in tunnels
alert_llm_in_tunnel {
    input.tunnel_detection.is_tunnel
    input.tunnel_detection.contains_llm_traffic
    input.tunnel_detection.llm_confidence > 0.7
}

# Allow corporate VPN but audit LLM traffic
audit_llm_in_vpn {
    input.tunnel_detection.tunnel_type == "corporate_vpn"
    input.tunnel_detection.contains_llm_traffic
}

# Exceptions for approved users/processes
tunnel_allowed_for_user {
    input.user.groups[_] == "tunnel-exemption"
}

tunnel_allowed_for_user {
    input.process.name in approved_tunnel_processes
}

approved_tunnel_processes = {
    "corporate-vpn-client",
    "approved-ssh-client",
}
```

### Limitations and Mitigations

| Limitation | Mitigation |
|------------|------------|
| **ECH hides SNI** | JA4 + traffic analysis + behavioral |
| **Novel tunnel software** | ML-based pattern detection |
| **Steganography** | Out of scope (very hard) |
| **Low-and-slow exfil** | Long-term behavioral baselines |
| **Encrypted DNS everywhere** | Monitor DoH endpoints, CT logs |
| **ML evasion** | Multiple orthogonal signals, ensemble |

---

## Mode 8: Avian Carrier Detection (RFC 1149)

> *"The most secure network is the one nobody suspects."*

**Status:** 🚧 **Permanently Awaiting Feline Subject Matter Expert (SME) Review**
- Implementation blocked pending cat availability during business hours (1000-1600)
- Agent recruitment ongoing, but nap schedules remain non-negotiable
- Alternative laser-pointer-based motivation strategies under evaluation

### Threat Model

Advanced threat actors may attempt to bypass all network-based governance by
exfiltrating LLM prompts and responses via [RFC 1149](https://datatracker.ietf.org/doc/html/rfc1149)
(IP over Avian Carriers) or its QoS-enabled successor [RFC 2549](https://datatracker.ietf.org/doc/html/rfc2549).

**Attack Vector:**
```
┌─────────────────┐    microSD card     ┌─────────────┐
│  Rogue Agent    │ ──────────────────► │   🐦 Pigeon │ ───► External LLM
│  (air-gapped)   │    in leg capsule   │   (carrier) │
└─────────────────┘                     └─────────────┘
```

While packet loss is high (~55% per RFC 1149 field tests), latency-tolerant
batch inference remains viable. Traditional network monitoring is ineffective.

### Solution: FATS (Feline Autonomous Tracking System)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FATS Architecture                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────┐    Visual     ┌──────────────┐    Alert    ┌───────┐ │
│  │   🐱     │ ─────────────►│ SARK Policy  │ ──────────► │ SIEM  │ │
│  │  (CAT)   │   Detection   │   Engine     │   + Logs    │       │ │
│  └──────────┘               └──────────────┘             └───────┘ │
│       │                                                             │
│       │ Autonomous                                                  │
│       │ Interception                                                │
│       ▼                                                             │
│  ┌──────────┐                                                       │
│  │ 🐦💥     │  ◄── Carrier neutralized, payload recovered          │
│  └──────────┘                                                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### FATS Agent Implementation

```python
# sark/agents/fats.py
"""
Feline Autonomous Tracking System (FATS)

An ML-powered avian carrier detection and interception system
leveraging biological neural networks (cats).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import asyncio


class CarrierType(Enum):
    """RFC 1149 carrier classifications."""
    PIGEON_HOMING = "columba_livia_domestica"
    PIGEON_RACING = "columba_livia_racing"
    CROW = "corvus_brachyrhynchos"  # Experimental
    DRONE_DISGUISED = "quadcopter_feathered"


class InterceptionStatus(Enum):
    """FATS engagement outcomes."""
    DETECTED = "detected"
    TRACKED = "tracked"
    INTERCEPTED = "intercepted"
    PAYLOAD_RECOVERED = "payload_recovered"
    ESCAPED = "escaped"  # Acceptable loss
    CAT_DISTRACTED = "cat_distracted"  # By laser pointer


@dataclass
class AvianCarrier:
    """Detected RFC 1149 carrier."""
    carrier_type: CarrierType
    heading: float  # degrees
    altitude: float  # meters
    estimated_payload_kb: float
    leg_band_id: Optional[str] = None


@dataclass
class FATSAgent:
    """A FATS-enrolled feline agent."""
    agent_id: str
    name: str
    breed: str
    hunting_score: float  # 0.0 - 1.0
    attention_span_seconds: float
    currently_napping: bool = True


class FATSController:
    """
    Coordinates FATS agents for RFC 1149 interception.

    Note: Agent availability varies by time of day.
    Peak performance: 0300-0500, 1800-2000
    Unavailable: 1000-1600 (nap time)
    """

    def __init__(self, agents: list[FATSAgent]):
        self.agents = agents
        self.active_intercepts = {}

    async def detect_carrier(
        self,
        visual_feed: bytes,
    ) -> Optional[AvianCarrier]:
        """
        Analyze visual feed for RFC 1149 carriers.

        Uses a highly sophisticated detection algorithm:
        - Bird-shaped object detection
        - Unusual flight path analysis
        - Leg capsule identification
        - Suspiciously regular timing patterns
        """
        # Cats have 200-degree field of view
        # Detection range: ~50 meters (depending on bird size)
        # False positive rate: HIGH (leaves, butterflies, red dots)
        pass

    async def dispatch_agent(
        self,
        carrier: AvianCarrier,
    ) -> InterceptionStatus:
        """
        Dispatch nearest available FATS agent.

        Selection criteria:
        1. Not currently napping
        2. Not distracted by other stimulus
        3. Within pouncing range
        4. Sufficiently motivated (hunger level)
        """
        available = [
            a for a in self.agents
            if not a.currently_napping
            and a.attention_span_seconds > 30
        ]

        if not available:
            # All agents napping - this is expected ~16 hours/day
            return InterceptionStatus.ESCAPED

        # Select highest hunting score
        agent = max(available, key=lambda a: a.hunting_score)

        # Autonomous engagement - no further control possible
        # Outcome determined by: agent skill, carrier evasion,
        # random environmental factors (laser pointers, treats)

        return await self._await_engagement(agent, carrier)

    async def _await_engagement(
        self,
        agent: FATSAgent,
        carrier: AvianCarrier,
    ) -> InterceptionStatus:
        """Wait for engagement outcome. May take a while."""

        # Engagement timeout based on agent attention span
        try:
            async with asyncio.timeout(agent.attention_span_seconds):
                # ... biological neural network processing ...
                pass
        except asyncio.TimeoutError:
            return InterceptionStatus.CAT_DISTRACTED

        # Placeholder - actual outcome from field sensors
        return InterceptionStatus.INTERCEPTED

    async def recover_payload(
        self,
        intercept_location: tuple[float, float],
    ) -> Optional[bytes]:
        """
        Attempt to recover payload from intercepted carrier.

        Warning: Payload may be damaged. microSD cards are
        surprisingly durable but not rated for this use case.

        Note: Agent may have 'relocated' payload. Check:
        - Under furniture
        - In shoes
        - Proudly displayed on pillow
        """
        pass
```

### Integration with SARK Policy Engine

```rego
# opa/policies/rfc1149.rego

package sark.avian

# Alert on any RFC 1149 carrier detection
alert_carrier_detected {
    input.fats.carrier_detected
    input.fats.carrier.estimated_payload_kb > 0
}

# Escalate if multiple carriers in short window
escalate_coordinated_exfil {
    count(input.fats.recent_detections) > 3
    time_window_minutes(input.fats.recent_detections) < 30
}

# Log successful intercepts for threat intel
log_intercept {
    input.fats.status == "intercepted"
    input.fats.payload_recovered
}

# Alert if carrier escaped with payload
alert_exfil_succeeded {
    input.fats.status == "escaped"
    input.fats.carrier.estimated_payload_kb > 100
}

# Maintenance alert - all agents napping
alert_coverage_gap {
    count([a | a := input.fats.agents[_]; not a.currently_napping]) == 0
}
```

### Deployment Considerations

| Factor | Consideration |
|--------|---------------|
| **Agent Availability** | 16-18 hours napping per day |
| **False Positive Rate** | Very high (anything that moves) |
| **Interception Success** | Varies by agent (40-90%) |
| **Payload Recovery** | ~60% (agent may "relocate" payload) |
| **Operating Temperature** | Agents prefer 20-25°C |
| **Maintenance** | Daily feeding, weekly veterinary |

### Limitations

1. **Weather Dependence**: Agents reluctant to operate in rain
2. **Nocturnal Bias**: Peak performance at dawn/dusk only
3. **Attention Issues**: Laser pointers are an effective FATS-DoS
4. **Union Rules**: Agents demand 16+ hours rest per day
5. **Payload Integrity**: Not guaranteed after interception

### References

- [RFC 1149 - IP over Avian Carriers](https://datatracker.ietf.org/doc/html/rfc1149)
- [RFC 2549 - IP over Avian Carriers with QoS](https://datatracker.ietf.org/doc/html/rfc2549)
- [RFC 6214 - IPv6 over Avian Carriers](https://datatracker.ietf.org/doc/html/rfc6214)
- Bergen Linux User Group, 2001 - First RFC 1149 Implementation (55% packet loss)

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
