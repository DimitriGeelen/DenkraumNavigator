# Project Notes for DenkraumNavigator

This file tracks key decisions, agreed-upon features, and next steps for the DenkraumNavigator project.

*See also: `database_management.md` for details on indexing, backups, versioning, and cleanup.*

## Current Project Goals

*Please refer to the `PROJECT_GOALS.md` file (also editable via the `/goals` webpage) for the list of active goals.*

## Decisions Made

*   Repository Name: `DenkraumNavigator`
*   Tracking Agreements: Using this `PROJECT_NOTES.md` file.
*   Linting: Added `flake8` and `ruff`, fixed initial issues.
*   Backup Strategy: Details in `database_management.md`.
*   Database Versioning: Details in `database_management.md`.

## Development Practices

*Please refer to the `DEVELOPMENT_PRACTICES.md` file for current development guidelines.*

## Server Management

*   **Application Root:** `/opt/DenkraumNavigator` (location of code, venv, logs)
*   **Archive Data Root:** `/dol-data-archive2` (location of files to be indexed, set via `DENKRAUM_ARCHIVE_DIR` environment variable)
*   **Starting/Restarting with Gunicorn:**
    *   Use `cd /opt/DenkraumNavigator && ./restart_server.sh` for development or general use. This binds Gunicorn to `0.0.0.0:5000` (all interfaces).
    *   Use `cd /opt/DenkraumNavigator && ./restart_server_prod.sh` for production. This attempts to bind Gunicorn to the specific LAN IP (e.g., `192.168.x.y:5000`). Ensure the detected IP is correct and accessible.
*   **Stopping:** The restart scripts handle stopping the previous process. Manually, find Gunicorn PID in `gunicorn.pid` and use `kill <PID>`. Avoid `pkill` if possible.
*   **Logs:** Check `gunicorn_access.log` and `gunicorn_error.log` in `/opt/DenkraumNavigator`.

## Commit & Versioning

*Please refer to the `commit.md` file for the detailed workflow for commits, version bumps, and changelog updates.*

## Open Questions / Ideas

*   Handling CSS linting errors in `history.html` comments (currently ignored).
*   Pushing local Git repo to a remote (GitHub push failed due to SSH key permissions).
*   **Improve Test Coverage:** While basic functionality is tested, consider adding more targeted tests for:
    *   **Download Routes:** Explicitly test `/download_file`, `/download_backup`, `/download_code_backup`, `/download_code`, `/download_package` for success and error cases (e.g., file not found, path traversal attempts).
    *   **Browse Route (`/browse/`):** Verify correct directory/file listing and breadcrumb generation for different paths.
    *   **Markdown Editing Routes:** Test loading content and saving updates for `/goals`, `/learnings`, `/md_files`.
    *   **Thumbnail Generation (`/thumbnail/`):** Test thumbnail creation, caching, and serving for various image types and error conditions.
    *   **History Page Content (`/history`):** Assert specific commit/tag details are rendered correctly.
    *   **Search Edge Cases:** Test `search_database` with more complex queries or empty results.

## Web Interface Notes

*   **Navbar:** The top navigation bar items are dynamically generated based on the contents of `menu.md`. Styling is controlled by `static/css/style.css`. See `PAGE_STYLING.md` for detailed styling notes.
*   **Goals Page:** Project goals are managed in `PROJECT_GOALS.md` and can be edited via the `/goals` page.
*   **Floating Page Navigation (Sections):** See `PAGE_STYLING.md` for implementation details.

## Version History Page (`/history`)

**Desired Structure:**

1.  **Top Navbar:** Match the design/links from `index.html`.
2.  **Header:** Display "(App Name) Version History" (using H1).
3.  **List of Tagged Versions:** Iterate through Git tags.
    *   Display: Tag Name (e.g., v0.7.0), associated Commit ID (short hash), Commit Date, Commit Subject (first line of message).
    *   Include a "Download Package" button for each tagged version, linking to a route that bundles the code and database backup associated with that tag's commit.
4.  **Detailed Commit History (Recent Commits):**
    *   Fetch a list of recent commits (e.g., last 50) using `git log`.
    *   For each commit, display:
        *   Commit Hash (short).
        *   Commit Date/Timestamp.
        *   Commit Subject (first line of message).
        *   Tag Name(s) associated with this commit, if any (e.g., v0.7.0).
        *   A "Download Package" button linking to `/download_commit_package/<hash>`, **only if** the corresponding `db_commit_<hash>.db` and `code_commit_<hash>.zip` files exist in the `backups/` directory. (The link should perhaps be greyed out or omitted if backups are missing).
5.  **Manual Backup Section:**
    *   Include the "Create New Manual Database Backup Now" button.
    *   List existing manual DB backups (`file_index_*.db`) with Download and Restore buttons.
6.  **Commit Workflow Notes:** Display the steps from the "Commit & Versioning Workflow" section of these notes.

*Note: The previous sections listing individual commit-based backup *files* (`db_commit_*`, `code_commit_*`) are replaced by the Detailed Commit History section above.*

## Design Notes

*(All styling notes moved to `PAGE_STYLING.md`)*

## Recent Fixes (2025-04-07)

*   **Commit Backup Links:** Corrected the glob patterns in `app.py` (`get_commit_details` and `download_commit_package` functions) to match the actual backup filenames created by the `post-commit` hook (`commit_<hash>.*` instead of `db_commit_*` / `code_commit_*`). This ensures the "Download Package" links appear correctly on the `/history` page and function as expected.

# Another test line for commit verification.
# Test line for minor commit after fixing backup links.

## Development Rules

- When I say lets try to solve in test, we not not switch back to main until i say so

## Open Issues / Assumptions

- **Navbar Rendering (Goals link):** The 'Goals' link sometimes fails to render in the main application (port 5000), showing only 3 menu items. Extensive testing on a minimal server (port 5001) confirmed the menu data, Jinja loop logic, CSS, and `url_for` calls are correct. The main app server also shows frequent 'Killed' messages in logs when run with `debug=True`. **Assumption:** The main app is likely crashing during template rendering (specifically during the loop for the 4th item) due to resource exhaustion (memory/CPU), preventing the final item from being rendered.
- **Thumbnail Test Failures (Skipped):** 5 tests in `tests/test_thumbnail_route.py` are skipped due to persistent mocking/path issues. Patching `os.path.exists` (via decorator or context manager) does not reliably intercept calls made within the route handler. Debugging needed to identify root cause (Flask/mock interaction, path resolution in test env).
- **Duplicate Index Entries:** Search results can show multiple hits for the same filename (e.g., `denkenohnegelaender_logo.eps`) because the source data directory (`/dol-data-archive2`) contains redundant copies of files in different subdirectories. The indexer correctly indexes each unique *path*. 
    - **Option 1 (Recommended):** Clean up the source data directory to remove redundant file copies.
    - **Option 2:** Modify indexer for content-based deduplication (e.g., using file hashes). (More complex)
    - **Option 3:** Filter/group duplicate results in the search UI (`app.py`). (Improves UX, doesn't fix index)
    - **Option 4:** Accept current behavior if duplicate paths are intentional.
- **Push to Remote:** GitHub push failed due to SSH key permissions.
- **Test Warnings (Benign):** The test suite (`pytest -v`) shows several warnings after the v4.5.0 update:
    - `PytestCollectionWarning`: Regarding `test_app` not being a function (expected Flask testing plugin behavior).
    - `UserWarning: Duplicate name`: In `tests/test_download_routes.py::test_download_code_success`, indicating duplicate file paths (`templates/index.html`, `templates/history.html`) were added during the test's zip creation process. This doesn't cause failure but might indicate slight inefficiency in the test logic.

# Test commit for download link verification.
# Test commit for download link verification.
# Test commit for download link verification.
# Test commit for download link verification.
# Test commit for download link verification.
# Test commit for download link verification.
# Test commit for download link verification.
# Test commit for download link verification.
# Test commit for download link verification.
# Test commit for download link verification.
# Test commit for download link verification.
# Test commit for download link verification.
# Test commit for download link verification.

## AI Assistant Capabilities

*   **File/Directory Creation:** While direct file creation tools might not always be available or functional, the assistant *can* use the `run_terminal_cmd` tool to execute `mkdir` and `touch` commands to create directories and empty files.
*   **File Editing:** The assistant can use the `edit_file` tool to add content to existing files (including those just created via the terminal).

## HTML Project Files (Templates)

This section lists the main HTML template files used by the Flask application.

*   `templates/base.html`: Base template providing the overall page structure (head, body, common CSS/JS, navbar structure). Other templates inherit from this.
*   `templates/index.html`: Main page template, includes search filters, keyword cloud, and search results display. Inherits from `base.html`.
*   `templates/browse.html`: Page for browsing the indexed directory structure. Displays subdirectories and files, including thumbnails for images. Inherits from `base.html`.
*   `templates/history.html`: Displays Git version history (tags, commits) and allows management of database backups (manual creation, download, restore). Inherits from `base.html`.
*   `templates/goals.html`: Displays the content of `PROJECT_GOALS.md` in an editable textarea. Inherits from `base.html`.
*   `templates/learnings.html`: Displays the content of `LEARNINGS.md` in an editable textarea. Inherits from `base.html`.
*   `templates/md_files.html`: Allows viewing and editing of various Markdown files in the project root (e.g., `PROJECT_NOTES.md`, `DEVELOPMENT_PRACTICES.md`). Inherits from `base.html`.
*   `templates/tests.html`: Displays a list of discovered unit tests, extracted from the `tests/` directory. Inherits from `base.html`.
*   `templates/config.html`: Displays the current configuration (e.g., `INDEXED_ROOT_DIR`) and allows temporary overrides (for the current session only). Inherits from `base.html`.
*   `templates/config_check.html`: Diagnostic page showing key configuration paths and environment variables. Inherits from `base.html`.
*   `templates/_navbar.html`: Partial template included by `base.html` to render the main navigation bar dynamically based on `menu.md`.

## Project Scripts

This section lists key Python and Shell scripts used for application functionality, maintenance, and development workflows.

**Python Scripts (.py):**

*   `app.py`: The main Flask application file. Defines routes, application logic, database interactions (via helpers), and renders HTML templates.
*   `indexer.py`: **Full Indexer.** Scans the specified directory, clears the existing database (`file_index.db`), extracts metadata/text from files, generates summaries/keywords, and populates the database. Run as `python3 indexer.py <directory>`.
*   `update_index.py`: **Incremental Indexer.** Scans the specified directory and adds/updates entries in the database without clearing existing data. Suitable for adding new files to an existing index. Run as `python3 update_index.py <directory>`.
*   `clean_up_database.py`: **Database Cleaner.** Checks the database for entries whose `path` no longer exists on the filesystem and removes those dead links. Run as `python3 clean_up_database.py`.
*   `searcher.py`: A command-line interface (CLI) script for searching the `file_index.db` database. (Purpose inferred, may need verification).
*   `version_bumper.py`: Script called by `safe_version_bump.sh` to automate version increments, update `VERSION` and `CHANGELOG.md`, zip the database (`file_index.zip`), commit, and tag releases.

**Shell Scripts (.sh):**

*   `restart_server.sh`: Stops any running Gunicorn process for the app and restarts it in the background, binding to `0.0.0.0:5000`. Used for general development/testing.
*   `restart_server_prod.sh`: Similar to `restart_server.sh` but attempts to bind Gunicorn specifically to the detected LAN IP address (e.g., `192.168.x.y:5000`). Intended for production use.
*   `safe_version_bump.sh`: A wrapper script for `version_bumper.py`. Ensures the Git working directory is clean and unit tests pass (`pytest`) before allowing the version bump script to run.
*   `deploy.sh`: (Purpose inferred from `commit.md`) Likely handles deployment tasks, including potentially checking out code and extracting `file_index.db` from the committed `file_index.zip`.
*   `.git/hooks/post-commit`: Git hook script that runs automatically after each commit. Creates database and code backups (`backups/commit_<hash>.*`) and copies the database backup back to the root (`file_index.db`).
*   `run_cleanup.sh`: Wrapper script to run `clean_up_database.py` within the virtual environment. Removes dead links from the database.
*   `reindex.sh`: Wrapper script to run the full indexer (`indexer.py`) within the virtual environment.
# Test commit for download link verification.