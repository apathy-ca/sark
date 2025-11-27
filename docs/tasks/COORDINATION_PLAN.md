# Engineer 3 & Engineer 4 Coordination Plan

**Timeline:** Days 1-5 (Starting Now)
**Status:** ACTIVE
**Goal:** Build UI foundation and integrate with Docker infrastructure

---

## 👥 Team Assignments

### Engineer 3 (Full-Stack)
- **Days 1-2:** T3.2 - React Project Scaffold
- **Days 3-4:** T4.3 - Authentication UI & State Management
- **Day 5:** T4.4 - Data Fetching & Error Handling
- **Branch:** `task/engineer3-ui-foundation`

### Engineer 4 (DevOps)
- **Day 3:** W4-E4-01 - Vite Build Configuration
- **Day 4:** W4-E4-02 - Development Docker Compose Setup
- **Day 5:** W4-E4-03 - Production UI Dockerfile
- **Branch:** `task/engineer4-ui-docker-integration`

---

## 📅 Day-by-Day Coordination

### Days 1-2: Engineer 3 Solo Work
**Engineer 3:** Building React scaffold
**Engineer 4:** Waiting for scaffold completion

**No coordination needed** - Engineer 4 is on standby.

**Engineer 3 Deliverables for Day 2:**
- ✅ `ui/` directory structure created
- ✅ Vite + React + TypeScript configured
- ✅ Tailwind + shadcn/ui installed
- ✅ Basic routing with React Router
- ✅ Dev server runs on port 3000
- ✅ Basic layout components

**End of Day 2 - Critical Handoff:**
Engineer 3 sends notification:
```
✅ T3.2 complete - React scaffold ready
Branch: task/engineer3-ui-foundation
Commit: <hash>

@Engineer4 You can start W4-E4-01 tomorrow!
```

---

### Day 3: Parallel Work Begins

#### Morning Check-in (Both Engineers)
**Time:** Start of day
**Engineer 4:** Pull Engineer 3's branch and verify scaffold
```bash
git fetch origin task/engineer3-ui-foundation
git checkout task/engineer3-ui-foundation
cd ui/
npm install
npm run dev  # Should work!
```

**If issues:** Coordinate with Engineer 3 immediately

**Engineer 3 Actions:**
- Available for questions about scaffold structure
- Starting T4.3 (Auth UI)
- Working in `ui/src/features/auth/` and `ui/src/stores/`

**Engineer 4 Actions:**
- Working on Vite production build config
- Working in `ui/vite.config.ts`, `ui/.env.*`, `ui/scripts/`
- **No conflicts** with Engineer 3's auth work

#### Afternoon Sync
**Engineer 4:** Inform Engineer 3 about environment variables
```
📝 Added environment variables for API configuration:
- VITE_API_BASE_URL
- VITE_API_TIMEOUT

You can use these in your auth code via import.meta.env.VITE_API_BASE_URL
```

---

### Day 4: Continued Parallel Work

#### Morning Status
**Engineer 3:**
- Continuing T4.3 (Auth UI)
- Building login page, protected routes, auth store
- Working in `ui/src/` application code

**Engineer 4:**
- Starting W4-E4-02 (Docker Compose)
- Working on `docker-compose.yml`, `ui/Dockerfile.dev`
- **No conflicts** with Engineer 3's work

#### Key Coordination Point
**Engineer 4:** May need to test auth flow in Docker
**Engineer 3:** Provide test credentials or auth bypass for dev

Example coordination:
```
Engineer 4: "Testing Docker setup, do you have dev auth working yet?"
Engineer 3: "Not yet - use this bypass flag in .env: VITE_AUTH_ENABLED=false"
```

#### End of Day 4 Sync
Both engineers commit and push to their respective branches.

---

### Day 5: Final Integration

#### Morning
**Engineer 3:**
- Working on T4.4 (Data fetching)
- Creating API client, error handling
- Working in `ui/src/lib/api/`, `ui/src/hooks/`

**Engineer 4:**
- Working on W4-E4-03 (Production Dockerfile)
- Creating multi-stage build
- Working in `ui/Dockerfile`, `ui/nginx/`

#### Integration Point: Nginx Configuration
**Potential conflict:** Both touching nginx config

**Resolution:**
```
Engineer 4: "I'm updating nginx/default.conf for production routing. Are you using any special proxy headers?"
Engineer 3: "Just the standard ones for auth tokens - looks good!"
```

#### End of Day 5: Merge Strategy
**Option 1 - Sequential Merge (Recommended):**
1. Engineer 3 merges `task/engineer3-ui-foundation` first
2. Engineer 4 rebases on main and resolves any conflicts
3. Engineer 4 merges `task/engineer4-ui-docker-integration`

**Option 2 - Coordinated Merge:**
Both engineers coordinate merge at same time, testing full integration:
```bash
# Engineer 3's branch merged
git checkout main
git merge task/engineer3-ui-foundation

# Engineer 4's branch merged
git merge task/engineer4-ui-docker-integration

# Test full integration
docker-compose --profile ui-dev up
```

---

## 🔄 File Ownership (Avoid Conflicts)

### Engineer 3 Owns:
```
ui/src/                    # All application code
ui/public/                 # Static assets
ui/index.html              # HTML template
ui/package.json            # Dependencies (coordinate on this)
ui/tsconfig.json           # TypeScript config
ui/tailwind.config.js      # Tailwind config
ui/components.json         # shadcn/ui config
```

### Engineer 4 Owns:
```
ui/Dockerfile              # Production build
ui/Dockerfile.dev          # Development build
ui/.dockerignore           # Docker ignore
ui/nginx/                  # Nginx configs
ui/scripts/build-docker.sh # Docker scripts
ui/scripts/verify-build.sh # Build verification
ui/.env.example            # Example env (coordinate)
ui/.env.production         # Production env
docker-compose.yml         # Root level compose
```

### Shared Files (Coordinate!):
```
ui/vite.config.ts          # Both may modify
ui/.env                    # Development env
ui/package.json            # Dependencies
```

**Protocol for shared files:**
1. Communicate before modifying
2. Pull latest before editing
3. Push frequently to avoid drift
4. Use comments to mark your changes

---

## 🚨 Conflict Resolution

### If Files Conflict During Merge:

**For `ui/vite.config.ts`:**
```bash
# Keep both sets of changes, merge manually
# Engineer 3's plugins + Engineer 4's build config
```

**For `ui/package.json`:**
```bash
# Merge dependencies
# Keep all scripts from both branches
npm install  # Re-resolve lockfile
```

**For `ui/.env`:**
```bash
# Combine all variables
# Remove duplicates
# Engineer 4's take precedence for build-related vars
```

### Escalation
If conflicts can't be resolved:
1. Create temporary branch with both changes
2. Test functionality
3. Both engineers review together
4. Merge consensus version

---

## ✅ Success Metrics

### Day 2 End:
- [ ] Engineer 3: React scaffold complete
- [ ] Engineer 4: Notified and ready to start

### Day 3 End:
- [ ] Engineer 3: Auth store and login page in progress
- [ ] Engineer 4: Production build config complete
- [ ] Both: No blocking issues

### Day 4 End:
- [ ] Engineer 3: Protected routes working
- [ ] Engineer 4: Docker Compose dev working
- [ ] Both: Hot reload functional

### Day 5 End:
- [ ] Engineer 3: Data fetching and error handling complete
- [ ] Engineer 4: Production Dockerfile complete
- [ ] Both: All branches merged to main
- [ ] Integration: `docker-compose --profile ui-dev up` works end-to-end

---

## 💬 Communication Channels

### Daily Standups
**Time:** 9:00 AM
**Format:**
```
Engineer 3:
- Yesterday: [completed work]
- Today: [planned work]
- Blockers: [any issues]

Engineer 4:
- Yesterday: [completed work]
- Today: [planned work]
- Blockers: [any issues]
- Dependencies: [waiting on Engineer 3?]
```

### Slack
**Channel:** `#sark-improvements-ui`
**Use for:**
- Quick questions
- File conflict warnings
- "I'm about to modify X file"
- Merge notifications

### Git Commit Messages
**Tag coordinated work:**
```bash
git commit -m "feat(ui): add auth store

Coordinates with Engineer 4's Docker setup.
Uses VITE_API_BASE_URL from .env config.

Part of T4.3"
```

---

## 🎯 End Goal

After 5 days, we have:

### Engineer 3's Contributions:
- ✅ Complete React application scaffold
- ✅ Authentication system with login, protected routes, token refresh
- ✅ Data fetching layer with React Query
- ✅ Error handling and loading states
- ✅ Reusable auth components

### Engineer 4's Contributions:
- ✅ Production build configuration
- ✅ Docker development environment with hot reload
- ✅ Production-ready multi-stage Dockerfile
- ✅ Nginx configuration for SPA + API proxy
- ✅ Health checks and security headers

### Combined Result:
- ✅ UI accessible at `http://localhost:3000` (dev)
- ✅ Full-stack Docker: `docker-compose --profile ui-dev up`
- ✅ Production-ready: `docker build -t sark-ui -f ui/Dockerfile ./ui`
- ✅ 14 Engineer 4 tasks UNBLOCKED
- ✅ Engineer 1 (Frontend) can start Week 4+ tasks
- ✅ QA can begin E2E testing setup

---

## 📞 Emergency Contact

**Blocked on Day 3?**
- Engineer 3's scaffold not ready → Engineer 4 waits
- Engineer 4 can start documenting approach in meantime

**Blocked on Day 4?**
- Docker issues → Engineer 4 troubleshoots
- Auth issues → Engineer 3 troubleshoots
- **Not blocking each other** - parallel work

**Blocked on Day 5?**
- Merge conflicts → Resolve together
- Integration test fails → Debug together
- **Pair programming session** if needed

---

## 🚀 You've Got This!

Two engineers, 5 days, full UI foundation. Let's ship it! 🎉

---

**Last Updated:** 2025-11-27
**Status:** Active
**Next Review:** End of Day 2 (Engineer 3 completes scaffold)
