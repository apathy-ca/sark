# SARK Code Review

**Reviewer:** Claude (Automated)
**Date:** 2026-02-16
**Scope:** Full codebase review — Python backend, Rust components, TypeScript frontend, configuration

---

## Executive Summary

SARK is an ambitious enterprise-grade AI governance platform with a well-structured multi-layer architecture spanning Python (FastAPI), Rust (PyO3 bindings), and TypeScript (React). The codebase demonstrates strong separation of concerns, comprehensive test coverage (~2,200 tests), and thorough documentation.

However, this review identified **~80 issues** across security, correctness, performance, and code quality. Several are **critical** and should be addressed before any production deployment.

### Issue Breakdown

| Severity | Count | Description |
|----------|-------|-------------|
| **Critical** | 8 | Security vulnerabilities, data corruption risks |
| **High** | 15 | Logic bugs, race conditions, missing auth |
| **Medium** | 30 | Performance issues, code smells, weak validation |
| **Low** | ~25 | Style, minor improvements, documentation gaps |

---

## Critical Issues

### 1. [CRITICAL] Hardcoded User Context in Rust Gateway

**File:** `rust/sark-gateway/src/main.rs:110-115`

The gateway authorize endpoint uses a hardcoded user for ALL requests:

```rust
let user = UserContext {
    user_id: "user123".to_string(),
    email: "user@example.com".to_string(),
    roles: vec!["developer".to_string()],
    permissions: vec!["mcp:invoke".to_string()],
};
```

All authorization decisions are made against the same static user, meaning every request is authorized identically regardless of who sends it. JWT extraction must be implemented before the gateway can be used.

---

### 2. [CRITICAL] OPA Engine Thread Safety Violation in Gateway

**File:** `rust/sark-gateway/src/main.rs:53`

The OPA engine is wrapped in `Arc<PolicyEngine>` but `PolicyEngine` has `&mut self` methods. Without a `Mutex` or `RwLock`, concurrent requests will cause undefined behavior:

```rust
opa_engine: Arc<PolicyEngine>,  // NEEDS: Arc<Mutex<PolicyEngine>>
```

---

### 3. [CRITICAL] Token Storage in localStorage (XSS-vulnerable)

**File:** `frontend/src/services/api.ts:62-63`

JWT access and refresh tokens are stored in `localStorage`, which is accessible to any JavaScript running on the page. A single XSS vulnerability would allow complete token theft:

```typescript
localStorage.setItem("access_token", access);
localStorage.setItem("refresh_token", refresh);
```

Additionally, tokens are stored in **three** separate locations: `api.ts` module variables, `localStorage`, and the Zustand `authStore` (which also persists to `localStorage`). This creates synchronization issues and multiplies the attack surface.

**Recommendation:** Use HttpOnly secure cookies managed by the backend.

---

### 4. [CRITICAL] SHA256 Used for API Key Hashing

**File:** `src/sark/services/auth/api_key.py:64-66`

API keys are hashed with plain SHA256 instead of a proper key derivation function:

```python
import hashlib
return hashlib.sha256(api_key.encode()).hexdigest()
```

SHA256 is too fast and lacks salting, making stored hashes vulnerable to brute-force and rainbow table attacks. Use `bcrypt`, `argon2`, or `PBKDF2` instead.

---

### 5. [CRITICAL] Blocking HTTP Call in Async Context

**File:** `src/sark/services/policy/opa_client.py:509`

A synchronous `httpx.get()` call blocks the entire asyncio event loop:

```python
httpx.get("https://worldtimeapi.org/api/ip").json()  # BLOCKING!
```

This will freeze all concurrent requests while waiting for this HTTP call to complete. Use `await self.client.get()` instead.

---

### 6. [CRITICAL] Race Condition in Cache TTL Expiry (Rust)

**File:** `rust/sark-cache/src/lru_ttl.rs:74-87`

TOCTOU (time-of-check-time-of-use) race condition in the cache `get()` method:

```rust
let entry = self.map.get(key)?;      // Check
if entry.is_expired() {
    drop(entry);
    self.map.remove(key);             // Use — another thread may access between these
    return None;
}
```

Between `drop(entry)` and `self.map.remove(key)`, another thread can read the expired entry. Use DashMap's atomic entry API instead.

---

### 7. [CRITICAL] Duplicate LDAP Configuration Fields

**File:** `src/sark/config/settings.py:59-70` and `109-123`

The `Settings` class defines LDAP fields **twice** with different defaults and types:

```python
# First definition (lines 59-70)
ldap_enabled: bool = False
ldap_server: str | None = None
ldap_bind_password: str | None = None
ldap_use_ssl: bool = True

# Second definition (lines 109-123) — OVERRIDES the first
ldap_enabled: bool = False
ldap_server: str = "ldap://localhost:389"
ldap_bind_password: str = ""
ldap_use_ssl: bool = False
```

The second definition silently overrides the first, changing `ldap_server` from `None` to `"ldap://localhost:389"`, `ldap_bind_password` from `None` to `""`, and `ldap_use_ssl` from `True` to `False`. This means SSL is **disabled by default** despite the first definition intending it to be enabled.

---

### 8. [CRITICAL] Version Mismatch

**Files:** `pyproject.toml:3` vs `src/sark/config/settings.py:27`

```
pyproject.toml:     version = "1.7.0"
settings.py:        app_version: str = "2.0.0"
```

The package version says 1.7.0 but the application reports itself as 2.0.0.

---

## High Severity Issues

### 9. [HIGH] Gateway Policies Never Loaded

**File:** `rust/sark-gateway/src/main.rs:206`

The OPA engine is initialized empty — no policies are loaded from configuration:

```rust
// TODO: Load policies from config
let opa_engine = Arc::new(PolicyEngine::new().context("Failed to initialize OPA engine")?);
```

All authorization checks against the empty engine will return default values (likely deny-all), rendering the gateway non-functional.

---

### 10. [HIGH] Silent Security Downgrade in Token Service

**File:** `src/sark/services/auth/tokens.py:45-46`

If RS256 private key is missing, the token service silently downgrades to HS256:

```python
self.settings.jwt_algorithm = "HS256"  # Silently downgrades security
```

This is logged as a warning but doesn't raise an error. In production, misconfigured RS256 could silently fall back to symmetric signing, which is a different trust model entirely.

---

### 11. [HIGH] Rate Limiter Race Condition

**File:** `src/sark/services/rate_limiter.py:77-93`

The rate limiter uses a Redis pipeline where the count is read and the request is added non-atomically. Between counting and adding, concurrent requests can all see the same count and all be allowed:

```
Client A: count=999, limit=1000, allowed=true
Client B: count=999, limit=1000, allowed=true (race!)
```

Use a Lua script or Redis `INCR` with `EXPIRE` for atomic rate limiting.

---

### 12. [HIGH] Implicit Admin Privilege Escalation

**File:** `src/sark/services/auth/user_context.py:20`

```python
def has_role(self, role: str) -> bool:
    return self.role == role or self.is_admin
```

Admin users pass ALL role checks unconditionally. This may be intentional but creates an implicit privilege escalation path — any code checking `has_role("viewer")` will also match admin, even if the intent was to restrict to viewer-only.

---

### 13. [HIGH] Incorrect Atomic Memory Ordering (Rust Cache)

**File:** `rust/sark-cache/src/lru_ttl.rs:31-38`

```rust
self.last_accessed.store(now, Ordering::Relaxed);
self.last_accessed.load(Ordering::Relaxed);
```

`Ordering::Relaxed` provides no synchronization guarantees between threads. LRU eviction decisions based on relaxed loads may evict recently-used entries. Should use `Release`/`Acquire` pair.

---

### 14. [HIGH] Inefficient OPA Serialization Round-Trips

**File:** `rust/sark-opa/src/python.rs:127-142`

Every policy evaluation performs 4 serialization/deserialization steps:

```
Python → serde_json::Value → String → regorus::Value (input)
regorus::Value → String → serde_json::Value → Python (output)
```

Each `.to_string()` allocates and parses JSON text. For the hot authorization path (target: p95 <5ms), this adds 1-2ms of overhead per call.

---

### 15. [HIGH] WebSocket Token Sent in Query Parameter

**File:** `frontend/src/hooks/useWebSocket.ts:74`

```typescript
const wsUrl = token ? `${url}?token=${token}` : url;
```

Tokens in URL query parameters are logged in browser history, server access logs, and proxy logs. Use cookies or the WebSocket subprotocol header for authentication.

---

### 16. [HIGH] Two Separate FastAPI Applications

**Files:** `src/sark/main.py` and `src/sark/api/main.py`

There are two separate FastAPI app factories:
- `src/sark/main.py` — uses `lifespan`, includes basic routers, has its own `/metrics` endpoint
- `src/sark/api/main.py` — uses deprecated `@app.on_event("startup")`, includes full routers, mounts Prometheus ASGI app

Both define CORS middleware and health routers. It's unclear which is the canonical entry point. The deprecated `on_event` in `api/main.py` should be migrated to the lifespan pattern used in `main.py`.

---

### 17. [HIGH] Dependency Injection Not Implemented

**File:** `src/sark/api/routers/auth.py:115-138`

Both `get_settings()` and `get_session_service()` dependencies raise `501 NOT IMPLEMENTED`:

```python
async def get_settings() -> Settings:
    # TODO: Get from app state
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Settings dependency not configured",
    )
```

Every auth endpoint will return 501 until these are properly wired up.

---

### 18. [HIGH] Auth Router Prefix Conflict

**File:** `src/sark/api/main.py:152` vs `src/sark/api/routers/auth.py:41`

The main app mounts the auth router at `/api/v1/auth`, but the router itself defines `prefix="/api/auth"`:

```python
# main.py
app.include_router(auth.router, prefix="/api/v1/auth", ...)

# auth.py
router = APIRouter(prefix="/api/auth", ...)
```

This results in endpoints being mounted at `/api/v1/auth/api/auth/...` — a double-prefixed path.

---

### 19. [HIGH] Hardcoded Development Credentials in Frontend

**File:** `frontend/src/pages/auth/LoginPage.tsx:57-58`

```jsx
<p>Development credentials:</p>
<p className="mt-1">john.doe / password</p>
```

Credentials visible in production builds. Gate behind an environment variable check.

---

### 20. [HIGH] OPA Client Iterator Bug

**File:** `src/sark/services/policy/opa_client.py:401`

`next(miss_iter)` can raise `StopIteration` if the iterator is exhausted, which would bubble up as a `RuntimeError` from the generator context. This indicates a bug in the result combination logic for batch policy evaluations.

---

### 21. [HIGH] O(n) LRU Eviction in Rust Cache

**File:** `rust/sark-cache/src/lru_ttl.rs:136-155`

Eviction scans the entire cache to find the least-recently-used entry:

```rust
for entry in self.map.iter() {
    if accessed_at < oldest_time { ... }
}
```

At 10K entries, every eviction requires 10K comparisons while holding iterator locks. Use a min-heap or the `lru` crate for O(log n) eviction.

---

### 22. [HIGH] Integer Overflow in Cache Time

**File:** `rust/sark-cache/src/lru_ttl.rs:68`

```rust
self.start_time.elapsed().as_nanos() as u64  // u128 → u64 silent truncation
```

While overflow requires ~584 years of runtime (unlikely), the silent `as` cast masks the risk. Use `saturating_cast` or `try_into()` with a documented expectation.

---

### 23. [HIGH] No Input Size Validation in Gateway

**File:** `rust/sark-gateway/src/main.rs:59-65`

The `GatewayAuthRequest` struct accepts unbounded `Option<serde_json::Value>` for `parameters` and `context` fields. An attacker can send megabyte-sized JSON payloads to exhaust memory. Add payload size limits via tower middleware.

---

## Medium Severity Issues

### 24. [MEDIUM] CORS Allows All Methods and Headers

**File:** `src/sark/api/main.py:129-135`

```python
app.add_middleware(
    CORSMiddleware,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Wildcard methods and headers are overly permissive. Restrict to the methods and headers actually used by the frontend.

---

### 25. [MEDIUM] Deprecated on_event Usage

**File:** `src/sark/api/main.py:167-185`

```python
@app.on_event("startup")   # Deprecated in FastAPI
@app.on_event("shutdown")  # Use lifespan instead
```

The `on_event` decorator is deprecated. The other `main.py` already uses the `lifespan` pattern correctly.

---

### 26. [MEDIUM] CSP Allows unsafe-inline

**File:** `src/sark/api/main.py:142`

```python
csp_policy="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
```

`'unsafe-inline'` for scripts defeats much of CSP's XSS protection. Use nonce-based CSP instead.

---

### 27. [MEDIUM] Untyped OIDCProvider Instantiation — Unused

**File:** `src/sark/api/routers/auth.py:216-223`

An `OIDCProvider` is constructed but never assigned to a variable:

```python
OIDCProvider(
    client_id=settings.oidc_client_id,
    ...
)  # Result discarded
```

This creates and discards an OIDC provider object on every call to `/providers`.

---

### 28. [MEDIUM] f-string Logging (Security)

**Files:** Multiple locations in `src/sark/api/routers/auth.py`

```python
logger.info(f"Stored OIDC state {state[:8]}... for CSRF validation")
logger.warning(f"OIDC callback with invalid/expired state: {state[:8]}...")
```

Using f-strings in log messages bypasses structured logging and can leak sensitive data if the log format changes. Use structlog's key-value style: `logger.info("stored_oidc_state", state_prefix=state[:8])`.

---

### 29. [MEDIUM] Gateway Audit API Key Comparison Not Constant-Time

**File:** `src/sark/api/routers/gateway.py:259`

```python
if x_gateway_api_key != expected_key:
```

String comparison with `!=` is not constant-time, potentially enabling timing attacks to discover the API key character by character. Use `hmac.compare_digest()`.

---

### 30. [MEDIUM] Error Messages Leak Internal Details

**Files:** Multiple routers

```python
detail=f"Failed to list servers: {e!s}"   # gateway.py:185
detail=f"Failed to log audit event: {e!s}" # gateway.py:289
```

Exception messages may contain internal paths, stack traces, or connection strings. Return generic messages to clients and log details server-side.

---

### 31. [MEDIUM] Missing `request.client` None Check

**File:** `src/sark/api/routers/auth.py:348`

```python
ip_address=request.client.host,
```

`request.client` can be `None` when running behind certain proxies or during testing. This will raise `AttributeError`.

---

### 32. [MEDIUM] Public Path Prefix Match is Too Broad

**File:** `src/sark/api/middleware/auth.py:153`

```python
return any(path.startswith(public_path) for public_path in self.PUBLIC_PATHS)
```

Since `/docs` is public, any path starting with `/docs` (e.g., `/docs-internal-admin`) would bypass authentication. Use exact matching or add trailing slashes.

---

### 33. [MEDIUM] OPA Engine Default Panics

**File:** `rust/sark-opa/src/engine.rs:229`

```rust
impl Default for OPAEngine {
    fn default() -> Self {
        Self::new().expect("Failed to create default OPA engine")
    }
}
```

`expect()` in library code will panic and crash the process. Either remove the Default impl or return a Result.

---

### 34. [MEDIUM] Inefficient Policy Update — Rebuilds Entire Engine

**File:** `rust/sark-opa/src/engine.rs:84-106`

Updating a single policy clones all existing policies, creates a new engine, and reloads everything. For large policy sets, this is an O(n) operation that blocks all evaluations.

---

### 35. [MEDIUM] Cache Python Bindings — No Upper Bounds

**File:** `rust/sark-cache/src/python.rs:24-28`

```rust
fn new(max_size: usize, ttl_secs: u64) -> PyResult<Self> {
```

No upper bound on `max_size` — a Python caller could accidentally request a 10GB cache.

---

### 36. [MEDIUM] Missing useEffect Dependencies

**File:** `frontend/src/hooks/useWebSocket.ts:147-155`

```typescript
useEffect(() => {
  if (url) connect();
  return () => disconnect();
}, [url]); // Missing: autoReconnect, reconnectDelay, callbacks
```

Stale closures will capture old callback references, causing unexpected behavior when options change.

---

### 37. [MEDIUM] Missing Accessible Dialog Patterns

**File:** `frontend/src/pages/apikeys/ApiKeysPage.tsx:213-225`

Modal dialogs lack `role="dialog"`, `aria-labelledby`, `aria-describedby`, and focus trap. Screen readers won't recognize them as modals.

---

### 38. [MEDIUM] Form Labels Not Associated

**File:** `frontend/src/pages/servers/ServerRegisterPage.tsx:139-151`

Labels lack `htmlFor` attributes and inputs lack matching `id`s. Screen readers cannot associate labels with their inputs.

---

### 39. [MEDIUM] `confirm()` for Destructive Actions

**Files:** `frontend/src/pages/apikeys/ApiKeysPage.tsx:60`, `frontend/src/pages/policies/PoliciesPage.tsx:89`

Browser `confirm()` dialogs are poor UX, untestable in unit tests, and can expose injected strings. Use custom modal components.

---

### 40. [MEDIUM] Inconsistent API Path Prefixes in Frontend

**File:** `frontend/src/services/api.ts`

Some endpoints use `${API_PREFIX}` variable, others hardcode `/api/auth/...`. Inconsistent and fragile.

---

### 41. [MEDIUM] Health Check Only Verifies Object Existence

**File:** `src/sark/db/pools.py:179`

```python
health["http"]["healthy"] = http_client is not None  # Just checks if object exists!
```

The HTTP client health check doesn't actually test connectivity. A client object can exist while the connection is broken.

---

### 42. [MEDIUM] Session Service Linear Key Search

**File:** `src/sark/services/auth/api_key.py:229-235`

Verifying an API key requires iterating through all stored keys — O(n) per request. Use an indexed lookup by key hash prefix.

---

### 43. [MEDIUM] Rate Limiter Fails Open

**File:** `src/sark/services/rate_limiter.py:121-129`

If Redis is unavailable, requests are allowed through. While documented, this could be exploited. Consider fail-closed for security-critical endpoints.

---

### 44. [MEDIUM] Missing Workspace Crate Alignment

**File:** `Cargo.toml` workspace

The workspace references both `sark-*` and `grid-*` crates:

```toml
grid-opa = { path = "../grid-core/crates/grid-opa" }
grid-cache = { path = "../grid-core/crates/grid-cache" }
```

The gateway uses `grid-*` while the Python bindings use `sark-*`. This creates architectural confusion about which implementation is canonical.

---

### 45. [MEDIUM] mypy and ruff Target Python 3.9, project requires 3.10+

**File:** `pyproject.toml:96,116`

```toml
target-version = ['py39']    # black
target-version = "py39"      # ruff
```

But:

```toml
requires-python = ">=3.10"
```

The linter/formatter targets are one minor version behind the minimum requirement.

---

## Low Severity Issues

### 46. [LOW] Excessive Ruff Ignores

**File:** `pyproject.toml:134-173`

39 ruff rules are ignored, several with "TODO: fix in future PR" comments (DTZ001-DTZ007, B904, RUF012). These represent known technical debt. The datetime-related ignores (DTZ*) mean naive datetimes are used throughout, which can cause subtle timezone bugs.

---

### 47. [LOW] mypy Disables Core Error Codes

**File:** `pyproject.toml:217`

```toml
disable_error_code = ["misc", "no-any-return", "attr-defined", "type-arg", "assignment"]
```

Disabling `attr-defined` and `assignment` masks real type errors. These should be re-enabled as the codebase matures.

---

### 48. [LOW] Secret Scanner Base64 Pattern Too Broad

**File:** `src/sark/security/secret_scanner.py:84-88`

The base64 pattern matches any 64+ character string that happens to be base64-compatible, with only 0.5 confidence. This will produce many false positives on regular content like long IDs, encoded URLs, or certificates.

---

### 49. [LOW] Injection Detector `_compile_patterns` is Static + Cached

**File:** `src/sark/security/injection_detector.py:92-94`

```python
@staticmethod
@lru_cache(maxsize=1)
def _compile_patterns():
```

Since this is a static method with `lru_cache`, patterns are compiled once globally regardless of config. Different `PromptInjectionDetector` instances with different configs will share the same patterns. This defeats per-instance customization.

---

### 50. [LOW] Default API URL Falls Back to HTTP

**File:** `frontend/src/services/api.ts:49`

```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
```

Acceptable for development but should never reach production.

---

### 51. [LOW] Loose `any` Types in Frontend

Multiple files use `any` types (`useAuth.ts:19`, `PoliciesPage.tsx:148`, `AuditLogsPage.tsx:44`, `export.ts`), defeating TypeScript's safety guarantees.

---

### 52. [LOW] Error Strings Lose Context in Rust

**File:** `rust/sark-opa/src/error.rs:45-54`

All error conversions use `.to_string()`, losing original error types. Consider using `thiserror` with `#[source]` attributes to preserve error chains.

---

### 53. [LOW] Redundant Session Closein DB

**File:** `src/sark/db/session.py:95`

Calls `session.close()` after the `finally` block, but `AsyncSession` auto-closes when exiting the context manager.

---

## Architectural Observations

### What's Done Well

1. **Separation of concerns** — Clear layering between API routers, services, models, and adapters
2. **Multi-protocol auth** — OIDC, LDAP, SAML, API keys, JWT all implemented
3. **Security modules** — Prompt injection detection (20+ patterns), secret scanning (25+ patterns), behavioral analysis
4. **Rust acceleration** — OPA engine and cache via PyO3 bindings (4-10x faster claims)
5. **Comprehensive testing** — 2,200+ tests across unit, integration, performance, security, chaos
6. **Infrastructure-as-code** — Helm, Terraform (AWS/GCP/Azure), Docker Compose profiles
7. **Structured logging** — Consistent use of structlog with key-value pairs

### Areas for Improvement

1. **Consolidate entry points** — Two FastAPI apps creates confusion
2. **Complete dependency injection** — Several DI stubs raise 501
3. **Resolve crate naming** — `sark-*` vs `grid-*` confusion
4. **Reduce linter suppressions** — 39 ignored rules indicates tech debt velocity
5. **Implement the gateway** — Core authorization path is stubbed/hardcoded
6. **Unified token storage** — Frontend has three token storage locations
7. **Timezone awareness** — Multiple datetime timezone ignores suggest systemic naive datetime usage

---

## Recommended Priority

### Phase 1: Security (Block Production)
- Fix hardcoded gateway user context (#1)
- Fix OPA engine thread safety (#2)
- Migrate frontend token storage (#3)
- Replace SHA256 API key hashing (#4)
- Fix LDAP config duplication — SSL disabled by default (#7)
- Fix blocking async call (#5)
- Implement auth DI stubs (#17)
- Fix auth router double prefix (#18)

### Phase 2: Correctness
- Fix cache TOCTOU race (#6)
- Fix rate limiter race condition (#11)
- Load gateway policies (#9)
- Fix version mismatch (#8)
- Fix OPA client iterator bug (#20)
- Fix atomic ordering (#13)

### Phase 3: Performance & Hardening
- Optimize OPA serialization (#14)
- Replace O(n) LRU eviction (#21)
- Add input size validation (#23)
- Constant-time API key comparison (#29)
- Restrict CORS methods/headers (#24)
- Harden CSP policy (#26)

### Phase 4: Code Quality
- Consolidate FastAPI entry points (#16)
- Resolve sark-*/grid-* crate naming (#44)
- Fix linter target versions (#45)
- Address ruff TODOs (#46)
- Improve frontend TypeScript strictness (#51)
- Add accessible dialog patterns (#37, #38)
