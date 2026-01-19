# Work Reallocation - Post-Omnibus Tasks

**Status:** Omnibus merged, work identified
**Priority:** Fix type errors → Merge E4 → UI docs → Release

---

## Task 1: Fix Frontend Type Errors (30 minutes)

**Assignee:** Any engineer (can be done now)
**Priority:** 🔴 CRITICAL - Blocks everything
**Status:** ❌ Not started

### Quick Fixes Required (26 errors)

**1. Fix Axios imports in `frontend/src/services/api.ts` (line 6)**
```typescript
// BEFORE:
import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios'

// AFTER:
import axios from 'axios'
import type { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios'
```

**Also remove unused import (line 28):**
```typescript
// DELETE this line:
  AuditEvent,
```

**2. Update `frontend/src/types/api.ts`**

Add missing fields to Policy interface:
```typescript
export interface Policy {
  id: string
  name: string
  content: string          // ADD THIS
  package_name: string     // ADD THIS
  created_at: string       // ADD THIS
  updated_at: string
  version: number
}
```

Add missing fields to ServerListItem interface:
```typescript
export interface ServerListItem {
  id: string
  name: string
  description: string      // ADD THIS
  url: string
  status: string
  transport: string
  tool_count: number       // ADD THIS
  created_at: string
  updated_at: string
}
```

Add missing field to ServerListParams interface:
```typescript
export interface ServerListParams {
  page?: number
  limit?: number
  search?: string
  status?: string
  transport?: string
  sensitivity_level?: string  // ADD THIS
}
```

Add/verify id field in ServerResponse:
```typescript
export interface ServerResponse {
  id: string               // ADD if missing
  server_id: string
  name: string
  // ... rest
}
```

**3. Fix Zod schema in `frontend/src/pages/servers/ServerRegisterPage.tsx` (line 13)**
```typescript
// BEFORE:
transport: z.enum(['http', 'stdio', 'sse'], { required_error: 'Transport is required' }),

// AFTER:
transport: z.enum(['http', 'stdio', 'sse'], {
  errorMap: () => ({ message: 'Please select a transport type' })
}),
```

**4. Verify build**
```bash
cd frontend
npm run build
# Should succeed with no errors
```

**Time:** 30 minutes
**Deliverable:** `npm run build` succeeds

---

## Task 2: Merge Engineer 4's Infrastructure (1 hour)

**Assignee:** DevOps engineer or maintainer
**Priority:** 🟡 HIGH - After type fixes
**Status:** ❌ Not started

### Steps

**1. Merge Engineer 4's branch**
```bash
git fetch origin claude/engineer-4-tasks-01BYTHwVScpE1LtHdnMcNM1w
git merge origin/claude/engineer-4-tasks-01BYTHwVScpE1LtHdnMcNM1w
```

**2. Resolve conflicts (expected)**

**Conflict 1: frontend/Dockerfile**
- E3 has basic version (36 lines)
- E4 has advanced version (136 lines)
- **Resolution:** Use E4's version (better)

**Conflict 2: frontend/vite.config.ts**
- E3 has basic config
- E4 has optimizations
- **Resolution:** Merge both (keep E3's proxy + E4's optimizations)

**Conflict 3: docker-compose files**
- E4 removed `version: '3.9'`
- **Resolution:** Use E4's version

**3. Clean up duplicate directory**
```bash
rm -rf frontend/frontend/
```

**4. Test builds**
```bash
# Test dev
docker-compose --profile ui-dev up

# Test production
cd frontend && docker build -t sark-ui .
```

**Time:** 1 hour
**Deliverable:** All Docker/K8s infrastructure merged and working

---

## Task 3: Create UI Documentation (2-3 days)

**Assignee:** Documenter (or technical writer)
**Priority:** 🟢 MEDIUM - After build works
**Status:** ❌ Not started

### Deliverables

**1. UI User Guide** (`docs/UI_USER_GUIDE.md`)
- Login process (screenshot)
- Dashboard overview (screenshot)
- Server management walkthrough
- Policy editor usage (screenshot)
- Audit log filtering
- API key management
- Keyboard shortcuts reference

**2. Deployment Guide Updates** (`docs/DEPLOYMENT_GUIDE.md` or update existing)
- Add UI deployment sections
- Docker Compose with UI
- Kubernetes with UI
- Environment variables for UI
- Nginx configuration

**3. Troubleshooting Guide** (`docs/UI_TROUBLESHOOTING.md`)
- Common UI errors
- Browser compatibility
- API connection issues
- Performance problems
- Dark mode issues

**4. Release Notes** (`RELEASE_NOTES_v1.0.0.md`)
- Feature summary
- API endpoints
- UI capabilities
- Breaking changes (if any)
- Upgrade guide

**Time:** 2-3 days
**Deliverable:** Complete UI documentation with screenshots

---

## Task 4: Final Testing & Cleanup (4 hours)

**Assignee:** QA or any engineer
**Priority:** 🟢 LOW - After docs complete
**Status:** ❌ Not started

### Checklist

**Frontend Testing:**
- [ ] `npm run dev` works
- [ ] `npm run build` succeeds
- [ ] All pages load without errors
- [ ] Authentication flow works
- [ ] CRUD operations work (servers, policies, etc.)
- [ ] Export to CSV/JSON works
- [ ] Dark mode works
- [ ] Keyboard shortcuts work

**Docker Testing:**
- [ ] Dev environment: `docker-compose --profile ui-dev up`
- [ ] Production build: `docker build -t sark-ui frontend/`
- [ ] Production run: `docker run -p 8080:80 sark-ui`
- [ ] UI accessible at localhost
- [ ] API proxy works
- [ ] Health checks pass

**Kubernetes Testing:**
- [ ] Manifests apply: `kubectl apply -k k8s/base/`
- [ ] Pods running
- [ ] Service accessible
- [ ] Ingress works
- [ ] HPA configured
- [ ] Health probes working

**Cleanup:**
- [ ] Remove duplicate `frontend/frontend/` directory
- [ ] Remove old planning documents (if any)
- [ ] Update main README with UI screenshots
- [ ] Tag v1.0.0 release

**Time:** 4 hours
**Deliverable:** Production-ready release

---

## Timeline

```
Day 1 (Today):
  Hour 1:    Fix type errors ← START HERE
  Hour 2-3:  Merge Engineer 4's infrastructure
  Hour 4:    Test Docker builds

Days 2-4:
  Documenter: Create UI documentation (parallel work)

Day 4-5:
  Final testing and cleanup
  Tag v1.0.0 release
```

**Total:** 4-5 days to v1.0.0 release

---

## Current Blockers

**BLOCKER 1:** Frontend build fails (26 type errors)
- **Impact:** Blocks production Docker build
- **Fix time:** 30 minutes
- **Action:** Anyone can fix using instructions above

**BLOCKER 2:** Engineer 4 not merged
- **Impact:** No Docker/K8s infrastructure in main
- **Fix time:** 1 hour (after type fixes)
- **Action:** Merge E4's branch, resolve conflicts

---

## Who Can Do What

**Task 1 (Type fixes):** Anyone with TypeScript knowledge
**Task 2 (Merge E4):** DevOps engineer or repo maintainer
**Task 3 (UI docs):** Documenter or technical writer
**Task 4 (Testing):** QA engineer or anyone

**Parallelization:**
- Type fixes must be done first (blocks everything)
- After types fixed: E4 merge + UI docs can happen in parallel
- Testing happens after both are done

---

## Success Criteria

**Build passes:**
```bash
cd frontend && npm run build
# ✅ No errors
```

**Docker works:**
```bash
docker build -t sark-ui frontend/
# ✅ Image builds successfully
```

**K8s deploys:**
```bash
kubectl apply -k k8s/base/
# ✅ All resources created
```

**Documentation complete:**
- ✅ UI user guide with screenshots
- ✅ Deployment guide updated
- ✅ Troubleshooting guide
- ✅ Release notes v1.0.0

**Release tagged:**
```bash
git tag v1.0.0
git push origin v1.0.0
# ✅ Release published
```

---

**Created:** 2025-11-27
**Status:** Ready for execution
**Next:** Fix type errors (30 min) → START NOW
