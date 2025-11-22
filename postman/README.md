# SARK Postman Collection

This directory contains the Postman collection and environment templates for testing the SARK API.

## Contents

- **SARK_API.postman_collection.json**: Complete API collection with all endpoints
- **SARK_Local.postman_environment.json**: Environment for local development
- **SARK_Staging.postman_environment.json**: Environment for staging
- **SARK_Production.postman_environment.json**: Environment for production

## Quick Start

### 1. Import Collection

1. Open Postman
2. Click **Import** button
3. Select `SARK_API.postman_collection.json`
4. Collection will appear in left sidebar

### 2. Import Environment

1. Click **Import** again
2. Select the environment file for your target:
   - `SARK_Local.postman_environment.json` for local testing
   - `SARK_Staging.postman_environment.json` for staging
   - `SARK_Production.postman_environment.json` for production
3. Select the environment from the dropdown in top-right corner

### 3. Configure Environment Variables

Update the environment variables:

- **baseUrl**: API base URL (pre-configured for each environment)
- **ldapUsername**: Your LDAP username
- **ldapPassword**: Your LDAP password
- **accessToken**: Auto-populated after login
- **refreshToken**: Auto-populated after login
- **apiKey**: Auto-populated after creating API key

### 4. Authenticate

Choose an authentication method:

#### Option A: LDAP Login

1. Navigate to **Authentication → LDAP Login**
2. Update `ldapUsername` and `ldapPassword` in environment
3. Click **Send**
4. Access token will be automatically saved to environment

#### Option B: OIDC Login

1. Navigate to **Authentication → OIDC Login - Initiate**
2. Copy the redirect URL from response
3. Complete authentication in browser
4. Extract `code` and `state` from callback URL
5. Use **Authentication → OIDC Callback** with extracted values

#### Option C: API Key

1. First authenticate with LDAP/OIDC
2. Navigate to **API Keys → Create API Key**
3. Click **Send**
4. API key will be automatically saved to environment
5. Update collection auth to use API key instead of JWT

## Collection Structure

### 1. Authentication

- **LDAP Login**: Authenticate via LDAP/Active Directory
- **OIDC Login**: OAuth 2.0 / OpenID Connect authentication
- **SAML Login**: SAML 2.0 SSO authentication
- **Refresh Token**: Get new access token using refresh token
- **Revoke Token**: Logout (invalidate refresh token)
- **Get Current User**: Verify authentication and get user info

### 2. API Keys

- **Create API Key**: Generate new API key with scopes
- **List API Keys**: View all your API keys
- **Get API Key**: Get details of specific key
- **Rotate API Key**: Generate new key, invalidate old
- **Revoke API Key**: Delete API key

### 3. Servers

- **Register Server**: Register new MCP server (requires authorization)
- **Get Server**: Get server details by ID
- **List Servers**: Paginated server listing
- **Search and Filter**: Advanced search with multiple filters

### 4. Bulk Operations

- **Bulk Register Servers**: Register multiple servers at once
  - **Transactional mode**: All or nothing
  - **Best-effort mode**: Partial success allowed

### 5. Policy Evaluation

- **Evaluate Policy**: Test OPA policy decisions
  - Returns: allow/deny, reasons, filtered parameters

### 6. Tools

- **Get Tool Sensitivity**: Get current sensitivity level
- **Set Tool Sensitivity**: Manually override sensitivity
- **Detect Tool Sensitivity**: Auto-detect based on name/description
- **Get Sensitivity History**: View sensitivity changes over time
- **Get Sensitivity Statistics**: Aggregate stats on all tools

### 7. Health & Monitoring

- **Health Check**: Basic health (200 = up)
- **Detailed Health**: Database, Redis, OPA, SIEM status
- **Liveness Probe**: Kubernetes liveness
- **Readiness Probe**: Kubernetes readiness
- **Startup Probe**: Kubernetes startup

## Authentication

The collection uses Bearer token authentication by default. After logging in via LDAP/OIDC, the `accessToken` variable is automatically set and used for subsequent requests.

### JWT Token Flow

```
1. Login (LDAP/OIDC/SAML)
   ↓
2. Receive access_token + refresh_token
   ↓
3. Use access_token for API requests (60 min TTL)
   ↓
4. When access_token expires, use refresh_token to get new access_token
   ↓
5. Repeat step 3-4 (refresh_token valid for 7 days)
```

### API Key Flow

```
1. Authenticate with JWT first
   ↓
2. Create API Key
   ↓
3. Save API key
   ↓
4. Use API key for all subsequent requests (no expiration)
```

## Example Workflows

### Workflow 1: Register a Server

```
1. Authentication → LDAP Login
2. Servers → Register Server
   - Modify request body with your server details
3. Servers → Get Server (using saved serverId)
```

### Workflow 2: Bulk Server Registration

```
1. Authentication → LDAP Login
2. Bulk Operations → Bulk Register Servers
   - Modify servers array in request body
   - Choose mode: "transactional" or "best-effort"
```

### Workflow 3: Test Policy Authorization

```
1. Authentication → LDAP Login
2. Policy Evaluation → Evaluate Policy
   - Modify action, resource, and context
   - View allow/deny decision and reasons
```

### Workflow 4: Manage Tool Sensitivity

```
1. Authentication → LDAP Login
2. Tools → Detect Tool Sensitivity
   - Provide tool name and description
   - View auto-detected sensitivity level
3. Tools → Set Tool Sensitivity (optional override)
4. Tools → Get Sensitivity History (view changes)
```

## Environment Variables

### Auto-Populated (Don't Edit)

- `accessToken`: JWT access token (auto-set after login)
- `refreshToken`: JWT refresh token (auto-set after login)
- `apiKey`: API key (auto-set after creation)
- `apiKeyId`: API key UUID (auto-set after creation)
- `serverId`: Server UUID (auto-set after registration)
- `toolId`: Tool identifier (set manually or from response)

### Manual Configuration

- `baseUrl`: API base URL
- `ldapUsername`: Your LDAP username
- `ldapPassword`: Your LDAP password
- `authCode`: OIDC authorization code (from callback)
- `state`: OIDC state parameter (from callback)

## Testing Scripts

The collection includes test scripts that automatically:

- Save tokens after successful authentication
- Save API key after creation
- Save server ID after registration
- Log important values to console

View test results in the **Test Results** tab after sending requests.

## Troubleshooting

### 401 Unauthorized

- **Cause**: Access token expired or invalid
- **Solution**: Re-authenticate or refresh token
  1. Try **Authentication → Refresh Token**
  2. If refresh fails, login again with **LDAP Login** or **OIDC Login**

### 403 Forbidden

- **Cause**: Policy denied access
- **Solution**: Check OPA policies and user permissions
  1. Verify user roles: **Authentication → Get Current User**
  2. Test policy: **Policy Evaluation → Evaluate Policy**

### 503 Service Unavailable

- **Cause**: Backend service down (Database, Redis, OPA)
- **Solution**: Check service health
  1. **Health & Monitoring → Detailed Health Check**
  2. Contact ops team if services are down

### Rate Limiting (429)

- **Cause**: Too many requests
- **Solution**: Wait or use API key with higher rate limit
  1. Check `X-RateLimit-Reset` header for reset time
  2. Create API key with custom rate limit

## Advanced Usage

### Using Pre-request Scripts

Add custom logic before requests:

```javascript
// Example: Add timestamp to request
pm.environment.set("timestamp", new Date().toISOString());
```

### Using Collection Runner

1. Click **Runner** button
2. Select **SARK API Collection**
3. Select environment
4. Click **Run**
5. View results for all requests

### Exporting Test Results

1. After running requests, click **View Results**
2. Export results as JSON or HTML

## API Documentation

For complete API documentation, see:
- [API_REFERENCE.md](../docs/API_REFERENCE.md)
- [AUTHENTICATION.md](../docs/AUTHENTICATION.md)
- [AUTHORIZATION.md](../docs/AUTHORIZATION.md)

## Support

For issues or questions:
- GitHub Issues: https://github.com/your-org/sark/issues
- Documentation: https://docs.sark.example.com
