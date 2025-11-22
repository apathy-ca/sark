# SAML 2.0 Setup Guide

Guide to configuring SAML 2.0 Enterprise SSO authentication in SARK.

## Overview

SARK supports SAML 2.0 for enterprise single sign-on integration.

### Features

- SP-initiated and IdP-initiated flows
- Encrypted assertions
- Single Logout (SLO)
- Multiple IdP support

## Quick Start

### 1. Configure Service Provider (SARK)

```bash
# Enable SAML
SAML_ENABLED=true

# SP Entity ID (your SARK URL)
SAML_SP_ENTITY_ID=https://sark.example.com

# Assertion Consumer Service URL
SAML_SP_ACS_URL=https://sark.example.com/api/auth/saml/acs

# Single Logout URL (optional)
SAML_SP_SLS_URL=https://sark.example.com/api/auth/saml/slo

# SP Certificate and Private Key (optional, for signing)
SAML_SP_X509_CERT=/path/to/sp-cert.pem
SAML_SP_PRIVATE_KEY=/path/to/sp-key.pem
```

### 2. Configure Identity Provider

```bash
# IdP Entity ID
SAML_IDP_ENTITY_ID=https://idp.example.com

# IdP SSO URL
SAML_IDP_SSO_URL=https://idp.example.com/sso

# IdP SLO URL (optional)
SAML_IDP_SLO_URL=https://idp.example.com/slo

# IdP Certificate
SAML_IDP_X509_CERT=/path/to/idp-cert.pem

# Or IdP Metadata URL (auto-configures above)
SAML_IDP_METADATA_URL=https://idp.example.com/metadata
```

## IdP Configuration

### Okta

1. In Okta Admin, create new SAML 2.0 app
2. Configure:
   - Single sign on URL: `https://sark.example.com/api/auth/saml/acs`
   - Audience URI: `https://sark.example.com`
   - Name ID format: EmailAddress
3. Add attribute statements:
   - email → user.email
   - firstName → user.firstName
   - lastName → user.lastName

### Azure AD

1. In Azure Portal, create Enterprise Application
2. Choose "Non-gallery application"
3. Configure SAML:
   - Identifier: `https://sark.example.com`
   - Reply URL: `https://sark.example.com/api/auth/saml/acs`
4. Download Federation Metadata XML
5. In SARK config:
   ```bash
   SAML_IDP_METADATA_URL=https://login.microsoftonline.com/.../federationmetadata/...
   ```

### OneLogin

1. Create new SAML app
2. Configure:
   - ACS URL: `https://sark.example.com/api/auth/saml/acs`
   - SAML Audience: `https://sark.example.com`
3. Parameters:
   - Email → Email
   - First Name → First Name
   - Last Name → Last Name

## Testing

```bash
# Start SARK
python -m sark

# Get SP metadata
curl http://localhost:8000/api/auth/saml/metadata

# Initiate SSO (SP-initiated)
curl http://localhost:8000/api/auth/saml/login?redirect_uri=http://localhost:3000/callback
```

## Troubleshooting

### "Invalid SAML Response"

Check:
- Clock skew (use NTP)
- Certificate expiration
- Signature validation

### "Audience mismatch"

Ensure `SAML_SP_ENTITY_ID` matches IdP configuration exactly.

### "Invalid destination"

Verify `SAML_SP_ACS_URL` is correct and matches IdP config.

## Security

1. Use encrypted assertions in production
2. Validate signatures
3. Use short assertion timeouts
4. Enable HTTPS only

## Next Steps

- [Main Authentication Guide](./AUTHENTICATION.md)
- [Troubleshooting](./TROUBLESHOOTING.md)
