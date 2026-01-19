# YORI - Home LLM Gateway Project Plan

**Repository:** `apathy-ca/yori` (new repo)
**Tagline:** "Zero-trust LLM governance for your home network"
**Target:** OPNsense router plugin, home users

---

## Project Overview

### Vision
Bring enterprise-grade LLM governance to home networks with a lightweight router appliance that observes, logs, and optionally controls LLM traffic.

### Goals
- **Low Resource** - Run on home router (512MB RAM, single core)
- **Easy Setup** - OPNsense plugin, click-to-install
- **Privacy First** - All data stays on-premise
- **Progressive** - Start with observation, optionally enable control
- **Educational** - Teach families about AI usage patterns

### Non-Goals (v0.1.0)
- ❌ Not a full enterprise SARK deployment
- ❌ Not a cloud service
- ❌ Not multi-tenant
- ❌ Not highly available (single router)

---

## Architecture

### Component Stack

```
┌─────────────────────────────────────────────────────────┐
│              OPNsense Router (FreeBSD)                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  OPNsense Plugin (PHP/MVC)                         │ │
│  │  - Web UI for config/dashboard                     │ │
│  │  - Service management (start/stop)                 │ │
│  │  - Log viewer                                      │ │
│  └────────────────┬───────────────────────────────────┘ │
│                   │                                      │
│  ┌────────────────▼───────────────────────────────────┐ │
│  │  YORI Service (Python + Rust)                      │ │
│  │                                                     │ │
│  │  ┌──────────────────────────────────────────────┐ │ │
│  │  │  Python Layer (FastAPI)                      │ │ │
│  │  │  - Transparent proxy                         │ │ │
│  │  │  - Request routing                           │ │ │
│  │  │  - SQLite audit logging                      │ │ │
│  │  └──────────────────────────────────────────────┘ │ │
│  │                                                     │ │
│  │  ┌──────────────────────────────────────────────┐ │ │
│  │  │  Rust Core (PyO3 bindings)                   │ │ │
│  │  │  - sark-opa: Policy evaluation               │ │ │
│  │  │  - sark-cache: In-memory caching             │ │ │
│  │  │  - sark-audit: Log primitives                │ │ │
│  │  └──────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  Data Storage                                        │ │
│  │  - SQLite database (/var/db/yori/audit.db)          │ │
│  │  - Rego policies (/usr/local/etc/yori/policies/)    │ │
│  │  - Config (/usr/local/etc/yori/yori.conf)           │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Traffic Flow

```
Device (laptop/phone)
    │
    │ DNS: api.openai.com → 203.0.113.50
    │
    ▼
OPNsense Firewall Rule
    │
    │ Port 443 → rdr-to 192.168.1.1:8443
    │
    ▼
YORI Proxy (:8443)
    │
    ├─ TLS termination (with CA cert)
    ├─ Log request (SQLite)
    ├─ Evaluate policy (Rust OPA)
    ├─ Apply action (log/alert/block)
    │
    ▼
Forward to Real LLM API
    │
    ▼
Log response (SQLite)
    │
    ▼
Return to client
```

---

## Repository Structure

```
yori/
├── Cargo.toml                  # Rust workspace
├── pyproject.toml             # Python packaging
├── README.md
├── LICENSE (MIT)
│
├── rust/                      # Rust components
│   ├── yori-core/            # Main Rust library
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs        # PyO3 bindings
│   │       ├── proxy.rs      # HTTP proxy logic
│   │       └── policy.rs     # Policy evaluation
│   │
│   └── vendor/               # Vendored SARK crates (if not using crates.io)
│       ├── sark-opa/
│       ├── sark-cache/
│       └── sark-audit/
│
├── python/                   # Python application
│   └── yori/
│       ├── __init__.py
│       ├── main.py          # FastAPI app
│       ├── proxy.py         # Proxy logic
│       ├── audit.py         # SQLite audit logging
│       ├── config.py        # Configuration
│       └── models.py        # Pydantic models
│
├── opnsense/                # OPNsense plugin
│   ├── +MANIFEST            # Plugin metadata
│   ├── Makefile
│   └── src/
│       └── opnsense/
│           └── mvc/
│               ├── app/
│               │   ├── controllers/
│               │   │   └── OPNsense/YORI/
│               │   │       ├── Api/ServiceController.php
│               │   │       └── IndexController.php
│               │   ├── models/
│               │   │   └── OPNsense/YORI/
│               │   │       └── General.xml
│               │   └── views/
│               │       └── OPNsense/YORI/
│               │           └── index.volt
│               └── service/
│                   └── conf/
│                       └── actions.d/
│                           └── actions_yori.conf
│
├── policies/                # Default Rego policies
│   ├── home_default.rego   # Default home policy (allow-all)
│   ├── bedtime.rego        # Example: bedtime blocks
│   └── parental.rego       # Example: content filtering
│
├── sql/                    # Database schemas
│   └── schema.sql         # SQLite schema for audit logs
│
├── scripts/
│   ├── build-freebsd.sh   # Cross-compile for FreeBSD
│   ├── package.sh         # Build OPNsense package
│   └── install-dev.sh     # Dev environment setup
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── INSTALLATION.md    # How to install on OPNsense
│   ├── USER_GUIDE.md      # For home users
│   ├── DEVELOPER_GUIDE.md # For contributors
│   └── POLICY_GUIDE.md    # Writing Rego policies
│
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

---

## Milestones

### Milestone 1: Foundation (Weeks 1-2)

**Goal:** Basic repository structure, build system, core libraries

**Deliverables:**
1. ✅ Create new repo `apathy-ca/yori`
2. ✅ Set up Rust workspace with vendored SARK crates
3. ✅ Create basic PyO3 bindings for Rust core
4. ✅ Set up Python packaging (pyproject.toml)
5. ✅ Cross-compilation for FreeBSD (x86_64)
6. ✅ CI/CD pipeline (GitHub Actions)
   - Build Rust for FreeBSD
   - Run tests
   - Package artifacts

**Exit Criteria:**
- Can build Rust binaries for FreeBSD
- Can import Rust functions from Python
- CI/CD green

---

### Milestone 2: Transparent Proxy (Weeks 3-4)

**Goal:** Working HTTP proxy that logs LLM traffic

**Deliverables:**
1. ✅ FastAPI proxy service
   - Listen on :8443
   - TLS termination (with CA cert)
   - Forward to real LLM endpoints
2. ✅ SQLite audit logging
   - Request: timestamp, endpoint, prompt_preview, user_agent
   - Response: status, tokens, duration
3. ✅ Basic policy evaluation (Rust OPA)
   - Load .rego files
   - Evaluate allow/deny
   - Log decisions
4. ✅ LLM endpoint detection
   - api.openai.com
   - api.anthropic.com
   - gemini.google.com
   - api.mistral.ai
5. ✅ Configuration file (YAML)
   ```yaml
   # /usr/local/etc/yori/yori.conf
   mode: observe  # observe | advisory | enforce
   listen: 0.0.0.0:8443

   endpoints:
     - domain: api.openai.com
       enabled: true
     - domain: api.anthropic.com
       enabled: true

   audit:
     database: /var/db/yori/audit.db
     retention_days: 365

   policies:
     directory: /usr/local/etc/yori/policies
     default: home_default.rego
   ```

**Exit Criteria:**
- Can intercept and log OpenAI/Anthropic requests
- SQLite database contains audit records
- Rust policy engine evaluates simple allow/deny rules
- No blocking in "observe" mode

---

### Milestone 3: OPNsense Plugin Scaffold (Weeks 5-6)

**Goal:** Basic OPNsense plugin that starts/stops YORI service

**Deliverables:**
1. ✅ OPNsense plugin structure
   - PHP controllers (start, stop, status)
   - Service configuration
   - Plugin manifest
2. ✅ Web UI (minimal)
   - Service control page (start/stop/restart)
   - Status indicator (running/stopped)
   - View config file
3. ✅ Service integration
   - rc.d script for YORI service
   - Auto-start on boot (optional)
   - Logs to syslog
4. ✅ Package build
   - Create .txz package for OPNsense
   - Installation instructions

**Exit Criteria:**
- Can install plugin via OPNsense package manager
- Can start/stop YORI from web UI
- Service persists across reboots (if enabled)

---

### Milestone 4: Dashboard & Reporting (Weeks 7-8)

**Goal:** Useful web UI for viewing LLM usage

**Deliverables:**
1. ✅ Dashboard page
   - Requests last 24h (chart)
   - Top endpoints (OpenAI vs Anthropic vs Gemini)
   - Top devices by IP
   - Recent alerts (if any)
2. ✅ Audit log viewer
   - Paginated table
   - Filters: date range, endpoint, device
   - Search by prompt keywords
   - Export to CSV
3. ✅ Statistics
   - Total requests (all time, last 30 days, last 7 days)
   - Average tokens per request
   - Peak usage hours
4. ✅ Simple charts
   - Requests per hour (bar chart)
   - Endpoint distribution (pie chart)
   - Device usage (bar chart)

**Technologies:**
- PHP/Volt templates (OPNsense standard)
- Chart.js for visualizations
- Bootstrap 5 (already in OPNsense)
- SQLite queries via PHP PDO

**Exit Criteria:**
- Dashboard shows meaningful LLM usage stats
- Can drill down into individual requests
- Can export audit logs

---

### Milestone 5: Policy Engine & Advisory Mode (Weeks 9-10)

**Goal:** Enable advisory alerts based on policies

**Deliverables:**
1. ✅ Policy editor UI
   - List installed policies
   - Enable/disable policies
   - Simple policy builder (no-code)
     - Time-based rules
     - Device-based rules
     - Keyword-based rules
2. ✅ Advisory alerts
   - Email notifications (via OPNsense SMTP)
   - Web UI alerts/warnings
   - Optional push notifications (Pushover/Gotify)
3. ✅ Pre-built policy templates
   - **Bedtime:** Alert if LLM use after 21:00
   - **High Usage:** Alert if >50 requests/day
   - **Homework Helper:** Alert on educational keywords
   - **Privacy Check:** Alert on personal info in prompts
4. ✅ Policy testing
   - "Test this policy" button
   - Shows which recent requests would match
   - Dry-run mode

**Exit Criteria:**
- Can create simple time-based policies
- Alerts appear in web UI
- Email notifications work (if configured)

---

### Milestone 6: Optional Enforcement (Weeks 11-12)

**Goal:** Allow blocking LLM requests (opt-in)

**Deliverables:**
1. ✅ Enforcement mode
   - Explicit user consent required
   - Clear warning about breaking functionality
   - Per-policy enforcement toggle
2. ✅ Block page
   - Friendly error message
   - Reason for block (policy name)
   - Timestamp
   - Request override option (with password)
3. ✅ Allowlist/blocklist
   - Device allowlist (never block these IPs)
   - Time-based exceptions
   - Emergency override (disable all policies)
4. ✅ Audit trail
   - Log all blocks
   - Include policy that triggered block
   - Include user override events

**Exit Criteria:**
- Can block LLM requests based on policies
- Block page explains why
- Allowlist prevents false positives
- All enforcement logged to audit DB

---

### Milestone 7: Documentation & Release (Week 13)

**Goal:** Public release of YORI v0.1.0

**Deliverables:**
1. ✅ User documentation
   - Installation guide (with screenshots)
   - Quick start guide (15 minutes)
   - Configuration reference
   - Policy cookbook (10+ examples)
   - FAQ
   - Troubleshooting guide
2. ✅ Developer documentation
   - Architecture overview
   - Building from source
   - Cross-compilation guide
   - Plugin development
   - Contributing guide
3. ✅ Release package
   - OPNsense .txz package
   - GitHub release with artifacts
   - Changelog
   - Migration guide (none for v0.1.0)
4. ✅ Community
   - README with screenshots
   - Demo video (optional)
   - Submission to OPNsense plugins repo

**Exit Criteria:**
- Can install YORI from OPNsense plugins UI
- Documentation covers all features
- GitHub Issues enabled for support
- v0.1.0 tagged and released

---

## Technical Specifications

### System Requirements

**Target Hardware:**
- CPU: 1 core (any arch with FreeBSD support)
- RAM: 512MB minimum, 1GB recommended
- Disk: 100MB for application + 1GB for audit logs
- OS: OPNsense 24.1+ (FreeBSD 13.2+)

**Network:**
- 1 LAN interface minimum
- Internet access for LLM forwarding

### Performance Targets

- **Latency overhead:** <10ms p95 (Rust proxy)
- **Throughput:** 50 requests/sec sustained (home use: ~1-10 req/sec)
- **Memory:** <256MB RSS under normal load
- **Database:** <500MB for 1 year of home usage

### Security

- **TLS:** User must install custom CA certificate
  - YORI generates self-signed CA on first run
  - User exports CA cert for device trust stores
  - Alternative: Use existing OPNsense CA
- **Authentication:** OPNsense session auth (already handled)
- **Audit integrity:** SQLite with triggers (prevent tampering)
- **Secrets:** No LLM API keys stored (pass-through proxy)

### Data Schema

```sql
-- /usr/local/share/yori/schema.sql

CREATE TABLE audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,           -- ISO 8601
    event_type TEXT NOT NULL,          -- 'request' | 'response' | 'block'

    -- Request details
    client_ip TEXT NOT NULL,
    client_device TEXT,                -- Device name (from DHCP)
    endpoint TEXT NOT NULL,            -- 'api.openai.com'
    http_method TEXT NOT NULL,         -- 'POST'
    http_path TEXT NOT NULL,           -- '/v1/chat/completions'

    -- Prompt analysis (privacy-aware)
    prompt_preview TEXT,               -- First 200 chars (optional)
    prompt_tokens INTEGER,
    contains_sensitive BOOLEAN,        -- PII detected

    -- Response
    response_status INTEGER,
    response_tokens INTEGER,
    response_duration_ms INTEGER,

    -- Policy
    policy_name TEXT,
    policy_result TEXT,                -- 'allow' | 'alert' | 'block'
    policy_reason TEXT,

    -- Metadata
    user_agent TEXT,
    request_id TEXT UNIQUE
);

CREATE INDEX idx_timestamp ON audit_events(timestamp);
CREATE INDEX idx_client_ip ON audit_events(client_ip);
CREATE INDEX idx_endpoint ON audit_events(endpoint);
CREATE INDEX idx_policy_result ON audit_events(policy_result);

-- Statistics view
CREATE VIEW daily_stats AS
SELECT
    DATE(timestamp) as date,
    endpoint,
    COUNT(*) as request_count,
    SUM(prompt_tokens) as total_prompt_tokens,
    SUM(response_tokens) as total_response_tokens,
    AVG(response_duration_ms) as avg_duration_ms
FROM audit_events
WHERE event_type = 'request'
GROUP BY DATE(timestamp), endpoint;
```

---

## Dependencies

### Rust Crates

```toml
[dependencies]
# From SARK (vendored or via git)
sark-opa = { version = "0.1.0", path = "../sark/rust/sark-opa" }
sark-cache = { version = "0.1.0", path = "../sark/rust/sark-cache" }

# PyO3 for Python bindings
pyo3 = { version = "0.20", features = ["extension-module"] }

# HTTP proxy
hyper = { version = "1.0", features = ["full"] }
tokio = { version = "1.35", features = ["full"] }
rustls = "0.21"

# Utilities
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
anyhow = "1.0"
tracing = "0.1"
```

### Python Packages

```toml
[project]
name = "yori"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "httpx>=0.26.0",
    "pydantic>=2.5.0",
    "pyyaml>=6.0",
    "python-multipart>=0.0.6",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.12.0",
    "ruff>=0.1.8",
    "mypy>=1.8.0",
]
```

### OPNsense Requirements

- PHP 8.1+
- Bootstrap 5 (already included)
- Chart.js (bundle with plugin)
- SQLite3 PHP extension (already included)

---

## Testing Strategy

### Unit Tests

- Rust: `cargo test` for all Rust modules
- Python: `pytest` for proxy logic, audit, config

### Integration Tests

- End-to-end proxy flow
- Policy evaluation with real Rego
- SQLite audit logging
- OPNsense plugin installation

### Manual Testing

- Install on physical OPNsense appliance
- Generate real LLM traffic
- Verify logs in dashboard
- Test all policy types

### Performance Testing

- Load test with `ab` or `wrk`
- Measure latency overhead
- Memory usage under load
- SQLite query performance (1M+ records)

---

## Release Process

### Version Scheme

Semantic versioning: `MAJOR.MINOR.PATCH`

- v0.1.0: Initial release (observe mode)
- v0.2.0: Advisory mode
- v0.3.0: Enforcement mode
- v1.0.0: Production-ready

### Build Artifacts

1. **Rust binary** - `yori-core` for FreeBSD (x86_64)
2. **Python wheel** - `yori-0.1.0-py3-none-any.whl`
3. **OPNsense package** - `os-yori-0.1.0.txz`

### Distribution

- **GitHub Releases:** All artifacts
- **OPNsense Plugins Repo:** Submit for inclusion
- **Docker Image:** For testing (not for production)

---

## Future Enhancements (Post v1.0.0)

### v1.1.0: OpenSearch Integration
- Optional OpenSearch backend
- Deploy OpenSearch on NAS/home server
- YORI forwards audit logs
- Advanced search and dashboards

### v1.2.0: Local LLM Support
- Detect Ollama traffic
- Prefer local LLM over cloud (policy-based)
- Cost savings tracking

### v1.3.0: Multi-Router Federation
- YORI instances on multiple routers
- Centralized audit aggregation
- Unified policy management

### v1.4.0: Advanced Threat Detection
- Prompt injection detection (from SARK)
- Secret scanning (from SARK)
- Anomaly detection (behavioral baselines)

### v2.0.0: YORI Cloud (Optional)
- Managed service for advanced features
- Cloud-based policy updates
- Community-shared policies
- Parental control presets

---

## Success Metrics

### Technical
- ✅ Latency overhead <10ms p95
- ✅ Memory usage <256MB RSS
- ✅ 99.9% uptime on router
- ✅ Zero CVEs in dependencies

### Adoption
- 🎯 100 GitHub stars in 6 months
- 🎯 50 installations (community feedback)
- 🎯 10 community-contributed policies
- 🎯 Accepted into OPNsense plugins repository

### User Satisfaction
- 🎯 <5 GitHub issues per release
- 🎯 Positive feedback on OPNsense forums
- 🎯 Featured in home lab communities (r/homelab, r/selfhosted)

---

## Team & Roles

### Phase 1 (v0.1.0)
- **Lead:** James Henry (architecture, Rust core)
- **Implementation:** Czarina (multi-agent orchestration)
  - Agent 1: Rust development (sark-opa integration)
  - Agent 2: Python proxy (FastAPI, audit logging)
  - Agent 3: OPNsense plugin (PHP, UI)
  - Agent 4: Documentation (guides, screenshots)
  - Agent 5: Testing & QA

### Phase 2 (Post v0.1.0)
- Open source contributors
- OPNsense community
- Home lab enthusiasts

---

## Budget (Open Source)

- **Infrastructure:** $0 (GitHub free tier, CI/CD minutes)
- **Development:** Volunteer (James + Czarina agents)
- **Marketing:** $0 (word of mouth, community forums)
- **Total:** $0

---

## Timeline Summary

| Milestone | Duration | Key Deliverable |
|-----------|----------|-----------------|
| M1: Foundation | 2 weeks | Repo structure, Rust builds |
| M2: Proxy | 2 weeks | Working transparent proxy |
| M3: Plugin Scaffold | 2 weeks | OPNsense plugin installed |
| M4: Dashboard | 2 weeks | Web UI with stats |
| M5: Advisory Mode | 2 weeks | Policy alerts |
| M6: Enforcement | 2 weeks | Optional blocking |
| M7: Release | 1 week | v0.1.0 public release |
| **Total** | **13 weeks** | **~3 months** |

---

## Risk Register

### Technical Risks

| ID | Risk | Impact | Likelihood | Mitigation | Owner |
|----|------|--------|------------|------------|-------|
| RISK-001 | FreeBSD cross-compilation issues | High | Medium | Early testing, fallback to x86_64 only | Rust Team |
| RISK-002 | OPNsense plugin approval delayed | Medium | Low | Start submission early, follow guidelines | Lead |
| RISK-003 | Rust dependencies too heavy for router | High | Low | Profile early, use minimal features | Rust Team |
| RISK-004 | CA cert installation too complex | Medium | Medium | Clear docs, automation script | Documentation |
| RISK-005 | PyO3 binding overhead | Medium | Low | Benchmark early, optimize hot paths | Rust Team |
| RISK-006 | SQLite performance at scale | Medium | Low | Index optimization, retention policies | Backend |
| RISK-007 | TLS inspection breaks HSTS pinning | Medium | Medium | Document known limitations, allowlist | Documentation |

### Adoption & Community Risks

| ID | Risk | Impact | Likelihood | Mitigation | Owner |
|----|------|--------|------------|------------|-------|
| RISK-010 | Low adoption (niche use case) | Low | Medium | Focus on quality, community engagement | Lead |
| RISK-011 | Negative feedback on CA cert requirement | Medium | Medium | Clear value proposition, easy setup | Documentation |
| RISK-012 | Competition from commercial solutions | Low | Low | Open source advantage, privacy focus | Community |

### Mode 8 Specific Risks (FATS Implementation)

> **Note:** The following risks apply exclusively to Mode 8 (Avian Carrier Detection via Feline Autonomous Tracking System). These are documented here for completeness, though Mode 8 remains permanently in research status pending feline SME availability.

| ID | Risk | Impact | Likelihood | Mitigation | Owner |
|----|------|--------|------------|------------|-------|
| RISK-008 | **SME Retention** | Catastrophic | Certain | None viable. Accept risk. | Feline HR |
| | **Description:** Feline SMEs demonstrate zero organizational loyalty and will immediately abandon review sessions upon detection of: (a) sunbeam migration, (b) unattended cardboard boxes, (c) the audacity of a closed door anywhere in the building, (d) mysterious sounds from adjacent rooms, (e) dinner time ±3 hours | | | **Status:** Risk accepted. All mitigation strategies (treats, laser pointers, catnip) provide only temporary engagement (5-30 seconds). Nap schedules remain non-negotiable. | |
| RISK-009 | **Scope Creep via Bird Detection** | Complete Project Derailment | High | Development environments must be windowless | Architecture |
| | **Description:** Mode 8 requirements may expand unpredictably when windows are involved. Initial scope: RFC 1149 carriers. Observed scope creep: butterflies, leaves, reflections, dust particles, own tail. Project timeline becomes dependent on local avian migration patterns and squirrel activity. | | | **Conflict:** Windowless environments directly conflict with RISK-008 mitigation (SMEs require sunbeam access). Trade-off analysis pending. | |
| RISK-013 | **False Positive Rate** | Medium | Certain | Calibration workshops (pending SME availability) | QA Team |
| | **Description:** FATS agents exhibit >90% false positive rate under controlled conditions. Known triggers include but not limited to: laser pointers (testing equipment), red dots (presentation slides), string (network cables), paper bags (office supplies), and the concept of "nothing" in general. | | | **Mitigation Strategy:** Accept 10:1 false-positive-to-true-positive ratio as within acceptable parameters for biological neural networks. | |
| RISK-014 | **Equipment Damage** | Low | Medium | Insurance coverage, soft surfaces | Facilities |
| | **Description:** High-velocity intercepts may result in collateral damage to: (a) monitoring equipment, (b) nearby furniture, (c) innocent bystanders, (d) the carrier pigeon (expected), (e) the FATS agent's dignity (temporary). | | | **Note:** Agent dignity fully recovers within 2-3 minutes, typically followed by aggressive grooming and denial of incident. | |
| RISK-015 | **Agent Distraction During Critical Operations** | High | High | Remove all distractors from operations area | Operations |
| | **Description:** Critical interception operations may be compromised by: (a) laser pointer attacks from adversaries, (b) catnip-based denial-of-service, (c) competitive agents entering the operational theater, (d) sudden realization that it's 3 AM and time for zoomies. | | | **Contingency:** Maintain redundant agent pool. Minimum 3:1 agent-to-target ratio recommended. | |

### Risk Matrix

```
Impact vs Likelihood:

                    Low         Medium        High          Certain
Catastrophic                                              [RISK-008]
High            [002, 003]   [001, 009]    [RISK-015]
                [006]
Medium          [005, 010]   [004, 007]    [RISK-013]
                [012]        [011, 014]
Low
```

### Risk Monitoring & Review

- **Frequency:** Weekly during active development
- **Owner:** Project Lead
- **Escalation:** Any risk moving to High/Catastrophic triggers immediate review
- **Mode 8 Exception:** RISK-008 and RISK-009 are accepted as permanent constraints and excluded from standard escalation procedures

---

## Next Steps

1. **Immediate:**
   - Create `apathy-ca/yori` repository
   - Set up basic structure
   - Vendor SARK Rust crates

2. **Week 1:**
   - Implement Rust core with PyO3 bindings
   - Set up CI/CD for FreeBSD cross-compilation
   - Create basic Python proxy skeleton

3. **Week 2:**
   - Get first successful transparent proxy working
   - SQLite audit logging
   - Simple Rego policy evaluation

4. **Checkpoints:**
   - End of M2: Demo proxy logging real OpenAI requests
   - End of M3: Install plugin on OPNsense VM
   - End of M4: Show dashboard to early testers
   - End of M7: Public release announcement

---

## Appendix: Use Case Stories

### Story 1: Tech Dad
> "I wanted to know what my kids were asking ChatGPT. YORI showed me they were using it for homework help (legitimate) and some creative writing prompts. I set up a bedtime policy so they can't use LLMs after 9pm. It's like parental controls but for AI."

### Story 2: Privacy Advocate
> "I run local Ollama for sensitive work but my family uses ChatGPT. YORI lets me see all the prompts leaving my network. I discovered my smart TV was sending viewing habits to an LLM for recommendations. Blocked that endpoint immediately."

### Story 3: Cost Conscious
> "ChatGPT Plus is $20/month per person. My family of 4 was spending $80/month. YORI showed me we were barely using it - mostly my kids asking basic questions that Ollama could answer for free. Switched to local LLM, saved $960/year."

### Story 4: Security Researcher
> "I use YORI to study LLM API patterns. It's helped me find several undocumented endpoints and understand rate limiting behavior. The SQLite audit log is perfect for analysis in Jupyter notebooks."

---

**Project Plan Version:** 1.0
**Last Updated:** 2026-01-19
**Author:** Architecture Team
**Status:** Ready for Implementation
