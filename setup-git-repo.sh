#!/bin/bash
# Setup git repository for google-photos-icloud-migration

cd "$(dirname "$0")"

# Initialize git if not already initialized
if [ ! -d .git ]; then
    echo "Initializing git repository..."
    git init
fi

# Add all files
echo "Adding all files to git..."
git add .

# Check if there are changes to commit
if git diff --cached --quiet; then
    echo "No changes to commit."
else
    echo "Creating initial commit..."
    git commit -m "Initial commit: Google Photos to iCloud Photos migration tool"
fi

# Set default branch to main
git branch -M main

# Get GitHub username
GITHUB_USER=$(git config --global user.name 2>/dev/null)
if [ -z "$GITHUB_USER" ]; then
    echo ""
    echo "Please enter your GitHub username:"
    read -r GITHUB_USER
fi

REMOTE_URL="https://github.com/${GITHUB_USER}/google-photos-icloud-migration.git"

# Add remote (or update if exists)
if git remote get-url origin &>/dev/null; then
    echo "Updating remote URL..."
    git remote set-url origin "${REMOTE_URL}"
else
    echo "Adding remote repository..."
    git remote add origin "${REMOTE_URL}"
fi

echo ""
echo "✓ Git repository initialized!"
echo ""
echo "Remote URL: ${REMOTE_URL}"
echo ""
echo "Next steps:"
echo "1. Create the repository on GitHub:"
echo "   Visit: https://github.com/new"
echo "   Repository name: google-photos-icloud-migration"
echo "   Make it private if you want (contains credentials)"
echo "   DO NOT initialize with README, .gitignore, or license"
echo "   Click 'Create repository'"
echo ""
echo "2. Push your code:"
echo "   git push -u origin main"
echo ""
echo "Or if you need to force push (if repo was initialized with files):"
echo "   git push -u origin main --force"
echo ""

