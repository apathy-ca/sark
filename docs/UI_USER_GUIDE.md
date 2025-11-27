# SARK UI User Guide

**Complete guide to using the SARK Web Interface**

Version 1.0.0 | Last Updated: 2025-11-27

---

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Authentication](#authentication)
4. [Dashboard](#dashboard)
5. [MCP Servers Management](#mcp-servers-management)
6. [Policy Management](#policy-management)
7. [Audit Logs](#audit-logs)
8. [API Keys](#api-keys)
9. [User Interface Features](#user-interface-features)
10. [Keyboard Shortcuts](#keyboard-shortcuts)
11. [Tips & Best Practices](#tips--best-practices)

---

## Overview

The SARK Web UI provides a modern, intuitive interface for managing your MCP (Model Context Protocol) governance infrastructure. Built with React and TypeScript, it offers real-time updates, dark mode support, and comprehensive keyboard shortcuts for power users.

### Key Features

✨ **Complete Management Suite**
- Server registration and monitoring
- Policy creation and testing
- Audit log analysis
- API key lifecycle management

⚡ **Real-Time Updates**
- WebSocket integration for live data
- Automatic refresh of server status
- Instant audit event notifications

🎨 **Modern User Experience**
- Dark/light/system theme modes
- Responsive design (desktop, tablet, mobile)
- Keyboard-first navigation
- Data export (CSV/JSON)

🔒 **Enterprise Ready**
- LDAP/OIDC authentication
- Role-based access control
- Session management
- Secure token handling

---

## Getting Started

### Accessing the UI

**Local Development:**
```
http://localhost:3000
```

**Production:**
```
https://sark.yourdomain.com
```

### System Requirements

**Supported Browsers:**
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

**Recommended:**
- Screen resolution: 1920x1080 or higher
- JavaScript enabled
- Cookies enabled for session management

### First-Time Setup

1. Open the SARK UI in your browser
2. Log in with your LDAP/OIDC credentials
3. Familiarize yourself with the dashboard
4. Press `Ctrl+/` to view keyboard shortcuts

---

## Authentication

### Logging In

**LDAP Authentication:**

1. Navigate to the login page
2. Enter your LDAP username and password
3. Click "Sign In" or press `Enter`
4. You'll be redirected to the dashboard upon successful authentication

**Example:**
```
Username: john.doe
Password: ••••••••
```

**OIDC/OAuth Authentication:**

1. Click "Sign in with OIDC"
2. You'll be redirected to your identity provider
3. Authenticate with your provider
4. Return to SARK dashboard automatically

### Session Management

- **Access Token Lifetime:** 60 minutes
- **Refresh Token Lifetime:** 7 days
- **Auto-Refresh:** Tokens refresh automatically before expiration
- **Session Timeout:** 30 minutes of inactivity

**Session Indicator:**
- Green dot in header: Active session
- Yellow dot: Session expiring soon (< 5 minutes)
- Red dot: Session expired (re-login required)

### Logging Out

**Methods:**
1. Click your username → "Logout"
2. Press `Shift+L` (keyboard shortcut)
3. Sessions expire automatically after inactivity

**Security Note:** Always log out when using shared computers.

---

## Dashboard

The Dashboard provides an at-a-glance view of your SARK deployment.

### Metrics Cards

**Total Servers**
- Count of registered MCP servers
- Shows active vs inactive servers
- Click to navigate to Servers page

**Active Policies**
- Number of OPA policies deployed
- Includes default and custom policies
- Click to navigate to Policies page

**Audit Events (24h)**
- Tool invocations in last 24 hours
- Real-time counter
- Click to view detailed audit logs

**API Keys**
- Count of active API keys
- Excludes revoked keys
- Click to manage API keys

### Quick Actions

From the Dashboard, you can:
- Navigate to any section via sidebar
- Use keyboard shortcuts (`g+s`, `g+p`, etc.)
- View system health status
- Access recent activity feed

---

## MCP Servers Management

Manage all your MCP servers from a single interface.

### Viewing Servers

**Servers List View:**

Navigate to: **Servers** (or press `g+s`)

**Columns:**
- **Name:** Server identifier
- **URL:** Server endpoint
- **Status:** Active/Inactive/Error
- **Team:** Owning team
- **Sensitivity:** LOW/MEDIUM/HIGH/CRITICAL
- **Tools:** Number of available tools
- **Last Seen:** Last heartbeat timestamp

**Features:**
- **Search:** Filter by name, URL, or team
- **Sort:** Click column headers
- **Pagination:** Navigate large lists
- **Export:** Download as CSV/JSON

### Registering a New Server

**Step-by-Step:**

1. Click "Register Server" button
2. Fill in the registration form:
   - **Name:** Unique server identifier (e.g., `jira-production`)
   - **URL:** Server endpoint (e.g., `https://jira-mcp.company.com`)
   - **Description:** Purpose of the server
   - **Team:** Owning team (e.g., `engineering`)
   - **Environment:** dev/staging/production
   - **Sensitivity:** Default sensitivity level
   - **Tags:** Searchable tags (comma-separated)

3. Click "Register" or press `Ctrl+Enter`

**Example:**
```json
{
  "name": "jira-production",
  "url": "https://jira-mcp.company.com",
  "description": "Jira MCP server for production ticket management",
  "team": "engineering",
  "environment": "production",
  "sensitivity": "medium",
  "tags": ["jira", "tickets", "production"]
}
```

**Validation:**
- Name must be unique
- URL must be valid HTTPS endpoint
- Server must respond to health check
- All required fields must be filled

### Server Details

**Click any server to view:**

**Overview Tab:**
- Full server metadata
- Connection status
- Health check results
- Last activity timestamp

**Tools Tab:**
- List of available MCP tools
- Tool descriptions
- Input schemas
- Sensitivity levels

**Metrics Tab:**
- Tool invocation counts
- Success/failure rates
- Response time distribution
- Usage over time

**Settings Tab:**
- Update server configuration
- Change sensitivity level
- Modify tags
- Deregister server

### Server Actions

**Bulk Operations:**
- Select multiple servers (checkboxes)
- Apply tags in bulk
- Update team assignment
- Export server list

**Individual Actions:**
- **Edit:** Update server configuration
- **Test Connection:** Verify server is reachable
- **View Audit:** See all events for this server
- **Deregister:** Remove server (requires confirmation)

---

## Policy Management

Create, test, and manage OPA (Open Policy Agent) policies.

### Viewing Policies

Navigate to: **Policies** (or press `g+p`)

**Policy List:**
- **Name:** Policy identifier
- **Type:** Default/Custom
- **Status:** Active/Inactive
- **Version:** Policy version number
- **Last Modified:** Timestamp

### Creating a Policy

**Step-by-Step:**

1. Click "New Policy" button
2. Enter policy details:
   - **Name:** Descriptive policy name
   - **Description:** What the policy enforces
   - **Policy Code:** Rego policy content

3. Write Rego policy using the syntax-highlighted editor
4. Test policy with sample inputs
5. Click "Create" or press `Ctrl+S`

**Example Policy:**
```rego
package sark.policies.custom

# Require MFA for production database access
deny[msg] if {
    input.server.environment == "production"
    input.tool contains "database"
    not input.user.mfa_verified
    msg := "Production database access requires MFA"
}

# Allow developers to access dev/staging
allow if {
    input.user.role == "developer"
    input.server.environment in ["dev", "staging"]
}
```

### Policy Editor Features

**Syntax Highlighting:**
- Rego syntax coloring
- Error highlighting
- Bracket matching
- Auto-indentation

**Code Completion:**
- Rego keywords
- Common policy patterns
- SARK-specific input fields

**Policy Testing:**
- Test with sample inputs
- View policy decision (allow/deny)
- See which rules matched
- Debug policy logic

**Test Input Example:**
```json
{
  "user": {
    "user_id": "user123",
    "role": "developer",
    "mfa_verified": false
  },
  "server": {
    "name": "db-production",
    "environment": "production"
  },
  "tool": "database_query",
  "sensitivity_level": "high"
}
```

### Policy Testing

**Interactive Testing:**

1. Select a policy
2. Click "Test Policy"
3. Enter test input (JSON)
4. Click "Evaluate"
5. View results:
   - **Decision:** Allow/Deny
   - **Matched Rules:** Which rules fired
   - **Evaluation Time:** Policy performance
   - **Explanation:** Why decision was made

**Regression Testing:**
- Save test cases
- Run all tests
- Verify policy changes don't break existing logic

### Policy Versioning

- All policy changes create new versions
- View version history
- Rollback to previous versions
- Compare versions side-by-side

---

## Audit Logs

View and analyze all MCP tool invocations and access attempts.

### Viewing Audit Events

Navigate to: **Audit Logs** (or press `g+a`)

**Event List:**

**Columns:**
- **Timestamp:** When event occurred
- **User:** Who performed the action
- **Action:** tool:invoke, policy:evaluate, etc.
- **Server:** Which MCP server
- **Tool:** Tool name
- **Decision:** Allow/Deny
- **Result:** Success/Failure

### Filtering Audit Logs

**Filter Options:**

**By Time:**
- Last hour
- Last 24 hours
- Last 7 days
- Custom range

**By User:**
- Select from user dropdown
- Search by email/username

**By Server:**
- Filter by server name
- Filter by server team

**By Decision:**
- Allowed only
- Denied only
- Both

**By Tool:**
- Specific tool name
- Tool category (database, api, file, etc.)

**Advanced Filters:**
- Combine multiple filters
- Save filter presets
- Export filtered results

### Event Details

**Click any event to view:**

**Overview:**
- Full event metadata
- User context (role, teams, IP)
- Server context (name, team, sensitivity)
- Tool parameters
- Policy decision

**Policy Evaluation:**
- Which policies were evaluated
- Rules that matched
- Evaluation time
- Cache hit/miss

**Result:**
- Tool response (if successful)
- Error message (if failed)
- Response time
- Sensitivity level

**Example Event:**
```json
{
  "event_id": "evt_abc123",
  "timestamp": "2025-11-27T10:15:30Z",
  "user_id": "user_456",
  "user_email": "developer@example.com",
  "action": "tool:invoke",
  "server_name": "jira-production",
  "tool_name": "create_ticket",
  "tool_params": {
    "project": "ENG",
    "summary": "Bug fix required"
  },
  "decision": "allow",
  "policy_rules": ["rbac", "team_access"],
  "sensitivity_level": "medium",
  "ip_address": "10.1.2.3",
  "response_status": "success",
  "response_time_ms": 245
}
```

### Audit Analytics

**Built-in Reports:**
- Tool usage by user
- Access patterns by time
- Policy denial reasons
- Server utilization
- Anomaly detection

**Export Options:**
- CSV for spreadsheet analysis
- JSON for custom processing
- PDF for compliance reports

---

## API Keys

Manage API keys for programmatic access to SARK.

### Viewing API Keys

Navigate to: **API Keys** (or press `g+k`)

**Key List:**
- **Name:** Key identifier
- **Prefix:** First 8 characters (e.g., `sk_sark_12345678...`)
- **Scopes:** Permissions granted
- **Created:** Creation timestamp
- **Expires:** Expiration date (if set)
- **Last Used:** Last access timestamp

### Creating an API Key

**Step-by-Step:**

1. Click "Create API Key"
2. Fill in key details:
   - **Name:** Descriptive name (e.g., `CI/CD Pipeline`)
   - **Description:** Purpose of the key
   - **Scopes:** Select permissions
     - `servers:read` - View servers
     - `servers:write` - Register/update servers
     - `policies:read` - View policies
     - `policies:write` - Create/update policies
     - `tools:invoke` - Invoke MCP tools
     - `audit:read` - View audit logs
   - **Expiration:** Never/30 days/90 days/1 year/custom

3. Click "Generate"
4. **IMPORTANT:** Copy the API key immediately
   - The full key is shown only once
   - Store it securely (password manager, secrets vault)
   - Key format: `sk_sark_abcdefghijklmnopqrstuvwxyz123456`

**Example Usage:**
```bash
curl -X GET https://sark.company.com/api/v1/servers \
  -H "Authorization: Bearer sk_sark_abcdefghijk..."
```

### API Key Security

**Best Practices:**
- Use separate keys for different applications
- Grant minimum necessary scopes
- Set expiration dates
- Rotate keys regularly
- Revoke compromised keys immediately
- Never commit keys to version control

### Rotating an API Key

**Process:**

1. Select key to rotate
2. Click "Rotate"
3. New key is generated
4. Old key remains valid for 24 hours
5. Update applications with new key within 24 hours
6. Old key automatically revoked after grace period

### Revoking an API Key

**Immediate Revocation:**

1. Select key to revoke
2. Click "Revoke"
3. Confirm action
4. Key is invalidated immediately
5. All requests with this key will fail

**Use Cases:**
- Key compromised or leaked
- Application decommissioned
- Employee offboarding
- Security incident

---

## User Interface Features

### Theme Modes

**Available Themes:**
- **Light Mode:** Traditional light background
- **Dark Mode:** Dark background, easier on eyes
- **System:** Matches OS preference

**Switching Themes:**
- Click theme toggle in header
- Press `t` keyboard shortcut
- Automatically saves preference

### Data Export

**Export Formats:**
- **CSV:** For Excel, Google Sheets
- **JSON:** For programmatic processing

**Exportable Data:**
- Server lists
- Audit events
- Policy definitions
- API key metadata

**How to Export:**
1. Navigate to any list view
2. Click "Export" button
3. Choose format (CSV/JSON)
4. File downloads automatically

**Example CSV Export:**
```csv
name,url,team,environment,sensitivity,tools_count
jira-production,https://jira-mcp.company.com,engineering,production,medium,5
db-staging,https://db-mcp-staging.company.com,engineering,staging,low,3
```

### Search & Filtering

**Global Search:**
- Search box in header
- Searches across all entities
- Press `/` to focus search

**List Filters:**
- Each list page has filters
- Combine multiple filters
- Save filter presets
- Clear all filters button

**Search Tips:**
- Use quotes for exact match: `"jira-production"`
- Use wildcards: `*production*`
- Search multiple terms: `jira production`

### Real-Time Updates

**WebSocket Connection:**
- Automatic connection to backend
- Real-time data updates
- No manual refresh needed
- Connection status indicator in header

**Real-Time Features:**
- Server status changes
- New audit events
- Policy updates
- API key usage

**Indicator States:**
- 🟢 Green: Connected
- 🟡 Yellow: Connecting
- 🔴 Red: Disconnected (using polling)

### Responsive Design

**Desktop (1920x1080+):**
- Full sidebar navigation
- Multi-column layouts
- All features accessible

**Tablet (768x1024):**
- Collapsible sidebar
- Optimized card layouts
- Touch-friendly controls

**Mobile (375x667+):**
- Bottom navigation
- Single-column layouts
- Swipe gestures
- Compact controls

---

## Keyboard Shortcuts

Press `Ctrl+/` (or `⌘+/` on Mac) to view all shortcuts.

### Navigation Shortcuts

| Shortcut | Action |
|----------|--------|
| `g + d` | Go to Dashboard |
| `g + s` | Go to Servers |
| `g + p` | Go to Policies |
| `g + a` | Go to Audit Logs |
| `g + k` | Go to API Keys |

### Global Shortcuts

| Shortcut | Action |
|----------|--------|
| `/` | Focus search |
| `t` | Toggle theme |
| `Ctrl+/` | Show keyboard shortcuts |
| `Esc` | Close modals/dialogs |
| `?` | Show help |

### List View Shortcuts

| Shortcut | Action |
|----------|--------|
| `n` | New item (server, policy, etc.) |
| `r` | Refresh list |
| `e` | Export data |
| `f` | Focus filter |
| `↑/↓` | Navigate items |
| `Enter` | Open selected item |

### Form Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Enter` | Submit form |
| `Ctrl+S` | Save changes |
| `Esc` | Cancel/close |
| `Tab` | Next field |
| `Shift+Tab` | Previous field |

### Editor Shortcuts (Policy Editor)

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Save policy |
| `Ctrl+Enter` | Test policy |
| `Ctrl+Z` | Undo |
| `Ctrl+Shift+Z` | Redo |
| `Ctrl+F` | Find in code |
| `Ctrl+/` | Toggle comment |

---

## Tips & Best Practices

### Performance Tips

**Faster Page Loads:**
- Use keyboard shortcuts instead of clicking
- Enable browser caching
- Use filters to reduce data loaded
- Export large datasets for offline analysis

**Efficient Searching:**
- Use specific search terms
- Leverage filters before searching
- Save commonly used filter presets
- Use pagination for large result sets

### Security Best Practices

**Authentication:**
- Enable MFA if available
- Use strong, unique passwords
- Log out from shared computers
- Review active sessions regularly

**API Keys:**
- One key per application/purpose
- Set expiration dates
- Rotate keys quarterly
- Revoke unused keys
- Monitor key usage in audit logs

**Access Control:**
- Request minimum necessary permissions
- Review your access periodically
- Report suspicious activity
- Don't share credentials

### Workflow Best Practices

**Server Management:**
- Use consistent naming conventions
- Tag servers by function, team, environment
- Set appropriate sensitivity levels
- Document server purposes in descriptions
- Regularly review server health

**Policy Management:**
- Start with default policies
- Test policies before deploying
- Version control policy code
- Document policy intent
- Review policies quarterly

**Audit Review:**
- Check audit logs daily
- Set up alerts for anomalies
- Export logs for compliance
- Investigate policy denials
- Monitor tool usage patterns

### Troubleshooting Tips

**Connection Issues:**
- Check WebSocket connection indicator
- Verify network connectivity
- Clear browser cache
- Disable browser extensions
- Try incognito/private mode

**Authentication Issues:**
- Verify credentials are correct
- Check if account is locked
- Confirm LDAP/OIDC is configured
- Clear cookies and retry
- Contact administrator if persists

**Performance Issues:**
- Clear browser cache
- Reduce number of filters
- Use pagination for large lists
- Close unused browser tabs
- Check network speed

**UI Glitches:**
- Hard refresh: `Ctrl+Shift+R`
- Clear browser cache
- Update browser to latest version
- Try different browser
- Report bug to support team

---

## Getting Help

### Documentation Resources

- **[API Reference](API_REFERENCE.md)** - Complete API documentation
- **[MCP Introduction](MCP_INTRODUCTION.md)** - Understanding MCP
- **[Deployment Guide](DEPLOYMENT.md)** - Production deployment
- **[Troubleshooting UI](TROUBLESHOOTING_UI.md)** - UI-specific issues
- **[FAQ](FAQ.md)** - Frequently asked questions

### Support Channels

**Internal:**
- **Slack:** #sark-support
- **Email:** sark-support@company.com
- **Tickets:** support.company.com/sark

**External:**
- **GitHub Issues:** https://github.com/company/sark/issues
- **Documentation:** https://docs.sark.company.com
- **Community:** https://community.sark.company.com

### Feedback

We welcome your feedback to improve SARK!

**Report Issues:**
- Bug reports via GitHub Issues
- Feature requests via GitHub Discussions
- UI/UX feedback via feedback form in app

**Contribute:**
- Documentation improvements
- Translation contributions
- UI/UX suggestions
- Code contributions (see CONTRIBUTING.md)

---

## Appendix

### Browser Compatibility

| Browser | Minimum Version | Recommended |
|---------|----------------|-------------|
| Chrome | 90 | Latest |
| Edge | 90 | Latest |
| Firefox | 88 | Latest |
| Safari | 14 | Latest |

### Accessibility

SARK UI follows WCAG 2.1 Level AA guidelines:

- Keyboard navigation support
- Screen reader compatible
- High contrast mode
- Scalable text
- Focus indicators
- ARIA labels

### Performance Targets

**Metrics:**
- First Contentful Paint: < 1.5s
- Time to Interactive: < 3.5s
- Lighthouse Score: > 90
- Bundle Size: < 500KB (gzipped)

### Change Log

**Version 1.0.0 (2025-11-27):**
- Initial release
- Complete feature set
- All core pages implemented
- Production ready

---

**Questions?** See [Troubleshooting UI](TROUBLESHOOTING_UI.md) or contact support.

**Last Updated:** 2025-11-27
**Version:** 1.0.0
