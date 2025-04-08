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
PORT="5000" # Define the port
WORKERS=2 # Adjust as needed (e.g., based on CPU cores)

echo "Executing reliable server restart procedure (using Gunicorn)..."

# --- Dynamically Detect LAN IP --- 
echo "Step 0: Detecting LAN IP address..."
# Get the first global scope IPv4 address, excluding 127.0.0.1
LAN_IP=$(ip -4 addr show scope global | grep 'inet' | awk '{print $2}' | cut -d/ -f1 | head -n 1)

if [ -z "$LAN_IP" ]; then
    echo "ERROR: Could not automatically detect a suitable LAN IP address." >&2
    echo "Please check network configuration or manually set BIND_ADDR in the script." >&2
    exit 1
fi
echo "Detected LAN IP: $LAN_IP"
BIND_ADDR="${LAN_IP}:${PORT}"
echo "Gunicorn will bind to: $BIND_ADDR"
# --- End IP Detection ---


# 1. Attempt to stop existing Gunicorn process
echo "Step 1: Checking and stopping existing Gunicorn process..."
STOPPED_GRACEFULLY=false
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null; then
        echo "Found running Gunicorn process (PID: $PID). Attempting graceful shutdown (TERM)..."
        kill -TERM $PID
        # Wait for shutdown
        TIMEOUT=10
        while [ $TIMEOUT -gt 0 ] && ps -p $PID > /dev/null; do
            echo "Waiting for Gunicorn (PID: $PID) to shut down... (${TIMEOUT}s)"
            sleep 1
            ((TIMEOUT--))
        done

        if ps -p $PID > /dev/null; then
            echo "Gunicorn (PID: $PID) did not shut down gracefully. Forcing kill (KILL)..."
            kill -KILL $PID # Use KILL signal for force
            sleep 1
        else
            echo "Gunicorn (PID: $PID) shut down gracefully."
            STOPPED_GRACEFULLY=true
        fi
    else
        echo "PID file found, but process (PID: $PID) is not running. Cleaning up stale PID file."
    fi
    # Always remove PID file if it exists
    rm -f "$PID_FILE"
else
    echo "No PID file found."
fi

# Check if port is still in use, even if PID file was missing or process was killed
echo "Step 1.1: Verifying port ${PORT} is free..."
RETRY_COUNT=0
MAX_RETRIES=3
while fuser "${PORT}/tcp" > /dev/null 2>&1 && [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    ((RETRY_COUNT++))
    echo "Port ${PORT} is still in use. Attempting to kill process holding it (Attempt $RETRY_COUNT/$MAX_RETRIES)..."
    
    # Try graceful termination first
    echo "Sending TERM signal via fuser..."
    fuser -k -TERM "${PORT}/tcp"
    sleep 2 # Wait for graceful termination
    
    if fuser "${PORT}/tcp" > /dev/null 2>&1; then
        echo "Graceful kill failed. Sending KILL signal via fuser..."
        fuser -k -KILL "${PORT}/tcp"
        sleep 2 # Wait after forceful kill
    else
        echo "Process terminated after TERM signal."
    fi
done

if fuser "${PORT}/tcp" > /dev/null 2>&1; then
    echo "ERROR: Port ${PORT} is still in use after $MAX_RETRIES kill attempts. Cannot start Gunicorn." >&2
    exit 1
else
    echo "Port ${PORT} is confirmed free."
fi


# Step 1.5: Clear Python bytecode cache
echo "Step 1.5: Clearing __pycache__ directory..."
rm -rf "$PYCACHE_DIR"

# Wait a moment longer for the port to definitely free up
echo "Waiting 3 seconds before starting new process..."
sleep 3

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
# --bind: Address and port (Now uses dynamic $BIND_ADDR)
# --workers: Number of worker processes
# --timeout: Worker timeout
# --log-level: Logging level (info, debug, etc.)
# --access-logfile: Path for access logs
# --error-logfile: Path for error logs
# --pid: Path to store PID file
# --daemon: Run in the background

# <<< ADDED: Set the environment variable for the archive directory >>>
export DENKRAUM_ARCHIVE_DIR="/opt/dol-data-archive2"
echo "Setting DENKRAUM_ARCHIVE_DIR to $DENKRAUM_ARCHIVE_DIR"

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
        echo "Gunicorn server started successfully (PID: $NEW_PID), bound to $BIND_ADDR. Check logs for details:"
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