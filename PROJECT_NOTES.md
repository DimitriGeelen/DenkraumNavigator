# Project Notes for DenkraumNavigator

This file tracks key decisions, agreed-upon features, and next steps for the DenkraumNavigator project.

## Current Goals (as of 2025-04-06)

1.  **Implement Automatic Backups via Git Hook:**
    *   Create backups of `file_index.db` (`db_commit_<hash>.db`) and code (`code_commit_<hash>.zip`) automatically after each `git commit` using a `post-commit` hook.
    *   Store backups in the `/backups` directory (already added to `.gitignore`).
    *   List commit-based backups (`db_commit_*`, `code_commit_*`) on the `/history` page.
    *   Provide download links for listed backups.
    *   **(Implemented & Tested)** `post-commit` hook is functional.

2.  **Manual Database Backup Functionality:**
    *   Keep the existing button/route (`/backup`) to trigger manual DB backup creation (`file_index_<timestamp>.db`).
    *   List manual DB backups separately on the `/history` page.
    *   Provide download links.
    *   **(Implemented & Tested)**

3.  **Implement Database Restore Functionality:** (Future)
    *   Add a "Restore" button next to each DB backup (manual or commit-based) on the `/history` page.
    *   Implement backend logic.
    *   Include confirmation prompts.
    *   **(Code Implemented - Pending User Testing)**

## Decisions Made

*   Repository Name: `DenkraumNavigator`
*   Tracking Agreements: Using this `PROJECT_NOTES.md` file.
*   Linting: Added `flake8` and `ruff`, fixed initial issues.
*   Backup Strategy: Primarily automatic via `post-commit` hook; manual DB backup retained.

## Development Practices

*   Always add unit tests for new functionality.
*   Ensure any new shell scripts (`.sh`) are made executable (`chmod +x <script_name>.sh`).

## Server Management

*   **Starting:** `source .venv/bin/activate && python app.py`
*   **Stopping:** Find the process ID (`ps aux | grep 'python app.py'`) and use `kill <PID>`, or use `pkill -f 'python app.py'`.
*   **Reliable Restart Script:** Use `./restart_server.sh`. This script handles stopping existing processes before starting a new one, preventing "Address already in use" errors.

## Commit & Versioning

*Please refer to the `COMMIT_VERSIONING_CHANGELOG.md` file for the detailed workflow for commits, version bumps, and changelog updates.*

## Open Questions / Ideas

*   Handling CSS linting errors in `history.html` comments (currently ignored).
*   Pushing local Git repo to a remote (GitHub push failed due to SSH key permissions).

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

### Top Navbar Styling Issue & Solution

*   **Problem:** Applying global styles directly to common HTML elements like `<li>` (e.g., setting a `background` or `padding`) caused unexpected visual bugs in the top navigation bar. Specifically, the navbar links (`<a>` tags inside `<li>` tags) inherited or were affected by the general `<li>` styles, making them appear as boxes instead of plain text links, even when `.navbar a` styles were set correctly.
*   **Solution:**
    1.  **Avoid Global Styles on Generic Elements:** Do not apply backgrounds, borders, or significant padding directly to generic selectors like `li` if those elements are used in structurally different components (like navbars and content lists).
    2.  **Use Specific Selectors for Content:** For styling list items within the main content area (e.g., backup lists, version lists), apply styles using a more specific selector. Add a class (e.g., `content-list`) to the parent `<ul>` and target the list items with `.content-list li`.
    3.  **Explicitly Reset Component Styles:** For components like the navbar, explicitly define styles for its child elements (e.g., `.navbar li`) to reset any potentially inherited properties (like `padding`, `border`, `background`, `display`) to ensure they don't interfere with the intended appearance.

## Recent Fixes (2025-04-07)

*   **Commit Backup Links:** Corrected the glob patterns in `app.py` (`get_commit_details` and `download_commit_package` functions) to match the actual backup filenames created by the `post-commit` hook (`commit_<hash>.*` instead of `db_commit_*` / `code_commit_*`). This ensures the "Download Package" links appear correctly on the `/history` page and function as expected.

# Another test line for commit verification.
# Test line for minor commit after fixing backup links.