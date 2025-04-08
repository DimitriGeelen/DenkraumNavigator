#!/bin/bash

# Reliable Server Restart Script (Using Gunicorn)

# Find the directory where the script is located (should be project root)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$SCRIPT_DIR" # Assuming script is in project root

# Define paths & Settings
VENV_DIR="$PROJECT_ROOT/.venv"
PYCACHE_DIR="$PROJECT_ROOT/__pycache__"
GUNICORN="$VENV_DIR/bin/gunicorn"
APP_MODULE="app:app" # Gunicorn format: module_name:flask_app_instance
LOG_FILE="$PROJECT_ROOT/flask_server.log" # Log file for gunicorn
ACCESS_LOG="$PROJECT_ROOT/gunicorn_access.log"
ERROR_LOG="$PROJECT_ROOT/gunicorn_error.log"
BIND_ADDR="0.0.0.0:5000"
WORKERS=2 # Number of worker processes

echo "Executing reliable server restart procedure (using Gunicorn)..."

# 1. Kill whatever process is using port 5000
echo "Step 1: Forcefully stopping any running Gunicorn processes..."
pkill -f gunicorn || echo "No running Gunicorn processes found or pkill failed (continuing)."
sleep 1

# Step 1.5: Clear Python bytecode cache
echo "Step 1.5: Clearing __pycache__ directory..."
rm -rf "$PYCACHE_DIR"

# Wait a moment for the port to potentially free up
sleep 2 # Increased sleep time slightly

# 2. Start new Gunicorn server process
echo "Step 2: Starting new Gunicorn server process in background..."
if [ -f "$GUNICORN" ]; then
    # Activate venv (gunicorn might need it to find app and dependencies)
    source "$VENV_DIR/bin/activate"
    
    # Set virtual memory limit (8GB = 8388608 KB)
    echo "Setting virtual memory ulimit to 8GB..."
    ulimit -v 8388608
    # Set resident memory limit (RSS) - less reliable enforcement
    echo "Setting resident memory ulimit to 8GB..."
    ulimit -m 8388608
    
    # Use nohup for backgrounding + redirect stdout/stderr to log file
    # Gunicorn options:
    # --bind: Address and port to listen on
    # --workers: Number of worker processes
    # --timeout: Worker timeout
    # --log-level: Logging level (e.g., info, debug)
    # --access-logfile: Path for access logs
    # --error-logfile: Path for error logs
    nohup "$GUNICORN" --bind "$BIND_ADDR" --workers "$WORKERS" --timeout 60 --log-level info --access-logfile "$ACCESS_LOG" --error-logfile "$ERROR_LOG" "$APP_MODULE" &
    
    # Deactivate venv if needed, though background process might inherit it
    # deactivate 

    # Check if the process started (check exit code of nohup initiation)
    if [ $? -eq 0 ]; then
        echo "Gunicorn server start command initiated successfully (running in background). Check $ERROR_LOG for output/errors."
        # Give the server a brief moment to write initial logs
        sleep 3 
        echo "\n--------------------------- Last 15 lines of $ERROR_LOG ---------------------------"
        tail -n 15 "$ERROR_LOG"
        echo "--------------------------- End of log tail ---------------------------"
        echo "Access logs are in: $ACCESS_LOG"
    else
        echo "ERROR: Failed to initiate Gunicorn server start command." >&2
        exit 1
    fi
else
    echo "ERROR: Cannot find Gunicorn executable ($GUNICORN). Is it installed in the venv?" >&2
    exit 1
fi

echo "Gunicorn restart procedure initiated."
exit 0 