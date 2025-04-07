#!/bin/bash

# Reliable Server Restart Script

# Find the directory where the script is located (should be project root)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$SCRIPT_DIR" # Assuming script is in project root

# Define paths
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
APP_SCRIPT="$PROJECT_ROOT/app.py"
LOG_FILE="$PROJECT_ROOT/flask_server.log" # Log file for nohup

echo "Executing reliable server restart procedure..."

# 1. Kill existing server process
echo "Step 1: Stopping existing 'python app.py' processes..."
# Use the full path to app.py in pkill pattern for more specificity
pkill -9 -f "$VENV_PYTHON $APP_SCRIPT" || echo "No existing process found or pkill failed (continuing)."

# Wait a moment for the port to potentially free up
sleep 1

# 2. Start new server process
echo "Step 2: Starting new server process in background..."
if [ -f "$VENV_PYTHON" ] && [ -f "$APP_SCRIPT" ]; then
    # Use nohup to run independently of the terminal, redirect stdout/stderr
    # The '&' runs it in the background.
    nohup "$VENV_PYTHON" "$APP_SCRIPT" >> "$LOG_FILE" 2>&1 &
    # Check if the process started (check exit code of nohup initiation)
    if [ $? -eq 0 ]; then
        echo "Server start command initiated successfully (running in background). Check $LOG_FILE for output/errors."
        # Give the server a brief moment to write initial logs
        sleep 0.5 
        echo "\n--- Last 15 lines of $LOG_FILE ---"
        tail -n 15 "$LOG_FILE"
        echo "--- End of log tail ---"
    else
        echo "ERROR: Failed to initiate server start command." >&2
        exit 1
    fi
else
    echo "ERROR: Cannot find venv Python ($VENV_PYTHON) or app script ($APP_SCRIPT)." >&2
    exit 1
fi

echo "Restart procedure initiated."
exit 0 