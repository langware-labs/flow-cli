#!/bin/bash
#
# Deploy flow-cli to GitHub for pip installation
# Usage: ./scripts/deploy_to_github.sh [--tag VERSION]
#
# After deployment, install with:
#   pip install git+https://github.com/langware-labs/flow-cli.git
#   pip install git+https://github.com/langware-labs/flow-cli.git@VERSION  # specific version
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
TAG_VERSION=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --tag)
            TAG_VERSION="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--tag VERSION]"
            echo ""
            echo "Options:"
            echo "  --tag VERSION   Create a git tag with the specified version (e.g., v0.1.0)"
            echo "  -h, --help      Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}=== Flow CLI GitHub Deployment ===${NC}"
echo ""

# Check if we're in a git repository
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo -e "${RED}Error: Not a git repository${NC}"
    exit 1
fi

# Check for uncommitted changes
if [[ -n $(git status --porcelain) ]]; then
    echo -e "${YELLOW}Warning: You have uncommitted changes:${NC}"
    git status --short
    echo ""
    read -p "Do you want to continue anyway? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Aborted. Please commit your changes first.${NC}"
        exit 1
    fi
fi

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)
echo -e "Current branch: ${GREEN}$CURRENT_BRANCH${NC}"

# Check if remote exists
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
if [[ -z "$REMOTE_URL" ]]; then
    echo -e "${RED}Error: No 'origin' remote configured${NC}"
    exit 1
fi
echo -e "Remote: ${GREEN}$REMOTE_URL${NC}"
echo ""

# Run tests before deploying
echo -e "${YELLOW}Running tests...${NC}"
if python -m pytest tests/ -v --tb=short; then
    echo -e "${GREEN}Tests passed!${NC}"
else
    echo -e "${RED}Tests failed!${NC}"
    read -p "Do you want to deploy anyway? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Aborted due to test failures.${NC}"
        exit 1
    fi
fi
echo ""

# Push to GitHub
echo -e "${YELLOW}Pushing to GitHub...${NC}"
git push origin "$CURRENT_BRANCH"
echo -e "${GREEN}Pushed to origin/$CURRENT_BRANCH${NC}"

# Create tag if requested
if [[ -n "$TAG_VERSION" ]]; then
    echo ""
    echo -e "${YELLOW}Creating tag: $TAG_VERSION${NC}"

    # Check if tag already exists
    if git rev-parse "$TAG_VERSION" >/dev/null 2>&1; then
        echo -e "${RED}Error: Tag '$TAG_VERSION' already exists${NC}"
        exit 1
    fi

    git tag -a "$TAG_VERSION" -m "Release $TAG_VERSION"
    git push origin "$TAG_VERSION"
    echo -e "${GREEN}Tag '$TAG_VERSION' created and pushed${NC}"
fi

echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo ""
echo "Install with:"
echo -e "  ${GREEN}pip install git+https://github.com/langware-labs/flow-cli.git${NC}"
if [[ -n "$TAG_VERSION" ]]; then
    echo -e "  ${GREEN}pip install git+https://github.com/langware-labs/flow-cli.git@$TAG_VERSION${NC}"
fi
