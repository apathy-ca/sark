# QA Engineer Tasks

**Your Role:** Quality Assurance
**Total Tasks:** 3 tasks over 8 weeks
**Estimated Effort:** ~7 days

You're the guardian of quality - ensure everything works flawlessly.

---

## Your Tasks

### ✅ T1.4 - Documentation QA & Integration
**Week:** 1
**Duration:** 1 day
**Priority:** P1 (High - ensures documentation quality)

**What you're testing:**
All new documentation created in Week 1 by the Documenter and engineers.

**Deliverables:**
1. **Documentation Review Checklist:**
   - [ ] MCP definition is clear and accurate
   - [ ] No assumptions of prior MCP knowledge
   - [ ] Examples are valid and tested
   - [ ] Links work (no 404s)
   - [ ] Cross-references are correct
   - [ ] Grammar and spelling checked
   - [ ] Code blocks have proper syntax highlighting
   - [ ] Images/diagrams render correctly
   - [ ] Consistent formatting

2. **Test All Code Examples:**
   - `examples/mcp-servers/minimal-server.json`
   - `examples/mcp-servers/database-server.json`
   - `examples/mcp-servers/api-server.json`
   - Verify they work with the API:
     ```bash
     curl -X POST http://localhost:8000/api/v1/servers \
       -d @examples/mcp-servers/minimal-server.json
     ```

3. **Create Issues List:**
   - Document any problems found
   - Rate by severity (P0, P1, P2)
   - Assign back to Documenter or engineers
   - Track fixes

4. **Final Approval:**
   - Once all issues fixed, sign off
   - Mark documentation as ready for publication

**Acceptance Criteria:**
- [ ] Zero broken links
- [ ] All examples work
- [ ] Documentation flows logically
- [ ] No spelling/grammar errors
- [ ] Ready for external users

**Dependencies:**
- T1.1 (Documenter)
- T1.2 (Engineer 3)
- T1.3 (Engineer 2)

**Claude Code Prompt:**
```
Review SARK documentation for Week 1 release.

Tasks:
1. Check README.md MCP definition section
2. Review docs/MCP_INTRODUCTION.md
3. Test all examples in examples/mcp-servers/
4. Verify all links work
5. Check diagrams render correctly
6. Create issue list of problems found

Be thorough - this is what new users will see first.
```

---

### ✅ T7.3 - Performance Optimization & Testing
**Week:** 7
**Duration:** 2-3 days
**Priority:** P0 (Critical - must pass before launch)

**What you're testing:**
Complete UI with focus on performance, cross-browser, and accessibility.

**Deliverables:**
1. **Performance Audit:**

   **Lighthouse Testing:**
   - Run on all major pages:
     - Dashboard
     - Servers list
     - Server detail
     - Policy editor
     - Audit logs
     - Settings
   - Target scores:
     - Performance: >85
     - Accessibility: >90
     - Best Practices: >90
     - SEO: >80

   **Bundle Size Analysis:**
   ```bash
   npm run build
   # Analyze bundle size
   npx vite-bundle-visualizer

   # Check gzipped size
   du -h dist/assets/*.js | sort -h
   ```
   - Target: Main bundle <500KB gzipped
   - Identify large dependencies
   - Recommend code splitting if needed

   **Loading Performance:**
   - Measure Time to First Byte (TTFB)
   - Measure First Contentful Paint (FCP)
   - Measure Largest Contentful Paint (LCP)
   - Measure Time to Interactive (TTI)
   - Target: LCP <2.5s, TTI <3.5s

2. **E2E Test Suite with Playwright:**

   **Setup:**
   ```bash
   npm install -D @playwright/test
   npx playwright install
   ```

   **Critical User Flows to Test:**

   `tests/e2e/auth.spec.ts`:
   ```typescript
   test('user can log in', async ({ page }) => {
     await page.goto('http://localhost:3000')
     await page.click('text=Login')
     // ... OIDC flow
     await expect(page).toHaveURL('/dashboard')
   })
   ```

   `tests/e2e/servers.spec.ts`:
   ```typescript
   test('user can register server', async ({ page }) => {
     await page.goto('/servers')
     await page.click('text=Register Server')
     await page.fill('[name="name"]', 'Test Server')
     await page.fill('[name="endpoint"]', 'http://localhost:9000')
     await page.click('text=Submit')
     await expect(page.locator('text=Server registered')).toBeVisible()
   })

   test('user can view server details', async ({ page }) => {
     await page.goto('/servers')
     await page.click('text=Test Server')
     await expect(page).toHaveURL(/\/servers\/.*/)
     await expect(page.locator('h1')).toContainText('Test Server')
   })

   test('user can delete server', async ({ page }) => {
     await page.goto('/servers')
     await page.click('[aria-label="Delete Test Server"]')
     await page.click('text=Confirm')
     await expect(page.locator('text=Test Server')).not.toBeVisible()
   })
   ```

   `tests/e2e/policies.spec.ts`:
   ```typescript
   test('user can edit policy', async ({ page }) => {
     await page.goto('/policies')
     await page.click('text=rbac.rego')
     await page.fill('.monaco-editor textarea', 'package mcp\nallow { true }')
     await page.click('text=Save')
     await expect(page.locator('text=Policy saved')).toBeVisible()
   })

   test('user can test policy', async ({ page }) => {
     await page.goto('/policies/editor')
     await page.click('text=Test Policy')
     await page.fill('[name="testInput"]', '{"user": {"role": "admin"}}')
     await page.click('text=Run Test')
     await expect(page.locator('text=Allow')).toBeVisible()
   })
   ```

   `tests/e2e/audit.spec.ts`:
   ```typescript
   test('user can filter audit logs', async ({ page }) => {
     await page.goto('/audit')
     await page.selectOption('[name="eventType"]', 'authorization_denied')
     await page.click('text=Apply Filters')
     // Verify all results are authorization_denied events
   })

   test('user can export audit logs', async ({ page }) => {
     await page.goto('/audit')
     const [download] = await Promise.all([
       page.waitForEvent('download'),
       page.click('text=Export CSV')
     ])
     expect(download.suggestedFilename()).toMatch(/audit-logs.*\.csv/)
   })
   ```

   **Minimum Coverage:**
   - [ ] Authentication flow
   - [ ] Server CRUD operations
   - [ ] Policy viewing and editing
   - [ ] Audit log filtering and export
   - [ ] Settings updates
   - [ ] API key management

3. **Cross-Browser Testing:**

   Test on:
   - [ ] Chrome (latest)
   - [ ] Firefox (latest)
   - [ ] Safari (latest)
   - [ ] Edge (latest)

   Use Playwright for automated cross-browser tests:
   ```typescript
   // playwright.config.ts
   export default {
     projects: [
       { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
       { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
       { name: 'webkit', use: { ...devices['Desktop Safari'] } },
     ],
   }
   ```

4. **Mobile Testing:**
   - [ ] iOS Safari (iPhone 12/13/14)
   - [ ] Android Chrome (Pixel/Samsung)

   Playwright mobile emulation:
   ```typescript
   test.use({ ...devices['iPhone 12'] })
   ```

5. **Performance Testing:**

   **Load Testing:**
   - Test API endpoints under load
   - Simulate 100 concurrent users
   - Measure response times
   - Identify bottlenecks

   Use k6 or Apache Bench:
   ```bash
   # Test dashboard API
   ab -n 1000 -c 100 http://localhost:8000/api/v1/ui/dashboard/metrics

   # Monitor response times
   # p50, p95, p99 should be within targets
   ```

6. **Bug Tracking:**
   - Create issues for all bugs found
   - Severity levels:
     - **P0:** Blocker (app unusable)
     - **P1:** Critical (major feature broken)
     - **P2:** Important (minor feature broken)
     - **P3:** Nice to fix (cosmetic)
   - Track fix status
   - Retest after fixes

**Acceptance Criteria:**
- [ ] Lighthouse performance >85 on all pages
- [ ] Bundle size <500KB gzipped
- [ ] E2E tests cover critical flows
- [ ] Works in Chrome, Firefox, Safari, Edge
- [ ] Mobile-friendly on iOS and Android
- [ ] All P0/P1 bugs fixed before launch
- [ ] Load testing passes (p95 <100ms)

**Dependencies:**
- Week 1-6 (UI must be feature-complete)

**Claude Code Prompt:**
```
Comprehensive QA testing for SARK UI.

Tasks:
1. Run Lighthouse audit on all pages
2. Analyze bundle size and identify optimizations
3. Create Playwright E2E test suite (auth, servers, policies, audit)
4. Test on Chrome, Firefox, Safari, Edge
5. Test on mobile (iOS, Android)
6. Load test API endpoints
7. Create bug report with all issues found

Target: Production-ready quality.
```

---

### ✅ T8.2 - Final Testing & Launch QA
**Week:** 8
**Duration:** 2-3 days
**Priority:** P0 (Critical - launch gate)

**What you're testing:**
Complete integrated system ready for production deployment.

**Deliverables:**
1. **Full Integration Testing:**

   **Docker Compose Testing:**
   ```bash
   # Test each profile
   docker compose --profile minimal up -d
   # Verify all services healthy
   docker compose ps
   # Test basic functionality
   curl http://localhost:8000/health
   curl http://localhost:3000/health

   docker compose down -v
   docker compose --profile standard up -d
   # Repeat verification

   docker compose down -v
   docker compose --profile full up -d
   # Repeat verification
   ```

   **Kubernetes Testing:**
   ```bash
   # Deploy to test cluster
   kubectl apply -k k8s/overlays/staging

   # Verify all pods running
   kubectl get pods -n sark-system

   # Check health
   kubectl exec -it deployment/sark-api -- curl localhost:8000/health

   # Test UI
   kubectl port-forward svc/sark-ui 3000:80
   open http://localhost:3000
   ```

   **Helm Testing:**
   ```bash
   helm install sark ./helm/sark --namespace sark-test --create-namespace
   helm test sark -n sark-test
   helm delete sark -n sark-test
   ```

2. **Security Testing (OWASP Top 10):**

   **Use OWASP ZAP or Burp Suite:**

   **Tests:**
   - [ ] **A01: Broken Access Control**
     - Try accessing API without auth
     - Try accessing other users' resources
     - Try privilege escalation

   - [ ] **A02: Cryptographic Failures**
     - Verify HTTPS enforced
     - Check for sensitive data in logs
     - Verify passwords hashed

   - [ ] **A03: Injection**
     - Test SQL injection in forms
     - Test XSS in inputs
     - Test command injection

   - [ ] **A04: Insecure Design**
     - Review authentication flow
     - Check for rate limiting
     - Verify CSRF protection

   - [ ] **A05: Security Misconfiguration**
     - Check for default credentials
     - Verify debug mode off in production
     - Check HTTP headers (CSP, HSTS, etc.)

   - [ ] **A06: Vulnerable Components**
     - Run `npm audit`
     - Run `safety check` (Python)
     - Verify no high/critical vulnerabilities

   - [ ] **A07: Authentication Failures**
     - Test brute force protection
     - Test session fixation
     - Verify MFA if enabled

   - [ ] **A08: Software and Data Integrity**
     - Verify CI/CD pipeline security
     - Check code signing
     - Verify dependency integrity

   - [ ] **A09: Logging Failures**
     - Verify audit logging
     - Check for PII in logs
     - Test log tampering protection

   - [ ] **A10: Server-Side Request Forgery**
     - Test SSRF in server registration
     - Verify URL validation

   **Run Automated Security Scans:**
   ```bash
   # Dependency scanning
   npm audit --audit-level=high
   pip-audit

   # Container scanning
   docker scan sark/api:latest
   docker scan sark/ui:latest

   # SAST
   semgrep --config auto src/
   ```

3. **Accessibility Testing:**

   **Automated:**
   ```bash
   # Run axe-core
   npx axe http://localhost:3000 --exit
   ```

   **Manual:**
   - [ ] Keyboard-only navigation
   - [ ] Screen reader test (NVDA/JAWS)
   - [ ] Color contrast verification
   - [ ] Focus indicators visible
   - [ ] ARIA labels correct

4. **Final Checklist:**

   **Functionality:**
   - [ ] All features work end-to-end
   - [ ] No console errors
   - [ ] No network errors (except expected)
   - [ ] Forms validate correctly
   - [ ] Error messages are helpful
   - [ ] Success messages display
   - [ ] Loading states show

   **Performance:**
   - [ ] Lighthouse score >85
   - [ ] Bundle size <500KB
   - [ ] Page loads <3s (3G)
   - [ ] API responses <100ms (p95)

   **Security:**
   - [ ] 0 high/critical vulnerabilities
   - [ ] HTTPS enforced
   - [ ] Auth works correctly
   - [ ] CSRF protection enabled
   - [ ] Rate limiting works

   **Deployment:**
   - [ ] Docker Compose works
   - [ ] Kubernetes deploys successfully
   - [ ] Helm chart installs correctly
   - [ ] Health checks pass
   - [ ] Monitoring works

   **Documentation:**
   - [ ] Deployment guide accurate
   - [ ] Troubleshooting guide helpful
   - [ ] API docs complete
   - [ ] UI guide clear

5. **Sign-Off Document:**

   Create `QA_SIGN_OFF.md`:
   ```markdown
   # SARK v1.0 QA Sign-Off

   ## Test Summary
   - Total tests run: X
   - Passed: Y
   - Failed: Z
   - Bugs found: N
   - P0/P1 bugs: 0

   ## Test Coverage
   - [ ] Integration testing
   - [ ] Security testing
   - [ ] Accessibility testing
   - [ ] Performance testing
   - [ ] Cross-browser testing
   - [ ] Mobile testing

   ## Outstanding Issues
   - None (or list P2/P3 issues for post-launch)

   ## Recommendation
   ✅ APPROVED FOR PRODUCTION LAUNCH

   QA Engineer: [Name]
   Date: [Date]
   Signature: [Signature]
   ```

**Acceptance Criteria:**
- [ ] All P0/P1 bugs fixed
- [ ] Security scan passes
- [ ] Integration tests pass
- [ ] Accessibility compliant
- [ ] Performance targets met
- [ ] QA sign-off document complete
- [ ] **READY FOR LAUNCH** 🚀

**Dependencies:**
- All Week 1-7 tasks complete
- T8.1 (Engineer 4 integration complete)

**Claude Code Prompt:**
```
Final QA testing for SARK v1.0 launch.

Comprehensive testing:
1. Full integration testing (Docker, K8s, Helm)
2. Security testing (OWASP Top 10)
3. Accessibility testing (WCAG 2.1 AA)
4. Performance verification
5. Cross-browser and mobile testing
6. Create QA sign-off document

This is the launch gate - be thorough!
```

---

## Your Timeline

| Week | Task | Duration | Focus |
|------|------|----------|-------|
| **1** | T1.4 | 1 day | Documentation QA |
| **2-6** | — | — | Ad-hoc testing, bug reports |
| **7** | T7.3 | 2-3 days | Performance & E2E testing |
| **8** | T8.2 | 2-3 days | Final testing & sign-off |

## Your Tools

### Testing Tools
- **Playwright** - E2E testing
- **Lighthouse** - Performance auditing
- **axe-core** - Accessibility testing
- **OWASP ZAP** - Security testing
- **k6** - Load testing

### Browser Tools
- Chrome DevTools
- Firefox Developer Tools
- Safari Web Inspector
- Responsively App (mobile testing)

### Commands
```bash
# E2E tests
npx playwright test

# Lighthouse
npx lighthouse http://localhost:3000 --view

# Accessibility
npx axe http://localhost:3000

# Security scan
npm audit
docker scan sark/ui:latest

# Load test
k6 run load-test.js
```

## Tips for Success

### Test Early, Test Often
- Don't wait until Week 7 to start testing
- Report bugs as you find them
- Retest after fixes

### Be Thorough
- Test happy paths AND edge cases
- Test error scenarios
- Test with bad/malicious input
- Test on different browsers and devices

### Document Everything
- Screenshot bugs
- Provide reproduction steps
- Include environment details
- Rate severity accurately

### Work with Engineers
- Pair on complex bugs
- Help them reproduce issues
- Verify fixes promptly
- Be constructive in feedback

---

**You're the last line of defense - keep quality high!** ✅
