# SARK Frontend Implementation Roadmap - Weeks 5-8

This document provides detailed implementation guides for the remaining UI features.

## Status

✅ **Week 2**: Documentation & Tutorials (Complete)
✅ **Week 3**: React foundation & routing (Complete)
✅ **Week 4**: Auth, state, error handling (Complete)
🚧 **Week 5**: Core UI pages (Ready to implement)
🚧 **Week 6**: Advanced features (Ready to implement)
🚧 **Week 7**: Polish & optimization (Ready to implement)
🚧 **Week 8**: Production & testing (Ready to implement)

---

## Week 5: Core UI Pages (20h)

### W5-E3-01: MCP Servers List Page (4h)

**File**: `frontend/src/pages/servers/ServersListPage.tsx`

**Features**:
- Data table with sortable columns
- Search by server name/description
- Filters: status, sensitivity, transport
- Pagination with cursor-based navigation
- Actions: view, edit, delete
- "Register Server" button

**Implementation**:
```typescript
import { useQuery } from '@tanstack/react-query';
import { serversApi } from '@/services/api';
import { useState } from 'react';

export default function ServersListPage() {
  const [search, setSearch] = useState('');
  const [filters, setFilters] = useState({
    status: '',
    sensitivity: '',
  });

  const { data, isLoading } = useQuery({
    queryKey: ['servers', search, filters],
    queryFn: () => serversApi.list({ search, ...filters }),
  });

  return (
    <div>
      <div className="flex justify-between mb-6">
        <input
          type="search"
          placeholder="Search servers..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <Link to="/servers/register">Register Server</Link>
      </div>

      <table>
        {/* Table implementation */}
      </table>
    </div>
  );
}
```

**shadcn/ui components needed**:
- `npx shadcn-ui@latest add table`
- `npx shadcn-ui@latest add input`
- `npx shadcn-ui@latest add button`
- `npx shadcn-ui@latest add select`

---

### W5-E3-02: Server Registration Form (4h)

**File**: `frontend/src/pages/servers/ServerRegisterPage.tsx`

**Features**:
- Multi-step form wizard
- Server basic info (name, transport, endpoint)
- Tools definition with JSON schema
- Sensitivity level selection
- Metadata tags
- Form validation with Zod
- Submit with loading state

**Implementation**:
```typescript
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { serversApi } from '@/services/api';

const schema = z.object({
  name: z.string().min(1).max(255),
  transport: z.enum(['http', 'stdio', 'sse']),
  endpoint: z.string().url().optional(),
  tools: z.array(z.object({
    name: z.string(),
    description: z.string().optional(),
    sensitivity_level: z.enum(['low', 'medium', 'high', 'critical']),
  })),
});

export default function ServerRegisterPage() {
  const queryClient = useQueryClient();
  const form = useForm({ resolver: zodResolver(schema) });

  const mutation = useMutation({
    mutationFn: serversApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['servers'] });
      toast.success('Server registered');
      navigate('/servers');
    },
  });

  return <form onSubmit={form.handleSubmit(data => mutation.mutate(data))}>
    {/* Form fields */}
  </form>;
}
```

**Dependencies**:
```bash
npm install react-hook-form @hookform/resolvers zod
npx shadcn-ui@latest add form
```

---

### W5-E3-03: Policy Viewer (4h)

**File**: `frontend/src/pages/policies/PoliciesPage.tsx`

**Features**:
- List all OPA policies
- Syntax-highlighted Rego code display
- Policy metadata (package, rules)
- Upload/edit/delete actions

**Implementation**:
```typescript
import { useQuery } from '@tanstack/react-query';
import { policyApi } from '@/services/api';

export default function PoliciesPage() {
  const { data: policies } = useQuery({
    queryKey: ['policies'],
    queryFn: policyApi.list,
  });

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-1">
        <h2>Policies</h2>
        <ul>
          {policies?.map(p => (
            <li key={p.id}>{p.name}</li>
          ))}
        </ul>
      </div>
      <div className="lg:col-span-2">
        <pre className="bg-muted p-4 rounded-lg">
          {/* Policy content */}
        </pre>
      </div>
    </div>
  );
}
```

---

### W5-E3-04: Audit Log Viewer (4h)

**File**: `frontend/src/pages/audit/AuditLogsPage.tsx`

**Features**:
- Time-based filtering (last 1h, 24h, 7d)
- Event type filter
- User/server filters
- Export to CSV
- Real-time updates (WebSocket in W6)

**Implementation**:
```typescript
import { useQuery } from '@tanstack/react-query';
import { auditApi } from '@/services/api';
import { useState } from 'react';

export default function AuditLogsPage() {
  const [period, setPeriod] = useState('24h');

  const { data } = useQuery({
    queryKey: ['audit-events', period],
    queryFn: () => auditApi.getEvents({
      start_time: getStartTime(period),
    }),
    refetchInterval: 30000, // Refetch every 30s
  });

  return (
    <div>
      <select value={period} onChange={e => setPeriod(e.target.value)}>
        <option value="1h">Last Hour</option>
        <option value="24h">Last 24 Hours</option>
        <option value="7d">Last 7 Days</option>
      </select>

      <table>
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Event Type</th>
            <th>User</th>
            <th>Decision</th>
            <th>Tool</th>
          </tr>
        </thead>
        <tbody>
          {data?.events.map(event => (
            <tr key={event.event_id}>
              <td>{formatDate(event.timestamp)}</td>
              <td>{event.event_type}</td>
              <td>{event.user_email}</td>
              <td>
                <span className={event.decision === 'allow' ? 'text-green-600' : 'text-red-600'}>
                  {event.decision}
                </span>
              </td>
              <td>{event.tool_name}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

---

### W5-E3-05: Search and Pagination Components (4h)

**Files**:
- `frontend/src/components/SearchInput.tsx`
- `frontend/src/components/Pagination.tsx`

**Implementation**:
```typescript
// SearchInput.tsx
import { useState, useEffect } from 'react';
import { useDebounce } from '@/hooks/useDebounce';

interface SearchInputProps {
  onSearch: (value: string) => void;
  placeholder?: string;
}

export function SearchInput({ onSearch, placeholder }: SearchInputProps) {
  const [value, setValue] = useState('');
  const debouncedValue = useDebounce(value, 300);

  useEffect(() => {
    onSearch(debouncedValue);
  }, [debouncedValue, onSearch]);

  return (
    <input
      type="search"
      value={value}
      onChange={(e) => setValue(e.target.value)}
      placeholder={placeholder}
      className="w-full px-4 py-2 border rounded-lg"
    />
  );
}

// Pagination.tsx
interface PaginationProps {
  hasMore: boolean;
  onLoadMore: () => void;
  isLoading: boolean;
}

export function Pagination({ hasMore, onLoadMore, isLoading }: PaginationProps) {
  return (
    <div className="flex justify-center mt-6">
      {hasMore && (
        <button
          onClick={onLoadMore}
          disabled={isLoading}
          className="px-6 py-2 bg-primary text-white rounded-lg"
        >
          {isLoading ? 'Loading...' : 'Load More'}
        </button>
      )}
    </div>
  );
}
```

---

## Week 6: Advanced Features (20h)

### W6-E3-01: Rego Syntax Highlighting (4h)

**Dependencies**:
```bash
npm install @codemirror/lang-rego @uiw/react-codemirror
```

**Implementation**:
```typescript
import CodeMirror from '@uiw/react-codemirror';
import { rego } from '@codemirror/lang-rego';

export function RegoEditor({ value, onChange }: RegoEditorProps) {
  return (
    <CodeMirror
      value={value}
      height="600px"
      extensions={[rego()]}
      onChange={onChange}
      theme="dark"
    />
  );
}
```

---

### W6-E3-02: Policy Save/Edit (4h)

Add edit functionality to PoliciesPage with CodeMirror editor.

---

### W6-E3-03: Data Export (4h)

**File**: `frontend/src/utils/export.ts`

```typescript
export function exportToCSV(data: any[], filename: string) {
  const csv = Papa.unparse(data);
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
}

export function exportToJSON(data: any, filename: string) {
  const json = JSON.stringify(data, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  // ... same download logic
}
```

**Dependencies**: `npm install papaparse`

---

### W6-E3-04: API Key Management UI (4h)

Implement full CRUD for API keys with copy-to-clipboard functionality.

---

### W6-E3-05: WebSocket Real-time Updates (4h)

**File**: `frontend/src/hooks/useWebSocket.ts`

```typescript
import { useEffect, useRef } from 'react';

export function useWebSocket(url: string, onMessage: (data: any) => void) {
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    const token = getAccessToken();
    ws.current = new WebSocket(`${url}?token=${token}`);

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onMessage(data);
    };

    return () => ws.current?.close();
  }, [url, onMessage]);
}
```

Usage in AuditLogsPage:
```typescript
useWebSocket('ws://localhost:8000/ws', (event) => {
  // Update audit logs in real-time
  queryClient.setQueryData(['audit-events'], (old) => ({
    ...old,
    events: [event, ...old.events],
  }));
});
```

---

## Week 7: Polish & UX (20h)

### W7-E3-01: Dark Mode Support (4h)

Already configured in Tailwind. Add toggle:

```typescript
// components/ThemeToggle.tsx
import { useUIStore } from '@/stores/uiStore';

export function ThemeToggle() {
  const { theme, setTheme } = useUIStore();

  useEffect(() => {
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');

    if (theme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      root.classList.add(systemTheme);
    } else {
      root.classList.add(theme);
    }
  }, [theme]);

  return <button onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>Toggle</button>;
}
```

---

### W7-E3-02: Keyboard Shortcuts (4h)

```bash
npm install react-hotkeys-hook
```

```typescript
import { useHotkeys } from 'react-hotkeys-hook';

// In layout component
useHotkeys('ctrl+k', () => setSearchOpen(true));
useHotkeys('ctrl+n', () => navigate('/servers/register'));
useHotkeys('esc', () => setSearchOpen(false));
```

---

### W7-E3-03: Tooltips and Help (4h)

```bash
npx shadcn-ui@latest add tooltip
npx shadcn-ui@latest add popover
```

Add tooltips to all icons and buttons.

---

### W7-E3-04: Bundle Optimization (4h)

**vite.config.ts**:
```typescript
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          query: ['@tanstack/react-query'],
          ui: ['@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu'],
        },
      },
    },
  },
});
```

Lazy load routes:
```typescript
const ServersListPage = lazy(() => import('./pages/servers/ServersListPage'));
```

---

### W7-E3-05: Loading Indicators (4h)

```bash
npx shadcn-ui@latest add skeleton
```

Add skeletons to all data-loading pages.

---

## Week 8: Production Ready (12h)

### W8-E3-01: Production Config (4h)

**File**: `frontend/.env.production`
```bash
VITE_API_BASE_URL=https://api.sark.yourdomain.com
VITE_APP_ENV=production
VITE_ENABLE_WEBSOCKETS=true
```

**Dockerfile**:
```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
```

---

### W8-E3-02: Bug Fixes (4h)

Test all features end-to-end and fix issues.

---

### W8-E3-03: Performance Testing (4h)

- Lighthouse audit (target: 90+ score)
- Bundle size analysis
- Load time optimization

---

## Quick Start Guide

To implement any week:

1. **Check dependencies**: Install required npm packages
2. **Add shadcn components**: Use provided commands
3. **Copy implementation**: Use code snippets above
4. **Test with backend**: Ensure SARK backend is running
5. **Commit**: `git commit -m "feat: implement [feature]"`

## Priority Order

If implementing incrementally:
1. Week 5 (Core UI) - Most important
2. Week 6 (Advanced features) - High value
3. Week 7 (Polish) - User experience
4. Week 8 (Production) - Deployment

Total estimated time: **72 hours** (Weeks 5-8)

---

## Related Documentation

- **[API Reference](./API_REFERENCE.md)** - Complete API docs
- **[Frontend README](../../frontend/README.md)** - Setup guide
- **[SARK Backend](../../README.md)** - Backend setup

---

**All foundation work (Weeks 2-4) is complete. Ready to build!**
