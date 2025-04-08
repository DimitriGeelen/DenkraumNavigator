# Commit, Versioning, and Changelog Workflow

This document outlines the standard process for making commits, bumping versions, and updating the changelog for the DenkraumNavigator project.

## Commit & Versioning Workflow

**Important Note (AI Assistant Interaction):** When instructing the AI assistant to perform a commit using the terminal tool, avoid using multi-line commit messages within the `-m "..."` flag. Use a single-line message instead, or the command may fail.

1.  **Run Unit Tests:** Before committing functional changes, run `pytest -v`. Fix any failures.
2.  **Stage Changes:** Stage the functionally complete changes (`git add .` or specific files).
3.  **Commit Functional Changes:** Commit with a conventional commit message (`git commit -m "type: Description"`).
4.  **Verify Hook:** Observe terminal output to ensure the post-commit hook created `commit_<hash>.db` and `commit_<hash>.zip` backups successfully.
5.  **(Manual) Decide Version Bump:** Determine if the committed changes warrant a version increment (patch, minor, major).
6.  **Perform Version Bump (Scripted Preferred):**
    *   **Recommended Method:** Run the safety wrapper script: `./safe_version_bump.sh --patch | --minor | --major`.
        *   This script automatically performs the following checks before calling the core bumper script:
            *   Verifies the Git working directory is clean.
            *   Runs `pytest` to ensure tests pass.
        *   If checks pass, it then executes `python version_bumper.py` which handles:
            *   Updating `VERSION` file.
            *   Updating `CHANGELOG.md`.
            *   Committing version changes.
            *   Tagging the new version commit.
    *   **(Alternative - Manual):** Follow steps in the previous version of this document (Option A) if manual control is absolutely necessary.
7.  **(Obsolete - Handled by Script):** Steps for manual staging, committing, and tagging are no longer the primary workflow if using the recommended script.
8.  **(Optional) Push:** Push commits and tags to remote (`git push origin <branch> --tags`).

*Note: Backups are primarily named by commit hash. Tags link semantic versions (vX.Y.Z) to specific commits (and thus their hash-named backups) in the Git history.*

## Related Files

*   `VERSION`: Stores the current version number.
*   `CHANGELOG.md`: Records version release notes.
*   `.git/hooks/post-commit`: The script that creates backups after each commit.
*   `version_bumper.py`: The core script that updates version files, commits, and tags.
*   `safe_version_bump.sh`: **Recommended** wrapper script that adds safety checks (clean repo, tests pass) before running `version_bumper.py`. 