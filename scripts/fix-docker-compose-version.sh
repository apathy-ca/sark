#!/bin/bash
# Remove deprecated version field from docker-compose files
# Docker Compose v2+ doesn't need/use the version field

set -e

echo "🔧 Removing deprecated docker-compose version fields..."
echo ""

# Fix docker-compose files
FILES=(
  "docker-compose.yml"
  "docker-compose.production.yml"
  "docker-compose.quickstart.yml"
)

FIXED_COUNT=0

for file in "${FILES[@]}"; do
  if [ -f "$file" ]; then
    if grep -q "^version:" "$file"; then
      echo "  ✓ Fixing $file"
      sed -i '/^version:/d' "$file"
      FIXED_COUNT=$((FIXED_COUNT + 1))
    else
      echo "  - $file (already fixed)"
    fi
  else
    echo "  ⚠ $file (not found)"
  fi
done

# Fix documentation
DOC_FILE="docs/SECURITY_HARDENING.md"
if [ -f "$DOC_FILE" ]; then
  if grep -q "version: '3\." "$DOC_FILE"; then
    echo "  ✓ Fixing $DOC_FILE"
    sed -i "/version: '3\./d" "$DOC_FILE"
    FIXED_COUNT=$((FIXED_COUNT + 1))
  else
    echo "  - $DOC_FILE (already fixed)"
  fi
fi

echo ""
echo "🔍 Checking for remaining occurrences..."

# Search for remaining version fields (exclude python-version and git files)
FOUND=$(grep -r "version.*['\"]3\." . \
  --include="*.yml" \
  --include="*.yaml" \
  --include="*.md" \
  --exclude-dir=".git" \
  --exclude-dir="node_modules" \
  --exclude-dir="venv" \
  2>/dev/null | \
  grep -v "python-version" | \
  grep -v "# version" || true)

if [ -n "$FOUND" ]; then
  echo ""
  echo "⚠️  Found remaining occurrences that may need manual review:"
  echo "$FOUND"
  echo ""
  echo "These might be false positives (python-version, etc.) - review manually."
fi

echo ""
echo "✅ Fixed $FIXED_COUNT file(s)"
echo ""
echo "📝 Git status:"
git status --short | grep -E "(docker-compose|SECURITY_HARDENING)" || echo "  No changes (already fixed)"

echo ""
echo "🧪 Testing docker-compose config..."
if docker-compose config >/dev/null 2>&1; then
  echo "✅ docker-compose config works!"
else
  echo "⚠️  docker-compose config failed - check syntax"
  exit 1
fi

echo ""
echo "Done! Commit these changes with:"
echo "  git add docker-compose*.yml docs/SECURITY_HARDENING.md"
echo "  git commit -m \"fix: remove deprecated docker-compose version field\""
echo "  git push"
