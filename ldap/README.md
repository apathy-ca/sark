# SARK LDAP Sample Users and Authentication

This directory contains OpenLDAP configuration and sample users for SARK tutorials and development.

⚠️ **WARNING:** These users and passwords are for **development and tutorial purposes ONLY**. **DO NOT** use in production.

---

## Quick Start

The OpenLDAP service is automatically started when using any Docker Compose profile:

```bash
# Start SARK with minimal profile (includes OpenLDAP)
docker compose --profile minimal up -d

# Verify LDAP is running
docker compose ps openldap

# Test LDAP connection
docker compose exec openldap ldapsearch -x -H ldap://localhost \
  -b "dc=sark,dc=local" -D "cn=admin,dc=sark,dc=local" -w admin
```

---

## Sample Users

All users have the password: `password` (except `admin` which uses `admin`)

### 1. john.doe - Developer & Team Lead

**Username:** `john.doe`
**Password:** `password`
**Email:** john.doe@sark.local

**Roles:**
- `developer`
- `team_lead`

**Teams:**
- `engineering`
- `platform`

**Permissions:**
- Server registration (can register MCP servers)
- Tool invocation up to `high` sensitivity
- Access during business hours (9 AM - 6 PM)
- Team-based access to engineering tools

**Tutorial Use:**
- Tutorial 1: Basic Setup (primary user)
- Tutorial 2: Authentication Deep Dive
- Policy demonstrations

**OPA Policy Behavior:**
```rego
# john.doe can:
- Invoke low/medium/high sensitivity tools during work hours
- Register new MCP servers
- Access tools owned by engineering team
- Cannot access critical tools outside work hours
```

---

### 2. jane.smith - Junior Developer

**Username:** `jane.smith`
**Password:** `password`
**Email:** jane.smith@sark.local

**Roles:**
- `developer`

**Teams:**
- `engineering`

**Permissions:**
- Limited server registration
- Tool invocation up to `medium` sensitivity only
- Access during business hours
- Team-based access to engineering tools

**Tutorial Use:**
- Demonstrating policy denials (attempts high-sensitivity tool)
- Role-based access control examples
- Least privilege demonstrations

**OPA Policy Behavior:**
```rego
# jane.smith can:
- Invoke low/medium sensitivity tools during work hours
- Register servers (developer role)
- Access engineering team tools
# jane.smith CANNOT:
- Invoke high or critical sensitivity tools
- Override security policies
```

---

### 3. admin - System Administrator

**Username:** `admin`
**Password:** `admin`
**Email:** admin@sark.local

**Roles:**
- `admin`
- `security_admin`

**Teams:**
- `admins`
- `security`

**Permissions:**
- Full server management
- Tool invocation up to `critical` sensitivity
- Policy override capabilities
- Unrestricted time-based access

**Tutorial Use:**
- Administration examples
- Policy management
- Break-glass access demonstrations

**OPA Policy Behavior:**
```rego
# admin can:
- Invoke any tool (low/medium/high/critical)
- Access at any time (no time restrictions)
- Override most policy constraints
- Manage all servers and policies
```

---

### 4. alice.engineer - Data Engineer

**Username:** `alice.engineer`
**Password:** `password`
**Email:** alice.engineer@sark.local

**Roles:**
- `data_engineer`

**Teams:**
- `data-engineering`
- `analytics`

**Permissions:**
- Database query tools
- Analytics and reporting tools
- Data export up to `medium` sensitivity

**Tutorial Use:**
- Database query tool examples
- Data analysis workflows
- Team-based policy demonstrations

**OPA Policy Behavior:**
```rego
# alice.engineer can:
- Execute database queries on analytics/reporting databases
- Generate reports and exports
- Access data-engineering team tools
# alice.engineer CANNOT:
- Modify production databases
- Access non-analytics tools
```

---

### 5. bob.security - Security Engineer

**Username:** `bob.security`
**Password:** `password`
**Email:** bob.security@sark.local

**Roles:**
- `security_engineer`
- `auditor`

**Teams:**
- `security`
- `compliance`

**Permissions:**
- Security tool access
- Audit log viewing
- Critical security operations (with MFA)

**Tutorial Use:**
- Security policy examples
- MFA requirement demonstrations
- Audit trail analysis

**OPA Policy Behavior:**
```rego
# bob.security can:
- Access security and compliance tools
- View all audit logs
- Perform security scans
- Require MFA for critical ops
# bob.security CANNOT:
- Access non-security tools without team ownership
- Bypass MFA requirements
```

---

### 6. carol.analyst - Data Analyst

**Username:** `carol.analyst`
**Password:** `password`
**Email:** carol.analyst@sark.local

**Roles:**
- `analyst`

**Teams:**
- `data-engineering`
- `analytics`

**Permissions:**
- Read-only database queries
- Report generation
- Limited to `low` sensitivity data

**Tutorial Use:**
- Read-only access patterns
- Data masking demonstrations
- Limited permission examples

**OPA Policy Behavior:**
```rego
# carol.analyst can:
- Execute SELECT queries only (no DELETE/UPDATE/INSERT)
- Access analytics database (read-only)
- Generate reports from query results
# carol.analyst CANNOT:
- Modify any data
- Access sensitive PII columns
- Invoke write operations
```

---

### 7. dave.devops - DevOps Engineer

**Username:** `dave.devops`
**Password:** `password`
**Email:** dave.devops@sark.local

**Roles:**
- `devops`
- `infrastructure`

**Teams:**
- `devops`
- `infrastructure`

**Permissions:**
- Infrastructure tools
- Deployment automation
- Server management

**Tutorial Use:**
- Infrastructure automation examples
- CI/CD integration patterns
- API key usage examples

**OPA Policy Behavior:**
```rego
# dave.devops can:
- Manage infrastructure tools
- Deploy and configure servers
- Access deployment automation tools
# dave.devops CANNOT:
- Access application data directly
- Modify security policies
```

---

## LDAP Groups

### developers
**Members:** john.doe, jane.smith
**GID:** 1001
**Purpose:** Software development team

### data-engineering
**Members:** alice.engineer, carol.analyst
**GID:** 1002
**Purpose:** Data engineering and analytics

### security
**Members:** bob.security
**GID:** 1003
**Purpose:** Security and compliance team

### devops
**Members:** dave.devops
**GID:** 1004
**Purpose:** DevOps and infrastructure

### admins
**Members:** admin
**GID:** 1000
**Purpose:** System administrators

### team-leads
**Members:** john.doe
**GID:** 2000
**Purpose:** Team leads with elevated permissions

---

## Directory Structure

```
ldap/
├── README.md                    # This file
└── bootstrap/
    └── 01-users.ldif           # LDAP user definitions
```

---

## Testing LDAP Authentication

### Test User Bind

```bash
# Test john.doe authentication
docker compose exec openldap ldapwhoami -x \
  -H ldap://localhost \
  -D "uid=john.doe,ou=people,dc=sark,dc=local" \
  -w password

# Expected: dn:uid=john.doe,ou=people,dc=sark,dc=local
```

### Search for All Users

```bash
# List all users
docker compose exec openldap ldapsearch -x \
  -H ldap://localhost \
  -b "ou=people,dc=sark,dc=local" \
  -D "cn=admin,dc=sark,dc=local" \
  -w admin \
  "(objectClass=inetOrgPerson)" uid cn mail

# Returns all 7 users with their attributes
```

### Search for Groups

```bash
# List all groups
docker compose exec openldap ldapsearch -x \
  -H ldap://localhost \
  -b "ou=groups,dc=sark,dc=local" \
  -D "cn=admin,dc=sark,dc=local" \
  -w admin \
  "(objectClass=posixGroup)" cn member

# Returns all 6 groups with members
```

---

## Integration with SARK

SARK automatically connects to OpenLDAP using environment variables in docker-compose.yml:

```yaml
- LDAP_ENABLED=true
- LDAP_SERVER=ldap://openldap:389
- LDAP_BASE_DN=dc=sark,dc=local
- LDAP_USER_DN=ou=people,dc=sark,dc=local
- LDAP_BIND_DN=cn=admin,dc=sark,dc=local
- LDAP_BIND_PASSWORD=admin
```

### Authenticate via SARK API

```bash
# Authenticate as john.doe
curl -X POST http://localhost:8000/api/v1/auth/login/ldap \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john.doe",
    "password": "password"
  }' | jq

# Returns JWT access token and user profile
```

---

## Role Mapping

SARK maps LDAP groups to roles:

| LDAP Group | SARK Role | Sensitivity Access |
|------------|-----------|-------------------|
| admins | admin | critical |
| team-leads | team_lead | high |
| developers | developer | medium |
| data-engineering | data_engineer | medium |
| security | security_engineer | high |
| devops | devops | medium |
| analysts | analyst | low |

---

## Troubleshooting

### OpenLDAP Won't Start

```bash
# Check logs
docker compose logs openldap

# Common issues:
# - Port 389 already in use
# - Volume permissions
# - LDIF syntax errors

# Fix: Stop conflicting services
lsof -i :389
sudo systemctl stop slapd  # If running system LDAP

# Restart
docker compose --profile minimal restart openldap
```

### Users Not Found

```bash
# Verify LDIF was loaded
docker compose exec openldap ldapsearch -x \
  -H ldap://localhost \
  -b "dc=sark,dc=local" \
  -D "cn=admin,dc=sark,dc=local" \
  -w admin \
  "(uid=john.doe)"

# If empty, check bootstrap volume mount
docker compose exec openldap ls -la /container/service/slapd/assets/config/bootstrap/ldif/custom/
```

### Authentication Fails

```bash
# Test LDAP bind directly
docker compose exec openldap ldapwhoami -x \
  -H ldap://localhost \
  -D "uid=john.doe,ou=people,dc=sark,dc=local" \
  -w password

# Check SARK logs
docker compose logs app | grep -i ldap

# Verify SARK can reach OpenLDAP
docker compose exec app curl ldap://openldap:389
```

---

## Adding Custom Users

To add your own test users:

1. Create a new LDIF file in `ldap/bootstrap/`
2. Follow the format in `01-users.ldif`
3. Restart OpenLDAP service

Example:

```ldif
# ldap/bootstrap/02-custom-users.ldif
dn: uid=myuser,ou=people,dc=sark,dc=local
objectClass: inetOrgPerson
objectClass: posixAccount
objectClass: shadowAccount
uid: myuser
cn: My User
sn: User
mail: myuser@sark.local
userPassword: {SSHA}mypassword
uidNumber: 2001
gidNumber: 1001
homeDirectory: /home/myuser
loginShell: /bin/bash
```

Then restart:
```bash
docker compose --profile minimal restart openldap
```

---

## Security Considerations

⚠️ **These sample users are for development ONLY**

### DO NOT in Production:
- Use default passwords (`password`, `admin`)
- Use plain LDAP (port 389 without TLS)
- Expose LDAP port publicly
- Use same users across environments

### Production LDAP Best Practices:
- Use LDAPS (LDAP over TLS) on port 636
- Integrate with corporate Active Directory or identity provider
- Use strong, unique passwords (or SSH keys)
- Enable MFA for critical accounts
- Restrict LDAP network access with firewalls
- Use read-only bind accounts for SARK integration
- Regular security audits and password rotation

---

## Related Documentation

- **[Tutorial 1: Basic Setup](../tutorials/01-basic-setup/README.md)** - Uses john.doe for walkthrough
- **[Tutorial 2: Authentication](../tutorials/02-authentication/README.md)** - All auth methods
- **[OPA Policies](../opa/policies/README.md)** - Role-based access control
- **[Quick Start Guide](../docs/QUICK_START.md)** - Complete setup instructions

---

**Ready to authenticate?** Start with [Tutorial 1: Basic Setup](../tutorials/01-basic-setup/README.md)
