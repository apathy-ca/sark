# Frontend Testing & Quality Assurance

## Testing Checklist

### Functional Testing

#### Authentication
- [ ] Login with LDAP credentials
- [ ] Token refresh on expiration
- [ ] Logout clears session
- [ ] Redirect to login when unauthenticated
- [ ] Remember me functionality

#### Servers Management
- [ ] List all servers with pagination
- [ ] Search and filter servers
- [ ] Register new server (all transport types)
- [ ] View server details
- [ ] Edit server configuration
- [ ] Delete server with confirmation

#### Policies
- [ ] List all policies
- [ ] View policy content with syntax highlighting
- [ ] Upload new policy
- [ ] Edit existing policy
- [ ] Save policy changes
- [ ] Delete policy with confirmation

#### Audit Logs
- [ ] View audit logs with time filters
- [ ] Filter by event type, user, server
- [ ] Export logs to CSV
- [ ] Export logs to JSON
- [ ] Real-time updates via WebSocket
- [ ] Toggle real-time mode on/off

#### API Keys
- [ ] List all API keys
- [ ] Create new API key
- [ ] Copy key to clipboard (shown once)
- [ ] Revoke API key
- [ ] View key expiration status

### UI/UX Testing

#### Theme & Appearance
- [ ] Light mode renders correctly
- [ ] Dark mode renders correctly
- [ ] System theme detection works
- [ ] Theme persists across sessions
- [ ] Theme toggle cycles through all modes

#### Responsive Design
- [ ] Mobile (320px-480px)
- [ ] Tablet (768px-1024px)
- [ ] Desktop (1024px+)
- [ ] Navigation menu adapts to screen size

#### Keyboard Navigation
- [ ] `g+d` navigates to Dashboard
- [ ] `g+s` navigates to Servers
- [ ] `g+p` navigates to Policies
- [ ] `g+a` navigates to Audit
- [ ] `g+k` navigates to API Keys
- [ ] `Ctrl+/` shows keyboard shortcuts
- [ ] `Esc` closes modals

#### Loading States
- [ ] Tables show skeletons while loading
- [ ] Forms show skeletons while loading
- [ ] Spinners appear for async actions
- [ ] Loading indicators are accessible

#### Error Handling
- [ ] Network errors show user-friendly messages
- [ ] Form validation errors are clear
- [ ] API errors display toast notifications
- [ ] Retry mechanisms work correctly

### Performance Testing

#### Bundle Size
```bash
npm run build
ls -lh dist/assets/*.js
# Target: < 500KB gzipped
```

#### Lighthouse Audit
```bash
npm run build && npm run preview
# Run Lighthouse in Chrome DevTools
# Targets: Performance > 90, Accessibility > 95
```

#### Load Testing
- [ ] Test with 100+ servers
- [ ] Test with 1000+ audit log entries
- [ ] Test with 50+ policies
- [ ] Pagination works smoothly
- [ ] Search/filter remains responsive

### Browser Compatibility

- [ ] Chrome (latest 2 versions)
- [ ] Firefox (latest 2 versions)
- [ ] Safari (latest 2 versions)
- [ ] Edge (latest 2 versions)

### Accessibility

- [ ] All images have alt text
- [ ] Forms have proper labels
- [ ] Keyboard navigation works throughout
- [ ] Screen reader compatible
- [ ] Color contrast meets WCAG AA standards

## Known Issues & Limitations

### Current Implementation

1. **WebSocket Reconnection**: Limited to 5 attempts
   - **Impact**: Real-time updates may stop after multiple disconnects
   - **Workaround**: Refresh page to reconnect
   - **Fix**: Implement exponential backoff with unlimited retries

2. **Search Debouncing**: 300ms delay
   - **Impact**: Very fast typing may feel laggy
   - **Workaround**: None needed
   - **Fix**: Consider reducing to 200ms

3. **Bundle Size**: ~400KB gzipped
   - **Impact**: Slightly longer initial load
   - **Optimization**: Code splitting already implemented
   - **Future**: Consider lazy loading routes

### Browser-Specific

- **Safari < 14**: May have CSS custom property issues
  - **Fix**: Add CSS fallbacks

- **Firefox**: WebSocket may require explicit protocol
  - **Fix**: Set ws:// or wss:// explicitly

## Performance Benchmarks

### Development Build
- First Load: ~2-3s
- Subsequent: ~500ms (cached)

### Production Build
- First Load: ~1-1.5s
- Subsequent: ~200ms (cached)

### Bundle Analysis

```bash
npm run build -- --mode=analyze
# Opens bundle analyzer
```

## CI/CD Integration

```yaml
# Example GitHub Actions
name: Frontend Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-node@v2
      - run: npm ci
      - run: npm run build
      - run: npm run test # when tests are added
```

## Manual Testing Scripts

```bash
# Build and serve locally
npm run build && npm run preview

# Check bundle size
npm run build && du -sh dist

# Test API connectivity
curl -X POST http://localhost:3000/api/v1/auth/login/ldap \
  -H "Content-Type: application/json" \
  -d '{"username":"john.doe","password":"password"}'
```

## Recommended Tools

- **Lighthouse**: Performance auditing
- **React DevTools**: Component debugging
- **Redux DevTools**: State inspection (Zustand compatible)
- **Axe DevTools**: Accessibility testing
- **BrowserStack**: Cross-browser testing
