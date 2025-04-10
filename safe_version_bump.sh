#!/bin/bash

# Wrapper script for version_bumper.py to enforce pre-checks
# Ensures working directory is clean and tests pass before bumping version.

set -e # Exit immediately if a command exits with a non-zero status.

# --- Argument Validation ---
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 --patch|--minor|--major"
    exit 1
fi

level_arg="$1"
if [[ "$level_arg" != "--patch" && "$level_arg" != "--minor" && "$level_arg" != "--major" ]]; then
    echo "Error: Invalid argument. Must be --patch, --minor, or --major."
    echo "Usage: $0 --patch|--minor|--major"
    exit 1
fi

echo "--- Running Safe Version Bump: $level_arg ---"

# --- 1. Check Git Working Directory ---
echo "[CHECK] Verifying clean Git working directory..."
# if ! git diff --quiet HEAD --; then
#     echo "Error: Uncommitted changes detected in tracked files. Please commit or stash changes."
#     git status --short # Show uncommitted changes
#     exit 1
# fi
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    echo "Error: Untracked files detected (excluding explicitly ignored). Please track or remove them."
    git status --short
    exit 1
fi
echo "Success: Git working directory is clean."

# --- 2. Run Unit Tests ---
echo "[CHECK] Running unit tests (pytest)..."
if ! pytest; then
    echo "Error: Unit tests failed. Please fix tests before bumping version."
    exit 1
fi
echo "Success: Unit tests passed."

# --- 3. Run Version Bumper Script ---
echo "[ACTION] Running python version_bumper.py $level_arg ..."
if python version_bumper.py "$level_arg"; then
    echo "--- Safe Version Bump Completed Successfully ---"
else
    echo "Error: python version_bumper.py script failed."
    exit 1 # Exit with error if the python script failed
fi

exit 0
