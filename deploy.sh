#!/bin/bash

# Deployment script for DenkraumNavigator on a new Debian/Ubuntu server
# Assumes script is run with sudo privileges or by root

set -e # Exit immediately if a command exits with a non-zero status.
set -u # Treat unset variables as an error.

# --- Configuration ---
REPO_URL="https://github.com/DimitriGeelen/DenkraumNavigator.git"
INSTALL_DIR="/opt/DenkraumNavigator" # Directory to clone the repo into
APP_USER=$(logname) # Use the user who logged in (avoids root if sudo is used)
ARCHIVE_DIR="/dol-data-archive2" # Location where user must place archive files
DB_FILENAME="file_index.db" # Name of the database file
PYTHON_CMD="python3" # Command to run python
VENV_DIR=".venv" # Name of the virtual environment directory
DB_ZIP_FILENAME="file_index.zip" # Name of the database zip file
APP_PORT="5000" # Port the application runs on

# --- Helper Functions ---
echo_info() {
    echo "[INFO] $1"
}

echo_warn() {
    echo "[WARN] $1"
}

echo_step() {
    echo "\n=== STEP: $1 ==="
}

# --- Sanity Checks ---
if [[ $EUID -eq 0 ]]; then
   echo_info "Script running as root. Will set ownership to user '$APP_USER'."
   # Ensure APP_USER actually exists if running as root
   if ! id "$APP_USER" &>/dev/null; then
       echo "[ERROR] User '$APP_USER' not found. Cannot set ownership." >&2
       exit 1
   fi
else
    echo_info "Script running as user $(whoami). Ensure you have sudo privileges if needed for apt/ufw."
    # Check if sudo is available if not root
    if ! command -v sudo &> /dev/null; then
        echo "[ERROR] sudo command not found. This script requires sudo privileges." >&2
        exit 1
    fi
fi

# --- Installation Steps ---

echo_step "Updating package lists and installing dependencies"
sudo apt-get update
sudo apt-get install -y git $PYTHON_CMD ${PYTHON_CMD}-venv unzip ufw # Added ufw
echo_info "Dependencies installed: git, python3, python3-venv, unzip, ufw"

echo_step "Cloning/Updating repository from $REPO_URL"
if [ -d "$INSTALL_DIR/.git" ]; then
    echo_info "Directory $INSTALL_DIR exists. Pulling latest changes..."
    cd $INSTALL_DIR
    sudo -u $APP_USER git stash push -m "deploy.sh stash $(date +%s)" || echo_info "No local changes to stash."
    sudo -u $APP_USER git pull origin master # Or your default branch
    sudo -u $APP_USER git stash pop || echo_info "No stash to pop."
    cd -
else
    sudo git clone $REPO_URL $INSTALL_DIR
    echo_info "Repository cloned to $INSTALL_DIR"
fi

echo_step "Setting ownership of $INSTALL_DIR to $APP_USER"
sudo chown -R $APP_USER:$APP_USER $INSTALL_DIR
echo_info "Ownership set."

# Go into the directory
cd $INSTALL_DIR
echo_info "Changed directory to $INSTALL_DIR"

# --- Python Virtual Environment Setup --- 
echo_step "Setting up Python virtual environment in $VENV_DIR (if needed)"
if [ ! -d "$VENV_DIR" ]; then
    echo_info "No virtual environment found, creating one..."
    sudo -u $APP_USER $PYTHON_CMD -m venv $VENV_DIR
    echo_info "Virtual environment created."
else
    echo_info "Virtual environment '$VENV_DIR' already exists."
fi

echo_step "Installing/Updating Python packages from requirements.txt"
sudo -u $APP_USER bash -c "source $VENV_DIR/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"
echo_info "Python packages installed/updated."

# --- Extract Database from Zip ---
echo_step "Extracting database from $DB_ZIP_FILENAME"
DB_ZIP_PATH="$INSTALL_DIR/$DB_ZIP_FILENAME"
DB_PATH="$INSTALL_DIR/$DB_FILENAME"
if [ -f "$DB_ZIP_PATH" ]; then
    echo_info "Found $DB_ZIP_FILENAME. Extracting $DB_FILENAME..."
    sudo -u $APP_USER unzip -o "$DB_ZIP_PATH" -d "$INSTALL_DIR" "$DB_FILENAME" 
    if [ $? -ne 0 ]; then # Check unzip exit status
        echo "[ERROR] Failed to extract $DB_FILENAME from $DB_ZIP_FILENAME." >&2
        exit 1
    fi
    sudo chown $APP_USER:$APP_USER "$DB_PATH"
    echo_info "Successfully extracted $DB_FILENAME."
else
    echo "[ERROR] $DB_ZIP_FILENAME not found in $INSTALL_DIR!" >&2
    echo "[ERROR] Cannot proceed without the database zip from the repository." >&2
    exit 1
fi

# --- Verify Database File Presence (Post-Extraction) ---
echo_step "Verifying database file presence"
if [ -f "$DB_PATH" ]; then
    echo_info "Database file $DB_FILENAME found in $INSTALL_DIR."
else
    echo "[ERROR] Database file $DB_FILENAME NOT found in $INSTALL_DIR after extraction attempt!" >&2
    exit 1
fi

echo_step "Creating necessary directories (if they don't exist)"
sudo -u $APP_USER mkdir -p backups thumbnail_cache
echo_info "Ensured directories exist: backups/, thumbnail_cache/"

echo_step "Setting execute permissions for scripts"
sudo -u $APP_USER chmod +x *.sh version_bumper.py || echo "[WARNING] No .sh/version_bumper.py files found to set permissions on."
echo_info "Set execute permissions for .sh and version_bumper.py files (if found)."

# --- Configure Firewall --- 
echo_step "Configuring Firewall (ufw)"
if sudo ufw status | grep -qw inactive; then
    echo_warn "ufw is inactive. Enabling firewall and allowing SSH (default port 22)."
    sudo ufw allow ssh
    sudo ufw enable
fi
sudo ufw allow ${APP_PORT}/tcp comment "DenkraumNavigator App Port"
echo_info "Firewall rule added to allow TCP traffic on port ${APP_PORT}."

# --- Manual Step Reminder (ARCHIVE DATA ONLY) --- 
echo_step "Manual Actions Required"
echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
echo "!! Before starting the server, you MUST manually copy the                   !!"
echo "!! ARCHIVE DATA into the directory:                                       !!"
echo "!!    $ARCHIVE_DIR                                                              !!"
echo "!!                                                                          !!"
echo "!! (Optional) You may also copy the contents of the 'backups/' directory    !!"
echo "!! from the source to '$INSTALL_DIR/backups/'.                                !!"
echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
read -p "Press [Enter] key ONLY after you have copied the Archive Data..." REPLY


# --- Check Port Availability --- 
echo_step "Checking if port ${APP_PORT} is in use"
if ss -tlpn | grep -q ":${APP_PORT}\b"; then 
    echo_warn "Port ${APP_PORT} appears to be in use. The restart script or manual start might fail if the service doesn't stop properly."
else
    echo_info "Port ${APP_PORT} appears to be free."
fi

# --- Completion ---
echo_step "Deployment Setup Complete!"
echo_info "Application installed in: $INSTALL_DIR"
echo_info "Database extracted from $DB_ZIP_FILENAME: $DB_PATH"
echo_info "Firewall configured to allow port ${APP_PORT}/tcp."
echo_info "To start the application server using Gunicorn:"
echo "1. Change directory: cd $INSTALL_DIR"
echo "2. Run the restart script: ./restart_server.sh"
echo "   (This will start Gunicorn in the background. See logs in $INSTALL_DIR/gunicorn_*.log)"
echo "Access the application in your browser (usually http://<server_ip>:${APP_PORT})."
echo ""
echo "To manually update the index later (e.g., after adding data to $ARCHIVE_DIR):"
echo "  cd $INSTALL_DIR && source $VENV_DIR/bin/activate && python indexer.py"

exit 0 