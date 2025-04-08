# Deployment Notes for DenkraumNavigator

This document provides instructions and information for deploying, configuring, and maintaining the DenkraumNavigator application on a Debian/Ubuntu server.

## Prerequisites

*   Debian/Ubuntu based server.
*   `sudo` privileges for package installation and service management.
*   Installed packages (handled by `deploy.sh`):
    *   `git`
    *   `python3`
    *   `python3-venv`
    *   `unzip`
    *   `ufw` (Uncomplicated Firewall)
*   **(Recommended for OCR)** Tesseract OCR engine (`tesseract-ocr`). If not installed, image text extraction will be skipped during indexing.

## 1. Initial Deployment

1.  **Clone Repository:** Clone this repository to a temporary location on the server (e.g., `/root/DenkraumNavigator` or `/home/your_user/DenkraumNavigator`).
2.  **Run Deployment Script:** Navigate into the cloned directory and run the deployment script with `sudo`:
    ```bash
    cd /path/to/cloned/repo
    sudo ./deploy.sh
    ```
3.  **What `deploy.sh` does:**
    *   Updates package lists and installs dependencies (`git`, `python3`, `python3-venv`, `unzip`, `ufw`).
    *   Clones or updates the application code into `/opt/DenkraumNavigator`.
    *   Sets ownership of `/opt/DenkraumNavigator` to the user who invoked `sudo` (or `root`'s logged-in user).
    *   Creates a Python virtual environment (`.venv`) inside `/opt/DenkraumNavigator` if it doesn't exist.
    *   Installs required Python packages from `requirements.txt` into the `.venv`.
    *   Extracts `file_index.db` from `file_index.zip` located in the repository root.
    *   Creates `backups/` and `thumbnail_cache/` directories if they don't exist.
    *   Sets execute permissions on `.sh` scripts and `version_bumper.py`.
    *   Configures `ufw` firewall: Enables it (if inactive), allows SSH (port 22), allows the application port (default 5000/tcp).
    *   Prompts the user to copy the archive data.

## 2. Post-Deployment Configuration (Manual Steps)

These steps are crucial after the `deploy.sh` script finishes.

1.  **Copy/Move Archive Data:**
    *   **IMPORTANT:** The application and indexer expect the archive data to be located at:
        `/opt/DenkraumNavigator/dol-data-archive2`
    *   Manually copy or move your entire archive data directory structure to this location.
2.  **Set Permissions:**
    *   The user that the web server (Gunicorn) runs as needs read and execute permissions on the archive directory and its contents.
    *   Determine the web server user (often `www-data`, or the user specified in a systemd service file).
    *   Run the following commands, replacing `<web_user>:<web_group>` with the correct user/group:
        ```bash
        sudo chown -R <web_user>:<web_group> /opt/DenkraumNavigator/dol-data-archive2
        # Example permissions (Owner RWX, Group RX, Other RX):
        sudo find /opt/DenkraumNavigator/dol-data-archive2 -type d -exec chmod 755 {} \;
        sudo find /opt/DenkraumNavigator/dol-data-archive2 -type f -exec chmod 644 {} \;
        ```
3.  **Set Environment Variable (`DENKRAUM_ARCHIVE_DIR`):**
    *   This variable tells the Flask application where the *base directory* for the indexed paths is located. After moving the data and re-indexing, the database paths will start with `dol-data-archive2/...`. Therefore, the Flask app needs to know the base directory containing this structure.
    *   Set the `DENKRAUM_ARCHIVE_DIR` environment variable **persistently** for the web server process to:
        `DENKRAUM_ARCHIVE_DIR="/opt/DenkraumNavigator"`
    *   **How to set:**
        *   **Systemd:** Edit the service file (e.g., `/etc/systemd/system/denkraum-navigator.service`) and add/modify the `Environment=` line:
            ```ini
            [Service]
            # ... other directives ...
            Environment="DENKRAUM_ARCHIVE_DIR=/opt/DenkraumNavigator"
            # ...
            ```
            Then run `sudo systemctl daemon-reload`.
        *   **Other Methods:** Consult documentation for your process manager or shell profile (`~/.profile`, `/etc/environment`, etc.), ensuring the variable is available when Gunicorn starts.
4.  **Re-Index Data:**
    *   Since you've moved the data and the original database likely contains paths relative to a different root (like `/`), you **must** re-index the data from its new location.
    *   Use the `reindex.sh` script:
        ```bash
        cd /opt/DenkraumNavigator
        ./reindex.sh
        ```
    *   When prompted, enter the full path to the archive data:
        `/opt/DenkraumNavigator/dol-data-archive2`
    *   This will activate the virtual environment, run `indexer.py`, and update `file_index.db` with paths relative to the new base directory (e.g., storing `dol-data-archive2/Denken 2016-2024/...`).

## 3. Starting / Stopping / Restarting the Server

*   **Always run restart scripts from the application directory:** `cd /opt/DenkraumNavigator`
*   **Development/General Use:**
    *   `./restart_server.sh`
    *   Binds Gunicorn to `0.0.0.0:5000` (listens on all interfaces). Accessible via `localhost` and LAN IP.
*   **Production Use (Specific LAN IP):**
    *   `./restart_server_prod.sh`
    *   Attempts to detect the primary LAN IP and binds Gunicorn only to `<LAN_IP>:5000`. Not accessible via `localhost`. Ensure the detected IP is correct.
*   **Stopping:** The restart scripts handle stopping previous instances. Manually, find the PID in `gunicorn.pid` and use `kill <PID>`.
*   **Logs:** Check `gunicorn_access.log` and `gunicorn_error.log` in `/opt/DenkraumNavigator`.

## 4. Updating the Application

1.  Navigate to the application directory: `cd /opt/DenkraumNavigator`
2.  Pull the latest changes from Git: `sudo -u $APP_USER git pull origin master` (replace `$APP_USER` with the correct user if needed).
3.  Re-run the deployment script to update dependencies and apply any necessary setup: `sudo ./deploy.sh`
4.  Restart the application server using the appropriate restart script (`./restart_server.sh` or `./restart_server_prod.sh`).

## 5. Key File/Directory Locations

*   `/opt/DenkraumNavigator`: Application Root (code, venv, logs, scripts).
*   `/opt/DenkraumNavigator/.venv`: Python Virtual Environment.
*   `/opt/DenkraumNavigator/dol-data-archive2`: **Intended location for the actual archive data** after moving and re-indexing.
*   `/opt/DenkraumNavigator/file_index.db`: Live SQLite database.
*   `/opt/DenkraumNavigator/file_index.zip`: Committed database zip (used by `deploy.sh`).
*   `/opt/DenkraumNavigator/gunicorn_access.log`, `gunicorn_error.log`: Gunicorn web server logs.
*   `/opt/DenkraumNavigator/indexing_errors.log`: Log file for `indexer.py` errors.
*   `/opt/DenkraumNavigator/backups/`: Directory for database/code backups created by the post-commit hook or manually.
*   `/opt/DenkraumNavigator/thumbnail_cache/`: Directory for generated image thumbnails.

## 6. Troubleshooting

*   **"Address already in use" Error:** Stop the existing process using `kill $(cat gunicorn.pid)` or by identifying the process using `sudo ss -tlpn | grep ':5000'` and killing it manually. Then run the restart script again.
*   **File Not Found (Downloads/Thumbnails):**
    *   Verify the `DENKRAUM_ARCHIVE_DIR` environment variable is correctly set (to `/opt/DenkraumNavigator`) where the server process runs (e.g., systemd service file).
    *   Verify the data was moved to `/opt/DenkraumNavigator/dol-data-archive2`.
    *   Verify the indexer was run using `reindex.sh` pointing to `/opt/DenkraumNavigator/dol-data-archive2`.
    *   Verify the web server user has read/execute permissions on `/opt/DenkraumNavigator/dol-data-archive2` and its contents.
    *   Check the `/config` page to see the path Flask is currently using (if available).
*   **Permission Denied Errors:** Ensure the user running Gunicorn has appropriate read/execute permissions for the archive directory and read permissions for files. Refer to step 2.2.
*   **Indexer Errors:** Check `/opt/DenkraumNavigator/indexing_errors.log` for details. 