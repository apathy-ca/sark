# SARK Frontend

Modern React + TypeScript frontend for SARK (Security Audit and Resource Kontroler).

## Quick Start

```bash
npm install && npm run dev
```

## Features

- **Full UI Suite**: Servers, Policies, Audit Logs, API Keys
- **Real-time Updates**: WebSocket integration
- **Dark Mode**: System/Light/Dark themes
- **Keyboard Shortcuts**: Press `Ctrl+/` to see all
- **Data Export**: CSV/JSON export for all tables
- **Code Editor**: Syntax-highlighted Rego policy editor

## Tech Stack

React 18 • TypeScript • Vite • Tailwind CSS • TanStack Query • Zustand • React Router

## Documentation

- [API Reference](../docs/ui/API_REFERENCE.md)
- [Implementation Roadmap](../docs/ui/IMPLEMENTATION_ROADMAP.md)
- [Keyboard Shortcuts](#keyboard-shortcuts)

## Keyboard Shortcuts

- `g+d/s/p/a/k` - Navigate to Dashboard/Servers/Policies/Audit/Keys
- `Ctrl+/` - Show all shortcuts
- `t` - Toggle theme
- `Esc` - Close modals

## Environment

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Build

```bash
npm run build  # Output: dist/
```
