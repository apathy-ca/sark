# SARK Tutorials - Code Examples

This directory contains executable code examples for SARK tutorials.

## Available Tutorials

### Tutorial 02: Authentication

Learn how to authenticate with SARK using various methods.

**Python Client:**
```bash
# Install dependencies
pip install requests

# API Key authentication
python auth_tutorial.py --method api-key --admin-token YOUR_TOKEN

# LDAP authentication
python auth_tutorial.py --method ldap --username john.doe --password secret

# Test token refresh
python auth_tutorial.py --method ldap --username john.doe --password secret --test-refresh

# Use existing API key
python auth_tutorial.py --use-api-key sark_dev_abc123...
```

**Bash Script:**
```bash
# Run all authentication tutorials
./auth_tutorial.sh all

# Run specific tutorial
./auth_tutorial.sh api-key
./auth_tutorial.sh ldap
./auth_tutorial.sh oidc
```

## Requirements

### Python Client
- Python 3.8+
- requests library: `pip install requests`

### Bash Script
- bash
- curl
- jq (for JSON parsing)

Install on Ubuntu/Debian:
```bash
sudo apt-get install curl jq
```

Install on macOS:
```bash
brew install curl jq
```

## Environment Variables

Set these before running tutorials:

```bash
# SARK API URL (default: http://localhost:8000)
export SARK_API_URL="http://localhost:8000"

# Admin token for bootstrapping (dev only)
export ADMIN_TOKEN="dev-admin-token-change-in-production"
```

## Running the Tutorials

1. **Start SARK:**
   ```bash
   docker-compose up -d
   ```

2. **Run a tutorial:**
   ```bash
   # Python
   python auth_tutorial.py --method ldap --username john.doe --password secret

   # Bash
   ./auth_tutorial.sh ldap
   ```

3. **Check results:**
   The tutorials will output success/failure messages and show you the API responses.

## Tutorial Structure

Each tutorial demonstrates:
1. ✅ **Setup** - How to configure authentication
2. ✅ **Usage** - How to make authenticated requests
3. ✅ **Testing** - How to test the implementation
4. ✅ **Cleanup** - How to revoke/logout

## Troubleshooting

### "curl: command not found"
Install curl:
```bash
# Ubuntu/Debian
sudo apt-get install curl

# macOS (usually pre-installed)
brew install curl
```

### "jq: command not found"
Install jq:
```bash
# Ubuntu/Debian
sudo apt-get install jq

# macOS
brew install jq
```

### "Connection refused"
Make sure SARK is running:
```bash
docker-compose ps
docker-compose logs sark-api
```

### "401 Unauthorized"
Check your credentials:
- LDAP: Verify username/password
- API Key: Check the key is valid and not revoked
- JWT: Token may have expired, refresh it

## Next Steps

After completing these tutorials:
- Read the full documentation in `docs/tutorials/`
- Explore other examples in `examples/`
- Try the interactive API docs: http://localhost:8000/docs

## Support

- Documentation: `docs/`
- FAQ: `docs/FAQ.md`
- Issues: File an issue on GitHub
