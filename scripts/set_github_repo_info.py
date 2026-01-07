#!/usr/bin/env python3
"""
Script to set GitHub repository description and topics via API.

Requires:
- GitHub personal access token with 'repo' scope
- Set GITHUB_TOKEN environment variable, in .env file, or pass as argument

Usage:
    # Option 1: Set in .env file (recommended)
    echo "GITHUB_TOKEN=your_token_here" >> .env
    python scripts/set_github_repo_info.py

    # Option 2: Set as environment variable
    export GITHUB_TOKEN=your_token_here
    python scripts/set_github_repo_info.py

    # Option 3: Pass as argument
    python scripts/set_github_repo_info.py --token your_token_here
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    # Load .env file from project root (one level up from scripts/)
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"📝 Loaded environment variables from {env_path}")
except ImportError:
    # python-dotenv not installed, skip .env loading
    pass

# Repository info
REPO_OWNER = "16wells"  # Update if different
REPO_NAME = "google-photos-icloud-migration"  # Update if different

DESCRIPTION = "Migrate photos from Google Photos (Takeout) to iCloud Photos on macOS. Preserves metadata, albums, and album structures. Terminal-based tool."

TOPICS = [
    "google-photos",
    "icloud-photos",
    "photo-migration",
    "macos",
    "python",
    "photokit",
    "exiftool",
    "metadata-preservation",
    "google-takeout",
    "photo-sync",
    "album-migration",
    "photo-management",
    "icloud",
    "google-drive",
    "python3",
    "exif-metadata",
    "oauth2",
    "api-integration",
    "photokit-framework",
    "terminal-tool"
]


def get_token():
    """Get GitHub token from .env file, environment variable, or argument."""
    # First, try loading from .env (already done at module level, but check anyway)
    token = os.getenv('GITHUB_TOKEN')
    
    # If not in environment, check command line argument
    if not token:
        parser = argparse.ArgumentParser(description='Set GitHub repo description and topics')
        parser.add_argument('--token', help='GitHub personal access token')
        args = parser.parse_args()
        token = args.token
    
    # Strip whitespace if token was found
    if token:
        token = token.strip()
        # Skip empty tokens
        if not token or token == 'your_github_token_here':
            token = None
    
    if not token:
        print("Error: GitHub token required")
        print("\nOptions:")
        print("1. Add GITHUB_TOKEN=your_token to .env file (recommended)")
        print("2. Set GITHUB_TOKEN environment variable")
        print("3. Use --token argument: python scripts/set_github_repo_info.py --token your_token")
        print("\nTo create a token:")
        print("1. Go to https://github.com/settings/tokens")
        print("2. Generate new token (classic)")
        print("3. Select 'repo' scope")
        print("4. Copy the token and add it to your .env file")
        sys.exit(1)
    
    return token


def set_repo_description(token, description):
    """Set repository description."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "description": description
    }
    
    response = requests.patch(url, headers=headers, json=data)
    if response.status_code == 200:
        print(f"✅ Description set: {description}")
        return True
    else:
        print(f"❌ Failed to set description: {response.status_code}")
        print(f"   {response.text}")
        return False


def set_repo_topics(token, topics):
    """Set repository topics."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/topics"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.mercy-preview+json"  # Required for topics API
    }
    data = {
        "names": topics
    }
    
    response = requests.put(url, headers=headers, json=data)
    if response.status_code == 200:
        print(f"✅ Topics set ({len(topics)} topics):")
        for topic in topics:
            print(f"   - {topic}")
        return True
    else:
        print(f"❌ Failed to set topics: {response.status_code}")
        print(f"   {response.text}")
        return False


def main():
    """Main function."""
    print(f"Setting GitHub repository info for {REPO_OWNER}/{REPO_NAME}")
    print()
    
    token = get_token()
    
    # Set description
    print("Setting description...")
    desc_success = set_repo_description(token, DESCRIPTION)
    print()
    
    # Set topics
    print("Setting topics...")
    topics_success = set_repo_topics(token, TOPICS)
    print()
    
    if desc_success and topics_success:
        print("✅ Successfully updated repository information!")
        print(f"\nView your repo: https://github.com/{REPO_OWNER}/{REPO_NAME}")
    else:
        print("⚠️  Some operations failed. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()

