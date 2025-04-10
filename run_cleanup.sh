#!/bin/bash

# Wrapper script to run the database cleanup utility.
# Ensures the virtual environment is active.

set -e # Exit on first error

APP_DIR="/opt/DenkraumNavigator"
VENV_PATH=".venv/bin/activate"
CLEANUP_SCRIPT="clean_up_database.py"
PYTHON_CMD="python3"

# Ensure we are in the correct directory
if [[ "$(pwd)" != "$APP_DIR" ]]; then
    echo "[INFO] Changing directory to $APP_DIR..."
    if ! cd "$APP_DIR"; then
        echo "[ERROR] Failed to change directory to '$APP_DIR'." >&2
        exit 1
    fi
fi
echo "[INFO] Current directory: $(pwd)"

# Check for venv and script
if [ ! -f "$VENV_PATH" ]; then
    echo "[ERROR] Virtual environment activate script not found at '$VENV_PATH'" >&2
    exit 1
fi
if [ ! -f "$CLEANUP_SCRIPT" ]; then
    echo "[ERROR] Cleanup script '$CLEANUP_SCRIPT' not found in $(pwd)." >&2
    exit 1
fi

# Activate venv
echo "[INFO] Activating virtual environment..."
source "$VENV_PATH"

# Run the cleanup script, passing all arguments
echo "[INFO] Running $CLEANUP_SCRIPT $@ ..."
"$PYTHON_CMD" "$CLEANUP_SCRIPT" "$@"
SCRIPT_EXIT_CODE=$?

# Deactivate venv
echo "[INFO] Deactivating virtual environment..."
deactivate

if [ $SCRIPT_EXIT_CODE -eq 0 ]; then
    echo "[SUCCESS] Database cleanup script completed successfully." 
else
    echo "[ERROR] Database cleanup script failed with exit code $SCRIPT_EXIT_CODE." >&2
    echo "[ERROR] Check '$APP_DIR/database_cleanup.log' for details." >&2
    exit 1
fi

exit 0 