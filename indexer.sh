#!/bin/bash

# Shell script to run the full DenkraumNavigator indexer (indexer.py)
# This script activates the virtual environment and passes arguments.

# Find the directory where the script is located (should be project root)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$SCRIPT_DIR"
VENV_DIR="$PROJECT_ROOT/.venv"
INDEXER_SCRIPT="$PROJECT_ROOT/indexer.py"

# --- Argument Check ---
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <directory_to_index>"
    echo "  Example: $0 /path/to/your/archive"
    exit 1
fi
TARGET_DIR="$1"

# --- Activate Virtual Environment ---
echo "[INFO] Activating virtual environment: $VENV_DIR"
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
else
    echo "Error: Virtual environment activate script not found at $VENV_DIR/bin/activate" >&2
    exit 1
fi

# --- Check Python Command ---
PYTHON_CMD="python3"
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "Error: '$PYTHON_CMD' command not found. Please ensure Python 3 is installed and accessible." >&2
    # Attempt to deactivate before exiting
    if type deactivate > /dev/null 2>&1; then deactivate; fi
    exit 1
fi

# --- Run Indexer ---
DB_FILENAME="file_index.db" # Explicitly define the target DB
echo "[INFO] Running $INDEXER_SCRIPT on directory: $TARGET_DIR"
echo "[INFO] Using database file: $PROJECT_ROOT/$DB_FILENAME"
$PYTHON_CMD "$INDEXER_SCRIPT" "$TARGET_DIR" "$DB_FILENAME" # Pass DB name as argument
INDEXER_EXIT_CODE=$?

# --- Deactivate Virtual Environment ---
if type deactivate > /dev/null 2>&1; then
    echo "[INFO] Deactivating virtual environment."
    deactivate
fi

exit $INDEXER_EXIT_CODE 