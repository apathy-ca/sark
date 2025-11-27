# Engineer 3 - Immediate Task Assignment
## UI Foundation Development (Next 5 Days)

**Branch:** Create new branch from main
**Status:** APPROVED TO START IMMEDIATELY
**Timeline:** 5 days (Days 1-5)
**Coordination:** Will unblock Engineer 4 on Day 3

---

## Decisions Confirmed ✅

- ✅ React 18 + TypeScript
- ✅ Vite (build tool)
- ✅ shadcn/ui + Tailwind CSS
- ✅ TanStack Query (data fetching)
- ✅ Zustand (state management)
- ✅ React Router (routing)

---

## Task 1: T3.2 - React Project Scaffold (Days 1-2)

**Priority:** P0 (CRITICAL - Blocks Engineer 4)
**Duration:** 2 days
**Branch:** `engineer-3/ui-scaffold`

### Deliverables

**1. Create UI Directory Structure**
```bash
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
├── components.json
└── README.md
```

**2. Initialize Project**
```bash
# Navigate to project root
cd /home/user/sark

# Create UI directory
mkdir ui
cd ui

# Initialize Vite project with React + TypeScript
npm create vite@latest . -- --template react-ts

# Install dependencies
npm install

# Install Tailwind CSS
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Install shadcn/ui
npx shadcn-ui@latest init

# Install routing
npm install react-router-dom
npm install -D @types/react-router-dom

# Install state management
npm install @tanstack/react-query zustand

# Install forms
npm install react-hook-form zod @hookform/resolvers

# Install API client generation
npm install axios
npm install -D @hey-api/openapi-ts

# Install dev tools
npm install -D @types/node
```

**3. Configure Vite (`vite.config.ts`)**
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

**4. Configure TypeScript (`tsconfig.json`)**
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

**5. Configure Tailwind (`tailwind.config.js`)**
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [require("tailwindcss-animate")],
}
```

**6. Set Up React Router (`src/App.tsx`)**
```typescript
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Create query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<div>SARK UI - Coming Soon</div>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
```

**7. Create Project README (`ui/README.md`)**
```markdown
# SARK UI

React-based web interface for SARK MCP Governance.

## Tech Stack

- React 18 + TypeScript
- Vite (build tool)
- shadcn/ui + Tailwind CSS
- TanStack Query (data fetching)
- Zustand (state management)
- React Router (routing)

## Development

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

- `src/components/ui/` - shadcn/ui components
- `src/components/layout/` - Layout components (Header, Sidebar, etc.)
- `src/components/features/` - Feature-specific components
- `src/pages/` - Page components
- `src/api/` - API client (auto-generated from OpenAPI)
- `src/stores/` - Zustand stores
- `src/hooks/` - Custom React hooks
- `src/lib/` - Utility functions
- `src/types/` - TypeScript type definitions
```

### Acceptance Criteria

- [ ] `npm run dev` starts dev server at http://localhost:3000
- [ ] Hot reload works
- [ ] TypeScript compiles with no errors
- [ ] Tailwind CSS working
- [ ] Path aliases work (`@/components`, etc.)
- [ ] Basic routing works
- [ ] README documents setup

### Notify Engineer 4 When Complete

Once T3.2 is done, Engineer 4 can start W4-E4-01 (Vite config) immediately.

---

## Task 2: T4.3 - Authentication UI (Days 3-4)

**Priority:** P0 (CRITICAL)
**Duration:** 2 days
**Branch:** Same (`engineer-3/ui-scaffold`)

### Deliverables

**1. Auth Store (`src/stores/authStore.ts`)**
```typescript
import { create } from 'zustand'

interface User {
  id: string
  email: string
  name: string
  roles: string[]
}

interface AuthStore {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  login: (code: string) => Promise<void>
  logout: () => void
  refreshToken: () => Promise<void>
  setUser: (user: User) => void
  setToken: (token: string) => void
}

export const useAuthStore = create<AuthStore>((set, get) => ({
  user: null,
  token: localStorage.getItem('token'),
  isAuthenticated: !!localStorage.getItem('token'),

  login: async (code: string) => {
    // OIDC login flow
    try {
      const response = await fetch('/api/v1/auth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code }),
      })
      const data = await response.json()

      set({
        token: data.access_token,
        user: data.user,
        isAuthenticated: true,
      })

      localStorage.setItem('token', data.access_token)
    } catch (error) {
      console.error('Login failed:', error)
      throw error
    }
  },

  logout: () => {
    localStorage.removeItem('token')
    set({ user: null, token: null, isAuthenticated: false })
  },

  refreshToken: async () => {
    const token = get().token
    if (!token) return

    try {
      const response = await fetch('/api/v1/auth/refresh', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })
      const data = await response.json()

      set({ token: data.access_token })
      localStorage.setItem('token', data.access_token)
    } catch (error) {
      console.error('Token refresh failed:', error)
      get().logout()
    }
  },

  setUser: (user: User) => set({ user }),
  setToken: (token: string) => {
    set({ token, isAuthenticated: true })
    localStorage.setItem('token', token)
  },
}))
```

**2. Login Page (`src/pages/Login.tsx`)**
```typescript
import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { Button } from '@/components/ui/button'

export function Login() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { login, isAuthenticated } = useAuthStore()

  useEffect(() => {
    // Handle OAuth callback
    const code = searchParams.get('code')
    if (code) {
      login(code).then(() => {
        navigate('/dashboard')
      }).catch((error) => {
        console.error('Login failed:', error)
      })
    }
  }, [searchParams])

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard')
    }
  }, [isAuthenticated])

  const handleLogin = () => {
    // Redirect to OIDC provider
    const clientId = import.meta.env.VITE_OIDC_CLIENT_ID
    const redirectUri = `${window.location.origin}/login`
    const authUrl = `${import.meta.env.VITE_OIDC_ISSUER}/authorize?client_id=${clientId}&redirect_uri=${redirectUri}&response_type=code&scope=openid profile email`

    window.location.href = authUrl
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-md space-y-8 p-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold">SARK</h1>
          <p className="mt-2 text-gray-600">MCP Governance Platform</p>
        </div>

        <Button
          onClick={handleLogin}
          className="w-full"
          size="lg"
        >
          Sign in with OIDC
        </Button>
      </div>
    </div>
  )
}
```

**3. Protected Route Component (`src/components/ProtectedRoute.tsx`)**
```typescript
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated } = useAuthStore()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}
```

**4. Update App.tsx with Auth Routes**
```typescript
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Login } from '@/pages/Login'
import { ProtectedRoute } from '@/components/ProtectedRoute'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <div>Dashboard - Coming Soon</div>
              </ProtectedRoute>
            }
          />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
```

**5. Environment Variables (`.env.example`)**
```
VITE_API_URL=http://localhost:8000
VITE_OIDC_ISSUER=https://your-idp.com
VITE_OIDC_CLIENT_ID=your-client-id
```

### Acceptance Criteria

- [ ] Login page displays
- [ ] OIDC redirect works
- [ ] Token stored in localStorage
- [ ] Protected routes redirect to login
- [ ] Authenticated users access dashboard
- [ ] Logout clears state

---

## Task 3: T4.4 - Data Fetching & Error Handling (Day 5)

**Priority:** P1 (High)
**Duration:** 1 day
**Branch:** Same (`engineer-3/ui-scaffold`)

### Deliverables

**1. Axios Instance (`src/lib/axios.ts`)**
```typescript
import axios from 'axios'
import { useAuthStore } from '@/stores/authStore'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor - add auth token
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor - handle errors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // Handle 401 - token expired
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        await useAuthStore.getState().refreshToken()
        const token = useAuthStore.getState().token
        originalRequest.headers.Authorization = `Bearer ${token}`
        return api(originalRequest)
      } catch (refreshError) {
        useAuthStore.getState().logout()
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)
```

**2. API Hooks (`src/api/hooks.ts`)**
```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/axios'

// Servers
export const useServers = () =>
  useQuery({
    queryKey: ['servers'],
    queryFn: async () => {
      const { data } = await api.get('/api/v1/servers')
      return data
    },
  })

export const useServer = (id: string) =>
  useQuery({
    queryKey: ['server', id],
    queryFn: async () => {
      const { data } = await api.get(`/api/v1/servers/${id}`)
      return data
    },
    enabled: !!id,
  })

export const useCreateServer = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (serverData: any) => {
      const { data } = await api.post('/api/v1/servers', serverData)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['servers'] })
    },
  })
}

// Policies
export const usePolicies = () =>
  useQuery({
    queryKey: ['policies'],
    queryFn: async () => {
      const { data } = await api.get('/api/v1/policies')
      return data
    },
  })

// Audit Logs
export const useAuditLogs = (filters?: any) =>
  useQuery({
    queryKey: ['audit', filters],
    queryFn: async () => {
      const { data } = await api.get('/api/v1/audit/events', { params: filters })
      return data
    },
  })
```

**3. Toast Notifications (`src/components/ui/toast.tsx`)**
```bash
# Install shadcn toast component
npx shadcn-ui@latest add toast
```

**4. Global Error Handler (`src/lib/errorHandler.ts`)**
```typescript
import { toast } from '@/components/ui/use-toast'

export function handleError(error: any) {
  console.error('Error:', error)

  const message = error.response?.data?.error || error.message || 'An error occurred'

  toast({
    title: 'Error',
    description: message,
    variant: 'destructive',
  })
}
```

**5. Update Query Client with Error Handler**
```typescript
// In App.tsx
import { handleError } from '@/lib/errorHandler'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
      onError: handleError,
    },
    mutations: {
      onError: handleError,
    },
  },
})
```

### Acceptance Criteria

- [ ] API client configured with auth
- [ ] Token refresh works automatically
- [ ] Query hooks available for common endpoints
- [ ] Errors display user-friendly messages
- [ ] Toast notifications work
- [ ] 401 errors redirect to login

---

## Git Workflow

```bash
# Create branch
git checkout -b engineer-3/ui-scaffold

# After T3.2 complete (Day 2)
git add ui/
git commit -m "feat(ui): complete T3.2 - React project scaffold

- Created ui/ directory with React + TypeScript + Vite
- Installed dependencies (shadcn/ui, TanStack Query, Zustand)
- Configured routing and state management
- Set up project structure
- Dev server running at localhost:3000

Unblocks Engineer 4 for W4-E4-01"

git push origin engineer-3/ui-scaffold

# Notify Engineer 4: UI scaffold ready!

# After T4.3 complete (Day 4)
git add .
git commit -m "feat(ui): complete T4.3 - authentication UI

- Auth store with Zustand
- Login page with OIDC flow
- Protected route component
- Token management and refresh
- Environment variables configured"

git push origin engineer-3/ui-scaffold

# After T4.4 complete (Day 5)
git add .
git commit -m "feat(ui): complete T4.4 - data fetching & error handling

- Axios instance with interceptors
- API hooks (useServers, usePolicies, useAuditLogs)
- Global error handling
- Toast notifications
- Auto token refresh on 401"

git push origin engineer-3/ui-scaffold

# Create PR
gh pr create --title "[Engineer 3] UI Foundation - React Scaffold + Auth + Data Fetching" \
  --body "Completes Tasks T3.2, T4.3, T4.4

## Deliverables
- ✅ React + TypeScript + Vite project
- ✅ Authentication flow (OIDC)
- ✅ Data fetching with TanStack Query
- ✅ Error handling and notifications

## Tech Stack Confirmed
- React 18, TypeScript, Vite
- shadcn/ui + Tailwind CSS
- TanStack Query, Zustand, React Router

## Next Steps
- Engineer 4 can now complete Docker integration
- Ready for feature development (components, pages)"
```

---

## Coordination with Engineer 4

### Day 2 End: Handoff to Engineer 4

**When T3.2 is complete, notify Engineer 4:**

"✅ UI scaffold complete. You can now start W4-E4-01 (Vite build config).

The following are ready:
- `ui/package.json` with all dependencies
- `ui/vite.config.ts` (initial config)
- `ui/src/` directory structure
- Dev server runs on port 3000
- API proxy configured

You can proceed with:
- Optimizing Vite config for production
- Setting up environment variables
- Configuring build optimization"

### Parallel Work (Days 3-5)

While you work on T4.3 and T4.4, Engineer 4 will work on:
- W4-E4-01: Vite build configuration
- W4-E4-02: Docker Compose dev setup
- W4-E4-03: UI Dockerfile

Stay in sync via Slack or daily standups.

---

## Success Criteria

**End of Day 2:**
- [ ] UI scaffold complete
- [ ] Engineer 4 notified and unblocked
- [ ] `npm run dev` works

**End of Day 4:**
- [ ] Authentication working
- [ ] Protected routes functional
- [ ] Login/logout flow complete

**End of Day 5:**
- [ ] Data fetching hooks ready
- [ ] Error handling functional
- [ ] Ready for feature development

---

## Getting Help

**Blocked?** Ask in #sark-improvements-ui

**Questions about:**
- API endpoints → Engineer 2
- Docker/deployment → Engineer 4
- Documentation → Documenter

---

**START IMMEDIATELY - Engineer 4 is waiting!** 🚀
