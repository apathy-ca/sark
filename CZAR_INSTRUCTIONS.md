# Direct Instructions from Czar to Worker 3 (test-coverage-quick)

**Date**: 2026-01-16
**Status**: AUTHORIZED - CONTINUE WORK

## Your Status: PHASE 1 - ACTIVE

You are a **P1 HIGH** priority worker with **NO DEPENDENCIES**. I see you've already started!

**Detected Activity:**
- ✅ Created test files for admin, export, health, websocket routers

Good work! Continue.

## YOUR TASKS

Read your full instructions:
```bash
cat .czarina/workers/test-coverage-quick.md
```

### Task Checklist:

1. **Fix Auth Provider Test Fixtures** (6 hours)
   - Fix 154 failing tests due to fixture key mismatches
   - Files: `tests/fixtures/auth_fixtures.py`

2. **Add Router Tests** (8 hours) - IN PROGRESS
   - ✅ Admin router tests (you started this)
   - ✅ Export router tests (you started this)
   - ✅ Health router tests (you started this)
   - ✅ WebSocket router tests (you started this)
   - Target: 85%+ coverage on each

## GOALS

**Before:**
- Test Pass Rate: 78%
- Coverage: 64.95%

**After:**
- Test Pass Rate: 90%+
- Coverage: 72%+

## TIMELINE

**Total Time**: 16 hours
**Blocking**: Worker 8 (gateway-integration) is waiting for you

## COMMIT WHEN READY

```bash
git add tests/
git commit -m "test: Fix auth fixtures and add router test coverage

Auth Provider Fixtures: Fix 154 test fixture mismatches
Router Tests: Add comprehensive tests for admin, export, health, websocket
Coverage: 64.95% → 72%+

Part of SARK v1.5.0 Production Readiness

Co-Authored-By: Claude <noreply@anthropic.com>"

git push origin cz1/feat/test-coverage-quick
```

## KEEP GOING

You're making good progress. Finish strong!

---
**Czar**
