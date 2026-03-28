# SARK Implementation Plan: LGPL Dependency Removal

**Status:** Ready for execution
**Priority:** Medium (license compliance)
**Effort:** S (150K–300K tokens)
**Reality Check:** 🟢 Smooth Sailing (1.0x) — scope is fully understood, no architectural changes

---

## Overview

Remove the two LGPL-3.0 licensed dependencies from the SARK dependency tree and replace them
with MIT-licensed alternatives. The project's own MIT license is compatible with standard dynamic
use of LGPL libraries, but eliminating them removes the obligation entirely and simplifies
distribution.

**Removes:**
- `psycopg2-binary` (LGPL-3.0) — used only in one test fixture
- `ldap3` (LGPL-3.0) — used in the LDAP auth provider and related tests

**Replaces with:**
- Socket probe (stdlib, no license) — for postgres readiness check
- `bonsai` (MIT) — for all LDAP operations
- Hand-rolled `_escape_filter_chars()` (stdlib, RFC 4515) — for LDAP filter escaping

**What does NOT change:**
- `LDAPProvider` and `LDAPProviderConfig` public API
- `__init__.py` exports
- All test assertions and security test cases
- LDAP schema assumptions (DN structure, objectClass, attribute names)
- SAML and OIDC providers — untouched

---

## Files Affected

| File | Change |
|---|---|
| `tests/fixtures/integration_docker.py` | Remove `psycopg2` import; rewrite `is_postgres_responsive()` |
| `src/sark/services/auth/providers/ldap.py` | Full rewrite against `bonsai`; add `_escape_filter_chars()` |
| `tests/fixtures/ldap_docker.py` | Rewrite `is_ldap_responsive()` and `populate_ldap_test_data()` |
| `tests/unit/auth/providers/test_ldap_security.py` | Update import of escape function |
| `pyproject.toml` | Remove `ldap3`, `psycopg2-binary`; add `bonsai` |
| `requirements.txt` | Remove `psycopg2-binary` |

---

## Phase 1: Remove `psycopg2-binary`

**File:** `tests/fixtures/integration_docker.py`

`psycopg2` is used in exactly one function — `is_postgres_responsive()` — which opens a
synchronous connection to check if the PostgreSQL Docker container is up during integration test
setup. Production code already uses `asyncpg` (Apache-2.0) for all real database work.

The existing `is_grpc_mock_responsive()` in the same file demonstrates the preferred pattern:
a raw `socket.connect_ex()` probe. Apply the same approach to the postgres check.

**Tasks:**

1. Remove `import psycopg2` (line 6)
2. Rewrite `is_postgres_responsive()` as a socket probe:

```python
def is_postgres_responsive(host: str, port: int) -> bool:
    """Check if PostgreSQL is responsive."""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False
```

**Acceptance criteria:**
- [ ] `import psycopg2` is gone from the file
- [ ] `is_postgres_responsive()` uses only stdlib
- [ ] Integration test suite still starts the postgres container correctly

---

## Phase 2: Write `_escape_filter_chars()`

**File:** `src/sark/services/auth/providers/ldap.py`

`ldap3.utils.conv.escape_filter_chars` implements RFC 4515 §3. Write this as a module-level
private function so it can be used in the rewritten provider and imported by the security test
suite.

The characters requiring escaping and their encodings:

| Character | Escaped form |
|---|---|
| `\` (backslash) | `\5c` |
| `*` (asterisk) | `\2a` |
| `(` (open paren) | `\28` |
| `)` (close paren) | `\29` |
| `\x00` (NUL) | `\00` |

Backslash must be escaped first to avoid double-escaping.

```python
def _escape_filter_chars(value: str) -> str:
    """Escape special characters in an LDAP filter value per RFC 4515."""
    value = value.replace("\\", "\\5c")
    value = value.replace("*", "\\2a")
    value = value.replace("(", "\\28")
    value = value.replace(")", "\\29")
    value = value.replace("\x00", "\\00")
    return value
```

This function is private but intentionally importable by the security test suite — it is a
security primitive and testing it directly is appropriate.

**Acceptance criteria:**
- [ ] Function is present at module level in `ldap.py` before the class definitions
- [ ] All five RFC 4515 special characters are handled
- [ ] Backslash is escaped before the other characters (prevents double-escaping)

---

## Phase 3: Rewrite `ldap.py` Against `bonsai`

**File:** `src/sark/services/auth/providers/ldap.py`

Replace the `ldap3` import block and rewrite the four private methods. The public API
(`LDAPProviderConfig`, `LDAPProvider`, and all method signatures) is unchanged.

### Import changes

**Remove:**
```python
from ldap3 import ALL, SIMPLE, Connection, Server
from ldap3.core.exceptions import LDAPBindError, LDAPException
from ldap3.utils.conv import escape_filter_chars
```

**Add:**
```python
import bonsai
```

Remove `import asyncio` — it is only needed for `run_in_executor`, which goes away entirely.

### Concept mapping: `ldap3` → `bonsai`

| ldap3 | bonsai |
|---|---|
| `Server(url, get_info=ALL, use_ssl=…)` | `bonsai.LDAPClient(url)` |
| `Connection(server, user=dn, password=pw, auto_bind=True)` | `client.set_credentials("SIMPLE", dn, pw)` then `await client.connect(is_async=True)` |
| `conn.search(base, filter, attributes)` | `await conn.search(base, bonsai.LDAPSearchScope.SUB, filter, attrlist)` |
| `conn.entries[0].entry_dn` | `result[0].dn` |
| `entry.attr.value` | `entry["attr"][0]` |
| `LDAPBindError` | `bonsai.AuthenticationError` |
| `LDAPException` | `bonsai.LDAPError` |
| `conn.unbind()` | handled by `async with` context manager |

### `_search_user(username)`

Replace the synchronous nested closure and `run_in_executor` call with direct async bonsai calls.
Build an `LDAPClient` with the service account credentials, connect, search, extract DN and
attribute dict from the result entries.

Attribute extraction changes: `ldap3` uses `entry.attr.value`; bonsai entries are dict-like,
so use `entry["attr"][0]` with a `KeyError` guard.

The `escape_filter_chars` call site becomes `_escape_filter_chars`.

### `_bind_user(user_dn, password)`

Build an `LDAPClient` with `user_dn` as the bind DN and `password` as the credential.
Attempt `await client.connect(is_async=True)`. Success = no exception. Failure =
`bonsai.AuthenticationError`. General errors = `bonsai.LDAPError`.

No nested closure. No `run_in_executor`.

### `_get_user_groups(user_dn)`

Same structure as `_search_user` but searches `group_search_base` with the group filter.
Extract `cn` values from result entries. `_escape_filter_chars` call site is unchanged in intent.

### `health_check()`

Service-account connect + minimal base-level search. Set connect timeout via
`client.set_connect_timeout(5)` before connecting. Same early-return guard for
`not self.config.enabled or not self.config.server_url`.

**Acceptance criteria:**
- [ ] No `ldap3` imports remain
- [ ] No `asyncio` import remains (it was only needed for `run_in_executor`)
- [ ] All four private methods are async-native (no `run_in_executor`, no nested sync closures)
- [ ] `LDAPProviderConfig` is unchanged
- [ ] `LDAPProvider` public method signatures are unchanged
- [ ] `_escape_filter_chars()` is used in place of the former `escape_filter_chars` import

---

## Phase 4: Update Test Files

### `tests/unit/auth/providers/test_ldap_security.py`

The only `ldap3` reference in this file is the import at line 5:

```python
from ldap3.utils.conv import escape_filter_chars
```

Used at lines 88 and 115 to independently verify SARK's own escaping. Replace with the new
internal function:

```python
from sark.services.auth.providers.ldap import _escape_filter_chars
```

Update the two call sites accordingly. All test assertions are unchanged — they test the same
RFC 4515 escaping contract.

### `tests/fixtures/ldap_docker.py`

Rewrite `is_ldap_responsive()` and `populate_ldap_test_data()` using `bonsai`.
Remove the `from ldap3 import ALL, Connection, Server` import.

**`is_ldap_responsive()`** — replace `ldap3.Server` + `ldap3.Connection` with a
`bonsai.LDAPClient` connect attempt:

```python
def is_ldap_responsive(host: str, port: int) -> bool:
    """Check if LDAP server is responsive."""
    import asyncio
    async def _check():
        try:
            client = bonsai.LDAPClient(f"ldap://{host}:{port}")
            client.set_credentials("SIMPLE", "cn=admin,dc=example,dc=com", "admin")
            client.set_connect_timeout(2)
            conn = await client.connect(is_async=True)
            await conn.close()
            return True
        except Exception:
            return False
    return asyncio.run(_check())
```

**`populate_ldap_test_data()`** — replace `conn.add(dn, objectClasses, attrs)` with
`bonsai.LDAPEntry`. Create an entry, set its DN, set the `objectClass` and attribute values,
then call `await conn.add(entry)`. The test data (OUs, users, groups, attribute values) is
identical to the current implementation.

Make `populate_ldap_test_data` async and update the `ldap_service` fixture to call it with
`asyncio.run()` or convert the fixture itself to async.

**Acceptance criteria:**
- [ ] No `ldap3` imports remain in either test file
- [ ] `test_ldap_security.py` imports `_escape_filter_chars` from the provider module
- [ ] All existing security test assertions pass without modification
- [ ] `ldap_docker.py` populates test data using `bonsai.LDAPEntry`
- [ ] `ldap_provider_config` and `ldap_provider` fixtures are unchanged

---

## Phase 5: Dependency Manifest Cleanup

### `pyproject.toml`

In `[project.dependencies]`:
- Remove `ldap3>=2.9.1`
- Remove `psycopg2-binary>=2.9.9`
- Add `bonsai>=1.5.3`

In `[[tool.mypy.overrides]]` (the `ignore_missing_imports = true` block):
- Add `"bonsai.*"` — bonsai ships a C extension; mypy stubs are incomplete

### `requirements.txt`

- Remove `psycopg2-binary>=2.9.9`

### Lock file

Regenerate after manifest changes:

```bash
uv lock
```

**Acceptance criteria:**
- [ ] `ldap3` does not appear anywhere in `pyproject.toml` or `requirements.txt`
- [ ] `psycopg2-binary` does not appear anywhere in `pyproject.toml` or `requirements.txt`
- [ ] `bonsai>=1.5.3` is present in `[project.dependencies]`
- [ ] `uv.lock` is regenerated and committed

---

## Execution Order

```
Phase 1          Phase 2          Phase 3          Phase 4          Phase 5
psycopg2    →   escape fn    →   ldap.py      →   tests        →   manifests
removal         (write once)     (rewrite)        (update)         (cleanup)
```

Phase 2 must precede Phase 3 (the escape function is called in the rewrite) and Phase 4
(the security tests import it directly). All other phases are sequential.

---

## Verification

Run after each phase to confirm nothing has regressed:

```bash
# Unit tests — no LDAP server required
pytest tests/unit/auth/providers/test_ldap_security.py -v

# Integration tests — requires Docker
pytest tests/ -m integration -v

# Confirm no ldap3 or psycopg2 references remain
grep -r "ldap3\|psycopg2" src/ tests/ pyproject.toml requirements.txt

# License / vulnerability scan
pip-audit
```

---

## References

- [RFC 4515 §3 — LDAP filter escaping](https://www.rfc-editor.org/rfc/rfc4515#section-3)
- [bonsai documentation](https://bonsai.readthedocs.io/)
- [License audit report](../SECURITY_AUDIT.md) — original LGPL finding
- `src/sark/services/auth/providers/base.py` — `AuthProvider` interface
- `src/sark/services/auth/providers/ldap.py` — file being replaced
