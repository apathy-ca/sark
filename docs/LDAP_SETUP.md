# LDAP/Active Directory Setup Guide

Complete guide to configuring LDAP and Active Directory authentication in SARK.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Basic Configuration](#basic-configuration)
- [Active Directory Setup](#active-directory-setup)
- [OpenLDAP Setup](#openldap-setup)
- [Advanced Configuration](#advanced-configuration)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## Overview

SARK supports LDAP (Lightweight Directory Access Protocol) and Active Directory for corporate directory authentication. This enables:

- **Single Source of Truth**: Authenticate against existing corporate directory
- **No Password Storage**: Credentials validated directly against LDAP
- **Group Membership**: Automatic role mapping from LDAP groups
- **Connection Pooling**: Efficient connection management
- **SSL/TLS Support**: Secure communication with LDAP server

### How It Works

```
1. User submits username/password
2. SARK connects to LDAP using service account
3. Search for user DN by username
4. Bind as user with provided password (validates credentials)
5. Retrieve user attributes and group membership
6. Create session with user info
7. Access granted
```

## Prerequisites

- LDAP server or Active Directory domain controller
- Service account with read access to users and groups
- Network connectivity from SARK to LDAP server
- LDAP server details (host, port, base DN)

## Basic Configuration

### Minimum Configuration

```bash
# Enable LDAP
LDAP_ENABLED=true

# LDAP server
LDAP_SERVER=ldap://ldap.example.com:389

# Service account credentials
LDAP_BIND_DN=cn=sark-service,ou=service-accounts,dc=example,dc=com
LDAP_BIND_PASSWORD=service-account-password

# Base DN for user searches
LDAP_USER_BASE_DN=ou=users,dc=example,dc=com
```

### Full Configuration

```bash
# LDAP server (use ldaps:// for SSL)
LDAP_SERVER=ldaps://ldap.example.com:636

# Service account
LDAP_BIND_DN=cn=sark-service,ou=service-accounts,dc=example,dc=com
LDAP_BIND_PASSWORD=your-password-here

# Search bases
LDAP_USER_BASE_DN=ou=users,dc=example,dc=com
LDAP_GROUP_BASE_DN=ou=groups,dc=example,dc=com

# Search filters
LDAP_USER_SEARCH_FILTER=(uid={username})
LDAP_GROUP_SEARCH_FILTER=(member={user_dn})

# Attribute mappings
LDAP_EMAIL_ATTRIBUTE=mail
LDAP_NAME_ATTRIBUTE=cn
LDAP_GIVEN_NAME_ATTRIBUTE=givenName
LDAP_FAMILY_NAME_ATTRIBUTE=sn

# Security
LDAP_USE_SSL=true

# Performance
LDAP_POOL_SIZE=10
```

## Active Directory Setup

### Prerequisites

- Active Directory domain controller
- Service account in AD
- Admin access to create service account (if needed)

### Step 1: Create Service Account

Create a service account in Active Directory:

1. Open "Active Directory Users and Computers"
2. Navigate to appropriate OU (e.g., `OU=Service Accounts`)
3. Right-click → New → User
4. Username: `sark-service`
5. Set password (non-expiring recommended)
6. Uncheck "User must change password at next logon"
7. Check "Password never expires"

### Step 2: Grant Permissions

The service account needs read access:

1. Right-click the domain → Properties
2. Security tab → Advanced
3. Add → Select Principal → `sark-service`
4. Permissions:
   - Read all properties
   - List contents
5. Apply to "This object and all descendant objects"

### Step 3: Get Configuration Details

```powershell
# Get domain DN
Get-ADDomain | Select-Object -ExpandProperty DistinguishedName
# Output: DC=example,DC=com

# Get user base DN
Get-ADOrganizationalUnit -Filter 'Name -eq "Users"' | Select-Object DistinguishedName
# Output: OU=Users,DC=example,DC=com

# Get domain controllers
Get-ADDomainController -Filter * | Select-Object HostName
# Output: dc1.example.com
```

### Step 4: Configure SARK

```bash
# Enable LDAP
LDAP_ENABLED=true

# Active Directory server (use LDAPS port 636 for SSL)
LDAP_SERVER=ldaps://dc1.example.com:636

# Service account
LDAP_BIND_DN=CN=sark-service,OU=Service Accounts,DC=example,DC=com
LDAP_BIND_PASSWORD=your-service-account-password

# Search bases
LDAP_USER_BASE_DN=OU=Users,DC=example,DC=com
LDAP_GROUP_BASE_DN=OU=Groups,DC=example,DC=com

# Active Directory search filters
LDAP_USER_SEARCH_FILTER=(sAMAccountName={username})
LDAP_GROUP_SEARCH_FILTER=(member={user_dn})

# Active Directory attributes
LDAP_EMAIL_ATTRIBUTE=mail
LDAP_NAME_ATTRIBUTE=displayName
LDAP_GIVEN_NAME_ATTRIBUTE=givenName
LDAP_FAMILY_NAME_ATTRIBUTE=sn

# Use SSL
LDAP_USE_SSL=true
```

### Active Directory-Specific Notes

**User Principal Name (UPN) Login:**
```bash
# Allow login with email@domain.com
LDAP_USER_SEARCH_FILTER=(userPrincipalName={username})
```

**Multiple Filters:**
```bash
# Support both sAMAccountName and UPN
LDAP_USER_SEARCH_FILTER=(|(sAMAccountName={username})(userPrincipalName={username}))
```

**Nested Groups:**

Active Directory supports nested groups. SARK recursively resolves group membership.

```python
# Automatically resolves nested groups
groups = await ldap_provider._get_user_groups(user_dn)
# Returns: ['CN=Developers,OU=Groups,DC=example,DC=com', ...]
```

## OpenLDAP Setup

### Prerequisites

- OpenLDAP server
- Admin access to create service account
- LDAP schema configured

### Step 1: Create Service Account

```bash
# Create LDIF file: sark-service.ldif
dn: cn=sark-service,ou=service-accounts,dc=example,dc=com
objectClass: organizationalRole
objectClass: simpleSecurityObject
cn: sark-service
userPassword: {SSHA}hashedpassword
description: SARK authentication service account

# Add to LDAP
ldapadd -x -D "cn=admin,dc=example,dc=com" -W -f sark-service.ldif
```

### Step 2: Set Permissions (ACL)

```bash
# In slapd.conf or cn=config
access to dn.subtree="ou=users,dc=example,dc=com"
  by dn="cn=sark-service,ou=service-accounts,dc=example,dc=com" read
  by * none

access to dn.subtree="ou=groups,dc=example,dc=com"
  by dn="cn=sark-service,ou=service-accounts,dc=example,dc=com" read
  by * none
```

### Step 3: Configure SARK

```bash
# Enable LDAP
LDAP_ENABLED=true

# OpenLDAP server
LDAP_SERVER=ldap://ldap.example.com:389

# Service account
LDAP_BIND_DN=cn=sark-service,ou=service-accounts,dc=example,dc=com
LDAP_BIND_PASSWORD=your-password

# Search bases
LDAP_USER_BASE_DN=ou=users,dc=example,dc=com
LDAP_GROUP_BASE_DN=ou=groups,dc=example,dc=com

# OpenLDAP filters (standard)
LDAP_USER_SEARCH_FILTER=(uid={username})
LDAP_GROUP_SEARCH_FILTER=(memberUid={username})

# Standard LDAP attributes
LDAP_EMAIL_ATTRIBUTE=mail
LDAP_NAME_ATTRIBUTE=cn
LDAP_GIVEN_NAME_ATTRIBUTE=givenName
LDAP_FAMILY_NAME_ATTRIBUTE=sn

# SSL (if using LDAPS)
LDAP_USE_SSL=false
```

### OpenLDAP Group Membership

OpenLDAP typically uses `memberUid` or `member` for groups:

```bash
# For memberUid (stores username)
LDAP_GROUP_SEARCH_FILTER=(memberUid={username})

# For member (stores full DN)
LDAP_GROUP_SEARCH_FILTER=(member={user_dn})
```

## Advanced Configuration

### SSL/TLS Configuration

#### Using LDAPS (LDAP over SSL)

```bash
# Use ldaps:// protocol and port 636
LDAP_SERVER=ldaps://ldap.example.com:636
LDAP_USE_SSL=true
```

#### Using StartTLS

```bash
# Use ldap:// but enable TLS
LDAP_SERVER=ldap://ldap.example.com:389
LDAP_USE_SSL=true
LDAP_START_TLS=true  # Not currently supported, coming soon
```

#### Certificate Validation

For self-signed certificates:

```bash
# Development only - skip certificate validation
export LDAPTLS_REQCERT=never

# Production - specify CA certificate
export LDAPTLS_CACERT=/path/to/ca-cert.pem
```

### Connection Pooling

Optimize performance with connection pooling:

```bash
# Number of connections to maintain
LDAP_POOL_SIZE=10
```

Benefits:
- Reduced latency (reuse connections)
- Better performance under load
- Efficient resource usage

### Custom Search Filters

#### Support Multiple Username Formats

```bash
# Active Directory: support sAMAccountName, UPN, and email
LDAP_USER_SEARCH_FILTER=(|(sAMAccountName={username})(userPrincipalName={username})(mail={username}))
```

#### Filter by Organizational Unit

```bash
# Only search in specific OU
LDAP_USER_SEARCH_FILTER=(&(uid={username})(ou=employees))
```

#### Filter by Account Status

```bash
# Active Directory: only enabled accounts
LDAP_USER_SEARCH_FILTER=(&(sAMAccountName={username})(!(userAccountControl:1.2.840.113556.1.4.803:=2)))
```

### Group-Based Access Control

Restrict access to specific groups:

```python
# In your authentication flow
user_info = await ldap_provider.authenticate(credentials)

# Check group membership
required_groups = ['CN=SARK Users,OU=Groups,DC=example,DC=com']
user_groups = user_info.additional_attributes.get('groups', [])

if not any(group in required_groups for group in user_groups):
    raise PermissionError("User not in authorized group")
```

### Attribute Mapping

Map LDAP attributes to user fields:

```bash
# Default mappings
LDAP_EMAIL_ATTRIBUTE=mail
LDAP_NAME_ATTRIBUTE=cn
LDAP_GIVEN_NAME_ATTRIBUTE=givenName
LDAP_FAMILY_NAME_ATTRIBUTE=sn

# Custom attributes
LDAP_EMPLOYEE_ID_ATTRIBUTE=employeeNumber
LDAP_PHONE_ATTRIBUTE=telephoneNumber
LDAP_DEPARTMENT_ATTRIBUTE=department
```

Access custom attributes:

```python
user_info = await ldap_provider.authenticate(credentials)
employee_id = user_info.additional_attributes.get('employeeNumber')
department = user_info.additional_attributes.get('department')
```

## Testing

### Test LDAP Connectivity

```bash
# Test connection with ldapsearch
ldapsearch -x -H ldap://ldap.example.com:389 \
  -D "cn=sark-service,ou=service-accounts,dc=example,dc=com" \
  -w "password" \
  -b "dc=example,dc=com" \
  "(objectClass=*)" dn
```

### Test User Search

```bash
# Search for specific user
ldapsearch -x -H ldap://ldap.example.com:389 \
  -D "cn=sark-service,ou=service-accounts,dc=example,dc=com" \
  -w "password" \
  -b "ou=users,dc=example,dc=com" \
  "(uid=jdoe)"
```

### Test Authentication in SARK

```bash
# Start SARK
python -m sark

# Test login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ldap",
    "username": "jdoe",
    "password": "secret"
  }'
```

### Test Group Resolution

```python
import asyncio
from sark.services.auth.providers import LDAPProvider

async def test_groups():
    provider = LDAPProvider(
        server_uri="ldap://ldap.example.com:389",
        bind_dn="cn=sark-service,ou=service-accounts,dc=example,dc=com",
        bind_password="password",
        user_base_dn="ou=users,dc=example,dc=com",
        group_base_dn="ou=groups,dc=example,dc=com"
    )

    user_info = await provider.authenticate({
        "username": "jdoe",
        "password": "secret"
    })

    print(f"User: {user_info.email}")
    print(f"Groups: {user_info.additional_attributes.get('groups', [])}")

asyncio.run(test_groups())
```

## Troubleshooting

### Connection Issues

#### "Can't contact LDAP server"

**Cause**: Network connectivity or firewall

**Solution**:
```bash
# Test connectivity
telnet ldap.example.com 389

# Test with ldapsearch
ldapsearch -x -H ldap://ldap.example.com:389 -b "" -s base
```

#### "Invalid credentials"

**Cause**: Wrong service account credentials

**Solution**:
1. Verify bind DN format (use full DN, not username)
2. Check password (no quotes in `.env`)
3. Test with ldapsearch:
   ```bash
   ldapsearch -x -H ldap://ldap.example.com:389 \
     -D "cn=sark-service,ou=service-accounts,dc=example,dc=com" \
     -w "password" \
     -b "dc=example,dc=com"
   ```

### Search Issues

#### "No such object"

**Cause**: Incorrect base DN

**Solution**:
```bash
# Find correct base DN
ldapsearch -x -H ldap://ldap.example.com:389 \
  -D "cn=admin,dc=example,dc=com" \
  -w "password" \
  -b "" \
  -s base \
  namingContexts
```

#### User not found

**Cause**: Wrong search filter or base DN

**Solution**:
```bash
# Test search filter
ldapsearch -x -H ldap://ldap.example.com:389 \
  -D "cn=sark-service,ou=service-accounts,dc=example,dc=com" \
  -w "password" \
  -b "ou=users,dc=example,dc=com" \
  "(uid=jdoe)"

# If no results, check:
# 1. User exists in that OU
# 2. Search filter is correct for your schema
# 3. Service account has read permissions
```

### Authentication Issues

#### Bind fails after user found

**Cause**: User DN incorrect or password wrong

**Solution**:
```bash
# Test user bind directly
ldapsearch -x -H ldap://ldap.example.com:389 \
  -D "uid=jdoe,ou=users,dc=example,dc=com" \
  -w "userpassword" \
  -b "dc=example,dc=com" \
  "(uid=jdoe)"
```

### SSL/TLS Issues

#### "TLS not available"

**Cause**: SSL not configured on LDAP server

**Solution**:
```bash
# Check if LDAPS is available
openssl s_client -connect ldap.example.com:636

# Or use non-SSL
LDAP_USE_SSL=false
LDAP_SERVER=ldap://ldap.example.com:389
```

#### "Certificate verify failed"

**Cause**: Self-signed certificate or CA not trusted

**Solution**:
```bash
# Development: skip verification (NOT for production)
export LDAPTLS_REQCERT=never

# Production: add CA certificate
export LDAPTLS_CACERT=/path/to/ca-cert.pem
```

### Performance Issues

#### Slow authentication

**Cause**: Connection not pooled or slow LDAP server

**Solution**:
```bash
# Increase pool size
LDAP_POOL_SIZE=20

# Monitor connection usage
# Check LDAP server performance
```

#### Too many connections

**Cause**: Pool size too high

**Solution**:
```bash
# Reduce pool size
LDAP_POOL_SIZE=5
```

### Debug Mode

Enable detailed logging:

```bash
LOG_LEVEL=DEBUG
```

Logs will show:
- Connection attempts
- Search queries
- Bind attempts
- Attribute retrieval
- Group resolution

## Security Best Practices

1. **Use SSL/TLS**
   ```bash
   LDAP_SERVER=ldaps://ldap.example.com:636
   LDAP_USE_SSL=true
   ```

2. **Limit Service Account Permissions**
   - Grant only read access to user and group OUs
   - Never use admin account

3. **Secure Service Account Password**
   - Use strong, random password
   - Store in environment variables or vault
   - Rotate periodically

4. **Network Segmentation**
   - Restrict LDAP server access to specific IPs
   - Use firewall rules

5. **Monitor Failed Authentications**
   - Enable audit logging
   - Alert on repeated failures
   - Lock accounts after threshold

6. **Validate Group Membership**
   - Require specific groups for access
   - Map groups to roles

## Next Steps

- [Session Management](./AUTHENTICATION.md#session-management)
- [Rate Limiting](./AUTHENTICATION.md#rate-limiting)
- [OIDC Setup](./OIDC_SETUP.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)

## Support

- GitHub Issues: https://github.com/apathy-ca/sark/issues
- Documentation: https://sark.readthedocs.io
