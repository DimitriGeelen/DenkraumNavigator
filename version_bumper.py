#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Automates the version bumping process including changelog update and git commit/tag.

Usage:
  python version_bumper.py --patch | --minor | --major
"""

import argparse
import subprocess
import re
import sys
from datetime import datetime
import os

VERSION_FILE = "VERSION"
CHANGELOG_FILE = "CHANGELOG.md"

def run_command(command, capture_output=False, check=True, shell=False):
    """Helper function to run a shell command."""
    try:
        print(f"Running command: {' '.join(command) if isinstance(command, list) else command}")
        result = subprocess.run(
            command,
            capture_output=capture_output,
            text=True,
            check=check,
            shell=shell # Use shell=True cautiously if needed, but prefer list format
        )
        if capture_output:
            return result.stdout.strip()
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {' '.join(command) if isinstance(command, list) else command}", file=sys.stderr)
        print(f"Stderr: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: Command not found. Is '{command[0]}' installed and in PATH?", file=sys.stderr)
        sys.exit(1)

def get_current_version():
    """Reads the current version from the VERSION file."""
    try:
        with open(VERSION_FILE, 'r') as f:
            version = f.read().strip()
            if not re.match(r"^\d+\.\d+\.\d+$", version):
                print(f"Error: Invalid version format '{version}' in {VERSION_FILE}", file=sys.stderr)
                sys.exit(1)
            return version
    except FileNotFoundError:
        print(f"Error: {VERSION_FILE} not found.", file=sys.stderr)
        sys.exit(1)

def get_latest_tag():
    """Gets the latest git tag matching v*.*.*."""
    try:
        # Fetch tags from remote just in case
        run_command(["git", "fetch", "--tags", "--quiet"])
        # Get tags sorted by version
        tags_str = run_command(["git", "tag", "--list", "v*.*.*", "--sort=-v:refname"], capture_output=True)
        if tags_str:
            latest_tag = tags_str.split('\n')[0]
            return latest_tag
        else:
             # Try getting the very first commit if no tags exist
            print("No version tags (v*.*.*) found. Getting first commit hash.", file=sys.stderr)
            first_commit = run_command(["git", "rev-list", "--max-parents=0", "HEAD"], capture_output=True)
            if first_commit:
                return first_commit
            else:
                print("Error: Cannot determine the initial commit.", file=sys.stderr)
                sys.exit(1)
    except Exception as e:
        print(f"Error getting latest tag: {e}", file=sys.stderr)
        sys.exit(1)

def calculate_next_version(current_version, bump_type):
    """Calculates the next version based on the bump type."""
    major, minor, patch = map(int, current_version.split('.'))
    if bump_type == 'major':
        major += 1
        minor = 0
        patch = 0
    elif bump_type == 'minor':
        minor += 1
        patch = 0
    elif bump_type == 'patch':
        patch += 1
    else:
        raise ValueError("Invalid bump type")
    return f"{major}.{minor}.{patch}"

def get_commits_since_tag(tag):
    """Gets commit subjects since the last tag."""
    try:
        log_format = "- %s (%h)" # Subject (%s), short hash (%h)
        commits = run_command([
            "git", "log", f"{tag}..HEAD", f"--pretty=format:{log_format}"
            ], capture_output=True, check=False) # check=False because it can be empty
        return commits if commits else "- No significant changes."
    except Exception as e:
        print(f"Error getting commits since tag {tag}: {e}", file=sys.stderr)
        # Return a default message instead of exiting
        return "- Could not retrieve commit list."

def update_version_file(new_version):
    """Updates the VERSION file."""
    print(f"Updating {VERSION_FILE} to {new_version}")
    with open(VERSION_FILE, 'w') as f:
        f.write(new_version + '\n')

def update_changelog(new_version, commits_summary):
    """Prepends the new version release notes to CHANGELOG.md."""
    print(f"Updating {CHANGELOG_FILE} for version {new_version}")
    today = datetime.now().strftime('%Y-%m-%d')
    new_section = f"## [{new_version}] - {today}\n\n### Changes\n\n{commits_summary}\n\n"

    try:
        with open(CHANGELOG_FILE, 'r+') as f:
            content = f.read()
            f.seek(0, 0)
            # Find the position of the first existing version header (if any)
            first_header_match = re.search(r"^## \[", content, re.MULTILINE)
            insert_pos = first_header_match.start() if first_header_match else 0

            # Handle edge case: If file only has # Changelog header
            changelog_header = "# Changelog"
            unreleased_header = "## [Unreleased]"
            if content.strip().startswith(changelog_header):
                # Find end of # Changelog line
                header_end_pos = content.find('\n') + 1
                # Find start of [Unreleased] section if exists
                unreleased_match = re.search(rf"^{unreleased_header}", content, re.MULTILINE)
                if unreleased_match:
                    insert_pos = unreleased_match.start()
                else:
                    insert_pos = header_end_pos # Insert right after # Changelog
            elif content.strip().startswith(unreleased_header):
                 insert_pos = re.search(rf"^{unreleased_header}", content, re.MULTILINE).start()

            f.seek(insert_pos)
            remaining_content = f.read()
            f.seek(insert_pos)
            f.write(new_section + remaining_content)
            f.truncate() # Truncate in case the new content is shorter (shouldn't happen here)

    except FileNotFoundError:
        print(f"Warning: {CHANGELOG_FILE} not found. Creating it.", file=sys.stderr)
        with open(CHANGELOG_FILE, 'w') as f:
            f.write(f"# Changelog\n\n{new_section}")
    except Exception as e:
        print(f"Error updating {CHANGELOG_FILE}: {e}", file=sys.stderr)
        sys.exit(1)

def check_git_status():
    """Checks if the git working directory is clean."""
    status = run_command(["git", "status", "--porcelain"], capture_output=True)
    if status:
        print("Error: Git working directory is not clean. Please commit or stash changes.", file=sys.stderr)
        print(status, file=sys.stderr)
        sys.exit(1)
    print("Git working directory is clean.")

def main():
    parser = argparse.ArgumentParser(description='Automate version bumping.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--patch', action='store_true', help='Bump patch version.')
    group.add_argument('--minor', action='store_true', help='Bump minor version.')
    group.add_argument('--major', action='store_true', help='Bump major version.')

    args = parser.parse_args()

    # check_git_status() # Check commented out - now handled by safe_version_bump.sh wrapper

    current_version = get_current_version()
    print(f"Current version: {current_version}")

    if args.patch:
        bump_type = 'patch'
    elif args.minor:
        bump_type = 'minor'
    elif args.major:
        bump_type = 'major'
    else:
        # Should not happen due to argparse required group
        print("Error: No bump type specified.", file=sys.stderr)
        sys.exit(1)

    new_version = calculate_next_version(current_version, bump_type)
    print(f"Next version ({bump_type}): {new_version}")

    latest_tag = get_latest_tag()
    print(f"Latest relevant tag/commit: {latest_tag}")

    commits_summary = get_commits_since_tag(latest_tag)
    print("Commits since last tag:")
    print(commits_summary)

    # --- Perform updates ---
    update_version_file(new_version)
    update_changelog(new_version, commits_summary)

    # --- Git actions ---
    print("Staging changes...")
    run_command(["git", "add", VERSION_FILE, CHANGELOG_FILE])

    commit_message = f"chore: Bump version to {new_version}"
    print(f"Committing with message: '{commit_message}'")
    run_command(["git", "commit", "-m", commit_message])

    tag_name = f"v{new_version}"
    print(f"Tagging commit as {tag_name}")
    run_command(["git", "tag", tag_name])

    print("\nVersion bump complete.")
    print(f"New version: {new_version}")
    print(f"Tagged commit as: {tag_name}")
    print("Remember to verify the post-commit hook ran successfully.")
    print("You may need to push the commit and tag ('git push origin <branch> --tags')")

if __name__ == "__main__":
    main() 