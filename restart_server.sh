#!/bin/bash

# Reliable Server Restart Script (Using Gunicorn)

# Find the directory where the script is located (should be project root)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$SCRIPT_DIR" # Assuming script is in project root

# Define paths & Settings
VENV_DIR="$PROJECT_ROOT/.venv"
GUNICORN="$VENV_DIR/bin/gunicorn"
APP_MODULE="app:app" # Gunicorn format: module_name:flask_app_instance
LOG_FILE="$PROJECT_ROOT/flask_server.log" # Log file for gunicorn
BIND_ADDR="0.0.0.0:5000"
WORKERS=2 # Number of worker processes

echo "Executing reliable server restart procedure (using Gunicorn)..."

# 1. Kill whatever process is using port 5000
echo "Step 1: Stopping process using TCP port 5000..."
fuser -k -n tcp 5000 || echo "No process found on port 5000 or fuser failed (continuing)."

# Wait a moment for the port to potentially free up
sleep 2 # Increased sleep time slightly

# 2. Start new Gunicorn server process
echo "Step 2: Starting new Gunicorn server process in background..."
if [ -f "$GUNICORN" ]; then
    # Activate venv (gunicorn might need it to find app and dependencies)
    source "$VENV_DIR/bin/activate"
    
    # Use nohup for backgrounding + redirect stdout/stderr to log file
    # Gunicorn options:
    # --bind: Address and port to listen on
    # --workers: Number of worker processes
    # --log-level: Logging level (e.g., info, debug)
    # --access-logfile / --error-logfile: Specify log files (using >> $LOG_FILE 2>&1 for simplicity here)
    # --daemon: Run in the background (Alternative to nohup &)
    nohup "$GUNICORN" --bind "$BIND_ADDR" --workers "$WORKERS" --log-level debug "$APP_MODULE" >> "$LOG_FILE" 2>&1 &
    
    # Deactivate venv if needed, though background process might inherit it
    # deactivate 

    # Check if the process started (check exit code of nohup initiation)
    if [ $? -eq 0 ]; then
        echo "Gunicorn server start command initiated successfully (running in background). Check $LOG_FILE for output/errors."
        # Give the server a brief moment to write initial logs
        sleep 3 
        echo "\n--------------------------- Last 15 lines of $LOG_FILE ---------------------------"
        tail -n 15 "$LOG_FILE"
        echo "--------------------------- End of log tail ---------------------------"
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