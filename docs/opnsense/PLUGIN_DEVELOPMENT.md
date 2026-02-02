# SARK OPNsense Plugin Development Guide

This document describes the development and deployment of the SARK Home Gateway plugin for OPNsense.

## Overview

The SARK OPNsense plugin provides a web-based interface for configuring and managing the SARK Home LLM Gateway directly from your OPNsense firewall. It follows OPNsense's MVC architecture and integrates with the configd backend service.

## Architecture

```
opnsense/
├── +MANIFEST              # Plugin metadata for pkg
├── Makefile               # FreeBSD port Makefile
├── pkg-plist              # Package file list
└── src/
    ├── etc/
    │   └── rc.d/
    │       └── sark       # FreeBSD service script
    └── opnsense/
        ├── mvc/
        │   └── app/
        │       ├── controllers/
        │       │   └── OPNsense/SARK/
        │       │       ├── IndexController.php
        │       │       ├── Api/
        │       │       │   ├── AnalyticsController.php
        │       │       │   ├── PolicyController.php
        │       │       │   ├── ServiceController.php
        │       │       │   └── SettingsController.php
        │       │       ├── forms/
        │       │       │   ├── general.xml
        │       │       │   └── policies.xml
        │       │       └── Menu/
        │       │           └── Menu.xml
        │       ├── models/
        │       │   └── OPNsense/SARK/
        │       │       ├── General.php
        │       │       ├── General.xml
        │       │       ├── Policy.php
        │       │       └── Policy.xml
        │       └── views/
        │           └── OPNsense/SARK/
        │               ├── index.volt
        │               ├── logs.volt
        │               ├── policies.volt
        │               └── settings.volt
        └── service/
            └── conf/
                └── actions.d/
                    └── actions_sark.conf
```

## Components

### Controllers

#### IndexController.php
Main page controller that renders the dashboard and sub-pages.

**Actions:**
- `indexAction()` - Dashboard with usage statistics
- `settingsAction()` - Configuration page
- `policiesAction()` - Policy management
- `logsAction()` - Audit log viewer

#### Api/ServiceController.php
REST API for service management.

**Endpoints:**
- `POST /api/sark/service/start` - Start the service
- `POST /api/sark/service/stop` - Stop the service
- `POST /api/sark/service/restart` - Restart the service
- `GET /api/sark/service/status` - Get service status
- `POST /api/sark/service/reconfigure` - Reload configuration

#### Api/SettingsController.php
REST API for configuration management.

**Endpoints:**
- `GET /api/sark/settings/get` - Get all settings
- `POST /api/sark/settings/set` - Update settings
- `GET /api/sark/settings/getUsers` - List users
- `POST /api/sark/settings/addUser` - Add user
- `POST /api/sark/settings/setUser/{uuid}` - Update user
- `POST /api/sark/settings/delUser/{uuid}` - Delete user
- `GET /api/sark/settings/getProviders` - List providers
- `POST /api/sark/settings/addProvider` - Add provider
- `POST /api/sark/settings/setProvider/{uuid}` - Update provider
- `POST /api/sark/settings/delProvider/{uuid}` - Delete provider

#### Api/PolicyController.php
REST API for policy management.

**Endpoints:**
- `GET /api/sark/policy/get` - Get policy configuration
- `POST /api/sark/policy/set` - Update policies
- `GET /api/sark/policy/getAvailable` - List available policies
- `GET /api/sark/policy/getRules` - List custom rules
- `POST /api/sark/policy/addRule` - Add custom rule
- `POST /api/sark/policy/setRule/{uuid}` - Update rule
- `POST /api/sark/policy/delRule/{uuid}` - Delete rule
- `POST /api/sark/policy/toggle` - Toggle built-in policy
- `GET /api/sark/policy/status` - Get policy status

#### Api/AnalyticsController.php
REST API for usage statistics.

**Endpoints:**
- `GET /api/sark/analytics/summary` - Usage summary
- `GET /api/sark/analytics/hourly` - Hourly breakdown
- `GET /api/sark/analytics/daily?days=N` - Daily breakdown
- `GET /api/sark/analytics/users` - Per-user statistics
- `GET /api/sark/analytics/models` - Per-model statistics
- `GET /api/sark/analytics/costs` - Cost breakdown
- `GET /api/sark/analytics/violations` - Policy violations
- `GET /api/sark/analytics/realtime` - Real-time stats
- `GET /api/sark/analytics/export?format=csv` - Export data
- `GET /api/sark/analytics/logs` - Query logs

### Models

#### General.xml
Main configuration model stored at `//OPNsense/SARK/general` in config.xml.

**Settings:**
- Service configuration (enabled, mode, listen address/port)
- Budget controls (token limits, cost limits)
- Time controls (bedtime hours)
- Users array (name, role, limits)
- Providers array (API configuration)

#### Policy.xml
Policy configuration model stored at `//OPNsense/SARK/policy`.

**Settings:**
- Built-in policy toggles
- Model allowlist
- Homework mode settings
- PII protection settings
- Custom rules array

### Views (Volt Templates)

All views use Bootstrap 3 (OPNsense default) and Chart.js for visualization.

#### index.volt
Dashboard with:
- Service status and controls
- Statistics cards (requests, tokens, cost, violations)
- Hourly usage chart
- User breakdown pie chart
- Quick action links

#### settings.volt
Configuration page with tabs:
- General (service settings)
- Budget (limits and bedtime)
- Users (household member management)
- Providers (API provider configuration)

#### policies.volt
Policy management with tabs:
- Built-in policies (toggles)
- Custom rules (CRUD table)
- Homework mode settings
- PII protection settings

#### logs.volt
Audit log viewer with:
- Filters (level, user, limit)
- Paginated log table
- Log detail modal
- Recent violations panel
- Export functionality

### Service Integration

#### actions_sark.conf
Configd actions for backend communication:
- Service control (start/stop/restart/status)
- Policy reload
- Analytics queries
- Log queries

#### rc.d/sark
FreeBSD service script:
- Standard rc.d interface
- Pre-start directory creation
- Config test command
- Reload (HUP) support

## Development

### Prerequisites

- OPNsense development environment
- PHP 8.1+
- FreeBSD pkg tools

### Building the Plugin

```bash
# From the opnsense directory
make package
```

### Installing for Development

```bash
# Copy files to OPNsense
scp -r src/* root@opnsense:/usr/local/

# Restart configd
service configd restart

# Clear template cache
rm -rf /tmp/cache/*
```

### Testing

1. Access OPNsense web UI
2. Navigate to Services > SARK Home Gateway
3. Verify all pages load correctly
4. Test API endpoints with curl:

```bash
# Get status
curl -k https://opnsense/api/sark/service/status

# Start service
curl -k -X POST https://opnsense/api/sark/service/start
```

### Debugging

- Check `/var/log/configd.log` for backend errors
- Check `/var/log/sark/sark.log` for service logs
- Enable debug logging in Settings

## Configuration Storage

All configuration is stored in `/conf/config.xml` under:
- `//OPNsense/SARK/general` - General settings
- `//OPNsense/SARK/policy` - Policy settings

## API Authentication

All API endpoints require OPNsense authentication. Use either:
- Session cookie (web UI)
- API key/secret (for automation)

## Dependencies

- python311
- py311-fastapi
- py311-uvicorn
- py311-pydantic
- py311-httpx
- py311-yaml

## Security Considerations

- API keys are stored encrypted in config.xml
- TLS is enabled by default
- All API endpoints require authentication
- PII redaction protects sensitive data

## Version History

- 2.0.0 - Initial release with full governance features
