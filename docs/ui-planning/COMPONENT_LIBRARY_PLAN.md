# SARK Component Library Plan

**Version:** 1.0.0
**Created:** 2025-11-27 (Week 3, Session W3-E1-04)
**Engineer:** Engineer 1 (Frontend Specialist)
**Technology Stack:** React 18+ | TypeScript 5+ | shadcn/ui | Tailwind CSS

---

## Overview

This document defines the complete component library for SARK's web interface. Components are built using shadcn/ui's copy-paste approach with Radix UI primitives and Tailwind CSS for styling.

### Design Principles

1. **Accessibility First** - WCAG 2.1 AA compliance
2. **Type Safety** - Full TypeScript support with strict types
3. **Composability** - Components can be combined easily
4. **Consistency** - Unified design language across all components
5. **Performance** - Optimized for minimal re-renders
6. **Customization** - Easy to theme and extend

---

## Component Categories

| Category | Count | Priority | Status |
|----------|-------|----------|--------|
| Layout | 5 | P0 | Week 4 |
| Foundation | 12 | P0 | Week 4 |
| Forms | 10 | P0 | Week 4 |
| Data Display | 8 | P0 | Week 5 |
| Feedback | 6 | P1 | Week 5 |
| Navigation | 4 | P0 | Week 4 |
| Overlays | 5 | P1 | Week 5 |
| Specialized | 8 | P1-P2 | Week 6 |
| **TOTAL** | **58** | | |

---

## 1. Layout Components (P0 - Week 4)

### 1.1 AppShell
**Purpose:** Main application layout structure

**Props:**
```typescript
interface AppShellProps {
  header: React.ReactNode;
  sidebar: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  sidebarCollapsed?: boolean;
  onSidebarToggle?: () => void;
}
```

**Features:**
- Responsive layout
- Collapsible sidebar
- Fixed header
- Scrollable content area

---

### 1.2 Header
**Purpose:** Top navigation bar with logo, search, and user menu

**Props:**
```typescript
interface HeaderProps {
  logo?: React.ReactNode;
  searchPlaceholder?: string;
  onSearch?: (query: string) => void;
  user?: {
    name: string;
    email: string;
    avatar?: string;
    role: string;
  };
  onLogout?: () => void;
}
```

**Features:**
- Global search
- User profile dropdown
- Notifications badge
- Breadcrumbs integration

---

### 1.3 Sidebar
**Purpose:** Navigation menu

**Props:**
```typescript
interface SidebarProps {
  items: NavigationItem[];
  collapsed?: boolean;
  activeItem?: string;
  onItemClick?: (item: NavigationItem) => void;
}

interface NavigationItem {
  id: string;
  label: string;
  icon?: React.ReactNode;
  href: string;
  badge?: number | string;
  children?: NavigationItem[];
}
```

**Features:**
- Nested navigation
- Active state indicators
- Icons with labels
- Collapse/expand animations

---

### 1.4 Container
**Purpose:** Content wrapper with consistent padding

**Props:**
```typescript
interface ContainerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  className?: string;
  children: React.ReactNode;
}
```

---

### 1.5 PageHeader
**Purpose:** Page-level header with title and actions

**Props:**
```typescript
interface PageHeaderProps {
  title: string;
  description?: string;
  breadcrumbs?: Breadcrumb[];
  actions?: React.ReactNode;
}
```

---

## 2. Foundation Components (P0 - Week 4)

### 2.1 Button
**Source:** shadcn/ui

**Variants:**
- `default` - Primary action button
- `destructive` - Delete/remove actions
- `outline` - Secondary actions
- `ghost` - Tertiary actions
- `link` - Text links

**Sizes:** `sm` | `md` | `lg` | `icon`

**Props:**
```typescript
interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'destructive' | 'outline' | 'ghost' | 'link';
  size?: 'sm' | 'md' | 'lg' | 'icon';
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}
```

---

### 2.2 Badge
**Source:** shadcn/ui

**Variants:**
- `default` - Neutral
- `success` - Green (Active, Success)
- `warning` - Orange (Warning, Inactive)
- `error` - Red (Error, Unhealthy)
- `info` - Blue (Info)

---

### 2.3 Avatar
**Source:** shadcn/ui

**Props:**
```typescript
interface AvatarProps {
  src?: string;
  alt: string;
  fallback: string; // Initials
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  status?: 'online' | 'offline' | 'busy' | 'away';
}
```

---

### 2.4 Card
**Source:** shadcn/ui

**Sub-components:**
- CardHeader
- CardTitle
- CardDescription
- CardContent
- CardFooter

---

### 2.5 Separator
**Source:** shadcn/ui

---

### 2.6 Skeleton
**Source:** shadcn/ui

**Usage:** Loading states for tables, cards, etc.

---

### 2.7 Tooltip
**Source:** shadcn/ui (Radix)

---

### 2.8 Progress
**Source:** shadcn/ui

---

### 2.9 Spinner
**Custom component**

**Sizes:** `xs` | `sm` | `md` | `lg`

---

### 2.10 Icon
**Library:** Lucide React

**Commonly used icons:**
- Navigation: Home, Server, Users, FileText, Settings
- Actions: Plus, Edit, Trash, Check, X, Save
- Status: CheckCircle, XCircle, AlertCircle, Info
- Data: Search, Filter, Download, Upload

---

### 2.11 EmptyState
**Custom component**

**Props:**
```typescript
interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}
```

---

### 2.12 ErrorBoundary
**Custom component**

**Props:**
```typescript
interface ErrorBoundaryProps {
  fallback?: React.ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  children: React.ReactNode;
}
```

---

## 3. Form Components (P0 - Week 4)

All forms use **React Hook Form** with **Zod** validation.

### 3.1 Input
**Source:** shadcn/ui

**Types:** text, email, password, number, url, search

**Props:**
```typescript
interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}
```

---

### 3.2 Textarea
**Source:** shadcn/ui

---

### 3.3 Select
**Source:** shadcn/ui (Radix)

**Features:**
- Searchable
- Multi-select variant
- Grouped options
- Custom render

---

### 3.4 Checkbox
**Source:** shadcn/ui

---

### 3.5 RadioGroup
**Source:** shadcn/ui

---

### 3.6 Switch
**Source:** shadcn/ui

---

### 3.7 Slider
**Source:** shadcn/ui

---

### 3.8 DatePicker
**Library:** React Day Picker + shadcn/ui Popover

**Props:**
```typescript
interface DatePickerProps {
  value?: Date;
  onChange?: (date: Date | undefined) => void;
  disabled?: boolean;
  minDate?: Date;
  maxDate?: Date;
  placeholder?: string;
}
```

---

### 3.9 Form
**Source:** shadcn/ui (React Hook Form wrapper)

**Sub-components:**
- FormField
- FormItem
- FormLabel
- FormControl
- FormDescription
- FormMessage

---

### 3.10 Combobox
**Source:** shadcn/ui (Radix + cmdk)

**Usage:** Searchable select with keyboard navigation

---

## 4. Data Display Components (P0 - Week 5)

### 4.1 Table
**Source:** TanStack Table + shadcn/ui

**Features:**
- Sorting
- Filtering
- Pagination
- Row selection
- Column visibility toggle
- Expandable rows
- Virtual scrolling (for large datasets)

**Props:**
```typescript
interface TableProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  pagination?: PaginationConfig;
  sorting?: SortingConfig;
  selection?: 'none' | 'single' | 'multiple';
  onRowClick?: (row: T) => void;
  loading?: boolean;
  emptyState?: React.ReactNode;
}
```

---

### 4.2 DataTable
**Custom wrapper around Table**

**Additional features:**
- Built-in search
- Column filters
- Export functionality
- Bulk actions

---

### 4.3 StatsCard
**Custom component**

**Props:**
```typescript
interface StatsCardProps {
  title: string;
  value: string | number;
  change?: {
    value: number;
    trend: 'up' | 'down' | 'neutral';
  };
  icon?: React.ReactNode;
  description?: string;
}
```

---

### 4.4 Chart
**Library:** Recharts

**Types:**
- LineChart
- BarChart
- AreaChart
- PieChart
- DonutChart

---

### 4.5 Timeline
**Custom component**

**Usage:** Audit logs, activity feed

**Props:**
```typescript
interface TimelineProps {
  items: TimelineItem[];
  loading?: boolean;
}

interface TimelineItem {
  id: string;
  title: string;
  description?: string;
  timestamp: Date;
  icon?: React.ReactNode;
  status?: 'success' | 'error' | 'warning' | 'info';
}
```

---

### 4.6 CodeBlock
**Library:** Prism React Renderer

**Features:**
- Syntax highlighting
- Line numbers
- Copy button
- Language selector

---

### 4.7 JsonViewer
**Library:** react-json-view

**Usage:** Display API responses, policy input/output

---

### 4.8 Tabs
**Source:** shadcn/ui (Radix)

---

## 5. Feedback Components (P1 - Week 5)

### 5.1 Alert
**Source:** shadcn/ui

**Variants:** `default` | `destructive` | `warning` | `success`

---

### 5.2 Toast
**Source:** shadcn/ui (Sonner)

**Types:**
- Success toast
- Error toast
- Warning toast
- Info toast
- Loading toast
- Promise toast

---

### 5.3 AlertDialog
**Source:** shadcn/ui (Radix)

**Usage:** Confirmations, warnings

---

### 5.4 Banner
**Custom component**

**Usage:** Page-level announcements, deprecation warnings

---

### 5.5 LoadingOverlay
**Custom component**

**Usage:** Full-page or section loading states

---

### 5.6 ConfirmDialog
**Custom wrapper around AlertDialog**

**Props:**
```typescript
interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'default' | 'destructive';
  onConfirm: () => void | Promise<void>;
  loading?: boolean;
}
```

---

## 6. Navigation Components (P0 - Week 4)

### 6.1 Breadcrumbs
**Custom component**

---

### 6.2 Pagination
**Custom component**

**Features:**
- Page numbers
- First/last buttons
- Rows per page selector
- Total count display

---

### 6.3 Tabs (duplicate from Data Display)
See section 4.8

---

### 6.4 NavigationMenu
**Source:** shadcn/ui (Radix)

**Usage:** Top-level navigation, mega menus

---

## 7. Overlay Components (P1 - Week 5)

### 7.1 Dialog
**Source:** shadcn/ui (Radix)

---

### 7.2 Sheet
**Source:** shadcn/ui (Radix)

**Usage:** Slide-out panels, mobile menus

---

### 7.3 Popover
**Source:** shadcn/ui (Radix)

---

### 7.4 DropdownMenu
**Source:** shadcn/ui (Radix)

---

### 7.5 ContextMenu
**Source:** shadcn/ui (Radix)

---

## 8. Specialized Components (P1-P2 - Week 6)

### 8.1 MonacoEditor
**Library:** @monaco-editor/react

**Usage:** Policy editor (Rego)

**Features:**
- Syntax highlighting for Rego
- Auto-completion
- Error indicators
- Line numbers
- Theme support (light/dark)

**Props:**
```typescript
interface MonacoEditorProps {
  value: string;
  onChange: (value: string) => void;
  language: 'rego' | 'json' | 'yaml';
  readOnly?: boolean;
  height?: string;
  theme?: 'light' | 'dark';
  options?: monaco.editor.IStandaloneEditorConstructionOptions;
}
```

---

### 8.2 PolicyTester
**Custom component**

**Features:**
- Input editor (JSON)
- Output display
- Test cases management
- Run button with loading state

---

### 8.3 ServerStatusIndicator
**Custom component**

**Props:**
```typescript
interface ServerStatusIndicatorProps {
  status: 'registered' | 'active' | 'inactive' | 'unhealthy' | 'decommissioned';
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
}
```

---

### 8.4 HealthCheckBadge
**Custom component**

**Shows:** Last check time, status, next check

---

### 8.5 FilterBuilder
**Custom component**

**Usage:** Advanced audit log filtering

**Features:**
- Add/remove filter conditions
- AND/OR operators
- Multiple field types (text, select, date, number)

---

### 8.6 BulkActionBar
**Custom component**

**Usage:** Table bulk actions

**Features:**
- Selection count
- Action buttons
- Clear selection

---

### 8.7 FileUpload
**Custom component**

**Features:**
- Drag and drop
- File type validation
- Size validation
- Progress indicator
- Multiple files support

---

### 8.8 ExportButton
**Custom component**

**Formats:** CSV, JSON, PDF

**Props:**
```typescript
interface ExportButtonProps {
  data: any[];
  filename: string;
  formats?: ('csv' | 'json' | 'pdf')[];
  onExport?: (format: string) => void;
}
```

---

## Implementation Plan

### Week 4: Foundation (19 components)
**Days 1-2: Layout**
- AppShell
- Header
- Sidebar
- Container
- PageHeader

**Days 3-4: Foundation**
- All 12 foundation components from shadcn/ui
- Custom Spinner and EmptyState

**Day 5: Forms (Part 1)**
- Input, Textarea, Select, Checkbox
- RadioGroup, Switch

---

### Week 5: Data & Feedback (22 components)
**Days 1-2: Forms (Part 2)**
- Slider, DatePicker, Form, Combobox

**Days 3-4: Data Display**
- Table, DataTable, StatsCard, Chart
- Timeline, CodeBlock, JsonViewer, Tabs

**Day 5: Feedback**
- Alert, Toast, AlertDialog
- Banner, LoadingOverlay, ConfirmDialog

---

### Week 6: Navigation & Specialized (17 components)
**Day 1: Navigation**
- Breadcrumbs, Pagination, NavigationMenu

**Days 2-3: Overlays**
- Dialog, Sheet, Popover
- DropdownMenu, ContextMenu

**Days 4-5: Specialized**
- MonacoEditor, PolicyTester
- ServerStatusIndicator, HealthCheckBadge
- FilterBuilder, BulkActionBar
- FileUpload, ExportButton

---

## Component Organization

```
src/
├── components/
│   ├── ui/                    # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   ├── select.tsx
│   │   └── ... (all shadcn components)
│   │
│   ├── layout/                # Layout components
│   │   ├── AppShell/
│   │   │   ├── AppShell.tsx
│   │   │   ├── AppShell.test.tsx
│   │   │   └── index.ts
│   │   ├── Header/
│   │   ├── Sidebar/
│   │   └── ...
│   │
│   ├── data-display/          # Data display components
│   │   ├── Table/
│   │   ├── Chart/
│   │   └── ...
│   │
│   ├── forms/                 # Custom form components
│   │   └── ...
│   │
│   ├── feedback/              # Feedback components
│   │   └── ...
│   │
│   └── specialized/           # SARK-specific components
│       ├── MonacoEditor/
│       ├── PolicyTester/
│       └── ...
│
└── lib/
    └── utils.ts               # Utility functions (cn, etc.)
```

---

## Testing Strategy

### Unit Tests
- Every component must have unit tests
- Test accessibility (aria-labels, keyboard navigation)
- Test all variants and states
- Test event handlers

### Visual Regression Tests
- Storybook for component documentation
- Chromatic for visual regression testing

### Integration Tests
- Test form submissions
- Test table interactions (sorting, filtering, pagination)
- Test dialog workflows

---

## Accessibility Checklist

Every component must meet these requirements:

- [ ] **Keyboard navigation** - All interactive elements accessible via keyboard
- [ ] **Focus indicators** - Clear visual focus states
- [ ] **ARIA labels** - Proper ARIA attributes for screen readers
- [ ] **Color contrast** - WCAG AA minimum (4.5:1 for text)
- [ ] **Focus trapping** - Modals/dialogs trap focus
- [ ] **Error messages** - Associated with form fields
- [ ] **Loading states** - Announced to screen readers
- [ ] **Semantic HTML** - Proper use of headings, buttons, links

---

## Theming

### Color Palette
```typescript
// Tailwind config
colors: {
  border: "hsl(var(--border))",
  input: "hsl(var(--input))",
  ring: "hsl(var(--ring))",
  background: "hsl(var(--background))",
  foreground: "hsl(var(--foreground))",
  primary: {
    DEFAULT: "hsl(var(--primary))",
    foreground: "hsl(var(--primary-foreground))",
  },
  // ... (full shadcn/ui color system)
}
```

### Dark Mode
- System preference detection
- Manual toggle
- Persistent preference (localStorage)
- All components support both themes

---

## Performance Optimization

### Lazy Loading
- Code split routes
- Lazy load heavy components (Monaco, Charts)

### Memoization
- Use `React.memo` for expensive renders
- Use `useMemo` for expensive computations
- Use `useCallback` for event handlers passed to children

### Virtual Scrolling
- Use @tanstack/react-virtual for long lists
- Implement in Table component for 1000+ rows

---

## Documentation

### Storybook
Every component must have Storybook stories showing:
- Default state
- All variants
- All sizes
- Interactive examples
- Code examples

### TypeScript
- Fully typed props
- Exported types for consumption
- JSDoc comments for complex props

---

## Component Checklist

Before marking a component complete:

- [ ] TypeScript types defined and exported
- [ ] Unit tests written (>80% coverage)
- [ ] Accessible (keyboard, screen reader, ARIA)
- [ ] Responsive (mobile, tablet, desktop)
- [ ] Dark mode support
- [ ] Storybook story created
- [ ] Used in at least one page
- [ ] Code reviewed
- [ ] Documentation updated

---

## References

- [shadcn/ui Documentation](https://ui.shadcn.com)
- [Radix UI Primitives](https://www.radix-ui.com)
- [TailwindCSS Documentation](https://tailwindcss.com)
- [React Hook Form](https://react-hook-form.com)
- [TanStack Table](https://tanstack.com/table)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

---

**Status:** ✅ Planning Complete
**Next Steps:** Begin Week 4 implementation (W4-E1-01: Build layout components)

---

**Created:** 2025-11-27 (Week 3, Session W3-E1-04)
**Engineer:** Engineer 1 (Frontend Specialist)
**Last Updated:** 2025-11-27
