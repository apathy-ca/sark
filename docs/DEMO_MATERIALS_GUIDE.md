# SARK Demo Materials Guide

This guide documents the demo materials needed for SARK v1.0.0 launch, including screenshots, GIFs, and video demos.

## Table of Contents

- [Overview](#overview)
- [Screenshot Requirements](#screenshot-requirements)
- [Animated GIF Workflows](#animated-gif-workflows)
- [Video Demo (Optional)](#video-demo-optional)
- [Capture Tools](#capture-tools)
- [File Organization](#file-organization)
- [Usage Guidelines](#usage-guidelines)

---

## Overview

Demo materials showcase SARK's Web UI and key workflows to potential users, stakeholders, and documentation readers. These materials should be:

- **High Quality**: 1920x1080 or higher resolution
- **Consistent**: Same theme (light or dark) across all materials
- **Clear**: Readable text, no sensitive data
- **Professional**: Clean UI state (no Lorem Ipsum or test data)
- **Annotated**: Highlights or arrows where needed

**Recommended Theme**: Light mode for accessibility and printing compatibility

---

## Screenshot Requirements

### 1. Dashboard - Overview

**Filename**: `01-dashboard-overview.png`

**Description**: Main dashboard showing at-a-glance metrics

**Capture Requirements**:
- Full browser window (1920x1080)
- Include browser chrome (address bar, tabs)
- URL: `http://localhost:5173/` (or production URL)
- Login as: `admin` user

**Content Requirements**:
- 4 metric cards visible:
  - Total Servers: ~24
  - Active Policies: ~12
  - Audit Events (Today): ~1,245
  - Active API Keys: ~8
- No error states visible
- Navigation menu visible on left

**Annotations**: None needed

---

### 2. Servers List

**Filename**: `02-servers-list.png`

**Description**: Server management page showing registered MCP servers

**Capture Requirements**:
- Full page view
- URL: `http://localhost:5173/servers`
- Show at least 5-8 servers in the table

**Content Requirements**:
- Table columns visible:
  - Name
  - URL
  - Status (Active/Inactive)
  - Tools Count
  - Owner
  - Created At
- Mix of Active and Inactive servers
- Search bar visible
- "Register Server" button visible
- Pagination visible (if applicable)

**Annotations**: Optional - highlight "Register Server" button

---

### 3. Server Registration Form

**Filename**: `03-server-registration.png`

**Description**: Server registration form with example data

**Capture Requirements**:
- Modal/form view
- URL: `http://localhost:5173/servers/register`
- Form filled with example data (not submitted)

**Content Requirements**:
- Form fields visible:
  - Server Name: "Analytics MCP Server"
  - Server URL: "http://analytics.internal:8080"
  - Description: "Internal data analytics and reporting tools"
  - Environment: "Production"
  - Owner: "data-team"
  - Tags: "analytics, reporting, data"
- Validation hints visible (green checkmarks for valid fields)
- "Register" and "Cancel" buttons visible

**Annotations**: None needed

---

### 4. Policy Editor

**Filename**: `04-policy-editor.png`

**Description**: Rego policy editor with syntax highlighting

**Capture Requirements**:
- Full editor view
- URL: `http://localhost:5173/policies/new` or edit existing policy
- Code editor with sample policy visible

**Content Requirements**:
- Rego policy code with syntax highlighting
- Line numbers visible
- Sample policy (e.g., RBAC or sensitivity-based policy)
- Policy metadata visible:
  - Name: "Team-Based Access Control"
  - Description: "Allow team members to access their team's servers"
  - Priority: "100"
- "Save" and "Test" buttons visible

**Example Policy Code**:
```rego
package sark.authz

import future.keywords.if
import future.keywords.in

default allow := false

allow if {
    # Allow if user's team matches server owner team
    input.user.team == input.server.owner_team

    # And tool sensitivity is not CRITICAL
    input.tool.sensitivity != "CRITICAL"
}

allow if {
    # Allow admins to access everything
    "admin" in input.user.roles
}
```

**Annotations**: Optional - highlight syntax highlighting

---

### 5. Audit Logs

**Filename**: `05-audit-logs.png`

**Description**: Audit log search and filtering interface

**Capture Requirements**:
- Full page view
- URL: `http://localhost:5173/audit`
- Table with at least 10-15 audit events

**Content Requirements**:
- Table columns visible:
  - Timestamp
  - User
  - Server
  - Tool
  - Action
  - Result (Success/Denied)
  - Duration
- Filter controls visible:
  - Date range picker
  - User filter
  - Result filter (Success/Denied/Error)
  - Search box
- Mix of Success and Denied events
- Export buttons visible (CSV, JSON)

**Annotations**: Optional - highlight filter controls

---

### 6. Audit Log Detail

**Filename**: `06-audit-log-detail.png`

**Description**: Expanded audit log entry showing full details

**Capture Requirements**:
- Modal or expanded view of a single audit event
- Show JSON payload or detailed fields

**Content Requirements**:
- Full event details visible:
  - Event ID
  - Timestamp (with timezone)
  - User (username, email, roles)
  - Server (name, URL)
  - Tool (name, sensitivity level)
  - Request parameters (JSON)
  - Policy decision (Allow/Deny)
  - Policy used
  - Result (success/failure)
  - Response time (ms)
- Code formatting for JSON data
- "Close" button visible

**Annotations**: None needed

---

### 7. API Keys Management

**Filename**: `07-api-keys.png`

**Description**: API key management interface

**Capture Requirements**:
- Full page view
- URL: `http://localhost:5173/api-keys`
- Table with 5-8 API keys

**Content Requirements**:
- Table columns visible:
  - Name
  - Key Prefix (e.g., `sark_a1b2c3...`)
  - Scopes
  - Rate Limit
  - Created At
  - Expires At
  - Status (Active/Revoked)
- Mix of Active and Revoked keys
- "Create API Key" button visible
- Action buttons visible (Rotate, Revoke, Delete)

**Annotations**: Optional - highlight "Create API Key" button

---

### 8. API Key Creation

**Filename**: `08-api-key-creation.png`

**Description**: API key creation form with generated key displayed

**Capture Requirements**:
- Modal showing newly created API key
- Key should be visible but blurred in documentation

**Content Requirements**:
- Generated API key displayed: `sark_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`
- Form fields visible:
  - Name: "Analytics Dashboard API"
  - Scopes: "servers:read, audit:read"
  - Rate Limit: "1000 requests/hour"
  - Expires: "90 days"
- Warning message: "Copy this key now. It won't be shown again."
- "Copy to Clipboard" button visible

**Annotations**: Blur the actual API key value in published docs

---

### 9. Dark Mode Example

**Filename**: `09-dashboard-dark-mode.png`

**Description**: Dashboard in dark mode theme

**Capture Requirements**:
- Same as screenshot #1 but in dark mode
- Toggle theme using `t` keyboard shortcut

**Content Requirements**:
- Same metrics as light mode dashboard
- Dark theme properly applied
- Good contrast and readability

**Annotations**: Caption: "Dark mode theme"

---

### 10. Keyboard Shortcuts Help

**Filename**: `10-keyboard-shortcuts.png`

**Description**: Keyboard shortcuts help modal

**Capture Requirements**:
- Modal overlay showing all keyboard shortcuts
- Trigger with `Ctrl+/` or `?`

**Content Requirements**:
- All shortcuts listed:
  - Navigation: `g+d`, `g+s`, `g+p`, `g+a`, `g+k`
  - Global: `t` (toggle theme), `Ctrl+/` (help), `Esc` (close)
  - Search: `/` (focus search)
  - Actions: `n` (new), `e` (edit), `d` (delete)
- Organized by category
- "Close" button visible

**Annotations**: None needed

---

## Animated GIF Workflows

Create short animated GIFs (10-20 seconds each) demonstrating key workflows.

**GIF Specifications**:
- Resolution: 1280x720 (720p)
- Frame rate: 15-20 fps
- File size: < 5MB per GIF
- Format: GIF or WEBP
- Duration: 10-20 seconds

---

### GIF 1: Server Registration Flow

**Filename**: `workflow-01-server-registration.gif`

**Duration**: 15 seconds

**Workflow Steps**:
1. Navigate to Servers page (`/servers`)
2. Click "Register Server" button
3. Fill in form:
   - Name: "Analytics Server"
   - URL: "http://analytics.internal:8080"
   - Description: "Data analytics tools"
4. Click "Register" button
5. Success notification appears
6. New server appears in table
7. Highlight the new server row (briefly)

**Annotations**: None needed (workflow is self-explanatory)

---

### GIF 2: Policy Creation and Testing

**Filename**: `workflow-02-policy-creation.gif`

**Duration**: 20 seconds

**Workflow Steps**:
1. Navigate to Policies page (`/policies`)
2. Click "Create Policy" button
3. Enter policy metadata:
   - Name: "Team Access Policy"
   - Description: "Restrict access by team"
4. Type Rego policy code (show typing effect):
   ```rego
   package sark.authz
   default allow := false
   allow if { input.user.team == input.server.owner_team }
   ```
5. Click "Test Policy" button
6. Test input appears with sample data
7. Test result shows "Allow: true"
8. Click "Save Policy"
9. Success notification

**Annotations**: Optional speed indicator ("2x speed" text overlay)

---

### GIF 3: Audit Log Filtering

**Filename**: `workflow-03-audit-filtering.gif`

**Duration**: 12 seconds

**Workflow Steps**:
1. Navigate to Audit Logs page (`/audit`)
2. Click date range filter
3. Select "Last 24 hours"
4. Click user filter dropdown
5. Select user: "alice@company.com"
6. Click result filter
7. Select "Denied Only"
8. Table updates to show filtered results
9. Highlight filtered results (briefly)
10. Click "Export CSV" button
11. Download notification appears

**Annotations**: None needed

---

### GIF 4: Real-Time Updates (WebSocket)

**Filename**: `workflow-04-realtime-updates.gif`

**Duration**: 10 seconds

**Workflow Steps**:
1. Show Dashboard page with current metrics
2. Simulate new audit event in background (API call or separate browser)
3. Dashboard "Audit Events" counter increments in real-time
4. Show audit log page
5. New event appears at top of table without page refresh
6. Highlight new row with brief animation
7. Show connection status indicator (green dot)

**Annotations**: Caption: "Real-time updates via WebSocket"

---

### GIF 5: Keyboard Navigation

**Filename**: `workflow-05-keyboard-nav.gif`

**Duration**: 15 seconds

**Workflow Steps**:
1. Start on any page
2. Press `g+d` - navigate to Dashboard
3. Press `g+s` - navigate to Servers
4. Press `g+p` - navigate to Policies
5. Press `g+a` - navigate to Audit
6. Press `g+k` - navigate to API Keys
7. Press `t` - toggle to dark mode
8. Press `t` again - toggle back to light mode
9. Press `Ctrl+/` - show keyboard shortcuts help

**Annotations**: Show key presses as overlay (e.g., "g+d" appears when pressed)

---

### GIF 6: Data Export

**Filename**: `workflow-06-data-export.gif`

**Duration**: 10 seconds

**Workflow Steps**:
1. Show Servers page with data table
2. Click "Export" dropdown button
3. Select "Export CSV"
4. Browser download dialog appears
5. File downloads (show download bar)
6. Click "Export" dropdown again
7. Select "Export JSON"
8. JSON file downloads
9. Show both files in downloads folder

**Annotations**: None needed

---

## Video Demo (Optional)

A 2-3 minute video walkthrough of SARK's key features.

**Filename**: `sark-demo-v1.0.0.mp4`

**Specifications**:
- Resolution: 1920x1080 (1080p)
- Format: MP4 (H.264)
- Duration: 2-3 minutes
- Audio: Optional voiceover or text captions
- File size: < 50MB

**Script Outline**:

1. **Introduction (15s)**
   - Show SARK logo/landing page
   - Text: "SARK - Enterprise MCP Governance"
   - Quick overview of what SARK does

2. **Dashboard (20s)**
   - Show dashboard with metrics
   - Highlight key metrics
   - Show navigation menu

3. **Server Management (30s)**
   - Browse servers list
   - Register a new server
   - Show server details

4. **Policy Management (30s)**
   - Browse policies list
   - Create new policy with Rego code
   - Test policy
   - Save policy

5. **Audit Logs (30s)**
   - Browse audit logs
   - Apply filters
   - View detailed audit entry
   - Export data

6. **API Keys (20s)**
   - Browse API keys
   - Create new API key
   - Show scopes and rate limits

7. **UI Features (15s)**
   - Toggle dark mode
   - Show keyboard shortcuts
   - Demonstrate real-time updates

8. **Conclusion (10s)**
   - Show documentation links
   - GitHub repository
   - Call to action: "Get started in 5 minutes"

---

## Capture Tools

### Screenshot Tools

**macOS**:
- **Cmd+Shift+4**: Select area to capture
- **Cmd+Shift+3**: Full screen capture
- **Preview**: Built-in annotation tools

**Windows**:
- **Windows+Shift+S**: Snipping tool
- **Windows+PrtScn**: Full screen to file
- **Snagit**: Professional screenshot tool

**Linux**:
- **gnome-screenshot**: GNOME default
- **Flameshot**: Advanced annotation
- **Shutter**: Feature-rich screenshot tool

**Browser Extensions**:
- **Awesome Screenshot**: Full page capture
- **Fireshot**: Scrolling screenshots
- **Nimbus Screenshot**: Annotation tools

### GIF Recording Tools

**Cross-Platform**:
- **LICEcap**: Lightweight, open-source
- **ScreenToGif**: Windows, feature-rich
- **Kap**: macOS, modern UI
- **Peek**: Linux, simple GIF recorder

**Professional**:
- **ScreenFlow** (macOS): Video editing + GIF export
- **Camtasia**: Full video editing suite
- **OBS Studio**: Free, powerful recording

### Video Recording

**Free**:
- **OBS Studio**: Industry standard, free
- **QuickTime Player** (macOS): Built-in screen recording
- **Windows Game Bar**: Built-in (Windows+G)

**Paid**:
- **Camtasia**: Professional editing
- **ScreenFlow** (macOS): Editing + effects
- **Snagit**: Simple video + screenshots

---

## File Organization

Store all demo materials in: `/home/user/sark/docs/screenshots/`

```
docs/
└── screenshots/
    ├── README.md                              # This file
    ├── screenshots/
    │   ├── 01-dashboard-overview.png
    │   ├── 02-servers-list.png
    │   ├── 03-server-registration.png
    │   ├── 04-policy-editor.png
    │   ├── 05-audit-logs.png
    │   ├── 06-audit-log-detail.png
    │   ├── 07-api-keys.png
    │   ├── 08-api-key-creation.png
    │   ├── 09-dashboard-dark-mode.png
    │   └── 10-keyboard-shortcuts.png
    ├── workflows/
    │   ├── workflow-01-server-registration.gif
    │   ├── workflow-02-policy-creation.gif
    │   ├── workflow-03-audit-filtering.gif
    │   ├── workflow-04-realtime-updates.gif
    │   ├── workflow-05-keyboard-nav.gif
    │   └── workflow-06-data-export.gif
    └── videos/
        └── sark-demo-v1.0.0.mp4
```

---

## Usage Guidelines

### In Documentation

**Markdown Syntax**:
```markdown
![Dashboard Overview](./screenshots/01-dashboard-overview.png)

*Figure 1: SARK Dashboard showing at-a-glance metrics*
```

**HTML (for sizing)**:
```html
<img src="./screenshots/01-dashboard-overview.png" alt="Dashboard" width="800">
```

### In README

Add screenshots to main README.md:

```markdown
## Screenshots

### Dashboard
![Dashboard](docs/screenshots/screenshots/01-dashboard-overview.png)

### Server Management
![Servers](docs/screenshots/screenshots/02-servers-list.png)

### Policy Editor
![Policies](docs/screenshots/screenshots/04-policy-editor.png)

### Audit Logs
![Audit](docs/screenshots/screenshots/05-audit-logs.png)
```

### In Presentations

- Use high-resolution screenshots (1920x1080)
- Add annotations or callouts in presentation software
- Use GIFs sparingly (can be large files)

### On Website/Blog

- Optimize file sizes (compress PNGs with TinyPNG)
- Use responsive images (srcset for different sizes)
- Host large GIFs on CDN or video platform

---

## Image Optimization

Before publishing, optimize all images:

**PNG Compression**:
```bash
# Using pngquant
pngquant --quality=80-90 *.png

# Using ImageOptim (macOS GUI)
# Drag and drop files into ImageOptim

# Using TinyPNG API
curl --upload-file input.png --output output.png https://api.tinypng.com/
```

**GIF Optimization**:
```bash
# Using gifsicle
gifsicle -O3 --colors 256 input.gif -o output.gif

# Using ffmpeg (convert to WEBP for better compression)
ffmpeg -i input.gif -c:v libwebp -quality 80 output.webp
```

**Target File Sizes**:
- Screenshots: < 500KB each
- GIFs: < 5MB each
- Video: < 50MB total

---

## Checklist

Before considering demo materials complete:

- [ ] All 10 screenshots captured
- [ ] All 6 GIF workflows created
- [ ] Optional video demo created
- [ ] All files optimized for web
- [ ] Files organized in correct directory structure
- [ ] README.md updated with screenshot embeds
- [ ] UI_USER_GUIDE.md updated with screenshots
- [ ] No sensitive data visible in any materials
- [ ] Consistent theme (light or dark) across all materials
- [ ] All images have descriptive alt text
- [ ] File sizes within targets
- [ ] Materials reviewed by 2+ team members

---

## Production Deployment

Once materials are ready:

1. **Commit to repository**:
   ```bash
   git add docs/screenshots/
   git commit -m "docs: add UI screenshots and demo materials"
   git push origin main
   ```

2. **Update documentation**:
   - README.md
   - docs/UI_USER_GUIDE.md
   - docs/GETTING_STARTED_5MIN.md

3. **Publish to website** (if applicable):
   - Upload to CDN
   - Update website with new images
   - Add to blog posts

4. **Share on social media**:
   - Twitter/X: Share GIFs with hashtags
   - LinkedIn: Share video demo
   - Reddit: r/selfhosted, r/programming

---

## Maintenance

Update demo materials when:

- UI design changes significantly
- New features are added
- Branding or color scheme changes
- User feedback indicates confusion
- Quarterly review for accuracy

**Review Schedule**: Every 3 months or with major releases

---

## Questions?

For questions about demo materials:

- GitHub Issues: https://github.com/company/sark/issues
- Slack: #sark-documentation
- Email: docs@company.com

---

**Last Updated**: 2025-11-27
**Version**: 1.0.0
**Maintainer**: Documentation Team
