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

## Commit Steps

1.  **(If applicable)** Run relevant unit tests (`pytest -v`) to ensure no regressions.
2.  Stage the changed files (`git add <file1> <file2> ...` or `git add .`).
3.  Commit the changes with a descriptive message following conventional commit standards (`git commit -m "type: Short description"`). Examples:
    *   `feat:` (new feature)
    *   `fix:` (bug fix)
    *   `test:` (adding/fixing tests)
    *   `docs:` (documentation changes)
    *   `refactor:` (code changes that neither fix a bug nor add a feature)
    *   `style:` (code style changes - often handled by linters)
4.  Observe the terminal output immediately after commit to verify the `post-commit` hook ran successfully and created the `db_commit_*` and `code_commit_*` backups.
5.  **(Optional/Future)** Push the commit and any tags to the remote repository (`git push origin <branch> --tags`).

## Open Questions / Ideas

*   Handling CSS linting errors in `history.html` comments (currently ignored).
*   Pushing local Git repo to a remote (GitHub push failed due to SSH key permissions). 