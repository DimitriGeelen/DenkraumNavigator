# Database Management for DenkraumNavigator

This document outlines the key aspects of managing the `file_index.db` SQLite database used by the DenkraumNavigator application.

## Overview

*   **Filename:** `file_index.db`
*   **Location:** Project root directory (`/opt/DenkraumNavigator`)
*   **Purpose:** Stores metadata, extracted text, summaries, and keywords for files found within the configured archive directory.
*   **Git Status:** `file_index.db` is listed in `.gitignore` and should *not* be tracked by Git directly.

## Indexing

*   **Full Indexing Script:** `indexer.py`
    *   Scans the target directory recursively.
    *   Extracts metadata and text content from supported file types (including OCR for images if Tesseract is available).
    *   Generates summaries and keywords (using NLTK/Sumy).
    *   Uses an **upsert** mechanism (`INSERT ... ON CONFLICT DO UPDATE`) to add new file entries or update existing ones based on the unique file `path`.
    *   **Important:** Does *not* delete entries for files that are no longer found on the filesystem during its run.
    *   Can be run directly: `python3 indexer.py <directory_to_index> [database_file]` (ensure venv is active).
*   **Re-indexing Wrapper:** `reindex.sh`
    *   Provides a convenient way to run the full indexer (`indexer.py`).
    *   Handles activating the virtual environment and ensuring NLTK data is present.
    *   Prompts for or accepts the archive data directory path as an argument.
    *   **Important:** Does *not* delete the existing database file before running `indexer.py`.

## Backup Strategy

*   **Automatic Commit-Based Backups:**
    *   Handled by the Git hook script: `.git/hooks/post-commit`.
    *   **Trigger:** Runs automatically after every successful `git commit`.
    *   **Actions:**
        1.  Copies the current `file_index.db` -> `backups/commit_<short_hash>.db`.
        2.  Creates a code archive -> `backups/commit_<short_hash>.zip` (using `git archive`).
        3.  **Crucially:** Copies the just-created `backups/commit_<short_hash>.db` back to the project root, overwriting the working `file_index.db`. This ensures the working DB matches the state captured at the time of the commit backup.
*   **Manual Database Backups:**
    *   Can be triggered via the web interface (`/history` page -> "Create New Manual Database Backup Now" button).
    *   Creates a timestamped backup: `backups/file_index_<timestamp>.db`.

## Versioning (Database Snapshots)

*   **Problem:** The live `file_index.db` is ignored by Git, but we need a way to associate a specific database state with a tagged code version.
*   **Solution:** `file_index.zip`
    *   The `version_bumper.py` script (run via `safe_version_bump.sh` during version bumps - patch/minor/major) performs the following:
        1.  Takes the *current* working `file_index.db` (which should reflect the state after the last commit, due to the post-commit hook's copy-back mechanism).
        2.  Zips this database into `file_index.zip` in the project root.
        3.  Commits `file_index.zip` along with `VERSION` and `CHANGELOG.md` for the version bump commit.
        4.  Tags the commit (e.g., `v5.1.0`).
*   **Deployment:**
    *   The `deploy.sh` script expects `file_index.zip` to be present in the checked-out code version.
    *   It extracts `file_index.db` from `file_index.zip` to provide the initial database state corresponding to the deployed code version.

## Cleanup (Removing Dead Links)

*   **Problem:** Files deleted from the archive directory are not automatically removed from the `file_index.db` by the indexer.
*   **Solution:** `clean_up_database.py` script, run via `run_cleanup.sh` wrapper.
    *   **Script:** `clean_up_database.py`
        *   Connects to the database.
        *   Fetches all `path` entries.
        *   Checks if each `path` exists on the filesystem using `os.path.exists()`.
        *   Deletes rows from the `files` table where the `path` does not exist.
        *   Logs activity to `database_cleanup.log`.
    *   **Wrapper:** `run_cleanup.sh`
        *   Ensures the virtual environment is activated.
        *   Runs `python3 clean_up_database.py`.
        *   Passes any command-line arguments to the Python script (e.g., to specify a different database file).
    *   **Usage:**
        ```bash
        # Navigate to project root
        cd /opt/DenkraumNavigator
        
        # Run cleanup on default DB (file_index.db)
        ./run_cleanup.sh
        
        # Run cleanup on a specific DB file
        ./run_cleanup.sh /path/to/other_db.db
        ```

## Environment Variables

*   `DENKRAUM_DB_FILE`: (Optional) Allows specifying a different database file path for `indexer.py` and `clean_up_database.py` if not provided as a command-line argument. Defaults to `file_index.db`. 