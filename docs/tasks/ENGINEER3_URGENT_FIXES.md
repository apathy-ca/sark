# Engineer 3 - URGENT: Fix TypeScript Errors

**Priority:** 🔴 CRITICAL - BLOCKING ALL OTHER WORKERS
**Estimated Time:** 3-4 hours
**Branch:** Current branch
**Status:** The UI is 95% complete but cannot build due to type errors

---

## Mission

Fix 26 TypeScript errors preventing `npm run build` from succeeding. Once this is complete, Engineer 4 and Documenter can proceed.

---

## The 26 TypeScript Errors to Fix

### 1. Axios Import Errors (3 errors)
**File:** `frontend/src/services/api.ts:6`

**Current:**
```typescript
import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios'
```

**Fix:**
```typescript
import axios from 'axios'
import type { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios'
```

**Also remove unused AuditEvent import on line 28**

---

### 2. Policy Type Missing Fields (13 errors)
**Files:** `frontend/src/types/api.ts`, `frontend/src/pages/policies/PoliciesPage.tsx`

**Current Policy interface is incomplete**

**Fix - Add to Policy interface in `frontend/src/types/api.ts`:**
```typescript
export interface Policy {
  id: string
  content: string          // ADD THIS
  package_name: string     // ADD THIS
  created_at: string       // ADD THIS
  updated_at: string
  version: number
}
```

**Check API response structure:**
- If `policyApi.list()` returns flat array `Policy[]`: Update PoliciesPage.tsx lines 140, 143, 148 to use `data` instead of `data.policies`
- If it returns `{ policies: Policy[] }`: Keep as is

**Add missing policyApi.upload() method in `frontend/src/services/api.ts`:**
```typescript
export const policyApi = {
  // ... existing methods ...

  upload: async (file: File): Promise<Policy> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post<Policy>(`${API_PREFIX}/policies/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  },
}
```

**OR if upload endpoint doesn't exist:** Remove upload UI from PoliciesPage.tsx line 29

---

### 3. ServerListItem Type Missing Fields (4 errors)
**Files:** `frontend/src/types/api.ts`, `frontend/src/pages/servers/ServersListPage.tsx`

**Fix - Add to ServerListItem in `frontend/src/types/api.ts`:**
```typescript
export interface ServerListItem {
  id: string
  name: string
  description: string    // ADD THIS
  status: string
  transport: string
  tool_count: number     // ADD THIS
  created_at: string
}
```

---

### 4. ServerListParams Missing Field (1 error)
**File:** `frontend/src/types/api.ts`

**Fix - Add to ServerListParams:**
```typescript
export interface ServerListParams {
  page?: number
  limit?: number
  search?: string
  status?: string
  sensitivity_level?: string  // ADD THIS
}
```

---

### 5. ServerResponse Missing ID Field (1 error)
**File:** `frontend/src/types/api.ts`

**Fix - Add to ServerResponse:**
```typescript
export interface ServerResponse {
  id: string           // ADD THIS (verify field name in actual API)
  // ... other fields
}
```

---

### 6. Zod Schema Errors in ServerRegisterPage (4 errors)
**File:** `frontend/src/pages/servers/ServerRegisterPage.tsx:13,19,29`

**Current (line 13):**
```typescript
transport: z.enum(['http', 'stdio', 'sse'], { required_error: '...' })
```

**Fix:**
```typescript
transport: z.enum(['http', 'stdio', 'sse'], {
  errorMap: () => ({ message: 'Please select a transport type' })
})
```

**Lines 19 and 29:** Check z.object() calls - ensure all required arguments provided

---

## Step-by-Step Process

### Step 1: Fix Type Definitions (1-2 hours)
```bash
cd /home/user/sark/frontend

# 1. Update frontend/src/types/api.ts
#    - Add missing fields to Policy, ServerListItem, ServerListParams, ServerResponse
#    - Verify response structures match actual API

# 2. Fix frontend/src/services/api.ts
#    - Change to type-only imports for Axios types
#    - Remove unused AuditEvent import
#    - Add policyApi.upload() OR remove UI reference
```

### Step 2: Fix Component Errors (1 hour)
```bash
# 3. Fix frontend/src/pages/servers/ServerRegisterPage.tsx
#    - Update Zod enum syntax (3 locations)
#    - Fix z.object() calls

# 4. Fix frontend/src/pages/policies/PoliciesPage.tsx
#    - Update array access if API returns flat arrays
```

### Step 3: Verify Build (30 minutes)
```bash
cd /home/user/sark/frontend

# Test TypeScript compilation
npm run type-check

# Build for production
npm run build

# Should succeed with no errors!
```

### Step 4: Test Docker Build (30 minutes)
```bash
cd /home/user/sark/frontend

# Test Docker build
docker build -t sark-ui .

# Should succeed!
```

---

## Success Criteria

✅ All 26 TypeScript errors resolved
✅ `npm run build` completes successfully
✅ `docker build -t sark-ui frontend/` succeeds
✅ Built dist/ directory contains valid files

---

## Once Complete

**Notify team:**
```
✅ TypeScript errors fixed!
✅ Build succeeds: npm run build
✅ Docker build works
✅ Engineer 4 UNBLOCKED - can start dev Docker
✅ Ready for final testing
```

**Push your fixes:**
```bash
git add frontend/
git commit -m "fix(ui): resolve 26 TypeScript errors blocking build

- Fix Axios type imports in api.ts
- Add missing fields to Policy, ServerListItem, ServerListParams types
- Fix Zod enum syntax in ServerRegisterPage
- Add policyApi.upload() method
- Build now succeeds

Unblocks Engineer 4 and Documenter"

git push -u origin claude/czar-status-check-014qXWKcUU22kiCAUXBFSt2H
```

---

## Need Help?

**TypeScript error reference:**
- All errors listed in `docs/OMNIBUS_ALL_WORKERS_FINAL.md` lines 64-198
- Check actual API responses by running backend and testing endpoints
- Backend API docs: `docs/API_REFERENCE.md` (880+ lines)

**Testing backend API:**
```bash
# Start backend
docker-compose --profile minimal up

# API available at http://localhost:8000
# Check /docs for OpenAPI spec
```

---

**YOU'RE 95% DONE! Just need these type fixes! 🚀**

**Created:** 2025-11-27
**Priority:** CRITICAL
**Blocking:** Engineer 4, Documenter
**Target:** Complete in 3-4 hours
