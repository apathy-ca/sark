# Engineer 3 (Full-Stack) - Updated Task Assignment

**Status:** FOUNDATION COMPLETE - NOW BUILD FEATURES
**Current Progress:** 3/8 tasks done (37.5%)
**Remaining Work:** 5 tasks over 12 days
**Branch:** `claude/engineer-3-tasks-0144kGrj1Y3LYz2JcCt13RrA`

---

## ✅ What You've Already Completed

**Weeks 1-3: EXCELLENT WORK!**

- ✅ Week 1: MCP diagrams and code examples
- ✅ Week 2: Tutorials, LDAP users, Docker profiles
- ✅ Week 3: **Complete React foundation** 🎉
  - React 19 + TypeScript + Vite configured
  - Tailwind CSS 4.1.17 + shadcn/ui integrated
  - React Router 7.9.6 set up
  - TanStack Query 5.90.11 + Zustand 5.0.8 + Axios installed
  - Complete API client (`frontend/src/services/api.ts`, 456 lines)
  - Full TypeScript types (`frontend/src/types/api.ts`, 392 lines)
  - Build system working

**Your foundation is solid!** Now it's time to build the actual UI features.

---

## 🎯 Your Mission: Build the UI (Days 1-12)

You need to build 3 main areas:
1. **Authentication & Dashboard** (Week 4)
2. **Server Management & Audit Viewer** (Week 5)
3. **Settings & API Keys** (Week 6)

This will unblock Engineer 4 (DevOps) and Documenter.

---

## 📅 Week 4: Authentication & Dashboard (Days 1-5)

### Day 1-2: Authentication UI

**Goal:** Users can log in and access protected pages.

**Files to create:**

#### 1. Auth Store (`frontend/src/stores/authStore.ts`)

```typescript
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { authApi, setTokens, clearTokens, getAccessToken } from '@/services/api'
import type { User } from '@/types/api'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  checkAuth: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (username: string, password: string) => {
        set({ isLoading: true, error: null })
        try {
          const response = await authApi.loginLdap({ username, password })
          set({
            user: response.user,
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (error: any) {
          set({
            error: error.response?.data?.message || 'Login failed',
            isLoading: false,
          })
          throw error
        }
      },

      logout: async () => {
        try {
          const refreshToken = localStorage.getItem('refresh_token')
          if (refreshToken) {
            await authApi.logout({ refresh_token: refreshToken })
          }
        } catch (error) {
          // Ignore logout errors
        } finally {
          clearTokens()
          set({ user: null, isAuthenticated: false })
        }
      },

      checkAuth: async () => {
        const token = getAccessToken()
        if (!token) {
          set({ isAuthenticated: false, user: null })
          return
        }

        try {
          const user = await authApi.getCurrentUser()
          set({ user, isAuthenticated: true })
        } catch (error) {
          clearTokens()
          set({ user: null, isAuthenticated: false })
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ user: state.user }),
    }
  )
)
```

#### 2. Login Page (`frontend/src/pages/LoginPage.tsx`)

```typescript
import { useState, FormEvent } from 'react'
import { useNavigate, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

export function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const { login, isLoading, error, isAuthenticated } = useAuthStore()
  const navigate = useNavigate()

  // If already authenticated, redirect to dashboard
  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    try {
      await login(username, password)
      navigate('/')
    } catch (error) {
      // Error is handled in store
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="max-w-md w-full space-y-8 p-10 bg-white rounded-xl shadow-2xl">
        <div className="text-center">
          <h2 className="text-4xl font-bold text-gray-900">SARK</h2>
          <p className="mt-2 text-sm text-gray-600">
            Security Audit and Resource Kontroler
          </p>
          <p className="mt-4 text-lg text-gray-700">Sign in to your account</p>
        </div>

        <form className="space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              <p className="text-sm font-medium">{error}</p>
            </div>
          )}

          <div>
            <label
              htmlFor="username"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Username
            </label>
            <input
              id="username"
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
              placeholder="Enter your username"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
              placeholder="Enter your password"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-3 px-4 border border-transparent rounded-lg shadow-sm text-base font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {isLoading ? (
              <span className="flex items-center justify-center">
                <svg
                  className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Signing in...
              </span>
            ) : (
              'Sign in'
            )}
          </button>
        </form>

        <div className="text-center text-sm text-gray-500">
          <p>Use your LDAP credentials to log in</p>
        </div>
      </div>
    </div>
  )
}
```

#### 3. Protected Route Component (`frontend/src/components/ProtectedRoute.tsx`)

```typescript
import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { LoadingSpinner } from './LoadingSpinner'

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuthStore()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
```

#### 4. Loading Spinner Component (`frontend/src/components/LoadingSpinner.tsx`)

```typescript
interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
}

export function LoadingSpinner({ size = 'md' }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'w-4 h-4 border-2',
    md: 'w-8 h-8 border-4',
    lg: 'w-12 h-12 border-4',
  }

  return (
    <div className="flex justify-center items-center">
      <div
        className={`${sizeClasses[size]} border-blue-200 border-t-blue-600 rounded-full animate-spin`}
      />
    </div>
  )
}
```

#### 5. Update App.tsx with Routes

```typescript
import { useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { LoginPage } from '@/pages/LoginPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { useAuthStore } from '@/stores/authStore'

function App() {
  const checkAuth = useAuthStore((state) => state.checkAuth)

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<DashboardPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
```

**Test it:**
```bash
cd frontend
npm run dev
# Visit http://localhost:3000
# Should redirect to /login
# Try logging in with LDAP credentials
```

**Commit:**
```bash
git add frontend/src/stores/ frontend/src/pages/LoginPage.tsx \
        frontend/src/components/ProtectedRoute.tsx \
        frontend/src/components/LoadingSpinner.tsx \
        frontend/src/App.tsx
git commit -m "feat(ui): implement authentication UI and protected routes

- Add Zustand auth store with login/logout
- Create login page with form validation
- Implement protected route component
- Add loading spinner component
- Set up React Router with auth flow

Part of Week 4 (T4.3)"
git push
```

---

### Day 3-4: Data Fetching & Error Handling

**Goal:** Reusable hooks for API data with loading/error states.

**Files to create:**

#### 1. Query Client Setup (`frontend/src/lib/queryClient.ts`)

```typescript
import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      refetchOnWindowFocus: false,
      retry: (failureCount, error: any) => {
        // Don't retry on auth errors
        if (error?.response?.status === 401 || error?.response?.status === 403) {
          return false
        }
        return failureCount < 3
      },
    },
  },
})
```

#### 2. Server Hooks (`frontend/src/hooks/useServers.ts`)

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { serversApi } from '@/services/api'
import type {
  ServerListParams,
  ServerRegistrationRequest,
} from '@/types/api'

export function useServers(params?: ServerListParams) {
  return useQuery({
    queryKey: ['servers', params],
    queryFn: () => serversApi.list(params),
  })
}

export function useServer(serverId: string) {
  return useQuery({
    queryKey: ['servers', serverId],
    queryFn: () => serversApi.get(serverId),
    enabled: !!serverId,
  })
}

export function useCreateServer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: serversApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['servers'] })
    },
  })
}

export function useUpdateServer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      serverId,
      data,
    }: {
      serverId: string
      data: ServerRegistrationRequest
    }) => serversApi.update(serverId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['servers'] })
      queryClient.invalidateQueries({
        queryKey: ['servers', variables.serverId],
      })
    },
  })
}

export function useDeleteServer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: serversApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['servers'] })
    },
  })
}
```

#### 3. Error Boundary (`frontend/src/components/ErrorBoundary.tsx`)

```typescript
import { Component, ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="text-center p-8 bg-white rounded-lg shadow-lg max-w-md">
              <div className="text-6xl mb-4">⚠️</div>
              <h1 className="text-2xl font-bold text-red-600 mb-2">
                Something went wrong
              </h1>
              <p className="text-gray-600 mb-4">{this.state.error?.message}</p>
              <button
                onClick={() => window.location.reload()}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
              >
                Reload Page
              </button>
            </div>
          </div>
        )
      )
    }

    return this.props.children
  }
}
```

#### 4. Update Main.tsx with Providers

```typescript
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from '@/lib/queryClient'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import App from './App'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </ErrorBoundary>
  </StrictMode>
)
```

**Commit:**
```bash
git add frontend/src/lib/ frontend/src/hooks/ \
        frontend/src/components/ErrorBoundary.tsx \
        frontend/src/main.tsx
git commit -m "feat(ui): implement data fetching and error handling

- Set up TanStack Query with retry logic
- Create useServers hooks (list, get, create, update, delete)
- Add error boundary for graceful error handling
- Wrap app with QueryClientProvider

Part of Week 4 (T4.4)"
git push
```

---

### Day 5: Dashboard Page

**Goal:** Show server statistics and recent activity.

**File to create:**

#### Dashboard Page (`frontend/src/pages/DashboardPage.tsx`)

```typescript
import { useServers } from '@/hooks/useServers'
import { useAuthStore } from '@/stores/authStore'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { useNavigate } from 'react-router-dom'

export function DashboardPage() {
  const { data, isLoading, error } = useServers({ limit: 10 })
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600">Error loading dashboard</p>
          <p className="text-sm text-gray-500">{(error as any).message}</p>
        </div>
      </div>
    )
  }

  const activeServers = data?.items.filter((s) => s.status === 'active') || []
  const totalTools =
    data?.items.reduce((acc, s) => acc + (s.tools?.length || 0), 0) || 0

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">SARK Dashboard</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">
              Welcome, {user?.username}
            </span>
            <button
              onClick={handleLogout}
              className="px-4 py-2 text-sm text-gray-700 hover:text-gray-900 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide">
              Total Servers
            </h2>
            <p className="text-4xl font-bold text-gray-900 mt-2">
              {data?.total || 0}
            </p>
            <p className="text-sm text-gray-500 mt-1">Registered MCP servers</p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide">
              Active Servers
            </h2>
            <p className="text-4xl font-bold text-green-600 mt-2">
              {activeServers.length}
            </p>
            <p className="text-sm text-gray-500 mt-1">Currently online</p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide">
              Total Tools
            </h2>
            <p className="text-4xl font-bold text-blue-600 mt-2">{totalTools}</p>
            <p className="text-sm text-gray-500 mt-1">Available MCP tools</p>
          </div>
        </div>

        {/* Recent Servers */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">
              Recent Servers
            </h2>
          </div>
          <div className="divide-y divide-gray-200">
            {data?.items.slice(0, 5).map((server) => (
              <div
                key={server.id}
                className="px-6 py-4 flex justify-between items-center hover:bg-gray-50 transition"
              >
                <div>
                  <h3 className="text-base font-medium text-gray-900">
                    {server.name}
                  </h3>
                  <p className="text-sm text-gray-500">{server.description}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    {server.tools?.length || 0} tools available
                  </p>
                </div>
                <span
                  className={`px-3 py-1 rounded-full text-sm font-medium ${
                    server.status === 'active'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {server.status}
                </span>
              </div>
            ))}

            {data?.items.length === 0 && (
              <div className="px-6 py-12 text-center text-gray-500">
                <p>No servers registered yet</p>
                <p className="text-sm mt-1">
                  Register your first MCP server to get started
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
```

**Test it:**
```bash
# Make sure backend is running
cd frontend
npm run dev

# Should be able to:
# 1. Log in
# 2. See dashboard with real data
# 3. Logout button works
```

**Commit:**
```bash
git add frontend/src/pages/DashboardPage.tsx
git commit -m "feat(ui): add dashboard page with server statistics

- Display total servers, active servers, and tool count
- Show recent servers list with status badges
- Add logout button in header
- Use useServers hook with loading/error states
- Responsive grid layout

Week 4 complete! 🎉"
git push
```

---

## ✅ End of Week 4 Checklist

- [ ] Users can log in with LDAP
- [ ] Login page has proper error handling
- [ ] Dashboard displays real server data
- [ ] Loading states work
- [ ] Error boundary catches errors
- [ ] Logout works
- [ ] `npm run build` succeeds

**Once Week 4 is done, you've unblocked Engineer 4!** 🚀

---

## 📅 Week 5: Server Management & Audit Viewer (Days 6-10)

*Full details in the main status document at `docs/ALL_WORKERS_STATUS_AND_PLANS.md`*

**Summary:**
- Days 6-8: Server management UI (list, detail, create, edit, delete)
- Days 9-10: Audit log viewer (list, filters, export)

---

## 📅 Week 6: Settings & API Keys (Days 11-12)

*Full details in the main status document*

**Summary:**
- Days 11-12: Settings page with API key management

---

## 🎯 Your Impact

**When you complete Week 4 (Day 5):**
- ✅ Engineer 4 can start Docker integration
- ✅ UI has authentication and dashboard
- ✅ Foundation for all future features

**When you complete Week 5 (Day 10):**
- ✅ Core features working (servers, audit logs)
- ✅ Engineer 4 can complete Docker work
- ✅ Documenter can start UI docs

**When you complete Week 6 (Day 12):**
- ✅ All UI features complete
- ✅ Project ready for testing and deployment
- ✅ Team can finalize everything

---

## 🚨 Need Help?

1. **API questions?** Check `docs/API_REFERENCE.md` (Engineer 2's work)
2. **Auth flow?** Your own `frontend/src/services/api.ts` has token refresh
3. **Build issues?** Your Vite config should be good
4. **Styling?** Tailwind is configured with shadcn/ui theme

---

## 📞 Daily Check-in

**Share progress in #sark-improvements-ui:**

```
Day X update:
- ✅ Completed: [what you finished]
- 🚧 In progress: [what you're working on]
- 🔴 Blockers: [any issues]
- 📅 Tomorrow: [what's next]
```

---

**You've built an excellent foundation. Now bring it to life! 🚀**

**Estimated completion:** 12 days from now
**Next milestone:** Week 4 complete (Day 5)
**Team depends on you:** Engineer 4 and Documenter are waiting

**Let's ship this UI! 💪**
