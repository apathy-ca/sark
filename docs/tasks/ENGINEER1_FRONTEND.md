# Engineer 1 (Frontend Specialist) Tasks

**Your Role:** Frontend/UI Development Lead
**Total Tasks:** 8 tasks over 8 weeks
**Estimated Effort:** ~17 days

You're responsible for the user interface - making SARK accessible and beautiful.

---

## Your Tasks

### ✅ T3.1 - UI Architecture & Technology Selection
**Week:** 3
**Duration:** 2-3 days
**Priority:** P0 (Critical - blocks all UI work)

**What you're building:**
The foundation and design for the entire UI.

**Deliverables:**
1. **Technology Selection Document:**
   - Recommended stack with rationale
   - Comparison matrix (React vs Vue vs Svelte)
   - Final decision: React 18 + TypeScript + Vite (recommended)
   - UI library: shadcn/ui + Tailwind CSS
   - State: TanStack Query + Zustand
   - Testing: Vitest + Playwright

2. **Complete Wireframes for all pages:**
   - Dashboard (metrics overview)
   - MCP Servers (list, detail, register form)
   - Policies (list, editor, testing playground)
   - Users & Teams (list, detail, roles)
   - Audit Logs (searchable table)
   - Settings (tabs for different configs)

   Tool: Figma, Excalidraw, or even hand-drawn → photographed

3. **UI Component Catalog:**
   - List all needed components
   - Component hierarchy
   - Reusable vs page-specific

4. **Design System:**
   - Color palette (light + dark mode)
   - Typography scale
   - Spacing system
   - Border radius, shadows
   - Animation guidelines

**Acceptance Criteria:**
- [ ] Team consensus on React stack
- [ ] Wireframes approved by stakeholders
- [ ] Design system documented
- [ ] Component catalog complete

**Claude Code Prompt:**
```
Create UI architecture and design system for SARK.

Tasks:
1. Document technology stack recommendation (React + TypeScript)
2. Create wireframes for 6 main pages (can be text-based Mermaid diagrams)
3. Define design system (colors, typography, spacing)
4. Create component catalog

Save as docs/UI_ARCHITECTURE.md
```

---

### ✅ T4.1 - Layout & Navigation System
**Week:** 4
**Duration:** 2-3 days
**Priority:** P0 (Critical - foundation for all pages)

**What you're building:**
The shell that every page will live inside.

**Deliverables:**
1. **App Shell** (`src/components/layout/AppLayout.tsx`):
   - Header with logo, user menu
   - Sidebar with navigation
   - Main content area
   - Footer (optional)

2. **Navigation Menu** (`src/components/layout/Sidebar.tsx`):
   - Routes:
     - 🏠 Dashboard (`/`)
     - 🖥️ Servers (`/servers`)
     - 📜 Policies (`/policies`)
     - 👥 Users (`/users`)
     - 📊 Audit Logs (`/audit`)
     - ⚙️ Settings (`/settings`)
   - Active state highlighting
   - Icons for each route

3. **Header** (`src/components/layout/Header.tsx`):
   - SARK logo
   - Page title
   - User menu (profile, logout)
   - Notifications icon (optional)

4. **Responsive Layout:**
   - Desktop: Fixed sidebar
   - Tablet: Collapsible sidebar
   - Mobile: Drawer sidebar

5. **Error Boundaries:**
   - Catch rendering errors
   - Show user-friendly error page

**Acceptance Criteria:**
- [ ] Navigation works between all routes
- [ ] Mobile-friendly sidebar (drawer)
- [ ] User context displayed in header
- [ ] Active route highlighted
- [ ] Logout redirects correctly

**Dependencies:**
- T3.2 (Engineer 3 must set up React project first)

**Claude Code Prompt:**
```
Create the app layout and navigation for SARK UI.

Build:
1. AppLayout component with header, sidebar, main content
2. Sidebar with navigation to all main routes
3. Header with user menu and logout
4. Make it responsive (mobile drawer sidebar)
5. Add error boundaries

Use shadcn/ui components and Tailwind CSS.
```

---

### ✅ T4.2 - Base Component Library
**Week:** 4
**Duration:** 2 days
**Priority:** P1 (High - needed for all features)

**What you're building:**
Reusable UI components that the whole app will use.

**Deliverables:**
1. **Install shadcn/ui components:**
   ```bash
   npx shadcn-ui@latest add button input select checkbox radio
   npx shadcn-ui@latest add card table tabs dialog sheet toast
   npx shadcn-ui@latest add dropdown-menu avatar badge separator
   ```

2. **Create custom components** (`src/components/ui/`):
   - `LoadingSpinner.tsx` - Animated spinner
   - `EmptyState.tsx` - For empty lists/tables
   - `ErrorAlert.tsx` - Error message display
   - `ConfirmDialog.tsx` - Confirmation modal
   - `PageHeader.tsx` - Consistent page headers

3. **Form Components** (`src/components/forms/`):
   - Integrate React Hook Form
   - Create `FormField` wrapper
   - Create `FormError` component
   - Example form validation with Zod

4. **Documentation:**
   - Component usage examples
   - Props documentation
   - Storybook (optional but nice)

**Acceptance Criteria:**
- [ ] All shadcn/ui components installed
- [ ] Custom components created
- [ ] Forms work with React Hook Form
- [ ] Dark mode supported
- [ ] TypeScript types for all props

**Claude Code Prompt:**
```
Build the base component library for SARK UI.

Tasks:
1. Install shadcn/ui components (button, input, card, table, dialog, toast, etc.)
2. Create custom components (LoadingSpinner, EmptyState, ErrorAlert, ConfirmDialog)
3. Set up React Hook Form integration
4. Ensure dark mode works for all components
5. Add TypeScript types

Use Tailwind CSS and shadcn/ui patterns.
```

---

### ✅ T5.1 - Dashboard Page
**Week:** 5
**Duration:** 2 days
**Priority:** P1 (High - first page users see)

**What you're building:**
The home page with system overview and metrics.

**Deliverables:**
1. **Dashboard Layout** (`src/pages/Dashboard.tsx`):
   - 4 metric cards at top:
     - Total MCP Servers
     - Active Servers
     - Policy Decisions (today)
     - Recent Audit Events
   - Charts section:
     - Policy decisions over time (line chart)
     - Server health distribution (pie chart)
   - Recent activity feed
   - Quick actions section

2. **Components:**
   - `MetricCard.tsx` - Displays a single metric
   - `PolicyDecisionChart.tsx` - Line chart with Recharts
   - `ServerHealthChart.tsx` - Pie chart
   - `ActivityFeed.tsx` - List of recent events

3. **Data Fetching:**
   - Use TanStack Query hooks
   - Real-time updates (polling or WebSocket)
   - Loading states
   - Error handling

**Acceptance Criteria:**
- [ ] Metrics display correctly
- [ ] Charts render and update
- [ ] Activity feed shows recent events
- [ ] Quick actions work
- [ ] Mobile responsive
- [ ] Loads in <500ms

**Dependencies:**
- T4.4 (Engineer 3 must set up data fetching)
- API endpoints for metrics

**Claude Code Prompt:**
```
Build the SARK dashboard page.

Create:
1. Dashboard layout with 4 metric cards (servers, policies, events)
2. Charts for policy decisions and server health (use Recharts)
3. Recent activity feed
4. Quick actions section

Use TanStack Query for data fetching.
Make it responsive and performant.
```

---

### ✅ T5.3 - Policy Viewer & User Management
**Week:** 5
**Duration:** 2 days
**Priority:** P1 (High)

**What you're building:**
Pages to view policies and manage users.

**Deliverables:**
1. **Policy List Page** (`src/pages/Policies.tsx`):
   - Table of policies with columns:
     - Name
     - Type (RBAC, team-based, etc.)
     - Environment (dev/staging/prod)
     - Last updated
     - Actions
   - Filter by type and environment
   - Search by name
   - Click to view details

2. **Policy Detail Modal:**
   - Policy metadata
   - Policy content (read-only, syntax highlighted)
   - Test policy button → leads to editor
   - Edit/Delete actions

3. **User List Page** (`src/pages/Users.tsx`):
   - Table of users:
     - Name
     - Email
     - Role badges
     - Teams
     - Status (active/inactive)
   - Search and filter
   - Click for user details

4. **User Detail Modal:**
   - User info
   - Roles and permissions
   - Team memberships
   - Recent activity

**Acceptance Criteria:**
- [ ] Can view all policies
- [ ] Can filter and search policies
- [ ] Policy content displays with syntax highlighting
- [ ] Can view all users
- [ ] Can see user details

**Claude Code Prompt:**
```
Build policy viewer and user management pages for SARK.

Create:
1. Policy list page with table, filters, search
2. Policy detail modal with syntax highlighting
3. User list page with table, filters
4. User detail modal showing roles and teams

Use shadcn/ui Table component and TanStack Query for data.
```

---

### ✅ T6.1 - Policy Editor with Monaco
**Week:** 6
**Duration:** 3 days
**Priority:** P1 (High - key feature)

**What you're building:**
A full-featured policy editor so users can write and test policies in the UI.

**Deliverables:**
1. **Install Monaco Editor:**
   ```bash
   npm install @monaco-editor/react
   ```

2. **Policy Editor Page** (`src/pages/PolicyEditor.tsx`):
   - File tree sidebar (list of policies)
   - Monaco editor pane:
     - Rego syntax highlighting
     - Line numbers
     - Syntax validation
     - Auto-complete (if possible)
   - Toolbar:
     - Save button
     - Cancel/Revert
     - Format code
     - Dark mode toggle for editor

3. **Policy Testing Panel** (bottom or side):
   - Input JSON editor (test input)
   - "Test Policy" button
   - Results display:
     - Allow/Deny decision
     - Reasons
     - Execution time
   - Pass/fail indicator

4. **Policy Template Library:**
   - Common policy templates
   - Insert template button

**Acceptance Criteria:**
- [ ] Monaco editor loads smoothly
- [ ] Rego syntax highlighted correctly
- [ ] Can save policy changes
- [ ] Can test policies inline
- [ ] Test results display clearly
- [ ] Performance: no lag when typing

**Dependencies:**
- API endpoint for testing policies

**Claude Code Prompt:**
```
Build a policy editor with Monaco for SARK.

Create:
1. Integrate Monaco editor with Rego syntax highlighting
2. Policy editor page with file tree and editor
3. Save/cancel/format toolbar
4. Policy testing panel with input/output
5. Display test results clearly

Use @monaco-editor/react library.
Ensure smooth performance even with large policies.
```

---

### ✅ T7.1 - Responsive Design & Dark Mode
**Week:** 7
**Duration:** 2 days
**Priority:** P1 (High - UX critical)

**What you're building:**
Making the UI work beautifully on all devices and in dark mode.

**Deliverables:**
1. **Mobile Optimization:**
   - Test all pages at 375px (mobile)
   - Adjust layouts for mobile:
     - Stack cards vertically
     - Simplify tables (hide less important columns)
     - Make forms single column
     - Touch-friendly buttons (min 44px)
   - Mobile navigation (drawer)

2. **Tablet Optimization:**
   - Test at 768px and 1024px
   - Optimize sidebar behavior
   - Adjust grid layouts

3. **Dark Mode:**
   - Implement theme toggle (sun/moon icon)
   - Dark mode colors for all components
   - Save preference in localStorage
   - Respect system preference

4. **Theme Toggle:**
   - In user menu
   - Smooth transition between themes
   - Persist across sessions

**Acceptance Criteria:**
- [ ] All pages work on mobile (375px+)
- [ ] Tablet layout optimized (768px+)
- [ ] Dark mode looks polished
- [ ] Theme persists across sessions
- [ ] No horizontal scroll on mobile

**Claude Code Prompt:**
```
Make SARK UI fully responsive and add dark mode.

Tasks:
1. Optimize all pages for mobile (375px+) and tablet (768px+)
2. Implement dark mode with theme toggle
3. Save theme preference in localStorage
4. Ensure smooth theme transitions
5. Test on different screen sizes

Use Tailwind CSS responsive utilities and dark: variants.
```

---

### ✅ T7.2 - Accessibility & UX Polish
**Week:** 7
**Duration:** 2-3 days
**Priority:** P0 (Critical - must be accessible)

**What you're building:**
Making SARK UI accessible to everyone and delightful to use.

**Deliverables:**
1. **WCAG 2.1 AA Compliance:**
   - Keyboard navigation:
     - All interactive elements reachable via Tab
     - Escape closes modals
     - Enter submits forms
   - ARIA labels:
     - Add to all icons and icon-only buttons
     - Proper roles for complex components
   - Focus indicators:
     - Visible focus rings
     - Logical tab order
   - Color contrast:
     - Minimum 4.5:1 for text
     - 3:1 for UI components

2. **Keyboard Shortcuts:**
   - Create shortcuts modal (press `?` to show)
   - Common shortcuts:
     - `/` - Focus search
     - `g d` - Go to dashboard
     - `g s` - Go to servers
     - `g p` - Go to policies
     - `?` - Show shortcuts

3. **UX Improvements:**
   - Helpful error messages (not "Error 500")
   - Contextual tooltips
   - Loading skeletons (better than spinners)
   - Empty states with actions
   - Confirmation dialogs for destructive actions
   - Success toasts for actions

4. **Micro-interactions:**
   - Smooth transitions
   - Button hover effects
   - Loading animations
   - Celebrate successful actions

**Acceptance Criteria:**
- [ ] Passes axe accessibility audit (0 violations)
- [ ] Keyboard-only navigation works
- [ ] Screen reader compatible (test with NVDA/JAWS)
- [ ] Lighthouse accessibility score >90
- [ ] All colors meet contrast requirements

**Claude Code Prompt:**
```
Make SARK UI accessible (WCAG 2.1 AA) and polished.

Tasks:
1. Add keyboard navigation to all features
2. Add ARIA labels and proper focus management
3. Implement keyboard shortcuts with help modal
4. Improve error messages and add tooltips
5. Add loading skeletons and empty states
6. Run accessibility audit and fix all issues

Test with keyboard-only navigation and screen reader.
```

---

## Your Timeline

| Week | Task | Duration | Focus |
|------|------|----------|-------|
| **3** | T3.1 | 2-3 days | Design & architecture |
| **4** | T4.1 | 2-3 days | Layout & navigation |
| **4** | T4.2 | 2 days | Component library |
| **5** | T5.1 | 2 days | Dashboard |
| **5** | T5.3 | 2 days | Policies & users |
| **6** | T6.1 | 3 days | Policy editor |
| **7** | T7.1 | 2 days | Responsive & dark mode |
| **7** | T7.2 | 2-3 days | Accessibility & polish |

## Your Tech Stack

```
Frontend Framework: React 18 + TypeScript
Build Tool: Vite
UI Components: shadcn/ui + Tailwind CSS
State Management: TanStack Query + Zustand
Forms: React Hook Form + Zod
Editor: Monaco Editor (@monaco-editor/react)
Charts: Recharts
Tables: TanStack Table
Testing: Vitest + React Testing Library + Playwright
```

## Getting Started

1. **Week 3:** Make design decisions, create wireframes
2. **Week 4:** Build the foundation (layout, components)
3. **Week 5-6:** Build features (pages, editor)
4. **Week 7:** Polish and perfect

## Tips for Success

- **Use shadcn/ui:** Don't build from scratch, use the component library
- **TypeScript:** Type everything - it saves time later
- **Mobile first:** Design for mobile, scale up to desktop
- **Test early:** Don't wait until Week 7 for accessibility
- **Ask for help:** Engineer 3 can pair on complex components

---

**You're building the face of SARK - make it beautiful!** 🎨
