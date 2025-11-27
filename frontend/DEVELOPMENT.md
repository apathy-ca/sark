# SARK Frontend - Development Guide

This guide covers local development setup for the SARK frontend application.

---

## Quick Start

### Option 1: Docker Development (Recommended)

```bash
# From the project root directory
docker compose -f docker-compose.dev.yml up

# Or with OPA for policy testing
docker compose -f docker-compose.dev.yml --profile with-opa up
```

**Access:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- OPA (optional): http://localhost:8181

**Features:**
- ✅ Hot module replacement (HMR)
- ✅ Automatic reload on file changes
- ✅ Source maps for debugging
- ✅ Full backend connectivity
- ✅ Isolated development environment

### Option 2: Local Development (Without Docker)

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env

# Start dev server
npm run dev
```

**Requirements:**
- Node.js 18+
- Backend API running separately

---

## Development Workflow

### Making Changes

1. **Edit Code:**
   ```bash
   # Edit files in frontend/src/
   vi frontend/src/pages/DashboardPage.tsx
   ```

2. **See Changes Instantly:**
   - Vite HMR automatically updates the browser
   - No manual refresh needed
   - Preserves component state when possible

3. **Check Terminal:**
   ```bash
   # Watch for errors in the terminal
   docker compose -f docker-compose.dev.yml logs -f frontend-dev
   ```

### Adding New Dependencies

```bash
# Stop the container
docker compose -f docker-compose.dev.yml down

# Add dependency
cd frontend
npm install <package-name>

# Rebuild and start
docker compose -f docker-compose.dev.yml up --build
```

### Running Tests

```bash
# Run tests
docker compose -f docker-compose.dev.yml exec frontend-dev npm test

# Run tests with coverage
docker compose -f docker-compose.dev.yml exec frontend-dev npm run test:coverage

# Run linting
docker compose -f docker-compose.dev.yml exec frontend-dev npm run lint
```

### Type Checking

```bash
# Type check
docker compose -f docker-compose.dev.yml exec frontend-dev npm run type-check

# Watch mode
docker compose -f docker-compose.dev.yml exec frontend-dev npm run type-check:watch
```

---

## Project Structure

```
frontend/
├── src/
│   ├── assets/          # Static assets (images, fonts)
│   ├── components/      # Reusable UI components
│   ├── hooks/           # Custom React hooks
│   ├── layouts/         # Page layouts
│   ├── pages/           # Page components
│   ├── services/        # API services
│   ├── stores/          # Zustand stores
│   ├── types/           # TypeScript types
│   ├── utils/           # Utility functions
│   ├── App.tsx          # Main app component
│   ├── Router.tsx       # Route definitions
│   └── main.tsx         # Entry point
├── public/              # Public static files
├── Dockerfile           # Production build
├── Dockerfile.dev       # Development build
├── vite.config.ts       # Vite configuration
├── tsconfig.json        # TypeScript config
├── tailwind.config.js   # Tailwind CSS config
└── package.json         # Dependencies
```

---

## Configuration

### Environment Variables

Create `frontend/.env` file:

```env
# API Configuration
VITE_API_URL=http://localhost:8000

# Feature Flags
VITE_ENABLE_DEBUG=true
VITE_ENABLE_MOCK_DATA=false

# Optional: Authentication
VITE_OIDC_AUTHORITY=https://your-oidc-provider.com
VITE_OIDC_CLIENT_ID=your-client-id
```

**Available Variables:**
- `VITE_API_URL` - Backend API URL (default: http://localhost:8000)
- `VITE_ENABLE_DEBUG` - Enable debug logging
- `VITE_ENABLE_MOCK_DATA` - Use mock data instead of API
- `VITE_OIDC_AUTHORITY` - OIDC provider URL
- `VITE_OIDC_CLIENT_ID` - OIDC client ID

### Vite Configuration

Edit `frontend/vite.config.ts` for:
- Build settings
- Proxy configuration
- Plugin configuration
- Path aliases

### Tailwind Configuration

Edit `frontend/tailwind.config.js` for:
- Theme customization
- Color palette
- Typography
- Plugins

---

## Common Tasks

### Adding a New Page

1. **Create Page Component:**
   ```tsx
   // frontend/src/pages/NewPage.tsx
   export default function NewPage() {
     return (
       <div>
         <h1>New Page</h1>
       </div>
     );
   }
   ```

2. **Add Route:**
   ```tsx
   // frontend/src/Router.tsx
   import NewPage from './pages/NewPage';

   // Add to routes
   { path: '/new-page', element: <NewPage /> }
   ```

3. **Add Navigation:**
   ```tsx
   // Add to sidebar/navigation component
   <Link to="/new-page">New Page</Link>
   ```

### Creating a Component

1. **Create Component File:**
   ```tsx
   // frontend/src/components/MyComponent.tsx
   interface MyComponentProps {
     title: string;
   }

   export function MyComponent({ title }: MyComponentProps) {
     return <div>{title}</div>;
   }
   ```

2. **Export from Index:**
   ```tsx
   // frontend/src/components/index.ts
   export { MyComponent } from './MyComponent';
   ```

3. **Use Component:**
   ```tsx
   import { MyComponent } from '@/components';

   <MyComponent title="Hello" />
   ```

### Adding API Endpoint

1. **Define Type:**
   ```tsx
   // frontend/src/types/api.ts
   export interface Server {
     id: string;
     name: string;
     endpoint: string;
   }
   ```

2. **Add API Function:**
   ```tsx
   // frontend/src/services/api.ts
   export async function getServers(): Promise<Server[]> {
     const response = await fetch(`${API_URL}/api/v1/servers`);
     return response.json();
   }
   ```

3. **Use in Component:**
   ```tsx
   import { useQuery } from '@tanstack/react-query';
   import { getServers } from '@/services/api';

   const { data: servers } = useQuery({
     queryKey: ['servers'],
     queryFn: getServers,
   });
   ```

---

## Debugging

### Browser DevTools

1. **Open DevTools:** F12 or Right-click → Inspect
2. **Sources:** View source code with source maps
3. **Console:** Check for errors and warnings
4. **Network:** Monitor API requests
5. **React DevTools:** Install browser extension

### Vite DevTools

```bash
# View detailed build info
docker compose -f docker-compose.dev.yml logs frontend-dev

# Check Vite config
docker compose -f docker-compose.dev.yml exec frontend-dev cat vite.config.ts
```

### API Debugging

```bash
# View API logs
docker compose -f docker-compose.dev.yml logs -f app

# Make test API request
curl http://localhost:8000/api/v1/health

# View API docs
open http://localhost:8000/docs
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 5173
lsof -i :5173

# Kill process
kill -9 <PID>

# Or change port in docker-compose.dev.yml
ports:
  - "3000:5173"  # Use port 3000 instead
```

### Hot Reload Not Working

```bash
# Enable polling (already enabled in Dockerfile.dev)
CHOKIDAR_USEPOLLING=true

# Restart container
docker compose -f docker-compose.dev.yml restart frontend-dev

# Check file permissions
ls -la frontend/src/
```

### Module Not Found

```bash
# Clear cache
rm -rf frontend/node_modules
rm frontend/package-lock.json

# Reinstall
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up --build
```

### CORS Errors

```bash
# Check backend CORS settings
docker compose -f docker-compose.dev.yml logs app | grep CORS

# Verify ALLOWED_ORIGINS in docker-compose.dev.yml includes:
# http://localhost:5173
```

### TypeScript Errors

```bash
# Run type check
docker compose -f docker-compose.dev.yml exec frontend-dev npm run type-check

# Check tsconfig.json
docker compose -f docker-compose.dev.yml exec frontend-dev cat tsconfig.json
```

---

## Performance Tips

### Optimize HMR

1. **Keep Components Small:** Smaller components reload faster
2. **Use React.memo:** Prevent unnecessary re-renders
3. **Split Code:** Use dynamic imports for large components
4. **Disable Source Maps:** In production builds only

### Reduce Build Time

1. **Update Dependencies:** Keep Vite and plugins up-to-date
2. **Use SWC:** Consider switching from Babel to SWC
3. **Optimize Tailwind:** Purge unused styles
4. **Cache Dependencies:** Docker volumes for node_modules

---

## Best Practices

### Code Style

- **Use TypeScript:** Always type your code
- **Follow ESLint Rules:** Run `npm run lint` regularly
- **Format with Prettier:** Automatic formatting on save
- **Write Tests:** Test components and hooks

### Component Guidelines

- **One Component Per File:** Easier to navigate
- **Props Interface:** Always define prop types
- **Default Exports:** For page components
- **Named Exports:** For reusable components

### State Management

- **Local State First:** Use useState for component state
- **Zustand for Global:** Shared state across components
- **React Query for API:** Server state management
- **Context for Theme:** Theme and UI preferences

### Styling

- **Tailwind Utility Classes:** Primary styling method
- **CSS Modules:** For complex styles
- **Component Variants:** Use cva for variant management
- **Responsive Design:** Mobile-first approach

---

## Additional Resources

- [Vite Documentation](https://vitejs.dev/)
- [React Documentation](https://react.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [TanStack Query](https://tanstack.com/query/latest)
- [Zustand](https://github.com/pmndrs/zustand)

---

## Getting Help

**Issues:**
- Check logs: `docker compose -f docker-compose.dev.yml logs`
- View errors in browser console (F12)
- Read error messages carefully

**Questions:**
- Check this documentation
- Review code examples in `/examples`
- Ask in team chat
- Open GitHub issue

---

**Last Updated:** 2025-11-27
**Version:** 1.0
