#!/bin/bash

# Deployment script for DenkraumNavigator on a new Debian/Ubuntu server
# Assumes script is run with sudo privileges or by root
# REPLICATES environment using EXISTING database (user must copy it).

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

# --- Helper Functions ---
echo_info() {
    echo "[INFO] $1"
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
    echo_info "Script running as user $(whoami). Ensure you have sudo privileges if needed for apt."
    # Check if sudo is available if not root
    if ! command -v sudo &> /dev/null; then
        echo "[WARNING] sudo command not found. apt commands might fail if run as non-root." >&2
    fi
fi

# --- Installation Steps ---

echo_step "Updating package lists and installing dependencies"
sudo apt-get update
sudo apt-get install -y git $PYTHON_CMD ${PYTHON_CMD}-venv unzip # Added unzip
echo_info "Dependencies installed: git, python3, python3-venv, unzip"

echo_step "Cloning/Updating repository from $REPO_URL"
if [ -d "$INSTALL_DIR/.git" ]; then
    echo_info "Directory $INSTALL_DIR exists. Pulling latest changes..."
    cd $INSTALL_DIR
    # Stash local changes, pull, pop stash (handle potential conflicts manually later if needed)
    sudo -u $APP_USER git stash || echo_info "No local changes to stash."
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

echo_step "Setting up Python virtual environment in $VENV_DIR"
sudo -u $APP_USER $PYTHON_CMD -m venv $VENV_DIR
echo_info "Virtual environment created/updated."

echo_step "Activating virtual environment and installing/updating Python packages"
sudo -u $APP_USER bash -c "source $VENV_DIR/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"
echo_info "Python packages installed/updated from requirements.txt"

# --- Extract Database from Zip ---
echo_step "Extracting database from $DB_ZIP_FILENAME (if exists)"
DB_ZIP_PATH="$INSTALL_DIR/$DB_ZIP_FILENAME"
DB_PATH="$INSTALL_DIR/$DB_FILENAME"
if [ -f "$DB_ZIP_PATH" ]; then
    echo_info "Found $DB_ZIP_FILENAME. Extracting $DB_FILENAME..."
    # Run unzip as the app user, overwrite existing file (-o), extract to install dir (-d)
    sudo -u $APP_USER unzip -o "$DB_ZIP_PATH" -d "$INSTALL_DIR" "$DB_FILENAME" 
    if [ $? -ne 0 ]; then # Check unzip exit status
        echo "[ERROR] Failed to extract $DB_FILENAME from $DB_ZIP_FILENAME." >&2
        exit 1
    fi
    if [ ! -f "$DB_PATH" ]; then # Verify extraction
        echo "[ERROR] $DB_FILENAME not found after attempting extraction from $DB_ZIP_FILENAME." >&2
        exit 1
    fi
    # Set ownership just in case
    sudo chown $APP_USER:$APP_USER "$DB_PATH"
    echo_info "Successfully extracted $DB_FILENAME."
else
    echo "[ERROR] $DB_ZIP_FILENAME not found in $INSTALL_DIR!" >&2
    echo "[ERROR] This deployment method requires the zipped database to be present in the repository." >&2
    echo "[ERROR] Please ensure the version you are deploying was tagged correctly using the updated version bumper." >&2
    exit 1
fi

echo_step "Creating necessary directories (if they don't exist)"
sudo -u $APP_USER mkdir -p backups thumbnail_cache
echo_info "Ensured directories exist: backups/, thumbnail_cache/"

echo_step "Setting execute permissions for scripts"
sudo -u $APP_USER chmod +x *.sh version_bumper.py || echo "[WARNING] No .sh/version_bumper.py files found to set permissions on."
echo_info "Set execute permissions for .sh and version_bumper.py files (if found)."

# --- Manual Step Reminder --- MODIFIED PROMPT ---
echo_step "Manual Actions Required"
echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
echo "!! Before proceeding, you MUST manually copy the following from your SOURCE !!"
echo "!! environment to this TARGET server:                                       !!"
echo "!!                                                                          !!"
echo "!! 1. The **Archive Data** into the directory:                              !!"
echo "!!    $ARCHIVE_DIR                                                              !!"
echo "!!                                                                          !!"
echo "!! 2. The **EXISTING Database File** ($DB_FILENAME) into the application directory: !!"
echo "!!    $INSTALL_DIR/$DB_FILENAME                                            !!"
echo "!!                                                                          !!"
echo "!! (Optional) You may also copy the contents of the 'backups/' directory    !!"
echo "!! from the source to '$INSTALL_DIR/backups/'.                                !!"
echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
read -p "Press [Enter] key ONLY after you have copied the Archive Data AND the Database File..." REPLY

# --- Verify Database File (This step is less critical now but good sanity check) ---
echo_step "Verifying database file presence"
if [ -f "$DB_PATH" ]; then
    echo_info "Database file $DB_FILENAME found in $INSTALL_DIR."
else
    echo "[ERROR] Database file $DB_FILENAME NOT found in $INSTALL_DIR after extraction attempt!" >&2
    exit 1
fi

# --- Completion ---
echo_step "Deployment Setup Complete!"
echo_info "Database extracted from $DB_ZIP_FILENAME: $DB_PATH (Expected name: $DB_FILENAME)"
echo_info "To start the application server:"
echo "1. Change directory: cd $INSTALL_DIR"
echo "2. Activate environment: source $VENV_DIR/bin/activate"
echo "3. Run the server: python app.py"
echo "   (Alternatively, use ./restart_server.sh)"
echo "Access the application in your browser (usually http://<server_ip>:5000)."
echo ""
echo "To manually update the index later (e.g., after adding data to $ARCHIVE_DIR):"
echo "  cd $INSTALL_DIR && source $VENV_DIR/bin/activate && python indexer.py"

exit 0 