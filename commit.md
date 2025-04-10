# Commit, Versioning, and Changelog Workflow

This document outlines the standard process for making commits, bumping versions, and updating the changelog for the DenkraumNavigator project.

## Commit & Versioning Workflow

**Key Changes (Database Handling):**
*   The `post-commit` hook now copies the created database backup (`backups/commit_<hash>.db`) back to overwrite the working `file_index.db`.
*   The `version_bumper.py` script (run via `safe_version_bump.sh`) now zips the current `file_index.db` into `file_index.zip` and commits this zip file alongside `VERSION` and `CHANGELOG.md` for version bump commits.
*   The `deploy.sh` script expects `file_index.zip` to be present in the checked-out code and extracts `file_index.db` from it.

**Important Note (AI Assistant Interaction):** When instructing the AI assistant to perform a commit using the terminal tool, avoid using multi-line commit messages within the `-m "..."` flag. Use a single-line message instead, or the command may fail.

**Standard Workflow:**

1.  **Run Unit Tests:** Before committing functional changes, run `pytest -v`. Fix any failures.
2.  **Stage Changes:** Stage the functionally complete changes (`git add .` or specific files).
3.  **Commit Functional Changes:** Commit with a conventional commit message (`git commit -m "type: Description"`).
4.  **Verify Hook & DB Copy:** Observe terminal output. The post-commit hook should:
    *   Create backups (`commit_<hash>.db`, `commit_<hash>.zip`).
    *   Copy the `commit_<hash>.db` back to the root `file_index.db`.
5.  **(Manual) Decide Version Bump:** Determine if the committed changes warrant a version increment (patch, minor, major).
6.  **Run Version Bump Script:** If bumping version, use the safe wrapper script:
    *   `./safe_version_bump.sh --patch | --minor | --major`
    *   This script will run tests, then execute `version_bumper.py` which:
        *   Updates `VERSION` and `CHANGELOG.md`.
        *   Zips the current `file_index.db` (updated by the last post-commit hook) into `file_index.zip`.
        *   Commits `VERSION`, `CHANGELOG.md`, and `file_index.zip`.
        *   Tags the commit (e.g., `vX.Y.Z`).
7.  **Push Changes & Tags:** Push commits and tags to remote (`git push origin <branch> --tags`).

*Note: The working `file_index.db` is ignored by Git. Only `file_index.zip` is committed with version bumps.*

## Related Files

*   `VERSION`: Stores the current version number.
*   `CHANGELOG.md`: Records version release notes.
*   `.git/hooks/post-commit`: Creates backups and updates working `file_index.db`.
*   `version_bumper.py`: Automates version bumping, zips DB, commits, tags.
*   `safe_version_bump.sh`: Wrapper script for safe execution of `version_bumper.py`.
*   `file_index.db`: The working database (ignored by Git).
*   `file_index.zip`: Zipped version of the working DB (committed with version bumps).
*   `.gitignore`: Defines rules for tracked/ignored files.
*   `deploy.sh`: Deployment script, expects `file_index.zip`. 