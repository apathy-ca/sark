#!/bin/bash
# ==============================================================================
# Fix Docker Compose Version Field
# ==============================================================================
# Removes the deprecated 'version:' field from Docker Compose files.
# Docker Compose v2+ doesn't require or use this field.
#
# Usage: ./scripts/fix-docker-compose-version.sh
# ==============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}Docker Compose Version Field Removal${NC}"
echo -e "${BLUE}===================================================${NC}"
echo ""

# Files to fix
COMPOSE_FILES=(
    "docker-compose.yml"
    "docker-compose.dev.yml"
    "docker-compose.production.yml"
    "docker-compose.quickstart.yml"
)

DOC_FILES=(
    "docs/SECURITY_HARDENING.md"
)

# Counter for changes
TOTAL_CHANGES=0

# Function to remove version field from compose files
fix_compose_file() {
    local file=$1
    
    if [ ! -f "$file" ]; then
        echo -e "${YELLOW}⚠ File not found: $file (skipping)${NC}"
        return
    fi
    
    # Check if file has version field
    if grep -q "^version: " "$file"; then
        echo -e "${BLUE}📝 Fixing: $file${NC}"
        
        # Create backup
        cp "$file" "$file.bak"
        
        # Remove version line
        sed -i '/^version: /d' "$file"
        
        # Remove the blank line that might be left
        sed -i '/^$/N;/^\n$/d' "$file"
        
        echo -e "${GREEN}✓ Removed version field${NC}"
        TOTAL_CHANGES=$((TOTAL_CHANGES + 1))
        
        # Validate the file
        if docker compose -f "$file" config --quiet 2>/dev/null; then
            echo -e "${GREEN}✓ File validates successfully${NC}"
            rm "$file.bak"
        else
            echo -e "${RED}✗ Validation failed! Restoring backup...${NC}"
            mv "$file.bak" "$file"
            TOTAL_CHANGES=$((TOTAL_CHANGES - 1))
        fi
    else
        echo -e "${GREEN}✓ Already fixed: $file${NC}"
    fi
    
    echo ""
}

# Function to fix documentation
fix_doc_file() {
    local file=$1
    
    if [ ! -f "$file" ]; then
        echo -e "${YELLOW}⚠ File not found: $file (skipping)${NC}"
        return
    fi
    
    if grep -q "version: '3" "$file"; then
        echo -e "${BLUE}📝 Fixing documentation: $file${NC}"
        
        # Create backup
        cp "$file" "$file.bak"
        
        # Replace version references in examples
        sed -i "s/version: '[0-9.]*'/# Docker Compose file (no version needed for Compose v2+)/g" "$file"
        
        echo -e "${GREEN}✓ Updated documentation${NC}"
        TOTAL_CHANGES=$((TOTAL_CHANGES + 1))
        rm "$file.bak"
    else
        echo -e "${GREEN}✓ Already fixed: $file${NC}"
    fi
    
    echo ""
}

# Fix all compose files
echo -e "${YELLOW}Fixing Docker Compose files...${NC}"
echo ""

for file in "${COMPOSE_FILES[@]}"; do
    fix_compose_file "$file"
done

# Fix documentation
echo -e "${YELLOW}Fixing documentation...${NC}"
echo ""

for file in "${DOC_FILES[@]}"; do
    fix_doc_file "$file"
done

# Summary
echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}===================================================${NC}"
echo ""

if [ $TOTAL_CHANGES -gt 0 ]; then
    echo -e "${GREEN}✓ Fixed $TOTAL_CHANGES file(s)${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Review changes: git diff"
    echo "  2. Test compose files: docker compose config --quiet"
    echo "  3. Commit changes:"
    echo "     git add docker-compose*.yml docs/SECURITY_HARDENING.md"
    echo "     git commit -m \"fix: remove deprecated docker-compose version field\""
    echo "     git push"
else
    echo -e "${GREEN}✓ All files already up to date${NC}"
fi

echo ""
