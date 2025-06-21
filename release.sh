#!/bin/bash
# Release script for claude-top

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}claude-top Release Script${NC}"
echo "========================"

# Check if we're on main branch
BRANCH=$(git branch --show-current)
if [ "$BRANCH" != "main" ]; then
    echo -e "${RED}Error: Not on main branch. Current branch: $BRANCH${NC}"
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${RED}Error: There are uncommitted changes${NC}"
    git status --short
    exit 1
fi

# Get current version from package.json
CURRENT_VERSION=$(node -p "require('./package.json').version")
echo -e "Current version: ${YELLOW}$CURRENT_VERSION${NC}"

# Push to GitHub
echo -e "\n${GREEN}Pushing to GitHub...${NC}"
git push origin main
git push origin --tags

# Build npm package
echo -e "\n${GREEN}Building npm package...${NC}"
npm pack

echo -e "\n${GREEN}Release preparation complete!${NC}"
echo "Next steps:"
echo "1. Create a GitHub release at: https://github.com/mcappelloni/claude-top/releases/new"
echo "2. Publish to npm: npm publish"
echo "3. Test with: npx claude-top"