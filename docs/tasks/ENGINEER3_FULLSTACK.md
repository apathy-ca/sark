# Engineer 3 (Full-Stack) Tasks

**Your Role:** Full-Stack Development - Bridge between frontend and backend
**Total Tasks:** 8 tasks over 8 weeks
**Estimated Effort:** ~17 days

You're the Swiss Army knife - handle both UI features and backend integration.

---

## Your Tasks

### ✅ T1.2 - MCP Visual Diagrams
**Week:** 1
**Duration:** 1-2 days
**Priority:** P1 (High - needed for documentation)

**What you're building:**
Visual diagrams that explain MCP concepts for non-technical users.

**Deliverables:**
1. Create `docs/diagrams/mcp-concepts/` directory

2. **Four Mermaid Diagrams:**

   **01-basic-mcp-flow.svg:**
   ```mermaid
   sequenceDiagram
       AI->>MCP Server: Request tool execution
       MCP Server->>Database: Query data
       Database-->>MCP Server: Results
       MCP Server-->>AI: Return results
   ```

   **02-ungoverned-mcp-risks.svg:**
   - Show security risks without governance
   - Unauthorized access, no audit trail, data leaks

   **03-sark-governance-layer.svg:**
   - Show how SARK sits between AI and MCP servers
   - Policy check, audit, security

   **04-enterprise-mcp-architecture.svg:**
   - Full enterprise deployment
   - Multiple servers, policies, monitoring

3. **Integration:**
   - Add diagrams to `docs/MCP_INTRODUCTION.md`
   - Ensure they render in GitHub
   - Add alt text for accessibility

**Acceptance Criteria:**
- [ ] All 4 diagrams created and clear
- [ ] Render correctly in GitHub markdown
- [ ] Integrated into documentation
- [ ] Alt text provided

**Claude Code Prompt:**
```
Create 4 Mermaid diagrams explaining MCP concepts for SARK documentation.

Build:
1. 01-basic-mcp-flow.svg - Simple MCP interaction
2. 02-ungoverned-mcp-risks.svg - Security risks without governance
3. 03-sark-governance-layer.svg - How SARK adds control
4. 04-enterprise-mcp-architecture.svg - Full enterprise deployment

Save in docs/diagrams/mcp-concepts/ and integrate into MCP_INTRODUCTION.md
```

---

### ✅ T2.3 - Interactive Tutorials Package
**Week:** 2
**Duration:** 3 days
**Priority:** P1 (High - critical for onboarding)

**What you're building:**
Hands-on tutorials that walk users through SARK features.

**Deliverables:**
1. Create `examples/tutorials/` directory

2. **Tutorial 1: Basic Setup** (`tutorial-01-basic-setup/`):
   - `README.md` - Step-by-step guide
   - `docker-compose.yml` - Minimal SARK setup
   - `sample-server.json` - Example server
   - Test script to verify setup

3. **Tutorial 2: Authentication** (`tutorial-02-authentication/`):
   - `README.md` - LDAP setup walkthrough
   - `ldap-config.yml` - Sample LDAP config
   - `test-users.ldif` - Sample users
   - Test script to verify auth works

4. **Tutorial 3: Writing Policies** (`tutorial-03-policies/`):
   - `README.md` - Policy writing workshop
   - 5 example policies:
     - `01-allow-all.rego` - Simple allow policy
     - `02-rbac.rego` - Role-based access
     - `03-team-based.rego` - Team ownership
     - `04-time-based.rego` - Business hours only
     - `05-sensitivity.rego` - Data classification
   - `test-policies.sh` - Test all policies
   - `test-cases.json` - Test inputs and expected outputs

5. **Tutorial README template:**
   - Objectives
   - Prerequisites
   - Estimated time
   - Step-by-step instructions
   - Expected outcomes
   - Troubleshooting section
   - Next steps

**Acceptance Criteria:**
- [ ] All 3 tutorials work standalone
- [ ] Clear step-by-step instructions
- [ ] Estimated completion time listed
- [ ] Test scripts verify success
- [ ] Referenced in LEARNING_PATH.md

**Claude Code Prompt:**
```
Create 3 interactive tutorials for SARK onboarding.

Build:
1. Tutorial 1: Basic Setup - Get SARK running
2. Tutorial 2: Authentication - Configure LDAP
3. Tutorial 3: Writing Policies - 5 policy examples with tests

Make each tutorial self-contained with README, config files, and test scripts.
Include estimated completion times and troubleshooting sections.
```

---

### ✅ T3.2 - React Project Scaffold
**Week:** 3
**Duration:** 2 days
**Priority:** P0 (Critical - blocks all UI work)

**What you're building:**
The React project foundation that everyone will build on.

**Deliverables:**
1. **Create `ui/` directory**

2. **Initialize React + TypeScript + Vite:**
   ```bash
   npm create vite@latest ui -- --template react-ts
   cd ui
   npm install
   ```

3. **Install Dependencies:**
   ```bash
   # UI Framework
   npm install -D tailwindcss postcss autoprefixer
   npx tailwindcss init -p

   # shadcn/ui
   npx shadcn-ui@latest init

   # Routing
   npm install react-router-dom

   # State Management
   npm install @tanstack/react-query zustand

   # Forms
   npm install react-hook-form zod @hookform/resolvers

   # API Client
   npm install @hey-api/openapi-ts axios

   # Dev Tools
   npm install -D @types/node
   ```

4. **Project Structure:**
   ```
   ui/
   ├── public/
   ├── src/
   │   ├── components/
   │   │   ├── ui/              # shadcn components
   │   │   ├── layout/          # Layout components
   │   │   └── features/        # Feature components
   │   ├── pages/               # Page components
   │   ├── lib/                 # Utilities
   │   ├── hooks/               # Custom hooks
   │   ├── api/                 # API client
   │   ├── types/               # TypeScript types
   │   ├── stores/              # Zustand stores
   │   ├── App.tsx
   │   ├── main.tsx
   │   └── index.css
   ├── package.json
   ├── tsconfig.json
   ├── vite.config.ts
   ├── tailwind.config.js
   └── components.json
   ```

5. **Configure:**
   - React Router setup
   - TanStack Query provider
   - Tailwind CSS
   - Path aliases (`@/components`, etc.)

6. **Test:**
   - `npm run dev` starts dev server
   - `npm run build` creates production build
   - No TypeScript errors

**Acceptance Criteria:**
- [ ] Dev server runs at http://localhost:3000
- [ ] Hot reload works
- [ ] TypeScript compiles with no errors
- [ ] Tailwind CSS working
- [ ] Path aliases work
- [ ] README.md with setup instructions

**Claude Code Prompt:**
```
Set up React + TypeScript + Vite project for SARK UI.

Create ui/ directory with:
1. React 18 + TypeScript + Vite
2. Tailwind CSS + shadcn/ui
3. React Router for routing
4. TanStack Query for data fetching
5. Zustand for state management
6. Proper project structure

Ensure dev server runs and build works.
Add README.md with setup instructions.
```

---

### ✅ T4.3 - Authentication UI & State Management
**Week:** 4
**Duration:** 2 days
**Priority:** P0 (Critical - blocks all features)

**What you're building:**
User authentication and session management for the UI.

**Deliverables:**
1. **Login Page** (`src/pages/Login.tsx`):
   - OIDC login button
   - Handle OAuth redirect flow
   - Loading states
   - Error messages

2. **Auth Store** (`src/stores/authStore.ts`):
   ```typescript
   interface AuthStore {
     user: User | null
     token: string | null
     isAuthenticated: boolean
     login: (code: string) => Promise<void>
     logout: () => void
     refreshToken: () => Promise<void>
   }
   ```

3. **Protected Route Component:**
   ```typescript
   <ProtectedRoute>
     <Dashboard />
   </ProtectedRoute>
   ```
   - Redirect to login if not authenticated
   - Show loading while checking auth

4. **Token Management:**
   - Store token in localStorage (or httpOnly cookie)
   - Add token to all API requests
   - Auto-refresh before expiration
   - Handle refresh failures

5. **User Context:**
   - Current user info
   - User roles/permissions
   - Display in header

**Acceptance Criteria:**
- [ ] Users can log in via OIDC
- [ ] Protected routes redirect to login
- [ ] Tokens refresh automatically
- [ ] Logout clears all state
- [ ] Auth persists across page reloads

**Dependencies:**
- T3.3 (Engineer 2 must configure CORS and auth endpoints)

**Claude Code Prompt:**
```
Build authentication for SARK UI.

Create:
1. Login page with OIDC flow
2. Auth state management (Zustand store)
3. Protected route wrapper
4. Token refresh logic
5. Logout functionality

Use the SARK API for authentication.
Store tokens securely and handle refresh.
```

---

### ✅ T4.4 - Data Fetching & Error Handling
**Week:** 4
**Duration:** 1-2 days
**Priority:** P1 (High - foundation for all features)

**What you're building:**
Centralized data fetching and error handling.

**Deliverables:**
1. **Configure TanStack Query:**
   ```typescript
   const queryClient = new QueryClient({
     defaultOptions: {
       queries: {
         staleTime: 1000 * 60 * 5, // 5 minutes
         cacheTime: 1000 * 60 * 10, // 10 minutes
         retry: 1,
         refetchOnWindowFocus: false,
       },
     },
   })
   ```

2. **Create Query Hooks** (`src/api/hooks.ts`):
   ```typescript
   export const useServers = () =>
     useQuery(['servers'], () => api.servers.list())

   export const useServer = (id: string) =>
     useQuery(['server', id], () => api.servers.get(id))

   export const usePolicies = () =>
     useQuery(['policies'], () => api.policies.list())

   export const useAuditLogs = (filters: AuditFilters) =>
     useQuery(['audit', filters], () => api.audit.list(filters))
   ```

3. **Mutation Hooks:**
   ```typescript
   export const useCreateServer = () =>
     useMutation((data: ServerCreate) => api.servers.create(data), {
       onSuccess: () => {
         queryClient.invalidateQueries(['servers'])
         toast.success('Server registered successfully')
       },
       onError: (error) => {
         toast.error('Failed to register server')
       }
     })
   ```

4. **Global Error Handling:**
   - Axios interceptor for 401 (refresh token)
   - Axios interceptor for 403 (show permission error)
   - Network error handling
   - Display user-friendly errors

5. **Toast Notification System:**
   - Success toasts
   - Error toasts
   - Loading toasts
   - Use shadcn/ui toast component

**Acceptance Criteria:**
- [ ] All queries use TanStack Query
- [ ] Queries cache appropriately
- [ ] Errors display user-friendly messages
- [ ] Loading states work consistently
- [ ] Toast notifications work

**Claude Code Prompt:**
```
Set up data fetching and error handling for SARK UI.

Create:
1. TanStack Query configuration
2. Query hooks for all API endpoints (servers, policies, users, audit)
3. Mutation hooks with invalidation
4. Global error handling with Axios interceptors
5. Toast notification system

Ensure good UX with loading states and error messages.
```

---

### ✅ T5.2 - MCP Servers Management
**Week:** 5
**Duration:** 3 days
**Priority:** P1 (High - core feature)

**What you're building:**
The full server management experience.

**Deliverables:**
1. **Servers List Page** (`src/pages/Servers.tsx`):
   - Table/grid view toggle
   - Columns:
     - Name
     - Endpoint
     - Health status (green/yellow/red)
     - Sensitivity level
     - Last seen
     - Actions (view, edit, delete)
   - Search by name
   - Filter by status, sensitivity
   - Pagination
   - "Register Server" button

2. **Server Detail Page** (`src/pages/ServerDetail.tsx`):
   - Server metadata
   - Tabs:
     - **Tools** - List of tools with descriptions
     - **Resources** - Available resources
     - **Prompts** - MCP prompts
     - **Health History** - Status over time (chart)
     - **Activity** - Recent audit events for this server
   - Edit/Delete buttons
   - Health check button

3. **Register Server Form** (`src/pages/ServerRegister.tsx`):
   - Multi-step form or single form with sections:
     - **Step 1:** Basic Info (name, transport, endpoint)
     - **Step 2:** Capabilities and Tools
     - **Step 3:** Security (sensitivity level, managers)
     - **Step 4:** Review and Submit
   - JSON schema validation
   - Test connection button
   - Preview JSON
   - Success/error feedback

4. **Components:**
   - `ServerCard.tsx` - Card view of server
   - `ServerHealthBadge.tsx` - Health indicator
   - `ServerToolsList.tsx` - Tools table
   - `ServerHealthChart.tsx` - Health history chart

**Acceptance Criteria:**
- [ ] Can view all servers in list
- [ ] Can register new server
- [ ] Can view server details
- [ ] Can delete server (with confirmation)
- [ ] Form validation works
- [ ] Health status updates in real-time

**Claude Code Prompt:**
```
Build complete MCP server management for SARK UI.

Create:
1. Servers list page with search, filters, pagination
2. Server detail page with tabs (Tools, Resources, Health)
3. Register server form (multi-step) with validation
4. Delete server with confirmation

Use shadcn/ui components and TanStack Query for data fetching.
Make it intuitive and user-friendly.
```

---

### ✅ T5.4 - Audit Log Viewer
**Week:** 5
**Duration:** 2 days
**Priority:** P1 (High - compliance requirement)

**What you're building:**
Searchable audit log viewer for compliance.

**Deliverables:**
1. **Audit Logs Page** (`src/pages/AuditLogs.tsx`):
   - Table with columns:
     - Timestamp
     - User (name/email)
     - Action (tool:invoke, server:register, etc.)
     - Resource (which tool/server)
     - Decision (allow/deny)
     - IP Address
     - Details (expandable)
   - Pagination or infinite scroll
   - Export button

2. **Advanced Filters:**
   - Date range picker (last hour, today, week, month, custom)
   - Event type dropdown
   - User search
   - Decision filter (all, allow, deny)
   - Resource filter
   - Apply/Clear buttons

3. **Search:**
   - Full-text search across all fields
   - Search as you type
   - Debounced (500ms)

4. **Event Detail Modal:**
   - Full event data (JSON)
   - Formatted display
   - Copy to clipboard

5. **Export Functionality:**
   - Export to CSV
   - Export to JSON
   - Respect current filters
   - Show progress for large exports

**Acceptance Criteria:**
- [ ] Can view all audit events
- [ ] Filters work correctly
- [ ] Search is fast (<500ms)
- [ ] Can export results
- [ ] Pagination handles 100k+ events

**Claude Code Prompt:**
```
Build audit log viewer for SARK UI.

Create:
1. Audit logs page with table
2. Advanced filters (date range, event type, user, decision)
3. Search functionality
4. Event detail modal
5. Export to CSV/JSON

Use TanStack Table for performant table rendering.
Handle large datasets gracefully.
```

---

### ✅ T6.2 - Settings & API Key Management
**Week:** 6
**Duration:** 2 days
**Priority:** P1 (High)

**What you're building:**
Settings interface and API key management.

**Deliverables:**
1. **Settings Page** (`src/pages/Settings.tsx`):
   - Tabs:
     - General
     - Authentication
     - SIEM Integration
     - Notifications

2. **General Settings Tab:**
   - System name
   - Logo upload
   - Timezone
   - Date format

3. **Authentication Tab:**
   - OIDC provider config
   - LDAP settings
   - SAML config
   - Test connection buttons

4. **SIEM Integration Tab:**
   - Splunk configuration
   - Datadog configuration
   - Enable/disable toggle
   - Test connection

5. **API Keys Page** (`src/pages/APIKeys.tsx`):
   - List of API keys:
     - Name
     - Created date
     - Last used
     - Scopes
     - Actions (revoke)
   - "Create API Key" button

6. **Create API Key Modal:**
   - Name input
   - Scopes selection (checkboxes):
     - `server:read`, `server:write`
     - `policy:read`, `policy:write`
     - `audit:read`
   - Create button
   - Show key ONCE (with copy button)
   - Warning: "Save this key, you won't see it again"

**Acceptance Criteria:**
- [ ] Can view/update settings
- [ ] Can create API keys
- [ ] Can revoke keys
- [ ] Keys shown only once at creation
- [ ] Scopes are selectable

**Claude Code Prompt:**
```
Build settings and API key management for SARK UI.

Create:
1. Settings page with tabs (General, Auth, SIEM, Notifications)
2. Forms for each settings category
3. API Keys page with list and create modal
4. API key creation with scopes selection
5. Show key only once with copy button

Use forms with validation and proper state management.
```

---

## Your Timeline

| Week | Task | Duration | Focus |
|------|------|----------|-------|
| **1** | T1.2 | 1-2 days | MCP diagrams |
| **2** | T2.3 | 3 days | Interactive tutorials |
| **3** | T3.2 | 2 days | React project setup |
| **4** | T4.3 | 2 days | Authentication |
| **4** | T4.4 | 1-2 days | Data fetching |
| **5** | T5.2 | 3 days | Server management |
| **5** | T5.4 | 2 days | Audit logs |
| **6** | T6.2 | 2 days | Settings & API keys |

## Tips for Success

- **You're the integrator:** Bridge frontend and backend, help both teams
- **Pair with E1:** On complex UI components
- **Pair with E2:** On API integration issues
- **Test thoroughly:** You touch both sides, catch integration bugs
- **Ask questions:** If unclear, clarify before building

---

**You're the glue that holds it all together!** 🔧
