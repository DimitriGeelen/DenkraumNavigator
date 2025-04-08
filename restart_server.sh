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
# Use distinct log files for gunicorn
ACCESS_LOG="$PROJECT_ROOT/gunicorn_access.log"
ERROR_LOG="$PROJECT_ROOT/gunicorn_error.log"
PID_FILE="$PROJECT_ROOT/gunicorn.pid"
BIND_ADDR="0.0.0.0:5000"
WORKERS=2 # Adjust as needed (e.g., based on CPU cores)

echo "Executing reliable server restart procedure (using Gunicorn)..."

# 1. Check if PID file exists and process is running
echo "Step 1: Checking for existing Gunicorn process (PID file: $PID_FILE)..."
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null; then
        echo "Found running Gunicorn process (PID: $PID). Attempting graceful shutdown..."
        kill $PID
        # Wait for shutdown
        TIMEOUT=10
        while [ $TIMEOUT -gt 0 ] && ps -p $PID > /dev/null; do
            echo "Waiting for Gunicorn (PID: $PID) to shut down... (${TIMEOUT}s)"
            sleep 1
            ((TIMEOUT--))
        done

        if ps -p $PID > /dev/null; then
            echo "Gunicorn did not shut down gracefully. Forcing kill..."
            kill -9 $PID
            sleep 1
        else
            echo "Gunicorn shut down gracefully."
        fi
    else
        echo "PID file found, but process (PID: $PID) is not running. Cleaning up stale PID file."
    fi
    rm -f "$PID_FILE"
else
    echo "No PID file found. Attempting to kill any Gunicorn processes listening on $BIND_ADDR..."
    # Fallback: Try killing by port/process name (less reliable)
    pkill -f "gunicorn.*${BIND_ADDR}" || echo "No running Gunicorn processes found listening on ${BIND_ADDR} or pkill failed."
    sleep 1
fi


# Step 1.5: Clear Python bytecode cache
echo "Step 1.5: Clearing __pycache__ directory..."
rm -rf "$PYCACHE_DIR"

# Wait a moment for the port to potentially free up
sleep 2 

# 2. Start new Gunicorn server process
echo "Step 2: Starting new Gunicorn server process in background..."
if [ ! -f "$GUNICORN" ]; then
    echo "ERROR: Cannot find Gunicorn executable ($GUNICORN). Ensure it's installed ('pip install gunicorn')." >&2
    exit 1
fi

# Activate venv (needed for Gunicorn to find app and dependencies)
echo "Activating virtual environment: $VENV_DIR"
source "$VENV_DIR/bin/activate"

# Set memory limits (optional, adjust as needed)
echo "Setting virtual memory ulimit to 8GB..."
ulimit -v 8388608
echo "Setting resident memory ulimit to 8GB..."
ulimit -m 8388608

echo "Starting Gunicorn..."
# Gunicorn options:
# --bind: Address and port
# --workers: Number of worker processes
# --timeout: Worker timeout
# --log-level: Logging level (info, debug, etc.)
# --access-logfile: Path for access logs
# --error-logfile: Path for error logs
# --pid: Path to store PID file
# --daemon: Run in the background
"$GUNICORN" --bind "$BIND_ADDR" \
            --workers "$WORKERS" \
            --timeout 60 \
            --log-level info \
            --access-logfile "$ACCESS_LOG" \
            --error-logfile "$ERROR_LOG" \
            --pid "$PID_FILE" \
            --daemon \
            "$APP_MODULE"

# Deactivate venv
deactivate

# Check if the process started
sleep 2 # Give Gunicorn a moment to start and write PID file
if [ -f "$PID_FILE" ]; then
    NEW_PID=$(cat "$PID_FILE")
    if ps -p $NEW_PID > /dev/null; then
        echo "Gunicorn server started successfully (PID: $NEW_PID). Check logs for details:"
        echo "  Access Log: $ACCESS_LOG"
        echo "  Error Log:  $ERROR_LOG"
        echo "\n--------------------------- Last 10 lines of $ERROR_LOG ---------------------------"
        tail -n 10 "$ERROR_LOG"
        echo "--------------------------- End of log tail ---------------------------"
    else
        echo "ERROR: PID file created, but Gunicorn process (PID: $NEW_PID) is not running. Check $ERROR_LOG." >&2
        rm -f "$PID_FILE"
        exit 1
    fi
else
    echo "ERROR: Failed to start Gunicorn server. PID file not found. Check $ERROR_LOG." >&2
    exit 1
fi

echo "Gunicorn restart procedure completed."
exit 0 