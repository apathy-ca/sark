# SARK Version Renumbering Explanation
## From v2.0.0 to v1.2.0 - December 9, 2025

---

## TL;DR

**Old Plan:** Jump from v1.1.0 → v2.0.0
**New Plan:** v1.1.0 → v1.2.0 → v1.3.0 → v1.4.0 → v1.5.0 → v2.0.0

**Why:** Honest, incremental versioning that reflects actual production readiness. v2.0.0 now means "truly production-ready after security audit" instead of "we worked on it for a while."

---

## What Happened

### Previous State (Nov 28 - Dec 8, 2025)

We were rushing toward a **v2.0.0 release** that included:
- ✅ Gateway v1.1.0 infrastructure (merged Nov 28)
- ✅ Advanced features (adapters, federation, GRID protocol)
- ❌ **But:** Gateway client was stubbed (returned empty lists, NotImplementedError)
- ❌ **But:** 154 failing auth tests (77.8% pass rate)
- ❌ **But:** No policy validation (policy injection risk)
- ❌ **But:** No external security audit

**Problem:** We were about to call this "v2.0.0" even though:
1. The Gateway couldn't actually communicate with real MCP servers
2. Security audit hadn't been performed
3. Critical features were incomplete

### Critical Analysis (Dec 8, 2025)

The **Lethal Trifecta Analysis** revealed serious implementation gaps:
- Gateway client stubbed → cannot govern real AI agents
- Policy injection risk → single malicious policy bypasses all security
- Test failures → 77.8% pass rate unacceptable for production
- No end-to-end verification → security controls unproven

**Decision:** Halt the v2.0.0 release and adopt honest versioning.

---

## New Versioning Strategy

### Semantic Versioning Applied Correctly

**v1.x.y** = Feature additions and bug fixes (minor/patch versions)
**v2.0.0** = Production-ready milestone (major version bump)

### Version Plan

```
v1.1.0 (Nov 28, 2025) - CURRENT
  ↓ Gateway infrastructure merged but stubbed

v1.2.0 (Target: 8 weeks)
  ↓ Gateway working + policy validation + tests passing
  ↓ Deliverable: Functional core

v1.3.0 (Target: +8 weeks)
  ↓ Advanced security (injection detection, anomaly, MFA, etc.)
  ↓ Deliverable: Enhanced security

v1.4.0 (Target: +6-8 weeks)
  ↓ Rust optimization foundation (OPA + cache)
  ↓ Deliverable: 5-10x performance gains

v1.5.0 (Target: +4-5 weeks)
  ↓ Rust detection algorithms
  ↓ Deliverable: 10-100x performance gains

v2.0.0 (Target: After security audit)
  ✓ Production-ready
  ✓ External security audit passed
  ✓ Zero critical/high vulnerabilities
  ✓ Deployed to production
```

---

## What Changed in the Codebase

### Version References Updated

**Python Code:**
```python
# OLD
__version__ = "2.0.0"

# NEW
__version__ = "1.2.0-dev"  # Current development toward v1.2.0
```

**Documentation:**
- All references to "v2.0.0 release" → "v1.2.0 development"
- "v2.0.0 features" → "v1.2.0+ features"
- Production target: "v2.0.0" (after security audit)

### Implementation Plans

**Created:**
- `docs/v1.2.0/IMPLEMENTATION_PLAN.md` - Gateway + policy + tests
- `docs/v1.3.0/IMPLEMENTATION_PLAN.md` - Advanced security
- `docs/v1.4.0/IMPLEMENTATION_PLAN.md` - Rust foundation
- `docs/v1.5.0/IMPLEMENTATION_PLAN.md` - Rust detection

**Updated:**
- `docs/ROADMAP.md` - Complete version timeline
- `README.md` - Current version, roadmap
- All references to version numbers

### Code Annotations

Files with "v2.0" comments now mean:
- **"SARK v2.0 features"** → Advanced features (adapters, federation) available in v1.2.0+
- **"v2.0 interface"** → Modern interface design (not version-specific)
- **"Target: v2.0.0"** → Production deployment milestone

---

## Why This Matters

### 1. Honest Communication

**Before:** "We're releasing v2.0.0!"
**Reality:** Gateway doesn't work, tests failing, no security audit
**Perception:** Misleading stakeholders

**After:** "We're releasing v1.2.0"
**Reality:** Gateway works, tests pass, policy validation added
**Perception:** Honest about capabilities

### 2. Clear Milestones

**v1.2.0** = Functional core (Gateway works)
**v1.3.0** = Enhanced security (Lethal Trifecta mitigations)
**v1.4.0** = Performance foundation (Rust OPA + cache)
**v1.5.0** = Performance advanced (Rust detection)
**v2.0.0** = Production ready (security audit passed)

Each version number has **clear meaning** and **measurable deliverables**.

### 3. Incremental Progress

Instead of one big leap (v1.1 → v2.0), we have:
- Smaller, achievable milestones
- Continuous integration and testing
- Flexibility to go to production earlier (after v1.2.0 or v1.3.0 if needed)
- Option to skip performance optimizations (v1.4.0, v1.5.0) if not needed

### 4. Industry Standard Compliance

**Semantic Versioning (semver.org):**
- Major version (2.0.0) = Breaking changes or major milestones
- Minor version (1.2.0) = New features, backward compatible
- Patch version (1.2.1) = Bug fixes

Our new strategy aligns with semver.org standards.

---

## Migration Guide for Developers

### If You Have Code References

**Update version constants:**
```python
# In your integration code
# OLD
assert sark.__version__ >= "2.0.0"

# NEW
assert sark.__version__ >= "1.2.0"
```

**Update feature checks:**
```python
# OLD
if supports_v2_features():
    use_advanced_adapter()

# NEW
if supports_adapters():  # Available in v1.2.0+
    use_advanced_adapter()
```

### If You Have Documentation

**Update references:**
- "SARK v2.0" → "SARK v1.2+" or "SARK (production)"
- "v2.0.0 release" → "v1.2.0 release" or "v2.0.0 production target"
- "v2.0 features" → "Advanced features (v1.2.0+)"

### If You're Planning Deployment

**Timeline expectations:**
- **Old:** v2.0.0 in 15 weeks (unrealistic given gaps)
- **New:** v1.2.0 in 8 weeks (functional), v2.0.0 in 22-36 weeks (production-ready)

**Recommended path:**
1. Deploy v1.2.0 to staging (8 weeks)
2. Add v1.3.0 security features (16 weeks total)
3. Security audit (22 weeks total)
4. Deploy v2.0.0 to production (23 weeks total)

---

## FAQ

### Q: Why not just call it v2.0.0 anyway?

**A:** Because version numbers should mean something. v2.0.0 should indicate a production-ready system, not "we did some work." Misleading version numbers erode trust.

### Q: Does this delay production?

**A:** No, it **clarifies** the path to production. We're being honest that we're not ready yet, rather than pretending we are.

### Q: Can we still go to production before v2.0.0?

**A:** Yes! v1.2.0 or v1.3.0 could be deployed to production if security audit passes. v2.0.0 is the **official production certification**, not a blocker.

### Q: What about marketing?

**A:** Being at v1.2.0 instead of v2.0.0 is **more impressive** because it shows maturity and honesty. "v1.2.0 with 99.9% uptime" beats "v2.0.0 that doesn't work."

### Q: Will we ever release v3.0.0?

**A:** Yes, when we make breaking changes or achieve another major milestone. Examples:
- GRID Protocol v2.0 (breaking changes to API)
- Multi-tenancy (major architectural change)
- Complete rewrite in Rust (unlikely but possible)

### Q: What if we want to skip v1.3.0/v1.4.0/v1.5.0?

**A:** Totally fine! Version numbers are cheap. We can go:
- v1.2.0 → v1.6.0 (skip 3, 4, 5)
- v1.2.0 → v2.0.0 (if security audit passes early)

The plan is flexible, the version numbers are honest.

---

## Impact on Project Artifacts

### Updated Files

**Core:**
- `README.md` - Version, roadmap, status
- `pyproject.toml` - Version string
- `src/sark/__init__.py` - `__version__`

**Documentation:**
- `docs/ROADMAP.md` - Complete version timeline
- `docs/v1.2.0/IMPLEMENTATION_PLAN.md` - NEW
- `docs/v1.3.0/IMPLEMENTATION_PLAN.md` - NEW
- `docs/v1.4.0/IMPLEMENTATION_PLAN.md` - NEW
- `docs/v1.5.0/IMPLEMENTATION_PLAN.md` - NEW
- `IMPLEMENTATION_PLAN.md` - Updated targets

**No Changes Needed:**
- Code functionality (no breaking changes)
- Test suite (no changes)
- API endpoints (no changes)
- Configuration files (no changes)

---

## Timeline Comparison

### Old Plan (Unrealistic)

```
Week 0:  v1.1.0 (Gateway stubbed)
Week 15: v2.0.0 (Production???)
```

**Problems:**
- Ignored 154 failing tests
- Ignored stubbed Gateway
- Ignored missing security audit
- Ignored policy injection risk

### New Plan (Realistic)

```
Week 0:   v1.1.0 (Gateway stubbed)
Week 8:   v1.2.0 (Gateway works, tests pass)
Week 16:  v1.3.0 (Advanced security)
Week 24:  v1.4.0 (Rust foundation) [OPTIONAL]
Week 29:  v1.5.0 (Rust detection) [OPTIONAL]
Week 23+: v2.0.0 (After security audit)
```

**Benefits:**
- Acknowledges reality
- Clear milestones
- Flexible path to production
- Optional performance work

---

## Conclusion

The version renumbering from v2.0.0 to v1.2.0 is **not a setback** — it's an act of **intellectual honesty**.

**What we're saying:**
- ✅ "We have strong foundations" (v1.1.0)
- ✅ "We're building incrementally" (v1.2.0, v1.3.0, etc.)
- ✅ "We'll be production-ready when security audit passes" (v2.0.0)

**What we're NOT saying:**
- ❌ "We're production-ready now" (we're not)
- ❌ "Trust us, it works" (we verify everything)
- ❌ "Version numbers are arbitrary" (they mean something)

This change demonstrates maturity, honesty, and commitment to quality over hype.

---

## References

- **Semantic Versioning:** https://semver.org/
- **Lethal Trifecta Analysis:** `LETHAL_TRIFECTA_ANALYSIS.md`
- **Implementation Plan:** `IMPLEMENTATION_PLAN.md`
- **Roadmap:** `docs/ROADMAP.md`
- **Version Plans:** `docs/v1.{2,3,4,5}.0/IMPLEMENTATION_PLAN.md`

---

**Document Version:** 1.0
**Date:** December 9, 2025
**Author:** SARK Team
**Status:** Official Explanation
