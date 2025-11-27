# SARK UI Troubleshooting Guide

**Solutions to common UI issues and problems**

Version 1.0.0 | Last Updated: 2025-11-27

---

## Table of Contents

1. [Connection Issues](#connection-issues)
2. [Authentication Problems](#authentication-problems)
3. [Performance Issues](#performance-issues)
4. [Display & Rendering Issues](#display--rendering-issues)
5. [Browser Compatibility](#browser-compatibility)
6. [WebSocket Issues](#websocket-issues)
7. [Data Loading Problems](#data-loading-problems)
8. [Form Submission Errors](#form-submission-errors)
9. [Export Functionality](#export-functionality)
10. [Developer Tools](#developer-tools)

---

## Connection Issues

### Cannot Connect to SARK UI

**Symptoms:**
- Page doesn't load
- "Cannot reach server" error
- Infinite loading spinner

**Solutions:**

**1. Check Server Status**
```bash
# Verify backend is running
curl http://localhost:8000/health

# Expected: {"status": "healthy"}
```

**2. Verify URL**
- Development: `http://localhost:3000`
- Production: `https://sark.yourdomain.com`
- Check for typos in URL

**3. Check Docker Status (if using Docker)**
```bash
docker compose ps

# All services should show "healthy"
docker compose logs frontend
```

**4. Verify Network Connection**
- Check internet connectivity
- Verify VPN connection (if required)
- Check firewall rules
- Test from different network

**5. Browser Cache**
```
1. Hard refresh: Ctrl+Shift+R (Cmd+Shift+R on Mac)
2. Clear browser cache
3. Try incognito/private mode
```

### "Failed to Connect to Backend" Error

**Symptoms:**
- UI loads but shows connection error
- API requests fail
- Red connection indicator

**Solutions:**

**1. Verify Backend URL**

Check `.env.production`:
```env
VITE_API_BASE_URL=http://localhost:8000
```

Should match your backend URL.

**2. Check CORS Configuration**

Backend should allow frontend origin:
```python
# In backend CORS config
origins = [
    "http://localhost:3000",  # Development
    "https://sark.yourdomain.com"  # Production
]
```

**3. Verify Backend is Running**
```bash
curl http://localhost:8000/api/v1/health
```

**4. Check Network Tab**
- Open browser DevTools (F12)
- Go to Network tab
- Look for failed requests
- Check status codes and error messages

---

## Authentication Problems

### Cannot Log In

**Symptoms:**
- Login button doesn't work
- "Invalid credentials" error
- Redirect loop

**Solutions:**

**1. Verify Credentials**
- Check username spelling
- Verify password (watch for caps lock)
- Try resetting password (if LDAP)

**2. Check LDAP Configuration**
```bash
# Test LDAP connection from backend
docker compose exec sark-api python -c "
from sark.services.auth.providers.ldap import LDAPProvider
ldap = LDAPProvider()
result = ldap.authenticate('username', 'password')
print(result)
"
```

**3. Check Browser Console**
```
1. Open DevTools (F12)
2. Go to Console tab
3. Look for error messages
4. Share errors with support team
```

**4. Clear Cookies**
```
1. Open DevTools (F12)
2. Application tab (Chrome) or Storage tab (Firefox)
3. Cookies → Select your domain
4. Clear all cookies
5. Retry login
```

**5. Check Backend Logs**
```bash
docker compose logs sark-api | grep -i auth
```

### "Session Expired" - Frequent Logouts

**Symptoms:**
- Logged out after short time
- Frequent "please log in again" prompts
- Sessions don't persist

**Solutions:**

**1. Check Token Lifetime**

Backend configuration:
```python
# Should be 60 minutes for access token
ACCESS_TOKEN_LIFETIME = 3600  # seconds

# Should be 7 days for refresh token
REFRESH_TOKEN_LIFETIME = 604800  # seconds
```

**2. Check Clock Sync**
- Ensure server and client clocks are synchronized
- Time difference > 5 minutes can cause issues

**3. Browser Cookie Settings**
- Ensure cookies are enabled
- Check if "Block third-party cookies" is disabled
- Verify cookies aren't being cleared automatically

**4. Check Session Storage**
```javascript
// In browser console
localStorage.getItem('sark_access_token')
localStorage.getItem('sark_refresh_token')
```

### OIDC/OAuth Login Fails

**Symptoms:**
- Redirect to IdP fails
- "Invalid state" error
- "PKCE verification failed"

**Solutions:**

**1. Check Redirect URI**

Must match exactly in IdP configuration:
```
http://localhost:3000/auth/callback/oidc  (dev)
https://sark.yourdomain.com/auth/callback/oidc  (prod)
```

**2. Verify OIDC Configuration**
```env
# Backend .env
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret
OIDC_ISSUER_URL=https://accounts.google.com
OIDC_REDIRECT_URI=http://localhost:3000/auth/callback/oidc
```

**3. Check State Parameter**
- State parameter prevents CSRF
- Check browser console for state mismatch
- Try login again (new state generated)

**4. Test OIDC Discovery**
```bash
curl https://accounts.google.com/.well-known/openid-configuration
```

---

## Performance Issues

### Slow Page Load Times

**Symptoms:**
- Pages take > 5 seconds to load
- Spinning indicators for long time
- Unresponsive UI

**Solutions:**

**1. Check Network Speed**
```
1. Open DevTools (F12)
2. Network tab
3. Check "Disable cache"
4. Reload page
5. Look for slow requests (> 1s)
```

**2. Check Backend Performance**
```bash
# Check API response times
time curl http://localhost:8000/api/v1/servers

# Should be < 200ms
```

**3. Reduce Data Load**
- Use pagination (reduce page size)
- Apply filters before loading
- Export large datasets for offline analysis

**4. Clear Browser Cache**
```
1. Settings → Privacy → Clear browsing data
2. Select "Cached images and files"
3. Clear data
4. Reload page
```

**5. Disable Browser Extensions**
- Extensions can slow down rendering
- Try disabling ad blockers
- Test in incognito mode

**6. Check Database Performance**
```bash
# Check database query times
docker compose logs postgres | grep "duration:"
```

### UI Freezes or Becomes Unresponsive

**Symptoms:**
- Page stops responding to clicks
- Buttons don't work
- Browser shows "Page Unresponsive" warning

**Solutions:**

**1. Check Browser Memory**
```
1. Open Task Manager (Shift+Esc in Chrome)
2. Check memory usage
3. Close unused tabs
4. Restart browser if > 2GB
```

**2. Reduce Open Tabs**
- Close unused SARK tabs
- One tab per instance recommended

**3. Check Console for Errors**
```
1. DevTools (F12) → Console
2. Look for infinite loops
3. Look for memory leaks
4. Report to support if found
```

**4. Disable Real-Time Updates**
```javascript
// Temporarily disable WebSocket
// In browser console:
localStorage.setItem('disable_websocket', 'true')
// Reload page
```

**5. Check for Large Data Sets**
- Listing 10,000+ servers can be slow
- Use filters to reduce data
- Increase pagination page size

---

## Display & Rendering Issues

### Broken Layout / Misaligned Elements

**Symptoms:**
- Elements overlap
- Sidebar collapsed incorrectly
- Text cut off
- Buttons not visible

**Solutions:**

**1. Hard Refresh**
```
Ctrl+Shift+R (Windows/Linux)
Cmd+Shift+R (Mac)
```

**2. Clear Cache and Reload**
```bash
# Force rebuild (if using Docker)
docker compose build --no-cache frontend
docker compose up -d frontend
```

**3. Check Browser Zoom**
- Should be 100%
- Press Ctrl+0 to reset zoom

**4. Check Window Size**
- Minimum recommended: 1024x768
- Some features require wider screens

**5. Try Different Browser**
- Chrome/Edge (recommended)
- Firefox
- Safari (may have limitations)

### Dark Mode Not Working

**Symptoms:**
- Dark mode toggle doesn't work
- Theme doesn't persist
- Mixed light/dark elements

**Solutions:**

**1. Check Theme Setting**
```javascript
// In browser console
localStorage.getItem('theme')
// Should be: 'light', 'dark', or 'system'
```

**2. Force Theme**
```javascript
// Set dark mode
localStorage.setItem('theme', 'dark')
// Reload page
location.reload()
```

**3. Check System Preference**
- If set to "System", check OS dark mode
- Change OS theme to test

**4. Clear Local Storage**
```javascript
localStorage.removeItem('theme')
location.reload()
```

### Icons or Images Not Loading

**Symptoms:**
- Missing icons
- Broken image placeholders
- Blank buttons

**Solutions:**

**1. Check Network Tab**
```
1. DevTools → Network
2. Filter by "Img"
3. Look for 404 errors
```

**2. Check CDN Access**
```bash
# If using CDN for icons
curl https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/check.svg
```

**3. Clear Service Worker**
```javascript
// In browser console
navigator.serviceWorker.getRegistrations().then(function(registrations) {
  for(let registration of registrations) {
    registration.unregister();
  }
});
location.reload();
```

---

## Browser Compatibility

### UI Doesn't Work in Older Browsers

**Symptoms:**
- Blank page
- "Browser not supported" message
- Features don't work

**Supported Browsers:**
- Chrome 90+
- Edge 90+
- Firefox 88+
- Safari 14+

**Solutions:**

**1. Update Browser**
- Check browser version
- Update to latest version
- Restart browser after update

**2. Enable JavaScript**
```
Chrome: Settings → Privacy and Security → Site Settings → JavaScript → Allowed
Firefox: about:config → javascript.enabled → true
```

**3. Check for Ad Blockers**
- Disable ad blocker for SARK domain
- Add to whitelist

**4. Try Different Browser**
- Chrome (recommended)
- Edge (Chromium-based)

### Safari-Specific Issues

**Common Safari Issues:**

**1. WebSocket Connection Fails**
```javascript
// Check if WebSockets are supported
if (typeof WebSocket === 'undefined') {
  console.error('WebSocket not supported');
}
```

**2. Local Storage Issues**
- Check Safari → Preferences → Privacy
- Disable "Prevent cross-site tracking" for SARK domain

**3. Date/Time Display Issues**
- Safari has stricter date parsing
- Report specific date format issues

---

## WebSocket Issues

### Real-Time Updates Not Working

**Symptoms:**
- Page doesn't auto-refresh
- Manual refresh required
- Red WebSocket indicator

**Solutions:**

**1. Check WebSocket Connection**
```javascript
// In browser console
window.wsConnection
// Should show WebSocket object if connected
```

**2. Verify Backend WebSocket Support**
```bash
# Check if WebSocket endpoint is available
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  http://localhost:8000/ws
```

**3. Check Firewall/Proxy**
- Corporate firewalls may block WebSockets
- Try disabling VPN temporarily
- Contact network admin if blocked

**4. Fallback to Polling**
```javascript
// Disable WebSocket (uses polling instead)
localStorage.setItem('disable_websocket', 'true')
location.reload()
```

**5. Check WebSocket URL**
```env
# .env.production
VITE_WS_URL=ws://localhost:8000/ws  # Development
VITE_WS_URL=wss://sark.yourdomain.com/ws  # Production (secure)
```

### "WebSocket Connection Failed" Error

**Solutions:**

**1. Check Console for Errors**
```
DevTools → Console
Look for: "WebSocket connection to 'ws://...' failed"
```

**2. Verify HTTPS/WSS**
```
HTTP site → ws://
HTTPS site → wss:// (secure WebSocket)
```

**3. Check CORS**
- WebSocket must allow origin
- Backend configuration issue

**4. Test WebSocket Manually**
```javascript
// In browser console
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onopen = () => console.log('Connected!');
ws.onerror = (error) => console.error('Error:', error);
```

---

## Data Loading Problems

### "No Data" Despite Having Data

**Symptoms:**
- Empty list pages
- "No servers found" (but servers exist)
- Filters show 0 results

**Solutions:**

**1. Check Filters**
- Clear all filters
- Reset search
- Try different filter combinations

**2. Check API Response**
```
DevTools → Network → XHR
Click on request → Preview tab
Verify data is returned
```

**3. Refresh Page**
```
Ctrl+R (soft refresh)
Ctrl+Shift+R (hard refresh)
```

**4. Check Backend Data**
```bash
# Query backend directly
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/servers
```

**5. Check Pagination**
- Might be on wrong page
- Reset to page 1
- Check total count

### Infinite Loading Spinners

**Symptoms:**
- Loading spinner never stops
- Page stuck in loading state
- No error messages

**Solutions:**

**1. Check Network Tab**
```
DevTools → Network
Look for:
- Failed requests (red)
- Pending requests (gray)
- Slow requests (> 30s)
```

**2. Check Console for Errors**
```javascript
// Look for unhandled errors
DevTools → Console
```

**3. Force Reload**
```
Ctrl+Shift+R (hard refresh)
```

**4. Check Backend Health**
```bash
curl http://localhost:8000/health
```

**5. Check for Rate Limiting**
```bash
# Look for 429 status codes
docker compose logs sark-api | grep 429
```

---

## Form Submission Errors

### "Validation Error" on Form Submit

**Symptoms:**
- Form won't submit
- Red error messages
- "This field is required"

**Solutions:**

**1. Check Required Fields**
- All fields with asterisk (*) are required
- Fill in all required fields

**2. Check Field Formats**
- URL: Must start with http:// or https://
- Email: Must be valid email format
- Numbers: No letters allowed

**3. Check Error Messages**
- Read specific error messages
- Fix indicated issues
- Try submitting again

**4. Example Validation Rules**
```
Server Name:
- 3-100 characters
- Letters, numbers, hyphens, underscores
- No spaces

URL:
- Valid HTTP/HTTPS URL
- Must be reachable
- Format: https://example.com

Tags:
- Comma-separated
- Max 10 tags
- Each tag max 30 characters
```

### Form Data Not Saving

**Symptoms:**
- Form submission appears successful
- Data not updated
- Changes don't persist

**Solutions:**

**1. Check Success Message**
- Look for success toast/notification
- Verify "saved successfully" message

**2. Check Network Response**
```
DevTools → Network → XHR
Find POST/PUT request
Check response status (should be 200 or 201)
```

**3. Refresh Page**
- Hard refresh to see latest data
- Check if changes persisted

**4. Check Backend Logs**
```bash
docker compose logs sark-api | tail -100
```

**5. Verify Permissions**
- Check if you have write access
- Some fields may be read-only
- Contact admin if permission denied

---

## Export Functionality

### CSV/JSON Export Not Working

**Symptoms:**
- Export button doesn't work
- No file downloads
- Empty file downloads

**Solutions:**

**1. Check Browser Download Settings**
- Ensure downloads are allowed
- Check if download was blocked
- Look in browser downloads folder

**2. Check Pop-up Blocker**
- Disable pop-up blocker for SARK
- Allow downloads from SARK domain

**3. Check Data Selection**
- Ensure you have data to export
- Check filters aren't too restrictive

**4. Try Different Format**
- If CSV fails, try JSON
- If JSON fails, try CSV

**5. Manual Export**
```javascript
// Get data from API directly
fetch('http://localhost:8000/api/v1/servers', {
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN'
  }
})
.then(r => r.json())
.then(data => {
  // Copy to clipboard
  navigator.clipboard.writeText(JSON.stringify(data, null, 2));
  console.log('Data copied to clipboard');
});
```

### Large Export Timeouts

**Symptoms:**
- Export of large datasets fails
- Timeout error
- Partial data exported

**Solutions:**

**1. Use Filters**
- Export in smaller chunks
- Filter by date range
- Filter by team/server

**2. Use API Directly**
```bash
# Export via API (supports streaming)
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:8000/api/v1/servers?format=csv" \
  > servers.csv
```

**3. Use Pagination**
- Export page by page
- Combine files manually

**4. Contact Admin**
- Request backend timeout increase
- For very large exports

---

## Developer Tools

### Debugging Tools

**Browser DevTools:**

```
Open DevTools: F12 (or Cmd+Option+I on Mac)

Tabs:
- Console: JavaScript errors, logs
- Network: API requests, response times
- Application: Cookies, local storage, service workers
- Performance: Page load analysis
```

**Useful Console Commands:**

```javascript
// Check authentication state
localStorage.getItem('sark_access_token')

// Check theme
localStorage.getItem('theme')

// Check WebSocket
window.wsConnection

// Force logout
localStorage.clear()
location.href = '/login'

// Enable debug logging
localStorage.setItem('debug', 'true')
location.reload()
```

### React DevTools

**Installation:**
```
Chrome: https://chrome.google.com/webstore/detail/react-developer-tools/
Firefox: https://addons.mozilla.org/en-US/firefox/addon/react-devtools/
```

**Usage:**
```
1. Open DevTools (F12)
2. Go to "Components" tab
3. Inspect React component tree
4. Check props and state
5. Debug component renders
```

### Network Debugging

**Check API Calls:**

```
1. DevTools → Network tab
2. Filter by "XHR" or "Fetch"
3. Click on request
4. Check:
   - Request Headers (auth token?)
   - Request Payload (correct data?)
   - Response Status (200 OK?)
   - Response Data (correct format?)
```

**Common Status Codes:**
- 200: Success
- 201: Created
- 400: Bad Request (validation error)
- 401: Unauthorized (login required)
- 403: Forbidden (permission denied)
- 404: Not Found
- 429: Too Many Requests (rate limited)
- 500: Internal Server Error (backend issue)

---

## Common Error Messages

### "Network Error"

**Causes:**
- Backend is down
- CORS not configured
- Firewall blocking requests
- Wrong API URL

**Solution:** Check backend health and CORS configuration

### "Unauthorized" / "Please log in again"

**Causes:**
- Token expired
- Invalid token
- Token not sent

**Solution:** Log out and log in again

### "Forbidden" / "Access Denied"

**Causes:**
- Insufficient permissions
- Account disabled
- IP blocked

**Solution:** Contact administrator for access

### "Not Found"

**Causes:**
- Wrong URL
- Resource deleted
- Backend routing issue

**Solution:** Verify URL and check if resource exists

### "Validation Error"

**Causes:**
- Invalid form data
- Missing required fields
- Data format incorrect

**Solution:** Check error message and fix indicated fields

### "Internal Server Error"

**Causes:**
- Backend bug
- Database connection issue
- Unhandled exception

**Solution:** Contact support with error details

---

## Getting Additional Help

### Before Contacting Support

**Collect Information:**

1. **Browser Info:**
   - Browser name and version
   - Operating system
   - Screen resolution

2. **Error Details:**
   - Exact error message
   - Screenshot of error
   - Console logs (DevTools → Console)
   - Network errors (DevTools → Network)

3. **Steps to Reproduce:**
   - What were you trying to do?
   - What steps did you take?
   - What happened vs what you expected?

4. **Environment:**
   - Development or production?
   - Docker or native?
   - Any proxies/VPNs?

### Contact Information

**Internal Support:**
- Slack: #sark-support
- Email: sark-support@company.com
- Tickets: support.company.com/sark

**External Support:**
- GitHub Issues: https://github.com/company/sark/issues
- Documentation: https://docs.sark.company.com
- Community: https://community.sark.company.com

### Reporting Bugs

**Bug Report Template:**

```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '....'
3. See error

**Expected behavior**
What you expected to happen.

**Screenshots**
If applicable, add screenshots.

**Environment:**
 - Browser: [e.g. Chrome 90]
 - OS: [e.g. Windows 10]
 - SARK Version: [e.g. 1.0.0]

**Additional context**
Add any other context about the problem here.
```

---

**Still having issues?** Contact support with the information above.

**Last Updated:** 2025-11-27
**Version:** 1.0.0
