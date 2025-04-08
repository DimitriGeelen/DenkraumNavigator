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
    echo "No PID file found. Attempting to kill any Gunicorn processes listening on port ${PORT}..."
    # Fallback: Try killing by port/process name (less reliable)
    # Updated pkill pattern to be more specific to the port
    PIDS_TO_KILL=$(ss -tlpn 'sport = :'"$PORT" | grep gunicorn | awk '{print $7}' | sed -E 's/.*pid=([0-9]+).*/\1/')
    if [ -n "$PIDS_TO_KILL" ]; then
        echo "Found Gunicorn processes listening on port ${PORT}: $PIDS_TO_KILL. Killing..."
        kill $PIDS_TO_KILL || echo "Kill command failed (processes might already be gone)."
        sleep 1
    else
        echo "No running Gunicorn processes found listening on port ${PORT}."
    fi
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
# --bind: Address and port (Now uses dynamic $BIND_ADDR)
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