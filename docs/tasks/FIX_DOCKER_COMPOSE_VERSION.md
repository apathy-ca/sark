# URGENT: Remove Deprecated docker-compose version Field

**Issue:** Using deprecated `version: '3.9'` in docker-compose files
**Impact:** Not compatible with modern Docker Compose v2+
**Priority:** HIGH - Fix before any Docker deployments

---

## Background

Docker Compose v2+ (released 2020) deprecated the `version` field. It's no longer needed and causes warnings:

```yaml
# ❌ OLD (deprecated)
version: '3.9'
services:
  ...

# ✅ NEW (correct)
services:
  ...
```

**Why remove it:**
- Docker Compose v2+ ignores it anyway
- Causes deprecation warnings
- Not needed for any features
- Official docs no longer show it

---

## Files to Fix

### 1. Docker Compose Files (3 files)

**File:** `/home/user/sark/docker-compose.yml`
- **Line 1:** Remove `version: '3.9'`

**File:** `/home/user/sark/docker-compose.production.yml`
- **Line 1:** Remove `version: '3.9'`

**File:** `/home/user/sark/docker-compose.quickstart.yml`
- **Line 31:** Remove `version: '3.9'`

**Fix:**
```bash
# Remove version field from all docker-compose files
sed -i "/^version:/d" docker-compose.yml
sed -i "/^version:/d" docker-compose.production.yml
sed -i "/^version:/d" docker-compose.quickstart.yml
```

### 2. Documentation (1 file)

**File:** `/home/user/sark/docs/SECURITY_HARDENING.md`
- Contains `version: '3.9'` in example code
- Find and remove from examples

**Fix:**
```bash
# Remove from documentation
sed -i "/^version: '3\.9'/d" docs/SECURITY_HARDENING.md
```

### 3. Search for Other Occurrences

**Check these locations:**
```bash
# Search all YAML files
grep -r "version.*3\." . --include="*.yml" --include="*.yaml"

# Search all documentation
grep -r "version.*3\." docs/ --include="*.md"

# Search example files
grep -r "version.*3\." examples/ --include="*.yml" --include="*.yaml"
```

---

## Complete Fix Script

```bash
#!/bin/bash
# fix-docker-compose-version.sh
# Remove deprecated version field from all files

set -e

echo "🔧 Removing deprecated docker-compose version fields..."

# Fix docker-compose files
FILES=(
  "docker-compose.yml"
  "docker-compose.production.yml"
  "docker-compose.quickstart.yml"
)

for file in "${FILES[@]}"; do
  if [ -f "$file" ]; then
    echo "  Fixing $file..."
    sed -i "/^version:/d" "$file"
  fi
done

# Fix documentation
echo "  Fixing docs/SECURITY_HARDENING.md..."
sed -i "/^version: '3\.9'/d" docs/SECURITY_HARDENING.md

# Search for any remaining occurrences
echo ""
echo "🔍 Checking for remaining occurrences..."
FOUND=$(grep -r "version.*3\." . --include="*.yml" --include="*.yaml" --include="*.md" 2>/dev/null | grep -v "python-version" | grep -v ".git" || true)

if [ -n "$FOUND" ]; then
  echo "⚠️  Found remaining occurrences:"
  echo "$FOUND"
  exit 1
else
  echo "✅ All fixed!"
fi

echo ""
echo "📝 Files modified:"
git status --short | grep -E "(docker-compose|SECURITY_HARDENING)" || echo "  (no changes detected)"
```

---

## Verification

After fixing, verify each file:

**docker-compose.yml:**
```yaml
# Should start like this (NO version line):
services:
  postgres:
    image: postgres:16
    ...
```

**Test it works:**
```bash
# Should work without warnings
docker-compose config
docker-compose up --dry-run
```

---

## Additional Checks

### Check Helm Charts
```bash
grep -r "version.*3\." charts/ --include="*.yaml"
```

### Check CI/CD Workflows
```bash
grep -r "version.*3\." .github/workflows/ --include="*.yml"
```

### Check Any Frontend Docker Files
```bash
grep -r "version.*3\." frontend/ --include="*.yml" --include="*.yaml"
```

---

## Documentation Updates Needed

After removing version field, update these docs to NOT show it in examples:

1. **docs/DOCKER_PROFILES.md** - Check examples
2. **docs/DEPLOYMENT_GUIDE.md** - Update examples (if exists)
3. **frontend/DEPLOYMENT.md** - Check docker-compose examples
4. **Any README files** - Search for docker-compose examples

**Search command:**
```bash
grep -r "docker-compose" docs/ --include="*.md" -l | xargs grep -l "version:"
```

---

## Timeline

**Effort:** 15 minutes
**Assignee:** Any engineer (Engineer 4 ideal - DevOps)
**When:** NOW (before any Docker deployments)

---

## Steps to Execute

1. **Run the fix script:**
   ```bash
   chmod +x fix-docker-compose-version.sh
   ./fix-docker-compose-version.sh
   ```

2. **Verify changes:**
   ```bash
   git diff docker-compose*.yml docs/SECURITY_HARDENING.md
   ```

3. **Test docker-compose still works:**
   ```bash
   docker-compose config
   ```

4. **Commit:**
   ```bash
   git add docker-compose*.yml docs/SECURITY_HARDENING.md
   git commit -m "fix: remove deprecated docker-compose version field

   - Remove version: '3.9' from all docker-compose files
   - Remove from documentation examples
   - Compatible with Docker Compose v2+
   - Eliminates deprecation warnings"
   git push
   ```

5. **Search for any other occurrences** and fix if found

---

## Why This Matters

**Current situation:**
```bash
$ docker-compose up
WARN[0000] version is obsolete
```

**After fix:**
```bash
$ docker-compose up
# No warnings, works perfectly
```

**Migration guide:** https://docs.docker.com/compose/compose-file/04-version-and-name/

> "The top-level version property is defined by the Compose Specification for backward compatibility. It is only informative."

---

## Assignee: Engineer 4 (DevOps)

**Why you:**
- Docker is your domain
- You know the compose files best
- You'll be deploying these

**Priority:** Do this BEFORE any other Docker work

**Estimated time:** 15 minutes

---

**Created:** 2025-11-27
**Status:** URGENT - Not started
**Blocker:** None - can be done immediately
**Impact:** Eliminates deprecation warnings, modernizes configs
