# Task: Remove Deprecated Docker Compose Version Field

## Status: ✅ Complete

**Assigned to**: Engineer 4 (DevOps/Infrastructure)
**Priority**: High - Do BEFORE any Docker work
**Estimated Time**: 15 minutes
**Created**: 2025-11-27

---

## Problem

Docker Compose files are using the deprecated `version: '3.9'` field at the top of the file. This field is no longer needed in Docker Compose v2+ and causes warnings when running docker compose commands.

### Why This Matters

1. **Deprecated**: Docker Compose v2 (released 2020) doesn't require or use this field
2. **Warnings**: Causes deprecation warnings in modern Docker Compose
3. **Confusion**: Misleads developers into thinking version matters
4. **Best Practice**: Modern Docker Compose files should omit this field

### Reference

From Docker Compose documentation:
> The top-level `version` property is defined by the Compose Specification for backward compatibility but is informative only. Docker Compose doesn't use it to select an exact schema to validate the Compose file.

Source: https://docs.docker.com/compose/compose-file/04-version-and-name/

---

## Files Affected

Total: 5 files

### Docker Compose Files (4)
1. `docker-compose.yml` - Main production compose file
2. `docker-compose.dev.yml` - Development compose file
3. `docker-compose.production.yml` - Production deployment file
4. `docker-compose.quickstart.yml` - Quickstart guide file

### Documentation (1)
5. `docs/SECURITY_HARDENING.md` - Contains example with old version

---

## Solution

Remove the `version: '3.9'` line from the top of all Docker Compose files.

### Before
```yaml
version: '3.9'

services:
  app:
    ...
```

### After
```yaml
services:
  app:
    ...
```

---

## Implementation

### Automated Script

A script has been created to automatically fix all files:

**Location**: `scripts/fix-docker-compose-version.sh`

**Usage**:
```bash
# Run the automated fix
./scripts/fix-docker-compose-version.sh

# Review changes
git diff

# Commit
git add docker-compose*.yml docs/SECURITY_HARDENING.md
git commit -m "fix: remove deprecated docker-compose version field"
git push
```

### Manual Fix (if needed)

If you prefer to fix manually:

```bash
# Remove version line from each file
sed -i '/^version: /d' docker-compose.yml
sed -i '/^version: /d' docker-compose.dev.yml
sed -i '/^version: /d' docker-compose.production.yml
sed -i '/^version: /d' docker-compose.quickstart.yml

# Fix documentation example
sed -i 's/version: .*/# Docker Compose file (no version needed for Compose v2+)/' docs/SECURITY_HARDENING.md
```

---

## Testing

After making changes, verify Docker Compose still works:

```bash
# Test standard profile
docker compose config --quiet

# Test development
docker compose -f docker-compose.dev.yml config --quiet

# Test production
docker compose -f docker-compose.production.yml config --quiet

# Test quickstart
docker compose -f docker-compose.quickstart.yml config --quiet

# All should exit with code 0 (no errors)
```

---

## Acceptance Criteria

- [x] All 4 Docker Compose files have `version:` field removed
- [x] Documentation updated to reflect modern best practice
- [x] No Docker Compose validation errors
- [x] All compose files can be validated with `docker compose config`
- [x] Changes committed with clear message
- [x] Changes pushed to branch

---

## Rationale

### Why Remove Instead of Update?

Some might suggest updating to a newer version like `3.10` or `3.11`, but:

1. **Not Needed**: Docker Compose v2+ ignores this field entirely
2. **Confusing**: Implies that version selection matters (it doesn't)
3. **Deprecated**: Official Docker docs recommend omitting it
4. **Modern**: Aligns with current best practices

### Backward Compatibility

Removing the version field is safe because:

- **Docker Compose v2+**: Doesn't use or require it
- **Specification**: Uses the full Compose Specification regardless of version
- **Features**: All features are available based on Compose version, not file version

---

## Additional Notes

### What Changed in Compose v2?

Docker Compose v2 (2020+) introduced several changes:

1. **No Version Field**: Top-level `version` is optional and informative only
2. **Compose Specification**: Uses full spec instead of version-based schemas
3. **CLI Integration**: `docker compose` (space) instead of `docker-compose` (hyphen)
4. **Go-based**: Rewritten in Go for better performance

### Migration Guide

If you see `docker-compose` (hyphen) in documentation:
- **Old**: `docker-compose up -d` (Python-based, deprecated)
- **New**: `docker compose up -d` (Go-based, current)

Both commands work with files that have or don't have the `version:` field.

---

## Related Issues

- None currently

## Related Documentation

- [Docker Compose Specification - Version](https://docs.docker.com/compose/compose-file/04-version-and-name/)
- [Compose v2 Migration Guide](https://docs.docker.com/compose/migrate/)

---

## Completion

**Date Completed**: 2025-11-27
**Completed By**: Engineer 4 (DevOps/Infrastructure)
**Commit Hash**: ffcffa2

**Notes**:
- Removed deprecated `version: '3.9'` field from 4 Docker Compose files
- Updated SECURITY_HARDENING.md to reflect modern best practice
- Created automated fix script for future use
- All changes validated and pushed to branch
