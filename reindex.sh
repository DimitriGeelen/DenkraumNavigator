#!/bin/bash

# Script to re-index the archive data after moving it.
# Prompts for the new location and runs indexer.py.
# Run this script manually from the server's command line.

set -e # Exit on first error
set -u # Treat unset variables as error

# --- Configuration --- 
INSTALL_DIR="/opt/DenkraumNavigator" # Application directory
VENV_DIR=".venv"                    # Relative venv dir name
PYTHON_CMD="python3"                # Python command
INDEXER_SCRIPT="indexer.py"
# --- End Configuration --- 

echo "--- DenkraumNavigator Re-indexing Helper ---"

# Ensure we are in the correct directory
if [[ "$(pwd)" != "$INSTALL_DIR" ]]; then
    echo "[INFO] Changing directory to $INSTALL_DIR..."
    if ! cd "$INSTALL_DIR"; then
        echo "[ERROR] Failed to change directory to '$INSTALL_DIR'." >&2
        exit 1
    fi
fi
echo "[INFO] Current directory: $(pwd)"

# Check for virtual environment
VENV_PATH="$INSTALL_DIR/$VENV_DIR"
if [ ! -d "$VENV_PATH" ]; then
    echo "[ERROR] Virtual environment '$VENV_PATH' not found." >&2
    echo "[ERROR] Please run the deployment script first." >&2
    exit 1
fi

# Check for indexer script
if [ ! -f "$INDEXER_SCRIPT" ]; then
    echo "[ERROR] Indexer script '$INDEXER_SCRIPT' not found in $(pwd)." >&2
    exit 1
fi

# Prompt for the new archive directory path
read -p "Enter the FULL, absolute path to the archive data directory: " ARCHIVE_PATH

# Basic path validation
if [ -z "$ARCHIVE_PATH" ]; then
    echo "[ERROR] Archive path cannot be empty." >&2
    exit 1
fi
# Attempt to make path absolute if user enters relative (though prompt asks for absolute)
ARCHIVE_PATH=$(realpath -m "$ARCHIVE_PATH") 
if [ ! -d "$ARCHIVE_PATH" ]; then
    echo "[ERROR] Provided path '$ARCHIVE_PATH' is not a valid directory or does not exist." >&2
    exit 1
fi
echo "[INFO] Indexing target directory set to: $ARCHIVE_PATH"

# Activate virtual environment
echo "[INFO] Activating virtual environment ($VENV_PATH)..."
source "$VENV_PATH/bin/activate"

# Run the indexer
echo "[INFO] Starting indexer.py..."
echo "[INFO] Target: $ARCHIVE_PATH"
echo "[INFO] This may take a long time depending on the data size..."

"$PYTHON_CMD" "$INDEXER_SCRIPT" "$ARCHIVE_PATH"

INDEXER_EXIT_CODE=$?

# Deactivate
echo "[INFO] Deactivating virtual environment..."
deactivate

if [ $INDEXER_EXIT_CODE -eq 0 ]; then
    echo "[SUCCESS] indexer.py completed successfully." 
    echo "[NEXT STEPS]"
    echo "1. Ensure the DENKRAUM_ARCHIVE_DIR environment variable for the web server is set to: $INSTALL_DIR"
    echo "   (This is the directory *containing* the indexed data relative paths)."
    echo "2. Restart the web server (e.g., using ./restart_server.sh or systemctl) to apply the environment variable."
else
    echo "[ERROR] indexer.py failed with exit code $INDEXER_EXIT_CODE." >&2
    echo "[ERROR] Check '$INSTALL_DIR/indexing_errors.log' for details." >&2
    exit 1
fi

echo "--- Re-indexing script finished ---"
exit 0 