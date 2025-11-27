# SARK UI Design System

**Version:** 1.0.0
**Created:** 2025-11-27 (Week 3, Session W3-E1-05)
**Engineer:** Engineer 1 (Frontend Specialist)
**Based On:** shadcn/ui + Tailwind CSS

---

## Introduction

This design system defines the visual language, components, and patterns for SARK's web interface. It ensures consistency, accessibility, and maintainability across all UI elements.

### Design Principles

1. **Clarity** - Information should be easy to understand at a glance
2. **Efficiency** - Users should accomplish tasks quickly
3. **Consistency** - Similar elements should look and behave similarly
4. **Accessibility** - Everyone should be able to use SARK effectively
5. **Trust** - Design should inspire confidence in critical operations

---

## Color System

### Brand Colors

```css
--primary: 221 83% 53%;        /* #2563eb - Primary blue */
--primary-foreground: 210 40% 98%;
```

### Semantic Colors

#### Success (Green)
```css
--success: 142 76% 36%;        /* #16a34a */
--success-light: 142 76% 96%;
--success-foreground: 355 100% 97%;
```

**Usage:** Active servers, successful operations, positive metrics

#### Warning (Orange)
```css
--warning: 25 95% 53%;         /* #f59e0b */
--warning-light: 48 96% 95%;
--warning-foreground: 20 14% 4%;
```

**Usage:** Inactive servers, degraded state, attention needed

#### Error (Red)
```css
--destructive: 0 84% 60%;      /* #ef4444 */
--destructive-light: 0 93% 95%;
--destructive-foreground: 0 0% 98%;
```

**Usage:** Unhealthy servers, failed operations, critical errors

#### Info (Blue)
```css
--info: 217 91% 60%;           /* #3b82f6 */
--info-light: 214 95% 95%;
--info-foreground: 222 47% 11%;
```

**Usage:** Informational messages, policy updates

### Neutral Colors

```css
--background: 0 0% 100%;       /* #ffffff */
--foreground: 222 84% 4.9%;    /* #020817 */

--card: 0 0% 100%;
--card-foreground: 222 84% 4.9%;

--popover: 0 0% 100%;
--popover-foreground: 222 84% 4.9%;

--muted: 210 40% 96.1%;        /* #f1f5f9 */
--muted-foreground: 215.4 16.3% 46.9%;

--accent: 210 40% 96.1%;
--accent-foreground: 222 47% 11%;

--border: 214.3 31.8% 91.4%;   /* #e2e8f0 */
--input: 214.3 31.8% 91.4%;
--ring: 221 83% 53%;
```

### Dark Mode Colors

```css
[class~="dark"] {
  --background: 222 84% 4.9%;   /* #020817 */
  --foreground: 210 40% 98%;    /* #f8fafc */

  --card: 222 84% 4.9%;
  --card-foreground: 210 40% 98%;

  --muted: 217 32% 17%;         /* #1e293b */
  --muted-foreground: 215 20% 65%;

  --border: 217 32% 17%;
  --input: 217 32% 17%;
  --ring: 224 76% 48%;
}
```

### Status Colors

| Status | Color | Hex | Usage |
|--------|-------|-----|-------|
| Active | Green | `#22c55e` | Servers, users online |
| Inactive | Orange | `#f59e0b` | Disabled, paused |
| Unhealthy | Red | `#ef4444` | Failed health checks |
| Registered | Gray | `#94a3b8` | Pending activation |
| Decommissioned | Dark Gray | `#64748b` | Archived |

### Sensitivity Level Colors

| Level | Color | Hex |
|-------|-------|-----|
| Low | Green | `#22c55e` |
| Medium | Blue | `#3b82f6` |
| High | Orange | `#f59e0b` |
| Critical | Red | `#ef4444` |

---

## Typography

### Font Family

```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
             "Helvetica Neue", Arial, sans-serif;
```

**Code/Monospace:**
```css
font-family: ui-monospace, SFMono-Regular, "SF Mono", Consolas,
             "Liberation Mono", Menlo, monospace;
```

### Type Scale

| Name | Size | Line Height | Weight | Usage |
|------|------|-------------|--------|-------|
| Display | 48px | 1.1 | 700 | Hero sections |
| H1 | 36px | 1.2 | 700 | Page titles |
| H2 | 30px | 1.3 | 700 | Section titles |
| H3 | 24px | 1.4 | 600 | Sub-sections |
| H4 | 20px | 1.4 | 600 | Card titles |
| H5 | 16px | 1.5 | 600 | Small headings |
| H6 | 14px | 1.5 | 600 | Smallest headings |
| Body Large | 16px | 1.6 | 400 | Large body text |
| Body | 14px | 1.6 | 400 | Default body |
| Body Small | 13px | 1.5 | 400 | Small text |
| Caption | 12px | 1.4 | 400 | Captions, labels |
| Overline | 11px | 1.3 | 500 | Tags, badges |

### Font Weights

- **Regular:** 400 (body text)
- **Medium:** 500 (emphasis)
- **Semibold:** 600 (headings, buttons)
- **Bold:** 700 (strong emphasis, titles)

### Text Colors

```css
--text-primary: hsl(var(--foreground));
--text-secondary: hsl(var(--muted-foreground));
--text-tertiary: hsl(215 16.3% 46.9%);
--text-disabled: hsl(220 8.9% 46.1%);
--text-link: hsl(var(--primary));
```

---

## Spacing System

Based on 4px base unit (0.25rem).

### Spacing Scale

| Token | Value | Pixels | Usage |
|-------|-------|--------|-------|
| spacing-0 | 0rem | 0px | Reset |
| spacing-1 | 0.25rem | 4px | Tiny gaps |
| spacing-2 | 0.5rem | 8px | Small gaps |
| spacing-3 | 0.75rem | 12px | Medium-small |
| spacing-4 | 1rem | 16px | Default |
| spacing-5 | 1.25rem | 20px | Medium |
| spacing-6 | 1.5rem | 24px | Medium-large |
| spacing-8 | 2rem | 32px | Large |
| spacing-10 | 2.5rem | 40px | Extra large |
| spacing-12 | 3rem | 48px | XXL |
| spacing-16 | 4rem | 64px | Section spacing |
| spacing-20 | 5rem | 80px | Large sections |
| spacing-24 | 6rem | 96px | Very large sections |

### Layout Spacing

- **Component padding:** 16px (spacing-4)
- **Card padding:** 24px (spacing-6)
- **Section spacing:** 48px (spacing-12)
- **Page margins:** 24px mobile, 48px desktop

---

## Border Radius

```css
--radius-none: 0px;
--radius-sm: 0.125rem;     /* 2px - tight corners */
--radius-md: 0.375rem;     /* 6px - default */
--radius-lg: 0.5rem;       /* 8px - cards */
--radius-xl: 0.75rem;      /* 12px - large cards */
--radius-2xl: 1rem;        /* 16px - modals */
--radius-full: 9999px;     /* Pills, avatars */
```

### Usage

- **Buttons:** `radius-md` (6px)
- **Cards:** `radius-lg` (8px)
- **Inputs:** `radius-md` (6px)
- **Badges:** `radius-full` (pill shape)
- **Avatars:** `radius-full` (circle)
- **Modals:** `radius-xl` (12px)

---

## Shadows

### Elevation System

```css
/* Level 0 - Flat */
--shadow-none: none;

/* Level 1 - Subtle */
--shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);

/* Level 2 - Default */
--shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1),
            0 2px 4px -2px rgb(0 0 0 / 0.1);

/* Level 3 - Elevated */
--shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1),
            0 4px 6px -4px rgb(0 0 0 / 0.1);

/* Level 4 - High */
--shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1),
            0 8px 10px -6px rgb(0 0 0 / 0.1);

/* Level 5 - Floating */
--shadow-2xl: 0 25px 50px -12px rgb(0 0 0 / 0.25);
```

### Usage

- **Cards:** `shadow-sm`
- **Dropdowns:** `shadow-lg`
- **Modals:** `shadow-xl`
- **Tooltips:** `shadow-md`
- **Hover states:** Increase shadow level

---

## Borders

### Border Widths

```css
--border-none: 0px;
--border-thin: 1px;
--border-default: 1px;
--border-thick: 2px;
```

### Border Colors

```css
--border-default: hsl(var(--border));
--border-muted: hsl(214.3 31.8% 91.4%);
--border-strong: hsl(215.4 16.3% 46.9%);
--border-success: hsl(142 76% 36%);
--border-warning: hsl(25 95% 53%);
--border-error: hsl(0 84% 60%);
```

---

## Iconography

### Icon Library

**Primary:** Lucide React
**Size variants:** 16px, 20px, 24px, 32px

### Icon Sizes

| Size | Pixels | Usage |
|------|--------|-------|
| xs | 12px | Inline with small text |
| sm | 16px | Inline with body text |
| md | 20px | Buttons, nav items |
| lg | 24px | Section headers |
| xl | 32px | Feature highlights |
| 2xl | 48px | Empty states |

### Icon Colors

- **Default:** `currentColor` (inherits text color)
- **Muted:** `text-muted-foreground`
- **Primary:** `text-primary`
- **Success:** `text-green-600`
- **Warning:** `text-orange-500`
- **Error:** `text-red-500`

---

## Animation & Motion

### Duration

```css
--duration-instant: 0ms;
--duration-fast: 150ms;
--duration-normal: 300ms;
--duration-slow: 500ms;
--duration-slower: 700ms;
```

### Easing

```css
--ease-linear: linear;
--ease-in: cubic-bezier(0.4, 0, 1, 1);
--ease-out: cubic-bezier(0, 0, 0.2, 1);
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
```

### Transitions

```css
/* Default transition */
transition: all 150ms cubic-bezier(0.4, 0, 0.2, 1);

/* Color transitions */
transition: color 150ms ease-out, background-color 150ms ease-out;

/* Transform transitions */
transition: transform 300ms cubic-bezier(0.4, 0, 0.2, 1);
```

### Animation Principles

1. **Purposeful** - Every animation should have a clear purpose
2. **Fast** - Keep animations under 300ms for most interactions
3. **Subtle** - Animations should enhance, not distract
4. **Consistent** - Use consistent timing and easing
5. **Reducible** - Respect `prefers-reduced-motion`

### Common Animations

**Fade In:**
```css
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
animation: fadeIn 200ms ease-out;
```

**Slide Up:**
```css
@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
animation: slideUp 300ms cubic-bezier(0.4, 0, 0.2, 1);
```

**Scale In:**
```css
@keyframes scaleIn {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
animation: scaleIn 200ms cubic-bezier(0.4, 0, 0.2, 1);
```

---

## Breakpoints

```css
/* Mobile first approach */
--screen-sm: 640px;    /* Small devices */
--screen-md: 768px;    /* Tablets */
--screen-lg: 1024px;   /* Desktops */
--screen-xl: 1280px;   /* Large desktops */
--screen-2xl: 1536px;  /* Extra large screens */
```

### Responsive Design

- **Mobile:** 375px - 639px
- **Tablet:** 640px - 1023px
- **Desktop:** 1024px+
- **Large Desktop:** 1280px+

---

## Layout Grid

### Container Widths

```css
.container {
  width: 100%;
  margin-left: auto;
  margin-right: auto;
  padding-left: 1rem;
  padding-right: 1rem;
}

@media (min-width: 640px) {
  .container { max-width: 640px; }
}
@media (min-width: 768px) {
  .container { max-width: 768px; }
}
@media (min-width: 1024px) {
  .container { max-width: 1024px; }
}
@media (min-width: 1280px) {
  .container { max-width: 1280px; }
}
@media (min-width: 1536px) {
  .container { max-width: 1536px; }
}
```

### Grid System

12-column responsive grid using CSS Grid or Flexbox.

```css
.grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 1.5rem;
}

.col-span-6 {
  grid-column: span 6 / span 6;
}
```

---

## Component Patterns

### Buttons

**Hierarchy:**
1. **Primary** - Main action (1 per screen)
2. **Secondary** - Alternative actions
3. **Tertiary** - Low-priority actions
4. **Link** - Navigation actions

**States:**
- Default
- Hover (darken 10%)
- Active (darken 20%)
- Focus (ring-2 ring-primary ring-offset-2)
- Disabled (opacity-50 cursor-not-allowed)
- Loading (spinner + disabled state)

### Input Fields

**States:**
- Default
- Hover (border-color darkens)
- Focus (ring-2 ring-primary)
- Error (border-destructive + error message)
- Disabled (bg-muted cursor-not-allowed)
- Read-only (bg-muted)

### Cards

**Variants:**
- Default (border + shadow-sm)
- Hover (shadow-md on hover)
- Interactive (cursor-pointer + hover state)
- Selected (border-primary ring-1 ring-primary)

---

## Accessibility

### Focus States

All interactive elements must have visible focus indicators:

```css
:focus-visible {
  outline: 2px solid hsl(var(--ring));
  outline-offset: 2px;
}
```

### Color Contrast

Minimum contrast ratios (WCAG AA):
- **Normal text:** 4.5:1
- **Large text (18px+):** 3:1
- **UI components:** 3:1

### Motion

Respect user preferences:

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## Dark Mode

### Switching Strategy

1. **System preference** (default)
2. **Manual toggle** (user override)
3. **Persistent** (localStorage)

### Implementation

```tsx
import { useTheme } from "next-themes"

function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  return (
    <button onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
      Toggle theme
    </button>
  )
}
```

### Dark Mode Colors

See Color System > Dark Mode Colors section above.

---

## Design Tokens (CSS Variables)

All design tokens are defined as CSS custom properties in `app/globals.css`:

```css
:root {
  /* Colors */
  --background: 0 0% 100%;
  --foreground: 222 84% 4.9%;
  /* ... all color tokens */

  /* Typography */
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", ...;
  --font-mono: ui-monospace, SFMono-Regular, ...;

  /* Spacing - inherits from Tailwind */
  /* Borders */
  --radius: 0.5rem;

  /* Shadows - inherits from Tailwind */
  /* Animation - inherits from Tailwind */
}
```

---

## Implementation Checklist

### Setup

- [ ] Install Tailwind CSS
- [ ] Configure shadcn/ui
- [ ] Set up CSS variables in globals.css
- [ ] Configure dark mode (next-themes)
- [ ] Set up Tailwind config with design tokens
- [ ] Install Lucide React for icons

### Components

- [ ] Create all foundation components (Week 4)
- [ ] Implement dark mode for all components
- [ ] Add focus states for accessibility
- [ ] Test color contrast ratios
- [ ] Create Storybook stories
- [ ] Write component documentation

### Testing

- [ ] Visual regression tests (Chromatic)
- [ ] Accessibility audits (aXe, Lighthouse)
- [ ] Cross-browser testing
- [ ] Responsive testing (mobile, tablet, desktop)
- [ ] Dark mode testing

---

## Usage Guidelines

### Do's ✅

- Use semantic color tokens (success, warning, error)
- Maintain consistent spacing (4px grid)
- Use elevation (shadows) to show hierarchy
- Respect user's color scheme preference
- Test with screen readers
- Provide keyboard navigation
- Use appropriate heading levels (h1-h6)

### Don'ts ❌

- Don't hardcode colors (use CSS variables)
- Don't use arbitrary spacing values
- Don't forget focus states
- Don't ignore color contrast
- Don't use color alone to convey information
- Don't animate too much (distraction)
- Don't skip heading levels

---

## Resources

### Tools

- [Coolors](https://coolors.co) - Color palette generator
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/) - WCAG compliance
- [Tailwind CSS](https://tailwindcss.com) - Utility framework
- [shadcn/ui](https://ui.shadcn.com) - Component library
- [Radix UI](https://radix-ui.com) - Accessible primitives

### References

- [Tailwind CSS Color Palette](https://tailwindcss.com/docs/customizing-colors)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Material Design](https://m3.material.io) - Design inspiration
- [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/)

---

**Status:** ✅ Design System Complete
**Next Steps:** Begin Week 4 component implementation

---

**Created:** 2025-11-27 (Week 3, Session W3-E1-05)
**Engineer:** Engineer 1 (Frontend Specialist)
**Version:** 1.0.0
