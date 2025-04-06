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

## Decisions Made

*   Repository Name: `DenkraumNavigator`
*   Tracking Agreements: Using this `PROJECT_NOTES.md` file.
*   Linting: Added `flake8` and `ruff`, fixed initial issues.
*   Backup Strategy: Primarily automatic via `post-commit` hook; manual DB backup retained.

## Open Questions / Ideas

*   Handling CSS linting errors in `history.html` comments (currently ignored).
*   Pushing local Git repo to a remote (GitHub push failed due to SSH key permissions).

# Test change for commit hook
# Test change for tagged commit
# Final test for code archive fix
# Final test take 2
# Final test take 3 (zip -d) 