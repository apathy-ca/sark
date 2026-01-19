# SARK Improvement Plan - Work Tasks

**Team:** 4 Engineers, 1 QA, 1 Documenter
**Timeline:** 8 weeks
**Total Tasks:** 24 major tasks (vs 124 micro-sessions)

Each task is designed to be handled by a single Claude Code instance or team member working autonomously.

---

## Week 1: MCP Definition (4 tasks)

### T1.1 - MCP Documentation Package
**Owner:** Documenter
**Duration:** 2-3 days
**Deliverables:**
- Update README.md with comprehensive MCP definition (first 100 lines)
- Create `docs/MCP_INTRODUCTION.md` (complete guide)
- Update `docs/GLOSSARY.md` with prominent MCP entries
- Update `docs/FAQ.md` with "What is MCP?" section

**Acceptance Criteria:**
- MCP defined without assumptions of prior knowledge
- Real-world examples included
- Links to MCP specification
- Reviewed and approved by 2+ engineers

---

### T1.2 - MCP Visual Diagrams
**Owner:** Engineer 3
**Duration:** 1-2 days
**Deliverables:**
- Create `docs/diagrams/mcp-concepts/` directory
- 4 Mermaid diagrams:
  - `01-basic-mcp-flow.svg` - Simple MCP interaction
  - `02-ungoverned-mcp-risks.svg` - Security risks
  - `03-sark-governance-layer.svg` - How SARK adds control
  - `04-enterprise-mcp-architecture.svg` - Full enterprise view
- Integrate diagrams into MCP_INTRODUCTION.md

**Acceptance Criteria:**
- Diagrams render correctly in GitHub
- Clear visual flow
- Accessible alt text

---

### T1.3 - MCP Code Examples
**Owner:** Engineer 2
**Duration:** 1 day
**Deliverables:**
- Create `examples/mcp-servers/` directory
- 3 example MCP servers:
  - `minimal-server.json` - Simplest possible server
  - `database-server.json` - Database query example
  - `api-server.json` - REST API integration example
- Add examples to documentation

**Acceptance Criteria:**
- Examples are valid and tested
- Clear comments explaining each field
- Referenced in quickstart guide

---

### T1.4 - Documentation QA & Integration
**Owner:** QA
**Duration:** 1 day
**Deliverables:**
- Review all Week 1 documentation for clarity
- Test all code examples
- Verify links and cross-references
- Create issue list for any gaps
- Final approval checklist

**Acceptance Criteria:**
- Zero broken links
- All examples work
- Documentation flows logically
- Ready for publication

---

## Week 2: Simplified Onboarding (4 tasks)

### T2.1 - Ultra-Simple Quickstart
**Owner:** Documenter
**Duration:** 2 days
**Deliverables:**
- Create `docs/GETTING_STARTED_5MIN.md`
- Test and document 3-command workflow
- Create `docker-compose.minimal.yml` profile
- Update main README with quickstart link

**Acceptance Criteria:**
- New user can run SARK in <5 minutes
- Tested on clean Ubuntu/Mac environment
- Clear error messages for common issues

---

### T2.2 - Progressive Learning Path
**Owner:** Documenter
**Duration:** 2 days
**Deliverables:**
- Create `docs/LEARNING_PATH.md`
- Create `docs/ONBOARDING_CHECKLIST.md`
- Define 4 learning levels (Beginner → Expert)
- Link existing docs into progression

**Acceptance Criteria:**
- Clear path from beginner to expert
- Estimated time for each level
- Checkboxes for tracking progress

---

### T2.3 - Interactive Tutorials Package
**Owner:** Engineer 3
**Duration:** 3 days
**Deliverables:**
- Create `examples/tutorials/` directory
- Tutorial 1: Basic Setup
  - `tutorial-01-basic-setup/README.md`
  - `docker-compose.yml`
  - `sample-server.json`
- Tutorial 2: Authentication
  - `tutorial-02-authentication/README.md`
  - Sample LDAP config
  - Test users
- Tutorial 3: Writing Policies
  - `tutorial-03-policies/README.md`
  - 5 example policies
  - Policy tests

**Acceptance Criteria:**
- Each tutorial works standalone
- Clear step-by-step instructions
- Estimated completion time listed

---

### T2.4 - Docker Compose Profiles
**Owner:** Engineer 4
**Duration:** 1-2 days
**Deliverables:**
- Update `docker-compose.yml` with profiles:
  - `minimal` - API + PostgreSQL + Redis + OPA only
  - `standard` - + Auth + Monitoring
  - `full` - Everything including Kong, Vault
- Document profile usage in README
- Test each profile on clean system

**Acceptance Criteria:**
- `minimal` starts in <30 seconds
- `standard` has monitoring working
- `full` includes all services
- Clear documentation on when to use each

---

## Week 3: UI Planning (3 tasks)

### T3.1 - UI Architecture & Technology Selection
**Owner:** Engineer 1
**Duration:** 2-3 days
**Deliverables:**
- Technology selection document with rationale
- Complete wireframes for all pages:
  - Dashboard
  - MCP Servers (list, detail, register)
  - Policies (list, editor, testing)
  - Users & Teams
  - Audit Logs
  - Settings
- UI component catalog
- Design system (colors, typography, spacing)

**Acceptance Criteria:**
- Team consensus on tech stack
- Wireframes approved by stakeholders
- Design system documented

---

### T3.2 - React Project Scaffold
**Owner:** Engineer 3
**Duration:** 2 days
**Deliverables:**
- Create `ui/` directory
- Set up React + TypeScript + Vite
- Configure shadcn/ui + Tailwind CSS
- Set up React Router
- Configure TanStack Query + Zustand
- Create project structure:
  ```
  ui/
  ├── src/
  │   ├── components/ui/
  │   ├── components/layout/
  │   ├── components/features/
  │   ├── pages/
  │   ├── lib/
  │   ├── hooks/
  │   ├── api/
  │   └── types/
  ```
- Basic build and dev server working

**Acceptance Criteria:**
- `npm run dev` starts dev server
- `npm run build` creates production build
- TypeScript with no errors
- Hot reload working

---

### T3.3 - API Client & Authentication Setup
**Owner:** Engineer 2
**Duration:** 2 days
**Deliverables:**
- Auto-generate API client from OpenAPI spec
- Add CORS support to API
- Implement session/token management
- Add UI-specific endpoints if needed:
  - `/api/v1/ui/dashboard/metrics`
  - `/api/v1/ui/health`
- Create authentication flow (OIDC)
- Test auth integration between UI and API

**Acceptance Criteria:**
- API client auto-generated
- Auth flow working end-to-end
- CORS configured correctly
- Session management secure

---

## Week 4: UI Foundation (4 tasks)

### T4.1 - Layout & Navigation System
**Owner:** Engineer 1
**Duration:** 2-3 days
**Deliverables:**
- App shell with header, sidebar, main content
- Navigation menu with routes:
  - Dashboard
  - Servers
  - Policies
  - Users
  - Audit Logs
  - Settings
- User menu with profile/logout
- Responsive layout (desktop/tablet/mobile)
- Loading states and error boundaries

**Acceptance Criteria:**
- Navigation works between all routes
- Mobile-friendly sidebar (drawer)
- User context displayed in header
- Logout redirects correctly

---

### T4.2 - Base Component Library
**Owner:** Engineer 1
**Duration:** 2 days
**Deliverables:**
- Implement core shadcn/ui components:
  - Button, Input, Select, Checkbox, Radio
  - Card, Table, Tabs
  - Dialog, Sheet, Toast
  - Form components (with React Hook Form)
- Create custom components:
  - LoadingSpinner
  - EmptyState
  - ErrorAlert
  - ConfirmDialog
- Component documentation (Storybook optional)

**Acceptance Criteria:**
- All components styled consistently
- Dark mode support
- Accessible (keyboard nav, ARIA labels)
- TypeScript types for all props

---

### T4.3 - Authentication UI & State Management
**Owner:** Engineer 3
**Duration:** 2 days
**Deliverables:**
- Login page with OIDC flow
- Protected route wrapper
- Auth state management (Zustand store)
- Token refresh logic
- Logout functionality
- Auth error handling

**Acceptance Criteria:**
- Users can log in via OIDC
- Protected routes redirect to login
- Tokens refresh automatically
- Logout clears all state

---

### T4.4 - Data Fetching & Error Handling
**Owner:** Engineer 3
**Duration:** 1-2 days
**Deliverables:**
- Configure TanStack Query defaults
- Create query hooks for common operations:
  - `useServers()`, `useServer(id)`
  - `usePolicies()`, `usePolicy(id)`
  - `useUsers()`, `useAuditLogs()`
- Global error handling
- Toast notification system
- Network error recovery

**Acceptance Criteria:**
- Queries cache appropriately
- Errors display user-friendly messages
- Loading states work consistently
- Retry logic for failed requests

---

## Week 5: UI Core Features (4 tasks)

### T5.1 - Dashboard Page
**Owner:** Engineer 1
**Duration:** 2 days
**Deliverables:**
- Dashboard layout with metrics cards:
  - Total MCP servers
  - Active servers
  - Policy decisions (allowed/denied)
  - Recent audit events
- Real-time metrics charts (Recharts)
- Quick actions section
- Recent activity feed

**Acceptance Criteria:**
- Metrics update in real-time
- Charts render correctly
- Quick actions work
- Mobile responsive

---

### T5.2 - MCP Servers Management
**Owner:** Engineer 3
**Duration:** 3 days
**Deliverables:**
- **Servers List Page:**
  - Table/grid view with search/filter
  - Health status indicators
  - Pagination
- **Server Detail Page:**
  - Server info and metadata
  - Tools/Resources/Prompts tabs
  - Health history
  - Edit/Delete actions
- **Register Server Form:**
  - Multi-step form
  - JSON schema validation
  - Server health check
  - Success/error feedback

**Acceptance Criteria:**
- Can view all servers
- Can register new server
- Can view server details
- Can delete server (with confirmation)

---

### T5.3 - Policy Viewer & User Management
**Owner:** Engineer 1
**Duration:** 2 days
**Deliverables:**
- **Policy List Page:**
  - List of policies
  - Filter by type/environment
  - Basic policy viewer (read-only)
- **User List Page:**
  - User table with search
  - User details modal
  - Role badges
  - Team memberships

**Acceptance Criteria:**
- Can view all policies
- Can view policy content
- Can see all users
- Can filter and search

---

### T5.4 - Audit Log Viewer
**Owner:** Engineer 3
**Duration:** 2 days
**Deliverables:**
- **Audit Logs Page:**
  - Event table with columns:
    - Timestamp
    - User
    - Action
    - Resource
    - Decision
    - IP Address
  - Advanced filters:
    - Date range
    - Event type
    - User
    - Decision (allow/deny)
  - Search functionality
  - Pagination (infinite scroll or pages)
  - Event detail modal

**Acceptance Criteria:**
- Can view all audit events
- Filters work correctly
- Search is fast (<500ms)
- Can export results (CSV/JSON)

---

## Week 6: UI Advanced Features (3 tasks)

### T6.1 - Policy Editor with Monaco
**Owner:** Engineer 1
**Duration:** 3 days
**Deliverables:**
- Integrate Monaco editor
- Rego syntax highlighting
- Policy editor page:
  - File tree for policies
  - Editor pane
  - Save/Cancel buttons
  - Syntax validation
- Policy testing panel:
  - Input JSON editor
  - "Test Policy" button
  - Results display
  - Pass/fail indicator

**Acceptance Criteria:**
- Monaco editor works smoothly
- Rego syntax highlighted
- Can save policies
- Can test policies inline

---

### T6.2 - Settings & API Key Management
**Owner:** Engineer 3
**Duration:** 2 days
**Deliverables:**
- **Settings Page with tabs:**
  - General settings
  - Authentication providers config
  - SIEM integration config
  - Notification settings
- **API Keys Page:**
  - List of API keys
  - Create new key modal
  - Copy to clipboard
  - Revoke key
  - Scopes/permissions UI

**Acceptance Criteria:**
- Can view/update settings
- Can create API keys
- Can revoke keys
- Keys never shown again after creation

---

### T6.3 - Advanced Features & Export
**Owner:** Engineer 2
**Duration:** 2 days
**Deliverables:**
- Export functionality:
  - Audit logs to CSV/JSON
  - Server configurations
  - Policy bundles
- Real-time updates (WebSocket):
  - New audit events
  - Server status changes
  - Policy decision metrics
- Batch operations:
  - Bulk server registration
  - Bulk policy deployment

**Acceptance Criteria:**
- Exports work for large datasets
- Real-time updates don't break UI
- Batch operations have progress indicators

---

## Week 7: Polish & Accessibility (3 tasks)

### T7.1 - Responsive Design & Dark Mode
**Owner:** Engineer 1
**Duration:** 2 days
**Deliverables:**
- Mobile optimization for all pages
- Tablet layout adjustments
- Dark mode implementation
- Theme toggle in user menu
- Theme persistence in localStorage

**Acceptance Criteria:**
- All pages work on mobile (375px+)
- Tablet layout optimized (768px+)
- Dark mode looks polished
- Theme persists across sessions

---

### T7.2 - Accessibility & UX Polish
**Owner:** Engineer 1
**Duration:** 2-3 days
**Deliverables:**
- WCAG 2.1 AA compliance:
  - Keyboard navigation for all features
  - ARIA labels and roles
  - Focus indicators
  - Color contrast ratios
- UX improvements:
  - Helpful error messages
  - Contextual help tooltips
  - Keyboard shortcuts (modal)
  - Loading skeletons
  - Empty states

**Acceptance Criteria:**
- Passes axe accessibility audit
- Keyboard-only navigation works
- Screen reader compatible
- Lighthouse accessibility score >90

---

### T7.3 - Performance Optimization & Testing
**Owner:** QA
**Duration:** 2-3 days
**Deliverables:**
- Performance audit:
  - Lighthouse performance score
  - Bundle size analysis
  - Lazy loading for routes
  - Image optimization
- Comprehensive testing:
  - E2E tests (Playwright)
  - Component tests (Vitest)
  - Cross-browser testing
  - Performance testing
- Bug fixes from testing

**Acceptance Criteria:**
- Lighthouse performance >85
- Bundle size <500KB (gzipped)
- E2E tests cover critical paths
- Works in Chrome, Firefox, Safari, Edge

---

## Week 8: Integration & Launch (2 tasks)

### T8.1 - Docker & Kubernetes Integration
**Owner:** Engineer 4
**Duration:** 3-4 days
**Deliverables:**
- **Docker Integration:**
  - `ui/Dockerfile` (multi-stage build)
  - Nginx config for SPA routing
  - Add UI service to `docker-compose.yml`
  - Environment-based config
- **Kubernetes Deployment:**
  - Update `k8s/` manifests
  - Add UI deployment, service, ingress
  - Update Helm chart
  - ConfigMap for environment variables
- **CI/CD:**
  - Build pipeline for UI
  - Automated testing in CI
  - Docker image publishing

**Acceptance Criteria:**
- `docker compose up` includes UI
- UI accessible at http://localhost:3000
- Kubernetes deployment works
- Helm chart updated

---

### T8.2 - Final Testing, Documentation & Launch
**Owner:** QA + Documenter
**Duration:** 2-3 days
**Deliverables:**
- **QA (QA Engineer):**
  - Full integration testing
  - Security testing (OWASP Top 10)
  - Load testing
  - Final bug fixes
  - Sign-off checklist
- **Documentation (Documenter):**
  - UI user guide
  - Deployment documentation
  - Troubleshooting guide
  - Update main README
  - Create release notes
  - Demo video/screenshots

**Acceptance Criteria:**
- All P0/P1 bugs fixed
- Security scan passes
- Documentation complete
- Ready for launch announcement

---

## Task Summary

| Week | Tasks | Focus | Key Deliverable |
|------|-------|-------|-----------------|
| **1** | 4 | MCP Definition | Complete MCP documentation |
| **2** | 4 | Onboarding | 5-min quickstart + tutorials |
| **3** | 3 | UI Planning | React project ready |
| **4** | 4 | UI Foundation | Auth + components working |
| **5** | 4 | UI Core | Dashboard + main pages |
| **6** | 3 | UI Advanced | Policy editor + settings |
| **7** | 3 | Polish | Accessibility + performance |
| **8** | 2 | Launch | Docker + K8s + docs |
| **Total** | **27** | | **Production Ready UI** |

## Team Load Balance

| Role | Tasks | Estimated Days |
|------|-------|----------------|
| **Documenter** | 4 tasks | 9 days |
| **Engineer 1** (Frontend) | 8 tasks | 17 days |
| **Engineer 2** (Backend/API) | 3 tasks | 6 days |
| **Engineer 3** (Full-Stack) | 8 tasks | 17 days |
| **Engineer 4** (DevOps) | 2 tasks | 5 days |
| **QA** | 3 tasks | 7 days |

**Note:** Engineers 1, 2, 3 can help each other when needed for load balancing.

## Critical Path

```
Week 1: T1.1 (MCP docs) must complete first
         ↓
Week 2: T2.1 (5-min guide) depends on T1.1
         ↓
Week 3: T3.2 (React scaffold) must complete before Week 4
         ↓
Week 4: T4.3 (Auth) blocks all feature work
         ↓
Week 5-6: Feature development (can parallelize)
         ↓
Week 7: Polish (depends on features complete)
         ↓
Week 8: Integration → Launch
```

## Task Templates for Claude Code

### Starting a Task

```bash
# Create task branch
git checkout -b task/T1.1-mcp-documentation

# Review task requirements
cat docs/WORK_TASKS.md | grep -A 20 "T1.1"

# Create task tracking issue (optional)
gh issue create --title "T1.1 - MCP Documentation Package" \
  --body "$(cat docs/WORK_TASKS.md | grep -A 20 'T1.1')"
```

### Completing a Task

```bash
# Ensure acceptance criteria met
# Run tests
# Commit changes
git add .
git commit -m "feat: complete T1.1 - MCP documentation package

- Added MCP definition to README
- Created MCP_INTRODUCTION.md
- Updated GLOSSARY.md
- Updated FAQ.md

Closes #[issue-number]"

# Push and create PR
git push origin task/T1.1-mcp-documentation
gh pr create --title "[T1.1] MCP Documentation Package" \
  --body "Completes T1.1 MCP Documentation Package

## Deliverables
- [x] README.md with MCP definition
- [x] MCP_INTRODUCTION.md
- [x] GLOSSARY.md updated
- [x] FAQ.md updated

## Acceptance Criteria
- [x] MCP defined without assumptions
- [x] Real-world examples included
- [x] Links to specification
- [x] Reviewed by 2+ engineers"
```

---

**This task breakdown provides:**
- ✅ Manageable units of work (1-3 days each)
- ✅ Clear ownership and deliverables
- ✅ Acceptance criteria for each task
- ✅ Suitable for autonomous Claude Code instances
- ✅ Realistic 8-week timeline
- ✅ Balanced workload across team

**Ready to start Task T1.1 on Monday!** 🚀
