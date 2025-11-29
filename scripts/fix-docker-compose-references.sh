#!/bin/bash

# ============================================================================
# Fix Docker Compose References
# ============================================================================
# This script updates all references from 'docker-compose' to 'docker compose'
# in documentation and script files.
#
# Usage: ./scripts/fix-docker-compose-references.sh

set -e

REPO_ROOT="/home/jhenry/Source/GRID/sark"
cd "$REPO_ROOT"

echo "🔍 Searching for files with 'docker-compose' references..."

# Find all markdown files with docker-compose
MARKDOWN_FILES=$(find docs -type f -name "*.md" -exec grep -l "docker-compose" {} \; 2>/dev/null || true)

# Find all script files with docker-compose
SCRIPT_FILES=$(find scripts -type f \( -name "*.sh" -o -name "*.bash" \) -exec grep -l "docker-compose" {} \; 2>/dev/null || true)

# Find all README files
README_FILES=$(find . -name "README.md" -exec grep -l "docker-compose" {} \; 2>/dev/null || true)

# Combine all files
ALL_FILES=$(echo -e "$MARKDOWN_FILES\n$SCRIPT_FILES\n$README_FILES" | sort -u | grep -v "^$")

if [ -z "$ALL_FILES" ]; then
    echo "✅ No files found with 'docker-compose' references"
    exit 0
fi

echo "📝 Files to update:"
echo "$ALL_FILES" | sed 's/^/  - /'
echo ""

# Count files
FILE_COUNT=$(echo "$ALL_FILES" | wc -l)
echo "📊 Total files to update: $FILE_COUNT"
echo ""

# Confirm before proceeding
read -p "❓ Proceed with updates? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Aborted"
    exit 1
fi

# Create backup
BACKUP_DIR="backups/docker-compose-fix-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Update files
UPDATED_COUNT=0
for file in $ALL_FILES; do
    if [ -f "$file" ]; then
        # Create backup
        cp "$file" "$BACKUP_DIR/$(basename $file)"

        # Replace docker-compose with docker compose
        # Use sed with proper escaping
        sed -i 's/docker-compose/docker compose/g' "$file"

        UPDATED_COUNT=$((UPDATED_COUNT + 1))
        echo "✓ Updated: $file"
    fi
done

echo ""
echo "✅ Successfully updated $UPDATED_COUNT files"
echo "💾 Backups saved to: $BACKUP_DIR"
echo ""
echo "🔍 Verification:"

# Verify no docker-compose references remain
REMAINING=$(find docs scripts -type f \( -name "*.md" -o -name "*.sh" -o -name "*.bash" \) -exec grep -l "docker-compose" {} \; 2>/dev/null | wc -l || echo "0")

if [ "$REMAINING" -eq 0 ]; then
    echo "✅ All 'docker-compose' references have been updated to 'docker compose'"
else
    echo "⚠️  Warning: $REMAINING files still contain 'docker-compose' references"
    find docs scripts -type f \( -name "*.md" -o -name "*.sh" -o -name "*.bash" \) -exec grep -l "docker-compose" {} \; 2>/dev/null | sed 's/^/  - /'
fi

echo ""
echo "Done! 🎉"
