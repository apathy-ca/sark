# SARK Frontend

Modern React + TypeScript web interface for SARK (Security Audit and Resource Kontroler).

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **React Router** - Client-side routing
- **TanStack Query** - Server state management
- **Zustand** - Global client state
- **Tailwind CSS** - Utility-first styling
- **shadcn/ui** - Component design system
- **Axios** - HTTP client
- **date-fns** - Date utilities

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- SARK backend running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env

# Start development server
npm run dev
```

The app will be available at `http://localhost:3000`

## Project Structure

```
frontend/
├── src/
│   ├── components/         # Reusable UI components
│   ├── pages/             # Page components (route handlers)
│   ├── layouts/           # Layout components
│   ├── hooks/             # Custom React hooks
│   ├── services/          # API client
│   ├── stores/            # Zustand state stores
│   ├── types/             # TypeScript types
│   ├── utils/             # Utility functions
│   └── features/          # Feature modules
├── public/                # Static assets
├── .env.example           # Environment template
└── package.json           # Dependencies
```

## Development

```bash
# Start dev server
npm run dev

# Build for production
npm run build

# Preview build
npm run preview
```

## Related Documentation

- **[API Reference](../docs/ui/API_REFERENCE.md)** - Complete API docs
- **[SARK Backend](../README.md)** - Backend setup
- **[Tutorial 1](../tutorials/01-basic-setup/README.md)** - Getting started
