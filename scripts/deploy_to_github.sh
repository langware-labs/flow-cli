#!/bin/bash
#
# Deploy flow-cli to GitHub for pip installation
#
# This script:
#   1. Increments the patch version in _version.py
#   2. Commits the version bump
#   3. Creates a git tag
#   4. Pushes to GitHub
#   5. Installs from GitHub
#   6. Validates the installed version
#
# Usage: ./scripts/deploy_to_github.sh [--skip-tests]
#
# After deployment, install with:
#   pip install git+https://github.com/langware-labs/flow-cli.git
#   pip install git+https://github.com/langware-labs/flow-cli.git@vX.Y.Z
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

VERSION_FILE="_version.py"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
SKIP_TESTS=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--skip-tests]"
            echo ""
            echo "Options:"
            echo "  --skip-tests  Skip running tests before deployment"
            echo "  -h, --help    Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Function to get current version from _version.py
get_current_version() {
    grep -o '"[0-9]*\.[0-9]*\.[0-9]*"' "$VERSION_FILE" | tr -d '"'
}

# Function to increment patch version
increment_patch_version() {
    local version="$1"
    local major minor patch
    IFS='.' read -r major minor patch <<< "$version"
    patch=$((patch + 1))
    echo "${major}.${minor}.${patch}"
}

# Function to update version in _version.py
update_version_file() {
    local new_version="$1"
    echo "__version__ = \"${new_version}\"" > "$VERSION_FILE"
}

echo -e "${GREEN}=== Flow CLI GitHub Deployment ===${NC}"
echo ""

# Check if we're in a git repository
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo -e "${RED}Error: Not a git repository${NC}"
    exit 1
fi

# Check if _version.py exists
if [[ ! -f "$VERSION_FILE" ]]; then
    echo -e "${RED}Error: $VERSION_FILE not found${NC}"
    exit 1
fi

# Get current and new version
CURRENT_VERSION=$(get_current_version)
NEW_VERSION=$(increment_patch_version "$CURRENT_VERSION")

echo -e "Current version: ${YELLOW}${CURRENT_VERSION}${NC}"
echo -e "New version:     ${GREEN}${NEW_VERSION}${NC}"
echo ""

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)
echo -e "Branch: ${GREEN}$CURRENT_BRANCH${NC}"

# Check if remote exists
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
if [[ -z "$REMOTE_URL" ]]; then
    echo -e "${RED}Error: No 'origin' remote configured${NC}"
    exit 1
fi
echo -e "Remote: ${GREEN}$REMOTE_URL${NC}"
echo ""

# Run tests before deploying (unless skipped)
if [[ "$SKIP_TESTS" == false ]]; then
    echo -e "${YELLOW}Running tests...${NC}"
    if python3 -m pytest tests/ -v --tb=short; then
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
else
    echo -e "${YELLOW}Skipping tests...${NC}"
    echo ""
fi

# Check for uncommitted changes (other than version file)
UNCOMMITTED=$(git status --porcelain | grep -v "$VERSION_FILE" || true)
if [[ -n "$UNCOMMITTED" ]]; then
    echo -e "${YELLOW}Warning: You have uncommitted changes:${NC}"
    echo "$UNCOMMITTED"
    echo ""
    read -p "These changes will be included in the version bump commit. Continue? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Aborted. Please commit your changes first.${NC}"
        exit 1
    fi
fi

# Update version file
echo -e "${YELLOW}Updating version to ${NEW_VERSION}...${NC}"
update_version_file "$NEW_VERSION"

# Stage and commit all changes
echo -e "${YELLOW}Committing version bump...${NC}"
git add -A
git commit -m "Bump version to ${NEW_VERSION}"
echo -e "${GREEN}Committed version bump${NC}"

# Create git tag
TAG_NAME="v${NEW_VERSION}"
echo -e "${YELLOW}Creating tag: ${TAG_NAME}${NC}"

# Check if tag already exists
if git rev-parse "$TAG_NAME" >/dev/null 2>&1; then
    echo -e "${RED}Error: Tag '$TAG_NAME' already exists${NC}"
    exit 1
fi

git tag -a "$TAG_NAME" -m "Release ${NEW_VERSION}"
echo -e "${GREEN}Tag '${TAG_NAME}' created${NC}"

# Push to GitHub
echo ""
echo -e "${YELLOW}Pushing to GitHub...${NC}"
git push origin "$CURRENT_BRANCH"
git push origin "$TAG_NAME"
echo -e "${GREEN}Pushed to origin/$CURRENT_BRANCH with tag ${TAG_NAME}${NC}"

# Install from GitHub
echo ""
echo -e "${YELLOW}Installing from GitHub...${NC}"
pip3 install --quiet git+https://github.com/langware-labs/flow-cli.git@${TAG_NAME} --force-reinstall
echo -e "${GREEN}Installed from GitHub${NC}"

# Validate installed version
echo ""
echo -e "${YELLOW}Validating installation...${NC}"
INSTALLED_VERSION=$(flow 2>/dev/null | grep -o '[0-9]*\.[0-9]*\.[0-9]*' || echo "")

if [[ "$INSTALLED_VERSION" == "$NEW_VERSION" ]]; then
    echo -e "${GREEN}✓ Version validated: ${INSTALLED_VERSION}${NC}"
else
    echo -e "${RED}✗ Version mismatch!${NC}"
    echo -e "  Expected: ${NEW_VERSION}"
    echo -e "  Got: ${INSTALLED_VERSION}"
    exit 1
fi

# Print summary
echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "  Version:  ${BLUE}${NEW_VERSION}${NC}"
echo -e "  Tag:      ${BLUE}${TAG_NAME}${NC}"
echo ""
echo -e "Install with:"
echo -e "  ${GREEN}pip install git+https://github.com/langware-labs/flow-cli.git${NC}"
echo -e "  ${GREEN}pip install git+https://github.com/langware-labs/flow-cli.git@${TAG_NAME}${NC}"
echo ""
